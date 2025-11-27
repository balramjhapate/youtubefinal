// Status constants
export const STATUS = {
  SUCCESS: 'success',
  FAILED: 'failed',
  PENDING: 'pending',
};

export const TRANSCRIPTION_STATUS = {
  NOT_TRANSCRIBED: 'not_transcribed',
  TRANSCRIBING: 'transcribing',
  TRANSCRIBED: 'transcribed',
  FAILED: 'failed',
};

export const AI_PROCESSING_STATUS = {
  NOT_PROCESSED: 'not_processed',
  PROCESSING: 'processing',
  PROCESSED: 'processed',
  FAILED: 'failed',
};

export const AUDIO_PROMPT_STATUS = {
  NOT_GENERATED: 'not_generated',
  GENERATING: 'generating',
  GENERATED: 'generated',
  FAILED: 'failed',
};

export const SYNTHESIS_STATUS = {
  NOT_SYNTHESIZED: 'not_synthesized',
  SYNTHESIZING: 'synthesizing',
  SYNTHESIZED: 'synthesized',
  FAILED: 'failed',
};

export const AI_PROVIDERS = [
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'openai', label: 'OpenAI GPT-4' },
  { value: 'anthropic', label: 'Anthropic Claude' },
];

// Status badge mappings
export const STATUS_BADGE_CONFIG = {
  // Extraction status
  success: { label: 'Success', className: 'badge-success' },
  failed: { label: 'Failed', className: 'badge-error' },
  pending: { label: 'Pending', className: 'badge-pending' },

  // Transcription status
  not_transcribed: { label: 'Not Transcribed', className: 'badge-pending' },
  transcribing: { label: 'Transcribing...', className: 'badge-warning' },
  transcribed: { label: 'Transcribed', className: 'badge-transcribed' },

  // AI processing status
  not_processed: { label: 'Not Processed', className: 'badge-pending' },
  processing: { label: 'Processing...', className: 'badge-warning' },
  processed: { label: 'Processed', className: 'badge-processed' },

  // Audio prompt status
  not_generated: { label: 'Not Generated', className: 'badge-pending' },
  generating: { label: 'Generating...', className: 'badge-warning' },
  generated: { label: 'Generated', className: 'badge-success' },

  // Synthesis status
  not_synthesized: { label: 'Not Synthesized', className: 'badge-pending' },
  synthesizing: { label: 'Synthesizing...', className: 'badge-warning' },
  synthesized: { label: 'Synthesized', className: 'badge-success' },
};
