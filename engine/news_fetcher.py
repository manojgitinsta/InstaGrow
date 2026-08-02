import os
import sys
import xml.etree.ElementTree as ET
import requests
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.gemini_keys import generate_with_rotation

RSS_FEEDS = [
    "https://feeds.feedburner.com/ndtvnews-india-news",
    "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
    "https://www.thehindu.com/news/national/feeder/default.rss",
]

def fetch_positive_news_raw():
    """Fetches recent Indian news items from national RSS feeds."""
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
                    link = item.find('link').text if item.find('link') is not None else ""
                    # Clean up basic HTML tags
                    import re
                    desc_clean = re.sub('<[^<]+>', '', desc).strip()
                    
                    if title:
                        all_items.append({
                            "title": title, 
                            "description": desc_clean[:300],
                            "link": link
                        }) # Keep descriptions short
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
    """Uses Gemini to select the most controversial Indian story and rewrite it as constructive criticism."""
    if not raw_news_items:
        print("[AI] No news items provided to curate.")
        return None

    news_textblock = ""
    for i, item in enumerate(raw_news_items):
        try:
            safe_title = item['title'].encode('ascii', 'ignore').decode('ascii')
            safe_desc = item['description'].encode('ascii', 'ignore').decode('ascii')
            safe_link = item['link']
        except:
             safe_title = "Title Error"
             safe_desc = "Desc Error"
             safe_link = "No Link"
        news_textblock += f"[{i+1}] TITLE: {safe_title}\nSUMMARY: {safe_desc}\nLINK: {safe_link}\n\n"

    prompt = f"""You are a sharp, bold Indian voice for the Instagram account @_the_positive_quote.
Your job is to highlight what's WRONG in India today — and challenge the government and system CONSTRUCTIVELY.

PRIORITY TOPICS (pick stories related to these if available):
- Road corruption, pothole deaths, crumbling infrastructure
- Bridge collapse, building collapse, civic negligence
- Government corruption, scams, misuse of public funds
- Hate speech by politicians, communal divide
- E20 Petrol impact, fuel price burden on common people
- Student protests, youth unemployment
- Exam paper leaks (NEET, SSC, etc.)
- Judiciary delays, mockery of justice
- Capitalism crushing the middle class, corporate favoritism
- Farmer distress, MSP issues
- Environmental neglect, pollution crisis

Here are {len(raw_news_items)} recent Indian news headlines:
{news_textblock}

TASK:
1. Select the SINGLE most controversial, system-challenging, policy-relevant story from the list above.
2. Rewrite it as CONSTRUCTIVE CRITICISM — acknowledge the real problem, call out the policy failure, and end with a strong citizen call-to-action.
3. The tone should be bold and fearless but NOT hateful. Think of it as a responsible citizen demanding accountability.

FORMAT REQUIREMENTS:
Return exactly THREE lines. Keep it in very simple English that common Indians understand.
Line 1: A bold, angry but constructive Headline (Keep it under 10 words. No quotes. UPPERCASE. Make it catchy and shareable.)
Line 2: A short summary of what went wrong, who is responsible, and what citizens should demand. (Keep it under 40 words total.)
Line 3: The exact URL (LINK) of the selected story.

DO NOT output anything else. No introductory text. Just Line 1, Line 2, and Line 3.
"""

    print("[AI] Curating the best positive news story via Gemini...")
    result = generate_with_rotation(prompt, temperature=0.7)
    
    if result:
        lines = result.strip().split('\n')
        # Filter out empty lines
        lines = [l.strip() for l in lines if l.strip()]
        
        if len(lines) >= 3:
            headline = lines[0]
            summary = lines[1]
            link = lines[2]
            
            # Clean formatting if AI added bold markers
            headline = headline.replace("**", "")
            summary = summary.replace("**", "")
            link = link.replace("**", "").strip()
            
            return {
                "headline": headline,
                "summary": summary,
                "link": link
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
             print(f"LINK:     {story.get('link')}")
        except UnicodeEncodeError:
             print(f"HEADLINE: {story['headline'].encode('ascii', 'ignore').decode('ascii')}")
             print(f"SUMMARY: {story['summary'].encode('ascii', 'ignore').decode('ascii')}")
             print(f"LINK:     {story.get('link')}")
    else:
        print("Failed to fetch or curate news.")
