# B200×8 단일노드 실측 (heavy-tail) — 큐-축 9정책

> 생성 2026-06-12. 직전 압축 캠페인(`B200_RESULTS.md`)이 duration 균일화로 아사 레짐을
> 못 만들어 non-validation으로 끝난 것을, **heavy-tail duration 보존**으로 바로잡는 재실측.
> 분석기 정의는 시뮬 `sim/order_fairness.py`·BSLD와 동일. **`paper/sn-article.tex`는 미수정.**
> 로그·raw: `/raid/squad/runs/m_ht_*/`.

## 0. 실 B200 서버 동작 확인 (real-cluster)

이 캠페인은 시뮬이 아니라 **실제 NVIDIA B200×8 노드**에서 돌았다:
- 노드 `llmd-control-plane`, K8s v1.31, GPU product 라벨 `NVIDIA-B200`, allocatable 8.
- 9정책 × 500잡 = **4,500개 실 K8s Pod**을 진짜 kube-scheduler가 스케줄·실행·완료.
- 측정값은 **실 Pod 수명주기 타임스탬프**: 큐잉 = `pod.status.start_time − creation_timestamp`,
  JCT = `container.terminated.finished_at − creation_timestamp`. 합성 아님.
- GPU 점유율은 `nvidia-smi` + K8s API 폴링 실측 — 본 캠페인 정상 구간 **alloc 80~91%**,
  게이트 검증 시 **8/8 GPU 100% 포화 + 대기 큐 47개**(아래 §1). 실 과부하가 물리적으로 형성됨.

## 1. 실험 구성 — 레짐 형성 게이트 통과

- 트레이스: `results/philly_sample500_jct2h_window.csv` (Philly JCT≤2h 윈도우, 500잡).
- 워크로드: `--trace csv --kappa 30 --min-dur 2 --max-dur 0 --submit-clamp 2.0` (전 9 run 동일).
  - **duration heavy-tail 보존**: post-κ 2~240s, p50 11s, p99/p50 = 20.5×, 고유값 290. (압축 캠페인은 [6,8]s 균일·고유값 11.)
  - **과부하 분리 형성**: κ로 duration만 스케일, `submit-clamp 2s`로 도착을 압축 → **게이트 검증 시 alloc 100%·대기 큐 47** 확인.
- **게이트 2개 통과 후** 캠페인 진행: (1) duration spread, (2) 지속 과부하. 둘 다 충족.

## 2. 결과 (9 run, 단일 시드)

순서 공정성은 **실 wall 제출시각 기준**(submit-clamp로 도착을 압축했으므로 물리적 도착 = wall).

| 정책 | q_p50 | q_p90 | q_max | BSLD_p50 | BSLD_max | fair평균 | **lt50%↓** | p1 | alloc | walltime |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| FIFO (default) | 857 | 2041 | 3855 | 16.3 | 373 | 56.3 | 49.8 | 0.2 | 91% | 68분 |
| FIFO (gate) | 422 | 631 | 2165 | 24.4 | 208 | 93.8 | 6.2 | 3.8 | 84% | 51분 |
| SJF | 15 | 1146 | 2507 | 1.8 | 191 | 71.9 | 30.4 | 0.0 | 82% | 52분 |
| LAS | 424 | 662 | 2202 | 24.4 | 212 | 94.5 | 5.2 | 3.8 | 84% | 52분 |
| Kueue | 449 | 1785 | 2048 | 29.2 | 206 | 95.6 | 4.4 | 19.3 | 82% | 52분 |
| EASY | 1138 | 1781 | 2114 | 69.5 | 201 | 96.6 | 1.8 | 17.6 | 80% | 54분 |
| Themis | 76 | 984 | 2464 | 5.1 | 185 | 70.6 | 31.4 | 0.0 | 84% | 52분 |
| SAFA (고정 α) | 424 | 660 | 2207 | 24.5 | 212 | 94.4 | 5.2 | 3.8 | 83% | 52분 |
| **SAFA (제안)** | 423 | 664 | 2203 | 24.4 | 212 | 94.6 | 5.2 | 3.8 | 83% | 52분 |

단위 초. **주 지표 = lt50%·fair평균**(n=500에 강건). p1(하위1%)은 =0 잡이 1~7개라 칼날 위 → 참고만(논문 §VI 소표본 경고).

