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

def fetch_all_media():
    """Fetch ALL media from Instagram Graph API using pagination."""
    if not ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        print("[ERROR] Missing Instagram credentials in .env")
        return []

    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,media_type,media_product_type,like_count,comments_count,timestamp,permalink",
        "limit": 50,
        "access_token": ACCESS_TOKEN
    }
    
    print(f"[FETCH] Starting full historical fetch from Instagram...")
    all_media = []
    
    while url:
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            try:
                print(f"[ERROR] API failed: {response.text}")
            except UnicodeEncodeError:
                safe_text = response.text.encode('ascii', 'ignore').decode('ascii')
                print(f"[ERROR] API failed: {safe_text} (emojis stripped for terminal)")
            break
            
        data = response.json()
        current_page_data = data.get("data", [])
        all_media.extend(current_page_data)
        
        print(f"   Fetched {len(current_page_data)} posts... (Total so far: {len(all_media)})")
        
        # Check for pagination
        paging = data.get("paging", {})
        url = paging.get("next")
        params = None # URL from 'next' already contains the URL params
        
    print(f"\n[OK] Completed! Total historical posts fetched: {len(all_media)}")
    return all_media

def generate_report(media_data, report_type):
    """Use Gemini to analyze the fetched posts and generate a report."""
    
    if not media_data:
        print(f"No media data available for {report_type}.")
        return None
        
    print(f"\n[AI] Analyzing {len(media_data)} {report_type}s with AI...")
    
    # Extract captions and engagement to build context
    context_lines = []
    # Send up to 50 items to Gemini to avoid context limits, sorting by most likes
    sorted_media = sorted(media_data, key=lambda x: x.get('like_count', 0), reverse=True)
    
    for item in sorted_media[:50]: 
        if "caption" in item:
            cap = item.get("caption", "")[:200].replace("\n", " ").strip()
            likes = item.get("like_count", 0)
            comments = item.get("comments_count", 0)
            type_str = item.get('media_type', 'UNKNOWN')
            if item.get('media_product_type') == 'REELS':
                type_str = 'REEL'
                
            try:
                 safe_cap = cap.encode('ascii', 'ignore').decode('ascii')
            except Exception:
                 safe_cap = "unreadable_caption"
                 
            context_lines.append(f"- Type: {type_str}, Likes: {likes}, Comments: {comments}, Caption snippet: '{safe_cap}'")
            
    context_str = "\n".join(context_lines)
    
    prompt = f"""You are an elite Instagram Strategist. I am providing you with the historical performance data of an Instagram account (@_the_positive_quote).
    
This specific report must focus ONLY on their: **{report_type.upper()}**

Here is the data for their top {len(context_lines)} {report_type}s (ranked by most likes first):
{context_str}

TASK:
Write a highly detailed, professional "Historical Performance Report" for their {report_type}s.
Include the following sections:
1.  **Executive Summary:** A brief conclusion on how {report_type}s generally perform for this account.
2.  **Top Performers Analysis:** What specific themes, words, or aesthetic choices drove the most likes in their historical data? Give concrete examples from the provided captions.
3.  **The Engagement Gap:** Why might some {report_type}s have failed based on the data?
4.  **Strategic Recommendations for {report_type}s:** Give 3 actionable rules they should follow moving forward when creating this specific type of content to guarantee higher engagement.

Return the full report in nicely formatted Markdown suitable for a PDF export. Do not include introductory conversational text, just the report.
"""

    report_markdown = generate_with_rotation(prompt, temperature=0.7)
    
    if report_markdown:
        report_path = os.path.join(os.path.dirname(__file__), "..", "output", f"Historical_Report_{report_type}.md")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_markdown.strip())
        print(f"[OK] Report saved to {report_path}")
        return report_path
    else:
        print(f"[ERROR] Failed to generate {report_type} report via Gemini.")
        return None

if __name__ == "__main__":
    all_posts = fetch_all_media()
    
    # Separate into Reels vs Static (Images/Carousels)
    reels_data = []
    static_data = []
    
    for post in all_posts:
        if post.get("media_product_type") == "REELS" or post.get("media_type") == "VIDEO":
            reels_data.append(post)
        else:
            static_data.append(post)
            
    print(f"\n[DATA] Split data into {len(reels_data)} Reels and {len(static_data)} Static Posts.")
    
    report1 = generate_report(static_data, "Static_Posts_and_Carousels")
    report2 = generate_report(reels_data, "Reels")
    
    print("\n[OK] Historical Analysis Complete. Reports generated in output/ directory.")
