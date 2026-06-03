// scheduler 는 SQUAD QueueSort 플러그인을 등록한 커스텀 kube-scheduler 바이너리다.
// out-of-tree 플러그인 패턴: 표준 kube-scheduler app 에 SQUADSort 를 추가 등록하고,
// KubeSchedulerConfiguration 에서 QueueSort 확장점에 SQUADSort 를 활성화(PrioritySort 비활성).
package main

import (
	"os"

	"k8s.io/component-base/cli"
	_ "k8s.io/component-base/logs/json/register"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"

	"github.com/mystous/gpu_scheduler/k8s/pkg/queuesort"
)

func main() {
	command := app.NewSchedulerCommand(
		app.WithPlugin(queuesort.Name, queuesort.New),
	)
	code := cli.Run(command)
	os.Exit(code)
}
