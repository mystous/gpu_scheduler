# Sia 네이티브 실행 결과 (저자 오픈소스, 실제 코드)

저자 아티팩트 `github.com/siasosp23/artifacts`의 `sia-simulator/sia.py`(cvxpy MIP)를
**수정 없이** 전용 환경(numpy<2, cvxpy+CBC[cylp])에서 실행한 결과.

- 워크로드: 저자 제공 `workloads/philly/`(8개, 총 1280잡, 5개 DL 앱 타입으로 매핑)
- 클러스터: Sia 기본 이종(rtx/dgx-ext/aws), 탄력(elastic) goodput 모델
- 커맨드: `multi_simulator.py workloads/philly/ --policy=sia --policy_p_val=-0.5 \
    --mip_lambda_a=0.01 --mip_lambda_n=1.1 --interval=60 --project_throughputs --share_max_replicas`

## 결과 (print_run_stats.py, interval=60)
- Avg Makespan = 14.45 hrs (range 11.0–17.2)
- Avg JCT = 0.656 hrs, p99 JCT = 10.45 hrs
- queue length: mean 0.009, median 0, max 1  (탄력 패킹으로 큐 거의 없음)
- 잡당 평균 재시작 = 4.33 (bert 2.0, cifar10 3.5, deepspeech2 8.0, yolov3 10.8, imagenet 14.9)
- contention: mean 7.27, max 33

## 비교 가능성 주의
Sia는 (i) 자체 이종 클러스터, (ii) 탄력·epoch·goodput 잡 모델(잡별 scalability 프로파일 필요)
에서 동작한다. 우리 본문 표(512 GPU 고정-duration gang, Philly 111k, makespan 154–222일)와는
클러스터 스케일·잡 실행 모델이 근본적으로 다르므로 **직접 비교 불가**. 본 결과는 Sia가 의도된
네이티브 설정에서 정상 동작함을 보이는 **별도 참고치**로만 사용한다.
