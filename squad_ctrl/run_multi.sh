#!/bin/bash
# 다정책 스케줄러 비교: 동일 트레이스(Alibaba v2023, limit40 경합)에서
# baseline(none=순수 default FIFO) + gate기반 FIFO/SJF/LAS/SFQA 5종.
set -u
VENV=/raid/squad/venv/bin/python
RE=/home/mystous/gpu_scheduler/squad_ctrl/run_experiment.py
CTRL=/home/mystous/gpu_scheduler/squad_ctrl/policy_controller.py
export KUBECONFIG=/home/mystous/.kube/config
A23=/raid/squad/traces/alibaba_repo/cluster-trace-gpu-v2023/csv/openb_pod_list_default.csv
LOG=/raid/squad/runs/run_multi.log
: > "$LOG"
COMMON="--trace alibaba2023 --input $A23 --limit 40 --kappa 3000 --min-dur 20 --max-dur 60 --gpu-types NVIDIA-B200"

clean(){ kubectl delete jobs --all -n squad >/dev/null 2>&1; kubectl delete pods --all -n squad >/dev/null 2>&1; sleep 6; }

run_policy(){  # policy runid
  clean
  echo "[$(date '+%T')] policy=$1 run=$2" | tee -a "$LOG"
  $VENV $CTRL --policy "$1" --period 5 > /raid/squad/runs/${2}_ctrl.log 2>&1 &
  echo $! > /raid/squad/${2}.pid
  sleep 3
  $VENV $RE $COMMON --policy "$1" --run-id "$2" >> "$LOG" 2>&1
  kill "$(cat /raid/squad/${2}.pid)" 2>/dev/null
}

# baseline: gate 없음(순수 default-scheduler FIFO)
clean
echo "[$(date '+%T')] policy=none run=m_base" | tee -a "$LOG"
$VENV $RE $COMMON --policy none --run-id m_base >> "$LOG" 2>&1

run_policy fifo m_fifo
run_policy sjf  m_sjf
run_policy las  m_las
run_policy sfqa m_sfqa
echo "[$(date '+%T')] ALL DONE" | tee -a "$LOG"
