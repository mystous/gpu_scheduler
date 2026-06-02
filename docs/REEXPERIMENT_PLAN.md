# SQUAD 재실험 설계 (K8S + H100/B200 실측)

> 목적: `reject/`의 4개 리젝(CCGrid2025, IEEE Cloud 2025, MASCOTS 2025, Journal of Cloud Computing)을
> 정통으로 해결하기 위해, 기존 **C++ 시뮬레이터 전용** 평가를 **실제 K8S 클러스터 + 실측**으로 재구성한다.

## 1. 리젝 사유 → 재실험 요구사항 매핑

| 공통 리젝 사유 | 빈도 | 재실험 대응 |
|---|---|---|
| ① 시뮬레이션만, 실제 클러스터 없음 | 전 venue | **실제 K8S(H100/B200)에 SQUAD 통합·실측** |
| ② GPU 선점/재배치 비현실성·오버헤드 미측정 (PipeSwitch, Singularity) | IEEE Cloud R5, CCGrid R3, MASCOTS R2 | **실제 재배치 다운타임 측정**(checkpoint+evict+resume), 메모리 경합 측정 |
| ③ 베이스라인·관련연구 빈약 | 전 venue | Tiresias/Themis/Optimus/Lucid/Sia/Kueue/CFS 비교, related work 보강 |
| ④ 저자 생성(합성) 데이터 | MASCOTS R3, CCGrid R3 | 실제 트레이스(사내 3개월 로그 + 공개 트레이스) 재생 |
| ⑤ 노브(α,β,ω,δ) 과다 + 오프라인 grid search | IEEE Cloud R1·R2, MASCOTS R2, JoCC R1 | 튜닝 비용 정량화 + 간단한 온라인 적응 휴리스틱 baseline |
| ⑥ 규모 작음(<8 GPU) | MASCOTS R3 | H100 3노드/B200 1노드 + 시뮬레이터로 스케일 보완 |
| ⑦ 글쓰기/명확성 부족 (tasks vs jobs 혼용, 생성형 AI 느낌, 용어 미정의) | IEEE Cloud R3·R5, CCGrid R2, JoCC R2 | 용어 통일·정의 명확화·재작성, 알고리즘 서술 정교화 |

> JoCC R1이 명시적으로 허용한 형태: "K8S + GPU plugin 실통합 **또는** 최소한 network/IO 오버헤드를 모델링하는
> 검증된 시뮬레이터(Kairos 등)". → **실측 + 시뮬레이터 하이브리드**가 정답.

## 2. SQUAD 두 알고리즘 (논문 확정 정의)

두 알고리즘 모두 **코어 스케줄러 실행 전에 동작하는 전처리 메커니즘**이며 서로 독립적.

### 2.1 Starvation-Free Queue Adjustment (SFQA) — Alg.1, Eq.1
```
P* = P + α·A·R   if β > AR
P* = P           otherwise
```
- `P`: 원 우선순위. p_i = 1/2^i (p0=1, p1=0.5, ...), n = 3 × 서버 수
- `α` (age_weight): starvation index 가중치 (0.01–1.99)
- `A`: 대기 나이, 10분마다 +1, 스케줄되면 reset
- `R`: resource suitability index. 요청==가용이면 1, 초과 1개당 −0.1
- `β` (svp_upper): 발동 임계 할당률 (80–95%). 최근 할당률 AR < β일 때만 큐 재정렬
- **특징: 대기(pending) job 순서만 변경 → 실행 중 job 미관여 → 실측 위험 낮음**

### 2.2 Preemptive Task Reallocation / Defragmentation (PTR) — Alg.2, Eq.2–6
- 실행 중 preemptive task를 이주시켜 **완전히 빈 서버 수 F를 최대화**하는 DP(메모이제이션).
- `f(a_j, t_r, M_j) = 1 if a'_j == M_j else 0` (재배치 후 서버가 정확히 꽉 비면 1)
- `δ` (reorder_count): DP 재귀 호출 상한 (100k–500k)
- `ω` (preemption_task_window): 대기큐 길이 ≥ ω 일 때만 발동 (10–200)
- **논문이 명시: 재배치는 OS 커널 레벨이 아니라 "job 정지→재배치→재개"이며 downtime 발생** (← 측정 안 함, 리젝 ②의 핵심)

### 2.3 기존 코드 매핑
| 논문 | 코드 위치 |
|---|---|
| SFQA, Eq.1 | `job_scheduler` (prevent_starvation, svp_upper=β, age_weight=α) + `job_age_struct` |
| PTR DP, Eq.2–6 | `adjusting_server` (reorder_count=δ, preemption_task_window=ω) |
| 가속기 타입 | `enum_definition.h` — h100/h200/b200 이미 정의됨 |

## 3. 목표 아키텍처 (하이브리드)

