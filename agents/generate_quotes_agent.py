import os
import json
import pandas as pd
from datetime import datetime, timedelta
from google import genai
from google.genai import types

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

    prompt = """
    You are an expert social media manager for a viral, aesthetic Instagram page.
    Generate 5 highly engaging, deep, heart-touching, and relatable quotes.
    The topics should vary between: life, love, breakup, motivation, feeling alone, regret, and happiness.
    Each quote MUST be short but extremely powerful (around 10 to 15 words max). This brevity is crucial for extreme algorithmic virality and viewer loop rate.
    Do NOT include author names. The quotes should be presented as anonymous deep thoughts.
    
    Return the response ONLY as a raw JSON array of objects with a 'quote' key.
    Example: [{"quote": "Some truths hit you at 3AM, when the world is quiet."}]
    Do NOT wrap the JSON in markdown code blocks (like ```json). Just return the raw array.
    """

    print("[VIBE] Asking Gemini for fresh viral quotes...")
    try:
        if generate_with_rotation:
            raw_text = generate_with_rotation(prompt, temperature=0.7)
        else:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7),
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
