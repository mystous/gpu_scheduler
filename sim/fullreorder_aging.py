"""Full-reorder 고전 aging 베이스라인(R1·R5 요구) — sim/policies.py 무수정.
  age-sort      : 절대 나이 내림차순 전체 정렬 = 정의상 도착순(FIFO) — 해석 검증용
  slurm-aging-w : Slurm multifactor류, score = w·(A/A_max) + (1−w)·(1−gpu/8) 내림차순
                  (나이 가중 + small-size factor; w ∈ {0.25,0.5,0.75} 그리드 — 베이스라인에 유리하게 최선값 보고)
                  blocking=True(head-of-queue) 기본 + w=0.5는 비차단(backfill류)도 측정
"""
import sys
sys.path.insert(0, "/home/mystous/projects/gpu_scheduler/sim")
sys.path.insert(0, "/home/mystous/projects/gpu_scheduler/squad_ctrl")
sys.path.insert(0, "/home/mystous/projects/gpu_scheduler/k8s_replay")
import numpy as np, json
import policies as P
from engine import Job, Node, Overheads, Simulator
from run_sweep import load_trace, build_nodes
from order_fairness import per_job_score

class AgeSort(P.Policy):
    name = "age-sort"; blocking = True
    def order(self, cand_idx, age, ar, sim):
        if cand_idx.size == 0: return cand_idx
        return cand_idx[np.argsort(-age, kind="stable")]

class SlurmAging(P.Policy):
    blocking = True
    def __init__(self, w, blocking=True):
        self.w = w; self.blocking = blocking
        self.name = f"slurm-aging-{w}{'b' if blocking else 'n'}"
    def order(self, cand_idx, age, ar, sim):
        if cand_idx.size == 0: return cand_idx
        amax = max(1.0, float(age.max()))
        gpu = sim._arr_gpu[cand_idx].astype(float)
        score = self.w * (age / amax) + (1.0 - self.w) * (1.0 - gpu / 8.0)
        return cand_idx[np.argsort(-score, kind="stable")]

def metrics(sim):
    jobs = [(j.arrival, j.place_time, 0) for j in sim.finished if j.place_time >= 0]
    sc = sorted(per_job_score(jobs)); n = len(sc)
    qs = sorted(j.queue_delay for j in sim.finished if j.queue_delay is not None)
    return dict(p1=round(sc[n//100],1), lt50=round(100.0*sum(1 for s in sc if s<50)/n,2),
                fair=round(sum(sc)/n,1), q_p50=round(qs[len(qs)//2]), n=n)

trace = load_trace("/home/mystous/projects/gpu_scheduler/sim/sweep_trace_vc.csv")
ovh = Overheads(enabled=True)
VARIANTS = [AgeSort(), SlurmAging(0.25), SlurmAging(0.5), SlurmAging(0.75), SlurmAging(0.5, blocking=False)]
res = {}
for gpu, kind in ((512,"hetero"),(512,"single"),(256,"hetero")):
    proto = build_nodes(gpu, kind)
    for pol in VARIANTS:
        nodes = [Node(name=x.name, gpu_type=x.gpu_type, total=x.total) for x in proto]
        jobs = [Job(id=i, arrival=a, duration=d, gpu_count=g, gpu_type="any", vc=vc) for i,a,d,g,vc in trace]
        sim = Simulator(jobs, nodes, pol, overheads=ovh); sim.run()
        m = metrics(sim); res[f"{gpu}_{kind}_{pol.name}"] = m
        print(f"{gpu} {kind:7} {pol.name:16} p1={m['p1']:6.1f} lt50={m['lt50']:6.2f} fair={m['fair']:6.1f} q_p50={m['q_p50']:>9}", flush=True)
json.dump(res, open("/tmp/fullreorder_results.json","w"), indent=1)
print("DONE")
