#pragma once
#include "job_scheduler.h"
class scheduler_fare_share : public job_scheduler {
public:
  virtual ~scheduler_fare_share() {};
  virtual int arrange_server(job_entry& job) override;
protected:
  virtual void postproessing_set_server() override {};
};

