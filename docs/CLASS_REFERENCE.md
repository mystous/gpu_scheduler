# 클래스 참조

## 핵심 클래스

---

### job_entry

작업(Job)을 나타내는 클래스

**파일:** `job_entry.h`, `job_entry.cpp`

#### 멤버 변수

```cpp
string pod_name;                              // 작업 이름
string project_name;                          // 프로젝트
string user_team;                             // 사용자 팀
string name_space;                            // 네임스페이스
int accelerator_count;                        // 필요한 GPU 개수
int computaion_load;                          // 계산 부하
double utilization;                           // GPU 사용률
accelator_type accelator_flavor;              // GPU 종류
bool preemtion_possible;                      // 선점 가능 여부
duration<double, ratio<60>> wall_time_min;    // 실행 시간 (분)
vector<int> assigned_accelerator;             // 할당된 GPU 위치
```

#### 주요 메서드

| 메서드 | 설명 |
|-------|------|
| `assign_accelerator(positions)` | GPU 할당 기록 |
| `ticktok()` | 시간 진행 (실행 시간 감소) |
| `flush()` | 작업 완료 후 GPU 해제 |
| `get_accelerator_count()` | 필요한 GPU 개수 반환 |
| `get_wall_time_min()` | 남은 실행 시간 반환 |

---

### server_entry

서버를 나타내는 클래스

**파일:** `server_entry.h`, `server_entry.cpp`

#### 멤버 변수

```cpp
int accelator_count;                    // 서버의 총 GPU 개수
string server_name;                     // 서버 이름
accelator_type coprocessor_type;        // GPU 타입
vector<bool> reserved;                  // GPU 예약 상태
vector<string> job_id_for_reserved;     // 각 GPU 담당 작업
vector<double> utilization_list;        // 각 GPU 사용률
vector<job_entry*> job_list;            // 실행 중인 작업 리스트
```

#### 주요 메서드

| 메서드 | 설명 |
|-------|------|
| `assign_accelator(job, count)` | 작업에 GPU 할당 |
| `get_avaliable_accelator_count()` | 사용 가능한 GPU 개수 |
| `remove_job(job)` | 작업 완료 후 제거 |
| `ticktok()` | 모든 작업의 시간 진행 |
| `flush()` | 완료된 작업 정리 |

---

### job_scheduler (추상 클래스)

스케줄러 기반 클래스

**파일:** `job_scheduler.h`

#### 멤버 변수

```cpp
vector<server_entry>* target_server;              // 서버 리스트
vector<queue<job_entry*>*>* wait_queue_group;     // 대기열 그룹
vector<vector<job_age_struct>>* wait_queue_age;   // 작업 나이 추적
vector<job_age_struct>* scheduled_history;        // 스케줄링 이력
bool preemtion_enabling;                          // 선점 활성화
bool scheduling_with_flavor;                      // GPU 타입별 스케줄링
bool perform_until_finish;                        // 완료까지 실행
```

#### 주요 메서드

| 메서드 | 설명 |
|-------|------|
| `arrange_server(job, queue_index, type)` | 순수 가상 함수 - 서버 선택 |
| `scheduling_job()` | 대기 큐에서 작업 스케줄링 |
| `set_server(server_list)` | 서버 리스트 설정 |

---

### job_emulator

시뮬레이션 엔진

**파일:** `job_emulator.h`, `job_emulator.cpp`

#### 멤버 변수

```cpp
vector<job_entry> job_list;                       // 작업 리스트
vector<server_entry> server_list;                 // 서버 리스트
job_entry_struct* job_queue;                      // 시간 슬롯별 작업
vector<queue<job_entry*>*> wait_queue_group;      // 대기열 그룹
vector<vector<job_age_struct>> wait_queue_age;    // 작업 나이
scheduler_type selected_scheduler;                // 선택된 스케줄러
job_scheduler* scheduler_obj;                     // 스케줄러 객체
adjusting_server* server_control;                 // 조각화 관리
```

#### 주요 메서드

| 메서드 | 설명 |
|-------|------|
| `build_job_list(filename)` | CSV에서 작업 로드 |
| `build_server_list(filename)` | CSV에서 서버 로드 |
| `build_job_queue()` | 시간 슬롯 기반 작업 큐 구성 |
| `step_foward()` | 시뮬레이션 한 스텝 진행 |
| `start_progress()` | 별도 스레드에서 시뮬레이션 |
| `initialize_job_state()` | 작업 상태 초기화 |
| `initialize_server_state()` | 서버 상태 초기화 |

