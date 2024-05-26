#pragma once
#include <string>
#include <fstream>
#include <vector>
#include <cstdlib>
#include <ctime>
#include <iomanip>
#include <sstream>
#include <chrono>

using namespace std;
class log_generator
{
public:
  struct task_entiry_meta{
    string pod_name;
    string pod_type;
    string project;
    string namespace_;
    string user_team;
    string start;
    string finish;
    int count;
    string time_diff;
    int computing_load;
    double gpu_utilization;
    string flavor;
    string preemption;
  };
  log_generator();

private:
  static string generate_random_string(int length);
  static string generate_random_timestamp();
  int task_count = 100;
};

