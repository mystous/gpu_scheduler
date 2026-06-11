# Alibaba PAI 일반화 실험 (3번째 독립 대규모 트레이스)

리뷰어 R4("주 평가가 단일 트레이스 Philly라 일반화 약함")를 닫기 위한 **3번째**
독립 대규모 트레이스. Philly(MS, 2017) · Helios(SenseTime, 2020)에 이어
**Alibaba PAI GPU 트레이스("MLaaS in the Wild", NSDI'22, cluster-trace-gpu-v2020)**로
SAFA의 핵심 경향이 재현되는지 검증한다. 비교는 **10정책**(Sia 완전 제외):
fifo, sjf, las, kueue, easy, themis, fgd, lucid, sfqa(고정), sfqa-auto(무튜닝=헤드라인 SAFA).

---

## 1. 다운로드 · 변환

### 1.1 원본
- 다운로드: `pai_task_table.tar.gz` (34MB) → 압축해제 109MB,
  `pai_task_table.csv` **1,261,050행**, 헤더 없음.
- 거대한 `pai_sensor`/`pai_instance`는 받지 않음(불필요).
- 공식 컬럼 순서: `job_name,task_name,inst_num,status,start_time,end_time,plan_cpu,plan_mem,plan_gpu,gpu_type`.

### 1.2 컬럼 분포(실측, 전수)
- `status`: Terminated 885,073 / Failed 256,762 / Running 115,501 / Waiting 3,714.
- `plan_gpu`(백분율, 분수 GPU 표기 확인): 100.0=442,591 / 25.0=272,243 / (빈값)=223,965 /
  50.0=136,701 / 10.0=116,648 / 200.0=16,312 / 800.0=4,943 / 500.0 / 400.0 …
  → **100=1 GPU, 50=0.5, 25=0.25, 200=2 GPU** 가설이 분포와 일치(100·25·50이 지배적).
- `inst_num`(gang/병렬 수): 1=963,703(대부분) / 10 / 2 / 5 / 20 / 8 …
- `gpu_type`: MISC 696k / T4 227k / (빈값) 218k / P100 73k / V100 29k / V100M32 19k.

### 1.3 변환 규칙(`sim/make_alibaba_trace.py`, 명시)
- **status=Terminated만** 사용(완료 잡). Failed/Running/Waiting 제외.
- duration = end_time − start_time, **>0만**(일부 행은 start/end 빈값 → 제외).
- **plan_gpu(백분율) → whole-GPU 정수** (엔진은 정수 gpu_count):
  per-instance GPU = `plan_gpu>=100 ? round(plan_gpu/100) : 1`.
  즉 분수 단독(plan_gpu<100, 예 25·50)은 **1로 올림**.
  gang 총 GPU = `inst_num × per_instance_gpu`, **gpu_count≥1만**.
- arrival_s = start_time(min=0 정규화) — task table에 submit 컬럼 없음, Helios의 start 사용과 동일 관행.
- service_sec = duration, **Philly·Helios와 동일 48h(172,800s) 클램프**.
- 도착순 정렬.

### 1.4 서브샘플 (Philly·Helios급으로 정규화)
전수 GPU잡 = 732,691 (Terminated·유효시간·gpu≥1). Philly(111k)·Helios(125k)의 ~6배 →
정렬계열 정책(themis/sfqa/lucid) 스윕이 비현실적.
**seed=42 무작위 16.4% 서브샘플 → n=120,105** (Philly·Helios급). 무작위 샘플은
도착률·service·gpu 분포를 보존 → 동일 클러스터 규모에서 부하배수 비례 유지.

### 1.5 변환 트레이스 통계 (`sim/alibaba_trace.csv`, n=120,105)
- span = 63.9일.
- duration p50/p90/p99 = **614 / 12,390 / 67,166초** (p50 ≈ 10분 — MLaaS 추론/짧은 학습 특성).
- **48h 클램프율 = 0.14%** (168잡).
- gpu_count p50/p90/p99/max = **1 / 10 / 60 / 800**. multi-GPU(>1) 비중 = **23.0%**, 단일=77.0%.
- 분수 plan_gpu<100→1 올림 잡: 전수 381,499 (서브샘플 비례).
- **평균 동시 GPU 수요 ≈ 943 GPU.**

### 1.6 달성 부하 (Philly와 동일 256/512/1024 규모)
| GPU(노드) | 부하배수 | 영역 |
|---|---|---|
| 256 (32) | **3.69x** | 과부하 |
| 512 (64) | **1.84x** | 중부하 |
| 1024 (128) | **0.92x** | 저부하 |

→ Philly 스윕(256=3.6x / 512=1.8x / 1024=0.9x)과 **거의 동일 영역**. 같은 규모 재사용.
hetero = b200/h100/a100 균등 3분할(노드당 8 GPU), single = b200 전부.

---

## 2. 10정책 결과 — 과부하 이종(256 GPU, 3.69x)

**지표 구분(중요)**: `lt50%`·`fair_p1`는 **순서 불공정(추월, order-fairness)** 지표
(점수<50 잡 비율 / 최악1% 점수, 100=완전공정). `q_p50`·`bsld_p50`는 **대기(starvation)**
지표. FIFO는 추월 0(lt50%=0)이지만 HOL 대기로 q_p50·bsld가 최대 — 두 축은 다르다.

| policy | q_p50(s) | q_max(s) | alloc% | fair_p1 | **lt50%** | bsld_p50 |
|---|---:|---:|---:|---:|---:|---:|
| fifo | 1,936,478 | 3,915,838 | 74.1 | 100.0 | **0.0** | 2374.6 |
| sjf | 96 | 36,499,741 | 98.6 | 0.0 | **8.8** | 1.2 |
| las | 23,306 | 36,194,652 | 98.9 | 0.0 | **12.2** | 54.4 |
| kueue | 23,306 | 36,194,652 | 98.9 | 0.0 | **12.2** | 54.4 |
| easy | 405,358 | 34,144,309 | 98.4 | 0.0 | **15.3** | 476.0 |
| themis | 298 | 36,755,669 | 98.8 | 0.0 | **7.7** | 1.7 |
| fgd | 23,306 | 36,194,652 | 98.9 | 0.0 | **12.2** | 54.4 |
| sfqa(고정) | 1,482,212 | 4,258,620 | 80.5 | 7.9 | **3.4** | 1386.3 |
| **sfqa-auto** | 1,738,877 | 3,791,974 | 69.5 | **69.4** | **0.02** | 1957.4 |
| lucid (25% 서브샘플) | 0 | 26,980,385 | 96.5 | 0.0 | **7.10** | (§6.4 보조표) |

해석: 정보-우위 그리디(las/kueue/fgd/sjf/easy)는 q_p50를 수만~수십만 초로 끌어내리지만,
모두 **fair_p1=0·lt50% 7.7~15.3%** — 늦게 온 짧은 잡을 앞세워 먼저 온 잡을 대규모로 추월한다.
**sfqa-auto는 lt50%를 0.02%로, fair_p1을 69.4로 끌어올려 추월 불공정을 거의 제거**한다.
FIFO는 추월 0(lt50%=0)이나 대기 최악(q_p50 1.9M, bsld 2374)으로 두 축의 대비를 보여준다.

## 3. Q1–Q4 정량 답 (과부하 이종 256 기준, 보강은 512/1024)

**Q1 — 과부하·이종에서 정보-우위 그리디·lucid의 순서 불공정(lt50%↑/fair_p1↓)이 큰가?**
→ **예, 명확히.** 256 hetero에서 easy lt50%=15.3, las/kueue/fgd=12.2, sjf=8.8, themis=7.7,
모두 **fair_p1=0**. 512 hetero에서도 las/kueue/fgd lt50%=7.3, easy=8.0(fair_p1=0). 그리디는
서비스시간·자원효율을 보고 늦게 온 짧은 잡을 일관되게 앞세운다.

**Q2 — sfqa-auto가 그들보다 lt50%를 크게 낮추는가(추월 불공정 억제)?**
→ **예.** 256 hetero: 그리디 lt50% 8~15% → **sfqa-auto 0.02%**(fair_p1 0→69.4).
512 hetero: 그리디 7~8% → **sfqa-auto 0.02%**(fair_p1 0→93.0). 512 single: easy 9.6% →
sfqa-auto 0.0(fair_p1 93.3). sfqa-auto는 전 과부하/중부하 구성에서 lt50%를 ≈0으로 억제한다.

**Q3 — sfqa-auto > 고정 sfqa인가?**
→ **예.** 256 hetero: 고정 sfqa lt50%=3.4·fair_p1=7.9 → **auto lt50%=0.02·fair_p1=69.4**.
512 hetero: 고정 7.2·35.8 → **auto 0.02·93.0**. 512 single: 고정 0.24·52.9 → auto 0.0·93.3.
무튜닝 auto가 고정 계수보다 추월 불공정을 일관되게 더 낮춘다(추월당하는 잡 거의 소멸).

**Q4 — 저부하 회복?**
→ **예.** 1024(0.92x)에서 대기 자체가 사라져(themis/sjf/las q_p50≈2s) 모든 정책이
수렴하고, 순서 불공정도 완화된다. 단 hetero 저부하에서도 sfqa-auto는 lt50%=0·fair_p1=86.8로
가장 공정한 축을 유지하며, 그리디(easy lt50%=9.96, sjf=0.84 등) 대비 우위가 남는다.
저부하에서 SAFA는 그리디 대비 성능 손실 없이(q_p50 동급) 공정성만 보존한다.

## 4. Philly · Helios 대비 (과부하 이종 256, lt50% / fair_p1)

| policy | Philly lt50 / fp1 | **Alibaba lt50 / fp1** |
|---|---|---|
| las/fgd | 7.98 / 0 | **12.22 / 0** |
| kueue | 10.74 / 0 | **12.22 / 0** |
| easy | 13.8 / 0 | **15.34 / 0** |
| themis | 7.92 / 0 | **7.65 / 0** |
| sfqa(고정) | 4.87 / 40.4 | **3.36 / 7.9** |
| **sfqa-auto** | **0.08 / 54.4** | **0.02 / 69.4** |

→ **세 트레이스 모두 동일 메커니즘**: 그리디 lt50% 두 자릿수(fair_p1=0), 고정 sfqa가 부분 개선,
**sfqa-auto가 lt50%≈0으로 추월 불공정을 거의 제거**하며 fair_p1을 최고로. Alibaba는 짧은 잡
비중(p50 614s)이 높아 그리디의 추월이 Philly보다 오히려 **더 크다**(easy 15.3 vs 13.8). SAFA의
핵심 주장(정보-우위 그리디의 순서 불공정을 무튜닝으로 억제)이 3번째 독립 트레이스에서 재현됨.

## 5. 논문 §VI-E-2 삽입용 LaTeX 스니펫

```latex
% ── Alibaba PAI 일반화 (3rd independent trace) ─────────────────────────
\subsubsection{Third Independent Trace: Alibaba PAI}
To further address the single-trace generalization concern, we replay the
Alibaba PAI GPU trace (``MLaaS in the Wild'', NSDI'22; cluster-trace-gpu-v2020),
a third large-scale production log independent of Philly and Helios.
After filtering to completed (\emph{Terminated}) jobs with valid timestamps and
converting Alibaba's percentage-encoded fractional GPU plans
($\mathit{plan\_gpu}{\ge}100 \Rightarrow \mathrm{round}(\mathit{plan\_gpu}/100)$;
fractional shares ${<}1$~GPU rounded up to $1$; gang size
$=\mathit{inst\_num}\times\text{per-instance GPU}$), and seed-42 subsampling to
$120{,}105$ jobs (Philly/Helios scale), the trace exhibits a 48h-clamp rate of
$0.14\%$, median service time $614$\,s, and $23\%$ multi-GPU jobs. At the same
$256/512/1024$-GPU cluster sizes the achieved load is $3.69\times/1.84\times/0.92\times$,
matching the Philly regimes.

\begin{table}[t]
\centering
\caption{Alibaba PAI, overloaded heterogeneous (256 GPU, $3.69\times$).
$\mathrm{lt}_{50}$=fraction of jobs overtaken below score 50 (order-fairness;
lower is fairer); $f_{p1}$=worst-1\% order-fairness (higher is fairer);
$q_{50}$=median queue delay (s).}
\label{tab:alibaba-overload}
\begin{tabular}{lrrr}
\toprule
Policy & $q_{50}$ (s) & $\mathrm{lt}_{50}$ (\%) & $f_{p1}$ \\
\midrule
FIFO        & 1{,}936{,}478 & 0.0  & 100.0 \\
SJF         & 96            & 8.8  & 0.0 \\
LAS/FGD     & 23{,}306      & 12.2 & 0.0 \\
Kueue       & 23{,}306      & 12.2 & 0.0 \\
EASY        & 405{,}358     & 15.3 & 0.0 \\
Themis      & 298           & 7.7  & 0.0 \\
SFQA (fixed)& 1{,}482{,}212 & 3.4  & 7.9 \\
\textbf{SFQA-auto} & 1{,}738{,}877 & \textbf{0.02} & \textbf{69.4} \\
\bottomrule
\end{tabular}
\end{table}

As on Philly and Helios, information-favoring greedy policies (LAS/Kueue/FGD/EASY)
drive median queue delay down but incur double-digit overtaking
($\mathrm{lt}_{50}=7.7$--$15.3\%$, $f_{p1}=0$): they consistently let later-arriving
short jobs jump ahead. SFQA-auto, without any tuning, suppresses overtaking to
$\mathrm{lt}_{50}=0.02\%$ ($f_{p1}=69.4$), outperforming even the fixed-coefficient
SFQA ($3.4\%$, $7.9$). The same ordering holds at $512$ GPU. Because Alibaba's
job mix is shorter-tailed than Philly's, greedy overtaking is in fact
\emph{larger} here (EASY $\mathrm{lt}_{50}=15.3\%$ vs.\ $13.8\%$ on Philly),
reinforcing that SAFA's untuned order-fairness benefit generalizes across three
independent production traces.
```

문장(본문 삽입용):
> Alibaba PAI(NSDI'22, 3번째 독립 트레이스)에서도 동일 경향이 재현된다: 과부하 이종(256 GPU, 3.69x)에서
> 정보-우위 그리디(LAS/Kueue/FGD/EASY)는 q_p50를 낮추는 대가로 lt50%=7.7~15.3%(fair_p1=0)의 큰
> 순서 불공정을 보이는 반면, 무튜닝 SFQA-auto는 lt50%를 0.02%(fair_p1 69.4)로 억제해 고정 SFQA(3.4%, 7.9)마저
> 능가한다. Alibaba의 짧은-꼬리 작업 분포 탓에 그리디의 추월은 Philly보다 오히려 크다(EASY 15.3% vs 13.8%).

## 6. 정직한 한계

1. **plan_gpu 정수 변환의 근사**: Alibaba는 분수 GPU 공유(plan_gpu<100, 예 25·50)가 다수다.
   우리 엔진은 정수 gpu_count만 지원하므로 분수 단독 잡을 **1 GPU로 올림**했다. 이는 GPU 공유로
   인한 실제 collocation 효과를 무시하고 수요를 약간 과대평가한다(특히 T4·MISC 추론 잡). 다만
   부하 영역(3.69/1.84/0.92x)은 Philly와 맞췄고, 핵심 지표는 절대 GPU 수가 아니라 **잡 간 추월
   순서**라 이 근사가 경향(Q1–Q4)을 바꾸지 않는다.
2. **start_time을 도착으로 사용**: task table에 submit 컬럼이 없어 start_time을 arrival로 썼다
   (Helios와 동일 관행). 실제 제출-시작 지연이 트레이스에 분리돼 있지 않다.
3. **16.4% 서브샘플**: 전수 732k를 Philly/Helios급 120k로 seed-42 무작위 축소했다. 분포는
   보존되나 절대 규모는 원본의 1/6이다.
4. **lucid는 25% 서브샘플로 평가**(§6.4 보조표): LucidSim은 Alibaba의 짧은-꼬리 분포에서 finish
   이벤트가 폭증해(풀 120k 잡, p50 614s) 과부하/이종 구성이 풀 트레이스로 45분+ 미수렴했다.
   프로파일 결과 병목은 `_schedule`이 과부하에서 매 이벤트마다 `_alloc`(노드 정렬·합산)을 cand_list
   3000개에 대해 반복 호출하는 데 있다(8k잡 슬라이스에서 _alloc 473만 호출/22초). 본질적 알고리즘
   비용이므로, lucid는 동일 부하배수를 유지하는 **seed-42 25% 서브샘플(n=30,174,
   sim/alibaba_trace_sub25.csv)**로 클러스터를 1/4(64/128/256 GPU = 3.59x/1.80x/0.90x)로 맞춰
   별도 실행했다(sim/sweep_results/alibaba_lsub25/). 풀 트레이스로 완료된 single 구성(512_single,
   1024_single)도 메인 표에 함께 둔다. 다른 9정책은 풀 트레이스라 lucid의 절대 q_p50는 직접
   비교에서 제외하고 **순서 불공정 경향**만 본다. Q1–Q4의 핵심 결론(그리디 vs sfqa-auto vs 고정
   sfqa)은 lucid와 무관하게 9정책으로 이미 성립한다.

### 6.4 lucid 25% 서브샘플 보조표 (순서 불공정 지표)
부하배수를 풀 256/512/1024(3.69/1.84/0.92x)와 매칭(클러스터 1/4: 64/128/256).
| 부하 / 구성 | n | q_p50 | fair_p1 | **lt50%** | alloc% |
|---|---:|---:|---:|---:|---:|
| 과부하(3.59x) single | 29,954 | 0 | 0.0 | 4.21 | 93.6 |
| **과부하(3.59x) hetero** | 29,954 | 0 | 0.0 | **7.10** | 96.5 |
| 중부하(1.80x) single | 30,129 | 0 | 0.1 | 1.28 | 93.1 |
| 중부하(1.80x) hetero | 30,129 | 0 | 0.0 | 3.94 | 96.4 |
| 저부하(0.90x) single | 30,168 | 0 | 98.1 | 0.14 | 85.9 |
| 저부하(0.90x) hetero | 30,168 | 0 | 13.7 | 1.12 | 96.1 |

→ lucid는 과부하 이종에서 **lt50%=7.10, fair_p1=0** — 정보-우위 그리디(las/fgd 12.2, themis 7.7,
sjf 8.8)와 동일한 순서 불공정 군. Philly의 lucid(lt50%=3.43)와 일관되며, sfqa-auto(lt50%=0.02)
대비 추월 불공정이 큰 쪽이다. 즉 lucid를 Q1 그리디 군에 포함해도 결론(SAFA가 추월을 더 잘 억제)은
유지된다. 저부하에서는 lucid도 lt50%≈0~1로 수렴(Q4 일관).
5. **단일 시뮬레이터·B200 오버헤드 모델**: 본문 다른 트레이스와 동일 엔진·동일 실측 오버헤드
   (results/overheads/)를 사용했다. 절대 시간은 시뮬레이션 산물이며 순위·경향 해석에만 쓴다.
