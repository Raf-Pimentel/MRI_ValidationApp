import { defineConfig } from 'vite'

// The backend has no CORS; in development the browser talks to Vite, which forwards /api to it.
export default defineConfig({
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
