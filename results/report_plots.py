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

# 논문용 출판 품질 설정: 벡터(PDF) + 큰 폰트(축소돼도 또렷), TrueType 폰트 임베드.
plt.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42,      # TrueType 임베드(편집기 호환)
    "font.size": 13, "axes.titlesize": 14, "axes.labelsize": 13,
    "xtick.labelsize": 11.5, "ytick.labelsize": 11.5, "legend.fontsize": 11,
    "axes.linewidth": 0.8, "figure.dpi": 150, "savefig.bbox": "tight",
})

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP_TABLE = os.path.join(ROOT, "sim", "sweep_results", "sweep_table.csv")


def _save(fig, out, name):
    """벡터 PDF(무손실) + 고해상도 PNG(300dpi) 동시 저장."""
    fig.savefig(os.path.join(out, name + ".pdf"))          # 벡터 — 확대해도 안 뭉개짐
    fig.savefig(os.path.join(out, name + ".png"), dpi=300)  # 고해상도 래스터 대안
    plt.close(fig)

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
    # 라벨 충돌 방지용 개별 오프셋(pt) — 밀집 구간 수동 배치
    off = {
        "default-FIFO": (8, 6), "SJF": (8, 6),
        "gate-FIFO": (-12, 16), "Kueue": (6, -18),
        "auto t=1": (10, 10), "SFQA fixed": (-34, -22),
        "auto t=10": (8, 12), "EASY*": (-18, -22),
    }
    fig, ax = plt.subplots(figsize=(8.2, 5.8))
    for name, (x, y) in K3000.items():
        squad = "auto" in name or "SFQA" in name
        on_f = name in K3000_FRONTIER
        c = "tab:red" if squad else ("tab:blue" if on_f else "gray")
        ax.scatter(x, y, s=120 if squad else 75, c=c, zorder=3,
                   edgecolors="k", linewidths=.5)
        ax.annotate(name, (x, y), textcoords="offset points",
                    xytext=off.get(name, (8, 6)), fontsize=10.5)
    fx = sorted(K3000[f] for f in K3000_FRONTIER)
    ax.plot([p[0] for p in fx], [p[1] for p in fx], "--", c="tab:blue",
            alpha=.5, zorder=1, label="Pareto frontier")
    ax.set_xlim(-15, 470)
    ax.set_ylim(620, 2560)
    ax.set_xlabel("median queueing delay p50 (s)  — efficiency")
    ax.set_ylabel("worst-case max (s) — starvation")
    ax.set_title("K8s measured, Philly-1K (peak 3.6x): protection costs median\n"
                 "(red = SQUAD family, * = EASY assumes perfect duration estimates)")
    ax.grid(alpha=.3)
    ax.legend()
    fig.tight_layout()
    _save(fig, out, "report_pareto_k3000")


