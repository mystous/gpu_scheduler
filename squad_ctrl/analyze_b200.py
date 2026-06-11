"""B200 실측 분석기 — 논문 §VI(eval:b200) 메트릭만 산출.

논문 fig:b200 placeholder가 보여주는 것: 큐-축 8정책의 **큐잉지연·JCT·BSLD**(부차) +
**순서 공정성 p1**(주 공정성 지표, threats §VI-5). 멀티-VC/테넌트/시드변동성은 논문 범위 밖.

기존 하니스 산출물만으로 전부 사후 계산(추가 계측 불요):
  - jct.csv      : pod, queue_sec, jct_sec   → q 분위수, JCT, service=jct-queue → BSLD
  - submit_log.csv: job, arrival, wall        → arrival(도착) → start=arrival+queue → p1
  - metrics.csv  : alloc_pct 시계열           → alloc_avg/max

정의는 시뮬(sim/order_fairness.py, sim/analyze_sweep.py)과 동일하게 재사용 → 시뮬 표와 직접 비교 가능.

실행: /raid/squad/venv/bin/python analyze_b200.py
출력: /home/mystous/gpu_scheduler/results/{b200_summary.csv, b200_table.md}
"""
import csv
import os
import sys

sys.path.insert(0, "/home/mystous/gpu_scheduler/sim")
from order_fairness import per_job_score   # noqa: E402  (시뮬과 동일 순서공정성)

RUNS = "/raid/squad/runs"
OUTDIR = "/home/mystous/gpu_scheduler/results"
BSLD_TAU = 10.0   # 시뮬과 동일(논문 §V-D 초단기 작업 퇴화 방지)

# run-id → (라벨, 큐-축 8정책 여부)
RUNSET = [
    ("m_fifo",     "FIFO (default-sched)", False),  # default-scheduler 통제군(게이트 없음)
    ("m_gatefifo", "FIFO",                 True),   # 큐-축 8정책의 FIFO(gate)
    ("m_sjf",      "SJF",                  True),
    ("m_las",      "LAS",                  True),
    ("m_kueue",    "Kueue",                True),
    ("m_easy",     "EASY",                 True),
    ("m_themis",   "Themis",               True),
    ("m_sfqa",     "SAFA (고정 α)",        True),   # 컨트롤러 키 sfqa, ablation 고정군
    ("m_auto",     "SAFA",                 True),   # 컨트롤러 키 sfqa-auto, zero-knob 제안 정책
]


def pctl(vals, p):
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[min(len(s) - 1, int(len(s) * p))]


def strip_pod_suffix(pod):
    """pod 이름(<job>-<5char>) → job 이름. 랜덤 접미사엔 '-'가 없어 rsplit 1회로 복원."""
    return pod.rsplit("-", 1)[0]


def analyze_run(run_id):
    jp = os.path.join(RUNS, run_id, "jct.csv")
    sp = os.path.join(RUNS, run_id, "submit_log.csv")
    mp = os.path.join(RUNS, run_id, "metrics.csv")
    if not os.path.exists(jp):
        return None

    # 도착시각: submit_log job → arrival
    arrival = {}
    if os.path.exists(sp):
        for r in csv.DictReader(open(sp)):
            arrival[r["job"]] = float(r["arrival"])

    qs, js, bslds, jobs_af = [], [], [], []
    mk_arr, mk_end = [], []                     # makespan = max(arrival+jct) − min(arrival)
    for r in csv.DictReader(open(jp)):
        q = r.get("queue_sec"); j = r.get("jct_sec")
        if not q or not j:
            continue
        q = float(q); j = float(j)
        qs.append(q); js.append(j)
        service = max(j - q, 0.0)              # service = finished-started = jct-queue (정확)
        bslds.append((q + service) / max(service, BSLD_TAU))
        job = strip_pod_suffix(r["pod"])
        if job in arrival:
            a = arrival[job]
            jobs_af.append((a, a + q, 0))      # (arrival, start, finish unused)
            mk_arr.append(a); mk_end.append(a + j)  # 시뮬 makespan_days 와 동일 정의

    # makespan(처리율 지표) — 정책 무관 makespan-bound 검증용. 초·분.
    makespan_s = (max(mk_end) - min(mk_arr)) if mk_arr else 0.0

    # 순서 공정성(시뮬과 동일 per_job_score): mean / p1(하위1%) / lt50(<50점 비율%)
    fmean = fp1 = lt50 = float("nan")
    if len(jobs_af) >= 2:
        sc = sorted(per_job_score(jobs_af))
        n = len(sc)
        fmean = sum(sc) / n
        fp1 = sc[int(n * .01)]
        lt50 = 100.0 * sum(1 for x in sc if x < 50) / n

    # 할당률 시계열 → avg/max
    alloc_avg = alloc_max = 0.0
    if os.path.exists(mp):
        ap = []
        for r in csv.DictReader(open(mp)):
            try:
                ap.append(float(r["alloc_pct"]))
            except (ValueError, KeyError):
                pass
        if ap:
            alloc_avg = sum(ap) / len(ap); alloc_max = max(ap)

    return dict(
        n=len(qs),
        q_p50=pctl(qs, .5), q_p90=pctl(qs, .9), q_max=max(qs) if qs else 0,
        j_p50=pctl(js, .5), j_p90=pctl(js, .9), j_max=max(js) if js else 0,
        bsld_p50=pctl(bslds, .5), bsld_p99=pctl(bslds, .99), bsld_max=max(bslds) if bslds else 0,
        fair_mean=fmean, fair_p1=fp1, lt50_pct=lt50,
        alloc_avg=alloc_avg, alloc_max=alloc_max,
        makespan_s=makespan_s, makespan_min=makespan_s / 60.0,
        matched=len(jobs_af),
    )


