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
  virtual void set_using_preemtion(bool using_preemetion) { preemtion_enabling = using_preemetion; };
  virtual int scheduling_job();
  void set_wait_queue(queue<job_entry*>* queue) { wait_queue = queue; };
protected:
  vector<server_entry>* target_server = nullptr;
  bool preemtion_enabling = false;
  virtual void postproessing_set_server() = 0;
  queue<job_entry*>* wait_queue = nullptr;
};

