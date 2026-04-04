import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    open: false,
    proxy: {
      '/v1/auth':      { target: 'http://localhost:8000', changeOrigin: true },
      '/v1/tenants':   { target: 'http://localhost:8000', changeOrigin: true },
      '/v1/infer':     { target: 'http://localhost:8000', changeOrigin: true },
      '/v1/workflows': { target: 'http://localhost:8000', changeOrigin: true },
      '/v1/ingestion': { target: 'http://localhost:8001', changeOrigin: true },
      '/v1/usage':     { target: 'http://localhost:8002', changeOrigin: true },
    },
  },
  build: { outDir: 'dist' },
});
