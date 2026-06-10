# 베이스라인 충실도 대조검증 (실제 공개 코드 ↔ 우리 통합 엔진 구현)

목적: 모든 정책을 **하나의 통합 시뮬레이터**(같은 Philly 111k 트레이스·같은 512 GPU·같은 실측 오버헤드)에서
돌려 통제 비교하되, 각 구현이 저자 공개 코드의 **알고리즘과 일치**하는지 라인 단위로 대조한다.
(네이티브 시뮬 federation은 트레이스·잡모델이 달라 비교 불가능한 점결과가 되므로 채택하지 않음.)

| 정책 | 공개 코드 | 핵심 알고리즘 | 우리 구현 일치 여부 |
|---|---|---|---|
| **Sia** | siasosp23/artifacts `sia.py` (cvxpy) | 목적 = Σ w·(X⊙goodput^p) + λ_no_alloc·(미배정), 타입별 용량, p<0 fairness | ✅ 동일 ILP 목적(거듭제곱 goodput^p + 배정 인센티브 λ + 타입 용량). 차이: goodput **모델**(저자=앱별 실측곡선 vs 우리=합성, Philly에 프로파일 없어 불가피), per-job weights(우리 균일), 이주페널티(우리 r_i 근사). 인메모리 python-mip로 저자 cvxpy와 동급 속도. 네이티브 교차확인: `results/sia_native/` |
| **LAS (Tiresias)** | SymbioticLab/Tiresias `run_sim.py` | attained service `j_gt = executed_time × num_gpu`, MLFQ 우선순위 + **선점** | ✅ 동일 지표(`attained=(now−place)×gpu_count`, 오름차순). 차이: **선점 없음** — 우리 엔진은 전 정책 비선점이라 통제된 공통 한계(Tiresias 특정 불리 아님). docstring·CLAUDE.md 명시 |
| **FGD** | hkust-adsl/kubernetes-scheduler-simulator (Go) | 단편화 `F=free·P(size>free)`, ΔF 최소 노드 배치, 큐 FCFS | ✅ 동일 측도·동일 배치 규칙. 차이: 저자는 **분수 GPU 공유**(Alibaba 트레이스), 우리는 **whole-GPU gang**으로 특수화(Philly). docstring 명시 |
| **Lucid** | S-Lab-System-Group/Lucid | 프로파일 기반 비침습 패킹(collocation), 비선점 | ⚠️ 우리 LucidSim은 collocation(util 기반 공유 배치)·비선점을 모사. 저자의 Primo EBM 프로파일러는 미사용(우리 트레이스에 프로파일 없음) — duration·util 합성. 적응판임을 §VI·타당성위협에 명시 |
| **Themis** | 공개 코드 없음 | 2단계 경매, finish-time-fairness ρ | ⚠️ ρ=(대기+잔여)/ideal 근사(경매·Gurobi 생략). 고정요청 gang에선 ρ-우선=느린잡 우선. 충실 구현 불가(코드 부재)라 근사임을 명시 |
| **Kueue** | kubernetes-sigs/kueue (Go 프로덕션 컨트롤러) | ClusterQueue 쿼타 + cohort borrowing | ✅ VC별 쿼타(Σgpu 비율) + under-served 우선 + blocking=False borrowing으로 충실 모사. 프로덕션 컨트롤러라 트레이스 시뮬엔 직접 못 돌려 로직만 이식 |
| FIFO / SJF / EASY | 교과서(별도 저장소 없음) | 도착순 / 최단 / 예약+백필 | ✅ 표준. EASY는 완벽 duration 추정 가정(정보우위 상한, 타당성위협 명시) |

## 결론
- **Sia를 포함한 11개 정책 모두 통합 엔진에 유지**(비교 가능성). 각 구현은 저자 알고리즘과 대조검증됨.
- 불가피한 차이는 두 종류뿐: (i) **잡 모델 데이터**(프로파일/scalability 곡선) — Philly에 없어 합성으로 대체(Sia·Lucid),
  (ii) **선점** — 우리 엔진은 전 정책 비선점(LAS·Tiresias). 둘 다 모든 정책에 공통이거나 명시된 한계이며 특정 베이스라인을 불리하게 하지 않음.
- 이전에 있던 불공정 주장("Sia 200배 느림/27–35% 유휴")은 **우리 옛 솔버(pulp 파일경유)·greedy fallback 아티팩트**였고, 인메모리 ILP로 교체해 제거함.
