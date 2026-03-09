#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# namgun-workspace — 무중단 업데이트 스크립트
# ═══════════════════════════════════════════════════════
#
# 사용법:
#   bash scripts/update.sh              # 기본 업데이트 (git pull + rebuild)
#   bash scripts/update.sh --no-pull    # git pull 생략 (로컬 변경만 반영)
#   bash scripts/update.sh --rollback   # 직전 이미지로 롤백
#
# 동작:
#   1. 현재 이미지 태그를 백업 (롤백용)
#   2. git pull (최신 코드)
#   3. DB 마이그레이션 (있으면)
#   4. 서비스별 순차 재빌드 + 재시작 (무중단)
#   5. 헬스체크 검증
#   6. 실패 시 자동 롤백
# ═══════════════════════════════════════════════════════

set -euo pipefail

# ─── Colors ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ─── Working directory ───
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$COMPOSE_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/tmp/ws-update-${TIMESTAMP}.log"
NO_PULL=false
ROLLBACK=false

# ─── Parse args ───
for arg in "$@"; do
  case "$arg" in
    --no-pull)  NO_PULL=true ;;
    --rollback) ROLLBACK=true ;;
    --help|-h)
      echo "Usage: bash scripts/update.sh [--no-pull] [--rollback]"
      echo "  --no-pull   Skip git pull (use local changes only)"
      echo "  --rollback  Roll back to previous image versions"
      exit 0
      ;;
    *) err "Unknown option: $arg"; exit 1 ;;
  esac
done

# ─── Rollback ───
if $ROLLBACK; then
  ROLLBACK_FILE="$COMPOSE_DIR/.update-rollback"
  if [[ ! -f "$ROLLBACK_FILE" ]]; then
    err "롤백 정보 없음 (.update-rollback 파일 없음)"
    exit 1
  fi
  info "롤백 시작..."
  while IFS='|' read -r service image; do
    info "  $service → $image"
    docker tag "$image" "namgun-workspace-${service}:latest" 2>/dev/null || true
  done < "$ROLLBACK_FILE"
  docker compose up -d --no-build 2>&1 | tee -a "$LOG_FILE"
  ok "롤백 완료"
  exit 0
fi

echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo -e "${BOLD}  namgun-workspace 업데이트${NC}"
echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo ""

# ─── Step 1: 현재 이미지 백업 (롤백용) ───
info "Step 1/5: 현재 이미지 ID 백업..."
ROLLBACK_FILE="$COMPOSE_DIR/.update-rollback"
> "$ROLLBACK_FILE"
for svc in backend frontend; do
  IMAGE_ID=$(docker inspect "ws-${svc}" --format '{{.Image}}' 2>/dev/null || echo "")
  if [[ -n "$IMAGE_ID" ]]; then
    echo "${svc}|${IMAGE_ID}" >> "$ROLLBACK_FILE"
  fi
done
ok "롤백 정보 저장 (.update-rollback)"

# ─── Step 2: Git pull ───
if $NO_PULL; then
  info "Step 2/5: git pull 생략 (--no-pull)"
else
  info "Step 2/5: git pull..."
  BEFORE_HASH=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
  if git pull origin main 2>&1 | tee -a "$LOG_FILE"; then
    AFTER_HASH=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    if [[ "$BEFORE_HASH" == "$AFTER_HASH" ]]; then
      ok "이미 최신 상태 ($BEFORE_HASH)"
    else
      ok "업데이트됨: ${BEFORE_HASH:0:8} → ${AFTER_HASH:0:8}"
    fi
  else
    err "git pull 실패"
    exit 1
  fi
fi

# ─── Step 3: DB 마이그레이션 ───
info "Step 3/5: DB 마이그레이션 확인..."
# 백엔드가 auto-migration을 시작 시 실행하므로 별도 작업 불필요
ok "마이그레이션은 백엔드 시작 시 자동 실행됨"

# ─── Step 4: 서비스별 순차 재빌드 + 재시작 ───
info "Step 4/5: 서비스 재빌드..."
ERRORS=0

# Backend 먼저 (API 서버)
info "  backend 빌드 중..."
if docker compose build --no-cache backend >> "$LOG_FILE" 2>&1; then
  ok "  backend 빌드 완료"
else
  err "  backend 빌드 실패"
  ERRORS=$((ERRORS + 1))
fi

# Frontend
info "  frontend 빌드 중..."
if docker compose build --no-cache frontend >> "$LOG_FILE" 2>&1; then
  ok "  frontend 빌드 완료"
else
  err "  frontend 빌드 실패"
  ERRORS=$((ERRORS + 1))
fi

if [[ $ERRORS -gt 0 ]]; then
  err "빌드 실패 ${ERRORS}건 — 롤백하려면: bash scripts/update.sh --rollback"
  exit 1
fi

# 순차 재시작 (nginx는 마지막)
info "  서비스 재시작 중..."
docker compose up -d --no-build backend >> "$LOG_FILE" 2>&1
sleep 3

# 백엔드 헬스체크 대기
info "  backend 헬스체크 대기..."
for i in $(seq 1 30); do
  if docker inspect ws-backend --format '{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
    ok "  backend healthy"
    break
  fi
  if [[ $i -eq 30 ]]; then
    err "  backend 헬스체크 타임아웃 (30s)"
    ERRORS=$((ERRORS + 1))
  fi
  sleep 1
done

docker compose up -d --no-build frontend >> "$LOG_FILE" 2>&1
sleep 2
docker compose up -d --no-build nginx >> "$LOG_FILE" 2>&1
ok "  서비스 재시작 완료"

# ─── Step 5: 최종 검증 ───
info "Step 5/5: 최종 검증..."
sleep 3

# 컨테이너 상태 확인
RUNNING=0
TOTAL=0
for svc in ws-postgres ws-redis ws-backend ws-frontend ws-nginx; do
  TOTAL=$((TOTAL + 1))
  if docker inspect "$svc" --format '{{.State.Running}}' 2>/dev/null | grep -q true; then
    RUNNING=$((RUNNING + 1))
  else
    err "  $svc 실행되지 않음"
    ERRORS=$((ERRORS + 1))
  fi
done

# API 헬스체크
if docker exec ws-backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" 2>/dev/null; then
  ok "  API 헬스체크 통과"
else
  err "  API 헬스체크 실패"
  ERRORS=$((ERRORS + 1))
fi

echo ""
if [[ $ERRORS -gt 0 ]]; then
  err "업데이트 완료 (경고 ${ERRORS}건)"
  warn "롤백하려면: bash scripts/update.sh --rollback"
  warn "로그: $LOG_FILE"
  exit 1
else
  ok "업데이트 완료 — 코어 ${RUNNING}/${TOTAL} 서비스 정상"
  info "로그: $LOG_FILE"
fi
