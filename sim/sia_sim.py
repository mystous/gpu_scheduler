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

라운드 배정은 pulp(CBC) ILP로 전역 최적 패킹을 푼다(원논문 충실):
  - 결정변수 x[j,c]∈{0,1}: 활성 잡 j를 후보 config c에 배정.
  - 목적: max Σ x[j,c]·(sign·u[j,c]). u는 row-normalize·restart·fairness power 효용
    (기존 greedy 효용과 동일), sign=−1(p<0) 또는 +1(p≥0)로 greedy 정렬 부호와 일치.
  - 제약: 잡당 config ≤1, 타입별 GPU 사용 Σ x·gpus(c) ≤ cap[t].
  - CBC에 라운드 시간 제한(round budget)을 둠. 변수 과다(잡수×config수 > 임계)·시간초과·
    솔버 실패 시 기존 greedy로 graceful fallback. greedy는 전역 패킹을 못 해 GPU를
    27–35% 비우는 artifact가 있으나, ILP가 이를 전역 최적으로 메운다.

throughput 모델(Pollux 형, 타입별 α,β):
  T_iter(N,m) = (T_grad(m)^γ + T_sync(N)^γ)^(1/γ),  m=batch/N
  T_grad = a_grad + b_grad·m ;  T_sync = a_sync + b_sync·(N−1)
  THROUGHPUT = batch / T_iter
efficiency(M) = (φ+M0)/(φ+M)  (큰 배치일수록 통계효율 감소)

기본은 ILP(pulp/CBC) 전역 배정. 변수 과다·시간초과·솔버부재면 greedy(잡별 best (r_i·G)^p
칸을 용량 한도까지 채움)로 graceful fallback.
출력: 잡별 (queue_sec, service_sec, gpu_count) — fairness 호환. service=완료−시작(이주 포함 체류).

