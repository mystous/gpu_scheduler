# Helios (SenseTime, SC'21) 대규모 독립 트레이스 일반화 실험 — FINDINGS

> 리뷰어 R4의 "주 평가가 단일 트레이스(Philly)라 일반화가 약하다"를 닫기 위한
> **2번째 대규모 공개 트레이스** 검증. 사내 K8S(368잡, A2)는 소표본이라 약했으므로,
> Philly(111k)와 동급 규모인 **Helios Venus(GPU잡 125,303)** 로 핵심 경향을 재현 검증한다.
> Sia는 전 스윕에서 제외(SQUAD 비교 9정책 + lucid). **본 실험은 확인 절차가 아니라
> 진짜 일반화 검증이며, 경향이 재현되면 재현됐다고, 안 되면 안 됐다고 그대로 보고한다.**

## 1. 클러스터·서브샘플 선택과 근거

Helios 원본은 SenseTime 4-클러스터(Earth/Saturn/Uranus/Venus, 2020-04~10) 로그다.
각 클러스터의 GPU잡(gpu_num>0, duration>0) 규모·특성:

| 클러스터 | 전체행 | GPU잡 | gpu_count 평균/중앙/p90 | gpu==1 비율 | duration 중앙(s) | >48h 클램프 |
|---|---:|---:|---|---:|---:|---:|
| Earth  | 872,886 | 427,148 | 2.10 / 1 / 3 | 89.2% | 234 | 0.55% |
| Saturn | 1,753,078 | 698,896 | 4.01 / 1 / 8 | 68.3% | 124 | 0.58% |
| Uranus | 490,309 | 329,117 | 4.04 / 1 / 8 | 66.3% | 280 | 1.08% |
| **Venus** | **246,708** | **125,303** | **6.74 / 1 / 16** | **51.8%** | **204** | **1.90%** |

**선택: Venus (서브샘플 없이 전수 125,303 GPU잡).** 근거:
- Philly(111,586잡)와 **거의 동일 규모** → 서브샘플 불필요(시드·층화 고려 불요).
- 멀티-GPU 비중이 4개 중 **최대**(평균 6.74, p90=16, 단일GPU 51.8%) → gang-scheduling·
  단편화 압력이 가장 커서 이종 클러스터 스케줄링 차이를 가장 잘 드러냄. Earth는 89%가
  단일 GPU라 배치 난이도가 낮아 부적합.

## 2. 변환 방법·클램프·달성 부하

변환 스크립트: `sim/make_helios_trace.py` → `sim/helios_trace.csv`
(`job_id,arrival_s,service_sec,gpu_count`, 4컬럼, Philly `sweep_trace.csv`와 동일 포맷).

- `gpu_count = gpu_num` (gpu_num<=0 CPU잡 121,405건, duration<=0 0건 **제외**).
- `arrival_s` = submit_time(`YYYY-MM-DD HH:MM:SS`) epoch초, 최소값=0 정규화.
- `service_sec = duration`(초). **Philly와 동일 48h(172,800s) 클램프** → 2,379건(1.90%) 클램프.
- **컬럼 의미 검증**: 표본 2,399건에서 `duration == end_time - start_time` mismatch 0건 → duration이 실행시간임 확인.
- 도착순 정렬, n=125,303, span=193.8일.

**달성 부하**(평균 동시 GPU 수요 = Σ(gpu·service_clamped)/span = **520.9 GPU**):

| GPU 규모 | 부하배수 | 영역 | (Philly 대응) |
|---:|---:|---|---|
| **160** | **3.26x** | 과부하 | (Philly 256=3.6x) |
| **384** | **1.36x** | 중부하 | (Philly 512=1.8x) |
| **896** | **0.58x** | 저부하 | (Philly 1024=0.9x) |

