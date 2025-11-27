document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('download-form');
    const urlInput = document.getElementById('url-input');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');
    const resultSection = document.getElementById('result-section');
    const videoPlayer = document.getElementById('video-player');
    const videoTitle = document.getElementById('video-title');
    const downloadLink = document.getElementById('download-link');
    const errorMessage = document.getElementById('error-message');
    // Sidebar elements
    const providerSelect = document.getElementById('provider-select');
    const apiKeyInput = document.getElementById('api-key');
    const saveSettingsBtn = document.getElementById('save-settings');
    const transcriptInput = document.getElementById('transcript-input');
    const generatePromptBtn = document.getElementById('generate-prompt');
    const generatedPromptPre = document.getElementById('generated-prompt');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();

        if (!url) return;

        // Reset UI
        setLoading(true);
        showError(null);
        resultSection.classList.add('hidden');
        videoPlayer.pause();
        videoPlayer.src = '';

        try {
            const response = await fetch('/api/extract', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch video');
            }

            // Success
            displayResult(data);

        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    });

    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        if (isLoading) {
            btnText.classList.add('hidden');
            loader.classList.remove('hidden');
        } else {
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
        }
    }

    function showError(msg) {
        if (msg) {
            errorMessage.textContent = msg;
            errorMessage.classList.remove('hidden');
        } else {
            errorMessage.classList.add('hidden');
        }
    }

    function displayResult(data) {
        videoPlayer.src = data.video_url;
        videoPlayer.poster = data.cover_url || '';
        videoTitle.textContent = data.title || 'Downloaded Video';
        downloadLink.href = data.video_url;
        // For cross-origin downloads, we might need a proxy, but let's try direct first
        downloadLink.setAttribute('download', `xhs_video_${Date.now()}.mp4`);

        resultSection.classList.remove('hidden');
    }

    // Event listeners for sidebar actions
    saveSettingsBtn.addEventListener('click', saveSettings);
    generatePromptBtn.addEventListener('click', () => {
        const transcript = transcriptInput.value.trim();
        if (transcript) {
            generatePrompt(transcript);
        } else {
            alert('Please enter a transcript');
        }
    });

    // Functions for settings persistence and prompt generation using API
    function fetchSettings() {
        fetch('/api/ai-settings/', { method: 'GET' })
            .then(r => r.json())
            .then(data => {
                if (data.provider) providerSelect.value = data.provider;
                if (data.api_key) apiKeyInput.value = data.api_key;
            })
            .catch(err => {
                console.error('Error fetching AI settings', err);
            });
    }

    function saveSettings() {
        const payload = {
            provider: providerSelect.value,
            api_key: apiKeyInput.value
        };
        fetch('/api/ai-settings/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then(r => r.json())
            .then(res => {
                alert('Settings saved');
            })
            .catch(err => {
                console.error('Error saving AI settings', err);
                alert('Failed to save settings');
            });
    }

    function generatePrompt(transcript) {
        // Retrieve current settings (could cache if needed)
        fetch('/api/ai-settings/', { method: 'GET' })
            .then(r => r.json())
            .then(settings => {
                if (!settings.provider || !settings.api_key) {
                    alert('Please configure provider and API key');
                    return;
                }
                // Placeholder API call – replace URL with actual endpoint
                return fetch('/api/generate-prompt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider: settings.provider, apiKey: settings.api_key, transcript })
                });
            })
            .then(r => r && r.json())
            .then(data => {
                if (data && data.prompt) {
                    generatedPromptPre.textContent = data.prompt;
                    generatedPromptPre.classList.remove('hidden');
                }
            })
            .catch(err => {
                console.error(err);
                alert('Error generating prompt');
            });
    }

    // Fetch settings from DB on startup
    fetchSettings();
});
