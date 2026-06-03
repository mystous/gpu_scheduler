package squad

import (
	"math"
	"testing"
)

func almost(a, b float64) bool { return math.Abs(a-b) < 1e-9 }

// SFQA: R 테이블 계산 (C++ job_emulator.cpp:416-425).
func TestComputeRTable(t *testing.T) {
	servers := []Server{{Name: "n0", GPUType: "b200", Total: 8}}
	// avail=2: 슬롯 6개 점유로 설정.
	for i := 0; i < 6; i++ {
		servers[0].Slots[i] = SlotFixed
	}
	for i := 6; i < 8; i++ {
		servers[0].Slots[i] = SlotEmpty
	}
	R := ComputeRTable(servers, "b200")
	// i=0: 1-(2-0-1)*0.1 = 0.9 ; i=1: 1-(2-1-1)*0.1 = 1.0 ; i>=2: 0
	if !almost(R[0], 0.9) || !almost(R[1], 1.0) || !almost(R[2], 0.0) {
		t.Fatalf("R 테이블 불일치: %v", R)
	}
}

// flavor-aware: 다른 GPU 타입 server는 R 계산에서 제외.
func TestComputeRTableFlavorAware(t *testing.T) {
	servers := []Server{
		{Name: "h", GPUType: "h100", Total: 8}, // 전부 empty (avail 8)
		{Name: "b", GPUType: "b200", Total: 8},
	}
	for i := 0; i < 8; i++ {
		servers[0].Slots[i] = SlotEmpty
	}
	for i := 0; i < 7; i++ {
		servers[1].Slots[i] = SlotFixed
	}
	servers[1].Slots[7] = SlotEmpty // b200 avail=1
	R := ComputeRTable(servers, "b200")
	// b200만 반영: avail=1, i=0: 1-(1-0-1)*0.1=1.0
	if !almost(R[0], 1.0) || !almost(R[1], 0.0) {
		t.Fatalf("flavor-aware R 불일치: %v", R)
	}
}

// SFQA: ReorderQueue 트리거 on (AR<=β) — 나이 큰 job이 앞으로.
func TestReorderQueueActive(t *testing.T) {
	servers := []Server{{Name: "n0", GPUType: "b200", Total: 8}}
	for i := 0; i < 6; i++ {
		servers[0].Slots[i] = SlotFixed
	}
	servers[0].Slots[6], servers[0].Slots[7] = SlotEmpty, SlotEmpty
	jobs := []PendingJob{
		{ID: "J1", GPUCount: 1, GPUType: "b200", Age: 0},
		{ID: "J2", GPUCount: 1, GPUType: "b200", Age: 100},
	}
	p := DefaultParams()
	out := ReorderQueue(jobs, servers, "b200", p, 50.0) // AR=50 <= β80 → active
	if out[0].ID != "J2" {
		t.Fatalf("나이 큰 J2가 앞에 와야 함, got %s (P*: J1=%.3f J2=%.3f)", out[0].ID, out[1].PStar, out[0].PStar)
	}
}

// SFQA: 트리거 off (AR>β) — 원순서 유지.
func TestReorderQueueInactive(t *testing.T) {
	servers := []Server{{Name: "n0", GPUType: "b200", Total: 8}}
	servers[0].Slots[0] = SlotEmpty
	jobs := []PendingJob{
		{ID: "J1", GPUCount: 1, GPUType: "b200", Age: 0},
		{ID: "J2", GPUCount: 1, GPUType: "b200", Age: 100},
	}
	p := DefaultParams()
	out := ReorderQueue(jobs, servers, "b200", p, 90.0) // AR=90 > β80 → inactive
	if out[0].ID != "J1" || out[1].ID != "J2" {
		t.Fatalf("AR>β면 원순서 유지해야 함, got %s,%s", out[0].ID, out[1].ID)
	}
}

// PTR: 2 server 각 절반 점유 → 1개 이주로 한 server를 완전히 비움.
func TestDefragBasic(t *testing.T) {
	mk := func(name, gt, jobID string) Server {
		s := Server{Name: name, GPUType: GPUType(gt), Total: 8}
		for i := 0; i < 4; i++ {
			s.Slots[i] = SlotFloating
			s.JobIDs[i] = jobID
		}
		for i := 4; i < 8; i++ {
			s.Slots[i] = SlotEmpty
		}
		return s
	}
	servers := []Server{mk("n0", "b200", "A"), mk("n1", "b200", "B")}
	jobs := []RunningJob{
		{ID: "A", GPUCount: 4, GPUType: "b200", ServerIndex: 0, TargetIndex: -1, Preemptible: true},
		{ID: "B", GPUCount: 4, GPUType: "b200", ServerIndex: 1, TargetIndex: -1, Preemptible: true},
	}
	d := NewDefrag(servers, jobs, DefaultDPExecutionMax)
	improved, plan, before, after := d.Run()
	if !improved || before != 0 || after != 1 {
		t.Fatalf("디프래그 기대: improved=true before=0 after=1, got improved=%v before=%d after=%d", improved, before, after)
	}
	moved := 0
	for _, j := range plan {
		if j.TargetIndex >= 0 {
			moved++
		}
	}
	if moved != 1 {
		t.Fatalf("정확히 1개 job 이주 기대, got %d", moved)
	}
}

// PTR: 이종 가드 — 다른 타입 server로는 이주하지 않아 개선 불가.
func TestDefragHeterogeneousGuard(t *testing.T) {
	mk := func(name, gt, jobID string) Server {
		s := Server{Name: name, GPUType: GPUType(gt), Total: 8}
		for i := 0; i < 4; i++ {
			s.Slots[i] = SlotFloating
			s.JobIDs[i] = jobID
		}
		for i := 4; i < 8; i++ {
			s.Slots[i] = SlotEmpty
		}
		return s
	}
	servers := []Server{mk("n0", "b200", "A"), mk("n1", "h100", "B")} // 타입 다름
	jobs := []RunningJob{
		{ID: "A", GPUCount: 4, GPUType: "b200", ServerIndex: 0, TargetIndex: -1, Preemptible: true},
		{ID: "B", GPUCount: 4, GPUType: "h100", ServerIndex: 1, TargetIndex: -1, Preemptible: true},
	}
	d := NewDefrag(servers, jobs, DefaultDPExecutionMax)
	improved, _, before, after := d.Run()
	if improved || before != 0 || after != 0 {
		t.Fatalf("이종이라 이주 불가, 개선 없어야 함: improved=%v before=%d after=%d", improved, before, after)
	}
}