def plot_c48(out):
    keys = list(C48)
    x = np.arange(len(keys))
    w = 0.26
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for i, p in enumerate(C48_POLICIES):
        vals = [C48[k][i] for k in keys]
        ax.bar(x + (i - 1) * w, vals, w, label=p, color=C48_COLORS[p])
        for j, v in enumerate(vals):
            ax.text(j + (i - 1) * w, v + 60, str(v), ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(keys)
    ax.set_ylabel("queueing delay (s)")
    ax.set_title("K8s measured, Philly-2K-C48 critical load (avg 1.01x, peak 8.9x):\n"
                 "sfqa-auto dominates ~97% of distribution; tails cross near the top 3%")
    ax.grid(alpha=.3, axis="y")
    ax.legend()
    fig.tight_layout()
    _save(fig, out, "report_c48")


# ── ④ auto 설계 동기 (SUMMARY §1 표2 + §2 κ6000) ────────────────────────
# 표2: 8개 워크로드 분포별 최적 α (고정 α가 워크로드마다 달라짐)
ALPHA_BY_DIST = {"Normal": 0.53, "Expon.": 0.44, "Log-norm": 1.63, "Gamma": 0.22,
                 "Beta": 0.26, "Weibull": 0.55, "Uniform": 0.5, "Poisson": 0.22}
# 고정 α(κ3000 튜닝값) vs auto, 부하 변화(κ3000→κ6000) 시 큐잉지연(초)
DRIFT = {  # cond: (fixed_p50, fixed_p90, auto_p50, auto_p90)
    "kappa=3000\n(tuned here)": (243, 589, 210, 582),
    "kappa=6000\n(2x load)":   (1080, 1613, 592, 907),
}


def plot_motivation(out):
    """auto를 만든 이유: 최적 α가 워크로드마다 7배 달라져 단일 값이 없음(C++ 시뮬, 표2)."""
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    names = list(ALPHA_BY_DIST); vals = [ALPHA_BY_DIST[n] for n in names]
    x = np.arange(len(names))
    bars = ax.bar(x, vals, .62, color="tab:purple")
    amin, amax = min(vals), max(vals)
    ax.axhline(amin, ls=":", c="gray", lw=1); ax.axhline(amax, ls=":", c="gray", lw=1)
    ax.annotate(f"{amax/amin:.0f}x spread\n(no single $\\alpha$)", (len(names)-1, amax),
                xytext=(-4, -8), textcoords="offset points", ha="right", va="top",
                fontsize=12, color="tab:purple", fontweight="bold")
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+0.03, f"{v}", ha="center", fontsize=9.5)
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=30, ha="right", fontsize=11)
    ax.set_ylabel("optimal fixed $\\alpha$"); ax.set_ylim(0, 1.8)
    ax.set_title("Optimal $\\alpha$ varies 7x across workloads\n(grid search must be redone per workload)")
    ax.grid(alpha=.3, axis="y")
    fig.tight_layout()
    _save(fig, out, "report_motivation")


def load_sweep():
    """sweep_table.csv → {(gpu, kind, policy): row dict}"""
    rows = {}
    with open(SWEEP_TABLE) as f:
        for r in csv.DictReader(f):
            rows[(r["gpu"], r["kind"], r["policy"])] = r
    return rows


# 정책별 색/스타일 (전 그래프 공통)
POL_STYLE = {
    "fifo": ("#888", "-"), "sjf": ("tab:orange", "-"), "las": ("tab:green", "-"),
    "kueue": ("tab:olive", "-"), "easy": ("tab:brown", "--"), "themis": ("tab:purple", "-"),
    "fgd": ("tab:gray", "-."), "sfqa": ("tab:cyan", "-"), "sfqa-auto": ("tab:red", "-"),
    "lucid": ("tab:blue", ":"), "sia": ("tab:pink", ":"),
}
RAW = os.path.join(ROOT, "sim", "sweep_results", "raw")


def _read_queue(cmpdir, pol):
    p = os.path.join(RAW, cmpdir, pol + "_jobs.csv")
    if not os.path.exists(p):
        return None
    q = []
    with open(p) as f:
        for r in csv.DictReader(f):
            q.append(float(r["queue_sec"]))
    return sorted(q) if q else None


# ── 측정 데이터 (SUMMARY.md) ────────────────────────────────────────────────
K3000_FULL = {  # policy: (p50, p90, max)  [s]  — SUMMARY §1
    "default-FIFO": (17, 275, 2450), "SJF": (33, 461, 2265),
    "gate-FIFO": (189, 484, 924), "Kueue": (195, 396, 869),
    "auto $\\tau$=1": (210, 582, 937), "SFQA": (243, 589, 782),
    "auto $\\tau$=10": (290, 612, 768), "EASY*": (419, 639, 691),
}
EASY_NOISE = {  # f: (q_p50,q_p90,q_max, bsld_p50,bsld_p90,bsld_max) — SUMMARY §1.5
    "f=0\n(perfect)": (5, 31, 46, 1.25, 3.73, 5.30),
    "f=1\n(1-2x)": (5, 22, 37, 1.10, 2.82, 4.40),
    "f=3\n(1-4x)": (5, 21, 37, 1.10, 2.70, 4.30),
}
SENS = {  # knob: [(label, delta%)] — results/sweep_summary.csv
    "R penalty": [("0.05", 0.01), ("0.1*", 0.0), ("0.15", 0.0), ("0.2", 2.02), ("0.3", -0.82)],
    "P base": [("1.5", 1.23), ("2*", 0.0), ("3", 1.78), ("4", 0.35)],
    "window $m$": [("1", 8.9), ("2", 1.35), ("3*", 0.0), ("5", -0.95), ("10", -0.63)],
}


