import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from .models import VideoDownload, AIProviderSettings
from .utils import _call_gemini_api, _call_openai_api, _call_anthropic_api

@api_view(['POST'])
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
                # Override provider if passed in request, otherwise use settings default
                # But actually, the frontend passes the selected provider, so we should try to use that
                # However, we need the API key. Assuming the API key in settings is valid for the selected provider
                # OR we might need separate keys for separate providers. 
                # For now, let's assume the settings object stores the key for the *active* provider.
                # If the user selects a different provider in frontend than what's in settings, it might fail if the key doesn't match.
                # To be safe, let's use the provider from settings if the key is there, 
                # OR check if the frontend provider matches the settings provider.
                
                # Simplified logic: Use the provider from request, but use the key from settings.
                # Ideally, we should have keys for each service. 
                # For this MVP, we'll assume the user has configured the backend for the provider they want to use,
                # or that the key works (which is unlikely if switching between Gemini/OpenAI).
                
                # Let's stick to the provider in settings to ensure the key is correct.
                # If frontend sends a different provider, we'll warn or just use the settings one.
                # Actually, let's trust the settings object's provider for the key.
                provider = settings_obj.provider
                
        except Exception as e:
            return Response({'error': 'AI Provider settings not found'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not api_key:
             return Response({'error': 'AI Provider API key not configured'}, status=status.HTTP_400_BAD_REQUEST)

        # 5. Call AI API
        result = None
        if provider == 'gemini':
            result = _call_gemini_api(api_key, system_prompt, final_message)
        elif provider == 'openai':
            result = _call_openai_api(api_key, system_prompt, final_message)
        elif provider == 'anthropic':
            result = _call_anthropic_api(api_key, system_prompt, final_message)
        else:
            return Response({'error': f'Unsupported provider: {provider}'}, status=status.HTTP_400_BAD_REQUEST)

        if result['status'] == 'success':
            return Response({'script': result['prompt']})
        else:
            return Response({'error': result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
