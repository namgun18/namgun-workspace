#!/usr/bin/env bash
# =============================================
# namgun-workspace — Interactive Setup Script
# =============================================
# Supported OS: Ubuntu 22.04/24.04, Debian 12
# Usage: sudo bash setup.sh
# =============================================

set -euo pipefail

# ─── Colors ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ─── 1. Pre-flight checks ───
if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (sudo bash setup.sh)"
    exit 1
fi

# Detect OS
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS_ID="${ID:-unknown}"
    OS_VERSION="${VERSION_ID:-unknown}"
else
    err "Cannot detect OS. /etc/os-release not found."
    exit 1
fi

case "$OS_ID" in
    ubuntu|debian)
        ok "Detected: $PRETTY_NAME"
        ;;
    *)
        warn "Unsupported OS: $OS_ID $OS_VERSION"
        warn "This script is designed for Ubuntu 22.04/24.04 or Debian 12."
        read -rp "Continue anyway? (y/N): " CONTINUE
        [[ "$CONTINUE" =~ ^[Yy]$ ]] || exit 1
        ;;
esac

ARCH=$(uname -m)
info "Architecture: $ARCH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
info "Working directory: $SCRIPT_DIR"

# ─── 2. Docker + Compose V2 ───
install_docker() {
    info "Installing Docker..."
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg lsb-release >/dev/null

    install -m 0755 -d /etc/apt/keyrings
    if [[ "$OS_ID" == "ubuntu" ]]; then
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
            | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
            https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
            > /etc/apt/sources.list.d/docker.list
    else
        curl -fsSL https://download.docker.com/linux/debian/gpg \
            | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
            https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
            > /etc/apt/sources.list.d/docker.list
    fi

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin >/dev/null
    systemctl enable --now docker
    ok "Docker installed"
}

if command -v docker &>/dev/null; then
    ok "Docker already installed: $(docker --version)"
else
    install_docker
fi

if docker compose version &>/dev/null; then
    ok "Docker Compose V2: $(docker compose version --short)"
else
    err "Docker Compose V2 not found. Please install docker-compose-plugin."
    exit 1
fi

# ─── 3. .env handling ───
ENV_FILE="$SCRIPT_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
    warn ".env file already exists."
    read -rp "Overwrite? (y/N): " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
        info "Keeping existing .env — skipping configuration."
        SKIP_ENV=true
    else
        SKIP_ENV=false
    fi
else
    SKIP_ENV=false
fi

# ─── 4. Interactive input ───
if [[ "$SKIP_ENV" == "false" ]]; then
    echo ""
    echo -e "${BOLD}═══════════════════════════════════════${NC}"
    echo -e "${BOLD}  namgun-workspace — Initial Setup${NC}"
    echo -e "${BOLD}═══════════════════════════════════════${NC}"
    echo ""

    # Domain
    read -rp "Domain (e.g. workspace.example.com): " DOMAIN
    DOMAIN="${DOMAIN:-localhost}"

    # Admin
    read -rp "Admin username: " ADMIN_USERNAME
    ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"

    while true; do
        read -rsp "Admin password: " ADMIN_PASSWORD
        echo ""
        if [[ ${#ADMIN_PASSWORD} -lt 8 ]]; then
            warn "Password must be at least 8 characters."
            continue
        fi
        read -rsp "Confirm password: " ADMIN_PASSWORD_CONFIRM
        echo ""
        if [[ "$ADMIN_PASSWORD" != "$ADMIN_PASSWORD_CONFIRM" ]]; then
            warn "Passwords do not match. Try again."
            continue
        fi
        break
    done

    read -rp "Admin display name [${ADMIN_USERNAME}]: " ADMIN_DISPLAY_NAME
    ADMIN_DISPLAY_NAME="${ADMIN_DISPLAY_NAME:-$ADMIN_USERNAME}"

    # Profiles
    echo ""
    echo -e "${BOLD}Select optional profiles (space-separated numbers):${NC}"
    echo "  1) mailserver  — Self-hosted mail (Postfix+Dovecot+Rspamd)"
    echo "  2) gitea       — Git hosting (Gitea)"
    echo "  3) livekit     — Video conferencing (LiveKit)"
    echo "  4) nginx       — Built-in TLS reverse proxy"
    echo "  5) certbot     — Let's Encrypt auto-certificate"
    echo ""
    read -rp "Profiles (e.g. 1 2 3 4 5): " PROFILE_INPUT

    PROFILES=()
    for n in $PROFILE_INPUT; do
        case "$n" in
            1) PROFILES+=("mailserver") ;;
            2) PROFILES+=("gitea") ;;
            3) PROFILES+=("livekit") ;;
            4) PROFILES+=("nginx") ;;
            5) PROFILES+=("certbot") ;;
            *) warn "Unknown profile number: $n" ;;
        esac
    done
    COMPOSE_PROFILES=$(IFS=,; echo "${PROFILES[*]}")

    # ─── 5. Generate secrets ───
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)
    LIVEKIT_KEY="WS$(openssl rand -hex 6)"
    LIVEKIT_SECRET=$(openssl rand -base64 32 | tr -d '=+/')

    # App URL
    if [[ " ${PROFILES[*]} " =~ " nginx " ]] || [[ " ${PROFILES[*]} " =~ " certbot " ]]; then
        APP_URL="https://${DOMAIN}"
    else
        APP_URL="http://${DOMAIN}"
    fi

    # ─── 6. Write .env ───
    info "Generating .env..."
    cat > "$ENV_FILE" <<ENVEOF
