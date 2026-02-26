# Architecture Guide

## 시스템 구성

```
┌──────────────────────────────────────────────────┐
│                  Docker Compose                    │
├──────────────────────────────────────────────────┤
│                                                    │
│  [코어 — 항상 실행]                                 │
│  ┌──────────┐  ┌──────────┐                       │
│  │ postgres │  │  redis   │                       │
│  │  :5432   │  │  :6379   │                       │
│  └────┬─────┘  └────┬─────┘                       │
│       │              │                              │
│  ┌────┴──────────────┴────┐                       │
│  │       backend          │  FastAPI :8000          │
│  │  인증, 메일(IMAP/SMTP), │  WebSocket (채팅)      │
│  │  캘린더, 연락처, 파일,  │                       │
│  │  채팅, 회의, Git API    │                       │
│  └────────────────────────┘                       │
│  ┌──────────┐                                     │
│  │ frontend │  Nuxt 3 SSR :3000                    │
│  └──────────┘                                     │
│                                                    │
│  [선택 — docker profile]                            │
│  nginx, gitea, livekit, mailserver, onlyoffice     │
│                                                    │
└──────────────────────────────────────────────────┘
```

## 설계 원칙

- 단일 서버, 단일 `docker compose up`
- 자체 인증 — 외부 IdP 의존성 없음
- 채팅/캘린더/연락처 → backend(FastAPI)에 내장, 추가 컨테이너 불필요
- 메일: IMAP/SMTP 클라이언트 기반 (외부 메일 서버 연결)
- 모듈 시스템: 관리자가 기능별 on/off
- `EXTERNAL_PROXY=true` — 외부 리버스 프록시 환경에서 내장 nginx 비활성화

## 모듈 시스템

모든 기능은 **모듈**로 등록됩니다. 관리자가 개별 모듈을 on/off할 수 있습니다.

```
GET /api/platform/modules  → 활성화된 모듈 목록 (인증 불필요)
PATCH /api/admin/modules/{id}  → 모듈 활성화/비활성화 (admin)
```

내장 모듈: mail, chat, meetings, files, calendar, contacts, git

비활성화된 모듈:
- 네비게이션에서 자동 숨김
- API 호출 시 `403 이 기능은 비활성화되어 있습니다`
- 페이지 접근 시 대시보드로 리다이렉트

### 플로우

```
1. 앱 시작 → init_db() → load_module_states(db)
2. 프론트엔드 부팅 → GET /api/platform/modules
3. AppHeader.vue → enabledModules 기반 동적 네비게이션
4. module-guard 미들웨어 → 비활성 모듈 페이지 차단
5. @require_module 데코레이터 → API 레벨 차단
```

## 메일 아키텍처

### IMAP/SMTP 클라이언트 모드 (기본)

```
사용자 → 포털 메일 UI → FastAPI 백엔드 → IMAP/SMTP → Gmail/Outlook/회사메일
```

- `mail_accounts` 테이블: 사용자별 IMAP/SMTP 서버 정보
- 비밀번호: Fernet 대칭 암호화 (SECRET_KEY에서 키 파생)
- 멀티 계정 지원
- `aioimaplib`: 비동기 IMAP 클라이언트
- `aiosmtplib`: 비동기 SMTP 클라이언트

### 자체 메일서버 모드 (선택)

```
COMPOSE_PROFILES=mailserver
FEATURE_BUILTIN_MAILSERVER=true

사용자 → 포털 UI → FastAPI → IMAP/SMTP → Dovecot/Postfix → 인터넷
```

- Postfix (MTA) + Dovecot (IMAP) + Rspamd (스팸 필터)
- 회원가입 시 메일 계정 자동 생성 (PostgreSQL users 테이블 연동)

## 캘린더/연락처

PostgreSQL 직접 CRUD. 외부 서비스 의존 없음.

| 테이블 | 용도 |
|--------|------|
| `calendars` | 사용자별 캘린더 (이름, 색상, 정렬) |
| `calendar_events` | 이벤트 (시작/종료, 종일, 위치, 상태) |
| `calendar_shares` | 캘린더 공유 (읽기/쓰기 권한) |
| `address_books` | 주소록 |
| `contacts` | 연락처 (이메일/전화/주소 JSON 저장) |

## 인증 플로우

```
사용자 → 포털 로그인 폼 (ID/PW)
       → FastAPI → bcrypt 해시 검증
       → 성공 → 세션 쿠키 발급 (httponly, secure, SameSite=lax)
       → 이후 모든 API 호출에 쿠키 자동 포함
```

Gitea SSO: OAuth 2.0 Provider → Gitea에서 포털 로그인으로 자동 인증

## 데이터베이스

단일 PostgreSQL 인스턴스:
- `workspace` DB — 포털 전체 데이터
- `gitea` DB — Gitea (별도 database, 같은 PostgreSQL)

## 포트 맵

| 포트 | 서비스 | 조건 |
|------|--------|------|
| 80, 443 | nginx | `COMPOSE_PROFILES=nginx` |
| 3000 | frontend (Nuxt SSR) | 항상 |
| 8000 | backend (FastAPI) | 항상 |
| 5432 | PostgreSQL | 내부 |
| 6379 | Redis | 내부 |
| 25, 587 | Postfix (SMTP) | `COMPOSE_PROFILES=mailserver` |
| 993, 143 | Dovecot (IMAP) | `COMPOSE_PROFILES=mailserver` |
| 7880, 7882/udp | LiveKit | `COMPOSE_PROFILES=livekit` |
| 2222 | Gitea SSH | `COMPOSE_PROFILES=gitea` |

## 의존성 라이선스

| 구성요소 | 라이선스 |
|----------|----------|
| Nuxt 3, Vue 3, TailwindCSS, shadcn-vue | MIT |
| FastAPI, SQLAlchemy | MIT |
| PostgreSQL | PostgreSQL License (BSD 계열) |
| Redis | BSD-3-Clause (v7) |
| Gitea | MIT |
| LiveKit | Apache-2.0 |
| aioimaplib | Apache-2.0 |
| aiosmtplib | MIT |
| cryptography | Apache-2.0 / BSD-3 |
| ONLYOFFICE Docs CE | AGPL-3.0 (선택적) |
| Postfix | IBM Public License (선택적) |
| Dovecot | MIT/LGPL-2.1 (선택적) |
| Rspamd | Apache-2.0 (선택적) |
| **namgun-workspace** | **AGPL-3.0** |
