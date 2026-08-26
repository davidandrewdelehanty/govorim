import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // One environment variable drives both sides. The server reads SITE_MODE
  // directly; the client can't, so it is inlined here at build time. Vercel
  // runs a separate build per project with that project's environment, so the
  // public deployment and the private one get different constants from the
  // same source tree.
  define: {
    __SITE_MODE__: JSON.stringify(process.env.SITE_MODE || "private"),
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});

