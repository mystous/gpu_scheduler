"""병렬 워커 — (gpu, kind, policy) 한 조합을 독립 프로세스로 실행.

스케줄러끼리 의존성이 없으므로 조합마다 별도 프로세스로 동시에 돌린다. 공유 파일 경쟁을
피하기 위해 각 워커는 자기 정책 전용 산출물만 쓴다:
  - raw 덤프:  cmp<gpu>_<kind>/<policy>_jobs.csv, <policy>_alloc.csv   (정책별 파일)
  - fragment:  cmp<gpu>_<kind>/_frag_<policy>.csv                      (단일 행 요약)
merge 단계(par_merge.py)가 fragment들을 모아 summary.csv를 만든다.

사용: python3 par_worker.py <gpu> <kind> <policy> [--trace PATH] [--no-overhead] [--round S]
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engine import Node, Overheads          # noqa: E402
import run_sweep as RS                       # noqa: E402

COLS = ["policy", "n", "q_p50", "q_p90", "q_p99", "q_max",
        "sd_p50", "sd_p90", "sd_max", "alloc_max", "alloc_avg"]


def run_sia_combo(trace, nodes_proto, ovh, round_s):
    from sia_sim import SJob, SiaSim
    nodes = [Node(name=n.name, gpu_type=n.gpu_type, total=n.total) for n in nodes_proto]
    jobs = [SJob(id=i, arrival=a, duration=d, gpu_count=g) for i, a, d, g, vc in trace]
    sim = SiaSim(jobs, nodes, ovh, round_s=round_s); r = sim.run(progress_every=500)
    jr = [(j.id, j.arrival, j.place_time, max(j.place_time - j.arrival, 0.0),
           max(j.finish_time - j.place_time, 0.1), j.gpu_count)
          for j in sim.finished if j.place_time >= 0]
    qs = [x[3] for x in jr]; ss = [x[4] for x in jr]; gs = [x[5] for x in jr]
    st = RS.stats(qs, ss, gs); st["policy"] = "sia"
    st["alloc_max"] = r.get("alloc_max", 0.0); st["alloc_avg"] = r.get("alloc_avg", 0.0)
    return st, jr, r.get("alloc_series", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gpu", type=int)
    ap.add_argument("kind")
    ap.add_argument("policy")
    vc = os.path.join(HERE, "sweep_trace_vc.csv")
    ap.add_argument("--trace", default=vc if os.path.exists(vc) else os.path.join(HERE, "sweep_trace.csv"))
    ap.add_argument("--results", default=os.path.join(HERE, "sweep_results"))
    ap.add_argument("--no-overhead", action="store_true")
    ap.add_argument("--round", type=float, default=300.0)
    a = ap.parse_args()

    trace = RS.load_trace(a.trace)
    ovh = Overheads(enabled=not a.no_overhead)
    nodes = RS.build_nodes(a.gpu, a.kind)
    tag = f"cmp{a.gpu}_{a.kind}"
    outdir = os.path.join(a.results, tag)
    os.makedirs(outdir, exist_ok=True)

    if a.policy == "sia":
        st, jr, alloc = run_sia_combo(trace, nodes, ovh, a.round)
    else:
        st, jr, alloc = RS.run_policy(a.policy, trace, nodes, ovh)

    RS.dump(outdir, a.policy, jr, alloc)
    frag = os.path.join(outdir, f"_frag_{a.policy}.csv")
    with open(frag, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader()
        w.writerow({k: st.get(k, "") for k in COLS})
    print(f"[done] {tag}/{a.policy}  q p50/p90/max="
          f"{st['q_p50']:.0f}/{st['q_p90']:.0f}/{st['q_max']:.0f}  alloc={st['alloc_avg']:.1f}%",
          flush=True)


if __name__ == "__main__":
    main()
