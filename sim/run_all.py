"""통합 비교 러너 — engine 정책 + Lucid + Sia를 동일 워크로드로 순차 실행.

트레이스엔 GPU 타입이 없음 → 우리가 클러스터 타입을 지정(단일 b200, 또는 이종).
engine 정책(fifo/sjf/las/kueue/easy/themis/sfqa/sfqa-auto)은 이벤트 구동,
Lucid·Sia는 전용 시뮬(collocation / 라운드 ILP).

차례로(순차) 돌린다 — lucid·sia를 맨 마지막에. 측정 결과는 모두 CSV로 저장:
  - 잡별 (queue,service,gpu)           → <pj-dir>/<policy>_jobs.csv
  - GPU allocation 시계열 추세(전 구간)  → <pj-dir>/<policy>_alloc.csv  (time_s,used_gpu,total_gpu,alloc_pct)
  - 요약(정책별 q·sd·alloc_max·alloc_avg) → <out>

사용:
  run_all.py --csv results/philly_2k_c48.csv --nodes b200:8x14 --round 300 \
     --pj-dir /raid/squad/analysis/uni_single --out .../uni_single.csv
  run_all.py ... --nodes b200:8x5,h100:8x5,a100:8x4 ...   (이종)
"""
import argparse, csv, os, sys, time
sys.path.insert(0, "/home/mystous/gpu_scheduler/sim")
sys.path.insert(0, "/home/mystous/gpu_scheduler/k8s_replay")
sys.path.insert(0, "/home/mystous/gpu_scheduler/squad_ctrl")
from engine import Job, Node, Overheads, Simulator
import policies as P
from lucid_sim import LJob, LucidSim
from sia_sim import SJob, SiaSim

# engine 정책 먼저, lucid·sia 마지막
ENGINE_POLS = ["fifo", "sjf", "las", "kueue", "easy", "themis", "sfqa", "sfqa-auto"]
SLOW_POLS = ["lucid", "sia"]


def load(path):
    out = []
    with open(path) as f:
        for r in csv.DictReader(f):
            out.append((r["job_id"], float(r["arrival_time_s"]), max(1.0, float(r["duration_s"])),
                        int(r["gpu_count"]), str(r.get("preemptible", "")).lower() in ("1", "true")))
    return out


def parse_nodes(spec):
    nodes = []; idx = 0
    for part in spec.split(","):
        typ, rest = part.split(":")
        cnt, rep = (rest.split("x") + ["1"])[:2] if "x" in rest else (rest, "1")
        for _ in range(int(rep)):
            nodes.append(Node(name=f"{typ}-{idx}", gpu_type=typ, total=int(cnt))); idx += 1
    return nodes


def stats(rows):
    """잡별 (queue,service,gpu) → 큐잉지연·stretch(slowdown) 분위수. Gini 폐기."""
    qs = sorted(r[0] for r in rows)
    S = sorted(max((q + s) / max(s, 10), 1.0) for q, s, g in rows)
    p = lambda a, x: a[min(len(a) - 1, int(len(a) * x))] if a else 0
    return dict(n=len(rows), q_p50=p(qs, .5), q_p90=p(qs, .9), q_p99=p(qs, .99),
                q_max=qs[-1] if qs else 0, sd_p50=p(S, .5), sd_p90=p(S, .9),
                sd_max=S[-1] if S else 0)


def run_one(name, jt, nodes_spec, no_ovh, round_s, util_seed, sfqa_beta=None):
    """단일 정책 실행 → {rows(stats용), jobrows(dump용), alloc_*} 반환.
    jobrows: (job_id, arrival_s, start_s, queue_sec, service_sec, gpu_count) — order-fairness용.
    sfqa_beta: 지정 시 sfqa·sfqa-auto의 β 트리거 임계를 덮어씀(101=포화에서도 항상 발동).
"""
    nodes = parse_nodes(nodes_spec)
    ovh = Overheads(enabled=not no_ovh)
    if name == "lucid":
        import random; rng = random.Random(util_seed)
        jobs = [LJob(id=i, arrival=a, duration=d, gpu_count=g,
                     util=min(0.99, max(0.05, rng.gauss(0.6, 0.2)))) for i, a, d, g, pr in jt]
        sim = LucidSim(jobs, nodes, ovh, gss=2); r = sim.run()
        jobrows = [(j.id, j.arrival, j.place_time, j.place_time - j.arrival,
                    max(j.finish_time - j.place_time, 0.1), j.gpu_count)
                   for j in sim.finished if j.place_time >= 0]
    elif name == "sia":
        jobs = [SJob(id=i, arrival=a, duration=d, gpu_count=g, preemptible=pr) for i, a, d, g, pr in jt]
        sim = SiaSim(jobs, nodes, ovh, round_s=round_s); r = sim.run()
        jobrows = [(j.id, j.arrival, j.place_time, max(j.place_time - j.arrival, 0.0),
                    max(j.finish_time - j.place_time, 0.1), j.gpu_count)
                   for j in sim.finished if j.place_time >= 0]
    else:
        jobs = [Job(id=i, arrival=a, duration=d, gpu_count=g, gpu_type="any", preemptible=pr) for i, a, d, g, pr in jt]
        kw = {}
        if sfqa_beta is not None and name in ("sfqa", "sfqa-auto"):
            kw["beta"] = sfqa_beta
        sim = Simulator(jobs, nodes, P.make(name, **kw), overheads=ovh)
        r = sim.run()
        jobrows = [(j.id, j.arrival, j.place_time, j.queue_delay, j.duration, j.gpu_count)
                   for j in sim.finished if j.queue_delay is not None]
    rows = [(jr[3], jr[4], jr[5]) for jr in jobrows]      # (queue, service, gpu) — stats용
    st = stats(rows)
    st["policy"] = name
    st["jobrows"] = jobrows
    st["alloc_series"] = r.get("alloc_series", [])
    st["alloc_max"] = r.get("alloc_max", 0.0)
    st["alloc_avg"] = r.get("alloc_avg", 0.0)
    return st


