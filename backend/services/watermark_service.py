"""
Watermark service for applying moving text watermarks to videos with smooth transitions
"""
import os
import subprocess
import tempfile
import math
import logging
import re

logger = logging.getLogger(__name__)


def escape_text_for_ffmpeg(text):
    """
    Escape special characters in text for ffmpeg drawtext filter
    Supports Hindi/Unicode characters
    """
    if not text:
        return ""
    
    # Escape special characters for ffmpeg drawtext
    # Replace single quotes with escaped version
    text = text.replace("'", "\\'")
    # Replace colons (used in time format)
    text = text.replace(":", "\\:")
    # Replace backslashes (must be done first)
    text = text.replace("\\", "\\\\")
    # Replace newlines with space
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    
    return text


def apply_moving_watermark(video_path, watermark_text, output_path, 
                          position_change_interval=1.0, opacity=0.7, 
                          font_size=24, font_color='white'):
    """
    Apply a smoothly moving text watermark to a video using ffmpeg drawtext filter.
    The watermark moves smoothly across the video with continuous transitions.
    
    Args:
        video_path: Path to input video file
        watermark_text: Text to display as watermark (supports Hindi/Unicode)
        output_path: Path to save output video
        position_change_interval: How often to change direction (in seconds) - used for smooth movement
        opacity: Watermark opacity (0.0 to 1.0)
        font_size: Font size for watermark text
        font_color: Font color (e.g., 'white', 'black', '#FFFFFF')
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Find ffmpeg
        from pipeline.utils import find_ffmpeg
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            logger.error("ffmpeg not found. Cannot apply watermark.")
            return False
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return False
        
        if not watermark_text or not watermark_text.strip():
            logger.error("Watermark text is empty")
            return False
        
        # Get video dimensions and duration using ffprobe
        from pipeline.utils import find_ffprobe
        ffprobe_path = find_ffprobe()
        if not ffprobe_path:
            logger.error("ffprobe not found. Cannot get video dimensions.")
            return False
        
        # Get video duration and dimensions
        cmd_probe = [
            ffprobe_path,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        result = subprocess.run(cmd_probe, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.error(f"Failed to probe video: {result.stderr}")
            return False
        
        lines = result.stdout.strip().split('\n')
        video_width = int(lines[0]) if len(lines) > 0 and lines[0].isdigit() else 1920
        video_height = int(lines[1]) if len(lines) > 1 and lines[1].isdigit() else 1080
        video_duration = float(lines[2]) if len(lines) > 2 and lines[2].replace('.', '').isdigit() else 30.0
        
        # Calculate text width estimate (rough estimate for positioning)
        # For Hindi/Unicode: approximately font_size * character_count * 0.7
        text_width_estimate = len(watermark_text) * font_size * 0.7
        text_height_estimate = font_size * 1.3
        
        # Escape text for ffmpeg (supports Hindi/Unicode)
        escaped_text = escape_text_for_ffmpeg(watermark_text)
        
        # Create smooth continuous movement
        # Instead of jumping between positions, create a smooth path
        # We'll use a circular or diagonal path that moves smoothly
        
        # Option 1: Smooth diagonal movement (top-left to bottom-right and back)
        # X position: moves from left to right smoothly
        # Y position: moves from top to bottom smoothly
        
        # Calculate movement speed based on video duration
        # Complete one full cycle (diagonal) in video_duration seconds
        cycle_duration = video_duration
        
        # Smooth X movement: 0 to (width - text_width) and back
        x_max = max(10, int(video_width - text_width_estimate - 10))
        x_min = 10
        
        # Smooth Y movement: 0 to (height - text_height) and back
        y_max = max(10, int(video_height - text_height_estimate - 10))
        y_min = 10
        
        # Create smooth sine wave movement for X and Y
        # This creates a smooth circular/elliptical path
        # X = center_x + amplitude_x * sin(2*PI*t/period)
        # Y = center_y + amplitude_y * cos(2*PI*t/period)
        
        center_x = (x_min + x_max) / 2
        center_y = (y_min + y_max) / 2
        amplitude_x = (x_max - x_min) / 2
        amplitude_y = (y_max - y_min) / 2
        
        # Period for one complete cycle (in seconds)
        period = cycle_duration
        
        # Build smooth position expressions using ffmpeg expressions
        # X position: smooth sine wave
        x_expr = f"{center_x}+{amplitude_x}*sin(2*PI*t/{period})"
        # Y position: smooth cosine wave (creates circular/elliptical path)
        y_expr = f"{center_y}+{amplitude_y}*cos(2*PI*t/{period})"
        
        # Alternative: Linear diagonal movement (simpler, also smooth)
        # Uncomment below and comment above for linear diagonal movement
        # x_expr = f"mod({x_min}+t*({x_max}-{x_min})/{cycle_duration},{x_max})"
        # y_expr = f"mod({y_min}+t*({y_max}-{y_min})/{cycle_duration},{y_max})"
        
        # Handle font color (hex or named)
        if font_color.startswith('#'):
            # Convert hex to format ffmpeg understands: 0xRRGGBB
            hex_color = font_color.lstrip('#')
            if len(hex_color) == 6:
                font_color_ffmpeg = f"0x{hex_color}"
            else:
                font_color_ffmpeg = "white"  # Fallback
        else:
            font_color_ffmpeg = font_color  # Use color name directly
        
        # Try to find a font that supports Hindi/Unicode
        # Common system fonts that support Unicode/Hindi:
        unicode_fonts = [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # macOS - best for Hindi
            "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS fallback
            "/Library/Fonts/Arial Unicode.ttf",  # macOS alternative
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",  # Linux - good for Hindi
            "C:/Windows/Fonts/arial.ttf",  # Windows
            "C:/Windows/Fonts/arialuni.ttf",  # Windows Unicode
        ]
        
        font_file = None
        for font_path in unicode_fonts:
            if os.path.exists(font_path):
                font_file = font_path
                logger.info(f"Using font for Hindi/Unicode: {font_file}")
                break
        
        # Build drawtext filter with smooth movement
        # Use expressions for X and Y positions to create smooth animation
        if font_file:
            # Escape font file path for ffmpeg (handle spaces and special chars)
            font_file_escaped = font_file.replace(":", "\\:").replace(" ", "\\ ")
            drawtext_filter = (
                f"drawtext="
                f"text='{escaped_text}':"
                f"x={x_expr}:"
                f"y={y_expr}:"
                f"fontsize={font_size}:"
                f"fontcolor={font_color_ffmpeg}@{opacity}:"
                f"fontfile={font_file_escaped}"
            )
        else:
            # No font file found, use default (may not support Hindi well)
            logger.warning("No Unicode font found, using default font (Hindi may not render correctly)")
            drawtext_filter = (
                f"drawtext="
                f"text='{escaped_text}':"
                f"x={x_expr}:"
                f"y={y_expr}:"
                f"fontsize={font_size}:"
                f"fontcolor={font_color_ffmpeg}@{opacity}"
            )
        
        # Build ffmpeg command
        # Use -vf (video filter) for single filter, or -filter_complex for complex filters
        cmd = [
            ffmpeg_path,
            '-i', video_path,
            '-vf', drawtext_filter,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-y',  # Overwrite output
            output_path
        ]
        
        # Log the command for debugging (without sensitive info)
        logger.debug(f"FFmpeg command: {' '.join(cmd[:3])} ... [filter] ... {output_path}")
        
        logger.info(f"Applying smooth moving text watermark to video: {video_path}")
        logger.info(f"Watermark text: {watermark_text}")
        logger.info(f"Font: {font_file or 'default'}")
        logger.info(f"Smooth movement: circular path across video")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0 and os.path.exists(output_path):
            logger.info(f"Watermark applied successfully: {output_path}")
            return True
        else:
            logger.error(f"Failed to apply watermark: {result.stderr}")
            logger.error(f"Command: {' '.join(cmd)}")
            return False
            
    except Exception as e:
        logger.error(f"Error applying watermark: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
