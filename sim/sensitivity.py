"""A4 — 합성계수 민감도(±50%): 결론 부호 불변성 검증.

흔드는 합성 파라미터(각각 독립적으로 ±50%):
  (1) 타입 속도계수 SPEED — 느린 타입(h100/a100/...)의 b200 대비 '추가' 느림을 ±50%.
      slow_factor s>1에 대해 (s-1)을 ±50% → 이종 클러스터의 속도 이질성 강도를 조절.
      single(b200 only)에는 무영향 — hetero에서만 의미.
  (2) 수명주기 오버헤드 — sched_lat/startup_solo/startup_busy/teardown 전부 ×{0.5,1.5}.
  (3) Lucid SS 슬로다운 — collocation 슬로다운 강도(1-rate)를 ±50%.
      rate' = 1 - (1-rate)*f.  f=0.5(약한 간섭)/1.5(강한 간섭).

핵심 질문(결론 부호): 이종·과부하(512 hetero)에서
  (A) sfqa-auto의 fair_p1 > 고정 sfqa의 fair_p1  (무튜닝이 더 공정한가)
  (B) sfqa-auto의 fair_p1 > Lucid의 fair_p1       (정보-우위 정책보다 하한이 안정적인가)
이 ±50% 전 구간에서 유지되는지 본다. 부호가 바뀌면 정직히 보고.

핵심 구성: 512 single / 512 hetero. 정책: fifo, las, sfqa, sfqa-auto, lucid.
출력: sweep_results/sensitivity/sensitivity.csv
"""
import csv
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (HERE, os.path.join(ROOT, "squad_ctrl"), os.path.join(ROOT, "k8s_replay")):
    sys.path.insert(0, p)

import engine                                          # noqa: E402
from engine import Job, Node, Overheads, Simulator     # noqa: E402
import policies as P                                    # noqa: E402
import lucid_sim                                        # noqa: E402
from lucid_sim import LJob, LucidSim                    # noqa: E402
from order_fairness import per_job_score                # noqa: E402

TRACE = os.path.join(HERE, "sweep_trace.csv")
CONFIGS = [(512, "single"), (512, "hetero")]
# 환경변수로 정책·워커·출력 제한 가능(무거운 lucid를 적은 워커로 분리 실행하기 위해).
POLS = os.environ.get("SENS_POLS", "fifo,las,sfqa,sfqa-auto,lucid").split(",")
_WORKERS = int(os.environ.get("SENS_WORKERS", "20"))
_OUTNAME = os.environ.get("SENS_OUT", "sensitivity.csv")

_BASE_SPEED = dict(engine.SPEED)
_BASE_SS = dict(lucid_sim.SS_SPEED)


def load_trace():
    out = []
    for r in csv.DictReader(open(TRACE)):
        out.append((r["job_id"], float(r["arrival_s"]),
                    max(1.0, float(r["service_sec"])), int(r["gpu_count"])))
    return out


def build_nodes(gpu, kind):
    n = gpu // 8
    if kind == "single":
        return [Node(name=f"b200-{i}", gpu_type="b200", total=8) for i in range(n)]
    base = n // 3
    rem = n - base * 3
    counts = [base + (1 if i < rem else 0) for i in range(3)]
    types = ["b200", "h100", "a100"]
    out, idx = [], 0
    for t, c in zip(types, counts):
        for _ in range(c):
            out.append(Node(name=f"{t}-{idx}", gpu_type=t, total=8)); idx += 1
    return out


