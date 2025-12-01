<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('video_downloads', function (Blueprint $table) {
            $table->id();
            $table->string('url', 500);
            $table->string('video_id', 100)->nullable()->unique();
            
            // Content
            $table->string('title', 500)->nullable();
            $table->string('original_title', 500)->nullable();
            $table->text('description')->nullable();
            $table->text('original_description')->nullable();
            
            // Media
            $table->string('video_url', 1000)->nullable();
            $table->string('cover_url', 1000)->nullable();
            $table->string('local_file')->nullable();
            $table->boolean('is_downloaded')->default(false);
            $table->integer('duration')->default(0);
            
            // Metadata
            $table->string('extraction_method', 20)->nullable();
            $table->enum('status', ['success', 'failed', 'pending'])->default('pending');
            $table->text('error_message')->nullable();
            
            // AI Processing
            $table->enum('ai_processing_status', [
                'not_processed', 'processing', 'processed', 'failed'
            ])->default('not_processed');
            $table->timestamp('ai_processed_at')->nullable();
            $table->text('ai_summary')->nullable();
            $table->string('ai_tags', 500)->nullable();
            $table->text('ai_error_message')->nullable();
            
            // Transcription
            $table->enum('transcription_status', [
                'not_transcribed', 'transcribing', 'transcribed', 'failed'
            ])->default('not_transcribed');
            $table->text('transcript')->nullable();
            $table->text('transcript_hindi')->nullable();
            $table->string('transcript_language', 10)->nullable();
            $table->timestamp('transcript_started_at')->nullable();
            $table->timestamp('transcript_processed_at')->nullable();
            $table->text('transcript_error_message')->nullable();
            
            // Audio Prompt
            $table->enum('audio_prompt_status', [
                'not_generated', 'generating', 'generated', 'failed'
            ])->default('not_generated');
            $table->text('audio_generation_prompt')->nullable();
            $table->timestamp('audio_prompt_generated_at')->nullable();
            $table->text('audio_prompt_error')->nullable();
            
            // Processing V2
            $table->string('processing_v2_status', 50)->default('not_started');
            $table->string('processing_v2_current_step', 100)->nullable();
            $table->text('processing_v2_log')->nullable();
            $table->timestamp('processing_v2_started_at')->nullable();
            $table->timestamp('processing_v2_completed_at')->nullable();
            
            // Step-specific statuses
            $table->string('step_download_status', 20)->default('pending');
            $table->string('step_transcription_status', 20)->default('pending');
            $table->string('step_ai_enhancement_status', 20)->default('pending');
            $table->string('step_script_generation_status', 20)->default('pending');
            $table->string('step_tts_synthesis_status', 20)->default('pending');
            $table->string('step_final_video_status', 20)->default('pending');
            $table->string('step_upload_sync_status', 20)->default('pending');
            
            // Additional fields for enhanced workflow
            $table->text('transcript_optimized')->nullable(); // AI-optimized transcript
            $table->text('transcript_clean_script')->nullable(); // Clean script for TTS
            $table->text('visual_analysis')->nullable(); // JSON: Visual frame analysis
            $table->string('synthesized_audio_path')->nullable(); // Google TTS audio file path
            $table->timestamp('synthesized_at')->nullable();
            $table->text('synthesis_error')->nullable();
            
            $table->timestamps();
            
            $table->index('status');
            $table->index('transcription_status');
            $table->index('ai_processing_status');
            $table->index('created_at');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('video_downloads');
    }
};
