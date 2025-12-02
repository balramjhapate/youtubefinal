import axios from 'axios';

// Use environment variable or default to proxy
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout for regular API calls (reduced from 3 minutes)
});

// Create a separate instance for long-running operations (like synthesis)
export const apiClientLongTimeout = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 180000, // 3 minute timeout for voice synthesis operations
});

// Add same interceptors to long timeout client
apiClientLongTimeout.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url} (long timeout)`);
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

apiClientLongTimeout.interceptors.response.use(
  (response) => {
    console.log(`[API] Response ${response.status}:`, response.config.url);
    return response;
  },
  (error) => {
    console.error('[API] Response error:', error);

    // Handle network errors
    if (!error.response) {
      console.error('[API] Network error - Django server may not be running');
      const networkError = new Error('Cannot connect to server. Make sure Django is running on port 8000.');
      networkError.isNetworkError = true;
      return Promise.reject(networkError);
    }

    // Handle HTTP errors
    const { status, data } = error.response;

    if (status === 401) {
      console.error('Unauthorized');
    } else if (status === 404) {
      console.error('Resource not found');
    } else if (status === 503) {
      console.error('Service unavailable');
    } else if (status >= 500) {
      console.error('Server error');
    }

    // Preserve error structure for proper handling
    const apiError = new Error(data?.error || data?.detail || error.message || 'An error occurred');
    apiError.response = error.response;
    apiError.status = status;
    apiError.data = data;
    
    return Promise.reject(apiError);
  }
);

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API] Response ${response.status}:`, response.config.url);
    return response;
  },
  (error) => {
    console.error('[API] Response error:', error);

    // Handle network errors (proxy not working, server down)
    if (!error.response) {
      console.error('[API] Network error - Django server may not be running');
      const networkError = new Error('Cannot connect to server. Make sure Django is running on port 8000.');
      networkError.isNetworkError = true;
      return Promise.reject(networkError);
    }

    // Handle HTTP errors
    const { status, data } = error.response;

    if (status === 401) {
      console.error('Unauthorized');
    } else if (status === 404) {
      console.error('Resource not found');
    } else if (status === 503) {
      console.error('Service unavailable');
    } else if (status >= 500) {
      console.error('Server error');
    }

    // Preserve error structure for proper handling
    const apiError = new Error(data?.error || data?.detail || error.message || 'An error occurred');
    apiError.response = error.response;
    apiError.status = status;
    apiError.data = data;
    
    return Promise.reject(apiError);
  }
);

export default apiClient;