def plot_measured_bar(out):
    """본선 실측 8정책 × (p50, p90, max) 그룹 막대 — 전 정책 한눈에."""
    pols = list(K3000_FULL)
    x = np.arange(len(pols)); w = 0.27
    fig, ax = plt.subplots(figsize=(11, 5))
    for j, (m, lab, col) in enumerate([(0, "p50", "tab:blue"), (1, "p90", "tab:orange"),
                                       (2, "max (starvation)", "tab:red")]):
        vals = [K3000_FULL[p][m] for p in pols]
        ax.bar(x + (j - 1) * w, vals, w, label=lab, color=col)
    ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels(pols, rotation=20, ha="right", fontsize=10)
    ax.set_ylabel("queueing delay (s, log)")
    ax.set_title("K8s measured, Philly-1K (peak 3.6x): all 8 policies\n"
                 "(* EASY assumes perfect duration estimates)")
    ax.grid(alpha=.3, axis="y", which="both"); ax.legend()
    fig.tight_layout()
    _save(fig, out, "report_measured_bar")


def plot_sensitivity(out):
    """잔여 내부 상수 민감도 (makespan Δ%) — m=1만 민감, 나머지 robust."""
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, (knob, pts) in zip(axes, SENS.items()):
        labs = [p[0] for p in pts]; vals = [p[1] for p in pts]
        cols = ["tab:red" if abs(v) > 5 else ("tab:green" if "*" in l else "tab:gray")
                for l, v in zip(labs, vals)]
        ax.bar(range(len(labs)), vals, .6, color=cols)
        ax.axhline(0, c="k", lw=.6); ax.axhline(2, ls=":", c="gray", lw=1); ax.axhline(-2, ls=":", c="gray", lw=1)
        for i, v in enumerate(vals):
            ax.text(i, v + (0.3 if v >= 0 else -0.6), f"{v:+.1f}", ha="center", fontsize=9)
        ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs)
        ax.set_title(knob); ax.set_xlabel("value (* = default)")
        ax.grid(alpha=.3, axis="y")
    axes[0].set_ylabel("makespan change vs base (%)")
    fig.suptitle("Sensitivity of remaining internal constants (C++ sim): "
                 "only window $m$=1 is sensitive; all others within $\\pm$2%", fontsize=13)
    fig.tight_layout()
    _save(fig, out, "report_sensitivity")


def plot_easy_noise(out):
    """EASY 추정 노이즈(과대추정 역설): 노이즈가 오히려 max·BSLD 개선."""
    fs = list(EASY_NOISE); x = np.arange(len(fs)); w = 0.35
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
    qmax = [EASY_NOISE[f][2] for f in fs]; qp90 = [EASY_NOISE[f][1] for f in fs]
    a1.bar(x - w/2, qp90, w, label="p90", color="tab:orange")
    a1.bar(x + w/2, qmax, w, label="max", color="tab:red")
    for i in range(len(fs)):
        a1.text(i - w/2, qp90[i]+0.5, f"{qp90[i]}", ha="center", fontsize=9)
        a1.text(i + w/2, qmax[i]+0.5, f"{qmax[i]}", ha="center", fontsize=9)
    a1.set_xticks(x); a1.set_xticklabels(fs); a1.set_ylabel("queueing delay (s)")
    a1.set_title("(a) Queueing delay"); a1.grid(alpha=.3, axis="y"); a1.legend()
    bmax = [EASY_NOISE[f][5] for f in fs]; bp90 = [EASY_NOISE[f][4] for f in fs]
    a2.bar(x - w/2, bp90, w, label="p90", color="tab:orange")
    a2.bar(x + w/2, bmax, w, label="max", color="tab:red")
    for i in range(len(fs)):
        a2.text(i - w/2, bp90[i]+0.05, f"{bp90[i]}", ha="center", fontsize=9)
        a2.text(i + w/2, bmax[i]+0.05, f"{bmax[i]}", ha="center", fontsize=9)
    a2.set_xticks(x); a2.set_xticklabels(fs); a2.set_ylabel("BSLD")
    a2.set_title("(b) Bounded slowdown"); a2.grid(alpha=.3, axis="y"); a2.legend()
    fig.suptitle("EASY estimation-noise robustness (S=360): "
                 "overestimation paradox — noise improves the tail", fontsize=13)
    fig.tight_layout()
    _save(fig, out, "report_easy_noise")


