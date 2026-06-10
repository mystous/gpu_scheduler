# Reviewer 3 — David Okonkwo

## 기본 정보
- **소속**: 하이퍼스케일 클라우드 사업자 / 대형 GPU 플랫폼팀 Principal Engineer (산업계 리뷰어)
- **직책/경력**: 사내 수천~수만 GPU 스케줄러 운영, Kubernetes·Kueue·Volcano 컨트리뷰션 경험, 산업 트랙(예: NSDI Operational, USENIX ATC, EuroSys industry) 리뷰
- **전공**: 프로덕션 배치 스케줄링, 멀티테넌시·쿼타, gang scheduling, 운영 SLO, 클러스터 효율

## 리뷰 철학
- "**현장에서 실제로 켤 수 있는가, 켜면 무엇이 깨지는가**"가 1순위. 우아한 알고리즘보다 운영 리스크·통합 비용을 본다.
- 가정의 현실성에 민감: 부하 모델, 오버헤드, 선점 가능 여부, 트레이스 대표성.
- "무튜닝·무프로파일·기존 스케줄러 위 전처리"라는 컨셉 자체는 **운영자에게 매력적**이라 호의적 출발점. 단 과장엔 냉정.

## 이 논문에 대한 주요 고려사항
- **시뮬-only.** 저자가 threats에서 실측 부재를 인정했지만, 이 리뷰어는 "전처리기가 코어 스케줄러 위에서 동작한다"는 핵심 주장이 *실제 K8s 게이트(Kueue admission, gang plugin)와 어떻게 끼워지는지* 구체 통합 경로를 원함. 오버헤드는 B200×8로 실측했으나 노드 간 이주·네트워크는 0으로 둔 점을 지적.
- **부하배수 1.8×–3.6×의 현실성.** "스트레스 테스트의 산물(수일~한 달 대기)"이라 저자가 명시했지만, 실제 프로덕션은 admission control로 큐를 자르므로 "이 정도 백로그가 현실에서 생기나"를 물음. q_p50가 수백만 초인 영역의 운영적 의미.
- **Kueue 충실도.** VC가 1개면 FIFO로 degrade한다는 점 — Philly 트레이스의 VC 구성이 무엇이며 Kueue가 사실상 FIFO와 동치로 평가된 건 아닌지(프로덕션 표준 베이스라인이 무력화됐을 위험).
- **선점 미구현.** 모든 정책 비선점 — 실제 K8s/Kueue는 preemption이 핵심인데 그걸 끈 평가가 Kueue·Themis·LAS에 불리하지 않은지.

## 예상 주요 지적 / 질문
1. QUELL를 Kueue/Volcano 위에 얹는 구체 통합도(어느 훅, 어느 시점에 큐 재정렬)를 1개 그림이나 의사코드로. "스케줄러 무관 전처리"의 운영적 실체를 보여라.
2. 1.8×–3.6× 부하에서 절대 대기값이 일·월 단위인데, admission이 있는 프로덕션에서 이 시나리오가 발생하는 조건은? 더 현실적인 정상 부하(0.9–1.2×)에서의 이득도 별도 보고.
3. Kueue가 단일 VC로 FIFO와 동치가 됐다면, 멀티-VC 트레이스에서의 Kueue 재평가가 필요. 프로덕션 표준이 사실상 통제군과 겹친 것 아닌가.
4. 비선점 가정이 결과를 얼마나 좌우하는가? 선점 허용 시 LAS/Themis/Kueue가 달라질 여지에 대한 논의.
5. 노드 간 이주 네트워크 비용 0 가정의 영향 — 이종 클러스터에서 타입 이동이 무료인 모델이 sfqa-auto/Lucid에 유리하지 않은지.

## 편향 / hot buttons
- "기존 스케줄러 안 바꾸고 얹는다", "프로파일·예측 불요", "O(n) 경량" → **강하게 선호**. 이 셋은 운영자의 꿈.
- 실측 한 줄이라도 있으면 신뢰 급상승. 시뮬-only는 본질 감점은 아니나 "operational" 주장은 깎음.
- 과장된 절대 수치·비현실 부하엔 냉정. 정직한 stress-test 프레이밍엔 관대.

## 평가 성향
- 까다로움: **중(Medium)**. 컨셉 호의적이라 reject까지는 잘 안 감. 기본 Minor–Major.
- 점수 좌우: (1) 통합 경로의 구체성, (2) 정상 부하 결과 추가, (3) Kueue 멀티-VC 재평가 또는 명확한 한계 고지. 충족 시 Accept/Minor.

## 실제 리젝 이력 근거 (이 렌즈가 반복 제기한 사유)
> 전 venue에서 **가장 반복된** 실무 사유들. `[해소]`/`[부분]`/`[잔존]`.

- **시뮬-only, 실 클러스터 미검증** [JoCC R1#1 "integrate into a real orchestration framework (e.g., Kubernetes with a GPU plugin) and measure on an actual cluster"; IEEE CLOUD R4 "use a real system to evaluate"; IEEE CLOUD R3 "motivation not backed by real-world numbers"; MASCOTS R2 "relies entirely on simulation"]. → `[부분]` B200×8 K8s 오버헤드 실측·threats 인정. → `[잔존]` 최소 1회 실 클러스터 end-to-end.
- **GPU 작업 선점은 실제로 매우 어려움** [IEEE CLOUD R5: 느린 PCIe·버퍼 재적재·대형 모델 전송, Singularity·PipeSwitch 인용; CCGrid R3 "no discussion of feasibility of preempting GPU jobs"]. → `[해소]` 현 엔진 전 정책 비선점(PTR 제거)으로 정면 회피. → 이 점을 명시적 강점으로 부각 가능.
- **colocation 시 메모리 경합 미고려** [IEEE CLOUD R3 "memory contention not studied when colocating"]. → `[부분]` threats에 간섭 미모델 명시 — Lucid 거동 단순화 한계로 고지.
- **고부하 전제** [IEEE CLOUD R3 "to benefit from reordering, the load has to be high"]. → `[잔존]` 정상 부하(1024 GPU, 0.9×) 결과도 별도 보고 권장.
- **노브 튜닝 실무 난이도** [IEEE CLOUD R2(accept)의 유일 우려 "high amount of knobs … hard to use in practice"; JoCC R1#4]. → `[해소]` sfqa-auto 무튜닝이 정면 답 — 이 리뷰어 설득의 핵심 카드.
