package squad

import (
	"math"
	"sort"
)

// SFQA (Starvation-Free Queue Adjustment)
// C++ 원본: gpu_scheuer/job_emulator.cpp::adjust_wait_queue (lines 410-478),
//           R 계산 (414-424), P* 계산 (432-436), AR 트리거 (411-412).
// 식: P* = P + α·A·R,  단 AR ≤ β 일 때만 (그렇지 않으면 P* = P).

// ComputeRTable은 자원 적합도 지수 R[0..7] 을 계산한다(요청 GPU 수 k → R[k-1]).
// flavor-aware: gpuType 과 일치하는 server 들만 대상(GPUTypeAny면 전부). 이종 클러스터에서
// 같은 타입 노드 풀의 가용도만 반영한다.
// C++ job_emulator.cpp:416-425 충실 포팅.
func ComputeRTable(servers []Server, gpuType GPUType) [AccelPerServerMax]float64 {
	var R [AccelPerServerMax]float64
	for si := range servers {
		if gpuType != GPUTypeAny && servers[si].GPUType != gpuType {
			continue
		}
		avail := servers[si].Available()
		for i := 0; i < AccelPerServerMax; i++ {
			if avail-i <= 0 {
				continue
			}
			suit := 1 - float64(avail-i-1)*0.1
			if suit > R[i] {
				R[i] = suit
			}
		}
	}
	return R
}

// PStar는 큐 위치 pos(0-base), 나이 age, 요청 GPU 수 gpuCount 에 대한 재우선순위 P* 를 돌려준다.
// C++ job_emulator.cpp:432-436. priority = 1/2^pos, starvation = age·α·R[k-1].
func PStar(pos, age, gpuCount int, alpha float64, R [AccelPerServerMax]float64) float64 {
	priority := 1.0 / math.Pow(2, float64(pos))
	k := gpuCount
	if k < 1 {
		k = 1
	}
	if k > AccelPerServerMax {
		k = AccelPerServerMax
	}
	starvation := float64(age) * alpha * R[k-1]
	return priority + starvation
}

// ReorderQueue는 한 flavor 대기큐(jobs, 현재 순서대로)에 SFQA를 적용해 P* 내림차순으로
// 재정렬한 새 슬라이스를 돌려준다. allocationRatePct 는 해당 시점의 클러스터(또는 타입별) 할당률(%).
//
// C++(adjust_wait_queue)은 최고 P* job 하나만 맨 앞으로 옮기지만(argmax-promote, 443-446),
// K8s QueueSort 는 전순서가 필요하므로 전체 내림차순 안정정렬로 일반화한다
// (argmax-promote 의 반복 적용은 전체 정렬로 수렴 — 계획서 §B1).
//
// 트리거: params.PreventStarv 가 false 거나 allocationRatePct > β 이면 P*=P(원순서 유지).
func ReorderQueue(jobs []PendingJob, servers []Server, gpuType GPUType, p Params, allocationRatePct float64) []PendingJob {
	out := make([]PendingJob, len(jobs))
	copy(out, jobs)

	active := p.PreventStarv && allocationRatePct <= p.StarvationβPct
	var R [AccelPerServerMax]float64
	if active {
		R = ComputeRTable(servers, gpuType)
	}
	for i := range out {
		if active {
			out[i].PStar = PStar(i, out[i].Age, out[i].GPUCount, p.AgeWeight, R)
		} else {
			// AR > β: P* = P (base priority only). 원순서 보존(정렬해도 동일).
			out[i].PStar = 1.0 / math.Pow(2, float64(i))
		}
	}
	if !active {
		return out // 원순서 유지
	}
	// 안정 정렬: P* 내림차순, 동점이면 기존 순서 유지.
	sort.SliceStable(out, func(a, b int) bool {
		return out[a].PStar > out[b].PStar
	})
	return out
}

// AdvanceAge는 한 reconcile 스텝의 나이 갱신 규칙을 적용한다.
// C++ job_scheduler.cpp:48-58: 해당 flavor 큐에서 스케줄이 발생했으면(scheduledThisStep)
// 그 큐 전체 age=0, 아니면 전체 age 를 inc 만큼 증가.
// K8s 컨트롤러는 inc 를 벽시계 기반("10분=+1")으로 전달한다.
func AdvanceAge(jobs []PendingJob, scheduledThisStep bool, inc int) {
	for i := range jobs {
		if scheduledThisStep {
			jobs[i].Age = 0
		} else {
			jobs[i].Age += inc
		}
	}
}
