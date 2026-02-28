"""
Carousel Agent — Orchestrates carousel generation + Instagram posting.
═══════════════════════════════════════════════════════════════════════════════════
Generates 3 dark cinematic carousel slides and publishes to Instagram via Graph API.

Usage:
    python agents/carousel_agent.py              # Full run (generate + post)
    python agents/carousel_agent.py --dry-run    # Generate only, skip posting
"""

import os
import sys
import time
import requests

# Ensure Windows console handles emojis/unicode correctly
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
BASE_URL = "https://graph.facebook.com/v21.0"


# ─── Image Upload ──────────────────────────────────────────────────────────────

def upload_image_to_public_host(filepath):
    """Upload an image to a temporary public host and return the URL."""
    print(f"   📤 Uploading {os.path.basename(filepath)}...")

    try:
        with open(filepath, 'rb') as f:
            response = requests.post(
                'https://tmpfiles.org/api/v1/upload',
                files={'file': (os.path.basename(filepath), f, 'image/png')},
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
        print(f"   ⚠️ Upload failed: {e}")

    return None


# ─── Instagram Carousel Posting ────────────────────────────────────────────────

def create_image_container(ig_user_id, image_url, token):
    """Create a single image media container (child of carousel)."""
    url = f"{BASE_URL}/{ig_user_id}/media"
    payload = {
        'image_url': image_url,
        'is_carousel_item': 'true',
        'access_token': token,
    }
    r = requests.post(url, data=payload)
    result = r.json()
    if 'id' in result:
        return result['id']
    else:
        print(f"   ❌ Failed to create image container: {result}")
        return None


def create_carousel_container(ig_user_id, children_ids, caption, token):
    """Create a carousel container from child media IDs."""
    url = f"{BASE_URL}/{ig_user_id}/media"
    payload = {
        'media_type': 'CAROUSEL',
        'children': ','.join(children_ids),
        'caption': caption,
        'access_token': token,
    }
    r = requests.post(url, data=payload)
    result = r.json()
    if 'id' in result:
        return result['id']
    else:
        print(f"   ❌ Failed to create carousel container: {result}")
        return None


def publish_container(ig_user_id, creation_id, token):
    """Publish a media container."""
    # Poll for processing status
    print("   ⏳ Waiting for Instagram to process...")
    status_url = f"{BASE_URL}/{creation_id}?fields=status_code,status&access_token={token}"

    for attempt in range(20):
        time.sleep(3)
        r = requests.get(status_url)
        status_data = r.json()
        status_code = status_data.get('status_code', 'UNKNOWN')
        print(f"   [{attempt + 1}/20] Status: {status_code}")
        if status_code == 'FINISHED':
            break
        elif status_code == 'ERROR':
            print(f"   ❌ Processing error: {status_data}")
            return None

    # Publish
    publish_url = f"{BASE_URL}/{ig_user_id}/media_publish"
    r = requests.post(publish_url, data={
        'creation_id': creation_id,
        'access_token': token,
    })
    return r.json()


def post_carousel_to_instagram(slide_paths, caption):
    """
    Full carousel posting flow:
    1. Upload each image to public host
    2. Create child containers for each
    3. Create carousel parent container
    4. Publish
    """
    if not ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        print("❌ Missing Instagram credentials in .env!")
        return None

    print("\n🚀 Posting carousel to Instagram...")

    # Step 1: Upload images and create child containers
    children_ids = []
    for i, path in enumerate(slide_paths):
        print(f"\n   Slide {i + 1}/{len(slide_paths)}:")

        # Upload to public host
        public_url = upload_image_to_public_host(path)
        if not public_url:
            print(f"   ❌ Failed to upload slide {i + 1}")
            return None

        # Create child container
        container_id = create_image_container(
            INSTAGRAM_ACCOUNT_ID, public_url, ACCESS_TOKEN
        )
        if not container_id:
            return None

        children_ids.append(container_id)
        print(f"   ✅ Container: {container_id}")

    # Step 2: Create carousel container
    print(f"\n   Creating carousel with {len(children_ids)} children...")
    carousel_id = create_carousel_container(
        INSTAGRAM_ACCOUNT_ID, children_ids, caption, ACCESS_TOKEN
    )
    if not carousel_id:
        return None

    # Step 3: Publish
    print(f"\n   Publishing carousel {carousel_id}...")
    result = publish_container(INSTAGRAM_ACCOUNT_ID, carousel_id, ACCESS_TOKEN)

    if result and 'id' in result:
        print(f"\n🎉 CAROUSEL PUBLISHED! Media ID: {result['id']}")
    else:
        print(f"\n⚠️ Publish result: {result}")

    return result


# ─── Main Agent ────────────────────────────────────────────────────────────────

def run_carousel_agent(dry_run=False):
    """
    Full carousel pipeline:
    1. Generate 3 slides + SEO caption via Gemini + Pexels
    2. Save locally for manual upload fallback
    3. Post to Instagram (unless --dry-run)
    """
    print("=" * 60)
    print("🎨 CAROUSEL AGENT — Starting...")
    print("=" * 60)

    from engine.generate_carousel import generate_carousel

    # 1. Generate carousel
    result = generate_carousel()
    if not result:
        print("\n❌ Carousel generation failed!")
        return False

    slide_paths = result["slides"]
    caption = result["caption"]
    carousel_dir = os.path.dirname(slide_paths[0]) if slide_paths else ""

    # 2. Always print local save details for manual upload
    print(f"\n{'='*60}")
    print(f"📁 LOCAL SAVE — Carousel ready for manual upload!")
    print(f"{'='*60}")
    print(f"   Folder: {carousel_dir}")
    for i, p in enumerate(slide_paths):
        print(f"   Slide {i+1}: {p}")
    print(f"   Caption: {os.path.join(carousel_dir, 'caption.txt')}")
    print(f"\n📋 Caption preview:")
    print(f"{caption[:400]}...")
    print(f"{'='*60}")

    # 3. Post to Instagram
    if dry_run:
        print("\n🏁 DRY RUN — Skipping Instagram posting.")
        print("   Slides and caption saved locally for manual upload.")
        return True

    post_result = post_carousel_to_instagram(slide_paths, caption)

    if post_result and 'id' in post_result:
        print("\n✅ Carousel posted successfully to Instagram!")
        return True
    else:
        print("\n⚠️ Instagram posting failed, but slides are saved locally!")
        print(f"   📁 Open this folder to upload manually: {carousel_dir}")
        return True  # Still return True — content was generated


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_carousel_agent(dry_run=dry_run)
