import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Use a dev server port unlikely to clash and allow any host (for container use)
export default defineConfig({
  plugins: [react()],
  base: '/ui/',
  server: {
    host: true,
    port: 52893,
    strictPort: true,
    cors: true,
    hmr: {
      clientPort: 52893
    }
  },
  preview: {
    port: 52893,
    strictPort: true
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Separate large charting library (used in RecordingModal)
          'vendor-charts': ['echarts', 'echarts-for-react'],
          // Separate documentation libraries (used in DocsViewer)
          'vendor-docs': ['react-markdown', 'remark-gfm', 'swagger-ui-react'],
          // Core React libraries
          'vendor-react': ['react', 'react-dom'],
          // Axios for API calls
          'vendor-axios': ['axios']
        }
      }
    },
    // Slightly increase threshold since vendor chunks may be 500-800KB
    chunkSizeWarningLimit: 600
  }
})
