"""Sia (SOSP'23) 충실 구현 — 라운드 기반 goodput ILP 스케줄러(전용 시뮬).

논문 핵심(조사 + 논문 §3):
  - 60초 라운드. 매 라운드 활성 잡을 (n노드, r GPU, type) config에 ILP로 재배정.
  - goodput = throughput(type,r) × efficiency(batch). 탄력: 잡이 GPU수·타입 가변.
  - config 집합 C: 단일노드 2^k(≤R) + 멀티노드 whole-node. |C|=N+log2R per type.
  - row-normalize: G_ij ← N_min_i·G_ij/min_j G_ij
  - restart factor r_i=(T_i−N_i·S_i)/(T_i+S_i), 현재 config과 다른 칸에 곱(이주 억제).
  - 목적: max Σ_i Σ_j A_ij·(r_i·G_ij)^p + λ(1−‖A_i‖₁), 공정성 p=−0.5.
  - 제약: 잡당 config ≤1, 타입별 GPU 사용 ≤ 용량.
  - 선점·이주: 라운드마다 재배치, 이주 시 restart 비용(work에 패널티).
  - 탄력 부여: min_ngpus=1, max_ngpus=트레이스 gpu_count. preemptible=False면 rigid(타입만 가변).
  - 단일 GPU타입이면 Pollux로 수렴(타입 차원 소멸) — 이종에서 진가.

throughput 모델(Pollux 형, 타입별 α,β):
  T_iter(N,m) = (T_grad(m)^γ + T_sync(N)^γ)^(1/γ),  m=batch/N
  T_grad = a_grad + b_grad·m ;  T_sync = a_sync + b_sync·(N−1)
  THROUGHPUT = batch / T_iter
efficiency(M) = (φ+M0)/(φ+M)  (큰 배치일수록 통계효율 감소)

ILP은 작은 규모면 그대로, 크면 greedy(잡별 best (r_i·G)^p 칸을 용량 한도까지 채움)로 근사.
출력: 잡별 (queue_sec, service_sec, gpu_count) — fairness 호환. service=완료−시작(이주 포함 체류).
"""
from __future__ import annotations
from dataclasses import dataclass, field

# GPU 타입별 성능 계수 (상대 — 빠른 타입일수록 a/b 작음; 이종 비교용 기본값)
TYPE_PERF = {
    "b200": dict(a_grad=0.5, b_grad=0.010, a_sync=0.3, b_sync=0.05),
    "h100": dict(a_grad=0.7, b_grad=0.014, a_sync=0.4, b_sync=0.07),
    "a100": dict(a_grad=1.0, b_grad=0.020, a_sync=0.5, b_sync=0.10),
    "v100": dict(a_grad=2.0, b_grad=0.040, a_sync=0.8, b_sync=0.18),
}
GAMMA = 2.0
PHI = 1000.0       # gradient noise scale 프록시
M0 = 32.0          # 기준 배치


def _perf(t):
    return TYPE_PERF.get(t, TYPE_PERF["a100"])


def throughput(gpu_type, N, batch):
    p = _perf(gpu_type)
    m = batch / max(1, N)
    t_grad = p["a_grad"] + p["b_grad"] * m
    t_sync = p["a_sync"] + p["b_sync"] * (N - 1)
    t_iter = (t_grad ** GAMMA + t_sync ** GAMMA) ** (1.0 / GAMMA)
    return batch / t_iter


def efficiency(batch):
    return (PHI + M0) / (PHI + batch)


def goodput(gpu_type, r, batch):
    return throughput(gpu_type, r, batch) * efficiency(batch)


@dataclass
class SJob:
    id: str
    arrival: float
    duration: float          # 트레이스 wall-clock(기준 타입에서)
    gpu_count: int           # 트레이스 요청 = max_ngpus
    gpu_type: str = "any"
    preemptible: bool = True
    # 탄력 범위
    min_ngpus: int = 1
    # 동역학
    work: float = 0.0        # 총 일감(goodput·초). duration×기준goodput으로 환산
    done: float = 0.0
    place_time: float = -1.0
    finish_time: float = -1.0
    cur_cfg: tuple = None    # (n, r, type)
    n_restart: int = 0
    started: bool = False


