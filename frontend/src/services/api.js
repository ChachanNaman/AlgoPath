import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("algopath_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem("algopath_token");
      localStorage.removeItem("algopath_user");
      window.location.href = "/";
    }
    return Promise.reject(error);
  },
);

export default api;

// Quick test (manual):
// - Start backend with `python run.py`
// - In browser devtools console, check:
//   await api.get("/api/auth/me") with Authorization header set

