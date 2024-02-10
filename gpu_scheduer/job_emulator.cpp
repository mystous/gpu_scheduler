#include "pch.h"
#include "job_emulator.h"

using namespace std;

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

void job_emulator::set_option(job_emulator::scheduler_type scheduler_index, bool using_preemetion) {
  selected_scheduler = scheduler_index;
  preemtion_enabling = using_preemetion;
}