def fmt(x, nd=0):
    if x != x:   # nan
        return "—"
    return f"{x:.{nd}f}"


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    rows = []
    for run_id, label, is8 in RUNSET:
        s = analyze_run(run_id)
        if s is None:
            print(f"[skip] {run_id} (결과 없음)", flush=True)
            continue
        s["run"] = run_id; s["policy"] = label; s["queue_axis_8"] = is8
        rows.append(s)
        print(f"  ✓ {label:18} n={s['n']:>4} q p50/p90/max={s['q_p50']:.0f}/{s['q_p90']:.0f}/{s['q_max']:.0f}"
              f"  BSLD p50/max={s['bsld_p50']:.2f}/{s['bsld_max']:.1f}"
              f"  p1={fmt(s['fair_p1'],1)} lt50={fmt(s['lt50_pct'],1)}%"
              f"  alloc avg={s['alloc_avg']:.0f}%  makespan={s['makespan_min']:.1f}분", flush=True)

    # CSV
    fields = ["run", "policy", "queue_axis_8", "n",
              "q_p50", "q_p90", "q_max", "j_p50", "j_p90", "j_max",
              "bsld_p50", "bsld_p99", "bsld_max", "fair_mean", "fair_p1", "lt50_pct",
              "alloc_avg", "alloc_max", "makespan_s", "makespan_min"]
    with open(os.path.join(OUTDIR, "b200_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})

    # Markdown 표(논문용): 큐-축 8정책
    md = ["# B200×8 단일노드 실측 — 큐-축 8정책 (논문 §VI fig:b200)\n",
          "워크로드: Philly 층화샘플 1000잡, seed=42, κ=3000, peak 3.6× 과부하. 단위: 초.\n",
          "공정성: p1=하위 1% 순서공정성(100=공정, **주 지표**), BSLD=bounded slowdown(부차).\n",
          "\n## 큐-축 8정책\n",
          "| 정책 | n | 큐잉 p50 | p90 | max | JCT p50 | BSLD p50 | BSLD max | p1 ↑ | lt50% ↓ | alloc avg | makespan(분) |",
          "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|"]
    for r in rows:
        if not r["queue_axis_8"]:
            continue
        md.append(f"| {r['policy']} | {r['n']} | {r['q_p50']:.0f} | {r['q_p90']:.0f} | {r['q_max']:.0f} "
                  f"| {r['j_p50']:.0f} | {r['bsld_p50']:.2f} | {r['bsld_max']:.1f} "
                  f"| {fmt(r['fair_p1'],1)} | {fmt(r['lt50_pct'],1)} | {r['alloc_avg']:.0f}% | {r['makespan_min']:.1f} |")
    # Ablation 소표
    abl = {r["run"]: r for r in rows}
    md.append("\n## Ablation: SAFA 고정 α vs 무튜닝 (실 클러스터 무튜닝 순효과)\n")
    md.append("| | 큐잉 p50 | 큐잉 max | BSLD p50 | p1 ↑ | lt50% ↓ |")
    md.append("|---|--:|--:|--:|--:|--:|")
    for rid, lbl in [("m_sfqa", "SAFA (고정 α, --beta 80)"), ("m_auto", "SAFA (무튜닝, 제안)")]:
        if rid in abl:
            r = abl[rid]
            md.append(f"| {lbl} | {r['q_p50']:.0f} | {r['q_max']:.0f} | {r['bsld_p50']:.2f} "
                      f"| {fmt(r['fair_p1'],1)} | {fmt(r['lt50_pct'],1)} |")
    md.append("\n## 통제군 (참고)\n")
    md.append("| 정책 | 큐잉 p50 | 큐잉 max | p1 | alloc avg |")
    md.append("|---|--:|--:|--:|--:|")
    for r in rows:
        if not r["queue_axis_8"]:
            md.append(f"| {r['policy']} | {r['q_p50']:.0f} | {r['q_max']:.0f} | {fmt(r['fair_p1'],1)} | {r['alloc_avg']:.0f}% |")

    with open(os.path.join(OUTDIR, "b200_table.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"\n→ {OUTDIR}/b200_summary.csv, b200_table.md  ({len(rows)} run)")


if __name__ == "__main__":
    main()
