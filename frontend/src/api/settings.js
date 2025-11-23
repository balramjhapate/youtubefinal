import apiClient from './client';

export const settingsApi = {
  // Get AI settings
  getAISettings: async () => {
    const response = await apiClient.get('/ai-settings/');
    return response.data;
  },

  // Save AI settings
  saveAISettings: async (provider, apiKey) => {
    const response = await apiClient.post('/ai-settings/', {
      provider,
      api_key: apiKey,
    });
    return response.data;
  },

  // Get dashboard stats
  getDashboardStats: async () => {
    const response = await apiClient.get('/dashboard/stats/');
    return response.data;
  },
};

export default settingsApi;