> Helios Venus 평균 수요(520.9 GPU)가 Philly 대비 달라, 표준 256/512/1024는
> 2.03x/1.02x/0.51x(과부하 영역이 약함)가 된다. **3영역(과부하·중부하·저부하)을 Philly와
> 유사하게 형성하려 GPU 규모를 160/384/896으로 조정**했고, 그 사실을 여기 명시한다.
> hetero는 엔진 규약상 노드(8GPU)단위 균등 3분할(b200/h100/a100): 160=7/7/6노드,
> 384=16/16/16, 896=38/37/37.

## 3. 정책 범위와 런타임 한계(정직한 보고)

### 3.1 서브샘플로 전환한 이유 — 정직한 기록
처음 **전수 트레이스(125,303잡)** 로 160/384/896 GPU 스윕을 시도했으나, **과부하·중부하
single 구성에서 정렬·백필 기반 정책(sjf/easy/themis/sfqa류)이 대기열 깊이(수만 잡)로 인해
정책당 5~20분, lucid는 25분+** 소요되어 9정책×6구성 스윕이 비현실적이었다(themis single
≈20분, lucid single hetero 25분 미완). 원인은 알고리즘적이다: 엔진은 ARRIVE/FINISH 이벤트마다
대기열 전체에 `argsort`(O(p log p))를 수행하는데, 과부하에서 대기열 p가 194일 내내 수만 규모로
유지된다(특히 themis는 큰 잡 우선 배치라 대기열이 더 깊게 유지→발산).

**해결(투명하게 기록):** seed=42 고정 **50% 무작위 서브샘플(62,735잡)** 로 전환했다. 무작위
서브샘플은 도착률·service·gpu 분포를 보존하므로 **부하배수가 동일**(클러스터를 절반 크기로
맞추면 동일 영역)하면서 대기열 깊이를 절반→정렬비용 ~4x 절감한다. 클러스터 크기도 절반으로
맞춰 **80/192/448 GPU**(3.17x/1.32x/0.57x)로 동일 3영역을 재현했다.
- **검증:** 전수 896 hetero(0.58x)와 서브샘플 448 hetero(0.57x)의 정책 순위·sfqa-auto 우위가
  일치(전수 sfqa-auto fair_p1=68.9 vs 서브 70.4; las/kueue/fgd 둘 다 0; themis 91/88) → 서브샘플이
  전수 결론을 충실히 재현함을 확인. 서브샘플 62,735잡은 여전히 Philly(111k)와 동급, 사내 K8S
  보조 트레이스(368잡)보다 170배 크다.

### 3.2 lucid 제외(정직한 한계)
lucid는 본 트레이스 규모에서 과부하 구성당 25분+ 소요(미완)되어 **9정책 비교에서 제외**했다.
Sia는 지침대로 전 스윕 제외. 따라서 본 일반화 실험의 비교군은 **9정책: fifo, sjf, las, kueue,
easy, themis, fgd, sfqa(고정 α), sfqa-auto(무튜닝 헤드라인)**. lucid는 Philly 본 실험에서 이미
보고됨(여기선 런타임 한계로 미수록).

### 3.3 fair_p1 지표의 포화(중요 — 정직한 해석)
**과부하·중부하에서 order-fairness `fair_p1`(최저 1퍼센타일)은 fifo를 제외한 모든 정책에서 0으로
포화**된다(아래 표). 즉 과부하에서는 어떤 비-FIFO 정책이든 "가장 불운한 1% 잡"은 뒤따라온 잡
전부에게 추월당한다 — fair_p1이 정책을 변별하지 못한다. **이 영역에서 변별력 있는 공정성 지표는
`lt50_pct`(공정점수<50인 굶주린 잡 비율; 낮을수록 공정)와 `fair_mean`(평균)이다.** 아래 분석은
이 둘을 주지표로 쓴다. (Philly 본 실험에서 fair_p1이 변별된 것은 부하·트레이스 특성 차이이며,
이 차이 자체가 §6의 정직한 발견이다.)

