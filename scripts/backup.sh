#!/usr/bin/env bash
# =============================================
# namgun-workspace — Backup Script
# =============================================
# Usage: sudo bash scripts/backup.sh [backup-dir]
#
# Backs up:
#   - PostgreSQL (pg_dump + gzip)
#   - Redis (BGSAVE + RDB copy)
#   - Mail data (tar, if mailserver running)
#
# Retention: deletes backups older than 30 days
# =============================================

set -euo pipefail

# ─── Colors ───
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

# ─── Configuration ───
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TARGET_DIR="${BACKUP_DIR}/${TIMESTAMP}"
RETENTION_DAYS=30

POSTGRES_CONTAINER="ws-postgres"
REDIS_CONTAINER="ws-redis"
MAIL_CONTAINER="ws-mailserver"

DB_USER="${DB_USER:-workspace}"
DB_NAME="${DB_NAME:-workspace}"

# ─── Pre-flight checks ───
echo ""
echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo -e "${BOLD}  namgun-workspace — Backup${NC}"
echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo ""
info "Timestamp: ${TIMESTAMP}"
info "Backup directory: ${TARGET_DIR}"

if ! command -v docker &>/dev/null; then
    err "Docker is not installed or not in PATH."
    exit 1
fi

# ─── Create backup directory ───
mkdir -p "${TARGET_DIR}"
ok "Backup directory created: ${TARGET_DIR}"

ERRORS=0

# ─── 1. PostgreSQL Backup ───
echo ""
info "─── PostgreSQL Backup ───"
if docker inspect "${POSTGRES_CONTAINER}" --format '{{.State.Running}}' 2>/dev/null | grep -q true; then
    PG_DUMP_FILE="${TARGET_DIR}/postgres_${TIMESTAMP}.sql.gz"
    info "Dumping database '${DB_NAME}' from ${POSTGRES_CONTAINER}..."
    if docker exec "${POSTGRES_CONTAINER}" pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${PG_DUMP_FILE}"; then
        PG_SIZE=$(du -h "${PG_DUMP_FILE}" | cut -f1)
        ok "PostgreSQL dump complete: ${PG_DUMP_FILE} (${PG_SIZE})"
    else
        err "PostgreSQL dump failed!"
        rm -f "${PG_DUMP_FILE}"
        ERRORS=$((ERRORS + 1))
    fi
else
    warn "Container '${POSTGRES_CONTAINER}' is not running — skipping PostgreSQL backup."
    ERRORS=$((ERRORS + 1))
fi

# ─── 2. Redis Backup ───
echo ""
info "─── Redis Backup ───"
if docker inspect "${REDIS_CONTAINER}" --format '{{.State.Running}}' 2>/dev/null | grep -q true; then
    REDIS_FILE="${TARGET_DIR}/redis_${TIMESTAMP}.rdb"
    info "Triggering BGSAVE on ${REDIS_CONTAINER}..."
    docker exec "${REDIS_CONTAINER}" redis-cli BGSAVE >/dev/null 2>&1

    # Wait for BGSAVE to complete (up to 30s)
    WAIT=0
    MAX_WAIT=30
    while [[ $WAIT -lt $MAX_WAIT ]]; do
        LAST_SAVE_STATUS=$(docker exec "${REDIS_CONTAINER}" redis-cli LASTSAVE 2>/dev/null || echo "")
        BG_STATUS=$(docker exec "${REDIS_CONTAINER}" redis-cli INFO persistence 2>/dev/null | grep "rdb_bgsave_in_progress:0" || true)
        if [[ -n "$BG_STATUS" ]]; then
            break
        fi
        sleep 1
        WAIT=$((WAIT + 1))
    done

    if [[ $WAIT -ge $MAX_WAIT ]]; then
        warn "BGSAVE may not have completed within ${MAX_WAIT}s — copying RDB anyway."
    fi

    # Copy the RDB file out of the container
    if docker cp "${REDIS_CONTAINER}:/data/dump.rdb" "${REDIS_FILE}" 2>/dev/null; then
        REDIS_SIZE=$(du -h "${REDIS_FILE}" | cut -f1)
        ok "Redis RDB backup complete: ${REDIS_FILE} (${REDIS_SIZE})"
    else
        err "Redis RDB copy failed! (dump.rdb may not exist if no data)"
        rm -f "${REDIS_FILE}"
        ERRORS=$((ERRORS + 1))
    fi