```
┌─ 실제 K8S 레이어 (신규) ─────────────────────────────────────────┐
│  ① SFQA = kube-scheduler 플러그인 (QueueSort) + P* 계산 컨트롤러  │
│     대기 Pod P* = P + α·A·R 계산 → 스케줄링 큐 정렬               │
│     ※ 로직은 기존 C++ job_scheduler Eq.1 구현을 그대로 포팅       │
│  ② PTR = defrag 컨트롤러(별도 controller/operator)               │
│     DP로 이주 대상 선정 → checkpoint → evict → 타겟 노드 재배치   │
│     ※ DP 로직은 기존 C++ adjusting_server 구현을 그대로 포팅      │
│  Workload Generator: 트레이스 재생 → 실제 학습/추론 컨테이너      │
│   gang 스케줄링: Coscheduling 플러그인 (QueueSort 공유 주의→R1)   │
│  하드웨어: H100 x3 node, B200 x1 node                            │
│  메트릭: DCGM-exporter + Prometheus                              │
│   → JCT, 할당률, GPU util, 실제 이주 downtime, 메모리 경합        │
└──────────────────────────────────────────────────────────────────┘
                  ▲ 실측 오버헤드로 보정/검증 ▼
┌─ 시뮬레이터 레이어 (기존 C++ 재활용) ────────────────────────────┐
│  대규모 파라미터 스윕 + 계수(α,β,ω,δ) 최적화                      │
│  실측 downtime 값으로 오버헤드 모델 캘리브레이션                  │
│  B200/H100 서버 프로파일, 실제 트레이스 replay                    │
└──────────────────────────────────────────────────────────────────┘
```

> **구현 원칙**: SFQA·PTR 알고리즘은 새로 설계하지 않고 **기존 C++ 소스의 검증된 로직을
> 그대로 이식**한다. SFQA는 `job_scheduler`의 우선순위/나이 계산(Eq.1), PTR은
> `adjusting_server`의 DP+메모이제이션(Eq.2–6)을 Go(플러그인)/컨트롤러로 포팅한다.
> 시뮬레이터와 실측 레이어가 **동일 알고리즘**을 쓰도록 보장해 결과 비교 가능성을 확보한다.

> **⚠ 설계 리스크** (상세: `docs/REEXPERIMENT_PLAN_REVIEW.md`)
> - **R1 (QueueSort 단일 제약)**: kube-scheduler는 QueueSort 플러그인을 **하나만** 허용하고
>   Coscheduling(gang)도 QueueSort를 사용한다 → SFQA QueueSort와 충돌.
>   해결: **PodGroup back-to-back 정렬 + P* 정렬을 모두 처리하는 단일 통합 QueueSort 플러그인**으로 구현.
> - **R2 (클러스터 상태 접근)**: QueueSort의 `Less(p1,p2)`는 두 Pod 정보만 받아 트리거 조건(AR<β)과
>   R(자원 적합도)에 필요한 클러스터 할당률을 직접 못 본다 → **별도 컨트롤러가 P*/AR/R을 주기적으로
>   계산해 Pod annotation/priority로 주입**하고 QueueSort는 그 값으로 정렬만 수행.

### 재배치(이주) 메커니즘 후보 — 워크로드별
| 워크로드 | 이주 방법 | 측정 다운타임 구성 |
|---|---|---|
| 학습(LLM finetune) | app-level checkpoint(Megatron/DeepSpeed/torch) → kill → 재배치 → resume | 체크포인트 저장 + pod teardown + 이미지/데이터 재적재 + resume-to-throughput |
| 학습/임의 | NVIDIA `cuda-checkpoint` + CRIU (H100/Hopper 지원 확인; **B200/Blackwell는 드라이버·CUDA 버전 지원 확인 필요**) | 투명 C/R 시간 (PipeSwitch/Singularity 반박 근거) |
| 추론(vLLM) | drain → kill → 타겟 노드 재기동 | 모델 weight 재적재(지배적) + warmup |

## 4. 단계별 로드맵

- **Phase 0 — 기반**: K8S 클러스터 라벨링(H100/B200), kube-scheduler-plugins(Coscheduling)+DCGM-exporter+Prometheus 설치, 트레이스→K8S Job 변환기, 메트릭 수집 파이프라인.
- **Phase 1 — SFQA 실측 (필수)**: P* 계산 컨트롤러 + 통합 QueueSort 플러그인(R1·R2 반영). baseline(default-scheduler FIFO / PriorityClass) 대비 JCT·할당률. **저위험·확실한 실제 결과.**
- **Phase 2 — PTR 실측 (권장)**: DP 이주 선정 + checkpoint 이주 실행 + **실제 다운타임 측정**. 작게(노드 1개 비우기)라도 실측 → 리젝 ② 정면 반박. memory contention 동시 측정.
- **Phase 3 — 시뮬레이터 스케일/튜닝**: 실측 오버헤드로 시뮬레이터 보정, 대규모 스윕으로 계수 최적화 + 튜닝 비용 정량화(리젝 ⑤).
- **Phase 4 — 베이스라인·작성**: SOTA 비교, related work 보강, 글쓰기 정리(리젝 ③⑦).

## 5. 확정된 결정 사항
- **K8S 기반**: kube-scheduler 플러그인 (Scheduler Framework, QueueSort 확장점). gang은 Coscheduling 플러그인.
- **트레이스 출처**: 사내 3개월 로그(H100/B200 remap) + **공개 트레이스(Alibaba GPU trace / Philly) 추가** — 일반화 입증(리젝 ④ 대응).
- **알고리즘**: 기존 C++ 소스(`job_scheduler` Eq.1, `adjusting_server` Eq.2–6) 로직을 포팅·참조. 신규 설계 금지.

## 6. 미확정 사항
- Phase 2 이주 방법: app-level checkpoint(학습) vs NVIDIA `cuda-checkpoint`+CRIU(투명) — Phase 2 착수 시 PoC로 결정.
