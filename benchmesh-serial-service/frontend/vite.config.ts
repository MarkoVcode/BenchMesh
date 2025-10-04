import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Use a dev server port unlikely to clash and allow any host (for container use)
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 52892,
    strictPort: true,
    cors: true,
    hmr: {
      clientPort: 52892
    }
  },
  preview: {
    port: 52892,
    strictPort: true
  }
})
