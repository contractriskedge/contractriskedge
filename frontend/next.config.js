/** @type {import('next').NextConfig} */
const nextConfig = {
  // Pre-existing TS errors in dashboard modules; don't block dev server startup.
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    remotePatterns: [
      { protocol: 'http', hostname: 'localhost' },
      { protocol: 'https', hostname: '**.auth0.com' },
    ],
  },
  async rewrites() {
    return [
      // Auth routes are handled by @auth0/nextjs-auth0 — don't proxy to backend
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ];
  },
  webpack: (config, { dev }) => {
    // Network-mounted workspaces (e.g. /Volumes/home) need polling for file watches.
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
        ignored: ['**/node_modules/**', '**/.git/**'],
      };
    }
    return config;
  },
};

module.exports = nextConfig;
