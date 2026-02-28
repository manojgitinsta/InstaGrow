import os
import sys
import time
import requests
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.news_fetcher import get_todays_news_story
from engine.generate_story import create_news_story_image
from agents.carousel_agent import upload_image_to_public_host

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
BASE_URL = "https://graph.facebook.com/v21.0"

# Note: Facebook API requires a public URL to upload an image.
# We will mock the upload portion for local dev unless the user has a linked
# server/S3 bucket or ngrok running, similar to how carousel uploads work.
# Alternatively, since there's no native local file upload endpoint in Facebook Graph API,
# we simulate the post mechanism or rely on an external proxy if provided.

def upload_story_container(image_url):
    """Create the initial story media container on IG."""
    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    payload = {
        "image_url": image_url,
        "media_type": "STORIES",
        "access_token": ACCESS_TOKEN
    }
    
    print("   [API] Creating Story Media Container...")
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        container_id = response.json().get("id")
        print(f"   [OK] Container ID: {container_id}")
        return container_id
    else:
        print(f"   [ERROR] Container creation failed: {response.text}")
        return None

def publish_story_container(container_id):
    """Publish the story container."""
    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    payload = {
        "creation_id": container_id,
        "access_token": ACCESS_TOKEN
    }
    
    print("   [API] Publishing Story...")
    max_retries = 3
    for attempt in range(max_retries):
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            media_id = response.json().get("id")
            print(f"   [FINAL OK] Story published successfully! ID: {media_id}")
            return True
            
        err = response.json()
        if "error" in err and err["error"].get("code") == 9007:
            print(f"   [WAIT] Container {container_id} not ready. Waiting 10s (attempt {attempt+1}/{max_retries})...")
            time.sleep(10)
        else:
             print(f"   [ERROR] Failed to post: {response.text}")
             break
    
    return False

def run_story_agent(dry_run=True, mock_url="https://images.pexels.com/photos/1484794/pexels-photo-1484794.jpeg?auto=compress&cs=tinysrgb&w=1080&h=1920&dpr=2"):
    """Orchestrates fetching, rendering, and posting the Morning Story."""
    print("\n" + "=" * 60)
    print(f"[START] MORNING STORY AGENT {'(DRY RUN)' if dry_run else '(LIVE MODE)'}")
    print("=" * 60)

    # 1. Fetch & Curate News
    print("\n1. Sourcing Positive News...")
    story_data = get_todays_news_story()
    if not story_data:
        print("[EXIT] Could not fetch news. Aborting.")
        return False
        
    try:
        safe_headline = story_data['headline'].encode('ascii', 'ignore').decode('ascii')
    except:
        safe_headline = story_data['headline']
    print(f"   -> Headline: '{safe_headline}'")

    # 2. Render Image
    print("\n2. Generating 9:16 Story Graphic...")
    output_path = os.path.join(os.path.dirname(__file__), "..", "output", "morning_story.jpg")
    success = create_news_story_image(story_data['headline'], story_data['summary'], output_path)
    
    if not success:
        print("[EXIT] Failed to render story image. Aborting.")
        return False

    # 3. Publish to IG
    print("\n3. Publishing to Instagram Stories...")
    if dry_run:
        print(f"   [DRY RUN] Image generated at: {output_path}")
        print("   [DRY RUN] Would upload to Graph API with media_type='STORIES'")
        print("=" * 60)
        return True

    # Note: Instagram Graph API requires a public URL for the image container.
    # We use tmpfiles.org to temporarily host the file for the Instagram servers to grab.
    print("\n   [API] Uploading local image to temporary public host for IG...")
    public_url = upload_image_to_public_host(output_path)
    
    if not public_url:
        print("   [ERROR] Failed to upload to public host.")
        return False
        
    container_id = upload_story_container(public_url)
    if not container_id:
        print("   [ERROR] Failed to create story container. Aborting.")
        return False
        
    publish_success = publish_story_container(container_id)
    if not publish_success:
        print("   [ERROR] Failed to publish story. Aborting.")
        return False
        
    print("=" * 60)
    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Run in LIVE mode (actually posts to Stories)")
    args = parser.parse_args()
    
    run_story_agent(dry_run=not args.live)
