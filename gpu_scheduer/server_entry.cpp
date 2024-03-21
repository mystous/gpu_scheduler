#include "pch.h"
#include "server_entry.h"

server_entry::server_entry(string server_name, accelator_type coprocessor_type, int accelator_count) :
  accelator_count(accelator_count), server_name(server_name), coprocessor_type(coprocessor_type) {
  build_accelator_status();
};

void server_entry::set_server_setting(string server_name, int accelator_count, accelator_type coprocessor_type) {
  this->accelator_count = accelator_count;
  this->server_name = server_name;
  this->coprocessor_type = coprocessor_type;
  build_accelator_status();
};

void server_entry::build_accelator_status() {
  reserved.clear();

  for (int i = 0; i < accelator_count; ++i) {
	  reserved.push_back(false);
  }
}

bool server_entry::assign_accelator(job_entry* job, int required_accelator_count) {
  if (required_accelator_count > get_avaliable_accelator_count()) {
    return false;
  }

  for( int i = 0 ; i < accelator_count ; ++i ){
    if (true == reserved[i]) {
      continue;
    }

    job->assign_accelerator(i);
    reserved[i] = true;
  }
  job_list.push_back(job);

  return true;
}

int server_entry::get_avaliable_accelator_count() {
  int avaliable_count = 0;
  for (auto&& avaliable_server : reserved) {
    if (false == avaliable_server) {
      avaliable_count++;
    }
  }
  return avaliable_count;
}