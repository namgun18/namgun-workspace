# namgun-workspace v2.0 Roadmap

> Status: **Experimental** — 아키텍처 설계 및 로드맵 단계

이 문서는 namgun-portal v1.x에서 namgun-workspace v2.0으로의 전면 재설계 로드맵입니다.

---

## Phase 1: 자체 인증 전환 (Authentik 제거)

**목표**: 외부 IdP(Authentik) 의존성을 완전히 제거하고, 포털 자체 인증 시스템으로 전환한다.

### 배경

v1.x는 Authentik을 IdP로 사용하여 Flow Executor API, LDAP Outpost 등 복잡한 의존성 체인이 있었다.
- Authentik 서버 장애 시 전체 인증 불가
- Stalwart 메일이 LDAP Outpost에 의존 → Outpost 다운 시 메일 인증 실패
- Authentik 버전 불일치 문제 (Outpost ↔ Server)
- 셀프 호스팅 배포 시 Authentik 설정이 진입장벽

### 작업 항목

- [ ] `users` 테이블 스키마 확장 (bcrypt password hash, email_verified, mfa_secret)
- [ ] 자체 로그인/회원가입 API (기존 Authentik Flow Executor 대체)
- [ ] JWT 발급 + 리프레시 토큰 (자체 구현, python-jose)
- [ ] OAuth 2.0 Provider 유지 (Gitea SSO용, 기존 코드 활용)
- [ ] Stalwart SQL directory 연동 (LDAP → SQL 쿼리로 대체)
- [ ] LDAP Outpost 제거, Watchdog 스크립트 제거
- [ ] 비밀번호 찾기: 자체 SMTP 발송 (Authentik 이메일 스테이지 대체)
- [ ] 관리자 사용자 CRUD (Authentik Admin API → 자체 DB)

### 완료 기준

- Authentik 컨테이너 없이 로그인/회원가입/비밀번호 변경 동작
- Gitea OAuth SSO 정상 동작
- Stalwart 메일 인증이 PostgreSQL users 테이블로 직접 동작

---

## Phase 2: 서비스 컨테이너 편입

**목표**: 외부 VM/네이티브 서비스를 Docker Compose로 통합하여 단일 `docker compose up`으로 전체 스택 구동.

### 2-1. Stalwart 컨테이너화

- [ ] Stalwart 공식 Docker 이미지 사용 (`stalwartlabs/mail-server`)
- [ ] `config.toml` 템플릿 작성 (환경변수 치환)
- [ ] SQL directory 설정 (PostgreSQL users 테이블 참조)
- [ ] DKIM 키 자동 생성 (`setup.sh`에서 `openssl` 호출)
- [ ] Let's Encrypt TLS 연동 (Nginx 프록시 또는 Stalwart 내장 ACME)
- [ ] 기존 RocksDB 데이터 마이그레이션 가이드

### 2-2. LiveKit 도입 (BBB 교체)

- [ ] LiveKit Server 컨테이너 추가 (`livekit/livekit-server`)
- [ ] LiveKit SDK 연동 (프론트엔드: `livekit-client`, 백엔드: `livekit-api`)
- [ ] 회의실 생성/참가 API (기존 BBB API 엔드포인트 호환 유지)
- [ ] 화면공유, 카메라/마이크 제어
- [ ] LiveKit Egress 컨테이너 (녹화, 선택적 활성화)
- [ ] TURN 서버 설정 (NAT 환경 대응)

### 완료 기준

- `docker compose up` 한 번으로 Stalwart + LiveKit 포함 전체 스택 기동
- BBB VM 제거 가능
- 메일 송수신 + DKIM 서명 정상 동작
- 2인 이상 화상회의 동작 (카메라, 마이크, 화면공유)

---

## Phase 3: 실시간 채팅 — Mattermost 편입

**목표**: Mattermost Team Edition을 Docker 컨테이너로 편입하여 Slack/Teams급 팀 메신저 제공.

### 배경

채팅을 자체 구현(WebSocket)하면 개발 비용이 크고, 검색/스레드/파일공유/알림 등 엔터프라이즈 기능을 재구현해야 한다.
Mattermost Team Edition(MIT 라이선스)을 컨테이너로 편입하면:
- 채널, DM, 스레드, 파일 공유, 검색, 웹훅 즉시 사용
- PostgreSQL 공유 (별도 DB 불필요)
- 포털 SSO 연동 (OpenID Connect)
- 포털 UI에서 iframe 또는 API 통합

