"""순서 공정성(0~100) 분포 시각화 — run_all.py 가 덤프한 <policy>_jobs.csv 사용.

정의(order_fairness.per_job_score): 잡별 100·(1 − 추월당한수/나보다_늦게도착한수).
  100 = 큐(도착)순서대로 처리됨(아무도 안 추월), 0 = 늦게 온 잡들에 전부 추월당함.
분포로 본다(집계 단일값 아님, 누적 CDF 아님): 잡별 점수의 히스토그램.

사용:
  plot_orderfair.py <pj_dir> [--out <png>] [--bins 25] [--title ...]
"""
import argparse, csv, glob, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, "/home/mystous/gpu_scheduler/sim")
from order_fairness import per_job_score

ORDER = ["fifo", "sjf", "las", "kueue", "easy", "themis", "sfqa", "sfqa-auto", "lucid", "sia"]


def load_jobs(path):
    """(arrival, start, start) 리스트. per_job_score는 start만 사용(finish 무시)."""
    jobs = []
    with open(path) as f:
        for r in csv.DictReader(f):
            a = float(r["arrival_s"]); s = float(r["start_s"])
            jobs.append((a, s, s))
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--out", default="")
    ap.add_argument("--bins", type=int, default=25)
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.dir, "*_jobs.csv")))
    if not files:
        raise SystemExit(f"no *_jobs.csv in {a.dir}")
    scores = {}
    for fp in files:
        name = os.path.basename(fp)[:-len("_jobs.csv")]
        jb = load_jobs(fp)
        scores[name] = per_job_score(jb)
    pols = [p for p in ORDER if p in scores] + [p for p in scores if p not in ORDER]

    def stat(s):
        ss = sorted(s); n = len(ss)
        p = lambda x: ss[min(n - 1, int(n * x))]
        return sum(s) / n, p(.5), p(.01), p(.1)   # mean, median, p1, p10

    print(f"{'정책':12} {'mean':>6} {'median':>7} {'p1':>6} {'p10':>6} {'<50점%':>7}")
    print("-" * 50)
    for p in pols:
        m, med, p1, p10 = stat(scores[p])
        lo = 100 * sum(1 for x in scores[p] if x < 50) / len(scores[p])
        print(f"{p:12} {m:>6.1f} {med:>7.1f} {p1:>6.1f} {p10:>6.1f} {lo:>6.1f}%")

    # small-multiples 히스토그램(분포, 누적 아님)
    n = len(pols); cols = 2; rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(13, 2.3 * rows), sharex=True)
    axes = axes.flatten()
    bins = a.bins
    for i, p in enumerate(pols):
        ax = axes[i]
        m, med, p1, p10 = stat(scores[p])
        ax.hist(scores[p], bins=bins, range=(0, 100), color="tab:blue", alpha=0.8)
        ax.axvline(med, ls="--", lw=1, color="tab:red")
        ax.set_title(f"{p}  (mean {m:.0f}, median {med:.0f}, p1 {p1:.0f})", fontsize=9)
        ax.grid(alpha=0.3)
    for j in range(n, len(axes)):
        axes[j].axis("off")
    fig.supxlabel("order-fairness score (100=FIFO order, 0=fully overtaken)")
    fig.supylabel("number of jobs")
    fig.suptitle(a.title or f"Order-fairness distribution — {os.path.basename(a.dir.rstrip('/'))}", fontsize=12)
    out = a.out or os.path.join(a.dir, "orderfair_dist.png")
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)
    print(f"→ {out}")


if __name__ == "__main__":
    main()
