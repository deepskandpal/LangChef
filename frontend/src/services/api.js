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
    
    // More detailed token debugging
    console.log('%c TOKEN DEBUG IN REQUEST INTERCEPTOR', 'background: darkblue; color: white; font-size: 12px', {
      url: config.url,
      method: config.method,
      hasToken: !!token,
      tokenLength: token ? token.length : 0,
      tokenStart: token ? token.substring(0, 10) + '...' : 'No token',
      tokenEnd: token ? '...' + token.substring(token.length - 10) : 'No token',
      isJWT: token && token.split('.').length === 3,
      previousAuthHeader: config.headers['Authorization'] || 'None'
    });
    
    if (token) {
      // Ensure token has correct format
      const formattedToken = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
      config.headers['Authorization'] = formattedToken;
      console.log('%c AUTH HEADER SET', 'background: green; color: white; font-size: 12px', {
        headerValue: formattedToken.substring(0, 15) + '...',
        url: config.url
      });
    } else {
      console.log('%c NO AUTH TOKEN AVAILABLE', 'background: red; color: white; font-size: 12px', {
        url: config.url
      });
    }
    
    // Enhanced debugging for chat-related API calls
    if (config.url && config.url.includes('/api/chats')) {
      console.log('%c 🔍 CHAT API REQUEST 🔍', 'background: purple; color: white; font-size: 14px', {
        method: config.method.toUpperCase(),
        url: config.url,
        headers: config.headers,
        data: config.data ? JSON.stringify(config.data) : null,
        timestamp: new Date().toISOString()
      });
      
      // Add a DOM marker we can check
      document.body.setAttribute('data-api-request-url', config.url);
      document.body.setAttribute('data-api-request-time', new Date().toISOString());
    } else {
      console.log('API Request:', config.method.toUpperCase(), config.url);
    }
    
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
    // Enhanced debugging for chat-related API calls
    if (response.config.url && response.config.url.includes('/api/chats')) {
      console.log('%c 🔍 CHAT API RESPONSE SUCCESS 🔍', 'background: green; color: white; font-size: 14px', {
        status: response.status,
        statusText: response.statusText,
        url: response.config.url,
        data: response.data,
        timestamp: new Date().toISOString()
      });
      
      // Add DOM marker for successful response
      document.body.setAttribute('data-api-response-status', response.status);
      document.body.setAttribute('data-api-response-time', new Date().toISOString());
    } else {
      console.log('API Response:', response.status, response.config.url);
    }
    return response;
  },
  (error) => {
    // Enhanced debugging for chat-related API calls
    if (error.config && error.config.url && error.config.url.includes('/api/chats')) {
      console.error('%c 🔍 CHAT API RESPONSE ERROR 🔍', 'background: red; color: white; font-size: 14px', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        url: error.config?.url,
        data: error.response?.data,
        message: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString(),
        originalRequest: {
          method: error.config?.method?.toUpperCase(),
          url: error.config?.url,
          headers: error.config?.headers,
          data: error.config?.data ? JSON.stringify(error.config.data) : null
        }
      });
      
      // Add DOM marker for error response
      document.body.setAttribute('data-api-error-status', error.response?.status || 'unknown');
      document.body.setAttribute('data-api-error-message', error.message || 'unknown error');
      document.body.setAttribute('data-api-error-time', new Date().toISOString());
    } else {
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