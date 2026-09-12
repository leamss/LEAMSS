import React from "react";
import ReactDOM from "react-dom/client";
import axios from "axios";
import "@/index.css";
import App from "@/App";
import { initGlobalToastSanitizer } from "@/lib/apiErrors";

// Globally sanitize all Sonner toast calls against raw error objects/arrays
initGlobalToastSanitizer();

// Ensure all API calls dynamically route to https://api.leamss.com on live domains
axios.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const isLive = window.location.hostname.includes("leamss.com");
    const targetBase = isLive
      ? "https://api.leamss.com"
      : (window.location.origin.includes("localhost") ? "http://localhost:8001" : "https://api.leamss.com");

    if (config.url) {
      if (config.url.startsWith("undefined/")) {
        config.url = config.url.replace(/^undefined\//, `${targetBase}/`);
      } else if (config.url.startsWith("/undefined/")) {
        config.url = config.url.replace(/^\/undefined\//, `${targetBase}/`);
      } else if (config.url.includes("/undefined/api")) {
        config.url = config.url.replace(/.*\/undefined\/api/g, `${targetBase}/api`);
      } else if (isLive && config.url.startsWith("/api")) {
        config.url = `${targetBase}${config.url}`;
      } else if (isLive && config.url.includes("localhost:8001")) {
        config.url = config.url.replace(/http:\/\/localhost:8001/g, "https://api.leamss.com");
      }
    }
    if (config.baseURL) {
      if (config.baseURL.startsWith("undefined/")) {
        config.baseURL = config.baseURL.replace(/^undefined\//, `${targetBase}/`);
      } else if (config.baseURL.startsWith("/undefined/")) {
        config.baseURL = config.baseURL.replace(/^\/undefined\//, `${targetBase}/`);
      } else if (isLive && config.baseURL.includes("localhost:8001")) {
        config.baseURL = config.baseURL.replace(/http:\/\/localhost:8001/g, "https://api.leamss.com");
      }
    }
  }
  return config;
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

