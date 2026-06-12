# B200 재실측 프롬프트 — 자동 α(SAFA 제안) 수정본 검증

아래 전체를 **B200 호스트에서 실행 중인 Claude Code 세션**에 그대로 붙여넣어라.

---

너는 NVIDIA B200×8 단일노드 K8s 호스트에서 작업한다. 컨트롤러 `sfqa-auto`(논문의 SAFA 제안 = 자동 α)
알고리즘이 수정되었다(옛 σ*-2-tier-SJF → 논문 SFQAAuto의 α_eff 단일승격 충실 이식).
이 수정본을 받아서 **SAFA(제안) run만** heavy-tail 캠페인과 **완전히 동일한 설정·데이터로** 재실측하고,
결과를 갱신하라. 나머지 8개 정책은 알고리즘이 바뀌지 않았으니 **재실행하지 말고** 기존 측정값을 보존한다.

## 0. 고정 경로·환경
- repo: `/home/mystous/gpu_scheduler`  (브랜치 `b200-campaign`)
- venv: `/raid/squad/venv/bin/python`
- `export KUBECONFIG=/home/mystous/.kube/config`
- run 데이터: `/raid/squad/runs/`  (정책별 `m_ht_*` 디렉토리, 8개는 그대로 둘 것)

## 1. 수정본 pull + 검증
```bash
cd /home/mystous/gpu_scheduler
git fetch origin
git checkout b200-campaign
git pull origin b200-campaign
# 수정 적용 확인: 아래 3줄이 모두 보여야 한다(없으면 멈추고 보고)
grep -n "충실 이식\|alpha_eff = g / (aref \* rmin)\|alpha_eff \* age_rel" squad_ctrl/policy_controller.py
# 옛 코드 잔재 없음 확인: 아래는 결과가 비어야 한다(sfqa-auto 블록에서 SJF tier2 제거됨)
grep -n "tier2.sort(key=lambda t: t\[1\])" squad_ctrl/policy_controller.py || echo "OK: 옛 SJF tier2 제거됨"
```
- `git pull`이 로컬 변경과 충돌하면, 절대 강제 덮어쓰지 말고 `git status`로 무엇이 충돌인지 보고하고 멈춰라.

## 2. 옛 auto run 백업(덮어쓰기 전)
```bash
mv /raid/squad/runs/m_ht_auto /raid/squad/runs/m_ht_auto_OLD_sjf2tier 2>/dev/null || true
ls -d /raid/squad/runs/m_ht_* | sort
```

## 3. SAFA(제안) 재실측 — 캠페인과 100% 동일한 설정·데이터
다른 정책은 건드리지 말 것. 아래 한 줄만 실행한다(원본 m_ht_auto와 동일 인자):
```bash
cd /home/mystous/gpu_scheduler
export KUBECONFIG=/home/mystous/.kube/config
bash squad_ctrl/run_one.sh sfqa-auto m_ht_auto "" \
  "--trace csv --input /home/mystous/gpu_scheduler/results/philly_sample500_jct2h_window.csv --sample 0 --kappa 30 --min-dur 2 --max-dur 0 --submit-clamp 2.0"
```
- 워크로드: 500잡, peak 24 GPU = **3.0× 과부하**, duration heavy-tail 보존(post-κ p50 11s, p99/p50≈20×).
- 소요 ~53분. run_one.sh가 시작 시 `squad` ns의 모든 job/pod를 지우고 컨트롤러+실험을 띄운다.
- **레짐 게이트 확인**(과거 캠페인 기준): 진행 중 한 번 `kubectl get pods -n squad | grep -c Pending`로
  대기 큐가 쌓이고(과부하 형성), `metrics.csv`의 alloc이 80~100%인지 확인. 큐가 안 쌓이면
  과부하 미형성이니 멈추고 보고(설정·트레이스 재점검).
- 진행 모니터: `tail -f /raid/squad/runs/run_m_ht_auto.log` (마지막에 `DONE rc=0`).
  컨트롤러 로그: `tail -f /raid/squad/runs/m_ht_auto_ctrl.log`.

## 4. 재분석(9정책 일괄 — 8개는 기존 데이터, auto만 신규)
```bash
cd /home/mystous/gpu_scheduler/squad_ctrl
/raid/squad/venv/bin/python analyze_b200_heavytail.py
```
- 출력 `results/b200_heavytail_summary.csv`가 9행으로 재생성된다.
- **회귀 점검(필수)**: FIFO/SJF/LAS/Kueue/EASY/Themis/SAFA(고정 α)/FIFO(gate) 8행의
  `lt50`·`fair_mean`·`q_p50`가 갱신 전 표(아래 §6 기준값)와 **동일한지** 확인. 달라졌으면
  다른 run 데이터가 훼손된 것이니 멈추고 보고.

## 5. 결과 문서 갱신 — `results/B200_RESULTS_heavytail.md`
§2 결과표에서 **SAFA(제안) 행만** 새 측정값으로 교체한다(다른 8행 불변). 그리고:
- 표 위/아래 해설에 **수정 전→후 대비**를 1~2문장 추가:
  "옛 sfqa-auto(σ*-2-tier, tier2=SJF)는 짧은 잡 추월로 lt50=28.6의 굶주림을 유발했다.
   논문 SFQAAuto(α_eff 단일승격)로 교체 후 lt50=<신규값>으로 …" — **실제 측정값 그대로** 적되,
  과장 금지. 자동 α가 SAFA(고정 α)(lt50≈5.2) 수준으로 굶주림을 억제하면 "무튜닝 자동 α 검증"으로,
  여전히 높으면 그 사실을 정직하게 보고(레짐·트레이스·후속 과제 명시).
- `git log -1 --format=%H` 커밋 해시를 표 캡션/각주에 기록(재현성).

## 6. 갱신 전 기준값(회귀 비교용 — 이 값들이 §4에서 유지돼야 함)
| 정책 | q_p50 | fair평균 | lt50% |
|---|--:|--:|--:|
| FIFO (default) | 857 | 56.3 | 49.8 |
| FIFO (gate) | 422 | 93.8 | 6.2 |
| SJF | 15 | 71.9 | 30.4 |
| LAS | 424 | 94.5 | 5.2 |
| Kueue | 449 | 95.6 | 4.4 |
| EASY | 1138 | 96.6 | 1.8 |
| Themis | 76 | 70.6 | 31.4 |
| SAFA (고정 α) | 424 | 94.4 | 5.2 |
| **SAFA (제안)** | 134 | 72.7 | **28.6 → 재측정** |

## 7. 커밋·푸시
```bash
cd /home/mystous/gpu_scheduler
git add results/B200_RESULTS_heavytail.md results/b200_heavytail_summary.csv
# (선택) 새 run 로그도 보관하려면: results/b200_runs_heavytail/m_ht_auto/ 갱신본 add
git commit -m "B200 heavy-tail: SAFA(제안) 자동 α 수정본 재실측 — sfqa-auto만 재실행, 8정책 불변"
git push origin b200-campaign
```
raw run 데이터(`/raid/squad/runs/`, *_jobs.csv 류)는 커밋하지 말 것(저장소 외부 보관).

## 끝나면 보고할 것
1. 새 SAFA(제안) 행: q_p50 / fair평균 / **lt50** / p1 / alloc.
2. 8개 정책 회귀 점검 결과(동일/불일치).
3. 레짐 게이트(과부하 형성) 충족 여부.
4. 수정본 커밋 해시.
