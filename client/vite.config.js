import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5123,
    proxy: {
      '/api': {
        target: 'http://localhost:8124',
        changeOrigin: true,
        // SSE needs this config – otherwise Vite buffers the response
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('Accept', 'text/event-stream');
          });
        },
      },
    },
  },
})
