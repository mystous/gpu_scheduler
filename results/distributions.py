"""분포 분석 — aggregation(p50/p90/max)이 아니라 전체 CDF·백분위·makespan.

산출: queue/BSLD CDF 그림(PNG) + 백분위 표 + run별 wall time(makespan).
makespan = max(submit_wall + jct) − min(submit_wall)  (submit_log × jct join)
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUNS = "/raid/squad/runs"
OUT = "/raid/squad/analysis"

GROUPS = {
    "k3000": {  # 본선: Philly 1000, duration cap[6,8]
        "default-FIFO": "p_base", "SJF": "p_sjf", "gate-FIFO": "p_fifo",
        "Kueue": "p_kueue", "SFQA": "p_sfqa", "auto t10": "p_sfqa_auto",
        "auto t1": "p_auto_t1", "EASY": "p_easy",
    },
    "s360": {  # 충실 duration: JCT<=2h, 윈도우, S=360, cap 없음
        "Kueue": "f360_kueue", "auto t10": "f360_auto", "EASY": "f360_easy",
        "EASY f=1": "f360_easyf1", "EASY f=3": "f360_easyf3",
    },
}


def load(run):
    sub = {}
    with open(f"{RUNS}/{run}/submit_log.csv") as f:
        for r in csv.DictReader(f):
            sub[r["job"]] = float(r["wall"])
    qs, bs, ends = [], [], []
    with open(f"{RUNS}/{run}/jct.csv") as f:
        for r in csv.DictReader(f):
            if not r.get("jct_sec") or not r.get("queue_sec"):
                continue
            job = "-".join(r["pod"].split("-")[:-1])
            jct, q = float(r["jct_sec"]), float(r["queue_sec"])
            qs.append(q)
            bs.append(jct / max(jct - q, 10.0))
            if job in sub:
                ends.append(sub[job] + jct)
    qs.sort(); bs.sort()
    mk = (max(ends) - 0.0) if ends else 0  # t0=첫 제출(wall 기준 0 근방)
    return qs, bs, mk


def pjoin(a):
    n = len(a)
    pick = lambda p: a[min(n - 1, int(n * p))]
    return [pick(.1), pick(.25), pick(.5), pick(.75), pick(.9), pick(.95), pick(.99), a[-1]]


def cdf_plot(ax, data, label):
    n = len(data)
    ys = [i / n for i in range(1, n + 1)]
    ax.plot(data, ys, label=label, linewidth=1.6)


def main():
    for gname, runs in GROUPS.items():
        fig, axes = plt.subplots(1, 2, figsize=(13, 5))
        print(f"\n## {gname}")
        print(f"{'정책':12} {'p10':>6} {'p25':>6} {'p50':>6} {'p75':>6} {'p90':>6} {'p95':>6} {'p99':>6} {'max':>7} | {'BSLDp99':>7} {'BSLDmax':>7} | {'makespan':>9}")
        for label, run in runs.items():
            if not os.path.exists(f"{RUNS}/{run}/jct.csv"):
                continue
            qs, bs, mk = load(run)
            qp = pjoin(qs); bp = pjoin(bs)
            print(f"{label:12} {qp[0]:>6.0f} {qp[1]:>6.0f} {qp[2]:>6.0f} {qp[3]:>6.0f} {qp[4]:>6.0f} {qp[5]:>6.0f} {qp[6]:>6.0f} {qp[7]:>7.0f} | {bp[6]:>7.1f} {bp[7]:>7.1f} | {mk/60:>7.1f}분")
            cdf_plot(axes[0], qs, label)
            cdf_plot(axes[1], bs, label)
        axes[0].set_xlabel("queueing delay (s)"); axes[0].set_ylabel("CDF")
        axes[0].set_xscale("symlog"); axes[0].grid(alpha=.3); axes[0].legend(fontsize=8)
        axes[0].set_title(f"{gname}: queueing delay CDF")
        axes[1].set_xlabel("BSLD"); axes[1].set_xscale("log")
        axes[1].grid(alpha=.3); axes[1].legend(fontsize=8)
        axes[1].set_title(f"{gname}: bounded slowdown CDF")
        fig.tight_layout()
        fig.savefig(f"{OUT}/cdf_{gname}.png", dpi=130)
        print(f"→ {OUT}/cdf_{gname}.png")


if __name__ == "__main__":
    main()
