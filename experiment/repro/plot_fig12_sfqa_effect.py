"""Fig_12 (fig:improve) 벡터 재생성 — SFQA 적용 전후(Normal vs Optimized) 비교.

C++ 시뮬레이터의 per-timestep 결과(.result, 열0=Allocation Rate, 열1=Utilization Rate)에서
  (A) 실제 작업 로그 시간축 추이(Normal vs Optimized, 할당률·사용률)
  (B) 증강 작업 로그 시간축 추이
  (C) 실제 로그 할당률·사용률 분포(밀도)
  (D) 증강 로그 할당률·사용률 분포
를 그린다. 기존 PNG(analysis_results/actual_job_vs_actual_job_optimal.png)의 벡터 대체본.

데이터: analysis_results/actual_job_optimal.zip 내 4개 .result
  actual_job.result(Normal·실제) / actual_job_optimal.result(Optimized·실제)
  aug.result(Normal·증강)       / aug_optimal.result(Optimized·증강)

사용: python3 analysis_results/plot_sfqa_effect.py [--out <dir>]  (기본 출력: paper/Pic 옆 results/)
"""
import argparse
import os
import zipfile

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
ZIP = os.path.join(HERE, "actual_job_optimal.zip")
TMP = "/tmp/squash_result"
GRAY, BLUE = "#7a7a7a", "tab:blue"
TS_N = 3000      # 시계열 다운샘플 점수(벡터 경량화)
KDE_N = 40000    # KDE 추정용 최대 표본


def _load(name):
    """zip에서 .result 추출 후 열0(Allocation)·열1(Utilization)만 로드."""
    path = os.path.join(TMP, name)
    if not os.path.exists(path):
        os.makedirs(TMP, exist_ok=True)
        with zipfile.ZipFile(ZIP) as z:
            z.extract(name, TMP)
    df = pd.read_csv(path, usecols=[0, 1])
    return df.iloc[:, 0].to_numpy(), df.iloc[:, 1].to_numpy()  # alloc, util


def _ds(a, n=TS_N):
    """등간격 다운샘플(시계열 플롯용)."""
    if len(a) <= n:
        return np.arange(len(a)), a
    idx = np.linspace(0, len(a) - 1, n).astype(int)
    return idx, a[idx]


def _timeseries(ax, normal, optimal, title):
    (n_al, n_ut), (o_al, o_ut) = normal, optimal
    for series, c, ls, lab in [(n_al, GRAY, "-", "Normal – Allocation"),
                               (n_ut, GRAY, ":", "Normal – Utilization"),
                               (o_al, BLUE, "-", "SFQA – Allocation"),
                               (o_ut, BLUE, ":", "SFQA – Utilization")]:
        x, y = _ds(series)
        ax.plot(x, y, ls, color=c, lw=1.0, alpha=0.9, label=lab)
    ax.set_xlim(0, max(len(n_al), len(o_al)))
    ax.set_ylim(0, 100)
    ax.set_ylabel("Rate (%)")
    ax.set_xlabel("emulation step")
    ax.set_title(title, fontsize=12)
    ax.grid(alpha=.3)


def _density(ax, normal, optimal, title):
    xs = np.linspace(0, 100, 300)
    for data, c, lab in [(normal, GRAY, "Normal"), (optimal, BLUE, "Optimized")]:
        d = data[np.isfinite(data)]
        if len(d) > KDE_N:
            d = d[np.linspace(0, len(d) - 1, KDE_N).astype(int)]
        # 분산 0(상수) 방어
        if d.std() < 1e-6:
            ax.axvline(d.mean(), color=c, lw=1.8, label=lab)
            continue
        kde = gaussian_kde(d)
        ax.plot(xs, kde(xs), color=c, lw=1.8, label=lab)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Rate (%)")
    ax.set_ylabel("Density")
    ax.set_title(title, fontsize=12)
    ax.grid(alpha=.3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "results"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    print("loading .result (열 0,1만)...", flush=True)
    a_n = _load("actual_job.result")
    a_o = _load("actual_job_optimal.result")
    g_n = _load("aug.result")
    g_o = _load("aug_optimal.result")

    fig, axd = plt.subplot_mosaic(
        [["A", "A"], ["B", "B"], ["C1", "C2"], ["D1", "D2"]],
        figsize=(12, 13.5))

    _timeseries(axd["A"], a_n, a_o,
                "(A) Actual job log: Normal vs Optimized over time")
    _timeseries(axd["B"], g_n, g_o,
                "(B) Augmented job log: Normal vs Optimized over time")
    _density(axd["C1"], a_n[0], a_o[0], "(C) Actual — Allocation Rate")
    _density(axd["C2"], a_n[1], a_o[1], "(C) Actual — Utilization Rate")
    _density(axd["D1"], g_n[0], g_o[0], "(D) Augmented — Allocation Rate")
    _density(axd["D2"], g_n[1], g_o[1], "(D) Augmented — Utilization Rate")
    for k in ("C1", "C2", "D1", "D2"):
        axd[k].legend()

    # 시계열 4선 공용 범례 — 최상단(제목·서브플롯과 비겹침)
    h, lab = axd["A"].get_legend_handles_labels()
    fig.legend(h, lab, ncol=4, fontsize=10, loc="upper center",
               bbox_to_anchor=(0.5, 0.975), frameon=False)
    fig.suptitle("SFQA effect (C++ simulator): allocation/utilization shift to higher use under SFQA",
                 fontsize=14, y=1.0)
    fig.tight_layout(rect=[0, 0, 1, 0.955])
    out = os.path.join(args.out, "report_sfqa_effect")
    fig.savefig(out + ".pdf")
    fig.savefig(out + ".png", dpi=200)
    plt.close(fig)
    print(f"saved {out}.pdf / .png", flush=True)


if __name__ == "__main__":
    main()
