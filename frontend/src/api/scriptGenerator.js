import apiClient from './client';

export const scriptGeneratorApi = {
    generate: (data) => apiClient.post('/script-generator/generate/', data),
};
