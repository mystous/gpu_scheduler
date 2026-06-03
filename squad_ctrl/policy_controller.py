"""다정책 gate 컨트롤러 — gate 해제 순서를 정책별로 바꿔 여러 스케줄러를 공정 비교한다.

동일 K8s 프레임워크(schedulingGate + 기본 kube-scheduler) 위에서 --policy 만 바꾸면
서로 다른 스케줄링 정책이 된다. baseline(gate 없음, 순수 default FIFO)과 별개로,
gate 기반 FIFO/SJF/Priority/LAS/SFQA 를 같은 오버헤드 조건에서 비교한다(리젝 ③ 대응).

정책:
  fifo     — pod 생성시각 순(오래된 것 먼저)
  sjf      — squad.io/duration 짧은 것 먼저 (JCT 최소화, starvation 유발)
  priority — squad.io/priority 높은 것 먼저
  las      — least-attained-service(받은 GPU-time 적은 것 먼저, Tiresias 근사)
  sfqa     — P* = P + α·A·R (starvation 방지)

실행(호스트): /raid/squad/venv/bin/python policy_controller.py --policy sjf --period 5
"""
import argparse
import time
from datetime import datetime, timezone

from kubernetes import client, config

from squad_algo import Server, PendingJob, Params, Slot, reorder_queue

GPU = "nvidia.com/gpu"
GPU_PRODUCT = "nvidia.com/gpu.product"
GATE = "squad.io/sfqa"
FLAVOR_LBL = "squad.io/gpu-type"
DUR_LBL = "squad.io/duration"
PRIO_LBL = "squad.io/priority"
AGE_ANNO = "squad.io/age"
AGE_UPDATED = "squad.io/age-updated"
AGE_STEP_MIN = 10


def load():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api()


def pod_gpu(p):
    t = 0
    for c in p.spec.containers:
        lim = (c.resources.limits or {}) if c.resources else {}
        if GPU in lim:
            t += int(str(lim[GPU]))
    return t


def has_gate(p):
    return any(g.name == GATE for g in (p.spec.scheduling_gates or []))


def lbl(p, k, d="0"):
    return (p.metadata.labels or {}).get(k, d)


def key(p):
    return f"{p.metadata.namespace}/{p.metadata.name}"


def build_servers(nodes, pods, flavor):
    used = {}
    for p in pods:
        if p.spec.node_name and p.status.phase not in ("Succeeded", "Failed"):
            used[p.spec.node_name] = used.get(p.spec.node_name, 0) + pod_gpu(p)
    servers = []
    for n in nodes:
        if (n.metadata.labels or {}).get(GPU_PRODUCT, "any") != flavor:
            continue
        total = min(8, int(str((n.status.allocatable or {}).get(GPU, "0"))))
        s = Server(name=n.metadata.name, gpu_type=flavor, total=total)
        u = used.get(n.metadata.name, 0)
        for j in range(total):
            s.slots[j] = Slot.FIXED if j < u else Slot.EMPTY
        servers.append(s)
    return servers


class PolicyCtrl:
    def __init__(self, v1, policy, params, period, age_unit):
        self.v1 = v1
        self.policy = policy
        self.params = params
        self.period = period
        self.age_unit = age_unit  # age 1 증가에 필요한 대기 초(실측 스케일에 맞춤)
        self.attained = {}  # LAS: job_key -> 누적 GPU-second

    def age_of(self, p):
        """age = pending 대기 시간(now - creationTimestamp) / age_unit.
        대기 중인 동안 자동 증가하고, 스케줄되면 pending 집합에서 빠지며 자연 리셋된다.
        (원래 'AGE_STEP_MIN=10분=+1'은 원본 트레이스의 실제 시간 스케일이라, 시간압축한
        실측에선 큐잉이 초~분 단위여서 age 가 0 에 머무는 버그였다. → 실측 대기시간 기반으로 수정.)"""
        created = p.metadata.creation_timestamp
        if created is None:
            return 0
        wait = (datetime.now(timezone.utc) - created).total_seconds()
        return int(wait / self.age_unit)

    def order(self, gated, servers, ar, flavor):
        """정책별 gate 해제 순서(앞이 먼저)."""
        if self.policy == "sfqa":
            by_key = {key(p): p for p in gated}
            jobs = [PendingJob(key(p), pod_gpu(p), flavor, age=self.age_of(p))
                    for p in gated]
            ordered = reorder_queue(jobs, servers, flavor, self.params, ar)
            return [by_key[j.id] for j in ordered]
        if self.policy == "sjf":
            return sorted(gated, key=lambda p: int(lbl(p, DUR_LBL)))
        if self.policy == "priority":
            return sorted(gated, key=lambda p: -int(lbl(p, PRIO_LBL)))
        if self.policy == "las":
            return sorted(gated, key=lambda p: self.attained.get(key(p), 0.0))
        # fifo (기본): 생성시각 순
        return sorted(gated, key=lambda p: p.metadata.creation_timestamp)

    def ungate(self, p):
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
        node_flavor = {}
        for n in nodes:
            f = (n.metadata.labels or {}).get(GPU_PRODUCT, "any")
            node_flavor[n.metadata.name] = f
            alloc[f] = alloc.get(f, 0) + int(str((n.status.allocatable or {}).get(GPU, "0")))

        pending = {}
        for p in pods:
            g = pod_gpu(p)
            if g == 0:
                continue
            if p.spec.node_name and p.status.phase == "Running":
                f = node_flavor.get(p.spec.node_name, "any")
                used[f] = used.get(f, 0) + g
                self.attained[key(p)] = self.attained.get(key(p), 0.0) + self.period * g  # LAS 누적
            elif has_gate(p) and p.status.phase == "Pending":
                f = lbl(p, FLAVOR_LBL, "any")
                pending.setdefault(f, []).append(p)

        for f, gated in pending.items():
            total = alloc.get(f, 0)
            ar = (used.get(f, 0) / total * 100) if total else 0.0
            servers = build_servers(nodes, pods, f)
            ordered = self.order(gated, servers, ar, f)
            free = max(0, total - used.get(f, 0))
            for p in ordered:
                g = pod_gpu(p)
                if g <= free:
                    self.ungate(p)
                    free -= g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="sfqa", choices=["fifo", "sjf", "priority", "las", "sfqa"])
    ap.add_argument("--period", type=float, default=5.0)
    ap.add_argument("--alpha", type=float, default=0.13889)
    ap.add_argument("--beta", type=float, default=80.0)
    ap.add_argument("--age-unit", type=float, default=10.0,
                    help="age 1 증가에 필요한 대기 초. 실측 큐잉 스케일에 맞춤(기본 10s)")
    args = ap.parse_args()
    v1 = load()
    ctrl = PolicyCtrl(v1, args.policy, Params(alpha=args.alpha, beta=args.beta, prevent_starv=True),
                      args.period, args.age_unit)
    print(f"[policy:{args.policy}] start period={args.period}s", flush=True)
    while True:
        try:
            ctrl.reconcile()
        except Exception as e:  # noqa
            print(f"[policy] err: {e}", flush=True)
        time.sleep(args.period)


if __name__ == "__main__":
    main()
