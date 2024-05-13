#include "pch.h"
#include "job_scheduler.h"

int job_scheduler::scheduling_job() {
  int scheduled = 0;
  if (nullptr == wait_queue_group) {
    return scheduled;
  }

  for (int i = 0; i < wait_queue_group->size(); ++i) {
    queue<job_entry*>* wait_queue = wait_queue_group->at(i);
    while (false == wait_queue->empty()) {
      auto job = wait_queue->front();
      if (-1 == arrange_server(*job, static_cast<accelator_type>(i))) {
        break;
      }
      wait_queue->pop();
      scheduled++;
    }

    if (!scheduling_with_flavor) { break; }
  }

  return scheduled;
}

void job_scheduler::set_scheduling_condition(bool using_preemetion, bool scheduling_follow_flavor, bool work_till_end) {
  scheduling_with_flavor = scheduling_follow_flavor;
  preemtion_enabling = using_preemetion;
  perform_until_finish = work_till_end;
}

void job_scheduler::get_wait_job_request_acclerator(vector<int>& request) {

  for (int i = 0; i < wait_queue_group->size(); ++i) {
    queue<job_entry*>* wait_queue = wait_queue_group->at(i);
    queue<job_entry*> queue_temp = *wait_queue;
    int inquired_count = queue_temp.size();

    inquired_count = inquired_count > 5 ? 5 : inquired_count;
    for (int i = 0; i < inquired_count; ++i) {
      auto job = queue_temp.front();
      request.push_back(job->get_accelerator_count());
      queue_temp.pop();
    }
    request.push_back(-1);
  }
}