#pragma once
#include <iostream>
#include <vector>
#include "job_entry.h"

using namespace std;
class server_entry
{
public:
  enum class accelator_type : int {
    a100, a30, cpu
  };

  server_entry(string server_name, accelator_type coprocessor_type, int accelator_count);
  int get_accelerator_count() { return accelator_count; };
  string get_server_name() { return server_name; };
  accelator_type get_accelator_type() { return coprocessor_type; };
  void set_server_setting(string server_name, int accelator_count, accelator_type coprocessor_type);
  vector<bool>* get_reserved_status() { return &reserved; };
  int get_avaliable_accelator_count();
  bool assign_accelator(job_entry* job, int required_accelator_count);

private:
  int accelator_count = 0;
  string server_name = "";
  accelator_type coprocessor_type = accelator_type::cpu;
  vector<bool> reserved;
  vector<job_entry*> job_list;

  void build_accelator_status();
};

