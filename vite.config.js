import { defineConfig } from 'vite'

// GitHub Pages serves the project at /BlackBird/; dev stays at /.
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/BlackBird/' : '/',
  server: { host: true },
  build: { chunkSizeWarningLimit: 1200 },
}))
