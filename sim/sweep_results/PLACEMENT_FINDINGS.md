# 배치(Node Placement) 축 실험 — SAFA의 스케줄러 무관성 실증

**질문**: SAFA(=SFQA)는 큐 **재정렬** 전처리기로, 그 아래 코어 GPU **배치(node placement)**
스케줄러와 **무관**하게 동작한다고 주장한다. 현재 시뮬은 배치를 most-allocated 하나로만
평가했다. 본 실험은 배치를 **most-allocated / compact / round_robin / mcts** 4종으로 바꿔도
**SAFA의 순서 공정성(p1) 이점이 유지됨**을 보여 "스케줄러 무관 전처리" 주장을 실증한다.

데이터: `sim/sweep_results/placement/placement_table.csv` (60 run, 에러 0).
하니스: `sim/placement_axis.py`, 배치 구현: `sim/placement_prefs.py`, 분석: `sim/placement_analyze.py`.

---

## 1. 구현 요약 (배치 4종 포팅 충실도·캡)

배치는 정책 인스턴스의 **`pref_fn`(노드 정렬 함수)**로 주입된다. 엔진 `_alloc`(engine.py:202)이
`policy.node_pref(job, nodes)` 순서대로 free GPU를 모아 멀티노드 gang을 구성한다. 하니스는
정책 인스턴스의 `pref_fn` 속성만 교체해 배치를 바꾼다(`policies.py`·`paper §SAFA` 불변).

| 배치 | 구현 | C++ 원본 | 포팅 |
|---|---|---|---|
| **mostallocated** | `pref_mostallocated` (기존) | scheduler_mostallocated | free 적은 노드 우선(단편화↓). 빠른타입 1차키. |
| **compact** | `pref_compact` (기존) | scheduler_compact | 인덱스 순(앞 노드부터). 빠른타입 1차키. |
| **round_robin** | `pref_round_robin`+`RoundRobinPref` (신규) | scheduler_round_robin.cpp | C++는 `current_server_index`를 회전시켜 다음 적합 서버 선택. pref_fn은 순수 정렬이라 인덱스 회전을 직접 복제 불가 → 라운드로빈 **취지(잡 고른 분산)**를 `free 많은 노드 우선`(most-alloc 정반대)으로 구현. `RoundRobinPref`는 호출마다 시작 오프셋을 회전시켜 동률 노드 간 순환 분산도 흉내(상태 보존). |
| **mcts** | `pref_mcts`/`MCTSPref` (신규) | scheduler_mcts.cpp | C++ 본질 = '후보 서버마다, 남은 대기 잡을 **무작위 서버에 배정하는 롤아웃**을 `simulation_count`회 돌려 **달성 할당률(max allocation)**을 보상으로 서버 평가'. pref_fn 인터페이스로 포팅: 후보 노드(free≥gpu_count)마다 그 노드에 잡 가정배치→남은 대기 잡(현재 큐, 깊이캡)을 무작위 노드에 배정하는 롤아웃을 N회 돌려 **최대 달성 할당률**을 점수로 매기고 노드를 점수 내림차순 정렬. **UCB 트리는 생략**하되 '롤아웃 기반 할당률 추정으로 서버를 고른다'는 MCTS 본질 보존. |

**MCTS 캡(보수적, 비용·종료 보장)**: 후보 노드당 롤아웃 `MCTS_ROLLOUTS=8`(C++ simulation_count=100→8),
롤아웃에 포함할 대기 잡 깊이 `MCTS_QUEUE_DEPTH=16`, 점수화 후보 노드 상한 `MCTS_MAX_CAND=12`
(나머지는 most-allocated 순으로 뒤에 붙임), 노드내 무작위 재시도 캡 6회.
**서브샘플 불필요**: full Philly 111,586잡에서도 mcts 최대 87s(아래 Q3)로 현실적이라 **전 배치를
동일 full 트레이스로 돌려 완전 공정 비교**(서브샘플로 인한 부하 밀도 왜곡 회피).

**검증(회귀 없음)**: mostallocated 배치 결과가 기존 `sweep_table.csv`의 15개 (구성×정책) 셀
q_p50·fair_p1 **전부와 정확히 일치** — 배치 주입 메커니즘이 기존 경로를 바꾸지 않음을 확인.

## 2. 실험 규모

- **배치 4종** × **정책 5종**(sfqa-auto, fifo, sjf, sfqa(고정α), las) × **구성 3종**
  (512:single, 512:hetero, 256:hetero=3.6× 과부하) = **60 run**, 모두 full 111,586잡.
- 노드: single=b200×8/노드, hetero=b200/h100/a100 균등 3분할. 오버헤드 모델 on(실측값).
- 지표: q_p50(중앙 큐 지연), fair_p1(worst-1% order-fairness; FIFO=100, 완전 역전=0), mcts wall-clock.

