# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 개요

이종(heterogeneous) 멀티 가속기 클러스터에서 GPU 작업 스케줄링 알고리즘을 벤치마킹하는 C++20 이산 시간(discrete-time) 시뮬레이터다. 학술적으로는 **SQUAD**(Scheduling Queue Unblocking and Allocation Defragmentation)로 불린다 — 제출 논문과 리뷰어 피드백은 `reject/`, 현재 진행 중인 재실험 설계(K8S + H100/B200 실측)는 `docs/REEXPERIMENT_PLAN.md` 참고. 이 저장소는 연구 산출물 역할도 겸하여 소스, 실측/합성 작업 트레이스, 파라미터 스윕 설정, Jupyter 분석 노트북이 함께 들어 있다.

## 빌드 & 실행

```bash
make              # ./experiment_gpu 빌드 (Linux, g++ -std=c++20)
make rebuild      # clean + build
make clean

./experiment_gpu <task_file.csv> <server_file.csv> <config.set>
# 예: ./experiment_gpu "job_flow_total(task,flavor,single)_neo_no_duplicate.csv" server.csv config.set
```

자동화된 테스트 스위트는 없다. 검증은 실험을 실행한 뒤 `.result` / `.result.meta` 출력물을 분석 노트북(`analysis_results/analysis.ipynb`, `analysis_results/Wating_Time.ipynb`)에서 확인하는 방식이다.

동일한 C++ 코어가 **Windows MFC GUI**(`gpu_scheduer.sln`)로도 컴파일된다. `linux_main.cpp`가 헤드리스 CLI 진입점이고, GUI 파일들(`gpu_scheduerView.cpp`, `*Dialog.cpp`, `MainFrm.cpp` 등)은 Windows 전용이다. 스케줄러/에뮬레이터 로직을 수정할 때는 플랫폼 종속·MFC 의존성이 섞이지 않도록 해서 양쪽 프론트엔드가 모두 빌드되게 유지해야 한다.

## config.set 포맷

6줄로 하이퍼파라미터 그리드 스윕을 정의한다(`linux_main.cpp::parse_config_file`에서 파싱):

```
<thread_total>
<alpha_start>,<alpha_end>,<alpha_step>     # α  age_weight        (SFQA)
<beta_start>,<beta_end>,<beta_step>        # β  svp_upper          (SFQA 발동 임계치)
<d_start>,<d_end>,<d_step>                 # δ  reorder_count      (PTR DP 재귀 상한)
<w_start>,<w_end>,<w_step>                 # ω  preemption_task_window (PTR)
mostallocated,compact,round_robin,mcts     # true/false: 스윕할 스케줄러 선택
```

`build_hyperparameter()`가 이 범위들을 전체 `scheduler_option` 탐색 공간으로 펼치고, `experiment_perform`이 이를 `thread_total`개의 워커 스레드에 나눠 실행한다.

## 아키텍처

시뮬레이션은 3개 계층으로 구성되며, 이들의 관계를 이해하는 것이 이 코드베이스의 핵심이다:

1. **`experiment_perform`** — 최상위 오케스트레이터. `job_emulator` 인스턴스 풀을 소유하고, 하이퍼파라미터 탐색 공간을 N개 스레드로 분할하여 각 파라미터 조합을 독립된 에뮬레이션 하나로 실행하고, 스레드 콜백으로 결과를 집계한다.

2. **`job_emulator`** — 단일 실험을 실행한다. 작업 트레이스 + 서버 토폴로지를 로드하고, 이산 `emulation_step` 클럭을 전진시키며, 매 스텝마다 활성 스케줄러를 호출하고, 실행 중 작업을 갱신하고, 할당/이용률 통계를 추적하고, 선택적으로 디프래그멘테이션을 트리거한다. 대기 큐(`wait_queue_group`, `wait_queue_age`)를 소유하며 모든 결과 파일을 기록한다. 시뮬레이션 루프가 여기 있다(`computing_forward`, `update_wait_queue`, `check_defragmentation_condition`).

3. **`job_scheduler`**(추상 베이스) — 단일 배치 결정. 서브클래스가 `arrange_server(job, queue_index, coprocessor)`를 구현한다:
   - `scheduler_mostallocated` — 가장 바쁜 서버에 빈 패킹
   - `scheduler_compact` — 단편화 최소화
   - `scheduler_round_robin` — 균등 분산
   - `scheduler_mcts` — Monte Carlo Tree Search 기반 배치
   - `scheduler_fare_share` — 페어 셰어 균형

   `scheduler_type` enum 순서는 `{mostallocated, compact, round_robin, mcts, fare_share}` — 앞 4개가 config 6번째 줄의 boolean에 대응한다.

**SQUAD의 두 가지 기여는 위 코어 스케줄러와 독립적인 전처리 계층이다:**
- **SFQA**(Starvation-Free Queue Adjustment) — α(나이 가중치)와 β(발동 임계치)를 사용해 *대기(pending)* 큐를 재정렬. 대기 중인 작업만 건드린다.
- **PTR / 디프래그멘테이션**(`adjusting_server`) — 실행 중인 preemptive 작업을 이주시켜 완전히 빈 서버 수를 최대화하며, δ로 상한을 둔 DP로 제한된다. 실행 중인 작업을 옮기는 유일한 메커니즘이다.

보조 타입: `job_entry`(작업 1개), `server_entry`(서버 1대의 가속기 상태), `coprocessor_server`, `accelator_type` enum(`v100, a30, a100, h100, h200, l4, l40, b200`), `global_structure::scheduler_option`(`global_definistion.h`에 정의된 실험별 노브 묶음).

## 컨벤션 & 주의사항

- **소스는 `gpu_scheduer/`에 있다**(주의: `l`이 빠진 오타). 이 디렉터리명을 포함해 여러 식별자에 박혀 있는 오타가 사실상 공개 API의 일부이므로 "고치지" 말고 그대로 맞춰 써야 한다: `scheduler_fare_share` / `fare_share`, `global_definistion.h`, `using_preemetion`, `scheduleing_with_flavor_option`, `complated_experiment`, `defragmentaion_criteria`, `accelator_type`.
- 튜닝 기본값은 `enum_definition.h`의 `global_const` 네임스페이스에 있다(starvation 임계치, age weight, DP 상한, defrag 기준).
- Makefile의 `HEADERS`/`SOURCES` 목록은 명시적이다 — `gpu_scheduer/`에 `.cpp`/`.h`를 추가하면 Makefile에(그리고 Windows에서도 빌드해야 하면 `.vcxproj`에도) 등록해야 링크된다.
- 루트와 `Task log Backup/`의 수많은 `.csv`는 작업 트레이스(`job_id, submit_time, duration, gpu_count, gpu_type, ...`)이고, `server*.csv`는 클러스터 토폴로지(`server_name, accelerator_count, gpu_type`)다. `experiments_set/`에는 생성된 분포 스윕(`co_<dist1>_<dist2>_gen.csv`)이 들어 있다.
