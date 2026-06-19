"""SAFA+KAI vs KAI-only 멀티노드 실험 — 배치 축(placement) 합성 검증.

단일노드 B200 실측은 노드 1개라 배치가 퇴화 → 배치 스케줄러(KAI)의 효과는 멀티노드 시뮬에서만
의미가 있다. 여기서 KAI placement(binpack, NVIDIA/KAI-Scheduler 충실 포팅)를 sim node_pref로
얹고, order 축(FIFO vs SAFA)과 2×2로 분리 측정한다.

2×2 (order × placement):
  fifo      = FIFO order   + mostallocated(기존 기본) 배치   — 베이스라인
  kai       = FIFO order   + KAI binpack 배치               — **KAI-only**
  sfqa-auto = SAFA order   + mostallocated 배치             — SAFA(기존)
  safa-kai  = SAFA order   + KAI binpack 배치               — **SAFA+KAI**

지표: q_p50/p90/max, 순서공정성 lt50%/fair_mean/p1(시뮬 order_fairness 동일 정의), alloc_avg, makespan.
트레이스/노드는 run_sweep와 동일(sweep_trace.csv, 256/512/1024 × single/hetero).
커밋된 sweep_results는 건드리지 않고 results/KAI_*에만 출력.

실행: /raid/squad/venv/bin/python run_kai_experiment.py [--gpus 512 --kinds single]
"""
import argparse
import csv
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "squad_ctrl"))
sys.path.insert(0, os.path.join(ROOT, "k8s_replay"))

from engine import Job, Node, Overheads, Simulator    # noqa: E402
import policies as P                                    # noqa: E402
from order_fairness import per_job_score                # noqa: E402

POLS = ["fifo", "kai", "sfqa-auto", "safa-kai"]
LABEL = {"fifo": "FIFO (mostalloc)", "kai": "KAI-only (FIFO+binpack)",
         "sfqa-auto": "SAFA (mostalloc)", "safa-kai": "SAFA+KAI (SAFA+binpack)"}
OUTDIR = os.path.join(ROOT, "results")


def load_trace(path):
    out = []
    for r in csv.DictReader(open(path)):
        out.append((r["job_id"], float(r["arrival_s"]), max(1.0, float(r["service_sec"])),
                    int(r["gpu_count"])))
    return out


def build_nodes(gpu, kind):
    n = gpu // 8
    if kind == "single":
        return [Node(name=f"b200-{i}", gpu_type="b200", total=8) for i in range(n)]
    base, rem = n // 3, n - (n // 3) * 3
    counts = [base + (1 if i < rem else 0) for i in range(3)]
    out, idx = [], 0
    for t, c in zip(["b200", "h100", "a100"], counts):
        for _ in range(c):
            out.append(Node(name=f"{t}-{idx}", gpu_type=t, total=8)); idx += 1
    return out


def pctl(a, p):
    a = sorted(a)
    return a[min(len(a) - 1, int(len(a) * p))] if a else 0.0


def run_one(name, trace, nodes_proto, ovh):
    nodes = [Node(name=n.name, gpu_type=n.gpu_type, total=n.total) for n in nodes_proto]
    pol = P.make(name)
    jobs = [Job(id=i, arrival=a, duration=d, gpu_count=g, gpu_type="any")
            for i, a, d, g in trace]
    sim = Simulator(jobs, nodes, pol, overheads=ovh)
    r = sim.run()
    qs, bslds, jb, mk_a, mk_e = [], [], [], [], []
    for j in sim.finished:
        if j.queue_delay is None:
            continue
        q = j.queue_delay; s = j.duration
        qs.append(q); bslds.append((q + s) / max(s, 10.0))
        jb.append((j.arrival, j.place_time, 0))
        mk_a.append(j.arrival); mk_e.append(j.arrival + q + s)
    sc = sorted(per_job_score(jb)); m = len(sc)
    return dict(
        n=len(qs), q_p50=pctl(qs, .5), q_p90=pctl(qs, .9), q_max=max(qs) if qs else 0,
        bsld_p50=pctl(bslds, .5),
        fair_mean=sum(sc) / m if m else 0, lt50=100 * sum(1 for x in sc if x < 50) / m if m else 0,
        p1=sc[m // 100] if m else 0,
        alloc_avg=r.get("alloc_avg", 0.0),
        makespan_min=(max(mk_e) - min(mk_a)) / 60.0 if mk_a else 0,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", default=os.path.join(HERE, "sweep_trace.csv"))
    ap.add_argument("--gpus", default="256,512,1024")
    ap.add_argument("--kinds", default="single,hetero")
    ap.add_argument("--policies", default=",".join(POLS))
    a = ap.parse_args()
    trace = load_trace(a.trace)
    gpus = [int(x) for x in a.gpus.split(",")]
    kinds = a.kinds.split(",")
    pols = a.policies.split(",")
    ovh = Overheads(enabled=True)
    os.makedirs(OUTDIR, exist_ok=True)
    print(f"trace n={len(trace)}, gpus={gpus}, kinds={kinds}, pols={pols}", flush=True)
    rows = []
    for gpu in gpus:
        for kind in kinds:
            nodes = build_nodes(gpu, kind)
            for name in pols:
                t0 = time.time()
                s = run_one(name, trace, nodes, ovh)
                s.update(gpu=gpu, kind=kind, policy=name, label=LABEL.get(name, name))
                rows.append(s)
                print(f"  {gpu:>4} {kind:6} {LABEL.get(name,name):26} "
                      f"q_p50={s['q_p50']:.0f} q_max={s['q_max']:.0f} lt50={s['lt50']:.1f}% "
                      f"p1={s['p1']:.1f} alloc={s['alloc_avg']:.0f}% mkspn={s['makespan_min']:.0f}m "
                      f"({time.time()-t0:.0f}s)", flush=True)
    fields = ["gpu", "kind", "policy", "label", "n", "q_p50", "q_p90", "q_max",
              "bsld_p50", "fair_mean", "lt50", "p1", "alloc_avg", "makespan_min"]
    with open(os.path.join(OUTDIR, "kai_experiment_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"\n→ {OUTDIR}/kai_experiment_summary.csv ({len(rows)} 행)")


if __name__ == "__main__":
    main()
