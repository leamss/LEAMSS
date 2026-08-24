import { useEffect, useState } from "react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL || "http://localhost:8001/api";

export default function AtlasCountryManager() {
  const [countries, setCountries] = useState([]);

  const loadCountries = async () => {
    try {
      const res = await axios.get(`${API}/atlas/admin/countries`);
      setCountries(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadCountries();
  }, []);

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6">
        Atlas Country Manager
      </h2>

      {countries.map((country) => (
        <div
          key={country.code}
          className="border rounded-lg p-4 mb-4"
        >
          <h3 className="text-xl font-semibold">
            {country.flag} {country.name}
          </h3>

          <p>
            <strong>Code:</strong> {country.code}
          </p>

          <p>
            <strong>Classification:</strong>{" "}
            {country.classification || "-"}
          </p>

          <p>
            <strong>Benchmark:</strong>{" "}
            {country.benchmark_label || "-"}
          </p>

          <p>
            <strong>Enabled:</strong>{" "}
            {country.enabled ? "Yes" : "No"}
          </p>
        </div>
      ))}
    </div>
  );
}