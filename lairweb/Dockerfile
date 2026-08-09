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

# 安装 pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# 先拷依赖清单，利用缓存层
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# 拷贝源码并构建（vue-tsc 类型检查 + vite build）
COPY . .
RUN pnpm run build

# --- Stage 2: 运行（nginx 托管 + 反代后端）---
FROM harbor.lcc007.top/docker.io/library/nginx:1.27-alpine

# 后端默认地址（K8s 同 namespace 的 backend Service）
# 部署时可用 env 覆盖：BACKEND_URL=http://xxx
ENV BACKEND_URL=http://openlair-backend:8000

# 拷贝构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# nginx 配置模板（官方镜像自动 envsubst 渲染 BACKEND_URL）
# 放 templates 目录，entrypoint 会自动渲染成 /etc/nginx/conf.d/default.conf
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80
