# Third-Party Licenses

namgun-workspace는 다음 오픈소스 프로젝트를 사용합니다.

## 코어 (항상 포함)

| 소프트웨어 | 라이선스 | 용도 |
|-----------|---------|------|
| PostgreSQL | PostgreSQL License | 데이터베이스 |
| Redis | BSD-3 | 캐시, 세션, Pub/Sub |
| Nuxt 3 | MIT | 프론트엔드 프레임워크 |
| Vue.js 3 | MIT | UI 프레임워크 |
| TailwindCSS | MIT | CSS 프레임워크 |
| shadcn-vue | MIT | UI 컴포넌트 |
| FastAPI | MIT | 백엔드 프레임워크 |
| SQLAlchemy | MIT | ORM |
| asyncpg | Apache-2.0 | PostgreSQL 드라이버 |
| Uvicorn | BSD-3 | ASGI 서버 |
| aioimaplib | Apache-2.0 | IMAP 클라이언트 |
| aiosmtplib | MIT | SMTP 클라이언트 |
| cryptography | Apache-2.0 / BSD-3 | 비밀번호 암호화 |
| Pillow | HPND | 이미지 처리 |
| Tiptap | MIT | 마크다운 에디터 |
| Yjs | MIT | 실시간 공동 편집 |
| passlib | BSD | 비밀번호 해싱 |

## 선택적 컨테이너

| 소프트웨어 | 라이선스 | 용도 | 활성화 조건 |
|-----------|---------|------|------------|
| Nginx | BSD-2 | 리버스 프록시 | `COMPOSE_PROFILES=nginx` |
| Gitea | MIT | Git 호스팅 | `COMPOSE_PROFILES=gitea` |
| LiveKit | Apache-2.0 | 화상회의 (WebRTC) | `COMPOSE_PROFILES=livekit` |
| ONLYOFFICE Docs CE | AGPL-3.0 | 웹 오피스 | `COMPOSE_PROFILES=office` |
| Postfix | IBM Public License | MTA (메일 전송) | `COMPOSE_PROFILES=mailserver` |
| Dovecot | MIT/LGPL-2.1 | IMAP 서버 | `COMPOSE_PROFILES=mailserver` |
| Rspamd | Apache-2.0 | 스팸 필터 | `COMPOSE_PROFILES=mailserver` |

## 라이선스 호환성

namgun-workspace 자체는 AGPL-3.0 라이선스입니다.

- MIT, BSD, Apache-2.0 라이선스: AGPL-3.0과 호환
- ONLYOFFICE CE (AGPL-3.0): 동일 라이선스, 호환
- PostgreSQL License: Permissive, 호환
