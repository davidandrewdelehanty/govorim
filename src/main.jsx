import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";

// No auth provider wraps the app any more. The site is public: reading,
// audio, definitions and exercises all work signed out. An optional account
// (see the sign-in panel in App.jsx and lib/auth.js on the server) only adds
// cross-device vocabulary, and admin access for ADMIN_EMAIL.

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
