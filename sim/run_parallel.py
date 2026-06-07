"""여러 스케줄러를 동시에(멀티프로세스) 시뮬 — wall-clock = 가장 느린 1개.

각 정책을 독립 프로세스로 실행하므로 N정책이 N코어를 병렬 사용. 전체 트레이스처럼
정책당 수십 초~분이 걸려도 동시에 끝난다. 시뮬은 이벤트 구동이라 시간축 압축 불필요
(실제 초 단위 그대로, 오버헤드도 실제 스케일 — 압축 시엔 오버헤드도 동일 비율로 환산).

사용:
  run_parallel.py --csv results/philly_2k_c48.csv --nodes b200:8 \
    --policies fifo,sjf,las,kueue,easy,sfqa,sfqa-auto,sfqa-auto-rsv,lucid,sia,themis \
    --out /raid/squad/analysis/sim_c48_par.csv
  run_parallel.py --trace philly --input <log> --clamp-over 172800 --nodes b200:8 ...  (전체)
"""
import argparse
import csv
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/home/mystous/gpu_scheduler/sim")
sys.path.insert(0, "/home/mystous/gpu_scheduler/k8s_replay")
sys.path.insert(0, "/home/mystous/gpu_scheduler/squad_ctrl")

from engine import Job, Node, Overheads, Simulator   # noqa: E402
import policies as P                                   # noqa: E402


def load_csv(path):
    out = []
    with open(path) as f:
        for r in csv.DictReader(f):
            out.append((r["job_id"], float(r["arrival_time_s"]), max(1.0, float(r["duration_s"])),
                        int(r["gpu_count"]), r.get("gpu_type", "any") or "any",
                        str(r.get("preemptible", "")).lower() in ("1", "true")))
    return out


def load_trace(args):
    from ingest import INGESTERS
    from run_experiment import stratified_sample
    js = INGESTERS[args.trace](args.input, limit=args.limit)
    if args.clamp_over > 0:
        for j in js:
            if j.duration > args.clamp_over:
                j.duration = args.clamp_over
    if args.sample > 0:
        js = stratified_sample(js, args.sample, args.seed)
    t0 = min(j.arrival_time for j in js)
    return [(j.job_id, j.arrival_time - t0, max(1.0, j.duration), j.gpu_count, "any", j.preemptible)
            for j in js]


def _parse_nodes(spec):
    """'b200:8' | 'b200:8x114'(114노드) | 'b200:8x57,h100:8x57'(이종) 노드 리스트 생성."""
    nodes = []
    idx = 0
    for part in spec.split(","):
        typ, rest = part.split(":")
        if "x" in rest:
            cnt, rep = rest.split("x"); cnt, rep = int(cnt), int(rep)
        else:
            cnt, rep = int(rest), 1
        for _ in range(rep):
            nodes.append(Node(name=f"{typ}-{idx}", gpu_type=typ, total=cnt)); idx += 1
    return nodes


