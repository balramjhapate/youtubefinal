<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class VideoDownload extends Model
{
    protected $fillable = [
        'url', 'video_id', 'title', 'original_title', 'description',
        'original_description', 'video_url', 'cover_url', 'local_file',
        'is_downloaded', 'duration', 'extraction_method', 'status',
        'error_message', 'ai_processing_status', 'ai_processed_at',
        'ai_summary', 'ai_tags', 'ai_error_message', 'transcription_status',
        'transcript', 'transcript_hindi', 'transcript_language',
        'transcript_started_at', 'transcript_processed_at',
        'transcript_error_message', 'audio_prompt_status',
        'audio_generation_prompt', 'audio_prompt_generated_at',
        'audio_prompt_error', 'processing_v2_status',
        'processing_v2_current_step', 'processing_v2_log',
        'processing_v2_started_at', 'processing_v2_completed_at',
        'step_download_status', 'step_transcription_status',
        'step_ai_enhancement_status', 'step_script_generation_status',
        'step_tts_synthesis_status', 'step_final_video_status',
        'step_upload_sync_status', 'transcript_optimized',
        'transcript_clean_script', 'visual_analysis',
        'synthesized_audio_path', 'synthesized_at', 'synthesis_error',
        'final_video_path',
    ];

    protected function casts(): array
    {
        return [
            'is_downloaded' => 'boolean',
            'duration' => 'integer',
            'ai_processed_at' => 'datetime',
            'transcript_started_at' => 'datetime',
            'transcript_processed_at' => 'datetime',
            'audio_prompt_generated_at' => 'datetime',
            'processing_v2_started_at' => 'datetime',
            'processing_v2_completed_at' => 'datetime',
            'synthesized_at' => 'datetime',
            'processing_v2_log' => 'array',
            'visual_analysis' => 'array',
        ];
    }

    public function isSuccessful(): bool
    {
        return $this->status === 'success';
    }

    public function isAIProcessed(): bool
    {
        return $this->ai_processing_status === 'processed';
    }
}
