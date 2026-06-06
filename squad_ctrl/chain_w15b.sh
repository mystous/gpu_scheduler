#!/bin/bash
# W15 체인 후속 (사용자 변경 2026-06-06 10:30): EASY를 오차 주입 버전으로 교체.
#  - w15_auto는 완료(보존). 잔여: EASY-noisy(f=1) → Kueue → SFQA → gate-FIFO
#  - EASY 예약이 보는 추정 = 실제 × (1+U[0,1]) (Mu'alem&Feitelson f-모델), 실행은 실제 그대로
set -u
SC=/home/mystous/gpu_scheduler/squad_ctrl
export KUBECONFIG=/home/mystous/.kube/config
CLOG=/raid/squad/runs/chain_w15.log
log(){ echo "[$(date '+%m-%d %T')] $*" | tee -a "$CLOG"; }

F="--sample 300 --clamp-over 172800 --window-start-day 65 --window-days 15 \
--kappa 240 --min-dur 5 --max-dur 1000000000 --submit-clamp 0 --timeout 9000"

log "=== W15b CHAIN (EASY->noisy f=1, then Kueue/SFQA/FIFO) ==="
log "2/5 w15_easy (est-noise f=1)"
"$SC/run_one.sh" easy w15_easy "" "$F --est-noise-f 1"
log "3/5 w15_kueue"
"$SC/run_one.sh" kueue w15_kueue "" "$F"
log "4/5 w15_sfqa"
"$SC/run_one.sh" sfqa w15_sfqa "--beta 100 --age-unit 10" "$F"
log "5/5 w15_fifo"
"$SC/run_one.sh" fifo w15_fifo "" "$F"
log "=== W15 CHAIN DONE ==="
