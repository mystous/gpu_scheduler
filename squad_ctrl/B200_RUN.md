# B200 단일노드 K8s — 현 비교 실험 실행 가이드

> 목적: 논문(SAFA)의 **큐-축 비교 정책**을 실제 NVIDIA B200×8 단일노드 K8s에서 실측해
> 리젝 ①(시뮬-only)을 정면으로 메운다. 2026-06-04/05 캠페인 인프라를 현 정책·실험 구성으로 재점검·확장한 결과.
>
> **본 개정의 핵심**: 시뮬에 추가된 실험들(고정 α vs 무튜닝 ablation, 합성계수 민감도, 독립 트레이스 일반화, 배치 축, 충실도)을 점검해 **B200 단일노드에서 실측이 의미 있는 것만** 추려 실행 대상으로 확정한다(§3.2 적용 매트릭스).

## 1. 환경 전제 (실험 서버 = `/home/mystous/gpu_scheduler`, `/raid/squad`)
- 노드: NVIDIA **B200×8 단일노드**, k8s v1.31 (기존 캠페인은 kind `llmd`).
- 네임스페이스 `squad`, GPU product 라벨 `NVIDIA-B200`.
- venv `/raid/squad/venv`, kubeconfig `~/.kube/config`.
- Kueue v0.9.4 설치 + `kueue-queues.yaml`(ClusterQueue/LocalQueue `squad-lq`) 적용 — `kueue` 정책용.
- 워크로드 = **GPU-holder 스텁**(점유·스케줄링은 진짜 kube-scheduler, 연산은 sleep) → 실제 K8s 타임스탬프로 큐잉지연·JCT 측정.
- 코드는 이 repo(origin) 동기화본을 서버에서 pull. **본 점검에서 Themis를 컨트롤러·러너에 추가**(아래 §3).

## 2. 테스트셋 (그대로 보존됨, `results/`)
| 파일 | 규모 | 용도 |
|---|---|---|
| `philly_sample1000_normalized.csv` | 1000잡 (seed=42 층화) | 본선 비교(κ=3000) — 기존 캠페인 표준 |
| `philly_2k_c48.csv` (**Philly-2K-C48**) | 2000잡, dur 48h 절단 | **차기 표준** — GPU·duration 분포 원본 보존 |
| `philly_sample500_jct2h_window.csv` | 500잡 (JCT≤2h, d51~65 윈도우) | 충실 duration 체인(BSLD 독립 신호) |

트레이스 원본: `/raid/squad/traces/philly/...`. 샘플 재생성: `run_experiment.py --sample N --seed 42 --clamp-over <초>`.

## 3. 정책 지원 현황 (현 10정책 대비)
큐-축 정책은 `policy_controller.py`(gate 해제 순서) + `run_experiment.py`(트레이스 제출)로 실행.

| 정책 | B200 K8s 실행 | 비고 |
|---|---|---|
| FIFO (`none`=default / `fifo`=gate) | ✅ | 통제군(게이트 유무 2종) |
| SJF | ✅ | `squad.io/duration` 라벨 |
| LAS (Tiresias) | ✅ | 컨트롤러 지원(기존 캠페인 미실행 → 이번에 추가 실행) |
| Kueue | ✅ | 네이티브 LocalQueue 제출(`--policy kueue`) |
| EASY backfill | ✅ | 예약+백필(완벽 추정 상한) |
| **Themis** | ✅ **(본 점검에서 추가)** | ρ=(대기+잔여)/ideal 정렬. `policy_controller.py`·`run_experiment.py` choices에 추가 |
| SAFA(고정 α) (키 `sfqa`) | ✅ | $P^*=P+\alpha A R$, 고정 노브. ablation의 고정군 |
| SAFA (키 `sfqa-auto`) | ✅ | zero-knob 무튜닝. **제안 정책**, ablation의 무튜닝군 |
| **FGD** | ❌ **범위 밖** | 노드 간 단편화 배치 정책 — **단일노드엔 노드 간 단편화가 없어 무의미**. 다중노드(H100 3노드) 시 또는 시뮬 전담. |
| **Lucid** | ❌ **범위 밖** | collocation(GPU 공유) 필요 — holder 스텁은 whole-GPU. MPS/타임슬라이싱 인프라 추가 필요(큰 작업). |