def plot_alloc(out):
    """GPU 할당률 평균 (512 단일·이종, 전 정책) — Sia만 탄력 비용으로 낮음."""
    rows = load_sweep()
    order = ["fifo", "sjf", "las", "kueue", "easy", "themis", "fgd", "sfqa", "sfqa-auto", "lucid", "sia"]
    x = np.arange(len(order)); w = 0.38
    fig, ax = plt.subplots(figsize=(11, 4.6))
    for j, (kind, col) in enumerate([("single", "tab:blue"), ("hetero", "tab:cyan")]):
        vals = [float(rows[(("512"), kind, p)]["alloc_avg"]) if ("512", kind, p) in rows else 0
                for p in order]
        ax.bar(x + (j - 0.5) * w, vals, w, label=f"512 {kind}", color=col)
    ax.set_ylim(40, 102)
    ax.set_xticks(x); ax.set_xticklabels(order, rotation=20, ha="right", fontsize=10)
    ax.set_ylabel("avg GPU allocation (%)")
    ax.set_title("Average GPU allocation (Philly 111k, 512 GPU): "
                 "all near 99% except Sia (elastic ILP leaves GPUs idle)")
    ax.grid(alpha=.3, axis="y"); ax.legend()
    fig.tight_layout()
    _save(fig, out, "report_alloc")


