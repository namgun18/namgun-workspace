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
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ─── 1. Pre-flight checks ───
if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (sudo bash setup.sh)"
    exit 1
fi

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

# ─── Helper: generate nginx.conf ───
generate_nginx_locations() {
    cat <<'LOCATIONS'
    # ─── ACME challenge (certbot) ───
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # ─── 파일 업로드 (대용량) ───
    location /api/files/upload {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 5G;
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }

    # ─── OAuth Provider → FastAPI ───
    location /oauth/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
        proxy_connect_timeout 10s;
    }

    # ─── WebSocket 프록시 → FastAPI ───
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ─── API 프록시 → FastAPI ───
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }

    # ─── Gitea 프록시 ───
    location /git/ {
        proxy_pass http://gitea:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        client_max_body_size 100M;
    }

    # ─── LiveKit WebSocket 프록시 ───
    location /livekit/ {
        proxy_pass http://livekit:7880/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # ─── Nuxt 정적 에셋 (content-hash 파일명 → 장기 캐시) ───
    location /_nuxt/ {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        add_header Cache-Control "public, max-age=31536000, immutable" always;
    }

    # ─── SSR 프록시 → Nuxt 3 (HTML은 캐시하지 않음) ───
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header Pragma "no-cache" always;
    }
LOCATIONS
}

generate_nginx_conf() {
    local mode="$1"
    local domain="$2"
    local nginx_conf="$SCRIPT_DIR/nginx/nginx.conf"

    mkdir -p "$SCRIPT_DIR/nginx"

    case "$mode" in
        standalone)
            # HTTP (ACME + redirect) + HTTPS (SSL + proxy)
            cat > "$nginx_conf" <<NGINX_STANDALONE_HEADER
# namgun-workspace — Nginx reverse proxy (standalone mode)

map \$http_upgrade \$connection_upgrade {
    default upgrade;
    ''      close;
}

# ─── Gzip 압축 ───
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_min_length 1024;
gzip_comp_level 5;
gzip_types text/plain text/css text/javascript application/json application/javascript application/xml application/xml+rss image/svg+xml;

