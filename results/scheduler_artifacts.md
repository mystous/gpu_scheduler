# 비교 스케줄러 코드·데이터 공개 현황

각 스케줄러의 (i) 공개 소스 코드, (ii) 공개 잡로그/트레이스, (iii) 분석·아티팩트 가용성과
본 연구의 실험 포함 방식을 정리한다. 베이스라인 충실도 대조검증은 `baseline_fidelity.md` 참고.

| 스케줄러 | 발표 | 공개 코드 | 잡로그/트레이스 | 분석·아티팩트 | 본 실험 |
|---|---|---|---|---|---|
| FIFO / SJF | 고전 | 없음(교과서) | — | — | 동일엔진 |
| EASY backfilling | HPC | 없음(Slurm 등 내장) | Parallel Workloads Archive (SWF) | — | 동일엔진 |
| LAS (Tiresias) | NSDI'19 | SymbioticLab/Tiresias | yarn-gput{1k,5k,10k}.csv 동봉 | 이산시간 시뮬 | 동일엔진 |
| Kueue | k8s | kubernetes-sigs/kueue (Go) | 없음(라이브 컨트롤러) | 벤치마크 문서 | 동일엔진 |
| Themis | NSDI'20 | **미공개** | 없음 | 논문 평가만 | 동일엔진(근사) |
| FGD | ATC'23 | hkust-adsl/kubernetes-scheduler-simulator (Go) | Alibaba cluster-trace-gpu-v2023 | 있음 | 동일엔진 |
| Lucid | ASPLOS'23 | S-Lab-System-Group/Lucid | Helios (HeliosData, 6k GPU·1.5M잡·6개월) | HeliosArtifact | 동일엔진 |
| Sia | SOSP'23 | siasosp23/artifacts (cvxpy) | workloads(philly/saturn)+앱 scalability trace | 시뮬+print_run_stats | 동일엔진(저자 ILP) |
| **sfqa-auto (제안)** | — | 본 저장소 | Philly 111k + B200×8 K8S 실측 | sweep/분석 노트북 | 제안 |
| Optimus | EuroSys'18 | 공식 없음 | — | 논문만 | 관련연구 |
| Pollux | OSDI'21 | petuum/adaptdl (osdi21-artifact) | 자체 | 있음 | 관련연구(Sia 대표) |
| Gandiva | OSDI'18 | 미공개(Microsoft) | — | — | 관련연구 |
| Arena/Rubick/RLTune/FFT/NotebookOS | '25–'26 | 대부분 미공개/불명 | — | 논문만 | 관련연구 |

## 요약
- **공개 코드 있음**: Tiresias, Kueue, FGD, Lucid, Sia, Pollux (+ 본 연구).
- **공개 코드 없음**: Themis, Optimus, Gandiva (+ FIFO/SJF/EASY는 교과서 알고리즘).
- **공개 잡로그/트레이스**: Tiresias(yarn-gput), FGD(Alibaba GPU trace), Lucid(Helios),
  Sia(philly/saturn workloads), EASY(SWF, 외부). Philly 원본은 microsoft/philly-traces.
- 본 연구는 코드 공개 여부와 무관하게 모든 베이스라인을 **단일 통합 엔진**에서 비교하되,
  공개 코드가 있는 것은 그 알고리즘과 라인 단위 대조검증을 거쳤다(`baseline_fidelity.md`).
  Themis는 코드가 없어 finish-time-fairness ρ 정렬로 근사함을 명시한다.
