import axios from 'axios';

// Create axios instance with base URL
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Prompts API
export const promptsApi = {
  getAll: (params) => api.get('/prompts', { params }),
  getById: (id) => api.get(`/prompts/${id}`),
  create: (data) => api.post('/prompts', data),
  update: (id, data) => api.put(`/prompts/${id}`, data),
  delete: (id) => api.delete(`/prompts/${id}`),
  getVersions: (id) => api.get(`/prompts/${id}/versions`),
};

// Datasets API
export const datasetsApi = {
  getAll: (params) => api.get('/datasets', { params }),
  getById: (id) => api.get(`/datasets/${id}`),
  create: (data) => api.post('/datasets', data),
  update: (id, data) => api.put(`/datasets/${id}`, data),
  delete: (id) => api.delete(`/datasets/${id}`),
  getItems: (id, params) => api.get(`/datasets/${id}/items`, { params }),
  createItem: (id, data) => api.post(`/datasets/${id}/items`, data),
  upload: (data) => api.post('/datasets/upload', data),
};

// Experiments API
export const experimentsApi = {
  getAll: (params) => api.get('/experiments', { params }),
  getById: (id) => api.get(`/experiments/${id}`),
  create: (data) => api.post('/experiments', data),
  update: (id, data) => api.put(`/experiments/${id}`, data),
  delete: (id) => api.delete(`/experiments/${id}`),
  getResults: (id, params) => api.get(`/experiments/${id}/results`, { params }),
  getMetrics: (id) => api.get(`/experiments/${id}/metrics`),
  run: (id) => api.post(`/experiments/${id}/run`),
};

// Traces API
export const tracesApi = {
  getAll: (params) => api.get('/traces', { params }),
  getById: (id) => api.get(`/traces/${id}`),
  create: (data) => api.post('/traces', data),
  update: (id, data) => api.put(`/traces/${id}`, data),
  delete: (id) => api.delete(`/traces/${id}`),
  getSpans: (id, params) => api.get(`/traces/${id}/spans`, { params }),
  createSpan: (id, data) => api.post(`/traces/${id}/spans`, data),
  updateSpan: (traceId, spanId, data) => api.put(`/traces/${traceId}/spans/${spanId}`, data),
  complete: (id) => api.post(`/traces/${id}/complete`),
};

// Metrics API
export const metricsApi = {
  getExperimentSummary: (id) => api.get(`/metrics/experiments/${id}/summary`),
  compareExperiments: (ids) => api.get('/metrics/experiments/compare', { params: { experiment_ids: ids } }),
  getDashboard: () => api.get('/metrics/dashboard'),
};

// Playground API
export const playgroundApi = {
  generate: (data) => api.post('/playground/generate', data),
};

export default {
  prompts: promptsApi,
  datasets: datasetsApi,
  experiments: experimentsApi,
  traces: tracesApi,
  metrics: metricsApi,
  playground: playgroundApi,
}; 