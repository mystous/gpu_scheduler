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

 /* string time_string = format("{:%Y-%m-%d %H:%M:%S}", tp);
  return time_string;*/

  time_t time = system_clock::to_time_t(tp);
  tm local_tm;
#ifdef _WIN32
  localtime_s(&local_tm, &time); // Windows�� ���
#else
  localtime_r(&time, &local_tm); // POSIX �ý����� ���
#endif

  stringstream ss;
  ss << put_time(&local_tm, "%Y-%m-%d %H:%M:%S") << "+00:00";

  return ss.str();
}

string utility_class::double_to_string(double value){
  std::ostringstream oss;
  oss << std::fixed << std::setprecision(0) << value;
  return oss.str();
}

system_clock::time_point utility_class::get_time_after(system_clock::time_point start, int min) {
  return start + std::chrono::minutes(min);
}

system_clock::time_point utility_class::get_time_after(const string& time_str, int min) {
  return get_time_after(parse_time_string(time_str), min);
}
