# 오버헤드 보정 시뮬레이터 설계 (하이브리드 — 리젝 ⑥ 대응)

> 목적: 실측(B200×8, 수백 잡)으로는 불가능한 **전체 트레이스(Philly 111k)·멀티노드·이종
> 토폴로지·v3 알고리즘**을 평가. 실측에서 보정한 오버헤드를 주입해 실측↔시뮬 정합성 확보.
> 핵심 원칙: **시뮬레이터의 정책 로직은 K8s 컨트롤러(`squad_ctrl/policy_controller.py`)와
> 동일 코드 경로**를 쓴다(같은 결정 = 비교 가능성). C++ 시뮬레이터(`gpu_scheuer/`)와도 알고리즘 일치.

## 1. 실측 보정 파라미터 (2026-06-06 측정, `/raid/squad/overheads/`, `/raid/squad/ptr/`)

| 파라미터 | 값 | 출처 |
|---|---|---|
| 스케줄링 지연(용량 有) | 0.5s | lifecycle.csv sched_s (par8/big8 ≈ 0) |
| 잡 기동(startup, 단독) | 1.5s | seq1 startup p50 |
| 잡 기동(동시 경합) | 3.5s | par8/par24 startup p50 |
| 종료(teardown→complete) | 2.5s | 전 시나리오 complete_s |
| **잡당 고정 오버헤드** | **4~7s** | startup + teardown |
| 실행 오버헤드 | 0 | exec_ovh ≈ 0 (holder) |
| **PTR 이주 다운타임 D(앱레벨)** | save+load(크기 의존) + teardown + reschedule | `ckpt_overhead.csv` (측정 중) |
| PTR 이주 다운타임 D(투명 C/R) | cuda-checkpoint (B200 스모크 대기) | 사용자 직접 실행 승인 후 |

주의: par24의 sched 17~36s는 **큐잉**(용량 대기)이지 오버헤드 아님 — 시뮬레이터가 직접 계산.

## 2. 구조 (이산사건 시뮬레이션, Python)

```
이벤트 큐(시각순): JOB_ARRIVAL, SCHED_TICK, JOB_FINISH, PTR_TRIGGER
상태: servers[node][gpu], wait_queue(flavor별), running[job]→(node, end_time)

JOB_ARRIVAL(j):  wait_queue.push(j); schedule SCHED_TICK(now)
SCHED_TICK:      ordered = policy.order(wait_queue, servers, AR)   # ← 컨트롤러와 동일 함수
                 for j in ordered: if fits(j): place(j);
                     end = now + sched_lat + startup + j.duration   # 오버헤드 주입
                     schedule JOB_FINISH(j, end)
JOB_FINISH(j):   free(j) after teardown; schedule SCHED_TICK(now+teardown)
PTR_TRIGGER:     if pending≥ω: defrag(servers) → 이주 잡마다 end += D(크기)  # PTR 비용
```

- **오버헤드 주입 지점**: place 시 `sched_lat + startup`, finish 시 `teardown`, 이주 시 `D`.
- 큐잉지연 = place_time − arrival_time (실측과 동일 정의) → 직접 비교.

## 3. 정책 로직 재사용

`policy_controller.py`의 `order()`·`sigma_star()`·`reorder_queue`(squad_algo)를 시뮬레이터가
import. fifo/sjf/las/sfqa/sfqa-auto/easy + **v3(감지+예약)** 모두 동일 구현 1벌로 평가.
→ "실측 5정책 == 시뮬 동일 5정책"이 코드로 보장(리젝 ① 정합성).

## 4. 검증(calibration) 절차

1. **동일 워크로드 재현**: Philly-2K-C48·W15 등 실측한 run을 시뮬에 그대로 입력.
2. **정합 판정**: 시뮬 큐잉 p50/p90/max가 실측의 ±15% 이내면 보정 성공.
3. 차이 크면 오버헤드 파라미터 재튜닝(특히 동시 경합 startup).
4. 정합 후 → 전체 111k·멀티노드·이종(B200+H100+A100)·δ/ω/α/β 그리드로 확장.

## 5. v3(감지+예약) — 이번 실측이 드러낸 설계

W15 실측: auto(순서만)는 8-GPU 굶은 잡을 tier-1로 올렸으나 gate 루프가 자리를 못 만들어
작은 잡에 추월당함(max 5688 vs EASY 347). 결론: **감지(우리, 무튜닝 u≥1) + 예약(EASY식 자리잠금)**.
- 컨트롤러/시뮬 공통: tier-1 선두가 안 들어가면 그 잡 몫의 GPU를 **예약**(작은 잡 ungate 중단,
  실행 중 잡 종료로 자리 확보될 때까지). EASY와 달리 duration 추정 불요(나이로 트리거).
- 시뮬레이터에서 먼저 검증 → 유망하면 컨트롤러 반영 → 실측.

## 6. 산출물(예정)

`sim/` 디렉터리: `engine.py`(이산사건), `policies.py`(controller import 래퍼),
`calibrate.py`(실측 대조), `sweep.py`(대규모·이종). 결과는 실측 SUMMARY와 합본.
