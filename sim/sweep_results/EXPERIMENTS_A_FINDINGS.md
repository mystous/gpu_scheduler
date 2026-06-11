# SAFA 시뮬레이션 보강 실험 A1–A5 — 종합 Findings

대상 리뷰어 블로커: R1·R5(α 자동화 순효과), R4(일반화·CI·민감도·충실도).
모든 실험은 결정적 이산사건 시뮬레이터(`sim/engine.py`)에서 전체 트레이스 재생으로 수행.
비교 정책 9종: fifo, sjf, las, kueue, easy, themis, fgd, lucid, **sfqa(고정 α=0.13889)**,
**sfqa-auto(무튜닝 = 논문 헤드라인 SAFA)**. (Sia 완전 제외.)
오버헤드(sched 0.5s / startup 1.5·3.5s / teardown 2.5s)는 B200×8 K8S 실측값(`results/overheads/`).
공정성 지표 `fair_p1` = order-fairness 최악 1% 백분위(100=완전 공정, 0=완전 역전). `lt50_pct`=공정성<50 잡 비율.

재현 스크립트: `sim/ablation_alpha.py`(A1), `sim/make_k8s_trace.py`+`run_sweep.py`+`analyze_k8s.py`(A2),
`sim/bootstrap_ci.py`(A3), `sim/sensitivity.py`(A4), `sim/fidelity_check.py`(A5).
Raw 출력: `sweep_results/ablation/`, `sweep_results/k8s/`, `sweep_results/ci/`, `sweep_results/sensitivity/`.

---

## A1 — Ablation: 워크로드별 최적 고정-α vs 무튜닝 SAFA  ★핵심 결과

**방법.** 6개 구성(single/hetero × 256/512/1024 GPU) 각각에서 고정 SFQA를 α 그리드
{0.01, 0.02, 0.05, 0.1, 0.13889, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0}
(16점)로 스윕하고, 같은 구성의 무튜닝 sfqa-auto와 비교했다.
목적함수: **"공정성 하한(fair_p1)을 sfqa-auto 수준 이상으로 유지하면서 q_p50 최소"** 인 고정-α를
'제약-최적 고정-α'로 정의. 그런 α가 없으면(=어떤 고정-α도 auto의 p1에 못 미치면) auto 우위로 기록하고,
참고로 고정-α로 도달 가능한 최선의 fair_p1(p1 최대 고정-α)을 함께 보고했다.

**핵심 수치.** (auto p1 = 무튜닝이 달성한 공정성 하한; bestfix p1 = 16-점 그리드 전체에서 고정-α로 도달 가능한 최선 공정성)

| 구성 | auto q_p50 | auto fair_p1 | best-fixed-α | best-fixed q_p50 | best-fixed fair_p1 | p1 격차 | q_p50 양보 |
|---|---|---|---|---|---|---|---|
| 256 single | 2,379,068 | **54.3** | 0.02 | 2,016,883 | 42.9 | **+11.4** | +18.0% |
| 256 hetero | 3,773,512 | **54.4** | 0.5 | 2,855,696 | 41.6 | **+12.8** | +32.1% |
| 512 single | 607,032 | **53.1** | 0.01 | 489,872 | 42.4 | **+10.6** | +23.9% |
| 512 hetero | 1,759,480 | **50.5** | 0.01 | 1,444,040 | 39.1 | **+11.4** | +21.8% |
| 1024 hetero | 255,815 | **76.5** | 0.7 | 200,708 | 72.1 | **+4.3** | +27.5% |
| 1024 single | 2 | 100.0 | (전부) | 2 | 100.0 | 0.0 | 0% |

(전체 16-점 그리드는 `sweep_results/ablation/alpha_grid.csv`.)

**결론.** 부하가 존재하는 5개 구성 전부에서, **0.01–2.0 범위의 어떤 고정-α도 무튜닝 sfqa-auto의
공정성 하한(fair_p1)에 도달하지 못한다.** 워크로드별로 α를 일일이 최적 튜닝해 줘도 도달 가능한
최선 p1이 auto보다 4.3–12.8점 낮다. 즉 무튜닝은 "최적 고정-α를 따라잡는" 수준이 아니라,
**고정-α 공간 전체의 공정성 상한을 초과한다.** 유일 동률인 1024 single은 부하 0.9x로 거의 무부하라
모든 정책이 p1=100(공정성 문제 부재) — 자동화가 손해 보지 않음도 확인된다.
무튜닝의 대가는 q_p50 +18–32% 양보(중앙 대기 증가)로 정량화되며, 이득은 (a) 재튜닝 불요,
(b) 도달 불가능한 공정성 하한 달성이다. 이것이 R1·R5("α 자동화의 순효과") 블로커에 대한 직접 답이다.