# =============================================
# namgun-workspace — Generated by setup.sh
# Generated: $(date -Iseconds)
# =============================================

# ─── Service Profiles ───
COMPOSE_PROFILES=${COMPOSE_PROFILES}

# ─── Ports ───
BACKEND_PORT=8000
FRONTEND_PORT=3000

# ─── Storage ───
STORAGE_VOLUME=ws-storage-data

# ─── App ───
APP_NAME=Workspace
APP_URL=${APP_URL}
DOMAIN=${DOMAIN}
DEBUG=false
SECRET_KEY=${SECRET_KEY}

# ─── PostgreSQL ───
DB_USER=workspace
DB_PASSWORD=${DB_PASSWORD}
DATABASE_URL=postgresql+asyncpg://workspace:${DB_PASSWORD}@postgres:5432/workspace

# ─── Mail Server ───
FEATURE_BUILTIN_MAILSERVER=false
DOVECOT_MASTER_USER=portal
DOVECOT_MASTER_PASSWORD=$(openssl rand -hex 12)
STALWART_URL=http://stalwart:8080
STALWART_ADMIN_USER=admin
STALWART_ADMIN_PASSWORD=$(openssl rand -hex 12)

# ─── SMTP (noreply) ───
SMTP_HOST=mailserver
SMTP_PORT=587
SMTP_USER=noreply@${DOMAIN}
SMTP_PASSWORD=$(openssl rand -hex 12)
SMTP_FROM=noreply@${DOMAIN}

# ─── Admin ───
ADMIN_EMAILS=${ADMIN_USERNAME}@${DOMAIN}
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# ─── Gitea ───
GITEA_URL=http://gitea:3000
GITEA_TOKEN=

# ─── OAuth ───
OAUTH_CLIENTS_JSON={}

# ─── LiveKit ───
LIVEKIT_API_KEY=${LIVEKIT_KEY}
LIVEKIT_API_SECRET=${LIVEKIT_SECRET}
LIVEKIT_URL=http://livekit:7880

# ─── Git SSH ───
GIT_SSH_PORT=2222

# ─── Let's Encrypt ───
LETSENCRYPT_EMAIL=${ADMIN_USERNAME}@${DOMAIN}
ENVEOF

    chmod 600 "$ENV_FILE"
    ok ".env created (secrets auto-generated)"

    # Enable mailserver profile flag if selected
    if [[ " ${PROFILES[*]} " =~ " mailserver " ]]; then
        sed -i 's/^FEATURE_BUILTIN_MAILSERVER=false/FEATURE_BUILTIN_MAILSERVER=true/' "$ENV_FILE"
    fi
fi

# ─── 7. DKIM (if mailserver profile) ───
if [[ -f "$ENV_FILE" ]]; then
    source "$ENV_FILE"
fi

if [[ "${COMPOSE_PROFILES:-}" == *"mailserver"* ]]; then
    info "Mailserver profile detected — generating DKIM keys..."
    if [[ -x "$SCRIPT_DIR/scripts/generate-dkim.sh" ]]; then
        bash "$SCRIPT_DIR/scripts/generate-dkim.sh" "${DOMAIN:-localhost}"
    else
        warn "scripts/generate-dkim.sh not found or not executable — skipping DKIM"
    fi
fi

