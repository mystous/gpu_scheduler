#pragma once
#include <string>
#include <fstream>
#include <vector>
#include <cstdlib>
#include <ctime>
#include <iomanip>
#include <sstream>
#include <chrono>
#include "enum_definition.h"

using namespace std;
using namespace std::chrono;

class log_generator
{
public:
  struct task_entiry_meta{
    string pod_name;
    string pod_type;
    string project;
    string namespace_;
    string user_team;
    string start;
    system_clock::time_point start_tp;
    string finish;
    system_clock::time_point finish_tp;
    int count;
    string time_diff;
    duration<double, ratio<60>> time_diff_tp;
    int computing_load;
    double gpu_utilization;
    string flavor;
    string preemption;
  };
  using task_entity = struct task_entiry_meta;
  log_generator();
  log_generator(int task_size);
  log_generator(int task_size, distribution_type gpu_count_dist, distribution_type wall_time_dist,
    distribution_type computation_dist, distribution_type flaver_dist, distribution_type preemetion_dist);
  virtual ~log_generator();
  string get_savefile_candidate_name();
  bool save_log(string filename);

private:
  static string generate_random_string(int length);
  static string generate_random_timestamp();
  void generate_random_task(task_entity &task);
  int task_count = 100;
  task_entity* gen_data = nullptr;
  void finialize_pointer();
  void generate_random_tasks();
  void generate_tasks();
  bool initialize_pointer(int task_size);
  bool random_generation = true;
  distribution_type gpu_count_distribution;
  distribution_type wall_time_distribution; 
  distribution_type computation_distribution; 
  distribution_type flaver_distribution; 
  distribution_type preemetion_diststribution;
};

