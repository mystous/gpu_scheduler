// sfqa-controller 는 SFQA 의 "두뇌"다(R2). 클러스터 상태(노드 GPU 타입/할당률, 대기 Pod)를
// 주기적으로 읽어 각 대기 Pod 의 P* = P + α·A·R 을 계산하고, 그 결과를 Pod annotation
// (squad.io/score)에 주입한다. QueueSort 플러그인(pkg/queuesort)은 그 값으로 정렬만 한다.
//
// 하드웨어 비종속: 노드 라벨 nvidia.com/gpu.product 로 GPU 타입을 식별하고 타입(flavor)별로
// 분리 처리한다. C++ job_emulator.cpp::adjust_wait_queue 의 K8s 컨트롤러 포팅.
package main

import (
	"context"
	"flag"
	"strconv"
	"time"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/client-go/rest"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/config"
	ctrllog "sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	"sigs.k8s.io/controller-runtime/pkg/manager"
	"sigs.k8s.io/controller-runtime/pkg/manager/signals"

	"github.com/mystous/gpu_scheduler/k8s/pkg/squad"
)

func mustConfig() *rest.Config { return config.GetConfigOrDie() }

const (
	gpuResource     = "nvidia.com/gpu"
	gpuProductLabel = "nvidia.com/gpu.product"
	schedulerName   = "squad-scheduler"
	scoreAnno       = "squad.io/score"
	ageAnno         = "squad.io/age"
	ageUpdatedAnno  = "squad.io/age-updated"
	flavorAnno      = "squad.io/gpu-type"
	ageStepMinutes  = 10 // "10분 = +1" (REEXPERIMENT_PLAN §2.5)
)

func main() {
	var period time.Duration
	var alpha, beta float64
	flag.DurationVar(&period, "period", 10*time.Second, "reconcile 주기")
	flag.Float64Var(&alpha, "alpha", squad.DefaultAgeWeight, "α age_weight")
	flag.Float64Var(&beta, "beta", squad.DefaultStarvationUpper, "β svp_upper(%)")
	flag.Parse()
	ctrllog.SetLogger(zap.New())

	mgr, err := manager.New(mustConfig(), manager.Options{})
	if err != nil {
		panic(err)
	}
	r := &sfqaReconciler{
		cl: mgr.GetClient(), period: period,
		params: squad.Params{AgeWeight: alpha, StarvationβPct: beta, PreventStarv: true, FlavorAware: true},
		prevPending: map[string]map[string]bool{},
	}
	if err := mgr.Add(r); err != nil {
		panic(err)
	}
	if err := mgr.Start(signals.SetupSignalHandler()); err != nil {
		panic(err)
	}
}

type sfqaReconciler struct {
	cl          client.Client
	period      time.Duration
	params      squad.Params
	prevPending map[string]map[string]bool // flavor -> set(podKey) (직전 reconcile 의 대기 집합)
}

// Start 는 manager.Runnable: 주기적으로 reconcile 한다.
func (r *sfqaReconciler) Start(ctx context.Context) error {
	t := time.NewTicker(r.period)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case <-t.C:
			if err := r.reconcile(ctx); err != nil {
				ctrllog.Log.Error(err, "reconcile 실패")
			}
		}
	}
}

func (r *sfqaReconciler) reconcile(ctx context.Context) error {
	var nodeList corev1.NodeList
	if err := r.cl.List(ctx, &nodeList); err != nil {
		return err
	}
	var podList corev1.PodList
	if err := r.cl.List(ctx, &podList); err != nil {
		return err
	}

	// 1) 노드를 GPU 타입(flavor)별로 분류하고 allocatable 집계.
	nodeFlavor := map[string]string{}
	allocByFlavor := map[string]int{}
	for i := range nodeList.Items {
		n := &nodeList.Items[i]
		f := n.Labels[gpuProductLabel]
		if f == "" {
			f = "any"
		}
		nodeFlavor[n.Name] = f
		allocByFlavor[f] += gpuQty(n.Status.Allocatable)
	}

	// 2) 실행 중(노드 바인딩) GPU 사용량을 타입별로 → AR. 대기 Pod 는 flavor 별로 수집.
	usedByFlavor := map[string]int{}
	pendingByFlavor := map[string][]*corev1.Pod{}
	for i := range podList.Items {
		p := &podList.Items[i]
		g := podGPU(p)
		if g == 0 {
			continue
		}
		if p.Spec.NodeName != "" && p.Status.Phase != corev1.PodSucceeded && p.Status.Phase != corev1.PodFailed {
			usedByFlavor[nodeFlavor[p.Spec.NodeName]] += g
			continue
		}
		if p.Spec.SchedulerName == schedulerName && p.Spec.NodeName == "" && p.Status.Phase == corev1.PodPending {
			f := p.Labels[flavorAnno]
			if f == "" {
				f = "any"
			}
			pendingByFlavor[f] = append(pendingByFlavor[f], p)
		}
	}

	// 3) flavor 별로 P* 계산 후 annotation 주입.
	for f, pods := range pendingByFlavor {
		total := allocByFlavor[f]
		ar := 0.0
		if total > 0 {
			ar = float64(usedByFlavor[f]) / float64(total) * 100
		}
		servers := buildServers(nodeList.Items, nodeFlavor, podList.Items, f)

		// age 갱신: 직전 대기집합 대비 사라진 Pod 가 있으면(=스케줄됨) 이 flavor 리셋.
		curSet := map[string]bool{}
		for _, p := range pods {
			curSet[key(p)] = true
		}
		scheduled := false
		for k := range r.prevPending[f] {
			if !curSet[k] {
				scheduled = true
				break
			}
		}
		jobs := make([]squad.PendingJob, len(pods))
		for i, p := range pods {
			jobs[i] = squad.PendingJob{
				ID: key(p), GPUCount: podGPU(p), GPUType: squad.GPUType(f),
				Age: r.advanceAge(ctx, p, scheduled),
			}
		}
		r.prevPending[f] = curSet

		ordered := squad.ReorderQueue(jobs, servers, squad.GPUType(f), r.params, ar)
		for _, j := range ordered {
			r.patchScore(ctx, j.ID, int64(j.PStar*1e6))
		}
	}
	return nil
}

