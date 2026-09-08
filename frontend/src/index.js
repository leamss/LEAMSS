import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";
import { initGlobalToastSanitizer } from "@/lib/apiErrors";

// Globally sanitize all Sonner toast calls against raw error objects/arrays
initGlobalToastSanitizer();

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

