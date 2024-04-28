#include "pch.h"
#include "job_scheduler.h"

int job_scheduler::scheduling_job() {
  int scheduled = 0;
  if (nullptr == wait_queue) {
    return scheduled;
  }

  while (false == wait_queue->empty()) {
    auto job = wait_queue->front();
    if (-1 == arrange_server(*job)) {
      break;
    }
    wait_queue->pop();
    scheduled++;
  }

  return scheduled;
}