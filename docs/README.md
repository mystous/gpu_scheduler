# GPU 스케줄러 프로젝트 개요

## 소개

GPU 스케줄러 프로젝트는 **GPU 리소스 할당 및 작업 스케줄링**을 시뮬레이션하는 종합 시스템입니다. Linux 환경에서 동작하며, 다양한 스케줄링 알고리즘의 성능을 비교하기 위한 실험 플랫폼입니다.

## 주요 특징

- 멀티스레드 기반 실험 수행
- 5개의 서로 다른 스케줄링 알고리즘 구현
- 하이퍼파라미터 자동 탐색 (그리드 서치)
- GPU 메모리 최적화 (Defragmentation)
- 작업 선점(Preemption) 및 기아(Starvation) 방지 기능

## 디렉토리 구조

```
gpu_scheduler/
├── gpu_scheduer/              # 주요 스케줄러 소스 코드
│   ├── linux_main.cpp         # Linux용 메인 엔트리포인트
│   ├── *.cpp / *.h            # 핵심 구현 파일들
│   ├── res/                   # 리소스 폴더
│   ├── Makefile               # Linux 컴파일 설정
│   └── gpu_scheduer.vcxproj   # Visual Studio 프로젝트
├── command/                   # 명령행 도구
├── experiment/                # 실험 데이터 및 결과
├── gen_data/                  # 데이터 생성 (Python)
├── data_analsys/              # 데이터 분석
├── result/                    # 실험 결과
├── docs/                      # 문서
├── Makefile                   # 최상위 빌드 설정
├── server.csv                 # 서버 설정 파일
└── job_flow_total.csv         # 작업 데이터
```

## 지원 스케줄러

| 스케줄러 | 설명 |
|---------|------|
| MostAllocated | 가장 많이 할당된 서버 우선 선택 |
| Compact | 압축 배치로 조각화 방지 |
| Round-Robin | 순환 방식 부하 분산 |
| MCTS | Monte Carlo Tree Search 기반 최적화 |
| FareShare | 공정 공유 (구현 진행 중) |

## 지원 GPU 타입

- A100, A30, V100, H100, H200, L4, L40, B200

## 문서 목록

- [아키텍처 분석](ARCHITECTURE.md)
- [스케줄러 알고리즘](SCHEDULER_ALGORITHMS.md)
- [빌드 및 실행 가이드](BUILD_GUIDE.md)
- [클래스 참조](CLASS_REFERENCE.md)
