"""병렬 워커가 남긴 _frag_<policy>.csv 들을 모아 각 구성의 summary.csv를 만든다.

사용: python3 par_merge.py [--results DIR] [--gpus 256,512,1024] [--kinds single,hetero]
fragment가 없는 정책은 기존 summary.csv 행을 보존한다(부분 재실행 호환).
"""
import argparse
import csv
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
COLS = ["policy", "n", "q_p50", "q_p90", "q_p99", "q_max",
        "sd_p50", "sd_p90", "sd_max", "alloc_max", "alloc_avg"]
ORDER = ["fifo", "sjf", "las", "kueue", "easy", "themis",
         "sfqa", "sfqa-auto", "fgd", "lucid", "sia"]


def merge_config(outdir):
    rows = {}
    # 기존 summary 보존(있으면)
    summ = os.path.join(outdir, "summary.csv")
    if os.path.exists(summ):
        with open(summ) as f:
            for r in csv.DictReader(f):
                rows[r["policy"]] = {k: r.get(k, "") for k in COLS}
    # fragment로 덮어쓰기(이번 실행분)
    n_frag = 0
    for frag in glob.glob(os.path.join(outdir, "_frag_*.csv")):
        with open(frag) as f:
            for r in csv.DictReader(f):
                rows[r["policy"]] = {k: r.get(k, "") for k in COLS}
                n_frag += 1
    ordered = sorted(rows.values(),
                     key=lambda r: ORDER.index(r["policy"]) if r["policy"] in ORDER else 99)
    with open(summ, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader()
        for r in ordered:
            w.writerow(r)
    print(f"  {os.path.basename(outdir)}: {len(ordered)} rows ({n_frag} from fragments)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(HERE, "sweep_results"))
    ap.add_argument("--gpus", default="256,512,1024")
    ap.add_argument("--kinds", default="single,hetero")
    ap.add_argument("--keep-frags", action="store_true")
    a = ap.parse_args()
    for gpu in a.gpus.split(","):
        for kind in a.kinds.split(","):
            outdir = os.path.join(a.results, f"cmp{gpu}_{kind}")
            if os.path.isdir(outdir):
                merge_config(outdir)
                if not a.keep_frags:
                    for frag in glob.glob(os.path.join(outdir, "_frag_*.csv")):
                        os.remove(frag)


if __name__ == "__main__":
    main()