## 3. [배치 × 정책 × 구성] 표 — fair_p1 (높을수록 공정)

### 512:single (저부하 0.9×)
| policy | mostallocated | compact | round_robin | mcts |
|---|---:|---:|---:|---:|
| **sfqa-auto** | 53.07 | 54.19 | 62.05 | 54.97 |
| fifo | 100.00 | 100.00 | 100.00 | 100.00 |
| sjf | 64.11 | 64.11 | 64.11 | 64.11 |
| sfqa | 41.36 | 39.79 | 43.97 | 39.76 |
| las | 30.85 | 30.85 | 30.85 | 30.85 |

### 512:hetero (1.8× 과부하)
| policy | mostallocated | compact | round_robin | mcts |
|---|---:|---:|---:|---:|
| **sfqa-auto** | 50.52 | 52.15 | 53.72 | 50.63 |
| fifo | 100.00 | 100.00 | 100.00 | 100.00 |
| sjf | 0.00 | 0.00 | 0.00 | 0.00 |
| sfqa | 37.35 | 37.72 | 38.10 | 37.42 |
| las | 0.00 | 0.00 | 0.00 | 0.00 |

### 256:hetero (3.6× 과부하)
| policy | mostallocated | compact | round_robin | mcts |
|---|---:|---:|---:|---:|
| **sfqa-auto** | 54.41 | 53.95 | 59.48 | 53.41 |
| fifo | 100.00 | 100.00 | 100.00 | 100.00 |
| sjf | 0.00 | 0.00 | 0.00 | 0.00 |
| sfqa | 40.45 | 43.02 | 42.92 | 41.74 |
| las | 0.00 | 0.00 | 0.00 | 0.00 |

### q_p50 (초, 낮을수록 빠름) — 512:hetero / 256:hetero 발췌
| policy | 512h most | 512h rr | 512h mcts | 256h most | 256h rr | 256h mcts |
|---|---:|---:|---:|---:|---:|---:|
| sfqa-auto | 1,759,480 | 1,925,676 | 1,764,756 | 3,773,512 | 3,978,450 | 3,840,510 |
| fifo | 3,550,051 | 3,550,051 | 3,572,696 | 9,746,217 | 9,746,217 | 9,706,761 |
| sjf | 1,110 | 1,110 | 1,094 | 2,192 | 2,192 | 2,169 |

## 4. Q1~Q3 정량 답

### Q1 — SAFA의 p1 이점이 4배치 전부에서 유지되는가? **유지된다(과부하에서; 정직한 단서 포함).**

- **과부하/이종(512:hetero·256:hetero): 4배치 전부에서 SAFA 압승.** sfqa-auto p1≈50.5~59.5
  vs sjf=0 / las=0 (Δ = **+50.5 ~ +59.5**). 즉 SAFA만이 과포화에서 큰 잡을 굶기지 않아
  fifo 다음으로 공정. **이 우위는 mostallocated/compact/round_robin/mcts 어느 배치에서도 동일.**
  배치별 sfqa-auto p1 편차는 ±~6(round_robin이 미세 우위)로, **이점의 부호·규모가 배치에 불변.**
- **정직한 단서(저부하 512:single):** 이 구성에선 sjf의 p1(64.1)이 sfqa-auto(53~62)보다 약간 높다.
  부하가 낮아 sjf가 짧은 잡을 빠르게 비워 starvation이 발생하지 않는, SAFA가 겨냥하지 **않는**
  영역이다(기존 sweep도 동일). **중요한 건 이 관계가 4배치 모두에서 똑같이 나타난다는 점** —
  즉 "어떤 배치에서 SAFA가 좋고 어떤 배치에선 나쁘다"가 아니라, **배치를 바꿔도 정책 간 관계가
  보존**된다. SAFA는 las(p1=30.85)·sfqa(고정)보다는 모든 배치에서 일관되게 공정.

### Q2 — 배치가 절대 성능·정책 상대 순위를 바꾸는가? **상대 순위는 안 바꾼다(배치 무관 성립).**

- **p1 정책 순위가 4배치에서 완전히 동일** (세 구성 모두):
  - 512:single: `fifo > sjf > sfqa-auto > sfqa > las`
  - 512:hetero·256:hetero: `fifo > sfqa-auto > sfqa > sjf > las`
  - → **배치를 바꿔도 순위 불변 = "배치 무관" 핵심 주장 성립.**
