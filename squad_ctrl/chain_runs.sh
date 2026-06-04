#!/bin/bash
# 본 체인 (Philly 1000, 기존과 동일 조건 κ=3000) — 직렬 실행, 총 ~4h
# 1) EASY  2) Kueue 설치+run  3) sfqa-auto τ=1 (H2 재시험)  4) κ=6000 한 점(고정 vs auto)
set -u
SC=/home/mystous/gpu_scheduler/squad_ctrl
export KUBECONFIG=/home/mystous/.kube/config
CLOG=/raid/squad/runs/chain.log
log(){ echo "[$(date '+%m-%d %T')] $*" | tee -a "$CLOG"; }

log "=== CHAIN START (Philly 1000) ==="

# 1) EASY-backfilling — duration 정보를 쓰는 고전 표준 베이스라인
log "1/4 p_easy"
"$SC/run_one.sh" easy p_easy "" ""

# 2) Kueue — 같은 레이어 프로덕션 표준
log "2/4 Kueue install"
kubectl apply --server-side -f /raid/squad/kueue/manifests.yaml >> "$CLOG" 2>&1
kubectl -n kueue-system rollout status deployment/kueue-controller-manager --timeout=300s >> "$CLOG" 2>&1
sleep 10
kubectl apply -f "$SC/kueue-queues.yaml" >> "$CLOG" 2>&1
sleep 5
log "2/4 p_kueue"
"$SC/run_one.sh" kueue p_kueue "" ""

# 3) sfqa-auto τ=1 — 압축 시간계 차원 정합 보정 후 H2(p50) 재시험
log "3/4 p_auto_t1"
"$SC/run_one.sh" sfqa-auto p_auto_t1 "--tau 1" ""

# 4) κ=6000 한 점: 고정 SFQA(κ3000 튜닝값 그대로) vs auto(무튜닝) — 불변성·전이성
log "4/4 kappa 6000 pair"
"$SC/run_one.sh" sfqa      p_sfqa_k6000 "--beta 100 --age-unit 10" "--kappa 6000"
"$SC/run_one.sh" sfqa-auto p_auto_k6000 "--tau 1" "--kappa 6000"

log "=== CHAIN DONE ==="
