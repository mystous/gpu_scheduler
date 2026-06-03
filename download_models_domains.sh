#!/bin/bash
# SQUAD 재실험용 - 추가 도메인 모델 (워크로드 패턴 최대 다양화)
# HF 캐시: ~/.cache/huggingface -> /raid/hf_cache (심링크)
set -u
export PATH="$HOME/.local/bin:$PATH"

LOG="$(dirname "$(readlink -f "$0")")/hf_download_domains.log"
: > "$LOG"

MODELS=(
  # 비전 고급 - 세그멘테이션 (작음, 먼저)
  "facebook/sam2-hiera-large"
  # 언어 도구 - reranker / 번역
  "BAAI/bge-reranker-large"
  "facebook/nllb-200-3.3B"
  # TTS / 오디오 / 음악 생성
  "suno/bark"
  "facebook/musicgen-large"
  # 과학 - 단백질 언어모델
  "facebook/esm2_t36_3B_UR50D"
  # 비디오 생성 (초장기 추론)
  "THUDM/CogVideoX-5b"
)

echo "[$(date '+%F %T')] 추가 도메인 ${#MODELS[@]}개 다운로드 시작 (-> /raid/hf_cache)" | tee -a "$LOG"
ok=0; fail=0
for m in "${MODELS[@]}"; do
  echo "[$(date '+%F %T')] START  $m" | tee -a "$LOG"
  if hf download "$m" >> "$LOG" 2>&1; then
    echo "[$(date '+%F %T')] DONE   $m" | tee -a "$LOG"; ok=$((ok+1))
  else
    echo "[$(date '+%F %T')] FAIL   $m (로그 확인)" | tee -a "$LOG"; fail=$((fail+1))
  fi
done
echo "[$(date '+%F %T')] 완료: 성공 $ok / 실패 $fail" | tee -a "$LOG"
