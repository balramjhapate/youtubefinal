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
});
