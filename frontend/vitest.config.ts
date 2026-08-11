import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
    exclude: ["**/node_modules/**", "**/.next/**"],
    // The default "forks" pool times out spawning worker processes in
    // this environment (Windows + a OneDrive-synced path with a space
    // in it) — "threads" avoids the extra process spawn entirely.
    pool: "threads",
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL(".", import.meta.url)),
    },
  },
});