결론 — 계산 overhead가 명백한 단점:
  라운드마다 '활성 잡 전체 × config goodput'을 평가하므로, 부하가 높을수록 라운드당 비용과
  총 라운드 수가 함께 폭증한다. 실측(Philly 111k, b200):
    - 256 GPU 극과부하(3.6×) 단일 sia ≈ 2시간 (engine 정책 ~30초 대비 200배+)
    - 512 GPU 과부하(1.8×) 이종 sia ≈ 100분
    - 1024 GPU 저부하(0.9×)에선 ~수분 (활성 잡 적어 빠름)
  즉 goodput-최적 라운드 ILP의 정확성을 얻는 대가가 스케줄링 계산 비용이다(부하에 민감).
  완화: 실제 K8s에선 스케줄 주기(60–300s)가 길고 결정 지연이 JCT(수시간)에 거의 무영향이라
  운영상 부담은 작다. 그러나 (a) 대규모 시뮬 wall-clock 부담, (b) 초대규모·고빈도 클러스터의
  실시간 스케줄링 병목 가능성은 남으며 — 원 논문도 ILP에 시간 제한(round budget)을 둔다.
  반면 SQUAD(SFQA/sfqa-auto)는 단일 승급 O(n)·벡터화로 부하 무관하게 ~수십 초로 경량이다.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

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

    # ILP 변수 수 가드: 잡수×config수가 이를 넘으면 greedy fallback
    ILP_MAX_VARS = 50000
    ILP_TIME_LIMIT_S = 4.0          # 라운드당 HiGHS 시간 제한. 초과 시 incumbent(유효 ILP 해) 채택

    def _build_cand(self, prev):
        """각 활성 잡의 후보 효용 리스트 cand[j.id] = [(u, cfg, gpus, type), ...] 와 sign 반환.
        효용 u = row-normalize × restart factor × fairness power (greedy·ILP 공용)."""
        C = self._configs()
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
        # p<0이면 효용이 작을수록 좋음 → "이득" = sign·u 를 최대화
        sign = -1 if self.p < 0 else 1
        return cand, sign

    def _round_alloc(self, prev):
        """라운드 배정. 기본 ILP(pulp/CBC) 전역 최적, 실패·과대 시 greedy fallback."""
        if not self.active:
            return {}
        cand, sign = self._build_cand(prev)
        nvars = sum(len(v) for v in cand.values())
        if nvars == 0:
            return {}
        if nvars <= self.ILP_MAX_VARS:                # 변수 과다 시 greedy로 우회
            alloc = self._round_alloc_ilp(cand, sign)
            if alloc is not None:
                return alloc
        return self._round_alloc_greedy(cand, sign)

    def _round_alloc_ilp(self, cand, sign):
        """ILP 배정: max Σ x[j,c]·(λ + sign·u). 잡당 ≤1 config, 타입별 GPU ≤ cap.

        **알고리즘은 그대로**(저자 sia.py와 동일 ILP 정식화), 구현만 저자처럼 행렬화한다:
        cvxpy 부울 변수 + scipy.sparse 제약행렬 + HiGHS 솔버. 이전 python-mip 원소별 모델
        구성은 활성 잡 수만 개에서 라운드당 수 분이 걸렸으나(과부하 백로그), 행렬 정식화는
        구성 0초·풀이 수초로 동일 최적해를 낸다(활성 26k에서 ~5초). 후보 K개 제한 같은
        알고리즘 변경 없이 '활성 전체에 대한 ILP'를 그대로 푼다. 솔버 부재 시 None(→greedy).

        목적계수 = (sign·u) + λ. λ(=Sia 원목적의 배정 인센티브 항)은 모든 |sign·u| 범위보다
        충분히 크게 잡아 (1) 가능한 한 많은 잡을 배정해 GPU를 채우고, (2) 동률에서 sign·u가
        좋은 config을 고르게 한다(p<0에서 '아무것도 배정 안 함' 퇴화해 방지)."""
        try:
            import highspy
            import scipy.sparse as sp
        except Exception:
            return None
        # 후보 평탄화(벡터화 — 원소별 파이썬 모델 구성 회피)
        coef = []            # 목적계수 λ+sign·u (후보별)
        job_row = []         # 후보의 잡 인덱스(잡당 ≤1 제약)
        gpus_of = []         # 후보의 GPU 수(타입 용량 제약)
        type_row = []        # 후보의 타입 인덱스
        meta = []            # (jid, cfg) — 해 추출용
        jmap = {}
        types = list(self.cap.keys())
        tmap = {t: i for i, t in enumerate(types)}
        all_u = 0.0
        for jid, util in cand.items():
            if not util:
                continue
            ji = jmap.setdefault(jid, len(jmap))
            for (u, c, gpus, t) in util:
                if t not in tmap:
                    continue
                coef.append(sign * u)                 # λ는 풀이 후 일괄 가산
                job_row.append(ji); gpus_of.append(float(gpus))
                type_row.append(tmap[t]); meta.append((jid, c))
                au = abs(u)
                if au > all_u:
                    all_u = au
        M = len(coef)
        if M == 0:
            return None
        njobs = len(jmap)
        lam = all_u * (len(self.active) + 1.0) + 1.0
        coef = np.asarray(coef) + lam                 # 배정 인센티브 λ 일괄 가산
        cols = np.arange(M)
        # 제약행렬 A = [J; T] (잡당 ≤1 njobs행 + 타입별 용량 types행), CSC로 HiGHS에 직접 주입.
        J = sp.csr_matrix((np.ones(M), (np.asarray(job_row), cols)), shape=(njobs, M))
        T = sp.csr_matrix((np.asarray(gpus_of), (np.asarray(type_row), cols)), shape=(len(types), M))
        A = sp.vstack([J, T]).tocsc()
        nrow = njobs + len(types)
        row_upper = np.concatenate([np.ones(njobs),
                                    np.asarray([float(self.cap[t]) for t in types])])
        # HiGHS 직접 호출(highspy) — cvxpy canonicalization 오버헤드(이종 ~10만 변수에서 멀티스레드
        # BLAS로 느리고 time_limit 미적용)를 제거. 동일 ILP 정식화·동일 알고리즘, 솔버 코어만 직접
        # 구동(저자 sia.py가 cvxpy→CBC를 쓰는 것과 동류, 여기선 highspy→HiGHS). 라운드당 수십~수백
        # ms. time_limit 초과 시 실행가능 incumbent(유효 ILP 해)를 수용한다.
        try:
            inf = highspy.kHighsInf
            h = highspy.Highs()
            h.setOptionValue("output_flag", False)
            h.setOptionValue("time_limit", float(self.ILP_TIME_LIMIT_S))
            h.setOptionValue("mip_rel_gap", 1e-3)
            h.setOptionValue("threads", 1)
            lp = highspy.HighsLp()
            lp.num_col_ = int(M); lp.num_row_ = int(nrow)
            lp.sense_ = highspy.ObjSense.kMaximize
            lp.col_cost_ = coef.astype(np.double)
            lp.col_lower_ = np.zeros(M); lp.col_upper_ = np.ones(M)
            lp.row_lower_ = np.full(nrow, -inf); lp.row_upper_ = row_upper
            lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
            lp.a_matrix_.start_ = A.indptr.astype(np.int32)
            lp.a_matrix_.index_ = A.indices.astype(np.int32)
            lp.a_matrix_.value_ = A.data.astype(np.double)
            lp.integrality_ = np.array([highspy.HighsVarType.kInteger] * M)
            h.passModel(lp)
            h.run()
            xv = np.asarray(h.getSolution().col_value)
        except Exception:
            return None
        if xv.size != M:                               # 해 없음 → greedy fallback
            return None
        alloc = {}
        for idx in np.nonzero(xv > 0.5)[0]:
            jid, c = meta[idx]
            if jid not in alloc:                       # 잡당 1개(제약상 보장되나 안전)
                alloc[jid] = c
        return alloc

    def _round_alloc_greedy(self, cand, sign):
        """그리디 fallback: 잡별 best 효용 칸을 타입 용량 한도까지 채움(전역 패킹 미보장)."""
        remain = dict(self.cap)
        # 잡 우선순위: 현재 최선 효용 기준(굶은·작은 잡 우선 경향)
        order = sorted(self.active,
                       key=lambda j: -(sign * max((u for u, *_ in cand[j.id]), default=0)))
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

    def run(self, progress_every=2000):
        import sys
        arr = sorted(self.jobs.values(), key=lambda x: x.arrival)
        ai = 0
        prev = {}
        rc = 0                                              # 라운드 카운터(진행 추세 로그용)
        ntot = len(arr)
        cache_sig = None; cache_alloc = None; since_solve = 0
        REFRESH = 50          # 활성·prev 불변이라도 이 라운드마다 재계산(나이 T drift 반영)
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
            # 캐시: 활성 집합·prev(이주 상태)가 불변이면 동일 ILP → 솔버 재호출 생략.
            # 긴 잡이 수백 라운드 도는 안정 구간에서 라운드당 솔버 서브프로세스 오버헤드 제거.
            sig = (frozenset(j.id for j in self.active), frozenset(prev.items()))
            if alloc_cached := (sig == cache_sig and since_solve < REFRESH):
                alloc = cache_alloc
                since_solve += 1
            else:
                alloc = self._round_alloc(prev)
                cache_sig = sig; cache_alloc = alloc; since_solve = 0
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
            rc += 1
            if progress_every and rc % progress_every == 0:  # 진행 추세: 라운드·도착·완료·활성
                print(f"    [sia] round={rc} arrived={ai}/{ntot} fin={len(self.finished)} "
                      f"active={len(self.active)}", flush=True, file=sys.stderr)
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
