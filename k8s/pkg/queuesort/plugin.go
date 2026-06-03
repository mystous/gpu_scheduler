// Package queuesort는 SQUAD 의 통합 QueueSort 스케줄러 플러그인이다.
//
// 설계(R1/R2, REEXPERIMENT_PLAN.md §B1):
//   - kube-scheduler 는 QueueSort 확장점에 플러그인을 하나만 허용한다(R1). 그래서 이 플러그인이
//     SFQA 순서와 gang(PodGroup) 순서를 모두 처리하는 "통합" QueueSort 가 된다.
//   - Less(p1,p2) 는 두 Pod 만 보고 클러스터 상태를 알 수 없다(R2). 따라서 클러스터 상태가 필요한
//     P* 계산은 SFQA 컨트롤러가 수행해 annotation(squad.io/score)에 주입하고, 이 플러그인은
//     주입된 값으로 "정렬만" 한다. 부수효과 없음.
package queuesort

import (
	"context"
	"strconv"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/kubernetes/pkg/scheduler/framework"
)

const (
	// Name 은 KubeSchedulerConfiguration 에서 QueueSort 로 활성화할 플러그인 이름.
	Name = "SQUADSort"
	// ScoreAnnotation 은 SFQA 컨트롤러가 주입하는 P*·1e6 정수 점수.
	ScoreAnnotation = "squad.io/score"
	// PodGroupLabel 은 gang(Coscheduling) 멤버를 묶는 라벨(있으면 tie-break 에 사용).
	PodGroupLabel = "scheduling.x-k8s.io/pod-group"
)

// SQUADSort 는 framework.QueueSortPlugin 을 구현한다.
type SQUADSort struct{}

var _ framework.QueueSortPlugin = &SQUADSort{}

// New 는 플러그인 팩토리(out-of-tree 등록용). k8s 1.31 PluginFactory 시그니처.
func New(_ context.Context, _ runtime.Object, _ framework.Handle) (framework.Plugin, error) {
	return &SQUADSort{}, nil
}

func (s *SQUADSort) Name() string { return Name }

// Less 는 두 대기 Pod 의 순서를 정한다. 우선 P*(score) 내림차순, 동점이면 gang 묶음 유지,
// 그다음 FIFO(타임스탬프). C++ adjust_wait_queue 의 전순서 일반화(REEXPERIMENT_PLAN §B1).
func (s *SQUADSort) Less(p1, p2 *framework.QueuedPodInfo) bool {
	s1 := readScore(p1.Pod)
	s2 := readScore(p2.Pod)
	if s1 != s2 {
		return s1 > s2 // 높은 P* 먼저
	}
	// gang tie-break: 같은 PodGroup 멤버는 인접 유지(먼저 도착한 그룹 우선).
	g1, ok1 := podGroup(p1.Pod)
	g2, ok2 := podGroup(p2.Pod)
	if ok1 && ok2 && g1 != g2 {
		return p1.Timestamp.Before(p2.Timestamp)
	}
	// 기본 FIFO (default PrioritySort 의 fallback 과 동일).
	return p1.Timestamp.Before(p2.Timestamp)
}

func readScore(pod *v1.Pod) int64 {
	if pod == nil || pod.Annotations == nil {
		return 0
	}
	if v, ok := pod.Annotations[ScoreAnnotation]; ok {
		if n, err := strconv.ParseInt(v, 10, 64); err == nil {
			return n
		}
	}
	return 0
}

func podGroup(pod *v1.Pod) (string, bool) {
	if pod == nil || pod.Labels == nil {
		return "", false
	}
	g, ok := pod.Labels[PodGroupLabel]
	return g, ok
}
