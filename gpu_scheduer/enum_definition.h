#pragma once

namespace global_const {
  const int accelator_category_count = 8;
  const int accelator_per_server_max = 8;
  const int accelerator_counts = 7;
  const double starvation_upper = 80.;
  const double age_weight = 0.13889;
  const int dp_execution_maximum = 100000;
  const int defragmentation_criteria = 20;
  const int statistics_array_size = 8;
};

enum class accelator_type : int {
  any = -2, cpu = -1, v100, a30, a100, h100, h200, l4, l40, b200
};


enum class scheduler_type : int {
  mostallocated = 0, compact, round_robin, mcts, fare_share
};

enum class emulation_status : int {
  stop, pause, start
};

enum class distribution_type : int {
  norm, expon, lognorm, gamma, beta, weibull_min, uniform, poisson, chi2
};

enum class gpu_allocation_type : int {
  none, empty, fixed, floating, adjusted
};

enum class gpu_defragmentation_method : int {
  max_space
};

enum statistics {
  min = 0, max, avg, sd, p_25, mid, p_75, p_95 
};