- **절대 성능(q_p50)에 대한 배치 영향은 대체로 작다**: sfqa-auto q_p50 배치 spread는
  512s 15.1% / 512h 9.4% / 256h 5.4%. fifo·sjf는 ≤1.5%. 가장 큰 변동은 단편화에 민감한
  las(512h 65%) — 단 las의 p1은 모든 배치에서 0이라 **순위에는 영향 없음.**

### Q3 — MCTS 배치의 비용은? **most-allocated 대비 1.0~1.9×, 절대 최대 87s/111k잡 (현실적).**

| 구성 | mcts wall (정책 범위) | most-alloc wall | 배율 |
|---|---|---|---|
| 512:single | 13.9 ~ 47.9 s | 9.8 ~ 35.1 s | 1.2~1.9× |
| 512:hetero | 20.5 ~ 57.2 s | 13.5 ~ 60.5 s | 0.9~1.5× |
| 256:hetero | 16.3 ~ 87.0 s | 17.0 ~ 65.6 s | 1.0~1.3× |

- 최대 비용은 256:hetero/sfqa-auto의 **87s**(111,586잡, 후보당 8 롤아웃). full 트레이스에서도
  현실적이라 **서브샘플 없이** 전 실험을 수행. 캡(롤아웃 8·큐깊이 16·후보 12)이 종료를 보장.

## 5. 정직한 한계

1. **MCTS 충실도**: UCB 트리 선택·역전파는 생략하고 '롤아웃 할당률 추정으로 노드 점수화 →
   내림차순 정렬'만 보존했다. 본 실험 목적(배치를 4종으로 다양화해 SAFA 무관성 시험)에는
   충분하나, C++ MCTS의 트리 탐색을 100% 재현하지는 않는다(simulation_count도 100→8로 캡).
2. **round_robin**: pref_fn이 순수 정렬이라 C++의 인덱스 회전을 정확히 복제할 수 없다.
   본 표는 상태 보존형 `RoundRobinPref`(호출마다 시작 오프셋 회전 + free 많은 노드 우선)를 사용한다.
   라운드로빈 취지(분산)와 순환을 모두 흉내내나, free가 같은 노드가 적은 본 토폴로지에선 회전의
   효과가 제한적이다. 무상태 `pref_round_robin`(분산 키만)도 제공한다.
3. **저부하(512:single)에서 sjf p1 우위**: SAFA가 겨냥하지 않는 영역의 관측이며, 4배치 모두에서
   동일하게 나타나 "배치 무관" 주장과 모순되지 않는다. 과대해석 금지.
4. Sia 배치는 본 실험에서 제외(지시).

---

## 6. 논문 §eval(배치 무관성 소절)용 LaTeX 스니펫

```latex
\subsection{SAFA Is Agnostic to the Underlying Placement Policy}
\label{sec:eval-placement}

SAFA reorders the \emph{pending} queue and never moves running jobs, so its
fairness effect should be independent of the core node-placement policy beneath
it. We test this by replacing the placement layer with four schedulers ported
from the C++ core---most-allocated (fragmentation-minimizing), compact, round-robin
(load-spreading), and an MCTS placement that scores each candidate node by the
max GPU allocation reached over randomized rollouts---while keeping the SAFA queue
reordering and all other settings fixed. We sweep three configurations on the full
Philly trace (111{,}586 jobs): 512-GPU single-type, 512-GPU heterogeneous (1.8$\times$
overload), and 256-GPU heterogeneous (3.6$\times$ overload).

\begin{table}[t]
\centering
\caption{Worst-1\% order-fairness ($p_1$; FIFO$=100$) across four placement
policies. SAFA's advantage over throughput-greedy baselines (SJF, LAS) under
overload holds for \emph{every} placement; the policy ranking is identical across
all four columns (placement-agnostic).}
\label{tab:placement-p1}
\small
\begin{tabular}{llcccc}
\toprule
Config & Policy & MostAlloc & Compact & RoundRobin & MCTS \\
\midrule
\multirow{3}{*}{512 single}
 & \textbf{SAFA} & 53.1 & 54.2 & 62.1 & 55.0 \\
 & SJF & 64.1 & 64.1 & 64.1 & 64.1 \\
 & LAS & 30.9 & 30.9 & 30.9 & 30.9 \\
\midrule
\multirow{3}{*}{512 hetero}
 & \textbf{SAFA} & 50.5 & 52.2 & 53.7 & 50.6 \\
 & SJF & 0.0 & 0.0 & 0.0 & 0.0 \\
 & LAS & 0.0 & 0.0 & 0.0 & 0.0 \\
\midrule
\multirow{3}{*}{256 hetero}
 & \textbf{SAFA} & 54.4 & 54.0 & 59.5 & 53.4 \\
 & SJF & 0.0 & 0.0 & 0.0 & 0.0 \\
 & LAS & 0.0 & 0.0 & 0.0 & 0.0 \\
\bottomrule
\end{tabular}
\end{table}

Table~\ref{tab:placement-p1} shows that under heterogeneous overload, SJF and LAS
collapse to $p_1=0$ (the largest jobs are starved) under \emph{all four} placement
policies, whereas SAFA retains $p_1\!\approx\!50$--$59$ regardless of placement---a
$+50$ to $+60$ point advantage that is invariant in sign and magnitude across the
placement axis. Moreover, the relative $p_1$ ranking of all policies is identical
across the four placement columns in every configuration, confirming that SAFA's
fairness contribution is orthogonal to, and composes with, any underlying placement
scheduler. Placement affects absolute queueing delay only mildly (SAFA $q_{p50}$
varies $5$--$15\%$ across placements) without reordering the policies. The MCTS
placement, the most expensive, completes the full 111k-job trace in at most $87$\,s
(within $1.0$--$1.9\times$ of most-allocated), so no subsampling was needed.
```