### 작업 항목

- [ ] Mattermost Team Edition 컨테이너 추가 (`mattermost/mattermost-team-edition`)
- [ ] PostgreSQL 공유 설정 (별도 DB 스키마 또는 별도 database)
- [ ] 포털 OAuth/OIDC Provider → Mattermost SSO 연동 (자동 계정 생성)
- [ ] Nginx 리버스 프록시 경로 설정 (`/chat` → Mattermost)
- [ ] 포털 UI 통합 (사이드바 채팅 위젯 또는 임베드)
- [ ] Mattermost 기본 UI 커스터마이징 (브랜드 색상, 로고)
- [ ] LiveKit 회의 중 채팅 연동 (Mattermost 채널 자동 생성)
- [ ] 웹훅 연동 (Gitea 커밋/PR → 채팅 알림)
- [ ] 파일 스토리지 통합 (Mattermost 첨부파일 → 포털 파일 서비스)
- [ ] `setup.sh`에서 Mattermost 자동 설정 (관리자 계정, SSO, 기본 채널)

### 완료 기준

- 포털 로그인 후 채팅 즉시 사용 (별도 로그인 없음)
- 채널, DM, 스레드, 파일 공유, 검색 동작
- Gitea 이벤트 → 채팅 알림
- 포털 UI와 시각적 통합 (통일된 네비게이션)

---

## Phase 4: 배포 자동화

**목표**: 비개발자도 10분 안에 전체 워크스페이스를 배포할 수 있는 원클릭 설치.

### setup.sh

사용자 입력 4개만 받는다:

```
DOMAIN          — 예: workspace.example.com
ADMIN_USER      — 예: admin
ADMIN_PASSWORD  — 관리자 비밀번호
ADMIN_EMAIL     — 예: admin@example.com
```

자동 생성되는 값:
- `SECRET_KEY` (64자 랜덤)
- `DB_PASSWORD` (32자 랜덤)
- `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET`
- `DKIM_PRIVATE_KEY` (RSA 2048)
- Gitea OAuth Client ID/Secret

### 작업 항목