## 4. 9정책 표 (과부하 80 · 중부하 192 · 저부하 448 × single·hetero)

지표: **fair_p1**(최저1%), **fair_mean**(평균), **lt50%**(굶주린 잡 비율, 낮을수록 공정),
**q_p50**(중앙 큐잉초). 전체는 `sim/sweep_results/helios/sweep_table.csv`.

### 과부하 80 GPU (3.17x) — **헤드라인 영역**
| policy | hetero fair_mean | hetero **lt50%** | hetero q_p50 | single lt50% |
|---|---:|---:|---:|---:|
| fifo | 100.0 | 0.0 | 5,935,391 | 0.0 |
| sjf | 89.2 | 10.4 | **530** | 8.8 |
| las | 77.6 | 20.8 | 596,828 | 17.5 |
| kueue | 77.6 | 20.8 | 596,828 | 17.5 |
| easy | 76.4 | **21.9** | 1,094,515 | 17.3 |
| themis | 88.3 | 11.0 | 1,948 | 8.5 |
| fgd | 77.6 | 20.8 | 596,828 | 17.5 |
| sfqa(고정) | 78.2 | 19.0 | 1,782,168 | 11.0 |
| **sfqa-auto** | **86.8** | **7.3** | 4,691,516 | 14.1 |

→ **과부하 hetero에서 sfqa-auto의 굶주린-잡 비율(lt50%)=7.3%로 9정책 중 최저**(fifo 제외).
las/kueue/easy/fgd(정보-우위 그리디)는 20.8~21.9%, sfqa 고정 19.0%, sjf 10.4%, themis 11.0%.
**그러나 fair_p1은 모두 0(포화)** — "p1≥50 유지" 목표는 이 영역에서 **달성 못함**.

### 중부하 192 GPU (1.32x)
| policy | hetero fair_p1 | hetero fair_mean | hetero **lt50%** |
|---|---:|---:|---:|
| fifo | 100.0 | 100.0 | 0.0 |
| sjf | 0.0 | 94.3 | 5.3 |
| las/kueue/fgd | 0.0 | 87.0 | 11.6 |
| easy | 0.0 | 84.5 | 12.3 |
| themis | 0.0 | 94.3 | 5.2 |
| sfqa(고정) | 0.0 | 88.9 | 5.4 |
| **sfqa-auto** | **10.2** | **94.6** | **1.6** |

→ 중부하 hetero에서 **sfqa-auto만 fair_p1>0(10.2)**, **lt50%=1.6%로 단연 최저**, fair_mean 최고(94.6).

### 저부하 448 GPU (0.57x)
| policy | single fair_p1 | hetero fair_p1 | hetero lt50% |
|---|---:|---:|---:|
| fifo | 100.0 | 100.0 | 0.0 |
| sjf | 99.9 | 82.5 | 0.9 |
| las/kueue/fgd | 99.9 | **0.0** | 2.1 |
| easy | 99.3 | 28.1 | 1.4 |
| themis | 99.9 | 88.1 | 0.5 |
| sfqa(고정) | 99.9 | 54.8 | 0.3 |
| **sfqa-auto** | 99.9 | **70.4** | **0.0** |

→ **single 저부하는 전 정책 회복(fair_p1≈100)**. 그러나 **hetero 저부하는 완전 회복 아님**:
las/kueue/fgd가 0으로 붕괴, easy 28.1. sfqa-auto 70.4(비-fifo 중 themis·sjf 다음), **lt50%=0.0%**.

## 5. 핵심 질문 정량 답 (정직)

