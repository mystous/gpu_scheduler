"""PTR 디프래그 컨트롤러 (Python).

주기적으로 GPU 슬롯 모델을 만들어 Defrag(DP)로 "완전히 빈 server 수"를 최대화하는 이주 계획을
구하고, 선점 가능 Pod 를 evict→재생성(resume)하며 실제 이주 다운타임을 측정한다(/raid/squad/runs).
멀티노드·이종 일반화(server=노드, 동일 GPU 타입 간 이주). 단일 노드면 이주 대상이 없어 무동작.
알고리즘은 squad_algo(Go 코어와 동일, 검증됨).

실행(호스트): /raid/squad/venv/bin/python ptr_controller.py --period 15 --omega 20 --dp-max 100000
"""
import argparse
import csv
import os
import time
from datetime import datetime, timezone

from kubernetes import client, config

from squad_algo import Server, RunningJob, Slot, Defrag, DEFAULT_DP_EXECUTION_MAX, DEFAULT_DEFRAG_CRITERIA

GPU = "nvidia.com/gpu"
GPU_PRODUCT = "nvidia.com/gpu.product"
PREEMPTIBLE = "squad.io/preemptible"
JOB_ID = "squad.io/job-id"
MIG_LOG = "/raid/squad/runs/migration_log.csv"


def load():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api()


def pod_gpu(p) -> int:
    t = 0
    for c in p.spec.containers:
        lim = (c.resources.limits or {}) if c.resources else {}
        if GPU in lim:
            t += int(str(lim[GPU]))
    return t


def build_model(nodes, pods, flavor):
    """flavor 노드 → Server 슬롯 모델 + 선점가능 Running Pod → RunningJob 후보.
    C++ reconstruct_server_status / Go buildModel 의 포팅."""
    idx, servers = {}, []
    for n in nodes:
        if (n.metadata.labels or {}).get(GPU_PRODUCT, "any") != flavor:
            continue
        total = min(8, int(str((n.status.allocatable or {}).get(GPU, "0"))))
        idx[n.metadata.name] = len(servers)
        servers.append(Server(name=n.metadata.name, gpu_type=flavor, total=total))

    jobs, cursor = [], {}
    pod_by_id = {}
    for p in pods:
        if not p.spec.node_name or p.status.phase != "Running":
            continue
        si = idx.get(p.spec.node_name)
        if si is None:
            continue
        g = pod_gpu(p)
        if g == 0:
            continue
        preempt = (p.metadata.labels or {}).get(PREEMPTIBLE) == "true"
        jid = (p.metadata.labels or {}).get(JOB_ID, p.metadata.name)
        start = cursor.get(p.spec.node_name, 0)
        for k in range(g):
            if start + k < servers[si].total:
                servers[si].slots[start + k] = Slot.FLOATING if preempt else Slot.FIXED
                servers[si].job_ids[start + k] = jid
        cursor[p.spec.node_name] = start + g
        if preempt and g < servers[si].total:  # whole-server 미점유 선점 job 만 후보
            jobs.append(RunningJob(jid, g, flavor, server_index=si, target_index=-1, preemptible=True))
            pod_by_id[jid] = p

    for s in servers:
        for k in range(s.total):
            if s.slots[k] == Slot.NONE:
                s.slots[k] = Slot.EMPTY
    return servers, jobs, pod_by_id


class PTR:
    def __init__(self, v1, omega, dp_max):
        self.v1 = v1
        self.omega = omega
        self.dp_max = dp_max
        self.last_sched = 0
        os.makedirs(os.path.dirname(MIG_LOG), exist_ok=True)
        if not os.path.exists(MIG_LOG):
            with open(MIG_LOG, "w", newline="") as f:
                csv.writer(f).writerow(["ts", "job", "flavor", "target_node", "evict_sec", "total_sec"])

    def reconcile(self):
        nodes = self.v1.list_node().items
        pods = self.v1.list_pod_for_all_namespaces().items

        pending = sum(1 for p in pods if pod_gpu(p) and not p.spec.node_name and p.status.phase == "Pending")
        scheduled = sum(1 for p in pods if p.spec.node_name and p.status.phase == "Running" and pod_gpu(p))
        do_defrag = scheduled != self.last_sched
        self.last_sched = scheduled
        if pending < self.omega or not do_defrag:      # ω 게이트 + do_defragmentation
            return

        flavors = {(n.metadata.labels or {}).get(GPU_PRODUCT, "any") for n in nodes}
        for f in flavors:
            servers, jobs, pod_by_id = build_model(nodes, pods, f)
            if not jobs:
                continue
            improved, plan, before, after = Defrag(servers, jobs, self.dp_max).run()
            if not improved:
                continue
            print(f"[ptr] {f}: empty server {before}→{after}, 이주 실행", flush=True)
            self.execute(plan, servers, pod_by_id, f)

    def execute(self, plan, servers, pod_by_id, flavor):
        for j in plan:
            if j.target_index < 0:
                continue
            pod = pod_by_id.get(j.id)
            if pod is None:
                continue
            target = servers[j.target_index].name
            t0 = time.time()
            # 1) evict: 삭제(holder/train_stub 는 CKPT_PATH 에 경과를 기록 중 → resume 가능)
            try:
                self.v1.delete_namespaced_pod(pod.metadata.name, pod.metadata.namespace,
                                              grace_period_seconds=10)
            except client.ApiException:
                pass
            t_evict = time.time()
            # 2) 재생성: 타겟 노드 고정 → resume
            self.v1.create_namespaced_pod(pod.metadata.namespace, self._rebuild(pod, target))
            total = time.time() - t0
            with open(MIG_LOG, "a", newline="") as fh:
                csv.writer(fh).writerow([datetime.now(timezone.utc).isoformat(), j.id, flavor,
                                         target, round(t_evict - t0, 2), round(total, 2)])
            print(f"[ptr] 이주 {j.id} → {target}: evict={t_evict-t0:.1f}s total={total:.1f}s", flush=True)

    @staticmethod
    def _rebuild(old, target_node):
        spec = client.ApiClient().sanitize_for_serialization(old.spec)
        spec["nodeName"] = target_node
        spec.pop("schedulingGates", None)
        return client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=old.metadata.name + "-m",
                namespace=old.metadata.namespace,
                labels=old.metadata.labels,
                annotations=old.metadata.annotations,
            ),
            spec=spec,
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", type=float, default=15.0)
    ap.add_argument("--omega", type=int, default=DEFAULT_DEFRAG_CRITERIA)
    ap.add_argument("--dp-max", type=int, default=DEFAULT_DP_EXECUTION_MAX)
    args = ap.parse_args()
    v1 = load()
    ptr = PTR(v1, args.omega, args.dp_max)
    print(f"[ptr] start period={args.period}s ω={args.omega} δ={args.dp_max}", flush=True)
    while True:
        try:
            ptr.reconcile()
        except Exception as e:  # noqa
            print(f"[ptr] reconcile err: {e}", flush=True)
        time.sleep(args.period)


if __name__ == "__main__":
    main()
