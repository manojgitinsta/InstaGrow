import instaloader
import os
import json
import random
import time
from datetime import datetime

# Initialize Instaloader
L = instaloader.Instaloader()

# Get profile
PROFILE = "_the_positive_quote"

def analyze_profile_reels():
    print(f"Fetching profile {PROFILE}...")
    try:
        profile = instaloader.Profile.from_username(L.context, PROFILE)
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return

    high_performing_reels = []
    
    print(f"Iterating over posts...")
    count = 0
    # Iterate through all posts
    for post in profile.get_posts():
        # Only process videos/reels
        if post.is_video:
            views = post.video_view_count
            likes = post.likes
            comments = post.comments
            caption = post.caption or ""
            url = f"https://www.instagram.com/p/{post.shortcode}/"
            
            print(f"Post {post.shortcode}: {views} views, {likes} likes")
            
            if views and views > 5000:
                high_performing_reels.append({
                    "id": post.shortcode,
                    "permalink": url,
                    "plays": views,
                    "like_count": likes,
                    "comments_count": comments,
                    "caption": caption[:300]
                })
        
        count += 1
        if count % 10 == 0:
            print(f"Processed {count} posts...")
            time.sleep(1) # Be nice to Instagram
            
    print(f"\nFound {len(high_performing_reels)} older reels with > 5000 views!")
    
    # Sort by views
    high_performing_reels = sorted(high_performing_reels, key=lambda x: x["plays"], reverse=True)
    
    # Save the raw data
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "high_performing_reels.json"), "w", encoding="utf-8") as f:
        json.dump(high_performing_reels, f, indent=4)
        
if __name__ == "__main__":
    analyze_profile_reels()
