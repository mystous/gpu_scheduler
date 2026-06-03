#!/bin/bash
# SQUAD 재실험용 워크로드 모델 다운로드 - 보충분 (도메인/크기/패턴 공백 메우기)
# HF 캐시: ~/.cache/huggingface -> /raid/hf_cache (심링크, 26TB 여유)
# 이미 보유한 18개 모델은 제외. 비게이트만 (게이트 Llama 추가분은 승인 후 별도)
set -u
export PATH="$HOME/.local/bin:$PATH"

LOG="$(dirname "$(readlink -f "$0")")/hf_download.log"
: > "$LOG"

MODELS=(
  # 텍스트 LLM dense - 크기 스펙트럼 중간 보충
  "Qwen/Qwen2.5-1.5B-Instruct"
  "Qwen/Qwen2.5-3B-Instruct"
  "Qwen/Qwen2.5-14B-Instruct"
  # 코드 도메인
  "Qwen/Qwen2.5-Coder-7B-Instruct"
  # 멀티모달(Vision-Language) 도메인
  "Qwen/Qwen2-VL-7B-Instruct"
  # MoE 패턴 (희소활성, 멀티 GPU)
  "mistralai/Mixtral-8x7B-Instruct-v0.1"
)

echo "[$(date '+%F %T')] 보충 ${#MODELS[@]}개 모델 다운로드 시작 (-> /raid/hf_cache)" | tee -a "$LOG"
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
