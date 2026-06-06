"""K8s 수명주기 오버헤드 측정 — 시뮬레이터 보정 파라미터용.

단계 분해(타임스탬프 소스):
  T0 Job 생성(job.metadata.creationTimestamp)
  T1 pod 생성(pod.metadata.creationTimestamp)          → Job컨트롤러 지연
  T2 PodScheduled 조건(lastTransitionTime)             → 스케줄링 지연
  T3 컨테이너 시작(containerStatuses.state.terminated.startedAt)  → 기동(이미지 캐시·런타임)
  T4 컨테이너 종료(terminated.finishedAt)              → 실행(=sleep 명목치와 비교→실행 오버헤드)
  T5 Job 완료(status.conditions Complete lastTransitionTime)      → 종료 북키핑

시나리오: ①단독 직렬 20개(1-GPU 10s) ②동시 8개 ③동시 24개(경합·큐 압력) ④8-GPU 5개 직렬
사용: /raid/squad/venv/bin/python measure_overheads.py --out /raid/squad/overheads
"""
import argparse
import csv
import os
import time

from kubernetes import client, config

NS = "squad"
IMG = "squad/holder:dev"


def k8s():
    config.load_kube_config()
    return client.CoreV1Api(), client.BatchV1Api()


def manifest(name, gpu, dur):
    return {
        "apiVersion": "batch/v1", "kind": "Job",
        "metadata": {"name": name, "namespace": NS, "labels": {"squad.io/ovh": "1"}},
        "spec": {"backoffLimit": 0, "template": {"metadata": {"labels": {"squad.io/ovh": "1"}},
            "spec": {"restartPolicy": "Never", "containers": [{
                "name": "wl", "image": IMG, "imagePullPolicy": "Never",
                "command": ["/holder"], "env": [{"name": "HOLD_SEC", "value": str(dur)}],
                "resources": {"limits": {"nvidia.com/gpu": str(gpu)}},
            }]}}},
    }


def wait_done(batch, names, timeout=600):
    deadline = time.time() + timeout
    while time.time() < deadline:
        jl = [j for j in batch.list_namespaced_job(NS, label_selector="squad.io/ovh=1").items
              if j.metadata.name in names]
        done = sum(1 for j in jl if (j.status.succeeded or 0) + (j.status.failed or 0) > 0)
        if done == len(names):
            return
        time.sleep(2)


def harvest(v1, batch, names, scenario, dur):
    jobs = {j.metadata.name: j for j in batch.list_namespaced_job(NS, label_selector="squad.io/ovh=1").items}
    rows = []
    for p in v1.list_namespaced_pod(NS, label_selector="squad.io/ovh=1").items:
        jn = (p.metadata.labels or {}).get("job-name")
        if jn not in names:
            continue
        j = jobs.get(jn)
        t0 = j.metadata.creation_timestamp if j else None
        t1 = p.metadata.creation_timestamp
        t2 = None
        for c in (p.status.conditions or []):
            if c.type == "PodScheduled" and c.status == "True":
                t2 = c.last_transition_time
        t3 = t4 = None
        if p.status.container_statuses:
            term = p.status.container_statuses[0].state.terminated
            if term:
                t3, t4 = term.started_at, term.finished_at
        t5 = None
        for c in (j.status.conditions or []) if j else []:
            if c.type == "Complete" and c.status == "True":
                t5 = c.last_transition_time
        if not all((t0, t1, t2, t3, t4)):
            continue
        rows.append({
            "scenario": scenario, "job": jn, "gpu": p.spec.containers[0].resources.limits["nvidia.com/gpu"],
            "jobctrl_s": (t1 - t0).total_seconds(),
            "sched_s": (t2 - t1).total_seconds(),
            "startup_s": (t3 - t2).total_seconds(),
            "exec_s": (t4 - t3).total_seconds(),
            "exec_ovh_s": (t4 - t3).total_seconds() - dur,
            "complete_s": (t5 - t4).total_seconds() if t5 else None,
        })
    return rows


def cleanup(batch):
    try:
        batch.delete_collection_namespaced_job(NS, label_selector="squad.io/ovh=1",
                                               propagation_policy="Background")
    except client.ApiException:
        pass
    time.sleep(6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/raid/squad/overheads")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    v1, batch = k8s()
    all_rows = []

    # ① 단독 직렬 20 (1-GPU, 10s)
    for i in range(20):
        nm = f"ovh-seq-{i}"
        batch.create_namespaced_job(NS, manifest(nm, 1, 10))
        wait_done(batch, [nm])
        all_rows += harvest(v1, batch, [nm], "seq1", 10)
        cleanup(batch)
        print(f"[seq] {i+1}/20", flush=True)

    # ② 동시 8 (1-GPU)
    names = [f"ovh-par8-{i}" for i in range(8)]
    for nm in names:
        batch.create_namespaced_job(NS, manifest(nm, 1, 10))
    wait_done(batch, names)
    all_rows += harvest(v1, batch, names, "par8", 10)
    cleanup(batch)
    print("[par8] done", flush=True)

    # ③ 동시 24 (1-GPU — 큐 압력: 8씩 3웨이브)
    names = [f"ovh-par24-{i}" for i in range(24)]
    for nm in names:
        batch.create_namespaced_job(NS, manifest(nm, 1, 10))
    wait_done(batch, names, timeout=900)
    all_rows += harvest(v1, batch, names, "par24", 10)
    cleanup(batch)
    print("[par24] done", flush=True)

    # ④ 8-GPU 직렬 5
    for i in range(5):
        nm = f"ovh-big-{i}"
        batch.create_namespaced_job(NS, manifest(nm, 8, 10))
        wait_done(batch, [nm])
        all_rows += harvest(v1, batch, [nm], "big8", 10)
        cleanup(batch)
        print(f"[big8] {i+1}/5", flush=True)

    with open(f"{args.out}/lifecycle.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader(); w.writerows(all_rows)

    # 요약
    import statistics as st
    print(f"\n{'시나리오':>7} {'단계':>10} {'p50':>7} {'p90':>7} {'max':>7}")
    for sc in ("seq1", "par8", "par24", "big8"):
        rs = [r for r in all_rows if r["scenario"] == sc]
        for k in ("jobctrl_s", "sched_s", "startup_s", "exec_ovh_s", "complete_s"):
            vs = sorted(r[k] for r in rs if r[k] is not None)
            if vs:
                print(f"{sc:>7} {k:>10} {vs[len(vs)//2]:>7.2f} {vs[int(len(vs)*.9)]:>7.2f} {vs[-1]:>7.2f}")
    print(f"→ {args.out}/lifecycle.csv")


if __name__ == "__main__":
    main()
