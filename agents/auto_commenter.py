import os
import sys
import json
import requests
import pandas as pd
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.gemini_keys import generate_with_rotation

# Load credentials from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
BASE_URL = "https://graph.facebook.com/v21.0"

def get_recent_posts(limit=5):
    """Fetch the IDs of recent media posts."""
    if not ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        print("[ERROR] Missing Instagram credentials in .env")
        return []

    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,media_type",
        "limit": limit,
        "access_token": ACCESS_TOKEN
    }
    
    print(f"[FETCH] Fetching {limit} recent posts...")
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("data", [])
    print(f"[ERROR] API failed: {response.text}")
    return []

def get_comments_for_post(media_id):
    """Fetch top-level comments for a specific post."""
    url = f"{BASE_URL}/{media_id}/comments"
    params = {
        "fields": "id,text,username,timestamp,replies",
        "access_token": ACCESS_TOKEN
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("data", [])
    try:
        print(f"   [ERROR] Failed to fetch comments: {response.text}")
    except UnicodeEncodeError:
        safe_text = response.text.encode('ascii', 'ignore').decode('ascii')
        print(f"   [ERROR] Failed to fetch comments: {safe_text} (emojis stripped for terminal)")
    return []

def generate_ai_reply(comment_text, username):
    """Use Gemini to generate a stoic, brand-aligned reply."""
    
    # Filter out empty or pure emoji comments unless they are very specific
    if len(comment_text.strip()) < 2 and not any(emo in comment_text for emo in ['🔥', '💯', '❤️', '👏']):
        return None
        
    prompt = f"""You are generating an automated reply to an Instagram comment on the account @_the_positive_quote. 
The brand aesthetic is "Dark, Cinematic, Stoic Motivation". 

User @{username} commented: "{comment_text}"

TASK: Write a short, highly engaging, empathetic, or stoic reply to this comment. 
- Keep it under 2 sentences.
- Use 0 or 1 dark/elegant emoji (e.g., 🖤, 🕊️, 🕯️, 🥀, ⏳, 🙏, 💯, 🤝). No bright/silly emojis.
- If the comment is just an emoji (like 🔥), reply with a matching energy or "Thank you for the support. 🖤"
- If the comment is negative, toxic, spam, or a bot asking for followers, return EXACTLY the word "IGNORE".
- Tone: Deep, mature, validating, resilient.

Return ONLY the reply text, nothing else.
"""

    reply = generate_with_rotation(prompt, temperature=0.7)
    if reply:
        reply = reply.strip().strip('"\'')
        if reply.upper() == "IGNORE":
            return None
        return reply
    return None

def post_reply(comment_id, message, dry_run=True):
    """Publish a reply to a comment via the Graph API."""
    
    # Safe terminal printing for Windows
    try:
        print(f"   [DRY RUN] Would reply to {comment_id}: '{message}'")
    except UnicodeEncodeError:
        safe_msg = message.encode('ascii', 'ignore').decode('ascii')
        print(f"   [DRY RUN] Would reply to {comment_id}: '{safe_msg}' (emojis stripped for terminal)")
        
    if dry_run:
        return True
        
    url = f"{BASE_URL}/{comment_id}/replies"
    payload = {
        "message": message,
        "access_token": ACCESS_TOKEN
    }
    
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print(f"   [OK] Successfully replied to {comment_id}")
        return True
    else:
        print(f"   [ERROR] Failed to reply: {response.text}")
        return False

def run_auto_commenter(dry_run=True):
    """Main function to scan recent posts and reply to unhandled comments."""
    print("=" * 60)
    print(f"[START] AUTO-COMMENTER {'(DRY RUN)' if dry_run else '(LIVE MODE)'}")
    print("=" * 60)

    # We track replied comments locally to avoid hitting the API rate limits
    # and to simplify the logic of checking individual replies.
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "replied_comments.json")
    if os.path.exists(db_path):
        with open(db_path, "r") as f:
            replied_db = set(json.load(f))
    else:
        replied_db = set()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    posts = get_recent_posts(limit=3) # Only check last 3 posts to save time/API calls
    unreplied_comments_found = False
    
    for post in posts:
        post_id = post['id']
        caption_snippet = post.get('caption', '')[:30].replace('\n', ' ')
        print(f"\nScanning Post {post_id} ('{caption_snippet}...')")
        
        comments = get_comments_for_post(post_id)
        
        for c in comments:
            c_id = c['id']
            c_text = c['text']
            c_user = c.get('username', 'user')
            
            # Skip if we already replied
            if c_id in replied_db:
                continue
                
            # Skip our own comments
            if c_user == "_the_positive_quote":
                 continue
                 
            # Skip if it already has replies (assuming we or someone else handled it)
            if 'replies' in c and len(c['replies'].get('data', [])) > 0:
                 replied_db.add(c_id) # Mark as handled so we skip faster next time
                 continue

            unreplied_comments_found = True
            try:
                print(f"   [NEW COMMENT] from @{c_user}: '{c_text}'")
            except UnicodeEncodeError:
                safe_text = c_text.encode('ascii', 'ignore').decode('ascii')
                print(f"   [NEW COMMENT] from @{c_user}: '{safe_text}'")
            
            # Generate AI Reply
            ai_reply = generate_ai_reply(c_text, c_user)
            
            if ai_reply:
                success = post_reply(c_id, ai_reply, dry_run=dry_run)
                if success and not dry_run:
                    replied_db.add(c_id)
            else:
                print("   [SKIP] (AI classified as 'IGNORE' or unable to generate)")
                # We optionally could mark as ignored in DB so AI doesn't re-process spam
                replied_db.add(c_id) 
                
    # Save updated DB
    if not dry_run and unreplied_comments_found:
        with open(db_path, "w") as f:
             json.dump(list(replied_db), f)
             print("\n[SAVED] Saved replied comments database.")
             
    if not unreplied_comments_found:
         print("\n[SLEEP] No new comments to reply to.")
         
    print("=" * 60)

if __name__ == "__main__":
    # Always default to dry_run when run from command line initially
    # Change to False via args when integrated into run_daily pipelne
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Run in LIVE mode (actually posts replies)")
    args = parser.parse_args()
    
    run_auto_commenter(dry_run=not args.live)
