#include "pch.h"
#include "utility_class.h"

system_clock::time_point utility_class::parse_time_string(const string& time_str) {
  std::tm tm = {};
  istringstream ss(time_str);
  ss >> get_time(&tm, "%Y-%m-%d %H:%M:%S");
  auto tp = system_clock::from_time_t(std::mktime(&tm));
  return tp;
}

string utility_class::conver_tp_str(const system_clock::time_point tp){
  string time_string = format("{:%Y-%m-%d %H:%M:%S}", tp);
  return time_string;
};

string utility_class::double_to_string(double value){
  std::ostringstream oss;
  oss << std::fixed << std::setprecision(0) << value;
  return oss.str();
};
