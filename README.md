# GPU Scheduler Simulator

A simulation framework for benchmarking GPU job scheduling algorithms in heterogeneous multi-accelerator cluster environments. It supports multiple scheduling strategies and runs configurable parameter-sweep experiments using real cluster job traces, with results analyzed via Jupyter notebooks.

## Requirements

- g++ with C++20 support
- Python 3 + Jupyter (for analysis notebooks)

## Build

```bash
make          # Build → experiment_gpu
make clean    # Remove build artifacts
make rebuild  # Clean + build
```

## Usage

```bash
./experiment_gpu <task_file.csv> <server_file.csv> <config.set>
```

### Input Files

**Task file** — CSV of job traces:
```
job_id, submit_time, duration, gpu_count, gpu_type, ...
```

**Server file** (`server.csv`) — GPU cluster topology:
```
server_name, accelerator_count, gpu_type
gpu_serverA1, 8, a100
gpu_serverB1, 4, a30
```

**Config file** (`config.set`) — Experiment parameter sweep:
```
<thread_total>
<alpha_start>,<alpha_end>,<alpha_step>
<beta_start>,<beta_end>,<beta_step>
<d_start>,<d_end>,<d_step>
<w_start>,<w_end>,<w_step>
<mostallocated>,<compact>,<round_robin>,<mcts>   # true/false per scheduler
```

## Scheduling Algorithms

| Algorithm | Description |
|-----------|-------------|
| Most Allocated | Prioritizes servers with the most GPUs already in use |
| Compact | Packs jobs tightly to minimize fragmentation |
| Round Robin | Distributes jobs evenly across servers |
| Fair Share | Balances resource usage across all jobs |
| MCTS | Monte Carlo Tree Search based scheduling |

### Scheduler Options

- **Preemption** — Allow running jobs to be preempted for higher-priority jobs
- **Starvation prevention** — Age-based prioritization to prevent indefinite queuing
- **Defragmentation** — Periodic server rebalancing to recover fragmented GPU slots

## Supported GPU Types

V100, A30, A100, H100, H200, L4, L40, B200

## Output & Analysis

Results are written to `analysis_results/` and `result/` as `.result` / `.result.meta` files.

Open the Jupyter notebooks to visualize and compare results across schedulers:

```bash
jupyter notebook analysis_results/analysis.ipynb
```

Key notebooks:
- `analysis_results/analysis.ipynb` — Main comparison across schedulers
- `analysis_results/Wating_Time.ipynb` — Waiting time distribution analysis
- `result/<date>/result_analysis.ipynb` — Per-experiment deep dive

## Windows GUI

A Windows MFC application (`gpu_scheduer.sln`) provides a graphical interface for configuring and running experiments without the command line.
