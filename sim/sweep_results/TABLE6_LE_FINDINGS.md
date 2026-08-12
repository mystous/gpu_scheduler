# Table 6 모집단 정정 재실험 (Alibaba le256 · Helios lucid)

논문 Table 6 "Generalization across independent large-scale traces"의 미결 두 곳을
실제 산출물로 채우기 위한 재실행 기록. 2026-08-13.

- **(A) Alibaba 열 모집단 불일치** — 커밋된 `alibaba/cmp256_hetero`는 정책마다 n이 달랐다.
  차단형(fifo 13,914 / sfqa-auto 13,914 / sfqa 26,589)은 256 GPU를 초과하는 요청 26건에
  막혀 중단했고, 비차단형(sjf·las·kueue·easy·themis·fgd 120,079)은 그 26건을 건너뛰고
  완주했다. 서로 다른 모집단이라 한 표에 놓을 수 없다.
- **(B) Helios 열의 Lucid 칸이 비어 있음(`--`)** — `helios_le80/cmp80_single/summary_le.csv`에
  아홉 정책만 있고 lucid 행이 없었다.

정정 방식은 Helios에 이미 적용한 것과 동일하다. 클러스터 용량을 넘는 요청을 **사전 필터**해
전 정책이 같은 모집단을 보게 만든다(D26).

---

## 1. 실행

```bash
cd sim
# (A) Alibaba — 10정책
python3 rerun_le_cells.py --trace alibaba_trace.csv --cap 256 --gpu 256 --kind single \
    --policies fifo,sjf,las,kueue,easy,themis,fgd,lucid,sfqa,sfqa-auto \
    --outdir sweep_results/alibaba_le256/cmp256_single

# (B) Helios — lucid 한 정책 (기존 cmp80_single 보존 위해 별도 outdir)
python3 rerun_le_cells.py --trace helios_trace_sub.csv --cap 80 --gpu 80 --kind single \
    --policies lucid --outdir sweep_results/helios_le80/cmp80_single_lucid
```

`--kind single`(Table 6의 Philly 열이 Table 1의 256 single과 일치하고 Helios 열도 single로
통일). `sfqa`는 `@` 없이 실행 — `policies.py`의 SFQA 기본값 `alpha=0.13889`가 논문의 고정 α다.

**실제 실행은 정책당 1프로세스로 병렬 처리**했다. 정책 간 독립 실행(각자 트레이스를 새로
로드하고 노드를 새로 생성)이라 순차 실행과 결과가 같다. `OMP_NUM_THREADS=1` 고정.
`fifo`와 `sjf`만 순차 러너에서 나왔고 나머지 8개는 병렬 프로세스에서 나왔다.

### 모집단 확인

| 트레이스 | 전체 | 최대 요청 | 클러스터 | 초과 요청 | 사용 |
|---|---|---|---|---|---|
| Alibaba | 120,105 | 800 GPU | 256 | 26 | **120,079** |
| Helios(50% 서브샘플) | 62,735 | 200 GPU | 80 | 666 | **62,069** |

Philly는 최대 요청이 8 GPU(노드 경계)라 256·512·1024 어느 구성에서도 초과 잡이 없다.
초과 요청이 Alibaba·Helios에만 있는 이유는 gang 총량이 `inst_num × per-instance GPU`로
커지기 때문이다(Alibaba에 200·400·512·800 GPU 요청이 실재).

---

## 2. 결과

### 2.1 Alibaba `alibaba_le256/cmp256_single/summary_le.csv`