# ─── HTTP: ACME challenge + redirect to HTTPS ───
server {
    listen 80 default_server;
    server_name ${domain};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

# ─── HTTPS: SSL + proxy ───
server {
    listen 443 ssl default_server;
    server_name ${domain};

    ssl_certificate     /etc/letsencrypt/live/${domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${domain}/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # ─── 보안 헤더 ───
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(self), geolocation=()" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

NGINX_STANDALONE_HEADER
            generate_nginx_locations >> "$nginx_conf"
            echo "}" >> "$nginx_conf"
            ;;
        external_proxy|dev|*)
            # HTTP-only single server block
            cat > "$nginx_conf" <<NGINX_HTTP_HEADER
# namgun-workspace — Nginx reverse proxy (${mode} mode)

map \$http_upgrade \$connection_upgrade {
    default upgrade;
    ''      close;
}

# ─── Gzip 압축 ───
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_min_length 1024;
gzip_comp_level 5;
gzip_types text/plain text/css text/javascript application/json application/javascript application/xml application/xml+rss image/svg+xml;

# ─── Workspace (HTTP-only) ───
server {
    listen 80 default_server;
    server_name _;

    # ─── 보안 헤더 ───
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(self), geolocation=()" always;

NGINX_HTTP_HEADER
            generate_nginx_locations >> "$nginx_conf"
            echo "}" >> "$nginx_conf"
            ;;
    esac

    ok "nginx/nginx.conf generated (mode: $mode)"
}

# ─── Helper: manage docker-compose.override.yml ───
manage_override_yml() {
    local mode="$1"
    local override_file="$SCRIPT_DIR/docker-compose.override.yml"

    if [[ "$mode" == "standalone" ]]; then
        cat > "$override_file" <<'OVERRIDE'
# Auto-generated by setup.sh (standalone mode)
# Adds :443 to nginx for direct TLS termination
services:
  nginx:
    ports:
      - "443:443"
OVERRIDE
        ok "docker-compose.override.yml created (standalone: :443)"
    else
        if [[ -f "$override_file" ]]; then
            rm -f "$override_file"
            warn "Removed stale docker-compose.override.yml (not needed for ${mode} mode)"
        fi
    fi
}

# ─── 4. Interactive input ───
if [[ "$SKIP_ENV" == "false" ]]; then
    echo ""
    echo -e "${BOLD}═══════════════════════════════════════${NC}"
    echo -e "${BOLD}  Workspace — Initial Setup${NC}"
    echo -e "${BOLD}═══════════════════════════════════════${NC}"
    echo ""

    # App Name
    read -rp "App name [Workspace]: " APP_NAME
    APP_NAME="${APP_NAME:-Workspace}"

    # Domain
    read -rp "Domain or IP (e.g. workspace.example.com or 192.168.1.100): " DOMAIN
    DOMAIN="${DOMAIN:-localhost}"

    # Detect domain type
    IS_IP=false
    IS_LOCALHOST=false
    if [[ "$DOMAIN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        IS_IP=true
    fi
    if [[ "$DOMAIN" == "localhost" || "$DOMAIN" == "127.0.0.1" ]]; then
        IS_LOCALHOST=true
    fi

    # Deploy Mode
    echo ""
    echo -e "${BOLD}Select deploy mode:${NC}"
    echo "  A) External Proxy — HTTP :80, SSL handled by external nginx/caddy"
    echo "  B) Standalone     — HTTPS :80+:443, Let's Encrypt auto-certificate"
    echo "  C) Development    — HTTP :80, no SSL"
    echo ""

    if [[ "$IS_IP" == "true" || "$IS_LOCALHOST" == "true" ]]; then
        warn "IP address or localhost detected — forcing Development mode."
        DEPLOY_MODE="dev"
    else
        read -rp "Deploy mode (A/B/C) [A]: " MODE_INPUT
        MODE_INPUT="${MODE_INPUT:-A}"
        case "$MODE_INPUT" in
            [Aa]) DEPLOY_MODE="external_proxy" ;;
            [Bb])
                DEPLOY_MODE="standalone"
                # DNS resolution check (warning only)
                if ! host "$DOMAIN" >/dev/null 2>&1; then
                    warn "DNS for '$DOMAIN' could not be resolved."
                    warn "Standalone mode requires DNS to point to this server for Let's Encrypt."
                    warn "Continuing anyway — make sure DNS is configured before certbot runs."
                fi
                ;;
            [Cc]) DEPLOY_MODE="dev" ;;
            *)
                warn "Invalid choice '$MODE_INPUT', defaulting to External Proxy."
                DEPLOY_MODE="external_proxy"
                ;;
        esac
    fi

    ok "Deploy mode: $DEPLOY_MODE"

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
    if [[ "$DEPLOY_MODE" == "external_proxy" ]]; then
        echo "  4) certbot     — Let's Encrypt certificate (for mail TLS)"
    fi
    echo ""
    read -rp "Profiles (e.g. 1 2 3): " PROFILE_INPUT

    PROFILES=()
    for n in $PROFILE_INPUT; do
        case "$n" in
            1) PROFILES+=("mailserver") ;;
            2) PROFILES+=("gitea") ;;
            3) PROFILES+=("livekit") ;;
            4)
                if [[ "$DEPLOY_MODE" == "external_proxy" ]]; then
                    PROFILES+=("certbot")
                else
                    warn "certbot selection ignored — managed automatically in ${DEPLOY_MODE} mode."
                fi
                ;;
            *) warn "Unknown profile number: $n" ;;
        esac
    done

    # Standalone mode → certbot forced
    if [[ "$DEPLOY_MODE" == "standalone" ]]; then
        if [[ ! " ${PROFILES[*]} " =~ " certbot " ]]; then
            PROFILES+=("certbot")
            info "certbot auto-enabled for standalone mode."
        fi
    fi

    COMPOSE_PROFILES=$(IFS=,; echo "${PROFILES[*]}")

    # ─── 5. Generate secrets ───
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)
    LIVEKIT_KEY="WS$(openssl rand -hex 6)"
    LIVEKIT_SECRET=$(openssl rand -base64 32 | tr -d '=+/')
    DOVECOT_PW=$(openssl rand -hex 12)
    SMTP_PW=$(openssl rand -hex 12)

    # App URL
    if [[ "$DEPLOY_MODE" == "dev" ]]; then
        APP_URL="http://${DOMAIN}"
    else
        APP_URL="https://${DOMAIN}"
    fi

    # ─── 6. Write .env ───
    info "Generating .env..."
    cat > "$ENV_FILE" <<ENVEOF
