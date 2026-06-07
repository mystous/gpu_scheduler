"""스케줄링 정책 — 큐 정렬(order) + 배치(place). 한 곳에서 모두 정의.

C++ 코어(mostallocated/compact/round_robin)와 SQUAD(SFQA/auto/PTR), 그리고
SOTA 베이스라인(Tiresias-LAS, Themis, Lucid, Sia, Gandiva, Optimus, Pollux,
EASY-backfill, Kueue)을 통일 인터페이스로 구현.

배치 규칙(place)은 commit=False면 fit만 검사(점유 안 함), 엔진이 점유를 직접 수행.
SOTA 중 탄력성이 본질인 것(Optimus/Pollux/Sia)은 고정요청 트레이스에서 degenerate됨을
주석에 명시(general-purpose 조사 결론). 단일 GPU타입에선 Sia≈Pollux, 2D-LAS≈1D-LAS.
"""
from __future__ import annotations

import sys
import numpy as np
sys.path.insert(0, "/home/mystous/gpu_scheduler/squad_ctrl")
sys.path.insert(0, "/home/mystous/gpu_scheduler/sim")
from squad_algo import Server as AlgoServer, PendingJob, Params, Slot, reorder_queue, compute_r_table  # noqa: E402
from engine import speed_of  # noqa: E402  (이종 flavor-aware: 빠른 타입 우선 배치)


# ── 배치(node_pref) 헬퍼 — 엔진이 이 순서로 free GPU를 모아 멀티노드 gang 구성 ──────
# 이종 클러스터: 1차 키로 '빠른 타입 우선'(flavor-aware), 2차 키로 기존 정책 선호.
# 안정정렬이라 단일 타입에선 speed가 모두 같아 기존 순서 그대로(단일 결과 불변).
def _typed(job, nodes):
    """요청 타입과 호환되는 노드만(any는 모두)."""
    return [n for n in nodes if job.gpu_type in ("any", n.gpu_type) or n.gpu_type == "any"]


def pref_mostallocated(job, nodes):
    """C++ mostallocated: 빠른 타입 우선, 그 안에서 free 적은 노드 우선(단편화↓)."""
    return sorted(_typed(job, nodes), key=lambda n: (speed_of(n.gpu_type), n.free))


def pref_compact(job, nodes):
    """C++ compact: 빠른 타입 우선, 그 안에서 인덱스 순(앞 노드부터)."""
    return sorted(_typed(job, nodes), key=lambda n: speed_of(n.gpu_type))


def pref_bestfit_type(job, nodes):
    """이종 인지: 같은 타입 노드 먼저, 그 안에서 빠른 타입·mostallocated."""
    same = [n for n in nodes if n.gpu_type == job.gpu_type]
    rest = [n for n in nodes if n.gpu_type != job.gpu_type and n.gpu_type == "any"]
    return (sorted(same, key=lambda n: (speed_of(n.gpu_type), n.free)) +
            sorted(rest, key=lambda n: (speed_of(n.gpu_type), n.free)))


# ── 정책 베이스 ─────────────────────────────────────────────────────────────
class Policy:
    """order(cand_idx, age, ar, sim) → 배치 우선순위 인덱스 순서(numpy 또는 list).
    cand_idx: 도착했고 미배치인 잡의 인덱스(이미 도착순). age: cand_idx별 절대 누적 age 벡터.
    sim: SoA 배열(_arr_gpu/_arr_dur/_arr_arrival/_arr_attained/_arr_seq)·nodes·running 접근."""
    name = "base"
    blocking = False           # True면 order 선두가 안 들어가면 그 틱 배치 중단
    pref_fn = staticmethod(pref_mostallocated)

    def order(self, cand_idx, age, ar, sim):
        return cand_idx

    def node_pref(self, job, nodes):
        return self.pref_fn(job, nodes)


# ── 기본 큐 정책 ────────────────────────────────────────────────────────────
class FIFO(Policy):
    name = "fifo"; blocking = True
    def order(self, cand_idx, age, ar, sim):
        return cand_idx                                  # cand_idx는 이미 도착순


class SJF(Policy):
    name = "sjf"
    def order(self, cand_idx, age, ar, sim):
        return cand_idx[np.argsort(sim._arr_dur[cand_idx], kind="stable")]


