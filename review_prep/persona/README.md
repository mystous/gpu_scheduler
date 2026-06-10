# 리뷰어 페르소나 (QUELL 논문 가상 심사단)

이 디렉토리는 본 논문(QUELL — 큐 관측 정보만으로 HOL 블로킹 기아를 해소하는 경량 큐 전처리, Philly 트레이스 이산 사건 시뮬 평가, IEEE 저널 타깃)을 심사할 **5인 가상 리뷰어**의 페르소나다. 제출 전 셀프 리뷰·반박 준비(rebuttal prep)·취약점 사전 보강에 사용한다.

## 심사단 구성 (서로 다른 렌즈로 약점 커버)

| # | 파일 | 렌즈 | 한 줄 성향 |
|---|---|---|---|
| 1 | [reviewer-1-mlsys.md](reviewer-1-mlsys.md) | ML/GPU 클러스터 스케줄링 (도메인 정면) | "Sia를 왜 뺐나, 큐 재정렬이 top-tier 기여인가" — 가장 깐깐 |
| 2 | [reviewer-2-queueing-theory.md](reviewer-2-queueing-theory.md) | 큐잉 이론·성능 모델링 | "σ*=1/(1−ρ) 연결이 directional analogy면 그건 증명이 아니다" |
| 3 | [reviewer-3-production-k8s.md](reviewer-3-production-k8s.md) | 프로덕션·쿠버네티스 실무 | "시뮬만으론 못 믿는다, 실제로 돌려봤나, 부하 1.8–3.6×가 현실적인가" |
| 4 | [reviewer-4-evaluation-methodology.md](reviewer-4-evaluation-methodology.md) | 평가 방법론·재현성 | "합성 모델·단일 트레이스로 일반화되나, 아티팩트 있나" |
| 5 | [reviewer-5-hpc-scheduling.md](reviewer-5-hpc-scheduling.md) | HPC 고전 스케줄링·백필 | "aging은 1990년대부터 있었다, EASY와 뭐가 다른가" |

## 평가 척도 (공통)
각 페르소나는 다음 축으로 판정한다 — **Novelty / Technical soundness / Evaluation rigor / Clarity / Reproducibility / Significance**. 최종 권고는 IEEE 척도(Accept / Minor revision / Major revision / Reject)로 기재.

## 사용법
1. 각 페르소나 입장에서 논문을 읽고 그들이 던질 "예상 질문"에 답할 수 있는지 점검.
2. 답이 막히는 질문 = 제출 전 보강 지점.
3. 5인의 공통 우려(특히 **Sia 제외**, **시뮬-only**, **aging 신규성**)는 본문/threats에서 선제 방어가 되어 있는지 확인.
