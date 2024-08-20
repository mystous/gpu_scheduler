#include "pch.h"
#include "job_emulator.h"
#include <ctime>


#ifdef _WIN32
#include <Windows.h>
#include <mmsystem.h>
#pragma comment(lib, "winmm.lib")
#else
#include <unistd.h>
#endif

using namespace std;
using namespace std::chrono;

template <typename T>
T* reallocate(T* oldArray, size_t oldSize, size_t newSize) {
  T* newArray = new T[newSize];
  std::memcpy(newArray, oldArray, oldSize * sizeof(T));
  delete[] oldArray;
  return newArray;
}

job_emulator::job_emulator() {

}

void job_emulator::initialize_wait_queue() {
  for (int i = 0; i < global_const::accelator_category_count + 1; ++i) {
    queue<job_entry*>* new_element = new queue<job_entry*>();
    wait_queue_group.push_back(new_element);
    vector<job_age_struct> new_age_queue;
    wait_queue_age.push_back(new_age_queue);
  }
}

job_emulator::~job_emulator() {
  if (nullptr != job_queue) {
    delete[] job_queue;
  }

  if (nullptr != scheduler_obj) {
    delete scheduler_obj;
  }

  delete_wait_queue();
  delete_rate_array();
  delete_server_info_log();
}

void job_emulator::initialize_job_state() {
  for (auto&& job : job_list) {
    job.reset();
  }
}

void job_emulator::initialize_server_state() {
  for (auto&& server : server_list) {
    server.build_accelator_status();
  }
}

void job_emulator::delete_server_info_log() {
  for (int i = 0; i < server_utilization_rate.size(); ++i) {
    double* server_utilization = server_utilization_rate[i];
    if (nullptr != server_utilization) {
      delete server_utilization;
      server_utilization = nullptr;
    }

    int* server_allocation = server_allocation_count[i];
    if (nullptr != server_allocation) {
      delete server_allocation;
      server_allocation = nullptr;
    }
  }

  
  server_utilization_rate.clear();
  server_allocation_count.clear();
}

void job_emulator::delete_wait_queue() {
  for (auto && queue : wait_queue_group) {
    if (nullptr != queue) {
      delete queue;
      queue = nullptr;
    }
  }
  wait_queue_group.clear();
}

void job_emulator::build_server_list(string filename) {
  ifstream file(filename);

  if (!file.is_open()) {
    cerr << "File cannot be opened.\n";
    return;
  }
  delete_server_info_log();
  server_list.clear();

  string line;
  while (getline(file, line)) {
    istringstream ss(line);
    string token;
    vector<string> tokens;

    while (std::getline(ss, token, ',')) {
      tokens.push_back(token);
    }

    int accelerator_count = stoi(tokens[1]);
    server_entry new_element(tokens[0], server_entry::get_accelerator_type(tokens[2]), accelerator_count);
    server_list.push_back(new_element);
    max_age_count = server_list.size() * max_age_count_constant;
  }

  scheduler_obj->set_server(&server_list);
  
  file.close();
}

void job_emulator::build_job_list(string filename, scheduler_type scheduler_index, 
                                  bool using_preemetion, bool scheduleing_with_flavor_option, 
                                  bool working_till_end, bool prevent_starvation) {
  ifstream file(filename);

  if (!file.is_open()) {
    cerr << "File cannot be opened.\n";
    return;
  }

  job_file_name = filename;
  set_option(scheduler_index, using_preemetion, scheduleing_with_flavor_option, working_till_end, prevent_starvation);

  string line;
  while (getline(file, line)) {
    istringstream ss(line);
    string token;
    vector<string> tokens;

    while (std::getline(ss, token, ',')) {
      tokens.push_back(token);
    }

    if (tokens[0] == "pod_name" && tokens[1] == "pod_type") { continue; }

    int computation_level = 1;
    double gpu_utilization = 50.;
    bool preemption_enable = false;
    accelator_type accelator = accelator_type::cpu;

    if (tokens.size() > 9) {
      computation_level = stoi(tokens[9]);
      gpu_utilization = stod(tokens[10]);
    }


    if (tokens.size() > 11) {
      accelator = server_entry::get_accelerator_type(tokens[11]);
    }

    if (tokens.size() > 12) {
      preemption_enable = tokens[12] == "y" ? true : false;
    }

    job_entry new_element(tokens[0], tokens[1], tokens[2], tokens[3], 
                          tokens[4], tokens[5], tokens[6], stoi(tokens[7]), 
                          computation_level, gpu_utilization, accelator, preemption_enable);
    job_list.push_back(new_element);
  }

  file.close();
}

