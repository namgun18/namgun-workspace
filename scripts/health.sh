#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# namgun-workspace — 서비스 자가진단 스크립트
# ═══════════════════════════════════════════════════════
#
# 사용법:
#   bash scripts/health.sh          # 전체 진단
#   bash scripts/health.sh --json   # JSON 출력 (모니터링 연동용)
#   bash scripts/health.sh --quiet  # 실패만 출력
#
# 점검 항목:
#   1. Docker 데몬
#   2. 컨테이너 상태 (코어 5개 + 옵션 4개)
#   3. PostgreSQL 연결
#   4. Redis 연결
#   5. API 헬스체크 (/api/health)
#   6. 디스크 사용량
#   7. NFS 스토리지 마운트
#   8. SSL 인증서 만료
# ═══════════════════════════════════════════════════════

set -uo pipefail

# ─── Colors ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ─── Options ───
JSON_MODE=false
QUIET_MODE=false
for arg in "$@"; do
  case "$arg" in
    --json)  JSON_MODE=true ;;
    --quiet) QUIET_MODE=true ;;
    --help|-h)
      echo "Usage: bash scripts/health.sh [--json] [--quiet]"
      echo "  --json   Output as JSON (for monitoring)"
      echo "  --quiet  Show failures only"
      exit 0
      ;;
  esac
done

# ─── Working directory ───
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$COMPOSE_DIR"

# ─── Counters ───
PASS=0
FAIL=0
WARN=0
CHECKS=()

check_pass() {
  PASS=$((PASS + 1))
  CHECKS+=("{\"name\":\"$1\",\"status\":\"pass\",\"detail\":\"$2\"}")
  if ! $QUIET_MODE && ! $JSON_MODE; then
    echo -e "  ${GREEN}✓${NC} $1 ${DIM}— $2${NC}"
  fi
}

check_fail() {
  FAIL=$((FAIL + 1))
  CHECKS+=("{\"name\":\"$1\",\"status\":\"fail\",\"detail\":\"$2\"}")
  if ! $JSON_MODE; then
    echo -e "  ${RED}✗${NC} $1 ${RED}— $2${NC}"
  fi
}

check_warn() {
  WARN=$((WARN + 1))
  CHECKS+=("{\"name\":\"$1\",\"status\":\"warn\",\"detail\":\"$2\"}")
  if ! $JSON_MODE; then
    echo -e "  ${YELLOW}!${NC} $1 ${YELLOW}— $2${NC}"
  fi
}

section() {
  if ! $QUIET_MODE && ! $JSON_MODE; then
    echo ""
    echo -e "${BOLD}─── $1 ───${NC}"
  fi
}

# ═══════════════════════════════════════
#  진단 시작
# ═══════════════════════════════════════
if ! $JSON_MODE; then
  echo -e "${BOLD}namgun-workspace 서비스 자가진단${NC}"
  echo -e "${DIM}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
fi

# ─── 1. Docker 데몬 ───
section "Docker"
if docker info >/dev/null 2>&1; then
  DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
  check_pass "Docker 데몬" "v${DOCKER_VER}"
else
  check_fail "Docker 데몬" "실행되지 않음"
fi

# ─── 2. 컨테이너 상태 ───
section "컨테이너"

CORE_SERVICES=(ws-postgres ws-redis ws-backend ws-frontend ws-nginx)
OPTIONAL_SERVICES=(ws-certbot ws-mailserver ws-gitea ws-livekit)

