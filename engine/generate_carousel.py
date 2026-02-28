"""
Carousel Post Engine — Produces dark, cinematic 1080x1080 Instagram carousel slides.
═══════════════════════════════════════════════════════════════════════════════════
Style: @_the_positive_quote

Visual Pipeline per slide:
  1. Pexels background photo (dark, cinematic query)
  2. Crop/resize to 1080x1080
  3. Cinematic color grading (desaturation + contrast + warm shadows)
  4. Semi-transparent dim overlay
  5. Radial vignette
  6. Subtle film grain
  7. Typewriter text (white) with one golden highlighted word + soft glow
  8. @_the_positive_quote watermark (bottom-right, semi-transparent)
"""

import os
import sys
import re
import json
import uuid
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Ensure Windows console handles unicode
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


# ─── Constants ──────────────────────────────────────────────────────────────────

SLIDE_SIZE = 1080
WATERMARK_TEXT = "@_the_positive_quote"
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

# Typewriter-style fonts
FONT_CANDIDATES_TYPEWRITER = [
    os.path.join(ASSETS_DIR, "fonts", "CourierPrime-Regular.ttf"),
    os.path.join(ASSETS_DIR, "fonts", "courier.ttf"),
    "C:\\Windows\\Fonts\\cour.ttf",       # Courier New
    "C:\\Windows\\Fonts\\consola.ttf",    # Consolas
    "C:\\Windows\\Fonts\\lucon.ttf",      # Lucida Console
    "cour.ttf",
]

FONT_CANDIDATES_SANS = [
    os.path.join(ASSETS_DIR, "fonts", "arial.ttf"),
    "C:\\Windows\\Fonts\\calibril.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
    "arial.ttf",
]

# Golden highlight color
GOLDEN = (255, 204, 0)
WHITE = (255, 255, 255)


# ─── Utility ────────────────────────────────────────────────────────────────────

def _find_font(candidates, size):
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _clean_text(text):
    return re.sub(r'[^\x00-\x7F\u2018\u2019\u201C\u201D\u2014\u2026]+', '', text).strip()


# ─── Pexels Image Fetch ────────────────────────────────────────────────────────

def fetch_pexels_image(query, output_path, orientation="square"):
    """Fetch a photo from Pexels API and save it locally."""
    if not PEXELS_API_KEY:
        print("[ERROR] No PEXELS_API_KEY set.")
        return False

    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={query}&orientation={orientation}&per_page=15&size=large"

    try:
        print(f"   [PEXELS] Searching: '{query}'...")
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()

        photos = data.get("photos", [])
        if not photos:
            print(f"   [WARN] No photos for '{query}', trying fallback...")
            if query != "dark cinematic sunset":
                return fetch_pexels_image("dark cinematic sunset", output_path, orientation)
            return False

        # Pick a random photo from top results for variety
        import random
        photo = random.choice(photos[:8])
        img_url = photo["src"]["large2x"]  # High quality

        print(f"   [DOWNLOAD] Downloading photo...")
        img_r = requests.get(img_url, timeout=60)
        img_r.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(img_r.content)

        print(f"   [DONE] Photo saved.")
        return True

    except Exception as e:
        print(f"   [ERROR] Pexels fetch failed: {e}")
        return False


# ─── Image Processing ──────────────────────────────────────────────────────────

def crop_to_square(img):
    """Center-crop image to square."""
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side)).resize(
        (SLIDE_SIZE, SLIDE_SIZE), Image.LANCZOS
    )


