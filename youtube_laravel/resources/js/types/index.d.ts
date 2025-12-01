import { InertiaLinkProps } from '@inertiajs/react';
import { LucideIcon } from 'lucide-react';

export interface Auth {
    user: User | null;
}

export interface BreadcrumbItem {
    title: string;
    href: string;
}

export interface NavGroup {
    title: string;
    items: NavItem[];
}

export interface NavItem {
    title: string;
    href: NonNullable<InertiaLinkProps['href']>;
    icon?: LucideIcon | null;
    isActive?: boolean;
}

export interface SharedData {
    name: string;
    quote: { message: string; author: string };
    auth: Auth;
    sidebarOpen: boolean;
    [key: string]: unknown;
}

export interface User {
    id: number;
    name: string;
    email: string;
    avatar?: string;
    email_verified_at: string | null;
    two_factor_enabled?: boolean;
    created_at: string;
    updated_at: string;
    [key: string]: unknown; // This allows for additional properties...
}

export interface VideoDownload {
    id: number;
    url: string;
    video_id: string | null;
    title: string | null;
    original_title: string | null;
    description: string | null;
    original_description: string | null;
    video_url: string | null;
    cover_url: string | null;
    local_file: string | null;
    is_downloaded: boolean;
    duration: number;
    extraction_method: string | null;
    status: 'success' | 'failed' | 'pending';
    error_message: string | null;
    ai_processing_status:
        | 'not_processed'
        | 'processing'
        | 'processed'
        | 'failed';
    ai_processed_at: string | null;
    ai_summary: string | null;
    ai_tags: string | null;
    ai_error_message: string | null;
    transcription_status:
        | 'not_transcribed'
        | 'transcribing'
        | 'transcribed'
        | 'failed';
    transcript: string | null;
    transcript_hindi: string | null;
    transcript_optimized: string | null;
    transcript_clean_script: string | null;
    transcript_language: string | null;
    transcript_started_at: string | null;
    transcript_processed_at: string | null;
    transcript_error_message: string | null;
    audio_prompt_status:
        | 'not_generated'
        | 'generating'
        | 'generated'
        | 'failed';
    audio_generation_prompt: string | null;
    audio_prompt_generated_at: string | null;
    audio_prompt_error: string | null;
    processing_v2_status: string;
    processing_v2_current_step: string | null;
    processing_v2_log: Record<string, unknown> | null;
    processing_v2_started_at: string | null;
    processing_v2_completed_at: string | null;
    step_download_status: string;
    step_transcription_status: string;
    step_ai_enhancement_status: string;
    step_script_generation_status: string;
    step_tts_synthesis_status: string;
    step_final_video_status: string;
    step_upload_sync_status: string;
    visual_analysis: Record<string, unknown> | null;
    synthesized_audio_path: string | null;
    synthesized_at: string | null;
    synthesis_error: string | null;
    final_video_path: string | null;
    created_at: string;
    updated_at: string;
}
