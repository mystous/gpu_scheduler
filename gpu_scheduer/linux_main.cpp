#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <thread>
#include <functional>
#include "call_back_object.h"
#include "experiment_perform.h"
#include "utility_class.h"

using namespace std;

// 기존 변수 선언
int thread_total = 4;
double alpha_para[3] = { 0.13889, 0.83889, 0.1 };
double beta_para[3] = { 70.0, 95.0, 5.0 };
int d_para[3] = { 100000, 1000000, 100000 };
int w_para[3] = { 20, 100, 10 };
bool sch[4] = { true, false, false, false };
string task_file_name = "job_flow_total(task,flavor,single).csv";
string server_file_name = "server.csv";

int hyperpara_total = 0;
int experiment_done = 0;
system_clock::time_point job_start_tp;

experiment_perform experiment_obj;
vector<global_structure::scheduler_option> hyperparameter_searchspace;

void add_string_to_status(string message) {
  cout << message << endl;
}

void add_string_to_status(vector<string> list) {
  for (auto&& message : list) {
    add_string_to_status(message);
  }
}


void parse_config_file(const string& config_filename) {
  ifstream config_file(config_filename);
  if (!config_file.is_open()) {
    cerr << "Error opening config file: " << config_filename << endl;
    exit(1);
  }

  auto parse_array = [](stringstream& ss, auto* array, int size) {
    string token;
    for (int i = 0; i < size; ++i) {
      getline(ss, token, ',');
      if constexpr (is_same_v<decltype(array[0]), double>) {
        array[i] = stod(token);
      }
      else if constexpr (is_same_v<decltype(array[0]), int>) {
        array[i] = stoi(token);
      }
      else if constexpr (is_same_v<decltype(array[0]), bool>) {
        array[i] = (token == "true");
      }
    }
    };

  string line;
  int line_num = 0;

  while (getline(config_file, line)) {
    stringstream ss(line);

    switch (line_num) {
    case 0:
      ss >> thread_total;
      break;
    case 1:
      parse_array(ss, alpha_para, 3);
      break;
    case 2:
      parse_array(ss, beta_para, 3);
      break;
    case 3:
      parse_array(ss, d_para, 3);
      break;
    case 4:
      parse_array(ss, w_para, 3);
      break;
    case 5:
      parse_array(ss, sch, 4);
      break;
    default:
      cerr << "Unexpected line in config file: " << line << endl;
      break;
    }
    ++line_num;
  }

  config_file.close();
}

void build_hyperparameter() {
  for (int i = 0; i < 4; ++i) {
    if (!sch[i]) continue;

    global_structure::scheduler_option option;
    option.scheduler_index = static_cast<scheduler_type>(i);
    option.working_till_end = true;
    option.scheduleing_with_flavor_option = false;

    option.prevent_starvation = false;
    option.svp_upper = 0.;
    option.age_weight = 0.;
    option.using_preemetion = false;
    option.reorder_count = 0;
    option.preemption_task_window = 0;

    hyperparameter_searchspace.push_back(option);
  }

  for (int i = 0; i < 4; ++i) {
    if (!sch[i]) continue;

    for (double alpha : alpha_para) {
      for (double beta : beta_para) {
        global_structure::scheduler_option option;
        option.scheduler_index = static_cast<scheduler_type>(i);
        option.working_till_end = true;
        option.scheduleing_with_flavor_option = false;

        option.prevent_starvation = true;
        option.svp_upper = beta;
        option.age_weight = alpha;
        option.using_preemetion = false;
        option.reorder_count = 0;
        option.preemption_task_window = 0;

        hyperparameter_searchspace.push_back(option);
      }
    }
  }

  for (int i = 0; i < 4; ++i) {
    if (!sch[i]) continue;

    for (int d : d_para) {
      for (int w : w_para) {
        global_structure::scheduler_option option;
        option.scheduler_index = static_cast<scheduler_type>(i);
        option.working_till_end = true;
        option.scheduleing_with_flavor_option = false;

        option.prevent_starvation = false;
        option.svp_upper = 0.;
        option.age_weight = 0.;
        option.using_preemetion = true;
        option.reorder_count = d;
        option.preemption_task_window = w;

        hyperparameter_searchspace.push_back(option);
      }
    }
  }


  for (int i = 0; i < 4; ++i) {
    if (!sch[i]) continue;

    for (double alpha : alpha_para) {
      for (double beta : beta_para) {
        for (int d : d_para) {
          for (int w : w_para) {
            global_structure::scheduler_option option;
            option.scheduler_index = static_cast<scheduler_type>(i);
            option.working_till_end = true;
            option.scheduleing_with_flavor_option = false;

            option.prevent_starvation = true;
            option.svp_upper = beta;
            option.age_weight = alpha;
            option.using_preemetion = true;
            option.reorder_count = d;
            option.preemption_task_window = w;

            hyperparameter_searchspace.push_back(option);
          }
        }
      }
    }
  }

  hyperpara_total = hyperparameter_searchspace.size();
}

void global_experiment_callback(void* object, thread::id id) {
  string message[2] = { "", "" };
  if (experiment_obj.call_back_from_thread(id, message[0], message[1])) {
    experiment_done = experiment_obj.get_complated_experiment();
    add_string_to_status(message[0]);
    if (!message[1].empty()) {
      add_string_to_status(message[1]);
    }
    if (hyperparameter_searchspace.size() == experiment_done) {
      chrono::duration<double> elapsed_seconds = system_clock::now() - job_start_tp;
      auto elapsed_duration = chrono::duration_cast<std::chrono::seconds>(elapsed_seconds);
      string wall_time = "Experiment is finished!(Takes - " + utility_class::format_duration(elapsed_duration) + ")";
      add_string_to_status(wall_time);
    }
  }
}

void global_message_callback(void* object, string message) {
  add_string_to_status(message);
}


int main(int argc, char* argv[]) {
  if (argc < 4) {
    cerr << "Usage: " << argv[0] << " <task_file_name> <server_file_name> <config_file>" << endl;
    return 1;
  }

  task_file_name = argv[1];
  server_file_name = argv[2];
  string config_filename = argv[3];

  experiment_done = 0;

  parse_config_file(config_filename);
  build_hyperparameter();

  function<void(void*, thread::id)> callback_func = global_experiment_callback;
  function<void(void*, string)> message_callback_func = global_message_callback;

  add_string_to_status("Experiment starting...");
  experiment_obj.set_hyperparameter(&hyperparameter_searchspace);
  if (experiment_obj.set_thread_count(thread_total)) {
    experiment_obj.set_call_back(callback_func);
    experiment_obj.set_call_back_obj(nullptr);
    experiment_obj.set_message_call_back(message_callback_func);
    experiment_obj.set_file_name(task_file_name, server_file_name);
    auto&& strings = experiment_obj.start_experiment();
    add_string_to_status(strings);
    job_start_tp = system_clock::now();
    return 0;
  }

  add_string_to_status("Experiment has been failed!");
  
  return 0;
}
