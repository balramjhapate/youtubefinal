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

  // Get Cloudinary settings
  getCloudinarySettings: async () => {
    const response = await apiClient.get('/cloudinary-settings/');
    return response.data;
  },

  // Save Cloudinary settings
  saveCloudinarySettings: async (cloudName, apiKey, apiSecret, enabled) => {
    const response = await apiClient.post('/cloudinary-settings/', {
      cloud_name: cloudName,
      api_key: apiKey,
      api_secret: apiSecret,
      enabled: enabled,
    });
    return response.data;
  },

  // Get Google Sheets settings
  getGoogleSheetsSettings: async () => {
    const response = await apiClient.get('/google-sheets-settings/');
    return response.data;
  },

  // Save Google Sheets settings
  saveGoogleSheetsSettings: async (spreadsheetId, sheetName, credentialsJson, enabled) => {
    const response = await apiClient.post('/google-sheets-settings/', {
      spreadsheet_id: spreadsheetId,
      sheet_name: sheetName,
      credentials_json: credentialsJson,
      enabled: enabled,
    });
    return response.data;
  },

  // Get dashboard stats
  getDashboardStats: async () => {
    const response = await apiClient.get('/dashboard/stats/');
    return response.data;
  },

  // Test Google Sheets configuration
  testGoogleSheets: async () => {
    const response = await apiClient.get('/test/google-sheets/');
    return response.data;
  },
};

export default settingsApi;
