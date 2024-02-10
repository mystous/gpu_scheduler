#pragma once
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <iomanip>
#include <chrono>

#include "job_entry.h"
#include "coprocessor_server.h"

using namespace std;

class job_emulator {
public:

  enum class scheduler_type : int {
    most_wanted = 0, compact, round_robin, fare_share
  };

  void build_job_list(string filename, job_emulator::scheduler_type scheduler_index, bool using_preemetion);
  void set_option(job_emulator::scheduler_type scheduler_index, bool using_preemetion);

  scheduler_type get_selction_scheduler() { return selected_scheduler; };
  bool get_preemtion_enabling() { return preemtion_enabling; };

private:
  vector<job_entry> job_list;
  vector< coprocessor_server> server_list;
  scheduler_type selected_scheduler = scheduler_type::most_wanted;
  bool preemtion_enabling = false;
};

