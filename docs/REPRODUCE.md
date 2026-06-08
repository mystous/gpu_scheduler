# 논문 실험 재현 가이드 (REPRODUCE.md)

`paper/sn-article.tex`에 실린 **모든 그림·표**를 코드+데이터로 직접 재현하는 커맨드, 산출물이
논문의 어느 요소에 들어가는지, 그리고 시간·디스크 부담을 줄이는 방법을 정리한다.

> 응답·문서 언어는 한글, 커맨드는 그대로. 모든 경로는 저장소 루트(`gpu_scheduler/`) 기준.

---

## 0. 사전 준비

```bash
# Python (시뮬레이터·그래프) — numpy / scipy / pandas / matplotlib
python3 -c "import numpy, scipy, pandas, matplotlib; print('ok')"

# C++ 코어(α 탐색·민감도용) 빌드 — Linux, g++ -std=c++20
make                       # → ./experiment_gpu
```

핵심 입력 데이터:
- `sim/sweep_trace.csv` — Philly 111k 작업 정규 트레이스(약 6 MB, 111,587행). §VI 대규모 실험의 단일 소스.
- `analysis_results/zjob_..._augemented_new_ver.csv` — 옛 증강 로그(3,001잡). 부록 재현용.

---

## 1. 재현 파이프라인 (3단계)

논문 §VI(대규모 평가)의 그림·표는 모두 아래 3단계에서 나온다.

| 단계 | 커맨드 | 산출물 |
|---|---|---|
| ① 시뮬레이션 | `python3 sim/run_sweep.py` | `sim/sweep_results/cmp<gpu>_<kind>/summary.csv` + `raw/` |
| ② 집계·분석 | `python3 sim/analyze_sweep.py` | `sim/sweep_results/sweep_table.csv`, `curve_*.png`, `tradeoff_scatter.png` |
| ③ 논문 그림 렌더 | `python3 results/report_plots.py` | `results/report_*.{pdf,png}` → `paper/Pic/Fig_NN.pdf`로 복사 |

```bash
# ① 전 구성(256/512/1024 × 단일/이종) × 빠른 정책 + Lucid
python3 sim/run_sweep.py
#   (sia는 계산비용 ~2h로 기본 제외 — 커밋된 결과를 ②에서 그대로 사용. 1-2절 참고)

# ② 종합표 + 부하곡선/트레이드오프 원본 PNG 생성
python3 sim/analyze_sweep.py        # → sim/sweep_results/sweep_table.csv

# ③ 출판 품질 벡터 PDF 생성 후 논문 Pic으로 복사
python3 results/report_plots.py
cp results/report_loadcurve.pdf   paper/Pic/Fig_20.pdf
cp results/report_tradeoff.pdf    paper/Pic/Fig_25.pdf
cp results/report_motivation.pdf  paper/Pic/Fig_18.pdf
cp results/report_sensitivity.pdf paper/Pic/Fig_22.pdf
```

---

## 2. 논문 요소 ↔ 재현 커맨드 매핑

| 논문 요소 | 내용 | 생성 코드 | 데이터 출처 | 산출 파일 |
|---|---|---|---|---|
| Fig 1–3 (§III) | HOL 블로킹 개념도 | (원논문 도식, 스크립트 없음) | — | `paper/Pic/Fig_01–03.png` |
| Fig (`fig:motivation`, §V-C) | 최적 α가 8분포에서 7배 변동 | `results/report_plots.py::plot_motivation` | C++ 8분포 α 탐색(§5절) → 상수 `ALPHA_BY_DIST` | `report_motivation.pdf`→`Fig_18.pdf` |
| Fig (`fig:sensitivity`, §V-D) | 잔여 상수 R·P·m 민감도 | `plot_sensitivity` | C++ 12구성 스윕 → 상수 `SENS` | `report_sensitivity.pdf`→`Fig_22.pdf` |
| Fig (`fig:loadcurve`, §VI) | 부하곡선 2×3(단일+이종 × 중앙값/최악/공정성), 11정책 | `plot_loadcurve` | `sim/sweep_results/sweep_table.csv` | `report_loadcurve.pdf`→`Fig_20.pdf` |
| Fig (`fig:tradeoff`, §VI) | q–공정성 트레이드오프, 11정책 × 6구성 | `plot_tradeoff` | `sweep_table.csv` | `report_tradeoff.pdf`→`Fig_25.pdf` |
| Table (`tab:sim-single`) | 단일 512 GPU, 11정책 × {q_p50,q_max,p1,Alloc} | (수기 전사) | `sweep_table.csv`의 `512,single` 행 | 본문 표 |
| Table (`tab:sim`) | 이종 512 GPU, 11정책 × 동일 지표 | (수기 전사) | `sweep_table.csv`의 `512,hetero` 행 | 본문 표 |

표 수치는 `sweep_table.csv`에서 직접 확인:

