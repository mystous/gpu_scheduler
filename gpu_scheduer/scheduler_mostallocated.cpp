#include "pch.h"
#include "scheduler_mostallocated.h"

int scheduler_mostallocated::arrange_server(job_entry& job) {
  const int max_value = 999999;
  int arrange_server = -1, i;
  int min_gap = max_value;
  vector<tuple<int, int, int>> candidate;

  for (i = 0; i < target_server->size(); ++i) {
    server_entry* target = &target_server->at(i);
    if (target->get_avaliable_accelator_count() < job.get_accelerator_count()) {
      continue;
    }

    int gap = target->get_avaliable_accelator_count() - job.get_accelerator_count();
    candidate.emplace_back(i, target->get_avaliable_accelator_count(), gap);

    if (gap < min_gap) {
      min_gap = gap;
    }
  }

  int min_accelator = max_value;
  for (auto& [index, server_accelator_count, gap] : candidate) {
    if (min_gap != gap) {
      continue;
    }
    if (server_accelator_count < min_accelator) {
      min_accelator = server_accelator_count;
      arrange_server = index;
    }
  }

  if (-1 != arrange_server) {
    server_entry* target = &target_server->at(arrange_server);
    target->assign_accelator(&job, job.get_accelerator_count());
  }
  return arrange_server;
}
