#include "pch.h"
#include "log_generator.h"
#include "utility_class.h"
#include <filesystem>

namespace fs = std::filesystem;

log_generator::log_generator() : log_generator(10000) {
}

log_generator::log_generator(int task_size) : task_count(task_size), random_generation(true) {
  generation_sucessed = start_generation();
}


log_generator::log_generator(int task_size, distribution_type gpu_count_dist, distribution_type wall_time_dist,
  distribution_type computation_dist, distribution_type flaver_dist, distribution_type preemetion_dist) 
  : task_count(task_size), random_generation(false), gpu_count_distribution(gpu_count_dist),
    wall_time_distribution(wall_time_dist), computation_distribution(computation_dist),
    flaver_distribution(flaver_dist), preemetion_diststribution(preemetion_dist){
  generation_sucessed = start_generation();
}

log_generator::~log_generator() {
  finialize_pointer();
}

bool log_generator::start_generation() {
  if (false == initialize_pointer(task_count)) { return false; }
  generate_seed_tp();
  set_whole_walltime(180); // Temporary
  if (random_gen_index == random_generation) {
    return generate_random_tasks();
  }

  return generate_distribution_tasks();

}

void log_generator::generate_seed_tp() {
  if (start_from_now) {
    seed_tp = system_clock::now();
    return;
  }

  seed_tp = utility_class::parse_time_string("2023-11-08 12:15:00+00:00"); // Temporary setting specific time stamp
}

void log_generator::set_whole_walltime(int day_count) {
  gen_time_duration_tp += (day_count * 24 * 60);
}

void log_generator::finialize_pointer() {
  if (nullptr != gen_data) {
    delete[] gen_data;
    gen_data = nullptr;
  }
}



bool log_generator::save_log(string filename) {
  bool dir_exited = true;
  string generated_filename = "";
  const string dir_prefix = "generated_task";

  if (!generation_sucessed) { return false; }

  
  generated_filename += filename;

  ofstream file(generated_filename);

  if (!file.is_open()) { return false; }

  file << "pod_name,pod_type,project,namespace,user_team,start,finish,count,time_diff,computing_load,gpu_utilization,flavor,preemption\n";
  for (int i = 0; i < task_count; ++i) {
    file << gen_data[i].pod_name << "," 
      << gen_data[i].pod_type << "," 
      << gen_data[i].project << "," 
      << gen_data[i].namespace_ << "," 
      << gen_data[i].user_team << ","
      << gen_data[i].start << "," 
      << gen_data[i].finish << "," 
      << gen_data[i].count << "," 
      << gen_data[i].time_diff << "," 
      << gen_data[i].computing_load << ","
      << gen_data[i].gpu_utilization << "," 
      << gen_data[i].flavor << "," 
      << gen_data[i].preemption << "\n";
  }
  file.close();

  return true;
}

string log_generator::get_savefile_candidate_name() {

  string filename = "";

  auto now = system_clock::now();
  std::time_t currentTime = system_clock::to_time_t(now);

  tm localTime;
  localtime_s(&localTime, &currentTime);
  stringstream ss;
  ss << std::put_time(&localTime, "%Y%m%d_%H%M%S");
  string formattedTime = ss.str();

  filename = std::format("{}.csv", formattedTime);
  return filename;
}

bool log_generator::generate_random_tasks() {
  for (int i = 0; i < task_count; ++i) {
    if (false == generate_random_task(gen_data[i])) {
      return false;
    }
  }

  return true;
}

bool log_generator::generate_task(task_entity& task, distribution_values* data, int index) {
  task.pod_name = "run-pipeline-gpu-" + generate_random_string(5) + "-" + std::to_string(rand() % 1000000000);
  task.pod_type = (rand() % 5 != 0) ? "task" : "instance";
  task.project = "PROJECT_" + std::to_string(rand() % 20 + 1);
  task.namespace_ = "ns-" + std::to_string(rand() % 1000000000);
  task.user_team = "TEAM_" + std::to_string(rand() % 10 + 1);

  if (random_gen_index == index) {
    task.start_tp = utility_class::get_time_after(seed_tp, rand() % gen_time_duration_tp);
    task.finish_tp = utility_class::get_time_after(task.start_tp, rand() % max_task_running);
    task.count = rand() % 8 + 1;
    task.gpu_utilization = (rand() % 10000) / 100.0;
    task.flavor = (rand() % 2 == 0) ? "A100" : "A30";
    task.preemption = (rand() % 2 == 0) ? "y" : "n";

    return true;
  }

  if (nullptr == data || -1 == data->array_size) { return false; }

  task.start_tp = data->start_tp[index];
  task.finish_tp = data->finish_tp[index];
  task.count = data->counts[index];
  task.gpu_utilization = data->utilizations[index];
  task.flavor = utility_class::get_accelerator_name(data->accelerators[index]);
  task.preemption = data->preemptions[index];

  return true;
}

