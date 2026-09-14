import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      '/api': 'http://127.0.0.1:8766',
      '/health': 'http://127.0.0.1:8766',
      '/ready': 'http://127.0.0.1:8766',
    },
  },
})

