"""Alibaba 스윕 분석 — analyze_sweep.py 로직 재사용, alibaba 디렉토리 대상.

출력: sim/sweep_results/alibaba/sweep_table.csv
  컬럼: gpu,kind,policy,q_p50,q_max,alloc_avg,fair_mean,fair_p1,lt50_pct,makespan_days
부하: 256=3.69x(과부하)/512=1.84x(중부하)/1024=0.92x(저부하), 동시수요≈943 GPU.
순서 불공정(추월) 지표 = lt50_pct(추월당해 점수<50인 잡 비율), fair_p1(최악1% 점수).
대기 지표 = q_p50.  (이 둘은 서로 다른 축 — FIFO는 추월0이나 q_p50 최대.)
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from order_fairness import per_job_score  # noqa: E402

ALI = os.path.join(HERE, "sweep_results", "alibaba")
RAW = os.path.join(HERE, "sweep_results", "raw_alibaba")
GPUS = [256, 512, 1024]
KINDS = ["single", "hetero"]
POLS = ["fifo", "sjf", "las", "kueue", "easy", "themis", "fgd", "sfqa", "sfqa-auto", "lucid"]
LOAD = {256: "3.69x", 512: "1.84x", 1024: "0.92x"}
BSLD_TAU = 10.0


def pctl(a, x):
    a = sorted(a)
    return a[min(len(a) - 1, int(len(a) * x))] if a else 0


def load_jobs(d, pol):
    f = f"{RAW}/{d}/{pol}_jobs.csv"
    if not os.path.exists(f):
        return None
    rows = list(csv.DictReader(open(f)))
    return rows if len(rows) >= 100 else None


def fairness(rows):
    jb = [(float(r["arrival_s"]), float(r["start_s"]), 0) for r in rows]
    sc = sorted(per_job_score(jb))
    n = len(sc)
    return sum(sc) / n, sc[int(n * .01)], 100 * sum(1 for x in sc if x < 50) / n


def bsld_stats(rows):
    b = [(float(r["queue_sec"]) + float(r["service_sec"])) / max(float(r["service_sec"]), BSLD_TAU)
         for r in rows]
    return pctl(b, .5), pctl(b, .99), max(b)


def makespan_days(rows):
    ends = [float(r["start_s"]) + float(r["service_sec"]) for r in rows]
    arr = [float(r["arrival_s"]) for r in rows]
    return (max(ends) - min(arr)) / 86400.0


def main():
    data = {}
    for g in GPUS:
        for k in KINDS:
            d = f"cmp{g}_{k}"
            smap = {}
            sf = f"{ALI}/{d}/summary.csv"
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
                    af = f"{RAW}/{d}/{pol}_alloc.csv"
                    if os.path.exists(af):
                        v = [float(r["alloc_pct"]) for r in csv.DictReader(open(af))]
                        rec["alloc"] = sum(v) / len(v) if v else 0
                    else:
                        rec["alloc"] = 0
                else:
                    continue
                if rows:
                    rec["fmean"], rec["fp1"], rec["flo"] = fairness(rows)
                    rec["b50"], rec["b99"], rec["bmax"] = bsld_stats(rows)
                    rec["mk"] = makespan_days(rows)
                data[(g, k, pol)] = rec
            print(f"  {d}: {[p for p in POLS if (g,k,p) in data]}", flush=True)

    out = f"{ALI}/sweep_table.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gpu", "load", "kind", "policy", "q_p50", "q_max", "alloc_avg",
                    "fair_mean", "fair_p1", "lt50_pct", "bsld_p50", "makespan_days"])
        for g in GPUS:
            for k in KINDS:
                for pol in POLS:
                    rec = data.get((g, k, pol))
                    if rec:
                        w.writerow([g, LOAD[g], k, pol, round(rec.get("q_p50", 0)),
                                    round(rec.get("q_max", 0)), round(rec.get("alloc", 0), 1),
                                    round(rec.get("fmean", 0), 1), round(rec.get("fp1", 0), 1),
                                    round(rec.get("flo", 0), 2), round(rec.get("b50", 0), 2),
                                    round(rec.get("mk", 0), 2)])
    print(f"→ {out}")

    # 핵심 콘솔 표: 256/512 × single/hetero
    for g in [256, 512]:
        for k in KINDS:
            print(f"\n=== {g} GPU ({LOAD[g]}) / {k} ===")
            print(f"{'policy':<11}{'q_p50':>11}{'q_max':>12}{'alloc%':>8}"
                  f"{'fair_p1':>9}{'lt50%':>8}{'bsld_p50':>10}")
            for pol in POLS:
                rec = data.get((g, k, pol))
                if rec:
                    print(f"{pol:<11}{rec.get('q_p50',0):>11.0f}{rec.get('q_max',0):>12.0f}"
                          f"{rec.get('alloc',0):>8.1f}{rec.get('fp1',0):>9.1f}"
                          f"{rec.get('flo',0):>8.1f}{rec.get('b50',0):>10.2f}")
    print("\nDONE")


if __name__ == "__main__":
    main()