def apply_cinematic_grade_image(img):
    """Dark cinematic color grading on a PIL image."""
    arr = np.array(img).astype(np.float32)

    # 1. Desaturate (65% saturation)
    grey = np.mean(arr[:, :, :3], axis=2, keepdims=True)
    arr[:, :, :3] = arr[:, :, :3] * 0.65 + grey * 0.35

    # 2. Boost contrast (1.3x around midpoint)
    midpoint = 128.0
    arr[:, :, :3] = (arr[:, :, :3] - midpoint) * 1.3 + midpoint

    # 3. Warm shadow tint (amber in dark areas)
    shadow_mask = np.clip(1.0 - (arr[:, :, :3] / 128.0), 0, 1)
    arr[:, :, 0] += shadow_mask[:, :, 0] * 10  # Red +
    arr[:, :, 1] += shadow_mask[:, :, 1] * 5   # Green +
    arr[:, :, 2] -= shadow_mask[:, :, 2] * 4   # Blue -

    # 4. Darken overall
    arr[:, :, :3] *= 0.82

    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def create_dim_overlay(size, opacity=150):
    """Semi-transparent black overlay for readability."""
    return Image.new('RGBA', (size, size), (0, 0, 0, opacity))


def create_vignette_image(size, intensity=1.3):
    """Creates a radial vignette overlay."""
    x = np.linspace(-1, 1, size)
    y = np.linspace(-1, 1, size)
    X, Y = np.meshgrid(x, y)
    radius = np.sqrt(X**2 + Y**2)
    mask = np.clip(1 - (radius * intensity), 0, 1)

    alpha_data = ((1.0 - mask) * 255 * 0.8).astype('uint8')
    alpha_img = Image.fromarray(alpha_data)
    black = Image.new('L', (size, size), 0)
    return Image.merge("RGBA", (black, black, black, alpha_img))


def add_film_grain(img, intensity=20):
    """Add subtle film grain noise."""
    arr = np.array(img).astype(np.int16)
    noise = np.random.normal(0, intensity, arr.shape[:2]).astype(np.int16)
    for c in range(3):
        arr[:, :, c] = np.clip(arr[:, :, c] + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


# ─── Text Rendering ────────────────────────────────────────────────────────────

def render_quote_on_image(img, lines, highlight_word, font_size=52):
    """
    Render quote text on image with golden highlight on one word.
    Features:
    - Auto word wrapping within safe margins
    - Auto font-size reduction if text is too wide
    - Proper vertical + horizontal centering
    """
    canvas = img.copy().convert('RGBA')
    draw = ImageDraw.Draw(canvas)

    # Safe area padding (120px on each side)
    PADDING = 120
    MAX_TEXT_WIDTH = SLIDE_SIZE - (PADDING * 2)

    highlight_upper = highlight_word.strip(".,!?;:'\"").upper() if highlight_word else ""

    # ── Step 1: Find font size that fits all lines ──
    def _measure_line(text, fnt):
        try:
            bbox = draw.textbbox((0, 0), text, font=fnt)
            return bbox[2] - bbox[0]
        except AttributeError:
            # Fallback for older PIL
            return fnt.getlength(text) if hasattr(fnt, 'getlength') else 0

    def _wrap_lines(raw_lines, fnt):
        """Word-wrap all lines to fit within MAX_TEXT_WIDTH."""
        wrapped = []
        for line in raw_lines:
            if not line.strip():
                wrapped.append("")  # keep spacers
                continue
            words = line.split()
            current = ""
            for word in words:
                test = f"{current} {word}".strip()
                if _measure_line(test, fnt) <= MAX_TEXT_WIDTH:
                    current = test
                else:
                    if current:
                        wrapped.append(current)
                    current = word
            if current:
                wrapped.append(current)
        return wrapped

    # Try decreasing font sizes until everything fits
    for try_size in range(font_size, 28, -2):
        font = _find_font(FONT_CANDIDATES_TYPEWRITER, try_size)
        wrapped = _wrap_lines(lines, font)
        # Check if all wrapped lines fit
        all_fit = all(
            _measure_line(l, font) <= MAX_TEXT_WIDTH
            for l in wrapped if l.strip()
        )
        if all_fit:
            break
    else:
        font = _find_font(FONT_CANDIDATES_TYPEWRITER, 30)
        wrapped = _wrap_lines(lines, font)

    # ── Step 2: Calculate vertical centering ──
    # Calculate more accurate line height using textbbox
    try:
        _, top, _, bottom = draw.textbbox((0, 0), "A", font=font)
        actual_h = bottom - top
    except AttributeError:
        actual_h = try_size
    line_height = max(try_size + 20, int(actual_h * 1.5))
    total_height = len(wrapped) * line_height
    y_start = (SLIDE_SIZE - total_height) // 2

    # ── Step 3: Draw each line, word by word ──
    for i, line in enumerate(wrapped):
        if not line.strip():
            continue  # skip spacer but keep its vertical space

        y = y_start + i * line_height

        # Measure each word for centering
        words = line.split()
        word_segments = []
        for word in words:
            w = _measure_line(word + " ", font)
            word_segments.append((word, w))

        total_width = sum(w for _, w in word_segments)
        # Remove trailing space from last word measurement
        if word_segments:
            last_word = word_segments[-1][0]
            last_w = _measure_line(last_word, font)
            total_width = total_width - word_segments[-1][1] + last_w

        x = (SLIDE_SIZE - total_width) // 2

        # Draw word by word
        for j, (word, seg_w) in enumerate(word_segments):
            clean_word = word.strip(".,!?;:'\"").upper()
            is_highlight = clean_word == highlight_upper

            if is_highlight:
                color = GOLDEN + (255,)
                glow_color = (255, 204, 0, 80)
            else:
                color = WHITE + (240,)
                glow_color = (255, 255, 255, 50)

            # Soft glow behind text
            glow_canvas = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_canvas)
            for dx in [-3, -2, -1, 0, 1, 2, 3]:
                for dy in [-3, -2, -1, 0, 1, 2, 3]:
                    glow_draw.text((x + dx, y + dy), word, font=font, fill=glow_color)
            glow_canvas = glow_canvas.filter(ImageFilter.GaussianBlur(radius=5))
            canvas = Image.alpha_composite(canvas, glow_canvas)
            draw = ImageDraw.Draw(canvas)

            # Main text
            draw.text((x, y), word, font=font, fill=color)
            x += seg_w

    return canvas


