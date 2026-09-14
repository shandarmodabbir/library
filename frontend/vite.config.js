import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxies API calls to the FastAPI backend during development so the
// browser never has to worry about CORS. Change the target if your
// backend runs somewhere other than localhost:8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/users': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
      '^/login/': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
      '/books': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
      '/borrow': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
      '/library': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
      '/agent': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000'
    }
  }
})
