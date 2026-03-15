import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,   // external access (e.g. Hugging Face Spaces)
    port: 7860,   // HF Spaces app_port; for local dev with backend on 8000, use port 5173 and target 8000
    proxy: {
      '/api': {
        target: 'http://localhost:7860',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
