/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

if (process.env.DUBSIBHAI_CONTAINER_BUILD === "1") {
  nextConfig.output = "standalone";
  nextConfig.rewrites = async () => [
    { source: "/api/v1/:path*", destination: "http://api:8000/api/v1/:path*" },
    { source: "/media/:path*", destination: "http://api:8000/media/:path*" },
  ];
}

module.exports = nextConfig;
