/**
 * Google Gemini TTS Service
 * Handles Text-to-Speech synthesis using Google Gemini TTS API
 * Migrated from backend to frontend for faster processing
 * 
 * API: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent
 */

/**
 * Generate speech using Google Gemini TTS API
 * @param {string} text - Text to synthesize (can include markup tags like [sigh], [laughing], [short pause], etc.)
 * @param {string} apiKey - Google Gemini API key
 * @param {string} languageCode - Language code (default: 'hi-IN' for Hindi)
 * @param {string} voiceName - Voice name (default: 'Enceladus' for Hindi)
 * @param {number} videoDuration - Target duration in seconds (optional). If provided, adjusts speaking rate.
 * @param {number} temperature - Temperature for generation (optional)
 * @param {string} stylePrompt - Style prompt for overall tone (optional)
 * @returns {Promise<Blob>} Audio blob (PCM format, can be converted to WAV/MP3)
 */
export const generateSpeech = async (
	text,
	apiKey,
	languageCode = 'hi-IN',
	voiceName = 'Enceladus',
	videoDuration = null,
	temperature = null,
	stylePrompt = null
) => {
	if (!apiKey) {
		throw new Error('Google Gemini API key is required');
	}

	if (!text || !text.trim()) {
		throw new Error('Text is required for TTS synthesis');
	}

	try {
		// Calculate target speed if video_duration is provided
		let speedInstruction = '';
		if (videoDuration && videoDuration > 0) {
			const wordCount = text.split(/\s+/).length;
			const estimatedDuration = wordCount / 2.5; // Average speaking rate: 2.5 words/second
			const speedFactor = estimatedDuration / videoDuration;

			console.log(
				`TTS Speed Calculation: Words=${wordCount}, Video Duration=${videoDuration}s, Est. Audio Duration=${estimatedDuration.toFixed(1)}s, Factor=${speedFactor.toFixed(2)}`
			);

			if (speedFactor > 1.3) {
				speedInstruction = 'Speak at a very fast pace to fit the content in a short time.';
			} else if (speedFactor > 1.1) {
				speedInstruction = 'Speak at a slightly faster pace than normal.';
			} else if (speedFactor < 0.7) {
				speedInstruction = 'Speak at a very slow, relaxed, and deliberate pace.';
			} else if (speedFactor < 0.9) {
				speedInstruction = 'Speak at a slightly slower, more relaxed pace.';
			} else {
				speedInstruction = 'Speak at a natural, moderate pace.';
			}
		}

		// Generate comprehensive style prompt
		if (!stylePrompt) {
			stylePrompt = generateComprehensiveStylePrompt(text, speedInstruction);
		} else {
			stylePrompt = enhanceStylePrompt(stylePrompt, speedInstruction);
		}

		// Prepare request payload
		const payload = {
			contents: [
				{
					parts: [
						{
							text: `${stylePrompt}\n\nRead the following text with all markup tags:\n\n${text}`,
						},
					],
				},
			],
			generationConfig: {
				responseModalities: ['AUDIO'],
				speechConfig: {
					voiceConfig: {
						prebuiltVoiceConfig: {
							voiceName: voiceName,
						},
					},
				},
			},
		};

		// Add temperature if provided
		if (temperature !== null) {
			payload.generationConfig.temperature = temperature;
		}

		// Make API request
		const apiEndpoint = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key=${apiKey}`;

		console.log(`Generating TTS with Gemini TTS (voice: ${voiceName}, language: ${languageCode})...`);

		const response = await fetch(apiEndpoint, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify(payload),
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			const errorMsg = errorData?.error?.message || `HTTP ${response.status}`;
			console.error(`Gemini TTS API error: ${errorMsg}`);
			throw new Error(`Gemini TTS API error: ${errorMsg}`);
		}

		// Parse response
		const result = await response.json();

		// Extract audio content from response
		let audioContentB64 = null;

		// Check for audio in candidates (standard Gemini API response)
		if (result.candidates && result.candidates.length > 0) {
			const candidate = result.candidates[0];
			if (candidate.content) {
				const parts = candidate.content.parts || [];
				for (const part of parts) {
					// Check for inlineData with audio/pcm mimeType
					if (part.inlineData) {
						const inlineData = part.inlineData;
						const mimeType = inlineData.mimeType || '';
						if (mimeType.toLowerCase().includes('audio') || mimeType.toLowerCase().includes('pcm')) {
							audioContentB64 = inlineData.data;
							console.log(`Found audio in inlineData with mimeType: ${mimeType}`);
							break;
						}
					}
					// Check if text field contains base64 audio (fallback)
					else if (part.text) {
						try {
							// Try to decode if it looks like base64
							const decoded = atob(part.text);
							if (decoded.length > 1000) {
								// Likely audio data
								audioContentB64 = part.text;
								console.log('Found audio in text field (base64)');
								break;
							}
						} catch (e) {
							// Not base64, continue
						}
					}
				}
			}
		}

		// Alternative: Check for audioContent directly (some API versions)
		if (!audioContentB64 && result.audioContent) {
			audioContentB64 = result.audioContent;
			console.log('Found audio in audioContent field');
		}

		// Try regex pattern matching as last resort
		if (!audioContentB64) {
			const responseStr = JSON.stringify(result);
			const base64Pattern = /"data"\s*:\s*"([A-Za-z0-9+/=]{100,})"/;
			const match = responseStr.match(base64Pattern);
			if (match) {
				audioContentB64 = match[1];
				console.log('Found audio using regex pattern matching');
			}
		}

		if (!audioContentB64) {
			console.error(`Response structure: ${JSON.stringify(result, null, 2).substring(0, 1000)}`);
			throw new Error('No audio content found in API response. Check console for response structure.');
		}

		// Decode base64 audio to binary
		const audioBytes = Uint8Array.from(atob(audioContentB64), (c) => c.charCodeAt(0));

		// Convert PCM to WAV blob (browser-compatible)
		const wavBlob = pcmToWav(audioBytes, 24000, 1, 16); // 24kHz, mono, 16-bit

		console.log(`TTS audio generated successfully (${(wavBlob.size / 1024).toFixed(2)} KB)`);
		return wavBlob;
	} catch (error) {
		console.error('Gemini TTS generation error:', error);
		throw error;
	}
};

/**
 * Convert PCM audio bytes to WAV blob
 * @param {Uint8Array} pcmData - PCM audio data
 * @param {number} sampleRate - Sample rate (default: 24000)
 * @param {number} channels - Number of channels (default: 1 for mono)
 * @param {number} bitsPerSample - Bits per sample (default: 16)
 * @returns {Blob} WAV audio blob
 */
function pcmToWav(pcmData, sampleRate = 24000, channels = 1, bitsPerSample = 16) {
	const dataSize = pcmData.length;
	const fileSize = 36 + dataSize;

	// Create WAV header
	const buffer = new ArrayBuffer(44 + dataSize);
	const view = new DataView(buffer);

	// RIFF header
	view.setUint32(0, 0x46464952, true); // "RIFF"
	view.setUint32(4, fileSize, true);
	view.setUint32(8, 0x45564157, true); // "WAVE"

	// fmt chunk
	view.setUint32(12, 0x20746d66, true); // "fmt "
	view.setUint32(16, 16, true); // fmt chunk size
	view.setUint16(20, 1, true); // audio format (PCM)
	view.setUint16(22, channels, true);
	view.setUint32(24, sampleRate, true);
	view.setUint32(28, (sampleRate * channels * bitsPerSample) / 8, true); // byte rate
	view.setUint16(32, (channels * bitsPerSample) / 8, true); // block align
	view.setUint16(34, bitsPerSample, true);

	// data chunk
	view.setUint32(36, 0x61746164, true); // "data"
	view.setUint32(40, dataSize, true);

	// Copy PCM data
	const pcmView = new Uint8Array(buffer, 44);
	pcmView.set(pcmData);

	return new Blob([buffer], { type: 'audio/wav' });
}

/**
 * Generate comprehensive style prompt based on content analysis
 * @param {string} text - Text to analyze
 * @param {string} speedInstruction - Speed instruction (optional)
 * @returns {string} Style prompt
 */
function generateComprehensiveStylePrompt(text, speedInstruction = '') {
	const textLower = text.toLowerCase();

	// Fear/suspense keywords
	const fearKeywords = [
		'राक्षस',
		'डर',
		'अंधेरा',
		'भय',
		'साहस',
		'पीछा',
		'भाग',
		'दौड़',
		'मौत',
		'खतरा',
		'डरावना',
		'भूत',
		'चिंता',
	];
	const hasFear = fearKeywords.some((keyword) => textLower.includes(keyword));

	// Exciting/energetic keywords
	const excitingKeywords = [
		'देखो',
		'वाह',
		'अरे',
		'मजेदार',
		'रोमांचक',
		'कमाल',
		'जादू',
		'अद्भुत',
		'शानदार',
		'बेहतरीन',
	];
	const hasExciting = excitingKeywords.some((keyword) => textLower.includes(keyword));

	// Determine primary tone
	let toneDescription, emotionalContext, specificGuidance;

	if (hasFear) {
		toneDescription = 'suspenseful, dramatic, and engaging';
		emotionalContext = 'narrating a suspenseful story with moments of tension and drama';
		specificGuidance = `
- Use a dramatic, slightly tense tone when describing scary or suspenseful moments (राक्षस, अंधेरा, डर)
- Use [whispering] tags strategically to create atmosphere for fear elements - whisper quietly and mysteriously
- Use [sigh] for relief, tension release, or dramatic pauses
- Maintain energy and engagement throughout - keep listeners on edge but not overwhelmed
- This is entertainment content, so balance excitement with appropriate pacing
- When text mentions fear elements, let your voice reflect genuine tension and drama
- Use [long pause] before revealing important or scary information for dramatic effect`;
	} else if (hasExciting) {
		toneDescription = 'energetic, enthusiastic, and vivid';
		emotionalContext = 'an engaging, energetic explainer bringing scenes to life';
		specificGuidance = `
- Speak in a friendly, vivid, and enthusiastic tone throughout
- Be genuinely enthusiastic about scenes and actions - let your excitement show
- Use [laughing] tags naturally for fun moments - react with genuine amusement and joy
- Maintain high energy and excitement - keep the pace lively and engaging
- When describing exciting events, use [short pause] to build anticipation
- Use [laughing] to react to humorous or delightful moments in the story`;
	} else {
		toneDescription = 'friendly, engaging, and descriptive';
		emotionalContext = 'a friendly narrator explaining content in an engaging way';
		specificGuidance = `
- Speak in a friendly, vivid, and descriptive tone
- Be enthusiastic about scenes and actions - bring the content to life
- Use natural pacing with appropriate pauses for clarity
- Maintain engagement throughout - keep listeners interested`;
	}

	const comprehensivePrompt = `You are ${emotionalContext} in Hindi. Your role is to create engaging and natural-sounding audio that captures the emotional essence of the content.

**PRIMARY STYLE (The Three Levers):**

1. **Style Prompt (Overall Tone):**
   - You are speaking in a ${toneDescription} manner
   - Your delivery should be natural, human-like, and emotionally consistent
   - Align your tone with the semantic meaning of the text content
   - Use emotionally rich delivery that matches the words being spoken

2. **Text Content Alignment:**
   - The text you are reading contains emotionally rich content
   - Match your emotional delivery to the meaning of the words
   - If the text describes fear, use a tense, dramatic tone
   - If the text describes excitement, use an enthusiastic, energetic tone
   - Let the words guide your emotional expression

3. **Markup Tags (Precise Control):**
   - Follow ALL markup tags exactly as written in the text
   - Markup tags work in concert with your style and the text content
   - Each tag has a specific behavior - respect it precisely

**MARKUP TAG GUIDANCE:**

**Mode 1: Non-speech Sounds (Replaced by audible vocalizations):**
- [sigh] - Insert a genuine sigh sound. The emotional quality (relief, tension, exhaustion) should match the context and your style prompt
- [laughing] - Insert a natural laugh. React with genuine amusement - the laugh should sound authentic and match the emotional context (amused, surprised, delighted)
- [uhm] - Insert a natural hesitation sound. Use this to create a more conversational, human-like feel

**Mode 2: Style Modifiers (Modify delivery of subsequent speech):**
- [sarcasm] - Deliver the subsequent phrase with a sarcastic tone. This is a powerful modifier - let the sarcasm be clear but not overdone
- [robotic] - Make the subsequent speech sound robotic. The effect extends across the phrase. Use sparingly and precisely
- [shouting] - Increase volume and intensity. Pair with text that implies yelling or excitement. Make it sound genuinely loud and energetic
- [whispering] - Decrease volume significantly. Speak as quietly as you can while remaining audible. Use for dramatic effect, secrets, or fear elements
- [extremely fast] - Increase speed significantly. Ideal for disclaimers or fast-paced dialogue. Maintain clarity even at high speed

**Mode 3: Pacing and Pauses (Insert silence for rhythm control):**
- [short pause] - Insert a brief pause (~250ms), similar to a comma. Use to separate clauses or list items for better clarity
- [medium pause] - Insert a standard pause (~500ms), similar to a sentence break. Effective for separating distinct sentences or thoughts
- [long pause] - Insert a significant pause (~1000ms+) for dramatic effect. Use for dramatic timing, like "The answer is... [long pause] ...no." Avoid overuse

**KEY STRATEGIES FOR RELIABLE RESULTS:**

1. **Align All Three Levers:** Ensure your Style Prompt, Text Content interpretation, and Markup Tags are all semantically consistent and working toward the same goal

2. **Use Emotionally Rich Delivery:** Don't just read the words - feel the emotions. If the text describes fear, genuinely sound tense. If it describes joy, genuinely sound happy

3. **Be Specific and Detailed:** Your delivery should be nuanced. A scared tone works best when you genuinely sound scared, not just "spooky"

4. **Respect Markup Tags Precisely:**
   - When you see [sigh], actually sigh - don't just pause
   - When you see [laughing], actually laugh - make it sound real
   - When you see [whispering], actually whisper - speak quietly and mysteriously
   - When you see [short pause], pause briefly (~250ms)
   - When you see [medium pause], pause longer (~500ms)
   - When you see [long pause], pause dramatically (~1000ms+)

5. **Natural Flow:** While following tags precisely, maintain natural speech flow. Don't sound robotic - sound human, just with precise control

${specificGuidance}

**FINAL INSTRUCTIONS:**
- Read the text exactly as written, following all markup tags precisely
- Match your emotional delivery to the content - be genuine and authentic
- Use pauses naturally - they control rhythm and pacing
- React naturally to emotional content - if something is scary, sound scared; if something is exciting, sound excited
- ${speedInstruction || 'Speak at a natural, moderate pace'}
- Create engaging, natural-sounding audio that captures the essence of the content`;

	return comprehensivePrompt;
}

/**
 * Enhance a provided style prompt with markup tag guidance and speed instructions
 * @param {string} providedPrompt - Provided style prompt
 * @param {string} speedInstruction - Speed instruction (optional)
 * @returns {string} Enhanced style prompt
 */
function enhanceStylePrompt(providedPrompt, speedInstruction = '') {
	const markupGuidance = `

**IMPORTANT - Markup Tag Behavior:**
- [sigh], [laughing], [uhm] - These are replaced by actual sounds (sigh, laugh, hesitation). React naturally.
- [whispering], [shouting], [sarcasm], [robotic] - These modify your delivery style. Follow them precisely.
- [short pause], [medium pause], [long pause] - These insert silence (~250ms, ~500ms, ~1000ms+ respectively). Use them for rhythm control.
- Read ALL markup tags in the text and follow them exactly as written.
- Markup tags work in concert with your style - align them with your overall tone.`;

	return `${providedPrompt}${markupGuidance}
- ${speedInstruction || 'Speak at a natural, moderate pace'}
- Read the text exactly as written, following all markup tags precisely`;
}

/**
 * Upload audio blob to backend for storage
 * @param {Blob} audioBlob - Audio blob to upload
 * @param {number} videoId - Video ID
 * @param {string} apiEndpoint - Backend API endpoint (default: '/api/videos/{id}/upload_audio/')
 * @returns {Promise<Object>} Upload response
 */
export const uploadAudioToBackend = async (audioBlob, videoId, apiEndpoint = null) => {
	const endpoint = apiEndpoint || `/api/videos/${videoId}/upload_audio/`;

	const formData = new FormData();
	formData.append('audio', audioBlob, `synthesized_${videoId}.wav`);

	const response = await fetch(endpoint, {
		method: 'POST',
		body: formData,
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ error: 'Upload failed' }));
		throw new Error(error.error || 'Failed to upload audio');
	}

	return await response.json();
};

export default {
	generateSpeech,
	uploadAudioToBackend,
};

