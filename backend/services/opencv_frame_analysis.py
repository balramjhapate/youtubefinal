"""
OpenCV-based Frame Analysis Module
Comprehensive frame analysis pipeline that extracts visual features from video frames
and outputs structured JSON data for AI transcript generation.
"""
import cv2
import numpy as np
import os
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict

# Optional dependencies
try:
    import pytesseract
    HAVE_TESSERACT = True
except ImportError:
    HAVE_TESSERACT = False


# Configuration
MAX_FRAMES = 60  # Maximum frames to sample
RESIZE_W = 640  # Resize width for faster processing
MOTION_THRESHOLD = 5.0  # Threshold for motion detection
SCENE_CHANGE_THRESHOLD = 0.3  # Histogram difference threshold for scene change


def dominant_color(img, k=3) -> Tuple[int, int, int]:
    """
    Extract dominant color using K-means clustering.
    
    Returns:
        tuple: (R, G, B) values
    """
    img_small = cv2.resize(img, (64, 64))
    data = img_small.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    counts = np.bincount(labels.flatten())
    dominant = centers[np.argmax(counts)].astype(int)
    # Return as (R, G, B) - OpenCV uses BGR, so reverse
    return int(dominant[2]), int(dominant[1]), int(dominant[0])


def detect_faces(frame_gray, face_cascade) -> List[Dict]:
    """
    Detect faces in frame using Haar cascade.
    
    Returns:
        list: List of face bounding boxes [{"bbox": [x, y, w, h]}]
    """
    faces = []
    try:
        face_rects = face_cascade.detectMultiScale(frame_gray, 1.1, 4)
        for (x, y, w, h) in face_rects:
            faces.append({"bbox": [int(x), int(y), int(w), int(h)]})
    except Exception as e:
        print(f"Face detection error: {e}")
    return faces


def detect_objects_opencv(frame) -> List[Dict]:
    """
    Placeholder for object detection.
    Can be extended with YOLO, MobileNet-SSD, or other models.
    
    Returns:
        list: List of detected objects [{"label": str, "score": float, "bbox": [x, y, w, h]}]
    """
    # TODO: Implement with YOLO/MobileNet if needed
    # For now, return empty list
    return []


