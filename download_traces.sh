#!/bin/bash
# SQUAD 트레이스 다운로드 — clone/pull 만 수행 (외부 셸 스크립트 실행 안 함).
# 병합/검증은 clone 후 사람이 검토하여 별도로 진행. 작업 루트: /raid/squad
set -u
TRACES=/raid/squad/traces
TOOLS=/raid/squad/tools
export PATH="$TOOLS/git-lfs-3.5.1:$HOME/.local/bin:$PATH"
LOG=/home/mystous/gpu_scheduler/trace_download.log
: > "$LOG"
log(){ echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# 1) git-lfs 정적 바이너리 (Philly LFS pull 용)
log "git-lfs 설치 확인"
mkdir -p "$TOOLS" && cd "$TOOLS"
if [ ! -x "$TOOLS/git-lfs-3.5.1/git-lfs" ]; then
  curl -sL -o git-lfs.tgz https://github.com/git-lfs/git-lfs/releases/download/v3.5.1/git-lfs-linux-amd64-v3.5.1.tar.gz && tar -xzf git-lfs.tgz
fi
git lfs version >>"$LOG" 2>&1 && log "git-lfs OK" || log "git-lfs 설치 실패"

# 2) Alibaba v2020 (GitHub 데이터 미러, OSS 우회) — clone만
log "Alibaba v2020 미러 clone"
mkdir -p "$TRACES/alibaba_v2020"
if [ ! -d "$TRACES/alibaba_v2020/repo/.git" ]; then
  git clone --depth 1 https://github.com/qzweng/clusterdata-cluster-trace-gpu-v2020-data.git "$TRACES/alibaba_v2020/repo" >>"$LOG" 2>&1
fi
log "Alibaba v2020 clone 완료: $(ls "$TRACES/alibaba_v2020/repo" 2>/dev/null | wc -l) 항목 (병합 별도)"

# 3) Alibaba main repo (v2023 보조) — clone만
log "Alibaba main repo (v2023)"
if [ ! -d "$TRACES/alibaba_repo/.git" ]; then
  git clone --depth 1 --filter=blob:limit=200m https://github.com/alibaba/clusterdata.git "$TRACES/alibaba_repo" >>"$LOG" 2>&1
fi
ls "$TRACES/alibaba_repo/cluster-trace-gpu-v2023/" >>"$LOG" 2>&1

# 4) Philly (git-lfs via GitHub — Azure blob 우회). git 표준 명령만.
log "Philly clone (LFS skip smudge)"
mkdir -p "$TRACES/philly"
if [ ! -d "$TRACES/philly/repo/.git" ]; then
  GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/msr-fiddle/philly-traces.git "$TRACES/philly/repo" >>"$LOG" 2>&1
fi
cd "$TRACES/philly/repo" || exit 1
git lfs install --local >>"$LOG" 2>&1
log "Philly git lfs pull (우회 시도)"
if timeout 1800 git lfs pull >>"$LOG" 2>&1; then
  log "Philly LFS pull 성공: trace-data.tar.gz $(stat -c%s trace-data.tar.gz 2>/dev/null) bytes (압축해제 별도)"
else
  log "Philly git-lfs pull 실패 — 폴백(Option B/C) 필요."
fi
log "clone 단계 종료. 디스크: $(df -h /raid | awk '/md1/{print $3" 사용 / "$4" 여유"}')"
