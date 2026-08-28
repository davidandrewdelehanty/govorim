import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
// Vercel Web Analytics. This is a Vite SPA, so the entry point is
// @vercel/analytics/react — the dashboard's quick-start shows
// @vercel/analytics/next, which is for Next.js and would not resolve here.
// Each Vercel project collects its own numbers from the same component, so
// Говорим and Самовар report separately with no branching.
import { Analytics } from "@vercel/analytics/react";

// No auth provider wraps the app any more. The site is public: reading,
// audio, definitions and exercises all work signed out. An optional account
// (see the sign-in panel in App.jsx and lib/auth.js on the server) only adds
// cross-device vocabulary, and admin access for ADMIN_EMAIL.

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
    <Analytics />
  </React.StrictMode>
);
