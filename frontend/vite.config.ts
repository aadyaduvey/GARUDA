import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const API = 'http://127.0.0.1:8010'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5174,
    strictPort: true,
    // The dashboard calls the API through this dev server (same origin), so it also works when
    // opened from another device (`pnpm start:lan`), where 127.0.0.1 would mean that device.
    proxy: { '/api': API, '/health': API, '/docs': API, '/openapi.json': API },
  },
})
