"""실측 오케스트레이터: 한 번 실행으로 워크로드 제출→메트릭 수집→완료 대기→JCT/큐잉 추출.

baseline(gate 없음, default-scheduler FIFO) vs SFQA(--sfqa, gate+컨트롤러)를 같은 트레이스로 비교.
SFQA 모드는 사전에 sfqa_controller.py 가 떠 있어야 한다(이 스크립트는 워크로드/측정만 담당).

예)
  # baseline
  python run_experiment.py --trace inhouse --input <csv> --limit 24 --kappa 400 --min-dur 30 \
      --run-id base
  # SFQA (별도 터미널에서 sfqa_controller.py 먼저 실행)
  python run_experiment.py ... --sfqa --run-id sfqa
"""
import argparse
import csv
import os
import random
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

K8S_REPLAY = "/home/mystous/gpu_scheduler/k8s_replay"
sys.path.insert(0, K8S_REPLAY)
from ingest import INGESTERS                       # noqa: E402
from normalize import NormalizeConfig, normalize, peak_demand  # noqa: E402
from model_assign import assign                    # noqa: E402
from emit import job_manifest                      # noqa: E402

from kubernetes import client, config              # noqa: E402

NS = "squad"
GPU = "nvidia.com/gpu"


def k8s():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api(), client.BatchV1Api()


def stratified_sample(jobs, n, seed=42):
    """전체 GPU 요청 개수 분포를 보존하며 n개 샘플.
    gpu_count 층별로 전체 비율대로 배분, 각 층 내 무작위 → duration(JCT) 분포도 자동 보존."""
    random.seed(seed)
    by = defaultdict(list)
    for j in jobs:
        by[j.gpu_count].append(j)
    tot = len(jobs)
    out = []
    for g, grp in by.items():
        k = max(1, round(n * len(grp) / tot))
        out.extend(random.sample(grp, min(k, len(grp))))
    random.shuffle(out)
    return out[:n]


def build(args):
    jobs = INGESTERS[args.trace](args.input, limit=args.limit)
    if args.sample > 0:
        before = len(jobs)
        jobs = stratified_sample(jobs, args.sample, args.seed)
        print(f"[run:{args.run_id}] 층화 샘플 {len(jobs)}/{before} (GPU·duration 분포 보존)", flush=True)
    cfg = NormalizeConfig(cluster_gpu_types=args.gpu_types.split(","),
                          kappa=args.kappa, min_duration_sec=args.min_dur,
                          max_duration_sec=args.max_dur)
    jobs = normalize(jobs, cfg)
    peak, _ = peak_demand(jobs)
    print(f"[run:{args.run_id}] {len(jobs)} jobs, peak {peak} GPU "
          f"({peak/args.total_gpu:.1f}× capacity)", flush=True)
    out = []
    for j in jobs:
        spec = assign(j, run_mode="holder")
        m = job_manifest(j, spec, "default-scheduler", namespace=NS, sfqa_gate=(args.policy != "none"))
        out.append((j.arrival_time, m))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", required=True, choices=list(INGESTERS))
    ap.add_argument("--input", required=True)
    ap.add_argument("--limit", type=int, default=0, help="앞 N개(0=무제한). 보통 --sample 사용")
    ap.add_argument("--sample", type=int, default=0, help="전체에서 분포보존 층화 샘플 N개")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--kappa", type=float, default=400.0)
    ap.add_argument("--min-dur", type=float, default=30.0)
    ap.add_argument("--max-dur", type=float, default=90.0, help="압축 후 duration 상한(초). 실험 시간 제한")
    ap.add_argument("--gpu-types", default="NVIDIA-B200")
    ap.add_argument("--total-gpu", type=int, default=8)
    ap.add_argument("--policy", default="none",
                    choices=["none", "fifo", "sjf", "priority", "las", "sfqa"],
                    help="none=gate 없음(순수 default FIFO). 나머지는 gate+policy_controller 필요")
    ap.add_argument("--run-id", default="run")
    ap.add_argument("--timeout", type=float, default=1800)
    ap.add_argument("--submit-clamp", type=float, default=5.0,
                    help="제출 간 최대 대기(초). 0=클램프 없음(arrival 충실 재현, 버스트 경합 보존)")
    args = ap.parse_args()

    outdir = f"/raid/squad/runs/{args.run_id}"
    os.makedirs(outdir, exist_ok=True)
    v1, batch = k8s()
    manifests = build(args)

    # 메트릭 수집기 시작
    mc = subprocess.Popen(
        ["/raid/squad/venv/bin/python",
         "/home/mystous/gpu_scheduler/squad_ctrl/metrics_collector.py",
         "--out", f"{outdir}/metrics.csv", "--period", "3", "--total-gpu", str(args.total_gpu)],
        env={**os.environ, "KUBECONFIG": "/home/mystous/.kube/config"})

    # arrival 타이밍대로 제출
    t0 = time.time()
    submit_log = open(f"{outdir}/submit_log.csv", "w", newline="")
    sw = csv.writer(submit_log); sw.writerow(["job", "arrival", "wall"])
    names = []
    for at, m in manifests:
        wait = at - (time.time() - t0)
        if wait > 0:
            time.sleep(wait if args.submit_clamp <= 0 else min(wait, args.submit_clamp))
        try:
            batch.create_namespaced_job(NS, m)
            names.append(m["metadata"]["name"])
            sw.writerow([m["metadata"]["name"], round(at, 1), round(time.time() - t0, 1)])
            submit_log.flush()
        except client.ApiException as e:
            print(f"  제출 실패 {m['metadata']['name']}: {e.status}", flush=True)
    print(f"[run:{args.run_id}] {len(names)} jobs 제출 완료, 완료 대기...", flush=True)

    # 모든 Job 완료 대기
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        jl = batch.list_namespaced_job(NS).items
        active = [j for j in jl if (j.status.succeeded or 0) + (j.status.failed or 0) == 0]
        if not active:
            break
        time.sleep(5)
    print(f"[run:{args.run_id}] 완료. JCT/큐잉 추출...", flush=True)
    mc.terminate()

    # pod lifecycle → JCT·큐잉
    rows = []
    for p in v1.list_namespaced_pod(NS).items:
        created = p.metadata.creation_timestamp
        started = p.status.start_time
        finished = None
        if p.status.container_statuses:
            term = p.status.container_statuses[0].state.terminated
            if term:
                finished = term.finished_at
        if not created:
            continue
        queue = (started - created).total_seconds() if started else None
        jct = (finished - created).total_seconds() if finished else None
        rows.append([p.metadata.name, queue, jct])
    with open(f"{outdir}/jct.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["pod", "queue_sec", "jct_sec"])
        w.writerows(rows)

    qs = sorted(r[1] for r in rows if r[1] is not None)
    js = sorted(r[2] for r in rows if r[2] is not None)

    def pct(a, p):
        return a[min(len(a) - 1, int(len(a) * p))] if a else 0

    print(f"\n===== {args.run_id} (policy={args.policy}) =====")
    print(f"  jobs={len(rows)} 완료={len(js)}")
    print(f"  큐잉지연(s) p50={pct(qs,.5):.1f} p90={pct(qs,.9):.1f} max={qs[-1] if qs else 0:.1f}")
    print(f"  JCT(s)      p50={pct(js,.5):.1f} p90={pct(js,.9):.1f} max={js[-1] if js else 0:.1f}")
    print(f"  결과: {outdir}/", flush=True)


if __name__ == "__main__":
    main()
