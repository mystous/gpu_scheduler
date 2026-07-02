#!/usr/bin/env python3
"""Figure 3 (이용률×공정성 트레이드오프) — broken y-axis 산점도.
9개 정책마다 고유 색·마커 + 그래프 아래 범례(Figure 2와 동일 매핑).
상단=공정 정책, 하단=Fairness 0 재정렬 베이스라인.
데이터: sim/sweep_results/fixed_sweep_table.csv (256 single)."""
import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
r = {(x['gpu'], x['kind'], x['policy']): x
     for x in csv.DictReader(open(os.path.join(ROOT, "sim/sweep_results/fixed_sweep_table.csv")))}
g, k = "256", "single"

# Figure 2(cliff)와 동일한 색·마커 매핑
STY = [("fifo", "FIFO", "black", "s", 150),
       ("sjf", "SJF", "tab:orange", "v", 110),
       ("las", "LAS", "tab:green", "^", 110),
       ("kueue", "Kueue", "tab:purple", "P", 120),
       ("easy", "EASY", "tab:brown", "X", 110),
       ("themis", "Themis", "tab:pink", "d", 110),
       ("lucid", "Lucid", "tab:olive", "<", 110),
       ("sfqa", "SAFA (fixed α)", "#5aa0ef", "o", 130),
       ("sfqa-auto", "SAFA", "#1a4fd0", "*", 480)]


def val(pol):
    x = r[(g, k, pol)]
    return float(x['alloc_avg']), float(x['fair_p1'])


fig, (axt, axb) = plt.subplots(2, 1, sharex=True, figsize=(7.2, 4.6),
                               gridspec_kw={'height_ratios': [3.2, 1], 'hspace': 0.10})

# 이상 영역(우상단) 옅은 초록
axt.axhspan(90, 103, xmin=0.50, color="#2ca02c", alpha=0.07, zorder=0)

handles = []
for pol, nm, c, m, s in STY:
    al, p1 = val(pol)
    ax = axt if p1 > 50 else axb
    z = 7 if pol == "sfqa-auto" else (6 if pol == "fifo" else 4)
    ec = "black" if pol in ("fifo", "sfqa-auto", "sfqa") else "0.25"
    ax.scatter(al, p1, c=c, s=s, marker=m, edgecolors=ec, linewidths=.8, zorder=z)
    handles.append(Line2D([0], [0], marker=m, color="w", markerfacecolor=c,
                          markeredgecolor=ec, markersize=(14 if pol == "sfqa-auto" else 9),
                          label=nm, linestyle="none"))

# 핵심 두 점만 텍스트 강조(나머지는 범례로 식별)
fa, ff = val("fifo")
sa, sf = val("sfqa-auto")
axt.annotate("FIFO", (fa, ff), xytext=(10, -4), textcoords="offset points",
             ha="left", va="top", fontsize=9.5, fontweight="bold", color="black", zorder=9)
axt.annotate("SAFA", (sa, sf), xytext=(0, 13), textcoords="offset points",
             ha="center", va="bottom", fontsize=12.5, fontweight="bold", color="#1a4fd0", zorder=9)

# HOL recovery 화살표 (FIFO → SAFA)
axt.annotate("", xy=(sa - 0.12, sf + 0.5), xytext=(fa + 0.12, ff - 0.6),
             arrowprops=dict(arrowstyle="-|>", color="#1a4fd0", lw=2), zorder=8)
axt.text((fa + sa) / 2 - 0.3, 97.6, "HOL recovery\n(stays fair)", color="#1a4fd0",
         fontsize=9, fontweight="bold", ha="center", va="center", zorder=9)

# 축 범위 / 스파인
axt.set_ylim(85, 102)
axb.set_ylim(-3.5, 4)
axt.set_xlim(91, 100.3)
axt.set_yticks([90, 95, 100])
axb.set_yticks([0])
axt.spines['bottom'].set_visible(False)
axb.spines['top'].set_visible(False)
axt.tick_params(labelbottom=False, bottom=False)

# broken-axis 대각 축약표시(표준 marker 방식)
d = .6
kw = dict(marker=[(-1, -d), (1, d)], markersize=11, linestyle="none",
          color='k', mec='k', mew=1.3, clip_on=False)
axt.plot([0, 1], [0, 0], transform=axt.transAxes, **kw)
axb.plot([0, 1], [1, 1], transform=axb.transAxes, **kw)

# 코너 설명 주석
axt.text(0.985, 0.96, "IDEAL: fair + high util", transform=axt.transAxes,
         ha="right", va="top", color="darkgreen", fontsize=9.5, fontweight="bold")
axb.text(0.5, 0.82, "reordering baselines: Fairness = 0 (starving)",
         transform=axb.transAxes, ha="center", va="center",
         color="darkred", fontsize=9, fontweight="bold")

axt.grid(alpha=0.3)
axb.grid(alpha=0.3)
axb.set_xlabel("Utilization (%)   —   more HOL recovered →", fontsize=11)
fig.text(0.015, 0.58, "Fairness   —   no starvation ↑", rotation=90,
         va="center", fontsize=11)

# 범례를 x축 라벨보다 더 아래로(겹침 방지)
fig.subplots_adjust(left=0.09, right=0.98, top=0.96, bottom=0.20)
fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.54, 0.10),
           ncol=5, fontsize=8.5, framealpha=0.9, columnspacing=1.0, handletextpad=0.4)
fig.savefig(os.path.join(ROOT, "paper/Pic/Fig_tradeoff.pdf"), bbox_inches="tight")
print("Fig_tradeoff: 9정책 고유 색·마커 + 범례로 식별 가능")
