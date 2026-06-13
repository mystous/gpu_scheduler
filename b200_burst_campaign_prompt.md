# B200 버스트 캠페인 프롬프트 — blocking-aware 컨트롤러 실측 (단일노드 잔여 검증)

아래 전체를 **B200 호스트의 Claude Code 세션**에 그대로 붙여넣어라.

---

너는 NVIDIA B200×8 단일노드 K8s 호스트에서 작업한다. 컨트롤러가 **blocking-aware 해제 + 도착-순번(counter) 나이**로 수정되었다(`--release {blocking,greedy} --age-mode {counter,wall}`, 기본=신규 권장). 목적은 **나이 승급이 활성인 버스트 도착 조건**에서의 첫 실측이다 — 기존 캠페인(균일 도착·greedy)은 승급 비활성 구간이었다.

**로컬 리플레이 예측치(검증 대상)**: blocking+counter → p1≈93·lt50≈0 / greedy → p1≈3.8·lt50≈5. 실측이 이 대비를 재현하는지가 핵심 질문이다.

## 0. 고정 경로
- repo `/home/mystous/gpu_scheduler` (브랜치 `b200-campaign`), venv `/raid/squad/venv/bin/python`
- `export KUBECONFIG=/home/mystous/.kube/config`, run 데이터 `/raid/squad/runs/`
- **기존 `m_ht_*` run은 절대 건드리지 말 것**(보존). 신규 run id는 `b_*` 접두.

## 1. pull + 컨트롤러 수정 확인
```bash
cd /home/mystous/gpu_scheduler && git fetch origin && git checkout b200-campaign && git pull origin b200-campaign
grep -n "release\|age_mode\|seen_pods" squad_ctrl/policy_controller.py | head -8   # 신규 플래그 3종 보여야 함
grep -c "elif blocking:" squad_ctrl/policy_controller.py                            # 1 이어야 함
```

## 2. 버스트 트레이스 생성 (원 도착 패턴 보존, 도착만 /40 압축)
```bash
/raid/squad/venv/bin/python - << 'EOF'
import csv
rows=list(csv.DictReader(open('/home/mystous/gpu_scheduler/results/philly_sample500_jct2h_window.csv')))
for r in rows: r['arrival_time_s']=str(float(r['arrival_time_s'])/40.0)
w=csv.DictWriter(open('/home/mystous/gpu_scheduler/results/philly_sample500_burst40.csv','w',newline=''),fieldnames=rows[0].keys())
w.writeheader(); w.writerows(rows)
print('rows:',len(rows))
EOF
```
- run_experiment의 κ=30이 arrival·duration을 다시 /30 하므로 최종 도착 span ≈ 996초, offered ≈ 3.6×, **submit-clamp 0**(클램프 금지 — 버스트 보존이 목적).

## 3. 실측 run (총 6개, 각 ~50–70분)
공통 EXP: `F="--trace csv --input /home/mystous/gpu_scheduler/results/philly_sample500_burst40.csv --sample 0 --kappa 30 --min-dur 2 --max-dur 0 --submit-clamp 0 --timeout 7200"`
```bash
SC=/home/mystous/gpu_scheduler/squad_ctrl
# (1) 핵심: blocking+counter (컨트롤러 기본값)
"$SC/run_one.sh" sfqa-auto b_auto_block "" "$F"
# (2) 대조: 기존 greedy+wall (재현 플래그)
"$SC/run_one.sh" sfqa-auto b_auto_greedy "--release greedy --age-mode wall" "$F"
# (3) Δ 스윕: blocking+counter, Δ=1초 (주기 아티팩트 분리)
"$SC/run_one.sh" sfqa-auto b_auto_d1 "--period 1" "$F"
# (4) 기준선: FIFO-gate blocking
"$SC/run_one.sh" fifo b_fifo "" "$F"
# (5)(6) 반복: 핵심 run 변동성 (R4)
"$SC/run_one.sh" sfqa-auto b_auto_block_r2 "" "$F"
"$SC/run_one.sh" fifo b_fifo_r2 "" "$F"
```
- 각 run 시작 후 한 번 `kubectl get pods -n squad | grep -c Pending`으로 버스트 큐 형성(수십 개)을 확인. 안 쌓이면 멈추고 보고.
- 진행: `tail -f /raid/squad/runs/run_b_*.log` (끝에 `DONE rc=0`).

## 4. 콜드 이미지 기동 1점 (저비용 — 오버헤드 절 보강)
```bash
# 이미지 캐시 삭제 후 단독 pod 1개 기동 시간 계측 (가능한 노드 명령으로; 불가하면 생략하고 보고)
docker rmi <holder-image> 2>/dev/null || crictl rmi <holder-image> 2>/dev/null
"$SC/run_one.sh" none b_cold "" "--trace csv --input /home/mystous/gpu_scheduler/results/philly_sample500_burst40.csv --sample 0 --limit 1 --kappa 30 --min-dur 30 --max-dur 0 --submit-clamp 0 --timeout 600"
# b_cold의 첫 pod queue→running 시간을 기록(콜드 기동). 캐시 상태와 비교치 보고.
```

## 5. 분석 — 버스트 캠페인용 (trace-arrival 기준)
클램프가 없으므로 도착=wall이 아니라 **트레이스 도착이 물리적 도착**이다. `analyze_b200_heavytail.py`를 복사해 `analyze_b200_burst.py`로 만들고: RUNSET을 `b_*` run들로 교체, 순서 공정성 계산은 submit_log의 `arrival`(트레이스) 열 기준으로(wall과 거의 일치할 것 — 둘 다 보고해 검증). 출력 `results/b200_burst_summary.csv`.

회귀 가드: 기존 `results/b200_heavytail_summary.csv`는 절대 수정 금지.

## 6. 결과 문서 `results/B200_RESULTS_burst.md`
- 표: run별 q_p50/q_max/fair/lt50/p1/alloc + 반복 run 간 차이(변동성).
- **예측 대비**: blocking(예측 p1≈93) vs greedy(≈3.8) — 실측이 대비를 재현하는가? 수치가 어긋나면 어긋난 대로 정직하게(레짐·구현 차이 후보 명시).
- Δ=1 vs 5: alloc 갭·lt50 변화로 주기 아티팩트 몫 분리.
- 콜드 기동: 캐시(1.5–3.5s) 대비 콜드 1점.
- 한계 명시: 단일노드(승급의 효율 이득 레짐 아님 — 검증 대상은 규율·의미론), n=500.

## 7. 커밋·푸시
```bash
cd /home/mystous/gpu_scheduler
git add results/B200_RESULTS_burst.md results/b200_burst_summary.csv squad_ctrl/analyze_b200_burst.py results/philly_sample500_burst40.csv
git commit -m "B200 버스트 캠페인: blocking+counter 실측 — greedy 대조·Δ스윕·반복·콜드 기동"
git push origin b200-campaign
```
raw(`/raid/squad/runs/`)는 커밋 금지.

## 끝나면 보고
1. blocking vs greedy의 p1/lt50 (예측 93/3.8 대비). 2. Δ=1 효과. 3. 반복 변동폭. 4. 콜드 기동 수치. 5. 버스트 큐 형성 확인 여부. 6. 커밋 해시.
