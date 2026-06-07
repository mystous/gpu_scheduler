# 빌드 및 실행 가이드

## 요구사항

### Linux

- g++ (C++20 지원)
- make

### Windows

- Visual Studio 2019 이상
- MFC 라이브러리

---

## Linux 빌드

### 방법 1: gpu_scheduer 디렉토리에서 빌드

```bash
cd gpu_scheduer
make clean
make
```

**생성 파일:** `gpu_schduler_emul`

### 방법 2: 최상위 디렉토리에서 빌드

```bash
make clean
make
```

**생성 파일:** `experiment_gpu`

### Makefile 설정

```makefile
CXX = g++
CXXFLAGS = -Wall -std=c++20

SRCS = call_back_object.cpp \
       coprocessor_server.cpp \
       job_emulator.cpp \
       job_entry.cpp \
       job_scheduler.cpp \
       linux_main.cpp \
       scheduler_compact.cpp \
       scheduler_fare_share.cpp \
       scheduler_mcts.cpp \
       scheduler_mostallocated.cpp \
       scheduler_round_robin.cpp \
       server_entry.cpp \
       utility_class.cpp
```

---

## Windows 빌드

### Visual Studio 사용

1. `gpu_scheduer.sln` 파일 열기
2. 솔루션 빌드 (Ctrl+Shift+B)

---

## 실행 방법

### 기본 실행

```bash
./gpu_schduler_emul <task_file> <server_file> <config_file>
```

### 예시

```bash
./gpu_schduler_emul ../job_flow_total.csv ../server.csv config.txt
```

또는

```bash
./experiment_gpu job_flow_total.csv server.csv config.txt
```

---

## 입력 파일 형식

### 작업 데이터 (job_flow_total.csv)

```csv
pod_name,pod_type,project,namespace,user_team,start_time,finish_time,accelerator_count,computing_level,gpu_utilization,accelerator_flavor,preemption
run-pipeline-gpu-9fg4g-4198045470,task,PROJECT_13,ns-16904409679649498,TEAM_1,2023-11-08 12:15:00+00:00,2023-12-16 00:45:00+00:00,4,37 days 12:30:00,5,97.46,A100,y
```

**필드 설명:**

| 필드 | 설명 |
|-----|------|
| pod_name | 작업 식별자 |
| pod_type | 작업 유형 (task, service 등) |
| project | 프로젝트 이름 |
| namespace | 네임스페이스 |
| user_team | 사용자 팀 |
| start_time | 시작 시간 |
| finish_time | 종료 시간 |
| accelerator_count | 필요한 GPU 개수 |
| computing_level | 계산 부하 |
| gpu_utilization | GPU 사용률 (%) |
| accelerator_flavor | GPU 종류 (A100, A30 등) |
| preemption | 선점 가능 여부 (y/n) |

### 서버 데이터 (server.csv)

```csv
server_name,accelerator_count,accelerator_type
gpu_serverA1,8,a100
gpu_serverA2,8,a100
gpu_serverB3,4,a30
```

**필드 설명:**

| 필드 | 설명 |
|-----|------|
| server_name | 서버 이름 |
| accelerator_count | 서버의 GPU 개수 |
| accelerator_type | GPU 종류 |

### 설정 파일 (config.txt)

```
4                           # thread_total
0.13889,0.83889,0.1         # alpha_para (min,max,step)
70.0,95.0,5.0               # beta_para (min,max,step)
100000,1000000,100000       # d_para (min,max,step)
20,100,10                   # w_para (min,max,step)
true,false,false,false      # sch (scheduler selection)
```

**파라미터 설명:**

| 파라미터 | 설명 |
|---------|------|
| thread_total | 실험에 사용할 스레드 수 |
| alpha_para | 나이 가중치 범위 |
| beta_para | 기아 방지 임계값 범위 |
| d_para | DP 최대 반복 횟수 범위 |
| w_para | 선점 작업 윈도우 범위 |
| sch | 스케줄러 선택 [MostAlloc, Compact, RoundRobin, MCTS] |

---

## 출력

### 콘솔 출력

```
[실험 시작]
스레드 수: 4
하이퍼파라미터 조합: 1680개

[진행 상황]
Thread 0: 10/420 완료
Thread 1: 8/420 완료
...

[결과]
최적 파라미터: alpha=0.2, beta=80, d=500000, w=40
할당률: 95.2%
사용률: 87.3%
```

### 파일 출력

- `result/*.csv`: 각 실험 결과
- `result/*.meta`: 실험 메타데이터
- `result/*.log`: 상세 로그

---

## 문제 해결

### 빌드 오류

**오류:** `g++: error: unrecognized command line option '-std=c++20'`

**해결:** g++ 버전 10 이상 필요
```bash
sudo apt install g++-10
export CXX=g++-10
```

### 실행 오류

**오류:** `파일을 찾을 수 없습니다`

**해결:** 상대 경로 확인 및 절대 경로 사용

```bash
./gpu_schduler_emul /full/path/to/job.csv /full/path/to/server.csv config.txt
```

---

## 알려진 제한사항

1. **Linux 선점 기능**: 현재 Linux에서 작업 선점이 제대로 작동하지 않음
2. **FareShare**: 구현 미완료
3. **대용량 데이터**: 매우 큰 작업 파일 처리 시 메모리 사용량 주의
