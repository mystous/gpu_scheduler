#include "pch.h"
#include "experiment_perform.h"

atomic<int> completed_threads(0);


struct thread_parameter {
  job_emulator*                                 emulator = nullptr;
  vector<global_structure::scheduler_options>*  hyperparameter = nullptr;
  int                                           start_index = -1;
  int                                           handle_count = -1;
  string                                        task_file_name = "";
  string                                        server_file_name = "";
  function<void(void*)>                         callback_func;
};

experiment_perform::~experiment_perform() {
  initialize_emul_vector();
}

void experiment_perform::initialize_emul_vector() {
  if (emulator_vector.size() > 0) {
    for (auto&& emul : emulator_vector) {
      delete emul;
    }
    emulator_vector.clear();
  }
}

bool experiment_perform::set_thread_count(int thread_num) {
  if (nullptr == hyperparameter) { return false; }

  thread_count = thread_num;
  for (int i = 0; i < thread_num; ++i) {
    job_emulator* emul = new job_emulator();
    if (nullptr == emul) {
      initialize_emul_vector();
      return false;
    }
    emulator_vector.push_back(emul);
  }
  num_per_thread = hyperparameter->size() / thread_num;
  last_one_standing = num_per_thread + hyperparameter->size() % thread_num;
  return true;
}

void experiment_perform::set_file_name(string task_file, string server_file) {
  task_file_name = task_file;
  server_file_name = server_file;
}

void experiment_perform::start_experiment() {
  for (int i = 0; i < emulator_vector.size(); ++i) {
    thread_parameter* param = new thread_parameter();

    param->emulator = emulator_vector[i];
    param->callback_func = callback_func;
    param->start_index = i * num_per_thread;
    param->handle_count = num_per_thread;
    if (i == (emulator_vector.size() - 1)) {
      param->handle_count += last_one_standing;
    }
    param->hyperparameter = hyperparameter;
    param->server_file_name = server_file_name;
    param->task_file_name = task_file_name;
  }
}