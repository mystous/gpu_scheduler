# 코드 이슈 및 개선 필요 사항

## 목차

1. [버그 및 잠재적 버그](#1-버그-및-잠재적-버그)
2. [미완료 구현](#2-미완료-구현)
3. [코드 품질 문제](#3-코드-품질-문제)
4. [설계 문제](#4-설계-문제)
5. [에러 처리](#5-에러-처리)
6. [테스트 관련](#6-테스트-관련)
7. [문서화](#7-문서화)
8. [기타 발견사항](#8-기타-발견사항)
9. [권장 개선사항](#9-권장-개선사항)

---

## 1. 버그 및 잠재적 버그

### 1.1 메모리 누수 문제 (Critical)

#### CWaitCursor 객체 누수

**파일:** `gpu_scheduer/experiment_perform.cpp:70-72`
```cpp
CWaitCursor* wait = new CWaitCursor();
// 사용 후 delete 없음
```

**동일 패턴 발견 위치:**
- `gpu_scheduerDoc.cpp:255`
- `MainFrm.cpp:189, 191, 211`

#### 동적 배열 누수 가능성

**파일:** `gpu_scheduer/job_emulator.cpp:577-578`
```cpp
allocation_rate = new double[memory_alloc_size];
utilization_rate = new double[memory_alloc_size];
// reallocation_log_memory()에서만 delete, 다른 경로에서는 누수 가능
```

#### 스케줄러 객체 누수

**파일:** `gpu_scheduer/job_emulator.cpp:129, 267-284`
```cpp
server_control = new adjusting_server(&server_list, dp_execution_maximum);
scheduler_obj = new scheduler_compact();
// 이전 scheduler_obj가 모든 경로에서 제대로 삭제되는가?
```

### 1.2 nullptr 역참조 위험

#### get_job_entry() 반환값 미검사

**파일:** `gpu_scheduer/adjusting_server.cpp:129-136`
```cpp
job_entry* adjusting_server::get_job_entry(string job_id, vector<job_entry*> job_list) {
    for (auto&& job : job_list) {
        if (job->get_job_id() == job_id) {
            return job;
        }
    }
    return nullptr;  // 호출자가 검사하지 않음
}
```

**문제 코드:** `adjusting_server.cpp:112-114`
```cpp
job = get_job_entry(...);
// 라인 114에서 job->is_preemtion_possible() 호출 - nullptr 역참조 가능
```

#### wait_queue_group nullptr 미검사

**파일:** `gpu_scheduer/job_emulator.cpp:494-495`
```cpp
wait_queue_group[queue_index]->push(job);
queue<job_entry*> shadow_queue = *wait_queue_group[queue_index];
// wait_queue_group이 nullptr인지 확인 없음
```

### 1.3 경계 조건 미처리

#### 음수 인덱싱 가능성

**파일:** `gpu_scheduer/job_emulator.cpp:439`
```cpp
resource_suitability_index[wait_queue[j].job->get_accelerator_count()-1];
// accelerator_count가 0인 경우 -1 인덱싱 발생
```

#### 배열 범위 초과 가능성

**파일:** `gpu_scheduer/job_emulator.cpp:243-244`
```cpp
auto startDiff = duration_cast<std::chrono::minutes>(job->get_start_tp() - min_start_time);
job_queue[startDiff.count()].job_list_in_slot.push_back(job);
// startDiff.count()가 total_time_slot 범위를 벗어날 수 있음
```

### 1.4 동시성 문제

#### 전역 변수 스레드 안전성

**파일:** `gpu_scheduer/linux_main.cpp:15-20`
```cpp
int thread_total = 4;
double alpha_para[3] = { 0.13889, 0.83889, 0.1 };
vector<global_structure::scheduler_option> hyperparameter_searchspace;
// 여러 스레드에서 접근 가능하지만 동기화 메커니즘 없음
```

#### 정적 변수 경쟁 조건

**파일:** `gpu_scheduer/job_entry.cpp:7-8`
```cpp
unsigned int job_entry::random_id_pre = 0;
unsigned int job_entry::random_id_post = 0;
// get_sequencial_id()에서 동시성 문제 가능
```

#### detach() 후 스레드 관리

**파일:** `gpu_scheduer/job_emulator.cpp:631`
```cpp
emulation_player.detach();  // 스레드가 종료되지 않고 분리됨
return id;  // 스레드 종료 시점 불명확
```

---

## 2. 미완료 구현

### 2.1 스텁 구현 (Critical)

#### FareShare 스케줄러 미구현

**파일:** `gpu_scheduer/scheduler_fare_share.cpp:4-5`
```cpp
int scheduler_fare_share::arrange_server(job_entry& job, int queue_index,
                                         accelator_type coprocessor) {
    return 0;  // 실제 구현 없음! 이 스케줄러는 작동하지 않음
}
```

### 2.2 TODO 주석 목록

#### 핵심 TODO

**파일:** `gpu_scheduer/scheduler_mcts.cpp:39`
```cpp
// TODO : 20 is a magic number. It has to be changed into reasonable number
// or finding exit condition this loop
for (int i = 0; i < min(20*(max_job_count + 1), ...) {
```

#### Windows MFC 자동 생성 TODO

| 파일 | 라인 | 내용 |
|-----|-----|------|
| `experiment_dialog.cpp` | 68 | "여기에 특수화된 코드를 추가" |
| `CSchedulerOption.cpp` | 58 | "Add extra initialization here" |
| `ChildFrm.cpp` | 28 | "add member initialization code here" |
| `MainFrm.cpp` | 49 | "add member initialization code here" |

### 2.3 빈 파일

**파일:** `gpu_scheduer/coprocessor_server.cpp`
- 파일이 거의 비어있음 (include만 있고 구현 없음)

---

## 3. 코드 품질 문제

### 3.1 매직 넘버

| 파일 | 라인 | 코드 | 문제 |
|-----|-----|------|------|
| `job_emulator.cpp` | 417 | `const int accelerator_count = 8;` | 하드코딩된 상수 |
| `job_emulator.cpp` | 424 | `0.1` | 설명 없는 계수 |
| `job_emulator.cpp` | 603 | `set_emulation_play_priod(0.1);` | 설명 없는 값 |
| `log_generator.cpp` | 32 | `set_whole_walltime(180);` | "Temporary" 주석 |
| `job_entry.h` | 52 | `digit_pre = 1001, digit_post = 501;` | 설명 없음 |

### 3.2 오타 목록 (전역)

| 잘못된 철자 | 올바른 철자 | 발견 위치 |
|-----------|-----------|----------|
| `global_definistion` | `global_definition` | 파일명 |
| `computaion_load` | `computation_load` | `job_entry.h:60` |
| `preemtion` | `preemption` | 전역 (50+ 위치) |
| `accelator` | `accelerator` | 전역 (100+ 위치) |
| `flaver` | `flavor` | `log_generator.h:34` |
| `preemetion` | `preemption` | `log_generator.h:51` |
| `finialize` | `finalize` | `log_generator.cpp:26, 53` |
| `get_name_sapce()` | `get_name_space()` | `job_entry.h:25` |
| `avaliable` | `available` | 다수 위치 |
| `suitablitiy` | `suitability` | `job_emulator.cpp` |

### 3.3 중복 코드

**파일:** `gpu_scheduer/job_emulator.cpp:452-477`
```cpp
// shadow_queue를 두 번 순회하는 중복 로직
queue<job_entry*> shadow_queue = *wait_queue_group[i];
// 첫 번째 순회...
shadow_queue = *wait_queue_group[i];  // 다시 복사
// 두 번째 순회...
```

**파일:** `gpu_scheduer/log_generator.cpp:208-313`
- 8가지 분포 타입에 대해 거의 동일한 코드 반복 (DRY 원칙 위반)

### 3.4 일관성 없는 명명

```cpp
// get 접두사 유무 불일치
avaliable_accelator_count()     // get 없음
get_avaliable_accelator_count() // get 있음

// 포인터 선언 스타일 불일치
CWaitCursor *wait   // 변수 쪽
CWaitCursor* wait   // 타입 쪽
```

---

## 4. 설계 문제

### 4.1 Raw 포인터 과다 사용

**파일:** `gpu_scheduer/job_emulator.h`
```cpp
job_entry_struct* job_queue = nullptr;
double* allocation_rate = nullptr;
double* utilization_rate = nullptr;
vector<double*> server_utilization_rate;
vector<int*> server_allocation_count;
```

**권장:** `std::unique_ptr<>` 또는 `std::vector<>` 사용

### 4.2 과도한 복잡성

| 파일 | 함수 | 라인 수 | 문제 |
|-----|-----|--------|------|
| `adjusting_server.cpp` | `reconstruct_server_status()` | 80줄 | 중첩 루프, 복잡한 조건문 |
| `scheduler_mcts.cpp` | MCTS 시뮬레이션 | 60줄 | 이해하기 어려운 로직 |

### 4.3 Single Responsibility Principle 위반

**클래스:** `job_emulator` (178줄 헤더)
- 작업 큐 관리
- 서버 상태 추적
- 스케줄링 실행
- 결과 저장
- 통계 계산

**권장:** 책임 분리

### 4.4 성능 이슈

**O(n²) 복잡도**

**파일:** `gpu_scheduer/job_emulator.cpp:456-473`
```cpp
// 큐의 순서를 재정렬하기 위해 큐를 여러 번 순회
```

**무한 루프 위험**

**파일:** `gpu_scheduer/log_generator.cpp:280-289`
```cpp
while(1) {  // 분포 생성에서 무한 루프 위험
    // ...
}
```

---

## 5. 에러 처리

### 5.1 예외 처리 부족

**빈 catch 블록**

**파일:** `gpu_scheduerView.cpp:194`
```cpp
catch (...) {}  // 모든 예외를 무시함!
```

**예외 처리 누락**

**파일:** `job_emulator.cpp:142-189`
```cpp
computation_level = stoi(tokens[9]);
// stoi() 실패 시 예외 발생하지만 처리하지 않음
```

### 5.2 반환값 무시

**파일 작업**

```cpp
file.close();  // close() 실패 가능하지만 반환값 무시
```

**파일:** `log_generator.cpp:70-72`
```cpp
ofstream file(generated_filename);
if (!file.is_open()) { return false; }
// file 쓰기 실패는 확인하지 않음
```

### 5.3 입력 검증 부족

**파일:** `linux_main.cpp:166-169`
```cpp
if (argc < 4) {
    cerr << "Usage: ..." << endl;
    return 1;
}
// 파일 존재 여부 확인 없음
```

---

## 6. 테스트 관련

### 6.1 테스트 코드 부재

- 단위 테스트 디렉토리 없음
- 테스트 파일 없음
- 모든 기능이 통합 테스트에만 의존

### 6.2 테스트 불가능한 코드

- `scheduler_fare_share.cpp`: 구현되지 않아 테스트 불가
- `scheduler_mcts.cpp`: 복잡한 로직을 검증하는 테스트 없음

---

## 7. 문서화

### 7.1 주석 부족

**주석이 거의 없는 핵심 함수들:**

| 파일 | 함수 | 라인 수 | 상태 |
|-----|-----|--------|------|
| `adjusting_server.cpp` | `reconstruct_server_status()` | 80줄 | 주석 없음 |
| `adjusting_server.cpp` | `get_optimal_adjusting_dp()` | 복잡 | 설명 부족 |
| `scheduler_mcts.cpp` | MCTS 구현 전체 | - | 알고리즘 설명 없음 |
| `job_emulator.cpp` | 상태 관리 로직 | - | 주석 부족 |

### 7.2 API 문서 부재

**현재 코드:**
```cpp
int arrange_server(job_entry& job, int queue_index = 0,
                   accelator_type coprocessor = accelator_type::any);
```

**권장 형식:**
```cpp
/// @brief Arrange GPU resource for a job
/// @param job The job to schedule
/// @param queue_index Index of the wait queue
/// @param coprocessor Type of accelerator required
/// @return Server index assigned to the job, or -1 if no suitable server found
int arrange_server(...);
```

---

## 8. 기타 발견사항

### 8.1 플랫폼 비호환성

**Windows 전용 API 사용:**
```cpp
// log_generator.cpp:103 (Windows 전용)
localtime_s(&localTime, &currentTime);  // MSVC specific

// Linux에서는:
localtime_r(&currentTime, &localTime);  // POSIX
```

### 8.2 사용되지 않는 코드

| 파일 | 라인 | 내용 |
|-----|-----|------|
| `experiment_dialog.h` | 29-32 | 주석 처리된 파라미터 범위 |
| `job_emulator.cpp` | 797-805 | 주석 처리된 stringstream 코드 |

### 8.3 비ASCII 문자

**파일:** `scheduler_mcts.cpp:59`
```cpp
// 한국어 주석 포함 - 인코딩 문제 가능성
```

---

## 9. 권장 개선사항

### 우선순위: 긴급 (1주)

- [ ] `scheduler_fare_share.cpp` 구현 완료
- [ ] 메모리 누수 수정
  - CWaitCursor 삭제
  - job_queue, allocation_rate 등 삭제 경로 확인
- [ ] nullptr 체크 추가
  - `adjusting_server::get_job_entry()` 반환값 검사

### 우선순위: 높음 (2주)

- [ ] 스레드 안전성 개선
  - 전역 변수에 뮤텍스 추가
  - 정적 변수 접근 동기화
- [ ] 배열 경계 검사 강화
  - accelerator_count 0 체크
  - job_queue 인덱스 범위 검증
- [ ] 단위 테스트 작성 시작
  - 스케줄러 알고리즘 테스트
  - job_entry 클래스 테스트

### 우선순위: 중간 (1개월)

- [ ] 전역 오타 수정
  - `preemtion` → `preemption`
  - `accelator` → `accelerator`
  - `avaliable` → `available`
- [ ] 복잡한 함수 리팩토링
  - `reconstruct_server_status()` 분할
  - MCTS 시뮬레이션 로직 정리
- [ ] Doxygen 주석 추가
- [ ] 매직 넘버를 상수로 변환

### 우선순위: 낮음 (지속적)

- [ ] 코드 스타일 일관성 확보
- [ ] 스마트 포인터로 전환
- [ ] 에러 처리 강화

---

## 심각도 요약

| 심각도 | 개수 | 주요 항목 |
|--------|------|----------|
| **Critical** | 5+ | 메모리 누수, nullptr 역참조, FareShare 미구현 |
| **High** | 10+ | 스레드 안전성, 경계 조건, 테스트 부재 |
| **Medium** | 20+ | 매직 넘버, 오타, 문서화 부족 |
| **Low** | 30+ | 코드 스타일, 중복 코드 |
