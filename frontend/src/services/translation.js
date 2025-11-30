/**
 * Translation Service
 * Handles text translation using Google Translate API (browser-compatible)
 * Migrated from backend to frontend for faster processing
 * 
 * Uses Google Translate's public API endpoint directly via fetch
 * (Browser-compatible, no Node.js dependencies)
 */

/**
 * Translate text to target language using Google Translate API
 * @param {string} text - Text to translate
 * @param {string} targetLang - Target language code (default: 'hi' for Hindi)
 * @param {string} sourceLang - Source language code (default: 'auto' for auto-detect)
 * @returns {Promise<string>} Translated text
 */
export const translateText = async (text, targetLang = 'hi', sourceLang = 'auto') => {
	if (!text || !text.trim()) {
		return '';
	}

	try {
		// Use Google Translate's public API endpoint
		// This is browser-compatible and doesn't require Node.js modules
		const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sourceLang}&tl=${targetLang}&dt=t&q=${encodeURIComponent(text)}`;
		
		const response = await fetch(url, {
			method: 'GET',
			headers: {
				'Accept': 'application/json',
			},
		});

		if (!response.ok) {
			throw new Error(`Translation API error: ${response.status} ${response.statusText}`);
		}

		const data = await response.json();
		
		// Google Translate API returns: [[["translated text", "original text", null, null, 0]], null, "en"]
		// Extract the translated text from the nested array
		if (Array.isArray(data) && Array.isArray(data[0]) && data[0].length > 0) {
			const translatedParts = data[0]
				.filter(item => Array.isArray(item) && item[0])
				.map(item => item[0]);
			
			return translatedParts.join(' ') || text;
		}

		// Fallback: return original text if parsing fails
		console.warn('Unexpected translation response format:', data);
		return text;
	} catch (error) {
		console.error('Translation error:', error);
		// Don't throw - return original text as fallback
		// This allows the app to continue working even if translation fails
		return text;
	}
};

/**
 * Translate text to Hindi (convenience function)
 * @param {string} text - Text to translate
 * @returns {Promise<string>} Hindi translated text
 */
export const translateToHindi = async (text) => {
	return translateText(text, 'hi', 'auto');
};

/**
 * Translate text to English (convenience function)
 * @param {string} text - Text to translate
 * @returns {Promise<string>} English translated text
 */
export const translateToEnglish = async (text) => {
	return translateText(text, 'en', 'auto');
};

export default {
	translateText,
	translateToHindi,
	translateToEnglish,
};

