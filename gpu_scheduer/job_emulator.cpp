#include "pch.h"
#include "job_emulator.h"
#include <ctime>

#ifdef _WIN32
#include <Windows.h>
#endif

using namespace std;
using namespace std::chrono;

job_emulator::~job_emulator() {
  if (nullptr != job_queue) {
    delete[] job_queue;
  }
}

void job_emulator::build_server_list(string filename) {
  ifstream file(filename);

  if (!file.is_open()) {
    cerr << "File cannot be opened.\n";
    return;
  }

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
        }
      }(tokens[2]),
      stoi(tokens[1]));
    server_list.push_back(new_element);
  }

  file.close();

}

void job_emulator::build_job_list(string filename, job_emulator::scheduler_type scheduler_index, bool using_preemetion) {
  ifstream file(filename);

  if (!file.is_open()) {
    cerr << "File cannot be opened.\n";
    return;
  }

  set_option(scheduler_index, using_preemetion);

  string line;
  while (getline(file, line)) {
    istringstream ss(line);
    string token;
    vector<string> tokens;

    while (std::getline(ss, token, ',')) {
      tokens.push_back(token);
    }

    job_entry new_element(tokens[0], tokens[1], tokens[2], tokens[3], tokens[4], tokens[5], tokens[6], stoi(tokens[7]));
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

  for (const auto& job : job_list) {
      auto startDiff = duration_cast<std::chrono::minutes>(job.get_start_tp() - min_start_time);
      job_queue[startDiff.count()].job_list_in_slot.push_back(job);
  
#ifdef _WIN32
      TRACE(_T("Job queue Index(%s): %d\n"), job.get_job_type() == job_entry::job_type::task ? _T("task") : _T("instance"), startDiff.count());
#endif
  }


  int j = 0;
}

void job_emulator::set_option(job_emulator::scheduler_type scheduler_index, bool using_preemetion) {
  selected_scheduler = scheduler_index;
  preemtion_enabling = using_preemetion;
}



