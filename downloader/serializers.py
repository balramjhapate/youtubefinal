from rest_framework import serializers
from .models import VideoDownload, AIProviderSettings, VoiceProfile


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


class VoiceProfileSerializer(serializers.ModelSerializer):
    """Serializer for Voice Profiles"""
    reference_audio_url = serializers.SerializerMethodField()

    class Meta:
        model = VoiceProfile
        fields = [
            'id', 'name', 'reference_audio', 'reference_audio_url',
            'reference_text', 'embedding_path', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'embedding_path']

    def get_reference_audio_url(self, obj):
        """Get full URL for reference audio"""
        if obj.reference_audio:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.reference_audio.url)
            return obj.reference_audio.url
        return None


class VoiceProfileListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views - includes audio URL for playback"""
    reference_audio_url = serializers.SerializerMethodField()

    class Meta:
        model = VoiceProfile
        fields = ['id', 'name', 'reference_text', 'reference_audio_url', 'created_at']

    def get_reference_audio_url(self, obj):
        """Get full URL for reference audio"""
        if obj.reference_audio:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.reference_audio.url)
            return obj.reference_audio.url
        return None


class VideoDownloadSerializer(serializers.ModelSerializer):
    """Full serializer for Video Downloads"""
    voice_profile_name = serializers.SerializerMethodField()
    local_file_url = serializers.SerializerMethodField()
    synthesized_audio_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoDownload
        fields = [
            # Core fields
            'id', 'url', 'video_id', 'created_at', 'updated_at',
            # Content
            'title', 'original_title', 'description', 'original_description',
            # Media
            'video_url', 'cover_url', 'local_file', 'local_file_url', 'is_downloaded',
            # Extraction
            'extraction_method', 'status', 'error_message',
            # AI Processing
            'ai_processing_status', 'ai_processed_at', 'ai_summary', 'ai_tags', 'ai_error_message',
            # Transcription
            'transcription_status', 'transcript', 'transcript_hindi',
            'transcript_language', 'transcript_started_at', 'transcript_processed_at',
            'transcript_error_message',
            # Audio Prompt
            'audio_prompt_status', 'audio_generation_prompt',
            'audio_prompt_generated_at', 'audio_prompt_error',
            # Synthesis
            'voice_profile', 'voice_profile_name', 'synthesized_audio',
            'synthesized_audio_url', 'synthesis_status', 'synthesis_error',
        ]
        read_only_fields = [
            'id', 'video_id', 'created_at', 'updated_at',
            'ai_processed_at', 'transcript_started_at', 'transcript_processed_at',
            'audio_prompt_generated_at'
        ]

    def get_voice_profile_name(self, obj):
        """Get voice profile name"""
        if obj.voice_profile:
            return obj.voice_profile.name
        return None

    def get_local_file_url(self, obj):
        """Get full URL for local file"""
        if obj.local_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.local_file.url)
            return obj.local_file.url
        return None

    def get_synthesized_audio_url(self, obj):
        """Get full URL for synthesized audio"""
        if obj.synthesized_audio:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.synthesized_audio.url)
            return obj.synthesized_audio.url
        return None


class VideoDownloadListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views"""
    voice_profile_name = serializers.SerializerMethodField()
    local_file_url = serializers.SerializerMethodField()
    synthesized_audio_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoDownload
        fields = [
            'id', 'url', 'video_id', 'title', 'cover_url', 'video_url',
            'status', 'extraction_method', 'is_downloaded', 'local_file_url',
            'transcription_status', 'ai_processing_status',
            'audio_prompt_status', 'synthesis_status',
            'voice_profile', 'voice_profile_name', 'synthesized_audio_url',
            'created_at'
        ]

    def get_voice_profile_name(self, obj):
        if obj.voice_profile:
            return obj.voice_profile.name
        return None

    def get_local_file_url(self, obj):
        if obj.local_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.local_file.url)
            return obj.local_file.url
        return None

    def get_synthesized_audio_url(self, obj):
        if obj.synthesized_audio:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.synthesized_audio.url)
            return obj.synthesized_audio.url
        return None


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


class AudioPromptGenerateSerializer(serializers.Serializer):
    """Serializer for audio prompt generation"""
    video_id = serializers.IntegerField(required=True, help_text="Video ID")


class SynthesizeAudioSerializer(serializers.Serializer):
    """Serializer for audio synthesis request"""
    text = serializers.CharField(required=True, help_text="Text to synthesize")
    profile_id = serializers.IntegerField(required=True, help_text="Voice profile ID")
    video_id = serializers.IntegerField(required=False, help_text="Optional video ID to link")


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
