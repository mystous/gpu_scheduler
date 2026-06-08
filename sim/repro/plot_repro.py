"""옛 데이터×새 시뮬레이터 결과 그림 — 평균이 아니라 '추세·분포'를 본다.

Fig_12(SFQA 효과): most-allocated 배치에서 Normal(FIFO) vs SFQA(α=0.72)의
  (A) 할당률 시간 추세, (B) 할당률 분포(밀도).
Fig_14(배치 비종속): most-allocated·compact 두 배치에서 Normal vs SFQA 할당률 분포.

데이터: sim/repro/data/<placement>_<mode>_alloc.csv  (run_repro.py 산출)
출력: results/report_repro_fig12.pdf, results/report_repro_fig14.pdf
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde

plt.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "font.size": 12, "axes.titlesize": 13, "axes.labelsize": 12,
    "xtick.labelsize": 10.5, "ytick.labelsize": 10.5, "legend.fontsize": 10,
    "axes.linewidth": 0.8, "figure.dpi": 150, "savefig.bbox": "tight",
})

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(ROOT, "results")
GRAY, BLUE = "#7a7a7a", "tab:blue"


def load(name):
    t, rate = [], []
    with open(os.path.join(DATA, name + "_alloc.csv")) as f:
        for r in csv.DictReader(f):
            t.append(float(r["t_s"]) / 86400.0)      # 일
            rate.append(float(r["rate_pct"]))
    return np.array(t), np.array(rate)


def kde(ax, rate, color, label):
    d = rate[np.isfinite(rate)]
    xs = np.linspace(0, 100, 300)
    if d.std() < 1e-6:
        ax.axvline(d.mean(), color=color, lw=1.8, label=label)
    else:
        ax.plot(xs, gaussian_kde(d)(xs), color=color, lw=1.8, label=label)


def fig12():
    tn, rn = load("mostalloc_normal")
    ts, rs = load("mostalloc_sfqa")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.4))
    # (A) 시간 추세 (계단 — allocation 변화점)
    a1.step(tn, rn, where="post", color=GRAY, lw=1.0, alpha=0.9, label="Normal (FIFO)")
    a1.step(ts, rs, where="post", color=BLUE, lw=1.2, alpha=0.9, label="SFQA ($\\alpha$=0.72)")
    a1.set_xlabel("time (days)"); a1.set_ylabel("GPU allocation (%)")
    a1.set_ylim(0, 100); a1.set_title("(A) Allocation over time"); a1.grid(alpha=.3); a1.legend()
    # (B) 분포
    kde(a2, rn, GRAY, "Normal (FIFO)")
    kde(a2, rs, BLUE, "SFQA ($\\alpha$=0.72)")
    a2.set_xlabel("GPU allocation (%)"); a2.set_ylabel("Density")
    a2.set_xlim(0, 100); a2.set_title("(B) Allocation distribution"); a2.grid(alpha=.3); a2.legend()
    fig.suptitle("SFQA effect on the old augmented log, re-run on the new simulator "
                 "(most-allocated, 84 GPU)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(OUT, "report_repro_fig12.pdf"))
    fig.savefig(os.path.join(OUT, "report_repro_fig12.png"), dpi=200)
    plt.close(fig)
    print("saved report_repro_fig12")


def fig14():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    for ax, (place, title) in zip(axes, [("mostalloc", "(A) most-allocated"),
                                         ("compact", "(B) compact")]):
        _, rn = load(f"{place}_normal")
        _, rs = load(f"{place}_sfqa")
        kde(ax, rn, GRAY, "Normal (FIFO)")
        kde(ax, rs, BLUE, "SFQA ($\\alpha$=0.72)")
        ax.set_xlim(0, 100); ax.set_xlabel("GPU allocation (%)")
        ax.set_title(title); ax.grid(alpha=.3); ax.legend()
    axes[0].set_ylabel("Density")
    fig.suptitle("Placement-agnostic SFQA effect, old log on the new simulator (84 GPU)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(OUT, "report_repro_fig14.pdf"))
    fig.savefig(os.path.join(OUT, "report_repro_fig14.png"), dpi=200)
    plt.close(fig)
    print("saved report_repro_fig14")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig12()
    fig14()
