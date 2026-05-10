import React from "react";
import ReactDOM from "react-dom/client";
import { ClerkProvider } from "@clerk/clerk-react";
import App from "./App.jsx";

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

const root = ReactDOM.createRoot(document.getElementById("root"));

if (!PUBLISHABLE_KEY) {
  // Friendly setup screen if Clerk env var is missing — clearer than a cryptic crash.
  root.render(
    <div style={{
      minHeight: "100vh", background: "#1a1611", color: "#d2c5af",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: 32, fontFamily: "'Crimson Pro', serif",
    }}>
      <div style={{ maxWidth: 540, textAlign: "center" }}>
        <div style={{ fontSize: 56 }}>🔐</div>
        <h1 style={{ fontFamily: "'Playfair Display', serif", color: "#c8a276", fontSize: 36, margin: "16px 0 8px" }}>
          Setup Required
        </h1>
        <p style={{ fontSize: 16, lineHeight: 1.6, color: "rgba(210,197,175,.75)" }}>
          Clerk authentication is not configured. Add{" "}
          <code style={{ background: "rgba(200,162,118,.12)", padding: "2px 8px", borderRadius: 6, color: "#c8a276" }}>
            VITE_CLERK_PUBLISHABLE_KEY
          </code>{" "}
          to your Vercel environment variables, then redeploy. See README for full setup steps.
        </p>
      </div>
    </div>
  );
} else {
  root.render(
    <React.StrictMode>
      <ClerkProvider
        publishableKey={PUBLISHABLE_KEY}
        appearance={{
          variables: {
            colorPrimary: "#c8a276",
            colorBackground: "#1f1c16",
            colorInputBackground: "#23201a",
            colorInputText: "#d2c5af",
            colorText: "#d2c5af",
            colorTextSecondary: "rgba(210,197,175,.6)",
            colorNeutral: "#d2c5af",
            colorDanger: "#9d4630",
            colorSuccess: "#5a8556",
            colorWarning: "#c8a276",
            fontFamily: "'Crimson Pro', serif",
            borderRadius: "10px",
          },
          elements: {
            card: { backgroundColor: "#1f1c16", border: "1px solid rgba(210,197,175,.14)" },
            headerTitle: { fontFamily: "'Playfair Display', serif", color: "#c8a276" },
            socialButtonsBlockButton: {
              backgroundColor: "#23201a",
              border: "1px solid rgba(210,197,175,.18)",
              color: "#d2c5af",
            },
            formButtonPrimary: {
              backgroundColor: "#9d4630",
              backgroundImage: "linear-gradient(135deg,#9d4630,#82362a)",
            },
          },
        }}
      >
        <App />
      </ClerkProvider>
    </React.StrictMode>
  );
}
