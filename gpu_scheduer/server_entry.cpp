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
    if( i % 3 )
      reserved.push_back(false);
    else
      reserved.push_back(true);
  }
}