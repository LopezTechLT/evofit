import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/login': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/logout': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/register': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/register_gym': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/cliente': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/mi_perfil': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/dashboard': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/clients': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/fitness': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/pending_gyms': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      },
      '/gyms': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      }
    }
  }
})
