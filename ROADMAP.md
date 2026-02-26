# namgun-workspace Roadmap

> 11-Phase 로드맵 — v3.0 메일 스택 전환 이후 재정의

---

## Phase 1: 자체 인증 — Done

자체 bcrypt + JWT 인증, OAuth 2.0 Provider (Gitea SSO), 승인제 회원가입.

## Phase 2: 서비스 컨테이너 구성 — Done

Nginx, Gitea, LiveKit 통합. `docker compose up` 한 번으로 전체 스택.

## Phase 3: 실시간 채팅 — Done

FastAPI WebSocket + Redis Pub/Sub. 채널, DM, 스레드, 멘션, 리액션, 검색.

## Phase 4: 모듈 시스템 + 메일 스택 전환 — Done (v3.0)

### 4-1. 기능 모듈 on/off 시스템
- 관리자가 모듈(메일, 채팅, 회의 등)을 개별 활성화/비활성화
- DB 기반 설정, 서버 재시작 불필요
- 프론트엔드 네비게이션 자동 동적화
- API 가드 (비활성 모듈 호출 시 403)

### 4-2. 메일 모듈 IMAP/SMTP 클라이언트 전환
- Stalwart JMAP 의존성 완전 제거
- 사용자가 Gmail, Outlook, 회사 메일 등 기존 계정을 IMAP/SMTP로 연결
- 멀티 계정 지원 (개인+업무 메일 동시 사용)
- Fernet 암호화로 비밀번호 안전 저장
- 접속 테스트 기능

### 4-3. 캘린더/연락처 PostgreSQL 자체 구현
- JMAP 의존성 제거, PostgreSQL 직접 CRUD
- 캘린더 공유 (읽기/쓰기 권한)
- 연락처 검색, 주소록 관리

### 4-4. 자체 메일서버 선택적 제공
- Postfix + Dovecot + Rspamd (docker profile: `mailserver`)
- `FEATURE_BUILTIN_MAILSERVER=true` 시 회원가입 → 메일 계정 자동 생성
- 기본값은 외부 IMAP/SMTP 클라이언트 모드

---

## Phase 5: 배포 자동화 — Done (v3.2)

- `setup.sh` 인터랙티브 설치 (배포 모드 3종: external_proxy / standalone / dev)
- nginx.conf 모드별 자동 생성 (HTTP-only / HTTP+HTTPS)
- Standalone: Let's Encrypt 자동 발급, docker-compose.override.yml 자동 생성
- DKIM 키 자동 생성, DNS 레코드 안내
- 초기 관리자 계정 DB seed
- 5단계 배포 후 검증 체인 (컨테이너 → 헬스체크 → admin seed → noreply → SSL)
- 컨테이너 리소스 제한 (메모리/CPU)
- 백업 스크립트 (`scripts/backup.sh`)

## Phase 6: 화이트라벨링 + i18n — In Progress

- 환경변수 3개로 브랜드 교체 (BRAND_NAME, BRAND_LOGO, BRAND_COLOR)
- 한/영 다국어 지원 (@nuxtjs/i18n, vue-i18n) — **기반 구축 완료 (v3.3)**
- i18n 구조: `locales/ko.json`, `locales/en.json`, `$t()` 패턴 (login.vue 전환 완료)
- 메일 템플릿 브랜드 반영
- 나머지 페이지 i18n 마이그레이션 진행 중

## Phase 7: CalDAV/CardDAV 동기화

- Thunderbird, iOS, Android와 캘린더/연락처 양방향 동기화
- CalDAV/CardDAV 서버 엔드포인트 (FastAPI 기반 또는 Radicale 연동)
- 외부 CalDAV 캘린더 구독 (읽기 전용)

## Phase 8: 플러그인 아키텍처

- 모듈 레지스트리를 외부 플러그인까지 확장
- 플러그인 매니페스트 (manifest.json): 이름, 라우트, API, 의존성
- 관리자 UI에서 플러그인 설치/제거/활성화
- 플러그인 마켓플레이스 (향후)

## Phase 9: 운영 도구

- `update.sh` — 무중단 업데이트
- `backup.sh` — PostgreSQL + Redis + 메일 백업 (**구현 완료 v3.3**, `scripts/backup.sh`)
- `restore.sh` — 복원 스크립트
- `health.sh` — 서비스 자가진단
- 감사 로그 (로그인, 설정 변경 기록)

## Phase 10: PWA + 모바일

- manifest.json, Service Worker, 푸시 알림
- 모바일 반응형 UI 최적화
- 오프라인 캐시

## Phase 11: 오픈코어 모델

- Community Edition (AGPL-3.0, 전체 기능)
- Pro Edition (사용자 무제한, SAML, 감사 로그 강화, 우선 지원)
- RSA 서명 기반 라이선스 키

---

## 타임라인

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | 자체 인증 | Done |
| Phase 2 | 서비스 컨테이너 구성 | Done |
| Phase 3 | 실시간 채팅 | Done |
| Phase 4 | 모듈 시스템 + 메일 스택 전환 | Done (v3.0) |
| Phase 5 | 배포 자동화 | Done (v3.2) |
| Phase 6 | 화이트라벨링 + i18n | In Progress |
| Phase 7 | CalDAV/CardDAV 동기화 | Planned |
| Phase 8 | 플러그인 아키텍처 | Planned |
| Phase 9 | 운영 도구 | Planned |
| Phase 10 | PWA + 모바일 | Planned |
| Phase 11 | 오픈코어 모델 | Planned |
