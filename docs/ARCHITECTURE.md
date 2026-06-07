# 아키텍처 분석

> 갱신: 2026-06-07. 프로젝트는 SQUAD 재실험을 거치며 3개 평가 계층으로 확장됨.
> 이 문서는 전체 구조와 C++ 시뮬레이터 상세를 다룬다. K8S 실측 상세는
> `results/SUMMARY.md`·`squad_ctrl/`, Python 시뮬 설계는 `docs/SIMULATOR_DESIGN.md` 참고.

## 전체 시스템 구성 (3계층)

```
                     ┌───────────────────────────────┐
                     │   워크로드 트레이스 (Philly 등)  │
                     │   k8s_replay/ : ingest →       │
                     │   normalize → emit/trace_to_cpp│
                     └───────┬───────────┬────────────┘
                             │           │
        ┌────────────────────┤           ├─────────────────────┐
        ▼                    ▼           ▼                     ▼
┌────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│ ① C++ 시뮬레이터 │  │ ② K8S 실측 (B200×8)     │  │ ③ Python 이산사건 시뮬   │
│ gpu_scheduer/  │  │ squad_ctrl/ (Python    │  │ sim/ (SoA·numpy,       │
│ 그리드 서치·     │  │  gate 컨트롤러, 10정책)  │  │  Philly 111k 부하 스윕, │
│ 민감도 스윕      │  │ k8s/ (Go 포팅·플러그인) │  │  Lucid/Sia SOTA 포함)  │
│                │  │ holder_img/ (GPU 스텁)  │  │  오버헤드 보정 주입       │
└───────┬────────┘  └───────────┬────────────┘  └───────────┬────────────┘
        │                       │                           │
        └───────────────────────┼───────────────────────────┘
                                ▼
                  ┌───────────────────────────┐
                  │  results/ (집계·그래프)      │
                  │  원본: 서버 /raid/squad/    │
                  └───────────────────────────┘
```

| 계층 | 코드 | 용도 | 알고리즘 일치성 |
|---|---|---|---|
| ① C++ 시뮬레이터 | `gpu_scheduer/` | 하이퍼파라미터 그리드 서치, 상수 민감도 스윕 | SFQA/PTR 원본 구현 |
| ② K8S 실측 | `squad_ctrl/`, `k8s/`, `holder_img/` | 실제 kube-scheduler 실측 (리젝 ① 대응) | `squad_algo.py` = 논문 Algorithm 1 |
| ③ Python 시뮬 | `sim/` | 대규모(111k 잡·256~1024 GPU)·SOTA 비교 | `policies.py`가 컨트롤러와 동일 로직 |

- **②의 두 구현**: `squad_ctrl/`(Python, PodSchedulingGates 방식 — 실제 사용)와
  `k8s/`(Go — QueueSort 플러그인 + SFQA/PTR 컨트롤러, 방화벽 제약 대비 포팅판).
- **오버헤드 보정**: ②에서 실측한 수명주기·체크포인트 오버헤드(`results/overheads/params.md`)를
  ③에 주입해 실측↔시뮬 정합성 확보.

---

## ① C++ 시뮬레이터 (`gpu_scheduer/`)

### 시스템 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                      linux_main.cpp                          │
│                    (설정 파싱, 실험 시작)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   experiment_perform                         │
│              (멀티스레드 실험 관리)                            │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Thread 1 │   │ Thread 2 │   │ Thread N │
        │ Emulator │   │ Emulator │   │ Emulator │
        └──────────┘   └──────────┘   └──────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                     job_emulator                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐    │
│  │  job_list   │  │ server_list │  │  wait_queue_group │    │
│  └─────────────┘  └─────────────┘  └──────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│                  ┌───────────────┐                          │
│                  │ job_scheduler │ (추상 클래스)             │
│                  └───────────────┘                          │
│                          │                                   │
│    ┌─────────┬─────────┬┴─────────┬─────────┐              │
│    ▼         ▼         ▼          ▼         ▼              │
│ MostAlloc  Compact  RoundRobin  MCTS   FareShare(미구현)    │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 클래스 관계

```
job_scheduler (추상 기반 클래스)
  ├── scheduler_mostallocated
  ├── scheduler_compact
  ├── scheduler_round_robin
  ├── scheduler_mcts
  └── scheduler_fare_share   # 미구현 (arrange_server가 return 0만)

job_emulator
  ├── has job_list (vector<job_entry>)
  ├── has server_list (vector<server_entry>)
  ├── has scheduler_obj (job_scheduler*)
  ├── has wait_queue_group (vector<queue<job_entry*>*>)
  └── has server_control (adjusting_server*)

experiment_perform
  ├── has emulator_vector (vector<job_emulator*>)
  └── has thread_meta_list (병렬 처리 관리)
```

### 실행 흐름

```
linux_main.cpp
  │
  ├── parse_config_file()           # 설정 파일 로드
  │
  ├── build_hyperparameter()        # 그리드 서치 공간 생성
  │
  └── experiment_perform::start_experiment()
        │
        └── for each thread:
              │
              ├── job_emulator 생성
              ├── build_job_list()
              ├── build_server_list()
              ├── build_job_queue()
              │
              └── for each hyperparameter:
                    │
                    ├── initialize_job_state()
                    ├── initialize_server_state()
                    │
                    └── while not finished:
                          ├── update_wait_queue()
                          ├── scheduler->scheduling_job()
                          ├── server->ticktok()
                          ├── server->flush()
                          └── check_defragmentation()
```

### 입력 데이터

