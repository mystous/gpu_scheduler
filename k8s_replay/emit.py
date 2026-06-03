"""CommonJob + ExecSpec → K8s Job 매니페스트(JSON dict). kubectl 은 JSON 매니페스트를 그대로 수용.

라벨이 load-bearing: squad.io/preemptible 이 true 인 job 만 PTR 이주 후보가 된다.
schedulerName 으로 baseline(default-scheduler) ↔ SUT(squad-scheduler) 를 전환한다.
GPU 타입은 nodeAffinity(nvidia.com/gpu.product)로 요청(이종 클러스터).
"""
from __future__ import annotations
import hashlib
import re

from common import CommonJob
from model_assign import ExecSpec, HF_CACHE

CKPT_HOST = "/var/squad-ckpt"   # PTR 체크포인트(이주 resume) — kind 노드 내부 경로(단일 노드 공유)


def sanitize(job_id: str) -> str:
    s = re.sub(r"[^a-z0-9-]", "-", job_id.lower())
    s = re.sub(r"-+", "-", s).strip("-")
    if len(s) > 50 or not s:
        h = hashlib.md5(job_id.encode()).hexdigest()[:8]
        s = (s[:40].strip("-") + "-" + h) if s else "j-" + h
    return s


def job_manifest(job: CommonJob, spec: ExecSpec, scheduler_name: str,
                 namespace: str = "squad", use_gpu_affinity: bool = True,
                 sfqa_gate: bool = False) -> dict:
    name = sanitize(job.job_id)
    labels = {
        "squad.io/preemptible": str(job.preemptible).lower(),
        "squad.io/workload-kind": job.workload_kind.value,
        "squad.io/gpu-count": str(job.gpu_count),
        "squad.io/gpu-type": job.gpu_type,
        "squad.io/source-trace": job.source_trace,
        "squad.io/job-id": name,
        "squad.io/duration": str(int(job.duration)),   # SJF 정책용
        "squad.io/priority": str(job.priority),         # Priority 정책용
    }
    env = [{"name": k, "value": v} for k, v in (spec.env or {}).items()]
    env.append({"name": "CKPT_PATH", "value": f"/squad-ckpt/{name}"})

    # holder 는 ckpt 만 필요(바이너리 이미지). real(vLLM/torch)만 코드/HF 캐시 마운트.
    volumes = [{"name": "ckpt", "hostPath": {"path": CKPT_HOST, "type": "DirectoryOrCreate"}}]
    mounts = [{"name": "ckpt", "mountPath": "/squad-ckpt"}]
    if spec.run_mode == "real":
        volumes += [
            {"name": "squad-code", "configMap": {"name": "squad-holder"}},
            {"name": "hf", "hostPath": {"path": HF_CACHE, "type": "Directory"}},
        ]
        mounts += [
            {"name": "squad-code", "mountPath": "/squad"},
            {"name": "hf", "mountPath": HF_CACHE},
        ]
    container = {
        "name": "wl",
        "image": spec.image,
        "imagePullPolicy": "IfNotPresent",
        "command": spec.command,
        "args": spec.args,
        "env": env,
        "resources": {"limits": {"nvidia.com/gpu": str(job.gpu_count)}},
        "volumeMounts": mounts,
    }
    pod_spec = {
        "schedulerName": scheduler_name,
        "restartPolicy": "Never",
        "containers": [container],
        "volumes": volumes,
    }
    # SFQA(SUT): schedulingGate 를 두면 SFQA 컨트롤러가 P* 순으로 해제할 때까지 스케줄 보류.
    # baseline 은 gate 없이 곧장 default-scheduler 가 처리.
    if sfqa_gate:
        pod_spec["schedulingGates"] = [{"name": "squad.io/sfqa"}]
    # 이종 클러스터: 특정 GPU 타입 요청(타입이 명시된 경우만).
    if use_gpu_affinity and job.gpu_type not in ("", "any"):
        pod_spec["affinity"] = {
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [{
                        "matchExpressions": [{
                            "key": "nvidia.com/gpu.product",
                            "operator": "In",
                            "values": [job.gpu_type, job.gpu_type.upper()],
                        }]
                    }]
                }
            }
        }
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": name, "namespace": namespace, "labels": labels},
        "spec": {
            "backoffLimit": 0,
            # ttlSecondsAfterFinished 제거: 완료 pod 을 유지해야 분석(JCT/큐잉)에서 누락되지 않음.
            # 런 종료 후 `kubectl delete jobs --all -n squad` 로 수동 정리.
            "template": {"metadata": {"labels": labels}, "spec": pod_spec},
        },
    }
