import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from ..model import VideoDownload, AIProviderSettings
from ..pipeline.utils import _call_gemini_api, _call_openai_api

@api_view(['POST'])
@permission_classes([AllowAny])
def generate_script(request):
    """
    Generate a script based on selected videos and a user prompt.
    """
    try:
        data = request.data
        video_ids = data.get('video_ids', [])
        user_prompt = data.get('prompt', '')
        provider = data.get('provider', 'gemini')
        
        if not user_prompt:
            return Response({'error': 'Prompt is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 1. Fetch Context from Videos
        context_parts = []
        if video_ids:
            videos = VideoDownload.objects.filter(id__in=video_ids)
            for video in videos:
                video_context = f"--- VIDEO: {video.title} ---\n"
                video_context += f"Description: {video.description}\n"
                if video.ai_summary:
                    video_context += f"Summary: {video.ai_summary}\n"
                if video.transcript:
                    # Limit transcript length to avoid token limits
                    video_context += f"Transcript: {video.transcript[:3000]}...\n"
                context_parts.append(video_context)
        
        full_context = "\n\n".join(context_parts)
        
        # 2. Construct System Prompt
        system_prompt = """You are an expert scriptwriter and content strategist. 
Your task is to generate a high-quality script based on the provided context videos and the user's specific instructions.

GUIDELINES:
- Analyze the provided video context (transcripts, summaries, descriptions).
- Follow the user's prompt strictly regarding style, format, and length.
- If the user asks for a specific platform format (e.g., YouTube, TikTok, LinkedIn), adhere to best practices for that platform.
- Output ONLY the requested script/content. Do not include conversational filler like "Here is your script"."""

        # 3. Construct Final User Message
        final_message = f"""User Instructions:
{user_prompt}

Context Videos:
{full_context}

Please generate the script now."""

        # 4. Get AI Provider Settings
        api_key = None
        try:
            settings_obj = AIProviderSettings.objects.first()
            if settings_obj and settings_obj.api_key:
                api_key = settings_obj.api_key
                # Use the provider from request if provided, otherwise use settings default
                # If frontend sends a different provider, we'll use the request provider
                # but the API key must be valid for that provider
                if not provider or provider == 'gemini':
                    # Default to settings provider if not specified or if gemini
                    provider = settings_obj.provider or 'gemini'
            else:
                # No settings found, but we can still try with the provider from request
                # if the user has configured environment variables or other settings
                pass
                
        except Exception as e:
            import traceback
            print(f"Error getting AI settings: {e}")
            print(traceback.format_exc())
            # Don't fail here, continue and check if api_key is set below

        if not api_key:
            return Response({
                'error': 'AI Provider API key not configured. Please configure your AI provider settings in the Settings page.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 5. Call AI API
        result = None
        if provider == 'gemini':
            result = _call_gemini_api(api_key, system_prompt, final_message)
        elif provider == 'openai':
            result = _call_openai_api(api_key, system_prompt, final_message)

        else:
            return Response({'error': f'Unsupported provider: {provider}'}, status=status.HTTP_400_BAD_REQUEST)

        if result['status'] == 'success':
            return Response({'script': result['prompt']})
        else:
            return Response({'error': result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
