#include "pch.h"
#include "adjusting_server.h"

int adjusting_server::defragemetation() {
  reconstruct_server_status();
  get_optimal_adjusting_dp(server_list->size(), global_const::accelator_per_server_max, 0);
  return 0;
}

adjusting_server::~adjusting_server() {
  if (nullptr != server_status) {
    delete[] server_status;
    server_status = nullptr;
  }
}

void adjusting_server::reconstruct_server_status() {
  if (nullptr != server_status) {
    delete[] server_status;
    server_status = nullptr;
  }

  server_status = new server_map[server_list->size() * global_const::accelator_per_server_max];
  if (nullptr == server_status) {
    return;
  }

  for (int i = 0; i < server_list->size(); ++i) {
    server_entry& server = server_list->at(i);
    string job_id_old = "";
    job_entry* job = nullptr;
    for (int j = 0; j < global_const::accelator_per_server_max; ++j) {

      server_status[i * global_const::accelator_per_server_max + j].job_id = "";
      if ( j > server.get_accelerator_count()-1) {
        server_status[i * global_const::accelator_per_server_max + j].status = gpu_allocation_type::none;
        job_id_old = "";
        job = nullptr;
        continue;
      }
      
      if (false == server.reserved[j]) {
        server_status[i * global_const::accelator_per_server_max + j].status = gpu_allocation_type::empty;
        job_id_old = "";
        job = nullptr;
        continue;
      }

      string job_id = server.job_id_for_reserved[j];
      if (job_id_old != job_id) {
        job_id_old = job_id;
        job = get_job_entry(job_id, server.job_list);
        server_status[i * global_const::accelator_per_server_max + j].job_id = job_id;
        if (job->is_preemtion_possible()){
          job_element new_element(job, i, j);
          job_list.push_back(new_element);
        }
      }
      server_status[i * global_const::accelator_per_server_max + j].status = gpu_allocation_type::fixed;

      if( job->is_preemtion_possible() )
        server_status[i * global_const::accelator_per_server_max + j].status = gpu_allocation_type::floating;
      
      server_status[i * global_const::accelator_per_server_max + j].job_id = job_id;
    }
  }
}

job_entry* adjusting_server::get_job_entry(string job_id, vector<job_entry*> job_list) {
  for (auto&& job : job_list) {
    if (job->get_job_id() == job_id) {
      return job;
    }
  }

  return nullptr;
}

int adjusting_server::get_optimal_adjusting_dp(int server_count, int accelerator_count, int recursive_count) {
  int i, j;
  static int max_full_empty_server = 0;

  if (0 == recursive_count) {
    max_full_empty_server = calcu_full_empty_server();
  }

  if (recursive_count == job_list.size()) {
    return max_full_empty_server;
  }

  job_element target_job = job_list[recursive_count];
  for (i = 0; i < server_count; ++i) {
    for (j = 0; j < accelerator_count; ++j) {
      if (rearrange_task(i, j, target_job, recursive_count, false)) {
        int full_empty_server = calcu_full_empty_server();
        if (full_empty_server > max_full_empty_server) {
          max_full_empty_server = full_empty_server;
          dumpy_job_list();
        }
        get_optimal_adjusting_dp(server_count, accelerator_count, recursive_count++);
        rearrange_task(i, j, target_job, recursive_count, true);
      }
    }
  }

  return max_full_empty_server;
}

void adjusting_server::dumpy_job_list() {
  optimal_position.clear();
  for (auto job : job_list) {
    optimal_position.push_back(job);
  }
}

int adjusting_server::calcu_full_empty_server() {
  int full_empty_server = 0;
  for (int i = 0; i < server_list->size(); ++i) {
    server_entry& server = server_list->at(i);
    if (server.get_avaliable_accelator_count() == server.get_accelerator_count()) {
      full_empty_server++;
    }
  }

  return full_empty_server;
}

bool adjusting_server::rearrange_task(int server_index, int accelerator_index, job_element job_obj, int recursive_count, bool reverse) {
  int i;
  int server_pos = server_index * global_const::accelator_per_server_max;
  int required_count = job_obj.job->get_accelerator_count();

  if (false == reverse) {
    server_entry server = server_list->at(server_index);

    if (required_count > server.get_accelerator_count()) { return false; }

    int empty_space = 0;
    for ( i = accelerator_index; i < global_const::accelator_per_server_max; ++i) {
      if (gpu_allocation_type::empty != server_status[server_pos + i].status) { break; }
      empty_space++;
    }
 
    if (empty_space < required_count) { return false; }

    for (i = accelerator_index; i < accelerator_index + required_count; ++i) {
      server_status[server_pos + i].status = gpu_allocation_type::adjusted;
      server_status[server_pos + i].job_id = job_obj.job->get_job_id();
    }

    server_pos = job_obj.server_index * global_const::accelator_per_server_max;
    for (i = job_obj.accelerator_index; i < job_obj.accelerator_index + required_count; ++i) {
      server_status[server_pos + i].status = gpu_allocation_type::empty;
      server_status[server_pos + i].job_id = "";
    }
    return true;
  }

  for (i = accelerator_index; i < accelerator_index + required_count; ++i) {
    server_status[server_pos + i].status = gpu_allocation_type::empty;
    server_status[server_pos + i].job_id = "";
  }

  server_pos = job_obj.server_index * global_const::accelator_per_server_max;
  for (i = job_obj.accelerator_index; i < job_obj.accelerator_index + required_count; ++i) {
    server_status[server_pos + i].status = gpu_allocation_type::floating;
    server_status[server_pos + i].job_id = job_obj.job->get_job_id();
  }

  return true;
}