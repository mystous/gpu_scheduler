"""B200 heavy-tail 캠페인 분석기 (m_ht_* run).

압축 캠페인용 analyze_b200.py와 분리: 이 캠페인은 `--submit-clamp`로 도착을 압축했으므로
**순서 공정성을 wall 제출시각 기준**으로 계산해야 한다(트레이스 도착은 κ로 11h 스팬이라
trace-arrival 기준이면 start≈arrival이 되어 lt50이 0으로 인위 포화됨).

지표: q p50/p90/max, BSLD(q+s)/max(s,10), 순서공정성 fair_mean/lt50/p1(wall 기준), alloc.
정의는 시뮬 sim/order_fairness.py 와 동일(per_job_score).
실행: /raid/squad/venv/bin/python analyze_b200_heavytail.py
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
    ("m_ht_fifo", "FIFO (default)"), ("m_ht_gatefifo", "FIFO (gate)"),
    ("m_ht_sjf", "SJF"), ("m_ht_las", "LAS"), ("m_ht_kueue", "Kueue"),
    ("m_ht_easy", "EASY"), ("m_ht_themis", "Themis"),
    ("m_ht_sfqa", "SAFA (고정 α)"), ("m_ht_auto", "SAFA (제안)"),
]


def pctl(a, p):
    a = sorted(a)
    return a[min(len(a) - 1, int(len(a) * p))] if a else 0.0


def analyze(run_id):
    jp = f"{RUNS}/{run_id}/jct.csv"
    sp = f"{RUNS}/{run_id}/submit_log.csv"
    mp = f"{RUNS}/{run_id}/metrics.csv"
    if not os.path.exists(jp):
        return None
    # job -> wall 제출시각 (= 물리적 도착, submit-clamp 적용본)
    wall = {x["job"]: float(x["wall"]) for x in csv.DictReader(open(sp))}
    qs, bs, jobs = [], [], []
    for x in csv.DictReader(open(jp)):
        if not x["queue_sec"] or not x["jct_sec"]:
            continue
        q = float(x["queue_sec"]); j = float(x["jct_sec"]); s = max(j - q, 0.0)
        qs.append(q); bs.append((q + s) / max(s, BSLD_TAU))
        job = x["pod"].rsplit("-", 1)[0]
        if job in wall:
            w = wall[job]
            jobs.append((w, w + q, 0))   # arrival=wall, start=wall+queue
    sc = sorted(per_job_score(jobs)); n = len(sc)
    alloc = [float(x["alloc_pct"]) for x in csv.DictReader(open(mp))] if os.path.exists(mp) else [0.0]
    return dict(
        n=len(qs), q_p50=pctl(qs, .5), q_p90=pctl(qs, .9), q_max=max(qs) if qs else 0,
        bsld_p50=pctl(bs, .5), bsld_max=max(bs) if bs else 0,
        fair_mean=sum(sc) / n, lt50=100 * sum(1 for s in sc if s < 50) / n,
        p1=sc[n // 100], zeros=sum(1 for s in sc if s == 0),
        alloc_avg=sum(alloc) / len(alloc),
    )


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    rows = []
    print(f"{'정책':14} {'q_p50':>6} {'q_max':>6} {'BSLDp50':>7} {'fair':>6} {'lt50%':>6} {'p1':>5} {'alloc':>5}")
    for rid, lbl in RUNSET:
        s = analyze(rid)
        if not s:
            print(f"{lbl:14}  (결과 없음)"); continue
        s["run"] = rid; s["policy"] = lbl; rows.append(s)
        print(f"{lbl:14} {s['q_p50']:6.0f} {s['q_max']:6.0f} {s['bsld_p50']:7.2f} "
              f"{s['fair_mean']:6.1f} {s['lt50']:6.1f} {s['p1']:5.1f} {s['alloc_avg']:4.0f}%")
    fields = ["run", "policy", "n", "q_p50", "q_p90", "q_max", "bsld_p50", "bsld_max",
              "fair_mean", "lt50", "p1", "zeros", "alloc_avg"]
    with open(f"{OUTDIR}/b200_heavytail_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"\n→ {OUTDIR}/b200_heavytail_summary.csv ({len(rows)} run)")


if __name__ == "__main__":
    main()
