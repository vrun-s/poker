/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: [
    "http://192.168.1.19",
    "http://192.168.1.19:80",
    "http://192.168.1.19:3000",
  ],
};

module.exports = nextConfig;
