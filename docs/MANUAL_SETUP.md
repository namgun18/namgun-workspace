# 수동 설정 체크리스트

`docker compose up` 전후로 수동으로 해야 할 작업 목록입니다.

---

## 1. 사전 준비 (docker compose up 전)

### 1-1. DNS 레코드 등록

도메인 DNS에 아래 레코드를 추가합니다. `your-domain.com`을 실제 도메인으로 교체하세요.

| 타입 | 이름 | 값 | 비고 |
|------|------|-----|------|
| A | `your-domain.com` | `공인 IP` | 포털 웹 (필수) |
| A | `mail.your-domain.com` | `공인 IP` | 메일 서버 (필수) |
| MX | `your-domain.com` | `mail.your-domain.com` (우선순위 10) | 수신 메일 (필수) |
| TXT | `your-domain.com` | `v=spf1 ip4:공인IP ~all` | SPF (필수) |
| TXT | `_dmarc.your-domain.com` | `v=DMARC1; p=quarantine; rua=mailto:postmaster@your-domain.com` | DMARC (권장) |
| CNAME | `default._domainkey.your-domain.com` | (Stalwart에서 DKIM 키 생성 후 등록) | DKIM (권장) |

**PTR 레코드**: ISP에 요청하여 공인 IP → `mail.your-domain.com` 역방향 DNS 설정 (메일 전송률 향상)

### 1-2. 방화벽/NAT 정책

서버 방화벽 또는 공유기/라우터에서 아래 포트를 개방합니다.

| 포트 | 프로토콜 | 용도 | 필수 여부 |
|------|----------|------|-----------|
| **80** | TCP | HTTP (ACME challenge, 리다이렉트) | 필수 |
| **443** | TCP | HTTPS (포털 웹) | 필수 |
| **25** | TCP | SMTP (메일 수신) | 메일 사용 시 필수 |
| **587** | TCP | SMTP Submission (메일 발송) | 메일 사용 시 필수 |
| **993** | TCP | IMAPS (외부 메일 클라이언트) | 메일 클라이언트 사용 시 |
| **2222** | TCP | Git SSH (기본값, GIT_SSH_PORT 변경 가능) | Git SSH 사용 시 |
| **7882** | UDP | LiveKit WebRTC (미디어) | 화상회의 사용 시 |

**주의**: 포트 25는 많은 ISP/클라우드에서 기본 차단됩니다. ISP에 25번 포트 개방을 요청하거나, 릴레이 서버를 구성해야 합니다.

### 1-3. `.env` 파일 생성

```bash
cp .env.example .env
# .env 파일을 열어 모든 CHANGE_ME 값을 실제 비밀번호로 교체
```

**필수 변경 항목**:
- `SECRET_KEY`: 랜덤 문자열 (예: `openssl rand -hex 32`)
- `DB_PASSWORD`: PostgreSQL 비밀번호
- `DATABASE_URL`: DB_PASSWORD와 동일하게 맞춤
- `STALWART_ADMIN_PASSWORD`: Stalwart 관리자 비밀번호
- `DOMAIN`: 실제 도메인
- `APP_URL`: `https://your-domain.com`
- SMTP 관련: 도메인에 맞게 수정

---

## 2. 첫 기동 후 수동 작업

### 2-1. Gitea 초기 설정

첫 기동 시 `http://your-domain.com/git/` 접속하면 Gitea 설치 마법사가 표시됩니다.

1. **Database**: PostgreSQL, Host=`postgres:5432`, DB=`gitea`, User=`workspace` (이미 docker-compose에서 설정됨)
2. **Site Title**: 원하는 이름
3. **Server Domain**: `your-domain.com`
4. **SSH Server Domain**: `your-domain.com`
5. **SSH Server Port**: `2222` (GIT_SSH_PORT와 동일)
6. **Gitea Base URL**: `https://your-domain.com/git/`
7. **관리자 계정 생성**: workspace 포털과 동일한 관리자 계정 권장

### 2-2. Gitea OAuth 연동 (포털 SSO)

Gitea 관리자로 로그인 → 사이트 관리 → Authentication Sources:

1. **Add Authentication Source** → OAuth2
2. Provider: `OpenID Connect`
3. Authentication Name: `workspace`
4. Client ID / Secret: 포털 `.env`의 `OAUTH_CLIENTS_JSON`에 등록한 값과 일치
5. OpenID Connect Auto Discovery URL: `https://your-domain.com/oauth/.well-known/openid-configuration`

