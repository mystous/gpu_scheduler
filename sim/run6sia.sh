#!/bin/bash
cd /home/mystous/projects/gpu_scheduler/sim
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
rm -f /tmp/par_logs/*_sia.log sweep_results/cmp*/_frag_sia.csv
for gpu in 256 512 1024; do for kind in single hetero; do
  python3 par_worker.py $gpu $kind sia > /tmp/par_logs/${gpu}_${kind}_sia.log 2>&1 &
done; done
wait
# 모두 끝나면 파이프라인
python3 par_merge.py > /tmp/sia_pipeline.log 2>&1
for d in cmp256_single cmp256_hetero cmp512_single cmp512_hetero cmp1024_single cmp1024_hetero; do
  cp -f sweep_results/$d/sia_jobs.csv sweep_results/raw/$d/ 2>/dev/null
  cp -f sweep_results/$d/sia_alloc.csv sweep_results/raw/$d/ 2>/dev/null
done
python3 analyze_sweep.py >> /tmp/sia_pipeline.log 2>&1
cd /home/mystous/projects/gpu_scheduler && python3 results/report_plots.py >> /tmp/sia_pipeline.log 2>&1
cp -f results/report_loadcurve.pdf paper/Pic/Fig_20.pdf
cp -f results/report_tradeoff.pdf paper/Pic/Fig_25.pdf
[ -f results/report_bigjob.pdf ] && cp -f results/report_bigjob.pdf paper/Pic/Fig_26.pdf
echo "PIPELINE_DONE $(date +%H:%M:%S)" >> /tmp/sia_pipeline.log
