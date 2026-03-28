import type { NextConfig } from "next";
import fs from "fs";
import path from "path";
import yaml from "js-yaml";

interface AppConfig {
  backend?: {
    host?: string;
    port?: number;
  };
}

const configPathCandidates = [
  path.resolve(process.cwd(), "config.yml"),
  path.resolve(process.cwd(), "../config.yml"),
];
const configPath = configPathCandidates.find((candidate) => fs.existsSync(candidate));
const config = configPath
  ? (yaml.load(fs.readFileSync(configPath, "utf8")) as AppConfig)
  : null;
const backendUrl =
  process.env.NEXT_PUBLIC_BACKEND_URL ??
  (config?.backend?.host && config.backend.port
    ? `${config.backend.host}:${config.backend.port}`
    : "http://localhost:8000");

const nextConfig: NextConfig = {
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
