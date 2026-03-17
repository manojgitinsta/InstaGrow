import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# Ensure Windows console handles emojis/unicode correctly
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

# Load credentials from .env file
load_dotenv()

# Use the environment variable if provided
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # Fallback for demonstration if no .env exists yet
    GEMINI_API_KEY = "AIzaSyBcVB1p0Md_4YDCWnAZ_17YcgnxI5VcBHw"

def generate_quotes():
    """Uses Gemini to generate 5 viral motivational quotes and appends them to the calendar."""
    print("[AI] Initializing Gemini AI Quote Agent...")
    
    try:
        from engine.gemini_keys import generate_with_rotation
    except ImportError:
        try:
            from gemini_keys import generate_with_rotation
        except ImportError:
            print("❌ Cannot import gemini_keys, falling back to direct API call")
            generate_with_rotation = None

    import random

    # Rotate emotional categories to force variety across runs
    emotional_categories = [
        "the pain of outgrowing someone you still love",
        "the silence after a betrayal you didn't see coming",
        "rebuilding your life from scratch while pretending you're fine",
        "realizing you were the toxic one all along",
        "the loneliness of being surrounded by people who don't know you",
        "the weight of words you never got to say",
        "self-worth you discovered only after they left",
        "the exhaustion of being emotionally strong for everyone else",
        "walking away from someone who was your whole world",
        "the specific moment you knew it was over",
        "forgiving someone who never apologized",
        "the fear of becoming exactly like the person who hurt you",
    ]

    # Pick 2-3 random categories for THIS run
    selected = random.sample(emotional_categories, min(3, len(emotional_categories)))
    categories_str = "\n".join(f"  - {c}" for c in selected)

    prompt = f"""You are the ghostwriter behind @_the_positive_quote — a dark, cinematic Instagram page that gets millions of views.

Your task: generate 5 quotes that make someone screenshot their phone and send it to that ONE person.

TODAY'S EMOTIONAL THEMES (focus on these):
{categories_str}

QUALITY EXAMPLES — every quote you write must hit THIS hard:
- "Some apologies never come. You just learn to stop waiting."
- "I didn't lose you. I lost the version of me that needed you."
- "The worst kind of lonely is being in a room full of people who don't see you."
- "You were my 3am thought. I wasn't even your afternoon."
- "I forgave you. Not because you deserved it, but because I deserved peace."
- "The saddest people smile the brightest. That's why nobody noticed."
- "I'm not afraid of being alone. I'm afraid of being with someone and still feeling alone."
- "Some chapters end mid-sentence. That's the cruelest kind of ending."
- "She didn't leave because she stopped loving him. She left because she started loving herself."
- "The hardest goodbye is the one you never said out loud."

CRITICAL RULES:
1. Maximum 15 words per quote. Shorter = more powerful.
2. Write about SPECIFIC MOMENTS and SITUATIONS, not generic advice.
3. The reader must feel "this was written about MY life."
4. Use precise, visceral language (shatter, haunt, ghost, anchor, fracture, dissolve, rebuild, unravel).

BANNED PHRASES (instant rejection if used):
- "keep going", "stay strong", "believe in yourself", "you matter", "don't give up"
- "rise above", "be positive", "everything happens for a reason", "good vibes"
- "your time will come", "trust the process", "it gets better"
- "you are enough", "be kind", "spread love", "never give up"

Return ONLY a raw JSON array:
[{{"quote": "..."}}]
Do NOT wrap in markdown code blocks.
"""

    print("[VIBE] Asking Gemini for fresh viral quotes...")
    try:
        if generate_with_rotation:
            raw_text = generate_with_rotation(prompt, temperature=0.9)
        else:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.9),
            )
            raw_text = response.text.strip()
        
        if not raw_text:
            print("❌ Error: Empty response from Gemini.")
            return

        # Clean markdown formatting if present
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        quotes_data = json.loads(raw_text.strip())
        
        if not isinstance(quotes_data, list) or len(quotes_data) == 0:
            print("❌ Error: Gemini did not return a valid list of quotes.")
            return
            
        print(f"✅ Successfully generated {len(quotes_data)} quotes!")
        
        # Append to the CSV calendar
        append_to_calendar(quotes_data)
        
    except Exception as e:
        print(f"❌ Failed to generate quotes: {e}")

def append_to_calendar(quotes_data):
    """Appends the generated quotes to content_calendar.csv at the next available date."""
    print("📅 Scheduling quotes into the content calendar...")
    
    calendar_file = os.path.join(os.path.dirname(__file__), "..", "data", "content_calendar.csv")
    
    os.makedirs(os.path.dirname(calendar_file), exist_ok=True)
    
    try:
        df = pd.read_csv(calendar_file)
        # Find the last scheduled date
        last_date_str = df['date'].iloc[-1]
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
        
    except (FileNotFoundError, IndexError):
        # If no file or empty, start tomorrow
        df = pd.DataFrame(columns=['date', 'time', 'type', 'content_source', 'caption', 'status'])
        last_date = datetime.now()
        
    new_rows = []
    current_date = last_date
    
    for item in quotes_data:
        # Increment by 1 day for each new post
        current_date += timedelta(days=1)
        next_date_str = current_date.strftime("%Y-%m-%d")
        
        quote = item.get('quote', '').replace('"', "'") # Escape quotes for CSV
        caption = f"{quote}"
        
        new_row = {
            'date': next_date_str,
            'time': '10:00',
            'type': 'reel',
            'content_source': 'quotes.txt',
            'caption': caption,
            'status': 'pending'
        }
        new_rows.append(new_row)
        print(f"  -> Scheduled: {quote[:20]}... on {next_date_str}")
        
    # Append the new rows
    new_df = pd.DataFrame(new_rows)
    df = pd.concat([df, new_df], ignore_index=True)
    df.to_csv(calendar_file, index=False)
    print("✅ Calendar successfully updated!")

if __name__ == "__main__":
    generate_quotes()
