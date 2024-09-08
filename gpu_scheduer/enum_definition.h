#pragma once

namespace global_const {
  const int accelator_category_count = 8;
};

enum class accelator_type : int {
  any = -2, cpu = -1, v100, a30, a100, h100, h200, l4, l40, b200
};

const int accelerator_counts = 7;

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
  none, empty, fixed, floating
};

enum class gpu_defragmentation_method : int {
  max_space
};