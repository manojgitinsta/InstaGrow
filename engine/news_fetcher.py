import os
import sys
import xml.etree.ElementTree as ET
import requests
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.gemini_keys import generate_with_rotation

RSS_FEEDS = [
    "https://www.goodnewsnetwork.org/feed/",
    "https://optimistdaily.com/feed/"
]

def fetch_positive_news_raw():
    """Fetches recent news items from positive RSS feeds."""
    all_items = []
    
    # Simple anti-user-agent blocking setup
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for feed_url in RSS_FEEDS:
        try:
            print(f"[RSS] Fetching from {feed_url}...")
            response = requests.get(feed_url, headers=headers, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                # Find all 'item' tags in the RSS feed
                for item in root.findall('.//item'):
                    title = item.find('title').text if item.find('title') is not None else ""
                    # Often descriptions contain HTML, we just want the raw text or the first snippet
                    desc = item.find('description').text if item.find('description') is not None else ""
                    # Clean up basic HTML tags
                    import re
                    desc_clean = re.sub('<[^<]+>', '', desc).strip()
                    
                    if title:
                        all_items.append({"title": title, "description": desc_clean[:300]}) # Keep descriptions short
            else:
                print(f"[RSS] Failed to fetch {feed_url} (Status: {response.status_code})")
        except Exception as e:
            print(f"[RSS] Error parsing {feed_url}: {e}")

    # Return a random sample of recent news to give AI variety
    if all_items:
        # Shuffle to not always pick the single newest one, gives variety everyday
        random.shuffle(all_items)
        return all_items[:10] 
    return []

def curate_and_rewrite_news(raw_news_items):
    """Uses Gemini to select the most impactful story and rewrite it for an IG Story."""
    if not raw_news_items:
        print("[AI] No news items provided to curate.")
        return None

    news_textblock = ""
    for i, item in enumerate(raw_news_items):
        try:
            safe_title = item['title'].encode('ascii', 'ignore').decode('ascii')
            safe_desc = item['description'].encode('ascii', 'ignore').decode('ascii')
        except:
             safe_title = "Title Error"
             safe_desc = "Desc Error"
        news_textblock += f"[{i+1}] TITLE: {safe_title}\nSUMMARY: {safe_desc}\n\n"

    prompt = f"""You are determining the "Positive News of the Day" for the Instagram account @_the_positive_quote. 
The brand aesthetic is soothing, healing, positive, and deeply motivational. It focuses on spreading truth, resilience, and belief in humanity.

Here are {len(raw_news_items)} recent positive news headlines:
{news_textblock}

TASK:
1. Select the SINGLE most impactful, uplifting, and society-affirming story from the list above.
2. Rewrite it into a short, highly engaging format specifically designed for a vertical Instagram Story image.

FORMAT REQUIREMENTS:
Return exactly TWO lines. Keep it in very simple English.
Line 1: The bold, punchy Headline (Keep it under 10 words. No quotes. UPPERCASE).
Line 2: A short, simple summary answering "What happened and where?" followed by a brief, deeply motivational takeaway. (Keep it under 35 words total).

DO NOT output anything else. No introductory text. Just Line 1 and Line 2. 
"""

    print("[AI] Curating the best positive news story via Gemini...")
    result = generate_with_rotation(prompt, temperature=0.7)
    
    if result:
        lines = result.strip().split('\n')
        # Filter out empty lines
        lines = [l.strip() for l in lines if l.strip()]
        
        if len(lines) >= 2:
            headline = lines[0]
            summary = " ".join(lines[1:]) # Just in case it split into more lines
            
            # Clean formatting if AI added bold markers
            headline = headline.replace("**", "")
            summary = summary.replace("**", "")
            
            return {
                "headline": headline,
                "summary": summary
            }
        else:
             print("[AI_ERROR] Gemini returned unexpected format:")
             print(result)
             return None
             
    return None

def get_todays_news_story():
    """Main function to be called by the generation agent."""
    raw_news = fetch_positive_news_raw()
    if raw_news:
        curated_story = curate_and_rewrite_news(raw_news)
        return curated_story
    return None

if __name__ == "__main__":
    print("Testing News Fetcher...")
    story = get_todays_news_story()
    if story:
        print("\n--- FINAL CURATED STORY ---")
        try:
             print(f"HEADLINE: {story['headline']}")
             print(f"SUMMARY: {story['summary']}")
        except UnicodeEncodeError:
             print(f"HEADLINE: {story['headline'].encode('ascii', 'ignore').decode('ascii')}")
             print(f"SUMMARY: {story['summary'].encode('ascii', 'ignore').decode('ascii')}")
    else:
        print("Failed to fetch or curate news.")