> **SAFA(제안) 갱신 이력**: 최초 측정은 lt50=28.6%(SJF류 아사)였으나, 이는 옛 `sfqa-auto` 컨트롤러가 σ\*-2-tier의 tier2를 SJF로 정렬한 **버그**였음(시뮬 `SFQAAuto`와 불일치). 컨트롤러를 논문 `SFQAAuto`(α_eff 단일승격, zero-knob)와 동일하게 수정(`policy_controller.py`, commit 6c43b14) 후 **m_ht_auto만 재실행** → 위 값(lt50 5.2%). 다른 8정책은 컨트롤러 미변경이라 유지.

## 3. Ablation — SAFA 고정 α vs 무튜닝(제안)

| | q_p50 | lt50%↓ | fair평균 | BSLD_p50 |
|---|--:|--:|--:|--:|
| SAFA (고정 α, --beta 80) | 424 | **5.2** | 94.4 | 24.5 |
| SAFA (무튜닝, 제안) — 수정 후 | 423 | **5.2** | 94.6 | 24.4 |

수정된 무튜닝 SAFA는 고정 α와 **사실상 동일**(q_p50 424≈423, lt50 5.2%=5.2%) — 노브 없이도 고정 α 수준의 순서 공정성을 달성한다(논문의 zero-knob 주장과 일치). 단, 이 등가성의 해석엔 단서가 있다(§4-aging 한계).

## 4. 시뮬 경향과의 일치성 — 축별 정직 평가

직전 압축 캠페인과 달리 **이번엔 순서 공정성이 강하게 변별**된다(lt50 1.8~49.8%). 레짐이 형성됐다.

### ✅ 확증 (CONFIRM)
- **그리디의 순서 불공정**: FIFO-default(49.8%)·Themis(31.4%)·SJF(30.4%)가 높은 lt50% — 시뮬의 "정보-우위 그리디가 과부하에서 추월 불공정↑" 경향과 **일치**.
- **예약/admission이 가장 공정**: EASY(1.8%)·Kueue(4.4%)가 최저 lt50% — 자리 예약·쿼타가 추월을 억제.
- **SAFA(고정 α·무튜닝 모두) FIFO 수준 순서공정성 유지**: 고정 5.2%·무튜닝 5.2% ≈ FIFO-gate 6.2% ≈ LAS 5.2% — 논문의 "SAFA가 FIFO 수준 순서공정성 유지" 및 "무튜닝(zero-knob)이 고정 α 수준 달성" 주장과 **일치**.
- **처리율(walltime)은 정책 거의 불변**: 51~54분(FIFO-default만 68분) — makespan-bound, 시뮬 전제와 일치.

### 🔧 컨트롤러 버그 수정 (최초 반증 → 해소)
- **최초 측정에서 무튜닝 SAFA가 lt50=28.6%(SJF류 아사)** 로 나와 논문 주장과 정면 배치됐다. 원인은 SAFA 개념이 아니라 **K8s 컨트롤러 버그**였다: 옛 `sfqa-auto`가 σ\*-2-tier의 tier2를 SJF로 정렬해 무튜닝 에이징을 덮어씀(시뮬 `SFQAAuto`와 불일치).
- 컨트롤러를 시뮬 `SFQAAuto`(α_eff 단일승급, age·R만 사용, duration/σ\*/SJF 미사용)와 동일하게 수정(commit 6c43b14, 무작위 큐 2만건 등가성 0건 불일치 검증)하고 **m_ht_auto 재실행** → **lt50 28.6% → 5.2%**, q_p50 134 → 423. **아사 소멸, 고정 α와 동등.** 즉 최초 반증은 구현 버그였고, 수정 후 시뮬 경향과 일치.

### ⚠️ 단서 — 이 레짐에서 에이징은 FIFO로 퇴화 (해석 주의)
수정으로 무튜닝 SAFA가 "FIFO 수준 공정"이 된 것은 맞으나, **그 성공이 에이징의 영리한 아사-탐지 때문이라고 보긴 어렵다**:
- 우리는 `submit-clamp 2s`로 도착을 **균일화**했다 → 작업의 `creation_timestamp`가 제출(=트레이스) 순서와 1:1.
- 컨트롤러의 age = now − creation 이므로 **대기 큐 안에서 age 순서 = 제출 순서 = 도착 순서**. 따라서 `P*=P+α_eff·age_rel·R`의 에이징 승급은 이 조건에서 **FIFO(+자원 가중)로 퇴화**한다.
- 결과적으로 무튜닝 SAFA ≈ FIFO-gate ≈ 고정 α(셋 다 lt50 ~5%)로 수렴한 것은 자연스럽다. **버그 수정이 "해로운 SJF 퇴화"를 제거해 FIFO-안전 상태로 되돌린 것**까지는 정당하나, 에이징이 *또래 대비 굶주린 큰 잡을 선별 승급*하는 고유 가치는 **균일 도착·단일노드에선 변별되지 않는다**.
- 그 고유 가치(아사 탐지가 단순 FIFO보다 나음)는 **버스트 도착 + 다중노드(단편화)** 에서만 드러나며, 시뮬(256~1024 GPU·트레이스 버스트)이 그 축을 담당한다.

