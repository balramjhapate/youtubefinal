"""
Google Sheets service for tracking video data
"""
import json
import logging
import re
import uuid

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    service_account = None
    build = None
    HttpError = Exception

from model import GoogleSheetsSettings, AIProviderSettings
from django.utils import timezone
import re

logger = logging.getLogger(__name__)


def _call_gemini_api(api_key, system_prompt, user_message):
    """Call Google Gemini API using REST"""
    try:
        import requests
        model_names = ['models/gemini-1.5-flash', 'models/gemini-2.0-flash', 'models/gemini-2.5-flash', 'models/gemini-pro']
        
        for model_name in model_names:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
                headers = {'Content-Type': 'application/json'}
                full_prompt = f"{system_prompt}\n\n{user_message}"
                payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
                
                response = requests.post(url, json=payload, headers=headers, timeout=15)  # Reduced timeout to 15s per call
                response.raise_for_status()
                data = response.json()
                
                if 'candidates' in data and len(data['candidates']) > 0:
                    candidate = data['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        text_parts = [part.get('text', '') for part in candidate['content']['parts']]
                        generated_text = ''.join(text_parts).strip()
                        if generated_text:
                            return {'prompt': generated_text, 'status': 'success', 'error': None}
            except Exception:
                continue
        
        return {'prompt': '', 'status': 'failed', 'error': 'Gemini API call failed'}
    except Exception as e:
        return {'prompt': '', 'status': 'failed', 'error': str(e)}


def generate_seo_title_with_gemini(video, api_key):
    """
    Generate SEO-optimized English title using Gemini API
    
    Args:
        video: VideoDownload instance
        api_key: Gemini API key
    
    Returns:
        str: SEO-optimized English title
    """
    try:
        # Get video context
        raw_title = video.generated_title or video.title or 'Untitled'
        raw_description = video.generated_description or video.description or ''
        transcript = getattr(video, 'transcript', '') or ''
        duration = video.duration or 0
        is_short = duration <= 180  # YouTube Shorts are <= 3 minutes (180 seconds)
        
        # Build context
        context = f"Original Title: {raw_title}\n"
        if raw_description:
            context += f"Description: {raw_description}\n"
        if transcript:
            # Use first 500 chars of transcript for context
            context += f"Transcript (excerpt): {transcript[:500]}...\n"
        context += f"Video Duration: {duration} seconds\n"
        if is_short:
            context += "This is a YouTube Short (<= 60 seconds)\n"
        
        system_prompt = """You are an expert SEO content writer specializing in YouTube titles. 
Generate a compelling, SEO-optimized English title that:
1. Is engaging and click-worthy (max 100 characters - YouTube's limit)
2. Includes relevant keywords for YouTube
3. Creates curiosity or emotional appeal
4. Is optimized for YouTube algorithm
5. Does NOT include hashtags in the title itself
6. Is in English only
7. Keep under 100 characters to ensure full visibility

Return ONLY the title text, nothing else."""

        user_message = f"""Based on this video information, generate an SEO-optimized English title:

{context}

Generate a compelling title that will maximize views and engagement for YouTube."""

        result = _call_gemini_api(api_key, system_prompt, user_message)
        
        if result['status'] == 'success' and result['prompt']:
            title = result['prompt'].strip()
            # Remove any quotes or extra formatting
            title = title.strip('"\'')
            # Ensure max 100 chars (YouTube limit)
            if len(title) > 100:
                title = title[:97] + "..."
            return title
        else:
            # Fallback to original title
            logger.warning(f"Gemini title generation failed: {result.get('error', 'Unknown error')}")
            return raw_title[:100] if len(raw_title) > 100 else raw_title
            
    except Exception as e:
        logger.error(f"Error generating SEO title: {str(e)}")
        raw_title = video.generated_title or video.title or 'Untitled'
        return raw_title[:100] if len(raw_title) > 100 else raw_title


def generate_seo_description_with_gemini(video, api_key):
    """
    Generate SEO-optimized English description using Gemini API
    
    Args:
        video: VideoDownload instance
        api_key: Gemini API key
    
    Returns:
        str: SEO-optimized English description
    """
    try:
        # Get video context
        raw_title = video.generated_title or video.title or 'Untitled'
        raw_description = video.generated_description or video.description or ''
        transcript = getattr(video, 'transcript', '') or ''
        duration = video.duration or 0
        is_short = duration <= 180  # YouTube Shorts are <= 3 minutes (180 seconds)
        
        # Build context
        context = f"Original Title: {raw_title}\n"
        if raw_description:
            context += f"Description: {raw_description}\n"
        if transcript:
            # Use first 1000 chars of transcript
            context += f"Transcript (excerpt): {transcript[:1000]}...\n"
        context += f"Video Duration: {duration} seconds\n"
        if is_short:
            context += "This is a YouTube Short (<= 3 minutes)\n"
        
        system_prompt = """You are an expert SEO content writer specializing in YouTube descriptions. 
Generate a compelling, SEO-optimized English description that:
1. Is engaging and encourages viewers to watch (max 5,000 characters - YouTube's limit)
2. Includes a call-to-action
3. Creates curiosity or emotional connection
4. Is optimized for YouTube algorithm
5. Is in English only
6. Use first 125 characters for the hook (visible without expansion)
7. At the END of the description, add a section with trending hashtags based on current daily trending topics from the web
8. Research current trending topics, news, and viral hashtags from Twitter/X, YouTube, and Google Trends
9. Include relevant trending hashtags that match the video content (examples: #imrankhan, #pakistan, #trending, #viral, etc.)
10. Format trending tags at the end like: "\\n\\nTrending Tags: #tag1 #tag2 #tag3..."

Return the complete description with trending tags at the end."""

        user_message = f"""Based on this video information, generate an SEO-optimized English description for YouTube:

{context}

IMPORTANT: 
- Analyze current daily trending topics from the web (Twitter/X, YouTube, Google Trends, news)
- Include relevant trending hashtags at the end of the description
- Examples of trending topics to check: current news, viral topics, political events, celebrity news, etc.
- Make sure trending tags are relevant to the video content

Generate a compelling description that will maximize engagement for YouTube with trending tags included."""

        result = _call_gemini_api(api_key, system_prompt, user_message)
        
        if result['status'] == 'success' and result['prompt']:
            description = result['prompt'].strip()
            # Remove any quotes or extra formatting
            description = description.strip('"\'')
            # Ensure max 5,000 chars (YouTube limit)
            if len(description) > 5000:
                # Try to preserve trending tags section
                if "Trending Tags:" in description or "trending" in description.lower():
                    # Keep last 500 chars for trending tags if possible
                    main_desc = description[:4500]
                    tags_section = description[4500:]
                    description = main_desc + "..." + tags_section
                    if len(description) > 5000:
                        description = description[:4997] + "..."
                else:
                    description = description[:4997] + "..."
            return description
        else:
            # Fallback to original description
            logger.warning(f"Gemini description generation failed: {result.get('error', 'Unknown error')}")
            return raw_description[:5000] if raw_description else ""
            
    except Exception as e:
        logger.error(f"Error generating SEO description: {str(e)}")
        raw_description = video.generated_description or video.description or ''
        return raw_description[:5000] if raw_description else ""


def get_trending_tags_with_gemini(video, api_key, existing_tags=""):
    """
    Get trending tags from Twitter/YouTube using Gemini API
    
    Args:
        video: VideoDownload instance
        api_key: Gemini API key
        existing_tags: Existing tags to enhance
    
    Returns:
        str: Trending tags including #Shorts if applicable
    """
    try:
        duration = video.duration or 0
        is_short = duration <= 60
        raw_title = video.generated_title or video.title or 'Untitled'
        raw_description = video.generated_description or video.description or ''
        transcript = getattr(video, 'transcript', '') or ''
        
        # Build context
        context = f"Video Title: {raw_title}\n"
        if raw_description:
            context += f"Description: {raw_description}\n"
        if transcript:
            context += f"Transcript (excerpt): {transcript[:500]}...\n"
        if existing_tags:
            context += f"Existing Tags: {existing_tags}\n"
        
        system_prompt = """You are an expert social media analyst specializing in trending hashtags on Twitter/X and YouTube.
Generate a list of trending, relevant hashtags for YouTube that:
1. Are currently popular on Twitter/X and YouTube
2. Are relevant to the video content
3. Include mix of broad and niche tags
4. Are optimized for discoverability
5. Each tag must be max 30 characters (YouTube limit per tag)
6. Total tags must not exceed 500 characters (YouTube limit)
7. Include 10-15 hashtags total
8. Are in English
9. Do NOT include #Shorts (it will be added automatically if needed)

Return ONLY the hashtags separated by spaces, like: #trending #viral #funny #amazing etc.
Do NOT include any other text."""

        user_message = f"""Based on this video information, generate trending hashtags from Twitter and YouTube:

{context}

Generate relevant trending hashtags that will maximize discoverability on YouTube."""

        result = _call_gemini_api(api_key, system_prompt, user_message)
        
        tags_list = []
        
        # Add #Shorts if video is <= 3 minutes (180 seconds)
        if is_short:
            tags_list.append("#Shorts")
        
        # Parse Gemini response
        if result['status'] == 'success' and result['prompt']:
            gemini_tags = result['prompt'].strip()
            # Extract hashtags from response
            hashtags = re.findall(r'#\w+', gemini_tags)
            # Filter tags to max 30 chars each and limit total to 500 chars
            total_length = len("#Shorts ") if is_short else 0
            for tag in hashtags:
                if len(tag) <= 30:  # YouTube limit per tag
                    if tag not in tags_list:
                        # Check if adding this tag would exceed 500 char limit
                        test_string = " ".join(tags_list + [tag])
                        if len(test_string) <= 500:
                            tags_list.append(tag)
                            total_length += len(tag) + 1
                        else:
                            break  # Stop if we'd exceed limit
        
        # Add existing tags if provided
        if existing_tags:
            existing_hashtags = re.findall(r'#\w+', existing_tags)
            for tag in existing_hashtags:
                if len(tag) <= 30 and tag not in tags_list:
                    test_string = " ".join(tags_list + [tag])
                    if len(test_string) <= 500:
                        tags_list.append(tag)
                    else:
                        break
        
        # Ensure we have at least some tags
        if not tags_list:
            default_tags = ["#trending", "#viral", "#shorts" if is_short else "#video", "#amazing", "#mustwatch"]
            tags_list.extend(default_tags)
        
        # Join tags, ensure total <= 500 chars (YouTube limit)
        tags_string = " ".join(tags_list)
        # Ensure total doesn't exceed 500 chars
        if len(tags_string) > 500:
            # Trim tags to fit
            while len(tags_string) > 500 and tags_list:
                tags_list.pop()
                tags_string = " ".join(tags_list)
        
        return tags_string
        
    except Exception as e:
        logger.error(f"Error generating trending tags: {str(e)}")
        # Fallback tags
        tags_list = []
        if duration and duration <= 180:
            tags_list.append("#Shorts")
        tags_list.extend(["#trending", "#viral", "#amazing", "#mustwatch"])
        return " ".join(tags_list)


def generate_facebook_title_with_gemini(video, api_key):
    """
    Generate SEO-optimized English title for Facebook using Gemini API
    
    Args:
        video: VideoDownload instance
        api_key: Gemini API key
    
    Returns:
        str: SEO-optimized English title for Facebook
    """
    try:
        raw_title = video.generated_title or video.title or 'Untitled'
        raw_description = video.generated_description or video.description or ''
        transcript = getattr(video, 'transcript', '') or ''
        duration = video.duration or 0
        
        context = f"Original Title: {raw_title}\n"
        if raw_description:
            context += f"Description: {raw_description}\n"
        if transcript:
            context += f"Transcript (excerpt): {transcript[:500]}...\n"
        context += f"Video Duration: {duration} seconds\n"
        
        system_prompt = """You are an expert SEO content writer specializing in Facebook video titles. 
Generate a compelling, SEO-optimized English title for Facebook that:
1. Is engaging and click-worthy (max 100 characters - Facebook's limit)
2. Includes relevant keywords for Facebook algorithm
3. Creates curiosity or emotional appeal
4. Is optimized for Facebook feed engagement
5. Does NOT include hashtags in the title itself
6. Is in English only
7. Works well for Facebook's audience

Return ONLY the title text, nothing else."""

        user_message = f"""Based on this video information, generate an SEO-optimized English title for Facebook:

{context}

Generate a compelling title that will maximize engagement on Facebook."""

        result = _call_gemini_api(api_key, system_prompt, user_message)
        
        if result['status'] == 'success' and result['prompt']:
            title = result['prompt'].strip().strip('"\'')
            if len(title) > 100:
                title = title[:97] + "..."
            return title
        else:
            logger.warning(f"Gemini Facebook title generation failed: {result.get('error', 'Unknown error')}")
            return raw_title[:100] if len(raw_title) > 100 else raw_title
            
    except Exception as e:
        logger.error(f"Error generating Facebook SEO title: {str(e)}")
        raw_title = video.generated_title or video.title or 'Untitled'
        return raw_title[:100] if len(raw_title) > 100 else raw_title


def generate_facebook_description_with_gemini(video, api_key):
    """
    Generate SEO-optimized English description for Facebook using Gemini API
    
    Args:
        video: VideoDownload instance
        api_key: Gemini API key
    
    Returns:
        str: SEO-optimized English description for Facebook
    """
    try:
        raw_title = video.generated_title or video.title or 'Untitled'
        raw_description = video.generated_description or video.description or ''
        transcript = getattr(video, 'transcript', '') or ''
        duration = video.duration or 0
        
        context = f"Original Title: {raw_title}\n"
        if raw_description:
            context += f"Description: {raw_description}\n"
        if transcript:
            context += f"Transcript (excerpt): {transcript[:1000]}...\n"
        context += f"Video Duration: {duration} seconds\n"
        
        system_prompt = """You are an expert SEO content writer specializing in Facebook video descriptions. 
Generate a compelling, SEO-optimized English description for Facebook that:
1. Is engaging and encourages viewers to watch (max 10,000 characters - Facebook's limit)
2. Includes a call-to-action
3. Creates curiosity or emotional connection
4. Is optimized for Facebook algorithm
5. Does NOT include hashtags in the description text itself
6. Is in English only
7. Works well for Facebook's audience
8. Keep first 300 characters compelling (visible in link previews)

Return ONLY the description text, nothing else."""

        user_message = f"""Based on this video information, generate an SEO-optimized English description for Facebook:

{context}

Generate a compelling description that will maximize engagement on Facebook."""

        result = _call_gemini_api(api_key, system_prompt, user_message)
        
        if result['status'] == 'success' and result['prompt']:
            description = result['prompt'].strip().strip('"\'')
            if len(description) > 10000:
                description = description[:9997] + "..."
            return description
        else:
            logger.warning(f"Gemini Facebook description generation failed: {result.get('error', 'Unknown error')}")
            return raw_description[:10000] if raw_description else ""
            
    except Exception as e:
        logger.error(f"Error generating Facebook SEO description: {str(e)}")
        raw_description = video.generated_description or video.description or ''
        return raw_description[:10000] if raw_description else ""


def get_facebook_trending_tags_with_gemini(video, api_key, existing_tags=""):
    """
    Get trending tags for Facebook using Gemini API
    
    Args:
        video: VideoDownload instance
        api_key: Gemini API key
        existing_tags: Existing tags to enhance
    
    Returns:
        str: Trending Facebook tags
    """
    try:
        duration = video.duration or 0
        raw_title = video.generated_title or video.title or 'Untitled'
        raw_description = video.generated_description or video.description or ''
        transcript = getattr(video, 'transcript', '') or ''
        
        context = f"Video Title: {raw_title}\n"
        if raw_description:
            context += f"Description: {raw_description}\n"
        if transcript:
            context += f"Transcript (excerpt): {transcript[:500]}...\n"
        if existing_tags:
            context += f"Existing Tags: {existing_tags}\n"
        
        system_prompt = """You are an expert social media analyst specializing in trending hashtags on Facebook.
Generate a list of trending, relevant hashtags for Facebook that:
1. Are currently popular on Facebook
2. Are relevant to the video content
3. Include mix of broad and niche tags
4. Are optimized for Facebook discoverability
5. Include 1-3 hashtags total (Facebook best practice - avoid spammy appearance)
6. Are in English
7. Work well for Facebook's algorithm

Return ONLY the hashtags separated by spaces, like: #trending #viral #funny etc.
Do NOT include any other text."""

        user_message = f"""Based on this video information, generate trending hashtags for Facebook:

{context}

Generate relevant trending hashtags that will maximize discoverability on Facebook."""

        result = _call_gemini_api(api_key, system_prompt, user_message)
        
        tags_list = []
        
        # Parse Gemini response
        if result['status'] == 'success' and result['prompt']:
            gemini_tags = result['prompt'].strip()
            hashtags = re.findall(r'#\w+', gemini_tags)
            # Facebook best practice: 1-3 hashtags
            tags_list.extend(hashtags[:3])
        
        # Add existing tags if provided (limit to 3 total for Facebook)
        if existing_tags and len(tags_list) < 3:
            existing_hashtags = re.findall(r'#\w+', existing_tags)
            for tag in existing_hashtags:
                if tag not in tags_list and len(tags_list) < 3:
                    tags_list.append(tag)
        
        # Ensure we have at least some tags (but max 3 for Facebook)
        if not tags_list:
            default_tags = ["#trending", "#viral", "#facebook"]
            tags_list.extend(default_tags[:3])
        
        # Limit to 3 tags for Facebook best practice
        tags_string = " ".join(tags_list[:3])
        
        return tags_string
        
    except Exception as e:
        logger.error(f"Error generating Facebook trending tags: {str(e)}")
        tags_list = ["#trending", "#viral", "#facebook", "#amazing", "#mustwatch"]
        return " ".join(tags_list)


def generate_instagram_title_with_gemini(video, api_key):
    """
    Generate SEO-optimized English title for Instagram using Gemini API
    
    Args:
        video: VideoDownload instance
        api_key: Gemini API key
    
    Returns:
        str: SEO-optimized English title for Instagram
    """
    try:
        raw_title = video.generated_title or video.title or 'Untitled'
        raw_description = video.generated_description or video.description or ''
        transcript = getattr(video, 'transcript', '') or ''
        duration = video.duration or 0
        
        context = f"Original Title: {raw_title}\n"
        if raw_description:
            context += f"Description: {raw_description}\n"
        if transcript:
            context += f"Transcript (excerpt): {transcript[:500]}...\n"
        context += f"Video Duration: {duration} seconds\n"
        
        system_prompt = """You are an expert SEO content writer specializing in Instagram Reels/IGTV captions. 
Generate a compelling, SEO-optimized English caption for Instagram that:
1. Is engaging and click-worthy (max 2,200 characters - Instagram's limit)
2. Includes relevant keywords for Instagram algorithm
3. Creates curiosity or emotional appeal
4. Is optimized for Instagram feed and Reels
5. Does NOT include hashtags in the caption text itself (hashtags go separately)
6. Is in English only
7. Works well for Instagram's audience
8. First 125 characters are most important (visible in feed without expansion)

Return ONLY the caption text, nothing else."""

        user_message = f"""Based on this video information, generate an SEO-optimized English title for Instagram:

{context}

Generate a compelling title that will maximize engagement on Instagram."""

        result = _call_gemini_api(api_key, system_prompt, user_message)
        
        if result['status'] == 'success' and result['prompt']:
            title = result['prompt'].strip().strip('"\'')
            if len(title) > 2200:
                title = title[:2197] + "..."
            return title
        else:
            logger.warning(f"Gemini Instagram caption generation failed: {result.get('error', 'Unknown error')}")
            return raw_title[:2200] if len(raw_title) > 2200 else raw_title
            
    except Exception as e:
        logger.error(f"Error generating Instagram SEO caption: {str(e)}")
        raw_title = video.generated_title or video.title or 'Untitled'
        return raw_title[:2200] if len(raw_title) > 2200 else raw_title


def generate_instagram_description_with_gemini(video, api_key):
    """
    Generate SEO-optimized English description for Instagram using Gemini API
    
    Args:
        video: VideoDownload instance
        api_key: Gemini API key
    
    Returns:
        str: SEO-optimized English description for Instagram
    """
    try:
        raw_title = video.generated_title or video.title or 'Untitled'
        raw_description = video.generated_description or video.description or ''
        transcript = getattr(video, 'transcript', '') or ''
        duration = video.duration or 0
        
        context = f"Original Title: {raw_title}\n"
        if raw_description:
            context += f"Description: {raw_description}\n"
        if transcript:
            context += f"Transcript (excerpt): {transcript[:1000]}...\n"
        context += f"Video Duration: {duration} seconds\n"
        
        system_prompt = """You are an expert SEO content writer specializing in Instagram Reels/IGTV captions. 
Generate a compelling, SEO-optimized English caption for Instagram that:
1. Is engaging and encourages viewers to watch (max 2,200 characters - Instagram's limit)
2. Includes a call-to-action
3. Creates curiosity or emotional connection
4. Is optimized for Instagram algorithm
5. Does NOT include hashtags in the caption text itself (hashtags go separately)
6. Is in English only
7. Works well for Instagram's audience
8. First 125 characters are most important (visible in feed without expansion)

Return ONLY the caption text, nothing else."""

        user_message = f"""Based on this video information, generate an SEO-optimized English caption for Instagram:

{context}

Generate a compelling caption that will maximize engagement on Instagram."""

        result = _call_gemini_api(api_key, system_prompt, user_message)
        
        if result['status'] == 'success' and result['prompt']:
            description = result['prompt'].strip().strip('"\'')
            if len(description) > 2200:
                description = description[:2197] + "..."
            return description
        else:
            logger.warning(f"Gemini Instagram caption generation failed: {result.get('error', 'Unknown error')}")
            return raw_description[:2200] if raw_description else ""
            
    except Exception as e:
        logger.error(f"Error generating Instagram SEO caption: {str(e)}")
        raw_description = video.generated_description or video.description or ''
        return raw_description[:2200] if raw_description else ""


def get_instagram_trending_tags_with_gemini(video, api_key, existing_tags=""):
    """
    Get trending tags for Instagram using Gemini API
    
    Args:
        video: VideoDownload instance
        api_key: Gemini API key
        existing_tags: Existing tags to enhance
    
    Returns:
        str: Trending Instagram tags
    """
    try:
        duration = video.duration or 0
        raw_title = video.generated_title or video.title or 'Untitled'
        raw_description = video.generated_description or video.description or ''
        transcript = getattr(video, 'transcript', '') or ''
        
        context = f"Video Title: {raw_title}\n"
        if raw_description:
            context += f"Description: {raw_description}\n"
        if transcript:
            context += f"Transcript (excerpt): {transcript[:500]}...\n"
        if existing_tags:
            context += f"Existing Tags: {existing_tags}\n"
        
        system_prompt = """You are an expert social media analyst specializing in trending hashtags on Instagram.
Generate a list of trending, relevant hashtags for Instagram that:
1. Are currently popular on Instagram
2. Are relevant to the video content
3. Include mix of broad and niche tags
4. Are optimized for Instagram discoverability
5. Include up to 30 hashtags total (Instagram's maximum limit)
6. Are in English
7. Work well for Instagram's algorithm and Reels
8. Each hashtag should be relevant and not spammy

Return ONLY the hashtags separated by spaces, like: #trending #viral #funny #amazing etc.
Do NOT include any other text."""

        user_message = f"""Based on this video information, generate trending hashtags for Instagram:

{context}

Generate relevant trending hashtags that will maximize discoverability on Instagram."""

        result = _call_gemini_api(api_key, system_prompt, user_message)
        
        tags_list = []
        
        # Parse Gemini response
        if result['status'] == 'success' and result['prompt']:
            gemini_tags = result['prompt'].strip()
            hashtags = re.findall(r'#\w+', gemini_tags)
            # Instagram allows up to 30 hashtags
            tags_list.extend(hashtags[:30])
        
        # Add existing tags if provided (limit to 30 total for Instagram)
        if existing_tags and len(tags_list) < 30:
            existing_hashtags = re.findall(r'#\w+', existing_tags)
            for tag in existing_hashtags:
                if tag not in tags_list and len(tags_list) < 30:
                    tags_list.append(tag)
        
        # Ensure we have at least some tags (but max 30 for Instagram)
        if not tags_list:
            default_tags = ["#trending", "#viral", "#instagram", "#reels", "#video", "#amazing", "#mustwatch"]
            tags_list.extend(default_tags[:30])
        
        # Limit to 30 tags for Instagram (their maximum)
        tags_string = " ".join(tags_list[:30])
        
        return tags_string
        
    except Exception as e:
        logger.error(f"Error generating Instagram trending tags: {str(e)}")
        tags_list = ["#trending", "#viral", "#instagram", "#reels", "#amazing", "#mustwatch"]
        return " ".join(tags_list)


def extract_spreadsheet_id(spreadsheet_id_or_url):
    """Extract spreadsheet ID from URL or return as-is if already an ID"""
    if not spreadsheet_id_or_url:
        return None
    
    # Check if it's a URL
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_id_or_url)
    if match:
        return match.group(1)
    
    # If it doesn't match URL pattern, assume it's already an ID
    return spreadsheet_id_or_url


