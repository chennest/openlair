#!/bin/sh
# OpenLair 后端容器启动脚本：先跑迁移，再启动应用
# 环境变量由 docker run -e 注入（OPENLAIR_JWT_SECRET / DATABASE_URL / CORS_ORIGINS）
set -e

echo "==> 执行数据库迁移 (alembic upgrade head)"
alembic upgrade head

echo "==> 启动 OpenLair 后端"
exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers "${UVICORN_WORKERS:-1}"
