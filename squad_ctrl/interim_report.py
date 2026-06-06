"""실행 중 run의 중간 성능 리포트 — 스냅샷(현재) + 히스토리컬(누적·추이).

스냅샷: 현재 대기 중 잡들의 '지금까지 기다린 시간' 분포, 할당률, 백로그.
히스토리컬: 완료 잡 누적 백분위 + 10분 버킷별 추이(완료 시각 기준 p50/max).
사용: interim_report.py <run_id> [--kueue]   (--kueue: Job 생성 기준)
"""
import argparse
import csv
import os
from datetime import datetime, timezone

from kubernetes import client, config

ap = argparse.ArgumentParser()
ap.add_argument("run_id")
ap.add_argument("--kueue", action="store_true")
args = ap.parse_args()

config.load_kube_config()
v1, batch = client.CoreV1Api(), client.BatchV1Api()
now = datetime.now(timezone.utc)

jc = {}
if args.kueue:
    jc = {j.metadata.name: j.metadata.creation_timestamp for j in batch.list_namespaced_job("squad").items}

done = []      # (완료시각, queue, jct)
waiting = []   # 현재 대기 중 잡의 현재까지 대기시간
running = 0
for p in v1.list_namespaced_pod("squad").items:
    jn = (p.metadata.labels or {}).get("job-name")
    c = jc.get(jn, p.metadata.creation_timestamp)
    if p.status.phase == "Running":
        running += 1
        continue
    if p.status.phase == "Pending":
        if c:
            waiting.append((now - c).total_seconds())
        continue
    st = p.status.start_time
    fin = None
    if p.status.container_statuses:
        t = p.status.container_statuses[0].state.terminated
        if t:
            fin = t.finished_at
    if c and st and fin:
        done.append((fin, (st - c).total_seconds(), (fin - c).total_seconds()))

# Kueue: 아직 pod 없는 suspended Job도 대기 집합에 포함
if args.kueue:
    podded = {(p.metadata.labels or {}).get("job-name") for p in v1.list_namespaced_pod("squad").items}
    for name, c in jc.items():
        if name not in podded and c:
            waiting.append((now - c).total_seconds())

pct = lambda a, x: a[min(len(a) - 1, int(len(a) * x))] if a else 0

print(f"════ 스냅샷 (지금 이 순간, {now.strftime('%H:%M:%S')}) ════")
mp = f"/raid/squad/runs/{args.run_id}/metrics.csv"
if os.path.exists(mp):
    with open(mp) as f:
        last = list(csv.DictReader(f))[-1]
    print(f"할당률 {float(last['alloc_pct']):.0f}%  (GPU {last['alloc_used']}/{last['n_gpu']}, running pods {last['running_gpu_pods']})")
waiting.sort()
print(f"대기 중 {len(waiting)}개 — 현재까지 대기: p50={pct(waiting,.5):.0f}s p90={pct(waiting,.9):.0f}s "
      f"최장={waiting[-1] if waiting else 0:.0f}s  | 실행 중 {running}")

print(f"\n════ 히스토리컬 (누적 완료 {len(done)}개) ════")
qs = sorted(q for _, q, _ in done)
bs = sorted(j / max(j - q, 10.0) for _, q, j in done)
print(f"큐잉: p50={pct(qs,.5):.0f} p90={pct(qs,.9):.0f} p99={pct(qs,.99):.0f} max={qs[-1] if qs else 0:.0f}")
print(f"BSLD: p50={pct(bs,.5):.1f} p90={pct(bs,.9):.1f} max={bs[-1] if bs else 0:.1f}")

if done:
    print("\n추이 (완료시각 10분 버킷: n, 큐잉 p50/max):")
    t0 = min(f for f, _, _ in done)
    buckets = {}
    for f, q, _ in done:
        b = int((f - t0).total_seconds() // 600)
        buckets.setdefault(b, []).append(q)
    for b in sorted(buckets):
        a = sorted(buckets[b])
        bar = "#" * min(60, int(pct(a, .5) / 30))
        print(f"  +{b*10:>3}분 n={len(a):>4} p50={pct(a,.5):>5.0f} max={a[-1]:>5.0f} {bar}")
