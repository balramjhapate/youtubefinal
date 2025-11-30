/**
 * Text Processing Utilities
 * Handles text cleaning, formatting, and processing for TTS
 * Migrated from backend to frontend for faster processing
 */

/**
 * Remove timestamps from text
 * @param {string} text - Text that may contain timestamps
 * @returns {string} Text without timestamps
 */
export const removeTimestamps = (text) => {
	if (!text) return '';
	
	// Remove timestamps in format: HH:MM:SS or MM:SS or H:MM:SS
	// Pattern matches timestamps anywhere in the text
	let cleaned = text.replace(/\b\d{1,2}:\d{2}(?::\d{2})?\b/g, '');
	
	// Clean up extra spaces left by timestamp removal
	cleaned = cleaned.replace(/\s+/g, ' ').trim();
	
	return cleaned;
};

/**
 * Remove non-Hindi characters (Chinese, English, etc.) from text
 * Keeps only Hindi (Devanagari) script, numbers, spaces, and punctuation
 * @param {string} text - Text that may contain mixed languages
 * @returns {string} Text with only Hindi characters
 */
export const removeNonHindiCharacters = (text) => {
	if (!text) return text;
	
	// Devanagari range: U+0900 to U+097F
	// Keep Hindi, numbers, spaces, and common punctuation
	const hindiPattern = /[^\u0900-\u097F\s0-9।!?.,:;()\-"'']+/g;
	let cleaned = text.replace(hindiPattern, '');
	
	// Clean up multiple spaces
	cleaned = cleaned.replace(/\s+/g, ' ').trim();
	
	return cleaned;
};

/**
 * Fix sentence structure for better TTS
 * Adds proper punctuation, fixes grammar, ensures natural flow
 * @param {string} text - Text with potential sentence structure issues
 * @returns {string} Text with improved sentence structure
 */
export const fixSentenceStructure = (text) => {
	if (!text) return text;
	
	const lines = text.split('\n');
	const fixedLines = [];
	
	// Common grammar fixes (array of [pattern, replacement] pairs)
	const fixes = [
		[/साहसाते/g, 'डराते'],
		[/बहुत साहस/g, 'बहुत डर'],
	];
	
	for (let line of lines) {
		line = line.trim();
		if (!line) {
			fixedLines.push('');
			continue;
		}
		
		// Apply grammar fixes
		for (const [pattern, replacement] of fixes) {
			line = line.replace(pattern, replacement);
		}
		
		// Ensure sentences end with proper punctuation
		// Check if it's a complete sentence (has verb or action word)
		const hasVerb = /(है|हैं|हो|था|थे|गया|गई|गए|कर|करता|करती|करते|जा|जाता|जाती|जाते|आ|आता|आती|आते|दे|देता|देती|देते|ले|लेता|लेती|लेते|रह|रहा|रही|रहे)/.test(line);
		
		if (hasVerb && !/[।!?]$/.test(line)) {
			line = line + '।';
		}
		
		fixedLines.push(line);
	}
	
	return fixedLines.join('\n');
};

/**
 * Format Hindi script with proper structure
 * Adds "देखो" at the start if missing
 * @param {string} rawScript - Raw script text
 * @param {string} title - Video title (optional)
 * @returns {string} Formatted script
 */
export const formatHindiScript = (rawScript, title = '') => {
	if (!rawScript) return '';
	
	let script = rawScript.trim();
	const lines = script.split('\n');
	
	// Find first content line and add "देखो" if needed
	for (let i = 0; i < lines.length; i++) {
		const line = lines[i].trim();
		if (!line) continue;
		
		// Check if line already starts with "देखो"
		if (/^(देखो|Dekho)/.test(line)) {
			break; // Already has "देखो"
		}
		
		// Check if line has timestamp
		const timestampMatch = line.match(/^(\d{1,2}:\d{2}:\d{2})\s+(.+)$/);
		if (timestampMatch) {
			// Has timestamp, add "देखो" after timestamp
			lines[i] = line.replace(/^(\d{1,2}:\d{2}:\d{2})\s+(.+)$/, '$1 देखो $2');
		} else {
			// No timestamp, add "देखो" at start
			lines[i] = `देखो ${line}`;
		}
		break;
	}
	
	return lines.join('\n');
};

/**
 * Clean script for TTS (remove headers, timestamps, questions, etc.)
 * Only keeps main action/content description
 * @param {string} formattedScript - Formatted script with headers
 * @returns {string} Clean script text for TTS
 */
export const cleanScriptForTTS = (formattedScript) => {
	if (!formattedScript) return '';
	
	const lines = formattedScript.split('\n');
	const cleanLines = [];
	
	// Patterns to identify introductory/meta text to remove
	const introPatterns = [
		/ठीक\s+है[,\s]*मैं\s+समझ\s+गया/i,
		/यहाँ\s+स्क्रिप्ट\s+है/i,
		/यहाँ\s+हिंदी\s+स्क्रिप्ट\s+है/i,
		/^नमस्ते/i,
		/^स्वागत\s+है/i,
		/^Title:/i,
		/^Description:/i,
		/^Visual:/i,
		/^Audio:/i,
		/^Scene\s+\d+:/i,
	];
	
	// Patterns to identify voice prompt/CTA content (we want to keep this but move to end)
	const ctaPatterns = [
		/माँ\s+बाप\s+की\s+कसम/i,
		/subscribe\s+और\s+like/i,
		/subscribe.*like/i,
		/^धन्यवाद/i,
		/अगर\s+माँ\s+बाप\s+से\s+प्यार/i,
		/कर\s+के\s+जाओ/i,
		/कसम\s+है/i,
	];
	
	// Valid TTS markup tags to preserve
	const markupPattern = /\[(sigh|laughing|uhm|sarcasm|robotic|shouting|whispering|extremely fast|short pause|medium pause|long pause|scared|curious|bored)\]/i;
	
	let ctaLine = null;
	
	for (const line of lines) {
		let processedLine = line.trim();
		
		// Skip empty lines
		if (!processedLine) continue;
		
		// Skip header sections (Markdown headers)
		if (/^[#*]+/.test(processedLine)) {
			// But check if it contains Hindi text that looks like script
			if (/:/.test(processedLine)) {
				const parts = processedLine.split(':', 2);
				if (parts.length > 1 && /[\u0900-\u097F]/.test(parts[1])) {
					processedLine = parts[1].trim();
				} else {
					continue;
				}
			} else {
				continue;
			}
		}
		
		// Remove timestamps from beginning of line
		processedLine = processedLine.replace(/^\d{1,2}:\d{2}(:\d{2})?\s+/, '');
		
		// Remove timestamps from anywhere in the text
		processedLine = processedLine.replace(/\b\d{1,2}:\d{2}(?::\d{2})?\b/g, '');
		
		// Clean up extra spaces
		processedLine = processedLine.replace(/\s+/g, ' ').trim();
		
		// Check for intro patterns
		const isIntro = introPatterns.some(pattern => pattern.test(processedLine));
		if (isIntro) continue;
		
		// Check for CTA patterns (save for end)
		const isCTA = ctaPatterns.some(pattern => pattern.test(processedLine));
		if (isCTA) {
			ctaLine = processedLine;
			continue; // Skip CTA line here, add at end
		}
		
		// Remove invalid brackets (keep TTS markup)
		processedLine = processedLine.replace(/\[.*?\]/g, (match) => {
			return markupPattern.test(match) ? match : '';
		});
		
		// Remove parentheses content (usually visual cues)
		processedLine = processedLine.replace(/\(.*?\)/g, '');
		
		// Only add if it contains Hindi characters or valid English words
		if ((/[\u0900-\u097F]/.test(processedLine) || /[a-zA-Z]/.test(processedLine)) && processedLine.length > 2) {
			cleanLines.push(processedLine);
		}
	}
	
	// Join all lines
	let cleanText = cleanLines.join(' ');
	
	// Fix punctuation spacing
	cleanText = cleanText.replace(/\s+([,।?!])/g, '$1');
	
	// Add CTA at the end if we found one
	if (ctaLine) {
		cleanText = `${cleanText} ${ctaLine}`;
	}
	
	// Remove non-Hindi characters
	cleanText = removeNonHindiCharacters(cleanText);
	
	// Fix sentence structure
	cleanText = fixSentenceStructure(cleanText);
	
	return cleanText.trim();
};

/**
 * Filter subscribe mentions from text
 * @param {string} text - Text that may contain subscribe mentions
 * @returns {string} Text with subscribe mentions removed
 */
export const filterSubscribeMentions = (text) => {
	if (!text) return '';
	
	const subscribePatterns = [
		/subscribe/gi,
		/सब्सक्राइब/gi,
		/सब्स्क्राइब/gi,
		/सब्सक्राइब\s+करें/gi,
		/सब्सक्राइब\s+जरूर\s+करें/gi,
		/like\s+और\s+subscribe/gi,
		/like.*subscribe/gi,
	];
	
	let filtered = text;
	for (const pattern of subscribePatterns) {
		filtered = filtered.replace(pattern, '');
	}
	
	// Clean up extra spaces
	filtered = filtered.replace(/\s+/g, ' ').trim();
	
	return filtered;
};

export default {
	removeTimestamps,
	removeNonHindiCharacters,
	fixSentenceStructure,
	formatHindiScript,
	cleanScriptForTTS,
	filterSubscribeMentions,
};

