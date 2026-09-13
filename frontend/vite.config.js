import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxies API calls to the FastAPI backend during development so the
// browser never has to worry about CORS. Change the target if your
// backend runs somewhere other than localhost:8001.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      '/users': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8001',
      '^/login/': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8001',
      '/books': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8001',
      '/borrow': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8001',
      '/library': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8001',
      '/agent': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8001'
    }
  }
})
