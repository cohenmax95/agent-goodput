import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  ...(process.env.AGENT_GOODPUT_STATIC_EXPORT === "1"
    ? {
        output: "export",
      }
    : {}),
};

export default nextConfig;