void job_emulator::set_callback(std::function<void(void*)> callback, void* object) {
  step_forward_callback = callback; 
  call_back_object = object;
};

string job_emulator::get_job_elapsed_time_string() {
  auto elapsed = get_job_elapsed_time();

  auto hours = chrono::duration_cast<chrono::hours>(elapsed);
  elapsed -= hours;
  auto minutes = chrono::duration_cast<chrono::minutes>(elapsed);
  elapsed -= minutes;
  auto seconds = chrono::duration_cast<chrono::seconds>(elapsed);
  elapsed -= seconds;
  auto milliseconds = chrono::duration_cast<chrono::milliseconds>(elapsed);

  ostringstream oss;
  oss << setw(2) << setfill('0') << hours.count() << ":"
    << setw(2) << setfill('0') << minutes.count() << ":"
    << setw(2) << setfill('0') << seconds.count() << ":"
    << std::setw(3) << std::setfill('0') << milliseconds.count();

  return oss.str();
}

void job_emulator::build_job_queue() {
  if (job_list.size() < 1) {
    return;
  }

  min_start_time = job_list[0].get_start_tp();
  max_end_time = job_list[0].get_finish_tp();

  for (const auto& job : job_list) {
    if (job.get_start_tp() < min_start_time) {
      min_start_time = job.get_start_tp();
    }
    if (job.get_finish_tp() > max_end_time) {
      max_end_time = job.get_finish_tp();
    }
  }

  auto diff = duration_cast<minutes>(max_end_time - min_start_time);
  total_time_slot = diff.count();
  job_queue = new job_entry_struct[total_time_slot];

  for (int i = 0; i < job_list.size(); ++i) {
    job_entry* job = &job_list[i];
    auto startDiff = duration_cast<std::chrono::minutes>(job->get_start_tp() - min_start_time);
    job_queue[startDiff.count()].job_list_in_slot.push_back(job);

#ifdef _WIN32
    //TRACE("Queue Idx: %d - %d\n", startDiff.count(), stoi(job->get_job_id()));
#else
    printf("Job queue Index(% s) : % d\n", job->get_job_type() == job_entry::job_type::task ? _T("task") : _T("instance"), startDiff.count());
#endif
  }
}

void job_emulator::get_wait_job_request_acclerator(vector<int>& request) {
  scheduler_obj->get_wait_job_request_acclerator(request);
}

void job_emulator::set_option(scheduler_type scheduler_index, bool using_preemetion, bool scheduleing_with_flavor_option, bool working_till_end, bool prevent_starvation) {
  preemtion_enabling = using_preemetion;
  scheduling_with_flavor = scheduleing_with_flavor_option;
  selected_scheduler = scheduler_index;
  perform_until_finish = working_till_end;
  starvation_prevention = prevent_starvation;
  if (nullptr != scheduler_obj) {
    delete scheduler_obj;
  }

  switch (selected_scheduler) {
  case scheduler_type::compact:
    scheduler_obj = new scheduler_compact();
    scheduling_name = compact_scheduler_name;
    break;
  case scheduler_type::fare_share:
    scheduler_obj = new scheduler_fare_share();
    scheduling_name = fare_share_scheduler_name;
    break;
  case scheduler_type::mostallocated: 
    scheduler_obj = new scheduler_mostallocated();
    scheduling_name = mostallocated_scheduler_name;
    break;
  case scheduler_type::mcts:
    scheduler_obj = new scheduler_mcts();
    scheduling_name = mcts_scheduler_name;
    break;
  case scheduler_type::round_robin:
  default:
    scheduler_obj = new scheduler_round_robin();
    scheduling_name = round_robin_scheduler_name;
    break;
  }
  scheduler_obj->set_wait_queue(&wait_queue_group);
  scheduler_obj->set_wait_age_queue(&wait_queue_age);
  scheduler_obj->set_server(&server_list);
  scheduler_obj->set_scheduling_condition(preemtion_enabling, scheduling_with_flavor, perform_until_finish);
}

