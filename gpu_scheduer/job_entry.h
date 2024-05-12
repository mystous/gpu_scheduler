#pragma once
#include <iostream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <vector>
#include "enum_definition.h"

using namespace std;
using namespace std::chrono;

class job_entry
{
public:
  enum class job_type {
    task, instance
  };
  job_entry(string pod_name_param, string pod_type, string project_param, string namespace_param, 
            string user_team_param, string start_time_string, string finish_time_string, int accelerator_count, 
            int computing_level, double gpu_utilization, accelator_type accelator);

  string get_pod_name() { return pod_name; };
  string get_user_team() { return user_team; };
  string get_name_sapce() { return name_space; };
  string get_project_name() { return project_name; };
  job_type get_job_type() const { return job_type_category; };
  system_clock::time_point get_start_tp() const { return start_tp; };
  system_clock::time_point get_finish_tp() const { return finish_tp; };
  duration<double, ratio<60>> get_wall_time() const { return wall_time_min; };
  double get_utilization() const { return utilization; };
  int get_accelerator_count() { return accelerator_count; };
  void assign_accelerator(int position);
  const string get_job_id() { return job_id; };
  bool flush();
  void reset();
  accelator_type get_flavor() { return accelator_flavor; };
  void ticktok() { 
    if (wall_time_min > minutes(0)) {
      wall_time_min = wall_time_min - minutes(1); 
    }
  };
private:

  system_clock::time_point parse_time_string(const string& time_str);
  string get_sequencial_id();
  system_clock::time_point start_tp, finish_tp;
  duration<double, ratio<60>> wall_time_min;
  duration<double, ratio<60>> wall_time_min_record;
  vector<int> assigned_accelerator;

  static unsigned int random_id_pre, random_id_post;
  const static unsigned int digit_pre = 1001, digit_post = 501;
  int accelerator_count = 0;
  string pod_name;
  string user_team;
  string name_space;
  string project_name;
  string job_id;
  job_type job_type_category;
  int computaion_load;
  double utilization;
  accelator_type accelator_flavor;
};