- [ ] `setup.sh` 스크립트 작성 (bash, POSIX 호환 목표)
- [ ] `.env` 파일 자동 생성
- [ ] Stalwart `config.toml` 템플릿 렌더링
- [ ] DKIM 키 생성 + DNS 레코드 안내 출력
- [ ] TLS 인증서 자동 발급 (Let's Encrypt / certbot)
- [ ] 초기 관리자 계정 생성 (DB seed)
- [ ] DNS 레코드 안내 출력 (A, MX, SPF, DKIM, DMARC)
- [ ] 시스템 요건 체크 (Docker, Docker Compose, 포트 가용성)
- [ ] `docker compose up -d` 자동 실행

### 완료 기준

- 클린 Ubuntu 22.04/24.04에서 `setup.sh` 실행 후 전체 서비스 동작
- DNS 설정 후 메일 송수신 + TLS 정상
- 관리자 로그인 후 즉시 사용 가능

---

## Phase 5: 화이트라벨링 + i18n

**목표**: 누구나 자신의 브랜드로 워크스페이스를 운영할 수 있도록 커스터마이징 지원.

### 화이트라벨

환경변수 3개로 브랜드 교체:

```env
BRAND_NAME=MyWorkspace
BRAND_LOGO=/path/to/logo.svg
BRAND_COLOR=#4F46E5
```

- [ ] 프론트엔드 하드코딩된 "namgun" 참조 전부 환경변수화
- [ ] 로고, 파비콘, OG 이미지 동적 교체
- [ ] 메일 템플릿 (비밀번호 찾기, 회원가입 승인 등) 브랜드 반영
- [ ] 브라우저 타이틀, manifest.json 브랜드 반영

### i18n

- [ ] `ko.json` 기본 (현재 하드코딩된 한국어 텍스트 추출)
- [ ] `en.json` 영문 번역
- [ ] vue-i18n 또는 @nuxtjs/i18n 적용
- [ ] 백엔드 에러 메시지 다국어화
- [ ] 브라우저 언어 자동 감지 + 수동 전환

### 완료 기준

- `BRAND_NAME=Acme` 설정 시 UI에 "namgun" 흔적 없음
- 한/영 전환 시 전체 UI 텍스트 교체

---

## Phase 6: 운영 도구

**목표**: 프로덕션 운영에 필요한 업데이트, 백업, 모니터링 도구 제공.

### 업데이트

- [ ] `update.sh` — git pull + docker compose 재빌드 + Alembic 마이그레이션 자동 실행
- [ ] 버전 체크 (현재 vs 최신) + 변경 로그 출력
- [ ] 롤백 지원 (이전 이미지 태그로 복원)

### 백업/복원

- [ ] `backup.sh` — PostgreSQL pg_dump + Stalwart 데이터 + 업로드 파일 + .env
- [ ] `restore.sh` — 백업 아카이브에서 복원
- [ ] 자동 백업 스케줄링 (cron 설정 안내)
- [ ] S3 호환 스토리지 업로드 (선택)

### 헬스체크/자가진단

- [ ] `health.sh` — 각 컨테이너 상태 + 포트 확인 + DNS 검증
- [ ] Docker healthcheck 정의 (각 서비스)
- [ ] `/api/health` 엔드포인트 (전체 서비스 상태 JSON)

### 감사 로그

- [ ] 로그인/로그아웃, 사용자 CRUD, 설정 변경 이벤트 기록
- [ ] 감사 로그 조회 API + 관리자 UI
- [ ] 로그 보존 기간 설정
- [ ] ISMS 대응 로그 포맷 (시간, 사용자, IP, 행위, 대상)

### 완료 기준

- `update.sh` 실행으로 무중단 업데이트
- `backup.sh` + `restore.sh`로 전체 데이터 백업/복원
- `health.sh`로 서비스 이상 탐지

---

## Phase 7: PWA + 모바일

**목표**: 네이티브 앱 없이 모바일에서도 워크스페이스를 쾌적하게 사용.

### 작업 항목

- [ ] `manifest.json` 작성 (name, icons, theme_color, display: standalone)
- [ ] Service Worker 등록 (오프라인 캐시, 백그라운드 동기화)
- [ ] 푸시 알림 (Web Push API)
  - 새 메일 도착
  - 채팅 메시지
  - 회의 초대
  - 관리자 알림 (회원가입 승인 요청 등)
- [ ] 모바일 반응형 UI 최적화
- [ ] 앱 설치 프롬프트 (Add to Home Screen)

### 완료 기준

- 모바일 Chrome/Safari에서 홈 화면 추가 후 앱처럼 동작
- 백그라운드 푸시 알림 수신

---

## Phase 8: 오픈코어 모델

**목표**: 지속 가능한 프로젝트 운영을 위한 수익 모델 구축.

### Community Edition (무료, AGPL-3.0)

- 전체 기능 사용 가능
- 사용자 수 제한 (예: 50명)
- 커뮤니티 지원 (GitHub Issues)

### Pro Edition (유료)

- 사용자 수 무제한
- 감사 로그 강화 (ISMS 대응)
- SAML 2.0 / 외부 IdP 연동
- 자동 백업 스케줄링
- 우선 기술 지원

### 라이선스 키

- [ ] RSA 서명 기반 라이선스 키 검증
- [ ] 오프라인 검증 (외부 서버 통신 없음)
- [ ] 라이선스 정보: 조직명, 사용자 수 제한, 만료일
- [ ] 관리자 UI에서 라이선스 입력/확인
- [ ] Community Edition은 라이선스 키 없이 동작

### 완료 기준

- Community Edition: 라이선스 키 없이 전체 기능 (사용자 수 제한만)
- Pro Edition: 라이선스 키 입력 시 제한 해제
- 라이선스 키 없이도 서비스 정상 동작 (기능 제한만)

---

## 타임라인 (예상)

| Phase | 예상 기간 | 우선순위 |
|-------|-----------|----------|
| Phase 1 | 2-3주 | **Critical** |
| Phase 2 | 3-4주 | **Critical** |
| Phase 3 | 2-3주 | High |
| Phase 4 | 1-2주 | **Critical** |
| Phase 5 | 1-2주 | Medium |
| Phase 6 | 2-3주 | High |
| Phase 7 | 1-2주 | Medium |
| Phase 8 | 2-3주 | Low |

> Phase 1~4는 v2.0 릴리즈의 최소 요건입니다.
> Phase 5~8은 v2.1+ 에서 점진적으로 추가됩니다.

---

## 참고

- v1.x 저장소: [namgun-portal](https://git.namgun.or.kr/namgun/namgun-portal)
- v1.x 최신 버전: v1.1.0 (2026-02-24)
- 이 로드맵은 experimental이며, 개발 진행에 따라 변경될 수 있습니다.
