// ptr-controller 는 PTR(디프래그)의 실행기다. 주기적으로 클러스터의 GPU 슬롯 모델을 만들어
// squad.Defrag(DP)로 "완전히 빈 server 수"를 최대화하는 이주 계획을 구하고, 그 계획대로
// 선점 가능 Pod 를 checkpoint→evict→재생성(resume) 하면서 실제 이주 다운타임을 측정한다.
//
// 멀티노드·이종 일반화: server=노드(동일 GPU 타입 간 이주). 단일 노드에선 이주 대상이 없어
// 무동작이지만 코드는 노드 수에 일반적이다. C++ adjusting_server::defragementation 의 포팅.
package main

import (
	"context"
	"flag"
	"time"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
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
	preemptibleLbl  = "squad.io/preemptible"
	jobIDLbl        = "squad.io/job-id"
)

func main() {
	var period time.Duration
	var omega, dpMax int
	flag.DurationVar(&period, "period", 15*time.Second, "reconcile 주기")
	flag.IntVar(&omega, "omega", squad.DefaultDefragCriteria, "ω 대기큐 길이 임계")
	flag.IntVar(&dpMax, "dp-max", squad.DefaultDPExecutionMax, "δ DP 재귀 상한")
	flag.Parse()
	ctrllog.SetLogger(zap.New())

	mgr, err := manager.New(mustConfig(), manager.Options{})
	if err != nil {
		panic(err)
	}
	r := &ptrReconciler{cl: mgr.GetClient(), period: period, omega: omega, dpMax: dpMax}
	if err := mgr.Add(r); err != nil {
		panic(err)
	}
	if err := mgr.Start(signals.SetupSignalHandler()); err != nil {
		panic(err)
	}
}

type ptrReconciler struct {
	cl         client.Client
	period     time.Duration
	omega      int
	dpMax      int
	lastSched  int // 직전 스케줄된 Pod 수(do_defragmentation 게이트용)
}

func (r *ptrReconciler) Start(ctx context.Context) error {
	t := time.NewTicker(r.period)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case <-t.C:
			if err := r.reconcile(ctx); err != nil {
				ctrllog.Log.Error(err, "ptr reconcile 실패")
			}
		}
	}
}

func (r *ptrReconciler) reconcile(ctx context.Context) error {
	var nodes corev1.NodeList
	if err := r.cl.List(ctx, &nodes); err != nil {
		return err
	}
	var pods corev1.PodList
	if err := r.cl.List(ctx, &pods); err != nil {
		return err
	}

	// 게이트 1: 대기큐 길이 ≥ ω (C++ job_emulator.cpp:322)
	pending, scheduled := 0, 0
	for i := range pods.Items {
		p := &pods.Items[i]
		if podGPU(p) == 0 {
			continue
		}
		if p.Spec.SchedulerName == schedulerName && p.Spec.NodeName == "" && p.Status.Phase == corev1.PodPending {
			pending++
		}
		if p.Spec.NodeName != "" && p.Status.Phase == corev1.PodRunning {
			scheduled++
		}
	}
	// 게이트 2: 직전 스텝 스케줄 발생(do_defragmentation, C++ :337-344)
	doDefrag := scheduled != r.lastSched
	r.lastSched = scheduled
	if pending < r.omega || !doDefrag {
		return nil
	}

	// GPU 타입(flavor)별로 독립 디프래그 — 이주는 동일 타입 server 간에만.
	flavors := map[string]bool{}
	for i := range nodes.Items {
		f := nodes.Items[i].Labels[gpuProductLabel]
		if f == "" {
			f = "any"
		}
		flavors[f] = true
	}
	for f := range flavors {
		servers, jobs := buildModel(nodes.Items, pods.Items, f)
		if len(jobs) == 0 {
			continue
		}
		d := squad.NewDefrag(servers, jobs, r.dpMax)
		improved, plan, before, after := d.Run()
		if !improved {
			continue
		}
		ctrllog.Log.Info("PTR 이주 계획", "flavor", f, "before", before, "after", after)
		r.executePlan(ctx, plan, servers, &pods)
	}
	return nil
}

