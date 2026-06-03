"""트레이스별 ingest — 각 함수는 list[CommonJob]을 돌려준다.

지원: Alibaba cluster-trace-gpu-v2020(pai_task_table), v2023(openb_pod_list, K8s-pod 형태),
사내 전처리 job_flow CSV, Philly cluster_job_log(JSON). 모두 gpu_type을 보존한다.
"""
from __future__ import annotations
import csv
import json
import sys
from datetime import datetime

from common import CommonJob, WorkloadKind, gpu_count_from_milli, classify_kind

csv.field_size_limit(sys.maxsize)


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ── Alibaba v2020: pai_task_table ──────────────────────────────────────────
# 헤더: job_name,task_name,inst_num,status,start_time,end_time,plan_cpu,plan_mem,plan_gpu,gpu_type
ALIBABA2020_COLS = ["job_name", "task_name", "inst_num", "status", "start_time",
                    "end_time", "plan_cpu", "plan_mem", "plan_gpu", "gpu_type"]


def ingest_alibaba2020(task_csv: str, limit: int | None = None) -> list[CommonJob]:
    out = []
    with open(task_csv, newline="") as f:
        r = csv.DictReader(f, fieldnames=ALIBABA2020_COLS)
        for i, row in enumerate(r):
            if limit and len(out) >= limit:
                break
            plan_gpu = _f(row["plan_gpu"])
            if plan_gpu <= 0:
                continue  # CPU-only task 스킵
            start, end = _f(row["start_time"]), _f(row["end_time"])
            dur = end - start
            if dur <= 0:
                continue
            gpu_count = min(8, max(1, gpu_count_from_milli(plan_gpu, unit=100.0)))
            gtype = (row["gpu_type"] or "any").strip()
            if gtype in ("", "MISC"):
                gtype = "any"
            out.append(CommonJob(
                job_id=f"a20-{row['job_name']}-{row['task_name']}-{i}",
                arrival_time=start, duration=dur,
                gpu_count=gpu_count, gpu_type=gtype,
                preemptible=False,  # v2020엔 선점 플래그 없음 → config 휴리스틱(normalize에서 부여 가능)
                workload_kind=classify_kind(dur, gpu_count),
                priority=0, source_trace="alibaba2020",
            ))
    return out


# ── Alibaba v2023: openb_pod_list (이미 K8s-pod 형태) ────────────────────────
# 헤더: name,cpu_milli,memory_mib,num_gpu,gpu_milli,gpu_spec,qos,pod_phase,
#       creation_time,deletion_time,scheduled_time
def ingest_alibaba2023(pod_csv: str, limit: int | None = None) -> list[CommonJob]:
    out = []
    with open(pod_csv, newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if limit and len(out) >= limit:
                break
            num_gpu = int(_f(row.get("num_gpu", 0)))
            gpu_milli = _f(row.get("gpu_milli", 0))
            gpu_count = num_gpu if num_gpu > 0 else gpu_count_from_milli(gpu_milli, unit=1000.0)
            if gpu_count <= 0:
                continue
            gpu_count = min(8, gpu_count)
            create = _f(row.get("creation_time", 0))
            sched = _f(row.get("scheduled_time", create))
            delete = _f(row.get("deletion_time", 0))
            dur = (delete - sched) if delete > sched else (delete - create)
            if dur <= 0:
                continue
            gtype = (row.get("gpu_spec") or "any").strip() or "any"
            qos = (row.get("qos") or "").strip()
            out.append(CommonJob(
                job_id=f"a23-{row.get('name','job')}-{i}",
                arrival_time=create, duration=dur,
                gpu_count=gpu_count, gpu_type=gtype,
                preemptible=(qos.upper() == "BE"),  # best-effort → 선점 가능
                workload_kind=classify_kind(dur, gpu_count),
                priority=0, source_trace="alibaba2023",
            ))
    return out


# ── 사내 전처리 job_flow (neo_no_duplicate) ─────────────────────────────────
# 헤더: pod_name,pod_type,project,namespace,user_team,start,finish,count,time_diff,
#       computing_load,gpu_utilization,flavor,preemption
def _parse_dt(s: str) -> float | None:
    s = (s or "").strip()
    if not s:
        return None
    try:  # ISO 8601 (타임존 오프셋 "+00:00" 포함 가능)
        return datetime.fromisoformat(s).timestamp()
    except (ValueError, AttributeError):
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).timestamp()
        except ValueError:
            continue
    return None