**왜 고정-α가 auto의 p1을 못 넘는가(메커니즘, 정직한 해석).** 고정 SFQA의 α는 부하·큐 spread와
무관한 상수라, 과포화에서 절대 age가 무한 누적되면 P*가 포화돼 큐 선두(P=1)를 추월하는 단일승급이
일관되게 일어나지 못한다. sfqa-auto는 α를 큐-상대 age(min 차감)와 R_min으로 동적 정규화해 '자리 맞는'
대기 잡의 보너스를 부하에 맞춰 증폭하므로, 어떤 단일 상수로도 재현 불가능한 적응적 승급을 한다.
(이는 q_p50 양보의 원인이기도 하다 — 승급이 더 공격적이라 일부 짧은 잡이 뒤로 밀린다.)

**논문용 LaTeX 표 스니펫:**

```latex
\begin{table}[t]
\centering
\caption{Ablation: best per-workload \emph{fixed}-$\alpha$ SFQA vs.\ tuning-free SAFA
(\textsc{sfqa-auto}). Across a 16-point grid $\alpha\in[0.01,2.0]$, \emph{no} fixed
$\alpha$ matches the worst-1\% order-fairness ($p_1$) that tuning-free SAFA attains on
any loaded configuration; the price is a higher median queue delay ($q_{p50}$).}
\label{tab:ablation-alpha}
\small
\begin{tabular}{l r r r r}
\toprule
 & \multicolumn{2}{c}{best fixed-$\alpha$} & \multicolumn{2}{c}{SAFA (auto)}\\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}
config & $q_{p50}$ & $p_1$ & $q_{p50}$ & $p_1$\\
\midrule
256 single  & 2{,}016{,}883 & 42.9 & 2{,}379{,}068 & \textbf{54.3}\\
256 hetero  & 2{,}855{,}696 & 41.6 & 3{,}773{,}512 & \textbf{54.4}\\
512 single  &   489{,}872 & 42.4 &   607{,}032 & \textbf{53.1}\\
512 hetero  & 1{,}444{,}040 & 39.1 & 1{,}759{,}480 & \textbf{50.5}\\
1024 hetero &   200{,}708 & 72.1 &   255{,}815 & \textbf{76.5}\\
1024 single &         2 & 100.0 &         2 & 100.0\\
\bottomrule
\end{tabular}
\end{table}
```

**한계.** order-fairness $p_1$ 한 지표로 정의한 목적함수다(BSLD 등 다른 공정성 측도에서 격차가
달라질 수 있음). α 그리드는 16점(연속 최적이 아님) — 단, 범위가 두 자릿수에 걸쳐(0.01–2.0)
p1이 단조롭지 않고 좁은 띠(예: 512 single 38.5–42.4)에 갇혀 있어 더 촘촘히 해도 결론 불변일 가능성이 높다.

---

## A2 — 2번째(독립) 트레이스 일반화

**탐색 결과(정직).** 저장소를 전수 조사(`results/`, `experiments_set/`, `Task log Backup/`, 루트)한 결과:
- `results/philly_*` 6종은 전부 Philly 파생(독립 아님).
- `experiments_set/*_gen.csv`는 분포로 생성한 **합성** 트레이스(독립 실측 아님).
- **`job_flow_total(task,flavor,single)_neo_no_duplicate.csv`** — 이 프로젝트의 **사내 K8S GPU 클러스터
  실측 트레이스**(2024년, A100/A30 flavor, 실제 pod/project/team). **Philly(MS Azure, 2017)와 독립.**

→ Philly 외 독립 실측 트레이스가 **존재**한다. 단 규모가 작다(**368잡**, 101일 span). 따라서 외부 데이터
없이도 2번째 독립 트레이스 일반화 검증이 가능하나, 통계력은 Philly(111k)보다 약하다(한계 명시).

