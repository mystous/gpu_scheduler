# SAFA 논문 한↔영 용어집 (Translation Glossary)

영어 버전(`sn-article-en.tex`) 작성·수정 시 이 표를 기준으로 용어를 통일한다.
표기 원칙:
- 고유명사·시스템명(SAFA, FIFO, Kueue, KAI, FGD, Philly, Helios, Alibaba PAI, B200 등)은 그대로 쓴다.
- Order/Placement는 두 스케줄링 단계를 가리키는 용어로 대문자 그대로 유지한다.
- 지표명(Fairness, Overtaken, MedianWait, MaxWait, Utilization, Gini, TailRatio)은 표·본문에서 영문 그대로 쓴다.

## 핵심 개념

| 한국어 | English | 비고 |
|---|---|---|
| 배치-전 재정렬 계층 | pre-placement reordering layer | SAFA의 정체성 표현 |
| 큐 조정 | queue adjustment | 알고리즘 이름과 일치 |
| 재정렬 | reordering | |
| 재정렬 베이스라인 | reordering baselines | SJF·LAS 등 빠른 정책 총칭 |
| 순서 공정성 | order fairness | |
| 하위 1% 순서 공정성 | bottom-1% order fairness | |
| 도착 순서 | arrival order | |
| 도착순 | arrival-order (FIFO) | 우선순위 첫 항 서술 |
| 추월 | overtaking / overtaken | 지표는 Overtaken |
| 기아 | starvation | |
| 굶기다 | starve | |
| HOL 블로킹 | HOL blocking (Head-of-Line blocking) | 첫 등장 시 풀어쓰기 |
| 선두 (작업) | (queue) head / head job | |
| 후속 작업 | subsequent jobs | |
| 큐잉 지연 | queueing delay | |
| 중앙값 큐 대기 | median queue wait | |
| 최악 큐 대기 | worst(-case) queue wait | |
| 자원 활용도 | resource utilization | |
| 할당률 | allocation rate | Utilization 정의: average GPU allocation rate |
| 단편화 | fragmentation | |
| 갱 (스케줄링) | gang (scheduling) | rigid job 의미, §4 서두에서 정의 |
| 불가분 | indivisible (all-or-nothing) | |
| 비선점 | non-preemptive / non-preemption | |
| 나이 | age | |
| 상대 나이 | relative age | $\tilde A_j$ |
| 나이 승급 | age promotion | |
| 승급 압력 | promotion pressure | |
| 자원 적합도 (지수) | resource fitness (index) | $R_j$ |
| 빈자리 | vacant slot | |
| 빈자리 적합도 | fitness to vacant slots | |
| 연속 자리/슬롯 | contiguous slot | |
| 무튜닝 | tuning-free | Zero-knob은 고유명 유지 |
| 튜닝 노브 | tuning knob | |
| 재튜닝 | re-tuning | |
| 계수 | coefficient | $\alpha$, $\alpha_{\text{eff}}$ |
| 기아 지수 | starvation index | $\alpha\tilde A_j R_j$ |
| 전처리(기) | preprocessing / preprocessor | |
| 결합성 | composability | |
| 결합하다 | compose (with) | |
| 보완재 | complement | |
| 흩뿌리는 배치 | scattering placement | round-robin·KAI spread 계열 |
| 집약하다 | consolidate | KAI binpack |
| 회복 | recovery / recover | HOL 낭비 자원 회복 |
| 부하--공정성 절벽 | load–fairness cliff | 그림 fig:cliff |
| 분포 공정성 | distributional fairness | Gini·TailRatio |
| 트레이드오프 | trade-off | 하이픈 포함 |
| 과부하 | overload(ed) | |
| 과포화 | oversaturation / oversaturated | |
| 경합 | contention | |
| 부하 | load | |

## 정보·비교 프레임

