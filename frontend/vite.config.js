import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiBase = env.VITE_API_BASE_URL || '/api/v1'
  if (!apiBase.startsWith('/') || apiBase.startsWith('//')) {
    throw new Error(
      'VITE_API_BASE_URL must be a same-origin path such as /api/v1. ' +
      'Set the backend host in the Vite proxy or the /api and /uploads Vercel rewrites.',
    )
  }

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
    },
    server: {
      port: Number(env.VITE_PORT) || 5173,
      // Requests to /api are proxied to FastAPI in development, so the browser
      // sees a same-origin call and CORS never comes into play locally.
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/uploads': {
          target: env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
