/**
 * Script Generator Service
 * Handles Hindi script generation using AI
 * Migrated from backend to frontend for faster processing
 * 
 * Supports multiple AI providers:
 * - Google Gemini
 * - OpenAI GPT
 * - Anthropic Claude
 */

import { GoogleGenerativeAI } from '@google/generative-ai';
import OpenAI from 'openai';
import Anthropic from '@anthropic-ai/sdk';

/**
 * Generate Hindi script for video using AI
 * @param {string} transcript - Original transcript
 * @param {string} transcriptHindi - Hindi translation of transcript
 * @param {string} title - Video title
 * @param {string} description - Video description
 * @param {number} duration - Video duration in seconds
 * @param {string} provider - AI provider ('gemini', 'openai', 'anthropic')
 * @param {string} apiKey - API key for the provider
 * @param {string} enhancedTranscript - Enhanced transcript (optional)
 * @param {string} visualTranscript - Visual analysis transcript (optional)
 * @returns {Promise<string>} Generated Hindi script
 */
export const generateHindiScript = async (
	transcript,
	transcriptHindi,
	title,
	description,
	duration,
	provider = 'gemini',
	apiKey,
	enhancedTranscript = '',
	visualTranscript = ''
) => {
	if (!apiKey) {
		throw new Error(`API key not provided for ${provider}`);
	}

	// Use Hindi transcript if available, otherwise use original
	const contentForScript = transcriptHindi || transcript || '';

	if (!contentForScript.trim() && !title && !description) {
		throw new Error('No content available for script generation');
	}

	// Calculate target word count based on duration (2.5 words per second)
	const targetWordCount = duration > 0 ? Math.round(duration * 2.5) : 40;
	const wordCountRange = `${targetWordCount - 5} to ${targetWordCount + 5}`;
	const durationText = duration > 0 ? `${duration} सेकंड` : 'अज्ञात अवधि';

	try {
		switch (provider.toLowerCase()) {
			case 'gemini':
				return await generateWithGemini(
					contentForScript,
					title,
					description,
					duration,
					targetWordCount,
					wordCountRange,
					durationText,
					enhancedTranscript,
					visualTranscript,
					apiKey
				);
			case 'openai':
				return await generateWithOpenAI(
					contentForScript,
					title,
					description,
					duration,
					targetWordCount,
					wordCountRange,
					durationText,
					enhancedTranscript,
					visualTranscript,
					apiKey
				);
			case 'anthropic':
				return await generateWithAnthropic(
					contentForScript,
					title,
					description,
					duration,
					targetWordCount,
					wordCountRange,
					durationText,
					enhancedTranscript,
					visualTranscript,
					apiKey
				);
			default:
				throw new Error(`Unsupported AI provider: ${provider}`);
		}
	} catch (error) {
		console.error(`Script generation error (${provider}):`, error);
		throw error;
	}
};

/**
 * Generate script using Google Gemini
 */
