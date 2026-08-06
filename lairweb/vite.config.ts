import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { mockDevServerPlugin } from 'vite-plugin-mock-dev-server'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.LAIRWEB_API_PROXY_TARGET || env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

  return {
    plugins: [
      vue(),
      mockDevServerPlugin({
        prefix: ['/api'],
        include: ['**/*.mock.{js,ts}'],
      }),
    ],
    server: {
      proxy: {
        '/assistant': apiProxyTarget,
        '/health': apiProxyTarget,
        '/notes': apiProxyTarget,
      },
    },
  }
})
