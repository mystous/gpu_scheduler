#pragma once
#include <chrono>
#include <string>

using namespace std;
using namespace std::chrono;

class utility_class
{
public:
  static system_clock::time_point parse_time_string(const string& time_str);
  static string conver_tp_str(const system_clock::time_point tp);
  static string double_to_string(double value);
};