| policy | n | q_p50 | q_max | fair_mean | **fair_p1** | **lt50_pct** | alloc_avg | 소요 |
|---|---|---|---|---|---|---|---|---|
| fifo | 120,079 | 12,403,124.0 | 23,335,826.5 | 100.0 | **100.0** | **0.00** | 75.7 | 19s |
| sjf | 120,079 | 2.0 | 22,489,094.0 | 93.9 | **0.0** | **6.04** | 74.9 | 4,825s |
| las | 120,079 | 2.0 | 21,722,644.5 | 89.3 | **0.0** | **10.55** | 80.8 | 8,207s |
| kueue | 120,079 | 2.0 | 21,722,644.5 | 89.3 | **0.0** | **10.55** | 80.8 | 8,203s |
| easy | 120,079 | 31,776,104.0 | 80,082,945.0 | 83.4 | **0.0** | **13.44** | 41.2 | 509s |
| themis | 120,079 | 2.0 | 22,827,117.0 | 93.0 | **0.0** | **6.56** | 75.6 | 4,958s |
| fgd | 120,079 | 2.0 | 22,098,221.0 | 88.9 | **0.0** | **10.97** | 76.2 | 10,669s |
| lucid | 120,079 | 0.0 | 22,965,786.2 | 94.2 | **0.0** | **5.77** | 58.0 | 5,079s |
| sfqa | 120,079 | 12,069,590.5 | 22,926,759.5 | 99.9 | **94.7** | **0.00** | 77.2 | 120s |
| sfqa-auto | 120,079 | 12,406,406.0 | 23,361,435.0 | 100.0 | **99.9** | **0.00** | 76.1 | 235s |

### 2.2 Helios lucid `helios_le80/cmp80_single_lucid/summary_le.csv`

| policy | n | q_p50 | q_max | fair_mean | **fair_p1** | **lt50_pct** | alloc_avg | 소요 |
|---|---|---|---|---|---|---|---|---|
| lucid | 62,069 | 2.0 | 43,013,776.4 | 94.5 | **0.0** | **5.09** | 91.0 | 516s |

### 2.3 검증 게이트

| # | 조건 | 결과 |
|---|---|---|
| 1 | Alibaba 전 정책 n = 120,079 | **통과** (10/10) |
| 2 | Alibaba fifo `fair_p1`=100.0, `lt50_pct`=0.0 | **통과** — 차단형 FIFO가 도착순을 지킨다는 정의와 일치 |
| 3 | Alibaba 정책 10개 행 | **통과** |
| 4 | Helios lucid n = 62,069 | **통과** — 나머지 8개 정책과 동일 모집단 |

---

## 3. 지표 매핑

| 논문 열 | 산출물 컬럼 |
|---|---|
| Overtaken | `lt50_pct` |
| Fairness | `fair_p1` |

`fair_mean`이 아니다. §V-A가 Fairness를 bottom-1% order-fairness score로 정의한다.
(원 논문의 Helios Fairness 97.6은 같은 행의 `fair_mean`을 잘못 가져다 쓴 값이었고,
`fair_p1`은 80.0이었다.)

---

## 4. Table 6 반영

| 행 | 열 | 이전 | 새 값 |
|---|---|---|---|
| Lucid | Helios Overtaken | `--` | **5.1** |
| Lucid | Helios Fairness | `--` | **0** |
| Lucid | Alibaba Overtaken | 5.7 | **5.8** |

**Alibaba 열의 나머지 값은 정정 후에도 전부 그대로다.** 기존 표의 Alibaba 값은 이미
비차단 정책이 초과 잡을 건너뛰고 완주한 n=120,079 기준이었고, 이번 정정으로 모집단이
바뀐 건 차단형 세 행(fifo·sfqa·sfqa-auto)인데 그 세 행의 Overtaken/Fairness가 정의상
또는 실측상 같은 값으로 나왔다.

| 정책 | Alibaba 논문값 | 재실행 | 일치 |
|---|---|---|---|
| FIFO | 0.0 / 100 | 0.0 / 100.0 | ○ |
| SJF | 6.0 / 0 | 6.0 / 0.0 | ○ |
| LAS·Kueue | 10.6 / 0 | 10.6 / 0.0 (두 정책 값 완전 동일) | ○ |
| EASY | 13.4 / 0 | 13.4 / 0.0 | ○ |
| Themis | 6.6 / 0 | 6.6 / 0.0 | ○ |
| Lucid | 5.7 / 0 | **5.8** / 0.0 | 반올림 정정 |
| SAFA (고정 α) | 0.0 / 94.7 | 0.0 / 94.7 | ○ |
| SAFA | 0.0 / 99.9 | 0.0 / 99.9 | ○ |

