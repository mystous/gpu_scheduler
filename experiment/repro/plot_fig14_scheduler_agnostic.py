"""Fig_14 (fig:14) 벡터 재생성 — SFQA의 스케줄러 비종속성.

Compact / Round Robin / MCTS 각 스케줄러에 대해 SFQA 적용 전(Normal)·후(Optimized)의
GPU 할당률(Allocation Rate, .result 열0) 분포를 밀도로 비교한다. 세 스케줄러 모두에서
Optimized 분포가 더 높은 할당률 쪽으로 이동함을 보여 SFQA가 코어 스케줄러와 무관하게
효율을 끌어올림을 입증한다. 기존 PNG(allocation_aggregation 계열)의 벡터 대체본.

데이터: C++ 시뮬레이터를 증강 작업 로그(3,001잡)·14서버(84 가속기)·α=0.72로 재실행해
생성한 .result 6개(스케줄러 3 × {Normal=starvation(false), Optimized=starvation(true)}).
재현 절차는 본 디렉토리 README 주석 / paper 메모리 참조.

사용: python3 analysis_results/plot_scheduler_agnostic.py --results <dir> [--out <dir>]
  <dir>: .result 6개가 있는 디렉토리(기본 /tmp/fig14_aug)
"""
import argparse
import glob
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde

plt.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "font.size": 12, "axes.titlesize": 13, "axes.labelsize": 12,
    "xtick.labelsize": 10.5, "ytick.labelsize": 10.5, "legend.fontsize": 10,
    "axes.linewidth": 0.8, "figure.dpi": 150, "savefig.bbox": "tight",
})

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GRAY, BLUE = "#7a7a7a", "tab:blue"
KDE_N = 40000
# 파일 prefix(스케줄러 내부명) → 표시 이름
SCHED = [("compact", "(A) Compact"),
         ("round_robin", "(B) Round Robin"),
         ("mcts", "(C) MCTS")]


def _find(results_dir, prefix, starvation):
    """prefix 스케줄러 + starvation(true/false) 매칭 파일 1개 반환.
    .result(원본) 또는 .alloc.csv.gz(할당률 열만 추출본) 둘 다 지원."""
    for ext in ("*.alloc.csv.gz", "*.result"):
        pat = os.path.join(results_dir, f"{prefix}_*starvation({starvation}){ext}")
        hits = glob.glob(pat)
        if hits:
            return hits[0]
    return None


def _alloc(path):
    """할당률(Allocation Rate, 열0) 로드. .result 또는 .alloc.csv.gz 모두 가능."""
    s = pd.read_csv(path, usecols=[0]).iloc[:, 0].to_numpy()
    return s[np.isfinite(s)]


def _density(ax, data, color, label):
    if data is None or len(data) == 0:
        return
    d = data
    if len(d) > KDE_N:
        d = d[np.linspace(0, len(d) - 1, KDE_N).astype(int)]
    xs = np.linspace(0, 100, 300)
    if d.std() < 1e-6:
        ax.axvline(d.mean(), color=color, lw=1.8, label=label)
    else:
        ax.plot(xs, gaussian_kde(d)(xs), color=color, lw=1.8, label=label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="/tmp/fig14_cols")
    ap.add_argument("--out", default=os.path.join(ROOT, "results"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4), sharey=True)
    for ax, (prefix, title) in zip(axes, SCHED):
        nrm = _find(args.results, prefix, "false")
        opt = _find(args.results, prefix, "true")
        if nrm is None or opt is None:
            print(f"[warn] {prefix}: normal={nrm} optimal={opt}")
        _density(ax, _alloc(nrm) if nrm else None, GRAY, "Normal")
        _density(ax, _alloc(opt) if opt else None, BLUE, "Optimized")
        ax.set_xlim(0, 100)
        ax.set_xlabel("Allocation Rate (%)")
        ax.set_title(title, fontsize=12)
        ax.grid(alpha=.3)
        ax.legend()
    axes[0].set_ylabel("Density")
    fig.suptitle("Scheduler-agnostic effect of SFQA (C++ simulator, augmented log, $\\alpha$=0.72): "
                 "Optimized shifts allocation higher for every core scheduler", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(args.out, "report_scheduler_agnostic")
    fig.savefig(out + ".pdf")
    fig.savefig(out + ".png", dpi=200)
    plt.close(fig)
    print(f"saved {out}.pdf / .png")


if __name__ == "__main__":
    main()
