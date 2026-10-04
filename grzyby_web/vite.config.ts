import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3210,
        strictPort: true,
        // Same contract as nginx in the image: the browser only ever talks to this origin,
        // and /api is stripped before the request reaches the server.
        proxy: {
            "/api": {
                // The end-to-end tests run their own server next to yours (just e2e).
                target: process.env["API_PROXY_TARGET"] ?? "http://localhost:6210",
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, ""),
            },
        },
    },
});