void log_generator::finialize_distribution(distribution_values& dist) {
  delete[] dist.start_tp;
  delete[] dist.finish_tp;
  delete[] dist.counts;
  delete[] dist.utilizations;
  delete[] dist.preemptions;
  delete[] dist.accelerators;

  dist.start_tp = nullptr;
  dist.finish_tp = nullptr;
  dist.counts = nullptr;
  dist.utilizations = nullptr;
  dist.preemptions = nullptr;
  dist.accelerators = nullptr;

  dist.array_size = -1;
}

bool log_generator::initialize_distribution(distribution_values& dist, int task_size) {
  dist.array_size = -1;
    dist.start_tp = new (nothrow)system_clock::time_point[task_size];
    dist.finish_tp = new (nothrow)system_clock::time_point[task_size];
    dist.counts = new (nothrow)int[task_size];
    dist.utilizations = new (nothrow)float[task_size];
    dist.preemptions = new (nothrow)bool[task_size];
    dist.accelerators = new (nothrow)accelator_type[task_size];

    if (!dist.start_tp || !dist.finish_tp || !dist.counts ||
      !dist.utilizations || !dist.preemptions || !dist.accelerators) {
      finialize_distribution(dist);
      return false;
    }

  for (size_t i = 0; i < task_size; ++i) {
    dist.start_tp[i] = system_clock::now();
    dist.finish_tp[i] = system_clock::now();
    dist.counts[i] = 0;
    dist.utilizations[i] = 0.0f;
    dist.preemptions[i] = false;
    dist.accelerators[i] = accelator_type::any;
  }

  return true;
}

bool log_generator::generate_distribution_task(task_entity& task, distribution_values& dist, int index) {
  if (false == generate_task(task, &dist, index)) { return false; }
  generate_task_postproecess(task);
  return true;
}

void log_generator::generate_time_point_distribution(system_clock::time_point* tp, distribution_type distribution_method, 
                                                      system_clock::time_point* start_tp, duration<double, ratio<60>>range) {
}

void log_generator::generate_distribution(distribution_values& dist, int task_size) {
  for (int i = 0; i < task_size; ++i) {
    dist.start_tp[i] = utility_class::get_time_after(seed_tp, rand() % gen_time_duration_tp);
  }
  generate_time_point_distribution(dist.finish_tp, wall_time_distribution, dist.start_tp, duration<double, ratio<60>>(max_task_running));
}

bool log_generator::generate_distribution_tasks() {
  distribution_values dist;
  if (false == initialize_distribution(dist, task_count)) { return false; }
  generate_distribution(dist, task_count);
  for (int i = 0; i < task_count; ++i) {
    if (false == generate_distribution_task(gen_data[i], dist, i)) {
      return false;
    }
  }

  finialize_distribution(dist);
  return true;
}

void log_generator::generate_task_postproecess(task_entity& task) {
  task.start = utility_class::conver_tp_str(task.start_tp);
  task.finish = utility_class::conver_tp_str(task.finish_tp);
  task.time_diff_tp = duration_cast<std::chrono::minutes>(task.finish_tp - task.start_tp);
  task.time_diff = utility_class::double_to_string(task.time_diff_tp.count());
  task.computing_load = task.gpu_utilization / 20 + 1;
  if (6 == task.computing_load) { task.computing_load = 5; }
}

bool log_generator::generate_random_task(task_entity& task) {
  if (false == generate_task(task, nullptr)) { return false; }
  generate_task_postproecess(task);
  return true;
}

bool log_generator::initialize_pointer(int task_size) {
  if (nullptr == gen_data) { finialize_pointer(); }

  gen_data = new task_entity[task_size];
  if (nullptr != gen_data) { return false; }

  return true;
}

string log_generator::generate_random_string(int length) {
  string chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  string result;
  for (int i = 0; i < length; ++i) {
    result += chars[rand() % chars.size()];
  }
  return result;
}

string log_generator::generate_random_timestamp() {
  int year = (rand() % 2 == 0) ? 2023 : 2024;
  int month = rand() % 12 + 1;
  int day = rand() % 28 + 1;
  int hour = rand() % 24;
  int minute = rand() % 60;
  int second = rand() % 60;

  ostringstream oss;
  oss << year << "-" << std::setw(2) << std::setfill('0') << 
        month << "-" << std::setw(2) << std::setfill('0') << 
        day << " " << std::setw(2) << std::setfill('0') << 
        hour << ":" << std::setw(2) << std::setfill('0') << 
        minute << ":" << std::setw(2) << std::setfill('0') << 
        second << "+00:00";

  return oss.str();
}