else
    warn "Container '${REDIS_CONTAINER}' is not running — skipping Redis backup."
    ERRORS=$((ERRORS + 1))
fi

# ─── 3. Mail Data Backup ───
echo ""
info "─── Mail Data Backup ───"
if docker inspect "${MAIL_CONTAINER}" --format '{{.State.Running}}' 2>/dev/null | grep -q true; then
    MAIL_FILE="${TARGET_DIR}/mail_${TIMESTAMP}.tar.gz"
    info "Archiving /var/mail from ${MAIL_CONTAINER}..."
    if docker exec "${MAIL_CONTAINER}" tar czf - /var/mail > "${MAIL_FILE}" 2>/dev/null; then
        MAIL_SIZE=$(du -h "${MAIL_FILE}" | cut -f1)
        # Check if the tar is non-trivially sized (not empty)
        MAIL_BYTES=$(stat --printf="%s" "${MAIL_FILE}" 2>/dev/null || echo "0")
        if [[ "${MAIL_BYTES}" -le 50 ]]; then
            warn "Mail archive appears empty (${MAIL_BYTES} bytes) — no mail data?"
            rm -f "${MAIL_FILE}"
        else
            ok "Mail data backup complete: ${MAIL_FILE} (${MAIL_SIZE})"
        fi
    else
        err "Mail data backup failed!"
        rm -f "${MAIL_FILE}"
        ERRORS=$((ERRORS + 1))
    fi
else
    warn "Container '${MAIL_CONTAINER}' is not running — skipping mail backup."
fi

# ─── 4. Retention Policy ───
echo ""
info "─── Retention Policy ───"
info "Removing backups older than ${RETENTION_DAYS} days from ${BACKUP_DIR}..."

OLD_COUNT=0
if [[ -d "${BACKUP_DIR}" ]]; then
    while IFS= read -r -d '' old_dir; do
        rm -rf "${old_dir}"
        OLD_COUNT=$((OLD_COUNT + 1))
        info "Deleted: ${old_dir}"
    done < <(find "${BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime +"${RETENTION_DAYS}" -print0 2>/dev/null)
fi

if [[ $OLD_COUNT -gt 0 ]]; then
    ok "Removed ${OLD_COUNT} old backup(s)."
else
    ok "No backups older than ${RETENTION_DAYS} days found."
fi

# ─── 5. Backup Summary ───
echo ""
echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo -e "${BOLD}  Backup Summary${NC}"
echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo ""
echo -e "  Timestamp:  ${CYAN}${TIMESTAMP}${NC}"
echo -e "  Directory:  ${CYAN}${TARGET_DIR}${NC}"
echo ""

if [[ -d "${TARGET_DIR}" ]]; then
    echo -e "  ${BOLD}Files:${NC}"
    TOTAL_SIZE=0
    while IFS= read -r file; do
        FILE_SIZE=$(du -h "${file}" | cut -f1)
        FILE_NAME=$(basename "${file}")
        echo -e "    ${GREEN}${FILE_NAME}${NC}  ${FILE_SIZE}"
    done < <(find "${TARGET_DIR}" -type f -print | sort)

    DIR_SIZE=$(du -sh "${TARGET_DIR}" | cut -f1)
    echo ""
    echo -e "  Total size: ${BOLD}${DIR_SIZE}${NC}"
fi

echo ""
if [[ $ERRORS -gt 0 ]]; then
    warn "${ERRORS} backup task(s) had errors. Check messages above."
    exit 1
else
    ok "All backups completed successfully."
    exit 0
fi