---

### experiment_perform

실험 관리자

**파일:** `experiment_perform.h`, `experiment_perform.cpp`

#### 내부 구조체

```cpp
struct thread_data {
    job_emulator* emulator;
    int option_index;
    int handling_opt_count;
    int experiment_done;
};

struct thread_meta {
    thread::id thread_id;
    int current_option;
    int total_options;
    bool finished;
};
```

#### 멤버 변수

```cpp
vector<job_emulator*> emulator_vector;
vector<global_structure::scheduler_options>* hyperparameter;
unordered_map<thread::id, thread_meta*> thread_map;
int thread_count;
```

#### 주요 메서드

| 메서드 | 설명 |
|-------|------|
| `set_thread_count(count)` | 스레드 수 설정 |
| `set_hyperparameter(params)` | 하이퍼파라미터 설정 |
| `start_experiment()` | 실험 시작 |
| `wait_for_completion()` | 모든 실험 완료 대기 |

---

### adjusting_server

GPU 조각화 제거

**파일:** `adjusting_server.h`, `adjusting_server.cpp`

#### 내부 구조체

```cpp
struct server_status_for_dp {
    gpu_allocation_type status;   // empty, fixed, floating, adjusted
    string job_id;
};

typedef vector<vector<server_status_for_dp>> server_map;
```

#### 멤버 변수

```cpp
server_map* server_status;
unordered_map<string, int> memoization_cache;
vector<server_entry>* target_servers;
```

#### 주요 메서드

| 메서드 | 설명 |
|-------|------|
| `set_servers(servers)` | 서버 리스트 설정 |
| `defragementation()` | 조각화 제거 실행 |
| `calculate_empty_servers()` | 빈 서버 개수 계산 |
| `apply_adjustment()` | 조정 결과 적용 |

---

## 열거형

### accelator_type

```cpp
enum class accelator_type : int {
    any,      // 무관
    cpu,      // CPU only
    v100,     // NVIDIA V100
    a30,      // NVIDIA A30
    a100,     // NVIDIA A100
    h100,     // NVIDIA H100
    h200,     // NVIDIA H200
    l4,       // NVIDIA L4
    l40,      // NVIDIA L40
    b200      // NVIDIA B200
};
```

### scheduler_type

```cpp
enum class scheduler_type : int {
    mostallocated = 0,
    compact,
    round_robin,
    mcts,
    fare_share
};
```

### gpu_allocation_type

```cpp
enum class gpu_allocation_type : int {
    none,       // 미정
    empty,      // 비어있음
    fixed,      // 고정 (이동 불가)
    floating,   // 유동 (이동 가능)
    adjusted    // 조정됨
};
```

### emulation_status

```cpp
enum class emulation_status : int {
    stop,    // 정지
    pause,   // 일시정지
    start    // 실행 중
};
```

---

## 유틸리티 클래스

### utility_class

**파일:** `utility_class.h`, `utility_class.cpp`

#### 정적 메서드

| 메서드 | 설명 |
|-------|------|
| `parse_time_string(str)` | 문자열을 time_point로 변환 |
| `conver_tp_str(tp)` | time_point를 문자열로 변환 |
| `get_accelerator_name(type)` | 열거형을 문자열로 변환 |
| `format_duration(duration)` | 시간을 형식화된 문자열로 |

---

## 설정 구조체

### scheduler_option

```cpp
struct scheduler_option {
    scheduler_type scheduler_index;         // 사용할 스케줄러
    bool using_preemetion;                  // 선점 활성화
    bool scheduleing_with_flavor_option;    // GPU 타입별 스케줄링
    bool working_till_end;                  // 완료까지 실행
    bool prevent_starvation;                // 기아 방지
    double svp_upper = 80.0;                // 기아 방지 임계값
    double age_weight = 0.13889;            // 나이 가중치
    int reorder_count = 100000;             // DP 최대 반복
    int preemption_task_window = 20;        // 조각화 제거 주기
};
```

### job_age_struct

```cpp
struct job_age_struct {
    int age;                  // 현재 대기 시간
    int accumulated_age;      // 누적 대기 시간
    job_entry* job;           // 작업 포인터
    double repriority_score;  // 재우선순위 점수
};
```
