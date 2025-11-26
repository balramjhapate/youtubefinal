from rest_framework import serializers
from .models import VideoDownload, AIProviderSettings, ClonedVoice


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

class ClonedVoiceSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ClonedVoice
        fields = ['id', 'name', 'file', 'file_url', 'created_at']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class VideoDownloadSerializer(serializers.ModelSerializer):
    """Full serializer for Video Downloads"""
    local_file_url = serializers.SerializerMethodField()

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


class VideoDownloadListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views"""
    local_file_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoDownload
        fields = [
            'id', 'url', 'video_id', 'title', 'cover_url', 'video_url',
            'status', 'extraction_method', 'is_downloaded', 'local_file_url',
            'transcription_status', 'ai_processing_status',
            'created_at'
        ]

    def get_local_file_url(self, obj):
        if obj.local_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.local_file.url)
            return obj.local_file.url
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
    failed = serializers.IntegerField()
