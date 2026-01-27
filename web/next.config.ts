import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable React strict mode
  reactStrictMode: true,
  
  // Configure rewrites for API proxy in development
  // Exclude Next.js API routes: auth, sessions, feedback, user
  async rewrites() {
    return [
      {
        source: '/api/:path((?!auth|sessions|feedback|user).*)*',
        destination: process.env.NEXT_PUBLIC_API_URL 
          ? `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
          : 'http://localhost:8000/api/:path*',
      },
    ];
  },
  
  // Image domains for team logos
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'a.espncdn.com',
      },
      {
        protocol: 'https',
        hostname: 'assets.nhle.com',
      },
    ],
  },
};

export default nextConfig;

