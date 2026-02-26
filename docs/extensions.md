# Extensions & Module System

## 모듈 시스템 개요

namgun-workspace의 모든 기능은 **모듈**로 등록됩니다.
관리자가 `/admin/modules` 페이지에서 개별 모듈을 활성화/비활성화할 수 있습니다.

## 내장 모듈

| ID | 이름 | 라우트 | API 접두사 | 기본 상태 |
|----|------|--------|-----------|----------|
| `mail` | 메일 | `/mail` | `/api/mail` | 활성 |
| `chat` | 채팅 | `/chat` | `/api/chat` | 활성 |
| `meetings` | 화상회의 | `/meetings` | `/api/meetings` | 활성 |
| `files` | 파일 | `/files` | `/api/files` | 활성 |
| `calendar` | 캘린더 | `/calendar` | `/api/calendar` | 활성 |
| `contacts` | 연락처 | `/contacts` | `/api/contacts` | 활성 |
| `git` | Git | `/git` | `/api/git` | 활성 |

## 모듈 상태 저장

`system_settings` 테이블에 `module.<id>.enabled` 키로 저장됩니다.

```sql
-- 예시
INSERT INTO system_settings (key, value) VALUES ('module.mail.enabled', 'false');
```

서버 재시작 불필요 — API 호출 시 즉시 반영됩니다.

## 백엔드 가드

`@require_module` 데코레이터로 API 엔드포인트를 보호합니다:

```python
from app.modules.registry import require_module

@router.get("/mailboxes")
@require_module("mail")
async def list_mailboxes(...):
    ...
```

비활성 모듈의 API 호출 시:
```json
HTTP 403
{"detail": "이 기능은 비활성화되어 있습니다"}
```

## 프론트엔드 가드

### 네비게이션 동적화

`usePlatform()` composable이 `/api/platform/modules`에서 모듈 목록을 가져와
`AppHeader.vue`에서 동적으로 네비게이션을 렌더링합니다.

### 페이지 가드

`middleware/module-guard.global.ts`가 비활성 모듈의 페이지 접근을
대시보드(`/`)로 리다이렉트합니다.

## 향후: 플러그인 아키텍처 (Phase 8)

현재 모듈 시스템은 내장 모듈만 지원합니다.
Phase 8에서 외부 플러그인 지원이 추가될 예정입니다:

- 플러그인 매니페스트 (`manifest.json`)
- 플러그인 마켓플레이스
- 동적 라우트/API 등록
- 플러그인 샌드박싱
