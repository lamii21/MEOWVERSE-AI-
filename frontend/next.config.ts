import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Minimal production runtime (Phase 17): traces the actual set of
  // node_modules files each page needs and emits a self-contained
  // `.next/standalone/server.js`, instead of shipping the full
  // node_modules tree in the production Docker image.
  output: "standalone",
};

export default nextConfig;