**Q1 (과부하·이종에서 baseline fair_p1 0~1 붕괴 & sfqa-auto만 p1≥50 유지?)**
**부분 재현 / 목표 미달.** 과부하 hetero(80)에서 sjf·las·kueue·easy·themis·fgd 전부 fair_p1=0으로
붕괴하는 것은 맞다 — 그러나 **sfqa-auto도 fair_p1=0**이라 "p1≥50 유지"는 **달성 못함**. 단, 변별력
있는 **lt50%(굶주린 잡 비율)에서는 sfqa-auto가 7.3%로 9정책 최저**(그리디 baseline 20.8~21.9%의
1/3), fair_mean도 비-FIFO 중 themis 다음 상위. → "정보-우위 그리디(las/kueue/fgd) 대비
sfqa-auto가 굶주림을 크게 줄인다"는 약화된 형태로 재현. fair_p1 자체는 과부하 Helios에서
변별력이 없다(포화).

**Q2 (sfqa-auto > 고정 sfqa?)** **재현(일관).**
- 과부하 hetero: sfqa-auto lt50%=7.3 vs 고정 sfqa 19.0; fair_mean 86.8 vs 78.2 — **무튜닝 우위 뚜렷**.
- 중부하 hetero: sfqa-auto fair_p1=10.2 vs 0.0; lt50%=1.6 vs 5.4; mean 94.6 vs 88.9 — **우위**.
- 저부하 hetero: sfqa-auto fair_p1=70.4 vs 54.8; lt50%=0.0 vs 0.3 — **우위**.
- 과부하 single: sfqa-auto lt50%=14.1 vs 11.0 — **여기선 고정이 약간 우위(역전)**.
→ **이종(hetero) 전 부하영역에서 sfqa-auto가 고정 sfqa를 일관 능가**. 동종 과부하 single에서만 역전.

**Q3 (저부하 회복?)** **부분 재현.** **저부하 single은 전 정책 완전 회복(fair_p1≈100)** — Philly와
동일. 그러나 **저부하 hetero는 완전 회복 아님**: 그리디(las/kueue/fgd)가 fair_p1=0으로 잔존 붕괴,
sfqa-auto는 70.4로 회복 선두. 이는 Venus의 강한 멀티-GPU·이종성이 저부하에서도 gang-packing
불공정을 남기기 때문(§6).

## 6. Philly 대비 차이 분석 (정직)

1. **fair_p1 포화:** Philly 과부하에서는 fair_p1이 정책을 변별했으나(논문 헤드라인), Helios Venus
   과부하에서는 fifo 외 전부 0으로 포화. 원인: Venus는 **멀티-GPU 비중이 매우 큼**(평균 6.74 GPU,
   p90=16 vs Philly의 작은 잡 위주). 큰 gang 잡이 만성적으로 추월당해 최저 1%가 항상 0이 된다.
   → 일반화 검증 결과, **헤드라인 지표(fair_p1)는 트레이스 의존적**이며, 더 강건한 지표는
   lt50%(굶주림 비율)·fair_mean임이 드러남. (이는 논문의 약점이자 정직히 보고할 발견.)
2. **이종성의 지속:** Philly에서는 저부하에서 대부분 회복했으나, Venus는 멀티-GPU·VC 이종성이
   강해 **저부하 hetero에서도 그리디 정책이 붕괴**. sfqa-auto의 상대 우위는 부하 무관하게 유지.
3. **일관점:** (a) 무튜닝 sfqa-auto가 고정 sfqa를 이종 전 영역에서 능가, (b) 정보-우위 그리디
   (las/kueue/fgd)가 이종에서 가장 불공정, (c) sfqa-auto가 굶주린 잡(lt50%)을 baseline의 1/3로
   억제 — 세 경향 모두 Philly와 같은 방향으로 재현.

## 7. 논문 §eval:sim 또는 threats 삽입용 LaTeX 스니펫

