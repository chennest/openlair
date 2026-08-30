import { execSync } from 'node:child_process'
import { defineConfig, loadEnv, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { mockDevServerPlugin } from 'vite-plugin-mock-dev-server'

// https://vite.dev/config/

// ---------- 构建版本信息 ----------
// 版本来源优先级：构建环境变量（CI 经 --build-arg 传入）→ 本地 git 短哈希 → 兜底
function resolveBuildVersion() {
  const commit =
    process.env.APP_COMMIT ||
    (() => {
      try {
        return execSync('git rev-parse --short HEAD', { stdio: 'pipe' }).toString().trim()
      } catch {
        return 'unknown'
      }
    })()
  return {
    version: process.env.APP_VERSION || 'dev',
    commit,
    buildTime: new Date().toISOString(),
  }
}

// 构建期注入：dist/version.json（nginx /version 端点返回）+ index.html <meta>
function buildVersionPlugin(): Plugin {
  const info = resolveBuildVersion()
  return {
    name: 'build-version',
    apply: 'build',
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'version.json',
        source: JSON.stringify(info, null, 2),
      })
    },
    transformIndexHtml() {
      return [
        {
          tag: 'meta',
          attrs: { name: 'app-version', content: `${info.version}+${info.commit}` },
          injectTo: 'head',
        },
      ]
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const useMock = env.VITE_USE_MOCK === 'true'
  const apiProxyTarget: string =
    env.LAIRWEB_API_PROXY_TARGET || env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'
  // 真实后端模式：/api 转发到后端；mock 模式不配 proxy（mock 插件优先拦截）
  const proxyTargets: Record<string, string> = useMock ? {} : { '/api': apiProxyTarget }

  return {
    resolve: {
      alias: { '@': new URL('./src', import.meta.url).pathname },
    },
    plugins: [
      vue(),
      tailwindcss(),
      buildVersionPlugin(),
      // 仅 mock 模式挂载：拦截 /api 请求到内存 mock 层（lairweb/mock/）
      ...(useMock
        ? [
            mockDevServerPlugin({
              prefix: ['/api'],
              include: ['**/*.mock.{js,ts}'],
            }),
          ]
        : []),
    ],
    server: {
      proxy: proxyTargets,
    },
  }
})
