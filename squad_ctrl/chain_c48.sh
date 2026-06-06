#!/bin/bash
# Philly-2K-C48 경향성 체인 (사용자 확정 2026-06-05): Kueue → EASY → sfqa-auto
#  - 워크로드: 층화 2000(seed 42), JCT>48h 클램프(잡 제거 0, GPU 구성 원본 87/2/5/6%)
#  - 부하: 평균 1.01×(임계), peak 8.5× / 정규화: S=1600(1s≈27분), cap 없음, 바닥 5s(82%)
#  - run당 ~1.83h → 총 ~5.7h (6시간 예산)
set -u
SC=/home/mystous/gpu_scheduler/squad_ctrl
export KUBECONFIG=/home/mystous/.kube/config
CLOG=/raid/squad/runs/chain_c48.log
log(){ echo "[$(date '+%m-%d %T')] $*" | tee -a "$CLOG"; }

F="--sample 2000 --clamp-over 172800 --kappa 1600 --min-dur 5 --max-dur 1000000000 \
--submit-clamp 0 --timeout 8000"

log "=== C48 CHAIN START (S=1600, Kueue/EASY/auto) ==="
log "1/3 c48_kueue"
"$SC/run_one.sh" kueue c48_kueue "" "$F"
log "2/3 c48_easy"
"$SC/run_one.sh" easy c48_easy "" "$F"
log "3/3 c48_auto (tau=10)"
"$SC/run_one.sh" sfqa-auto c48_auto "" "$F"
log "=== C48 CHAIN DONE ==="