// advanceAge 는 Pod 의 squad.io/age 를 벽시계 기반으로 갱신하고 현재 age 를 돌려준다.
func (r *sfqaReconciler) advanceAge(ctx context.Context, p *corev1.Pod, scheduledInFlavor bool) int {
	age := 0
	if v, ok := p.Annotations[ageAnno]; ok {
		age, _ = strconv.Atoi(v)
	}
	now := time.Now()
	if scheduledInFlavor {
		age = 0 // C++ job_scheduler.cpp:48-52 큐 전체 리셋
	} else if v, ok := p.Annotations[ageUpdatedAnno]; ok {
		if t0, err := time.Parse(time.RFC3339, v); err == nil {
			steps := int(now.Sub(t0).Minutes()) / ageStepMinutes
			age += steps
		}
	}
	r.patchAnno(ctx, p.Namespace, p.Name, map[string]string{
		ageAnno: strconv.Itoa(age), ageUpdatedAnno: now.Format(time.RFC3339),
	})
	return age
}

func (r *sfqaReconciler) patchScore(ctx context.Context, podKey string, score int64) {
	ns, name := splitKey(podKey)
	r.patchAnno(ctx, ns, name, map[string]string{scoreAnno: strconv.FormatInt(score, 10)})
}

func (r *sfqaReconciler) patchAnno(ctx context.Context, ns, name string, anno map[string]string) {
	patch := []byte(annoPatch(anno))
	_ = r.cl.Patch(ctx, &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{Namespace: ns, Name: name},
	}, client.RawPatch(types.StrategicMergePatchType, patch))
}

// buildServers 는 지정 flavor 노드들을 squad.Server(가용 슬롯) 모델로 만든다.
func buildServers(nodes []corev1.Node, nodeFlavor map[string]string, pods []corev1.Pod, flavor string) []squad.Server {
	usedPerNode := map[string]int{}
	for i := range pods {
		p := &pods[i]
		if p.Spec.NodeName != "" && p.Status.Phase != corev1.PodSucceeded && p.Status.Phase != corev1.PodFailed {
			usedPerNode[p.Spec.NodeName] += podGPU(p)
		}
	}
	var out []squad.Server
	for i := range nodes {
		n := &nodes[i]
		if nodeFlavor[n.Name] != flavor {
			continue
		}
		total := gpuQty(n.Status.Allocatable)
		if total > squad.AccelPerServerMax {
			total = squad.AccelPerServerMax
		}
		s := squad.Server{Name: n.Name, GPUType: squad.GPUType(flavor), Total: total}
		used := usedPerNode[n.Name]
		for j := 0; j < total; j++ {
			if j < used {
				s.Slots[j] = squad.SlotFixed
			} else {
				s.Slots[j] = squad.SlotEmpty
			}
		}
		out = append(out, s)
	}
	return out
}

// ── 헬퍼 ──
func podGPU(p *corev1.Pod) int {
	total := 0
	for i := range p.Spec.Containers {
		total += gpuQty(p.Spec.Containers[i].Resources.Limits)
	}
	return total
}

func gpuQty(rl corev1.ResourceList) int {
	if q, ok := rl[gpuResource]; ok {
		return int(q.Value())
	}
	return 0
}

func key(p *corev1.Pod) string      { return p.Namespace + "/" + p.Name }
func splitKey(k string) (string, string) {
	for i := 0; i < len(k); i++ {
		if k[i] == '/' {
			return k[:i], k[i+1:]
		}
	}
	return "default", k
}
func annoPatch(a map[string]string) string {
	s := `{"metadata":{"annotations":{`
	first := true
	for k, v := range a {
		if !first {
			s += ","
		}
		s += strconv.Quote(k) + ":" + strconv.Quote(v)
		first = false
	}
	return s + `}}}`
}
