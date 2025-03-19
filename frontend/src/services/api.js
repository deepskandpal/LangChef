import axios from 'axios';

// Create axios instance with base URL
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8001',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    console.log('API Request:', config.method.toUpperCase(), config.url, config.data, config.headers);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for debugging
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url, response.data);
    return response;
  },
  (error) => {
    console.error('API Response Error:', 
      error.response?.status, 
      error.response?.config?.url, 
      error.response?.data,
      error.message
    );
    return Promise.reject(error);
  }
);

// Models API
export const modelsApi = {
  getAvailable: () => api.get('/api/models/available'),
  runPlayground: (data) => api.post('/api/models/playground/run', data),
};

// Chats API
export const chatsApi = {
  getAll: (params) => api.get('/api/chats', { params }),
  getById: (id) => api.get(`/api/chats/${id}`),
  create: (data) => api.post('/api/chats', data),
  update: (id, data) => api.put(`/api/chats/${id}`, data),
  delete: (id) => api.delete(`/api/chats/${id}`),
  addMessage: (chatId, message) => api.post(`/api/chats/${chatId}/messages`, message),
};

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
  deleteItem: (id, itemId) => api.delete(`/datasets/${id}/items/${itemId}`),
  getExperiments: (id, params) => api.get(`/datasets/${id}/experiments`, { params }),
  upload: (formData) => {
    return api.post('/datasets/upload/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  uploadCSV: (formData) => {
    return api.post('/datasets/upload/csv', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  export: (id) => api.get(`/datasets/${id}/export`, { 
    responseType: 'blob' 
  }),
  runExperiment: (id, data) => api.post(`/datasets/${id}/run`, data),
  getVersions: (id) => api.get(`/datasets/${id}/versions`),
};

// Experiments API
export const experimentsApi = {
  getAll: (params) => api.get('/experiments', { params }),
  getById: (id) => api.get(`/experiments/${id}`),
  create: (data) => api.post('/experiments', data),
  update: (id, data) => api.put(`/experiments/${id}`, data),
  delete: (id) => api.delete(`/experiments/${id}`),
  getResults: (id, params) => api.get(`/experiments/${id}/results`, { params }),
  getRuns: (id, params) => api.get(`/experiments/${id}/runs`, { params }),
  getItemResults: (id, itemId) => api.get(`/experiments/${id}/items/${itemId}/results`),
  compareTo: (id, otherExperimentId) => api.get(`/experiments/${id}/compare/${otherExperimentId}`),
  getMetrics: (id) => api.get(`/experiments/${id}/metrics`),
  run: (id, data) => api.post(`/experiments/${id}/run`, data),
  abort: (id) => api.post(`/experiments/${id}/abort`),
  export: (id) => api.get(`/experiments/${id}/export`, { 
    responseType: 'blob' 
  }),
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

// Create combined API object
const apiServices = {
  prompts: promptsApi,
  datasets: datasetsApi,
  experiments: experimentsApi,
  traces: tracesApi,
  metrics: metricsApi,
  models: modelsApi,
  chats: chatsApi,
};

// Export the combined API object
export default apiServices;