→ **B200 단일노드 실측 = 큐-축 8정책**(FIFO·SJF·LAS·Kueue·EASY·Themis·SAFA(고정 α)·SAFA). 이게 SAFA의 기여 축(HOL 블로킹·기아)과 정확히 일치. FGD·Lucid는 직교 축(배치·collocation)이라 단일노드 큐 검증의 범위 밖임을 논문에 명시.

### 3.1 FGD·Lucid 제외 사유 (상세)

두 정책의 제외는 "강한 베이스라인 회피"가 아니라, **단일노드라는 물리 조건에서 그 정책의 결정 변수가 정의되지 않거나(FGD) 측정 인프라가 부재(Lucid)** 하기 때문이다. 둘 다 QUELL의 기여 축(큐 순서)이 아닌 **직교 축**(노드 간 배치 / GPU 공유 collocation)이며, 이 축은 시뮬레이터가 256–1024 GPU 다중노드 규모에서 이미 평가한다.

**FGD — 단일노드엔 결정 변수가 존재하지 않음 (FIFO로 퇴화).**
- FGD의 결정 변수는 **노드 선택**이다: 단편화 증가 $\Delta F$가 최소인 노드에 배치. 측도는 $F_n = \text{free}_n \cdot P(\text{size} > \text{free}_n)$ — 노드 $n$의 기대 미할당 GPU(노드 간 stranding).
- **B200 단일노드 = 노드가 1개** → 노드 선택 결정 자체가 없다. 모든 잡이 유일한 노드로 가고, $\Delta F$ 비교·최소점유 노드 통합 같은 FGD 메커니즘은 전부 null이 된다.
- FGD가 줄이려는 "단편화"는 **노드 간 stranding**(여러 서버에 7장씩 흩어진 빈 GPU로 8-GPU 잡을 못 넣는 상황)이다. 8개 GPU가 한 노드에 연속으로 있는 단일노드엔 이 stranding이 **원리적으로 없다**(잡 큐는 FCFS, 배치는 강제).
- 결과: 단일노드에서 FGD는 **FIFO와 거동이 동일**하다. 따로 실측해도 FIFO 행을 복제할 뿐 새 정보가 0이다.
- FGD의 가치는 **클러스터 규모(다중 노드)**에서만 발현한다(원 FGD 논문도 6,200+ GPU 클러스터로 평가). → 우리 시뮬의 256–1024 GPU(다중노드)가 이 축을 담당. 실측은 H100 3노드 합류 시 의미가 생긴다.

**Lucid — collocation 측정 인프라가 단일노드 whole-GPU 설정에 부재.**
- Lucid의 결정 변수는 **collocation**(호환되는 두 잡을 같은 GPU 집합에 packing)이다. 프로파일러(Primo EBM)로 공유 안전성·간섭(슬로다운)을 예측해 GPU 공유 이득을 얻는다.
- 실 K8s에서 이를 측정하려면 **GPU 공유 인프라**가 필요하다: MPS(Multi-Process Service) / MIG / time-slicing + 분수 GPU device-plugin 설정. 그런데 기존 캠페인의 GPU-holder 스텁은 **whole-GPU 점유**(1 pod = N개 통GPU, `nvidia.com/gpu` limit)로, collocation의 정반대다.
- 충실한 Lucid 실측엔 세 가지가 선행돼야 한다 — (a) B200에 MPS/MIG 활성 + 분수 GPU 플러그인, (b) 어떤 잡을 colocate할지·그 슬로다운(SS score)을 정할 **프로파일/간섭 모델**, (c) 실제 co-run 슬로다운(메모리 대역폭·SM 경합) **측정**. (c)는 그 자체가 별도 연구 측정이며, 설정 플래그가 아니라 상당한 인프라 빌드다.
- 게다가 holder 스텁의 연산은 sleep이라 **colocate해도 측정할 실제 간섭이 없다** — Lucid의 packing 이득/손실을 보려면 진짜 워크로드를 돌려야 하고, 이는 "빠르고 결정적인 큐 측정"이라는 holder-스텁 설계를 무력화한다.
- 또한 Lucid는 잡별 utilization/throughput 프로파일을 전제하는데 트레이스엔 없다(시뮬에선 합성으로 대체). 실측에선 이 이상화가 **실 프로파일링 필요**로 더 무거워진다.
- 결론: 단일노드 whole-GPU holder 설정의 **범위 밖**. GPU 공유 인프라 + 실 워크로드 + 간섭 측정이 선행돼야 하며, 이는 별도 연구 규모의 작업이다.

