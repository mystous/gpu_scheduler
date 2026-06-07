"""검증 보고용 그래프 3종 생성기.

  ① report_pareto_k3000.png — κ3000 본선 8정책 (p50, max) Pareto 트레이드오프
  ② report_c48.png          — Philly-2K-C48 임계부하 3정책 백분위 비교
  ③ report_scale.png        — 시뮬 111k 부하 스윕: auto의 median 단축 + 공정성 유지

데이터 출처:
  ①② 실측 — results/SUMMARY.md §1(κ3000), §1.6(C48). 수치 갱신 시 아래 상수 동기화.
  ③   시뮬 — sim/sweep_results/sweep_table.csv 에서 직접 로드.

사용: python3 results/report_plots.py [--out <dir>]   (기본 출력: results/)
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP_TABLE = os.path.join(ROOT, "sim", "sweep_results", "sweep_table.csv")

# ── ① κ3000 본선 (SUMMARY.md §1) ─────────────────────────────────────────
K3000 = {  # policy: (queueing p50, max) [s]
    "default-FIFO": (17, 2450),
    "SJF": (33, 2265),
    "gate-FIFO": (189, 924),
    "Kueue": (195, 869),
    "auto t=1": (210, 937),
    "SFQA fixed": (243, 782),
    "auto t=10": (290, 768),
    "EASY*": (419, 691),
}
K3000_FRONTIER = ["default-FIFO", "Kueue", "auto t=1", "auto t=10", "EASY*"]

# ── ② Philly-2K-C48 임계부하 (SUMMARY.md §1.6) ──────────────────────────
C48_POLICIES = ["Kueue", "EASY*", "sfqa-auto"]
C48_COLORS = {"Kueue": "tab:green", "EASY*": "tab:blue", "sfqa-auto": "tab:red"}
C48 = {  # percentile: [Kueue, EASY, sfqa-auto] [s]
    "p50": [1838, 1201, 340],
    "p90": [4943, 2657, 1167],
    "p99": [5130, 3068, 3490],
    "max": [5963, 3309, 4874],
}


def plot_pareto(out):
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for name, (x, y) in K3000.items():
        squad = "auto" in name or "SFQA" in name
        on_f = name in K3000_FRONTIER
        c = "tab:red" if squad else ("tab:blue" if on_f else "gray")
        ax.scatter(x, y, s=110 if squad else 70, c=c, zorder=3,
                   edgecolors="k", linewidths=.5)
        ax.annotate(name, (x, y), textcoords="offset points", xytext=(8, 6),
                    fontsize=9)
    fx = sorted(K3000[f] for f in K3000_FRONTIER)
    ax.plot([p[0] for p in fx], [p[1] for p in fx], "--", c="tab:blue",
            alpha=.5, zorder=1, label="Pareto frontier")
    ax.set_xlabel("median queueing delay p50 (s)  — efficiency")
    ax.set_ylabel("worst-case max (s) — starvation")
    ax.set_title("K8s measured, Philly-1K (peak 3.6x): protection costs median\n"
                 "(red = SQUAD family, * = EASY assumes perfect duration estimates)")
    ax.grid(alpha=.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out, "report_pareto_k3000.png"), dpi=130)
    plt.close(fig)


def plot_c48(out):
    keys = list(C48)
    x = np.arange(len(keys))
    w = 0.26
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for i, p in enumerate(C48_POLICIES):
        vals = [C48[k][i] for k in keys]
        ax.bar(x + (i - 1) * w, vals, w, label=p, color=C48_COLORS[p])
        for j, v in enumerate(vals):
            ax.text(j + (i - 1) * w, v + 60, str(v), ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(keys)
    ax.set_ylabel("queueing delay (s)")
    ax.set_title("K8s measured, Philly-2K-C48 critical load (avg 1.01x, peak 8.9x):\n"
                 "sfqa-auto dominates ~97% of distribution, tails cross at p97")
    ax.grid(alpha=.3, axis="y")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out, "report_c48.png"), dpi=130)
    plt.close(fig)


def load_sweep():
    """sweep_table.csv → {(gpu, kind, policy): row dict}"""
    rows = {}
    with open(SWEEP_TABLE) as f:
        for r in csv.DictReader(f):
            rows[(r["gpu"], r["kind"], r["policy"])] = r
    return rows


def plot_scale(out):
    rows = load_sweep()
    # 1024 single은 전 정책 q_p50≈2s(저부하, 스케줄러 무의미)라 제외
    configs = [("256", "single", "3.6x"), ("256", "hetero", "3.6x"),
               ("512", "single", "1.8x"), ("512", "hetero", "1.8x"),
               ("1024", "hetero", "0.9x")]
    labels = [f"{g}\n{k}\n({ld})" for g, k, ld in configs]

    def q50(g, k, p):
        return float(rows[(g, k, p)]["q_p50"])

    def p1(g, k, p):
        return float(rows[(g, k, p)]["fair_p1"])

    red_auto = [round((1 - q50(g, k, "sfqa-auto") / q50(g, k, "fifo")) * 100)
                for g, k, _ in configs]
    red_fgd = [round((1 - q50(g, k, "fgd") / q50(g, k, "fifo")) * 100)
               for g, k, _ in configs]
    p1_auto = [p1(g, k, "sfqa-auto") for g, k, _ in configs]
    p1_fgd = [p1(g, k, "fgd") for g, k, _ in configs]
    p1_sjf = [p1(g, k, "sjf") for g, k, _ in configs]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    x = np.arange(len(configs))

    # 좌: 중앙값 단축 — FGD(배치)도 sfqa-auto(큐)만큼/더 줄인다
    ax = axes[0]
    w = .38
    ax.bar(x - w / 2, red_auto, w, label="sfqa-auto (queue)", color="tab:red")
    ax.bar(x + w / 2, red_fgd, w, label="FGD (placement)", color="tab:gray")
    for i, v in enumerate(red_auto):
        ax.text(i - w / 2, v + 1, f"{v}", ha="center", fontsize=8)
    for i, v in enumerate(red_fgd):
        ax.text(i + w / 2, v + 1, f"{v}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("q_p50 reduction vs FIFO (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Both cut median vs FIFO\n(simulator, Philly 111k jobs)")
    ax.grid(alpha=.3, axis="y")
    ax.legend(fontsize=8)

    # 우: 공정성 — FGD는 배치만 하므로 과부하서 p1 붕괴, sfqa-auto만 유지
    ax = axes[1]
    w = .27
    ax.bar(x - w, p1_auto, w, label="sfqa-auto (queue)", color="tab:red")
    ax.bar(x, p1_fgd, w, label="FGD (placement)", color="tab:gray")
    ax.bar(x + w, p1_sjf, w, label="SJF", color="tab:orange")
    ax.axhline(100, ls="--", c="gray", lw=1)
    ax.text(len(configs) - .6, 101, "FIFO=100", fontsize=8, color="gray")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("order-fairness p1 (worst 1%, 100=fair)")
    ax.set_title("...but only the queue axis keeps fairness\n(0 = complete starvation)")
    ax.grid(alpha=.3, axis="y")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "report_scale.png"), dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)),
                    help="출력 디렉토리 (기본: results/)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    plot_pareto(args.out)
    plot_c48(args.out)
    plot_scale(args.out)
    print(f"3개 그래프 저장 완료: {args.out}/report_{{pareto_k3000,c48,scale}}.png")


if __name__ == "__main__":
    main()