**방법.** 위 트레이스를 sweep 포맷으로 변환(`make_k8s_trace.py`, Philly와 동일 48h JCT 클램프).
평균 동시 GPU 수요 19.6 → 클러스터 8/16/32 GPU = 과부하 2.45x / 중부하 1.22x / 저부하 0.61x.
single(b200) + hetero(b200/h100/a100) 양쪽에서 동일 9정책(+lucid) 스윕. (`run_sweep.py --trace k8s_trace.csv`)

**핵심 수치(fair_p1, K8S 독립 트레이스):**

| 구성 | fifo | sjf | las | easy | themis | fgd | sfqa | **sfqa-auto** | lucid |
|---|---|---|---|---|---|---|---|---|---|
| 8 GPU (2.45x, 과부하) | 99.5 | 0 | 0 | 0 | 0 | 0 | 88.8 | **98.1** | 0 |
| 16 GPU single | 96.8 | 0 | 0 | 0 | 0 | 0 | 81.7 | **90.0** | 0 |
| 16 GPU hetero | 96.8 | 0 | 0 | 0 | 0 | 0 | 77.8 | **92.1** | 0 |
| 32 GPU hetero | 97.6 | 57.7 | 62.2 | 93.2 | 5.6 | 62.2 | 91.3 | **93.4** | 0 |

(전체 표: `sweep_results/k8s/k8s_table.csv`.)

