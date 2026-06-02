# REEXPERIMENT_PLAN.md 상세 점검 리포트

> 대상: `docs/REEXPERIMENT_PLAN.md`
> 점검 범위: 내부 일관성, 기술적 사실 정확성, 논문/리젝 인용 정확성, 코드 매핑, 마크다운 렌더링, 완전성.
> 결론: **치명적 오류 없음.** 발견된 이슈 8건 중 7건 수정 완료, 1건은 의도된 미결(PoC 필요)로 유지.

## 요약 표

| # | 분류 | 심각도 | 상태 |
|---|---|---|---|
| I1 | 일관성: Phase 0/1에 폐기된 "Kueue" 잔존 | 높음 | ✅ 수정 |
| I2 | 마크다운: 아키텍처 코드펜스 안에 blockquote가 갇혀 렌더 깨짐 | 중간 | ✅ 수정 |
| I3 | 기술 정확성: kube-scheduler QueueSort 단일 제약 → Coscheduling 충돌 누락 | 높음 | ✅ 수정(R1) |
| I4 | 기술 정확성: QueueSort `Less()`가 클러스터 할당률(AR)을 못 봄 | 높음 | ✅ 수정(R2) |
| I5 | 사실 단정: cuda-checkpoint의 B200 지원을 확인 없이 단정 | 중간 | ✅ 수정 |
| I6 | 완전성: Phase 4가 리젝 ⑦을 참조하나 표에 ⑦ 미정의 | 낮음 | ✅ 수정 |
| I7 | 수치 정밀도: ω 범위 표기(10–200) 단순화 | 낮음 | ⚠ 유지(주석) |
| I8 | 미결: Phase 2 이주 방법 미확정 | — | ⚠ 의도된 미결 |

---

## 검증 OK 항목 (이슈 없음)

- **계수 범위**: α(0.01–1.99), β(80–95%, step 5%), δ(100k–500k, step 100k) — 논문 Table 1과 일치.
- **Eq.1 조건**: `P* = P + α·A·R if β > AR`, Alg.1의 "if latest allocation ≥ β then return"과 정합.
- **우선순위 정의**: p_i = 1/2^i (p0=1, p1=0.5...), n = 3×서버수 — 논문과 일치.
- **R 정의**: 요청==가용이면 1, 초과 1개당 −0.1 — 논문과 일치.
- **A(나이)**: 10분마다 +1, 스케줄 시 reset — 논문과 일치.
- **PTR DP**: f(a_j,t_r,M_j)=1 iff 서버가 정확히 빔, δ=재귀상한, ω=대기큐 임계 — Eq.2–6/Alg.2와 정합.
- **코드 매핑**: SFQA→`job_scheduler`(age_weight=α, svp_upper=β)+`job_age_struct`, PTR→`adjusting_server`(reorder_count=δ, preemption_task_window=ω) — `enum_definition.h`에 h100/h200/b200 정의 확인됨.
- **리젝 인용**: ② PipeSwitch/Singularity는 IEEE Cloud R5, "preemption feasibility 미논의"는 CCGrid R3, "memory contention" 미고려는 CCGrid R3, ⑥ "<8 GPU"는 MASCOTS R3 — 모두 실제 레터와 일치.
- **JoCC R1 허용 형태**: "K8S+GPU plugin 실통합 또는 Kairos류 시뮬레이터" 인용 정확.

---

## 발견 이슈 상세

### I1 — Phase 0/1에 폐기된 "Kueue" 잔존 (높음, 수정)
Section 5에서 K8S 기반을 **kube-scheduler 플러그인**으로 확정했으나, Phase 0("Kueue+DCGM…"), Phase 1("→ Kueue 반영", "Kueue 기본")에 이전 안인 Kueue가 남아 자기모순.
→ Phase 0을 `kube-scheduler-plugins(Coscheduling)+DCGM-exporter+Prometheus`로, Phase 1을 `P* 계산 컨트롤러 + 통합 QueueSort 플러그인`, baseline을 `default-scheduler FIFO/PriorityClass`로 수정.