**정리.** FGD는 *결정 변수가 단일노드에 정의되지 않아 FIFO 중복*이고, Lucid는 *collocation 측정 인프라(GPU 공유+실 워크로드+간섭 측정)가 부재*하다. 둘 다 직교 축이라 시뮬이 규모에서 커버하므로, 단일노드 실측은 **결정 변수가 단일노드에 정의되는 큐-축 정책**에 한정한다 — 이것이 "convenient exclusion"이 아닌 원리적 한정이다.

### 3.2 현 실험 변경분의 B200 적용 매트릭스 (★본 개정 핵심)

시뮬에 추가·변경된 실험을 단일노드 B200 실측에 매핑한다. **단일노드라는 물리 조건**과 **gate 기반 holder 하니스**(큐 순서만 제어, 배치는 kube-scheduler가 binding)가 적용 가능 여부를 가른다.

| 시뮬 실험 (현행) | B200 단일노드 | 사유 / 조치 |
|---|---|---|
| **큐-축 8정책 비교** | ✅ **실행** | SAFA 기여 축(HOL·기아)과 정확히 일치. §4 스크립트 |
| **Ablation: SAFA(고정 α) vs SAFA** | ✅ **실행(자동 포함)** | `sfqa`·`sfqa-auto` 두 run이 곧 ablation. §5에서 두 run의 p50·max·BSLD를 직접 대비 → 무튜닝의 실측 순효과 |
| **독립 트레이스 일반화** | ⚠️ **선택 실행** | 큐-축 8정책을 **2번째 테스트셋**(Philly-2K-C48 또는 별도 트레이스)으로 1회 더 → 실 클러스터 일반화 보강. 비용 있으니 1순위 8정책 완료 후 |
| **합성 계수 민감도(±50%)** | ❌ **부적용** | 타입 속도계수·오버헤드·Lucid SS는 \textit{시뮬 모델 파라미터}. 실 클러스터는 그 자체가 ground truth라 흔들 대상이 없음(오히려 B200 실측이 오버헤드 모델의 \textit{원천}) |
| **시뮬레이터 충실도(toy 대조)** | ❌ **부적용** | 이산사건 엔진 내부 정확성 검증 — 실 클러스터엔 해석해 대조 개념이 없음 |
| **배치 축(most-alloc/compact/round_robin/mcts)** | ❌ **단일노드 부적용** | 배치 = \textbf{노드 선택}인데 단일노드엔 노드가 1개. holder 하니스는 큐 게이트만 제어하고 GPU binding은 kube-scheduler가 수행 → 우리 배치 정책을 주입할 지점이 없음. **FGD와 동일 사유**, 다중노드(H100 3노드) 합류 시 의미 |

**정리**: B200 단일노드에서 **필요·가능한 실측은 (1) 큐-축 8정책, (2) 그 안에 포함된 고정 vs 무튜닝 ablation, (3) 선택적 2번째 트레이스 일반화** 셋이다. 민감도·충실도·배치 축은 단일노드에 정의되지 않거나(배치) 실 클러스터에 대응 개념이 없어(민감도·충실도) 시뮬 전담이며, 이를 논문에 명시한다(\S\ref{eval:robust}의 강건성 검증은 시뮬 한정, 실측은 큐-축 정책 비교가 담당).

