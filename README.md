# namgun-workspace

> Self-hosted all-in-one workspace — Mail, Video, Chat, Docs, Office, Git, Files, Calendar, Contacts

**namgun-workspace**는 소규모 팀을 위한 셀프 호스팅 올인원 워크스페이스입니다.
하나의 `docker compose up`으로 메일, 화상회의, 채팅, 문서, 웹 오피스, Git, 파일 관리, 캘린더, 연락처를 모두 배포할 수 있습니다.

## 비전

Microsoft 365, Google Workspace 같은 SaaS에 종속되지 않고, 자체 서버에서 팀 협업에 필요한 모든 도구를 운영할 수 있어야 합니다.

- **제로 의존성**: 외부 SaaS 없이 완전한 오프라인 운영 가능
- **원클릭 배포**: 도메인과 관리자 정보만 입력하면 전체 스택 자동 구성
- **통합 경험**: 사용자는 하나의 서비스만 인식, 개별 솔루션은 보이지 않음
- **모듈화**: 관리자가 기능별로 on/off 가능 (메일, 채팅, 회의 등)
- **기존 메일 연동**: Gmail, Outlook 등 기존 계정을 IMAP/SMTP로 연결

## 빠른 시작

### 원클릭 설치 (권장)

```bash
git clone https://git.namgun.or.kr/namgun/namgun-workspace.git
cd namgun-workspace
sudo bash setup.sh
```

`setup.sh`가 Docker 설치, .env 생성, 빌드, 관리자 계정 생성까지 인터랙티브로 처리합니다.
(Ubuntu 22.04/24.04, Debian 12 지원)

### 수동 설치

```bash
git clone https://git.namgun.or.kr/namgun/namgun-workspace.git
cd namgun-workspace
cp .env.example .env
# .env 편집 (DB_PASSWORD, SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD 등)
docker compose up -d
```

## 아키텍처

코어 컨테이너 4개 (항상 실행) + 선택적 컨테이너:

```
┌───────────────────────────────────────────────┐
│         docker-compose.yml                      │
├───────────────────────────────────────────────┤
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  nginx   │  │ frontend │  │ backend  │    │
│  │ (proxy)  │  │ (Nuxt 3) │  │(FastAPI) │    │
│  └──────────┘  └──────────┘  └────┬─────┘    │
│                              채팅/캘린더/     │
│                              연락처/메일API   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ postgres │  │  redis   │  │  gitea   │    │
│  │   (db)   │  │ (cache)  │  │  (git)   │    │
│  └──────────┘  └──────────┘  └──────────┘    │
│                                                 │
│  ┌──────────┐  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐    │
│  │ livekit  │    mailserver (선택)          │    │
│  │ (video)  │  │ postfix+dovecot+rspamd │    │
│  └──────────┘  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘    │
│                                                 │
└───────────────────────────────────────────────┘
```

- **채팅, 캘린더, 연락처**: backend(FastAPI) 내장. 추가 컨테이너 불필요.
- **메일**: IMAP/SMTP 클라이언트 기반 (Gmail, Outlook 등 외부 메일 연결)
- **자체 메일서버**: `COMPOSE_PROFILES=mailserver`로 선택적 활성화
- **외부 프록시**: `EXTERNAL_PROXY=true`로 내장 nginx 비활성화

## 주요 기능

| 기능 | 설명 |
|------|------|
| **통합 인증** | 자체 인증 (bcrypt, JWT), OAuth 2.0 Provider, 승인제 회원가입 |
| **메일** | IMAP/SMTP 클라이언트 (Gmail, Outlook 등 연결), 멀티 계정 지원 |
| **화상회의** | LiveKit (WebRTC SFU), 화면공유, 녹화(선택) |
| **실시간 채팅** | 채널, DM, 스레드, 멘션, 리액션, 검색, 파일 첨부 |
| **문서/메모** | 마크다운 위키, 실시간 공동 편집 (Yjs) |
| **웹 오피스** | ONLYOFFICE (DOCX/XLSX/PPTX, 선택적) |
| **Git** | Gitea (저장소, 이슈, PR, 코드 리뷰) |
| **파일 관리** | 웹 파일 브라우저 (업로드/다운로드/공유링크) |
| **캘린더** | PostgreSQL 기반 (월/주/일 뷰, 캘린더 공유) |
| **연락처** | PostgreSQL 기반 (주소록, 검색) |
| **모듈 관리** | 관리자가 기능별 on/off (메일, 채팅, 회의 등) |
| **관리자 패널** | 사용자 관리, 방문자 분석, 모듈 설정 |

## 기술 스택

| 분류 | 기술 |
|------|------|
| 프론트엔드 | Nuxt 3, Vue 3, TailwindCSS, shadcn-vue |
| 백엔드 | FastAPI, SQLAlchemy 2.0 (async), asyncpg |
| 인증 | 자체 구현 (bcrypt, JWT, OAuth 2.0 Provider) |
| 데이터베이스 | PostgreSQL 16, Redis |
| 메일 | IMAP/SMTP 클라이언트 (aioimaplib, aiosmtplib) |
| 화상회의 | LiveKit (WebRTC SFU) |
| 채팅 | 자체 구현 (FastAPI WebSocket + Redis Pub/Sub) |
| 문서 | 자체 구현 (Tiptap/Milkdown + Yjs) |
| Git | Gitea (MIT) |
| 웹 오피스 | ONLYOFFICE Docs CE (AGPL-3.0, 선택적) |
| 컨테이너 | Docker Compose |

## 로드맵

전체 로드맵은 [ROADMAP.md](ROADMAP.md)를 참고하세요.

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | 자체 인증 | Done |
| Phase 2 | 서비스 컨테이너 구성 | Done |
| Phase 3 | 실시간 채팅 | Done |
| Phase 4 | 모듈 시스템 + 메일 스택 전환 | Done (v3.0) |
| Phase 5 | 배포 자동화 | Done |
| Phase 6 | 화이트라벨링 + i18n | Planned |
| Phase 7~11 | CalDAV, 플러그인, 운영도구, PWA, 오픈코어 | Planned |

## 변경이력

| 버전 | 날짜 | 내용 |
|------|------|------|
| v3.2.0 | 2026-02-26 | Phase 5: 배포 자동화 — setup.sh 인터랙티브 스크립트, 관리자 시드 CLI, DKIM 생성, docker-compose 볼륨 자동 생성 |
| v3.1.0 | 2026-02-26 | 메일 상용 기능 (스팸 지정, 헤더 보기, 편지함 CRUD, 수신확인/MDN), 헬스체크 대시보드 최신화, 보안/버그/레거시 코드 전면 점검 및 수정 |
| v3.0.0 | 2026-02-26 | Phase 4: 모듈 on/off 시스템, 메일 IMAP/SMTP 전환 (Stalwart JMAP 제거), 캘린더/연락처 PostgreSQL 자체 구현, 자체 메일서버 선택적 제공 (docker profile) |
| v2.1.0 | 2026-02-26 | Phase 3-2: 스레드, 이모지 리액션, 메시지 검색, Gitea 웹훅 알림, LiveKit 회의 채팅 |
| v2.0.0 | 2026-02-26 | Phase 3-1: 실시간 채팅 기본 기능 |

## 라이선스

[AGPL-3.0](LICENSE)
