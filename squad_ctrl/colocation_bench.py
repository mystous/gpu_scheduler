"""콜로케이션 간섭 측정 (리젝 ① '메모리 경합 미측정' 대응).

같은 노드에서 GPU-점유 학습형 잡(실제 연산: bf16 matmul + HBM 대역폭 커널)을
1개(solo) → N개(packed, GPU당 1개) 동시 실행해 per-job throughput 저하율을 측정.
PTR 디프래그가 잡을 한 서버로 모을 때(콜로케이션) 발생하는 간섭의 실측 근거.

이미지: kind 노드 캐시 vllm_hybrid(torch 2.11+cu128) — 방화벽 무관.
사용: /raid/squad/venv/bin/python colocation_bench.py --counts 1,2,4,8 --out /raid/squad/colocation
"""
import argparse
import csv
import os
import re
import time

from kubernetes import client, config

NS = "squad"
IMAGE = "localhost/mystous/vllm_hybrid:v1.9-claudeworks"
PY = "/workspace/vllm_dev_prj/bin/python"

BENCH = r"""
import torch, time
torch.cuda.init()
dev = torch.device('cuda')
# 1) compute-bound: bf16 matmul
d = 8192
a = torch.randn(d, d, device=dev, dtype=torch.bfloat16)
b = torch.randn(d, d, device=dev, dtype=torch.bfloat16)
for _ in range(10):
    c = a @ b
torch.cuda.synchronize()
t0 = time.time(); n = 400
for _ in range(n):
    c = a @ b
torch.cuda.synchronize()
dt = time.time() - t0
print(f"COMPUTE tflops={2*d**3*n/dt/1e12:.2f}", flush=True)
# 2) bandwidth-bound: 대형 elementwise (HBM 왕복)
m = 1 << 28  # 256M elem bf16 = 512MB/tensor
x = torch.randn(m, device=dev, dtype=torch.bfloat16)
y = torch.randn(m, device=dev, dtype=torch.bfloat16)
for _ in range(5):
    z = x + y
torch.cuda.synchronize()
t0 = time.time(); k = 200
for _ in range(k):
    z = x + y
torch.cuda.synchronize()
dt = time.time() - t0
print(f"BANDWIDTH gbps={3*m*2*k/dt/1e9:.1f}", flush=True)
"""


def k8s():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api(), client.BatchV1Api()


def job_manifest(name):
    return {
        "apiVersion": "batch/v1", "kind": "Job",
        "metadata": {"name": name, "namespace": NS, "labels": {"squad.io/colo": "1"}},
        "spec": {"backoffLimit": 0, "template": {"spec": {
            "restartPolicy": "Never",
            "containers": [{
                "name": "bench", "image": IMAGE, "imagePullPolicy": "Never",
                "command": [PY, "-c", BENCH],
                "resources": {"limits": {"nvidia.com/gpu": "1"}},
            }],
        }}},
    }


def run_round(v1, batch, n, timeout=900):
    names = [f"colo-{n}-{i}" for i in range(n)]
    for nm in names:
        batch.create_namespaced_job(NS, job_manifest(nm))
    deadline = time.time() + timeout
    while time.time() < deadline:
        jl = [j for j in batch.list_namespaced_job(NS).items if j.metadata.name in names]
        done = sum(1 for j in jl if (j.status.succeeded or 0) > 0)
        fail = sum(1 for j in jl if (j.status.failed or 0) > 0)
        if done + fail == n:
            break
        time.sleep(5)
    rows = []
    for p in v1.list_namespaced_pod(NS, label_selector="squad.io/colo=1").items:
        if not any(p.metadata.name.startswith(nm) for nm in names):
            continue
        try:
            log = v1.read_namespaced_pod_log(p.metadata.name, NS)
        except client.ApiException:
            log = ""
        tf = re.search(r"COMPUTE tflops=([\d.]+)", log)
        bw = re.search(r"BANDWIDTH gbps=([\d.]+)", log)
        rows.append({"concurrency": n, "pod": p.metadata.name,
                     "tflops": float(tf.group(1)) if tf else None,
                     "gbps": float(bw.group(1)) if bw else None})
    for nm in names:
        try:
            batch.delete_namespaced_job(NS, nm, propagation_policy="Background")
        except client.ApiException:
            pass
    time.sleep(8)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--counts", default="1,2,4,8")
    ap.add_argument("--out", default="/raid/squad/colocation")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    v1, batch = k8s()
    all_rows = []
    for n in [int(x) for x in args.counts.split(",")]:
        print(f"[colo] concurrency={n} 시작", flush=True)
        rows = run_round(v1, batch, n)
        ok = [r for r in rows if r["tflops"]]
        if ok:
            mt = sum(r["tflops"] for r in ok) / len(ok)
            mb = sum(r["gbps"] for r in ok if r["gbps"]) / max(1, len([r for r in ok if r["gbps"]]))
            print(f"[colo] n={n}: tflops/job={mt:.1f}, gbps/job={mb:.0f} ({len(ok)}/{n} 성공)", flush=True)
        all_rows.extend(rows)
    with open(f"{args.out}/colocation.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["concurrency", "pod", "tflops", "gbps"])
        w.writeheader(); w.writerows(all_rows)
    print(f"[colo] 결과 → {args.out}/colocation.csv", flush=True)


if __name__ == "__main__":
    main()
