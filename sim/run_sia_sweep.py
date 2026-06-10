"""Sia(라운드 ILP) 전용 스윕 러너 — run_sweep와 동일한 형식으로 summary.csv의 sia 행만 갱신.

run_sweep.py는 sia를 실행하지 않고 기존 행을 보존만 한다(계산비용 큼). 이 스크립트는 수정된
SiaSim(실 ILP)을 vc 트레이스로 돌려 cmp<gpu>_<kind>/summary.csv의 sia 행을 교체하고,
sia_jobs.csv / sia_alloc.csv 를 덤프한다(analyze_sweep의 order-fairness 계산용).

사용:
  python3 sim/run_sia_sweep.py --gpus 512 --kinds single,hetero
  python3 sim/run_sia_sweep.py            # 기본 512 single,hetero
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engine import Node, Overheads          # noqa: E402
from sia_sim import SJob, SiaSim            # noqa: E402
import run_sweep as RS                       # noqa: E402

COLS = ["policy", "n", "q_p50", "q_p90", "q_p99", "q_max",
        "sd_p50", "sd_p90", "sd_max", "alloc_max", "alloc_avg"]


def run_sia(trace, nodes_proto, ovh, round_s):
    nodes = [Node(name=n.name, gpu_type=n.gpu_type, total=n.total) for n in nodes_proto]
    jobs = [SJob(id=i, arrival=a, duration=d, gpu_count=g)
            for i, a, d, g, vc in trace]
    sim = SiaSim(jobs, nodes, ovh, round_s=round_s)
    r = sim.run()
    jr = [(j.id, j.arrival, j.place_time, max(j.place_time - j.arrival, 0.0),
           max(j.finish_time - j.place_time, 0.1), j.gpu_count)
          for j in sim.finished if j.place_time >= 0]
    qs = [x[3] for x in jr]; ss = [x[4] for x in jr]; gs = [x[5] for x in jr]
    st = RS.stats(qs, ss, gs); st["policy"] = "sia"
    st["alloc_max"] = r.get("alloc_max", 0.0); st["alloc_avg"] = r.get("alloc_avg", 0.0)
    return st, jr, r.get("alloc_series", [])


def upsert_summary(summ_path, st):
    """summary.csv의 sia 행을 교체(없으면 추가). 다른 정책 행은 보존."""
    rows = []
    if os.path.exists(summ_path):
        with open(summ_path) as f:
            rows = [r for r in csv.DictReader(f)]
    rows = [r for r in rows if r.get("policy") != "sia"]
    rows.append({k: st.get(k, "") for k in COLS})
    # 표준 정책 순서로 정렬
    order = ["fifo", "sjf", "las", "kueue", "easy", "themis",
             "sfqa", "sfqa-auto", "fgd", "lucid", "sia"]
    rows.sort(key=lambda r: order.index(r["policy"]) if r["policy"] in order else 99)
    with open(summ_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    vc = os.path.join(HERE, "sweep_trace_vc.csv")
    ap.add_argument("--trace", default=vc if os.path.exists(vc) else os.path.join(HERE, "sweep_trace.csv"))
    ap.add_argument("--gpus", default="512")
    ap.add_argument("--kinds", default="single,hetero")
    ap.add_argument("--round", type=float, default=300.0)
    ap.add_argument("--no-overhead", action="store_true")
    ap.add_argument("--results", default=os.path.join(HERE, "sweep_results"))
    a = ap.parse_args()

    trace = RS.load_trace(a.trace)
    ovh = Overheads(enabled=not a.no_overhead)
    gpus = [int(x) for x in a.gpus.split(",")]
    kinds = a.kinds.split(",")
    print(f"trace n={len(trace)}, gpus={gpus}, kinds={kinds}, overhead={not a.no_overhead}", flush=True)

    for gpu in gpus:
        for kind in kinds:
            nodes = RS.build_nodes(gpu, kind)
            tag = f"cmp{gpu}_{kind}"
            print(f"\n== {tag}  ({gpu} GPU, {kind}) sia 시작 ==", flush=True)
            st, jr, alloc = run_sia(trace, nodes, ovh, a.round)
            print(f"  ✓ sia  q p50/p90/max={st['q_p50']:.0f}/{st['q_p90']:.0f}/{st['q_max']:.0f}"
                  f"  alloc avg={st['alloc_avg']:.1f}%", flush=True)
            outdir = os.path.join(a.results, tag)
            os.makedirs(outdir, exist_ok=True)
            RS.dump(outdir, "sia", jr, alloc)
            upsert_summary(os.path.join(outdir, "summary.csv"), st)
            print(f"  → {outdir}/summary.csv 갱신", flush=True)


if __name__ == "__main__":
    main()
