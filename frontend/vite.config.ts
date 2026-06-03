/// <reference types="node" />
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Vite dev-server config.
//
// `/api` is proxied to the API service running on port 8003 so the
// browser doesn't hit CORS during development. The proxy strips the
// `/api` prefix so the API service sees `/sessions`, not `/api/sessions`.
//
// In production the build is served statically from CloudFront; the
// `/api` rewrite happens at the ALB layer there.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8003",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
