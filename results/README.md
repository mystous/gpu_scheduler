# SQUAD K8s 실측 결과 (2026-06-04~05 캠페인)

원본 run 데이터는 `/raid/squad/runs/<run_id>/{jct,metrics,submit_log}.csv` (저장소 외부).
여기에는 집계·분석 산출물과 재현용 샘플을 보관한다.

| 파일 | 내용 |
|---|---|
| `SUMMARY.md` | 종합 리포트 — 8정책 본선(κ3000), 충실 duration 체인(S=360), κ6000 적응성, 민감도, EASY-noisy |
| `runs_summary.csv` / `tables.md` | 전체 run 집계 (`squad_ctrl/analyze.py` 산출) |
| `cdf_k3000.png` / `cdf_s360.png` | 큐잉지연·BSLD 전체 CDF (`distributions.py` 산출) |
| `distributions.py` | 분포(백분위·CDF·makespan) 분석기 |
| `sweep_summary.{md,csv}` | C++ 시뮬 민감도 스윕(R 페널티·P 밑·재정렬 창) |
| `philly_sample1000_{raw,normalized}.csv` | 본선 층화 1000 (전체 분포 보존, seed=42) |
| `philly_sample500_jct2h_{fullspan,window}.csv` | JCT≤2h 모집단 층화 500 (충실 체인용) |
|  `philly_sample2000_jct2dcap_fullspan.csv` | **층화 2000, JCT>2일은 2일로 절단(클램프)** — 잡 제거 없음 → GPU 잡수 분포 원본 그대로(87/2/5/6%), GPU-시간 비중 8-GPU 60%, dur p50 22.2분/max 48h(절단 65건). drop 방식은 multi-GPU 장기 잡을 빼서 구성을 왜곡하므로 폐기(사용자 결정 2026-06-05) |

샘플 생성 규칙(전 샘플 공통): 모집단 필터(JCT 상한) → gpu_count 층별 비례 층화 → seed=42 →
duration 분포 자동 보존 검증 → CSV 저장. 재현: `run_experiment.py --sample N --seed 42 --drop-over <초>`.
