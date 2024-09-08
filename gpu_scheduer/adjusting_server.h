#pragma once
#include <vector>
#include "server_entry.h"
class adjusting_server
{
public:
  adjusting_server(vector<server_entry>* servers) 
  : server_list(servers){};
  virtual ~adjusting_server();

  int defragemetation();
  void reconstruct_server_status();
private:
  struct server_status_for_dp {
    gpu_allocation_type     status;
    string                  job_id;
  };
  struct job_for_dp {
    job_for_dp(job_entry* job_instance, int server_number, int accelerator_pos) :
      job{ job_instance }, server_index{ server_number }, accelerator_index{ accelerator_pos} {};
    job_entry*              job = nullptr;
    int                     server_index = -1;
    int                     accelerator_index = -1;
  };
  using server_map = struct server_status_for_dp;
  using job_element = struct job_for_dp;

  vector<server_entry>* server_list = nullptr;
  gpu_defragmentation_method adjusting_method = gpu_defragmentation_method::max_space;
  server_map* server_status = nullptr;
  vector<job_element> job_list;
  vector<job_element> optimal_position;

  job_entry* get_job_entry(string job_id, vector<job_entry*> job_list);
  int get_optimal_adjusting_dp(int server_count, int accelerator_count, int recursive_count);
  bool rearrange_task(int server_index, int accelerator_index, job_element job_obj, int recursive_count, bool reverse);
  int calcu_full_empty_server();
  void dumpy_job_list();
};

