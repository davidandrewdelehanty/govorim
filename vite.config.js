import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";

// One stamp per build, computed here so the constant compiled into the bundle
// and the file served beside it can never disagree.
const BUILD_ID = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14) +
                 "-" + Math.random().toString(36).slice(2, 8);

// Writes the stamp where the running app can fetch it. Vercel serves dist/ at
// the site root, so this lands at /version.json.
function versionStamp() {
  return {
    name: "version-stamp",
    closeBundle() {
      const out = path.join("dist", "version.json");
      fs.mkdirSync("dist", { recursive: true });
      fs.writeFileSync(out, JSON.stringify({ build: BUILD_ID }) + "\n");
      console.log("version.json  " + BUILD_ID);
    },
  };
}

export default defineConfig({
  plugins: [react(), versionStamp()],
  // One environment variable drives both sides. The server reads SITE_MODE
  // directly; the client can't, so it is inlined here at build time. Vercel
  // runs a separate build per project with that project's environment, so the
  // public deployment and the private one get different constants from the
  // same source tree.
  define: {
    __SITE_MODE__: JSON.stringify(process.env.SITE_MODE || "private"),
    // Stamped once per build and inlined into the bundle. dist/version.json
    // below carries the SAME value, so the running page can tell whether a
    // newer build has been deployed since it loaded.
    __BUILD_ID__: JSON.stringify(BUILD_ID),
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});

