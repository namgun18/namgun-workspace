# namgun-workspace v2.0 아키텍처

## 목표 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│                  docker-compose.yml                       │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │                    nginx                          │    │
│  │      리버스 프록시, TLS 종단, Let's Encrypt        │    │
│  │      (EXTERNAL_PROXY=true 시 비활성화)             │    │
│  └──────┬──────────┬──────────┬──────────────────────┘    │
│         │          │          │                            │
│  ┌──────┴───┐ ┌────┴─────┐ ┌─┴──────────┐               │
│  │ frontend │ │ backend  │ │  stalwart   │               │
│  │ (Nuxt 3) │ │(FastAPI) │ │   (mail)    │               │
│  │          │ │채팅/문서  │ │ SQL directory│               │
│  └──────────┘ └────┬─────┘ └─────────────┘               │
│                    │                                      │
│              ┌─────┴─────┐                                │
│              │ postgres  │                                │
│              │ (단일 DB)  │                                │
│              └───────────┘                                │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │  livekit  │  │  redis   │  │  gitea   │               │
│  │  (video)  │  │ (cache/  │  │  (git)   │               │
│  │  WebRTC   │  │  session/ │  │          │               │
│  │  SFU      │  │  pubsub)  │  │          │               │
│  └──────────┘  └──────────┘  └──────────┘               │
│                                                           │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐                │
│    onlyoffice (선택적, ENABLE_OFFICE=true)                 │
│  │ DOCX/XLSX/PPTX 웹 편집 + 동시 작업  │                │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘                │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### 설계 원칙

- 단일 서버, 단일 `docker compose up`
- 8개 코어 컨테이너 (nginx, frontend, backend, postgres, redis, stalwart, livekit, gitea)
- 자체 인증 — 외부 IdP 의존성 없음
- 채팅/문서 → backend(FastAPI)에 내장, 추가 컨테이너 불필요
- ONLYOFFICE → 선택적 컨테이너 (DOCX/XLSX/PPTX 웹 편집)
- `EXTERNAL_PROXY=true` — 기존 리버스 프록시가 있는 환경에서 내장 nginx 비활성화
- setup.sh 자동화 → 사용자 입력 4개로 전체 구성

---

## 컨테이너 구성

### 코어 (8개)

| 컨테이너 | 이미지 | 포트 | 역할 |
|-----------|--------|------|------|
| **nginx** | `nginx:alpine` | 80, 443 | 리버스 프록시, TLS 종단 (`EXTERNAL_PROXY=true` 시 비활성화) |
| **frontend** | 자체 빌드 | 3000 (내부) | Nuxt 3 SSR, Vue 3 SPA |
| **backend** | 자체 빌드 | 8000 (내부) | FastAPI, API Gateway, WebSocket (채팅 + 문서 공동편집) |
| **postgres** | `postgres:16-alpine` | 5432 (내부) | 포털 DB + Stalwart SQL directory + Gitea (단일 인스턴스) |
| **redis** | `redis:7-alpine` | 6379 (내부) | 세션 캐시, WebSocket pub/sub, 레이트 리미팅 |
| **stalwart** | `stalwartlabs/mail-server` | 25, 587, 993 | 메일 서버 (SMTP, IMAP, JMAP, Sieve) |
| **livekit** | `livekit/livekit-server` | 7880, 7881, 7882/udp | WebRTC SFU (화상회의, 화면공유) |
| **gitea** | `gitea/gitea` (MIT) | 3000 (내부), 22/2222 (SSH) | Git 호스팅, 저장소, 이슈, PR |

### 선택적

| 컨테이너 | 이미지 | 활성화 | 역할 |
|-----------|--------|--------|------|
| **onlyoffice** | `onlyoffice/documentserver` (AGPL-3.0) | `ENABLE_OFFICE=true` | DOCX/XLSX/PPTX 웹 편집 + 동시 작업 (WOPI) |
| **livekit-egress** | `livekit/egress` | `ENABLE_RECORDING=true` | 회의 녹화 |

---

## 인증 플로우

```
사용자 → 포털 로그인 폼
         → FastAPI → PostgreSQL users 테이블
                     → bcrypt 비밀번호 검증
                     → JWT 발급
         → 포털 세션 발급

Stalwart 메일 인증:
         → Stalwart → PostgreSQL SQL directory
                      → users 테이블 직접 조회
                      → 인증 결과 반환

Gitea SSO:
         → Gitea → 포털 OAuth 2.0 Provider
                   → 자동 로그인/계정 생성
```

### 설계 효과

- 인증 경로: DB 직접 1홉 (외부 IdP 경유 없음)
- 단일 장애점 없음 (외부 IdP 서버 다운 → 인증 불가 문제 해소)
- 모든 서비스가 동일한 users 테이블 참조

---

## 호스트 노출 포트

외부에서 접근 필요한 포트만 호스트에 노출:

| 포트 | 서비스 | 프로토콜 |
|------|--------|----------|
| 80, 443 | nginx | HTTP/HTTPS |
| 25 | stalwart | SMTP (메일 수신) |
| 587 | stalwart | Submission (메일 발송) |
| 993 | stalwart | IMAPS (메일 읽기) |
| 22/2222 | gitea | Git SSH |
| 7882 | livekit | WebRTC 미디어 (UDP) |

나머지는 Docker 내부 네트워크 전용.

---

## 의존성 라이선스

| 구성요소 | 라이선스 | 비고 |
|----------|----------|------|
| Nuxt 3 | MIT | |
| Vue 3 | MIT | |
| FastAPI | MIT | |
| SQLAlchemy | MIT | |
| PostgreSQL | PostgreSQL License | BSD 계열 |
| Redis | BSD-3-Clause (v7) | v7.4+는 RSALv2/SSPLv1 |
| Stalwart | AGPL-3.0 | 동일 라이선스 |
| Gitea | MIT | |
| ONLYOFFICE Docs CE | AGPL-3.0 | 동일 라이선스, 선택적 |
| Tiptap | MIT | 마크다운 에디터 |
| Yjs | MIT | CRDT 실시간 공동 편집 |
| LiveKit Server | Apache-2.0 | |
| LiveKit Client SDK | Apache-2.0 | |
| Nginx | BSD-2-Clause | |
| TailwindCSS | MIT | |
| shadcn-vue | MIT | |
| **namgun-workspace** | **AGPL-3.0** | |

> Redis v7.4 이후 라이선스가 RSALv2/SSPLv1 듀얼로 변경됨.
> Docker 이미지로 사용하는 것은 허용되나, Redis 포크/재배포 시 주의 필요.
> 대안: Valkey (BSD-3-Clause, Redis 7.2 포크)