def extract_ocr_text(frame_gray) -> str:
    """
    Extract text from frame using OCR (pytesseract).
    
    Returns:
        str: Extracted text
    """
    if not HAVE_TESSERACT:
        return ""
    
    try:
        # Preprocess for better OCR
        _, thresh = cv2.threshold(frame_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(thresh, lang='eng+hin')
        return text.strip()
    except Exception as e:
        print(f"OCR error: {e}")
        return ""


def calculate_motion_score(frame_gray, prev_frame_gray) -> float:
    """
    Calculate motion score by comparing current frame with previous frame.
    
    Returns:
        float: Motion score (higher = more motion)
    """
    if prev_frame_gray is None:
        return 0.0
    
    try:
        # Resize both frames to same size for comparison
        h, w = frame_gray.shape[:2]
        prev_resized = cv2.resize(prev_frame_gray, (w, h))
        
        # Calculate absolute difference
        diff = cv2.absdiff(frame_gray, prev_resized)
        motion_score = np.mean(diff)
        return float(motion_score)
    except Exception as e:
        print(f"Motion calculation error: {e}")
        return 0.0


def detect_scene_change(frame, prev_hist) -> Tuple[bool, np.ndarray]:
    """
    Detect scene change using histogram comparison.
    
    Returns:
        tuple: (is_scene_change: bool, current_histogram: np.ndarray)
    """
    try:
        # Calculate histogram for each channel
        hist_b = cv2.calcHist([frame], [0], None, [256], [0, 256])
        hist_g = cv2.calcHist([frame], [1], None, [256], [0, 256])
        hist_r = cv2.calcHist([frame], [2], None, [256], [0, 256])
        current_hist = np.concatenate([hist_b, hist_g, hist_r])
        
        if prev_hist is None:
            return False, current_hist
        
        # Normalize histograms
        current_hist = current_hist / (current_hist.sum() + 1e-7)
        prev_hist_norm = prev_hist / (prev_hist.sum() + 1e-7)
        
        # Calculate correlation
        correlation = cv2.compareHist(prev_hist_norm.reshape(-1, 1).astype(np.float32),
                                     current_hist.reshape(-1, 1).astype(np.float32),
                                     cv2.HISTCMP_CORREL)
        
        # Scene change if correlation is below threshold
        is_scene_change = correlation < (1.0 - SCENE_CHANGE_THRESHOLD)
        
        return is_scene_change, current_hist
    except Exception as e:
        print(f"Scene change detection error: {e}")
        return False, None


def analyze_frame_comprehensive(frame, frame_index, timestamp, prev_frame_gray=None, prev_hist=None, face_cascade=None) -> Dict:
    """
    Comprehensive frame analysis using OpenCV.
    
    Args:
        frame: BGR frame image
        frame_index: Frame index in video
        timestamp: Timestamp in seconds
        prev_frame_gray: Previous frame (grayscale) for motion detection
        prev_hist: Previous histogram for scene change detection
        face_cascade: Haar cascade for face detection
        
    Returns:
        dict: Comprehensive frame analysis data
    """
    try:
        h, w = frame.shape[:2]
        
        # Resize for faster processing
        scale = RESIZE_W / float(w) if w > RESIZE_W else 1.0
        if scale != 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            frame_proc = cv2.resize(frame, (new_w, new_h))
        else:
            frame_proc = frame
        
        # Convert to grayscale for some operations
        frame_gray = cv2.cvtColor(frame_proc, cv2.COLOR_BGR2GRAY)
        
        # Extract features
        dominant_color_rgb = dominant_color(frame_proc)
        
        # Motion score
        motion_score = calculate_motion_score(frame_gray, prev_frame_gray)
        
        # Scene change detection
        scene_change, current_hist = detect_scene_change(frame_proc, prev_hist)
        
        # Face detection
        faces = []
        if face_cascade is not None:
            faces = detect_faces(frame_gray, face_cascade)
        
        # Object detection (placeholder - can be extended)
        objects = detect_objects_opencv(frame_proc)
        
        # OCR text extraction
        ocr_text = extract_ocr_text(frame_gray)
        
        return {
            'frame_index': frame_index,
            'timestamp': float(timestamp),
            'dominant_color_rgb': list(dominant_color_rgb),
            'motion_score': float(motion_score),
            'scene_change': bool(scene_change),
            'faces': faces,
            'objects': objects,
            'ocr_text': ocr_text,
            'histogram': current_hist.tolist() if current_hist is not None else None
        }
    except Exception as e:
        print(f"Error analyzing frame {frame_index}: {e}")
        return {
            'frame_index': frame_index,
            'timestamp': float(timestamp),
            'error': str(e)
        }


def analyze_video_frames_comprehensive(video_path: str, output_dir: str, max_frames: int = MAX_FRAMES) -> Tuple[List[Dict], str]:
    """
    Analyze video frames comprehensively and output JSONL file.
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save frames and JSONL
        max_frames: Maximum number of frames to sample
        
    Returns:
        tuple: (list of frame analysis dicts, path to JSONL file)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize face detector
    try:
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    except Exception as e:
        print(f"Warning: Could not load face cascade: {e}")
        face_cascade = None
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    duration = frame_count / fps if fps > 0 else 0
    
    # Choose evenly spaced frames
    if frame_count <= max_frames:
        indices = list(range(frame_count))
    else:
        step = frame_count / max_frames
        indices = [int(i * step) for i in range(max_frames)]
    
    results = []
    prev_hist = None
    prev_frame_gray = None
    jsonl_path = os.path.join(output_dir, 'frames.jsonl')
    
    # Open JSONL file for writing
    with open(jsonl_path, 'w', encoding='utf-8') as jsonl_file:
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            # Calculate timestamp
            timestamp = idx / fps if fps > 0 else 0.0
            
            # Analyze frame
            frame_data = analyze_frame_comprehensive(
                frame, idx, timestamp,
                prev_frame_gray=prev_frame_gray,
                prev_hist=prev_hist,
                face_cascade=face_cascade
            )
            
            # Save frame image
            frame_filename = f"frame_{idx}.jpg"
            frame_path = os.path.join(output_dir, frame_filename)
            cv2.imwrite(frame_path, frame)
            frame_data['image_path'] = frame_filename
            
            # Update previous frame data
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            prev_frame_gray = frame_gray
            if frame_data.get('histogram') is not None:
                prev_hist = np.array(frame_data['histogram'])
            
            # Remove histogram from output (too large for JSON)
            frame_data.pop('histogram', None)
            
            # Write to JSONL
            jsonl_file.write(json.dumps(frame_data, ensure_ascii=False) + '\n')
            results.append(frame_data)
    
    cap.release()
    
    print(f"[OPENCV PIPELINE] Analyzed {len(results)} frames from video")
    print(f"[OPENCV PIPELINE] Output: {jsonl_path}")
    print(f"[OPENCV PIPELINE] Frames saved to: {output_dir}")
    
    return results, jsonl_path


def analyze_frame_with_opencv(frame_path: str) -> Dict[str, any]:
    """
    Legacy function for single frame analysis (backward compatibility).
    """
    try:
        if not os.path.exists(frame_path):
            return {
                'error': f'Frame file not found: {frame_path}',
                'description': ''
            }
        
        frame = cv2.imread(frame_path)
        if frame is None:
            return {
                'error': f'Could not load frame: {frame_path}',
                'description': ''
            }
        
        # Use comprehensive analysis
        frame_data = analyze_frame_comprehensive(frame, 0, 0.0)
        
        # Generate description from frame data
        description_parts = []
        
        if frame_data.get('scene_change'):
            description_parts.append("Scene change detected")
        
        if frame_data.get('faces'):
            description_parts.append(f"{len(frame_data['faces'])} person(s) detected")
        
        if frame_data.get('objects'):
            obj_labels = [obj.get('label', 'object') for obj in frame_data['objects']]
            description_parts.append(f"Objects: {', '.join(obj_labels)}")
        
        if frame_data.get('ocr_text'):
            description_parts.append(f"Text: {frame_data['ocr_text'][:50]}")
        
        if frame_data.get('motion_score', 0) > MOTION_THRESHOLD:
            description_parts.append("High motion detected")
        
        description = ". ".join(description_parts) if description_parts else "Frame analyzed"
        
        return {
            'has_motion': frame_data.get('motion_score', 0) > MOTION_THRESHOLD,
            'brightness': 0.0,  # Not calculated in comprehensive version
            'contrast': 0.0,
            'dominant_colors': [frame_data.get('dominant_color_rgb', [0, 0, 0])],
            'edge_density': 0.0,
            'text_regions': 0,
            'face_count': len(frame_data.get('faces', [])),
            'scene_type': 'unknown',
            'key_objects': [obj.get('label', 'object') for obj in frame_data.get('objects', [])],
            'description': description,
            'error': None,
            'frame_data': frame_data  # Include full data
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'description': f'Error analyzing frame: {str(e)}'
        }


def analyze_frames_batch_opencv(frame_paths: List[str]) -> List[Dict[str, any]]:
    """
    Analyze multiple frames using OpenCV (backward compatibility).
    """
    results = []
    for frame_path in frame_paths:
        result = analyze_frame_with_opencv(frame_path)
        results.append(result)
    return results
