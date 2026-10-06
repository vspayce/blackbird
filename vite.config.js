import { defineConfig } from 'vite'

// Relative asset paths so the build works at any URL (GitHub Pages, a phone on the LAN, a subfolder).
export default defineConfig({
  base: './',
  server: { host: true },
  build: { chunkSizeWarningLimit: 1200 },
})
