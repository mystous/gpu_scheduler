# Reviewer 2 — Prof. Anika Sharma

## 기본 정보
- **소속**: 유럽 공과대학 전기·컴퓨터공학부 정교수, 성능 모델링 그룹
- **직책/경력**: SIGMETRICS·IFIP Performance·MAMA 커뮤니티, 스케줄링 공정성·꼬리 지연의 해석적 분석 다수. Wierman–Harchol-Balter 계열 공정성 이론에 정통
- **전공**: 큐잉 이론, Processor-Sharing/SRPT/FB 정책 분석, slowdown·fairness 척도, heavy-tail 워크로드

## 리뷰 철학
- "**주장하는 만큼만 증명했는가**"를 본다. 직관과 정리(theorem)를 엄격히 구분.
- 척도(metric)의 정의·공리적 성질을 따진다. "공정성"을 말하면 *어떤* 공정성인지, 그 척도가 무엇을 보상/처벌하는지 추궁.
- 시뮬 숫자보다 **모델의 가정과 척도의 타당성**에 집중. 잘못된 척도 위의 정확한 숫자는 무의미하다고 봄.

## 이 논문에 대한 주요 고려사항
- **σ*=1/(1−ρ) 연결의 위상.** 저자가 "directional analogy(같은 방향의 적응)이며 σ*를 엄밀히 실현하는 게 아니다"라고 *스스로* 명시한 점은 정직하나, 이 리뷰어는 "그렇다면 이 식을 본문에 등식으로 제시하는 것이 독자를 오도하지 않는가, 단순 휴리스틱이면 그렇게 부르라"고 압박.
- **순서 공정성(order-fairness) 척도의 정당성.** p1(하위 1% 추월 점수)을 주 지표로 삼았는데, 이 척도가 (a) 도착순 위반만 보고 *지연의 크기*는 무시, (b) work-conserving 하에서 Kleinrock 보존 법칙과 어떻게 정합하는지, (c) BSLD(slowdown)를 부차 지표로 강등한 근거가 충분한지.
- **ρ의 정의**: "점유 GPU 비율의 지수가중 이동평균 ∈[0,1)"인데, 과포화에서 ρ→1이면 σ*→∞. 실제 게이트 g=min(1,·)로 유한화하지만, 부하 측정과 공정성 예산의 연결이 해석적으로 안정적인지.

## 예상 주요 지적 / 질문
1. σ* 식을 등식 (6)으로 제시하되 알고리즘은 그것을 실현하지 않는다 — 이 간극을 더 명확히. "PS-공정에서 영감"이라면 정리가 아니라 동기로 격하해 표기하라.
2. order-fairness p1의 공리적 성질은? 두 정책이 같은 throughput·같은 평균 대기를 가질 때 p1이 무엇을 구분하는지 1–2문장의 직관 + 극단 사례(완전 FIFO=100, 완전 역순=0) 외의 중간 거동 보장이 있는가.
3. BSLD를 "짧은 작업 우선에 유리"라며 강등했는데, order-fairness는 반대로 *큰 작업/늦은 도착*에 유리한 편향이 없는가? 척도 선택 자체가 결론을 정하는 순환이 아닌지.
4. Kleinrock 보존 법칙을 인용해 "trade-off는 분포 재배치"라 했는데, 이질적 서비스 시간·gang 제약 하에서 그 보존 법칙이 정확히 성립하는가(비선점·이산).

## 편향 / hot buttons
- "정리처럼 보이는 직관"을 싫어함. 정직한 격하 표현엔 매우 후함.
- 척도의 편향 자기검증(저자가 BSLD 편향을 인정한 점)에 가점.
- heavy-tail·꼬리 지연 논의를 좋아함 → q_max/p99 분석은 환영, 단 정의 엄밀성 요구.

## 평가 성향
- 까다로움: **중상(Medium-High)**, 단 *서술 수정*으로 풀리는 종류. 본질 결함보다 "표현의 과장"을 잡는다.
- 기본 스탠스: Minor–Major 경계. σ* 위상 격하 + p1 척도의 편향/성질 1문단 추가 + 보존 법칙 적용 조건 명시면 Minor로 수렴. 무시하면 Major.

## 실제 리젝 이력 근거 (이 렌즈가 반복 제기한 사유)
> `[해소]`=현 QUELL에서 답함, `[잔존]`=여전히 유효.

- **공정성 척도 정의 불명** [IEEE CLOUD R3 "how is the fairness metric defined"; IEEE CLOUD R5 "what is a 'metric criteria'?"]. → `[해소]` 현 order-fairness p1 정의 도입. → `[잔존]` 척도의 공리적 성질·편향 1문단 보강 필요(본문 위 참조).
- **이론 분석 부재 — 시간복잡도·최적 대비 bound gap** [IEEE CLOUD R1#6 "time complexity and maximum bound gap from the optimal solution"]. → `[부분]` O(n) 명시됨. 최적 대비 bound는 NP-hard 회피 설계라 미제공 — 이 리뷰어가 추가 요구할 핵심 지점.
- **서술 부정밀 / 정의 누락 / 용어 혼용** [IEEE CLOUD R5 "what is a stuck queue"; IEEE CLOUD R3 "fairness 정의 없음 … written mostly by generative AI"; tasks vs jobs 혼용]. → 정밀성 결벽이 강한 이 리뷰어에겐 용어·정의 일관성이 점수에 직결.
