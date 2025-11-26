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

    // Voice Cloning elements
    const voiceNameInput = document.getElementById('voice-name');
    const voiceAudioInput = document.getElementById('voice-audio');
    const voiceTextInput = document.getElementById('voice-text');
    const createVoiceBtn = document.getElementById('create-voice');
    const voiceSelect = document.getElementById('voice-select');
    const synthTextInput = document.getElementById('synth-text');
    const synthesizeBtn = document.getElementById('synthesize-audio');
    const synthPlayer = document.getElementById('synth-player');

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

    // Voice Cloning Functions

    function loadVoiceProfiles() {
        fetch('/api/voice-profiles/')
            .then(r => r.json())
            .then(data => {
                voiceSelect.innerHTML = '<option value="">Select a voice...</option>';
                if (data.profiles && data.profiles.length > 0) {
                    data.profiles.forEach(p => {
                        const option = document.createElement('option');
                        option.value = p.id;
                        option.textContent = p.name;
                        voiceSelect.appendChild(option);
                    });
                } else {
                    voiceSelect.innerHTML = '<option value="">No voices found</option>';
                }
            })
            .catch(err => console.error('Error loading voices:', err));
    }

    createVoiceBtn.addEventListener('click', () => {
        const name = voiceNameInput.value.trim();
        const text = voiceTextInput.value.trim();
        const file = voiceAudioInput.files[0];

        if (!name || !text || !file) {
            alert('Please fill all voice fields');
            return;
        }

        createVoiceBtn.disabled = true;
        createVoiceBtn.textContent = 'Creating...';

        const formData = new FormData();
        formData.append('name', name);
        formData.append('reference_text', text);
        formData.append('reference_audio', file);

        fetch('/api/voice-profiles/', {
            method: 'POST',
            body: formData
        })
            .then(r => r.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                alert('Voice profile created!');
                loadVoiceProfiles();
                // Clear inputs
                voiceNameInput.value = '';
                voiceTextInput.value = '';
                voiceAudioInput.value = '';
            })
            .catch(err => {
                console.error(err);
                alert('Failed to create voice: ' + err.message);
            })
            .finally(() => {
                createVoiceBtn.disabled = false;
                createVoiceBtn.textContent = 'Create Voice Profile';
            });
    });

    synthesizeBtn.addEventListener('click', () => {
        const text = synthTextInput.value.trim();
        const profileId = voiceSelect.value;

        if (!text || !profileId) {
            alert('Please select a voice and enter text');
            return;
        }

        synthesizeBtn.disabled = true;
        synthesizeBtn.textContent = 'Synthesizing...';
        synthPlayer.style.display = 'none';

        fetch('/api/synthesize-audio/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, profile_id: profileId })
        })
            .then(r => r.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                synthPlayer.src = data.audio_url;
                synthPlayer.style.display = 'block';
                synthPlayer.play();
            })
            .catch(err => {
                console.error(err);
                alert('Synthesis failed: ' + err.message);
            })
            .finally(() => {
                synthesizeBtn.disabled = false;
                synthesizeBtn.textContent = 'Synthesize Audio';
            });
    });

    // Fetch settings and voices on startup
    fetchSettings();
    loadVoiceProfiles();
});
