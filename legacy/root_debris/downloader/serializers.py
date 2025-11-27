from rest_framework import serializers
from .models import VideoDownload, AIProviderSettings, ClonedVoice, CloudinarySettings, GoogleSheetsSettings


class AIProviderSettingsSerializer(serializers.ModelSerializer):
    """Serializer for AI Provider Settings"""

    class Meta:
        model = AIProviderSettings
        fields = ['id', 'provider', 'api_key']

    def to_representation(self, instance):
        """Mask API key in responses"""
        data = super().to_representation(instance)
        if data.get('api_key'):
            # Show only last 4 characters
            api_key = data['api_key']
            if len(api_key) > 4:
                data['api_key_masked'] = '*' * (len(api_key) - 4) + api_key[-4:]
            else:
                data['api_key_masked'] = '*' * len(api_key)
        return data


class CloudinarySettingsSerializer(serializers.ModelSerializer):
    """Serializer for Cloudinary Settings"""

    class Meta:
        model = CloudinarySettings
        fields = ['id', 'cloud_name', 'api_key', 'api_secret', 'enabled']

    def to_representation(self, instance):
        """Mask API key and secret in responses"""
        data = super().to_representation(instance)
        if data.get('api_key'):
            api_key = data['api_key']
            if len(api_key) > 4:
                data['api_key_masked'] = '*' * (len(api_key) - 4) + api_key[-4:]
            else:
                data['api_key_masked'] = '*' * len(api_key)
        if data.get('api_secret'):
            api_secret = data['api_secret']
            if len(api_secret) > 4:
                data['api_secret_masked'] = '*' * (len(api_secret) - 4) + api_secret[-4:]
            else:
                data['api_secret_masked'] = '*' * len(api_secret)
        return data


class GoogleSheetsSettingsSerializer(serializers.ModelSerializer):
    """Serializer for Google Sheets Settings"""

    class Meta:
        model = GoogleSheetsSettings
        fields = ['id', 'spreadsheet_id', 'sheet_name', 'credentials_json', 'enabled']

    def to_representation(self, instance):
        """Mask credentials JSON in responses"""
        data = super().to_representation(instance)
        if data.get('credentials_json'):
            # Don't show credentials JSON in responses for security
            data['credentials_json'] = '***hidden***'
        return data

class ClonedVoiceSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ClonedVoice
        fields = ['id', 'name', 'file', 'file_url', 'is_default', 'created_at']
        read_only_fields = ['created_at']
    
    def get_file_url(self, obj):
        if obj.file:
            try:
                request = self.context.get('request')
                if request:
                    try:
                        return request.build_absolute_uri(obj.file.url)
                    except Exception:
                        # Fallback if build_absolute_uri fails
                        return obj.file.url
                return obj.file.url
            except Exception:
                # Fallback if file.url fails
                return None
        return None


