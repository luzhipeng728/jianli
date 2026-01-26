import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())

  return {
    base: '/interview/',
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    server: {
      port: parseInt(env.VITE_PORT) || 5174,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: 'http://localhost:8002',
          changeOrigin: true
        },
        '/ws': {
          target: 'ws://localhost:8002',
          ws: true
        }
      }
    },
    preview: {
      port: parseInt(env.VITE_PORT) || 5174,
      host: '0.0.0.0',
      allowedHosts: ['resume.luzhipeng.com', 'resume-agent.finmall.com', 'localhost'],
      proxy: {
        '/api': {
          target: 'http://localhost:8002',
          changeOrigin: true
        },
        '/ws': {
          target: 'ws://localhost:8002',
          ws: true
        }
      }
    }
  }
})