for svc in "${CORE_SERVICES[@]}"; do
  STATE=$(docker inspect "$svc" --format '{{.State.Status}}' 2>/dev/null || echo "not_found")
  HEALTH=$(docker inspect "$svc" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' 2>/dev/null || echo "n/a")

  if [[ "$STATE" == "running" ]]; then
    if [[ "$HEALTH" == "healthy" || "$HEALTH" == "n/a" ]]; then
      UPTIME=$(docker inspect "$svc" --format '{{.State.StartedAt}}' 2>/dev/null | head -c 19 || echo "")
      check_pass "$svc" "running (health: ${HEALTH}, since: ${UPTIME})"
    elif [[ "$HEALTH" == "unhealthy" ]]; then
      check_fail "$svc" "running but unhealthy"
    else
      check_warn "$svc" "running (health: ${HEALTH})"
    fi
  else
    check_fail "$svc" "$STATE"
  fi
done

for svc in "${OPTIONAL_SERVICES[@]}"; do
  STATE=$(docker inspect "$svc" --format '{{.State.Status}}' 2>/dev/null || echo "not_found")
  if [[ "$STATE" == "running" ]]; then
    check_pass "$svc" "running"
  elif [[ "$STATE" == "not_found" ]]; then
    # Optional service not deployed — not a failure
    if ! $QUIET_MODE && ! $JSON_MODE; then
      echo -e "  ${DIM}○ $svc — 미배포 (선택적)${NC}"
    fi
  else
    check_warn "$svc" "$STATE"
  fi
done

# ─── 3. PostgreSQL ───
section "데이터베이스"
if docker exec ws-postgres pg_isready -U "${DB_USER:-workspace}" >/dev/null 2>&1; then
  PG_VER=$(docker exec ws-postgres psql -U "${DB_USER:-workspace}" -d "${DB_NAME:-workspace}" -tAc "SELECT version();" 2>/dev/null | head -1 | cut -d' ' -f1-2 || echo "unknown")
  DB_SIZE=$(docker exec ws-postgres psql -U "${DB_USER:-workspace}" -d "${DB_NAME:-workspace}" -tAc "SELECT pg_size_pretty(pg_database_size(current_database()));" 2>/dev/null | xargs || echo "unknown")
  check_pass "PostgreSQL" "${PG_VER}, 크기: ${DB_SIZE}"
else
  check_fail "PostgreSQL" "연결 실패"
fi

# ─── 4. Redis ───
if docker exec ws-redis redis-cli ping 2>/dev/null | grep -q PONG; then
  REDIS_MEM=$(docker exec ws-redis redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r' || echo "unknown")
  check_pass "Redis" "PONG, 메모리: ${REDIS_MEM}"
else
  check_fail "Redis" "연결 실패"
fi

# ─── 5. API 헬스체크 ───
section "API"
API_RESP=$(docker exec ws-backend python -c "
import urllib.request, json
try:
    r = urllib.request.urlopen('http://localhost:8000/api/health', timeout=5)
    print(r.read().decode())
except Exception as e:
    print(f'ERROR:{e}')
" 2>/dev/null || echo "ERROR:exec failed")

if echo "$API_RESP" | grep -qi "error"; then
  check_fail "API /health" "$API_RESP"
else
  check_pass "API /health" "응답 정상"
fi

# ─── 6. 디스크 사용량 ───
section "디스크"
DOCKER_ROOT=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || echo "/var/lib/docker")
DISK_USAGE=$(df -h "$DOCKER_ROOT" 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%' || echo "0")
DISK_AVAIL=$(df -h "$DOCKER_ROOT" 2>/dev/null | tail -1 | awk '{print $4}' || echo "unknown")

if [[ "$DISK_USAGE" -lt 80 ]]; then
  check_pass "Docker 디스크" "${DISK_USAGE}% 사용, ${DISK_AVAIL} 여유"
elif [[ "$DISK_USAGE" -lt 90 ]]; then
  check_warn "Docker 디스크" "${DISK_USAGE}% 사용 — 정리 권장 (docker system prune)"
else
  check_fail "Docker 디스크" "${DISK_USAGE}% 사용 — 즉시 정리 필요"
fi

# ─── 7. NFS 스토리지 ───
section "스토리지"
STORAGE_VOL=$(grep '^STORAGE_VOLUME=' .env 2>/dev/null | cut -d= -f2 || echo "")
if [[ -n "$STORAGE_VOL" ]]; then
  MOUNT_CHECK=$(docker volume inspect "$STORAGE_VOL" --format '{{.Options.device}}' 2>/dev/null || echo "")
  if [[ -n "$MOUNT_CHECK" ]]; then
    # Check if actually accessible via backend
    if docker exec ws-backend python -c "import os; os.listdir('/storage')" >/dev/null 2>&1; then
      check_pass "NFS 스토리지" "${STORAGE_VOL} (${MOUNT_CHECK})"
    else
      check_fail "NFS 스토리지" "볼륨 존재하나 /storage 접근 불가"
    fi
  else
    check_warn "NFS 스토리지" "볼륨 ${STORAGE_VOL} 정보 없음"
  fi
else
  if ! $QUIET_MODE && ! $JSON_MODE; then
    echo -e "  ${DIM}○ NFS 스토리지 — STORAGE_VOLUME 미설정${NC}"
  fi
fi

# ─── 8. SSL 인증서 만료 ───
section "SSL"
DOMAIN=$(grep '^DOMAIN=' .env 2>/dev/null | cut -d= -f2 || echo "namgun.or.kr")
if command -v openssl >/dev/null 2>&1; then
  CERT_EXPIRY=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN":443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2 || echo "")
  if [[ -n "$CERT_EXPIRY" ]]; then
    EXPIRY_EPOCH=$(date -d "$CERT_EXPIRY" +%s 2>/dev/null || echo "0")
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
    if [[ $DAYS_LEFT -gt 30 ]]; then
      check_pass "SSL 인증서" "${DOMAIN} — ${DAYS_LEFT}일 남음 (${CERT_EXPIRY})"
    elif [[ $DAYS_LEFT -gt 7 ]]; then
      check_warn "SSL 인증서" "${DOMAIN} — ${DAYS_LEFT}일 남음 — 갱신 필요"
    else
      check_fail "SSL 인증서" "${DOMAIN} — ${DAYS_LEFT}일 남음 — 즉시 갱신!"
    fi
  else
    check_warn "SSL 인증서" "인증서 정보 조회 실패"
  fi
else
  if ! $QUIET_MODE && ! $JSON_MODE; then
    echo -e "  ${DIM}○ SSL — openssl 미설치${NC}"
  fi
fi

# ═══════════════════════════════════════
#  결과 출력
# ═══════════════════════════════════════

if $JSON_MODE; then
  echo "{"
  echo "  \"timestamp\": \"$(date -Iseconds)\","
  echo "  \"pass\": $PASS,"
  echo "  \"fail\": $FAIL,"
  echo "  \"warn\": $WARN,"
  echo "  \"checks\": ["
  for i in "${!CHECKS[@]}"; do
    if [[ $i -lt $((${#CHECKS[@]} - 1)) ]]; then
      echo "    ${CHECKS[$i]},"
    else
      echo "    ${CHECKS[$i]}"
    fi
  done
  echo "  ]"
  echo "}"
else
  echo ""
  echo -e "${BOLD}═══════════════════════════════════════${NC}"
  if [[ $FAIL -eq 0 ]]; then
    echo -e "  ${GREEN}${BOLD}ALL PASS${NC}  ✓ ${PASS} pass, ${WARN} warn, ${FAIL} fail"
  else
    echo -e "  ${RED}${BOLD}FAILURE${NC}   ✓ ${PASS} pass, ! ${WARN} warn, ✗ ${FAIL} fail"
  fi
  echo -e "${BOLD}═══════════════════════════════════════${NC}"
fi

# Exit code: 0 if no failures, 1 if any failure
[[ $FAIL -eq 0 ]]