class VideoDownloadSerializer(serializers.ModelSerializer):
    """Full serializer for Video Downloads"""
    local_file_url = serializers.SerializerMethodField()
    voice_removed_video_url = serializers.SerializerMethodField()
    final_processed_video_url = serializers.SerializerMethodField()
    # Use SerializerMethodField for new fields to avoid database queries if migration hasn't been run
    duration = serializers.SerializerMethodField()
    script_status = serializers.SerializerMethodField()
    hindi_script = serializers.SerializerMethodField()
    clean_script_for_tts = serializers.SerializerMethodField()
    script_error_message = serializers.SerializerMethodField()
    script_generated_at = serializers.SerializerMethodField()
    tts_speed = serializers.SerializerMethodField()
    tts_temperature = serializers.SerializerMethodField()
    tts_repetition_penalty = serializers.SerializerMethodField()
    synthesized_audio_url = serializers.SerializerMethodField()
    review_status = serializers.SerializerMethodField()
    review_notes = serializers.SerializerMethodField()
    reviewed_at = serializers.SerializerMethodField()

    class Meta:
        model = VideoDownload
        fields = [
            # Core fields
            'id', 'url', 'video_id', 'video_source', 'created_at', 'updated_at',
            # Content
            'title', 'original_title', 'description', 'original_description',
            # Media
            'video_url', 'cover_url', 'local_file', 'local_file_url', 'is_downloaded', 'duration', 
            'voice_removed_video', 'voice_removed_video_url', 'final_processed_video', 'final_processed_video_url',
            # Extraction
            'extraction_method', 'status', 'error_message',
            # AI Processing
            'ai_processing_status', 'ai_processed_at', 'ai_summary', 'ai_tags', 'ai_error_message',
            # Transcription
            'transcription_status', 'transcript', 'transcript_without_timestamps', 'transcript_hindi',
            'transcript_language', 'transcript_started_at', 'transcript_processed_at',
            'transcript_error_message',
            # Script Generation
            'script_status', 'hindi_script', 'clean_script_for_tts', 'script_error_message', 'script_generated_at',
            # TTS Parameters
            'tts_speed', 'tts_temperature', 'tts_repetition_penalty',
            # Synthesis
            'synthesis_status', 'synthesis_error', 'synthesized_audio', 'synthesized_audio_url', 'voice_profile',
            # Review
            'review_status', 'review_notes', 'reviewed_at',
            # Cloudinary
            'cloudinary_url', 'cloudinary_uploaded_at',
            # Generated Metadata
            'generated_title', 'generated_description', 'generated_tags',
            # Google Sheets
            'google_sheets_synced', 'google_sheets_synced_at',
        ]
        read_only_fields = [
            'id', 'video_id', 'created_at', 'updated_at',
            'ai_processed_at', 'transcript_started_at', 'transcript_processed_at',
        ]

    def get_local_file_url(self, obj):
        """Get full URL for local file"""
        if obj.local_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.local_file.url)
            return obj.local_file.url
        return None
    
    def get_voice_removed_video_url(self, obj):
        """Get full URL for voice removed video file"""
        if obj.voice_removed_video:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.voice_removed_video.url)
            return obj.voice_removed_video.url
        return obj.voice_removed_video_url or None
    
    def get_final_processed_video_url(self, obj):
        """Get full URL for final processed video file"""
        if obj.final_processed_video:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.final_processed_video.url)
            return obj.final_processed_video.url
        return obj.final_processed_video_url or None
    
    def get_duration(self, obj):
        """Safely get duration field"""
        try:
            return getattr(obj, 'duration', None)
        except (AttributeError, ValueError):
            return None
    
    def get_script_status(self, obj):
        """Safely get script_status field"""
        try:
            return getattr(obj, 'script_status', 'not_generated')
        except (AttributeError, ValueError):
            return 'not_generated'
    
    def get_hindi_script(self, obj):
        """Safely get hindi_script field"""
        try:
            return getattr(obj, 'hindi_script', '')
        except (AttributeError, ValueError):
            return ''
    
    def get_clean_script_for_tts(self, obj):
        """Get clean script text for TTS (without formatting headers)"""
        from .utils import get_clean_script_for_tts
        try:
            script = getattr(obj, 'hindi_script', '')
            if script:
                return get_clean_script_for_tts(script)
            return ''
        except (AttributeError, ValueError):
            return ''
    
    def get_script_error_message(self, obj):
        """Safely get script_error_message field"""
        try:
            return getattr(obj, 'script_error_message', '')
        except (AttributeError, ValueError):
            return ''
    
    def get_script_generated_at(self, obj):
        """Safely get script_generated_at field"""
        try:
            return getattr(obj, 'script_generated_at', None)
        except (AttributeError, ValueError):
            return None
    
    def get_tts_speed(self, obj):
        """Safely get tts_speed field"""
        try:
            return getattr(obj, 'tts_speed', 1.0)
        except (AttributeError, ValueError):
            return 1.0
    
    def get_tts_temperature(self, obj):
        """Safely get tts_temperature field"""
        try:
            return getattr(obj, 'tts_temperature', 0.75)
        except (AttributeError, ValueError):
            return 0.75
    
    def get_tts_repetition_penalty(self, obj):
        """Safely get tts_repetition_penalty field"""
        try:
            return getattr(obj, 'tts_repetition_penalty', 5.0)
        except (AttributeError, ValueError):
            return 5.0
    
    def get_synthesized_audio_url(self, obj):
        """Get full URL for synthesized audio file"""
        if obj.synthesized_audio:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.synthesized_audio.url)
            return obj.synthesized_audio.url
        return None
    
    def get_review_status(self, obj):
        """Safely get review_status field"""
        try:
            return getattr(obj, 'review_status', 'pending_review')
        except (AttributeError, ValueError):
            return 'pending_review'
    
    def get_review_notes(self, obj):
        """Safely get review_notes field"""
        try:
            return getattr(obj, 'review_notes', '')
        except (AttributeError, ValueError):
            return ''
    
    def get_reviewed_at(self, obj):
        """Safely get reviewed_at field"""
        try:
            return getattr(obj, 'reviewed_at', None)
        except (AttributeError, ValueError):
            return None


class VideoDownloadListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views"""
    local_file_url = serializers.SerializerMethodField()
    # Use SerializerMethodField to avoid database queries if migration hasn't been run
    duration = serializers.SerializerMethodField()
    script_status = serializers.SerializerMethodField()

    class Meta:
        model = VideoDownload
        fields = [
            'id', 'url', 'video_id', 'title', 'cover_url', 'video_url',
            'status', 'extraction_method', 'is_downloaded', 'local_file_url',
            'transcription_status', 'ai_processing_status', 'script_status',
            'duration', 'created_at'
        ]

    def get_local_file_url(self, obj):
        if obj.local_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.local_file.url)
            return obj.local_file.url
        return None
    
    def get_duration(self, obj):
        """Safely get duration field"""
        try:
            return getattr(obj, 'duration', None)
        except (AttributeError, ValueError):
            return None
    
    def get_script_status(self, obj):
        """Safely get script_status field"""
        try:
            return getattr(obj, 'script_status', 'not_generated')
        except (AttributeError, ValueError):
            return 'not_generated'


class VideoExtractSerializer(serializers.Serializer):
    """Serializer for video extraction request"""
    url = serializers.URLField(required=True, help_text="Xiaohongshu video URL")


class VideoTranscribeSerializer(serializers.Serializer):
    """Serializer for transcription request"""
    language = serializers.CharField(required=False, default='auto', help_text="Language code or 'auto'")
    model_size = serializers.ChoiceField(
        required=False,
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help_text="Whisper model size"
    )


class BulkActionSerializer(serializers.Serializer):
    """Serializer for bulk actions"""
    video_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        help_text="List of video IDs"
    )


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_videos = serializers.IntegerField()
    successful_extractions = serializers.IntegerField()
    downloaded_locally = serializers.IntegerField()
    transcribed = serializers.IntegerField()
    ai_processed = serializers.IntegerField()
    audio_prompts_generated = serializers.IntegerField()
    synthesized = serializers.IntegerField()
    failed = serializers.IntegerField()
