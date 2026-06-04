#!/bin/bash
# EASY-noisy 실험 (Mu'alem & Feitelson f-모델, 사용자 승인 2026-06-04 밤):
# EASY 예약이 보는 duration을 est=dur×(1+U[0,f])로 오염(f=1, 3). holder 실행은 실제 그대로.
# 동일 조건: JCT≤2h, 윈도우 d51~65, 층화 500, S=360, cap 없음. run당 ~1h.
set -u
SC=/home/mystous/gpu_scheduler/squad_ctrl
export KUBECONFIG=/home/mystous/.kube/config
CLOG=/raid/squad/runs/chain_fid.log
log(){ echo "[$(date '+%m-%d %T')] $*" | tee -a "$CLOG"; }

F="--sample 500 --drop-over 7200 --window-start-day 51 --window-days 14 \
--kappa 360 --min-dur 5 --max-dur 1000000000 --submit-clamp 0 --timeout 10000"

log "=== NOISY-EASY START (f-model) ==="
log "1/2 f360_easyf1 (f=1: 추정 1~2x)"
"$SC/run_one.sh" easy f360_easyf1 "" "$F --est-noise-f 1"
log "2/2 f360_easyf3 (f=3: 추정 1~4x)"
"$SC/run_one.sh" easy f360_easyf3 "" "$F --est-noise-f 3"
log "=== NOISY-EASY DONE ==="