def get_google_sheets_service():
    """Get Google Sheets API service instance"""
    if not GOOGLE_SHEETS_AVAILABLE:
        logger.warning("Google Sheets packages not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return None
    
    sheets_settings = GoogleSheetsSettings.objects.first()
    if not sheets_settings or not sheets_settings.enabled:
        return None
    
    if not sheets_settings.spreadsheet_id or not sheets_settings.credentials_json:
        logger.warning("Google Sheets is enabled but credentials are missing")
        return None
    
    # Extract spreadsheet ID from URL if needed
    spreadsheet_id = extract_spreadsheet_id(sheets_settings.spreadsheet_id)
    if not spreadsheet_id:
        logger.warning("Could not extract spreadsheet ID")
        return None
    
    try:
        # Parse credentials JSON
        credentials_dict = json.loads(sheets_settings.credentials_json)
        
        # Create credentials object
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Build the service
        service = build('sheets', 'v4', credentials=credentials)
        return {
            'service': service,
            'spreadsheet_id': spreadsheet_id,
            'sheet_name': sheets_settings.sheet_name or 'Sheet1',
        }
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in Google Sheets credentials: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error creating Google Sheets service: {str(e)}")
        return None


def ensure_header_row(sheets_config):
    """Ensure the header row exists in the Google Sheet"""
    try:
        service = sheets_config['service']
        spreadsheet_id = sheets_config['spreadsheet_id']
        sheet_name = sheets_config['sheet_name']
        
        # Check if header row exists
        range_name = f'{sheet_name}!A1:Q1'
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        # If no header row exists, create it
        if not values or len(values) == 0:
            headers = [
                'UUID (Unique ID)',
                'YouTube Title (SEO Optimized)',
                'YouTube Description (with Trending Tags)',
                'YouTube Tags (for Tags Field)',
                'Facebook Title (SEO Optimized)',
                'Facebook Description (SEO Optimized)',
                'Facebook Hashtags (1-3 tags)',
                'Instagram Caption/Title (SEO Optimized)',
                'Instagram Description/Caption (SEO Optimized)',
                'Instagram Hashtags (up to 30)',
                'Video Link (Cloudinary URL)',
                'Original Video URL',
                'Video ID',
                'Duration (seconds)',
                'Created At (Timestamp)',
                'Status (Review Status)',
                'Synced At (Last Sync Time)'
            ]
            
            body = {
                'values': [headers]
            }
            
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'{sheet_name}!A1:Q1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info("Created header row in Google Sheet with UUID, YouTube, Facebook, and Instagram columns")
    except HttpError as e:
        logger.error(f"Error ensuring header row: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error ensuring header row: {str(e)}")


def add_video_to_sheet(video, cloudinary_url=None):
    """
    Add or update video data in Google Sheet.
    If video ID already exists, updates the existing row instead of creating a new one.
    
    Args:
        video: VideoDownload instance
        cloudinary_url: Optional Cloudinary URL (if not provided, uses video.cloudinary_url)
    
    Returns:
        dict: {
            'success': bool,
            'error': str (if failed),
            'action': str ('created' or 'updated')
        }
    """
    import signal
    import threading
    
    # Set a timeout for the entire operation (5 minutes max)
    timeout_seconds = 300
    
    def timeout_handler():
        raise TimeoutError("Google Sheets sync operation timed out after 5 minutes")
    
    timer = threading.Timer(timeout_seconds, timeout_handler)
    timer.start()
    
    try:
        sheets_config = get_google_sheets_service()
        if not sheets_config:
            sheets_settings = GoogleSheetsSettings.objects.first()
            if not sheets_settings:
                error_msg = "Google Sheets settings not found. Please configure in Settings."
            elif not sheets_settings.enabled:
                error_msg = "Google Sheets is disabled. Enable it in Settings."
            elif not sheets_settings.spreadsheet_id:
                error_msg = "Spreadsheet ID is missing. Add it in Settings."
            elif not sheets_settings.credentials_json:
                error_msg = "Service Account credentials are missing. Add them in Settings."
            else:
                error_msg = "Google Sheets configuration error. Check Settings."
            
            logger.warning(f"Google Sheets sync failed: {error_msg}")
            return {'success': False, 'error': error_msg}
        
        service = sheets_config['service']
        spreadsheet_id = sheets_config['spreadsheet_id']
        sheet_name = sheets_config['sheet_name']
        
        # Ensure header row exists
        ensure_header_row(sheets_config)
        
        # Get Gemini API key for SEO generation
        ai_settings = AIProviderSettings.objects.first()
        gemini_api_key = None
        if ai_settings:
            gemini_api_key = ai_settings.get_api_key('gemini') or ai_settings.gemini_api_key
        
        # Generate unique UUID for this video entry
        video_uuid = str(uuid.uuid4())
        
        # Check if video already exists in sheet by Video ID (column M, index 12)
        # Use a more efficient method: search only the Video ID column instead of reading all rows
        existing_row_index = None
        video_id = video.video_id or str(video.id)
        
        try:
            logger.info(f"Checking for existing video ID '{video_id}' in Google Sheet...")
            
            # First, try to find the row by searching column M (Video ID column)
            # Read only column M to find the row index (more efficient than reading all columns)
            video_id_range = f'{sheet_name}!M:M'
            video_id_rows = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=video_id_range
            ).execute()
            
            if video_id_rows.get('values'):
                # Find the row index where Video ID matches (skip header row, so start at index 1)
                for idx, row in enumerate(video_id_rows['values'], start=1):
                    if row and len(row) > 0 and str(row[0]).strip() == str(video_id).strip():
                        existing_row_index = idx + 1  # +1 because sheet rows are 1-indexed, +1 to skip header
                        logger.info(f"Found existing video in Google Sheet at row {existing_row_index}")
                        
                        # Get the UUID from the existing row (column A)
                        uuid_range = f'{sheet_name}!A{existing_row_index}'
                        uuid_result = service.spreadsheets().values().get(
                            spreadsheetId=spreadsheet_id,
                            range=uuid_range
                        ).execute()
                        
                        if uuid_result.get('values') and len(uuid_result['values']) > 0:
                            existing_uuid = uuid_result['values'][0][0] if uuid_result['values'][0] else ''
                            if existing_uuid:
                                video_uuid = existing_uuid
                                logger.info(f"Using existing UUID: {video_uuid}")
                        break
            
            if not existing_row_index:
                logger.info(f"Video ID '{video_id}' not found in sheet, will create new row")
        except Exception as e:
            logger.warning(f"Error checking for existing video in sheet: {str(e)}")
            existing_row_index = None
        
        # Generate SEO-optimized English title using Gemini (with timeout)
        raw_title = video.generated_title or video.title or 'Untitled'
        title = raw_title[:60] if len(raw_title) > 60 else raw_title
        
        if gemini_api_key:
            try:
                # Use existing title if available and not expired (to avoid unnecessary API calls)
                if existing_row_index and video.generated_title:
                    # If updating existing row and we already have a generated title, reuse it
                    title = video.generated_title[:60] if len(video.generated_title) > 60 else video.generated_title
                    logger.info(f"Reusing existing generated title for video {video.id}")
                else:
                    # Generate new title only if creating new row or title is missing
                    title = generate_seo_title_with_gemini(video, gemini_api_key)
                    logger.info(f"Generated SEO title using Gemini for video {video.id}")
            except Exception as e:
                logger.warning(f"Failed to generate SEO title with Gemini: {str(e)}")
                title = raw_title[:60] if len(raw_title) > 60 else raw_title
        else:
            logger.warning("Gemini API key not found, using original title")
        
        # Generate SEO-optimized English description using Gemini (with reuse logic)
        raw_description = video.generated_description or video.description or ''
        description = raw_description[:5000] if raw_description else ""
        
        if gemini_api_key:
            try:
                # Reuse existing description if updating and available
                if existing_row_index and video.generated_description:
                    description = video.generated_description[:5000] if len(video.generated_description) > 5000 else video.generated_description
                    logger.info(f"Reusing existing generated description for video {video.id}")
                else:
                    description = generate_seo_description_with_gemini(video, gemini_api_key)
                    logger.info(f"Generated SEO description using Gemini for video {video.id}")
            except Exception as e:
                logger.warning(f"Failed to generate SEO description with Gemini: {str(e)}")
                description = raw_description[:5000] if raw_description else ""
        else:
            logger.warning("Gemini API key not found, using original description")
        
        # Generate trending tags using Gemini (includes #Shorts if duration <= 3 minutes)
        existing_tags = video.generated_tags or video.ai_tags or ''
        if gemini_api_key:
            try:
                tags = get_trending_tags_with_gemini(video, gemini_api_key, existing_tags)
                logger.info(f"Generated YouTube trending tags using Gemini for video {video.id}")
            except Exception as e:
                logger.warning(f"Failed to generate trending tags with Gemini: {str(e)}")
                # Fallback tags
                duration = video.duration or 0
                tags_list = []
                if duration <= 180:
                    tags_list.append("#Shorts")
                tags_list.extend(["#trending", "#viral", "#amazing"])
                tags = " ".join(tags_list)
        else:
            # Fallback tags
            duration = video.duration or 0
            tags_list = []
            if duration <= 180:
                tags_list.append("#Shorts")
            if existing_tags:
                tags_list.append(existing_tags)
            else:
                tags_list.extend(["#trending", "#viral", "#amazing"])
            tags = " ".join(tags_list)
            logger.warning("Gemini API key not found, using fallback tags")
        
        # Generate Facebook title, description, and tags using Gemini
        facebook_title = ""
        facebook_description = ""
        facebook_tags = ""
        if gemini_api_key:
            try:
                facebook_title = generate_facebook_title_with_gemini(video, gemini_api_key)
                logger.info(f"Generated Facebook title using Gemini for video {video.id}")
            except Exception as e:
                logger.warning(f"Failed to generate Facebook title with Gemini: {str(e)}")
                raw_title = video.generated_title or video.title or 'Untitled'
                facebook_title = raw_title[:100] if len(raw_title) > 100 else raw_title
            
            try:
                facebook_description = generate_facebook_description_with_gemini(video, gemini_api_key)
                logger.info(f"Generated Facebook description using Gemini for video {video.id}")
            except Exception as e:
                logger.warning(f"Failed to generate Facebook description with Gemini: {str(e)}")
                raw_description = video.generated_description or video.description or ''
                facebook_description = raw_description[:500] if raw_description else ""
            
            try:
                facebook_tags = get_facebook_trending_tags_with_gemini(video, gemini_api_key, existing_tags)
                logger.info(f"Generated Facebook tags using Gemini for video {video.id}")
            except Exception as e:
                logger.warning(f"Failed to generate Facebook tags with Gemini: {str(e)}")
                facebook_tags = "#trending #viral #facebook"
        else:
            # Fallback for Facebook
            raw_title = video.generated_title or video.title or 'Untitled'
            facebook_title = raw_title[:100] if len(raw_title) > 100 else raw_title
            raw_description = video.generated_description or video.description or ''
            facebook_description = raw_description[:10000] if raw_description else ""
            facebook_tags = "#trending #viral #facebook"
            logger.warning("Gemini API key not found, using fallback for Facebook content")
        
        # Generate Instagram title, description, and tags using Gemini
        instagram_title = ""
        instagram_description = ""
        instagram_tags = ""
        if gemini_api_key:
            try:
                instagram_title = generate_instagram_title_with_gemini(video, gemini_api_key)
                logger.info(f"Generated Instagram title using Gemini for video {video.id}")
            except Exception as e:
                logger.warning(f"Failed to generate Instagram title with Gemini: {str(e)}")
                raw_title = video.generated_title or video.title or 'Untitled'
                instagram_title = raw_title[:125] if len(raw_title) > 125 else raw_title
            
            try:
                instagram_description = generate_instagram_description_with_gemini(video, gemini_api_key)
                logger.info(f"Generated Instagram description using Gemini for video {video.id}")
            except Exception as e:
                logger.warning(f"Failed to generate Instagram description with Gemini: {str(e)}")
                raw_description = video.generated_description or video.description or ''
                instagram_description = raw_description[:500] if raw_description else ""
            
            try:
                instagram_tags = get_instagram_trending_tags_with_gemini(video, gemini_api_key, existing_tags)
                logger.info(f"Generated Instagram tags using Gemini for video {video.id}")
            except Exception as e:
                logger.warning(f"Failed to generate Instagram tags with Gemini: {str(e)}")
                instagram_tags = "#trending #viral #instagram #reels #amazing #mustwatch"
        else:
            # Fallback for Instagram
            raw_title = video.generated_title or video.title or 'Untitled'
            instagram_title = raw_title[:2200] if len(raw_title) > 2200 else raw_title
            raw_description = video.generated_description or video.description or ''
            instagram_description = raw_description[:2200] if raw_description else ""
            instagram_tags = "#trending #viral #instagram #reels #amazing #mustwatch"
            logger.warning("Gemini API key not found, using fallback for Instagram content")
        
        # Prepare other data
        video_url = cloudinary_url or video.cloudinary_url or video.final_processed_video_url or ''
        original_url = video.url or ''
        video_id = video.video_id or str(video.id)  # Use video_id or fallback to database ID
        duration = str(video.duration) if video.duration else ''
        created_at = video.created_at.strftime('%Y-%m-%d %H:%M:%S') if video.created_at else ''
        status = video.review_status or 'pending_review'
        synced_at = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Prepare row data with UUID as first column, including all platform content
        values = [[
            video_uuid,           # UUID column (A)
            title,                # Title (YouTube) column (B)
            description,          # Description (YouTube) column (C)
            tags,                 # Tags (YouTube) column (D)
            facebook_title,       # Facebook Title column (E)
            facebook_description, # Facebook Description column (F)
            facebook_tags,        # Facebook Tags column (G)
            instagram_title,      # Instagram Title column (H)
            instagram_description,# Instagram Description column (I)
            instagram_tags,       # Instagram Tags column (J)
            video_url,            # Video Link (Cloudinary) column (K)
            original_url,         # Original URL column (L)
            video_id,             # Video ID column (M)
            duration,             # Duration column (N)
            created_at,           # Created At column (O)
            status,               # Status column (P)
            synced_at             # Synced At column (Q)
        ]]
        
        body = {
            'values': values
        }
        
        # Perform update or insert operation
        action = 'updated' if existing_row_index else 'created'
        try:
            if existing_row_index:
                # Update existing row
                result = service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f'{sheet_name}!A{existing_row_index}:Q{existing_row_index}',
                    valueInputOption='RAW',
                    body=body
                ).execute()
                logger.info(f"✓ Successfully updated video in Google Sheet at row {existing_row_index}: {video.id} (UUID: {video_uuid})")
            else:
                # Append new row
                result = service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id,
                    range=f'{sheet_name}!A:Q',
                    valueInputOption='RAW',
                    insertDataOption='INSERT_ROWS',
                    body=body
                ).execute()
                logger.info(f"✓ Successfully added video to Google Sheet: {video.id} (UUID: {video_uuid})")
            
            # Update video model
            video.google_sheets_synced = True
            video.google_sheets_synced_at = timezone.now()
            video.save(update_fields=['google_sheets_synced', 'google_sheets_synced_at'])
            
            timer.cancel()  # Cancel timeout timer on success
            return {'success': True, 'error': None, 'action': action}
        except Exception as e:
            timer.cancel()
            raise
    except HttpError as e:
        error_details = str(e)
        # Extract more specific error information
        if hasattr(e, 'content'):
            try:
                import json
                error_content = json.loads(e.content.decode('utf-8'))
                if 'error' in error_content:
                    error_details = error_content['error'].get('message', error_details)
            except:
                pass
        
        # Common error messages
        if 'PERMISSION_DENIED' in error_details or 'permission' in error_details.lower():
            error_msg = f"Permission denied. Make sure the service account email has edit access to the Google Sheet. Error: {error_details}"
        elif 'NOT_FOUND' in error_details or 'not found' in error_details.lower():
            error_msg = f"Spreadsheet not found. Check the Spreadsheet ID in Settings. Error: {error_details}"
        elif 'UNAUTHENTICATED' in error_details or 'invalid' in error_details.lower():
            error_msg = f"Authentication failed. Check your Service Account JSON credentials in Settings. Error: {error_details}"
        else:
            error_msg = f"Google Sheets API error: {error_details}"
        
        logger.error(f"Error adding video to Google Sheet: {error_msg}")
        return {'success': False, 'error': error_msg, 'action': None}
    except Exception as e:
        timer.cancel()
        error_msg = f"Unexpected error adding video to Google Sheet: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return {'success': False, 'error': error_msg, 'action': None}

