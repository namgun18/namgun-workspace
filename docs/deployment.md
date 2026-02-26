# Deployment Guide

## 요구사항

- Docker 24+ & Docker Compose v2
- 2+ CPU 코어, 4GB+ RAM
- 고정 공인 IP (메일 서버 사용 시)
- 도메인 1개

## 빠른 시작

```bash
git clone https://github.com/namgun/namgun-workspace.git
cd namgun-workspace
cp .env.example .env
# .env 편집
docker compose up -d
```

## 환경변수 (.env)

### 필수

| 변수 | 설명 | 예시 |
|------|------|------|
| `DB_PASSWORD` | PostgreSQL 비밀번호 | 32자 랜덤 |
| `SECRET_KEY` | JWT/세션 서명 키 | 64자 랜덤 |
| `DOMAIN` | 서비스 도메인 | `workspace.example.com` |
| `APP_URL` | 외부 접근 URL | `https://workspace.example.com` |

### 선택

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `COMPOSE_PROFILES` | 활성화할 프로필 | (코어만) |
| `FEATURE_BUILTIN_MAILSERVER` | 자체 메일서버 모드 | `false` |
| `SMTP_HOST` | 시스템 메일 발송 서버 | `localhost` |
| `SMTP_PORT` | SMTP 포트 | `587` |
| `SMTP_USER` | SMTP 인증 사용자 | |
| `SMTP_PASSWORD` | SMTP 인증 비밀번호 | |
| `SMTP_FROM` | 발신자 주소 | `noreply@localhost` |
| `GITEA_URL` | Gitea 내부 URL | `http://gitea:3000` |
| `GITEA_TOKEN` | Gitea API 토큰 | |
| `LIVEKIT_API_KEY` | LiveKit API 키 | |
| `LIVEKIT_API_SECRET` | LiveKit API 시크릿 | |
| `EXTERNAL_PROXY` | 외부 리버스 프록시 사용 | `false` |

## 프로필별 배포

### 최소 배포 (코어만)

```bash
# .env에 COMPOSE_PROFILES= (비워두기)
docker compose up -d
# → postgres, redis, backend, frontend
```

### 풀스택 (자체 메일서버 포함)

```bash
COMPOSE_PROFILES=nginx,mailserver,gitea,livekit
FEATURE_BUILTIN_MAILSERVER=true
```

### 외부 메일 연결 (클라우드 메일)

```bash
COMPOSE_PROFILES=nginx,gitea,livekit
# 사용자가 Gmail/Outlook IMAP/SMTP를 직접 설정
```

### 기존 리버스 프록시 뒤에서 운영

```bash
COMPOSE_PROFILES=gitea,livekit
# nginx 프로필 제외, 외부 nginx/Traefik에서 프록시
```

## DNS 설정 (자체 메일서버 사용 시)

| 레코드 | 타입 | 값 |
|--------|------|------|
| `example.com` | A | 서버 IP |
| `mail.example.com` | A | 서버 IP |
| `example.com` | MX | `mail.example.com` (우선순위 10) |
| `example.com` | TXT | `v=spf1 mx ~all` |
| `default._domainkey.example.com` | TXT | DKIM 공개키 |
| `_dmarc.example.com` | TXT | `v=DMARC1; p=quarantine; rua=...` |

## 업그레이드

```bash
git pull
docker compose build
docker compose up -d
# DB 마이그레이션은 백엔드 시작 시 자동 실행
```

## 백업

```bash
# PostgreSQL
docker exec ws-postgres pg_dump -U workspace workspace > backup.sql

# 파일 스토리지
docker cp ws-backend:/storage ./storage-backup
```