| 한국어 | English | 비고 |
|---|---|---|
| 큐에서 직접 관측되는 정보/신호 | information/signals directly observable in the queue | |
| 부차 정보 | auxiliary information | |
| 사전 정보 | prior information | |
| 무정보 | information-free | LAS 규율 서술 |
| 실행시간 추정 | runtime estimation / runtime estimates | duration estimate 혼용 금지 |
| 성능 프로파일 | performance profile | |
| 순위 예측 | rank prediction | |
| 솔버 | solver | |
| 경매 (입찰) | auction (bids) | |
| 결정 변수 | decision variable | |
| 계층 불일치 | layer mismatch | |
| 동일 층위 | same layer | |
| 무개입 베이스라인 | non-intervening baseline | FIFO |
| 통제군 | control (group) | |
| 대조 실행 | control run | B200 실측 |
| 게이트 계층 | gating layer | Kueue |
| 누적 서비스 | attained service | LAS = least attained service |
| 완료시간 공정성 | finish-time fairness | Themis $r$ |
| 퇴화하다 | degenerate (to) | FIFO/FCFS로 퇴화 |
| 다단계 피드백 큐 | multi-level feedback queue | |
| 쿼타 | quota | |
| 탄력 (스케줄러) | elastic (scheduler) | |
| 고정 요청 갱 트레이스 | fixed-request gang trace | |

## 평가·실험

| 한국어 | English | 비고 |
|---|---|---|
| 이산 사건 시뮬레이터 | discrete-event simulator | |
| 실측 | real-cluster measurement | B200 |
| 실 클러스터 실측 검증 | real-cluster validation | §eval:b200 제목 |
| 교차 검증 | cross-validation / cross-validate | |
| 어드미션·바인딩 경로 | admission-and-binding path | |
| 버스트 | burst / bursty | |
| 백로그 | backlog | |
| 표본 | sample | |
| 모집단 | population | |
| 서브샘플 | subsample | |
| 부하 배수 | load multiplier | |
| 재생하다 | replay | 트레이스 재생 |
| 격리 확인 | isolation check | |
| 반복 편차 | deviation across repetitions | |
| 작업당 라이프사이클 오버헤드 | per-job lifecycle overhead | 표 tab:overhead |
| 기동 (단독/혼잡) | startup (solo/congested) | |
| 종료 | teardown | |
| 손계산 가능한 | hand-computable | toy 사례 |
| 오버헤드 회계 | overhead accounting | |
| 충실도 | fidelity | |
| 그리드 탐색 | grid search | |
| 목적함수 | objective function | |
| 누적 거리 | accumulated distance (AD) | |
| 누적 최대 거리 | accumulated maximum distance (AMD) | |
| min--max 정규화 | min–max normalization | |
| 분포별 최적 α | optimal α by distribution | 표 fig:motivation |
| 주 결과 | main results | |
| 주 지표 | primary metric | |
| 지표 편향 | metric bias | |
| 독립 분배 지표 | independent distributional metrics | |
| 자릿수 차이 | order-of-magnitude difference | |
| 경향 | trend | 절대값 아닌 경향 |

## 이론·알고리즘

| 한국어 | English | 비고 |
|---|---|---|
| 비예지 | non-clairvoyant | |
| 경쟁비 하한 | competitive-ratio lower bound | |
| 공간 공유 병렬 작업 스케줄링 | space-shared parallel job scheduling | JSSPP |
| 오랜 기본 가정 | long-standing basic assumption | |
| 바닥/덮개 (클램프) | floor / cap (clamps) | eq:auto-alpha 해설 |
| 폭주하다 | blow up | $\alpha_{\text{eff}}$ |
| 재기준(하다) | re-base | 상대 나이 |
| 큐 spread | queue('s age) spread | |
| 큐 평균 대비 나이 | age relative to queue mean | eq:alphaeff underbrace |
| 최악 적합 대비 적합도 | fitness relative to worst fit | eq:alphaeff underbrace |
| 우선순위 역전 | priority inversion / invert priorities | |
| 유휴 수 | idle count | $f_{S_i}$ |
| 가속기 요청 | accelerator request | $a_{t_i}$ |

## 일반 표현

| 한국어 | English | 비고 |
|---|---|---|
| 작업 | job | task 금지 |
| 대기 큐 | wait queue | 알고리즘 표기와 일치 |
| 대기 작업 | pending job | |
| 대기 시간 | waiting time | 지표 서술 시 wait |
| 자원 요구량 | resource demand | |
| 서버 풀 | server pool | |
| 미할당 GPU | unallocated GPUs | |
| 클러스터 용량 | cluster capacity | |
| 배치하다 (자리에) | place | placement와 구별 시 소문자 |
| 워크로드 | workload | |
| 완료 시간 | completion time (JCT) | |
| 본 연구/논문 | this work / this paper | |
| 향후 과제 | future work | |
