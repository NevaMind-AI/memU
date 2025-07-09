import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true,
    },
    hmr: {
      port: 5173,
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
  },
  optimizeDeps: {
    force: true,
  },
  define: {
    global: 'globalThis',
  },
})
