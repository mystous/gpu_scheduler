#!/usr/bin/env python3
"""새 실험(ablation grid / sensitivity / Helios / placement) 결과 그래프 생성.
출력: paper/Pic/fig_ablation_grid.pdf, fig_sensitivity.pdf, fig_helios.pdf, fig_placement.pdf
라벨은 폰트 안전을 위해 영문."""
import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.join(HERE, "sweep_results")
OUT = os.path.abspath(os.path.join(HERE, "..", "paper", "Pic"))
os.makedirs(OUT, exist_ok=True)

DISP = {"fifo": "FIFO", "sjf": "SJF", "las": "LAS", "kueue": "Kueue", "easy": "EASY",
        "themis": "Themis", "fgd": "FGD", "sfqa": "SAFA-fix", "sfqa-auto": "SAFA",
        "lucid": "Lucid"}
ORDER = ["fifo", "sjf", "las", "kueue", "easy", "themis", "fgd", "lucid", "sfqa", "sfqa-auto"]
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})


def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))


# ── Fig 1: ablation α-grid — fixed-α p1 vs α, with tuning-free SAFA line ──────
def fig_ablation_grid():
    rows = load(os.path.join(SR, "ablation", "alpha_grid.csv"))
    configs = [("single", 256), ("single", 512), ("single", 1024),
               ("hetero", 256), ("hetero", 512), ("hetero", 1024)]
    fig, axes = plt.subplots(2, 3, figsize=(7.1, 3.8), sharex=True)
    for ax, (kind, gpu) in zip(axes.flat, configs):
        fixed = sorted([r for r in rows if r["kind"] == kind and int(r["gpu"]) == gpu
                        and r["policy"] == "sfqa" and r["alpha"]],
                       key=lambda r: float(r["alpha"]))
        xs = [float(r["alpha"]) for r in fixed]
        ys = [float(r["fair_p1"]) for r in fixed]
        auto = [r for r in rows if r["kind"] == kind and int(r["gpu"]) == gpu
                and r["policy"] == "sfqa-auto"]
        ax.plot(xs, ys, "o-", color="#d9534f", ms=2.5, lw=1.0, label="fixed $\\alpha$")
        if auto:
            ya = float(auto[0]["fair_p1"])
            ax.axhline(ya, ls="--", color="#2c7fb8", lw=1.3, label="SAFA (tuning-free)")
            if ya - max(ys) > 2:
                ax.annotate("", xy=(xs[len(xs)//2], ya), xytext=(xs[len(xs)//2], max(ys)),
                            arrowprops=dict(arrowstyle="<->", color="gray", lw=0.7))
        ax.set_xscale("log")
        ax.set_title(f"{kind} {gpu} GPU", fontsize=8)
        ax.set_ylim(-3, 105)
    for ax in axes[1]:
        ax.set_xlabel("fixed age-weight $\\alpha$ (log)")
    for ax in axes[:, 0]:
        ax.set_ylabel("order-fairness $p_1$")
    axes[0, 0].legend(fontsize=7, loc="center right", framealpha=0.9)
    fig.suptitle("No fixed $\\alpha$ reaches tuning-free SAFA's fairness (any workload)", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(OUT, "fig_ablation_grid.pdf"))
    plt.close(fig)
    print("wrote fig_ablation_grid.pdf")


# ── Fig 2: sensitivity ±50% — p1 per policy, range across perturbations ───────
def fig_sensitivity():
    rows = [r for r in load(os.path.join(SR, "sensitivity", "sensitivity_full.csv"))
            if r["kind"] == "hetero" and int(r["gpu"]) == 512]
    pols = [p for p in ORDER if any(r["policy"] == p for r in rows)]
    base, lo, hi = [], [], []
    for p in pols:
        vs = [float(r["fair_p1"]) for r in rows if r["policy"] == p]
        b = [float(r["fair_p1"]) for r in rows if r["policy"] == p and r["scenario"] == "baseline"]
        base.append(b[0] if b else sum(vs)/len(vs)); lo.append(min(vs)); hi.append(max(vs))
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    xs = range(len(pols))
    colors = ["#2c7fb8" if p == "sfqa-auto" else "#7bccc4" if p == "sfqa"
              else "#bdbdbd" for p in pols]
    ax.bar(xs, base, color=colors, width=0.7,
           yerr=[[b-l for b, l in zip(base, lo)], [h-b for h, b in zip(hi, base)]],
           capsize=2, ecolor="#d9534f", error_kw={"lw": 0.8})
    ax.set_xticks(list(xs)); ax.set_xticklabels([DISP[p] for p in pols], rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("order-fairness $p_1$"); ax.set_ylim(0, 105)
    ax.set_title("512 hetero: $\\pm$50% coeff. perturbation\n(whisker=min/max; baselines stay $\\approx$0)", fontsize=8)
    fig.savefig(os.path.join(OUT, "fig_sensitivity.pdf"))
    plt.close(fig)
    print("wrote fig_sensitivity.pdf")


# ── Fig 3: Helios — starvation rate (lt50%) per policy, overload hetero ───────
def fig_helios():
    rows = [r for r in load(os.path.join(SR, "helios", "sweep_table.csv"))
            if r["kind"] == "hetero" and int(r["gpu"]) == 80 and r["policy"] in DISP]
    rows = sorted(rows, key=lambda r: float(r["lt50_pct"]), reverse=True)
    pols = [r["policy"] for r in rows]
    vals = [float(r["lt50_pct"]) for r in rows]
    colors = ["#2c7fb8" if p == "sfqa-auto" else "#7bccc4" if p == "sfqa"
              else "#9ecae1" if p == "fifo" else "#bdbdbd" for p in pols]
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    ax.barh(range(len(pols)), vals, color=colors)
    ax.set_yticks(range(len(pols))); ax.set_yticklabels([DISP[p] for p in pols], fontsize=7)
    ax.set_xlabel("starvation rate lt50\\% (lower = fairer)")
    ax.set_title("Helios (Venus, 125k jobs) overload hetero\nSAFA starves $\\approx$1/3 of greedy baselines", fontsize=8)
    for i, v in enumerate(vals):
        ax.text(v+0.3, i, f"{v:.1f}", va="center", fontsize=6.5)
    ax.set_xlim(0, max(vals)*1.18)
    fig.savefig(os.path.join(OUT, "fig_helios.pdf"))
    plt.close(fig)
    print("wrote fig_helios.pdf")


# ── Fig 4: placement-agnostic — SAFA p1 across 4 core placements ──────────────
def fig_placement():
    rows = load(os.path.join(SR, "placement", "placement_table.csv"))
    placements = ["mostallocated", "compact", "round_robin", "mcts"]
    plabel = {"mostallocated": "most-alloc", "compact": "compact",
              "round_robin": "round-robin", "mcts": "MCTS"}
    configs = [("256:hetero", "256 het"), ("512:hetero", "512 het"), ("512:single", "512 sgl")]
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    w = 0.2
    for ci, (cfg, clab) in enumerate(configs):
        ys = []
        for pl in placements:
            m = [r for r in rows if r["config"] == cfg and r["placement"] == pl
                 and r["policy"] == "sfqa-auto"]
            ys.append(float(m[0]["fair_p1"]) if m else 0)
        xs = [j + ci*w for j in range(len(placements))]
        ax.bar(xs, ys, width=w, label=clab)
    ax.axhline(50, ls=":", color="gray", lw=0.8)
    ax.text(0.02, 51, "$p_1$=50", fontsize=6.5, color="gray")
    ax.set_xticks([j + w for j in range(len(placements))])
    ax.set_xticklabels([plabel[p] for p in placements], rotation=20, ha="right", fontsize=7)
    ax.set_ylabel("SAFA order-fairness $p_1$"); ax.set_ylim(0, 70)
    ax.set_title("SAFA $p_1$ across core placements\n(SJF/LAS = 0 at hetero, any placement)", fontsize=8)
    ax.legend(fontsize=6.5, ncol=3, loc="upper center", columnspacing=1.0)
    fig.savefig(os.path.join(OUT, "fig_placement.pdf"))
    plt.close(fig)
    print("wrote fig_placement.pdf")


if __name__ == "__main__":
    fig_ablation_grid()
    fig_sensitivity()
    fig_helios()
    fig_placement()
    print("done →", OUT)
