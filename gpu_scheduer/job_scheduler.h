#pragma once
#include "job_entry.h"
#include "server_entry.h"
#include <vector>
#include <queue>

using namespace std;

class job_scheduler{
public:
  virtual ~job_scheduler() {};
  virtual int arrange_server(job_entry& job) = 0;
  void set_server(vector<server_entry>* server_list) { 
    target_server = server_list; 
    postproessing_set_server();
  };
  void set_scheduling_condition(bool using_preemetion, bool scheduling_follow_flavor, bool work_till_end);
  virtual int scheduling_job();
  virtual void get_wait_job_request_acclerator(vector<int>& request);
  void set_wait_queue(queue<job_entry*>* queue) { wait_queue = queue; };
protected:
  vector<server_entry>* target_server = nullptr;
  bool preemtion_enabling = false;
  bool scheduling_with_flavor = false;
  bool perform_until_finish = false;
  virtual void postproessing_set_server() = 0;
  queue<job_entry*>* wait_queue = nullptr;
};

