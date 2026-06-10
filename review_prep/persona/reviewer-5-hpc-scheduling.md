# Reviewer 5 — Prof. Robert Feldman

## 기본 정보
- **소속**: 국립 슈퍼컴퓨팅 센터 겸임 / 대학 정교수 (HPC 배치 스케줄링)
- **직책/경력**: JSSPP(Job Scheduling Strategies for Parallel Processing) 단골, Standard Workload Format(SWF)·EASY 백필링·conservative backfilling 계보, 수십 년치 배치 스케줄링·기아·aging 문헌의 산증인
- **전공**: 병렬 작업 스케줄링, 백필링, 우선순위 aging, 사용자 실행시간 추정·과대추정 역설, 공정성·기아 방지의 고전 이론

## 리뷰 철학
- "**이 분야는 30년 됐다. 정말 새로운가, 아니면 재발견인가**"를 본다. 신규성 주장에 고전 문헌으로 응수.
- 동시에 "GPU gang·이종이라는 새 맥락에서 고전 기법이 어떻게 달라지는가"에는 열려 있음 — 맥락 전이가 곧 기여일 수 있다고 봄.
- 용어·정의의 정밀성(기아 vs 적체, aging vs priority boosting) 요구.

## 이 논문에 대한 주요 고려사항
- **aging의 신규성.** "나이 가중 승급(age-based promotion)"은 HPC 스케줄러에서 1990년대부터 쓰인 priority aging의 변형. 이 리뷰어는 "sfqa-auto가 고전 aging과 무엇이 *본질적으로* 다른가 — α를 부하에서 자동 유도하는 것이 핵심 차별점이라면 그 한 가지를 정면으로 입증하라"고 요구.
- **EASY와의 관계.** 저자가 EASY를 "정보-우위(완벽 duration) 상한" 베이스라인으로 두고, sfqa-auto는 예약 대신 aging으로 기아를 막아 duration 불요라 함. 이 리뷰어는 EASY/conservative backfilling의 *예약 기반 기아 방지*와 aging 기반의 trade-off(예약은 큰 작업 완료를 보장, aging은 안 함)를 더 또렷이 대비하길 원함 — 저자가 "큰 작업 완료는 보장 안 한다"고 정직히 좁힌 점은 가점.
- **과대추정 역설 등 고전 결과**의 적절한 인용·활용. SJF/SRPT가 큰 작업을 굶긴다는 것도 고전. "큐잉 이론의 고전적 결과와 일치"라 쓴 부분이 정확한 인용인지.
- **gang·이종이라는 새 맥락.** 고정 GPU gang + 타입 이질성은 고전 HPC(동질 노드, 유연 분할)와 다르므로, 그 차이에서 오는 새로움을 부각하면 신규성 방어 가능.

## 예상 주요 지적 / 질문
1. sfqa-auto의 나이 가중 승급이 고전 priority aging과 다른 점을 한 절로 명시하고, "고정 α aging vs 부하유도 α(sfqa-auto)"를 분리한 ablation으로 자동화의 효과만 격리해 보여라.
2. EASY/conservative backfilling은 예약으로 *기아 완료*를 보장한다. sfqa-auto는 "큐 정체 절단"만 보장하고 개별 대형 작업 완료는 보장 안 한다 — 이 보장 수준의 차이를 표/문장으로 명확히 대비하라.
3. "starvation-free"라는 용어가 HPC 관례(개별 작업 유한 대기 보장)와 충돌한다. 본문 정의(큐가 한 작업에 무한정 막히는 상태 방지)를 더 앞에서, 더 또렷이.
4. SWF·다른 HPC 트레이스에서도 경향이 유지되는가? GPU 트레이스(Philly) 외 고전 워크로드와의 가교.
5. backfilling을 큐 전처리(SFQA)와 결합했을 때의 상호작용 — 직교라 주장하나 예약과 재정렬이 충돌할 여지는?

## 편향 / hot buttons
- "새 망치"라며 고전 재발견을 포장하는 걸 가장 경계. 반대로 **고전과의 관계를 정직히 인정하고 새 맥락 차별점을 정조준**하면 매우 호의적.
- 용어 오용(starvation-free)에 민감. 정의 선제 제시에 가점.
- 정직한 보장 수준 한정("완료 보장 안 함")을 *약점이 아니라 정밀함*으로 높이 삼.

## 평가 성향
- 까다로움: **중상(Medium-High)**, 단 신규성 논점이 풀리면 급호의적. 기본 Major(신규성 해명 요구) → aging ablation + EASY 보장 대비 + 용어 정의가 충족되면 Minor/Accept.
- 점수 좌우: (1) 고정-α vs 부하유도-α ablation, (2) EASY 대비 보장 수준 표, (3) starvation-free 정의의 선제·명료화.

## 실제 리젝 이력 근거 (이 렌즈가 반복 제기한 사유)
> `[해소]`/`[부분]`/`[잔존]`.

- **왜 GPU 단편화가 고전 CPU 스케줄링과 근본적으로 다른가** [MASCOTS R2 "does not articulate why fragmentation in GPU scheduling presents challenges fundamentally different from the classical CPU job scheduling problem, and whether existing CPU techniques are inapplicable"]. → `[잔존]` gang·이종이라는 새 맥락의 차별점을 정면 서술 필요.
- **고전 알고리즘(Linux CFS 등) 비교/차이** [CCGrid R3 "how does the Linux completely fair scheduler (or similar) compare … differences/similarities"]. → `[잔존]` aging·공유 계열 고전과의 위치 정리.
- **strict FIFO 가정 비판** [IEEE CLOUD R5 "most schedulers do not work as strict FIFO; would schedule t3,4,5 since space is available; many include preemption/priority/sharing"]. → `[부분]` 현 동기 서술이 과부하·HOL로 정교화, 백필(EASY) 베이스라인 포함으로 답. → 동기 예시에서 "백필도 못 막는 HOL"임을 더 또렷이.
- **용어 정의 불명(stuck queue, starvation-free, metric criteria)** [IEEE CLOUD R5; JoCC R2 "algorithms not explained"]. → `[잔존]` starvation-free의 HPC 관례 충돌 → 정의 선제 제시(본문 위 참조).
