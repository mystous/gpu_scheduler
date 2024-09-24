# 컴파일러 설정
CC = g++
CXXFLAGS = -Wall -Wextra -std=c++20

# 헤더 파일 목록
HEADERS = \
    gpu_scheduer/enum_definition.h \
    gpu_scheduer/global_definistion.h \
    gpu_scheduer/job_emulator.h \
    gpu_scheduer/scheduler_fare_share.h \
    gpu_scheduer/server_entry.h \
    gpu_scheduer/call_back_object.h \
    gpu_scheduer/job_entry.h \
    gpu_scheduer/scheduler_mostallocated.h \
    gpu_scheduer/coprocessor_server.h \
    gpu_scheduer/job_scheduler.h \
    gpu_scheduer/scheduler_compact.h \
    gpu_scheduer/utility_class.h \
    gpu_scheduer/call_back_object.h \
    gpu_scheduer/scheduler_mcts.h \
    gpu_scheduer/utility_class.h \
    gpu_scheduer/experiment_perform.h \
    gpu_scheduer/adjusting_server.h \
    gpu_scheduer/scheduler_round_robin.h

# 소스 파일 목록
SOURCES = \
    gpu_scheduer/job_scheduler.cpp \
    gpu_scheduer/scheduler_fare_share.cpp \
    gpu_scheduer/server_entry.cpp \
    gpu_scheduer/call_back_object.cpp \
    gpu_scheduer/job_emulator.cpp \
    gpu_scheduer/scheduler_mostallocated.cpp \
    gpu_scheduer/coprocessor_server.cpp \
    gpu_scheduer/job_entry.cpp \
    gpu_scheduer/scheduler_compact.cpp \
    gpu_scheduer/scheduler_mcts.cpp \
    gpu_scheduer/utility_class.cpp \
    gpu_scheduer/utility_class.cpp \
    gpu_scheduer/experiment_perform.cpp \
    gpu_scheduer/adjusting_server.cpp \
    gpu_scheduer/scheduler_round_robin.cpp \
    gpu_scheduer/linux_main.cpp

# 오브젝트 파일 목록
OBJECTS = $(SOURCES:.cpp=.o)

# 실행 파일 이름
TARGET = gpu_scheduler

# 기본 목표
all: $(TARGET)

# 실행 파일 생성 규칙
$(TARGET): $(OBJECTS)
	$(CC) $(CXXFLAGS) -o $@ $^

# 오브젝트 파일 생성 규칙
%.o: %.cpp $(HEADERS)
	$(CC) $(CXXFLAGS) -c $< -o $@

# 깨끗하게 만들기 규칙
clean:
	rm -f $(OBJECTS) $(TARGET)

# 재빌드 규칙
rebuild: clean all
