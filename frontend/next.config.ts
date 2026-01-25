import type { NextConfig } from "next";
import fs from "fs";
import yaml from "js-yaml";

interface AppConfig {
  backend: {
    host: string;
    port: number;
  };
}

const config = yaml.load(fs.readFileSync('../config.yml', 'utf8')) as AppConfig;
const backendUrl = `${config.backend.host}:${config.backend.port}`;

const nextConfig: NextConfig = {
  /* config options here */
  env: {
    NEXT_PUBLIC_BACKEND_URL: backendUrl,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'ddragon.leagueoflegends.com',
      },
      {
        protocol: 'https',
        hostname: 'raw.communitydragon.org',
      },
    ],
  },
};

export default nextConfig;