class LAS(Policy):
    """Tiresias 2D-LAS: attained service(gpu_count×runtime) 작은 잡 우선.
    대기 잡은 attained=0이라 사실상 도착순. 선점 없으면 약함(조사 결론)."""
    name = "las"
    def order(self, cand_idx, age, ar, sim):
        return cand_idx[np.argsort(sim._arr_attained[cand_idx], kind="stable")]


class Themis(Policy):
    """finish-time fairness 근사: rho = (대기+잔여) / ideal. ideal=duration/fair_share.
    탄력·경매 생략(고정요청에선 ρ-우선 = 느린잡 우선). rho 큰 잡 우선."""
    name = "themis"
    def order(self, cand_idx, age, ar, sim):
        n = cand_idx.size
        fair = max(1.0, sim.total_gpu / max(1, n))
        gpu = sim._arr_gpu[cand_idx].astype(float)
        dur = sim._arr_dur[cand_idx]
        waited = sim.now - sim._arr_arrival[cand_idx]
        t_ideal = dur / np.minimum(fair, gpu) * gpu
        rho = (waited + dur) / np.maximum(t_ideal, 1.0)
        return cand_idx[np.argsort(-rho, kind="stable")]


class Lucid(Policy):
    """프로파일 기반 비선점 SJF + interference packing. 트레이스 재생이면 완벽 프로파일
    가정 → 정렬은 SJF, 배치는 compact(작은 서버부터 채워 단편화↓·collocation 유사)."""
    name = "lucid"; pref_fn = staticmethod(pref_compact)
    def order(self, wait, nodes, ar, sim):
        return sorted(wait, key=lambda j: j.duration)


class Sia(Policy):
    """이종 goodput 매칭(탄력 생략판): 타입 일치 best-fit 배치 + goodput 프록시 정렬.
    단일 타입이면 ≈ SJF(조사 결론). goodput∝1/duration 근사로 짧은·맞는 타입 우선."""
    name = "sia"; pref_fn = staticmethod(pref_bestfit_type)
    def order(self, wait, nodes, ar, sim):
        return sorted(wait, key=lambda j: j.duration)


# ── SQUAD ───────────────────────────────────────────────────────────────────
def _r_table_fast(nodes):
    """Resource suitability index R (저자 정의 — 서버마다 비교, 그 중 최댓값):
      각 서버 free에 대해: free ≥ req 면 1, 1개 부족할 때마다 0.1 감소(부족분 k → 1−0.1k).
      R[req-1] = max over servers (논문 line 10의 max{R_j, ...}).
    R[req-1], req=1..8."""
    R = [0.0] * 8
    for n in nodes:
        free = n.free
        for req in range(1, 9):
            short = req - free                       # 이 서버에서 req개에 부족한 수
            suit = 1.0 if short <= 0 else 1.0 - 0.1 * short
            if suit > R[req - 1]:
                R[req - 1] = suit                    # 서버 중 최댓값
    # floor 0
    return [x if x > 0 else 0.0 for x in R]


class SFQA(Policy):
    """고정 노브 SFQA: P*=P+α·A·R(AR≤β). 핫패스 최적화(객체 복사 제거, R 직접 계산).
    수식은 squad_algo.reorder_queue/C++ 원본과 동일.
    Algorithm 1: 큐 현재순서에서 P_i=1/2^i, P*_i=P_i+α·A_i·R. **P* 최댓값 잡 1개만**
    맨 앞으로 옮기고 나머지는 한 칸씩 뒤로(전체 정렬 아님, line 20-25).
    배치는 선두부터 못 넣으면 break(blocking=True, job_scheduler.cpp:19-21)."""
    name = "sfqa"; blocking = True
    def __init__(self, alpha=0.13889, beta=100.0):
        self.alpha = alpha; self.beta = beta
    def order(self, cand_idx, age, ar, sim):
        # cand_idx는 도착순. 미트리거(AR≥β)면 그대로.
        if cand_idx.size == 0 or ar >= self.beta:
            return cand_idx
        R = np.array(_r_table_fast(sim.nodes))
        gidx = np.clip(sim._arr_gpu[cand_idx].astype(int) - 1, 0, 7)
        n = cand_idx.size
        pos = np.arange(n)
        P = np.where(pos < 60, 1.0 / (2.0 ** np.minimum(pos, 60)), 0.0)
        pstar = P + self.alpha * age * R[gidx]        # P* = P + αA·R
        imax = int(np.argmax(pstar))                  # P* 최댓값 1개 (line 20)
        if imax == 0:
            return cand_idx
        return np.concatenate(([cand_idx[imax]], cand_idx[:imax], cand_idx[imax + 1:]))  # 단일승급


