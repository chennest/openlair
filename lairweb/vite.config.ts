import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { mockDevServerPlugin } from 'vite-plugin-mock-dev-server'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const useMock = env.VITE_USE_MOCK === 'true'
  const apiProxyTarget: string =
    env.LAIRWEB_API_PROXY_TARGET || env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
  // 真实后端模式：/api 转发到后端；mock 模式不配 proxy（mock 插件优先拦截）
  const proxyTargets: Record<string, string> = useMock ? {} : { '/api': apiProxyTarget }

  return {
    plugins: [
      vue(),
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