async function generateWithGemini(
	contentForScript,
	title,
	description,
	duration,
	targetWordCount,
	wordCountRange,
	durationText,
	enhancedTranscript,
	visualTranscript,
	apiKey
) {
	const genAI = new GoogleGenerativeAI(apiKey);
	const model = genAI.getGenerativeModel({ model: 'gemini-pro' });

	const systemPrompt = `You are an AI that creates Hindi narration scripts ONLY based on the real actions shown in the video information I provide.  
You must NEVER invent scenes, NEVER guess, and NEVER create your own story.  
Use only what is actually happening in the video.

YOUR GOAL:
Create a smooth, natural Hindi narration that explains the video step-by-step, in my signature style:
- Start with "देखो —"
- Explain what the person/animal/object is doing
- Describe events in the same order they happen
- Use simple dramatic Hindi, not heavy Hindi
- Use short, TTS-friendly sentences
- End with: "आपकी मम्मी कसम — सब्सक्राइब कर लेना!"

STRICT RULES:

1. STYLE RULES:
- Start with "देखो —"
- Use natural, simple Hindi.
- Use small punchy sentences.
- Tone: dramatic + explanatory + exciting.
- Keep it clean, no abusive words.
- No timestamps in output.
- No long paragraphs. Break sentences for TTS airflow.
- Final line MUST be: "आपकी मम्मी कसम — सब्सक्राइब कर लेना!"

2. VIDEO EXPLANATION RULE (MOST IMPORTANT):
Your script MUST directly explain the actual visuals.
Describe ONLY what the camera shows.
No imagination outside the given frames.
No assumptions.
Explain the real actions clearly and in correct order.

3. TTS RULES:
- Sentences must be short.
- Add proper full stops.
- Should sound smooth in voice narration.
- No timestamps, but maintain natural pacing.

4. DURATION MATCHING RULE (CRITICAL):
The script MUST match the video duration PERFECTLY.
- Generate approximately ${targetWordCount} Hindi words total (range: ${wordCountRange} words).
- DO NOT exceed or fall short of the target word count significantly.
- Adjust sentence length and content density to fit the duration perfectly.
- Include the mandatory hook ("देखो —") and CTA ("आपकी मम्मी कसम — सब्सक्राइब कर लेना!") within this word count.

OUTPUT FORMAT:
Return ONLY the final narration script.
Do NOT add timestamps.
Do NOT add explanations.
Do NOT break character.`;

	const visualContext = visualTranscript
		? `\n\n**दृश्य विश्लेषण (Visual Analysis - Scene-by-Scene):**\n${visualTranscript.substring(0, 2000)}`
		: '\n\n**दृश्य विश्लेषण (Visual Analysis):** Not available (optional) - continue without it.';

	const userMessage = `VIDEO INFORMATION:
Title: ${title}
Description: ${description}
Duration: ${durationText} (${duration} seconds)

⚠️ CRITICAL: Generate a script with approximately ${targetWordCount} Hindi words (range: ${wordCountRange} words).
This ensures the narration perfectly matches the video duration when spoken at natural pace (2.5 words/second).

ORIGINAL TRANSCRIPT:
${contentForScript.substring(0, 4000)}

${visualContext}

${enhancedTranscript ? `AI-ENHANCED TRANSCRIPT (Reference):\n${enhancedTranscript.substring(0, 3000)}` : ''}

YOUR TASK:
Generate the Hindi script following the STRICT RULES defined in the system prompt.
1. Start with "देखो —"
2. End with "आपकी मम्मी कसम — सब्सक्राइब कर लेना!"
3. Match actions perfectly.
4. Use short sentences with voice markup (e.g. [short pause], [sigh]).
5. MATCH DURATION: Generate exactly ${targetWordCount} words (±5 words) to fit ${duration} seconds perfectly.
6. OUTPUT PLAIN TEXT ONLY (No timestamps in final output).`;

	const result = await model.generateContent(userMessage);
	const response = result.response;
	let script = response.text().trim();

	// Ensure "देखो" is at the start
	if (script && !script.startsWith('देखो') && !script.startsWith('Dekho')) {
		script = `देखो — ${script}`;
	}

	// Ensure CTA is at the end
	const ctaText = 'आपकी मम्मी कसम — सब्सक्राइब कर लेना!';
	const incorrectCTAs = [
		'आपकी मम्मी पापा कसम सब्सक्राइब जरूर करे',
		'आपकी मम्मी पुण्या कसम सब्सक्राइब जरूर करे',
		'आपकी मम्मी कसम सब्सक्राइब जरूर करे',
		'सब्सक्राइब जरूर करे',
		'सब्सक्राइब कर लेना',
	];

	// Remove incorrect CTAs
	for (const badCTA of incorrectCTAs) {
		if (script.endsWith(badCTA)) {
			script = script.substring(0, script.length - badCTA.length).trim();
		}
	}

	// Add correct CTA if not present
	if (!script.endsWith(ctaText)) {
		script = `${script}\n\n${ctaText}`;
	}

	return script;
}

/**
 * Generate script using OpenAI GPT
 */