def dump_policy(pj_dir, st):
    os.makedirs(pj_dir, exist_ok=True)
    # 잡별: 식별자·도착·시작시각 포함(order-fairness 0~100 분포 계산용) + (queue,service,gpu)
    with open(f"{pj_dir}/{st['policy']}_jobs.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["job_id", "arrival_s", "start_s", "queue_sec", "service_sec", "gpu_count"])
        for jid, arr, start, q, s, g in st["jobrows"]:
            w.writerow([jid, round(arr, 1), round(start, 1), round(q, 1), round(s, 1), g])
    # GPU allocation 추세 전 구간(시계열)
    with open(f"{pj_dir}/{st['policy']}_alloc.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["time_s", "used_gpu", "total_gpu", "alloc_pct"])
        for t, u, tot in st["alloc_series"]:
            w.writerow([round(t, 1), u, tot, round(u / tot * 100, 2) if tot else 0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True); ap.add_argument("--nodes", required=True)
    ap.add_argument("--policies", default=",".join(ENGINE_POLS + SLOW_POLS))
    ap.add_argument("--round", type=float, default=300.0)
    ap.add_argument("--no-overhead", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--pj-dir", default=""); ap.add_argument("--out", default="")
    ap.add_argument("--sfqa-beta", type=float, default=None,
                    help="sfqa·sfqa-auto β 트리거 임계 override (101=포화에서도 항상 발동)")
    a = ap.parse_args()
    jt = load(a.csv)
    # lucid·sia를 항상 맨 마지막으로 정렬
    pols = a.policies.split(",")
    pols = [p for p in pols if p not in SLOW_POLS] + [p for p in pols if p in SLOW_POLS]
    tot = sum(int(p.split(":")[1].split("x")[0]) * (int(p.split("x")[1]) if "x" in p else 1)
              for p in a.nodes.split(","))
    print(f"jobs={len(jt)}, nodes={a.nodes} ({tot} GPU), policies={pols} 순차", flush=True)
    results = []
    for name in pols:
        t0 = time.time()
        st = run_one(name, jt, a.nodes, a.no_overhead, a.round, a.seed,
                     sfqa_beta=a.sfqa_beta)
        dt = time.time() - t0
        print(f"  ✓ {st['policy']:12} n={st['n']:>5} q p50/p90/max={st['q_p50']:.0f}/{st['q_p90']:.0f}/{st['q_max']:.0f}"
              f"  alloc max/avg={st['alloc_max']:.1f}/{st['alloc_avg']:.1f}%  ({dt:.1f}s)", flush=True)
        if a.pj_dir:
            dump_policy(a.pj_dir, st)
        del st["jobrows"]; del st["alloc_series"]
        results.append(st)
    print(f"\n{'정책':12} {'n':>5} {'q_p50':>7} {'q_p90':>8} {'q_max':>8} {'sd_max':>7} {'alloc_max':>9} {'alloc_avg':>9}")
    print("-" * 78)
    for r in results:
        print(f"{r['policy']:12} {r['n']:>5} {r['q_p50']:>7.0f} {r['q_p90']:>8.0f} {r['q_max']:>8.0f} "
              f"{r['sd_max']:>7.0f} {r['alloc_max']:>9.1f} {r['alloc_avg']:>9.1f}")
    if a.out:
        d = os.path.dirname(a.out)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(a.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["policy", "n", "q_p50", "q_p90", "q_p99", "q_max",
                                              "sd_p50", "sd_p90", "sd_max", "alloc_max", "alloc_avg"])
            w.writeheader(); w.writerows(results)
        print(f"→ {a.out}")


if __name__ == "__main__":
    main()
