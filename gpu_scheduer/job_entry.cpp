#include "pch.h"
#include "job_entry.h"

job_entry::job_entry(string pod_name_param, string pod_type, string project_param, string namespace_param, string user_team_param,
  string start_time_string, string finish_time_string, int gpu_count)
  : pod_name(pod_name_param), project_name(project_param), user_team(user_team_param), name_space(namespace_param), gpu_number(gpu_count) {

  start_tp = parse_time_string(start_time_string);
  finish_tp = parse_time_string(finish_time_string);

  if ("task" == pod_type) {
    job_type_category = job_type::task;
  }
  else {
    job_type_category = job_type::instance;
  }
}

system_clock::time_point job_entry::parse_time_string(const string& time_str) {
  std::tm tm = {};
  istringstream ss(time_str);
  ss >> get_time(&tm, "%Y-%m-%d %H:%M:%S");
  auto tp = system_clock::from_time_t(std::mktime(&tm));
  return tp;
}
