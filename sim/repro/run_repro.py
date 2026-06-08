"""옛 증강 작업 로그를 '새 시뮬레이터(sim/)'로 재실험 — SFQA 효과·배치 비종속성.

C++(옛 시뮬레이터)가 아니라 Python 이산사건 시뮬레이터로, 2024년과 동일한 작업 트레이스
(analysis_results/zjob_...augemented_new_ver.csv, 3,001잡)를 그대로 입력해
  · Normal(=FIFO, SFQA 미적용) vs SFQA(α=0.72)
  · 배치 most-allocated vs compact (둘 다 새 sim에 구현됨; round_robin/mcts는 미구현)
를 돌려 GPU 할당률(used/total) 시계열을 data/에 저장한다.

토폴로지는 옛 server(14대/84 가속기: a100×8 ×7, a30×4 ×7)와 동일.
옛 로그의 duration은 이미 실제 실행시간이므로 새 sim의 타입별 speed 배수를 1.0으로 두어
이중 적용을 막는다(타입 매칭은 유지).

사용: python3 sim/repro/run_repro.py
출력: sim/repro/data/<placement>_<mode>_alloc.csv  (t_s,used,total,rate_pct)
"""
import csv
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.dirname(HERE)
ROOT = os.path.dirname(SIM)
sys.path.insert(0, SIM)
sys.path.insert(0, os.path.join(ROOT, "squad_ctrl"))   # squad_algo (policies.py 의존)

import engine                       # noqa: E402
from engine import Job, Node, Overheads, Simulator   # noqa: E402
import policies as P                # noqa: E402

# 옛 로그 duration=실제 실행시간 → 타입 speed 배수 제거(이중 적용 방지). 타입 매칭은 유지.
engine.SPEED = {"a100": 1.0, "a30": 1.0, "any": 1.0}

OLD_LOG = os.path.join(ROOT, "analysis_results",
                       "zjob_flow_total(task,flavor,single)_augemented_new_ver.csv")
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)


def _parse_dt(s):
    return datetime.fromisoformat(s.strip())


def load_old_log(path):
    """옛 증강 로그 → Job 리스트. arrival=start-min(start), duration=finish-start(초)."""
    rows = list(csv.DictReader(open(path)))
    t0 = min(_parse_dt(r["start"]) for r in rows)
    jobs = []
    for i, r in enumerate(rows):
        st, fi = _parse_dt(r["start"]), _parse_dt(r["finish"])
        jobs.append(Job(
            id=r["pod_name"] or f"job{i}",
            arrival=(st - t0).total_seconds(),
            duration=max(1.0, (fi - st).total_seconds()),
            gpu_count=int(r["count"]),
            gpu_type=r["flavor"].strip().lower(),     # A100→a100, A30→a30
            preemptible=str(r.get("preemption", "")).strip().lower() in ("y", "1", "true")))
    return jobs


def make_nodes():
    """옛 server.csv와 동일: gpu_server01-07 = a100×8, gpu_server10-16 = a30×4 (84 GPU)."""
    nodes = [Node(name=f"a100-{i}", gpu_type="a100", total=8) for i in range(7)]
    nodes += [Node(name=f"a30-{i}", gpu_type="a30", total=4) for i in range(7)]
    return nodes


def run_one(jobs, placement_fn, mode):
    """mode: 'normal'(FIFO) | 'sfqa'(α=0.72). placement_fn 배치로 실행 → (results, sim)."""
    pol = P.FIFO() if mode == "normal" else P.SFQA(alpha=0.72, beta=100.0)
    pol.pref_fn = staticmethod(placement_fn)          # most-allocated / compact 주입
    sim = Simulator(jobs, make_nodes(), pol, overheads=Overheads(enabled=False))
    r = sim.run()
    return r, sim


def save_series(series, name):
    out = os.path.join(DATA, name + "_alloc.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "used", "total", "rate_pct"])
        for t, used, total in series:
            w.writerow([f"{t:.1f}", used, total, f"{100.0 * used / total:.4f}"])
    print(f"  saved {out}  ({len(series)} samples)", flush=True)


def main():
    print(f"loading old log: {os.path.basename(OLD_LOG)}", flush=True)
    jobs = load_old_log(OLD_LOG)
    print(f"  {len(jobs)} jobs, {sum(j.gpu_count for j in jobs)} total GPU-requests", flush=True)
    placements = {"mostalloc": P.pref_mostallocated, "compact": P.pref_compact}
    print(f"\n{'run':22} {'q_p50':>8} {'q_p90':>9} {'q_max':>10} {'alloc_avg':>9}", flush=True)
    for pname, pfn in placements.items():
        for mode in ("normal", "sfqa"):
            r, sim = run_one(jobs, pfn, mode)
            save_series(r["alloc_series"], f"{pname}_{mode}")
            print(f"{pname+'/'+mode:22} {r['q_p50']:>8.0f} {r['q_p90']:>9.0f} {r['q_max']:>10.0f} {r['alloc_avg']:>8.1f}%", flush=True)
            qs = sorted(j.queue_delay for j in sim.finished if j.queue_delay is not None)
            with open(os.path.join(DATA, f"{pname}_{mode}_queue.csv"), "w", newline="") as f:
                w = csv.writer(f); w.writerow(["queue_delay_s"])
                for q in qs:
                    w.writerow([f"{q:.1f}"])
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
