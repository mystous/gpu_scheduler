#include "pch.h"
#include "log_generator.h"
#include "utility_class.h"
#include <filesystem>
#include <cmath>

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
  if (true == random_generation) {
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

  if (!get_generation_sucessed_result()) { return false; }

  
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
  task.preemption = data->preemptions[index] ? "y" : "n";

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

template<typename distribution>
void log_generator::generate_time_point_distribution_inner(system_clock::time_point* tp, system_clock::time_point* start_tp, distribution_type distribution_method, distribution& dist, int task_size) {
  random_device rd;
  mt19937 gen(rd());

  for (int i = 0; i < task_size; ++i) {
    auto offset = duration_cast<std::chrono::minutes>(duration<double, ratio<60>>(dist(gen)));
    if (distribution_type::chi2 == distribution_method) {
      offset *= multi_const;
    }
    tp[i] = start_tp[i] + abs(offset);
  }
}

template<typename T, typename distribution_data>
void log_generator::generate_array_distribution_inner(T* array, T* seed, distribution_data& dist, int task_size, T min_value, T max_value) {
  std::random_device rd;
  std::mt19937 gen(rd());

  for (int i = 0; i < task_size; ++i) {
    T generated_data = static_cast<T>(dist(gen));
    while (generated_data < min_value || generated_data > max_value) {
      generated_data = static_cast<T>(dist(gen));
    }
    array[i] = generated_data;
  }
}

template<typename TT, typename distribution_value>
void log_generator::generate_discrete_distribution_inner(TT* array, TT* seed, distribution_value& dist, int seed_size, int task_size) {
  std::random_device rd;
  std::mt19937 gen(rd());

  for (int i = 0; i < task_size; ++i) {
    double random_value = dist(gen);
    int seed_index = static_cast<int>(random_value * seed_size);
    if (seed_index >= seed_size) {
      seed_index = seed_size - 1;
    }
    array[i] = seed[seed_index];
  }
}

template<typename datatype>
void log_generator::generate_array_distribution(datatype* array, datatype* seed, distribution_type distribution_method, datatype range, int task_size, datatype min_value, datatype max_value) {
  random_device rd;
  mt19937 gen(rd());

  switch (distribution_method) {
    case distribution_type::norm: {
      std::normal_distribution<> dist(range / 2.0, range / 3.0);
      generate_array_distribution_inner(array, seed, dist, task_size, min_value, max_value);
      break;
    }
    case distribution_type::expon: {
      std::exponential_distribution<> dist(1.0 / (range / 2.0));
      generate_array_distribution_inner(array, seed, dist, task_size, min_value, max_value);
      break;
    }
    case distribution_type::lognorm: {
      std::lognormal_distribution<> dist(0.0, range / 2.0);
      generate_array_distribution_inner(array, seed, dist, task_size, min_value, max_value);
      break;
    }
    case distribution_type::gamma: {
      std::gamma_distribution<> dist(2.0, range / 4.0);
      generate_array_distribution_inner(array, seed, dist, task_size, min_value, max_value);
      break;
    }
    case distribution_type::beta: {
      std::gamma_distribution<> dist_alpha(2.0, 1.0);
      std::gamma_distribution<> dist_beta(2.0, 1.0);
      for (int i = 0; i < task_size; ++i) {
        double alpha_sample = dist_alpha(gen);
        double beta_sample = dist_beta(gen);
        double beta_random = alpha_sample / (alpha_sample + beta_sample);
          array[i] = static_cast<datatype>(beta_random * range);
      }
      break;
    }
    case distribution_type::weibull_min: {
      std::weibull_distribution<> dist(2.0, range / 2.0);
      generate_array_distribution_inner(array, seed, dist, task_size, min_value, max_value);
      break;
    }
    case distribution_type::uniform: {
      std::uniform_real_distribution<> dist(0.0, range);
      generate_array_distribution_inner(array, seed, dist, task_size, min_value, max_value);
      break;
    }
    case distribution_type::poisson: {
      std::poisson_distribution<> dist(range / 2.0);
      generate_array_distribution_inner(array, seed, dist, task_size, min_value, max_value);
      break;
    }
    case distribution_type::chi2: {
      std::chi_squared_distribution<> dist(chi_dof);
      generate_array_distribution_inner(array, seed, dist, task_size, min_value, max_value);
      break;
    }
  }
}

template<typename datatype>
void log_generator::generate_discrete_distribution(datatype* array, datatype* seed, distribution_type distribution_method, int seed_size, int task_size) {
  std::random_device rd;
  std::mt19937 gen(rd());

  switch (distribution_method) {
    case distribution_type::norm: {
      std::normal_distribution<> dist(0.0, static_cast<double>(seed_size) / 2.0);
      generate_discrete_distribution_inner(array, seed, dist, seed_size, task_size);
      break;
    }
    case distribution_type::expon: {
      std::exponential_distribution<> dist(1.0 / (static_cast<double>(seed_size) / 2.0));
      generate_discrete_distribution_inner(array, seed, dist, seed_size, task_size);
      break;
    }
    case distribution_type::lognorm: {
      std::lognormal_distribution<> dist(0.0, static_cast<double>(seed_size) / 2.0);
      generate_discrete_distribution_inner(array, seed, dist, seed_size, task_size);
      break;
    }
    case distribution_type::gamma: {
      std::gamma_distribution<> dist(2.0, static_cast<double>(seed_size) / 4.0);
      generate_discrete_distribution_inner(array, seed, dist, seed_size, task_size);
      break;
    }
    case distribution_type::beta: {
      std::gamma_distribution<> dist_alpha(2.0, 1.0);
      std::gamma_distribution<> dist_beta(2.0, 1.0);
      for (int i = 0; i < task_size; ++i) {
        double alpha_sample = dist_alpha(gen);
        double beta_sample = dist_beta(gen);
        double beta_random = alpha_sample / (alpha_sample + beta_sample);

        if constexpr (std::is_same_v<datatype, bool>) {
          int seed_index = static_cast<int>(beta_random * 2);
          if (seed_index >= 2) {
            seed_index = 1;  // 최대 인덱스는 1
          }
          array[i] = seed[seed_index];
        }
        else if constexpr (std::is_same_v<datatype, accelator_type>) {
          int seed_index = static_cast<int>(beta_random * accelerator_counts);
          if (seed_index >= accelerator_counts) {
            seed_index = accelerator_counts - 1;  // 최대 인덱스는 accelerator_counts - 1
          }
          array[i] = seed[seed_index];
        }
        break;
      }
    }
    case distribution_type::weibull_min: {
      std::weibull_distribution<> dist(2.0, static_cast<double>(seed_size) / 2.0);
      generate_discrete_distribution_inner(array, seed, dist, seed_size, task_size);
      break;
    }
    case distribution_type::uniform: {
      std::uniform_real_distribution<> dist(0.0, static_cast<double>(seed_size));
      generate_discrete_distribution_inner(array, seed, dist, seed_size, task_size);
      break;
    }
    case distribution_type::poisson: {
      std::poisson_distribution<> dist(static_cast<double>(seed_size) / 2.0);
      generate_discrete_distribution_inner(array, seed, dist, seed_size, task_size);
      break;
    }
    case distribution_type::chi2: {
      std::chi_squared_distribution<> dist(chi_dof);
      generate_discrete_distribution_inner(array, seed, dist, seed_size, task_size);
      break;
    }
   }
}

void log_generator::generate_time_point_distribution(system_clock::time_point* tp, distribution_type distribution_method,
                                                      system_clock::time_point* start_tp, duration<double, ratio<60>>range, int task_size) {
  random_device rd;
  mt19937 gen(rd());

  switch (distribution_method) {
    case distribution_type::norm: {
      normal_distribution<> dist(range.count() / 2.0, range.count() / 3.0);
      generate_time_point_distribution_inner(tp, start_tp, distribution_method, dist, task_size);
      break;
    }
    case distribution_type::expon: {
      exponential_distribution<> dist(1.0 / (range.count() / 2.0));
      generate_time_point_distribution_inner(tp, start_tp, distribution_method, dist, task_size);
      break;
    }
    case distribution_type::lognorm: {
      lognormal_distribution<> dist(0.0, range.count() / 3.0);
      generate_time_point_distribution_inner(tp, start_tp, distribution_method, dist, task_size);
      break;
    }
    case distribution_type::gamma: {
      gamma_distribution<> dist(2.0, range.count() / 4.0);
      generate_time_point_distribution_inner(tp, start_tp, distribution_method, dist, task_size);
      break;
    }
    case distribution_type::beta: {
      gamma_distribution<> dist_alpha(2.0, 1.0);
      gamma_distribution<> dist_beta(2.0, 1.0);
      for (int i = 0; i < task_size; ++i) {
        double alpha_sample = dist_alpha(gen);
        double beta_sample = dist_beta(gen);
        double beta_random = alpha_sample / (alpha_sample + beta_sample);
        auto offset = duration_cast<system_clock::duration>(duration<double>(beta_random * range.count()));
        tp[i] = start_tp[i] + offset * multi_const / 2;
      }
      break;
    }
    case distribution_type::weibull_min: {
      weibull_distribution<> dist(2.0, range.count() / 2.0);
      generate_time_point_distribution_inner(tp, start_tp, distribution_method, dist, task_size);
      break;
    }
    case distribution_type::uniform: {
      uniform_real_distribution<> dist(0.0, range.count());
      generate_time_point_distribution_inner(tp, start_tp, distribution_method, dist, task_size);
      break;
    }
    case distribution_type::poisson: {
      poisson_distribution<> dist(range.count() / 2.0);
      generate_time_point_distribution_inner(tp, start_tp, distribution_method, dist, task_size);
      break;
    }
    case distribution_type::chi2: {
      chi_squared_distribution<> dist(chi_dof);
      generate_time_point_distribution_inner(tp, start_tp, distribution_method, dist, task_size);
      break;
    }
  }

}

void log_generator::generate_distribution(distribution_values& dist, int task_size) {
  int i = 0;
  for (i = 0; i < task_size; ++i) {
    dist.start_tp[i] = utility_class::get_time_after(seed_tp, rand() % gen_time_duration_tp);
    dist.accelerators[i] = (rand() % 4 == 0) ? accelator_type::a30 : accelator_type::a100;
    dist.preemptions[i] = (rand() % 4 == 0) ? true : false;

  }
  chi_dof = 10.0;
  generate_time_point_distribution(dist.finish_tp, wall_time_distribution, dist.start_tp, duration<double, ratio<60>>(max_task_running), task_size);
  chi_dof = 8.0;
  generate_array_distribution(dist.counts, (int*)nullptr, gpu_count_distribution, 8, task_size, 0, 8);
  for (int i = 0; i < task_size; ++i) {
    if (dist.counts[i] >= 8) {
      dist.counts[i] = 8;
      continue;
    }
    dist.counts[i] += 1;
    if (dist.counts[i] <= 0) {
      dist.counts[i] = 0;
    }
  }
  chi_dof = 10.0;
  generate_array_distribution(dist.utilizations, (float*)nullptr, computation_distribution, 100.0f, task_size, 20.0f, 100.0f);
  if (distribution_type::chi2 == computation_distribution) {
    float min_value = 1000000.0f, max_value = 0.0f;
    for (i = 0; i < task_size; ++i) {
      if (dist.utilizations[i] < min_value) {
        min_value = dist.utilizations[i];
      }

      if (dist.utilizations[i] > max_value) {
        max_value = dist.utilizations[i];
      }
    }

    float ratio_float = 80.0f / (max_value - min_value);
    for (i = 0; i < task_size; ++i) {
      dist.utilizations[i] = (dist.utilizations[i] - min_value) * ratio_float + 20.0f;
    }
  }
  dist.array_size = task_size;
  /*bool preemptions_seed[] = {true, false};
  generate_discrete_distribution_inner(dist.preemptions, preemptions_seed, preemetion_diststribution, 2, task_size);
  accelator_type accelator_type_seed[accelerator_counts] = { accelator_type::v100, accelator_type::a100, accelator_type::a30, 
                                                              accelator_type::h100, accelator_type::l4, accelator_type::l40, accelator_type::b200 };
  generate_discrete_distribution_inner(dist.accelerators, accelator_type_seed, flaver_distribution, accelerator_counts, task_size);*/
}

bool log_generator::generate_distribution_tasks() {
  distribution_values dist;
  if (false == initialize_distribution(dist, task_count)) { return false; }
  generate_distribution(dist, task_count);
  for (int i = 0; i < task_count; ++i) {
    if (false == generate_distribution_task(gen_data[i], dist, i)) {
      finialize_distribution(dist);
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
  if (nullptr != gen_data) { finialize_pointer(); }

  gen_data = new task_entity[task_size];
  if (nullptr == gen_data) { return false; }

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