```bash
column -t -s, sim/sweep_results/sweep_table.csv | grep -E '^gpu|512'
```

### 2-1. C++ α 탐색·민감도(Fig_18·Fig_22 원천)

`report_plots.py`는 현재 C++ 실험의 **요약 상수**(`ALPHA_BY_DIST`, `SENS`)로 그림을 그린다.
그 상수의 원천을 처음부터 재생성하려면 C++ 코어로 8개 합성 분포·민감도 스윕을 돌린다:

```bash
make
# 분포별 작업 로그(experiments_set/ 의 co_*_gen.csv 등)와 server.csv, config.set로 α 스윕
./experiment_gpu <distribution_trace.csv> server.csv <config.set>
# 산출 .result/.result.meta를 analysis_results 노트북에서 집계 → 분포별 최적 α
```

> config.set 포맷·하이퍼파라미터 스윕 규칙은 루트 `CLAUDE.md`의 "config.set 포맷" 절 참고.

### 2-2. Sia(계산비용 큰 정책)

`run_sweep.py`는 sia를 기본 제외한다(256-단일 고부하에서 라운드마다 ILP를 풀어 ~2h).
sia 행은 커밋된 `summary.csv`/`sweep_table.csv`에 이미 있어 ②·③가 그대로 사용한다.
직접 재실행하려면 sia 전용 러너:

```bash
python3 sim/run_all.py --csv sim/sweep_trace.csv --nodes <topology> --policies lucid,sia
#   <topology> 예: 단일 "b200:64" / 이종은 run_sweep.py build_nodes(균등 3분할 b200/h100/a100) 참고
```

---

## 3. 자원(시간·디스크) 부담 줄이기

| 부담 | 원인 | 완화 방법 |
|---|---|---|
| **시간** | sia ILP(256-단일 ~2h) | sia 제외(`--policies`에서 빼고 커밋된 결과 사용). 나머지 11정책 ×6구성 ≈ 수십 분 |
| **시간** | 전 구성 스윕 | 부분만: `python3 sim/run_sweep.py --gpus 512 --kinds hetero --policies fgd,sfqa-auto` |
| **시간** | 오버헤드 모델 | 순수 정책 비교만 필요하면 `--no-overhead` |
| **디스크** | `raw/` per-job 덤프 ≈ 830 MB (gitignore) | 필요할 때만 압축 해제(아래), 분석 후 `raw/` 삭제 |
| **디스크** | C++ `.result` 타임스텝 덤프 ≈ 280 MB/run | 할당률 열만 추출 후 원본 삭제(부록 `sim/repro/run_fig14` 패턴) |

`raw/` 재추출(분석 노트북·`analyze_sweep.py`의 per-job 공정성 계산에 필요):

```bash
cd sim/sweep_results
for f in *_raw.tar.gz; do mkdir -p raw/${f%_raw.tar.gz}; tar xzf "$f" -C raw/${f%_raw.tar.gz}; done
```

권장 최소 재현(논문 핵심 표·그림만, 빠르게):

```bash
# sia 제외 11→10정책, 512 단일·이종만 → 표·트레이드오프 핵심 재현(수 분)
python3 sim/run_sweep.py --gpus 512 --kinds single,hetero
python3 sim/analyze_sweep.py
python3 results/report_plots.py
```

---

## 4. 부록 — 옛 데이터×새 시뮬레이터 재현(왜 옛 Fig_12/14가 재현 안 되는가)

옛 C++ 그림(SFQA 할당률 상향)은 PTR/디프래그 효과였고, PTR을 제거한 새 시뮬레이터에서는
같은 SFQA·같은 트레이스로도 할당률이 바뀌지 않음을 보이는 검증 산출물.

```bash
python3 sim/repro/run_repro.py     # 옛 증강 로그 → 새 sim, FIFO(Normal) vs SFQA, most-alloc/compact
                                    # → sim/repro/data/*_alloc.csv, *_queue.csv
python3 sim/repro/plot_repro.py    # → results/report_repro_fig12.pdf / report_repro_fig14.pdf
```

결론 데이터: Normal·SFQA의 할당률 추세·분포가 거의 일치(평균 48.8% vs 48.5%) — 본문 §VI에서
이 그림들을 제거하고 새 시뮬레이터 결과(`sweep_table.csv`)로 대체한 근거.

> 옛 C++ Fig_12/14 자체의 재현 스크립트(이제 논문 미수록)는 `experiment/repro/`에 보존.

---

## 5. 한 줄 요약

```bash
# 전체 재현(sia 제외, 커밋 결과 활용): 시뮬 → 분석 → 렌더
python3 sim/run_sweep.py && python3 sim/analyze_sweep.py && python3 results/report_plots.py
# 그 뒤 results/report_{loadcurve,tradeoff,motivation,sensitivity}.pdf 를 paper/Pic/Fig_{20,25,18,22}.pdf 로 복사
```