### I2 — 아키텍처 다이어그램 렌더링 (중간, 수정)
"구현 원칙" blockquote와 시뮬레이터 박스가 모두 같은 ``` 코드펜스 내부에 들어가 blockquote가 일반 코드로 렌더됨.
→ 두 박스 + 화살표만 코드펜스에 두고, 구현 원칙/설계 리스크는 펜스 바깥의 실제 blockquote로 분리.

### I3 — QueueSort 단일 플러그인 제약 (높음, 수정) ★핵심
kube-scheduler는 **QueueSort 확장점에 플러그인을 하나만** 허용한다(펜딩 큐가 하나뿐이라 정렬 로직이 충돌 불가). 그런데 gang용 **Coscheduling 플러그인이 이미 QueueSort를 구현**(PodGroup back-to-back 정렬)한다. 따라서 SFQA를 별도 QueueSort로 넣으면 gang 스케줄링과 **양립 불가**.
→ 해결책을 R1로 명문화: **PodGroup 정렬 + P* 정렬을 동시에 수행하는 단일 통합 QueueSort 플러그인**을 작성하거나, P*는 컨트롤러가 주입하고 QueueSort는 그 값으로만 정렬.
근거: Kubernetes Scheduling Framework 문서, scheduler-plugins Coscheduling KEP.

### I4 — QueueSort의 클러스터 상태 접근 한계 (높음, 수정)
QueueSort의 `Less(p1, p2)`는 **두 Pod 정보만** 인자로 받는다. SFQA의 발동 트리거(AR<β, 클러스터 할당률)와 R(가용 가속기 대비 적합도)은 **클러스터 전역 상태**가 필요해 `Less` 내부에서 직접 계산 불가.
→ R2로 명문화: 별도 컨트롤러가 P*/AR/R을 주기적으로 계산해 **Pod annotation/PriorityClass에 주입**, QueueSort는 그 값을 읽어 정렬만.

### I5 — cuda-checkpoint의 B200 지원 단정 (중간, 수정)
원문은 "cuda-checkpoint + CRIU (H100/B200 GPU 프로세스 C/R)"로 B200 지원을 단정. 웹 검색으로 B200(Blackwell)에서의 cuda-checkpoint 지원을 **공식 확인하지 못함**(H100/Hopper 사례는 일반적).
→ "H100/Hopper 지원 확인; B200/Blackwell는 드라이버·CUDA 버전 지원 확인 필요"로 수정. Phase 2 PoC에서 실검증 필요.

### I6 — 리젝 ⑦ 미정의 (낮음, 수정)
Phase 4가 "리젝 ③⑦"을 참조하나 Section 1 표는 ①–⑥만 정의.
→ 표에 ⑦(글쓰기/명확성: tasks vs jobs 혼용, 생성형 AI 느낌, 용어 미정의 — IEEE Cloud R3·R5, CCGrid R2, JoCC R2) 추가.

### I7 — ω 범위 표기 (낮음, 유지)
논문은 Table 1에서 ω=10–100(step 10), Section 6.x에서 ω=20–200(step 20)으로 실험마다 다르게 사용. 문서는 "10–200"으로 단순 표기 → 큰 오해 없어 유지하되 본 리포트에 차이를 기록.

### I8 — Phase 2 이주 방법 미확정 (의도된 미결)
app-level checkpoint vs cuda-checkpoint+CRIU는 Phase 2 착수 시 PoC로 결정하기로 한 의도된 미결 사항. I5와 연동(B200 지원 확인 결과가 선택에 영향).

---

## 추가 권고 (차기 반영 후보)
- **리젝 ⑤(온라인 적응)**: Phase 3에 "간단한 온라인 계수 적응 휴리스틱"을 명시적 baseline으로 추가하면 JoCC R1 대응이 강화됨.
- **베이스라인 구체화**: Phase 4의 SOTA 비교 대상(Tiresias/Themis/Optimus/Lucid/Sia) 중 K8S에서 실제 재현 가능한 것과 시뮬레이터로만 비교할 것을 구분.
- **메모리 경합 측정 방법**: DCGM의 mem util 외에, colocation 시 throughput 저하(%)를 별도 지표로 정의하면 리젝 ② 대응이 정량화됨.