### ⚠️ 단일노드 구조적 한계 (명시)
- 본 실측이 잡는 순서 불공정은 **스케줄링/큐-순서 유발**(작은·늦은 잡이 큐에서 추월)이며, 이는 SAFA의 실제 메커니즘(큐 재정렬) 축이라 **단일노드에서 검증 가능**하다.
- 반면 **배치/단편화 유발 아사**(여러 노드에 7장씩 흩어진 빈 GPU로 8-GPU 갱 잡이 stranded)는 단일노드(8 GPU가 한 노드)엔 **원리적으로 부재** — 이 축은 시뮬의 256~1024 GPU 다중노드와 FGD가 담당한다. 단일노드 실측은 **큐 축에 한정**됨을 명시한다.
- 또한 과부하 형성을 위해 `submit-clamp`로 **도착을 균일화**했으므로, 트레이스 원래의 버스트가 유발하는 아사는 본 실측 범위 밖이다.
- p1은 n=500에서 =0 잡 1~7개로 표본 변동이 커 주 지표에서 제외(lt50%·fair평균 사용).

### 종합 판정
**확증(컨트롤러 버그 수정 후).** 큐-축 레짐은 제대로 형성됐고(그리디 불공정·예약 공정·처리율 불변 모두 시뮬과 일치), 단일노드는 SAFA의 **큐 재정렬 축을 검증할 수 있음**이 확인됐다. 최초에 무튜닝 SAFA가 아사(lt50 28.6%)를 보였으나, 이는 SAFA 개념이 아니라 **K8s 컨트롤러의 SJF-퇴화 버그**였고, 시뮬 `SFQAAuto`와 동일하게 수정 후 재실행하니 **lt50 5.2%로 고정 α와 동등**해져 시뮬 경향과 일치했다(무튜닝이 노브 없이 고정 α 수준 공정성 달성 = 논문 zero-knob 주장 확증).
**단, 정직한 단서**: 이 검증은 `submit-clamp` 균일 도착이라 **에이징이 FIFO로 퇴화**한 상태에서 이뤄졌다(age = 제출 순서). 따라서 "무튜닝 SAFA가 해로운 SJF-퇴화 없이 FIFO-안전하다"까지는 확증이나, **에이징이 FIFO보다 영리하게 아사를 선별 예방하는 고유 가치는 버스트 도착·다중노드(시뮬 전담)에서만 입증**된다. 배치/단편화 축도 단일노드 범위 밖이다.

## 5. 재현
```
cd squad_ctrl
EXP="--trace csv --input ../results/philly_sample500_jct2h_window.csv --sample 0 --kappa 30 --min-dur 2 --max-dur 0 --submit-clamp 2.0"
./run_one.sh none m_ht_fifo "" "$EXP";  ./run_one.sh fifo m_ht_gatefifo "" "$EXP"
./run_one.sh sjf m_ht_sjf "" "$EXP";    ./run_one.sh las m_ht_las "" "$EXP"
./run_one.sh kueue m_ht_kueue "" "$EXP";./run_one.sh easy m_ht_easy "" "$EXP"
./run_one.sh themis m_ht_themis "" "$EXP"
./run_one.sh sfqa m_ht_sfqa "--beta 80" "$EXP";  ./run_one.sh sfqa-auto m_ht_auto "" "$EXP"
```
- CSV ingester(`k8s_replay/ingest.py::ingest_csv`)를 추가해 sim 트레이스 포맷을 K8s 하니스가 소비.
- 순서공정성은 **wall 제출시각 기준**으로 계산(submit-clamp로 트레이스 도착이 fictional해짐 — trace-arrival 기준이면 lt50이 0으로 인위 포화).
