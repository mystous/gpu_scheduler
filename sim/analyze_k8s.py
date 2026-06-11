"""A2 분석 — K8S 트레이스 스윕 결과에서 q_p50·fair_p1·lt50 계산."""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from order_fairness import per_job_score   # noqa: E402

RAW = os.path.join(HERE, "sweep_results", "raw_k8s")
GPUS = [8, 16, 32]
KINDS = ["single", "hetero"]
POLS = ["fifo", "sjf", "las", "kueue", "easy", "themis", "fgd", "sfqa", "sfqa-auto", "lucid"]


def pctl(a, x):
    a = sorted(a)
    return a[min(len(a) - 1, int(len(a) * x))] if a else 0


def main():
    out = []
    for g in GPUS:
        for k in KINDS:
            d = f"cmp{g}_{k}"
            for pol in POLS:
                f = os.path.join(RAW, d, f"{pol}_jobs.csv")
                if not os.path.exists(f):
                    continue
                rows = list(csv.DictReader(open(f)))
                qs = [float(r["queue_sec"]) for r in rows]
                jb = [(float(r["arrival_s"]), float(r["start_s"]), 0) for r in rows]
                sc = sorted(per_job_score(jb))
                n = len(sc)
                fp1 = sc[int(n * .01)] if n else 0
                lt50 = 100.0 * sum(1 for x in sc if x < 50) / n if n else 0
                out.append((g, k, pol, round(pctl(qs, .5)), round(max(qs)),
                            round(fp1, 1), round(lt50, 2), n))
    of = os.path.join(HERE, "sweep_results", "k8s", "k8s_table.csv")
    with open(of, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gpu", "kind", "policy", "q_p50", "q_max", "fair_p1", "lt50_pct", "n"])
        w.writerows(out)
    print(f"→ {of}\n")
    # 콘솔 표
    for g in GPUS:
        for k in KINDS:
            print(f"=== {g} GPU {k} ===")
            print(f"{'policy':<11}{'q_p50':>10}{'fair_p1':>9}{'lt50%':>8}")
            for row in out:
                if row[0] == g and row[1] == k:
                    print(f"{row[2]:<11}{row[3]:>10}{row[5]:>9}{row[6]:>8}")
            print()


if __name__ == "__main__":
    main()
