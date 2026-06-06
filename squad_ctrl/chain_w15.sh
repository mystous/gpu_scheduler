#!/bin/bash
# Philly-300-C48-W15 경향성 체인 (사용자 확정 2026-06-06): 5정책, run당 ~2.2h, 총 ~11h
#  - cap 48h 클램프 / 윈도우 day 65~80(일감 최대 15일) / 층화 300(seed 42) / S=240(1s=4분)
#  - 부하 1.17×(임계+), peak 3.8×, 바닥 37%, 실행 dur 5s~12분 (EASY 예약 작동권)
#  - 순서: auto → EASY → Kueue → SFQA(고정) → gate-FIFO
set -u
SC=/home/mystous/gpu_scheduler/squad_ctrl
export KUBECONFIG=/home/mystous/.kube/config
CLOG=/raid/squad/runs/chain_w15.log
log(){ echo "[$(date '+%m-%d %T')] $*" | tee -a "$CLOG"; }

F="--sample 300 --clamp-over 172800 --window-start-day 65 --window-days 15 \
--kappa 240 --min-dur 5 --max-dur 1000000000 --submit-clamp 0 --timeout 9000"

log "=== W15 CHAIN START (5 policies, S=240) ==="
log "1/5 w15_auto"
"$SC/run_one.sh" sfqa-auto w15_auto "" "$F"
log "2/5 w15_easy"
"$SC/run_one.sh" easy w15_easy "" "$F"
log "3/5 w15_kueue"
"$SC/run_one.sh" kueue w15_kueue "" "$F"
log "4/5 w15_sfqa"
"$SC/run_one.sh" sfqa w15_sfqa "--beta 100 --age-unit 10" "$F"
log "5/5 w15_fifo"
"$SC/run_one.sh" fifo w15_fifo "" "$F"
log "=== W15 CHAIN DONE ==="
