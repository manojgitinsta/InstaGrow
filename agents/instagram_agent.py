import pandas as pd
import requests
import time
import os
import sys
import json
import random

from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load credentials from .env file
load_dotenv()

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
REMOTE_BASE_URL = os.getenv("REMOTE_VIDEO_BASE_URL", "") # Public URL required for IG API

BASE_URL = "https://graph.facebook.com/v21.0"

def get_instagram_account_id(page_id, token):
    """
    Helper to find the IG Business ID linked to the Page
    """
    url = f"{BASE_URL}/{page_id}?fields=instagram_business_account&access_token={token}"
    response = requests.get(url)
    data = response.json()
    if 'instagram_business_account' in data:
        return data['instagram_business_account']['id']
    return None

def upload_video_to_tmpfiles(filepath):
    """Upload a video to tmpfiles.org and return the direct download URL."""
    print(f"   📤 Uploading {os.path.basename(filepath)} to tmpfiles.org...")
    try:
        file_size = os.path.getsize(filepath)
        print(f"   📦 File size: {file_size / (1024*1024):.1f} MB")
        with open(filepath, 'rb') as f:
            response = requests.post(
                'https://tmpfiles.org/api/v1/upload',
                files={'file': (os.path.basename(filepath), f, 'video/mp4')},
                timeout=300,  # 5 min timeout for large videos
            )
        if response.status_code == 200:
            data = response.json()
            url = data.get('data', {}).get('url', '')
            if url:
                direct_url = url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
                print(f"   ✅ Uploaded: {direct_url}")
                return direct_url
        print(f"   ❌ Upload failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Upload error: {e}")
    return None


def post_reel(ig_user_id, video_url, caption, token, audio_name=None):
    """
    Post a reel to Instagram via Graph API.
    """
    # Step 1: Create container
    post_url = f"{BASE_URL}/{ig_user_id}/media"
    payload = {
        'media_type': 'REELS',
        'video_url': video_url,
        'caption': caption,
        'share_to_feed': 'true',  # Also show in main feed
        'access_token': token,
    }
    if audio_name:
        payload['audio_name'] = audio_name

    print(f"   📡 Creating reel container...")
    r = requests.post(post_url, data=payload)
    result = r.json()
    
    if 'id' not in result:
        print(f"   ❌ Failed to create reel container: {result}")
        return result

    creation_id = result['id']
    print(f"   ✅ Container: {creation_id}")
    
    # Step 2: Poll for processing status
    print(f"   ⏳ Waiting for Instagram to process video...")
    status_url = f"{BASE_URL}/{creation_id}?fields=status_code,status&access_token={token}"
    for attempt in range(30):  # Up to 5 min
        time.sleep(10)
        r_status = requests.get(status_url)
        status_data = r_status.json()
        status_code = status_data.get('status_code', 'UNKNOWN')
        print(f"   [{attempt + 1}/30] Status: {status_code}")
        
        if status_code == 'FINISHED':
            break
        elif status_code == 'ERROR':
            print(f"   ❌ Processing error: {status_data}")
            return status_data
    
    # Step 3: Publish
    print(f"   🚀 Publishing reel...")
    publish_url = f"{BASE_URL}/{ig_user_id}/media_publish"
    r_pub = requests.post(publish_url, data={
        'creation_id': creation_id,
        'access_token': token,
    })
    result = r_pub.json()
    
    if 'id' in result:
        print(f"   🎉 REEL PUBLISHED! Media ID: {result['id']}")
    else:
        print(f"   ⚠️ Publish result: {result}")
    
    return result

def run_agent():
    print("🤖 Instagram Agent Starting (Aggressive Growth Mode)...")
    
    # Path to data
    calendar_path = os.path.join(os.path.dirname(__file__), "..", "data", "content_calendar.csv")
    os.makedirs(os.path.dirname(calendar_path), exist_ok=True)
    
    try:
        df = pd.read_csv(calendar_path)
    except FileNotFoundError:
        print(f"Error: {calendar_path} not found!")
        return

    # Check for flood_ready posts first
    ready_posts = df[df['status'] == 'flood_ready']
    
    if not ready_posts.empty:
        post = ready_posts.iloc[0]
        index = ready_posts.index[0]
        print(f"🌊 Processing Flood Content for Row {index}...")
        
        # We assume content_flood generated 1 premium variant (v1)
        output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
        for variant in [1]:
            video_path = os.path.join(output_dir, f"reel_row{index}_v{variant}.mp4")
            if os.path.exists(video_path):
                print(f"🔥 Dispatching Variant {variant}...")
                
                # Build SEO-optimized caption via Gemini
                raw_caption = post['caption'] if pd.notna(post['caption']) else "Stay driven."
                
                try:
                    from engine.seo_caption import generate_reel_caption
                    full_caption = generate_reel_caption(raw_caption, theme="motivation")
                    print("   ✅ SEO caption generated via Gemini (Aggressive Growth Mode)")
                except Exception as e:
                    print(f"   [WARN] SEO caption failed ({e}), using fallback")
                    full_caption = f"Stay driven.\n\n{raw_caption}"
                
                print("   --- Caption Preview ---")
                print(full_caption[:300] + "\n...")
                print("   -----------------------")
                print(f"   Video: {video_path}")
                
                if ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID:
                    # Upload video to tmpfiles.org
                    video_url = upload_video_to_tmpfiles(video_path)
                    if video_url:
                        print(f"   🚀 Posting reel to Instagram...")
                        result = post_reel(
                            INSTAGRAM_ACCOUNT_ID,
                            video_url,
                            full_caption,
                            ACCESS_TOKEN,
                            audio_name="Motivational Vibes",
                        )
                        if result and 'id' in result:
                            print(f"   ✅ Reel posted! Media ID: {result['id']}")
                            
                            # Mark as fully published
                            df.at[index, 'status'] = 'published_variants'
                            df.to_csv(calendar_path, index=False)
                            print("✅ Finished dispatching flood batch.")
                            return True
                        else:
                            print(f"   ⚠️ Reel posting result: {result}")
                            return False
                    else:
                        print("   ❌ Failed to upload video. Reel saved locally for manual upload.")
                        return False
                else:
                    print("   ⚠️ Missing Instagram credentials in .env")
                    return False
            else:
                print(f"   ⚠️ Variant {variant} video not found. Aborting IG upload.")
                return False

    # Fallback to normal pending check
    pending_posts = df[df['status'] == 'pending']
    
    if pending_posts.empty:
        print("No pending posts found.")
        return False

    post = pending_posts.iloc[0]
    index = pending_posts.index[0]
    
    print(f"Processing normal post for {post['date']}: {post['type']}")

    if post['type'] == 'image':
        print("Generating image post logic (Placeholder)...")
        df.at[index, 'status'] = 'generated_ready'

    elif post['type'] == 'reel':
        print("Skipping basic reel generation. Use content_flood.py first for aggressive growth.")

    df.to_csv(calendar_path, index=False)
    print("Updated calendar status.")
    return True

if __name__ == "__main__":
    run_agent()