def add_watermark(img, text=WATERMARK_TEXT):
    """Add semi-transparent watermark to bottom-right."""
    canvas = img.copy().convert('RGBA')
    draw = ImageDraw.Draw(canvas)

    font = _find_font(FONT_CANDIDATES_SANS, 28)
    wm_color = (255, 255, 255, 100)

    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw = font.getlength(text) if hasattr(font, 'getlength') else 0

    x = SLIDE_SIZE - tw - 30
    y = SLIDE_SIZE - 50

    draw.text((x, y), text, font=font, fill=wm_color)
    return canvas


# ─── Gemini Quote + Caption Generator ──────────────────────────────────────────

def generate_carousel_content():
    """
    Uses Gemini to generate 3 slide quotes + SEO caption + hashtags.
    Uses multi-key rotation to avoid quota exhaustion.
    Returns dict with slide data and caption.
    """
    try:
        from engine.gemini_keys import generate_with_rotation
    except ImportError:
        from gemini_keys import generate_with_rotation

    prompt = """You are a premium Instagram content strategist for @_the_positive_quote.
Generate content for a 3-slide dark cinematic motivational carousel post.

Return ONLY raw JSON (no markdown blocks). The JSON must have this exact structure:
{
  "slides": [
    {
      "slide_number": 1,
      "theme": "motivation",
      "quote_line_1": "First line of quote",
      "quote_line_2": "Second line of quote",
      "highlight_word": "ONE key word to highlight in golden",
      "pexels_query": "dark cinematic search query for background (3-4 words)"
    },
    {
      "slide_number": 2,
      "theme": "healing",
      "quote_line_1": "...",
      "quote_line_2": "...",
      "highlight_word": "...",
      "pexels_query": "..."
    },
    {
      "slide_number": 3,
      "theme": "cta",
      "quote_line_1": "Dynamic short emotional hook (varying each time)",
      "quote_line_2": "Dynamic short emotional follow-up (varying each time)",
      "cta_line_1": "Follow @_the_positive_quote",
      "cta_line_2": "Dynamic emotional CTA (e.g., Share with a quiet soul)",
      "highlight_word": "light",
      "pexels_query": "..."
    }
  ],
  "caption": "Full Instagram caption here with hook, emotional paragraph, CTA, question, and save/share encouragement",
  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10", "tag11", "tag12", "tag13", "tag14", "tag15"]
}

RULES:
- Slide 1 (Motivation): Max 18 words across two lines. Deep, powerful, not aggressive. Pexels query should be dark moody landscape (e.g. "dark sunset silhouette road")
- Slide 2 (Healing): Two lines max. Calm, reflective. Pexels query: nature close-ups (e.g. "butterfly dark golden light", "rain window blur", "moon reflection water")
- Slide 3 (CTA): Write a completely custom, dynamic short emotional hook (`quote_line_1` and `quote_line_2`) that changes entirely every time. Do NOT reuse "This world is heavy". Must include "Follow @_the_positive_quote" as `cta_line_1`. For the secondary CTA (`cta_line_2`), write exactly ONE highly emotional but COMMANDING phrase (3-to-5 words) that actively forces the viewer to do ONE of these actions: Save, Share, or Follow. Do not just ask nicely—tell them what to do. (e.g., "Save this before you forget", "Share this to help them", "Follow us to stay strong"). Randomly rotate the focused action. Pexels query: hopeful dark (e.g. "sunrise dark clouds", "candle flame dark")
- Highlight ONE powerful word per slide in golden
- Caption: Strong hook first 2 lines, emotional paragraph, engaging question, and ONE emotional dynamic CTA (randomly focusing on only Save, Share, Like, or Follow). Make it deeply emotional and organic.
- Exactly 15 hashtags: 5 high volume (#motivation #quotes #viral #mindset #explore), 5 medium (#deepthoughts #innergrowth #healingjourney #lifequotes #positivevibes), 5 niche (#darkcinematic #cinematicquotes #motivationaldarkquotes #thepositivequote #quotestoliveby)
- Do NOT use any banned or spam hashtags.
- All quotes must be original, deep, mature, emotionally powerful.
- Tone: Premium, cinematic, deeply human.
"""

    print("[AI] Generating carousel content via Gemini (with key rotation)...")
    raw = generate_with_rotation(prompt, temperature=0.8)

    if not raw:
        print("[ERROR] All Gemini keys/models exhausted!")
        return None

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        data = json.loads(cleaned.strip())
        print(f"[OK] Generated {len(data.get('slides', []))} slides + caption.")
        return data
    except Exception as e:
        print(f"[ERROR] Failed to parse Gemini JSON: {e}")
        return None


