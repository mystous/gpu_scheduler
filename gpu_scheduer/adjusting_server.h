#pragma once
#include <vector>
#include "server_entry.h"
class adjusting_server
{
public:
  adjusting_server(vector<server_entry>* servers) 
  : server_list(servers){};

  int defragemetation();
  void reconstruct_server_status();
private:
  vector<server_entry>* server_list = nullptr;
  gpu_defragmentation_method adjusting_method = gpu_defragmentation_method::max_space;

};

