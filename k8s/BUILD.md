# SQUAD-K8s 빌드 가이드 (방화벽 환경 — 외부 vendor 반입)

이 클러스터는 GOPROXY·`go.googlesource.com`·docker hub·go.dev 가 모두 방화벽에 막혀 있다.
github 과 PyPI 는 열려 있다. 따라서 Go 모듈 의존성은 **인터넷 되는 외부 머신에서 vendor 를
만들어 반입**한 뒤 오프라인 빌드한다.

## 0. 무엇이 검증됐나
- `pkg/squad` (SFQA/PTR 알고리즘 코어)는 표준 라이브러리만 사용 → 이미 `go test ./pkg/squad/` 6/6 PASS.
- 빌드가 필요한 것: `cmd/scheduler`(QueueSort 플러그인), `cmd/sfqa-controller`, `cmd/ptr-controller`.

## 1. 외부(인터넷) 머신에서 vendor 생성
이 `k8s/` 디렉토리 전체를 인터넷 되는 머신(노트북 등, Go 1.22 설치)으로 복사한 뒤:
```bash
cd k8s
go mod tidy          # require/replace 해석 + go.sum 생성
go mod vendor        # 모든 의존성을 vendor/ 로 고정
go build ./...       # (선택) 외부에서 빌드 검증
tar czf squad-vendor.tgz vendor go.sum
```
`go mod tidy` 가 staging replace 목록을 조정할 수 있다(정상). 빌드까지 통과하면 vendor 가 완전한 것.

## 2. 클러스터로 반입
```bash
# 외부 머신 → 이 노드
scp squad-vendor.tgz mystous@<this-node>:/home/mystous/gpu_scheduler/k8s/
# (또는 비공개 HF dataset 경유: huggingface-cli upload/download)
cd /home/mystous/gpu_scheduler/k8s && tar xzf squad-vendor.tgz
```

## 3. 오프라인 빌드 (이 노드)
```bash
cd /home/mystous/gpu_scheduler/k8s
export GOFLAGS=-mod=vendor GOCACHE=/raid/squad/tools/gocache
go build -o /raid/squad/bin/squad-scheduler   ./cmd/scheduler
go build -o /raid/squad/bin/sfqa-controller   ./cmd/sfqa-controller
go build -o /raid/squad/bin/ptr-controller    ./cmd/ptr-controller
go test -mod=vendor ./pkg/squad/              # 재검증
```

## 4. 컨테이너 이미지 → kind 로드
docker hub 가 막혔으므로 베이스 이미지는 **이미 로컬에 있는 것**을 쓴다
(`kindest/node:v1.31.0`, 그리고 registry.k8s.io 는 열려 있어 `registry.k8s.io/kube-scheduler:v1.31.0` pull 가능).
정적 바이너리(CGO_ENABLED=0)면 distroless 없이 scratch 도 가능:
```bash
CGO_ENABLED=0 go build -mod=vendor -o squad-scheduler ./cmd/scheduler   # 정적 빌드
# 간단한 이미지 빌드(로컬 베이스 사용) 후 kind 로드:
sudo docker build -t squad/scheduler:dev -f deploy/Dockerfile.scheduler .
sudo kind load docker-image squad/scheduler:dev --name <cluster>
```
`<cluster>` 는 `kubectl config current-context`(예: kind-llmd)에서 확인.

## 5. 배포
```bash
kubectl apply -f deploy/namespace.yaml
kubectl -n squad create configmap squad-holder --from-file=../k8s_replay/holder.py
kubectl apply -f deploy/rbac.yaml
kubectl apply -f deploy/scheduler.yaml          # secondary scheduler (schedulerName=squad-scheduler)
kubectl apply -f deploy/sfqa-controller.yaml
kubectl apply -f deploy/ptr-controller.yaml
```

## 빌드가 막힐 때 폴백
- `go mod tidy` 가 특정 모듈에서 실패하면 그 모듈만 버전을 맞춰 `go.mod` require 에 추가.
- 최악의 경우 `cmd/scheduler`(k8s.io/kubernetes 거대 의존)만 외부에서 **바이너리로 빌드해 반입**하고
  컨트롤러 2개는 controller-runtime 만 의존하므로 vendor 가 가볍다(분리 빌드 가능).
