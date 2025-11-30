/**
 * AI Processing Service
 * Handles AI-powered summary and tag generation
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
 * Generate summary and tags using AI
 * @param {string} transcript - Video transcript text
 * @param {string} title - Video title
 * @param {string} description - Video description
 * @param {string} provider - AI provider ('gemini', 'openai', 'anthropic')
 * @param {string} apiKey - API key for the provider
 * @returns {Promise<{summary: string, tags: string[]}>}
 */
export const generateSummary = async (transcript, title, description, provider = 'gemini', apiKey) => {
	if (!apiKey) {
		throw new Error(`API key not provided for ${provider}`);
	}

	const content = [title, description, transcript].filter(Boolean).join('\n\n');
	
	if (!content.trim()) {
		return {
			summary: 'No content available for AI processing.',
			tags: ['content', 'social-media', 'video'],
		};
	}

	try {
		switch (provider.toLowerCase()) {
			case 'gemini':
				return await generateWithGemini(content, title, description, transcript, apiKey);
			case 'openai':
				return await generateWithOpenAI(content, title, description, transcript, apiKey);
			case 'anthropic':
				return await generateWithAnthropic(content, title, description, transcript, apiKey);
			default:
				throw new Error(`Unsupported AI provider: ${provider}`);
		}
	} catch (error) {
		console.error(`AI processing error (${provider}):`, error);
		throw error;
	}
};

/**
 * Generate summary and tags using Google Gemini
 */
async function generateWithGemini(content, title, description, transcript, apiKey) {
	const genAI = new GoogleGenerativeAI(apiKey);
	const model = genAI.getGenerativeModel({ model: 'gemini-pro' });

	const prompt = `Analyze this video content and provide:
1. A concise summary (2-3 sentences)
2. Relevant tags (comma-separated, max 10 tags)

Video Title: ${title}
Description: ${description}
Transcript: ${transcript.substring(0, 2000)}${transcript.length > 2000 ? '...' : ''}

Return your response in JSON format:
{
  "summary": "brief summary here",
  "tags": ["tag1", "tag2", "tag3"]
}`;

	const result = await model.generateContent(prompt);
	const response = result.response;
	const text = response.text();

	// Try to parse JSON from response
	try {
		// Extract JSON from markdown code blocks if present
		const jsonMatch = text.match(/```json\s*([\s\S]*?)\s*```/) || text.match(/\{[\s\S]*\}/);
		const jsonText = jsonMatch ? (jsonMatch[1] || jsonMatch[0]) : text;
		const parsed = JSON.parse(jsonText);
		
		return {
			summary: parsed.summary || extractSummary(text),
			tags: Array.isArray(parsed.tags) ? parsed.tags : extractTags(text),
		};
	} catch (e) {
		// Fallback: extract summary and tags from text
		return {
			summary: extractSummary(text),
			tags: extractTags(text),
		};
	}
}

/**
 * Generate summary and tags using OpenAI GPT
 */
async function generateWithOpenAI(content, title, description, transcript, apiKey) {
	const openai = new OpenAI({ apiKey, dangerouslyAllowBrowser: true });
	
	const prompt = `Analyze this video content and provide:
1. A concise summary (2-3 sentences)
2. Relevant tags (comma-separated, max 10 tags)

Video Title: ${title}
Description: ${description}
Transcript: ${transcript.substring(0, 2000)}${transcript.length > 2000 ? '...' : ''}

Return your response in JSON format:
{
  "summary": "brief summary here",
  "tags": ["tag1", "tag2", "tag3"]
}`;

	const completion = await openai.chat.completions.create({
		model: 'gpt-3.5-turbo',
		messages: [
			{
				role: 'system',
				content: 'You are a helpful assistant that analyzes video content and generates summaries and tags.',
			},
			{
				role: 'user',
				content: prompt,
			},
		],
		temperature: 0.7,
		max_tokens: 500,
	});

	const text = completion.choices[0].message.content;

	try {
		const jsonMatch = text.match(/```json\s*([\s\S]*?)\s*```/) || text.match(/\{[\s\S]*\}/);
		const jsonText = jsonMatch ? (jsonMatch[1] || jsonMatch[0]) : text;
		const parsed = JSON.parse(jsonText);
		
		return {
			summary: parsed.summary || extractSummary(text),
			tags: Array.isArray(parsed.tags) ? parsed.tags : extractTags(text),
		};
	} catch (e) {
		return {
			summary: extractSummary(text),
			tags: extractTags(text),
		};
	}
}

/**
 * Generate summary and tags using Anthropic Claude
 */
async function generateWithAnthropic(content, title, description, transcript, apiKey) {
	const client = new Anthropic({ apiKey });

	const prompt = `Analyze this video content and provide:
1. A concise summary (2-3 sentences)
2. Relevant tags (comma-separated, max 10 tags)

Video Title: ${title}
Description: ${description}
Transcript: ${transcript.substring(0, 2000)}${transcript.length > 2000 ? '...' : ''}

Return your response in JSON format:
{
  "summary": "brief summary here",
  "tags": ["tag1", "tag2", "tag3"]
}`;

	const message = await client.messages.create({
		model: 'claude-3-haiku-20240307',
		max_tokens: 500,
		messages: [
			{
				role: 'user',
				content: prompt,
			},
		],
	});

	const text = message.content[0].text;

	try {
		const jsonMatch = text.match(/```json\s*([\s\S]*?)\s*```/) || text.match(/\{[\s\S]*\}/);
		const jsonText = jsonMatch ? (jsonMatch[1] || jsonMatch[0]) : text;
		const parsed = JSON.parse(jsonText);
		
		return {
			summary: parsed.summary || extractSummary(text),
			tags: Array.isArray(parsed.tags) ? parsed.tags : extractTags(text),
		};
	} catch (e) {
		return {
			summary: extractSummary(text),
			tags: extractTags(text),
		};
	}
}

/**
 * Extract summary from AI response text (fallback)
 */
function extractSummary(text) {
	// Try to find summary section
	const summaryMatch = text.match(/summary[:\s]+(.+?)(?:\n|tags|$)/i);
	if (summaryMatch) {
		return summaryMatch[1].trim();
	}
	
	// Fallback: first 200 characters
	return text.substring(0, 200).trim() + (text.length > 200 ? '...' : '');
}

/**
 * Extract tags from AI response text (fallback)
 */
function extractTags(text) {
	// Try to find tags section
	const tagsMatch = text.match(/tags?[:\s]+(.+?)(?:\n|$)/i);
	if (tagsMatch) {
		const tagsText = tagsMatch[1];
		// Extract tags from comma-separated or array format
		const tags = tagsText
			.replace(/[\[\]"]/g, '')
			.split(/[,;]/)
			.map(tag => tag.trim())
			.filter(tag => tag.length > 0)
			.slice(0, 10);
		
		if (tags.length > 0) {
			return tags;
		}
	}
	
	// Fallback: extract keywords from text
	const words = text.match(/\b\w{4,}\b/g) || [];
	const stopWords = new Set(['summary', 'tags', 'video', 'content', 'description', 'transcript']);
	const keywords = words
		.filter(word => !stopWords.has(word.toLowerCase()))
		.slice(0, 10);
	
	return keywords.length > 0 ? keywords : ['content', 'social-media', 'video'];
}

export default {
	generateSummary,
};

