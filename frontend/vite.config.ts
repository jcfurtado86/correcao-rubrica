import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// No Docker Compose o alvo do proxy é http://backend:8000 (variável de ambiente).
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8810";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5183,
    proxy: {
      "/api": { target: apiProxyTarget, changeOrigin: true },
      "/admin": { target: apiProxyTarget, changeOrigin: true },
      "/static": { target: apiProxyTarget, changeOrigin: true },
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
