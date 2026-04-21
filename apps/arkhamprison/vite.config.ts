import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    open: false,
    proxy: {
      "/v1": {
        target: import.meta.env?.VITE_ARKHAM_URL ?? "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },
  build: { outDir: "dist" },
});
