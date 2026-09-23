# ============================================================
# lairweb 前端镜像 — 两阶段构建
# Stage 1: node 构建（pnpm + Vite，产出 dist/）
# Stage 2: nginx 托管静态 + 反代后端 /api
#
# 环境变量（K8s Deployment 运行时设置）：
#   BACKEND_URL: 后端服务地址，如 http://openlair-backend:8000
#                默认 http://127.0.0.1:8000
# 镜像名: harbor.lcc007.top/chennest/openlair-web
# ============================================================

# --- Stage 1: 构建 ---
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/node:22-alpine AS build

WORKDIR /app

# 安装 pnpm（国内镜像下载，固定版本避免 latest 解析波动；与 CI web-build 的 pnpm@9.15.0 一致）
ENV COREPACK_NPM_REGISTRY=https://registry.npmmirror.com
ENV npm_config_registry=https://registry.npmmirror.com
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

# 先拷依赖清单（含 .npmrc 镜像源配置），利用缓存层
COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

# 拷贝源码并构建（vue-tsc 类型检查 + vite build）
COPY . .

# 版本信息（CI 经 --build-arg 传入：APP_VERSION=镜像 tag、APP_COMMIT=git 短哈希）
# ⚠️ 必须声明在 COPY . . 之后：CI 每次传入的 APP_VERSION 都是新值（如 test-42），
#    若放在依赖安装之前，该层缓存键每次变化会连带让 pnpm install 及之后所有层缓存失效，
#    此时 CI 侧 --layers --cache-to 的远程缓存也无层可命中（等于白配）。
ARG APP_VERSION=dev
ARG APP_COMMIT=unknown
ENV APP_VERSION=${APP_VERSION} \
    APP_COMMIT=${APP_COMMIT}

RUN pnpm run build

# --- Stage 2: 运行（nginx 托管 + 反代后端）---
FROM harbor.lcc007.top/docker.io/library/nginx:1.27-alpine

# 后端默认地址（K8s 同 namespace 的 backend Service）
# 部署时可用 env 覆盖：BACKEND_URL=http://xxx
ENV BACKEND_URL=http://openlair-backend:8000

# 前端版本（构建期经 --build-arg 注入，entrypoint envsubst 渲染进 front-version 响应头）
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# 拷贝构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# nginx 配置模板（官方镜像自动 envsubst 渲染 BACKEND_URL / APP_VERSION）
# 放 templates 目录，entrypoint 会自动渲染成 /etc/nginx/conf.d/default.conf
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80