// executePlan 은 이주 계획을 실행하며 다운타임을 측정한다.
// 현재 구현은 holder 스텁의 checkpoint→evict(삭제)→재생성(resume) 경로를 따른다.
// 실제 vLLM/torch 워크로드는 spec 의 squad/migrate-method 에 따라 분기(model_assign 참조).
func (r *ptrReconciler) executePlan(ctx context.Context, plan []squad.RunningJob, servers []squad.Server, pods *corev1.PodList) {
	byID := map[string]*corev1.Pod{}
	for i := range pods.Items {
		if id := pods.Items[i].Labels[jobIDLbl]; id != "" {
			byID[id] = &pods.Items[i]
		}
	}
	for _, j := range plan {
		if j.TargetIndex < 0 {
			continue // 이주 안 함
		}
		pod := byID[j.ID]
		if pod == nil {
			continue
		}
		t0 := time.Now()
		// 1) checkpoint 신호: holder 는 CKPT_PATH 에 경과시간을 주기 기록 중이므로 별도 신호 불필요.
		//    실제 워크로드는 여기서 checkpoint 훅을 호출(annotation/exec).
		// 2) evict: Pod 삭제(스케줄러가 우리 것이라 PDB 충돌 없음).
		_ = r.cl.Delete(ctx, pod, &client.DeleteOptions{
			GracePeriodSeconds: ptrInt64(10),
		})
		tEvict := time.Now()
		// 3) 재생성: 타겟 노드(servers[j.TargetIndex].Name)로 유도해 재배치 → resume.
		//    holder 는 CKPT_PATH 에서 경과를 읽어 이어서 점유 → 다운타임만큼만 손실.
		newPod := rebuildPod(pod, servers[j.TargetIndex].Name)
		_ = r.cl.Create(ctx, newPod)
		ctrllog.Log.Info("이주 다운타임",
			"job", j.ID,
			"target_node", servers[j.TargetIndex].Name,
			"evict_sec", tEvict.Sub(t0).Seconds(),
			"total_sec", time.Since(t0).Seconds())
		// 메트릭(squad_migration_downtime_seconds)은 별도 Prometheus exporter 로 노출.
	}
}

// rebuildPod 는 삭제된 Pod 사양을 복제해 타겟 노드로 nodeName 고정한 새 Pod 를 만든다.
func rebuildPod(old *corev1.Pod, targetNode string) *corev1.Pod {
	np := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:        old.Name + "-m",
			Namespace:   old.Namespace,
			Labels:      old.Labels,
			Annotations: old.Annotations,
		},
		Spec: *old.Spec.DeepCopy(),
	}
	np.Spec.NodeName = targetNode // 타겟 노드로 직접 배치(resume)
	np.ResourceVersion = ""
	np.Status = corev1.PodStatus{}
	return np
}

// buildModel 은 지정 flavor 노드들을 squad.Server 슬롯 모델로, 그 위의 선점가능 Running Pod 를
// squad.RunningJob 이주 후보로 만든다. C++ reconstruct_server_status 의 K8s 매핑.
func buildModel(nodes []corev1.Node, pods []corev1.Pod, flavor string) ([]squad.Server, []squad.RunningJob) {
	nodeFlavor := map[string]string{}
	idx := map[string]int{}
	var servers []squad.Server
	for i := range nodes {
		n := &nodes[i]
		f := n.Labels[gpuProductLabel]
		if f == "" {
			f = "any"
		}
		nodeFlavor[n.Name] = f
		if f != flavor {
			continue
		}
		total := gpuQty(n.Status.Allocatable)
		if total > squad.AccelPerServerMax {
			total = squad.AccelPerServerMax
		}
		idx[n.Name] = len(servers)
		servers = append(servers, squad.Server{Name: n.Name, GPUType: squad.GPUType(flavor), Total: total})
	}
	// 슬롯 채우기 + 선점가능 후보 수집.
	var jobs []squad.RunningJob
	cursor := map[string]int{}
	for i := range pods {
		p := &pods[i]
		if p.Spec.NodeName == "" || p.Status.Phase != corev1.PodRunning {
			continue
		}
		si, ok := idx[p.Spec.NodeName]
		if !ok {
			continue // 다른 flavor 노드
		}
		g := podGPU(p)
		if g == 0 {
			continue
		}
		preempt := p.Labels[preemptibleLbl] == "true"
		start := cursor[p.Spec.NodeName]
		for k := 0; k < g && start+k < servers[si].Total; k++ {
			if preempt {
				servers[si].Slots[start+k] = squad.SlotFloating
			} else {
				servers[si].Slots[start+k] = squad.SlotFixed
			}
			servers[si].JobIDs[start+k] = p.Labels[jobIDLbl]
		}
		cursor[p.Spec.NodeName] = start + g
		if preempt && g < servers[si].Total { // whole-server 미점유 선점 job 만 후보(C++ :114)
			jobs = append(jobs, squad.RunningJob{
				ID: p.Labels[jobIDLbl], GPUCount: g, GPUType: squad.GPUType(flavor),
				ServerIndex: si, TargetIndex: -1, Preemptible: true,
			})
		}
	}
	// 남은 슬롯은 empty.
	for si := range servers {
		for k := 0; k < servers[si].Total; k++ {
			if servers[si].Slots[k] == squad.SlotNone {
				servers[si].Slots[k] = squad.SlotEmpty
			}
		}
	}
	return servers, jobs
}

func podGPU(p *corev1.Pod) int {
	t := 0
	for i := range p.Spec.Containers {
		t += gpuQty(p.Spec.Containers[i].Resources.Limits)
	}
	return t
}
func gpuQty(rl corev1.ResourceList) int {
	if q, ok := rl[gpuResource]; ok {
		return int(q.Value())
	}
	return 0
}
func ptrInt64(v int64) *int64 { return &v }
