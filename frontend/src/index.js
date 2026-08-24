import React from "react";
import ReactDOM from "react-dom/client";
import axios from "axios";
import "@/index.css";
import App from "@/App";

// Ensure all API calls on live leamss.com domains dynamically route to https://api.leamss.com
axios.interceptors.request.use((config) => {
  if (typeof window !== "undefined" && window.location.hostname.includes("leamss.com")) {
    if (config.url && config.url.includes("localhost:8001")) {
      config.url = config.url.replace(/http:\/\/localhost:8001/g, "https://api.leamss.com");
    } else if (config.baseURL && config.baseURL.includes("localhost:8001")) {
      config.baseURL = config.baseURL.replace(/http:\/\/localhost:8001/g, "https://api.leamss.com");
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

