"""Fig. 4 (paper/Pic/Fig_placement_hol.pdf) — 배치 정책별 HOL 회수량.

원래 그림에는 생성 스크립트가 없었고, 제목·부제가 §VI-E에서 철회된 단편화 인과
주장("HOL recovery grows with fragmentation", "the more a placement scatters free
GPUs, the more FIFO wastes")을 그대로 달고 있었다. 본문과 맞추려고 다시 그린다.

데이터는 sweep_results/placement/placement_table.csv 의 256-GPU single 행에서
직접 읽는다(하드코딩 없음). 막대는 FIFO 이용률, 그 위 누적분이 SAFA 가 회수한 몫.

사용: python3 plot_placement_hol.py
출력: ../paper/Pic/Fig_placement_hol.pdf
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sweep_results", "placement", "placement_table.csv")
OUT = os.path.join(HERE, os.pardir, "paper", "Pic", "Fig_placement_hol.pdf")

# consolidate → spread 순서(본문 §VI-E 서술 순서와 동일)
ORDER = [("mostallocated", "most-alloc"), ("kai_binpack", "KAI binpack"),
         ("compact", "compact"), ("fgd", "FGD"), ("mcts", "MCTS"),
         ("round_robin", "round-robin"), ("kai_spread", "KAI spread")]

FIFO_C, SAFA_C = "#9fb3c8", "#2f6f4e"


def load():
    rows = [r for r in csv.DictReader(open(SRC))
            if r["kind"] == "single" and r["gpu"] == "256"]
    by = {}
    for r in rows:
        by.setdefault(r["placement"], {})[r["policy"]] = r
    out = []
    for key, label in ORDER:
        f = float(by[key]["fifo"]["alloc_avg"])
        s = float(by[key]["sfqa-auto"]["alloc_avg"])
        out.append((label, f, s))
    return out


def main():
    data = load()
    fair = [float(r["fair_p1"]) for r in csv.DictReader(open(SRC))
            if r["kind"] == "single" and r["gpu"] == "256" and r["policy"] == "sfqa-auto"]
    lo, hi = min(fair), max(fair)

    fig, ax = plt.subplots(figsize=(8.9, 5.7))
    x = range(len(data))
    labels = [d[0] for d in data]
    base = [d[1] for d in data]
    gain = [d[2] - d[1] for d in data]

    ax.bar(x, base, 0.62, color=FIFO_C, label="FIFO (HOL-blocked)")
    ax.bar(x, gain, 0.62, bottom=base, color=SAFA_C, label="recovered by SAFA")
    for i, (lbl, f, s) in enumerate(data):
        ax.text(i, s + 0.12, f"+{s - f:.1f}", ha="center", va="bottom",
                fontsize=9, color=SAFA_C, fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_xlabel("placement:  consolidate  →  spread", fontsize=11)
    ax.set_ylabel("Utilization (%)", fontsize=11.5)
    ax.set_ylim(88, 98)
    ax.set_yticks([88, 90, 92, 94, 96, 98])
    ax.grid(axis="y", color="0.88", linewidth=0.7)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)

    ax.set_title(
        f"SAFA raises utilization under every placement "
        f"(256 GPUs, single; SAFA Fairness {lo:.1f}–{hi:.1f})",
        fontsize=10.5, pad=16)
    ax.text(0.5, 1.012, "the gain is largest where the FIFO baseline was lowest",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=9.5, color="0.35")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.135), ncol=2,
              frameon=False, fontsize=10)

    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"→ {os.path.normpath(OUT)}")
    for lbl, f, s in data:
        print(f"   {lbl:<13} FIFO {f:5.1f}  SAFA {s:5.1f}  +{s - f:.1f}")
    print(f"   SAFA Fairness {lo:.1f}~{hi:.1f}")


if __name__ == "__main__":
    main()
