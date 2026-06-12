"""제로베이스 리뷰 반영 변형 3종 — sim/policies.py 무수정(회귀 가드), 별도 정의.
  1) auto-noR   : SAFA에서 R 결합 제거(R≡1) — R1의 성분 ablation
  2) aging-fix  : 고전 priority aging(절대 나이×고정 α, R 없음, 항상 발동) — R1
  3) kueue-sfifo: Kueue StrictFIFO(per-VC head-blocking, borrowing 끔) — R3
구성: 512 hetero(헤드라인) + 512 single + 256 hetero. 지표: p1, lt50, fair_mean, q_p50.
"""
import sys, csv, os
sys.path.insert(0, "/home/mystous/projects/gpu_scheduler/sim")
sys.path.insert(0, "/home/mystous/projects/gpu_scheduler/squad_ctrl")
sys.path.insert(0, "/home/mystous/projects/gpu_scheduler/k8s_replay")
import numpy as np
import policies as P
from engine import Job, Node, Overheads, Simulator
from run_sweep import load_trace, build_nodes
from order_fairness import per_job_score

class SFQAAutoNoR(P.SFQAAuto):
    """SAFA와 동일하되 R≡1 (자원 적합도 결합 제거)."""
    name = "auto-noR"
    def order(self, cand_idx, age, ar, sim):
        if cand_idx.size == 0:
            return cand_idx
        rq = np.ones(cand_idx.size)                       # R ≡ 1
        rmin = 1.0
        age_rel = age - age.min()
        aref = max(1.0, float(age_rel.mean()))
        g = min(1.0, float(age_rel.max()) / aref)
        alpha_eff = g / (aref * rmin)
        n = cand_idx.size; pos = np.arange(n)
        Pb = np.where(pos < 60, 1.0 / (self.base ** np.minimum(pos, 60)), 0.0)
        pstar = Pb + alpha_eff * age_rel * rq
        imax = int(np.argmax(pstar))
        if imax == 0:
            return cand_idx
        return np.concatenate(([cand_idx[imax]], cand_idx[:imax], cand_idx[imax + 1:]))

class AgingClassic(P.Policy):
    """고전 priority aging: P* = P + α·A(절대 나이), 고정 α=0.13889, R 없음, 항상 발동."""
    name = "aging-fix"; blocking = True
    def __init__(self, alpha=0.13889):
        self.alpha = alpha
    def order(self, cand_idx, age, ar, sim):
        if cand_idx.size == 0:
            return cand_idx
        n = cand_idx.size; pos = np.arange(n)
        Pb = np.where(pos < 60, 1.0 / (2.0 ** np.minimum(pos, 60)), 0.0)
        pstar = Pb + self.alpha * age                     # 절대 누적 age, R 없음
        imax = int(np.argmax(pstar))
        if imax == 0:
            return cand_idx
        return np.concatenate(([cand_idx[imax]], cand_idx[:imax], cand_idx[imax + 1:]))

class KueueStrict(P.Kueue):
    """Kueue StrictFIFO: VC별 도착순 head만 후보(그 뒤는 그 VC 블록), borrowing 끔
    (usage+req > quota인 VC는 이번 패스 스킵). blocking=False지만 VC 내 순서는 엄격."""
    name = "kueue-sfifo"; blocking = False
    def order(self, cand_idx, age, ar, sim):
        if cand_idx.size == 0:
            return cand_idx
        self._ensure_quota(sim)
        usage = {}
        for j in sim.running.values():
            usage[j.vc] = usage.get(j.vc, 0.0) + j.gpu_count
        out = []
        seen_vc = set()
        for ii in cand_idx:                               # cand_idx = 도착순
            v = sim._arr_vc[ii]
            if v in seen_vc:
                continue                                  # VC head 뒤는 head-blocking
            seen_vc.add(v)
            req = float(sim._arr_gpu[ii])
            if usage.get(v, 0.0) + req > self._quota.get(v, 1.0):
                continue                                  # 쿼타 초과 → borrowing 없음, 스킵
            out.append(ii)
        return np.array(out, dtype=cand_idx.dtype)

def metrics(sim):
    jobs = [(j.arrival, j.place_time, 0) for j in sim.finished if j.place_time >= 0]
    sc = sorted(per_job_score(jobs)); n = len(sc)
    qs = sorted(j.queue_delay for j in sim.finished if j.queue_delay is not None)
    return dict(p1=sc[n // 100], lt50=100.0 * sum(1 for s in sc if s < 50) / n,
                fair=sum(sc) / n, q_p50=qs[len(qs) // 2], n=n)

trace = load_trace("/home/mystous/projects/gpu_scheduler/sim/sweep_trace_vc.csv")
ovh = Overheads(enabled=True)
VARIANTS = [SFQAAutoNoR(), AgingClassic(), KueueStrict()]
print(f"{'config':14} {'policy':12} {'p1':>6} {'lt50%':>6} {'fair':>6} {'q_p50':>10} {'n':>7}")
results = {}
for gpu, kind in ((512, "hetero"), (512, "single"), (256, "hetero")):
    nodes_proto = build_nodes(gpu, kind)
    for pol in VARIANTS:
        nodes = [Node(name=x.name, gpu_type=x.gpu_type, total=x.total) for x in nodes_proto]
        if isinstance(pol, P.Kueue):
            pol._quota = None                             # 구성별 쿼타 재계산
        jobs = [Job(id=i, arrival=a, duration=d, gpu_count=g, gpu_type="any", vc=vc)
                for i, a, d, g, vc in trace]
        sim = Simulator(jobs, nodes, pol, overheads=ovh)
        sim.run()
        m = metrics(sim)
        results[(gpu, kind, pol.name)] = m
        print(f"{gpu} {kind:9} {pol.name:12} {m['p1']:6.1f} {m['lt50']:6.1f} {m['fair']:6.1f} {m['q_p50']:10.0f} {m['n']:7}")
import json
json.dump({f"{k[0]}_{k[1]}_{k[2]}": v for k, v in results.items()}, open("/tmp/variants_results.json", "w"), indent=1)
print("→ /tmp/variants_results.json")
