"""SFQA 컨트롤러 (PodSchedulingGates 방식).

커스텀 kube-scheduler 플러그인 대신, 대기 Pod 에 schedulingGate("squad.io/sfqa")를 두고
이 컨트롤러가 P* 높은 순으로 gate 를 해제하면 기본 kube-scheduler 가 그 순서대로 스케줄한다.
→ Go 스케줄러 빌드 불필요(방화벽 우회), R1/R2 자연 해결(클러스터 상태는 컨트롤러가 봄).

알고리즘은 squad_algo(Go 코어와 동일, 검증됨). 하드웨어 비종속(노드 라벨 gpu.product 로 flavor).
실행(호스트): /raid/squad/venv/bin/python sfqa_controller.py --period 10 --alpha 0.13889 --beta 80
"""
import argparse
import time
from datetime import datetime, timezone

from kubernetes import client, config

from squad_algo import Server, PendingJob, Params, Slot, reorder_queue

GPU = "nvidia.com/gpu"
GPU_PRODUCT = "nvidia.com/gpu.product"
GATE = "squad.io/sfqa"
AGE_ANNO = "squad.io/age"
AGE_UPDATED = "squad.io/age-updated"
FLAVOR_LBL = "squad.io/gpu-type"
AGE_STEP_MIN = 10  # "10분 = +1"


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


def has_gate(p) -> bool:
    gates = p.spec.scheduling_gates or []
    return any(g.name == GATE for g in gates)


def build_servers(nodes, pods, flavor):
    used = {}
    for p in pods:
        if p.spec.node_name and p.status.phase not in ("Succeeded", "Failed"):
            used[p.spec.node_name] = used.get(p.spec.node_name, 0) + pod_gpu(p)
    servers = []
    for n in nodes:
        if (n.metadata.labels or {}).get(GPU_PRODUCT, "any") != flavor:
            continue
        total = int(str((n.status.allocatable or {}).get(GPU, "0")))
        total = min(total, 8)
        s = Server(name=n.metadata.name, gpu_type=flavor, total=total)
        u = used.get(n.metadata.name, 0)
        for j in range(total):
            s.slots[j] = Slot.FIXED if j < u else Slot.EMPTY
        servers.append(s)
    return servers


class SFQA:
    def __init__(self, v1, params):
        self.v1 = v1
        self.params = params
        self.prev_pending = {}  # flavor -> set(podkey)

    def advance_age(self, p, scheduled_in_flavor) -> int:
        anno = p.metadata.annotations or {}
        age = int(anno.get(AGE_ANNO, "0"))
        now = datetime.now(timezone.utc)
        if scheduled_in_flavor:
            age = 0
        elif AGE_UPDATED in anno:
            try:
                t0 = datetime.fromisoformat(anno[AGE_UPDATED])
                age += int((now - t0).total_seconds() // 60) // AGE_STEP_MIN
            except ValueError:
                pass
        self._patch(p, {"metadata": {"annotations": {
            AGE_ANNO: str(age), AGE_UPDATED: now.isoformat()}}})
        return age

    def ungate(self, p):
        # schedulingGates 제거는 strategic merge 로 안 됨(빈 리스트 무시) → JSON patch 사용.
        keep = [{"name": g.name} for g in (p.spec.scheduling_gates or []) if g.name != GATE]
        op = ([{"op": "replace", "path": "/spec/schedulingGates", "value": keep}] if keep
              else [{"op": "remove", "path": "/spec/schedulingGates"}])
        try:
            self.v1.patch_namespaced_pod(p.metadata.name, p.metadata.namespace, op)
        except client.ApiException:
            pass

    def _patch(self, p, body):
        try:
            self.v1.patch_namespaced_pod(p.metadata.name, p.metadata.namespace, body)
        except client.ApiException:
            pass

    def reconcile(self):
        nodes = self.v1.list_node().items
        pods = self.v1.list_pod_for_all_namespaces().items

        alloc, used = {}, {}
        for n in nodes:
            f = (n.metadata.labels or {}).get(GPU_PRODUCT, "any")
            alloc[f] = alloc.get(f, 0) + int(str((n.status.allocatable or {}).get(GPU, "0")))
        node_flavor = {n.metadata.name: (n.metadata.labels or {}).get(GPU_PRODUCT, "any") for n in nodes}

        pending = {}  # flavor -> [pod]
        for p in pods:
            g = pod_gpu(p)
            if g == 0:
                continue
            if p.spec.node_name and p.status.phase not in ("Succeeded", "Failed"):
                f = node_flavor.get(p.spec.node_name, "any")
                used[f] = used.get(f, 0) + g
            elif has_gate(p) and p.status.phase == "Pending":
                f = (p.metadata.labels or {}).get(FLAVOR_LBL, "any")
                pending.setdefault(f, []).append(p)

        for f, pods_f in pending.items():
            total = alloc.get(f, 0)
            ar = (used.get(f, 0) / total * 100) if total else 0.0
            servers = build_servers(nodes, pods, f)

            cur = {f"{p.metadata.namespace}/{p.metadata.name}" for p in pods_f}
            scheduled = any(k not in cur for k in self.prev_pending.get(f, set()))
            self.prev_pending[f] = cur

            jobs, by_key = [], {}
            for p in pods_f:
                k = f"{p.metadata.namespace}/{p.metadata.name}"
                by_key[k] = p
                jobs.append(PendingJob(k, pod_gpu(p), f, age=self.advance_age(p, scheduled)))

            ordered = reorder_queue(jobs, servers, f, self.params, ar)
            free = max(0, total - used.get(f, 0))
            for j in ordered:                       # P* 높은 순
                if j.gpu_count <= free:
                    self.ungate(by_key[j.id])       # gate 해제 → 스케줄 가능
                    free -= j.gpu_count
                # 안 맞으면 남겨 다음 reconcile (큐 앞 유지)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", type=float, default=10.0)
    ap.add_argument("--alpha", type=float, default=0.13889)
    ap.add_argument("--beta", type=float, default=80.0)
    args = ap.parse_args()
    v1 = load()
    sfqa = SFQA(v1, Params(alpha=args.alpha, beta=args.beta, prevent_starv=True))
    print(f"[sfqa] start period={args.period}s α={args.alpha} β={args.beta}", flush=True)
    while True:
        try:
            sfqa.reconcile()
        except Exception as e:  # noqa
            print(f"[sfqa] reconcile err: {e}", flush=True)
        time.sleep(args.period)


if __name__ == "__main__":
    main()
