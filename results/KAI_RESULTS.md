# SAFA × KAI 합성 실험 — 배치 스케줄러를 SAFA에 얹기 (멀티노드 시뮬)

> 생성 2026-06-19. 목적: NVIDIA **KAI-Scheduler**의 배치(placement) 알고리즘을 SAFA의 placement
> 계층으로 붙여 **SAFA+KAI vs KAI-only**를 비교. 단일노드 B200 실측은 노드 1개라 배치가 퇴화 →
> 배치 축이 의미를 갖는 **멀티노드 시뮬(256–1024 GPU)**에서 수행(논문의 sim=배치축 프레임과 정합).
> 코드: `sim/policies.py`(KAI 포팅)·`sim/run_kai_experiment.py`. `paper/sn-article.tex` 미수정.

## 1. KAI placement 포팅 (충실)

KAI 소스(`github.com/NVIDIA/KAI-Scheduler`, `pkg/scheduler/plugins/nodeplacement/`)에서 기본 전략 = **binpack**(GPU). 노드 스코어:
```
score = MaxHighDensity · (1 − (free − min)/(max − min))     # pack.go::getScoreOfCurrentNode
```
free(미할당 GPU)가 가장 작은 노드가 최고점 → **consolidate**(빈 노드를 큰 gang용으로 남김). 스코어가 free에 단조 감소이므로 순위 = **free 오름차순**으로 충실 포팅(`pref_kai_binpack`). KAI는 GPU 타입 speed-tier를 하지 않음(순수 binpack).

KAI admission = allocate action이 큐 순서로 `PopNextJob` + 안 맞는 gang을 **pipeline(자원 예약)**해 굶주림 방지 → head-of-line 예약. 엔진 `blocking=True` FIFO로 근사(pipelining의 예약-존중 backfill은 미모델 — KAI-only 처리량을 과소평가할 뿐 공정성엔 보수적).

**2×2 (order × placement):**

| | mostallocated(기존) | KAI binpack |
|---|---|---|
| **FIFO order** | fifo (베이스라인) | **kai (KAI-only)** |
| **SAFA order** | sfqa-auto (SAFA) | **safa-kai (SAFA+KAI)** |

## 2. 결과 (Philly 111,586잡, alloc≈99% 과포화)

q_p50 단위 초. p1=하위1% 순서공정성, lt50=추월 불공정 비율.

| GPU·종류 | 정책 | q_p50 | q_max | lt50% | p1 | alloc |
|---|---|--:|--:|--:|--:|--:|
| **256 hetero** | KAI-only | 10,243,133 | 23.98M | 0.0 | 100.0 | 99% |
| | **SAFA+KAI** | **3,462,431** | 23.97M | 0.2 | 54.5 | 99% |
| | (참고) FIFO | 9,746,217 | 22.49M | 0.0 | 100.0 | 99% |
| | (참고) SAFA | 3,773,512 | 21.51M | 0.1 | 54.4 | 99% |
| **512 hetero** | KAI-only | 3,775,926 | 8.35M | 0.0 | 100.0 | 99% |
| | **SAFA+KAI** | **1,773,330** | 8.32M | 0.7 | 50.5 | 99% |
| | (참고) FIFO | 3,550,051 | 7.81M | 0.0 | 100.0 | 99% |
| | (참고) SAFA | 1,759,480 | 7.26M | 0.8 | 50.5 | 99% |
| **1024 hetero** | KAI-only | 671,128 | 1.09M | 0.0 | 100.0 | 97% |
| | **SAFA+KAI** | **304,854** | 1.32M | 0.3 | 62.6 | 97% |
| | (참고) FIFO | 607,296 | 0.97M | 0.0 | 100.0 | 97% |
| | (참고) SAFA | 255,815 | 1.02M | 0.0 | 76.5 | 96% |

**단일 타입(256/512/1024 single): KAI-only ≡ FIFO, SAFA+KAI ≡ SAFA — 완전 동일** (예: 512 single 둘 다 q_p50 1,216,806 / 607,032). 전수 수치 `results/kai_experiment_summary.csv`.

