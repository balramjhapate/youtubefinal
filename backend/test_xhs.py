import requests
import re
import json

def get_xhs_video(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.xiaohongshu.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        print(f"Fetching {url}...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        html = response.text
        print("Page fetched successfully.")
        
        # Look for initial state
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            print("Found initial state.")
            # Navigate JSON to find video URL
            # Note: The structure needs to be explored. 
            # Usually under note -> video -> url
            return data
        else:
            print("Could not find initial state.")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    url = "https://www.xiaohongshu.com/discovery/item/69147f3200000000050100d4?source=webshare&xhsshare=pc_web&xsec_token=ABkAboivRVQVrgm3TNrzLjX2giKzFKasGDcrLG-AK4VVg=&xsec_source=pc_share"
    data = get_xhs_video(url)
    if data:
        print("Data found (truncated):", str(data)[:500])