def metrics(jr):
    qs = [x[3] for x in jr]
    jb = [(x[1], x[2], 0) for x in jr]
    sc = sorted(per_job_score(jb))
    n = len(sc)
    q50 = sorted(qs)[len(qs) // 2] if qs else 0
    fp1 = sc[int(n * .01)] if n else 0
    return q50, fp1


def run_pol(name, trace, nodes_proto, ovh):
    nodes = [Node(name=n.name, gpu_type=n.gpu_type, total=n.total) for n in nodes_proto]
    if name == "lucid":
        import random
        rng = random.Random(42)
        jobs = [LJob(id=i, arrival=a, duration=d, gpu_count=g,
                     util=min(0.99, max(0.05, rng.gauss(0.6, 0.2)))) for i, a, d, g in trace]
        sim = LucidSim(jobs, nodes, ovh, gss=2); sim.run()
        jr = [(j.id, j.arrival, j.place_time, j.place_time - j.arrival,
               max(j.finish_time - j.place_time, 0.1), j.gpu_count)
              for j in sim.finished if j.place_time >= 0]
    else:
        pol = P.make(name) if name != "sfqa" else P.SFQA(alpha=0.13889, beta=100.0)
        jobs = [Job(id=i, arrival=a, duration=d, gpu_count=g, gpu_type="any")
                for i, a, d, g in trace]
        sim = Simulator(jobs, nodes, pol, overheads=ovh); sim.run()
        jr = [(j.id, j.arrival, j.place_time, j.queue_delay, j.duration, j.gpu_count)
              for j in sim.finished if j.queue_delay is not None]
    return metrics(jr)


def set_speed(factor):
    """느린 타입의 추가 느림(s-1)을 factor배. b200/any/h200(≤1)은 유지."""
    engine.SPEED.clear()
    for t, s in _BASE_SPEED.items():
        engine.SPEED[t] = 1.0 + (s - 1.0) * factor if s > 1.0 else s


def set_ss(factor):
    lucid_sim.SS_SPEED.clear()
    for k, rate in _BASE_SS.items():
        lucid_sim.SS_SPEED[k] = 1.0 - (1.0 - rate) * factor


def reset():
    engine.SPEED.clear(); engine.SPEED.update(_BASE_SPEED)
    lucid_sim.SS_SPEED.clear(); lucid_sim.SS_SPEED.update(_BASE_SS)


SCENARIOS = [
    ("baseline", 1.0, 1.0, 1.0),
    ("speed-50", 0.5, 1.0, 1.0),
    ("speed+50", 1.5, 1.0, 1.0),
    ("ovh-50", 1.0, 0.5, 1.0),
    ("ovh+50", 1.0, 1.5, 1.0),
    ("lucidSS-50", 1.0, 1.0, 0.5),   # 슬로다운 약화(Lucid 유리)
    ("lucidSS+50", 1.0, 1.0, 1.5),   # 슬로다운 강화(Lucid 불리)
]


def _task(args):
    """프로세스 격리: 워커마다 전역 SPEED/SS_SPEED를 패치 후 1회 실행."""
    label, sf, of, ssf, gpu, kind, pol = args
    reset()
    set_speed(sf)
    set_ss(ssf)
    ovh = Overheads(enabled=True)
    ovh.sched_lat *= of; ovh.startup_solo *= of
    ovh.startup_busy *= of; ovh.teardown *= of
    trace = load_trace()
    nodes = build_nodes(gpu, kind)
    q50, fp1 = run_pol(pol, trace, nodes, ovh)
    return dict(scenario=label, gpu=gpu, kind=kind, policy=pol, q_p50=q50, fair_p1=fp1)


def main():
    scenarios = SCENARIOS
    _only = os.environ.get("SENS_SCENARIOS", "").strip()
    if _only:
        _keep = set(_only.split(","))
        scenarios = [s for s in SCENARIOS if s[0] in _keep]
    tasks = []
    for label, sf, of, ssf in scenarios:
        for gpu, kind in CONFIGS:
            for pol in POLS:
                tasks.append((label, sf, of, ssf, gpu, kind, pol))
    print(f"total tasks: {len(tasks)} (parallel, workers={_WORKERS})", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=_WORKERS) as ex:
        futs = {ex.submit(_task, t): t for t in tasks}
        done = 0
        for fut in as_completed(futs):
            r = fut.result(); rows.append(r); done += 1
            print(f"  [{done}/{len(tasks)}] [{r['scenario']:11}] {r['gpu']} {r['kind']:6} "
                  f"{r['policy']:9} q50={r['q_p50']:.0f} p1={r['fair_p1']:.1f}", flush=True)
    rows.sort(key=lambda r: (r["scenario"], r["gpu"], r["kind"], r["policy"]))

    outdir = os.path.join(HERE, "sweep_results", "sensitivity")
    os.makedirs(outdir, exist_ok=True)
    of = os.path.join(outdir, _OUTNAME)
    with open(of, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "gpu", "kind", "policy", "q_p50", "fair_p1"])
        for r in rows:
            w.writerow([r["scenario"], r["gpu"], r["kind"], r["policy"],
                        round(r["q_p50"]), round(r["fair_p1"], 2)])
    print(f"\n→ {of}")

    # 결론 부호 요약(512 hetero): auto p1 vs sfqa p1, auto p1 vs lucid p1
    print("\n=== 결론 부호 검증 (512 hetero) ===")
    by = {(r["scenario"], r["policy"]): r for r in rows if r["gpu"] == 512 and r["kind"] == "hetero"}
    for label, *_ in scenarios:
        a = by.get((label, "sfqa-auto"), {}).get("fair_p1", 0)
        s = by.get((label, "sfqa"), {}).get("fair_p1", 0)
        l = by.get((label, "lucid"), {}).get("fair_p1", 0)
        print(f"  {label:11}  auto={a:.1f}  sfqa={s:.1f}  lucid={l:.1f}  "
              f"| auto>sfqa:{a>s}  auto>lucid:{a>l}")


if __name__ == "__main__":
    main()
