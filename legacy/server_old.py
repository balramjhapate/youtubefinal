import http.server
import socketserver
import json
import re
import requests
import urllib.parse
from http import HTTPStatus

PORT = 8000

class XHSHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/extract':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                url = data.get('url')
                
                if not url:
                    self.send_error_response("URL is required")
                    return

                video_data = self.extract_video(url)
                
                if video_data:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(video_data).encode('utf-8'))
                else:
                    self.send_error_response("Could not extract video. The link might be invalid or protected.")
            except Exception as e:
                self.send_error_response(str(e))
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")

    def send_error_response(self, message):
        self.send_response(400)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode('utf-8'))

    def extract_video(self, url):
        # Priority 1: Try Seekin.ai API (Works on blocked IPs)
        print(f"Attempting extraction via Seekin.ai API: {url}")
        video_data = self.extract_video_seekin(url)
        if video_data:
            return video_data

        # Priority 2: yt-dlp (Works on local/unblocked IPs)
        print(f"Seekin API failed. Fallback to yt-dlp: {url}")
        try:
            # Use the local yt-dlp binary
            yt_dlp_path = './yt-dlp'
            import os
            if not os.path.exists(yt_dlp_path):
                # Fallback to global command if local binary not found
                yt_dlp_path = 'yt-dlp'

            import subprocess
            result = subprocess.run(
                [yt_dlp_path, '--dump-json', url],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"yt-dlp error: {result.stderr}")
                # Fallback to requests method if yt-dlp fails
                return self.extract_video_requests(url)

            data = json.loads(result.stdout)
            
            # yt-dlp returns the direct video url in 'url' or 'requested_downloads'
            video_url = data.get('url')
            if not video_url:
                # Check formats
                formats = data.get('formats', [])
                # Get best video
                best_video = sorted(formats, key=lambda x: x.get('height', 0), reverse=True)[0]
                video_url = best_video.get('url')

            return {
                "video_url": video_url,
                "title": data.get('title', 'Xiaohongshu Video'),
                "cover_url": data.get('thumbnail')
            }

        except Exception as e:
            print(f"yt-dlp extraction failed: {e}")
            return self.extract_video_requests(url)

    def extract_video_seekin(self, url):
        try:
            api_url = "https://api.seekin.ai/ikool/media/download"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            payload = {"url": url}
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == "0000" and data.get("data"):
                video_data = data["data"]
                medias = video_data.get("medias", [])
                video_url = None
                
                # Try to find the best quality video
                if medias:
                    # Sort by file size (assuming larger is better quality) or just take the last one (often HD)
                    # The sample response had "超高清" (Ultra HD) as the second item.
                    # Let's pick the one with the largest fileSize
                    best_media = sorted(medias, key=lambda x: x.get("fileSize", 0), reverse=True)[0]
                    video_url = best_media.get("url")
                
                if video_url:
                    return {
                        "video_url": video_url,
                        "title": video_data.get("title", "Xiaohongshu Video"),
                        "cover_url": video_data.get("imageUrl")
                    }
            
            print(f"Seekin API returned invalid data: {data}")
            return None
            
        except Exception as e:
            print(f"Seekin API error: {e}")
            return None

    def extract_video_requests(self, url):
        print("Fallback to requests extraction...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
             # Add a dummy cookie to look more legit
            'Cookie': 'web_session=123; xsec_token=ABkAboivRVQVrgm3TNrzLjX2giKzFKasGDcrLG-AK4VVg=' 
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            html = response.text
            
            match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
            if match:
                state_json = match.group(1)
                state_json = state_json.replace('undefined', 'null')
                data = json.loads(state_json)
                
                note_data = data.get('note', {}).get('note', {})
                if not note_data:
                    note_data = data.get('note', {})

                video_info = note_data.get('video', {})
                
                video_url = None
                if 'media' in video_info:
                    stream = video_info['media'].get('stream', {}).get('h264', [])
                    if stream:
                        video_url = stream[0].get('masterUrl')
                
                if not video_url:
                     mp4_match = re.search(r'"masterUrl":"(http[^"]+mp4[^"]*)"', state_json)
                     if mp4_match:
                         video_url = mp4_match.group(1)

                if video_url:
                    title = note_data.get('title', 'Xiaohongshu Video')
                    cover_url = note_data.get('imageList', [{}])[0].get('url') if note_data.get('imageList') else None
                    
                    return {
                        "video_url": video_url,
                        "title": title,
                        "cover_url": cover_url
                    }
            
            return None

        except Exception as e:
            print(f"Requests extraction error: {e}")
            return None

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

# Refactored extraction logic
def run_extraction_test():
    url = "https://www.xiaohongshu.com/discovery/item/69147f3200000000050100d4?source=webshare&xhsshare=pc_web&xsec_token=ABkAboivRVQVrgm3TNrzLjX2giKzFKasGDcrLG-AK4VVg=&xsec_source=pc_share"
    print(f"Testing extraction for: {url}")
    
    # We need to access the extraction logic. 
    # Since it's inside the class, let's just create a temporary handler instance with mocks.
    class MockHandler(XHSHandler):
        def __init__(self):
            pass
        def setup(self):
            pass
        def handle(self):
            pass
        def finish(self):
            pass
    
    extractor = MockHandler()
    result = extractor.extract_video(url)
    if result:
        print("SUCCESS: Video extracted successfully!")
        print(f"Title: {result.get('title')}")
        print(f"URL: {result.get('video_url')}")
    else:
        print("FAILURE: Could not extract video. Check logs above for details.")
    print("--- Self-Test Finished ---")

if __name__ == "__main__":
    run_extraction_test()
    
    with ReusableTCPServer(("", PORT), XHSHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
