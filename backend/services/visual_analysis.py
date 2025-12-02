"""
Visual Frame Analysis Module
Comprehensive visual analysis using OpenCV pipeline + AI for Hindi transcript generation.
Uses OpenCV to extract frame metadata, then sends JSONL to AI for transcript generation.
"""
import os
import subprocess
import tempfile
import base64
import requests
import json
from pathlib import Path
from typing import Dict
from django.conf import settings
from django.utils import timezone
from pipeline.utils import translate_text
from downloader.websocket_utils import broadcast_video_update
try:
    from services.opencv_frame_analysis import (
        analyze_frame_with_opencv, 
        analyze_frames_batch_opencv,
        analyze_video_frames_comprehensive,
        MAX_FRAMES
    )
except ImportError:
    # OpenCV not available, fallback to direct image analysis
    analyze_frame_with_opencv = None
    analyze_frames_batch_opencv = None
    analyze_video_frames_comprehensive = None
    MAX_FRAMES = 60


def detect_audio_in_video(video_path):
    """
    Check if video has audio track using ffprobe
    
    Args:
        video_path: Path to video file
        
    Returns:
        bool: True if audio exists, False otherwise
    """
    try:
        # Use ffprobe to check for audio streams
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a:0',
            '-show_entries', 'stream=codec_type',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # If output contains 'audio', video has audio
        has_audio = 'audio' in result.stdout.lower()
        print(f"Audio detection for {video_path}: {has_audio}")
        return has_audio
        
    except Exception as e:
        print(f"Error detecting audio: {e}")
        # Assume video has audio if detection fails
        return True


