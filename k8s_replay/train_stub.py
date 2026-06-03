"""real 모드 학습 스텁: PTR 이주 다운타임 정밀 측정용(소수 job).

실제 모델 가중치를 로드해 GPU 메모리를 점유하고, --seconds 동안 간단한 학습 루프를 돌며
주기적으로 체크포인트를 기록한다. PTR 이주(evict→재생성) 시 CKPT_PATH 에서 경과를 읽어 resume
하므로, 다운타임 = evict~resume 구간으로 실측된다. holder 와 달리 실제 연산/메모리 패턴을 갖는다.
"""
import argparse
import os
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--seconds", type=int, default=300)
    ap.add_argument("--ckpt-every", type=int, default=10)
    args = ap.parse_args()

    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    # 실제 모델 가중치 일부를 메모리에 올려 현실적 풋프린트(생략 시 무거운 텐서로 대체).
    if args.model and os.path.isdir(os.path.expanduser("~/.cache/huggingface")):
        try:
            from transformers import AutoModelForCausalLM
            AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16).to(dev)
            print(f"[train] loaded {args.model}", flush=True)
        except Exception as e:
            print(f"[train] 모델 로드 생략({e})", flush=True)

    w = torch.randn(8192, 8192, device=dev, requires_grad=True)
    opt = torch.optim.SGD([w], lr=1e-4)

    ckpt = os.environ.get("CKPT_PATH", "")
    elapsed = 0
    if ckpt and os.path.exists(ckpt):
        try:
            elapsed = int(float(open(ckpt).read().strip() or 0))
            print(f"[train] resume @ {elapsed}s", flush=True)
        except Exception:
            elapsed = 0

    t0 = time.time() - elapsed
    last_ckpt = elapsed
    while elapsed < args.seconds:
        x = torch.randn(8192, 8192, device=dev)
        loss = (w @ x).pow(2).mean()
        loss.backward()
        opt.step()
        opt.zero_grad()
        elapsed = int(time.time() - t0)
        if ckpt and elapsed - last_ckpt >= args.ckpt_every:
            try:
                os.makedirs(os.path.dirname(ckpt), exist_ok=True)
                open(ckpt, "w").write(str(elapsed))
                last_ckpt = elapsed
            except Exception:
                pass
    print(f"[train] done @ {elapsed}s", flush=True)


if __name__ == "__main__":
    main()
