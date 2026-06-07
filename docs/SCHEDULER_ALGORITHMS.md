# 스케줄러 알고리즘 상세

## 개요

이 프로젝트는 5가지 스케줄링 알고리즘을 구현하여 GPU 클러스터 환경에서의 성능을 비교합니다.

---

## 1. MostAllocated (가장 많이 할당된 서버 선택)

### 파일
- `scheduler_mostallocated.h`
- `scheduler_mostallocated.cpp`

### 알고리즘 설명

First Fit Decreasing 전략 기반으로, 남은 GPU 개수가 가장 적은 서버에 작업을 배치합니다.

### 동작 방식

1. 필요한 GPU 개수 이상을 가진 서버를 찾음
2. 남은 GPU 개수가 가장 적은 서버 선택
3. 못 찾으면:
   - 엄격 모드: 실패 반환
   - 비엄격 모드: 첫 번째 가능한 서버 선택

### 자료구조

```cpp
vector<vector<tuple<int, server_entry*>>> accelerator_count_hash_list;
// 가속기 타입별로 서버를 남은 GPU 개수로 정렬
```

### 장단점

| 장점 | 단점 |
|-----|-----|
| 서버 통합 효과 | 특정 서버에 부하 집중 |
| 빈 서버 유지 용이 | 선점 비용 증가 가능 |

---

## 2. Compact (압축 배치)

### 파일
- `scheduler_compact.h`
- `scheduler_compact.cpp`

### 알고리즘 설명

현재 서버부터 순차적으로 탐색하여 가능한 첫 서버에 배치합니다.

### 동작 방식

```cpp
int current_server_index = 0;

for (i = current_server_index; i < server_count; i++) {
    if (server[i].available >= job.required) {
        assign(server[i], job);
        return i;
    }
}
// 처음부터 다시 탐색
for (i = 0; i < current_server_index; i++) {
    ...
}
```

### 장단점

| 장점 | 단점 |
|-----|-----|
| 구현 단순 | 조각화 발생 가능 |
| 빠른 결정 | 최적 배치 보장 X |

---

## 3. Round-Robin (순환 선택)

### 파일
- `scheduler_round_robin.h`
- `scheduler_round_robin.cpp`

### 알고리즘 설명

서버를 순환하며 작업을 할당하여 부하를 분산합니다.

### 동작 방식

```cpp
int get_next_server_index() {
    current_server_index = (current_server_index + 1) % server_count;
    return current_server_index;
}

// 스케줄링
int attempts = 0;
while (attempts < server_count) {
    int idx = get_next_server_index();
    if (server[idx].available >= job.required) {
        return idx;
    }
    attempts++;
}
return -1;  // 실패
```

### 장단점

| 장점 | 단점 |
|-----|-----|
| 부하 분산 | 빈 서버 유지 어려움 |
| 공정한 배분 | 조각화 증가 |

---

## 4. MCTS (Monte Carlo Tree Search)

### 파일
- `scheduler_mcts.h`
- `scheduler_mcts.cpp`

### 알고리즘 설명

MCTS 알고리즘을 사용하여 최적의 서버 배치를 탐색합니다.

### 핵심 자료구조

```cpp
struct MCTSNode {
    vector<unique_ptr<MCTSNode>> children;
    MCTSNode* parent;
    int visits;
    double value;
    int server_index;
    int depth;
};
```

### 동작 단계

#### 1. Selection (선택)
UCB(Upper Confidence Bound) 공식으로 노드 선택:

```
UCB = value/visits + exploration_parameter * sqrt(ln(parent_visits)/visits)
```

#### 2. Expansion (확장)
가능한 모든 서버를 자식 노드로 생성

#### 3. Simulation (시뮬레이션)
무작위로 작업을 배치하여 효율성 평가

#### 4. Backpropagation (역전파)
결과를 부모 노드로 역전파

### 파라미터

```cpp
int simulation_count = 100;           // 시뮬레이션 횟수
double exploration_parameter = 1.414;  // sqrt(2), 탐색 계수
```

### 장단점

| 장점 | 단점 |
|-----|-----|
| 최적에 가까운 결정 | 계산 비용 높음 |
| 복잡한 상황에 적합 | 파라미터 튜닝 필요 |

---

## 5. FareShare (공정 공유)

### 파일
- `scheduler_fare_share.h`
- `scheduler_fare_share.cpp`

### 상태

**구현 미완료** - 현재 `return 0`만 반환

### 예정 기능

- 사용자/팀별 GPU 할당량 관리
- 과거 사용량 기반 우선순위 조정

---

## 공통 기능

### 기아(Starvation) 방지

작업이 너무 오래 대기하면 우선순위를 상향합니다.

```cpp
struct job_age {
    int age;                    // 대기 시간
    int accumulated_age;        // 누적 대기 시간
    job_entry* job;
    double repriority_score;
};

// 스케줄 실패 시 나이 증가
if (!scheduled) {
    job_age.age++;
}

// 임계값 초과 시 우선순위 조정
if (job_age.age * age_weight > svp_upper) {
    // 우선순위 상향
}
```

### GPU 조각화 제거 (Defragmentation)

동적 프로그래밍으로 작업을 재배치하여 빈 서버를 최대화합니다.

```cpp
// 상태 정의
struct server_status_for_dp {
    gpu_allocation_type status;  // empty, fixed, floating, adjusted
    string job_id;
};

// DP 함수
f(step, max_full_empty_server) =
    max(f(step+1) with job moved,
        f(step+1) without move)
```

---

## 스케줄러 선택 가이드

| 상황 | 권장 스케줄러 |
|-----|-------------|
| 서버 통합 필요 | MostAllocated |
| 단순한 환경 | Compact |
| 부하 분산 필요 | Round-Robin |
| 복잡한 최적화 | MCTS |
| 다중 사용자 환경 | FareShare (예정) |
