# OpenLair 后端镜像（参照官方 full-stack-fastapi-template 的 uv 模式）
# 构建：docker build -f backend/Dockerfile -t openlair-backend backend
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.14.5-slim

ENV PYTHONUNBUFFERED=1

# 安装 uv（从官方 uv 镜像拷贝二进制，避免包管理器安装）
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# 编译字节码 + 缓存优化
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app/

# venv 可执行文件前置到 PATH（镜像内直接可用 uvicorn/alembic）
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/.venv/bin:$PATH"

# 国内加速：uv 下载 PyPI 依赖走清华源（构建时也可 --build-arg 覆盖）
ENV UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

# 第一层：仅挂载 lock 文件安装第三方依赖（不复制源码 → 依赖层可缓存）
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-workspace

# 复制源码（此时才失效依赖缓存层）
COPY ./app /app/app
COPY ./alembic.ini /app/alembic.ini
COPY ./migrations /app/migrations
COPY ./scripts /app/scripts

# 第二层：完整 sync（安装 workspace 包本体）
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen

# 启动前脚本（alembic 迁移 + 启动应用；create_all/seed 由应用兜底）
RUN chmod +x /app/scripts/prestart.sh

EXPOSE 8001

WORKDIR /app/

CMD ["/app/scripts/prestart.sh"]
