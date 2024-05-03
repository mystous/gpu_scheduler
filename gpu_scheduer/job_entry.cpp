#include "pch.h"
#include "job_entry.h"

#include <sstream>

unsigned int job_entry::random_id_pre = 0;
unsigned int job_entry::random_id_post = 0;

job_entry::job_entry(string pod_name_param, string pod_type, string project_param, string namespace_param, string user_team_param,
  string start_time_string, string finish_time_string, int accelerator_count, int computing_level, double gpu_utilization, accelator_type accelator)
  : pod_name(pod_name_param), project_name(project_param), user_team(user_team_param), name_space(namespace_param), accelerator_count(accelerator_count), 
  computaion_load(computing_level), utilization(gpu_utilization), accelator_flavor(accelator){

  start_tp = parse_time_string(start_time_string);
  finish_tp = parse_time_string(finish_time_string);
  //wall_time_min = finish_tp - start_tp;
  wall_time_min = duration_cast<std::chrono::minutes>(finish_tp - start_tp);
  wall_time_min_record = wall_time_min;

  if ("task" == pod_type) {
    job_type_category = job_type::task;
  }
  else {
    job_type_category = job_type::instance;
  }
  job_id = get_sequencial_id();
}

bool job_entry::flush() {
  bool flushed = false;
  if (minutes(0) == wall_time_min) {
    flushed = true;
    reset();
  }

  return flushed;
}

void job_entry::reset() { 
  wall_time_min = wall_time_min_record; 
  assigned_accelerator.clear();
}

string job_entry::get_sequencial_id() {
  string id;

  ostringstream oss;
  oss << setw(3) << setfill('0') << random_id_pre;
  oss << setw(3) << setfill('0') << random_id_post;

  id = oss.str();

  random_id_pre = (random_id_pre + 1) % digit_pre;
  random_id_post = (random_id_post + 1) % digit_post;

  return id;
}
void job_entry::assign_accelerator(int position) {
  assigned_accelerator.push_back(position);
  //accelerator_count++;
}

system_clock::time_point job_entry::parse_time_string(const string& time_str) {
  std::tm tm = {};
  istringstream ss(time_str);
  ss >> get_time(&tm, "%Y-%m-%d %H:%M:%S");
  auto tp = system_clock::from_time_t(std::mktime(&tm));
  return tp;
}
