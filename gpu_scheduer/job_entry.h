#pragma once
#include <iostream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <vector>

using namespace std;
using namespace std::chrono;

class job_entry
{
public:
  enum class job_type {
    task, instance
  };
  job_entry(string pod_name_param, string pod_type, string project_param, string namespace_param, 
            string user_team_param, string start_time_string, string finish_time_string, int accelerator_count, int computing_level, double gpu_utilization);

  string get_pod_name() { return pod_name; };
  string get_user_team() { return user_team; };
  string get_name_sapce() { return name_space; };
  string get_project_name() { return project_name; };
  job_type get_job_type() const { return job_type_category; };
  system_clock::time_point get_start_tp() const { return start_tp; };
  system_clock::time_point get_finish_tp() const { return finish_tp; };
  duration<double, ratio<60>> get_wall_time() const { return wall_time_min; };
  int get_accelerator_count() { return accelerator_count; };
  void assign_accelerator(int position);

private:

  system_clock::time_point parse_time_string(const string& time_str);
  system_clock::time_point start_tp, finish_tp;
  duration<double, ratio<60>> wall_time_min;
  vector<int> assigned_accelerator;

  int accelerator_count = 0;
  string pod_name;
  string user_team;
  string name_space;
  string project_name;
  job_type job_type_category;
  int computaion_load;
  double utilization;
};

