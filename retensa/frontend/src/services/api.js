const BASE = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
  } catch (error) {
    throw new Error("Unable to connect to RETENSA backend.");
  }
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (!response.ok) {
    const detail = body?.detail;
    const message = Array.isArray(detail) ? detail[0]?.msg : detail;
    throw new Error(message || `Request failed (${response.status})`);
  }
  return body;
}

export const getHealth = () => request("/api/health");
export const getDashboard = () => request("/api/dashboard");
export const getSchema = () => request("/api/schema");
export const getModelMetrics = () => request("/api/model-metrics");
export const getCustomers = (params = {}) => {
  const query = new URLSearchParams();
  if (params.limit) query.set("limit", String(params.limit));
  if (params.risk) query.set("risk", params.risk);
  const suffix = query.toString() ? `?${query}` : "";
  return request(`/api/customers${suffix}`);
};
export const getCustomerAnalysis = (id) => request(`/api/customers/${id}/analysis`);
export const getCustomerRecommendation = (id) => request(`/api/customers/${id}/recommendation`);
export const getCustomerActionCenter = (id) => request(`/api/customers/${id}/action-center`);
export const simulateWhatIf = (id, changes) =>
  request(`/api/customers/${id}/what-if`, {
    method: "POST",
    body: JSON.stringify({ changes }),
  });
export const simulateWhatIfFeatures = (features, changes) =>
  request("/api/what-if", {
    method: "POST",
    body: JSON.stringify({ features, changes }),
  });
export const analyzeNewCustomer = (customerData) =>
  request("/api/analyze-new-customer", {
    method: "POST",
    body: JSON.stringify(customerData),
  });
export const askAssistant = (message, customerIndex = null, features = null) =>
  request("/api/assistant", {
    method: "POST",
    body: JSON.stringify({
      message,
      customer_index: customerIndex == null || customerIndex === "" ? null : Number(customerIndex),
      features: features || null,
    }),
  });
