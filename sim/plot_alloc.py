"""GPU allocation 추세(전 구간) 시각화 — run_all.py 가 덤프한 <policy>_alloc.csv 사용.

allocation은 추세를 다 본다: 시작(min time)부터 끝까지 시계열을 그대로 계단(step) 플롯.
  - overlay: 전 정책 한 축에 겹쳐 비교
  - small-multiples: 정책별 패널 + 평균선

사용:
  plot_alloc.py <pj_dir> [--out <png>] [--unit day|hour] [--title ...]
"""
import argparse, csv, glob, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# run_all 의 정책 표시 순서(engine 먼저, lucid·sia 마지막)
ORDER = ["fifo", "sjf", "las", "kueue", "easy", "themis", "sfqa", "sfqa-auto", "lucid", "sia"]


def load_alloc(path):
    t, pct = [], []
    with open(path) as f:
        for r in csv.DictReader(f):
            t.append(float(r["time_s"])); pct.append(float(r["alloc_pct"]))
    return t, pct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--out", default="")
    ap.add_argument("--unit", choices=["day", "hour"], default="day")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.dir, "*_alloc.csv")))
    if not files:
        raise SystemExit(f"no *_alloc.csv in {a.dir}")
    series = {}
    for fp in files:
        name = os.path.basename(fp)[:-len("_alloc.csv")]
        series[name] = load_alloc(fp)
    pols = [p for p in ORDER if p in series] + [p for p in series if p not in ORDER]
    # 공통 시간 원점(전 정책 최소 time)
    t0 = min(s[0][0] for s in series.values() if s[0])
    div = 86400.0 if a.unit == "day" else 3600.0
    avg = {p: (sum(series[p][1]) / len(series[p][1]) if series[p][1] else 0) for p in pols}

    # 1) overlay
    fig, ax = plt.subplots(figsize=(13, 5.5))
    for p in pols:
        t, pct = series[p]
        ax.step([(x - t0) / div for x in t], pct, where="post", lw=1.0,
                label=f"{p} (avg {avg[p]:.0f}%)", alpha=0.8)
    ax.set_xlabel(f"time since first arrival ({a.unit})")
    ax.set_ylabel("GPU allocation (%)")
    ax.set_ylim(0, 102)
    ax.set_title(a.title or f"GPU allocation trend — {os.path.basename(a.dir.rstrip('/'))}")
    ax.legend(ncol=2, fontsize=8, loc="lower right")
    ax.grid(alpha=0.3)
    out = a.out or os.path.join(a.dir, "alloc_overlay.png")
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)
    print(f"→ {out}")

    # 2) small-multiples
    n = len(pols); cols = 2; rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(13, 2.3 * rows), sharex=True, sharey=True)
    axes = axes.flatten()
    for i, p in enumerate(pols):
        t, pct = series[p]
        ax = axes[i]
        ax.step([(x - t0) / div for x in t], pct, where="post", lw=0.8, color="tab:blue")
        ax.axhline(avg[p], ls="--", lw=1, color="tab:red")
        ax.set_title(f"{p}  (avg {avg[p]:.1f}%, max {max(pct) if pct else 0:.0f}%)", fontsize=9)
        ax.set_ylim(0, 102); ax.grid(alpha=0.3)
    for j in range(n, len(axes)):
        axes[j].axis("off")
    fig.supxlabel(f"time since first arrival ({a.unit})")
    fig.supylabel("GPU allocation (%)")
    out2 = out.replace(".png", "_panels.png")
    fig.tight_layout(); fig.savefig(out2, dpi=130); plt.close(fig)
    print(f"→ {out2}")


if __name__ == "__main__":
    main()