### 범위 재계산

Order 베이스라인 6개(SJF, LAS, Kueue, EASY, Themis, Lucid) 기준.

| 트레이스 | Overtaken 범위 | Fairness |
|---|---|---|
| Philly (256 single) | 3.4 ~ 8.1% | 전부 0 |
| Helios (80) | **5.1 ~ 17.5%** (이전 8.5~17.5, lucid 5.09가 새 최소) | 전부 0 |
| Alibaba (256) | 5.8 ~ 13.4% | 전부 0 |
| **세 트레이스 종합** | **3.4 ~ 17.5%** (변동 없음 — 최소는 Philly Lucid 3.4, 최대는 Helios LAS/Kueue 17.5) | 전부 0 |

"every one of them falls to a Fairness of 0"은 세 트레이스 18개 조합 모두에서 참이다.

---

## 5. 관찰

### 5.1 lucid는 완주했다

`ALIBABA_FINDINGS.md` §7에 "LucidSim은 Alibaba의 짧은-꼬리 분포에서 finish 이벤트가
폭증해 풀 120k 트레이스로 45분+ 미수렴"이라 적혀 있었고 그래서 기존 `cmp256_single`에
lucid 행이 없었다. 이번에는 **Alibaba 5,079초(85분), Helios 516초(8.6분)로 둘 다 완주**했다.
그때는 과부하/이종 구성이었고 이번은 single·모집단 정정 구성이라 조건이 다르다.
따라서 본문의 "Lucid did not complete on this trace" 문장은 더 이상 사실이 아니다.

### 5.2 비차단 정책이 오래 걸리는 이유

`engine.py`의 배치 루프는 차단형이면 선두가 안 들어갈 때 즉시 `break`하지만(FIFO 19초),
비차단형은 `continue`로 **백로그 전체를 매 스케줄링 라운드마다 훑는다**. Alibaba는
duration p50이 614초라 완료 이벤트가 많고, 라운드 수 × 백로그 깊이로 비용이 곱해진다.
백로그가 얕게 유지되는 `easy`(head reservation)가 509초인 반면 큐가 계속 자라는
`las`/`kueue`/`fgd`가 2~3시간 걸린 것이 이 구조 때문이다. `fgd`는 배치 후보마다
단편화 증가량 ΔF를 계산해 가장 느리다(10,669초).

### 5.3 las = kueue

두 정책이 `q_p50`·`q_max`·`fair_mean`·`fair_p1`·`lt50_pct`까지 완전히 동일하다.
비선점 엔진에서 order 키가 같은 값으로 귀결되기 때문이며, Table 6이 두 정책을
한 행(LAS/Kueue)으로 묶는 근거가 된다. `fgd`는 order는 같지만 배치가 달라
lt50이 10.97로 갈라진다(Table 6의 Order 베이스라인 행에는 들어가지 않는다).

---

## 6. 산출물

| 경로 | 내용 | 비고 |
|---|---|---|
| `alibaba_le256/cmp256_single/summary_le.csv` | 10정책 요약 | 비압축 |
| `alibaba_le256_raw.tar.gz` | 정책별 `*_jobs.csv`·`*_alloc.csv` | 178MB → 49MB |
| `helios_le80/cmp80_single_lucid/` | lucid 요약 + jobs/alloc | 7.5MB, 비압축 (형제 디렉터리 `cmp80_single/`이 이미 비압축 커밋이라 맞춤) |

압축 해제:
```bash
mkdir -p raw/alibaba_le256 && tar xzf alibaba_le256_raw.tar.gz -C raw/alibaba_le256
```

기존 `alibaba/`와 `helios_le80/cmp80_single/`은 **덮어쓰지 않았다.**
