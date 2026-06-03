"""SQUAD 트레이스 → K8s 워크로드 변환기: 공통 스키마.

여러 GPU 클러스터 트레이스(Alibaba v2020/v2023, Philly, 사내 로그)를 하나의 정규화
스키마(CommonJob)로 흡수한 뒤, K8s Job 매니페스트로 방출한다. 하드웨어 비종속:
gpu_type을 보존하고, 타겟 클러스터의 가용 GPU 타입 풀에 매핑한다(고정 remap 금지).
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
import csv
import math


class WorkloadKind(str, Enum):
    INFERENCE = "inference"
    TRAINING = "training"


@dataclass
class CommonJob:
    """정규화된 작업 1건. 모든 ingest 모듈의 공통 출력."""
    job_id: str
    arrival_time: float          # t0 기준 초 (압축 전 원본)
    duration: float              # 초 (압축 전 원본)
    gpu_count: int               # 1.. (0=CPU job, 보통 스킵)
    gpu_type: str                # 원본 GPU 타입 보존 (MISC/T4/V100/A100/...). 비면 "any"
    preemptible: bool
    workload_kind: WorkloadKind
    priority: int = 0            # 원본 우선순위/큐 (없으면 0)
    source_trace: str = ""       # alibaba2020 | alibaba2023 | philly | inhouse

    def as_row(self) -> dict:
        d = asdict(self)
        d["workload_kind"] = self.workload_kind.value
        return d


NORMALIZED_FIELDS = [
    "job_id", "arrival_time", "duration", "gpu_count", "gpu_type",
    "preemptible", "workload_kind", "priority", "source_trace",
]


def gpu_count_from_milli(milli: float, unit: float = 100.0) -> int:
    """milli-GPU 값을 정수 GPU 수로 올림. Alibaba v2020 plan_gpu unit=100, v2023 gpu_milli unit=1000."""
    if milli is None:
        return 0
    g = math.ceil(float(milli) / unit)
    return max(0, g)


def classify_kind(duration: float, gpu_count: int, inference_max_sec: float = 1800.0) -> WorkloadKind:
    """휴리스틱: 짧고(≤30분) 작은(≤2 GPU) 작업은 추론, 그 외 학습.
    트레이스에 명시적 serving 플래그가 없을 때 사용. config로 비율 조정 가능."""
    if duration <= inference_max_sec and gpu_count <= 2:
        return WorkloadKind.INFERENCE
    return WorkloadKind.TRAINING


def write_normalized_csv(jobs: list[CommonJob], path: str) -> int:
    """정규화 작업 목록을 CSV로 저장(인간 가독). 대용량은 parquet 권장."""
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=NORMALIZED_FIELDS)
        w.writeheader()
        for j in jobs:
            w.writerow(j.as_row())
    return len(jobs)


def read_normalized_csv(path: str) -> list[CommonJob]:
    out = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            out.append(CommonJob(
                job_id=r["job_id"],
                arrival_time=float(r["arrival_time"]),
                duration=float(r["duration"]),
                gpu_count=int(r["gpu_count"]),
                gpu_type=r["gpu_type"],
                preemptible=r["preemptible"] in ("True", "true", "1"),
                workload_kind=WorkloadKind(r["workload_kind"]),
                priority=int(r["priority"]),
                source_trace=r["source_trace"],
            ))
    return out