# =============================================
# namgun-workspace — Generated by setup.sh
# Generated: $(date -Iseconds)
# =============================================

# ─── Deploy Mode ───
DEPLOY_MODE=${DEPLOY_MODE}

# ─── Service Profiles ───
COMPOSE_PROFILES=${COMPOSE_PROFILES}

# ─── Storage ───
STORAGE_VOLUME=ws-storage-data

# ─── App ───
APP_NAME=${APP_NAME}
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
DOVECOT_MASTER_PASSWORD=${DOVECOT_PW}

# ─── SMTP (noreply) ───
SMTP_HOST=mailserver
SMTP_PORT=587
SMTP_USER=noreply@${DOMAIN}
SMTP_PASSWORD=${SMTP_PW}
SMTP_FROM=noreply@${DOMAIN}

# ─── Admin ───
ADMIN_EMAILS=${ADMIN_USERNAME}@${DOMAIN}
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# ─── Gitea ───
GITEA_URL=http://gitea:3000
GITEA_EXTERNAL_URL=${APP_URL}/git/
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

        # Generate dovecot master user config
        mkdir -p "$SCRIPT_DIR/mailserver/config"
        echo "portal:{PLAIN}${DOVECOT_PW}" > "$SCRIPT_DIR/mailserver/config/dovecot-masters.cf"
        ok "Dovecot master user configured"
    fi

    # ─── 6½. Generate nginx.conf (mode-based) ───
    generate_nginx_conf "$DEPLOY_MODE" "$DOMAIN"

    # ─── 6¾. Manage docker-compose.override.yml ───
    manage_override_yml "$DEPLOY_MODE"
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

    cat > "$LIVEKIT_YAML" <<LKEOF
port: 7880
bind_addresses:
  - 0.0.0.0
rtc:
  port_range_start: 7882
  port_range_end: 7882
  use_external_ip: false
  node_ip: ${PUBLIC_IP:-0.0.0.0}
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

# ─── 8. Generate .env.example ───
info "Regenerating .env.example..."
cat > "$SCRIPT_DIR/.env.example" <<'EXAMPLEEOF'
# =============================================
# namgun-workspace — Environment Variables
# =============================================
# Copy to .env and fill in values:
#   cp .env.example .env
# Or use setup.sh for interactive configuration:
#   sudo bash setup.sh
# =============================================

# ─── Deploy Mode ───
# external_proxy — HTTP :80, SSL handled by external reverse proxy
# standalone     — HTTPS :80+:443, Let's Encrypt auto-certificate
# dev            — HTTP :80, no SSL
DEPLOY_MODE=external_proxy

# ─── 서비스 활성화 (쉼표 구분) ───
# 사용 가능: mailserver, gitea, livekit, certbot
# 풀스택 (standalone):  certbot,mailserver,gitea,livekit
# 풀스택 (ext. proxy):  mailserver,gitea,livekit
# 최소 (코어만):        (비워두기)
COMPOSE_PROFILES=mailserver,gitea,livekit

# ─── 스토리지 볼륨 ───
STORAGE_VOLUME=ws-storage-data

# ─── App ───
APP_NAME=Workspace
APP_URL=https://your-domain.com
DOMAIN=your-domain.com
DEBUG=false
SECRET_KEY=CHANGE_ME_TO_RANDOM_SECRET

# ─── PostgreSQL ───
DB_USER=workspace
DB_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD
DATABASE_URL=postgresql+asyncpg://workspace:CHANGE_ME_TO_STRONG_PASSWORD@postgres:5432/workspace

# ─── Mail Server ───
FEATURE_BUILTIN_MAILSERVER=false
DOVECOT_MASTER_USER=portal
DOVECOT_MASTER_PASSWORD=CHANGE_ME

# ─── SMTP (noreply sender) ───
SMTP_HOST=mailserver
SMTP_PORT=587
SMTP_USER=noreply@your-domain.com
SMTP_PASSWORD=CHANGE_ME
SMTP_FROM=noreply@your-domain.com

# ─── Admin ───
ADMIN_EMAILS=admin@your-domain.com

