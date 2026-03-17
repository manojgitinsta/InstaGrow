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
    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,media_type,media_product_type,like_count,comments_count,timestamp,permalink",
        "limit": 50,
        "access_token": ACCESS_TOKEN
    }
    
    print(f"[FETCH] Fetching media from Instagram...")
    all_media = []
    
    while url:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"[ERROR] API failed: {response.text}")
            break
            
        data = response.json()
        current_page_data = data.get("data", [])
        all_media.extend(current_page_data)
        
        paging = data.get("paging", {})
        url = paging.get("next")
        params = None
        
    return all_media

def analyze_reels_performance():
    all_media = fetch_all_media()
    reels = [m for m in all_media if m.get("media_product_type") == "REELS" or m.get("media_type") == "VIDEO"]
    
    print(f"Found {len(reels)} Reels. Fetching view (plays) counts...")
    
    high_performing_reels = []
    
    for count, reel in enumerate(reels, 1):
        media_id = reel.get("id")
        
        insights_url = f"{BASE_URL}/{media_id}/insights"
        params = {
            "metric": "plays",
            "access_token": ACCESS_TOKEN
        }
        res = requests.get(insights_url, params=params)
        
        plays = 0
        if res.status_code == 200:
            insights_data = res.json().get("data", [])
            for metric in insights_data:
                if metric.get("name") == "plays":
                    plays = metric.get("values", [{}])[0].get("value", 0)
        else:
            print(f"Failed to fetch insights for {media_id}: {res.text}")
            
        reel["plays"] = plays
        print(f"[{count}/{len(reels)}] Reel {media_id}: {plays} plays")
        
        if plays >= 5000:
            high_performing_reels.append(reel)
            
    # sort by plays
    high_performing_reels = sorted(high_performing_reels, key=lambda x: x["plays"], reverse=True)
    
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "high_performing_reels.json"), "w", encoding="utf-8") as f:
        json.dump(high_performing_reels, f, indent=4)
        
    print(f"\nFound {len(high_performing_reels)} reels with >= 5000 views!")
    
    # If there are none, we fallback to the top 5 to still provide a report
    if len(high_performing_reels) == 0:
        print("Since no reels were found with >= 5000 views, analyzing the top 5 reels instead.")
        high_performing_reels = sorted(reels, key=lambda x: x.get("plays", 0), reverse=True)[:5]
        
    generate_report(high_performing_reels)
    
def generate_report(high_performing_reels):    
    context_lines = []
    
    for item in high_performing_reels[:50]: 
        cap = item.get("caption", "")[:300].replace("\n", " ").strip()
        try:
            safe_cap = cap.encode('ascii', 'ignore').decode('ascii')
        except Exception:
            safe_cap = "unreadable_caption"
            
        plays = item.get("plays", 0)
        likes = item.get("like_count", 0)
        comments = item.get("comments_count", 0)
        permalink = item.get("permalink", "")
             
        context_lines.append(f"- URL: {permalink}, Views(Plays): {plays}, Likes: {likes}, Comments: {comments}, Caption: '{safe_cap}'")
        
    context_str = "\n".join(context_lines)
    
    prompt = f"""You are an elite Instagram Strategist. I am providing you with the data for an Instagram account's top-performing Reels (specifically those near or over 5,000 views).
    
Here is the data for these Reels (ranked by most views):
{context_str}

TASK:
Write a highly detailed, professional "High-Performing Reels Analysis Report".
Include the following sections:
1.  **Overview of Top Performers:** A brief summary of the most viral videos and their view counts.
2.  **Viral Themes & Content:** What specific patterns, themes, hooks, or aesthetic choices drove these videos to higher watch rates? Reference the captions specifically. Focus heavily on why these worked so well.
3.  **Engagement Metrics:** Analyze the ratio of likes/comments to views. What does this indicate about the audience taking action?
4.  **Strategic Recommendations for Future Videos:** Give 3-5 actionable rules for future content creation to replicate this success and push far past 5k views.

Return the full report in nicely formatted Markdown suitable for a PDF export. Do not include introductory conversational text, just the report.
"""

    report_markdown = generate_with_rotation(prompt, temperature=0.7)
    
    if report_markdown:
        report_path = os.path.join(os.path.dirname(__file__), "..", "output", "High_Performing_Reels_Review.md")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_markdown.strip())
        print(f"[OK] Report saved to {report_path}")
    else:
        print(f"[ERROR] Failed to generate report via Gemini.")

if __name__ == "__main__":
    analyze_reels_performance()
