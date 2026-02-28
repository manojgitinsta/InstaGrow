"""
Content Flood Pipeline — Generates premium cinematic reels from the content calendar.
Uses Gemini to intelligently split quotes into hook + reflective lines and pick scene queries.
"""

import os
import sys
import re
import pandas as pd

# Add project root to path so we can import from engine/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.generate_reels import create_cinematic_reel
from engine.trending_audio import get_contextual_trending_audio


def _split_quote_with_gemini(quote_text):
    """
    Uses Gemini to split a quote into a short hook line, a reflective followup,
    and a cinematic Pexels scene query.

    Returns: (hook_line, reflective_line, scene_query)
    """
    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY") or "AIzaSyBcVB1p0Md_4YDCWnAZ_17YcgnxI5VcBHw"
        client = genai.Client(api_key=api_key)

        prompt = f"""You are a cinematic reel director. Given this motivational quote, split it into TWO lines and pick a visual scene.

QUOTE: "{quote_text}"

Return EXACTLY 3 lines (no labels, no numbering, no extra text):
Line 1: A short punchy HOOK (max 8 words) that grabs attention
Line 2: The deeper REFLECTIVE follow-up (the rest of the quote, slightly rephrased if needed)
Line 3: A 2-3 word cinematic Pexels search query starting with "cinematic" (e.g. "cinematic dark rain")

RULES:
- Hook must be SHORT and impactful
- Reflective line should be the emotional core of the quote
- Scene query must be DARK, MOODY, CINEMATIC. No humans, no bright colors.
"""
        response = client.models.generate_content(
            model='gemini-1.5-flash-latest',
            contents=prompt,
        )
        lines = [l.strip() for l in response.text.strip().split('\n') if l.strip()]

        if len(lines) >= 3:
            return lines[0], lines[1], lines[2]
        elif len(lines) == 2:
            return lines[0], lines[1], "cinematic dark ocean"
        else:
            raise ValueError(f"Unexpected response: {lines}")

    except Exception as e:
        print(f"[WARN] Gemini split failed: {e}. Using heuristic fallback.")
        return _split_quote_heuristic(quote_text)


def _split_quote_heuristic(quote_text):
    """Simple fallback: split at first comma/period that's past 20 chars."""
    # Find a natural break point
    for sep in [', but ', '. ', ', ']:
        idx = quote_text.find(sep)
        if idx > 15:
            hook = quote_text[:idx].strip().rstrip(',.')
            reflective = quote_text[idx + len(sep):].strip()
            return hook, reflective, "cinematic dark ocean"

    # If no good split, take first ~6 words as hook
    words = quote_text.split()
    mid = min(6, len(words) // 2)
    return " ".join(words[:mid]), " ".join(words[mid:]), "cinematic dark ocean"


def generate_flood_content():
    """
    Premium Content Flood Pipeline.
    Generates cinematic reels for all pending posts in the content calendar.
    """
    print("=" * 60)
    print("🎬 CINEMATIC CONTENT FLOOD — Starting...")
    print("=" * 60)

    # Path to data
    calendar_path = os.path.join(os.path.dirname(__file__), "..", "data", "content_calendar.csv")
    os.makedirs(os.path.dirname(calendar_path), exist_ok=True)
    
    try:
        df = pd.read_csv(calendar_path)
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].str.strip()
    except FileNotFoundError:
        print(f"[ERROR] {calendar_path} not found!")
        return

    pending_reels = df[(df['status'] == 'pending') & (df['type'] == 'reel')]
    print(f"\n📋 Found {len(pending_reels)} pending reels.")

    if pending_reels.empty:
        print("Nothing to generate. All reels are already processed.")
        return

    output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
    os.makedirs(output_dir, exist_ok=True)

    for index, post in pending_reels.iterrows():
        text = post['caption'] if pd.notna(post['caption']) else "Stay motivated!"
        output_name = os.path.join(output_dir, f"reel_row{index}_v1.mp4")

        if os.path.exists(output_name):
            print(f"\n⏩ Row {index} already exists, skipping.")
            df.at[index, 'status'] = 'flood_ready'
            df.to_csv(calendar_path, index=False)
            continue

        print(f"\n{'─' * 50}")
        print(f"🎬 Row {index}: {text[:60]}...")
        print(f"{'─' * 50}")

        # 1. Split quote into hook + reflective + scene via Gemini
        print("🤖 Splitting quote with AI...")
        hook, reflective, scene_query = _split_quote_with_gemini(text)
        print(f"   Hook:       '{hook}'")
        print(f"   Reflective: '{reflective}'")
        print(f"   Scene:      '{scene_query}'")

        # 2. Get contextual audio
        trending_audio = get_contextual_trending_audio(text)
        audio_name = os.path.basename(trending_audio) if trending_audio else "None"
        print(f"   Audio:      {audio_name}")

        # 3. Generate the cinematic reel
        result = create_cinematic_reel(
            hook_line=hook,
            reflective_line=reflective,
            scene_query=scene_query,
            output_path=output_name,
            trending_audio_path=trending_audio,
            video_index=index,
        )

        if result:
            df.at[index, 'status'] = 'flood_ready'
            df.to_csv(calendar_path, index=False)
            print(f"✅ Row {index} → flood_ready")
        else:
            print(f"⚠️ Row {index} failed. Stays 'pending'.")

    print("\n" + "=" * 60)
    print("🎬 CONTENT FLOOD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    generate_flood_content()
