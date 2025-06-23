import type { NextConfig } from 'next';

/** @type {NextConfig} */
const nextConfig: NextConfig = {
  reactStrictMode: true,
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },
  trailingSlash: false,
  poweredByHeader: false,
  compress: true,
  productionBrowserSourceMaps: true,
  output: 'standalone',
  outputFileTracingRoot: process.cwd(),
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3000',
  },
};

export default nextConfig;