## 4. 실행 절차 (정책당 1 run)
```bash
cd /home/mystous/gpu_scheduler/squad_ctrl
# run_one.sh <policy> <run_id> "<ctrl_extra>" "<exp_extra>"
./run_one.sh none      m_fifo      ""              ""           # default FIFO 베이스라인
./run_one.sh fifo      m_gatefifo  ""              ""           # gate-FIFO 통제군
./run_one.sh sjf       m_sjf       ""              ""
./run_one.sh las       m_las       ""              ""
./run_one.sh kueue     m_kueue     ""              ""
./run_one.sh easy      m_easy      ""              ""
./run_one.sh themis    m_themis    ""              ""
./run_one.sh sfqa      m_sfqa      "--beta 80"     ""           # SAFA(고정 α) — ablation 고정군
./run_one.sh sfqa-auto m_auto      ""              ""           # SAFA(무튜닝) — 제안 + ablation 무튜닝군
```
- 공통 워크로드는 `run_one.sh`에 박힌 `--sample 1000 --seed 42 --kappa 3000 --min-dur 6 --max-dur 8`.
- **duration 이질성을 살리려면**(BSLD 독립 신호) Philly-2K-C48 또는 충실 체인 설정으로 `EXP_EXTRA` 교체 — 예: `"--sample 500 --kappa 360 --min-dur 5 --max-dur 20 --clamp-over 172800"` (기존 S=360 체인과 동일 취지).
- 각 run 산출: `/raid/squad/runs/<run_id>/{jct,metrics,submit_log}.csv`.

## 5. 집계·분석
```bash
$VENV analyze.py            # → results/runs_summary.csv, tables.md (p50/p90/max 큐잉지연·BSLD)
$VENV distributions.py      # → CDF(큐잉지연·BSLD)
```
논문 §VI 실측 표(기존 SUMMARY.md의 8정책 표)에 LAS·Themis 행을 추가해 큐-축 8정책 완성.

**Ablation(실측):** 위 8정책 표의 `sfqa`(고정 α) 행과 `sfqa-auto`(무튜닝) 행을 직접 대비하면, 시뮬 §VI-D의 "무튜닝 순효과" ablation을 \textit{실 클러스터}에서 재확인하는 것이 된다 --- 두 run의 p50·max 큐잉지연·BSLD 차이를 별도 소표로 뽑아 시뮬 경향(무튜닝이 공정성↑·중앙값 소폭 양보)과 일치하는지 보고.

## 6. 갭·주의 (실행 전 확인)
1. **FGD/Lucid 범위 밖** — 위 §3. 논문 실측 절에 "단일노드 큐-축 검증"으로 한정 명시.
2. **선점 없음** — 전 정책 비선점(holder 스텁 whole-GPU). 리젝 ②(GPU 선점 비현실성)는 **비선점 설계로 회피**했음을 강점으로 서술.
3. **duration 압축의 한계** — κ=3000·cap 6~8s는 서비스시간을 사실상 균일화해 BSLD 신호가 약함(기존 SUMMARY.md 명시). 이질 duration이 핵심이면 Philly-2K-C48/충실 체인으로 별도 run.
4. **Kueue 멀티-VC** — 단일 VC면 FIFO로 degrade. VC 분포가 있는 트레이스/라벨로 돌려야 쿼타 공정성이 발현(리뷰어 R3 우려).
5. **시드·반복** — 핵심 지표(p50·max·BSLD)는 시드 2~3개로 변동성 구간 확보 권장(리뷰어 R4).
6. **오버헤드 실측** — `measure_overheads.py`로 스케줄링·기동·종료 구간 계측(논문 B200 오버헤드 모델의 원천). 이미 `results/overheads/`에 1차 결과 보존.

## 7. 한 줄 요약
인프라·테스트셋·컨트롤러 모두 준비됨. B200 단일노드에서 **필요·가능한 실측 = 큐-축 8정책(FIFO·SJF·LAS·Kueue·EASY·Themis·SAFA(고정 α)·SAFA) + 그 안의 고정 vs 무튜닝 ablation + 선택적 2번째 트레이스**(§3.2 매트릭스). 서버에서 §4 스크립트를 돌리면 논문 §VI에 실 클러스터 비교를 채워 리젝①(시뮬-only)을 정면 해소한다. **배치 축·민감도·충실도는 단일노드에 정의되지 않거나 실 클러스터 대응 개념이 없어 시뮬 전담**이며(배치 축은 FGD와 같은 사유로 다중노드 향후), FGD·Lucid도 다중노드/collocation 인프라가 필요해 범위 밖 --- 모두 논문에 명시.