# ─── Gitea ───
GITEA_URL=http://gitea:3000
GITEA_EXTERNAL_URL=https://your-domain.com/git/
GITEA_TOKEN=

# ─── OAuth Provider (Gitea SSO) ───
OAUTH_CLIENTS_JSON={}

# ─── LiveKit ───
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
LIVEKIT_URL=http://livekit:7880

# ─── 초기 관리자 (setup.sh 자동 설정, 시드 완료 후 삭제 권장) ───
ADMIN_USERNAME=
ADMIN_PASSWORD=

# ─── Git SSH ───
GIT_SSH_PORT=2222

# ─── Let's Encrypt ───
LETSENCRYPT_EMAIL=admin@your-domain.com
EXAMPLEEOF
ok ".env.example regenerated"

# ─── 9. Create storage volume (external) and build ───
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

# ─── 10. Post-deploy verification chain ───

# Step 1: Container health check
echo ""
info "Step 1/5: Checking container status..."
FAILED_CONTAINERS=$(docker compose ps --format '{{.Name}} {{.Status}}' 2>/dev/null | grep -iv "up\|running" || true)
if [[ -n "$FAILED_CONTAINERS" ]]; then
    err "Some containers are not running:"
    echo "$FAILED_CONTAINERS"
    warn "Check logs: docker compose logs"
    warn "Continuing with health check anyway..."
else
    ok "All containers are running"
fi

# Step 2: Backend health check (via nginx :80)
info "Step 2/5: Waiting for backend health check (via nginx)..."
HEALTH_URL="http://localhost:80/api/health"
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
    warn "Check logs: docker compose logs backend nginx"
fi

# Step 3: Admin seed
info "Step 3/5: Seeding admin account..."
ADMIN_USER_VAR="${ADMIN_USERNAME:-}"
ADMIN_PASS_VAR="${ADMIN_PASSWORD:-}"

if [[ -n "$ADMIN_USER_VAR" && -n "$ADMIN_PASS_VAR" ]]; then
    docker exec ws-backend python -m app.cli seed-admin \
        --username "$ADMIN_USER_VAR" \
        --password "$ADMIN_PASS_VAR" \
        && ok "Admin account seeded" \
        || warn "Admin seed failed — you can retry manually: docker exec ws-backend python -m app.cli seed-admin"
else
    warn "ADMIN_USERNAME or ADMIN_PASSWORD not set — skipping admin seed"
fi

# Step 4: Mailserver noreply account (mailserver profile only)
if [[ "${COMPOSE_PROFILES:-}" == *"mailserver"* ]]; then
    info "Step 4/5: Creating noreply mail account..."
    NOREPLY_PW="${SMTP_PASSWORD:-$(openssl rand -hex 12)}"
    docker exec ws-mailserver setup email add "noreply@${DOMAIN:-localhost}" "$NOREPLY_PW" 2>/dev/null \
        && ok "noreply@${DOMAIN:-localhost} created" \
        || warn "noreply account creation failed (mailserver may still be starting)"
else
    info "Step 4/5: Skipped (mailserver profile not active)"
fi

# Step 5: SSL verification (standalone mode only)
if [[ "${DEPLOY_MODE:-}" == "standalone" ]]; then
    info "Step 5/5: Verifying SSL certificate..."
    sleep 5  # Give certbot a moment
    if curl -sf "https://${DOMAIN:-localhost}/" >/dev/null 2>&1; then
        ok "SSL is working! https://${DOMAIN} is accessible."
    else
        warn "SSL verification failed — certificate may not be issued yet."
        warn "Check certbot logs: docker compose logs certbot"
        warn "Ensure DNS for '${DOMAIN}' points to this server."
    fi
else
    info "Step 5/5: Skipped (SSL verification only for standalone mode)"
fi

# ─── 11. Done ───
echo ""
echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Setup Complete!${NC}"
echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo ""
echo -e "  Mode:  ${CYAN}${DEPLOY_MODE:-unknown}${NC}"
echo -e "  URL:   ${CYAN}${APP_URL:-http://localhost}${NC}"
echo -e "  Admin: ${CYAN}${ADMIN_USER_VAR:-admin}${NC}"
echo ""

if [[ "${DEPLOY_MODE:-}" == "standalone" ]]; then
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