def run_one(args_tuple):
    """별도 프로세스: (policy_name, job_tuples, nodes_spec, no_overhead) → 결과 dict."""
    name, job_tuples, nodes_spec, no_ovh, compress, pj_dir = args_tuple
    jobs = [Job(id=t[0], arrival=t[1] / compress, duration=t[2] / compress, gpu_count=t[3],
                gpu_type=t[4], preemptible=t[5]) for t in job_tuples]
    nodes = _parse_nodes(nodes_spec)
    ovh = Overheads(enabled=not no_ovh)
    # 압축 시 오버헤드도 동일 비율(시간 단위 환산) — 사용자 지적 반영
    if compress != 1.0 and not no_ovh:
        ovh.sched_lat /= compress; ovh.startup_solo /= compress
        ovh.startup_busy /= compress; ovh.teardown /= compress
    prog = None
    if pj_dir:
        import os as _os
        _os.makedirs(f"{pj_dir}/status", exist_ok=True)
        sp = f"{pj_dir}/status/{name}.prog"
        def prog(done, total, wlen, _sp=sp):
            with open(_sp, "w") as f:
                f.write(f"{done}/{total} wait={wlen}")
    sim = Simulator(jobs, nodes, P.make(name), overheads=ovh, progress=prog)
    r = sim.run()
    if pj_dir:
        with open(f"{pj_dir}/status/{name}.prog", "w") as f:
            f.write(f"DONE {r['n']}/{len(job_tuples)}")
    r["policy"] = name
    # 압축 결과를 실제 스케일로 복원(×C)
    if compress != 1.0:
        for k in ("q_p50", "q_p90", "q_p99", "q_max", "j_p50", "j_p90", "j_max", "makespan"):
            r[k] *= compress
    if pj_dir:                                # 잡별 (q,s,g) 덤프 → fairness 분석용
        import os as _os
        _os.makedirs(pj_dir, exist_ok=True)
        with open(f"{pj_dir}/{name}_jobs.csv", "w", newline="") as f:
            wr = csv.writer(f); wr.writerow(["queue_sec", "service_sec", "gpu_count"])
            for q, s, g in sim.per_job():
                wr.writerow([round(q * compress, 1), round(s * compress, 1), g])
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace"); ap.add_argument("--input"); ap.add_argument("--csv")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--clamp-over", type=float, default=0.0)
    ap.add_argument("--nodes", default="b200:8")
    ap.add_argument("--policies", default="fifo,sjf,las,kueue,easy,sfqa,sfqa-auto,sfqa-auto-rsv,lucid,sia,themis")
    ap.add_argument("--no-overhead", action="store_true")
    ap.add_argument("--compress", type=float, default=1.0,
                    help="계산 가속용 시간축 압축(이벤트 구동이라 보통 1.0이면 충분). 오버헤드도 동일 압축됨")
    ap.add_argument("--workers", type=int, default=0, help="0=정책 수만큼")
    ap.add_argument("--pj-dir", default="", help="잡별 (q,s,g) 덤프 디렉터리 — fairness 분석용")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    job_tuples = load_csv(args.csv) if args.csv else load_trace(args)
    pols = args.policies.split(",")
    print(f"jobs={len(job_tuples)}, nodes={args.nodes}, policies={len(pols)} 병렬, "
          f"overhead={'off' if args.no_overhead else 'on'}, compress={args.compress}", flush=True)

    tasks = [(p, job_tuples, args.nodes, args.no_overhead, args.compress, args.pj_dir) for p in pols]
    workers = args.workers or len(pols)
    results = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(run_one, tasks):
            results.append(r)
            print(f"  ✓ {r['policy']:14} q p50/p90/p99/max={r['q_p50']:.0f}/{r['q_p90']:.0f}/"
                  f"{r['q_p99']:.0f}/{r['q_max']:.0f} bsld50/max={r['bsld_p50']:.1f}/{r['bsld_max']:.1f} "
                  f"mk={r['makespan']/3600:.0f}h", flush=True)

    order = {p: i for i, p in enumerate(pols)}
    results.sort(key=lambda r: order[r["policy"]])
    hdr = f"\n{'정책':14} {'q_p50':>7} {'q_p90':>8} {'q_p99':>8} {'q_max':>8} {'bsld50':>6} {'bsldmax':>8} {'alloc%':>6}"
    print(hdr); print("-" * len(hdr))
    for r in results:
        print(f"{r['policy']:14} {r['q_p50']:>7.0f} {r['q_p90']:>8.0f} {r['q_p99']:>8.0f} "
              f"{r['q_max']:>8.0f} {r['bsld_p50']:>6.1f} {r['bsld_max']:>8.1f} {r['alloc_max']:>5.0f}%")
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["policy", "n", "q_p50", "q_p90", "q_p99", "q_max",
                                              "j_p50", "j_p90", "j_max", "bsld_p50", "bsld_p90",
                                              "bsld_max", "alloc_max", "alloc_avg", "makespan",
                                              "ptr_migrations"])
            w.writeheader()
            for r in results:
                w.writerow({k: r.get(k, "") for k in w.fieldnames})
        print(f"→ {args.out}")


if __name__ == "__main__":
    main()
