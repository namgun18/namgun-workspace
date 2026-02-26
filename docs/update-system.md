# Update System

## 현재 업데이트 방식

namgun-workspace는 Git 기반 업데이트를 사용합니다.

```bash
# 1. 최신 코드 가져오기
git pull origin main

# 2. 컨테이너 재빌드
docker compose build

# 3. 컨테이너 재시작
docker compose up -d
```

DB 마이그레이션은 백엔드 시작 시 자동 실행됩니다 (`init_db()` → `_run_migrations()`).

## 마이그레이션 방식

경량 마이그레이션 시스템:
- `CREATE TABLE IF NOT EXISTS` — 새 테이블 자동 생성
- `ALTER TABLE ... ADD COLUMN` — 새 컬럼 추가 (기존 데이터 보존)
- 각 마이그레이션은 독립적으로 실행 (SAVEPOINT 사용)
- 이미 적용된 마이그레이션은 자동 스킵

## 버전 체계

- **Major** (3.x.x): 호환성 깨지는 변경 (메일 스택 전환 등)
- **Minor** (x.1.x): 새 기능 추가
- **Patch** (x.x.1): 버그 수정

## 롤백

```bash
# 이전 커밋으로 돌아가기
git log --oneline -10
git checkout <이전 커밋 해시>
docker compose build && docker compose up -d
```

주의: DB 스키마가 변경된 경우 롤백 시 호환성 문제가 있을 수 있습니다.
새 컬럼 추가는 안전하지만, 테이블 삭제나 컬럼 타입 변경은 롤백이 어렵습니다.

## 배포 방식

현재 **수동 배포**를 사용합니다:

```bash
git pull origin main
docker compose up -d --build
```

> CI/CD 자동 배포(Gitea Actions)는 비활성화 상태입니다.
> 필요 시 `.gitea/workflows/` 디렉토리에 워크플로를 추가하여 재활성화할 수 있습니다.

## 백업

```bash
# 자동 백업 (PostgreSQL + Redis + 메일)
sudo bash scripts/backup.sh [백업디렉토리]

# 30일 이상 된 백업은 자동 삭제됩니다.
```
