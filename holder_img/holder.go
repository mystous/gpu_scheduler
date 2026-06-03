// holder — GPU-holder 스텁(정적 Go, 표준 라이브러리만 → 방화벽 무관 빌드).
// nvidia.com/gpu N 개를 요청한 Pod 로 스케줄되어, 압축된 duration 만큼 점유(대기)하고 종료한다.
// 실제 GPU 연산은 하지 않으므로 수천 job 을 유한 시간에 재생 가능(스케줄링 동역학 측정용).
// 선점 가능 job 은 경과시간을 CKPT_PATH 에 기록하고, PTR 이주(evict→재생성) 후 resume.
//
// env: HOLD_SEC(점유 초), PREEMPTIBLE(0/1), CKPT_PATH(체크포인트 파일).
package main

import (
	"os"
	"strconv"
	"strings"
	"time"
)

func main() {
	dur, _ := strconv.ParseFloat(os.Getenv("HOLD_SEC"), 64)
	if dur <= 0 {
		dur = 60
	}
	preempt := os.Getenv("PREEMPTIBLE") == "1"
	ckpt := os.Getenv("CKPT_PATH")

	var elapsed float64
	if preempt && ckpt != "" {
		if b, err := os.ReadFile(ckpt); err == nil {
			if v, e := strconv.ParseFloat(strings.TrimSpace(string(b)), 64); e == nil {
				elapsed = v // 이주 후 resume
			}
		}
	}
	const step = 5.0
	for elapsed < dur {
		time.Sleep(step * time.Second)
		elapsed += step
		if preempt && ckpt != "" {
			_ = os.WriteFile(ckpt, []byte(strconv.FormatFloat(elapsed, 'f', 0, 64)), 0o644)
		}
	}
}
