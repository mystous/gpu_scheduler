#include "pch.h"
#include "adjusting_server.h"

int adjusting_server::defragemetation() {
  reconstruct_server_status();
  return 0;
}

adjusting_server::~adjusting_server() {
  if (nullptr != server_status) {
    delete[] server_status;
    server_status = nullptr;
  }
}

void adjusting_server::reconstruct_server_status() {
  if (nullptr != server_status) {
    delete[] server_status;
    server_status = nullptr;
  }

  server_status = new server_map[server_list->size() * global_const::accelator_category_count];
  if (nullptr != server_status) {
    return;
  }

  for (int i = 0; i < server_list->size(); ++i) {
    server_entry& server = server_list->at(i);
    string job_id_old;
    for (int j = 0; j < global_const::accelator_category_count; ++j) {
      string job_id = server.job_id_for_reserved[j];
      if (job_id_old == job_id)
        continue;
      job_id_old = job_id;
      job_entry* job = get_job_entry(job_id, server.job_list);
      server_status[i * global_const::accelator_category_count + j].job_id = job_id;
      job_element new_element(job, i, j);
      job_list.push_back(new_element);
    }
    //server.
  }
}

job_entry* adjusting_server::get_job_entry(string job_id, vector<job_entry*> job_list) {
  for (auto&& job : job_list) {
    if (job->get_job_id() == job_id) {
      return job;
    }
  }

  return nullptr;
}