void job_emulator::step_foward() {
  for (int i = 0; i < ticktok_duration; ++i) {
    if (check_finishing()) {
      last_emulation_step = emulation_step;
      emulation_step = -1;
      progress_status = emulation_status::stop;
      initialize_server_state();
      initialize_job_state();
      break;
    }
    else {
      emulation_step++;
#ifndef _WIN32
      printf("Step foward %d/%d", emulation_step, total_time_slot);
#endif
      computing_forward();
      update_wait_queue();
      scheduled_job_count += scheduler_obj->scheduling_job();
      adjust_wait_queue();
      log_rate_info();
      step_forward_callback(call_back_object);
    }
  }

  progress_tp = system_clock::now();
}

bool job_emulator::check_finishing() {
  bool finished_condition = false;
  if (perform_until_finish) {
    if (get_total_job_count() == get_scheduled_job_count()) {
      int server_size = server_list.size();
      finished_condition = true;
      for (int i = 0; i < server_size; ++i) {
        server_entry server = server_list.at(i);
        if (server.get_loaded_job_count() > 0) {
          finished_condition = false;
          break;
        }
      }
    }
    return finished_condition;
  }
  
  if ((total_time_slot - 1) == emulation_step) {
    finished_condition = true;
  }

  return finished_condition;
}


void job_emulator::log_rate_info() {
  if (rate_index >= memory_alloc_size) {
    reallocation_log_memory();
  }
  int total_reserved_count = 0, total_GPU_count = 0;
  double reserved_utilization = 0.0;
  int server_size = server_list.size();

  for (int i = 0; i < server_size; ++i) {
    server_entry server = server_list.at(i);

    int accelerator_count = server.get_accelerator_count();
    int avaliable_accelerator_count = server.get_avaliable_accelator_count();
    double utilization_rate = server.get_server_utilization();
    total_GPU_count += accelerator_count;
    total_reserved_count += (accelerator_count - avaliable_accelerator_count);
    reserved_utilization += utilization_rate;

    server_utilization_rate[i][rate_index] = utilization_rate;
    server_allocation_count[i][rate_index] = accelerator_count - avaliable_accelerator_count;
  }

  allocation_rate[rate_index] = (double)total_reserved_count / (double)total_GPU_count * 100;
  latest_allocation = allocation_rate[rate_index];
  utilization_rate[rate_index] = reserved_utilization / (double)server_size;
  rate_index++;
}

//void job_emulator::scheduling_job() {
//  //for (auto&& wait_queue : wait_queue_group) {
//  for (int i = 0; i < wait_queue_group.size(); ++i) {
//    bool scheduled_server = false;
//    while (false == wait_queue_group[i]->empty()) {
//      auto job = wait_queue_group[i]->front();
//      if (-1 == scheduler_obj->arrange_server(*job)) {
//        break;
//      }
//      scheduled_server = true;
//      wait_queue_group[i]->pop();
//      wait_queue_age[i].erase(wait_queue_age[i].begin());
//    }
//
//    if (scheduled_server) {
//      for (auto&& age_queue : wait_queue_age[i]) {
//        age_queue.age = 0;
//      }
//      continue;
//    }
//
//    for (auto&& age_queue : wait_queue_age[i]) {
//      age_queue.age++;
//    }
//  }
//}

void job_emulator::computing_forward() {
  for (auto&& server : server_list) {
    server.ticktok(ticktok_duration);
    finished_job_count += server.flush();
  }
}