def _parse_timedelta(s: str) -> float:
    """pandas timedelta 문자열 → 초. 예: "2 days 17:00:00", "0 days 13:00:00", "13:00:00"."""
    s = (s or "").strip()
    if not s:
        return 0.0
    days = 0
    if "day" in s:
        a, b = s.split("day", 1)
        try:
            days = int(float(a.strip()))
        except ValueError:
            days = 0
        s = b.lstrip("s").strip()
    h = m = sec = 0
    if ":" in s:
        p = s.split(":")
        try:
            h = int(p[0]); m = int(p[1]); sec = int(float(p[2])) if len(p) > 2 else 0
        except ValueError:
            pass
    return days * 86400 + h * 3600 + m * 60 + sec


def ingest_inhouse(job_flow_csv: str, limit: int | None = None) -> list[CommonJob]:
    out = []
    t0 = None
    with open(job_flow_csv, newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if limit and len(out) >= limit:
                break
            count = int(_f(row.get("count", 1))) or 1
            dur = _parse_timedelta(row.get("time_diff", ""))  # "N days HH:MM:SS" → 초
            if dur <= 0:
                continue
            start = _parse_dt(row.get("start", ""))
            if start is None:
                continue
            if t0 is None or start < t0:
                t0 = start
            kind = (WorkloadKind.INFERENCE if (row.get("pod_type", "").strip() == "instance")
                    else WorkloadKind.TRAINING)
            gtype = (row.get("flavor") or "any").strip() or "any"
            out.append(CommonJob(
                job_id=f"ih-{row.get('pod_name','pod')}-{i}",
                arrival_time=start, duration=dur,
                gpu_count=min(8, max(1, count)), gpu_type=gtype,
                preemptible=(row.get("preemption", "n").strip().lower() in ("y", "yes", "true", "1")),
                workload_kind=kind, priority=0, source_trace="inhouse",
            ))
    # arrival_time을 t0 기준 상대 초로 정규화
    if t0 is not None:
        for j in out:
            j.arrival_time -= t0
    return out


# ── Philly: cluster_job_log (JSON) ──────────────────────────────────────────
def ingest_philly(job_log_json: str, limit: int | None = None) -> list[CommonJob]:
    with open(job_log_json) as f:
        data = json.load(f)
    jobs = data if isinstance(data, list) else data.get("jobs", [])
    out = []
    for i, j in enumerate(jobs):
        if limit and len(out) >= limit:
            break
        attempts = j.get("attempts", []) or []
        if not attempts:
            continue
        # gpu_count = 첫 attempt 의 detail 별 gpus 합
        first = attempts[0]
        gpu_count = sum(len(d.get("gpus", [])) for d in first.get("detail", []))
        if gpu_count <= 0:
            continue
        # Philly 시각은 "YYYY-MM-DD HH:MM:SS" 문자열. running job 은 end_time=None.
        submit = _parse_dt(j.get("submitted_time", ""))
        if submit is None:
            continue
        # duration = 모든 attempt 의 (end-start) 합
        dur = 0.0
        for a in attempts:
            s, e = _parse_dt(a.get("start_time", "")), _parse_dt(a.get("end_time", ""))
            if s is not None and e is not None and e > s:
                dur += e - s
        if dur <= 0:
            continue
        out.append(CommonJob(
            job_id=f"ph-{j.get('jobid', i)}",
            arrival_time=submit, duration=dur,
            gpu_count=min(8, gpu_count), gpu_type="any",  # Philly는 동종 클러스터(타입 미구분)
            preemptible=(len(attempts) > 1),  # 다중 attempt = 선점 발생
            workload_kind=classify_kind(dur, min(8, gpu_count)),
            priority=0, source_trace="philly",
        ))
    return out


INGESTERS = {
    "alibaba2020": ingest_alibaba2020,
    "alibaba2023": ingest_alibaba2023,
    "inhouse": ingest_inhouse,
    "philly": ingest_philly,
}
