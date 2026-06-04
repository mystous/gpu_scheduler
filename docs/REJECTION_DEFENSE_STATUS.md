# 리젝 사유별 방어 현황 (PTR ② 제외)

> 갱신: 2026-06-04. 근거 리뷰: `reject/{2025_ccgrid,2025_IEEE_CLOUD,2025_MASCOTS,journal_of_cloud_conputing}.txt`
> 실측 증거: `/raid/squad/analysis/SUMMARY.md` (Philly 1000 층화, 5정책, kind+B200×8)

## 판정 요약

| 축 | 리젝 사유 | 판정 | 비고 |
|---|---|---|---|
| ④ | 저자 생성(합성) 데이터 | ✅ 방어 | Philly·Alibaba 실트레이스 + 사내 로그. κ 압축 정당화 절만 논문에 필요 |
| ① | 시뮬레이션만 | 🟡 부분 | 실 kube-scheduler 실측 확보. holder 스텁(GPU 연산 無)이 잔여 구멍 |
| ③ | 베이스라인 빈약 | 🟡 부분 | 5정책+통제군 확보. SOTA(Kueue/EASY-backfill) 및 related work 부재 |
| ⑤ | 노브 과다 | 🟡 부분 | zero-knob v2 설계 완료(`ADAPTIVE_SFQA_DESIGN.md`). 실증 0 |
| ⑥ | 규모 <8 GPU | ❌ | H100×3 인입 시 멀티노드(+B200 조인 시 이종)로 개선 예정 |
| ⑦ | 글쓰기 | ❌ | 논문 재작성에서 일괄 처리 예정 |

## 이미 닫힌 개별 지적 (재투고 시 명시 활용)

- **IEEE Cloud R5 "실제 스케줄러는 strict FIFO 아님(backfill)"** → 실제 kube-scheduler(backfill 동작)에서도 max 2450s starvation 실측 — 반박이 아니라 motivation 강화 재료.
- **IEEE Cloud R3 "load가 높아야 의미"** → peak 3.6× capacity 부하 실측.
- **JoCC R1 "K8s+GPU plugin 통합 또는 검증된 시뮬레이터"** → 전자를 그대로 수행.
- **JoCC R1 "online adaptation heuristic baseline"** → sfqa-auto v2가 정확히 대응(실증 대기).
- **IEEE Cloud R1-6 "이론적 분석 부재"** → v2 Lemma(BSLD ≤ σ*/R_min + O(1) 유계)가 재료 제공.
- **JoCC R2 "GPU 수 외 특성 미고려"** → v2가 service time 사용 + SJF/LAS 비교 추가.

## 남은 작업 → 보강 계획

| 축 | 작업 | 의존성 |
|---|---|---|
| ① | 실모델 캠페인(S-스케일링) — **학습 잡은 로컬 캐시 이미지로 지금 가능**(`LOCAL_IMAGE_INVENTORY` 참고), 콜로케이션 간섭 측정, per-pod util 수집(DCGM-exporter 이미지 노드에 캐시됨), 반복 실행 | 실험 승인 |
| ③ | Kueue 베이스라인(registry.k8s.io 열림), EASY-backfill 정책 추가, 시뮬 내 SOTA 단순화 재현, 기능 비교표(`RELATED_WORK_MATRIX.md` ✅) | 실험 승인(표 제외) |
| ⑤ | sfqa-auto 실증(H1–H4), κ 불변성, 계수 전이성, 잔여 상수 민감도 스윕(`KNOB_COST_AND_SENSITIVITY.md` ✅ 설계) | 실험 승인 |
| ⑥ | H100×3 멀티노드 + B200 조인(이종), 시뮬↔실측 cross-validation | H100 도착 |
| ⑦ | 용어 통일, Alg.1/2 재서술, GPU vs CPU 단편화 문제정의, NP-hard 인용, MIG/vGPU 논의, 그림 가독성 | 논문 작성 |
