"""작업 실행 모드/모델 배정.

run_mode:
  holder — 압축 duration 만큼 GPU 를 점유하고 끝나는 스텁(대규모 스케줄링 재생의 기본).
           실제 모델 연산을 하지 않으므로 수천 job 을 유한 시간에 재생 가능.
  real   — 실제 모델(vLLM 추론 / torch 학습). PTR 다운타임·콜로케이션 정밀 측정용 소수 job.
"""
from __future__ import annotations
from dataclasses import dataclass

from common import CommonJob, WorkloadKind

# 캐시된 모델 풀(/raid/hf_cache/hub). gpu_count → (추론 모델, 학습 모델, TP).
MODEL_POOL = {
    1: ("Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct", 1),
    2: ("Qwen/Qwen2.5-14B-Instruct", "Qwen/Qwen2.5-3B-Instruct", 2),
    4: ("Qwen/Qwen2.5-32B-Instruct", "Qwen/Qwen2.5-7B-Instruct", 4),
    8: ("meta-llama/Llama-3.1-70B-Instruct", "meta-llama/Llama-3.1-8B-Instruct", 8),
}


def _pool_for(gpu_count: int):
    for k in (8, 4, 2, 1):
        if gpu_count >= k:
            return MODEL_POOL[k]
    return MODEL_POOL[1]


@dataclass
class ExecSpec:
    run_mode: str          # "holder" | "real"
    image: str
    command: list[str]
    args: list[str]
    model: str = ""        # real 모드일 때 HF repo id
    tp_size: int = 1
    env: dict | None = None


# 컨테이너 이미지. holder 는 방화벽 무관 로컬 scratch 이미지(kind load 됨).
HOLDER_IMAGE = "squad/holder:dev"
VLLM_IMAGE = "vllm/vllm-openai:latest"        # real 추론(정밀측정 시, 별도 확보 필요)
TRAIN_IMAGE = "pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime"  # real 학습(정밀측정 시)

HF_CACHE = "/raid/hf_cache"  # hostPath 마운트로 모델 재적재 현실화


def assign(job: CommonJob, run_mode: str = "holder") -> ExecSpec:
    """job 에 실행 스펙을 배정. 기본 holder, run_mode='real'이면 실제 모델."""
    if run_mode == "holder":
        # holder.py 를 ConfigMap 으로 /squad/holder.py 에 마운트(emit 참조).
        env = {
            "HOLD_SEC": str(int(job.duration)),
            "GPU_COUNT": str(job.gpu_count),
            "PREEMPTIBLE": "1" if job.preemptible else "0",
        }
        return ExecSpec(
            run_mode="holder", image=HOLDER_IMAGE,
            command=["/holder"], args=[], env=env,
        )

    infer_model, train_model, tp = _pool_for(job.gpu_count)
    if job.workload_kind == WorkloadKind.INFERENCE:
        # vLLM OpenAI 서버를 띄우고 짧게 self-bench (정밀 측정 시에만).
        return ExecSpec(
            run_mode="real", image=VLLM_IMAGE,
            command=["/bin/sh", "-c"],
            args=[f"vllm serve {infer_model} --tensor-parallel-size {tp} "
                  f"--download-dir {HF_CACHE}/hub & sleep {int(job.duration)}"],
            model=infer_model, tp_size=tp,
            env={"HF_HOME": HF_CACHE},
        )
    # 학습: torchrun fine-tune 스텁(체크포인트 디렉토리는 emit 에서 /raid/squad/ckpt 마운트).
    return ExecSpec(
        run_mode="real", image=TRAIN_IMAGE,
        command=["/bin/sh", "-c"],
        args=[f"torchrun --nproc_per_node={tp} /squad/train_stub.py "
              f"--model {train_model} --seconds {int(job.duration)}"],
        model=train_model, tp_size=tp,
        env={"HF_HOME": HF_CACHE},
    )