**문장 스니펫(본문 삽입용)**:
> SAFA의 공정성 기여는 코어 배치 스케줄러와 직교한다. most-allocated·compact·round-robin·MCTS
> 네 배치 어디에서도 과부하·이종 환경에서 SJF/LAS가 $p_1=0$으로 붕괴하는 반면 SAFA는
> $p_1\approx50$--$59$를 유지하며, 정책 간 $p_1$ 순위가 네 배치에서 동일하다(배치 무관).

---

## 5. 신규 배치 추가 — KAI binpack/spread, bestfit_type (2026-06-19)

미테스트였던 placement를 동일 그리드(정책 행 × 배치 열)로 추가 검증. SAFA 적용(sfqa-auto·sfqa) vs 미적용(fifo·sjf·las) 분리.

**포팅**: KAI Scheduler(NVIDIA) nodeplacement — `binpack`(pack.go: free 적은 노드 consolidate, 순위=free 오름차순)·`spread`(spread.go: free 많은 노드 분산, 순위=free 내림차순). `sim/policies.py::pref_kai_binpack/pref_kai_spread`. KAI는 GPU 타입 speed-tier 안 함(순수 binpack/spread). `placement_axis.py`에 열로 추가.

### fair_p1 (sfqa-auto = SAFA 적용 / 미적용 비교)
| 배치 | 256단일 | 256이종 | 512단일 | 512이종 | 비고 |
|---|--:|--:|--:|--:|---|
| (참고) most-allocated | 54.3 | 54.4 | 53.1 | 50.5 | 기존 |
| **KAI binpack** | 54.3 | 54.5 | 53.1 | 50.5 | **≈ most-allocated** (consolidate=최소 free 선택으로 수렴) |
| **KAI spread** | 67.7 | 68.5 | 58.2 | 58.5 | 분산 → round-robin과 같은 소폭 상향 대역 |
| (참고) round-robin | 69.7 | 59.5 | 62.1 | 53.7 | 기존(분산) |

미적용 정책은 신규 배치에서도 동일: **fifo p1=100**(순서공정·느림), 과부하 이종에서 **sjf=0·las=0**(붕괴). SAFA만 50–68 유지.

### q_p50 (초) — KAI는 speed 무시로 이종에서 most-allocated 대비 차이
- kai_binpack 이종 q_p50(sfqa-auto): 512h 1.77M, 256h 3.46M — most-alloc(1.76M/3.77M)과 근사하나, fifo 기준 KAI 단독은 +5~10%(KAI가 빠른 타입 우선을 안 해 느린 타입 배치 증가).
- kai_spread는 분산이라 q_p50 소폭 증가(패킹 비효율).

### 결론 (정직)
- **SAFA 배치 불변이 7개 배치(코어 4 + FGD + KAI binpack/spread)로 확장 재확인** — SAFA p1 50–70, 미적용 그리디는 과부하 이종에서 0 붕괴. 정책 간 순위가 모든 배치에서 보존.
- **KAI binpack ≡ most-allocated**(whole-GPU 과포화에서 consolidate=최소 free), KAI spread ≈ round-robin. 배치 축은 이 레짐에서 여전히 무변별.
- **bestfit_type 제외**: 타입-인지 best-fit은 작업이 GPU 타입을 명시한다고 가정하나 본 트레이스는 type-agnostic(`any`)이라 후보 노드 집합이 비어 q_p50=0으로 퇴화 → 부적용.
- **범위 밖**: 외부 운영 스케줄러(Volcano·YuniKorn)·부분 GPU 공유 레짐은 whole-GPU 엔진 밖의 향후 과제. (mcts 256:hetero 재확인 run은 고부하 비용으로 미완료 → §3의 기존 커밋값 사용.)
