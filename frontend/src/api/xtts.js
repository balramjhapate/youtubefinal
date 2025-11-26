import apiClient from './client';

export const xttsApi = {
    async generate(formData) {
        const response = await apiClient.post('/xtts/generate/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    async getLanguages() {
        const response = await apiClient.get('/xtts/languages/');
        return response.data;
    },

    async getVoices() {
        const response = await apiClient.get('/xtts/voices/');
        return response.data;
    },

    async saveVoice(formData) {
        const response = await apiClient.post('/xtts/voices/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    async deleteVoice(voiceId) {
        const response = await apiClient.delete(`/xtts/voices/${voiceId}/`);
        return response.data;
    },
};

export default xttsApi;
