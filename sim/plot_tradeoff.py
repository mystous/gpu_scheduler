#!/usr/bin/env python3
"""Figure 3 (이용률×공정성 트레이드오프) — broken y-axis 산점도.
상단=공정 정책(FIFO·SAFA·SAFA(fixα)), 하단=Fairness 0 재정렬 베이스라인(그룹 주석).
데이터: sim/sweep_results/fixed_sweep_table.csv (256 single)."""
import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
r = {(x['gpu'], x['kind'], x['policy']): x
     for x in csv.DictReader(open(os.path.join(ROOT, "sim/sweep_results/fixed_sweep_table.csv")))}
g, k = "256", "single"


def val(pol):
    x = r[(g, k, pol)]
    return float(x['alloc_avg']), float(x['fair_p1'])


GREEDY = ["sjf", "las", "kueue", "easy", "themis", "lucid"]

fig, (axt, axb) = plt.subplots(2, 1, sharex=True, figsize=(7.2, 4.4),
                               gridspec_kw={'height_ratios': [3.2, 1], 'hspace': 0.10})

# 이상 영역(우상단) 옅은 초록
axt.axhspan(90, 103, xmin=0.50, color="#2ca02c", alpha=0.07, zorder=0)

# --- 하단: 재정렬 베이스라인(Fairness 0) 6종, 개별 라벨 없음 ---
for pol in GREEDY:
    al, p1 = val(pol)
    axb.scatter(al, p1, c="0.55", s=120, marker='o', edgecolors="0.3", linewidths=.6, zorder=3)

# --- 상단: 공정 정책 3종 ---
fa, ff = val("fifo")
sa, sf = val("sfqa-auto")
xa, xf = val("sfqa")
axt.scatter(fa, ff, c="black", s=200, marker='s', edgecolors="black", linewidths=1, zorder=6)
axt.scatter(xa, xf, c="#5aa0ef", s=150, marker='o', edgecolors="black", linewidths=.8, zorder=5)
axt.scatter(sa, sf, c="#1a4fd0", s=520, marker='*', edgecolors="black", linewidths=1.2, zorder=7)

# 점 라벨(겹치지 않게 개별 오프셋)
axt.annotate("FIFO", (fa, ff), xytext=(10, -6), textcoords="offset points",
             ha="left", va="top", fontsize=10, fontweight="bold", color="black", zorder=9)
axt.annotate("SAFA", (sa, sf), xytext=(0, 12), textcoords="offset points",
             ha="center", va="bottom", fontsize=13, fontweight="bold", color="#1a4fd0", zorder=9)
axt.annotate("SAFA (fixed α)", (xa, xf), xytext=(6, -12), textcoords="offset points",
             ha="left", va="top", fontsize=9, color="0.35", zorder=9)

# HOL recovery 화살표 (FIFO → SAFA)
axt.annotate("", xy=(sa - 0.12, sf + 0.4), xytext=(fa + 0.12, ff - 0.6),
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

# --- broken-axis 대각 축약표시(표준 marker 방식, 확실히 보임) ---
d = .6
kw = dict(marker=[(-1, -d), (1, d)], markersize=11, linestyle="none",
          color='k', mec='k', mew=1.3, clip_on=False)
axt.plot([0, 1], [0, 0], transform=axt.transAxes, **kw)
axb.plot([0, 1], [1, 1], transform=axb.transAxes, **kw)

# 코너 설명 주석(점을 가리지 않는 위치)
axt.text(0.985, 0.96, "IDEAL: fair + high util", transform=axt.transAxes,
         ha="right", va="top", color="darkgreen", fontsize=9.5, fontweight="bold")
axt.text(0.015, 0.12, "FIFO: fair, but\nwastes GPUs (HOL)", transform=axt.transAxes,
         ha="left", va="bottom", color="0.35", fontsize=8.5)
axb.text(0.5, 0.80, "reordering baselines — high util, Fairness = 0 (starving)",
         transform=axb.transAxes, ha="center", va="center",
         color="darkred", fontsize=9, fontweight="bold")

axt.grid(alpha=0.3)
axb.grid(alpha=0.3)
axb.set_xlabel("Utilization (%)   —   more HOL recovered →", fontsize=11)
fig.text(0.015, 0.55, "Fairness   —   no starvation ↑", rotation=90,
         va="center", fontsize=11)

fig.tight_layout(rect=[0.04, 0, 1, 1])
fig.savefig(os.path.join(ROOT, "paper/Pic/Fig_tradeoff.pdf"), bbox_inches="tight")
print("Fig_tradeoff: labels decluttered, greedy→reordering baselines, break marks fixed")
