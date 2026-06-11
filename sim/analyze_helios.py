"""Helios(Venus) 부하 스윕 분석 — analyze_sweep.py의 지표 정의를 그대로 쓰되
디렉토리/규모만 Helios로 교체. 출력: sweep_results/helios/sweep_table.csv.

지표(analyze_sweep.py와 동일):
  fair_p1  = per_job_score(arrival,start)의 1퍼센타일(낮을수록 불공정; 100=완전 공정)
  fair_mean= 평균, lt50_pct = score<50 비율
  q_p50/q_max = summary.csv의 큐잉 지연
  makespan_days = (max(start+service) - min(arrival))/86400
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from order_fairness import per_job_score   # noqa: E402

OUT = os.path.join(HERE, "sweep_results", "helios")
A = os.path.join(HERE, "sweep_results", "raw_helios")   # per-job/alloc 덤프
SUM = OUT                                                # summary.csv
GPUS = [80, 192, 448]                                    # 3.17x / 1.32x / 0.57x (seed=42 50% 서브샘플)
KINDS = ["single", "hetero"]
POLS = ["fifo", "sjf", "las", "kueue", "easy", "themis", "fgd", "sfqa", "sfqa-auto", "lucid"]


def dname(g, k):
    return f"cmp{g}_{k}"


def pctl(a, x):
    a = sorted(a)
    return a[min(len(a) - 1, int(len(a) * x))] if a else 0


def load_jobs(d, pol):
    f = f"{A}/{d}/{pol}_jobs.csv"
    if not os.path.exists(f):
        return None
    rows = list(csv.DictReader(open(f)))
    if len(rows) < 100:
        return None
    return rows


def fairness_p1(rows):
    jb = [(float(r["arrival_s"]), float(r["start_s"]), 0) for r in rows]
    sc = sorted(per_job_score(jb))
    n = len(sc)
    return sum(sc) / n, sc[int(n * .01)], 100 * sum(1 for x in sc if x < 50) / n


def makespan_days(rows):
    ends = [float(r["start_s"]) + float(r["service_sec"]) for r in rows]
    arr = [float(r["arrival_s"]) for r in rows]
    return (max(ends) - min(arr)) / 86400.0


def alloc_avg(d, pol):
    f = f"{A}/{d}/{pol}_alloc.csv"
    if not os.path.exists(f):
        return None
    v = [float(r["alloc_pct"]) for r in csv.DictReader(open(f))]
    return sum(v) / len(v) if v else 0


data = {}
for g in GPUS:
    for k in KINDS:
        d = dname(g, k)
        smap = {}
        sf = f"{SUM}/{d}/summary.csv"
        if os.path.exists(sf):
            for r in csv.DictReader(open(sf)):
                smap[r["policy"]] = r
        for pol in POLS:
            rows = load_jobs(d, pol)
            rec = {}
            if pol in smap and smap[pol].get("q_p50"):
                rec["q_p50"] = float(smap[pol]["q_p50"])
                rec["q_max"] = float(smap[pol]["q_max"])
                rec["alloc"] = float(smap[pol]["alloc_avg"])
            elif rows:
                qs = [float(r["queue_sec"]) for r in rows]
                rec["q_p50"] = pctl(qs, .5)
                rec["q_max"] = max(qs)
                aa = alloc_avg(d, pol)
                rec["alloc"] = aa if aa is not None else 0
            else:
                continue
            if rows:
                rec["fmean"], rec["fp1"], rec["flo"] = fairness_p1(rows)
                rec["makespan_days"] = makespan_days(rows)
            data[(g, k, pol)] = rec
        print(f"  {d}: {[p for p in POLS if (g,k,p) in data]}", flush=True)

os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/sweep_table.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["gpu", "kind", "policy", "q_p50", "q_max", "alloc_avg",
                "fair_mean", "fair_p1", "lt50_pct", "makespan_days"])
    for g in GPUS:
        for k in KINDS:
            for pol in POLS:
                rec = data.get((g, k, pol))
                if rec:
                    w.writerow([g, k, pol, round(rec.get("q_p50", 0)), round(rec.get("q_max", 0)),
                                round(rec.get("alloc", 0), 1), round(rec.get("fmean", 0), 1),
                                round(rec.get("fp1", 0), 1), round(rec.get("flo", 0), 2),
                                round(rec.get("makespan_days", 0), 2)])
print(f"→ {OUT}/sweep_table.csv")

# 핵심 질문용 콘솔 표: 과부하(160)/중부하(384)/저부하(896) × hetero 의 fair_p1·q_p50
for g, label in [(80, "OVERLOAD 3.17x"), (192, "MID 1.32x"), (448, "LOW 0.57x")]:
    for k in KINDS:
        print(f"\n=== {g} GPU / {k}  [{label}] ===")
        print(f"{'policy':<11}{'fair_p1':>9}{'fair_mean':>11}{'lt50%':>8}{'q_p50':>12}")
        for pol in POLS:
            rec = data.get((g, k, pol))
            if rec and "fp1" in rec:
                print(f"{pol:<11}{rec['fp1']:>9.1f}{rec['fmean']:>11.1f}{rec['flo']:>8.1f}{rec['q_p50']:>12.0f}")
print("DONE")
