/** @type {import('next').NextConfig} */
const nextConfig = {
  // react-leaflet v4's MapContainer isn't StrictMode-safe: dev-mode's
  // double-invoked effects mount it twice, and Leaflet throws ("Map
  // container is already initialized") trying to re-init a map on a
  // DOM node that already has one. Production builds don't double-
  // invoke effects, so this is a dev-only tradeoff — disabling it here
  // is the fix react-leaflet's own docs point to for this exact issue.
  reactStrictMode: false,
};

export default nextConfig;
