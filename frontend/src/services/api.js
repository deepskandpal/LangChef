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
      // Ensure token has correct format
      const formattedToken = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
      config.headers['Authorization'] = formattedToken;
    }
    
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (process.env.NODE_ENV === 'development') {
      console.error('API Response Error:', 
        error.response?.status, 
        error.config?.url, 
        error.message
      );
    }
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
  getAll: (params) => api.get('/api/prompts', { params }),
  getById: (id) => api.get(`/api/prompts/${id}`),
  create: (data) => api.post('/api/prompts', data),
  update: (id, data) => api.put(`/api/prompts/${id}`, data),
  delete: (id) => api.delete(`/api/prompts/${id}`),
  getVersions: (id) => api.get(`/api/prompts/${id}/versions`),
};

// Datasets API
export const datasetsApi = {
  getAll: (params) => api.get('/api/datasets', { params }),
  getById: (id) => api.get(`/api/datasets/${id}`),
  create: (data) => api.post('/api/datasets', data),
  update: (id, data) => api.put(`/api/datasets/${id}`, data),
  delete: (id) => api.delete(`/api/datasets/${id}`),
  getItems: (id, params) => api.get(`/api/datasets/${id}/items`, { params }),
  createItem: (id, data) => api.post(`/api/datasets/${id}/items`, data),
  deleteItem: (id, itemId) => api.delete(`/api/datasets/${id}/items/${itemId}`),
  getExperiments: (id, params) => api.get(`/api/datasets/${id}/experiments`, { params }),
  upload: (formData) => {
    return api.post('/api/datasets/upload/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  uploadCSV: (formData) => {
    return api.post('/api/datasets/upload/csv', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  export: (id) => api.get(`/api/datasets/${id}/export`, { 
    responseType: 'blob' 
  }),
  runExperiment: (id, data) => api.post(`/api/datasets/${id}/run`, data),
  getVersions: (id) => api.get(`/api/datasets/${id}/versions`),
};

// Experiments API
export const experimentsApi = {
  getAll: (params) => api.get('/api/experiments', { params }),
  getById: (id) => api.get(`/api/experiments/${id}`),
  create: (data) => api.post('/api/experiments', data),
  update: (id, data) => api.put(`/api/experiments/${id}`, data),
  delete: (id) => api.delete(`/api/experiments/${id}`),
  getResults: (id, params) => api.get(`/api/experiments/${id}/results`, { params }),
  getRuns: (id, params) => api.get(`/api/experiments/${id}/runs`, { params }),
  getItemResults: (id, itemId) => api.get(`/api/experiments/${id}/items/${itemId}/results`),
  compareTo: (id, otherExperimentId) => api.get(`/api/experiments/${id}/compare/${otherExperimentId}`),
  getMetrics: (id) => api.get(`/api/experiments/${id}/metrics`),
  run: (id, data) => api.post(`/api/experiments/${id}/run`, data),
  abort: (id) => api.post(`/api/experiments/${id}/abort`),
  export: (id) => api.get(`/api/experiments/${id}/export`, { 
    responseType: 'blob' 
  }),
};

// Traces API
export const tracesApi = {
  getAll: (params) => api.get('/api/traces', { params }),
  getById: (id) => api.get(`/api/traces/${id}`),
  create: (data) => api.post('/api/traces', data),
  update: (id, data) => api.put(`/api/traces/${id}`, data),
  delete: (id) => api.delete(`/api/traces/${id}`),
  getSpans: (id, params) => api.get(`/api/traces/${id}/spans`, { params }),
  createSpan: (id, data) => api.post(`/api/traces/${id}/spans`, data),
  updateSpan: (traceId, spanId, data) => api.put(`/api/traces/${traceId}/spans/${spanId}`, data),
  complete: (id) => api.post(`/api/traces/${id}/complete`),
};

// Metrics API
export const metricsApi = {
  getExperimentSummary: (id) => api.get(`/api/metrics/experiments/${id}/summary`),
  compareExperiments: (ids) => api.get('/api/metrics/experiments/compare', { params: { experiment_ids: ids } }),
  getDashboard: () => api.get('/api/metrics/dashboard'),
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