import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";

// Vercel Web Analytics is loaded by a plain script tag in index.html, NOT by
// the @vercel/analytics package. The bundled component broke a deploy: Vercel
// restored a cached node_modules, npm reported the tree "up to date" and
// installed nothing, so the freshly added package was absent on the build
// machine and Rollup could not resolve it — even though package.json and the
// lockfile both listed it. The script tag has no bundler step to fail, and
// Vercel serves /_vercel/insights/script.js on every deployment that has
// Analytics switched on.

// No auth provider wraps the app any more. The site is public: reading,
// audio, definitions and exercises all work signed out. An optional account
// (see the sign-in panel in App.jsx and lib/auth.js on the server) only adds
// cross-device vocabulary, and admin access for ADMIN_EMAIL.

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
