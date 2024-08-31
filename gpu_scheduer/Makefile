# 컴파일러와 컴파일 옵션
CXX = g++
CXXFLAGS = -Wall -std=c++20

# 소스 파일 목록
SRCS = call_back_object.cpp \
       coprocessor_server.cpp \
       job_emulator.cpp \
       job_entry.cpp \
       job_scheduler.cpp \
       linux_main.cpp \
       scheduler_compact.cpp \
       scheduler_fare_share.cpp \
       scheduler_mcts.cpp \
       scheduler_mostallocated.cpp \
       scheduler_round_robin.cpp \
       server_entry.cpp \
       utility_class.cpp

# 오브젝트 파일 목록
OBJS = call_back_object.o \
       coprocessor_server.o \
       job_emulator.o \
       job_entry.o \
       job_scheduler.o \
       linux_main.o \
       scheduler_compact.o \
       scheduler_fare_share.o \
       scheduler_mcts.o \
       scheduler_mostallocated.o \
       scheduler_round_robin.o \
       server_entry.o \
       utility_class.o

# 실행 파일 이름
TARGET = gpu_schduler_emul

# 기본 타겟
all: $(TARGET)

# 실행 파일 생성 규칙
$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJS)

# 개별 오브젝트 파일 생성 규칙
%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# 클린업 규칙
clean:
	rm -f $(OBJS) $(TARGET)

# Makefile 종료
.PHONY: all clean
