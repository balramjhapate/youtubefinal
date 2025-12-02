"""
Visual Frame Analysis Module
Analyzes video frames using Gemini Vision API when no audio is present
"""
import os
import subprocess
import tempfile
import base64
import requests
from pathlib import Path
from django.conf import settings
from pipeline.utils import translate_text


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


def extract_frames_at_intervals(video_path, interval_seconds=0.003, max_frames=None):
    """
    Extract frames from video at regular intervals
    
    Args:
        video_path: Path to video file
        interval_seconds: Extract frame every N seconds (default: 0.003 = 3 milliseconds)
        max_frames: Maximum number of frames to extract (None = no limit, extract all frames)
        
    Returns:
        list: List of frame file paths
    """
    try:
        # Create temp directory for frames
        temp_dir = tempfile.mkdtemp(prefix='video_frames_')
        output_pattern = os.path.join(temp_dir, 'frame_%04d.jpg')
        
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
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"ffmpeg error: {result.stderr}")
            return []
        
        # Get list of extracted frames
        frames = sorted(Path(temp_dir).glob('frame_*.jpg'))
        frame_paths = [str(f) for f in frames]
        
        print(f"Extracted {len(frame_paths)} frames from video")
        return frame_paths
        
    except Exception as e:
        print(f"Error extracting frames: {e}")
        return []


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
        
        # Gemini Vision API endpoint
        model_name = 'gemini-2.0-flash-exp'
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}'
        
        # Prompt for frame analysis
        prompt = """Describe what is happening in this video frame in 1-2 concise sentences. 
Focus on:
- Main subjects/people and their actions
- Important objects or text visible
- Scene setting or location
- Any significant events or changes

Be specific and descriptive but brief."""
        
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


def generate_visual_transcript(video_path, api_key, interval=0.003, max_frames=None):
    """
    Generate timestamped transcript from video frames using Gemini Vision
    
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
                    result = analyze_frame_with_gemini(frame_path, api_key, timestamp_seconds)
                    
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
