"""시뮬레이터 실행기 — 트레이스 로드 → 정책별 시뮬 → 결과 표.

워크로드는 실측과 동일 파이프라인(k8s_replay.ingest + 층화 + clamp)을 재사용해
실측↔시뮬 정합(calibrate)을 보장. 시간압축 S는 시뮬엔 불필요(이벤트 구동이라
실제 초 단위로 즉시 계산)하지만, 실측과 절대값 비교하려면 동일 clamp/sample 적용.

사용:
  run_sim.py --trace philly --sample 2000 --clamp-over 172800 \
             --policies fifo,sjf,las,easy,kueue,sfqa,sfqa-auto,sfqa-auto-rsv,lucid,sia,themis \
             --total-gpu 8 [--ptr] [--no-overhead]
  run_sim.py --csv results/philly_2k_c48.csv --policies ...   (저장된 샘플 직접)
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, "/home/mystous/gpu_scheduler/sim")
sys.path.insert(0, "/home/mystous/gpu_scheduler/k8s_replay")
sys.path.insert(0, "/home/mystous/gpu_scheduler/squad_ctrl")

from engine import Job, Node, Overheads, Simulator   # noqa: E402
import policies as P                                   # noqa: E402


def load_csv(path):
    jobs = []
    with open(path) as f:
        for r in csv.DictReader(f):
            jobs.append(Job(
                id=r["job_id"], arrival=float(r["arrival_time_s"]),
                duration=max(1.0, float(r["duration_s"])),
                gpu_count=int(r["gpu_count"]),
                gpu_type=r.get("gpu_type", "any") or "any",
                preemptible=str(r.get("preemptible", "")).lower() in ("1", "true")))
    return jobs


def load_trace(args):
    from ingest import INGESTERS
    from run_experiment import stratified_sample
    js = INGESTERS[args.trace](args.input, limit=args.limit)
    if args.clamp_over > 0:
        for j in js:
            if j.duration > args.clamp_over:
                j.duration = args.clamp_over
    if args.window_days > 0:
        t0 = min(j.arrival_time for j in js)
        ws, we = t0 + args.window_start_day * 86400, t0 + (args.window_start_day + args.window_days) * 86400
        js = [j for j in js if ws <= j.arrival_time < we]
        rb = min(j.arrival_time for j in js)
        for j in js:
            j.arrival_time -= rb
    if args.sample > 0:
        js = stratified_sample(js, args.sample, args.seed)
    t0 = min(j.arrival_time for j in js)
    return [Job(id=j.job_id, arrival=j.arrival_time - t0, duration=max(1.0, j.duration),
                gpu_count=j.gpu_count, gpu_type="any", preemptible=j.preemptible) for j in js]


def make_nodes(spec):
    """spec: 'b200:8' 또는 'b200:8,h100:8,a100:8' (이종)."""
    nodes = []
    for i, part in enumerate(spec.split(",")):
        typ, cnt = part.split(":")
        nodes.append(Node(name=f"{typ}-{i}", gpu_type=typ, total=int(cnt)))
    return nodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace"); ap.add_argument("--input")
    ap.add_argument("--csv", help="저장된 샘플 CSV 직접 로드")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--clamp-over", type=float, default=0.0)
    ap.add_argument("--window-start-day", type=float, default=0.0)
    ap.add_argument("--window-days", type=float, default=0.0)
    ap.add_argument("--nodes", default="b200:8", help="토폴로지: 'b200:8' 또는 이종 'b200:8,h100:8'")
    ap.add_argument("--policies", default="fifo,sjf,las,easy,kueue,sfqa,sfqa-auto,sfqa-auto-rsv")
    ap.add_argument("--ptr", action="store_true", help="PTR 디프래그 활성(미구현 시 무시)")
    ap.add_argument("--no-overhead", action="store_true", help="오버헤드 0(순수 정책 비교)")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    jobs = load_csv(args.csv) if args.csv else load_trace(args)
    total_gpu = sum(int(p.split(":")[1]) for p in args.nodes.split(","))
    print(f"jobs={len(jobs)}, nodes={args.nodes} (총 {total_gpu} GPU), "
          f"overhead={'off' if args.no_overhead else 'on'}", flush=True)

    rows = []
    hdr = f"{'정책':14} {'n':>5} {'q_p50':>6} {'q_p90':>6} {'q_p99':>7} {'q_max':>7} {'bsld50':>6} {'bsldmax':>7} {'alloc%':>6} {'makespan':>9}"
    print(hdr); print("-" * len(hdr))
    for name in args.policies.split(","):
        nodes = make_nodes(args.nodes)   # 정책마다 새 토폴로지
        js = [Job(id=j.id, arrival=j.arrival, duration=j.duration, gpu_count=j.gpu_count,
                  gpu_type=j.gpu_type, preemptible=j.preemptible) for j in jobs]
        ovh = Overheads(enabled=not args.no_overhead)
        pol = P.make(name)
        sim = Simulator(js, nodes, pol, overheads=ovh)
        r = sim.run()
        print(f"{name:14} {r['n']:>5} {r['q_p50']:>6.0f} {r['q_p90']:>6.0f} {r['q_p99']:>7.0f} "
              f"{r['q_max']:>7.0f} {r['bsld_p50']:>6.1f} {r['bsld_max']:>7.1f} "
              f"{r['alloc_max']:>5.0f}% {r['makespan']/3600:>7.1f}h", flush=True)
        rows.append({"policy": name, **r})

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"→ {args.out}")


if __name__ == "__main__":
    main()