def extract_frames_at_intervals(video_path, interval_seconds=0.003, max_frames=None, save_to_dir=None):
    """
    Extract frames from video at regular intervals
    
    Args:
        video_path: Path to video file
        interval_seconds: Extract frame every N seconds (default: 0.003 = 3 milliseconds)
        max_frames: Maximum number of frames to extract (None = no limit, extract all frames)
        save_to_dir: Directory to save frames to (if None, uses temp directory)
        
    Returns:
        list: List of frame file paths (relative paths if save_to_dir is provided, absolute otherwise)
    """
    try:
        # Use provided directory or create temp directory
        if save_to_dir:
            # Ensure directory exists
            os.makedirs(save_to_dir, exist_ok=True)
            output_dir = save_to_dir
        else:
            output_dir = tempfile.mkdtemp(prefix='video_frames_')
        
        output_pattern = os.path.join(output_dir, 'frame_%04d.jpg')
        
        # Use ffmpeg to extract frames
        # -vf fps=1/N extracts 1 frame every N seconds
        # For 3 milliseconds (0.003 seconds), fps = 1/0.003 = 333.33 fps
        fps_filter = f"fps=1/{interval_seconds}"
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', fps_filter,
            '-q:v', '2',  # High quality
            output_pattern
        ]
        
        # Only add max_frames limit if specified
        if max_frames:
            cmd.insert(-1, '-frames:v')
            cmd.insert(-1, str(max_frames))
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # Increased timeout for longer videos
        )
        
        if result.returncode != 0:
            print(f"ffmpeg error: {result.stderr}")
            return []
        
        # Get list of extracted frames
        frames = sorted(Path(output_dir).glob('frame_*.jpg'))
        if save_to_dir:
            # Return relative paths from media root
            media_root = settings.MEDIA_ROOT
            frame_paths = [os.path.relpath(str(f), media_root) for f in frames]
        else:
            frame_paths = [str(f) for f in frames]
        
        print(f"Extracted {len(frame_paths)} frames from video")
        return frame_paths
        
    except Exception as e:
        print(f"Error extracting frames: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_and_save_frames_for_video(video_download, interval_seconds=1.0):
    """
    Extract frames from video and save them to media/visual_frames/{video_id}/ directory
    
    Args:
        video_download: VideoDownload model instance
        interval_seconds: Extract frame every N seconds (default: 1.0 = 1 frame per second)
        
    Returns:
        dict: {
            'success': bool,
            'frames_extracted': int,
            'frame_paths': list,
            'error': str (if failed)
        }
    """
    try:
        if not video_download.is_downloaded or not video_download.local_file:
            return {
                'success': False,
                'frames_extracted': 0,
                'frame_paths': [],
                'error': 'Video must be downloaded first'
            }
        
        # Skip if frames already extracted
        if video_download.frames_extracted:
            print(f"Frames already extracted for video {video_download.id}")
            return {
                'success': True,
                'frames_extracted': video_download.total_frames_extracted,
                'frame_paths': video_download.extracted_frames_paths or [],
                'error': None
            }
        
        video_path = video_download.local_file.path
        
        # Create directory for frames: media/visual_frames/{video_id}/
        video_id = video_download.video_id or str(video_download.id)
        frames_dir = os.path.join(settings.MEDIA_ROOT, 'visual_frames', video_id)
        os.makedirs(frames_dir, exist_ok=True)
        
        # Calculate max frames based on duration (1 frame per second, but cap at reasonable limit)
        max_frames = None
        if video_download.duration:
            max_frames = int(video_download.duration / interval_seconds)
            # Cap at 300 frames (5 minutes at 1 fps) to avoid too many frames
            max_frames = min(max_frames, 300)
        
        print(f"[FRAME EXTRACTION] Starting frame extraction for video {video_id}")
        print(f"[FRAME EXTRACTION] Video path: {video_path}")
        print(f"[FRAME EXTRACTION] Interval: {interval_seconds}s, Max frames: {max_frames}")
        print(f"[FRAME EXTRACTION] Frames directory: {frames_dir}")
        
        # Extract frames
        frame_paths = extract_frames_at_intervals(
            video_path=video_path,
            interval_seconds=interval_seconds,
            max_frames=max_frames,
            save_to_dir=frames_dir
        )
        
        print(f"[FRAME EXTRACTION] Extracted {len(frame_paths)} frames")
        
        if not frame_paths:
            print(f"[FRAME EXTRACTION] ERROR: No frames extracted")
            return {
                'success': False,
                'frames_extracted': 0,
                'frame_paths': [],
                'error': 'Could not extract frames from video'
            }
        
        # Save to database
        from django.utils import timezone
        print(f"[FRAME EXTRACTION] Saving frame data to database...")
        video_download.frames_extracted = True
        video_download.extracted_frames_paths = frame_paths
        video_download.frames_extracted_at = timezone.now()
        video_download.frames_extraction_interval = interval_seconds
        video_download.total_frames_extracted = len(frame_paths)
        video_download.save()
        broadcast_video_update(video_download.id, video_instance=video_download)
        
        print(f"[FRAME EXTRACTION] ✓ Successfully extracted and saved {len(frame_paths)} frames for video {video_id}")
        print(f"[FRAME EXTRACTION] Frame paths stored: {len(frame_paths)} paths")
        print(f"[FRAME EXTRACTION] Database updated: frames_extracted=True, total_frames={len(frame_paths)}")
        
        return {
            'success': True,
            'frames_extracted': len(frame_paths),
            'frame_paths': frame_paths,
            'error': None
        }
        
    except Exception as e:
        print(f"Error extracting and saving frames: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'frames_extracted': 0,
            'frame_paths': [],
            'error': str(e)
        }


def generate_hindi_transcript_from_frames_jsonl(jsonl_path: str, api_key: str, provider: str = 'gemini') -> Dict:
    """
    Generate Hindi transcript from frames JSONL data using AI provider.
    
    Args:
        jsonl_path: Path to JSONL file with frame analysis data
        api_key: API key for provider
        provider: 'gemini' or 'openai'
        
    Returns:
        dict: {
            'status': 'success' or 'failed',
            'transcript': str (Hindi transcript),
            'hook': str (short hook line),
            'error': str (if failed)
        }
    """
    try:
        # Read JSONL file
        frames_data = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    frames_data.append(json.loads(line))
        
        if not frames_data:
            return {
                'status': 'failed',
                'transcript': '',
                'hook': '',
                'error': 'No frame data found in JSONL file'
            }
        
        # Format frames data for AI prompt
        frames_summary = []
        for frame in frames_data[:30]:  # Limit to first 30 frames for prompt
            summary = {
                'timestamp': frame.get('timestamp', 0),
                'scene_change': frame.get('scene_change', False),
                'faces': len(frame.get('faces', [])),
                'objects': [obj.get('label', '') for obj in frame.get('objects', [])],
                'ocr_text': frame.get('ocr_text', ''),
                'motion_score': frame.get('motion_score', 0)
            }
            frames_summary.append(summary)
        
        frames_json = json.dumps(frames_summary, ensure_ascii=False, indent=2)
        
        # Create prompt for Hindi transcript generation
        prompt = f"""आप एक concise video-analysis assistant हैं। मैं नीचे per-frame JSON दूँगा। उसका उपयोग करके एक छोटा और स्पष्ट explanation/transcript बनाइए। अंतिमCTA लाइन "आपकी मम्मी-पापा की कसम — सब्सक्राइब कर देना।" बिल्कुल वैसी ही रखें। आउटपुट केवल प्लेन टेक्स्ट में दें।

हर JSON line में fields हैं: timestamp, scene_change, faces, objects, ocr_text, motion_score. इनसे करें:

1) 1–3 छोटे पैरा में वीडियो का वर्णन (अधिकतम 120 शब्द) — प्रमुख घटनाओं के साथ 3-4 timestamps दें (format: [0:02]).

2) उसके बाद 1-line hook (max 12 words).

3) अंत में CTA लाइन: "आपकी मम्मी-पापा की कसम — सब्सक्राइब कर देना।"

नियम:
- भाषा: हिंदी, सरल शब्दों में।
- OCR text मिलने पर उसे एक बार उद्धरण में लिखें।
- scene_change=true मिलने पर नया स्टेप मानें।
- faces होने पर "लड़की" या "व्यक्ति" तभी लिखें जब face bbox मौजूद हो।
- कुल transcript शब्द 120 से ज्यादा न हों।

Frames data:
{frames_json}"""
        
        # Call appropriate provider
        if provider == 'openai':
            return _generate_transcript_with_openai(prompt, api_key)
        else:
            return _generate_transcript_with_gemini(prompt, api_key)
            
    except Exception as e:
        print(f"[TRANSCRIPT GENERATION] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'failed',
            'transcript': '',
            'hook': '',
            'error': str(e)
        }


def _generate_transcript_with_gemini(prompt: str, api_key: str) -> Dict:
    """Generate transcript using Gemini API."""
    try:
        model_name = 'gemini-2.0-flash-exp'
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}'
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            candidates = data.get('candidates', [])
            if candidates:
                content = candidates[0].get('content', {})
                parts = content.get('parts', [])
                if parts:
                    transcript_text = parts[0].get('text', '').strip()
                    return {
                        'status': 'success',
                        'transcript': transcript_text,
                        'hook': '',  # Will be extracted from transcript
                        'error': None
                    }
        
        error_data = response.json().get('error', {})
        error_msg = error_data.get('message', 'Unknown error')
        return {
            'status': 'failed',
            'transcript': '',
            'hook': '',
            'error': error_msg
        }
    except Exception as e:
        return {
            'status': 'failed',
            'transcript': '',
            'hook': '',
            'error': str(e)
        }


