#pragma once

enum class accelator_type : int {
  a100, a30, cpu
};

enum class scheduler_type : int {
  mostallocated = 0, compact, round_robin, fare_share
};

enum class emulation_status : int {
  stop, pause, start
};