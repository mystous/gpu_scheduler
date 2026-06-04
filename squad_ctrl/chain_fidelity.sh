#!/bin/bash
# 충실 duration 경향성 체인 v3 (사용자 확정, 2026-06-04 저녁):
#  - 모집단: Philly − duration>2h 제거(18.6%) / 윈도우 day 51~65(multi-GPU 최다) / 층화 500(seed 42)
#  - 정규화: S=360(실험 1s=실세계 3분), cap 없음, 바닥 5s(~77% — 초고속 경향 모드)
#  - 실행 dur 5~20s, peak 24 GPU(3.0×), run당 ~1.9h → 3정책 ~6h
#  - 정책: EASY, sfqa-auto(τ=10), Kueue (사용자 지정 3종)
set -u
SC=/home/mystous/gpu_scheduler/squad_ctrl
export KUBECONFIG=/home/mystous/.kube/config
CLOG=/raid/squad/runs/chain_fid.log
log(){ echo "[$(date '+%m-%d %T')] $*" | tee -a "$CLOG"; }

F="--sample 500 --drop-over 7200 --window-start-day 51 --window-days 14 \
--kappa 360 --min-dur 5 --max-dur 1000000000 --submit-clamp 0 --timeout 10000"

log "=== FIDELITY v3 START (JCT<=2h, S=360, EASY/auto/Kueue) ==="
log "1/3 f360_easy"
"$SC/run_one.sh" easy f360_easy "" "$F"
log "2/3 f360_auto (tau=10)"
"$SC/run_one.sh" sfqa-auto f360_auto "" "$F"
log "3/3 f360_kueue"
"$SC/run_one.sh" kueue f360_kueue "" "$F"
log "=== FIDELITY v3 DONE ==="