**작업 데이터 CSV 형식:**
```
pod_name, pod_type, project, namespace, user_team, start_time, finish_time,
accelerator_count, computing_level, gpu_utilization, accelerator_flavor, preemption
```

**서버 데이터 CSV 형식:**
```
server_name, accelerator_count, accelerator_type
```

**설정 파일 형식** (1~6행 필수, 7~9행 선택):
```
4                           # thread_total (스레드 수)
0.13889,0.83889,0.1         # alpha_para (min, max, step)
70.0,95.0,5.0               # beta_para
100000,1000000,100000       # d_para
20,100,10                   # w_para
true,false,false,false      # sch (스케줄러 선택)
0.1                         # 선택(7행): r_penalty — R 감쇠 (기본 0.1)
2.0                         # 선택(8행): priority_base — P=1/base^j 의 밑 (기본 2.0)
3                           # 선택(9행): queue_prefix_mult — 재정렬 창=서버수×배수 (기본 3)
```
7~9행은 민감도 스윕용. 생략 시 `global_const` 기본값 사용.

### 출력 데이터

- `*.csv`: 할당률, 사용률 지표
- `.meta`: 메타데이터
- `.log`: 상세 로그

### 메모리 관리

- 동적 할당 사용: `new[]`, `delete[]`, `unique_ptr`
- `job_queue`: 시간 슬롯 기반 동적 배열
- MCTS 노드: `unique_ptr`로 자동 관리

### 플랫폼 호환성

```cpp
#ifdef _WIN32
  localtime_s(&local_tm, &time);  // Windows
#else
  localtime_r(&time, &local_tm);  // Linux/POSIX
#endif
```

| 플랫폼 | 빌드 도구 | GUI 지원 |
|--------|----------|---------|
| Linux | Makefile + g++ | X |
| Windows | Visual Studio | O (MFC) |

---

## ② K8S 실측 계층

```
트레이스 ─▶ k8s_replay/ ─▶ Job YAML(holder 스텁) ─▶ kind 클러스터(B200×8)
                                                        │
            squad_ctrl/policy_controller.py ◀───────────┤ PodSchedulingGates
            (정책 순서 결정 → ungate)                     │ (실제 kube-scheduler가 배치)
                                                        ▼
            metrics_collector.py / analyze.py ─▶ results/, /raid/squad/runs/
```

- **`squad_ctrl/`** (실사용 경로): `policy_controller.py`(정책: fifo/sjf/priority/las/sfqa/
  sfqa-auto/easy, gate 해제 순서로 정책 구현), `squad_algo.py`(SFQA 논문 Algorithm 1),
  `run_experiment.py`(샘플링·Kueue·추정노이즈), `run_one.sh`/`chain_*.sh`(캠페인 러너),
  `measure_overheads.py`(수명주기·체크포인트 실측), `analyze.py`(집계).
- **`k8s/`** (Go 포팅판): `pkg/squad`(SFQA/PTR 알고리즘, 테스트 6/6), `pkg/queuesort`
  (kube-scheduler QueueSort 플러그인), `cmd/{scheduler,sfqa-controller,ptr-controller}`,
  `deploy/`(매니페스트). 클러스터 내 Go 빌드가 막힐 경우의 대안이었으나 현재는 Python 경로 사용.
- **`k8s_replay/`**: 트레이스 수집(`ingest.py`: Philly·Alibaba·사내) → 정규화 → flavor 매핑
  (`model_assign.py`) → 시간 압축 → Job 생성(`emit.py`). `holder_img/`: scratch 기반 Go
  GPU-holder 스텁(GPU 점유만, 연산은 sleep).

## ③ Python 이산사건 시뮬레이터 (`sim/`)

```
engine.py (이산사건, SoA·numpy 벡터화, 타입계수·오버헤드 주입)
  ├── policies.py     : fifo/sjf/las/kueue/easy/themis/sfqa/sfqa-auto (인덱스 기반)
  ├── lucid_sim.py    : Lucid(ASPLOS'23) 충실 구현 — collocation
  ├── sia_sim.py      : Sia(SOSP'23) 충실 구현 — goodput ILP (계산비용 큼)
  ├── order_fairness.py / fairness.py : 순서공정성(역전수) 지표
  ├── run_all.py / run_parallel.py / run_sim.py : 러너
  ├── analyze_sweep.py / plot_*.py : 부하곡선·trade-off 분석
  └── trace_to_cpp.py : Philly → C++ 시뮬 입력 변환 (계층 ① 연동)
```

- 실측(②)에서 보정한 오버헤드를 주입, ±15% 정합 목표(`docs/SIMULATOR_DESIGN.md`).
- 부하 스윕 결과: `sim/sweep_results/` (FINDINGS.md, sweep_table.csv, 그래프, raw 아카이브).
  raw 압축 해제본은 `sim/sweep_results/raw/`(gitignore — tar.gz에서 복원 가능).

## 결과물 (`results/`)

| 위치 | 내용 |
|---|---|
| `SUMMARY.md`, `runs_summary.csv`, `tables.md` | K8S 실측 캠페인 집계 |
| `../sim/sweep_results/` | ③ 부하 스윕 (256/512/1024 × 단일/이종 × 10정책) + raw 아카이브 |
| `overheads/` | 수명주기·체크포인트 실측 → 시뮬 주입 파라미터 |
| `philly_*.csv` | 재현용 층화 샘플 (명명 규칙: `<트레이스>-<샘플수>-C<절단h>`) |
| 서버 `/raid/squad/` | 원본 run 데이터 (저장소 외부) |
