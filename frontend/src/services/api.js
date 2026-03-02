import axios from "axios";

/* =========================================================
   AXIOS BASE CONFIG
========================================================= */
const api = axios.create({
  baseURL: "http://localhost:8000/api/v1",
  timeout: 60000,  // 60s — biometric ops (InsightFace) can be slow on CPU
  headers: {
    "Content-Type": "application/json",
  },
});

/* =========================================================
   REQUEST INTERCEPTOR (AUTH TOKEN)
========================================================= */
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/* =========================================================
   RESPONSE INTERCEPTOR (401 HANDLING)
========================================================= */
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");

      if (!window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

/* =========================================================
   AUTH API
========================================================= */
export const authApi = {
  login: ({ username, password }) => {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);
    formData.append("grant_type", "password");

    return api.post("/admin/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },

  getCurrentUser: () => api.get("/admin/me"),

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    return Promise.resolve();
  },
};

/* =========================================================
   EMPLOYEE API
========================================================= */
export const employeeApi = {
  getAll: (params) => api.get("/employees", { params }),
  getById: (id) => api.get(`/employees/${id}`),
  create: (data) => api.post("/employees", data),
  update: (id, data) => api.put(`/employees/${id}`, data),
  delete: (id) => api.delete(`/employees/${id}`),

  /* -------- BIOMETRIC ENROLLMENT (USED BY FaceEnroll.jsx) -------- */
  registerBiometric: (employeeId, payload) =>
    api.post(`/employees/${employeeId}/biometrics`, payload),

  enrollFaceProfile: (employeeId, payload) =>
    api.post(`/employees/${employeeId}/enroll-face-profile`, payload),

  getBiometrics: (employeeId) =>
    api.get(`/employees/${employeeId}/biometrics`),
};

/* =========================================================
   BIOMETRIC VERIFY (ATTENDANCE)
========================================================= */
export const biometricApi = {
  verifyFace: (payload) =>
    api.post("/biometric/verify/face", payload),

  verifyFingerprint: (payload) =>
    api.post("/biometric/fingerprint/verify", payload),
};

/* =========================================================
   ATTENDANCE API
========================================================= */
export const attendanceApi = {
  getToday: () => api.get("/attendance/today"),

  getReport: (params) =>
    api.get("/attendance/report", { params }),

  getByEmployee: (employeeId, params) =>
    api.get(`/attendance/employee/${employeeId}`, { params }),
};

/* =========================================================
   DEVICE API
========================================================= */
export const deviceApi = {
  getAll: () => api.get("/devices"),
  register: (data) => api.post("/devices", data),
  getById: (id) => api.get(`/devices/${id}`),
  delete: (id) => api.delete(`/devices/${id}`),
  activate: (id) => api.post(`/devices/${id}/activate`),
  deactivate: (id) => api.post(`/devices/${id}/deactivate`),
  regenerateKey: (id) =>
    api.post(`/devices/${id}/regenerate-key`),
};

/* =========================================================
   DEFAULT EXPORT
========================================================= */
export default api;
