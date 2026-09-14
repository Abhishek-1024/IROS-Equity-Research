/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Proxy API calls to the FastAPI backend during local dev (agent/src/api).
    return [
      { source: "/api/:path*", destination: "http://localhost:8000/v1/:path*" },
    ];
  },
};

module.exports = nextConfig;
