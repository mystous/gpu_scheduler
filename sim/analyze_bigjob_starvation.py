#!/usr/bin/env python3
"""
analyze_bigjob_starvation.py — 리뷰 지적 N5 검증

리뷰어 비판:
  SFQA/sfqa-auto는 R(자리 적합도)이 큰 작업을 큰 작업 앞으로 승급시키므로,
  HOL 블로킹의 주범인 가장 큰 작업(8 GPU)은 R이 최소라 계속 뒤로 밀려
  오히려 더 굶을 수 있다 → 'starvation-free'는 과장이다.

이 스크립트는 raw <policy>_jobs.csv 의 queue_sec 를 요청 GPU 수 그룹별로
집계하여, 특히 8-GPU(가장 큰) 작업 그룹의 큐 지연을
fifo / sjf / themis / sfqa-auto 에서 비교한다.

데이터: sim/sweep_results/raw/cmp<gpu>_<kind>/<policy>_jobs.csv
  컬럼: job_id,arrival_s,start_s,queue_sec,service_sec,gpu_count
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_ROOT = os.path.join(HERE, "sweep_results", "raw")

# 논문 비교 대상 정책 (출력 순서 고정)
FOCUS_POLICIES = ["fifo", "sjf", "themis", "sfqa-auto"]

# GPU 수 → 그룹 라벨
def gpu_group(g):
    if g <= 1:
        return "1"
    if g <= 4:
        return "2-4"
    if g <= 7:
        return "5-7"
    return "8+"

GROUP_ORDER = ["1", "2-4", "5-7", "8+"]


def percentile(sorted_vals, p):
    """선형 보간 백분위 (p in [0,100]). sorted_vals 는 정렬된 list."""
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (p / 100.0) * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def median(sorted_vals):
    return percentile(sorted_vals, 50)


def load_jobs(config_dir, policy):
    path = os.path.join(config_dir, f"{policy}_jobs.csv")
    if not os.path.isfile(path):
        return None
    # 그룹별 queue_sec 리스트
    groups = {g: [] for g in GROUP_ORDER}
    with open(path, newline="") as fh:
        rdr = csv.DictReader(fh)
        for row in rdr:
            try:
                q = float(row["queue_sec"])
                g = int(float(row["gpu_count"]))
            except (KeyError, ValueError):
                continue
            groups[gpu_group(g)].append(q)
    for g in groups:
        groups[g].sort()
    return groups


def fmt_sec(x):
    if x != x:  # nan
        return "    n/a"
    # 초 → 시간으로 보조 표기는 생략, 초 단위 정수 반올림
    return f"{x:10.1f}"


def analyze_config(gpu, kind, policies):
    config_name = f"cmp{gpu}_{kind}"
    config_dir = os.path.join(RAW_ROOT, config_name)
    if not os.path.isdir(config_dir):
        print(f"[skip] 디렉토리 없음: {config_dir}", file=sys.stderr)
        return None

    # policy -> group -> {n, median, p99}
    table = {}
    for pol in policies:
        groups = load_jobs(config_dir, pol)
        if groups is None:
            print(f"[skip] 파일 없음: {pol} @ {config_name}", file=sys.stderr)
            continue
        table[pol] = {}
        for g in GROUP_ORDER:
            vals = groups[g]
            table[pol][g] = {
                "n": len(vals),
                "median": median(vals),
                "p99": percentile(vals, 99),
            }
    return config_name, table


def print_config(config_name, table):
    print("=" * 92)
    print(f"구성: {config_name}   (큐 지연 queue_sec, 단위=초)")
    print("=" * 92)

    # 그룹별 표: 각 그룹마다 정책 행
    for g in GROUP_ORDER:
        print(f"\n  GPU 그룹 [{g}]")
        print(f"    {'policy':<12} {'n':>8} {'median(s)':>12} {'p99(s)':>14}")
        print(f"    {'-'*12} {'-'*8} {'-'*12} {'-'*14}")
        for pol in FOCUS_POLICIES:
            if pol not in table:
                continue
            cell = table[pol].get(g)
            if cell is None or cell["n"] == 0:
                print(f"    {pol:<12} {0:>8} {'n/a':>12} {'n/a':>14}")
                continue
            print(f"    {pol:<12} {cell['n']:>8} "
                  f"{cell['median']:>12.1f} {cell['p99']:>14.1f}")


def print_bigjob_summary(config_name, table):
    """8+ 그룹에 대한 비교 결론."""
    g = "8+"
    print(f"\n  >>> [{config_name}] 8-GPU(최대) 작업 큐 지연 비교 <<<")
    ref = {}
    for pol in FOCUS_POLICIES:
        if pol in table and table[pol].get(g) and table[pol][g]["n"] > 0:
            ref[pol] = table[pol][g]

    def get(pol, key):
        return ref[pol][key] if pol in ref else float("nan")

    print(f"    {'policy':<12} {'n':>7} {'median(s)':>12} {'p99(s)':>14}")
    for pol in FOCUS_POLICIES:
        if pol in ref:
            c = ref[pol]
            print(f"    {pol:<12} {c['n']:>7} {c['median']:>12.1f} {c['p99']:>14.1f}")
        else:
            print(f"    {pol:<12} {'--':>7} {'n/a':>12} {'n/a':>14}")

    # 비교 결론
    sa = ref.get("sfqa-auto")
    fi = ref.get("fifo")
    sj = ref.get("sjf")
    if not sa:
        print("    [결론 불가] sfqa-auto 데이터 없음")
        return

    lines = []
    for label, base in (("FIFO", fi), ("SJF", sj)):
        if not base:
            continue
        for metric in ("median", "p99"):
            bv = base[metric]
            sv = sa[metric]
            if bv == 0:
                ratio = float("inf") if sv > 0 else 1.0
            else:
                ratio = sv / bv
            direction = "더 굶음(악화)" if sv > bv else ("덜 굶음(완화)" if sv < bv else "동일")
            lines.append(
                f"    sfqa-auto {metric} = {sv:.1f}s  vs {label} {bv:.1f}s  "
                f"→ {ratio:.2f}x  [{direction}]")
    for ln in lines:
        print(ln)


def main():
    ap = argparse.ArgumentParser(description="N5 big-job starvation 검증")
    ap.add_argument("--gpu", default=None,
                    help="클러스터 GPU 규모 (예: 512). 미지정 시 512 기본.")
    ap.add_argument("--kind", default=None,
                    help="single 또는 hetero. 미지정 시 둘 다.")
    args = ap.parse_args()

    if args.gpu is None and args.kind is None:
        configs = [("512", "single"), ("512", "hetero")]
    else:
        gpus = [args.gpu] if args.gpu else ["512"]
        kinds = [args.kind] if args.kind else ["single", "hetero"]
        configs = [(g, k) for g in gpus for k in kinds]

    results = []
    for gpu, kind in configs:
        res = analyze_config(gpu, kind, FOCUS_POLICIES)
        if res:
            results.append(res)

    for config_name, table in results:
        print_config(config_name, table)

    print("\n" + "#" * 92)
    print("# 8-GPU(최대) 작업 그룹 핵심 비교 — 리뷰 N5")
    print("#" * 92)
    for config_name, table in results:
        print_bigjob_summary(config_name, table)
        print()


if __name__ == "__main__":
    main()
