#pragma once
#include "job_scheduler.h"
class scheduler_mostallocated :public job_scheduler {
public:
  virtual int arrange_server(job_entry& job) override;

protected:
  virtual void postproessing_set_server() override;

private:
  void get_suitable_server(vector<tuple<int, server_entry*>> &server, int required_accelerator);
};

