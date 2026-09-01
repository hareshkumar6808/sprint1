import type { NextConfig } from "next";

const apiOrigin = (process.env.FINSYNC_API_ORIGIN ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  outputFileTracingRoot: process.cwd(),
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${apiOrigin}/api/v1/:path*` },
      { source: "/health", destination: `${apiOrigin}/health` },
    ];
  },
};
export default nextConfig;
