import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// base: './' penting -- pywebview load index.html lewat file:// setelah di-build,
// path absolut '/assets/...' bakal 404 kalau tidak di-relative-kan.
export default defineConfig({
  base: './',
  plugins: [vue()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    strictPort: true,
  },
})
