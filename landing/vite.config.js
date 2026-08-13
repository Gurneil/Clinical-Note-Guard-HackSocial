import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(process.cwd(), "src"),
    },
  },
  build: {
    // The bundle is dominated by the committed benchmark (~164kB of JSON).
    // Splitting it out keeps app-code changes from busting its cache - it
    // only changes when the eval is re-run.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("src/data/cases.json")) return "benchmark-data";
          if (id.includes("node_modules/framer-motion")) return "motion";
          return undefined;
        },
      },
    },
  },
});