void job_emulator::adjust_wait_queue() {
  if (!starvation_prevention) { return; }
  if (latest_allocation > starvation_prevention_criteria) { return; }
  const double age_weight_constant = 0.13889;
  const int accelerator_count = 8;
  double resource_suitability_index[accelerator_count] = {0,};

  for (auto&& server : server_list) {
    int avaliable_accelator_count = server.get_avaliable_accelator_count();
    for (int i = 0; i < accelerator_count; ++i) {
      if ((avaliable_accelator_count - i) < 0) { continue; }
      double suitablitiy_index = 1 - (avaliable_accelator_count - i)* 0.1;
      if (suitablitiy_index > resource_suitability_index[i]) {
        resource_suitability_index[i] = suitablitiy_index;
      }
    }
  }

  for (auto&& wait_queue : wait_queue_age) {
    int max_repriority_score_index = 0;
    double max_repriority_score = 0.;
    for (int j = 0; j < wait_queue.size(); ++j) {
      double priority = 1 * ( 1 / pow(2, j));
      double starvation_score = wait_queue[j].age 
                                * age_weight_constant 
                                * resource_suitability_index[wait_queue[j].job->get_accelerator_count()-1];
      wait_queue[j].repriority_score = priority + starvation_score;
      if (wait_queue[j].repriority_score > max_repriority_score) {
        max_repriority_score = wait_queue[j].repriority_score;
        max_repriority_score_index = j;
      }
    }

    if (0 != max_repriority_score_index) {
      job_age job_high_prioirty = wait_queue[max_repriority_score_index];
      wait_queue.erase(wait_queue.begin() + max_repriority_score_index);
      wait_queue.insert(wait_queue.begin(), job_high_prioirty);

      // Meta뿐 아니라 실제 wait queue도 업데이트 해주어야 함
    }

  }

}

void job_emulator::update_wait_queue() {
  if (emulation_step >= get_total_time_slot()) { return; }
 
  if (job_queue[emulation_step].job_list_in_slot.size() > 0) {
    for (auto&& job : job_queue[emulation_step].job_list_in_slot) {
      //wait_queue.push(job);
      int queue_index = 0;
      if (scheduling_with_flavor) {
        queue_index = static_cast<int>(job->get_flavor());
      }
      wait_queue_group[queue_index]->push(job);
      if (wait_queue_age[queue_index].size() < max_age_count) {
        wait_queue_age[queue_index].push_back(job_age_struct(job));
      }
    }
  }
}

void job_emulator::pause_progress() {
  progress_status = emulation_status::pause;
  last_emulation_step = emulation_step;

#ifdef _WIN32
  TRACE(_T("\nPause progress\n"));
#else
  printf("\nPause progress\n");
#endif
}

void job_emulator::stop_progress() {
  if (emulation_status::pause == progress_status) {
    last_emulation_step = emulation_step;
    emulation_step = -1;
  }
  progress_status = emulation_status::stop;
  initialize_server_state();
  initialize_job_state();

#ifdef _WIN32
  TRACE(_T("\nStop progress\n"));
#else
  printf("\nStop progress\n");
#endif
}

void job_emulator::exit_thread() {
  if (emulation_player.joinable()) {
    emulation_player.join();
  }
}

void job_emulator::delete_rate_array() {
  if (nullptr != allocation_rate) {
    delete allocation_rate;
    allocation_rate = nullptr;
  }
  if (nullptr != utilization_rate) {
    delete utilization_rate;
    utilization_rate = nullptr;
  }
}


void job_emulator::reallocation_log_memory() {
  int old_memory_size = memory_alloc_size;
  memory_alloc_size *= 2;
  allocation_rate = reallocate(allocation_rate, old_memory_size, memory_alloc_size);
  utilization_rate = reallocate(utilization_rate, old_memory_size, memory_alloc_size);
  int server_count = server_list.size();

  for (int i = 0; i < server_list.size(); ++i) {
    server_entry server = server_list.at(i);

    server_utilization_rate[i] = reallocate(server_utilization_rate[i], old_memory_size, memory_alloc_size);
    server_allocation_count[i] = reallocate(server_allocation_count[i], old_memory_size, memory_alloc_size);
  }
}

