#pragma once
#include "job_scheduler.h"
class scheduler_most_wanted : public job_scheduler {
public:
  virtual ~scheduler_most_wanted() {};
  virtual int arrange_server(job_entry& job) override;

protected:
  virtual void postproessing_set_server() override {};
};