class SFQAAuto(Policy):
    """SFQA(논문) 식·동작 그대로, 계수 α·β만 적응적으로 결정. **duration(사후값) 미사용.**
    P*(j)=1/base^pos + α·A·R, 단일 승급, 트리거 β>AR. (age=신규 도착마다 +1.)

    적응(관측 가능값만 — age 통계·부하, 외부 상수 0개):
      **age는 절대 누적(engine 유지). order에서 큐 상대화**: age_rel = age − min(큐 age).
        dequeue(배치)로 큐 멤버가 바뀌면 min이 갱신돼 남은 잡들의 상대 age가 자동 재기준.
        과포화에서 절대 age가 무한 누적돼도, 상대 age는 '현재 큐 spread'로 제한돼 안정.
      A_ref = 큐 상대 age 평균(동적). α = 1 / (A_ref · R_min) → age_rel=A_ref인 '자리 맞는'
        (R=1) 잡의 보너스가 1/R_min배 증폭돼 base priority P(맨앞=1)를 넘는다.
      g(동적 게이트): S = max(age_rel)/A_ref, g=min(1,S).
    원리: 절대 age는 맨앞이 최대라 항상 no-op. 큐-상대 + R_min 정규화로 자리 맞는 잡의
      보너스를 증폭해 큐를 막는 큰 잡을 추월(starvation-free). 상수 0개, duration-free."""
    name = "sfqa-auto"; blocking = True
    def __init__(self, base=2.0, beta=101.0):
        self.base = base
        self.beta = beta           # 트리거 임계(AR≥β면 미발동). 101=항상 발동(포화에서도)
    def order(self, cand_idx, age, ar, sim):
        if cand_idx.size == 0 or ar >= self.beta:             # 트리거(β=101이면 항상 통과)
            return cand_idx
        Rr = np.array(_r_table_fast(sim.nodes)); Rr[Rr <= 0] = 0.5
        gidx = np.clip(sim._arr_gpu[cand_idx].astype(int) - 1, 0, 7)
        rq = Rr[gidx]                                          # 큐 잡들의 자리적합
        rmin = max(0.1, float(rq.min()))                       # 최악 자리적합(가장 큰 잡), floor 0.1
        age_rel = age - age.min()                              # 큐 상대 age(dequeue 시 자동 재기준)
        aref = max(1.0, float(age_rel.mean()))                 # 상대 age 스케일(동적, 큐 기준)
        S = (float(age_rel.max()) / aref) if cand_idx.size else 0.0   # starvation 압력
        g = min(1.0, S)                                        # 동적 게이트
        alpha_eff = g / (aref * rmin)                          # α=1/(A_ref·R_min): R차등이 P 넘게
        n = cand_idx.size
        pos = np.arange(n)
        P = np.where(pos < 60, 1.0 / (self.base ** np.minimum(pos, 60)), 0.0)
        pstar = P + alpha_eff * age_rel * rq                   # P*, 큐상대+R_min로 자리맞는 잡 승급
        imax = int(np.argmax(pstar))                           # 단일 승급(Algorithm 1)
        if imax == 0:
            return cand_idx
        return np.concatenate(([cand_idx[imax]], cand_idx[:imax], cand_idx[imax + 1:]))


# ── EASY-backfilling ────────────────────────────────────────────────────────
class EASY(Policy):
    """FIFO + 선두 예약 + 예약 침해 없는 backfill. duration(추정) 사용.
    실측 EASY와 동일 알고리즘. est_noise는 별도 주입(시뮬은 완벽 추정 기본)."""
    name = "easy"; blocking = False   # order()가 이미 허용집합만 반환
    def order(self, cand_idx, age, ar, sim):
        gpu = sim._arr_gpu; dur = sim._arr_dur                 # cand_idx는 이미 도착순(=FIFO)
        free = sum(n.free for n in sim.nodes)
        ends = sorted((j.finish_time, j.gpu_count) for j in sim.running.values())  # 종료시각 예측
        out = []
        cl = cand_idx.tolist()
        for k in range(len(cl)):
            i = cl[k]
            if gpu[i] <= free:
                out.append(i); free -= int(gpu[i]); continue
            # 예약 시각 T: 종료 누적으로 head(i) 확보 시점
            avail, T = free, None
            for end, g in ends:
                avail += g
                if avail >= gpu[i]:
                    T = end; break
            for j in cl[k + 1:]:                               # 예약 침해 없는 backfill
                if gpu[j] <= free and (T is None or sim.now + dur[j] <= T):
                    out.append(j); free -= int(gpu[j])
            break
        return out                                            # 허용집합(idx 리스트)