void job_emulator::initialize_progress_variables() {
  rate_index = 0;
  finished_job_count = 0;
  scheduled_job_count = 0;
  memory_alloc_size = get_total_time_slot();

  allocation_rate = new double[memory_alloc_size];
  utilization_rate = new double[memory_alloc_size];


  int server_count = server_list.size();

  for (int i = 0; i < server_count; ++i) {
    double* utilization = new double[memory_alloc_size];
    memset(utilization, 0.0, sizeof(double) * memory_alloc_size);
    server_utilization_rate.push_back(utilization);

    int* allocation = new int[memory_alloc_size];
    memset(allocation, 0, sizeof(int) * memory_alloc_size);
    server_allocation_count.push_back(allocation);
  }
}

int job_emulator::get_wait_job_count() {
  int wait_job_count = 0;

  for (auto&& queue : wait_queue_group) {
    wait_job_count += queue->size();
  }
  return wait_job_count;
}

//#define USE_TIME_BEGIN

void job_emulator::start_progress() {
  set_emulation_play_priod(0.1);

  delete_rate_array();
  delete_server_info_log();
  delete_wait_queue();
  initialize_progress_variables();
  initialize_wait_queue();

  if (emulation_status::pause != this->progress_status) {
    job_start_tp = system_clock::now();
  }
  
  emulation_player = thread([this]() {
    this->progress_status = emulation_status::start;

    while (emulation_status::start == this->progress_status) {
#ifdef USE_TIME_BEGIN
      double sleep_period = 1;
      this->step_foward();
      timeBeginPeriod(sleep_period);
      Sleep(sleep_period);
      timeEndPeriod(sleep_period);
#else // USE_TIME_BEGIN
      saving_possiblity = true;
      this->step_foward();
      auto next_call = steady_clock::now() + milliseconds(this->get_emulation_play_priod());
      std::this_thread::sleep_until(next_call);
#endif //USE_TIME_BEGIN

    }
    if (progress_status == emulation_status::stop) {
      emulation_step = -1;
    }
    });

  emulation_player.detach();
}

bool job_emulator::save_result_log() {
  return save_result_log(get_savefile_candidate_name());
}

int job_emulator::get_progress_time_slot() {
  return last_emulation_step;
}

bool job_emulator::save_result_log(string file_name) {
  ofstream file(file_name);

  if (!saving_possiblity) { return false; }
  if (!file.is_open()) { return false; }

  file << "Allocation Rate,Utilization Rate";
  for (int i = 0; i < server_list.size(); i++)
  {
    file << "," << server_list[i].get_server_name() 
      << " Utilization Rate," << server_list[i].get_server_name() << " Allocation";
  }
  file << "\n";

  for (int i = 0; i < get_progress_time_slot(); i++)
  {
    file << allocation_rate[i] << "," << utilization_rate[i];
    for (int j = 0; j < server_list.size(); j++)
    {
      file << "," << server_utilization_rate[j][i] << "," << server_allocation_count[j][i];
    }
    file << "\n";
  }
  file.close();
  return true;
}

string job_emulator::get_savefile_candidate_name() {
  string filename = "";

  int server_number = server_list.size();
  int accelerator_number = 0;

  for (int i = 0; i < server_number; ++i) {
    server_entry server = server_list.at(i);
    accelerator_number += server.get_accelerator_count();
  }

  auto now = system_clock::now();
  std::time_t currentTime = system_clock::to_time_t(now);

  tm localTime;
  localtime_s(&localTime, &currentTime);
  stringstream ss;
  ss << std::put_time(&localTime, "%Y%m%d_%H%M%S");
  string formattedTime = ss.str();

  filename = std::format("{}_{}_job({})_server({})_accelerator({})_elapsed({})_flavor({}).result", 
    get_setting_scheduling_name(), formattedTime, get_total_job_count(), server_number, accelerator_number,
    get_done_emulation_step(), scheduling_with_flavor ? "true" : "false");
  return filename;
}

