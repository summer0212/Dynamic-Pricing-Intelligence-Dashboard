const API_BASE = "http://localhost:8000";

export async function apiCall(endpoint: string, options: any = {}) {
  const token = localStorage.getItem("token");
  
  const headers: any = {
    "Content-Type": "application/json",
    ...options.headers,
  };
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Something went wrong");
  }
  
  return response.json();
}

// Auth
export async function signup(data: { email: string; password: string; name: string; org_name?: string; invite_code?: string }) {
  return apiCall("/api/auth/signup", { method: "POST", body: JSON.stringify(data) });
}

export async function login(data: { email: string; password: string }) {
  return apiCall("/api/auth/login", { method: "POST", body: JSON.stringify(data) });
}

// Products
export async function getProducts() {
  return apiCall("/api/products");
}

export async function createProduct(data: any) {
  return apiCall("/api/products", { method: "POST", body: JSON.stringify(data) });
}

export async function deleteProduct(id: string) {
  return apiCall(`/api/products/${id}`, { method: "DELETE" });
}

export async function scrapeCompetitors(productId: string) {
  return apiCall(`/api/products/${productId}/scrape-competitors`, {
    method: "POST"
  });
}

// Recommendations
export async function getRecommendations(status?: string) {
  const query = status ? `?status=${status}` : "";
  return apiCall(`/api/recommendations${query}`);
}

export async function generateRecommendations(productId?: string) {
  const body = productId ? { product_id: productId } : {};
  return apiCall("/api/recommendations/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function reviewRecommendation(
  id: string,
  data: { status: string; review_note?: string }
) {
  return apiCall(`/api/recommendations/${id}/review`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
