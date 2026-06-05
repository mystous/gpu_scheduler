# SQUAD K8s 실측 — 종합 분석 리포트

> 갱신: 2026-06-04 (저녁, 2차 캠페인 반영). 환경: kind 단일노드 `llmd`, k8s v1.31, NVIDIA B200×8.
> 워크로드: GPU-holder 스텁(점유·스케줄링은 진짜 kube-scheduler, 연산은 sleep).
> 측정: 실제 K8s 타임스탬프 기반 큐잉지연·JCT. 시뮬레이션 아님(리젝 ① 대응).
> 데이터: `/raid/squad/runs/`, 집계 `runs_summary.csv`/`tables.md`, 민감도 `/raid/squad/sensitivity/`.

## 1. 최종 비교: Philly 1000 층화샘플, 동일 조건 8정책 — 큐잉지연(초)

| 정책 | p50 | p90 | **max(starvation)** | 정보 요구 | 비고 |
|---|---|---|---|---|---|
| default-FIFO | **17** | 275 | 2450 | — | 빠르나 무방비 |
| SJF | 33 | 461 | 2265 | duration | 평균 최적류, 최악 방치 |
| gate-FIFO | 189 | 484 | 924 | — | gate 효과 통제군 |
| Kueue v0.9.4 | 195 | **396** | 869 | — | 프로덕션 표준(BestEffortFIFO) |
| SFQA-auto (τ=1) | 210 | 582 | 937 | duration(추정 허용) | slowdown 비례 보호 |
| SFQA (고정 α·β) | 243 | 589 | 782 | — | 기존 결과 |
| SFQA-auto (τ=10) | 290 | 612 | **768** | duration(추정 허용) | 절대 나이 보호, **max 2위** |
| EASY-backfill | 419 | 639 | **691** | duration(**완벽 가정**†) | max 1위, p50 꼴찌 |

† EASY 주의: 본 실험은 duration 라벨=실제 실행시간(오차 0)이라 예약이 완벽 정보로 동작 —
실제 클러스터의 사용자 추정(2~10× 오차)에선 무너지는 상한선(upper bound)으로 해석해야 함.
SFQA-auto는 τ-floor로 추정 오차에 견고(이론: `docs/ADAPTIVE_SFQA_DESIGN.md`).

### 핵심 결과
- **starvation(max) 순위**: EASY 691 < auto(τ10) 768 < SFQA 782 < Kueue 869 < gate-FIFO 924 ≪ SJF/default.
- **zero-knob auto(τ10)가 고정 SFQA를 무튜닝으로 능가**(768<782) + 프로덕션 표준 Kueue 대비 max −12%.
- **Pareto 프런티어**: (p50, max) 평면에서 default(17,2450)→Kueue(195,869)→auto τ1(210,937)/auto τ10(290,768)→EASY(419,691)가 프런티어 형성 — max를 지킬수록 p50을 내주는 구조(Kleinrock 보존법칙과 일치).
- **τ의 의미(실측으로 확인)**: τ는 절대-나이 보호(τ↑)와 slowdown-비례 보호(τ↓) 사이의 **의미 선택 다이얼**.
  τ=10: max 최강(768) / τ=1: p50 회복(210, SFQA 243보다 좋음) + max 양보(937).
- **본 압축 워크로드의 한계**: duration cap(6~8s)으로 서비스 시간이 사실상 균일 → v2의 잡 크기별
  차등 보호(slowdown 개인화)가 작동할 신호 자체가 없음. BSLD로 평가해도 순위 동일(전 잡 BSLD≈JCT/10).
  → **이질적 duration의 VC 전체 재생(§5)이 v2의 진짜 시험대.**

### BSLD(bounded slowdown, τ_eval=10s) 참고표

| run | BSLD p50 | p90 | max |
|---|---|---|---|
| default | 2.5 | 24.8 | 223.7 |
| Kueue | 17.7 | 34.6 | 87.0 |
| auto τ=1 | 19.7 | 52.8 | 89.4 |
| SFQA | 24.2 | 53.7 | 78.3 |
| auto τ=10 | 27.4 | 52.6 | 77.0 |
| EASY | 36.8 | 53.9 | 67.7 |

## 1.5 충실 duration 체인 (S=360, JCT≤2h 모집단, 윈도우 d51~65, cap 없음) — 2026-06-04 밤

설계: 사용자 확정 — duration cap 제거, 정률 S=360(실험 1s=실세계 6분), 바닥 5s만(~77%),
multi-GPU 최다 14일 윈도우(층화 500, peak 26 GPU=3.2×). 실행 dur 5~20s로 비율 일부 보존 →
**BSLD가 처음으로 독립 정보**를 가짐. 절대값 작음(노이즈 바닥 2~5s) — p90·max 위주 비교.

| 정책 | 큐잉 p50/p90/max | BSLD p50/p90/max |
|---|---|---|
| Kueue | **0 / 12 / 45** | **0.70 / 1.80 / 5.20** |
| sfqa-auto (τ=10) | 5 / **20** / 52 | 1.10 / 2.60 / 6.00 |
| EASY (완벽 추정†) | 5 / 31 / **46** | 1.25 / 3.73 / **5.30** |

- **κ=3000 본선과 동일 구도 재현**: EASY max 우위(−12%) / auto p90 우위(−35%, 본선 −4%에서
  duration이 살아나자 9배 확대 — v2 slowdown 개인화의 첫 실증). Kueue는 본선처럼 percentile 효율 1위.
- 이 조건(peak 3.2×, 짧은 백로그)에선 Kueue가 max에서도 선전(45) — 본선(5.4× 지속 경합, max 869 열위)과
  대비되는 부하 의존성. 고경합일수록 SFQA 계열·EASY의 보호가 필요해짐.
