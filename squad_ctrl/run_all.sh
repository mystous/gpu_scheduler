#!/bin/bash
# Alibaba v2023 / Philly × baseline/SFQA 순차 실측. 사내(1.5×)와 동일 부하.
set -u
VENV=/raid/squad/venv/bin/python
RE=/home/mystous/gpu_scheduler/squad_ctrl/run_experiment.py
CTRL=/home/mystous/gpu_scheduler/squad_ctrl/sfqa_controller.py
export KUBECONFIG=/home/mystous/.kube/config
A23=/raid/squad/traces/alibaba_repo/cluster-trace-gpu-v2023/csv/openb_pod_list_default.csv
PH=/raid/squad/traces/philly/repo/trace-data/cluster_job_log
LOG=/raid/squad/runs/run_all.log
: > "$LOG"

clean(){ kubectl delete jobs --all -n squad >/dev/null 2>&1; kubectl delete pods --all -n squad >/dev/null 2>&1; sleep 6; }

run_base(){  # trace input limit kappa runid
  clean
  echo "[$(date '+%T')] BASELINE $5" | tee -a "$LOG"
  $VENV $RE --trace "$1" --input "$2" --limit "$3" --kappa "$4" --min-dur 20 --max-dur 60 \
     --gpu-types NVIDIA-B200 --run-id "$5" >> "$LOG" 2>&1
}
run_sfqa(){  # trace input limit kappa runid
  clean
  echo "[$(date '+%T')] SFQA $5 (컨트롤러 시작)" | tee -a "$LOG"
  $VENV $CTRL --period 5 --beta 80 > /raid/squad/runs/${5}_ctrl.log 2>&1 &
  echo $! > /raid/squad/${5}.pid
  sleep 3
  $VENV $RE --trace "$1" --input "$2" --limit "$3" --kappa "$4" --min-dur 20 --max-dur 60 \
     --gpu-types NVIDIA-B200 --sfqa --run-id "$5" >> "$LOG" 2>&1
  kill "$(cat /raid/squad/${5}.pid)" 2>/dev/null
}

# a23 는 완료(보존됨). Philly 만 경합 확보(limit 40)해 재실측.
run_base philly      "$PH" 40 3000 ph_base
run_sfqa philly      "$PH" 40 3000 ph_sfqa
echo "[$(date '+%T')] ALL DONE" | tee -a "$LOG"