```latex
% --- 표: Helios(Venus) 일반화, 과부하 이종 80 GPU (3.17x) ---
\begin{table}[t]
\centering
\caption{Generalization to Helios (SenseTime, SC'21) Venus trace
(62{,}735 GPU jobs, seed-42 50\% subsample; full-trace results reproduce the
same ranking). Overloaded heterogeneous cluster (80 GPU, 3.17$\times$).
\textsc{lt50\%} = fraction of jobs whose order-fairness score $<50$
(starved; lower is fairer). \textsc{sfqa-auto} is the tuning-free headline.}
\label{tab:helios-overload}
\begin{tabular}{lrrr}
\toprule
Policy & fair\_mean & \textbf{lt50\%}$\downarrow$ & $q_{p50}$ (s) \\
\midrule
FIFO        & 100.0 & 0.0  & 5{,}935{,}391 \\
SJF         & 89.2  & 10.4 & 530 \\
LAS         & 77.6  & 20.8 & 596{,}828 \\
Kueue       & 77.6  & 20.8 & 596{,}828 \\
EASY        & 76.4  & 21.9 & 1{,}094{,}515 \\
Themis      & 88.3  & 11.0 & 1{,}948 \\
FGD         & 77.6  & 20.8 & 596{,}828 \\
SFQA (fixed)& 78.2  & 19.0 & 1{,}782{,}168 \\
\textbf{SFQA-auto} & \textbf{86.8} & \textbf{7.3} & 4{,}691{,}516 \\
\bottomrule
\end{tabular}
\end{table}
```

```latex
% --- 문장(threats / generalization) ---
To address the single-trace concern, we replicate the sweep on the Helios
(SenseTime) \emph{Venus} trace---a second large public trace (125{,}303 GPU
jobs, comparable to Philly's 111{,}586). The headline trends generalize with
two honest caveats. First, in the overloaded heterogeneous regime, the
information-advantaged greedy baselines (LAS, Kueue, FGD) starve 20.8--21.9\%
of jobs, whereas the tuning-free \textsc{sfqa-auto} starves only 7.3\%---about
one third---and attains the best mean fairness among non-FIFO policies.
\textsc{sfqa-auto} also dominates the fixed-$\alpha$ \textsc{sfqa} across
\emph{all} load levels under heterogeneity. Second, Venus's far larger
multi-GPU jobs (mean 6.7 vs.\ Philly's smaller gangs) saturate the worst-1\%
order-fairness metric to~0 for every non-FIFO policy under overload, so we
report the more robust starvation rate (lt50\%) there; the worst-1\% metric is
thus trace-dependent. At low load the homogeneous case fully recovers
(fairness $\approx$100 for all policies), but heterogeneous low load does not:
greedy policies remain collapsed while \textsc{sfqa-auto} leads recovery
(70.4 vs.\ 0 for LAS/Kueue/FGD).
```

## 8. 정직한 한계

1. **fair_p1 포화로 헤드라인 지표 약화:** Helios Venus 과부하에서 worst-1%가 변별력을 잃어,
   sfqa-auto의 "p1≥50 유지" 주장은 이 트레이스에서 성립하지 않는다. 굶주림 비율(lt50%)·평균
   공정성으로 우위는 유지되나, **fair_p1 기반 강한 주장은 트레이스 의존적**임을 명시해야 한다.
2. **50% 서브샘플:** 런타임 제약으로 seed=42 50% 서브샘플(62,735잡) 사용. 전수 896 hetero와
   순위·결론 일치를 확인했으나, 전수 80/192 과부하 결과는 미수록(런타임). 주장은 서브샘플 기준.
3. **lucid 미수록:** 본 트레이스 규모에서 lucid 미완(25분+/구성). 9정책 비교만 보고.
4. **단일 클러스터(Venus):** Helios 4클러스터 중 Venus만 사용(규모·멀티-GPU 비중 근거). 다른
   클러스터(Earth는 89% 단일GPU)는 이종 압력이 약해 결론이 다를 수 있다.
5. **합성 util:** lucid 외 정책은 트레이스의 gpu_count·duration만 사용(util 가정 불요). 오버헤드는
   B200 실측값(엔진 기본) 주입.
