import axios from 'axios';

// Use environment variable or default to proxy
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 180000, // 3 minute timeout for voice synthesis operations
});

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
      return Promise.reject('Cannot connect to server. Make sure Django is running on port 8000.');
    }

    // Handle HTTP errors
    const { status, data } = error.response;

    if (status === 401) {
      console.error('Unauthorized');
    } else if (status === 404) {
      console.error('Resource not found');
    } else if (status >= 500) {
      console.error('Server error');
    }

    // Return error message from server if available
    return Promise.reject(data?.error || data?.detail || error.message);
  }
);

export default apiClient;
