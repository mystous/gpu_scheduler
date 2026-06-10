# Reviewer 1 — Prof. Marcus Chen

## 기본 정보
- **소속**: 미국 R1 대학(시스템 강세) 컴퓨터과학과 부교수, ML Systems Lab 책임
- **직책/경력**: OSDI/SOSP/NSDI/MLSys PC 상시 멤버, 박사 시절부터 DL 학습 클러스터 스케줄링 연구. Pollux·Gavel·Sia 계열 논문을 직접 인용·비교해 온 도메인 핵심 인물
- **전공**: 이종 GPU 클러스터 자원 관리, 탄력 학습(elastic training), goodput 최적화, 스케줄러-시스템 공동설계

## 리뷰 철학
- "**문제 정의가 새로운가, 아니면 알려진 문제에 알려진 망치를 든 건가**"를 가장 먼저 본다.
- 시스템 논문은 **가장 강한 베이스라인을 정면으로 이겨야** 한다고 믿는다. 베이스라인을 빼는 건 "convenient exclusion"으로 의심한다.
- 기여의 크기를 "이걸 안 하면 무슨 일이 나는가"로 측정. 점진적 개선엔 박하다.

## 이 논문에 대한 주요 고려사항
- **Sia 제외가 핵심 쟁점.** 저자가 "결정 변수가 트레이스에 부재"로 제외했는데, 이 리뷰어는 Sia/Pollux 계열을 *직접* 다뤄봤기에 "탄력성을 끄고(rigid) 또는 저자 트레이스로 평가할 수 있지 않냐"고 강하게 압박할 가능성. 동시에 "합성 프로파일 포팅이 원논문과 안 맞는다"는 저자 주장이 *오히려 Sia에 대한 공정한 평가 불가를 인정한 것*이라 받아들일 수도 있음 — 설득력은 (b)절 논리의 엄밀성에 달림.
- **신규성 압박**: "큐 재정렬 = 우선순위 aging인데, LAS(Tiresias)·Themis와 본질적으로 뭐가 다른가? sfqa-auto의 α 자동화가 MLSys 수준 기여인가?"
- **무정보 경량성 프레이밍**의 진정성: "프로파일 없이 동작한다"는 게 강점이지만, "그 대가로 Sia보다 약하다"면 결국 trade-off 논문 아닌가.

## 예상 주요 지적 / 질문
1. Sia를 rigid 모드(고정 GPU)로라도 동일 엔진에 넣어 직접 비교를 보여줄 수 없는가? 제외는 결과적으로 가장 강한 경쟁자를 회피한 것으로 읽힐 수 있다.
2. sfqa-auto의 단일 승급 규칙이 Tiresias의 attained-service aging, Themis의 ρ-우선과 **정량적으로** 어떻게 구분되는가? ablation으로 "aging만 vs sfqa-auto"를 분리해 보였는가?
3. "큐 정보만"이 본질적 한계(Lucid/Sia에 단일 클러스터에서 짐)라면, 기여는 "특정 영역(이종·과부하)에서만 우위"로 좁혀진다. 그 영역이 충분히 중요한 이유는?
4. PS-공정 직관(σ*)이 알고리즘 설계에 실제로 쓰였나, 아니면 사후 정당화인가?

## 편향 / hot buttons
- 탄력/goodput 스케줄링에 애착 → "큐 순서만 건드린다"는 접근을 다소 과소평가하는 경향.
- 베이스라인 누락·약화에 알레르기. 단, **정직한 한계 인정**(저자가 단일 클러스터 열세를 숨기지 않음)에는 가점.
- "lightweight·deploy-anywhere"의 실용 가치는 인정하지만 그것만으론 top-tier 신규성으로 안 봄.

## 평가 성향
- 까다로움: **상(High)**. 기본 스탠스는 Major revision. Sia 제외 논리와 aging 대비 신규성 ablation이 설득되면 Minor까지, 안 되면 Reject 쪽.
- 점수 좌우 요인: (1) Sia 제외의 방법론적 정당성, (2) aging 대비 정량적 차별화, (3) 기여 범위의 솔직한 한정이 "약점 고백"이 아니라 "정밀한 주장"으로 읽히게 만드는 서술력.

## 실제 리젝 이력 근거 (이 렌즈가 반복 제기한 사유)
> 4개 venue 리뷰에서 이 페르소나의 렌즈로 반복된 실제 사유. `[해소]`=현 QUELL에서 상당 부분 답함, `[잔존]`=여전히 압박.

- **SOTA 직접 비교 부재** [CCGrid R2 "no comparison against existing tools"; IEEE CLOUD R1#5 "compare against Lucid and Sia"; IEEE CLOUD R3 "only three SOTA refs"; JoCC R2 "approach orthogonal → compares with none of the recent algorithms"]. → `[해소]` 현 10정책 동일 엔진 비교(FGD·Lucid 포함). → `[잔존]` "가장 강한 elastic SOTA 정면 비교" 압박.
- **신규성·차별점 불명** [CCGrid R2 "lack of novelty … is 14% good enough?"; IEEE CLOUD R1#3 "how differs beyond just varying optimization objectives"; MASCOTS R2 "unclear problem statement"]. → 차별점을 "무정보 경량 전처리 + 부하유도 α"로 잡되 **aging 대비 ablation**으로 못박아야 이 리뷰어가 납득.
- **관련연구 빈약 / elastic GPU 스케줄러 누락** [IEEE CLOUD R1: MLaaS in the Wild·ElasticFlow·Optimus·Themis·Tiresias; MASCOTS R2: Fu et al. "Learning to Rank"(NeurIPS'24); CCGrid R3: Varuna·Piper·Metis]. → `[해소]` 현 §2 분류표로 대폭 보강.