def _generate_transcript_with_openai(prompt: str, api_key: str) -> Dict:
    """Generate transcript using OpenAI API."""
    try:
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 500
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            choices = data.get('choices', [])
            if choices:
                message = choices[0].get('message', {})
                transcript_text = message.get('content', '').strip()
                return {
                    'status': 'success',
                    'transcript': transcript_text,
                    'hook': '',  # Will be extracted from transcript
                    'error': None
                }
        
        error_data = response.json().get('error', {})
        error_msg = error_data.get('message', 'Unknown error')
        return {
            'status': 'failed',
            'transcript': '',
            'hook': '',
            'error': error_msg
        }
    except Exception as e:
        return {
            'status': 'failed',
            'transcript': '',
            'hook': '',
            'error': str(e)
        }


def analyze_frame_with_gemini_text_only(opencv_description, api_key, timestamp_seconds):
    """
    Generate transcript from OpenCV analysis description using Gemini API (text-only, no images).
    This is much cheaper than sending full images.
    
    Args:
        opencv_description: Text description from OpenCV analysis
        api_key: Gemini API key
        timestamp_seconds: Timestamp of this frame in video
        
    Returns:
        dict: {
            'timestamp': int,
            'description': str,
            'error': str (if failed)
        }
    """
    try:
        # Format timestamp
        hours = int(timestamp_seconds // 3600)
        minutes = int((timestamp_seconds % 3600) // 60)
        seconds = int(timestamp_seconds % 60)
        timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Gemini API endpoint - Using Gemini 2.0 Flash
        model_name = 'gemini-2.0-flash-exp'
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}'
        
        print(f"[GEMINI TEXT] Generating transcript from OpenCV analysis at {timestamp_str} using {model_name}")
        
        # Prompt to convert OpenCV analysis to detailed transcript
        prompt = f"""Based on this OpenCV frame analysis, provide a detailed description of what is happening in this video frame:

{opencv_description}

Please provide a clear, descriptive explanation in 2-3 sentences about:
- What is visible in the frame
- What actions or events are occurring
- Important details that help understand the video content

Be specific and detailed."""
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract text from response
            candidates = data.get('candidates', [])
            if candidates:
                content = candidates[0].get('content', {})
                parts = content.get('parts', [])
                if parts:
                    description = parts[0].get('text', '').strip()
                    
                    print(f"[GEMINI TEXT] ✓ Transcript generated at {timestamp_str}: {len(description)} chars")
                    
                    return {
                        'timestamp': timestamp_seconds,
                        'timestamp_str': timestamp_str,
                        'description': description,
                        'error': None
                    }
        
        # If we get here, something went wrong
        error_data = response.json().get('error', {})
        error_msg = error_data.get('message', 'Unknown error')
        
        # Check for quota/rate limit errors
        is_quota_error = (
            'quota' in error_msg.lower() or 
            'rate limit' in error_msg.lower() or
            'exceeded' in error_msg.lower()
        )
        
        return {
            'timestamp': timestamp_seconds,
            'timestamp_str': timestamp_str,
            'description': '',
            'error': error_msg,
            'is_quota_error': is_quota_error
        }
        
    except Exception as e:
        print(f"[GEMINI TEXT] Error generating transcript at {timestamp_seconds}s: {e}")
        return {
            'timestamp': timestamp_seconds,
            'timestamp_str': f"{int(timestamp_seconds//3600):02d}:{int((timestamp_seconds%3600)//60):02d}:{int(timestamp_seconds%60):02d}",
            'description': '',
            'error': str(e)
        }


def analyze_frame_with_gemini(frame_path, api_key, timestamp_seconds):
    """
    Analyze a single frame using Gemini Vision API
    
    Args:
        frame_path: Path to frame image
        api_key: Gemini API key
        timestamp_seconds: Timestamp of this frame in video
        
    Returns:
        dict: {
            'timestamp': int,
            'description': str,
            'error': str (if failed)
        }
    """
    try:
        # Read and encode image
        with open(frame_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Format timestamp
        hours = int(timestamp_seconds // 3600)
        minutes = int((timestamp_seconds % 3600) // 60)
        seconds = int(timestamp_seconds % 60)
        timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Gemini Vision API endpoint - Using Gemini 2.0 Flash for visual analysis
        model_name = 'gemini-2.0-flash-exp'
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}'
        
        print(f"[GEMINI VISION] Analyzing frame at {timestamp_str} using {model_name}")
        
        # Prompt for frame analysis - works for both Gemini and OpenAI
        prompt = """Analyze this video frame in detail and describe what is happening. 
Focus on:
- Main subjects/people and their actions, expressions, and interactions
- Important objects, text, or visual elements visible in the frame
- Scene setting, location, and environment
- Any significant events, changes, or movements
- Context and narrative elements that help understand the video content

Provide a clear, descriptive, and detailed explanation in 2-3 sentences. Be specific about what you see and what is happening."""
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_data
                        }
                    }
                ]
            }]
        }
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract text from response
            candidates = data.get('candidates', [])
            if candidates:
                content = candidates[0].get('content', {})
                parts = content.get('parts', [])
                if parts:
                    description = parts[0].get('text', '').strip()
                    
                    print(f"[GEMINI VISION] ✓ Frame analyzed at {timestamp_str}: {len(description)} chars generated by Gemini AI")
                    
                    return {
                        'timestamp': timestamp_seconds,
                        'timestamp_str': timestamp_str,
                        'description': description,
                        'error': None
                    }
        
        # If we get here, something went wrong
        error_data = response.json().get('error', {})
        error_msg = error_data.get('message', 'Unknown error')
        
        # Check for quota/rate limit errors
        is_quota_error = (
            'quota' in error_msg.lower() or 
            'rate limit' in error_msg.lower() or
            'exceeded' in error_msg.lower()
        )
        
        # Extract retry time if available
        retry_after = None
        if 'retry in' in error_msg.lower():
            import re
            retry_match = re.search(r'retry in ([\d.]+)s', error_msg.lower())
            if retry_match:
                retry_after = float(retry_match.group(1))
        
        return {
            'timestamp': timestamp_seconds,
            'timestamp_str': timestamp_str,
            'description': '',
            'error': error_msg,
            'is_quota_error': is_quota_error,
            'retry_after': retry_after
        }
        
    except Exception as e:
        print(f"Error analyzing frame at {timestamp_seconds}s: {e}")
        return {
            'timestamp': timestamp_seconds,
            'timestamp_str': f"{int(timestamp_seconds//3600):02d}:{int((timestamp_seconds%3600)//60):02d}:{int(timestamp_seconds%60):02d}",
            'description': '',
            'error': str(e)
        }