async function generateWithOpenAI(
	contentForScript,
	title,
	description,
	duration,
	targetWordCount,
	wordCountRange,
	durationText,
	enhancedTranscript,
	visualTranscript,
	apiKey
) {
	const openai = new OpenAI({ apiKey, dangerouslyAllowBrowser: true });

	const systemPrompt = `You are an AI that creates Hindi narration scripts ONLY based on the real actions shown in the video information I provide.  
You must NEVER invent scenes, NEVER guess, and NEVER create your own story.  
Use only what is actually happening in the video.

YOUR GOAL:
Create a smooth, natural Hindi narration that explains the video step-by-step, in my signature style:
- Start with "देखो —"
- Explain what the person/animal/object is doing
- Describe events in the same order they happen
- Use simple dramatic Hindi, not heavy Hindi
- Use short, TTS-friendly sentences
- End with: "आपकी मम्मी कसम — सब्सक्राइब कर लेना!"

STRICT RULES:
1. Start with "देखो —"
2. Use natural, simple Hindi with short sentences
3. Tone: dramatic + explanatory + exciting
4. No timestamps in output
5. Final line MUST be: "आपकी मम्मी कसम — सब्सक्राइब कर लेना!"
6. Generate approximately ${targetWordCount} Hindi words (range: ${wordCountRange} words)
7. Match video duration perfectly (${duration} seconds = ${targetWordCount} words at 2.5 words/second)

OUTPUT FORMAT:
Return ONLY the final narration script. No timestamps. No explanations.`;

	const visualContext = visualTranscript
		? `\n\n**दृश्य विश्लेषण (Visual Analysis):**\n${visualTranscript.substring(0, 2000)}`
		: '';

	const userMessage = `VIDEO INFORMATION:
Title: ${title}
Description: ${description}
Duration: ${durationText} (${duration} seconds)

⚠️ CRITICAL: Generate a script with approximately ${targetWordCount} Hindi words (range: ${wordCountRange} words).

ORIGINAL TRANSCRIPT:
${contentForScript.substring(0, 4000)}

${visualContext}

${enhancedTranscript ? `AI-ENHANCED TRANSCRIPT:\n${enhancedTranscript.substring(0, 3000)}` : ''}

Generate the Hindi script following the STRICT RULES.`;

	const completion = await openai.chat.completions.create({
		model: 'gpt-4o-mini',
		messages: [
			{ role: 'system', content: systemPrompt },
			{ role: 'user', content: userMessage },
		],
		temperature: 0.7,
		max_tokens: 1000,
	});

	let script = completion.choices[0].message.content.trim();

	// Ensure "देखो" is at the start
	if (script && !script.startsWith('देखो') && !script.startsWith('Dekho')) {
		script = `देखो — ${script}`;
	}

	// Ensure CTA is at the end
	const ctaText = 'आपकी मम्मी कसम — सब्सक्राइब कर लेना!';
	if (!script.endsWith(ctaText)) {
		script = `${script}\n\n${ctaText}`;
	}

	return script;
}

/**
 * Generate script using Anthropic Claude
 */
async function generateWithAnthropic(
	contentForScript,
	title,
	description,
	duration,
	targetWordCount,
	wordCountRange,
	durationText,
	enhancedTranscript,
	visualTranscript,
	apiKey
) {
	const client = new Anthropic({ apiKey });

	const systemPrompt = `You are an AI that creates Hindi narration scripts ONLY based on the real actions shown in the video information I provide.  
You must NEVER invent scenes, NEVER guess, and NEVER create your own story.  
Use only what is actually happening in the video.

YOUR GOAL:
Create a smooth, natural Hindi narration that explains the video step-by-step, in my signature style:
- Start with "देखो —"
- Explain what the person/animal/object is doing
- Describe events in the same order they happen
- Use simple dramatic Hindi, not heavy Hindi
- Use short, TTS-friendly sentences
- End with: "आपकी मम्मी कसम — सब्सक्राइब कर लेना!"

STRICT RULES:
1. Start with "देखो —"
2. Use natural, simple Hindi with short sentences
3. Tone: dramatic + explanatory + exciting
4. No timestamps in output
5. Final line MUST be: "आपकी मम्मी कसम — सब्सक्राइब कर लेना!"
6. Generate approximately ${targetWordCount} Hindi words (range: ${wordCountRange} words)
7. Match video duration perfectly (${duration} seconds = ${targetWordCount} words at 2.5 words/second)

OUTPUT FORMAT:
Return ONLY the final narration script. No timestamps. No explanations.`;

	const visualContext = visualTranscript
		? `\n\n**दृश्य विश्लेषण (Visual Analysis):**\n${visualTranscript.substring(0, 2000)}`
		: '';

	const userMessage = `VIDEO INFORMATION:
Title: ${title}
Description: ${description}
Duration: ${durationText} (${duration} seconds)

⚠️ CRITICAL: Generate a script with approximately ${targetWordCount} Hindi words (range: ${wordCountRange} words).

ORIGINAL TRANSCRIPT:
${contentForScript.substring(0, 4000)}

${visualContext}

${enhancedTranscript ? `AI-ENHANCED TRANSCRIPT:\n${enhancedTranscript.substring(0, 3000)}` : ''}

Generate the Hindi script following the STRICT RULES.`;

	const message = await client.messages.create({
		model: 'claude-3-haiku-20240307',
		max_tokens: 1000,
		system: systemPrompt,
		messages: [
			{
				role: 'user',
				content: userMessage,
			},
		],
	});

	let script = message.content[0].text.trim();

	// Ensure "देखो" is at the start
	if (script && !script.startsWith('देखो') && !script.startsWith('Dekho')) {
		script = `देखो — ${script}`;
	}

	// Ensure CTA is at the end
	const ctaText = 'आपकी मम्मी कसम — सब्सक्राइब कर लेना!';
	if (!script.endsWith(ctaText)) {
		script = `${script}\n\n${ctaText}`;
	}

	return script;
}

export default {
	generateHindiScript,
};