class SiaSim:
    def __init__(self, jobs, nodes, overheads, round_s=60.0, p_fair=-0.5,
                 restart_cost_s=60.0, lam=1e6):
        self.jobs = {j.id: j for j in jobs}
        self.nodes = nodes        # Node(name, gpu_type, total)
        self.ovh = overheads
        self.round = round_s
        self.p = p_fair
        self.restart_cost = restart_cost_s
        self.lam = lam
        self.now = 0.0
        self.active = []
        self.finished = []
        self.total_gpu = sum(n.total for n in nodes)
        self.alloc_samples = []
        # 타입별 노드 그룹
        self.types = sorted(set(n.gpu_type for n in nodes))
        self.cap = {t: sum(n.total for n in nodes if n.gpu_type == t) for t in self.types}
        self.gpus_per_node = {t: max((n.total for n in nodes if n.gpu_type == t), default=8)
                              for t in self.types}
        self.nnodes = {t: sum(1 for n in nodes if n.gpu_type == t) for t in self.types}
        # work 환산: duration이 기준타입(가장 흔한)에서의 wall-clock이라 가정
        ref_t = max(self.cap, key=self.cap.get)
        for j in jobs:
            base_gp = goodput(ref_t, j.gpu_count, M0 * j.gpu_count)
            j.work = j.duration * base_gp
            j.min_ngpus = 1 if j.preemptible else j.gpu_count

    def _configs(self):
        """타입별 config (n,r,type): 단일노드 2^k≤R + 멀티노드 whole-node."""
        C = []
        for t in self.types:
            R = self.gpus_per_node[t]; N = self.nnodes[t]
            k = 1
            while k <= R:
                C.append((1, k, t)); k *= 2
            for n in range(2, N + 1):
                C.append((n, n * R, t))
        return C

    def _goodput_cfg(self, job, cfg):
        n, r, t = cfg
        if r < job.min_ngpus or r > job.gpu_count:    # 탄력 범위 [min, trace count]
            return 0.0
        if not job.preemptible and r != job.gpu_count:  # rigid: GPU 수 고정
            return 0.0
        batch = M0 * r
        return goodput(t, r, batch)

    def _round_alloc(self, prev):
        """그리디 ILP 근사: row-normalize + restart factor + fairness power, 용량 한도 채움."""
        C = self._configs()
        remain = dict(self.cap)
        # 각 잡의 후보 (효용, cfg) 리스트
        cand = {}
        for j in self.active:
            gs = [(c, self._goodput_cfg(j, c)) for c in C]
            gs = [(c, g) for c, g in gs if g > 0]
            if not gs:
                cand[j.id] = []; continue
            gmin = min(g for _, g in gs)
            T = max(1.0, self.now - j.arrival)
            r_i = max(0.0, (T - j.n_restart * self.restart_cost) / (T + self.restart_cost))
            util = []
            for c, g in gs:
                gn = j.min_ngpus * g / gmin           # row-normalize
                if prev.get(j.id) is not None and c != prev[j.id]:
                    gn *= r_i                          # restart factor(이주 억제)
                u = gn ** self.p if gn > 0 else 0      # fairness power
                util.append((u, c, c[1], c[2]))
            cand[j.id] = util
        # p<0이면 효용이 작을수록 좋음 → "이득" = -u 로 정렬해 greedy
        sign = -1 if self.p < 0 else 1
        # 잡 우선순위: 현재 최선 효용 기준(굶은·작은 잡 우선 경향)
        order = sorted(self.active, key=lambda j: -(sign * max((u for u, *_ in cand[j.id]), default=0)))
        alloc = {}
        for j in order:
            best = None
            for u, c, r, t in sorted(cand[j.id], key=lambda x: sign * x[0]):
                if remain.get(t, 0) >= r:
                    best = c; break
            if best is not None:
                alloc[j.id] = best
                remain[best[2]] -= best[1]
        return alloc

    def run(self):
        arr = sorted(self.jobs.values(), key=lambda x: x.arrival)
        ai = 0
        prev = {}
        # 라운드 진행
        end_horizon = max(j.arrival for j in arr) + sum(j.work for j in arr)  # 느슨한 상한
        while True:
            # 도착 처리
            while ai < len(arr) and arr[ai].arrival <= self.now:
                self.active.append(arr[ai]); ai += 1
            if not self.active and ai >= len(arr):
                break
            if not self.active:
                self.now = arr[ai].arrival; continue
            alloc = self._round_alloc(prev)
            used = 0
            for j in list(self.active):
                cfg = alloc.get(j.id)
                if cfg is None:
                    continue
                if not j.started:
                    j.started = True; j.place_time = self.now + self.ovh.place_cost(1)
                if prev.get(j.id) is not None and cfg != prev[j.id]:
                    j.n_restart += 1
                    j.done -= min(j.done, self.restart_cost *
                                  goodput(cfg[2], cfg[1], M0 * cfg[1]))  # 이주 손실
                gp = goodput(cfg[2], cfg[1], M0 * cfg[1])
                j.done += gp * self.round
                j.cur_cfg = cfg
                used += cfg[1]
                if j.done >= j.work:
                    j.finish_time = self.now + self.round
                    self.finished.append(j); self.active.remove(j)
            self.alloc_samples.append((self.now, used, self.total_gpu))
            prev = {j.id: j.cur_cfg for j in self.active if j.cur_cfg}
            self.now += self.round
            if self.now > end_horizon * 2 + 1e6:    # 안전장치
                break
        return self._results()

    def _results(self):
        rows = [(max(j.place_time - j.arrival, 0.0), max(j.finish_time - j.place_time, 0.1), j.gpu_count)
                for j in self.finished if j.place_time >= 0]
        qs = sorted(r[0] for r in rows)
        p = lambda a, x: a[min(len(a) - 1, int(len(a) * x))] if a else 0
        amax = max((u / t * 100 for _, u, t in self.alloc_samples), default=0)
        aavg = (sum(u / t * 100 for _, u, t in self.alloc_samples) /
                len(self.alloc_samples)) if self.alloc_samples else 0
        return {"n": len(self.finished),
                "q_p50": p(qs, .5), "q_p90": p(qs, .9), "q_p99": p(qs, .99),
                "q_max": qs[-1] if qs else 0, "alloc_max": amax, "alloc_avg": aavg,
                "alloc_series": self.alloc_samples, "rows": rows}
