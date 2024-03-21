#pragma once
#include "job_scheduler.h"
class scheduler_round_robin : public job_scheduler{
public:
  virtual int arrange_server(job_entry& job) override;
private:
  int current_server_index;
  int get_next_server_index();
  virtual void postproessing_set_server() override;
};

