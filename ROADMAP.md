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

## Phase 6: 화이트라벨링 + i18n — Done (v3.4)

- 환경변수 3개로 브랜드 교체 (BRAND_NAME, BRAND_LOGO, BRAND_COLOR)
- 한/영 다국어 지원 (@nuxtjs/i18n, vue-i18n, 430+ 키)
- 동적 테마 색상 (hex→HSL), 파비콘 업로드
- 관리자 설정 패널 (브랜딩/SMTP/SSL DB 저장)

## Phase 7: CalDAV/CardDAV 동기화 — Done (v3.5)

- Thunderbird, iOS, Android와 캘린더/연락처 양방향 동기화
- CalDAV/CardDAV 서버 엔드포인트 (FastAPI 기반)
- .well-known 자동 디스커버리
- PROPFIND/REPORT/GET/PUT/DELETE, HTTP Basic Auth

## Phase 8: 전수조사 + 보안강화 + 플러그인 — Done (v4.0)

- TOTP 2FA, 할일관리(Tasks), 통합검색, 감사로그
- 파일휴지통, 메일임시저장, vCard 가져오기/내보내기
- 채팅파일첨부, 비밀번호복잡도, nginx rate limiting
- DAV If-Match 충돌방지, OAuth Redis 저장
- Docker non-root, 플러그인 아키텍처 (자동 발견·로드·관리)

## Phase 9: 운영 도구 — Done (v4.0.2)

- `update.sh` — 무중단 업데이트 (git pull → 순차 재빌드 → 헬스체크 → 실패 시 롤백)
- `backup.sh` — PostgreSQL + Redis + 메일 백업 (v3.3)
- `restore.sh` — 복원 스크립트 (v4.0.0)
- `health.sh` — 서비스 자가진단 (Docker/DB/Redis/API/디스크/NFS/SSL, JSON 출력 지원)
- 감사 로그 (로그인, 설정 변경 기록) (v4.0.0)

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
| Phase 6 | 화이트라벨링 + i18n | Done (v3.4) |
| Phase 7 | CalDAV/CardDAV 동기화 | Done (v3.5) |
| Phase 8 | 전수조사 + 보안강화 + 플러그인 | Done (v4.0) |
| Phase 9 | 운영 도구 | Done (v4.0.2) |
| Phase 10 | PWA + 모바일 | Planned |
| Phase 11 | 오픈코어 모델 | Planned |
