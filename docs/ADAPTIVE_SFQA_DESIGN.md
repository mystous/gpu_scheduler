# Zero-Knob Adaptive SFQA (v2) — 이론 기반 설계 (실험 미착수)

> 상태: **설계 단계, 구현·실험 보류** (사용자 지시 "실험은 진행하지마", 2026-06-04).
> v1(c₁·Ê[W] 휴리스틱)은 이론 근거 부족으로 폐기 — §9 변경 이력 참조.
> 비교 기준 실측: `/raid/squad/analysis/SUMMARY.md` (Philly 1000, SFQA max=782s 최저 / p50=243s 최악).

## 1. 알고리즘의 이론적 정식화

스케줄러를 다음 **제약 최적화 문제의 온라인 근사**로 정의한다:

```
minimize   mean JCT                          (효율)
subject to BSLDᵢ(t) ≤ σ*(t)   ∀ 대기 job i   (공정성 제약)
```

| 구성요소 | 정의 | 이론 근거 |
|---|---|---|
| 목적함수의 최적해 | 제약이 느슨할 때 **SJF 순서** | Smith(1956)·Schrage(1968): 최단 작업 우선이 평균 완료시간 최적 |
| 공정성 지표 BSLD | `(Wᵢ+sᵢ)/max(sᵢ, τ)` | Feitelson bounded slowdown(JSSPP '98), Mu'alem & Feitelson(TPDS '01), τ=10s 관례 |
| 공정성 임계 σ\*(t) | `1/(1−ρ(t))` | **Wierman–Harchol-Balter 공정성 기준**(SIGMETRICS '03): 모든 작업 크기에서 E[slowdown] ≤ 1/(1−ρ)면 fair. PS(processor sharing)가 정확히 이 값 달성(Kleinrock) |
| 트레이드오프의 필연성 | p50↔max는 제로섬 | **Kleinrock 보존 법칙**: work-conserving 정책 간 Σρᵢ·Wᵢ 불변 → max를 줄이면 평균이 오르는 건 법칙. 본 설계는 "제약을 만족하는 한 평균 최적" 점을 선택 |
| GPU 도메인 선례 | slowdown 기반 공정성 | Themis(NSDI '20) finish-time fairness = T_shared/T_ideal(slowdown 동형), Maui XFactor = (wait+run)/run (수십 년 프로덕션 검증) |

여기서 Wᵢ=대기시간, sᵢ=서비스 시간(duration 추정), ρ(t)=클러스터 부하.

**핵심**: v1의 "부당한 대기의 두 원리" 중 약했던 원리 1(시스템 정상 대기의 3배)을
**PS 벤치마크 σ\*=1/(1−ρ)** 로 교체. "지금 부하에서 PS(이상적 공평 분배)였다면 겪었을
slowdown까지는 정상, 그 이상은 부당" — 임의 상수가 아니라 큐잉 이론의 공정성 정의 그 자체.

## 2. 유도되는 양들 (전부 측정값에서 계산, 튜닝 노브 0)

```
ρ(t)   = EWMA(점유 GPU / 전체 GPU)          # half-life = 관측 평균 JCT (자기 스케일링)
σ*(t)  = 1 / (1 − ρ̂(t))                     # ρ̂는 Laplace 평활로 1 미만 보장
W*ᵢ(t) = σ*(t)·max(sᵢ, τ) − sᵢ              # BSLDᵢ ≤ σ* 를 Wᵢ에 대해 푼 것 (대수적 동치)
uᵢ(t)  = Aᵢ / W*ᵢ(t)                         # 긴급도 = 공정성 예산 소진율 (무차원)
S(t)   = maxᵢ uᵢ(t)                          # starvation 압력 (모니터링 지표)
```

- `uᵢ ≥ 1` ⟺ job i의 BSLD가 PS-fair 한계 σ\* 초과 = **공정성 제약 위반**.
- 부하가 높을수록 σ\*↑ → 더 긴 대기가 "정상" (이론적으로 불가피하므로). 부하가 낮으면
  σ\*→1 → 거의 기다리지 않아야 정상. v1의 β 역설(만석에서 SFQA 꺼짐)이 원천 제거됨.
- τ=10s: 초단기 job의 W\*→0 퇴화 방지. 문헌 표준값이라 노브가 아님.

## 3. 스케줄링 규칙 — 2-계층 순서 (Lagrangian 구조)

```
tier 1 (제약 위반: uᵢ ≥ 1):  uᵢ·Rᵢ 내림차순     # 공정성 복구 우선
tier 2 (제약 충족: uᵢ < 1):  sᵢ 오름차순(SJF)    # 평균 최적 (Smith/Schrage)
tier 1 전체가 tier 2보다 앞선다.
```

- 제약 최적화의 표준 구조: **제약이 느슨하면 목적함수 최적해(SJF), 제약이 활성화되면
  위반 해소가 우선**. v1의 `α_eff=α·min(1,S)` 연속 댐핑 휴리스틱은 이 2-계층 규칙이
  대체한다(별도 메커니즘 불필요 — S(t)는 관측 지표로만 남음).
- uᵢ는 대기 중 단조 증가(A 선형 증가, s 고정) → tier 승격은 비가역적, 진동 없음.
- Rᵢ(자원 적합도, C++ R 테이블 `job_emulator.cpp:414-424` 계승)는 tier 1 내부 가중 —
  같은 위반 수준이면 자원이 맞는 job 먼저(배치 가능성↑).

### Lemma (bounded starvation — v1 Lemma의 강화판)
대기 job i는 `Aᵢ = W*ᵢ`에서 tier 1로 승격하고, tier 1 내에서 uᵢ는 무한 증가하므로
유한 시간 내 큐 선두에 도달한다. R_min=0.5를 감안하면 선두 도달 시점의 BSLD는
`σ*(t)/R_min + O(1)` 이내로 유계. (배치 자체는 capacity에 의존하나, 큐 순서상
어떤 신규 job도 i를 영구 추월할 수 없음 — starvation-freedom은 aging의 고전 결과와 동형.)

## 4. v1 대비 무엇이 이론으로 대체됐나

| v1 (휴리스틱) | v2 (이론) | 근거 |
|---|---|---|
| c₁·Ê[W](t), c₁=3 (3σ 관례) | σ\*(t)=1/(1−ρ) PS 벤치마크 | Wierman–Harchol-Balter '03, Kleinrock |
| c₂·serviceᵢ, c₂=1 | BSLD ≤ σ\* 를 W로 푼 W\*ᵢ | Feitelson BSLD (τ=10s 포함) |
| max(원리1, 원리2) 결합 | BSLD 정의에서 대수적으로 유도 | 정의의 일부 (합성 아님) |
| α(t) 유도식 + min(1,S) 댐핑 | 2-계층 규칙 (Lagrangian 활성화) | Smith/Schrage SJF 최적성 + 제약 활성화 |
| FIFO 기반 + age 가산 | 느슨할 때 SJF, 위반 시 urgency | 평균 최적성 근거 확보 |

남는 파라미터: τ=10s(문헌 상수), EWMA half-life(=관측 평균 JCT, 자기 스케일링),
R 테이블(C++ 원본 계승). **튜닝 대상 노브 0개** — H3(κ 불변성)로 검증 예정.

## 5. 구현 스케치 (보류 중 — 착수 금지)

- `squad_ctrl/policy_controller.py`에 `--policy sfqa-auto` (~50줄):
  - reconcile마다: metrics에서 ρ EWMA 갱신 → σ\* → 대기 pod별 W\*ᵢ, uᵢ → 2-계층 정렬 → 기존 ungate 경로 재사용
  - sᵢ = label `squad.io/duration` (holder 실험에선 정확; 실전은 추정치 — W\*의 τ floor가 과소추정 보호)
- `analyze.py`에 BSLD(p50/p90/max)·S(t) 시계열 지표 추가
- 검증: Philly 1000 동일조건(seed=42, κ=3000, clamp 0) `p_sfqa_auto` run, ~50분

## 6. 가설 (실험으로 검증할 것)

1. **H1 (공정성)**: max 큐잉 ≤ 고정 SFQA(782s) 동급 — Lemma의 bounded starvation.
2. **H2 (효율 회복)**: p50 ≤ SJF(33s)~gate-FIFO(189s) 구간 — 제약 느슨할 때 SJF 순서.
3. **H3 (무차원성)**: κ 변경에도 재튜닝 없이 동일 경향 — σ\*·u가 전부 무차원.
4. **H4 (이론 일치)**: 측정 BSLD 분포의 max가 σ\*(t)/R_min 예측 범위 내 — Lemma 정량 검증.

## 7. 참고 문헌 (앵커)

- W. E. Smith, *Various optimizers for single-stage production*, Naval Res. Logist. 1956. (SJF 평균 최적)
- L. Schrage, *A proof of the optimality of SRPT*, Oper. Res. 1968.
- L. Kleinrock, *Queueing Systems Vol. 2*, 1976. (보존 법칙, PS slowdown=1/(1−ρ))
- D. Feitelson & L. Rudolph, *Metrics and benchmarking for parallel job scheduling*, JSSPP 1998. (bounded slowdown)
- A. Mu'alem & D. Feitelson, *Utilization, predictability... backfilling*, IEEE TPDS 2001. (BSLD τ=10s)
- A. Wierman & M. Harchol-Balter, *Classifying scheduling policies with respect to unfairness*, SIGMETRICS 2003. (공정성 기준 1/(1−ρ))
- N. Bansal & M. Harchol-Balter, *Analysis of SRPT: investigating unfairness*, SIGMETRICS 2001. (평균↔공정 트레이드오프)
- D. Jackson et al., *Core algorithms of the Maui scheduler*, JSSPP 2001. (XFactor)
- Gu et al., *Tiresias*, NSDI 2019 / Mahajan et al., *Themis*, NSDI 2020. (GPU 도메인 slowdown 공정성)

## 8. 원본 SFQA와의 관계

P\*=P+α·A·R(AR≤β)의 구조적 요소는 보존·승격된다: A(age)→uᵢ의 분자, R→tier 1 가중,
α·β(고정 노브)→σ\*(t) 측정값으로 흡수. 즉 v2는 SFQA의 "age로 starvation 방지" 정체성을
유지하면서 계수 결정을 큐잉 이론에 위임한 것. C++ 시뮬레이터 역포팅 시에도 동일 식 적용 가능
(ρ는 시뮬 내 할당률로 대체).

## 9. 변경 이력

- **v1 (2026-06-04, 폐기)**: W\*ᵢ=max(c₁·Ê[W], c₂·serviceᵢ), c₁=3/c₂=1, α(t) 유도 + min(1,S) 댐핑.
  문제: 원리 1(3σ)이 통계 관례일 뿐 스케줄링 이론 부재, max 결합·댐핑이 자의적 합성.
- **v2 (2026-06-04, 현재)**: 제약 최적화 정식화. 모든 항이 기존 정리·표준 지표에서 유도.
