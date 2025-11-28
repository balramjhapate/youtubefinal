import apiClient from './client';

export const videosApi = {
  // Get all videos
  getAll: async (params = {}) => {
    const response = await apiClient.get('/videos/', { params });
    return response.data;
  },

  // Get single video
  getById: async (id) => {
    const response = await apiClient.get(`/videos/${id}/`);
    return response.data;
  },

  // Extract video from URL
  extract: async (url) => {
    const response = await apiClient.post('/videos/extract/', { url });
    return response.data;
  },

  // Upload local video file
  uploadFile: async (formData) => {
    const response = await apiClient.post('/videos/extract/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Download video to local storage
  download: async (id) => {
    const response = await apiClient.post(`/videos/${id}/download/`);
    return response.data;
  },

  // Start transcription
  transcribe: async (id, options = {}) => {
    const response = await apiClient.post(`/videos/${id}/transcribe/`, options);
    return response.data;
  },

  // Get transcription status
  getTranscriptionStatus: async (id) => {
    const response = await apiClient.get(`/videos/${id}/transcription_status/`);
    return response.data;
  },

  // Process with AI
  processAI: async (id) => {
    const response = await apiClient.post(`/videos/${id}/process_ai/`);
    return response.data;
  },

  // Generate audio prompt
  generateAudioPrompt: async (id) => {
    const response = await apiClient.post(`/videos/${id}/generate_audio_prompt/`);
    return response.data;
  },

  // Synthesize audio (uses Google TTS, profileId is optional)
  synthesize: async (id, profileId = null, text = null) => {
    const payload = {};
    if (profileId) payload.profile_id = profileId;
    if (text) payload.text = text;
    const response = await apiClient.post(`/videos/${id}/synthesize/`, payload);
    return response.data;
  },

  // Update voice profile for video
  updateVoiceProfile: async (id, profileId) => {
    const response = await apiClient.patch(`/videos/${id}/`, {
      voice_profile: profileId,
    });
    return response.data;
  },

  // Manually trigger Cloudinary upload and Google Sheets sync
  uploadAndSync: async (id) => {
    const response = await apiClient.post(`/videos/${id}/upload_and_sync/`);
    return response.data;
  },

  // Delete video
  delete: async (id) => {
    const response = await apiClient.delete(`/videos/${id}/delete/`);
    return response.data;
  },

  // Review video
  review: async (id, reviewStatus, reviewNotes = '') => {
    const response = await apiClient.post(`/videos/${id}/review/`, {
      review_status: reviewStatus,
      review_notes: reviewNotes,
    });
    return response.data;
  },

  // Reprocess video
  reprocess: async (id) => {
    const response = await apiClient.post(`/videos/${id}/reprocess/`);
    return response.data;
  },

  // Reset stuck transcription
  resetTranscription: async (id) => {
    const response = await apiClient.post(`/videos/${id}/reset_transcription/`);
    return response.data;
  },

  // Bulk actions
  bulkDownload: async (videoIds) => {
    const response = await apiClient.post('/bulk/download/', { video_ids: videoIds });
    return response.data;
  },

  bulkTranscribe: async (videoIds) => {
    const response = await apiClient.post('/bulk/transcribe/', { video_ids: videoIds });
    return response.data;
  },

  bulkProcessAI: async (videoIds) => {
    const response = await apiClient.post('/bulk/process-ai/', { video_ids: videoIds });
    return response.data;
  },

  bulkGeneratePrompts: async (videoIds) => {
    const response = await apiClient.post('/bulk/generate-prompts/', { video_ids: videoIds });
    return response.data;
  },

  bulkDelete: async (videoIds) => {
    const response = await apiClient.post('/bulk/delete/', { video_ids: videoIds });
    return response.data;
  },
};

export default videosApi;
