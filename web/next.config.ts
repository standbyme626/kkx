import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow reverse-proxy/dev access from public IP and localhost-style hosts.
  allowedDevOrigins: ["127.0.0.1", "47.115.59.85"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
