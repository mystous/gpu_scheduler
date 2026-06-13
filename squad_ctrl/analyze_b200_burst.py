"""B200 버스트 캠페인 분석기 (b_* run) — blocking-aware 컨트롤러 실측.

버스트 캠페인은 submit-clamp 0 (버스트 보존)이라 **트레이스 도착이 물리적 도착**이다.
순서 공정성을 trace-arrival 기준으로 산출하되, wall 기준도 함께 출력해 둘이 일치하는지 검증
(submit-clamp 0이면 wall≈trace-arrival, 둘 다 보고).

지표: q p50/p90/max, BSLD (q+s)/max(s,10), 순서공정성 fair_mean/lt50/p1 (trace+wall), alloc.
정의는 시뮬 sim/order_fairness.py 와 동일(per_job_score).
실행: /raid/squad/venv/bin/python analyze_b200_burst.py
"""
import csv
import os
import sys

sys.path.insert(0, "/home/mystous/gpu_scheduler/sim")
from order_fairness import per_job_score   # noqa: E402

RUNS = "/raid/squad/runs"
OUTDIR = "/home/mystous/gpu_scheduler/results"
BSLD_TAU = 10.0

RUNSET = [
    ("b_auto_block",    "SAFA blocking+counter (Δ5)"),
    ("b_auto_greedy",   "SAFA greedy+wall (대조)"),
    ("b_auto_d1",       "SAFA blocking+counter (Δ1)"),
    ("b_fifo",          "FIFO blocking"),
    ("b_auto_block_r2", "SAFA blocking+counter (반복)"),
    ("b_fifo_r2",       "FIFO blocking (반복)"),
]


def pctl(a, p):
    a = sorted(a)
    return a[min(len(a) - 1, int(len(a) * p))] if a else 0.0


def fairness(jobs):
    sc = sorted(per_job_score(jobs)); n = len(sc)
    if n == 0:
        return 0.0, 0.0, 0.0
    return sum(sc) / n, 100 * sum(1 for s in sc if s < 50) / n, sc[n // 100]


def analyze(run_id):
    jp = f"{RUNS}/{run_id}/jct.csv"
    sp = f"{RUNS}/{run_id}/submit_log.csv"
    mp = f"{RUNS}/{run_id}/metrics.csv"
    if not os.path.exists(jp):
        return None
    rows = list(csv.DictReader(open(sp)))
    tarr = {x["job"]: float(x["arrival"]) for x in rows}   # 트레이스 도착(물리적 = submit-clamp 0)
    wall = {x["job"]: float(x["wall"]) for x in rows}      # 실제 wall 제출
    qs, bs, jt, jw = [], [], [], []
    for x in csv.DictReader(open(jp)):
        if not x["queue_sec"] or not x["jct_sec"]:
            continue
        q = float(x["queue_sec"]); j = float(x["jct_sec"]); s = max(j - q, 0.0)
        qs.append(q); bs.append((q + s) / max(s, BSLD_TAU))
        job = x["pod"].rsplit("-", 1)[0]
        if job in tarr:
            jt.append((tarr[job], tarr[job] + q, 0))
        if job in wall:
            jw.append((wall[job], wall[job] + q, 0))
    fmean_t, lt50_t, p1_t = fairness(jt)
    fmean_w, lt50_w, p1_w = fairness(jw)
    alloc = [float(x["alloc_pct"]) for x in csv.DictReader(open(mp))] if os.path.exists(mp) else [0.0]
    return dict(
        n=len(qs), q_p50=pctl(qs, .5), q_p90=pctl(qs, .9), q_max=max(qs) if qs else 0,
        bsld_p50=pctl(bs, .5), bsld_max=max(bs) if bs else 0,
        fair_mean=fmean_t, lt50=lt50_t, p1=p1_t,                 # 주: trace-arrival
        fair_mean_wall=fmean_w, lt50_wall=lt50_w, p1_wall=p1_w,  # 검증: wall
        alloc_avg=sum(alloc) / len(alloc),
    )


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    rows = []
    print(f"{'정책':30} {'q_p50':>6} {'q_max':>6} {'BSLDp50':>7} {'fair':>5} {'lt50%':>6} {'p1':>5} "
          f"{'lt50_w':>6} {'p1_w':>5} {'alloc':>5}")
    for rid, lbl in RUNSET:
        s = analyze(rid)
        if not s:
            print(f"{lbl:30}  (결과 없음)"); continue
        s["run"] = rid; s["policy"] = lbl; rows.append(s)
        print(f"{lbl:30} {s['q_p50']:6.0f} {s['q_max']:6.0f} {s['bsld_p50']:7.2f} {s['fair_mean']:5.1f} "
              f"{s['lt50']:6.1f} {s['p1']:5.1f} {s['lt50_wall']:6.1f} {s['p1_wall']:5.1f} {s['alloc_avg']:4.0f}%")
    fields = ["run", "policy", "n", "q_p50", "q_p90", "q_max", "bsld_p50", "bsld_max",
              "fair_mean", "lt50", "p1", "fair_mean_wall", "lt50_wall", "p1_wall", "alloc_avg"]
    with open(f"{OUTDIR}/b200_burst_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"\n→ {OUTDIR}/b200_burst_summary.csv ({len(rows)} run)")


if __name__ == "__main__":
    main()
