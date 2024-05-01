#include "pch.h"
#include "scheduler_mostallocated.h"

int scheduler_mostallocated::arrange_server(job_entry& job) {
  const int max_value = 999999;
  int arrange_server = -1, i;
  int min_gap = max_value;
  vector<tuple<int, int, int>> candidate;
  vector<tuple<int, server_entry*>> suitable_server_list;

  get_suitable_server(suitable_server_list, job.get_accelerator_count());
  for (auto& [index, server] : suitable_server_list) {
    if (server->get_avaliable_accelator_count() < job.get_accelerator_count()) { continue; }

    int gap = server->get_avaliable_accelator_count() - job.get_accelerator_count();
    candidate.emplace_back(index, server->get_avaliable_accelator_count(), gap);

    if (gap < min_gap) {
      min_gap = gap;
    }
  }

  for (auto& [index, server_accelator_count, gap] : candidate) {
    if (min_gap != gap) {
      continue;
    }
    arrange_server = index;
    break;
  }

  if (-1 != arrange_server) {
    server_entry* target = &target_server->at(arrange_server);
    target->assign_accelator(&job, job.get_accelerator_count());
    return arrange_server;
  }

  for (i = 0; i < target_server->size(); ++i) {
    server_entry* target = &target_server->at(i);
    if (target->get_avaliable_accelator_count() < job.get_accelerator_count()) {
      continue;
    }

    arrange_server = i;
    break;
  }
    
  if (-1 != arrange_server) {
    server_entry* target = &target_server->at(arrange_server);
    target->assign_accelator(&job, job.get_accelerator_count());
  }
  return arrange_server;
}

void scheduler_mostallocated::get_suitable_server(vector<tuple<int, server_entry*>>& server, int required_accelerator){
  // return most suitable accelerator group
}

void scheduler_mostallocated::postproessing_set_server() {
  // Grouping Server with accelerator counts
}