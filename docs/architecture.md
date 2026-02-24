# namgun-workspace v2.0 아키텍처

## 현재 (v1.x) vs 목표 (v2.0) 비교

### v1.x 아키텍처 (namgun-portal)

```
┌───────────────────────────────────────────────────────────────┐
│                    Docker (WSL2, 192.168.0.150)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Authentik │  │ frontend │  │ backend  │  │ postgres │     │
│  │ (Server)  │  │ (Nuxt 3) │  │(FastAPI) │  │          │     │
│  │ (Worker)  │  │          │  │          │  │          │     │
│  │ (Redis)   │  │          │  │          │  │          │     │
│  └─────┬─────┘  └──────────┘  └────┬─────┘  └──────────┘     │
│        │                           │                          │
│  ┌─────┴─────┐                     │                          │
│  │  Gitea    │                     │                          │
│  └───────────┘                     │                          │
└────────────────────────────────────┼──────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────┐
         │                           │                    │
┌────────┴───────┐  ┌───────────────┴──┐  ┌─────────────┴──┐
│ Rocky Linux     │  │ Hyper-V VM       │  │ OMV NAS        │
│ (192.168.0.250) │  │ (BBB 3.0)        │  │ (NFS v4.1)     │
│                 │  │                   │  │                 │
│ - Stalwart      │  │ - BigBlueButton  │  │ - 파일 스토리지  │
│   (네이티브)     │  │ - TURN Server    │  │                 │
│ - LDAP Outpost  │  │                   │  │                 │
│ - Watchdog      │  │                   │  │                 │
└─────────────────┘  └───────────────────┘  └─────────────────┘
```

**v1.x 문제점**:
- 3개 서버/VM에 서비스 분산 → 관리 복잡
- Authentik 4개 컨테이너 (server, worker, redis, postgres) → 리소스 과다
- LDAP Outpost 버전 불일치 문제
- BBB가 별도 VM 필요 (Ubuntu 22.04 전용)
- 배포 시 수동 설정 항목 20개 이상

---

### v2.0 목표 아키텍처 (namgun-workspace)

```
┌──────────────────────────────────────────────────────────┐
│                  docker-compose.yml                       │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │                   nginx                           │    │
│  │         (리버스 프록시, TLS 종단, 정적 파일)        │    │
│  └──────┬──────────┬──────────┬──────────────────────┘    │
│         │          │          │                            │
│  ┌──────┴───┐ ┌────┴─────┐ ┌─┴──────────┐               │
│  │ frontend │ │ backend  │ │  stalwart   │               │
│  │ (Nuxt 3) │ │(FastAPI) │ │   (mail)    │               │
│  │          │ │          │ │ SQL directory│               │
│  └──────────┘ └────┬─────┘ └─────────────┘               │
│                    │                                      │
│              ┌─────┴─────┐                                │
│              │ postgres  │                                │
│              │ (단일 DB)  │                                │
│              └───────────┘                                │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐              │
│  │  livekit  │  │  redis   │  │ mattermost │              │
│  │  (video)  │  │ (cache/  │  │   (chat)   │              │
│  │  WebRTC   │  │  session/ │  │  Team Ed.  │              │
│  │  SFU      │  │  pubsub)  │  │  MIT       │              │
│  └──────────┘  └──────────┘  └────────────┘              │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**v2.0 개선점**:
- 단일 서버, 단일 `docker compose up`
- 8개 컨테이너로 전체 스택 (v1.x 대비 Authentik 4개 제거, Mattermost 추가)
- 자체 인증 → 외부 IdP 의존성 제거
- LiveKit → BBB VM 제거, Docker 컨테이너 1개로 교체
- Mattermost Team Edition → Slack/Teams급 채팅 내장
- Stalwart Docker 편입 → 별도 서버 불필요
- setup.sh 자동화 → 수동 설정 4개로 축소

---

## 컨테이너 구성 상세

| 컨테이너 | 이미지 | 포트 | 역할 |
|-----------|--------|------|------|
| **nginx** | `nginx:alpine` | 80, 443 | 리버스 프록시, TLS 종단, 정적 파일 서빙 |
| **frontend** | 자체 빌드 | 3000 (내부) | Nuxt 3 SSR, Vue 3 SPA |
| **backend** | 자체 빌드 | 8000 (내부) | FastAPI, API Gateway, WebSocket |
| **postgres** | `postgres:16-alpine` | 5432 (내부) | 포털 DB + Stalwart SQL directory (단일 인스턴스) |
| **redis** | `redis:7-alpine` | 6379 (내부) | 세션 캐시, WebSocket pub/sub, 레이트 리미팅 |
| **stalwart** | `stalwartlabs/mail-server` | 25, 587, 993, 4190 | 메일 서버 (SMTP, IMAP, JMAP, Sieve) |
| **livekit** | `livekit/livekit-server` | 7880, 7881, 7882/udp | WebRTC SFU (화상회의, 화면공유) |
| **mattermost** | `mattermost/mattermost-team-edition` | 8065 (내부) | 팀 채팅 (채널, DM, 스레드, 파일, 검색) |

### 선택적 컨테이너

| 컨테이너 | 이미지 | 역할 |
|-----------|--------|------|
| **livekit-egress** | `livekit/egress` | 회의 녹화 (선택) |
| **gitea** | `gitea/gitea` | Git 호스팅 (선택, 외부 Gitea 사용 가능) |

---

## 인증 플로우 변경

### v1.x (Authentik 기반)

```
사용자 → 포털 로그인 폼
         → FastAPI → Authentik Flow Executor API
                     → Authentik DB 인증
                     → 토큰 반환
         → 포털 세션 발급

Stalwart 메일 인증:
         → Stalwart → LDAP Outpost (3389)
                      → Authentik LDAP Provider
                      → Authentik DB 조회
                      → 인증 결과 반환
```

### v2.0 (자체 인증)

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
```

**변경 효과**:
- 인증 경로 단축 (Authentik + LDAP Outpost 2홉 → DB 직접 1홉)
- 단일 장애점(SPOF) 제거 (Authentik 서버 다운 → 인증 불가 문제 해소)
- 리소스 절약 (Authentik 4개 컨테이너 제거)

---

## 의존성 라이선스 요약

| 구성요소 | 라이선스 | 비고 |
|----------|----------|------|
| Nuxt 3 | MIT | |
| Vue 3 | MIT | |
| FastAPI | MIT | |
| SQLAlchemy | MIT | |
| PostgreSQL | PostgreSQL License | BSD 계열 |
| Redis | BSD-3-Clause (v7) | v7.4+는 RSALv2/SSPLv1, 호환성 확인 필요 |
| Stalwart | AGPL-3.0 | 동일 라이선스 |
| Mattermost Team Edition | MIT | 무료, 상용 가능 |
| LiveKit Server | Apache-2.0 | |
| LiveKit Client SDK | Apache-2.0 | |
| Nginx | BSD-2-Clause | |
| TailwindCSS | MIT | |
| shadcn-vue | MIT | |
| **namgun-workspace** | **AGPL-3.0** | Stalwart AGPL 호환 |

> Redis v7.4 이후 라이선스가 RSALv2/SSPLv1 듀얼로 변경됨.
> Docker 이미지로 사용하는 것은 허용되나, Redis 포크/재배포 시 주의 필요.
> 대안: Valkey (BSD-3-Clause, Redis 7.2 포크)
