/** @type {import('next').NextConfig} */
function normalizeProxyTarget(raw) {
  const value = (raw || "http://localhost:8000").trim().replace(/\/$/, "");
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return value;
  }
  return `http://${value}`;
}

const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    const apiProxyTarget = normalizeProxyTarget(process.env.API_PROXY_TARGET);
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiProxyTarget}/api/v1/:path*`,
      },
      {
        source: "/health",
        destination: `${apiProxyTarget}/health`,
      },
    ];
  },
};

module.exports = nextConfig;
