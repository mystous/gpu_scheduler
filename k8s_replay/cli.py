"""SQUAD 트레이스 재생 CLI.

파이프라인: ingest(트레이스) → normalize(타입매핑·시간압축) → [dry-run: peak demand 보고]
            → emit(K8s Job JSON) → [--submit: arrival 순서대로 kubectl apply].

예)
  # κ 선택용 dry-run (peak 동시 GPU 수요가 capacity 1.5~3배 되도록 κ 조정)
  python cli.py --trace alibaba2023 --input <pod_csv> --kappa 240 --dry-run
  # 매니페스트 생성(holder 스텁, squad-scheduler 대상)
  python cli.py --trace inhouse --input <job_flow_csv> --run-mode holder \
                --scheduler squad-scheduler --out /raid/squad/runs/s1
  # 실제 제출(arrival 타이밍대로)
  python cli.py ... --out /raid/squad/runs/s1 --submit
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import time

from ingest import INGESTERS
from normalize import NormalizeConfig, normalize, peak_demand
from model_assign import assign
from emit import job_manifest
from common import write_normalized_csv


def build_manifests(jobs, run_mode, scheduler, namespace, sfqa=False):
    out = []
    for j in jobs:
        spec = assign(j, run_mode=run_mode)
        m = job_manifest(j, spec, scheduler, namespace=namespace, sfqa_gate=sfqa)
        out.append((j.arrival_time, m))
    return out


def submit_by_arrival(manifests, out_dir, capacity=8):
    """arrival_time(압축 후 초) 순서대로 kubectl apply. 동시 수요>capacity면 Pending 발생."""
    log_path = os.path.join(out_dir, "submit_log.csv")
    with open(log_path, "w") as log:
        log.write("idx,job,arrival_sec,submit_wall\n")
        t_start = time.time()
        for i, (at, m) in enumerate(manifests):
            wait = at - (time.time() - t_start)
            if wait > 0:
                time.sleep(wait)
            path = os.path.join(out_dir, f"{i:05d}_{m['metadata']['name']}.json")
            with open(path, "w") as f:
                json.dump(m, f)
            subprocess.run(["kubectl", "apply", "-f", path], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log.write(f"{i},{m['metadata']['name']},{at:.1f},{time.time()-t_start:.1f}\n")
            log.flush()
    print(f"제출 완료: {len(manifests)} jobs → {log_path}")


def main():
    ap = argparse.ArgumentParser(description="SQUAD trace replay")
    ap.add_argument("--trace", required=True, choices=list(INGESTERS))
    ap.add_argument("--input", required=True, help="트레이스 파일 경로")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--kappa", type=float, default=240.0, help="시간압축 계수(arrival·duration /κ)")
    ap.add_argument("--min-dur", type=float, default=90.0, help="압축 후 최소 duration(초)")
    ap.add_argument("--max-dur", type=float, default=0.0, help="압축 후 최대 duration(초). 0=무제한")
    ap.add_argument("--cluster-gpu-types", default="b200", help="콤마구분 타겟 GPU 타입 풀")
    ap.add_argument("--scheduler", default="default-scheduler",
                    help="기본 default-scheduler. SFQA 는 schedulingGate+컨트롤러로 동작")
    ap.add_argument("--sfqa", action="store_true",
                    help="SUT: 각 Job 에 SFQA schedulingGate 부여(컨트롤러가 P* 순 해제)")
    ap.add_argument("--namespace", default="squad")
    ap.add_argument("--run-mode", default="holder", choices=["holder", "real"])
    ap.add_argument("--capacity", type=int, default=8, help="클러스터 총 GPU 수(peak 비교용)")
    ap.add_argument("--out", default="/raid/squad/runs/run1")
    ap.add_argument("--dry-run", action="store_true", help="제출 없이 peak demand만 보고")
    ap.add_argument("--submit", action="store_true", help="arrival 순서대로 kubectl apply")
    args = ap.parse_args()

    print(f"[ingest] {args.trace} ← {args.input}")
    jobs = INGESTERS[args.trace](args.input, limit=args.limit)
    print(f"[ingest] {len(jobs)} jobs")

    cfg = NormalizeConfig(cluster_gpu_types=args.cluster_gpu_types.split(","), kappa=args.kappa,
                          min_duration_sec=args.min_dur, max_duration_sec=args.max_dur)
    jobs = normalize(jobs, cfg)
    if not jobs:
        print("정규화 후 job 0개 — 입력/필터 확인")
        return

    peak, peak_t = peak_demand(jobs)
    span = max(j.arrival_time + j.duration for j in jobs)
    ratio = peak / max(1, args.capacity)
    print(f"[normalize] {len(jobs)} jobs, 실험 길이 ~{span/3600:.2f}h, "
          f"peak 동시 GPU 수요={peak} ({ratio:.1f}× capacity={args.capacity}) @ t={peak_t:.0f}s")
    if ratio < 1.5:
        print("  ⚠ peak<1.5× capacity: 경합 약함 → κ를 키워(압축↑) 도착 밀도를 높이세요")
    elif ratio > 3:
        print("  ⚠ peak>3× capacity: 과포화 → κ를 줄이세요")

    os.makedirs(args.out, exist_ok=True)
    write_normalized_csv(jobs, os.path.join(args.out, "normalized.csv"))

    if args.dry_run:
        print(f"[dry-run] normalized.csv 저장. 제출 생략.")
        return

    manifests = build_manifests(jobs, args.run_mode, args.scheduler, args.namespace, sfqa=args.sfqa)
    for i, (_, m) in enumerate(manifests):
        with open(os.path.join(args.out, f"{i:05d}_{m['metadata']['name']}.json"), "w") as f:
            json.dump(m, f)
    print(f"[emit] {len(manifests)} 매니페스트 → {args.out}")

    if args.submit:
        submit_by_arrival(manifests, args.out, capacity=args.capacity)


if __name__ == "__main__":
    main()
