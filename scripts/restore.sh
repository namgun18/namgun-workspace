#!/usr/bin/env bash
# =============================================
# namgun-workspace — Restore Script
# =============================================
# Usage: sudo bash scripts/restore.sh [backup-dir]
#
# Restores from a backup created by backup.sh:
#   - PostgreSQL (pg_dump gzip)
#   - Redis (RDB file)
#   - Mail data (tar archive)
# =============================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

BACKUP_DIR="${1:-}"
COMPOSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ERRORS=0

# ─── Pre-flight ───

if [[ -z "$BACKUP_DIR" ]]; then
    echo -e "${BOLD}Usage:${NC} sudo bash scripts/restore.sh <backup-directory>"
    echo ""
    echo "Available backups:"
    BACKUP_ROOT="${COMPOSE_DIR}/backups"
    if [[ -d "$BACKUP_ROOT" ]]; then
        ls -1d "$BACKUP_ROOT"/*/ 2>/dev/null | while read -r d; do
            ts=$(basename "$d")
            files=$(ls "$d" 2>/dev/null | wc -l)
            size=$(du -sh "$d" 2>/dev/null | cut -f1)
            echo "  $d  ($files files, $size)"
        done
    else
        echo "  No backups found in $BACKUP_ROOT"
    fi
    exit 1
fi

if [[ ! -d "$BACKUP_DIR" ]]; then
    err "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

cd "$COMPOSE_DIR"

if ! command -v docker &>/dev/null; then
    err "docker not found"
    exit 1
fi

echo ""
echo -e "${BOLD}=== namgun-workspace Restore ===${NC}"
echo -e "Backup: ${CYAN}$BACKUP_DIR${NC}"
echo ""

# ─── Confirmation ───

echo -e "${YELLOW}WARNING: This will OVERWRITE the current database and data.${NC}"
echo -e "${YELLOW}Make sure you have a current backup before proceeding.${NC}"
echo ""
read -rp "Type 'RESTORE' to confirm: " CONFIRM
if [[ "$CONFIRM" != "RESTORE" ]]; then
    info "Restore cancelled."
    exit 0
fi

# ─── 1. PostgreSQL ───

PG_DUMP=$(find "$BACKUP_DIR" -name "postgres_*.sql.gz" -type f 2>/dev/null | head -1)
if [[ -n "$PG_DUMP" ]]; then
    info "Restoring PostgreSQL from $(basename "$PG_DUMP")..."

    # Get DB credentials from .env
    DB_USER=$(grep '^DB_USER=' .env 2>/dev/null | cut -d= -f2 || echo "workspace")
    DB_NAME=$(grep '^DB_NAME=' .env 2>/dev/null | cut -d= -f2 || echo "workspace")
    DB_USER="${DB_USER:-workspace}"
    DB_NAME="${DB_NAME:-workspace}"

    # Drop and recreate database
    docker compose exec -T postgres psql -U "$DB_USER" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" \
        2>/dev/null || true

    docker compose exec -T postgres dropdb -U "$DB_USER" --if-exists "$DB_NAME" 2>/dev/null || true
    docker compose exec -T postgres createdb -U "$DB_USER" "$DB_NAME" 2>/dev/null || true

    # Restore
    gzip -dc "$PG_DUMP" | docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -q 2>/dev/null
    if [[ $? -eq 0 ]]; then
        ok "PostgreSQL restored ($(du -h "$PG_DUMP" | cut -f1))"
    else
        err "PostgreSQL restore failed"
        ERRORS=$((ERRORS + 1))
    fi
else
    warn "No PostgreSQL backup found in $BACKUP_DIR"
fi

# ─── 2. Redis ───

REDIS_DUMP=$(find "$BACKUP_DIR" -name "redis_*.rdb" -type f 2>/dev/null | head -1)
if [[ -n "$REDIS_DUMP" ]]; then
    info "Restoring Redis from $(basename "$REDIS_DUMP")..."
    docker compose cp "$REDIS_DUMP" redis:/data/dump.rdb 2>/dev/null
    docker compose restart redis 2>/dev/null
    if [[ $? -eq 0 ]]; then
        ok "Redis restored ($(du -h "$REDIS_DUMP" | cut -f1))"
    else
        err "Redis restore failed"
        ERRORS=$((ERRORS + 1))
    fi
else
    warn "No Redis backup found in $BACKUP_DIR"
fi

# ─── 3. Mail ───

MAIL_DUMP=$(find "$BACKUP_DIR" -name "mail_*.tar.gz" -type f 2>/dev/null | head -1)
if [[ -n "$MAIL_DUMP" ]]; then
    if docker compose ps --status running 2>/dev/null | grep -q mailserver; then
        info "Restoring mail data from $(basename "$MAIL_DUMP")..."
        docker compose cp "$MAIL_DUMP" mailserver:/tmp/mail_restore.tar.gz 2>/dev/null
        docker compose exec -T mailserver bash -c "cd / && tar xzf /tmp/mail_restore.tar.gz && rm /tmp/mail_restore.tar.gz" 2>/dev/null
        if [[ $? -eq 0 ]]; then
            ok "Mail data restored ($(du -h "$MAIL_DUMP" | cut -f1))"
        else
            err "Mail restore failed"
            ERRORS=$((ERRORS + 1))
        fi
    else
        warn "Mailserver not running, skipping mail restore"
    fi
else
    warn "No mail backup found in $BACKUP_DIR"
fi

# ─── 4. Restart services ───

info "Restarting backend to apply restored database..."
docker compose restart backend 2>/dev/null
ok "Backend restarted"

# ─── Summary ───

echo ""
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}=== Restore Complete (0 errors) ===${NC}"
else
    echo -e "${RED}${BOLD}=== Restore Complete ($ERRORS errors) ===${NC}"
fi
echo ""
