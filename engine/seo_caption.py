"""
SEO Caption Engine — Generates optimized captions for Instagram reels & carousel posts.
═══════════════════════════════════════════════════════════════════════════════════
Produces captions with:
  - Emotional hook (first 2 lines)
  - Engagement bait paragraph
  - CTA to follow
  - Engagement question
  - Save/share encouragement
  - 15 rotated hashtags (5 high volume + 5 medium + 5 niche)
"""

import os
import json
import random
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def generate_seo_caption(content_type="reel", quote_text="", theme="motivation"):
    """
    Generate a full SEO-optimized Instagram caption with hashtags.
    Uses multi-key rotation to avoid quota exhaustion.
    """
    try:
        from engine.gemini_keys import generate_with_rotation
    except ImportError:
        from gemini_keys import generate_with_rotation

    prompt = f"""You are an elite Instagram Viral Strategist specializing in dark, cinematic, and deeply emotional content for @_the_positive_quote.
Your task is to transform a simple quote into a viral masterpiece that triggers heavy engagement (shares, saves, and comments).

QUOTE: "{quote_text}"
THEME: {theme}

Return ONLY raw JSON:
{{
  "caption": "Full formatted caption text",
  "hashtags": ["tag1", ..., "tag15"]
}}

STRICT STRUCTURE:
1. THE HOOK: A brutal, relatable, or mysterious opening line. Use "..." to force the user to click "more".
   Examples: "The hardest part isn't leaving..." or "Read this twice if you're tired of being 'fine'."
2. THE CORE: 2-3 sentences of deep, philosophical reflection. Use a mature, stoic, and poetic tone. No emojis in this section.
3. THE PROVOCATION: A question that the reader *cannot* ignore. Something that makes them want to share their story.
4. THE DYNAMIC CTA: ONE emotional request to Save, Share, or Follow. Choose ONLY ONE.

TONE: Dark, Moody, Cinematic, Stoic, Emotional.
Avoid: Salesy words, generic positive vibes, exclamation marks (use periods for weight).
"""

    raw = generate_with_rotation(prompt, temperature=0.85)

    if raw:
        try:
            import json
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            return data
        except Exception as e:
            print(f"Failed to parse SEO caption JSON: {e}")
            pass

    return _fallback_caption(quote_text)


def build_full_caption(caption_text, hashtags):
    """
    Combine caption text with hashtags, using Instagram-style hidden spacing.
    """
    hashtag_str = " ".join(f"#{tag.lstrip('#')}" for tag in hashtags)

    # Add engagement trap opener
    traps = [
        "99% of people scroll past this. But the 1% who stay — they understand.",
        "Read this twice. Let it sink in.",
        "Not everyone is ready to hear this. But maybe you are.",
        "This might be the sign you've been waiting for.",
        "Some things hit harder when you read them at the right time.",
    ]
    opener = random.choice(traps)

    full = f"{opener}\n\n{caption_text}\n\n.\n.\n.\n.\n.\n{hashtag_str}"
    return full


def generate_reel_caption(quote_text, theme="motivation"):
    """Convenience wrapper for reel captions."""
    data = generate_seo_caption("reel", quote_text, theme)
    hook = get_engagement_trap()
    bomber = get_keyword_bomber(theme)
    
    full = f"{hook}\n\n{data['caption']}\n{bomber}"
    return full


def generate_carousel_caption(quote_text, theme="motivation"):
    """Convenience wrapper for carousel captions."""
    data = generate_seo_caption("carousel", quote_text, theme)
    hook = get_engagement_trap()
    bomber = get_keyword_bomber(theme)
    
    full = f"{hook}\n\n{data['caption']}\n{bomber}"
    return full


def get_keyword_bomber(theme="motivation"):
    """
    Algorithmic Hijacking: Massive hidden hashtag block + Competitor Leeching + Global Polyglot.
    """
    viral = "#fyp #foryou #viral #explore #explorepage #trending #reels #tiktok #instagramreels "
    
    # Theme-specific niches
    if "love" in theme.lower() or "heart" in theme.lower():
        niche = "#lovequotes #brokenheart #healing #soulmate #relationshipgoals #relatable "
    elif "alone" in theme.lower() or "sad" in theme.lower():
        niche = "#lonely #sadqoutes #deepfeeling #midnightthoughts #mentalhealth #introvert "
    else:
        niche = "#motivation #mindset #success #quotes #life #focus #grind #hustle "
    
    competitors = "@successpictures @hustle_mentality @wealth @deep_quotes @sigma_rules_ @millionaire_mentor "
    polyglot = "#exito #motivacion #frases #सफलता #प्रेरणा #اقتباسات #نجاح #мотивация #успех"
    
    hidden_block = "\n.\n.\n.\n.\n.\n.\n.\n.\n" + viral + niche + "\n" + competitors + "\n" + polyglot
    return hidden_block


def get_engagement_trap():
    """
    Hooks that force a double-take and increase read time.
    """
    traps = [
        "99% of people will scroll past this, but the 1% who stay will understand. Do you agree? 👇",
        "This might offend some people, but it’s the harsh truth. Let me know if I'm wrong below.",
        "I hesitated to post this, but someone needs to hear it today. Tag them.",
        "Read that again. How many times have you felt this way? Be honest. ⬇️",
        "Most people won't admit this is true. Are you one of them? Share your thoughts.",
        "Stop scrolling. This is the sign you were looking for. 🕯️",
        "Your future self is watching you right now through your memories. Make them proud.",
        "The version of you that you're becoming is costing you people, relationships, and spaces. Post 'YES' if you're ready.",
        "If you see this at 3AM, it's not a coincidence. It's a wake-up call.",
        "Someone is winning because they didn't quit. Someone is losing because they did. Which one are you?"
    ]
    return random.choice(traps)


def _fallback_caption(quote_text):
    """Fallback caption when Gemini is unavailable."""
    high = ["motivation", "quotes", "viral", "mindset", "explore"]
    medium = random.sample([
        "deepthoughts", "healingquotes", "innerpeace", "lifequotes",
        "emotionalquotes", "positivevibes", "innergrowth", "darkquotes",
    ], 5)
    niche = random.sample([
        "cinematicquotes", "thepositivequote", "darkmotivation",
        "midnightthoughts", "quotesthatmatter", "darkcinematic",
        "motivationaldarkquotes", "quotestoliveby",
    ], 5)

    cta_list = [
        "Save this. Your future self might need to read it again. 💌",
        "Share this with someone whose heart needs a reminder. ✨",
        "If this resonated, follow @_the_positive_quote for your daily anchor. 🖤",
        "Tap the heart if you're trying your best today. ❤️‍🩹",
        "Send this to a friend who is fighting a quiet battle. 🕊️"
    ]
    cta_line = random.choice(cta_list)

    caption = (
        f"{quote_text}\n\n"
        "Some words stay with you forever. This is one of them.\n\n"
        "What would you add? Tell us below. 👇\n\n"
        f"{cta_line}"
    )

    return {
        "caption": caption,
        "hashtags": high + medium + niche,
    }


if __name__ == "__main__":
    full = generate_reel_caption(
        quote_text="Pain builds the strength you pray for.",
        theme="inner strength",
    )
    print(full)
