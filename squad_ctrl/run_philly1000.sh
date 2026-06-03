#!/bin/bash
# Philly 1000 층화샘플(전체 GPU·duration 분포 보존) × 다정책 5종.
# age 수정(=대기시간/age_unit), SFQA β=100(경합에서도 발동) 반영.
set -u
VENV=/raid/squad/venv/bin/python
RE=/home/mystous/gpu_scheduler/squad_ctrl/run_experiment.py
CTRL=/home/mystous/gpu_scheduler/squad_ctrl/policy_controller.py
export KUBECONFIG=/home/mystous/.kube/config
PH=/raid/squad/traces/philly/repo/trace-data/cluster_job_log
LOG=/raid/squad/runs/run_philly1000.log
: > "$LOG"
COMMON="--trace philly --input $PH --sample 1000 --seed 42 --kappa 3000 --min-dur 6 --max-dur 8 --submit-clamp 0 --gpu-types NVIDIA-B200 --timeout 7200"

clean(){ kubectl delete jobs --all -n squad >/dev/null 2>&1; kubectl delete pods --all -n squad >/dev/null 2>&1; sleep 6; }

run(){  # policy runid ctrl_extra
  clean
  echo "[$(date '+%T')] policy=$1 run=$2" | tee -a "$LOG"
  if [ "$1" != "none" ]; then
    $VENV $CTRL --policy "$1" --period 5 $3 > /raid/squad/runs/${2}_ctrl.log 2>&1 &
    echo $! > /raid/squad/${2}.pid
    sleep 3
  fi
  $VENV $RE $COMMON --policy "$1" --run-id "$2" >> "$LOG" 2>&1
  [ -f /raid/squad/${2}.pid ] && kill "$(cat /raid/squad/${2}.pid)" 2>/dev/null && rm -f /raid/squad/${2}.pid
}

run none p_base ""
run fifo p_fifo ""
run sjf  p_sjf  ""
run las  p_las  ""
run sfqa p_sfqa "--beta 100 --age-unit 10"
echo "[$(date '+%T')] ALL DONE" | tee -a "$LOG"
