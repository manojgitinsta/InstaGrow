import os
import sys
import json
import requests
import pandas as pd
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.gemini_keys import generate_with_rotation

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
BASE_URL = "https://graph.facebook.com/v21.0"

def fetch_recent_media(limit=50):
    """Fetch recent media from Instagram Graph API."""
    if not ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        print("[ERROR] Missing Instagram credentials in .env")
        return []

    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,media_type,media_product_type,like_count,comments_count,timestamp,permalink",
        "limit": limit,
        "access_token": ACCESS_TOKEN
    }
    
    print(f"[FETCH] Fetching up to {limit} recent posts from Instagram...")
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"[ERROR] API failed: {response.text}")
        return []
        
    data = response.json()
    media_data = data.get("data", [])
    print(f"[OK] Fetched {len(media_data)} posts.")
    return media_data

def generate_profile_report(media_data):
    """Use Gemini to analyze the fetched posts and generate a report + new content."""
    
    if not media_data:
        print("No media data to analyze.")
        return None
        
    print("[AI] Analyzing content with AI...")
    
    # Extract captions and engagement to build context
    context_lines = []
    for item in media_data[:20]: # Send top 20 recent posts for context to avoid huge tokens
        if "caption" in item:
            # Clean up the caption a bit to focus on the quote text
            cap = item["caption"][:200].replace("\n", " ").strip()
            likes = item.get("like_count", 0)
            context_lines.append(f"- Type: {item.get('media_type', 'UNKNOWN')}, Likes: {likes}, Caption snippet: '{cap}'")
            
    context_str = "\n".join(context_lines)
    
    prompt = f"""You are an elite Instagram Strategist. I am providing you with the recent posts of an Instagram account (@_the_positive_quote) focused on dark, cinematic, stoic motivation.
    
Here is their recent post data (Type, Likes, and Caption Snippets):
{context_str}

TASK:
1. Write a detailed "Content Theme & Style Report" analyzing their current aesthetic, tone, and what seems to resonate with their audience based on this data. Be specific about the visual and written language they use.
2. Based *strictly* on this analysis, generate 5 BRAND NEW, original quotes that compliment this exact theme. They must not be duplicates of the past quotes, but they should feel like they belong on the same page. Make them deeply emotional, stoic, and relatable. 
3. Suggest 3 new specific ideas for Cinematic Reels based on this style (e.g., specific visuals + text combinations).

Return the full report in nicely formatted Markdown.
"""

    report_markdown = generate_with_rotation(prompt, temperature=0.7)
    
    if report_markdown:
        report_path = os.path.join(os.path.dirname(__file__), "..", "output", "profile_analysis_report.md")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_markdown)
        print(f"[OK] Report saved to {report_path}")
        return report_path
    else:
        print("[ERROR] Failed to generate report via Gemini.")
        return None

if __name__ == "__main__":
    posts = fetch_recent_media(limit=30)
    report_file = generate_profile_report(posts)
    if report_file:
         print(f"Ready for review: {report_file}")
