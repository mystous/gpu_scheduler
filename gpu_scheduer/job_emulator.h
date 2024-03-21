#pragma once
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <iomanip>
#include <chrono>
#include <limits>
#include <atomic>
#include <functional>
#include <thread>
#include <queue>

#include "job_entry.h"
#include "coprocessor_server.h"
#include "server_entry.h"
#include "job_scheduler.h"
#include "scheduler_compact.h"
#include "scheduler_fare_share.h"
#include "scheduler_most_wanted.h"
#include "scheduler_round_robin.h"

using namespace std;
using namespace std::chrono;

class job_emulator {
public:
  job_emulator() = default;
  struct job_entry_element {
    vector<job_entry> job_list_in_slot;
  };

  using job_entry_struct = struct job_entry_element;

  virtual ~job_emulator();
  enum class scheduler_type : int {
    most_wanted = 0, compact, round_robin, fare_share
  };

  enum class emulation_status : int {
    stop, pause, start
  };

  void build_job_list(string filename, job_emulator::scheduler_type scheduler_index, bool using_preemetion);
  void build_job_queue();
  void build_server_list(string filename);
  void set_option(job_emulator::scheduler_type scheduler_index, bool using_preemetion);

  scheduler_type get_selction_scheduler() { return selected_scheduler; };
  bool get_preemtion_enabling() { return preemtion_enabling; };
  vector<job_entry>* get_job_list_ptr() { return &job_list; };
  vector<server_entry>* get_server_list() { return &server_list; };
  int get_total_time_slot() { return total_time_sloct; };
  int get_emulation_play_priod() { return emulation_play_priod; };
  void set_emulation_play_priod(int priod) { emulation_play_priod = priod; };
  string get_job_file_name() { return job_file_name; };
  void step_foward();
  void pause_progress();
  void stop_progress();
  void start_progress();
  void exit_thread();
  void update_wait_queue();
  void scheduling_job();
  void set_callback(std::function<void()> callback) { step_forward_callback = callback; };

private:
  vector<job_entry> job_list;
  vector<server_entry> server_list;
  scheduler_type selected_scheduler = scheduler_type::most_wanted;
  bool preemtion_enabling = false;
  system_clock::time_point min_start_time;
  system_clock::time_point max_end_time;
  job_entry_struct* job_queue = nullptr;
  int total_time_sloct = 0;
  string job_file_name = "";
  int emulation_step = -1;
  int emulation_play_priod = 1;
  emulation_status emul_status= emulation_status::stop;
  job_scheduler* scheduler_obj = nullptr;
  atomic<emulation_status> progress_status = emulation_status::stop;
  thread emulation_player;
  queue<job_entry> wait_queue;
  std::function<void()> step_forward_callback;
};

