"""
Dual Transcription Function - Run both NCA and Whisper for comparison

This module provides a function to run both NCA and Whisper transcription
simultaneously and store results in separate database fields for comparison.
"""

from django.utils import timezone
from django.conf import settings
from . import whisper_transcribe
from .nca_toolkit_client import get_nca_client
from pipeline.utils import extract_audio_from_video, translate_text, _call_gemini_api, _call_openai_api
from model import AIProviderSettings
from downloader.websocket_utils import broadcast_video_update
import os
import json
import re


def enhance_transcript_with_ai(whisper_segments, nca_segments, visual_segments, api_key, provider='gemini'):
    """
    Use AI to merge and enhance transcripts from Whisper, NCA Toolkit, and Visual Analysis.
    Creates a perfect, comprehensive transcript by combining all three sources.
    
    Args:
        whisper_segments: List of segments from Whisper transcription
        nca_segments: List of segments from NCA Toolkit transcription
        visual_segments: List of segments from Visual Analysis
        api_key: AI provider API key
        provider: AI provider ('gemini', 'openai', 'anthropic')
    
    Returns:
        dict: {
            'status': 'success' or 'failed',
            'enhanced_segments': list of enhanced segments,
            'enhanced_text': str (plain text),
            'enhanced_text_with_timestamps': str (with timestamps),
            'error': str (if failed)
        }
    """
    try:
        # Prepare transcript data for AI
        whisper_text = ' '.join([seg.get('text', '') for seg in (whisper_segments or []) if seg.get('text')])
        nca_text = ' '.join([seg.get('text', '') for seg in (nca_segments or []) if seg.get('text')])
        visual_text = ' '.join([seg.get('text', '') for seg in (visual_segments or []) if seg.get('text')])
        
        # Detect if transcripts contain Chinese or mixed languages
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', whisper_text + nca_text + visual_text))
        has_mixed_lang = bool(re.search(r'[a-zA-Z]', whisper_text + nca_text + visual_text)) and bool(re.search(r'[\u0900-\u097F]', whisper_text + nca_text + visual_text))
        
        # Create system prompt - STRICT: Only return transcript in Hindi, no explanations
        system_prompt = """You are a transcript enhancement and translation system. Your ONLY task is to merge transcripts, translate to Hindi (Devanagari script), and return ONLY the enhanced Hindi transcript with timestamps.

CRITICAL RULES:
1. **TRANSLATE ALL CONTENT TO HINDI (Devanagari script)** - Remove ALL Chinese characters, English words, and mixed languages
2. Return ONLY timestamped transcript lines in Hindi (HH:MM:SS format)
3. NO explanatory text, NO notes, NO comments, NO formatting markers
4. NO English text mixed in, NO Chinese characters (哥哥, etc.), NO pinyin, NO mixed languages
5. NO lines starting with "Here's", "Since", "Note:", "**", or any explanatory phrases
6. Format: HH:MM:SS followed by Hindi transcript text (Devanagari script only)
7. Do NOT add any introductory sentences, explanations, or notes
8. **Translate ALL words properly - do not skip any words or meanings**
9. **If original has Chinese characters (like 哥哥), translate to appropriate Hindi (like भैया or बड़ा भाई)**
10. **If original has English words, translate them to Hindi**

Example of CORRECT output (Hindi only):
00:00:00 यहां बहुत अंधेरा है
00:00:05 हम जल्दी चलते हैं
00:00:10 तुरंत ही घर पहुँचने वाले हैं

Example of WRONG output (DO NOT DO THIS):
Here's the enhanced transcript...
00:00:00 哥哥 यहां बहुत अंधेरा है (mixed Chinese/Hindi)
00:00:05 Here is the text (English)
**Note:** This combines...
Since no visual analysis..."""

        # Create user message with all three transcripts
        user_message = f"""Merge these transcripts into one enhanced transcript and translate EVERYTHING to Hindi (Devanagari script). Remove ALL Chinese characters, English words, and mixed languages. Return ONLY timestamped Hindi lines, nothing else.

WHISPER TRANSCRIPT:
{whisper_text if whisper_text else '(No Whisper transcript available)'}

NCA TOOLKIT TRANSCRIPT:
{nca_text if nca_text else '(No NCA transcript available)'}

VISUAL ANALYSIS TRANSCRIPT:
{visual_text if visual_text else '(No visual analysis available)'}

**CRITICAL INSTRUCTIONS:**
1. **Translate ALL content to Hindi (Devanagari script)** - Remove Chinese characters (哥哥 → भैया/बड़ा भाई), English words, etc.
2. **Preserve ALL words and meanings** - Do not skip any words during translation
3. **Merge the best parts from all three sources** - Use the most accurate and complete version
4. **Maintain timestamps** - Keep the original timestamps from segments
5. **Return ONLY timestamped Hindi lines** - NO explanations, NO notes, NO formatting

Return ONLY the enhanced Hindi transcript in this format (NO explanations, NO notes, NO formatting, NO mixed languages):
00:00:00 यहां बहुत अंधेरा है
00:00:05 हम जल्दी चलते हैं
00:00:10 तुरंत ही घर पहुँचने वाले हैं"""

        # Call AI API
        if provider == 'gemini':
            result = _call_gemini_api(api_key, system_prompt, user_message)
        elif provider == 'openai':
            result = _call_openai_api(api_key, system_prompt, user_message)

        else:
            return {
                'status': 'failed',
                'enhanced_segments': [],
                'enhanced_text': '',
                'enhanced_text_with_timestamps': '',
                'error': f'Unknown AI provider: {provider}'
            }
        
        if result.get('status') != 'success':
            return {
                'status': 'failed',
                'enhanced_segments': [],
                'enhanced_text': '',
                'enhanced_text_with_timestamps': '',
                'error': result.get('error', 'AI enhancement failed')
            }
        
        enhanced_text = result.get('prompt', '').strip()
        
        # AGGRESSIVE filtering: Remove ALL explanatory/meta text, formatting, and non-transcript content
        # Remove formatting markers first
        enhanced_text = re.sub(r'\*\*.*?\*\*', '', enhanced_text)  # Remove **bold** markers
        enhanced_text = re.sub(r'\*.*?\*', '', enhanced_text)  # Remove *italic* markers
        enhanced_text = re.sub(r'\[.*?\]', '', enhanced_text)  # Remove [notes] (but keep TTS markup tags added later)
        
        # Remove Chinese characters and ensure only Hindi (Devanagari) script
        # Remove all Chinese characters (哥哥, etc.) - they should have been translated
        enhanced_text = re.sub(r'[\u4e00-\u9fff]+', '', enhanced_text)  # Remove all Chinese characters
        # Remove standalone English words (but keep numbers and timestamps)
        # Only remove if it's clearly not part of a timestamp
        enhanced_text = re.sub(r'\b[A-Za-z]{2,}\b', '', enhanced_text)  # Remove English words (2+ letters)
        # Clean up extra spaces
        enhanced_text = re.sub(r'\s+', ' ', enhanced_text).strip()
        enhanced_text = re.sub(r'\(.*?\)', '', enhanced_text)  # Remove (parentheses notes) - but be careful, might remove valid content
        
        # Remove Chinese characters and pinyin (keep only if it's part of original transcript)
        # First, identify and remove explanatory patterns that contain Chinese
        enhanced_text = re.sub(r'\([^)]*[\u4e00-\u9fff]+[^)]*\)', '', enhanced_text)  # Remove (Chinese text)
        enhanced_text = re.sub(r'[（][^）]*[\u4e00-\u9fff]+[^）]*[）]', '', enhanced_text)  # Remove (Chinese text) with Chinese brackets
        
        # Remove lines that are entirely explanatory (Hindi/English)
        explanatory_patterns = [
            # Hindi patterns
            r'यहां प्रदत्त.*स्रोतों',
            r'यहां प्रदत्त स्रोतों का संयोजन',
            r'चूँकि कोई दृश्य विश्लेषण',
            r'चूँकि कोई.*दृश्य.*विश्लेषण.*प्रदान.*नहीं',
            r'प्रतिलेख.*ऑडियो-आधारित.*पाठ.*परिष्कृत',
            r'प्रतिलेख.*परिष्कृत.*करने.*पर.*केंद्रित',
            r'यहां.*उन्नत.*प्रतिलेख',
            r'स्रोतों.*संयोजन.*सुधार',
            r'यहां.*दिया गया है',
            r'यहां.*प्रदान.*किया',
            r'ठीक है.*मैं.*उन्नत',
            r'मैं.*संयोजित.*करूँगा',
            r'व्याकरण.*विराम',
            r'संवर्द्धन.*व्याख्या',
            r'मर्ज.*किए.*गए',
            # English patterns
            r'Here\'?s the enhanced transcript',
            r'Here is the enhanced transcript',
            r'Here\'?s.*enhanced.*transcript.*combining',
            r'Here\'?s.*enhanced.*transcript.*combining.*correcting',
            r'combining.*correcting.*provided sources',
            r'combining and correcting the provided sources',
            r'Since.*no.*visual.*analysis.*provided',
            r'Since.*visual.*analysis.*was.*not.*provided',
            r'Since.*no.*visual.*analysis.*was.*provided',
            r'transcript.*focuses.*on.*refining',
            r'focuses.*on.*refining.*audio-based.*text',
            r'transcript.*focuses.*on.*refining.*audio-based.*text',
            r'enhanced transcript.*combining',
            r'provided sources',
            r'audio-based text',
            r'Note:',
            r'Note\s*:',
            r'\*\*.*?Note.*?\*\*',
            r'Explanation:',
            r'Enhancement explanation:',
        ]
        
        # Remove ALL introductory/explanatory text blocks (multi-line)
        intro_patterns = [
            r'^.*?Here\'?s.*?enhanced.*?transcript.*?\.\s*',
            r'^.*?Here is.*?enhanced.*?transcript.*?\.\s*',
            r'^.*?combining.*?correcting.*?provided.*?sources.*?\.\s*',
            r'^.*?Since.*?no.*?visual.*?analysis.*?provided.*?\.\s*',
            r'^.*?Since.*?visual.*?analysis.*?was.*?not.*?provided.*?\.\s*',
            r'^.*?transcript.*?focuses.*?on.*?refining.*?audio-based.*?text.*?\.\s*',
            r'^.*?यहां.*?प्रदत्त.*?स्रोतों.*?संयोजन.*?सुधार.*?।\s*',
            r'^.*?चूँकि.*?कोई.*?दृश्य.*?विश्लेषण.*?प्रदान.*?नहीं.*?।\s*',
            r'^.*?प्रतिलेख.*?ऑडियो-आधारित.*?पाठ.*?परिष्कृत.*?।\s*',
            r'^.*?ठीक है.*?मैं.*?उन्नत.*?सटीक.*?व्यापक.*?प्रतिलेख.*?।\s*',
            r'^.*?मैं.*?संयोजित.*?करूँगा.*?।\s*',
            r'^.*?\*\*.*?उन्नत.*?प्रतिलेख.*?\*\*.*?\s*',
            r'^.*?\*\*.*?संवर्द्धन.*?व्याख्या.*?\*\*.*?\s*',
        ]
        
        for pattern in intro_patterns:
            enhanced_text = re.sub(pattern, '', enhanced_text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        
        # Remove lines that start with explanatory phrases (even if they have timestamps)
        lines_to_remove = []
        for pattern in explanatory_patterns:
            enhanced_text = re.sub(rf'^\d{{2}}:\d{{2}}:\d{{2}}\s+.*?{pattern}.*?$', '', enhanced_text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove Chinese pinyin patterns (text in parentheses with pinyin)
        enhanced_text = re.sub(r'\([A-Za-z\s]+\)', '', enhanced_text)  # Remove (English pinyin)
        
        # Clean up extra whitespace but preserve line structure
        enhanced_text = re.sub(r'[ \t]+', ' ', enhanced_text)  # Multiple spaces -> single space
        enhanced_text = re.sub(r'\n\s*\n+', '\n', enhanced_text)  # Multiple newlines -> single newline
        enhanced_text = enhanced_text.strip()
        
        # Parse enhanced transcript into segments
        # STRATEGY: Extract ONLY lines that match timestamp pattern, ignore everything else
        enhanced_segments = []
        enhanced_text_with_timestamps_lines = []
        enhanced_plain_text = ''
        
        # Split into lines and extract ONLY timestamped lines
        lines = enhanced_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # ONLY process lines that start with timestamp pattern HH:MM:SS
            timestamp_match = re.match(r'^(\d{2}):(\d{2}):(\d{2})\s+(.+)$', line)
            if timestamp_match:
                hours, minutes, seconds = map(int, timestamp_match.groups()[:3])
                text = timestamp_match.group(4).strip()
                
                # AGGRESSIVE cleaning: Remove ALL non-transcript content
                # CRITICAL: Remove ALL Chinese characters (哥哥, etc.) - they should have been translated to Hindi
                text = re.sub(r'[\u4e00-\u9fff]+', '', text)  # Remove all Chinese characters
                # Remove text in parentheses (pinyin, notes, translations) - but preserve if it's part of dialogue
                # Only remove if it looks like pinyin/translation, not dialogue
                text = re.sub(r'\([^)]*[a-z]{3,}[^)]*\)', '', text, flags=re.IGNORECASE)  # Remove (pinyin/English notes)
                text = re.sub(r'[（][^）]*[a-z]{3,}[^）]*[）]', '', text, flags=re.IGNORECASE)  # Remove Chinese brackets with pinyin
                # Remove formatting markers
                text = re.sub(r'\*\*|\*|\[|\]|_|#', '', text)
                # Remove explanatory phrases
                text = re.sub(r'\b(Note|Explanation|Enhancement|Merged|Combined|Here\'?s|Since|provided sources|audio-based text|संवर्द्धन|व्याख्या|मर्ज):?\s*', '', text, flags=re.IGNORECASE)
                # Remove patterns like "English: translation" 
                text = re.sub(r'[Ee]nglish\s*:?\s*[^।.!?]+', '', text)
                # Remove pinyin patterns (sequences of lowercase romanized Chinese)
                text = re.sub(r'\b([a-z]+[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]+\s*){2,}', '', text, flags=re.IGNORECASE)
                # Remove standalone English words (2+ letters) - but keep numbers and timestamps
                text = re.sub(r'\b[A-Za-z]{2,}\b', '', text)  # Remove English words
                # Clean up multiple spaces
                text = re.sub(r'\s+', ' ', text)
                
                # CRITICAL: Remove any remaining timestamps that might have been captured
                # e.g. if AI output "00:00:00 00:00:05 text"
                text = re.sub(r'\d{1,2}:\d{2}:\d{2}', '', text)
                text = text.strip()
                
                # Skip if text is empty, too short, or is clearly explanatory
                if not text or len(text) < 2:
                    continue
                # Skip if it's clearly an explanatory line
                if any(re.search(pattern, text, re.IGNORECASE) for pattern in explanatory_patterns):
                    continue
                # Skip if it's all English and looks like explanation (not dialogue)
                if re.match(r'^[A-Za-z\s:.,!?\-]+$', text) and len(text) > 30 and not any(word in text.lower() for word in ['said', 'says', 'talking', 'speaking']):
                    continue
                
                timestamp_seconds = hours * 3600 + minutes * 60 + seconds
                
                enhanced_segments.append({
                    'start': timestamp_seconds,
                    'text': text,
                    'timestamp_str': f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                })
                enhanced_text_with_timestamps_lines.append(f"{hours:02d}:{minutes:02d}:{seconds:02d} {text}")
                enhanced_plain_text += text + ' '
            # Skip all lines without timestamps - we only want timestamped transcript lines
        
        enhanced_plain_text = enhanced_plain_text.strip()
        enhanced_text_with_timestamps = '\n'.join(enhanced_text_with_timestamps_lines)
        
        return {
            'status': 'success',
            'enhanced_segments': enhanced_segments,
            'enhanced_text': enhanced_plain_text,
            'enhanced_text_with_timestamps': enhanced_text_with_timestamps,
            'error': None
        }
        
    except Exception as e:
        print(f"Error enhancing transcript with AI: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'failed',
            'enhanced_segments': [],
            'enhanced_text': '',
            'enhanced_text_with_timestamps': '',
            'error': str(e)
        }


def transcribe_video_dual(video_download):
    """
    Run BOTH NCA and Whisper transcription for comparison.
    Stores results in separate database fields.
    
    Args:
        video_download: VideoDownload model instance
    
    Returns:
        dict: {
            'nca_result': dict (NCA transcription result),
            'whisper_result': dict (Whisper transcription result),
            'status': 'success' or 'partial' or 'failed'
        }
    """
    results = {
        'nca_result': None,
        'whisper_result': None,
        'status': 'failed'
    }
    
    # ========== NCA TRANSCRIPTION ==========
    print("\n" + "="*60)
    print("STARTING NCA TRANSCRIPTION")
    print("="*60)
    
    # Check if NCA transcription is enabled in database settings (NOT environment variables)
    settings_obj = AIProviderSettings.objects.first()
    nca_enabled = (
        settings_obj and
        settings_obj.enable_nca_transcription
    )
    
    if nca_enabled:
        nca_client = get_nca_client()
        if nca_client:
            try:
                video_download.transcription_status = 'transcribing'
                video_download.transcript_started_at = timezone.now()
                video_download.save()
                broadcast_video_update(video_download.id, video_instance=video_download)
                
                print("Attempting NCA transcription...")
                
                # Try with video URL first
                if video_download.video_url:
                    nca_result = nca_client.transcribe_video(video_url=video_download.video_url)
                elif video_download.is_downloaded and video_download.local_file:
                    video_path = video_download.local_file.path
                    if os.path.exists(video_path):
                        nca_result = nca_client.transcribe_video(video_file_path=video_path)
                    else:
                        nca_result = {'status': 'failed', 'error': 'Video file not found'}
                else:
                    nca_result = {'status': 'failed', 'error': 'No video URL or file available'}
                
                if nca_result['status'] == 'success':
                    # Process and store NCA results
                    transcript_text = nca_result.get('text', '')
                    
                    # Format timestamps
                    segments = nca_result.get('segments', [])
                    if segments:
                        timestamped_lines = []
                        plain_lines = []
                        for seg in segments:
                            start = seg.get('start', 0)
                            text = seg.get('text', '').strip()
                            if text:
                                hours = int(start // 3600)
                                minutes = int((start % 3600) // 60)
                                seconds = int(start % 60)
                                timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                timestamped_lines.append(f"{timestamp} {text}")
                                plain_lines.append(text)
                        
                        video_download.transcript = '\n'.join(timestamped_lines)
                        video_download.transcript_without_timestamps = ' '.join(plain_lines)
                    else:
                        video_download.transcript = transcript_text
                        video_download.transcript_without_timestamps = transcript_text
                    
                    # Translate to Hindi using AI for better quality and meaning preservation
                    if transcript_text:
                        print("Translating NCA transcript to Hindi using AI (preserves meaning)...")
                        from pipeline.utils import translate_text_with_ai
                        hindi_translation = translate_text_with_ai(transcript_text, target='hi')
                        video_download.transcript_hindi = hindi_translation
                    
                    video_download.transcript_language = nca_result.get('language', 'unknown')
                    video_download.transcription_status = 'transcribed'
                    video_download.transcript_processed_at = timezone.now()
                    video_download.save()
                    broadcast_video_update(video_download.id, video_instance=video_download)
                    
                    results['nca_result'] = nca_result
                    print(f"✓ NCA transcription successful: {len(transcript_text)} chars")
                else:
                    video_download.transcription_status = 'failed'
                    video_download.transcript_error_message = nca_result.get('error', 'Unknown error')
                    video_download.save()
                    print(f"✗ NCA transcription failed: {nca_result.get('error')}")
                    
            except Exception as e:
                print(f"✗ NCA transcription error: {e}")
                video_download.transcription_status = 'failed'
                video_download.transcript_error_message = str(e)
                video_download.save()
    else:
        # Check if NCA is enabled in database settings
        nca_settings_enabled = settings_obj and settings_obj.enable_nca_transcription
        
        if not nca_settings_enabled:
            print("NCA transcription disabled in provider settings, skipping NCA transcription")
            print("  To enable NCA, go to Settings > Analysis Provider Settings and enable 'NCA Toolkit Transcription'")
        else:
            # NCA is enabled in settings but failed - log the error
            error_msg = results.get('nca_result', {}).get('error', 'Unknown error')
            print(f"NCA transcription failed: {error_msg}")
            print("  Check if NCA Toolkit server is running and NCA_API_URL/NCA_API_KEY are configured in settings.py")
    
    # ========== WHISPER TRANSCRIPTION ==========
    print("\n" + "="*60)
    print("STARTING WHISPER TRANSCRIPTION")
    print("="*60)
    
    # Check if Whisper transcription is enabled
    whisper_enabled = (
        settings_obj and
        settings_obj.enable_whisper_transcription
    )
    
    if not whisper_enabled:
        print("Whisper transcription disabled in provider settings, skipping Whisper transcription")
        results['status'] = 'partial' if results.get('nca_result') else 'failed'
        return results
    
    try:
        video_download.whisper_transcription_status = 'transcribing'
        video_download.whisper_transcript_started_at = timezone.now()
        video_download.save()
        broadcast_video_update(video_download.id, video_instance=video_download)
        
        # Ensure video is downloaded
        if not video_download.is_downloaded or not video_download.local_file:
            if video_download.video_url:
                print("Video not downloaded, downloading first...")
                from pipeline.utils import download_file
                file_content = download_file(video_download.video_url)
                if file_content:
                    filename = f"{video_download.video_id or 'video'}_{video_download.pk}.mp4"
                    video_download.local_file.save(filename, file_content, save=True)
                    video_download.is_downloaded = True
                    video_download.save()
                else:
                    raise Exception("Could not download video for Whisper transcription")
            else:
                raise Exception("No video file or URL available for Whisper transcription")
        
        video_path = video_download.local_file.path
        
        if not os.path.exists(video_path):
            raise Exception(f"Video file not found: {video_path}")
        
        # Extract audio
        print(f"Extracting audio from: {video_path}")
        audio_path = extract_audio_from_video(video_path)
        
        if not audio_path:
            raise Exception("Failed to extract audio from video")
        
        try:
            # Get Whisper configuration (default: 'medium' for Mac Mini M4)
            model_size = getattr(settings, 'WHISPER_MODEL_SIZE', 'medium')
            confidence_threshold = getattr(settings, 'WHISPER_CONFIDENCE_THRESHOLD', -1.5)
            retry_enabled = getattr(settings, 'WHISPER_RETRY_WITH_LARGER_MODEL', True)
            
            print(f"Transcribing with Whisper (model: {model_size})...")
            
            # Load model and transcribe
            model = whisper_transcribe.load_whisper_model(model_size)
            whisper_result = whisper_transcribe.transcribe_with_whisper(
                model=model,
                audio_path=audio_path,
                task='transcribe',
                language=None  # Auto-detect
            )
            
            if whisper_result['status'] == 'success':
                # Check confidence and retry if needed
                if retry_enabled and whisper_result.get('segments'):
                    high_conf, low_conf = whisper_transcribe.check_segment_confidence(
                        whisper_result['segments'],
                        threshold=confidence_threshold
                    )
                    
                    if low_conf:
                        print(f"Found {len(low_conf)} low-confidence segments, retrying...")
                        retry_result = whisper_transcribe.retry_low_confidence_segments(
                            audio_path=audio_path,
                            segments=whisper_result['segments'],
                            current_model_name=model_size,
                            threshold=confidence_threshold
                        )
                        
                        if retry_result.get('improved'):
                            print(f"✓ Retry improved {retry_result.get('retry_count')} segments")
                            whisper_result['segments'] = retry_result['segments']
                            whisper_result['text'] = whisper_transcribe.format_segments_to_plain_text(
                                whisper_result['segments']
                            )
                
                # Store Whisper results
                segments = whisper_result.get('segments', [])
                
                # Format timestamps
                video_download.whisper_transcript = whisper_transcribe.format_segments_to_timestamped_text(segments)
                video_download.whisper_transcript_without_timestamps = whisper_result.get('text', '')
                
                # Translate to Hindi using AI for better quality and meaning preservation
                if whisper_result.get('text'):
                    print("Translating Whisper transcript to Hindi using AI (preserves meaning)...")
                    from pipeline.utils import translate_text_with_ai
                    hindi_translation = translate_text_with_ai(whisper_result['text'], target='hi')
                    video_download.whisper_transcript_hindi = hindi_translation
                
                video_download.whisper_transcript_language = whisper_result.get('language', 'unknown')
                video_download.whisper_transcript_segments = segments  # Store raw segments JSON
                video_download.whisper_model_used = model_size
                
                # Calculate average confidence
                if segments:
                    avg_confidence = sum(seg.get('confidence', 0) for seg in segments) / len(segments)
                    video_download.whisper_confidence_avg = avg_confidence
                
                video_download.whisper_transcription_status = 'transcribed'
                video_download.whisper_transcript_processed_at = timezone.now()
                video_download.save()
                
                # Also update main transcription status if Whisper succeeded (use as primary)
                # This ensures the main transcript fields are populated even if NCA failed
                video_download.transcription_status = 'transcribed'
                video_download.transcript = video_download.whisper_transcript
                video_download.transcript_without_timestamps = video_download.whisper_transcript_without_timestamps
                video_download.transcript_hindi = video_download.whisper_transcript_hindi
                video_download.transcript_language = video_download.whisper_transcript_language
                video_download.transcript_processed_at = timezone.now()
                video_download.transcript_error_message = ''  # Clear any previous errors
                video_download.save()
                print(f"✓ Updated main transcription status with Whisper result")
                
                results['whisper_result'] = whisper_result
                print(f"✓ Whisper transcription successful: {len(whisper_result['text'])} chars")
            else:
                raise Exception(whisper_result.get('error', 'Unknown error'))
                
        finally:
            # Clean up audio file
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    print(f"Cleaned up audio file: {audio_path}")
                except Exception as e:
                    print(f"Warning: Could not delete temp audio: {e}")
    
    except Exception as e:
        print(f"✗ Whisper transcription error: {e}")
        video_download.whisper_transcription_status = 'failed'
        video_download.whisper_transcript_error_message = str(e)
        video_download.save()
        import traceback
        traceback.print_exc()
    
    # ========== VISUAL FRAME ANALYSIS (OPTIONAL - for enhanced transcript) ==========
    print("\n" + "="*60)
    print("STARTING VISUAL FRAME ANALYSIS (OPTIONAL - For Enhanced Transcript)")
    print("="*60)
    print("Note: Visual analysis is optional. If it fails, we'll continue with Whisper + NCA only.")
    
    visual_result = None
    visual_available = False
    
    try:
        from . import visual_analysis
        
        # Try to run visual analysis (optional - won't block pipeline if it fails)
        if video_download.is_downloaded and video_download.local_file:
            video_path = video_download.local_file.path
            
            # Detect if video has audio (for reference)
            has_audio = visual_analysis.detect_audio_in_video(video_path)
            video_download.has_audio = has_audio
            video_download.save()
            
            print(f"Audio detected: {has_audio}")
            print("Attempting visual analysis (optional - will continue if it fails)...")
            
            settings_obj = AIProviderSettings.objects.first()
            # Check if visual analysis is enabled
            visual_enabled = (
                settings_obj and
                settings_obj.enable_visual_analysis
            )
            
            if not visual_enabled:
                print("Visual analysis disabled in provider settings, skipping visual analysis")
                visual_available = False
            elif settings_obj:
                # Use the provider selected in settings for visual analysis
                provider = settings_obj.visual_analysis_provider or 'openai'
                api_key = settings_obj.get_api_key(provider)
                
                if api_key and api_key.strip():
                    provider_name = 'OpenAI GPT-4o-mini' if provider == 'openai' else 'Gemini Vision API'
                    print(f"Using {provider_name} for frame analysis...")
                    print(f"Provider: {provider}, API Key configured: {bool(api_key)}")
                    
                    # Calculate reasonable frame extraction parameters based on video duration
                    # Use 1 frame per second for reasonable processing time (max 60 frames for speed)
                    if video_download.duration:
                        # Calculate interval to get approximately 1 frame per second
                        # But cap at 60 frames total for performance (reduced from 200)
                        max_frames = min(int(video_download.duration), 60)
                        # Calculate interval: if we want max_frames frames in duration seconds
                        # interval = duration / max_frames
                        interval = video_download.duration / max_frames if max_frames > 0 else 1.0
                        print(f"Video duration: {video_download.duration}s, extracting {max_frames} frames at {interval:.3f}s intervals")
                    else:
                        # Default: 1 frame per second, max 60 frames
                        max_frames = 60
                        interval = 1.0  # 1 frame per second
                        print(f"Video duration unknown, using default: {max_frames} frames at {interval}s intervals")
                    
                    visual_result = visual_analysis.generate_visual_transcript(
                        video_path=video_path,
                        api_key=api_key,
                        interval=interval,  # Adjusted interval for reasonable frame count
                        max_frames=max_frames  # Limit frames to prevent timeout
                    )
                    
                    if visual_result['status'] == 'success':
                        # Store visual transcript
                        video_download.visual_transcript = visual_result['text_with_timestamps']
                        video_download.visual_transcript_without_timestamps = visual_result['text']
                        video_download.visual_transcript_segments = visual_result['segments']
                        
                        # Translate to Hindi using AI for better quality and meaning preservation
                        print("Translating visual description to Hindi using AI (preserves meaning)...")
                        try:
                            from pipeline.utils import translate_text_with_ai
                            hindi_translation = translate_text_with_ai(visual_result['text'], target='hi')
                            video_download.visual_transcript_hindi = hindi_translation
                        except Exception as trans_error:
                            print(f"⚠ Hindi translation failed for visual transcript: {trans_error}")
                        
                        video_download.save()
                        
                        results['visual_result'] = visual_result
                        visual_available = True
                        print(f"✓ Visual analysis successful: {len(visual_result['text'])} chars")
                    else:
                        error_msg = visual_result.get('error', 'Unknown error')
                        print(f"⚠ Visual analysis failed (continuing without it): {error_msg[:200]}")
                        results['visual_error'] = error_msg
                        visual_available = False
                        
                        # Store error message in video model for admin visibility (non-blocking)
                        if not video_download.transcript_error_message:
                            video_download.transcript_error_message = f"Visual Analysis (Optional) Failed: {error_msg[:500]}"
                        else:
                            video_download.transcript_error_message += f"\nVisual Analysis (Optional) Failed: {error_msg[:500]}"
                        video_download.save()
                        print("→ Continuing pipeline with Whisper + NCA only (visual analysis is optional)")
                else:
                    error_msg = "Neither OpenAI nor Gemini API key configured for visual analysis (optional)."
                    print(f"⚠ {error_msg}")
                    results['visual_error'] = error_msg
                    visual_available = False
                    print("→ Continuing pipeline with Whisper + NCA only (visual analysis is optional)")
            else:
                print("⚠ Video file not found, skipping visual analysis")
                visual_available = False
    except Exception as e:
        print(f"⚠ Visual analysis error (continuing without it): {e}")
        import traceback
        traceback.print_exc()
        visual_available = False
        results['visual_error'] = str(e)
        print("→ Continuing pipeline with Whisper + NCA only (visual analysis is optional)")
    
    # ========== AI-ENHANCED TRANSCRIPT GENERATION ==========
    print("\n" + "="*60)
    print("GENERATING AI-ENHANCED TRANSCRIPT")
    print("="*60)
    
    try:
        # Get AI provider settings
        settings_obj = AIProviderSettings.objects.first()
        if settings_obj:
            # Collect segments from enabled sources only
            whisper_segments = []
            if settings_obj and settings_obj.enable_whisper_transcription:
                if results.get('whisper_result') and results['whisper_result'].get('segments'):
                    whisper_segments = results['whisper_result']['segments']
                elif video_download.whisper_transcript_segments:
                    whisper_segments = video_download.whisper_transcript_segments
            
            nca_segments = []
            if settings_obj and settings_obj.enable_nca_transcription:
                if results.get('nca_result') and results['nca_result'].get('segments'):
                    nca_segments = results['nca_result']['segments']
            
            # If NCA segments not in results, try to parse from stored transcript
            if not nca_segments and video_download.transcript:
                # Try to parse NCA transcript into segments
                lines = video_download.transcript.split('\n')
                for line in lines:
                    match = re.match(r'(\d{2}):(\d{2}):(\d{2})\s+(.+)', line.strip())
                    if match:
                        hours, minutes, seconds = map(int, match.groups()[:3])
                        text = match.group(4)
                        timestamp_seconds = hours * 3600 + minutes * 60 + seconds
                        nca_segments.append({
                            'start': timestamp_seconds,
                            'text': text,
                            'timestamp_str': f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        })
            
            # Get visual segments from visual_result (only if enabled)
            visual_segments = []
            if settings_obj.enable_visual_analysis:
                if visual_result and visual_result.get('status') == 'success' and visual_result.get('segments'):
                    visual_segments = visual_result['segments']
                elif video_download.visual_transcript_segments:
                    visual_segments = video_download.visual_transcript_segments
            
            # Only enhance if we have at least one transcript source (Whisper or NCA required, Visual optional)
            if whisper_segments or nca_segments:
                # Set AI processing status to 'processing' BEFORE starting AI enhancement
                # This ensures frontend can see the status update in real-time
                video_download.ai_processing_status = 'processing'
                video_download.ai_processing_started_at = timezone.now()
                video_download.enhanced_transcript_started_at = timezone.now()
                video_download.save(update_fields=['ai_processing_status', 'ai_processing_started_at', 'enhanced_transcript_started_at'])
                broadcast_video_update(video_download.id, video_instance=video_download)
                print(f"✓ AI Processing status set to 'processing' for video {video_download.id} (before AI enhancement)")
                
                provider = settings_obj.default_provider or settings_obj.provider or 'gemini'
                api_key = settings_obj.get_api_key(provider)
                
                print(f"Enhancing transcript with AI ({provider})...")
                print(f"  Whisper segments: {len(whisper_segments)} {'(enabled)' if settings_obj.enable_whisper_transcription else '(disabled)'}")
                print(f"  NCA segments: {len(nca_segments)} {'(enabled)' if settings_obj.enable_nca_transcription else '(disabled)'}")
                print(f"  Visual segments: {len(visual_segments)} {'(enabled)' if (settings_obj.enable_visual_analysis and visual_segments) else '(disabled or not available)'}")
                
                enhanced_result = None
                if not api_key:
                    print(f"⚠ No API key found for provider {provider}, skipping AI enhancement")
                    enhanced_result = {
                        'status': 'failed',
                        'enhanced_segments': [],
                        'enhanced_text': '',
                        'enhanced_text_with_timestamps': '',
                        'error': 'No API key found for AI enhancement'
                    }
                else:
                    enhanced_result = enhance_transcript_with_ai(
                        whisper_segments=whisper_segments,
                        nca_segments=nca_segments,
                        visual_segments=visual_segments,
                        api_key=api_key,
                        provider=provider
                    )
                
                if enhanced_result and enhanced_result.get('status') == 'success':
                    # Store enhanced transcript AS-IS (no word filtering during transcript generation)
                    # Word filtering will be applied only at final TTS script generation stage
                    print("Storing enhanced transcript (word filtering will be applied at TTS script generation stage)...")
                    video_download.enhanced_transcript = enhanced_result['enhanced_text_with_timestamps']
                    video_download.enhanced_transcript_without_timestamps = enhanced_result['enhanced_text']
                    video_download.enhanced_transcript_segments = enhanced_result['enhanced_segments']
                    
                    # Get the enhanced text for translation check
                    filtered_enhanced_text = enhanced_result['enhanced_text']
                    
                    # Check if enhanced transcript is already in Hindi or needs translation
                    # If it contains Chinese characters or English, translate it
                    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', filtered_enhanced_text))
                    has_english = bool(re.search(r'[a-zA-Z]{3,}', filtered_enhanced_text))  # 3+ letter English words
                    is_hindi = bool(re.search(r'[\u0900-\u097F]', filtered_enhanced_text))
                    
                    if has_chinese or (has_english and not is_hindi):
                        # Translate filtered enhanced transcript to Hindi using AI (preserves meaning)
                        print("Translating filtered enhanced transcript to Hindi using AI (removes Chinese/English, preserves meaning)...")
                        try:
                            from pipeline.utils import translate_text_with_ai
                            hindi_translation = translate_text_with_ai(filtered_enhanced_text, target='hi')
                        except Exception as trans_error:
                            print(f"⚠ Hindi translation failed for enhanced transcript: {trans_error}")
                            hindi_translation = filtered_enhanced_text  # Fallback to original
                    else:
                        # Already in Hindi, use as-is but ensure no Chinese/English remains
                        print("Enhanced transcript is already in Hindi, cleaning any remaining non-Hindi characters...")
                        hindi_translation = filtered_enhanced_text
                        # Remove any remaining Chinese/English characters
                        hindi_translation = re.sub(r'[^\u0900-\u097F\s0-9:।!?.,:;()\-"\']+', '', hindi_translation)
                        hindi_translation = re.sub(r'\s+', ' ', hindi_translation).strip()
                    
                    # Filter out explanatory messages from Hindi translation
                    hindi_explanatory_patterns = [
                        r'यहां प्रदत्त.*स्रोतों',
                        r'यहां प्रदत्त स्रोतों का संयोजन',
                        r'चूँकि कोई दृश्य विश्लेषण',
                        r'चूँकि कोई.*दृश्य.*विश्लेषण.*प्रदान.*नहीं',
                        r'प्रतिलेख.*ऑडियो-आधारित.*पाठ.*परिष्कृत',
                        r'प्रतिलेख.*परिष्कृत.*करने.*पर.*केंद्रित',
                        r'यहां.*उन्नत.*प्रतिलेख',
                        r'स्रोतों.*संयोजन.*सुधार',
                    ]
                    
                    # Split into sentences and filter
                    hindi_lines = hindi_translation.split('\n')
                    filtered_hindi_lines = []
                    for line in hindi_lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Check if line is explanatory
                        is_explanatory = False
                        for pattern in hindi_explanatory_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                is_explanatory = True
                                break
                        
                        if not is_explanatory:
                            filtered_hindi_lines.append(line)
                    
                    # Also filter within sentences (in case explanatory text is part of a sentence)
                    filtered_hindi = '\n'.join(filtered_hindi_lines)
                    for pattern in hindi_explanatory_patterns:
                        filtered_hindi = re.sub(pattern, '', filtered_hindi, flags=re.IGNORECASE)
                    
                    # Clean up extra spaces and newlines
                    filtered_hindi = re.sub(r'\s+', ' ', filtered_hindi).strip()
                    filtered_hindi = re.sub(r'\n\s*\n', '\n', filtered_hindi)
                    
                    video_download.enhanced_transcript_hindi = filtered_hindi
                    
                    # Update AI processing status to 'processed' after successful enhancement
                    video_download.ai_processing_status = 'processed'
                    video_download.ai_processed_at = timezone.now()
                    video_download.enhanced_transcript_finished_at = timezone.now()
                    video_download.save()
                    broadcast_video_update(video_download.id, video_instance=video_download)
                    
                    results['enhanced_result'] = enhanced_result
                    print(f"✓ Enhanced transcript generated: {len(enhanced_result['enhanced_text'])} chars")
                    print(f"✓ AI Processing status set to 'processed' for video {video_download.id}")
                else:
                    error_msg = enhanced_result.get('error', 'Unknown error')
                    print(f"✗ Enhanced transcript generation failed: {error_msg}")
                    # Update AI processing status to 'failed' if enhancement fails
                    video_download.ai_processing_status = 'failed'
                    video_download.ai_error_message = error_msg
                    video_download.save(update_fields=['ai_processing_status', 'ai_error_message'])
                    results['enhanced_error'] = error_msg
            else:
                error_msg = "No transcript sources available for enhancement (need at least Whisper or NCA)"
                print(f"⚠ {error_msg}")
                # Set status to failed if no sources available
                video_download.ai_processing_status = 'failed'
                video_download.ai_error_message = error_msg
                video_download.save(update_fields=['ai_processing_status', 'ai_error_message'])
                results['enhanced_error'] = error_msg
        else:
            error_msg = "AI provider not configured. Please configure AI provider in Settings."
            if not settings_obj:
                error_msg = "AI Provider Settings not found. Please configure in Settings."
            elif not settings_obj.api_key:
                error_msg = f"{settings_obj.provider} API key not configured. Please add API key in Settings."
            print(f"⚠ {error_msg}")
            # Set status to failed if AI provider not configured
            video_download.ai_processing_status = 'failed'
            video_download.ai_error_message = error_msg
            video_download.save(update_fields=['ai_processing_status', 'ai_error_message'])
            broadcast_video_update(video_download.id, video_instance=video_download)
            results['enhanced_error'] = error_msg
    except Exception as e:
        print(f"✗ Enhanced transcript generation error: {e}")
        import traceback
        traceback.print_exc()
        # Set status to failed on exception
        try:
            video_download.ai_processing_status = 'failed'
            video_download.ai_error_message = str(e)
            video_download.save(update_fields=['ai_processing_status', 'ai_error_message'])
        except:
            pass  # Don't fail if save fails
    
    # ========== FINAL STATUS ==========
    print("\n" + "="*60)
    print("TRANSCRIPTION COMPARISON RESULTS")
    print("="*60)
    
    nca_success = results['nca_result'] and results['nca_result'].get('status') == 'success'
    whisper_success = results['whisper_result'] and results['whisper_result'].get('status') == 'success'
    
    if nca_success and whisper_success:
        results['status'] = 'success'
        print("✓ Both NCA and Whisper succeeded")
        print(f"  NCA: {len(results['nca_result'].get('text', ''))} chars")
        print(f"  Whisper: {len(results['whisper_result'].get('text', ''))} chars")
    elif nca_success or whisper_success:
        results['status'] = 'partial'
        print("⚠ Partial success:")
        print(f"  NCA: {'✓' if nca_success else '✗'}")
        print(f"  Whisper: {'✓' if whisper_success else '✗'}")
    else:
        results['status'] = 'failed'
        print("✗ Both transcription methods failed")
    
    print("="*60 + "\n")
    
    return results
