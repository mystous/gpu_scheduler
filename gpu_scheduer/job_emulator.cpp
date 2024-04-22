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

job_emulator::~job_emulator() {
  if (nullptr != job_queue) {
    delete[] job_queue;
  }

  if (nullptr != scheduler_obj) {
    delete scheduler_obj;
  }
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

void job_emulator::build_server_list(string filename) {
  ifstream file(filename);

  if (!file.is_open()) {
    cerr << "File cannot be opened.\n";
    return;
  }
  server_list.clear();

  string line;
  while (getline(file, line)) {
    istringstream ss(line);
    string token;
    vector<string> tokens;

    while (std::getline(ss, token, ',')) {
      tokens.push_back(token);
    }

    server_entry new_element(tokens[0], [](string accelerator_type)->server_entry::accelator_type {
      if ("a100" == accelerator_type) {
        return server_entry::accelator_type::a100;
      }
      else if ("a30" == accelerator_type) {
        return server_entry::accelator_type::a30;
      }
      else if ("cpu" == accelerator_type) {
        return server_entry::accelator_type::cpu;
      }
      else {
        return server_entry::accelator_type::cpu;
      } }(tokens[2]), stoi(tokens[1]));
    server_list.push_back(new_element);
  }

  scheduler_obj->set_server(&server_list);

  file.close();
}

void job_emulator::build_job_list(string filename, job_emulator::scheduler_type scheduler_index, bool using_preemetion) {
  ifstream file(filename);

  if (!file.is_open()) {
    cerr << "File cannot be opened.\n";
    return;
  }

  job_file_name = filename;
  set_option(scheduler_index, using_preemetion);

  string line;
  while (getline(file, line)) {
    istringstream ss(line);
    string token;
    vector<string> tokens;

    while (std::getline(ss, token, ',')) {
      tokens.push_back(token);
    }

    int computation_level = 1;
    double gpu_utilization = 50.;
    if (tokens.size() > 9) {
      computation_level = stoi(tokens[9]);
      gpu_utilization = stod(tokens[10]);
    }

    job_entry new_element(tokens[0], tokens[1], tokens[2], tokens[3], tokens[4], tokens[5], 
                          tokens[6], stoi(tokens[7]), computation_level, gpu_utilization);
    job_list.push_back(new_element);
  }

  file.close();
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
  total_time_sloct = diff.count();
  job_queue = new job_entry_struct[total_time_sloct];

  for (int i = 0; i < job_list.size(); ++i) {
    job_entry* job = &job_list[i];
    auto startDiff = duration_cast<std::chrono::minutes>(job->get_start_tp() - min_start_time);
    job_queue[startDiff.count()].job_list_in_slot.push_back(job);

#ifndef _WIN32
    printf("Job queue Index(% s) : % d\n", job->get_job_type() == job_entry::job_type::task ? _T("task") : _T("instance"), startDiff.count());
#endif
  }
}

void job_emulator::set_option(job_emulator::scheduler_type scheduler_index, bool using_preemetion) {
  preemtion_enabling = using_preemetion;
  selected_scheduler = scheduler_index;
  if (nullptr != scheduler_obj) {
    delete scheduler_obj;
  }

  switch (selected_scheduler) {
  case scheduler_type::compact:
    scheduler_obj = new scheduler_compact();
    break;
  case scheduler_type::fare_share:
    scheduler_obj = new scheduler_fare_share();
    break;
  case scheduler_type::most_wanted:
    scheduler_obj = new scheduler_most_wanted();
    break;
  case scheduler_type::round_robin:
  default:
    scheduler_obj = new scheduler_round_robin();
    break;
  }
}

void job_emulator::step_foward() {
  for (int i = 0; i < ticktok_duration; ++i) {
    if ((total_time_sloct - 1) == emulation_step) {
      emulation_step = -1;
      progress_status = emulation_status::stop;
      initialize_server_state();
      initialize_job_state();
      break;
    }
    else {
      emulation_step++;
#ifndef _WIN32
      printf("Step foward %d/%d", emulation_step, total_time_sloct);
#endif

      // computing previous job & termination
      computing_forward();
      update_wait_queue();
      scheduling_job();
      step_forward_callback();
      //#ifdef _WIN32
      //      Sleep(sleep_for_drawing);
      //#else
      //      sleep(sleep_for_drawing / 1000);
      //#endif
    }
  }
}

void job_emulator::scheduling_job() {
  while (false == wait_queue.empty()) {
    auto job = wait_queue.front();
    if (-1 == scheduler_obj->arrange_server(*job)) {
      break;
    }
    wait_queue.pop();
  }
}

void job_emulator::computing_forward() {
  for (auto&& server : server_list) {
    server.ticktok(ticktok_duration);
    server.flush();
  }
}

void job_emulator::update_wait_queue() {
  if (job_queue[emulation_step].job_list_in_slot.size() > 0) {
    for (auto&& job : job_queue[emulation_step].job_list_in_slot) {
      wait_queue.push(job);
    }
  }
}

void job_emulator::pause_progress() {
  progress_status = emulation_status::pause;

#ifdef _WIN32
  TRACE(_T("\nPause progress\n"));
#else
  printf("\nPause progress\n");
#endif
}

void job_emulator::stop_progress() {
  if (emulation_status::pause == progress_status) {
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

//#define USE_TIME_BEGIN

void job_emulator::start_progress() {
  set_emulation_play_priod(0.1);
  queue<job_entry*> new_one;
  swap(wait_queue, new_one);
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
      auto next_call = steady_clock::now() + milliseconds(this->get_emulation_play_priod());
      this->step_foward();
      std::this_thread::sleep_until(next_call);
#endif //USE_TIME_BEGIN

    }
    if (progress_status == emulation_status::stop) {
      emulation_step = -1;
    }
    });

  emulation_player.detach();
}