# ─── Slide Generator ───────────────────────────────────────────────────────────

def generate_single_slide(slide_data, output_path):
    """
    Generate a single 1080x1080 carousel slide image.
    """
    # 1. Fetch background photo
    temp_photo = f"temp_carousel_{uuid.uuid4().hex[:8]}.jpg"
    query = slide_data.get("pexels_query", "dark cinematic sunset")

    if not fetch_pexels_image(query, temp_photo):
        if not fetch_pexels_image("dark cinematic sunset", temp_photo):
            print("[ERROR] Could not fetch background image.")
            return None

    try:
        # 2. Load and crop to square
        img = Image.open(temp_photo).convert('RGB')
        img = crop_to_square(img)

        # 3. Cinematic color grading
        img = apply_cinematic_grade_image(img)

        # 4. Film grain
        img = add_film_grain(img, intensity=18)

        # Convert to RGBA for compositing
        img = img.convert('RGBA')

        # 5. Dim overlay
        dim = create_dim_overlay(SLIDE_SIZE, opacity=140)
        img = Image.alpha_composite(img, dim)

        # 6. Vignette
        vignette = create_vignette_image(SLIDE_SIZE, intensity=1.3)
        img = Image.alpha_composite(img, vignette)

        # 7. Render quote text
        lines = []
        lines.append(slide_data.get("quote_line_1", ""))
        lines.append(slide_data.get("quote_line_2", ""))

        # For CTA slide, add extra lines
        if slide_data.get("cta_line_1"):
            lines.append("")  # spacer
            lines.append(slide_data["cta_line_1"])
        if slide_data.get("cta_line_2"):
            lines.append(slide_data["cta_line_2"])

        # Filter empty lines for quote (but keep spacer for CTA)
        has_cta = bool(slide_data.get("cta_line_1"))
        if not has_cta:
            lines = [l for l in lines if l.strip()]

        highlight = slide_data.get("highlight_word", "")

        # Adjust font size based on content
        if has_cta:
            font_size = 44
        else:
            font_size = 54

        img = render_quote_on_image(img, lines, highlight, font_size=font_size)

        # 8. Watermark
        img = add_watermark(img)

        # 9. Save as PNG (high quality)
        final = img.convert('RGB')
        final.save(output_path, "PNG", quality=95)

        print(f"   [SAVED] {output_path}")
        return output_path

    except Exception as e:
        print(f"[ERROR] Slide generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        if os.path.exists(temp_photo):
            try:
                os.remove(temp_photo)
            except:
                pass


# ─── Main Carousel Generator ───────────────────────────────────────────────────

def generate_carousel(output_dir=None):
    """
    Generate a complete 3-slide carousel post.

    Returns:
        dict with 'slides' (list of file paths), 'caption' (str), 'hashtags' (list)
        or None on failure.
    """
    print("=" * 60)
    print("🎨 CAROUSEL POST ENGINE — Starting...")
    print("=" * 60)

    if output_dir is None:
        output_dir = OUTPUT_DIR

    # Create timestamped folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    carousel_dir = os.path.join(output_dir, f"carousel_{timestamp}")
    os.makedirs(carousel_dir, exist_ok=True)

    # 1. Generate content via Gemini
    content = generate_carousel_content()
    if not content or "slides" not in content:
        print("[ERROR] Failed to generate carousel content!")
        return None

    slides_data = content["slides"]
    caption = content.get("caption", "")
    hashtags = content.get("hashtags", [])

    # 2. Generate each slide
    slide_paths = []
    for i, slide_data in enumerate(slides_data):
        print(f"\n{'─' * 50}")
        print(f"📸 Slide {i + 1}: {slide_data.get('theme', 'unknown')}")
        print(f"   Quote: \"{slide_data.get('quote_line_1', '')}\"")
        print(f"          \"{slide_data.get('quote_line_2', '')}\"")
        print(f"   Highlight: {slide_data.get('highlight_word', '')}")
        print(f"{'─' * 50}")

        slide_path = os.path.join(carousel_dir, f"slide_{i + 1}.png")
        result = generate_single_slide(slide_data, slide_path)

        if result:
            slide_paths.append(result)
        else:
            print(f"[WARN] Slide {i + 1} failed!")

    if len(slide_paths) < 3:
        print(f"[ERROR] Only {len(slide_paths)}/3 slides generated!")
        return None

    # 3. Build full caption with hashtags
    hashtag_str = " ".join(f"#{tag.lstrip('#')}" for tag in hashtags)
    full_caption = f"{caption}\n\n.\n.\n.\n{hashtag_str}"

    # 4. Save caption to file
    caption_path = os.path.join(carousel_dir, "caption.txt")
    with open(caption_path, 'w', encoding='utf-8') as f:
        f.write(full_caption)

    print(f"\n{'=' * 60}")
    print(f"✅ CAROUSEL COMPLETE: {len(slide_paths)} slides")
    print(f"   Directory: {carousel_dir}")
    print(f"   Caption saved: {caption_path}")
    print(f"{'=' * 60}")

    return {
        "slides": slide_paths,
        "caption": full_caption,
        "hashtags": hashtags,
        "carousel_dir": carousel_dir,
    }


if __name__ == "__main__":
    result = generate_carousel()
    if result:
        print(f"\nSlides: {result['slides']}")
        print(f"\nCaption preview:\n{result['caption'][:300]}...")
