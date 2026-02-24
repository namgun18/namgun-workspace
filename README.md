# namgun-workspace

> Self-hosted all-in-one workspace for startups — Mail, Video, Chat, Docs, Office, Git, Files, Calendar

**namgun-workspace**는 소규모 팀을 위한 셀프 호스팅 올인원 워크스페이스입니다.
하나의 `docker compose up`으로 메일, 화상회의, 채팅, 문서, 웹 오피스, Git, 파일 관리, 캘린더를 모두 배포할 수 있습니다.

## 비전

Microsoft 365, Google Workspace 같은 SaaS에 종속되지 않고, 자체 서버에서 팀 협업에 필요한 모든 도구를 운영할 수 있어야 합니다.

namgun-workspace는 다음 원칙으로 설계됩니다:

- **제로 의존성**: 외부 SaaS 없이 완전한 오프라인 운영 가능
- **원클릭 배포**: 도메인과 관리자 정보 4개만 입력하면 전체 스택 자동 구성
- **통합 경험**: 사용자는 하나의 서비스만 인식, 뒤에서 돌아가는 개별 솔루션은 보이지 않음
- **화이트라벨**: 브랜드명, 로고, 색상을 환경변수로 자유롭게 교체

## v1 → v2 주요 변경점

| 항목 | v1 (namgun-portal) | v2 (namgun-workspace) |
|------|--------------------|-----------------------|
| 인증 | Authentik (외부 IdP) | 자체 인증 (내장) |
| 화상회의 | BigBlueButton (별도 VM) | LiveKit (Docker 컨테이너) |
| 메일 | Stalwart (네이티브 설치) | Stalwart (Docker 편입) |
| 채팅 | 없음 | 자체 구현 (WebSocket, 채널, DM, 스레드) |
| 문서/메모 | 없음 | 자체 마크다운 위키 + 실시간 공동 편집 |
| 웹 오피스 | 없음 | ONLYOFFICE Docs CE (선택적, DOCX/XLSX/PPTX) |
| 배포 | 수동 설정 다수 | `setup.sh` 원클릭 자동화 |
| 라이선스 | Private | AGPL-3.0 (오픈소스) |
| 브랜딩 | "namgun" 하드코딩 | 화이트라벨 (환경변수) |
| i18n | 한국어 전용 | ko/en 다국어 |

## 목표 아키텍처

```
docker compose up -d
```

8개 코어 컨테이너 + 선택적 컨테이너:

```
┌───────────────────────────────────────────────────────┐
│          namgun-workspace/docker-compose.yml            │
├───────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  nginx   │  │ frontend │  │ backend  │            │
│  │ (proxy)  │  │ (Nuxt 3) │  │(FastAPI) │            │
│  └────┬─────┘  └──────────┘  └────┬─────┘            │
│       │                      채팅/문서/API              │
│  ┌────┴─────┐  ┌──────────┐  ┌──────────┐            │
│  │ stalwart │  │  livekit  │  │  gitea   │            │
│  │  (mail)  │  │  (video)  │  │  (git)   │            │
│  └──────────┘  └──────────┘  └──────────┘            │
│                                                        │
│  ┌──────────┐  ┌──────────┐                           │
│  │ postgres │  │  redis   │                           │
│  │   (db)   │  │ (cache)  │                           │
│  └──────────┘  └──────────┘                           │
│                                                        │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐                 │
│    onlyoffice (선택, ENABLE_OFFICE)                     │
│  │ DOCX/XLSX/PPTX 편집 + 동시작업  │                 │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘                 │
│                                                        │
└───────────────────────────────────────────────────────┘
```

> 채팅, 문서/메모는 backend(FastAPI) 컨테이너에 내장. 추가 컨테이너 불필요.
> ONLYOFFICE는 `ENABLE_OFFICE=true`로 선택적 활성화.
> 외부 프록시 뒤에서 운영 시 `EXTERNAL_PROXY=true`로 내장 nginx 비활성화.

## 기술 스택

| 분류 | 기술 |
|------|------|
| 프론트엔드 | Nuxt 3, Vue 3, TailwindCSS, shadcn-vue |
| 백엔드 | FastAPI, SQLAlchemy 2.0 (async), asyncpg |
| 인증 | 자체 구현 (bcrypt, JWT, OAuth 2.0 Provider) |
| 데이터베이스 | PostgreSQL 16, Redis |
| 메일 | Stalwart Mail Server (JMAP, SQL directory) |
| 화상회의 | LiveKit (WebRTC SFU) |
| 실시간 채팅 | 자체 구현 (FastAPI WebSocket + Redis Pub/Sub) |
| 문서/메모 | 자체 구현 (Tiptap/Milkdown 에디터 + Yjs 공동 편집) |
| Git | Gitea (MIT) |
| 웹 오피스 | ONLYOFFICE Docs CE (AGPL-3.0, 선택적) |
| TLS | Let's Encrypt (자동 발급) |
| 컨테이너 | Docker Compose |

## 빠른 시작 (목표)

```bash
git clone https://git.namgun.or.kr/namgun/namgun-workspace.git
cd namgun-workspace
./setup.sh
# → DOMAIN, ADMIN_USER, ADMIN_PASSWORD, ADMIN_EMAIL 입력
# → 자동으로 모든 설정 생성 + docker compose up
```

## 로드맵

전체 로드맵은 [ROADMAP.md](ROADMAP.md)를 참고하세요.

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | 자체 인증 전환 (Authentik 제거) | Planned |
| Phase 2 | 서비스 컨테이너 편입 — Gitea, Stalwart, LiveKit | Planned |
| Phase 3 | 실시간 채팅 (자체 구현, WebSocket) | Planned |
| Phase 4 | 배포 자동화 (setup.sh) | Planned |
| Phase 5 | 화이트라벨링 + i18n | Planned |
| Phase 6 | 문서/메모 + 웹 오피스 (ONLYOFFICE) | Planned |
| Phase 7 | 운영 도구 (업데이트, 백업, 헬스체크) | Planned |
| Phase 8 | PWA + 모바일 | Planned |
| Phase 9 | 오픈코어 모델 | Planned |

## v1.x (namgun-portal)

v1.x는 현재 안정 운영 중인 namgun-portal 프로젝트입니다.

- 저장소: [namgun-portal](https://git.namgun.or.kr/namgun/namgun-portal)
- 최신 버전: v1.1.0

## 라이선스

[AGPL-3.0](LICENSE)

Copyright (c) 2026 namgun.or.kr
