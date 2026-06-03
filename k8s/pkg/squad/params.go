// Package squad는 C++ 시뮬레이터(gpu_scheduer/)의 검증된 SQUAD 알고리즘
// (SFQA 큐 재정렬, PTR 디프래그)을 K8s 비의존 순수 Go로 포팅한 것이다.
// 시뮬레이터와 K8s 레이어가 동일 알고리즘을 쓰도록 보장한다(REEXPERIMENT_PLAN.md "동일 알고리즘").
//
// 하드웨어 비종속: 모든 함수가 GPU 타입(flavor)과 server 수에 일반화되어 있으며,
// 특정 GPU(B200 등)나 노드 수에 종속되지 않는다.
package squad

// 기본 파라미터 — C++ enum_definition.h global_const 와 일치.
const (
	// AccelPerServerMax: 한 server(노드/GPU그룹)의 최대 가속기 슬롯 수.
	// C++ global_const::accelator_per_server_max = 8. PTR 슬롯 모델의 크기.
	AccelPerServerMax = 8

	// DefaultAgeWeight (α): starvation 가중치. C++ global_const::age_weight = 0.13889.
	DefaultAgeWeight = 0.13889
	// DefaultStarvationUpper (β): SFQA 발동 임계 할당률(%). C++ global_const::starvation_upper = 80.
	DefaultStarvationUpper = 80.0
	// DefaultDPExecutionMax (δ): PTR DP 재귀 호출 상한. C++ global_const::dp_execution_maximum = 100000.
	DefaultDPExecutionMax = 100000
	// DefaultDefragCriteria (ω): PTR 발동 대기큐 길이 임계. C++ global_const::defragmentation_criteria = 20.
	DefaultDefragCriteria = 20
)

// Params는 한 번의 스케줄링 사이클에 적용되는 SQUAD 노브 묶음.
// C++ global_structure::scheduler_option 에 대응.
type Params struct {
	AgeWeight      float64 // α
	StarvationβPct float64 // β (allocation rate %, 트리거 임계)
	DPExecutionMax int     // δ
	DefragCriteria int     // ω
	PreventStarv   bool    // SFQA 활성
	UsePreemption  bool    // PTR 활성
	FlavorAware    bool    // GPU 타입별 분리 스케줄링
}

// DefaultParams는 시뮬레이터 기본값과 동일한 Params를 돌려준다.
func DefaultParams() Params {
	return Params{
		AgeWeight:      DefaultAgeWeight,
		StarvationβPct: DefaultStarvationUpper,
		DPExecutionMax: DefaultDPExecutionMax,
		DefragCriteria: DefaultDefragCriteria,
		PreventStarv:   true,
		UsePreemption:  true,
		FlavorAware:    true,
	}
}
