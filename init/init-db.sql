-- namgun-workspace: 초기 DB 생성
-- workspace DB는 POSTGRES_DB 환경변수로 자동 생성됨
-- Gitea용 데이터베이스 추가 생성

CREATE DATABASE gitea OWNER workspace;
