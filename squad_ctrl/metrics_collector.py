"""경량 메트릭 수집기 — Prometheus 대체(quay.io/nvcr.io CDN 차단 우회).

호스트 nvidia-smi(GPU util/mem) + K8s API(할당률·pending/running)를 주기 폴링해 CSV 시계열로 저장.
JCT·큐잉지연은 실측 후 analyze_run.py 가 pod lifecycle 에서 추출한다.
실행(호스트): /raid/squad/venv/bin/python metrics_collector.py --out /raid/squad/runs/<run>/metrics.csv
"""
import argparse
import csv
import subprocess
import time
from datetime import datetime, timezone

from kubernetes import client, config

GPU = "nvidia.com/gpu"


def gpu_stats():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return 0.0, 0.0, 0
    utils, mems = [], []
    for line in out.strip().splitlines():
        try:
            u, m = line.split(",")
            utils.append(float(u)); mems.append(float(m))
        except ValueError:
            pass
    n = len(utils) or 1
    return sum(utils) / n, sum(mems), len(utils)


def pod_gpu(p):
    t = 0
    for c in p.spec.containers:
        lim = (c.resources.limits or {}) if c.resources else {}
        if GPU in lim:
            t += int(str(lim[GPU]))
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/raid/squad/runs/metrics.csv")
    ap.add_argument("--period", type=float, default=5.0)
    ap.add_argument("--total-gpu", type=int, default=8)
    args = ap.parse_args()
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    v1 = client.CoreV1Api()

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "gpu_util_avg", "gpu_mem_used_mib", "n_gpu",
                    "alloc_used", "alloc_pct", "pending_gpu_pods", "running_gpu_pods"])
        print(f"[metrics] → {args.out} (period {args.period}s)", flush=True)
        while True:
            util, mem, ngpu = gpu_stats()
            try:
                pods = v1.list_pod_for_all_namespaces().items
            except Exception:
                pods = []
            used = pending = running = 0
            for p in pods:
                g = pod_gpu(p)
                if g == 0:
                    continue
                if p.spec.node_name and p.status.phase == "Running":
                    used += g; running += 1
                elif p.status.phase == "Pending":
                    pending += 1
            w.writerow([datetime.now(timezone.utc).isoformat(), round(util, 1), round(mem, 0),
                        ngpu, used, round(used / args.total_gpu * 100, 1), pending, running])
            f.flush()
            time.sleep(args.period)


if __name__ == "__main__":
    main()
