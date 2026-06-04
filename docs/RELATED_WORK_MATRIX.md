# 관련 연구 기능 비교 매트릭스 (리젝 ③ 대응)

> 용도: related work 절 + 비교표(논문 Table). 리뷰어 요구 인용 전부 포함:
> Tiresias/Themis/Optimus/Lucid/Sia(IEEE Cloud R1), Varuna/Piper/Metis/CFS(CCGrid R3),
> Learning-to-Rank(MASCOTS R2), Singularity/PipeSwitch(IEEE Cloud R5), Kueue(계획 확정).

## 1. 클러스터 잡 스케줄러 (직접 비교 대상)

| 시스템 | 발표 | 선점/이주 필요 | duration·프로파일 요구 | 앱 수정 | 최적화 목표 | 기존 스케줄러 대체 | SQUAD 대비 |
|---|---|---|---|---|---|---|---|
| Tiresias | NSDI '19 | ○ (suspend-resume) | ✕ (attained service만) | △ (체크포인트 협조) | 평균 JCT | ○ (전용 매니저) | LAS 베이스라인으로 실측 비교(선점 도입 후 유의미) |
| Themis | NSDI '20 | ○ (lease 회수) | ○ (finish-time 추정) | ○ (auction agent 통합) | finish-time fairness | ○ | slowdown 계열 공정성의 GPU 선례 — v2 σ* 논리와 연결 |
| Optimus | EuroSys '18 | ○ (worker 증감) | ○ (성능 모델 학습) | ○ (elastic PS 구조) | 평균 JCT | ○ | 모델 기반 vs 우리=정보 최소 |
| Gandiva | OSDI '18 | ○ (time-slice·migration) | △ (introspection) | ○ (프레임워크 수정) | util·JCT | ○ | 이주 메커니즘 선례(PTR 비교) |
| Pollux | OSDI '21 | ○ (재할당) | ○ (goodput 모델) | ○ (elastic) | goodput | ○ | adaptive 계수 선례(단 앱 침습) |
| Lucid | ASPLOS '23 | ✕ | ○ (프로파일링 잡) | △ | JCT (해석가능) | ○ | 비침습 지향 동일, 단 프로파일링 요구 |
| Sia | SOSP '23 | ○ | ○ (throughput 프로파일) | ○ (adaptive 병렬화) | 이종 goodput | ○ | 이종 인지 — 우리 flavor-aware와 비교 축 |
| Kueue | K8s SIG | △ (cohort 선점) | ✕ | ✕ | quota 공정성 | ✕ (suspend 기반) | **같은 레이어(비침습 게이트)** → 실측 베이스라인 1순위 |
| Volcano | CNCF | △ | ✕ | ✕ (CRD) | gang/큐 | ○ (스케줄러 교체) | K8s gang 스케줄링 표준 — 논의 비교 |
| **SQUAD (SFQA+PTR)** | — | △ (PTR만, SFQA는 ✕) | ✕ (v1) / △ 추정 허용 (v2, τ-floor로 오차 견고) | ✕ | **max 대기(starvation) 유계 + 평균** | **✕ (전처리: gate·annotation)** | — |

**포지셔닝 문장**: 기존 연구는 (i) 코어 스케줄러를 통째로 대체하고 (ii) duration/throughput
프로파일과 (iii) 앱 협조(elastic·agent)를 요구한다. SQUAD는 큐 전처리(SFQA)와 자원 전처리(PTR)로
**기본 스케줄러를 유지한 채** 동작하며, 정보 요구가 가장 적은 칸을 차지한다. v2(sfqa-auto)는
duration 추정을 *선택적으로* 활용하되 τ-floor로 추정 오차에 견고.

## 2. 다른 레이어 (related work에서 구분 서술 — "비교 불가"가 아니라 "직교"임을 명시)

| 시스템 | 레이어 | SQUAD와의 관계 |
|---|---|---|
| Linux CFS | 단일 노드 CPU 시분할 | CCGrid R3 요청 비교: CFS는 시분할(나눌 수 있는 자원), GPU 잡은 공간 점유 gang(나눌 수 없음) — vruntime 공정성이 적용 불가한 이유를 한 단락으로. 단 "최소 서비스 보장" 철학은 SFQA의 starvation-freedom과 동일 계보 |
| Varuna (EuroSys '21) | 탄력 학습 프레임워크 | 스케줄러가 아니라 스케줄러의 *대상*. PTR 이주 대상 워크로드로 포섭 가능 |
| Piper | 병렬화 플래너 | 잡 내부 분할 결정 — 클러스터 큐잉과 직교 |
| Metis (ATC '24) | 이종 GPU 병렬화 플래너 | 잡 내부 이종 분할 — 우리는 잡 간 이종 배치 |
| Fu et al. L2R (NeurIPS '24) | vLLM 요청 레벨 | 요청 길이 예측→SJF. 레이어는 다르나 "추정 기반 SJF + starvation 방지" 구조가 sfqa-auto tier-2와 동형 — 인용 필수(MASCOTS R2 명시 요구) |
| PipeSwitch (OSDI '20) | 노드 내 컨텍스트 스위칭 | GPU 선점 비용의 근거 문헌 — PTR 다운타임 실측의 비교 기준 |
| Singularity (arXiv '22) | 투명 checkpoint·이주 | PTR 이주 백엔드의 실현 가능성 근거(cuda-checkpoint 계열) |
| MLaaS in the Wild (NSDI '22) | 트레이스 분석 | Alibaba GPU 트레이스 출처 논문 — 데이터 절에서 인용 |

## 3. 표가 만드는 논증 (논문 서술용)

1. **빈 칸이 우리 자리**: "스케줄러 비대체 + 앱 비수정 + 정보 최소 + starvation 유계 보장" 조합은 표에서 SQUAD/Kueue 행뿐이고, Kueue는 quota 공정성일 뿐 starvation 유계·디프래그가 없다.
2. **베이스라인 선정 근거**: 같은 레이어(Kueue)·같은 정보 조건(Tiresias-LAS)·정보 우위(SJF/EASY-backfill)를 골랐다 — "비교가 없다"(CCGrid R2) 정면 대응.
3. **이종 축**: Sia/Metis는 잡 내부 이종 병렬화, 우리는 잡 간 이종 배치(flavor-aware) — ⑥ 확장의 차별점.
