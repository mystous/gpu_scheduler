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
    order = ["fifo", "sjf", "las", "kueue", "easy", "themis", "fgd", "sfqa", "sfqa-auto", "lucid"]
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
                 "all policies near 99% (queue/placement effects, not resource idling)")
    ax.grid(alpha=.3, axis="y"); ax.legend()
    fig.tight_layout()
    _save(fig, out, "report_alloc")


def plot_cdf(out):
    """큐잉 지연 전체 분포 CDF (512 GPU 단일·이종, 전 정책). 백분위 표가 못 보여주는
    분포 형태를 드러냄 — sfqa-auto는 몸통을 왼쪽(빠름)으로 당기면서 꼬리도 억제."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    order = ["fifo", "sjf", "las", "kueue", "easy", "themis", "fgd", "sfqa", "sfqa-auto", "lucid"]
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
    h, lab = axes[1].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, 0.06),
               ncol=len(lab), fontsize=10, frameon=True)
    fig.suptitle("Queueing-delay CDF (Philly 111k): full distribution, all policies", fontsize=14)
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    _save(fig, out, "report_cdf")


ORDER_ALL = ["fifo", "sjf", "las", "kueue", "easy", "themis", "fgd",
             "sfqa", "sfqa-auto", "lucid"]   # Sia는 동일엔진 비교에서 제외(related work) — 프로파일 결정변수 트레이스에 부재


def plot_loadcurve(out):
    """종합 부하곡선: 클러스터 크기(부하)에 따른 중앙값(q_p50)·최악대기(q_max)·공정성(p1)을
    단일·이종 두 행으로, 전 10정책(FGD 포함; Sia는 동일엔진 제외) 라인으로 한 눈에.
    부하·이질성이 깊을수록 sfqa-auto만 '빠름+공정'을 동시에 유지함을 보인다."""
    rows = load_sweep()
    gpus = ["256", "512", "1024"]
    xg = [256, 512, 1024]
    panels = [("q_p50", "median queue delay p50 (s)", True),
              ("q_max", "worst-case max (s)", True),
              ("fair_p1", "order-fairness p1 (100=fair)", False)]
    from matplotlib.ticker import NullFormatter, FixedLocator
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 6.4))
    for ri, kind in enumerate(["single", "hetero"]):
        for ci, (key, ylab, logy) in enumerate(panels):
            ax = axes[ri][ci]
            for pol in ORDER_ALL:
                ys = []
                for g in gpus:
                    r = rows.get((g, kind, pol))
                    ys.append(float(r[key]) if r else np.nan)
                if all(np.isnan(ys)):
                    continue
                c, ls = POL_STYLE[pol]
                lw = 2.6 if pol == "sfqa-auto" else 1.3
                a = 1.0 if pol in ("sfqa-auto", "fifo") else 0.7
                ax.plot(xg, ys, ls, marker="o", ms=4, color=c, lw=lw, alpha=a, label=pol)
            ax.set_xscale("log")
            ax.xaxis.set_major_locator(FixedLocator(xg)); ax.set_xticklabels(xg)
            ax.xaxis.set_minor_formatter(NullFormatter())
            if logy:
                ax.set_yscale("log")
            if ri == 1 and ci == 1:   # 가운데 하단 패널에만 한 번(좌우 중복 라벨이 겹쳐 뭉개지던 문제 해소)
                ax.set_xlabel("cluster GPUs (256=3.6$\\times$, 512=1.8$\\times$, 1024=0.9$\\times$ load)")
            ax.set_ylabel(ylab)
            ax.set_title(f"{kind} — {['median','worst-case','fairness'][ci]}", fontsize=12)
            ax.grid(alpha=.3, which="both")
    h, lab = axes[0][0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, 0.045),
               ncol=len(lab), fontsize=11, frameon=True)
    fig.suptitle("Load dependence, all 10 policies (Philly 111k): single (top) vs heterogeneous (bottom)",
                 fontsize=14)
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    _save(fig, out, "report_loadcurve")


def plot_tradeoff(out):
    """q–공정성 trade-off 산점도: 6구성(단일·이종 × 256/512/1024)을 패널로,
    각 점이 한 정책. 좌상단(빠르고 공정)이 이상적 — sfqa-auto만 그 영역을 차지함을 보인다."""
    rows = load_sweep()
    gpus = ["256", "512", "1024"]
    ld = {"256": "3.6$\\times$", "512": "1.8$\\times$", "1024": "0.9$\\times$"}
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 6.6))
    for ri, kind in enumerate(["single", "hetero"]):
        for ci, g in enumerate(gpus):
            ax = axes[ri][ci]
            for pol in ORDER_ALL:
                r = rows.get((g, kind, pol))
                if not r:
                    continue
                x = max(float(r["q_p50"]), 1.0)
                y = float(r["fair_p1"])
                c, _ = POL_STYLE[pol]
                big = pol == "sfqa-auto"
                ax.scatter(x, y, s=150 if big else 70, color=c, zorder=3,
                           edgecolor="k", linewidths=0.9 if big else 0.4)
                ax.annotate(pol, (x, y), fontsize=8, xytext=(4, 3),
                            textcoords="offset points")
            ax.set_xscale("log")
            ax.set_ylim(-5, 108)
            if ri == 1:
                ax.set_xlabel("median queue delay p50 (s, log) — faster $\\leftarrow$")
            if ci == 0:
                ax.set_ylabel("order-fairness p1 (100=fair) $\\uparrow$")
            ax.set_title(f"{g} GPU {kind} ({ld[g]})", fontsize=12)
            ax.grid(alpha=.3, which="both")
    fig.suptitle("Queue-delay vs fairness trade-off, all 10 policies (Philly 111k): "
                 "top-left = fast & fair (sfqa-auto's target region)", fontsize=14)
    fig.tight_layout()
    _save(fig, out, "report_tradeoff")


def plot_scale(out):
    """전 11정책(FGD 포함) 정면 비교 — 대표 과부하 구성(512 GPU 이종, 1.8x):
    (좌) 중앙값 q_p50 (낮을수록 빠름), (우) 공정성 p1 (높을수록 공정).
    정책을 x축에 두어 11개를 모두 표시 — '빠름'과 '공정'을 동시에 가진 정책은 sfqa-auto뿐."""
    rows = load_sweep()
    g, k = "512", "hetero"
    pols = [p for p in ORDER_ALL if (g, k, p) in rows]
    q50 = [max(float(rows[(g, k, p)]["q_p50"]), 1.0) for p in pols]
    p1 = [float(rows[(g, k, p)]["fair_p1"]) for p in pols]
    cols = [POL_STYLE[p][0] for p in pols]
    x = np.arange(len(pols))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.0))

    # 좌: 중앙값 (로그) — 낮을수록 빠름
    ax = axes[0]
    ax.bar(x, q50, 0.7, color=cols, edgecolor="k", linewidth=0.4)
    ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels(pols, rotation=30, ha="right", fontsize=10)
    ax.set_ylabel("median queue delay p50 (s, log)")
    ax.set_title("(a) Speed: median queue delay (lower = faster)")
    ax.grid(alpha=.3, axis="y", which="both")

    # 우: 공정성 p1 — 높을수록 공정, 0=완전 기아
    ax = axes[1]
    bars = ax.bar(x, p1, 0.7, color=cols, edgecolor="k", linewidth=0.4)
    for b, v in zip(bars, p1):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.0f}", ha="center", fontsize=9)
    ax.axhline(100, ls="--", c="gray", lw=1)
    ax.text(len(pols) - 0.5, 101, "FIFO=100", fontsize=9, color="gray", ha="right")
    ax.set_ylim(0, 112)
    ax.set_xticks(x); ax.set_xticklabels(pols, rotation=30, ha="right", fontsize=10)
    ax.set_ylabel("order-fairness p1 (worst 1%, 100=fair)")
    ax.set_title("(b) Fairness: worst-1% order-fairness (0 = starvation)")
    ax.grid(alpha=.3, axis="y")

    fig.suptitle("All policies at peak overload (Philly 111k, 512 GPU heterogeneous, 1.8$\\times$): "
                 "lightweight fast policies collapse fairness; only sfqa-auto keeps it without prior information",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    _save(fig, out, "report_scale")


def _bigjob_queue(cmpdir, pol, gpu=8):
    """raw _jobs.csv에서 요청 GPU=gpu(최대) 작업의 큐 지연(queue_sec) 리스트."""
    p = os.path.join(RAW, cmpdir, pol + "_jobs.csv")
    if not os.path.exists(p):
        return None
    q = []
    with open(p) as f:
        for r in csv.DictReader(f):
            if int(r["gpu_count"]) == gpu:
                q.append(float(r["queue_sec"]))
    return sorted(q) if q else None


def plot_bigjob(out):
    """최대(8-GPU) 작업의 큐 지연: 중앙값 vs 최악 꼬리(p99). sfqa-auto는 중앙값은
    FIFO보다 크지만 p99(영구 적체 꼬리)는 SJF보다 낮춰 SJF식 starvation tail을 끊는다."""
    pols = ["fifo", "sjf", "themis", "sfqa-auto"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, kind in zip(axes, ["single", "hetero"]):
        med, p99 = [], []
        for pol in pols:
            q = _bigjob_queue(f"cmp512_{kind}", pol)
            if not q:
                med.append(0); p99.append(0); continue
            med.append(q[len(q) // 2])
            p99.append(q[min(len(q) - 1, int(len(q) * 0.99))])
        x = np.arange(len(pols)); w = 0.38
        b1 = ax.bar(x - w / 2, med, w, label="median", color="tab:blue")
        b2 = ax.bar(x + w / 2, p99, w, label="p99 (starvation tail)", color="tab:red")
        # sfqa-auto p99 vs sjf p99 강조(꼬리 절단)
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels(["FIFO", "SJF", "Themis", "sfqa-auto"], fontsize=10)
        ax.set_title(f"512 GPU, {kind} (1.8$\\times$)")
        ax.grid(alpha=.3, axis="y", which="both")
        for bars in (b1, b2):
            for b in bars:
                v = b.get_height()
                if v > 0:
                    ax.text(b.get_x() + b.get_width() / 2, v * 1.05,
                            f"{v/1e6:.2f}M", ha="center", fontsize=8)
    axes[0].set_ylabel("8-GPU job queue delay (s, log)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, 0.06),
               ncol=2, fontsize=10, frameon=True)
    fig.suptitle("Largest (8-GPU) jobs: sfqa-auto raises the median but bounds the worst-case "
                 "tail (p99) below SJF --- breaking SJF's permanent starvation", fontsize=12)
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    _save(fig, out, "report_bigjob")


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
    plot_tradeoff(args.out)
    plot_scale(args.out)
    plot_alloc(args.out)
    plot_bigjob(args.out)
    print(f"11개 그래프 저장 완료: {args.out}/report_*.{{pdf,png}}")


if __name__ == "__main__":
    main()
