import apiClient from './client';

export const voiceProfilesApi = {
  // Get all voice profiles
  getAll: async () => {
    const response = await apiClient.get('/voice-profiles/');
    return response.data;
  },

  // Get single voice profile
  getById: async (id) => {
    const response = await apiClient.get(`/voice-profiles/${id}/`);
    return response.data;
  },

  // Create voice profile
  create: async (formData) => {
    const response = await apiClient.post('/voice-profiles/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Delete voice profile
  delete: async (id) => {
    const response = await apiClient.delete(`/voice-profiles/${id}/`);
    return response.data;
  },
};

export default voiceProfilesApi;
