"""A2 — 사내 K8S 실측 트레이스를 sweep 포맷으로 변환(Philly 외 독립 트레이스).

원본: job_flow_total(task,flavor,single)_neo_no_duplicate.csv
  컬럼: pod_name, pod_type, project, namespace, user_team, start, finish, count(gpu),
        time_diff, computing_load, gpu_utilization, flavor, preemption
  → 2024년 사내 GPU 클러스터 실측(A100/A30). Philly(MS, 2017)와 독립.

변환: job_id=pod_name+행번호(중복 pod_name 대비), arrival_s=start-min(start),
      service_sec=(finish-start), gpu_count=count.
JCT 클램프: Philly 스윕과 동일하게 48h(172800s)로 클램프(꼬리 작업 비현실적 1700일 제거).
출력: sim/k8s_trace.csv (job_id,arrival_s,service_sec,gpu_count)
"""
import csv
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "job_flow_total(task,flavor,single)_neo_no_duplicate.csv")
OUT = os.path.join(HERE, "k8s_trace.csv")
CLAMP = 172800.0   # 48h, Philly 스윕과 동일


def main():
    rows = list(csv.DictReader(open(SRC)))
    parsed = []
    for i, r in enumerate(rows):
        st = datetime.fromisoformat(r["start"])
        fi = datetime.fromisoformat(r["finish"])
        d = (fi - st).total_seconds()
        if d <= 0:
            continue
        parsed.append((f"{r['pod_name']}#{i}", st, min(d, CLAMP), int(r["count"])))
    t0 = min(p[1] for p in parsed)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["job_id", "arrival_s", "service_sec", "gpu_count"])
        for jid, st, d, g in sorted(parsed, key=lambda x: x[1]):
            w.writerow([jid, round((st - t0).total_seconds(), 1), round(d, 1), g])
    print(f"→ {OUT}  n={len(parsed)}  span_days={(max(p[1] for p in parsed)-t0).total_seconds()/86400:.1f}")


if __name__ == "__main__":
    main()
