"""GPU-holder 스텁: 압축된 duration 만큼 GPU 를 점유하고 종료한다.

실제 모델 연산을 하지 않으므로 수천 job 을 유한 시간에 재생할 수 있다. 스케줄러가 보는
도착/점유/종료/요청량은 실제 워크로드와 동일하다. 선점 가능 job 은 주기적으로 경과시간을
체크포인트에 기록하고, PTR 이주(evict→재생성) 후 그 지점부터 resume 한다 → 이주 다운타임 측정.

환경변수: HOLD_SEC(점유 초), GPU_COUNT(요청 GPU 수), PREEMPTIBLE(0/1), CKPT_PATH(체크포인트 파일).
"""
import os
import time
import sys


def main():
    dur = float(os.environ.get("HOLD_SEC", "60"))
    preempt = os.environ.get("PREEMPTIBLE", "0") == "1"
    ckpt = os.environ.get("CKPT_PATH", "")

    bufs = []
    try:
        import torch
        n = torch.cuda.device_count()
        for i in range(n):
            # GPU 당 ~0.8GB 점유 → DCGM FB_USED 에 잡혀 배치가 가시화된다.
            bufs.append(torch.zeros(200_000_000, dtype=torch.float32, device=f"cuda:{i}"))
        print(f"[holder] {n} GPU 점유, hold={dur:.0f}s preempt={preempt}", flush=True)
    except Exception as e:  # torch/cuda 불가 시 sleep 만 (스케줄링 동역학엔 무해)
        print(f"[holder] torch/cuda 불가({e}), sleep-only hold={dur:.0f}s", flush=True)

    elapsed = 0.0
    if preempt and ckpt and os.path.exists(ckpt):
        try:
            elapsed = float(open(ckpt).read().strip())
            print(f"[holder] resume @ {elapsed:.0f}s (이주 후 재개)", flush=True)
        except Exception:
            elapsed = 0.0

    step = 5.0
    while elapsed < dur:
        for b in bufs:  # 가벼운 연산으로 util 발생(점유 가시화)
            b.add_(1.0)
        time.sleep(min(step, dur - elapsed))
        elapsed += step
        if preempt and ckpt:
            try:
                os.makedirs(os.path.dirname(ckpt), exist_ok=True)
                with open(ckpt, "w") as f:
                    f.write(str(elapsed))
            except Exception:
                pass
    print(f"[holder] done @ {elapsed:.0f}s", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
