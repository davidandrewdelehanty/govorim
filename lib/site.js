// Branding, server side. One place decides what this deployment calls itself,
// so the two sites share a codebase without sharing a name.
//
// The client has its own copy of this in App.jsx, driven by the same SITE_MODE
// variable — it can't import from here because vite inlines the value at build
// time rather than reading the environment at runtime.

export function isPublicSite() {
  return process.env.SITE_MODE === "public";
}

export function siteName() {
  return isPublicSite() ? "Samovar" : "Govorim";
}