## 3. 분석 — 정직 평가

**① 합성 자체는 작동(아키텍처 검증).** SAFA order × KAI binpack(`safa-kai`)이 정상 실행됨. SAFA는 `order()`(큐 재정렬), KAI는 `node_pref()`(배치)를 담당하는 **직교 2-훅 합성**이 코드로 검증됨. KAI-only(FIFO order + KAI binpack)도 동일 프레임에서 동작.

**② 배치 축(KAI binpack vs mostalloc)은 이 레짐에서 거의 무차별 — 일부 더 나쁨.**
- **단일 타입: 완전 동일.** mostalloc 정렬키 `(speed, free)`의 speed가 상수라 KAI binpack(free 오름차순)과 같은 선택 → KAI-only ≡ FIFO, SAFA+KAI ≡ SAFA.
- **이종: KAI binpack이 약간 더 느림.** KAI는 GPU 타입 속도를 무시(순수 binpack)하므로 잡이 느린 타입에 더 자주 배치 → service↑ → 대기↑. 256 hetero KAI-only q_p50 10.24M > FIFO 9.75M(+5%), 1024 hetero 671K > 607K(+11%). mostalloc은 빠른 타입 우선이라 이 레짐에서 더 유리.

**③ 성능 이득은 전적으로 order(SAFA) 축에서 나온다.**
- KAI-only ≈ FIFO (q_p50 ~10M, 256 hetero) / SAFA+KAI ≈ SAFA (q_p50 ~3.5M) → **SAFA order가 중앙 대기를 50–65% 단축**, 배치 정책과 무관.
- 즉 동일 KAI binpack 배치 위에서 FIFO→SAFA로 바꾼 효과(10.24M→3.46M)가, 배치를 mostalloc→KAI로 바꾼 효과(±5–11%)를 압도.

**④ 논문 경향과 정합.** 이는 논문 §VI(`paper` line 599)의 *"whole-GPU 과포화에서 단편화 인지 배치(FGD)와 most-allocated가 같은 선택으로 수렴 → 배치 축이 추가 효과를 못 냄. 이득은 배치가 아니라 비차단 큐 규율(SAFA)"* 발견을 **KAI라는 독립 배치 스케줄러로 재확인**한 것이다. SAFA의 기여는 큐-순서 축이며 배치 축과 직교한다는 명제가 강화됨.

## 4. 한계 (명시)
- **whole-GPU 모델**: 분수(fractional) GPU 공유가 없다. KAI binpack(및 FGD)의 consolidate 이득은 분수-GPU·중간 부하에서 더 크다(원논문 레짐). 본 과포화 whole-GPU에서는 배치 차이가 억제됨 — 배치 무차별 결론은 **이 레짐 한정**.
- **KAI pipelining 근사**: 예약-존중 backfill을 blocking FIFO로 근사 → KAI-only 처리량을 보수적으로 과소평가(공정성 결론엔 영향 없음).
- **KAI 미설치(실 클러스터)**: docker.io 방화벽 차단 + 단일노드 퇴화로 실 KAI 설치는 불가 → 알고리즘 충실 포팅으로 대체(소스 대조).
- **p1 해석**: FIFO/KAI-only는 재정렬을 안 해 p1=100(완전 순서공정)이나 대기가 큼; SAFA계는 대기를 크게 줄이는 대신 p1을 일부 양보(추월). lt50은 0.2–0.7%로 낮아 *꼬리만* 추월 — SAFA의 "빠르면서 (그리디 대비) 공정" 균형.

## 5. 재현
```
cd sim
/raid/squad/venv/bin/python run_kai_experiment.py --gpus 256,512,1024 --kinds single,hetero
# → results/kai_experiment_summary.csv
```
KAI 포팅: `sim/policies.py` (`pref_kai_binpack`, `KAIonly`, `SAFA_KAI`).
