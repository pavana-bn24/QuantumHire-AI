import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    // Default port only: pass --port <n> on the command line to override it,
    // and do not hard-fail when the default port is already taken (Vite then
    // falls back to the next free port instead of exiting).
    port: Number(process.env.PORT) || 5000,
    strictPort: false,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
    open: false,
  },
})