### 2-3. Stalwart DKIM 설정

Stalwart 웹 관리콘솔(`http://stalwart:8080` 또는 포트 매핑된 주소)에 접속:

1. **Domain 추가**: `your-domain.com`
2. **DKIM 키 생성**: 도메인 설정에서 자동 생성
3. DNS에 DKIM TXT 레코드 등록 (1-1에서 예약한 `default._domainkey`)

### 2-4. TLS 인증서 (Phase 4 이전 임시 방법)

현재 nginx는 HTTP(80)만 리슨합니다. HTTPS가 필요한 경우:

**옵션 A**: 외부 리버스 프록시 (이미 nginx/traefik이 있는 경우)
```
# .env에 추가
NGINX_PROFILE=external
```
→ 내장 nginx 비활성화, backend(8000)/frontend(3000)만 expose

**옵션 B**: certbot 수동 실행
```bash
docker run --rm -v ws-certbot-data:/etc/letsencrypt -v ws-certbot-webroot:/var/www/certbot \
  certbot/certbot certonly --webroot -w /var/www/certbot -d your-domain.com
```
이후 nginx.conf에 SSL 블록 추가 (Phase 4에서 자동화 예정)

### 2-5. 관리자 계정 생성

포털에서 첫 가입 후 PostgreSQL에서 수동으로 관리자 권한 부여:

```bash
docker exec -it ws-postgres psql -U workspace -d workspace -c \
  "UPDATE users SET is_admin = true, is_active = true WHERE username = 'your-admin-username';"
```

---

## 3. 운영 중 체크리스트

### 3-1. 백업

| 대상 | 방법 | 주기 |
|------|------|------|
| PostgreSQL | `docker exec ws-postgres pg_dump -U workspace workspace > backup.sql` | 일 1회 |
| Stalwart 데이터 | `docker cp ws-stalwart:/opt/stalwart-mail ./stalwart-backup/` | 주 1회 |
| Gitea 데이터 | `docker exec ws-gitea gitea dump` | 주 1회 |
| 파일 스토리지 | `docker cp ws-backend:/storage ./storage-backup/` | 필요 시 |

### 3-2. 업데이트

```bash
git pull
docker compose build
docker compose up -d
```

### 3-3. 로그 확인

```bash
docker compose logs -f backend   # FastAPI 로그
docker compose logs -f stalwart  # 메일 서버 로그
docker compose logs -f gitea     # Gitea 로그
docker compose logs -f nginx     # 프록시 로그
```

---

## 4. 네트워크 참고 (NAT 환경)

### 공유기/라우터 뒤 서버인 경우

공유기 관리 페이지에서 **포트 포워딩** 규칙 추가:

```
외부 포트 80   → 서버 내부 IP:80   (TCP)
외부 포트 443  → 서버 내부 IP:443  (TCP)
외부 포트 25   → 서버 내부 IP:25   (TCP)
외부 포트 587  → 서버 내부 IP:587  (TCP)
외부 포트 993  → 서버 내부 IP:993  (TCP)
외부 포트 2222 → 서버 내부 IP:2222 (TCP)
외부 포트 7882 → 서버 내부 IP:7882 (UDP)
```

### 클라우드 환경 (AWS/GCP/Azure)

Security Group / 방화벽 규칙에 위 포트들을 인바운드 허용으로 추가.

### Hyper-V / WSL2 환경

WSL2는 NAT 모드로 동작하므로 호스트에서 추가 포트 포워딩이 필요할 수 있습니다:

```powershell
# Windows PowerShell (관리자)
netsh interface portproxy add v4tov4 listenport=80 listenaddress=0.0.0.0 connectport=80 connectaddress=$(wsl hostname -I | ForEach-Object { $_.Trim() })
netsh interface portproxy add v4tov4 listenport=443 listenaddress=0.0.0.0 connectport=443 connectaddress=$(wsl hostname -I | ForEach-Object { $_.Trim() })
netsh interface portproxy add v4tov4 listenport=25 listenaddress=0.0.0.0 connectport=25 connectaddress=$(wsl hostname -I | ForEach-Object { $_.Trim() })
# ... 나머지 포트도 동일
```

### firewalld (Rocky Linux / CentOS)

```bash
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --permanent --add-port=25/tcp
firewall-cmd --permanent --add-port=587/tcp
firewall-cmd --permanent --add-port=993/tcp
firewall-cmd --permanent --add-port=2222/tcp
firewall-cmd --permanent --add-port=7882/udp
firewall-cmd --reload
```
