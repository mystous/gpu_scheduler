package squad

// GPUType은 가속기 타입(flavor). 하드웨어 비종속 — 임의의 타입 문자열을 허용한다.
// C++ enum accelator_type(v100/a30/a100/h100/h200/l4/l40/b200)의 일반화.
// K8s에서는 노드 라벨 nvidia.com/gpu.product 값(예: "NVIDIA-B200", "NVIDIA-H100-80GB")에서 채운다.
type GPUType string

const GPUTypeAny GPUType = ""

// SlotStatus는 PTR 슬롯 모델의 한 GPU 슬롯 상태.
// C++ enum gpu_allocation_type 와 1:1 대응.
type SlotStatus int

const (
	SlotNone     SlotStatus = iota // 슬롯 없음 (server 용량 미만 영역)
	SlotEmpty                      // 비어 있음(배치 가능)
	SlotFixed                      // 비선점 job 점유
	SlotFloating                  // 선점 가능 job 점유(이주 후보)
	SlotAdjusted                  // DP 탐색 중 타겟 슬롯
)

// Server는 스케줄링 단위(노드 또는 노드내 GPU그룹). topology-config로 매핑 단위가 결정된다.
// C++ server_entry 의 PTR 관점 모델.
type Server struct {
	Name    string
	GPUType GPUType            // 이 server가 제공하는 가속기 타입(이종 클러스터)
	Total   int               // 가속기 총 슬롯 수 (≤ AccelPerServerMax)
	Slots   [AccelPerServerMax]SlotStatus
	JobIDs  [AccelPerServerMax]string // 각 슬롯을 점유한 job id
}

// Available은 비어 있는(SlotEmpty) 슬롯 수.
func (s *Server) Available() int {
	n := 0
	for i := 0; i < s.Total; i++ {
		if s.Slots[i] == SlotEmpty {
			n++
		}
	}
	return n
}

// PendingJob은 대기열의 한 job(=K8s pending pod). SFQA 입력.
type PendingJob struct {
	ID       string
	GPUCount int
	GPUType  GPUType
	Age      int     // 나이 카운터(C++ job_age.age)
	PStar    float64 // 계산된 재우선순위 P*
}

// RunningJob은 PTR 이주 후보가 될 수 있는 실행 중 job(=K8s running pod).
type RunningJob struct {
	ID          string
	GPUCount    int
	GPUType     GPUType
	ServerIndex int // 현재 위치한 server 인덱스
	TargetIndex int // DP가 정한 이주 타겟(-1=이주 안 함)
	Preemptible bool
}