def plot_cdf(out):
    """큐잉 지연 전체 분포 CDF (512 GPU 단일·이종, 전 정책). 백분위 표가 못 보여주는
    분포 형태를 드러냄 — sfqa-auto는 몸통을 왼쪽(빠름)으로 당기면서 꼬리도 억제."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    order = ["fifo", "sjf", "las", "kueue", "easy", "themis", "fgd", "sfqa", "sfqa-auto", "lucid", "sia"]
    for ax, kind in zip(axes, ["single", "hetero"]):
        for pol in order:
            q = _read_queue(f"cmp512_{kind}", pol)
            if not q:
                continue
            y = np.linspace(0, 1, len(q))
            c, ls = POL_STYLE[pol]
            lw = 2.4 if pol == "sfqa-auto" else 1.3
            a = 1.0 if pol in ("sfqa-auto", "fifo") else 0.7
            ax.plot(np.maximum(q, 1), y, ls, color=c, lw=lw, alpha=a, label=pol)
        ax.set_xscale("log")
        ax.set_xlabel("queueing delay (s, log)")
        ax.set_title(f"512 GPU, {kind} (1.8$\\times$)")
        ax.grid(alpha=.3, which="both")
    axes[0].set_ylabel("CDF (fraction of jobs)")
    axes[1].legend(ncol=2, fontsize=9, loc="lower right")
    fig.suptitle("Queueing-delay CDF (Philly 111k): full distribution, all policies", fontsize=14)
    fig.tight_layout()
    _save(fig, out, "report_cdf")


def plot_loadcurve(out):
    """부하곡선: 클러스터 크기(부하)에 따른 q_p50 / q_max / 공정성 p1, 전 정책.
    부하·이질성이 깊을수록 sfqa-auto의 균형 우위가 커짐을 한 눈에."""
    rows = load_sweep()
    gpus = ["256", "512", "1024"]
    xg = [256, 512, 1024]
    order = ["fifo", "sjf", "las", "kueue", "easy", "themis", "fgd", "sfqa", "sfqa-auto", "lucid", "sia"]
    panels = [("q_p50", "median queue delay p50 (s)", True),
              ("q_max", "worst-case max (s)", True),
              ("fair_p1", "order-fairness p1 (100=fair)", False)]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for ax, (key, ylab, logy) in zip(axes, panels):
        for pol in order:
            ys = []
            for g in gpus:
                r = rows.get((g, "hetero", pol))
                ys.append(float(r[key]) if r else np.nan)
            if all(np.isnan(ys)):
                continue
            c, ls = POL_STYLE[pol]
            lw = 2.4 if pol == "sfqa-auto" else 1.3
            a = 1.0 if pol in ("sfqa-auto", "fifo") else 0.7
            ax.plot(xg, ys, ls, marker="o", ms=4, color=c, lw=lw, alpha=a, label=pol)
        from matplotlib.ticker import NullFormatter, FixedLocator
        ax.set_xscale("log")
        ax.xaxis.set_major_locator(FixedLocator(xg)); ax.set_xticklabels(xg)
        ax.xaxis.set_minor_formatter(NullFormatter())   # 로그 보조눈금 라벨 제거
        if logy:
            ax.set_yscale("log")
        ax.set_xlabel("cluster GPUs (256=3.6$\\times$, 512=1.8$\\times$, 1024=0.9$\\times$ load)")
        ax.set_ylabel(ylab); ax.grid(alpha=.3, which="both")
    axes[2].legend(ncol=2, fontsize=8.5, loc="lower left")
    fig.suptitle("Load dependence on heterogeneous clusters (Philly 111k, all policies)", fontsize=14)
    fig.tight_layout()
    _save(fig, out, "report_loadcurve")


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
        ax.text(i - w / 2, v + 1, f"{v}", ha="center", fontsize=9)
    for i, v in enumerate(red_fgd):
        ax.text(i + w / 2, v + 1, f"{v}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("q_p50 reduction vs FIFO (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Both cut median vs FIFO\n(simulator, Philly 111k jobs)")
    ax.grid(alpha=.3, axis="y")

    # 우: 공정성 — FGD는 배치만 하므로 과부하서 p1 붕괴, sfqa-auto만 유지
    ax = axes[1]
    w = .27
    ax.bar(x - w, p1_auto, w, label="sfqa-auto (queue)", color="tab:red")
    ax.bar(x, p1_fgd, w, label="FGD (placement)", color="tab:gray")
    ax.bar(x + w, p1_sjf, w, label="SJF", color="tab:orange")
    ax.axhline(100, ls="--", c="gray", lw=1)
    ax.text(len(configs) - .6, 101, "FIFO=100", fontsize=9, color="gray")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("order-fairness p1 (worst 1%, 100=fair)")
    ax.set_title("...but only the queue axis keeps fairness\n(0 = complete starvation)")
    ax.grid(alpha=.3, axis="y")
    h, lab = ax.get_legend_handles_labels()        # 3개 항목(sfqa-auto/FGD/SJF)
    fig.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, 0.05),
               ncol=len(lab), fontsize=11, frameon=True)
    fig.tight_layout(rect=[0, 0.08, 1, 1])         # 하단 범례 공간
    _save(fig, out, "report_scale")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)),
                    help="출력 디렉토리 (기본: results/)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    plot_pareto(args.out)
    plot_measured_bar(args.out)
    plot_c48(args.out)
    plot_easy_noise(args.out)
    plot_motivation(args.out)
    plot_sensitivity(args.out)
    plot_cdf(args.out)
    plot_loadcurve(args.out)
    plot_scale(args.out)
    plot_alloc(args.out)
    print(f"10개 그래프 저장 완료: {args.out}/report_*.{{pdf,png}}")


if __name__ == "__main__":
    main()
