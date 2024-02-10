#pragma once
#include <iostream>
#include <sstream>
#include <iomanip>
#include <chrono>

using namespace std;
using namespace std::chrono;

class job_entry
{
public:
  enum class job_type {
    task, instance
  };
  job_entry(string pod_name_param, string pod_type, string project_param, string namespace_param, 
            string user_team_param, string start_time_string, string finish_time_string, int gpu_count);

private:

  system_clock::time_point parse_time_string(const string& time_str);
  system_clock::time_point start_tp, finish_tp;
  int gpu_number;
  string pod_name;
  string user_team;
  string name_space;
  string project_name;
  job_type job_type_category;
};

