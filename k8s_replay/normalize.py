"""정규화: GPU 타입 매핑(하드웨어 비종속) + 시간압축 + 선점 플래그 부여.

핵심: 실험이 유한 시간에 끝나도록 arrival_time 과 duration 을 동일 계수 κ 로 압축한다.
실제 모델 연산을 끝까지 돌리지 않고, 압축된 duration 만큼 GPU 를 점유하는 holder 스텁으로
재생하므로(emit 참조), 스케줄러가 보는 동역학은 보존되면서 실험은 빠르게 끝난다.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from common import CommonJob


@dataclass
class NormalizeConfig:
    # 타겟 클러스터가 실제로 보유한 GPU 타입 풀(노드 라벨 nvidia.com/gpu.product 기준).
    # 현재 테스트 클러스터는 ["b200"]. 이종이면 ["b200","h100","a100"].
    cluster_gpu_types: list[str] = field(default_factory=lambda: ["b200"])
    # 원본 타입 → 타겟 타입 매핑(없으면 등급 유사 우선, 그래도 없으면 첫 타입으로).
    type_map: dict[str, str] = field(default_factory=dict)
    # 시간압축 계수 κ: arrival·duration 둘 다 /κ. 1.0이면 압축 없음.
    kappa: float = 240.0
    # 압축 후 최소 duration(초) — pod 기동 오버헤드가 지배하지 않게.
    min_duration_sec: float = 90.0
    # 압축 후 최대 duration(초) — 0=무제한. 실험을 유한 시간에 끝내기 위한 상한(긴 job clamp).
    max_duration_sec: float = 0.0
    # v2020처럼 선점 플래그가 없는 트레이스에 부여할 선점 비율(0~1).
    preemptible_ratio: float = 0.5


# 대략적 GPU 등급(높을수록 신형). 매핑 시 가까운 등급 우선.
_TIER = {
    "any": 0, "misc": 0, "k80": 1, "m60": 1, "p100": 2, "t4": 2,
    "v100": 3, "v100m16": 3, "v100m32": 3, "a30": 4, "a10": 4,
    "a100": 5, "l4": 4, "l40": 5, "h100": 6, "h200": 7, "b200": 8,
}


def _norm_type(t: str) -> str:
    return (t or "any").strip().lower().replace("nvidia-", "").replace("-", "")


def map_gpu_type(src: str, cfg: NormalizeConfig) -> str:
    """원본 GPU 타입을 타겟 클러스터의 가용 타입으로 매핑(고정 remap 아님 — 등급 근접).
    동종 단일 타입 클러스터면 항상 그 타입. 이종이면 등급이 가장 가까운 타입."""
    targets = cfg.cluster_gpu_types
    if not targets:
        return src
    s = _norm_type(src)
    if s in cfg.type_map:
        return cfg.type_map[s]
    if len(targets) == 1:
        return targets[0]
    src_tier = _TIER.get(s, 0)
    return min(targets, key=lambda t: abs(_TIER.get(_norm_type(t), 0) - src_tier))


def normalize(jobs: list[CommonJob], cfg: NormalizeConfig) -> list[CommonJob]:
    """매핑·압축·선점부여를 적용한 새 목록을 t0(최소 arrival) 기준으로 돌려준다."""
    if not jobs:
        return []
    t0 = min(j.arrival_time for j in jobs)
    out = []
    for idx, j in enumerate(jobs):
        arrival = (j.arrival_time - t0) / cfg.kappa
        dur = max(cfg.min_duration_sec, j.duration / cfg.kappa)
        if cfg.max_duration_sec > 0:
            dur = min(dur, cfg.max_duration_sec)
        gtype = map_gpu_type(j.gpu_type, cfg)
        preempt = j.preemptible
        if j.source_trace == "alibaba2020":  # 선점 플래그 없음 → 결정적 해시로 비율 부여
            preempt = (hash(j.job_id) % 100) < int(cfg.preemptible_ratio * 100)
        out.append(CommonJob(
            job_id=j.job_id, arrival_time=arrival, duration=dur,
            gpu_count=j.gpu_count, gpu_type=gtype, preemptible=preempt,
            workload_kind=j.workload_kind, priority=j.priority, source_trace=j.source_trace,
        ))
    out.sort(key=lambda x: x.arrival_time)
    return out


def peak_demand(jobs: list[CommonJob], window_sec: float = 60.0) -> tuple[int, float]:
    """동시 GPU 수요의 피크와 그 시각을 어림한다(--dry-run 으로 κ 선택용).
    event sweep: 각 job 을 [arrival, arrival+duration) 구간으로 보고 최대 동시 GPU 합."""
    events = []
    for j in jobs:
        events.append((j.arrival_time, j.gpu_count))
        events.append((j.arrival_time + j.duration, -j.gpu_count))
    events.sort()
    cur = peak = 0
    peak_t = 0.0
    for t, d in events:
        cur += d
        if cur > peak:
            peak, peak_t = cur, t
    return peak, peak_t
