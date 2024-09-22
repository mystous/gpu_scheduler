#pragma once
#include "job_emulator.h"
#include <vector>
#include <thread>
#include <iostream>
#include <atomic>

using namespace std;

class experiment_perform
{
public:
  virtual ~experiment_perform();
  void set_hyperparameter(vector<global_structure::scheduler_options>* func) { hyperparameter = func; };
  bool set_thread_count(int thread_num);
  void set_call_back(function<void(void*)> callback) { callback_func = callback; };
  void set_call_back_obj(void* ptr) { object = ptr; };
  void set_file_name(string task_file, string server_file);
  void start_experiment();
private:
  vector<job_emulator*> emulator_vector;
  vector<global_structure::scheduler_options>* hyperparameter = nullptr;
  int num_per_thread;
  int last_one_standing;
  int thread_count;
  string task_file_name;
  string server_file_name;

  function<void(void*)> callback_func;
  void* object = nullptr;

  void initialize_emul_vector();
};