def analyze_frame_with_openai_text_only(opencv_description, api_key, timestamp_seconds):
    """
    Generate transcript from OpenCV analysis description using OpenAI API (text-only, no images).
    This is much cheaper than sending full images.
    
    Args:
        opencv_description: Text description from OpenCV analysis
        api_key: OpenAI API key
        timestamp_seconds: Timestamp of this frame in video
        
    Returns:
        dict: {
            'timestamp': int,
            'description': str,
            'error': str (if failed)
        }
    """
    try:
        # Format timestamp
        hours = int(timestamp_seconds // 3600)
        minutes = int((timestamp_seconds % 3600) // 60)
        seconds = int(timestamp_seconds % 60)
        timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        print(f"[OPENAI TEXT] Generating transcript from OpenCV analysis at {timestamp_str} using gpt-4o-mini")
        
        # Prompt to convert OpenCV analysis to detailed transcript
        prompt = f"""Based on this OpenCV frame analysis, provide a detailed description of what is happening in this video frame:

{opencv_description}

Please provide a clear, descriptive explanation in 2-3 sentences about:
- What is visible in the frame
- What actions or events are occurring
- Important details that help understand the video content

Be specific and detailed."""
        
        # OpenAI API endpoint
        url = 'https://api.openai.com/v1/chat/completions'
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 300
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract text from response
            choices = data.get('choices', [])
            if choices:
                message = choices[0].get('message', {})
                description = message.get('content', '').strip()
                
                print(f"[OPENAI TEXT] ✓ Transcript generated at {timestamp_str}: {len(description)} chars")
                
                return {
                    'timestamp': timestamp_seconds,
                    'timestamp_str': timestamp_str,
                    'description': description,
                    'error': None
                }
        
        # If we get here, something went wrong
        error_data = response.json().get('error', {})
        error_msg = error_data.get('message', 'Unknown error')
        
        # Check for quota/rate limit errors
        is_quota_error = (
            'quota' in error_msg.lower() or 
            'rate limit' in error_msg.lower() or
            'exceeded' in error_msg.lower() or
            'insufficient' in error_msg.lower()
        )
        
        return {
            'timestamp': timestamp_seconds,
            'timestamp_str': timestamp_str,
            'description': '',
            'error': error_msg,
            'is_quota_error': is_quota_error
        }
        
    except Exception as e:
        print(f"[OPENAI TEXT] Error generating transcript at {timestamp_seconds}s: {e}")
        return {
            'timestamp': timestamp_seconds,
            'timestamp_str': f"{int(timestamp_seconds//3600):02d}:{int((timestamp_seconds%3600)//60):02d}:{int(timestamp_seconds%60):02d}",
            'description': '',
            'error': str(e)
        }


def analyze_frame_with_openai(frame_path, api_key, timestamp_seconds):
    """
    Analyze a single frame using OpenAI GPT-4o-mini Vision API
    
    Args:
        frame_path: Path to frame image
        api_key: OpenAI API key
        timestamp_seconds: Timestamp of this frame in video
        
    Returns:
        dict: {
            'timestamp': int,
            'description': str,
            'error': str (if failed)
        }
    """
    try:
        # Read and encode image
        with open(frame_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Format timestamp
        hours = int(timestamp_seconds // 3600)
        minutes = int((timestamp_seconds % 3600) // 60)
        seconds = int(timestamp_seconds % 60)
        timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        print(f"[OPENAI VISION] Analyzing frame at {timestamp_str} using gpt-4o-mini")
        
        # Prompt for frame analysis - same as Gemini version
        prompt = """Analyze this video frame in detail and describe what is happening. 
Focus on:
- Main subjects/people and their actions, expressions, and interactions
- Important objects, text, or visual elements visible in the frame
- Scene setting, location, and environment
- Any significant events, changes, or movements
- Context and narrative elements that help understand the video content

Provide a clear, descriptive, and detailed explanation in 2-3 sentences. Be specific about what you see and what is happening."""
        
        # OpenAI Vision API endpoint
        url = 'https://api.openai.com/v1/chat/completions'
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract text from response
            choices = data.get('choices', [])
            if choices:
                message = choices[0].get('message', {})
                description = message.get('content', '').strip()
                
                print(f"[OPENAI VISION] ✓ Frame analyzed at {timestamp_str}: {len(description)} chars generated by GPT-4o-mini")
                
                return {
                    'timestamp': timestamp_seconds,
                    'timestamp_str': timestamp_str,
                    'description': description,
                    'error': None
                }
        
        # If we get here, something went wrong
        error_data = response.json().get('error', {})
        error_msg = error_data.get('message', 'Unknown error')
        
        # Check for quota/rate limit errors
        is_quota_error = (
            'quota' in error_msg.lower() or 
            'rate limit' in error_msg.lower() or
            'exceeded' in error_msg.lower() or
            'insufficient' in error_msg.lower()
        )
        
        return {
            'timestamp': timestamp_seconds,
            'timestamp_str': timestamp_str,
            'description': '',
            'error': error_msg,
            'is_quota_error': is_quota_error
        }
        
    except Exception as e:
        print(f"[OPENAI VISION] Error analyzing frame at {timestamp_seconds}s: {e}")
        return {
            'timestamp': timestamp_seconds,
            'timestamp_str': f"{int(timestamp_seconds//3600):02d}:{int((timestamp_seconds%3600)//60):02d}:{int(timestamp_seconds%60):02d}",
            'description': '',
            'error': str(e)
        }


def generate_visual_transcript_from_video_comprehensive(video_download, api_key, provider='gemini'):
    """
    Generate Hindi transcript using comprehensive OpenCV pipeline and AI analysis.
    This is the new recommended method that uses the full OpenCV pipeline.
    
    Args:
        video_download: VideoDownload model instance
        api_key: API key for provider
        provider: 'gemini' or 'openai' (from settings)
        
    Returns:
        dict: {
            'status': 'success' or 'failed',
            'text': str (plain text transcript),
            'text_with_timestamps': str (with timestamps),
            'transcript': str (full transcript with hook and CTA),
            'hook': str (short hook line),
            'segments': list,
            'error': str (if failed)
        }
    """
    try:
        from services.opencv_frame_analysis import analyze_video_frames_comprehensive
        
        if not video_download.is_downloaded or not video_download.local_file:
            return {
                'status': 'failed',
                'text': '',
                'text_with_timestamps': '',
                'transcript': '',
                'hook': '',
                'segments': [],
                'error': 'Video must be downloaded first'
            }
        
        video_path = video_download.local_file.path
        video_id = video_download.video_id or str(video_download.id)
        
        # Create output directory for frames
        frames_dir = os.path.join(settings.MEDIA_ROOT, 'visual_frames', video_id, 'analysis')
        os.makedirs(frames_dir, exist_ok=True)
        
        print(f"[COMPREHENSIVE ANALYSIS] Starting comprehensive frame analysis for video {video_id}")
        print(f"[COMPREHENSIVE ANALYSIS] Video path: {video_path}")
        print(f"[COMPREHENSIVE ANALYSIS] Output directory: {frames_dir}")
        print(f"[COMPREHENSIVE ANALYSIS] Provider: {provider}")
        
        # Step 1: Run comprehensive OpenCV pipeline
        try:
            frames_data, jsonl_path = analyze_video_frames_comprehensive(
                video_path, frames_dir, max_frames=MAX_FRAMES
            )
            print(f"[COMPREHENSIVE ANALYSIS] ✓ OpenCV pipeline complete: {len(frames_data)} frames analyzed")
        except Exception as e:
            print(f"[COMPREHENSIVE ANALYSIS] ✗ OpenCV pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'failed',
                'text': '',
                'text_with_timestamps': '',
                'transcript': '',
                'hook': '',
                'segments': [],
                'error': f'OpenCV pipeline failed: {str(e)}'
            }
        
        # Step 2: Generate Hindi transcript from JSONL using AI
        print(f"[COMPREHENSIVE ANALYSIS] Generating Hindi transcript using {provider}...")
        transcript_result = generate_hindi_transcript_from_frames_jsonl(jsonl_path, api_key, provider)
        
        if transcript_result['status'] != 'success':
            return {
                'status': 'failed',
                'text': '',
                'text_with_timestamps': '',
                'transcript': '',
                'hook': '',
                'segments': [],
                'error': transcript_result.get('error', 'Transcript generation failed')
            }
        
        # Parse transcript to extract hook and main content
        transcript_text = transcript_result['transcript']
        lines = transcript_text.split('\n')
        
        # Extract CTA (should be last line)
        cta_line = "आपकी मम्मी-पापा की कसम — सब्सक्राइब कर देना।"
        hook_line = ""
        main_transcript = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if cta_line in line:
                continue  # Skip CTA line (will be added separately)
            elif len(line.split()) <= 12 and not hook_line:
                hook_line = line  # First short line is likely the hook
            else:
                main_transcript.append(line)
        
        # Format segments from frames data
        segments = []
        for frame in frames_data:
            timestamp_seconds = frame.get('timestamp', 0)
            hours = int(timestamp_seconds // 3600)
            minutes = int((timestamp_seconds % 3600) // 60)
            seconds = int(timestamp_seconds % 60)
            timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Create description from frame data
            desc_parts = []
            if frame.get('scene_change'):
                desc_parts.append("Scene change")
            if frame.get('faces'):
                desc_parts.append(f"{len(frame['faces'])} person(s)")
            if frame.get('objects'):
                obj_labels = [obj.get('label', '') for obj in frame['objects']]
                desc_parts.append(f"Objects: {', '.join(obj_labels)}")
            if frame.get('ocr_text'):
                desc_parts.append(f"Text: {frame['ocr_text'][:30]}")
            
            description = ". ".join(desc_parts) if desc_parts else "Frame analyzed"
            
            segments.append({
                'start': timestamp_seconds,
                'text': description,
                'timestamp_str': timestamp_str
            })
        
        # Combine transcript parts
        full_transcript = '\n\n'.join(main_transcript)
        if hook_line:
            full_transcript += f'\n\n{hook_line}'
        full_transcript += f'\n\n{cta_line}'
        
        # Plain text (without timestamps for main transcript)
        plain_text = ' '.join(main_transcript)
        
        # Text with timestamps
        timestamped_lines = [f"{seg['timestamp_str']} {seg['text']}" for seg in segments]
        text_with_timestamps = '\n'.join(timestamped_lines)
        
        print(f"[COMPREHENSIVE ANALYSIS] ✓ Hindi transcript generated successfully")
        print(f"[COMPREHENSIVE ANALYSIS] Transcript length: {len(plain_text)} chars")
        
        return {
            'status': 'success',
            'text': plain_text,
            'text_with_timestamps': text_with_timestamps,
            'transcript': full_transcript,
            'hook': hook_line,
            'segments': segments,
            'error': None
        }
        
    except Exception as e:
        print(f"[COMPREHENSIVE ANALYSIS] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'failed',
            'text': '',
            'text_with_timestamps': '',
            'transcript': '',
            'hook': '',
            'segments': [],
            'error': str(e)
        }


def generate_visual_transcript_from_stored_frames(video_download, api_key, provider='gemini'):
    """
    Generate timestamped transcript from stored frames using Gemini Vision or OpenAI GPT-4o-mini
    
    Args:
        video_download: VideoDownload model instance with extracted frames
        api_key: API key (Gemini or OpenAI depending on provider)
        provider: 'gemini' or 'openai' (default: 'gemini')
        
    Returns:
        dict: {
            'status': 'success' or 'failed',
            'text': str (plain text description),
            'text_with_timestamps': str (with HH:MM:SS timestamps),
            'segments': list of dicts with timestamp and description,
            'error': str (if failed),
            'quota_exceeded': bool (if quota error occurred)
        }
    """
    try:
        if not video_download.frames_extracted or not video_download.extracted_frames_paths:
            return {
                'status': 'failed',
                'text': '',
                'text_with_timestamps': '',
                'segments': [],
                'error': 'Frames not extracted yet. Please extract frames first.'
            }
        
        print(f"Starting visual frame analysis for video {video_download.id} using stored frames")
        
        # Get frame paths (they are relative to MEDIA_ROOT)
        frame_paths_relative = video_download.extracted_frames_paths
        interval = video_download.frames_extraction_interval or 1.0
        
        # Convert to absolute paths
        frame_paths = [os.path.join(settings.MEDIA_ROOT, path) for path in frame_paths_relative]
        
        # Filter out non-existent frames
        frame_paths = [path for path in frame_paths if os.path.exists(path)]
        
        if not frame_paths:
            return {
                'status': 'failed',
                'text': '',
                'text_with_timestamps': '',
                'segments': [],
                'error': 'Stored frame files not found. Please re-extract frames.'
            }
        
        provider_name = 'OpenAI GPT-4o-mini' if provider == 'openai' else 'Gemini Vision API'
        print(f"[VISUAL ANALYSIS] Using {len(frame_paths)} stored frames for {provider_name} analysis")
        print(f"[VISUAL ANALYSIS] Frame extraction interval: {interval}s")
        print(f"[VISUAL ANALYSIS] Starting {provider_name} processing...")
        print(f"[VISUAL ANALYSIS] Provider: {provider}")
        
        # Step 1: Analyze frames locally with OpenCV first (cost-free)
        # If OpenCV is available, use it to reduce API costs
        if analyze_frames_batch_opencv is not None:
            print(f"[VISUAL ANALYSIS] Step 1: Analyzing {len(frame_paths)} frames locally with OpenCV...")
            try:
                opencv_results = analyze_frames_batch_opencv(frame_paths)
                print(f"[VISUAL ANALYSIS] ✓ OpenCV analysis complete: {len(opencv_results)} frames analyzed")
                use_opencv = True
            except Exception as e:
                print(f"[VISUAL ANALYSIS] ⚠ OpenCV analysis failed, falling back to direct image analysis: {e}")
                use_opencv = False
                opencv_results = []
        else:
            print(f"[VISUAL ANALYSIS] ⚠ OpenCV not available, using direct image analysis (more expensive)")
            use_opencv = False
            opencv_results = []
        
        # Step 2: Send analysis to AI
        if use_opencv:
            # Send only OpenCV analysis results to AI (not full images) to generate transcript
            # This reduces API costs significantly (text-only API calls are much cheaper than vision API)
            print(f"[VISUAL ANALYSIS] Step 2: Sending OpenCV analysis results to {provider_name} for transcript generation...")
            
            # Choose analysis function based on provider (text-only functions)
            if provider == 'openai':
                analyze_func = analyze_frame_with_openai_text_only
            else:
                analyze_func = analyze_frame_with_gemini_text_only
        else:
            # Fallback: Send full images to AI (more expensive but works without OpenCV)
            print(f"[VISUAL ANALYSIS] Step 2: Sending full frame images to {provider_name} for analysis...")
            
            # Choose analysis function based on provider (image-based functions)
            if provider == 'openai':
                analyze_func = analyze_frame_with_openai
            else:
                analyze_func = analyze_frame_with_gemini
        
        # Analyze each frame's OpenCV results using selected provider (batch processing for efficiency)
        segments = []
        total_frames = len(frame_paths)
        batch_size = 10  # Can process more since we're sending text, not images
        successful_frames = 0
        failed_frames = 0
        quota_errors = 0
        import time
        
        print(f"[VISUAL ANALYSIS] Processing {total_frames} OpenCV analysis results in batches of {batch_size} using {provider_name}...")
        
        for batch_start in range(0, total_frames, batch_size):
            batch_end = min(batch_start + batch_size, total_frames)
            batch_opencv_results = opencv_results[batch_start:batch_end]
            batch_frames = frame_paths[batch_start:batch_end]
            
            print(f"[VISUAL ANALYSIS] Analyzing frames {batch_start+1}-{batch_end}/{total_frames} with {provider_name}...")
            
            for idx, (opencv_result, frame_path) in enumerate(zip(batch_opencv_results, batch_frames)):
                frame_idx = batch_start + idx
                timestamp_seconds = frame_idx * interval
                
                # Check if OpenCV analysis failed
                if opencv_result.get('error'):
                    print(f"⚠ Frame {frame_idx+1} OpenCV analysis error: {opencv_result['error']}")
                    failed_frames += 1
                    continue
                
                try:
                    # Send OpenCV analysis description to AI (text-only, much cheaper)
                    result = analyze_func(opencv_result.get('description', ''), api_key, timestamp_seconds)
                    
                    # Check for quota/rate limit errors
                    if result.get('is_quota_error'):
                        quota_errors += 1
                        error_msg = result.get('error', 'Quota exceeded')
                        print(f"⚠ Frame {frame_idx+1} quota error: {error_msg[:100]}...")
                        
                        # If we hit quota limit, stop processing and return error
                        if quota_errors >= 3:  # After 3 quota errors, stop
                            return {
                                'status': 'failed',
                                'text': '',
                                'text_with_timestamps': '',
                                'segments': segments,
                                'error': f'Gemini API quota exceeded. {quota_errors} frames failed due to quota limits. Please check your API quota or wait before retrying. Error: {error_msg[:200]}',
                                'quota_exceeded': True
                            }
                        
                        # Wait before retrying if retry_after is specified
                        retry_after = result.get('retry_after')
                        if retry_after and retry_after < 60:  # Only wait if less than 60 seconds
                            print(f"Waiting {retry_after:.1f}s before next request...")
                            time.sleep(retry_after)
                        
                        failed_frames += 1
                        continue
                    
                    if result.get('error'):
                        print(f"⚠ Frame {frame_idx+1} analysis error: {result['error'][:100]}")
                        failed_frames += 1
                        continue
                    
                    if result.get('description'):
                        segments.append({
                            'start': timestamp_seconds,
                            'text': result['description'],
                            'timestamp_str': result['timestamp_str']
                        })
                        successful_frames += 1
                    else:
                        failed_frames += 1
                    
                    # Add small delay between requests to avoid rate limits
                    if idx < len(batch_frames) - 1:  # Don't delay after last frame in batch
                        time.sleep(0.5)  # 500ms delay between frames
                        
                except Exception as api_error:
                    error_str = str(api_error)
                    if 'timeout' in error_str.lower() or 'Timeout' in str(type(api_error)):
                        print(f"⚠ Frame {frame_idx+1} API timeout")
                    else:
                        print(f"⚠ Frame {frame_idx+1} error: {api_error}")
                    failed_frames += 1
                    continue
            
            # Add delay between batches
            if batch_start + batch_size < total_frames:
                time.sleep(1)  # 1 second delay between batches
        
        print(f"[VISUAL ANALYSIS] Frame analysis complete: {successful_frames} successful, {failed_frames} failed")
        print(f"[VISUAL ANALYSIS] Generated {len(segments)} segments from {provider_name}")
        
        if not segments:
            error_msg = f'No descriptions generated from {total_frames} frames. '
            if quota_errors > 0:
                error_msg += f'QUOTA ERROR: {quota_errors} frames failed due to Gemini API quota/rate limits. '
                error_msg += 'Please check your Gemini API quota or wait before retrying.'
            elif failed_frames > 0:
                error_msg += f'{failed_frames} frames failed to analyze.'
            return {
                'status': 'failed',
                'text': '',
                'text_with_timestamps': '',
                'segments': [],
                'error': error_msg,
                'quota_exceeded': quota_errors > 0
            }
        
        # Format results
        # Plain text (without timestamps)
        plain_text = ' '.join([seg['text'] for seg in segments])
        
        # Text with timestamps
        timestamped_lines = [
            f"{seg['timestamp_str']} {seg['text']}"
            for seg in segments
        ]
        text_with_timestamps = '\n'.join(timestamped_lines)
        
        print(f"[VISUAL ANALYSIS] ✓ Visual analysis complete: {len(segments)} segments generated using {provider_name}")
        print(f"[VISUAL ANALYSIS] Transcript length: {len(plain_text)} chars (with timestamps: {len(text_with_timestamps)} chars)")
        
        return {
            'status': 'success',
            'text': plain_text,
            'text_with_timestamps': text_with_timestamps,
            'segments': segments,
            'error': None
        }
        
    except Exception as e:
        print(f"[VISUAL ANALYSIS] Error generating visual transcript from stored frames: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'status': 'failed',
            'text': '',
            'text_with_timestamps': '',
            'segments': [],
            'error': str(e)
        }


def generate_visual_transcript(video_path, api_key, interval=0.003, max_frames=None):
    """
    Generate timestamped transcript from video frames using Gemini Vision
    (Legacy function - use generate_visual_transcript_from_stored_frames for new implementation)
    
    Args:
        video_path: Path to video file
        api_key: Gemini API key
        interval: Extract frame every N seconds (default: 0.003 = 3 milliseconds for high accuracy)
        max_frames: Maximum number of frames to analyze (None = no limit, analyze all frames)
        
    Returns:
        dict: {
            'status': 'success' or 'failed',
            'text': str (plain text description),
            'text_with_timestamps': str (with HH:MM:SS timestamps),
            'segments': list of dicts with timestamp and description,
            'error': str (if failed)
        }
    """
    try:
        print(f"Starting visual frame analysis for: {video_path}")
        
        # Extract frames
        frame_paths = extract_frames_at_intervals(video_path, interval, max_frames)
        
        if not frame_paths:
            return {
                'status': 'failed',
                'text': '',
                'text_with_timestamps': '',
                'segments': [],
                'error': 'Could not extract frames from video'
            }
        
        # Choose analysis function based on provider (default to Gemini for legacy function)
        # Note: This legacy function doesn't support provider selection, defaults to Gemini
        analyze_func = analyze_frame_with_gemini
        
        # Analyze each frame (batch processing for efficiency with many frames)
        segments = []
        total_frames = len(frame_paths)
        batch_size = 5  # Reduced batch size to avoid rate limits
        successful_frames = 0
        failed_frames = 0
        quota_errors = 0
        import time
        
        print(f"Processing {total_frames} frames in batches of {batch_size}...")
        
        for batch_start in range(0, total_frames, batch_size):
            batch_end = min(batch_start + batch_size, total_frames)
            batch_frames = frame_paths[batch_start:batch_end]
            
            print(f"Analyzing frames {batch_start+1}-{batch_end}/{total_frames}...")
            
            for idx, frame_path in enumerate(batch_frames):
                frame_idx = batch_start + idx
                timestamp_seconds = frame_idx * interval
                
                # Check if frame file exists
                if not os.path.exists(frame_path):
                    print(f"⚠ Frame {frame_idx+1} file not found: {frame_path}")
                    failed_frames += 1
                    continue
                
                try:
                    result = analyze_func(frame_path, api_key, timestamp_seconds)
                    
                    # Check for quota/rate limit errors
                    if result.get('is_quota_error'):
                        quota_errors += 1
                        error_msg = result.get('error', 'Quota exceeded')
                        print(f"⚠ Frame {frame_idx+1} quota error: {error_msg[:100]}...")
                        
                        # If we hit quota limit, stop processing and return error
                        if quota_errors >= 3:  # After 3 quota errors, stop
                            return {
                                'status': 'failed',
                                'text': '',
                                'text_with_timestamps': '',
                                'segments': segments,
                                'error': f'Gemini API quota exceeded. {quota_errors} frames failed due to quota limits. Please check your API quota or wait before retrying. Error: {error_msg[:200]}',
                                'quota_exceeded': True
                            }
                        
                        # Wait before retrying if retry_after is specified
                        retry_after = result.get('retry_after')
                        if retry_after and retry_after < 60:  # Only wait if less than 60 seconds
                            print(f"Waiting {retry_after:.1f}s before next request...")
                            time.sleep(retry_after)
                        
                        failed_frames += 1
                        continue
                    
                    if result.get('error'):
                        print(f"⚠ Frame {frame_idx+1} analysis error: {result['error'][:100]}")
                        failed_frames += 1
                        continue
                    
                    if result.get('description'):
                        segments.append({
                            'start': timestamp_seconds,
                            'text': result['description'],
                            'timestamp_str': result['timestamp_str']
                        })
                        successful_frames += 1
                    else:
                        failed_frames += 1
                    
                    # Add small delay between requests to avoid rate limits
                    if idx < len(batch_frames) - 1:  # Don't delay after last frame in batch
                        time.sleep(0.5)  # 500ms delay between frames
                        
                except Exception as api_error:
                    # Check if it's a requests exception
                    error_str = str(api_error)
                    if 'timeout' in error_str.lower() or 'Timeout' in str(type(api_error)):
                        print(f"⚠ Frame {frame_idx+1} API timeout")
                    elif 'requests' in error_str.lower() or 'RequestException' in str(type(api_error)):
                        print(f"⚠ Frame {frame_idx+1} API error: {api_error}")
                    else:
                        print(f"⚠ Frame {frame_idx+1} error: {api_error}")
                    failed_frames += 1
                    continue
                except Exception as e:
                    print(f"⚠ Error analyzing frame {frame_idx+1}: {e}")
                    failed_frames += 1
                    continue
            
            # Add delay between batches
            if batch_start + batch_size < total_frames:
                time.sleep(1)  # 1 second delay between batches
        
        print(f"Frame analysis complete: {successful_frames} successful, {failed_frames} failed")
        
        # Clean up frame files
        try:
            for frame_path in frame_paths:
                os.remove(frame_path)
            # Remove temp directory
            if frame_paths:
                temp_dir = os.path.dirname(frame_paths[0])
                os.rmdir(temp_dir)
        except Exception as e:
            print(f"Warning: Could not clean up temp frames: {e}")
        
        if not segments:
            error_msg = f'No descriptions generated from {total_frames} frames. '
            if quota_errors > 0:
                error_msg += f'QUOTA ERROR: {quota_errors} frames failed due to Gemini API quota/rate limits. '
                error_msg += 'Please check your Gemini API quota or wait before retrying. '
                error_msg += 'You may need to upgrade your API plan or reduce the number of frames analyzed.'
            elif failed_frames > 0:
                error_msg += f'{failed_frames} frames failed to analyze. '
            if successful_frames == 0:
                if quota_errors == 0:
                    error_msg += 'Please check Gemini API key and network connection.'
            return {
                'status': 'failed',
                'text': '',
                'text_with_timestamps': '',
                'segments': [],
                'error': error_msg,
                'quota_exceeded': quota_errors > 0
            }
        
        # Format results
        # Plain text (without timestamps)
        plain_text = ' '.join([seg['text'] for seg in segments])
        
        # Text with timestamps
        timestamped_lines = [
            f"{seg['timestamp_str']} {seg['text']}"
            for seg in segments
        ]
        text_with_timestamps = '\n'.join(timestamped_lines)
        
        print(f"✓ Visual analysis complete: {len(segments)} segments generated")
        
        return {
            'status': 'success',
            'text': plain_text,
            'text_with_timestamps': text_with_timestamps,
            'segments': segments,
            'error': None
        }
        
    except Exception as e:
        print(f"Error generating visual transcript: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'status': 'failed',
            'text': '',
            'text_with_timestamps': '',
            'segments': [],
            'error': str(e)
        }
