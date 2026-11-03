import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/",
  server: {
    host: process.env.VITE_HOST || "127.0.0.1",
    port: Number(process.env.VITE_PORT) || 5188,
    proxy: {
      "/api": process.env.VITE_API_TARGET || "http://127.0.0.1:8788",
      "/tracker.js": process.env.VITE_API_TARGET || "http://127.0.0.1:8788",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    chunkSizeWarningLimit: 3000,
  },
});
