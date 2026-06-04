# 로컬 컨테이너 이미지 인벤토리 (실모델 캠페인 사전조사, 2026-06-04)

> 목적: 방화벽(Docker Hub·nvcr blob 차단) 하에서 실모델 워크로드(리젝 ① 보강)에
> 당장 쓸 수 있는 이미지 확인. 조사: `docker images` + kind 노드 내 `crictl images`.

## 1. 핵심 발견

| 이미지 | 위치 | 내용 | 의미 |
|---|---|---|---|
| `localhost/mystous/vllm_hybrid:v1.9-claudeworks` | 호스트(247GB) + **kind 노드 캐시(119GB)** | venv `/workspace/vllm_dev_prj`: **torch 2.11.0+cu128, torchrun, transformers** (Python 3.12.13, CUDA 12.8 = B200 OK) | **실제 학습 잡 지금 가능** — 방화벽 개방 불필요. HF 모델은 hostPath(`/raid/hf_cache`) 마운트 |
| `nvcr.io/nvidia/k8s/dcgm-exporter:4.5.3-4.8.2-distroless` | **kind 노드 캐시** | DCGM exporter | **GPU util/메모리 실측 가능** — "nvcr blob 차단으로 설치 불가" 결론 뒤집힘. Prometheus 없이 metrics endpoint 직접 scrape |
| `nvcr.io/nvidia/k8s-device-plugin:v0.16.2` | kind 노드 | GPU device plugin | 이미 사용 중 |
| `squad/holder:dev` | 호스트+노드 (3MB) | GPU-holder 스텁 | 기존 실험용 |

## 2. 주의·제약

- **vLLM 추론**: 이미지 내 시스템 python·venv 모두 `import vllm` 실패(editable install 잔재만 확인,
  `/tmp/vllm_env_restore*.sh` 복구 스크립트 존재). 추론 잡은 (a) venv 내 vllm 복구 시도,
  (b) torch 직접 generate 루프, (c) 방화벽 개방 후 정식 vLLM 이미지 중 택1. **학습 잡이 먼저**.
- **⚠️ 보안**: 이미지 내부에 `/workspace/github_gph` 파일 존재(인증 파일과 동일 이름 — 내용 미확인,
  접근하지 않음). 이미지가 `localhost/` 전용이라 외부 유출은 없으나, **이 이미지는 어떤 레지스트리에도
  push 금지**. 캠페인용으로는 venv만 추출한 슬림 이미지 재빌드 권장(자격증명·소스 제외).
- entrypoint 미지정 워크로드 실행 형태: `command: ["/workspace/vllm_dev_prj/bin/torchrun", ...]`
  + hostPath로 `/raid/hf_cache` 마운트(kind extraMounts 설정은 `~/k8s_llmd/kind-gpu.yaml` 확인).

## 3. 캠페인 적용 (승인 후)

1. `k8s_replay/model_assign.py` `run_mode="train"` 추가: 이미지=`mystous/vllm_hybrid:v1.9-claudeworks`,
   command=torchrun finetune 스텁(`train_stub.py` 확장), S-스케일링 이터레이션 수 계산.
2. DCGM-exporter DaemonSet 배포(캐시 이미지, `imagePullPolicy: Never`) → `metrics_collector.py`에
   DCGM scrape 추가(per-pod GPU util·FB 메모리).
3. 콜로케이션 간섭 실험: 같은 노드 2 학습 잡 → throughput 저하 % (리젝 ① 메모리 경합 지적).
