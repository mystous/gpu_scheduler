package squad

import (
	"sort"
	"strconv"
	"strings"
)

// PTR (Preemptive Task Reallocation / Defragmentation)
// C++ 원본: gpu_scheuer/adjusting_server.cpp.
//   DP 코어 get_optimal_adjusting_dp (146-191), calcu_full_empty_server (200-210),
//   rearrange_task (238-263), switch_accelerator_status (224-236), generate_state_key (265-274).
//
// 멀티노드 일반화: "server" 추상화는 노드/노드내 GPU그룹 어느 쪽이든 매핑되며 server 수에
// 종속되지 않는다. 이종 클러스터 대응으로 이주는 동일 GPUType server 간에만 허용한다(C++엔 없던 가드).

// Defrag는 PTR DP 한 실행의 (변이되는) 상태를 캡슐화한다. C++ adjusting_server 클래스에 대응.
type Defrag struct {
	servers   []Server     // 슬롯 모델 — DP 백트래킹 중 변이된다
	jobs      []RunningJob // 이주 후보(선점가능·whole-server 미점유), 순서대로 DP
	targets   []int        // 타겟 server 인덱스(available 오름차순) — C++ priroried_target_server
	maxExec   int          // δ
	execCount int
	memo      map[string]int
	best      []RunningJob // C++ optimal_position (각 job의 TargetIndex 포함)
}

// NewDefrag는 슬롯 모델과 이주 후보로 Defrag를 만든다. 타겟 server는 부분 점유(0<avail<Total)인
// server들이며 available 오름차순으로 정렬한다(C++ reconstruct_server_status target_server +
// build_dp_target/compare_server_priority).
func NewDefrag(servers []Server, jobs []RunningJob, dpMax int) *Defrag {
	d := &Defrag{servers: servers, jobs: jobs, maxExec: dpMax, memo: map[string]int{}}
	for i := range servers {
		av := servers[i].Available()
		if av > 0 && av < servers[i].Total {
			d.targets = append(d.targets, i)
		}
	}
	sort.SliceStable(d.targets, func(a, b int) bool {
		return servers[d.targets[a]].Available() < servers[d.targets[b]].Available()
	})
	return d
}

// Run은 DP를 실행한다. before(현재 빈 server 수)보다 after(DP 최적)가 크면 improved=true 와
// 이주 계획(plan, TargetIndex≥0 인 job만 실제 이주)을 돌려준다. C++ defragementation(4-20).
func (d *Defrag) Run() (improved bool, plan []RunningJob, before, after int) {
	before = d.calcFullEmpty()
	maxFull := 0
	after = d.dp(0, &maxFull)
	if before < after {
		return true, d.best, before, after
	}
	return false, nil, before, after
}

// dp는 C++ get_optimal_adjusting_dp(146-191) 충실 포팅.
func (d *Defrag) dp(rc int, maxFull *int) int {
	if d.execCount > d.maxExec { // δ 상한
		return *maxFull
	}
	d.execCount++

	key := d.stateKey(rc)
	if v, ok := d.memo[key]; ok {
		return v
	}
	if rc == 0 {
		d.memo = map[string]int{}
		d.memo[key] = *maxFull
		*maxFull = d.calcFullEmpty()
	}
	if rc == len(d.jobs) {
		return *maxFull
	}

	job := &d.jobs[rc]
	for i := 0; i < len(d.targets); i++ {
		ti := d.targets[i]
		// 자기 server로의 이주 스킵. (C++ 170은 server_index==i 로 배열 인덱스와 비교하는
		// 불일치가 있어 의도 — 자기 server 제외 — 를 살려 실제 server 인덱스로 비교한다.)
		if job.ServerIndex == ti {
			continue
		}
		srv := &d.servers[ti]
		if srv.GPUType != job.GPUType { // 이종 가드: 동일 타입 server 간 이주만
			continue
		}
		if srv.Available() < job.GPUCount {
			continue
		}
		if d.rearrange(ti, job, false) {
			full := d.calcFullEmpty()
			if full > *maxFull {
				*maxFull = full
				d.memo[key] = *maxFull
				d.snapshot()
			}
			*maxFull = d.dp(rc+1, maxFull)
			d.rearrange(ti, job, true) // 백트래킹(undo)
		}
	}
	*maxFull = d.dp(rc+1, maxFull) // 이 job 이주 안 함
	return *maxFull
}

// rearrange는 job 을 serverIdx 로 이주(reverse=false)하거나 되돌린다(true). C++ rearrange_task(238-263).
func (d *Defrag) rearrange(serverIdx int, job *RunningJob, reverse bool) bool {
	if !reverse {
		srv := &d.servers[serverIdx]
		if job.GPUCount > srv.Total {
			return false
		}
		if d.emptySlots(serverIdx) < job.GPUCount {
			return false
		}
		d.switchStatus(serverIdx, job.GPUCount, SlotEmpty, SlotAdjusted)
		d.switchStatus(job.ServerIndex, job.GPUCount, SlotFloating, SlotEmpty)
		job.TargetIndex = serverIdx
		return true
	}
	d.switchStatus(serverIdx, job.GPUCount, SlotAdjusted, SlotEmpty)
	d.switchStatus(job.ServerIndex, job.GPUCount, SlotEmpty, SlotFloating)
	job.TargetIndex = -1
	return true
}

// switchStatus는 server 의 앞에서부터 prev 상태 슬롯 count 개를 after 로 바꾼다.
// None 슬롯을 만나면 중단. C++ switch_accelerator_status(224-236).
func (d *Defrag) switchStatus(serverIdx, count int, prev, after SlotStatus) {
	srv := &d.servers[serverIdx]
	for i := 0; i < AccelPerServerMax; i++ {
		if count == 0 {
			break
		}
		if srv.Slots[i] == SlotNone {
			break
		}
		if srv.Slots[i] == prev {
			srv.Slots[i] = after
			count--
		}
	}
}

// calcFullEmpty는 모든 슬롯이 비어 있는 server 수. C++ calcu_full_empty_server(200-210).
func (d *Defrag) calcFullEmpty() int {
	n := 0
	for i := range d.servers {
		if d.emptySlots(i) == d.servers[i].Total {
			n++
		}
	}
	return n
}

// emptySlots는 SlotEmpty 슬롯 수. C++ get_empty_slot(212-222).
func (d *Defrag) emptySlots(serverIdx int) int {
	n := 0
	srv := &d.servers[serverIdx]
	for i := 0; i < AccelPerServerMax; i++ {
		if srv.Slots[i] == SlotEmpty {
			n++
		}
	}
	return n
}

// stateKey는 recursive_count + 각 타겟 server의 (idx:available) 직렬화. C++ generate_state_key(265-274).
func (d *Defrag) stateKey(rc int) string {
	var b strings.Builder
	b.WriteString(strconv.Itoa(rc))
	b.WriteByte('-')
	for _, ti := range d.targets {
		b.WriteString(strconv.Itoa(ti))
		b.WriteByte(':')
		b.WriteString(strconv.Itoa(d.emptySlots(ti)))
		b.WriteByte(';')
	}
	return b.String()
}

// snapshot은 현재 job_list(각 TargetIndex)를 best로 복사. C++ dumpy_job_list(193-198).
func (d *Defrag) snapshot() {
	d.best = make([]RunningJob, len(d.jobs))
	copy(d.best, d.jobs)
}
