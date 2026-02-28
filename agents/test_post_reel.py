"""
Test Instagram Reel Posting — Restored and Organized
──────────────────────────────────────────────────
Uploads the reel to a temporary public host and then posts via IG Graph API.
"""

import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

# Load env from root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
BASE_URL = "https://graph.facebook.com/v21.0"

# Path to a rendered reel
REEL_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
VIDEO_FILE = os.path.join(REEL_DIR, "reel_row0_v1.mp4")

CAPTION = (
    "Regret isn't just about mistakes, but the beautiful chances we let pass "
    "and the important words we were too afraid to speak.\n\n"
    "Send this to someone who needs it 💌\n\n"
    "#fyp #viral #explore #motivation #mindset #quotes #life #reels"
)


def upload_to_public_host(filepath):
    """Upload video to a temporary public file host and return the URL."""
    print(f"📤 Uploading {filepath} to public host...")
    
    # Try tmpfiles.org
    try:
        print("   Trying tmpfiles.org...")
        with open(filepath, 'rb') as f:
            response = requests.post(
                'https://tmpfiles.org/api/v1/upload',
                files={'file': (os.path.basename(filepath), f, 'video/mp4')},
                timeout=120,
            )
        if response.status_code == 200:
            data = response.json()
            url = data.get('data', {}).get('url', '')
            if url:
                direct_url = url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
                print(f"   ✅ Uploaded: {direct_url}")
                return direct_url
    except Exception as e:
        print(f"   ⚠️ tmpfiles.org failed: {e}")
    
    return None


def post_reel_to_instagram(video_url, caption):
    """Post a reel to Instagram via Graph API."""
    if not ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        print("❌ Missing Instagram credentials in .env!")
        return None
    
    # Step 1: Create media container
    print("\n   Step 1/3: Creating media container...")
    create_url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    payload = {
        'media_type': 'REELS',
        'video_url': video_url,
        'caption': caption,
        'access_token': ACCESS_TOKEN,
    }
    
    r = requests.post(create_url, data=payload)
    result = r.json()
    if 'id' not in result:
        print(f"❌ Failed to create container: {result}")
        return result
    
    container_id = result['id']
    
    # Step 2: Poll for status
    print("\n   Step 2/3: Waiting for Instagram to process video...")
    status_url = f"{BASE_URL}/{container_id}?fields=status_code,status&access_token={ACCESS_TOKEN}"
    
    for attempt in range(30):
        time.sleep(5)
        r = requests.get(status_url)
        status_data = r.json()
        status_code = status_data.get('status_code', 'UNKNOWN')
        print(f"   [{attempt+1}/30] Status: {status_code}")
        if status_code == 'FINISHED':
            break
        elif status_code == 'ERROR':
            return status_data
    
    # Step 3: Publish
    print("\n   Step 3/3: Publishing reel...")
    publish_url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    r = requests.post(publish_url, data={'creation_id': container_id, 'access_token': ACCESS_TOKEN})
    return r.json()


def main():
    if not os.path.exists(VIDEO_FILE):
        print(f"❌ Video not found: {VIDEO_FILE}")
        return
    
    video_url = upload_to_public_host(VIDEO_FILE)
    if video_url:
        result = post_reel_to_instagram(video_url, CAPTION)
        if result and 'id' in result:
            print(f"\n🎉 SUCCESS! Media ID: {result['id']}")
        else:
            print(f"\n⚠️ Posting failed: {result}")

if __name__ == "__main__":
    main()
