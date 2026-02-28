import os
import requests
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from dotenv import load_dotenv

# Re-use font definitions from carousel engine
try:
    from engine.generate_carousel import FONT_CANDIDATES_TYPEWRITER, FONT_CANDIDATES_SANS, _find_font
except ImportError:
    from generate_carousel import FONT_CANDIDATES_TYPEWRITER, FONT_CANDIDATES_SANS, _find_font

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

STORY_WIDTH = 1080
STORY_HEIGHT = 1920

def get_soothing_background():
    """Fetches a vertical 'soothing/light' image from Pexels."""
    if not PEXELS_API_KEY:
        print("[ERROR] Pexels API key missing.")
        return None
        
    queries = ["morning sun", "calm ocean", "soft clouds", "healing nature", "gentle light", "sunrise mist"]
    query = random.choice(queries)
    
    url = f"https://api.pexels.com/v1/search?query={query}&orientation=portrait&size=large&per_page=15"
    headers = {"Authorization": PEXELS_API_KEY}
    
    print(f"[FETCH] Fetching Story Background from Pexels (Query: '{query}')...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        photos = data.get("photos", [])
        if photos:
            photo = random.choice(photos)
            return photo["src"]["large2x"] # High res portrait
    print(f"[ERROR] Failed to fetch from Pexels: {response.status_code}")
    return None

def download_image(url, filepath):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return True
    return False

def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within a specific width."""
    lines = []
    words = text.split()
    while words:
        line = ''
        while words and draw.textlength(line + words[0], font=font) <= max_width:
            line += (words.pop(0) + ' ')
        lines.append(line.strip())
    return lines

def create_news_story_image(headline, summary, output_path):
    """Generates the 9:16 Instagram Story image."""
    
    bg_url = get_soothing_background()
    if not bg_url:
        return False
        
    bg_path = os.path.join(os.path.dirname(__file__), "..", "data", "temp_story_bg.jpg")
    os.makedirs(os.path.dirname(bg_path), exist_ok=True)
    
    if not download_image(bg_url, bg_path):
        return False

    # 1. Load Background and Resize/Crop to exactly 1080x1920
    try:
        base_img = Image.open(bg_path).convert("RGBA")
        
        # Calculate ratio to fill the target box (1080x1920)
        target_ratio = STORY_WIDTH / STORY_HEIGHT
        img_ratio = base_img.width / base_img.height
        
        if img_ratio > target_ratio:
            # Image is too wide, resize to match height
            new_height = STORY_HEIGHT
            new_width = int(new_height * img_ratio)
        else:
            # Image is too tall, resize to match width
            new_width = STORY_WIDTH
            new_height = int(new_width / img_ratio)
            
        base_img = base_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Center crop to exactly 1080x1920
        left = (new_width - STORY_WIDTH) // 2
        top = (new_height - STORY_HEIGHT) // 2
        base_img = base_img.crop((left, top, left + STORY_WIDTH, top + STORY_HEIGHT))
        
    except Exception as e:
        print(f"[ERROR] Processing background: {e}")
        return False

    # 2. Add subtle dark gradient/overlay so white text pops even on light backgrounds
    overlay = Image.new("RGBA", (STORY_WIDTH, STORY_HEIGHT), (0, 0, 0, 160)) # 160 alpha = ~62% opacity
    img = Image.alpha_composite(base_img, overlay)
    
    # Optional: subtle vignette
    x = __import__('numpy').linspace(-1, 1, STORY_WIDTH)
    y = __import__('numpy').linspace(-1, 1, STORY_HEIGHT)
    X, Y = __import__('numpy').meshgrid(x, y)
    radius = __import__('numpy').sqrt(X**2 + Y**2)
    mask = __import__('numpy').clip(1 - (radius * 1.0), 0, 1)
    alpha_data = ((1.0 - mask) * 255 * 0.7).astype('uint8')
    alpha_img = Image.fromarray(alpha_data)
    black = Image.new('L', (STORY_WIDTH, STORY_HEIGHT), 0)
    vignette = Image.merge("RGBA", (black, black, black, alpha_img))
    img = Image.alpha_composite(img, vignette)
    
    draw = ImageDraw.Draw(img)

    # 3. Setup Fonts
    font_label = _find_font(FONT_CANDIDATES_TYPEWRITER, 55)
    font_headline = _find_font(FONT_CANDIDATES_TYPEWRITER, 95)
    font_summary = _find_font(FONT_CANDIDATES_TYPEWRITER, 70)
    font_watermark = _find_font(FONT_CANDIDATES_SANS, 45)

    margin = 80
    max_text_width = STORY_WIDTH - (margin * 2)
    # Start near the top to give the summary plenty of space
    current_y = 200 

    def draw_text_with_glow(canvas, xy, text, font, fill, glow_fill, glow_radius=5):
        # Soft glow behind text
        glow_canvas = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_canvas)
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                glow_draw.text((xy[0] + dx, xy[1] + dy), text, font=font, fill=glow_fill)
        glow_canvas = glow_canvas.filter(ImageFilter.GaussianBlur(radius=glow_radius))
        canvas = Image.alpha_composite(canvas, glow_canvas)
        # Main text
        ImageDraw.Draw(canvas).text(xy, text, font=font, fill=fill)
        return canvas

    # 4. Draw "POSITIVE NEWS OF THE DAY" Label
    label_text = "POSITIVE NEWS OF THE DAY"
    label_w = draw.textlength(label_text, font=font_label)
    img = draw_text_with_glow(img, ((STORY_WIDTH - label_w) / 2, current_y), label_text, font=font_label, fill=(255, 204, 0, 255), glow_fill=(255, 204, 0, 80))
    current_y += 180

    # 5. Draw Headline
    headline_lines = wrap_text(headline, font_headline, max_text_width, draw)
    for line in headline_lines:
        line_w = draw.textlength(line, font=font_headline)
        img = draw_text_with_glow(img, ((STORY_WIDTH - line_w) / 2, current_y), line, font=font_headline, fill=(255, 255, 255, 255), glow_fill=(255, 255, 255, 50))
        current_y += 110
    
    current_y += 120 # Gap before summary

    # 6. Draw Summary
    summary_lines = wrap_text(summary, font_summary, max_text_width, draw)
    for line in summary_lines:
        line_w = draw.textlength(line, font=font_summary)
        img = draw_text_with_glow(img, ((STORY_WIDTH - line_w) / 2, current_y), line, font=font_summary, fill=(230, 230, 230, 255), glow_fill=(255, 255, 255, 40))
        current_y += 85
        
    # 7. Add Brand Footer (Watermark)
    footer_text = "@_the_positive_quote"
    footer_w = draw.textlength(footer_text, font=font_watermark)
    # Strong watermark at the bottom
    img = draw_text_with_glow(img, ((STORY_WIDTH - footer_w) / 2, STORY_HEIGHT - 120), footer_text, font=font_watermark, fill=(255, 255, 255, 200), glow_fill=(0, 0, 0, 150), glow_radius=3)


    # Save final
    img = img.convert("RGB") # Drop alpha for JPEG mapping
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, quality=95)
    print(f"[SUCCESS] Story Image generated: {output_path}")
    
    # Cleanup temp bg
    if os.path.exists(bg_path):
        os.remove(bg_path)
        
    return True

if __name__ == "__main__":
    # Test generation
    test_out = os.path.join(os.path.dirname(__file__), "..", "output", "test_story.jpg")
    create_news_story_image(
        "YANGTZE RIVER REBOUNDS: A GLOBAL HOPE.",
        "After a decade-long ban and massive investment, China's Yangtze River is thriving again. A powerful testament to nature's resilience and humanity's ability to heal.",
        test_out
    )