# ─── 7½. LiveKit config (if livekit profile) ───
if [[ "${COMPOSE_PROFILES:-}" == *"livekit"* ]]; then
    LIVEKIT_YAML="$SCRIPT_DIR/livekit/livekit.yaml"
    LK_KEY="${LIVEKIT_API_KEY:-devkey}"
    LK_SECRET="${LIVEKIT_API_SECRET:-secret}"

    # Detect public IP for WebRTC
    PUBLIC_IP=$(curl -sf --max-time 5 https://api.ipify.org 2>/dev/null || echo "")

    info "Generating livekit/livekit.yaml..."
    mkdir -p "$SCRIPT_DIR/livekit"

    if [[ -n "$PUBLIC_IP" ]]; then
        USE_EXT_IP="true"
        NODE_IP_LINE="  node_ip: $PUBLIC_IP"
    else
        USE_EXT_IP="false"
        NODE_IP_LINE=""
    fi

    cat > "$LIVEKIT_YAML" <<LKEOF
port: 7880
rtc:
  port_range_start: 7882
  port_range_end: 7882
  use_external_ip: ${USE_EXT_IP}
${NODE_IP_LINE}
  tcp_port: 7881
keys:
  ${LK_KEY}: ${LK_SECRET}
room:
  enabled_codecs:
    - mime: video/vp9
    - mime: video/h264
    - mime: video/vp8
    - mime: audio/opus
    - mime: audio/red
LKEOF
    ok "LiveKit config created (API key: $LK_KEY)"
fi

# ─── 7¾. Gitea initial setup ───
if [[ "${COMPOSE_PROFILES:-}" == *"gitea"* ]]; then
    info "Gitea will be available at ${APP_URL:-http://localhost}/git/"
fi

# ─── 8. Create storage volume (external) and build ───
STORAGE_VOL="${STORAGE_VOLUME:-ws-storage-data}"
if docker volume inspect "$STORAGE_VOL" >/dev/null 2>&1; then
    ok "Storage volume '$STORAGE_VOL' already exists"
else
    docker volume create "$STORAGE_VOL"
    ok "Storage volume '$STORAGE_VOL' created"
fi

echo ""
info "Building and starting containers..."
docker compose up -d --build

# ─── 9. Health check ───
info "Waiting for backend health check..."
HEALTH_URL="http://localhost:${BACKEND_PORT:-8000}/api/health"
MAX_WAIT=120
ELAPSED=0

while [[ $ELAPSED -lt $MAX_WAIT ]]; do
    if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
        ok "Backend is healthy!"
        break
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    printf "\r  Waiting... %ds / %ds" "$ELAPSED" "$MAX_WAIT"
done
echo ""

if [[ $ELAPSED -ge $MAX_WAIT ]]; then
    warn "Backend health check timed out after ${MAX_WAIT}s"
    warn "Check logs: docker compose logs backend"
fi

# ─── 10. Seed admin ───
ADMIN_USER_VAR="${ADMIN_USERNAME:-}"
ADMIN_PASS_VAR="${ADMIN_PASSWORD:-}"

if [[ -n "$ADMIN_USER_VAR" && -n "$ADMIN_PASS_VAR" ]]; then
    info "Seeding admin account..."
    docker exec ws-backend python -m app.cli seed-admin \
        --username "$ADMIN_USER_VAR" \
        --password "$ADMIN_PASS_VAR" || warn "Admin seed failed — check backend logs"
fi

# ─── 10½. Mailserver noreply account ───
if [[ "${COMPOSE_PROFILES:-}" == *"mailserver"* ]]; then
    info "Creating noreply mail account..."
    SMTP_PW="${SMTP_PASSWORD:-$(openssl rand -hex 12)}"
    docker exec ws-mailserver setup email add "noreply@${DOMAIN:-localhost}" "$SMTP_PW" 2>/dev/null \
        && ok "noreply@${DOMAIN:-localhost} created" \
        || warn "noreply account creation failed (mailserver may still be starting)"
fi

# ─── 11. Done ───
echo ""
echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Setup Complete!${NC}"
echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo ""
echo -e "  URL:   ${CYAN}${APP_URL:-http://localhost}${NC}"
echo -e "  Admin: ${CYAN}${ADMIN_USER_VAR:-admin}${NC}"
echo ""

if [[ "${COMPOSE_PROFILES:-}" == *"nginx"* ]]; then
    echo -e "${YELLOW}DNS Setup:${NC}"
    echo "  Point ${DOMAIN:-your-domain} → this server's IP"
    echo ""
fi

if [[ "${COMPOSE_PROFILES:-}" == *"mailserver"* ]]; then
    echo -e "${YELLOW}Mail DNS:${NC}"
    echo "  See DNS records printed above (MX, SPF, DKIM, DMARC)"
    echo "  Set PTR record for your IP → mail.${DOMAIN:-your-domain}"
    echo ""
fi

echo -e "${YELLOW}Security:${NC}"
echo "  After first login, remove ADMIN_PASSWORD from .env:"
echo "    sed -i 's/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=/' .env"
echo ""
echo "  View logs:  docker compose logs -f"
echo "  Stop:       docker compose down"
echo "  Update:     git pull && docker compose up -d --build"
echo ""