class Kueue(Policy):
    """BestEffortFIFO admission: 도착순, 들어갈 수 있는 잡 먼저(관대한 backfill).
    예약 없음 — blocking=False."""
    name = "kueue"
    def order(self, cand_idx, age, ar, sim):
        return cand_idx                                        # 도착순(engine 배치 루프가 backfill)


# ── FGD: Fragmentation Gradient Descent (Weng et al., USENIX ATC '23) ─────────
class FGD(Policy):
    """Fragmentation Gradient Descent — 단편화 인지 *배치* 휴리스틱.

    원논문(Weng et al. 2023)은 부분(fractional) GPU 공유 단편화를 대상으로, 노드의
    통계적 단편화를 '대상 워크로드에서 무작위 추출한 태스크가 쓸 수 없는 기대 GPU량'으로
    정의하고, 배치 시 단편화 증가(gradient)가 최소인 노드를 고른다. 본 구현은 동일한
    측도를 통째(whole) GPU gang 스케줄링에 충실히 특수화한 것이다:

      노드 n의 단편화  F_n = free_n · P(task_size > free_n)
        - P(·)는 트레이스의 GPU-수 분포 M (set_dist로 주입). free_n개 빈 GPU가
          '들어올 태스크가 못 쓸 확률'만큼 낭비로 계산 — 원논문 정의의 whole-GPU 형태.
      잡 g 배치의 단편화 기울기  ΔF_n = F(free_n − g) − F(free_n)
      → 실현 가능 노드 중 ΔF_n 최소(단편화를 가장 적게 늘리는) 노드 선택.

    큐 순서는 원논문(Kubernetes 기본 스케줄러 + FGD 스코어링 플러그인)대로 FCFS이며,
    부적합 잡은 보류하되 후속 잡 배치는 막지 않는다(kube-scheduler 동작, blocking=False).
    즉 FGD는 baseline FIFO와 *배치(node_pref)에서만* 다르므로 단편화 인지 배치의 순효과를
    분리 측정한다. (SQUAD의 SFQA는 큐를, PTR는 실행 중 이주를 다루는 직교 축.)"""
    name = "fgd"

    def __init__(self, size_dist=None):
        self.pdist = size_dist or {1: 1.0}

    def set_dist(self, gpu_counts):
        from collections import Counter
        c = Counter(int(g) for g in gpu_counts)
        tot = sum(c.values()) or 1
        self.pdist = {g: c[g] / tot for g in c}

    def _tail(self, x):                       # P(task_size > x)
        return sum(p for g, p in self.pdist.items() if g > x)

    def _frag(self, free):                    # F = free · P(size > free)
        return free * self._tail(free) if free > 0 else 0.0

    def order(self, cand_idx, age, ar, sim):
        return cand_idx                        # FCFS(도착순), 비차단 backfill

    def node_pref(self, job, nodes):
        g = job.gpu_count
        cand = _typed(job, nodes)

        def key(n):
            dF = (self._frag(n.free - g) - self._frag(n.free)) if n.free >= g else 1e18
            return (speed_of(n.gpu_type), dF, n.free)  # 빠른타입 우선(이종 정합), 그 안 ΔF 최소
        return sorted(cand, key=key)


# 주의: sfqa-auto-rsv(v3)는 EASY식 예약이 duration(사후값)에 의존해 SQUAD 철학 위반 → 제거.
# SQUAD에서 자리 비우기는 PTR(디프래그)이 담당. SFQA 라인은 duration-free만 유지.
POLICIES = {p.name: p for p in [FIFO, SJF, LAS, Themis, SFQA, SFQAAuto, EASY, Kueue, FGD]}


def make(name, **kw):
    if name in ("sfqa",):
        return SFQA(**kw)
    if name in ("sfqa-auto",):
        return SFQAAuto(**kw)
    if name == "fgd":
        return FGD(**kw)
    cls = {p.name: p for p in [FIFO, SJF, LAS, Themis, EASY, Kueue]}.get(name)
    if cls is None:
        raise ValueError(f"unknown policy: {name}")
    return cls()
