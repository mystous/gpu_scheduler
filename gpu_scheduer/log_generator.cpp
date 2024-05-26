#include "pch.h"
#include "log_generator.h"

log_generator::log_generator() {
}

string log_generator::generate_random_string(int length) {
  string chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  string result;
  for (int i = 0; i < length; ++i) {
    result += chars[rand() % chars.size()];
  }
  return result;
}

string log_generator::generate_random_timestamp() {
  int year = (rand() % 2 == 0) ? 2023 : 2024;
  int month = rand() % 12 + 1;
  int day = rand() % 28 + 1;
  int hour = rand() % 24;
  int minute = rand() % 60;
  int second = rand() % 60;

  ostringstream oss;
  oss << year << "-" << std::setw(2) << std::setfill('0') << 
        month << "-" << std::setw(2) << std::setfill('0') << 
        day << " " << std::setw(2) << std::setfill('0') << 
        hour << ":" << std::setw(2) << std::setfill('0') << 
        minute << ":" << std::setw(2) << std::setfill('0') << 
        second << "+00:00";

  return oss.str();
}