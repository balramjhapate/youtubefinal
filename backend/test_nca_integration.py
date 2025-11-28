import os
import django
import sys

# Setup Django environment
sys.path.append('/home/radha/Downloads/narendras/Video-Scrapper-Automation-RedNote')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rednote_project.settings')
django.setup()

from downloader.nca_toolkit_client import get_nca_client
from django.conf import settings

def test_integration():
    print(f"Testing NCA Toolkit Integration...")
    print(f"URL: {settings.NCA_API_URL}")
    print(f"API Key: {settings.NCA_API_KEY}")
    print(f"Enabled: {settings.NCA_API_ENABLED}")
    
    client = get_nca_client()
    if not client:
        print("Error: Could not initialize NCA Client. Check settings.")
        return

    # Test Health Check
    print("\n1. Testing Health Check...")
    health = client.health_check()
    print(f"Health Check Response: {health}")
    
    if not health.get('success') and health.get('status_code') != 404:
         # Note: The health endpoint might be different or not implemented in this version of the container, 
         # but we saw 404 earlier. Let's try the test endpoint which we know works.
         pass

    # Test Auth/Test Endpoint
    print("\n2. Testing Auth/Test Endpoint...")
    import requests
    try:
        r = requests.get('http://127.0.0.1:8080/v1/toolkit/test', headers={'X-API-Key': settings.NCA_API_KEY})
        print(f"Status Code: {r.status_code}")
        print(f"Content: {r.text}")
        try:
            print(f"JSON: {r.json()}")
        except:
            print("Could not decode JSON")
    except Exception as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    test_integration()
