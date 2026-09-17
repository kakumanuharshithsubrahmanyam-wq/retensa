import { useEffect, useState } from "react";
import { getCustomerAnalysis } from "../services/api";

export function useCustomerAnalysis(customerIndex) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (customerIndex == null || Number.isNaN(Number(customerIndex))) {
      setError("Invalid customer.");
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");
    getCustomerAnalysis(customerIndex)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Unable to load customer analysis.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [customerIndex]);

  return { data, loading, error };
}