- **EASY-noisy 결과(f-모델, Mu'alem&Feitelson TPDS'01)**: est=dur×(1+U[0,f]) 주입(holder 실행은 실제 그대로).

  | EASY 변형 | 큐잉 p50/p90/max | BSLD p50/p90/max |
  |---|---|---|
  | perfect (f=0) | 5 / 31 / 46 | 1.25 / 3.73 / 5.30 |
  | f=1 (추정 1~2×) | 5 / 22 / **37** | 1.10 / 2.82 / 4.40 |
  | f=3 (추정 1~4×) | 5 / 21 / **37** | 1.10 / 2.70 / 4.30 |

  **과대추정 역설 재현**(Tsafrir·Feitelson 계열의 고전 결과): 노이즈가 예약을 보수화→백필 구멍 확대→
  전 지표 개선(f1·f3 모두, f 증가에 둔감). 25년 문헌 결과의 재현 = 측정 파이프라인 타당성 방증.
  한계: f-모델은 과대추정만 — 예약을 실제로 깨는 **과소추정**(추정보다 오래 도는 잡)은 미시험.
  결론: 이 저부하 조건에선 EASY의 max 우위가 완벽추정 산물이 아님. auto의 가치는
  "추정 자체 불요 + **고경합(κ3000)에서 p50(−31%)·p90 우위**"로 정리됨 — 부하 영역별 적합 정책이 다름.

## 2. κ=6000 적응성 실험 (시간 스케일 2배 변화, peak 5.4×) — 리젝 ⑤ 결정 증거

같은 1000잡을 2배 압축(절대값은 κ=3000과 직접 비교 불가, 두 run 간 상대 비교만):

| 정책 (κ=6000) | p50 | p90 | max |
|---|---|---|---|
| SFQA 고정 (κ3000 튜닝값 그대로) | 1080 | 1613 | **1682** |
| SFQA-auto (τ=1, 무튜닝) | **592** (−45%) | **907** (−44%) | 2087 (+24%) |

- **고정 노브의 드리프트 입증**: age-unit=10s가 κ=6000의 대기 스케일(~1000s)에서 과보정 →
  설계자가 의도한 "균형점"을 잃고 극단적 나이 정렬로 쏠림(p50/p90가 auto의 1.8배).
- **auto는 무튜닝 적응**: σ*(t)가 부하에서 유도되어 균형 유지(p50·p90 −45%). max는 고정이 더
  좋으나 이는 과보정의 부산물(전부를 나이순으로 = max 특화) — 의도된 동작이 아님.
- 결론: 고정 계수는 워크로드 시간 스케일이 바뀌면 **의도한 트레이드오프 점을 유지하지 못한다**.
  auto는 동일 코드·동일 설정으로 균형점을 유지한다(튜닝 비용 0, `docs/KNOB_COST_AND_SENSITIVITY.md` §1).

## 3. 민감도 스윕 (C++ 시뮬레이터, 12 configs) — "임의 상수" 방어

| 상수 | 스윕 | makespan Δ | 판정 |
|---|---|---|---|
| R 페널티 0.05–0.3 | 5점 | −0.8%~+2.0% | robust |
| P 밑 1.5–4 | 4점 | +0.3%~+1.8% | robust |
| 재정렬 창 m∈{1,2,3,5,10} | 5점 | **m=1만 +8.9%**(alloc −6.3pp), m≥2 ≤1.4% | 창 필요성 입증, 3은 안전값 |

상세: `/raid/squad/sensitivity/sweep_summary.{md,csv}`.

## 4. 방법론 노트 (1차 캠페인에서 확립, 유지)

교란요인 5종 제거: ①gate 효과 분리(gate-FIFO 통제군) ②age=대기시간/10s 수정 ③β=100
④현실적 GPU 분포(Philly) ⑤층화 1000(seed=42 재현, `philly_sample1000_*.csv`).
Kueue run은 Job suspend 방식이라 큐잉을 Job 생성 기준으로 측정(공정 비교).

## 5. 다음 단계

1. **VC 전체 재생** (무샘플링·duration cap 없음·균일 S → JCT 비율 보존):
   - 적합 후보 **VC 103959**(2,780잡, 1/2/4-GPU 혼합 35%, VC 부하 25.9 GPU):
     **H100×3 합류 후 32 GPU에서 0.81× — S=15~20으로 5~6일 실험** (duration p10 ≥5s 유지).
   - 현 8 GPU에선 3.2× 지속 과부하라 풀 재생 부적합. ed69ec(1.1×)는 100% 1-GPU라 순서 둔감.
   - 지금 가능한 대안: 103959 최번기 2주 윈도우의 **전체** 잡(무샘플링) 재생.
   - 이질적 duration(82s~수일)에서 v2 slowdown 개인화·BSLD 지표가 비로소 검증됨.
2. 반복 실행(신뢰구간) — 논문 수치 확정 시.
3. 실제 GPU 연산 워크로드 — 캐시 torch 이미지로 가능(`docs/LOCAL_IMAGE_INVENTORY.md`).
4. PTR — 보류(2026-06-04 사용자 결정 대기: 현 증거로 SFQA-only 스코프 가능성).

## 6. 재현
- 단일 run: `squad_ctrl/run_one.sh <policy> <run_id> "<ctrl_extra>" "<exp_extra>"`.
- 정책: `policy_controller.py --policy {fifo,sjf,priority,las,sfqa,sfqa-auto,easy} [--tau]`.
  Kueue는 `run_experiment.py --policy kueue`(gate 없음, `kueue-queues.yaml` 선적용).
- 집계: `analyze.py`. 민감도: `/raid/squad/sensitivity/run_sweep.sh` + `analyze_sweep.py`.
