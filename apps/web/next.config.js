/** @type {import('next').NextConfig} */
function normalizeProxyTarget(raw) {
  const value = (raw || "http://localhost:8000").trim().replace(/\/$/, "");
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return value;
  }
  return `http://${value}`;
}

const apiProxyTarget = normalizeProxyTarget(process.env.API_PROXY_TARGET);

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiProxyTarget}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
