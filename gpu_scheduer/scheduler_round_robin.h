#pragma once
#include "job_scheduler.h"
class scheduler_round_robin : public job_scheduler{
public:
  virtual int arrange_server(job_entry& job) override;
};