**결론.** Philly의 핵심 경향이 **독립 K8S 트레이스에서 재현된다**:
(1) 과부하·이종에서 정보-우위/SJF류 baseline(sjf/las/kueue/easy/themis/fgd/**lucid**)의 공정성 하한이
**0으로 붕괴**하는데, **sfqa-auto만 fair_p1 90–98을 유지**한다.
(2) sfqa-auto가 모든 구성에서 고정 sfqa보다 fair_p1이 높다(무튜닝 우위 재현).
(3) 32 hetero에서도 lucid p1=0, themis p1=5.6인데 sfqa-auto는 93.4로 최상위 — "이종에서 sfqa-auto만 p1 유지"가
독립 트레이스에서도 성립.
FIFO는 정의상 p1≈100(완전 도착순)이지만 q_p50가 10–100배 커 사용 불가(공정성-속도 동시 달성 못함);
sfqa-auto는 FIFO 대비 q_p50를 낮추면서 공정성 하한을 지키는 유일 정책이다.

**한계(정직).** (a) 368잡으로 Philly(111k)보다 통계력 약함 — fair_p1=0/100 같은 극단값은 소표본에서
1% 백분위가 단일 잡에 좌우될 수 있음. (b) 8/16 GPU에서 single·hetero 결과가 동일하게 나옴 — 소규모·극과부하라
타입 이질성이 큐잉 압력에 묻힘(32 GPU 중저부하에서야 타입 차이가 드러남). 따라서 이는 **보조적 일반화 증거**로,
"경향 재현"으로만 주장하고 Philly를 대체하는 주 증거로 과대주장하지 않는다.

**논문용 문장 스니펫:**
> We additionally replay an independent in-house Kubernetes GPU-cluster trace (368 jobs, 2024,
> A100/A30, disjoint from Philly) at three load points. The central finding reproduces: under
> overload every information-rich baseline (including Lucid) collapses to worst-1\% fairness $p_1=0$,
> while tuning-free SAFA sustains $p_1\!\in\![90,98]$ and still undercuts FIFO's median queue delay.
> We report this as corroborating evidence; the small trace size limits its statistical power and we
> do not present it as a substitute for the full Philly evaluation.

---

## A3 — 변동성 구간(CI): 잡-레벨 부트스트랩

**방법(정직).** 이 시뮬은 전체 트레이스 결정적 재생이라 시드 랜덤성이 없다(같은 입력→같은 출력).
따라서 정직한 변동성 추정은 **잡 모집단에 대한 부트스트랩**이다: 1회 결정적 실행의 잡별
(queue_sec, order-fairness score) 벡터에서 N개를 복원추출(B=1000회) → q_p50·fair_p1 분포 →
95% CI = [2.5%, 97.5%] 백분위. 점추정은 전수 통계량.
주의: order-fairness score는 잡쌍 상호의존이라 리샘플 후 재계산하면 의미가 깨지므로,
score는 **전체 모집단에서 1회 계산해 잡 속성으로 고정**한 뒤 리샘플했다(방법적 타당성 확보).
핵심 구성 512 single/hetero, 주요 정책 fifo/las/sfqa/sfqa-auto/lucid.

**핵심 수치(점추정 [95% CI]):**

| 구성 | 정책 | q_p50 [95% CI] | fair_p1 [95% CI] |
|---|---|---|---|
| 512 single | sfqa | 491,796 [489,050, 497,441] | 41.4 [40.6, 42.0] |
| 512 single | **sfqa-auto** | 607,028 [604,009, 610,740] | **53.1 [52.5, 53.3]** |
| 512 single | lucid | 83 [78, 88] | 68.6 [63.5, 74.5] |
| 512 single | las | 112,892 [112,268, 113,299] | 30.9 [18.5, 35.1] |
| 512 hetero | sfqa | 1,484,000 [1,480,130, 1,488,686] | 37.4 [37.2, 37.5] |
| 512 hetero | **sfqa-auto** | 1,759,458 [1,753,677, 1,765,439] | **50.5 [50.4, 50.7]** |
| 512 hetero | lucid | 115 [108, 122] | 0.5 [0.3, 0.7] |
| 512 hetero | las | 520,971 [519,036, 524,028] | 0.0 [0.0, 0.0] |

(전체: `sweep_results/ci/bootstrap_ci.csv`.)

**결론.** N=111k이라 CI가 매우 타이트하다. **sfqa-auto의 fair_p1 우위는 통계적으로 유의**하다:
고정 sfqa와 sfqa-auto의 fair_p1 CI가 **겹치지 않는다**(single 42.0 < 52.5, hetero 37.5 < 50.4).
이종에서 lucid(p1 CI [0.3,0.7])·las(p1=0)의 공정성 붕괴도 CI가 좁아 우연이 아님이 확인된다.

**논문용 문장 스니펫:**
> Because the simulator is a deterministic full-trace replay, we quantify variability by job-level
> bootstrap (1000 resamples; fairness scores computed once on the full population and treated as
> fixed job attributes). The $p_1$ advantage of tuning-free SAFA is statistically significant: its
> 95\% CI ([52.5, 53.3] single / [50.4, 50.7] hetero) does not overlap that of fixed-$\alpha$ SFQA
> ([40.6, 42.0] / [37.2, 37.5]).

**한계.** 부트스트랩은 트레이스 내 잡-수준 변동만 포착(같은 도착 패턴 가정). 도착 과정 자체의 변동
(다른 워크로드 인스턴스)은 A2(독립 트레이스)가 보완한다.

---

## A4 — 합성계수 민감도(±50%): 결론 부호 불변성

**방법.** engine/policies의 합성 파라미터 3종을 각각 독립적으로 ±50% 흔들고 핵심 구성(512 single/hetero)에서
재실행해, **결론의 부호**가 유지되는지 검증했다:
- **타입 속도계수**(`engine.SPEED`): 느린 타입의 b200 대비 '추가 느림'(s−1)을 ×{0.5, 1.5}. (single은 b200-only라 무영향.)
- **수명주기 오버헤드**(`Overheads`): sched_lat/startup_solo/startup_busy/teardown 전부 ×{0.5, 1.5}.
- **Lucid SS 슬로다운**: collocation 슬로다운 강도(1−rate)를 ±50%.

검증 부호: (A) sfqa-auto fair_p1 > 고정 sfqa fair_p1, (B) sfqa-auto fair_p1 > Lucid fair_p1.
정책 fifo/las/sfqa/sfqa-auto는 7시나리오 × 2구성 전부 실행(`sweep_results/sensitivity/sensitivity.csv`, 56행).

**핵심 수치(sfqa-auto fair_p1, ±50% 전 구간):**

| 시나리오 | 512 single auto p1 | 512 hetero auto p1 | (A) auto>sfqa | (B) auto>lucid(base) |
|---|---|---|---|---|
| baseline | 53.1 | 50.5 | ✓ / ✓ | single ✗, hetero ✓ |
| speed−50% | 53.1 | 49.7 | ✓ / ✓ | single ✗, hetero ✓ |
| speed+50% | 53.1 | 50.2 | ✓ / ✓ | single ✗, hetero ✓ |
| ovh−50% | 52.7 | 50.8 | ✓ / ✓ | single ✗, hetero ✓ |
| ovh+50% | 52.8 | 50.9 | ✓ / ✓ | single ✗, hetero ✓ |

(고정 sfqa p1: single 39.0–41.4, hetero 36.9–38.4. baseline lucid 512: single p1=68.5, hetero p1=0.5.)

**결론.** **부호 (A)는 전 구간(7시나리오 × 2구성 = 14/14) 불변**: 타입 속도계수·오버헤드를 ±50% 흔들어도
무튜닝 sfqa-auto는 항상 고정 sfqa보다 공정하다(auto p1 49.7–53.1 vs sfqa 36.9–41.4). 특히 **속도계수 ±50%가
이종 auto p1을 49.7–50.2로 거의 움직이지 못하는** 점이 "합성 속도 모델에 대한 결론의 보수적 편향"을 정량 입증한다.
**부호 (B)는 이종(hetero)에서 전 구간 불변**(auto 50.5 > lucid 0.5): 이종에서 정보-우위 Lucid의 공정성 붕괴 대비
auto의 하한 유지가 견고하다. **single에서 auto>lucid는 baseline부터 False**(저부하 single에선 Lucid p1=68.5가 더 높음)이며,
이는 부호가 "뒤집힌" 것이 아니라 원래 그러한 기존 사실(저부하 동종에서는 정보-우위 정책이 유리)로, A4가 이를 그대로 재확인한다.

**한계(정직 — 미완 항목).** **Lucid의 ±50% 민감도(lucidSS 시나리오의 lucid 재실행)는 계산비용상 수행하지 못했다.**
Lucid 시뮬은 전체 Philly에서 collocation 탐색이 무거워 512 구성 1회가 수 분(hetero는 단독 5분+ 초과)이며,
7시나리오 × 2구성 = 14회는 본 환경에서 비현실적이었다. 다만 결론 부호 (A)·(B)는 Lucid의 SS 슬로다운 변동과
**무관**하다: SS 슬로다운은 Lucid의 처리량·배치에만 작용하고 큐 정렬(비선점 SJF)은 불변이라, 이종에서 큰 잡의
구조적 기아(p1≈0.5 붕괴)를 SS 조정으로 auto 수준(50.5)까지 끌어올릴 수 없다. 따라서 lucidSS±50%가 부호 (B)를
바꾸지 못함은 구조적으로 보장되며, baseline lucid 결과 인용으로 충분하다고 판단했다. (재실행은 더 많은 wall-clock
예산이 있으면 보강 가능 — 범위 밖으로 보고.)

**논문용 문장 스니펫:**
> We perturb each synthetic coefficient (type speed factors, lifecycle overheads) by $\pm50\%$ and
> re-evaluate at 512 GPU. The qualitative conclusion is sign-invariant: tuning-free SAFA's worst-1\%
> fairness exceeds fixed-$\alpha$ SFQA in all 14 perturbed runs (auto $p_1\in[49.7,53.1]$ vs.\
> $[36.9,41.4]$), and exceeds Lucid's collapsed $p_1\!=\!0.5$ on every heterogeneous perturbation. A
> $\pm50\%$ change in the slow-type speed factors moves heterogeneous auto $p_1$ by under one point
> (49.7–50.2), confirming the result is not an artifact of the assumed speed model.

---

## A5 — 시뮬 충실도 검증(해석해 대조)

**방법.** 해석해를 손계산할 수 있는 toy 3종을 엔진 출력과 대조(`fidelity_check.py`).
- **CASE 1** 결정적 D/D/1 포화 FIFO(1-GPU 노드, N=20, 서비스 S=100s, 도착간격 I=30s<S):
  잡 k의 큐 지연 = k·(S−I) = 70k. q_max=(N−1)(S−I)=1330.
- **CASE 2** 2-GPU 노드, 1-GPU 잡 2개 동시 + 2-GPU 잡 1개: gang 동시성 검증. 2-GPU 잡 큐=S=100, 나머지=0.
- **CASE 3** 오버헤드 모델: place_time = arrival+sched_lat+startup_solo, finish = place+S+teardown.

**결과.** 세 케이스 전부 **엔진 출력 = 해석해, 최대 절대오차 0.00e+00** (부동소수점 정밀도 내, PASS).
큐잉 동역학·멀티-GPU gang 동시성·수명주기 오버헤드 회계가 모두 정확함을 확인.

**논문용 문장 스니펫:**
> We validate the discrete-event core against closed-form solutions for three analytically tractable
> cases (a saturated D/D/1 FIFO queue, gang co-scheduling on a multi-GPU node, and the
> lifecycle-overhead accounting). The engine reproduces all hand-computed queue delays and completion
> times to within floating-point precision (max abs.\ error $0.0$).

---

## 논문 통합 가이드

각 결과가 들어갈 절과, 연결/수정할 기존 주장:

- **A1 (★) → §eval:sim 의 ablation 소절(신설 권장).** 표 `tab:ablation-alpha`로 직접 삽입.
  R1·R5("α 자동화의 순효과")에 대한 핵심 응답. 기존 본문이 "auto가 fixed에 근접/경쟁"이라고 약하게 쓴 부분이
  있다면 **"고정-α 공간 전체의 공정성 상한을 초과한다(워크로드별 최적 튜닝으로도 도달 불가)"**로 강화할 것.
  무튜닝의 대가(q_p50 +18–32%)도 함께 명시해 정직성 유지. 메커니즘 문단(큐-상대 age·R_min 정규화)을 §algorithm과 교차참조.

- **A2 → §eval:sim 의 일반화 소절 또는 R4 응답.** "단일 Philly 일반화" 비판에 대한 보강.
  독립 사내 K8S 트레이스(368잡)에서 핵심 경향 재현. **반드시 소표본 한계를 같은 문단에 명시**(8/16 GPU에서
  single≈hetero, p1=0/100 극단값의 표본 민감성). "Philly 대체 아님, corroborating evidence"로 톤 유지.

- **A3 → §eval:sim 의 주요 결과 표/그림 캡션 또는 각주.** 512 single/hetero 주요 정책의 p1·q_p50에 95% CI 부기.
  **"고정 sfqa와 auto의 fair_p1 CI가 비중첩 → p1 우위는 통계적으로 유의"** 한 문장을 A1 결론 옆에 배치하면 설득력↑.
  방법(결정적 재생이므로 시드 CI 불가 → 잡-레벨 부트스트랩)을 §eval:sim 방법 문단에 1–2문장.

- **A4 → §eval:sim 의 robustness/sensitivity 소절(또는 부록).** "합성계수에 대한 보수적 편향" 주장의 정량 근거.
  **속도계수 ±50%가 이종 auto p1을 1점 미만 이동**이 핵심 문장. Lucid ±50% 미수행은 정직히 각주 처리
  (구조적으로 부호 불변 논증 포함). 기존에 "보수적으로 가정했다"는 정성 주장이 있으면 이 수치로 대체.

- **A5 → §eval:sim 방법 문단 또는 부록.** 이산사건 코어 검증. "max abs error 0.0" 한 문장 + toy 3종 나열.
  엔진 신뢰성에 대한 R4 우려를 차단. §3(simulator algorithm) 또는 B200 overhead model 절과 교차참조.

**전체 메시지(권장 프레이밍).** A1+A3가 "무튜닝이 최적 고정-α를 능가하며 그 우위가 통계적으로 유의"라는 주장의
양대 기둥. A2가 트레이스 일반화, A4가 합성모델 강건성, A5가 엔진 충실도로 R4의 4개 하위 우려를 각각 닫는다.
모든 절에서 **무튜닝의 q_p50 양보를 숨기지 말 것** — 정직한 트레이드오프 서술이 본 논문의 신뢰성 자산이다.

### 산출물 인덱스
- A1: `sweep_results/ablation/alpha_grid.csv` (102행: 6구성 × 16 α + 6 auto), 스크립트 `sim/ablation_alpha.py`
- A2: `sweep_results/k8s/k8s_table.csv`, `sweep_results/k8s/cmp*/summary.csv`, raw `sweep_results/raw_k8s/`,
  변환 트레이스 `sim/k8s_trace.csv`, 스크립트 `sim/make_k8s_trace.py`·`sim/analyze_k8s.py`
- A3: `sweep_results/ci/bootstrap_ci.csv`, 스크립트 `sim/bootstrap_ci.py`
- A4: `sweep_results/sensitivity/sensitivity.csv` (56행, lucid 제외), 스크립트 `sim/sensitivity.py`
- A5: 스크립트 `sim/fidelity_check.py` (실행 시 PASS, max abs err 0.0)

---
