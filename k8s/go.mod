module github.com/mystous/gpu_scheduler/k8s

go 1.22

// 핵심 알고리즘 패키지(pkg/squad)는 표준 라이브러리만 사용 — 외부 의존성 없음(go test 검증됨).
// 아래 require/replace 는 컨트롤러(controller-runtime)와 커스텀 스케줄러(k8s.io/kubernetes
// Scheduler Framework, out-of-tree 플러그인) 빌드용이다. k8s v1.31 라인에 고정.
//
// 방화벽으로 GOPROXY/go.googlesource.com 이 막혀 있으므로, 인터넷 되는 외부 머신에서
//   go mod tidy && go mod vendor
// 로 vendor/ 를 만들어 이 디렉토리에 반입한 뒤 `go build -mod=vendor` 로 오프라인 빌드한다.
// (자세한 절차: k8s/BUILD.md)

require (
	k8s.io/api v0.31.0
	k8s.io/apimachinery v0.31.0
	k8s.io/client-go v0.31.0
	k8s.io/component-base v0.31.0
	k8s.io/kubernetes v1.31.0
	sigs.k8s.io/controller-runtime v0.19.0
)

// k8s.io/kubernetes 를 의존하면 staging 모듈을 동일 버전으로 replace 해야 한다(표준 패턴).
replace (
	k8s.io/api => k8s.io/api v0.31.0
	k8s.io/apiextensions-apiserver => k8s.io/apiextensions-apiserver v0.31.0
	k8s.io/apimachinery => k8s.io/apimachinery v0.31.0
	k8s.io/apiserver => k8s.io/apiserver v0.31.0
	k8s.io/cli-runtime => k8s.io/cli-runtime v0.31.0
	k8s.io/client-go => k8s.io/client-go v0.31.0
	k8s.io/cloud-provider => k8s.io/cloud-provider v0.31.0
	k8s.io/cluster-bootstrap => k8s.io/cluster-bootstrap v0.31.0
	k8s.io/code-generator => k8s.io/code-generator v0.31.0
	k8s.io/component-base => k8s.io/component-base v0.31.0
	k8s.io/component-helpers => k8s.io/component-helpers v0.31.0
	k8s.io/controller-manager => k8s.io/controller-manager v0.31.0
	k8s.io/cri-api => k8s.io/cri-api v0.31.0
	k8s.io/cri-client => k8s.io/cri-client v0.31.0
	k8s.io/csi-translation-lib => k8s.io/csi-translation-lib v0.31.0
	k8s.io/dynamic-resource-allocation => k8s.io/dynamic-resource-allocation v0.31.0
	k8s.io/endpointslice => k8s.io/endpointslice v0.31.0
	k8s.io/kms => k8s.io/kms v0.31.0
	k8s.io/kube-aggregator => k8s.io/kube-aggregator v0.31.0
	k8s.io/kube-controller-manager => k8s.io/kube-controller-manager v0.31.0
	k8s.io/kube-proxy => k8s.io/kube-proxy v0.31.0
	k8s.io/kube-scheduler => k8s.io/kube-scheduler v0.31.0
	k8s.io/kubectl => k8s.io/kubectl v0.31.0
	k8s.io/kubelet => k8s.io/kubelet v0.31.0
	k8s.io/metrics => k8s.io/metrics v0.31.0
	k8s.io/mount-utils => k8s.io/mount-utils v0.31.0
	k8s.io/pod-security-admission => k8s.io/pod-security-admission v0.31.0
	k8s.io/sample-apiserver => k8s.io/sample-apiserver v0.31.0
)
