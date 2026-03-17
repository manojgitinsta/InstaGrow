"""
Cinematic Reel Engine — Produces dark, moody, cinematic 9:16 motivational reels.
═══════════════════════════════════════════════════════════════════════════════════
Style: @_the_positive_quote

Visual Effects Pipeline:
  1. Pexels background video (dark, cinematic query)
  2. Ken Burns slow zoom (1.0x → 1.15x)
  3. Cinematic color grading (desaturation + contrast + warm shadows)
  4. Heavy radial vignette
  5. Animated film grain overlay
  6. Elegant serif typography with soft glow + fade-in
  7. @_the_positive_quote watermark
  8. Cinematic piano audio at 30% volume
"""

from moviepy import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip,
    concatenate_videoclips, TextClip, ImageClip, concatenate_audioclips,
)
import moviepy.video.fx as vfx
import moviepy.audio.fx as afx
import sys
import os
import traceback
import time
import uuid
import re
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Ensure Windows console handles emojis/unicode correctly
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from engine.fetch_pexels_video import fetch_pexels_video
except ImportError:
    from fetch_pexels_video import fetch_pexels_video


# ─── Constants ──────────────────────────────────────────────────────────────────

REEL_WIDTH = 1080
REEL_HEIGHT = 1920
FPS = 24
WATERMARK_TEXT = "@_the_positive_quote"

# Typography: Try elegant serif fonts, fall back gracefully
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

FONT_CANDIDATES_TYPEWRITER = [
    os.path.join(ASSETS_DIR, "fonts", "CourierPrime-Regular.ttf"),
    os.path.join(ASSETS_DIR, "fonts", "courier.ttf"),
    "C:\\Windows\\Fonts\\cour.ttf",
    "C:\\Windows\\Fonts\\consola.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", # GitHub Actions Ubuntu
    "cour.ttf",
    "georgia.ttf",
]
FONT_CANDIDATES_SANS = [
    os.path.join(ASSETS_DIR, "fonts", "arial.ttf"),
    "C:\\Windows\\Fonts\\calibril.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", # GitHub Actions Ubuntu
    "arial.ttf",
]


# ─── Utility Functions ─────────────────────────────────────────────────────────

def _find_font(candidates, size):
    """Try each font path until one works."""
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _clean_text(text):
    """Remove emojis and special characters, keep standard punctuation."""
    return re.sub(r'[^\x00-\x7F\u2018\u2019\u201C\u201D\u2014\u2026]+', '', text).strip()


def _create_image_clip(img_rgba, dur):
    """Create a masked ImageClip from a PIL RGBA image."""
    rgb = np.array(img_rgba.convert("RGB"))
    alpha = np.array(img_rgba.split()[3]) / 255.0
    clip = ImageClip(rgb).with_duration(dur)
    mask = ImageClip(alpha, is_mask=True).with_duration(dur)
    return clip.with_mask(mask)


# ─── Visual Effects ─────────────────────────────────────────────────────────────

def create_vignette_overlay(duration, intensity=1.2):
    """Creates a heavy radial vignette overlay (dark corners)."""
    x = np.linspace(-1, 1, REEL_WIDTH)
    y = np.linspace(-1, 1, REEL_HEIGHT)
    X, Y = np.meshgrid(x, y)
    radius = np.sqrt(X**2 + Y**2)
    mask = np.clip(1 - (radius * intensity), 0, 1)

    # Black overlay where vignette darkens
    alpha_data = ((1.0 - mask) * 255 * 0.85).astype('uint8')
    alpha_img = Image.fromarray(alpha_data)
    black = Image.new('L', (REEL_WIDTH, REEL_HEIGHT), 0)
    vignette_img = Image.merge("RGBA", (black, black, black, alpha_img))

    return _create_image_clip(vignette_img, duration)


def create_film_grain_frame(w, h, intensity=25):
    """Generate a single frame of film grain noise."""
    noise = np.random.normal(0, intensity, (h, w)).astype(np.int16)
    # Create RGBA: grey noise with partial transparency
    grey = np.clip(128 + noise, 0, 255).astype(np.uint8)
    alpha = np.full((h, w), 30, dtype=np.uint8)  # Very subtle
    return np.stack([grey, grey, grey, alpha], axis=-1)


def apply_ken_burns_zoom(clip, zoom_start=1.0, zoom_end=1.15, style=None):
    """
    Apply a Ken Burns effect. Style can be:
      'zoom_in'  — classic slow zoom in
      'zoom_out' — starts zoomed, pulls back
      'pan_left' — slow pan from right to left
      'pan_right'— slow pan from left to right
    If style is None, a random style is chosen.
    """
    if style is None:
        style = random.choice(['zoom_in', 'zoom_out', 'pan_left', 'pan_right'])
    print(f"   \U0001f3ac Ken Burns style: {style}")

    duration = clip.duration
    w, h = clip.size

    def zoom_effect(get_frame, t):
        progress = t / duration
        frame = get_frame(t)

        if style == 'zoom_in':
            scale = zoom_start + (zoom_end - zoom_start) * progress
        elif style == 'zoom_out':
            scale = zoom_end - (zoom_end - zoom_start) * progress
        else:
            scale = (zoom_start + zoom_end) / 2  # constant mild zoom for pans

        new_w = int(w / scale)
        new_h = int(h / scale)

        if style == 'pan_left':
            max_shift = w - new_w
            x_offset = int(max_shift * (1 - progress))
            y_offset = (h - new_h) // 2
        elif style == 'pan_right':
            max_shift = w - new_w
            x_offset = int(max_shift * progress)
            y_offset = (h - new_h) // 2
        else:
            x_offset = (w - new_w) // 2
            y_offset = (h - new_h) // 2

        # Clamp to prevent out-of-bounds
        x_offset = max(0, min(x_offset, w - new_w))
        y_offset = max(0, min(y_offset, h - new_h))

        cropped = frame[y_offset:y_offset + new_h, x_offset:x_offset + new_w]

        from PIL import Image as PILImage
        img = PILImage.fromarray(cropped)
        img = img.resize((w, h), PILImage.LANCZOS)
        return np.array(img)

    return clip.transform(zoom_effect)


# Color grading presets for visual variety
GRADING_PRESETS = {
    'warm_amber': {'sat': 0.65, 'contrast': 1.25, 'r': 10, 'g': 5, 'b': -4, 'dark': 0.86},
    'cold_blue':  {'sat': 0.60, 'contrast': 1.30, 'r': -3, 'g': 2, 'b': 8, 'dark': 0.84},
    'noir':       {'sat': 0.40, 'contrast': 1.40, 'r': 3, 'g': 3, 'b': 3, 'dark': 0.80},
    'golden_hour':{'sat': 0.75, 'contrast': 1.20, 'r': 12, 'g': 8, 'b': -6, 'dark': 0.90},
}


def apply_cinematic_grade(clip, preset=None):
    """Apply dark cinematic color grading with a random visual preset."""
    if preset is None:
        preset = random.choice(list(GRADING_PRESETS.keys()))
    p = GRADING_PRESETS[preset]
    print(f"   \U0001f3a8 Color grade: {preset}")

    def grade_frame(frame):
        img = frame.astype(np.float32)

        # 1. Desaturate
        grey = np.mean(img, axis=2, keepdims=True)
        img = img * p['sat'] + grey * (1 - p['sat'])

        # 2. Boost contrast
        midpoint = 128.0
        img = (img - midpoint) * p['contrast'] + midpoint

        # 3. Shadow tint
        shadow_mask = np.clip(1.0 - (img / 128.0), 0, 1)
        img[:, :, 0] += shadow_mask[:, :, 0] * p['r']
        img[:, :, 1] += shadow_mask[:, :, 1] * p['g']
        img[:, :, 2] += shadow_mask[:, :, 2] * p['b']

        # 4. Overall darkening
        img *= p['dark']

        return np.clip(img, 0, 255).astype(np.uint8)

    return clip.image_transform(grade_frame)


# ─── Text Rendering ─────────────────────────────────────────────────────────────

def _wrap_text(text, font, max_width, draw):
    """Wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test = " ".join(current_line + [word])
        try:
            left, top, right, bottom = draw.textbbox((0, 0), test, font=font)
            tw = right - left
        except AttributeError:
            tw = font.getlength(test) if hasattr(font, 'getlength') else 0

        if tw > max_width and current_line:
            lines.append(" ".join(current_line))
            current_line = [word]
        else:
            current_line.append(word)

    if current_line:
        lines.append(" ".join(current_line))
    return lines


def create_text_overlay(text, font, y_center, duration, glow=True, color=(255, 255, 255)):
    """Create a centered text overlay with optional soft glow effect."""
    canvas = Image.new('RGBA', (REEL_WIDTH, REEL_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    lines = _wrap_text(text, font, REEL_WIDTH - 160, draw)

    # Calculate total text block height
    line_height = font.size + 16
    
    # Precise height calculation
    try:
        _, top, _, bottom = draw.textbbox((0, 0), "A", font=font)
        text_actual_height = bottom - top
    except AttributeError:
        text_actual_height = font.size
        
    line_height = max(line_height, int(text_actual_height * 1.5))
    total_height = len(lines) * line_height
    y_start = y_center - total_height // 2

    for i, line in enumerate(lines):
        try:
            left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
            tw = right - left
        except AttributeError:
            tw = font.getlength(line) if hasattr(font, 'getlength') else 0

        x = (REEL_WIDTH - tw) // 2
        y = y_start + i * line_height

        if glow:
            # 1. Dark Drop Shadow (improves contrast against bright backgrounds)
            shadow_color = (0, 0, 0, 255)
            shadow_offset = 5
            draw.text((x + shadow_offset, y + shadow_offset), line, font=font, fill=shadow_color)
            
            # 2. Soft glow: draw text slightly larger in semi-transparent white, then blur
            # We must apply glow on a separate layer so it blurs cleanly
            glow_canvas = Image.new('RGBA', (REEL_WIDTH, REEL_HEIGHT), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_canvas)
            glow_color = (color[0], color[1], color[2], 60)
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    glow_draw.text((x + dx, y + dy), line, font=font, fill=glow_color)
            glow_canvas = glow_canvas.filter(ImageFilter.GaussianBlur(radius=4))
            canvas = Image.alpha_composite(canvas, glow_canvas)
            draw = ImageDraw.Draw(canvas)  # Refresh draw object

        # Main text with slight stroke for crispness
        draw.text((x, y), line, font=font, fill=color + (255,), stroke_width=2, stroke_fill=(0,0,0,150))

    clip = _create_image_clip(canvas, duration)
    return clip, total_height


def create_watermark_overlay(duration):
    """Create the @_the_positive_quote watermark — visible but not distracting."""
    canvas = Image.new('RGBA', (REEL_WIDTH, REEL_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    font = _find_font(FONT_CANDIDATES_SANS, 56)  # Larger for visibility
    wm_color = (255, 255, 255, 140)  # More visible

    try:
        left, top, right, bottom = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
        tw = right - left
    except AttributeError:
        tw = font.getlength(WATERMARK_TEXT) if hasattr(font, 'getlength') else 0

    x = REEL_WIDTH - tw - 50
    y = REEL_HEIGHT - 220  # Moved higher up to be distinctly visible

    draw.text((x, y), WATERMARK_TEXT, font=font, fill=wm_color)
    return _create_image_clip(canvas, duration)


# Rotating CTA pool — never the same CTA twice in a row
CTA_POOL = [
    "Send this to someone who needs it",
    "Save this for your darkest hour",
    "Share with someone fighting silently",
    "Tag someone who understands this",
    "Save this. Read it again at 3AM.",
    "Follow for more truths like this",
    "Double tap if this hit different",
    "Share this before you forget",
    "Send this to your strongest friend",
    "Save this. You'll need it someday.",
    "Tag someone who never gives up",
    "Follow if you felt this one",
    "Share with someone rebuilding",
    "Save this for when you almost quit",
    "This one's for the silent warriors",
]


def create_cta_overlay(duration, appear_at):
    """Create a CTA overlay from a rotating pool — appears in the last few seconds."""
    cta_text = random.choice(CTA_POOL)
    canvas = Image.new('RGBA', (REEL_WIDTH, REEL_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    font = _find_font(FONT_CANDIDATES_SANS, 38)
    cta_color = (255, 255, 255, 200)

    # Center horizontally, place in lower third
    try:
        left, top, right, bottom = draw.textbbox((0, 0), cta_text, font=font)
        tw = right - left
    except AttributeError:
        tw = font.getlength(cta_text) if hasattr(font, 'getlength') else 0

    x = (REEL_WIDTH - tw) // 2
    y = REEL_HEIGHT - 350  # Above the watermark

    # Shadow for CTA
    draw.text((x + 2, y + 2), cta_text, font=font, fill=(0, 0, 0, 150))
    
    # Soft glow behind CTA
    glow_canvas = Image.new('RGBA', (REEL_WIDTH, REEL_HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_canvas)
    for dx in [-2, -1, 0, 1, 2]:
        for dy in [-2, -1, 0, 1, 2]:
            glow_draw.text((x + dx, y + dy), cta_text, font=font, fill=(255, 255, 255, 40))
    glow_canvas = glow_canvas.filter(ImageFilter.GaussianBlur(radius=3))
    canvas = Image.alpha_composite(canvas, glow_canvas)
    draw = ImageDraw.Draw(canvas)

    draw.text((x, y), cta_text, font=font, fill=cta_color, stroke_width=1, stroke_fill=(0,0,0,80))

    cta_dur = duration - appear_at
    clip = _create_image_clip(canvas, cta_dur)
    clip = apply_fade_in(clip, fade_duration=1.0)
    clip = clip.with_start(appear_at).with_position("center")
    return clip


def create_dim_overlay(duration, opacity=180):
    """Semi-transparent black overlay for text readability."""
    dim = Image.new('RGBA', (REEL_WIDTH, REEL_HEIGHT), (0, 0, 0, opacity))
    return _create_image_clip(dim, duration)


# ─── Fade-In Effect ─────────────────────────────────────────────────────────────

def apply_fade_in(clip, fade_duration=1.0):
    """Apply a smooth opacity fade-in to a clip."""
    def fade_mask(get_frame, t):
        if t < fade_duration:
            opacity = t / fade_duration
        else:
            opacity = 1.0
        frame = get_frame(t)
        return frame * opacity

    if clip.mask:
        clip = clip.with_mask(clip.mask.transform(fade_mask))
    return clip


# ─── Main Generator ─────────────────────────────────────────────────────────────

def create_cinematic_reel(
    hook_line: str,
    reflective_line: str,
    scene_query: str = "cinematic dark ocean",
    output_path: str = "cinematic_reel.mp4",
    trending_audio_path: str = None,
    video_index: int = 0,
) -> str:
    """
    Generate a premium cinematic motivational reel.

    Args:
        hook_line: Short punchy opening line
        reflective_line: Deeper follow-up line
        scene_query: Pexels search query for background
        output_path: Output video file path
        trending_audio_path: Path to background music

    Returns:
        Path to the generated video, or None on failure.
    """
    print(f"\n🎬 Creating Cinematic Reel...")
    print(f"   Hook:       '{hook_line}'")
    print(f"   Reflective: '{reflective_line}'")
    print(f"   Scene:      '{scene_query}'")

    # Clean text
    hook_line = _clean_text(hook_line) or "Stay patient. Stay strong."
    reflective_line = _clean_text(reflective_line) or "Your time is coming."

    # Duration: 7-10 seconds
    total_words = len(hook_line.split()) + len(reflective_line.split())
    duration = max(7.0, min(10.0, total_words * 0.4 + 4.0))
    print(f"   Duration:   {duration:.1f}s")

    # ── 1. Fetch Background Video ───────────────────────────────────────────
    bg_path = f"temp_cinematic_{uuid.uuid4().hex[:8]}.mp4"
    print(f"\n📥 Fetching cinematic background: '{scene_query}'...")

    if not fetch_pexels_video(scene_query, bg_path, use_local=False, result_index=video_index):
        print("[WARN] Primary query failed, trying diverse fallback...")
        fallback_queries = ["cinematic rainy street night", "cinematic foggy mountain", "cinematic lonely sunset", "cinematic dark forest"]
        fallback_query = random.choice(fallback_queries)
        if not fetch_pexels_video(fallback_query, bg_path, use_local=False, result_index=video_index):
            print("[ERROR] Could not fetch any background video. Aborting.")
            return None

    if not os.path.exists(bg_path) or os.path.getsize(bg_path) < 1000:
        print("[ERROR] Background video is invalid. Aborting.")
        return None

    # ── 2. Process Background Video ─────────────────────────────────────────
    try:
        print("\n🎨 Processing background video...")
        bg_clip = VideoFileClip(bg_path).without_audio()

        # Loop if too short
        if bg_clip.duration < duration:
            bg_clip = vfx.Loop(duration=duration).apply(bg_clip)
        else:
            bg_clip = bg_clip.subclipped(0, duration)

        # Fit to 1080x1920
        if bg_clip.size[0] / bg_clip.size[1] > REEL_WIDTH / REEL_HEIGHT:
            bg_clip = bg_clip.with_effects([vfx.Resize(height=REEL_HEIGHT)])
            bg_clip = bg_clip.with_effects([vfx.Crop(x_center=bg_clip.size[0] / 2, width=REEL_WIDTH)])
        else:
            bg_clip = bg_clip.with_effects([vfx.Resize(width=REEL_WIDTH)])
            bg_clip = bg_clip.with_effects([vfx.Crop(y_center=bg_clip.size[1] / 2, height=REEL_HEIGHT)])

        # Apply Ken Burns effect (randomized direction)
        print("   🔍 Applying Ken Burns effect...")
        bg_clip = apply_ken_burns_zoom(bg_clip, zoom_start=1.0, zoom_end=1.18)

        # Apply cinematic color grading (randomized preset)
        print("   🎨 Applying cinematic color grading...")
        bg_clip = apply_cinematic_grade(bg_clip)

    except Exception as e:
        print(f"[ERROR] Background processing failed: {e}")
        traceback.print_exc()
        return None

    # ── 3. Create Visual Effects Layers ─────────────────────────────────────
    print("\n✨ Building cinematic layers...")

    # Dim overlay — randomize opacity for visual variety
    dim_opacity = random.randint(140, 190)
    dim_layer = create_dim_overlay(duration, opacity=dim_opacity)
    print(f"   🌑 Dim overlay opacity: {dim_opacity}")

    # Vignette — randomize intensity
    vig_intensity = round(random.uniform(1.0, 1.4), 2)
    print(f"   🔲 Vignette intensity: {vig_intensity}")
    vignette_layer = create_vignette_overlay(duration, intensity=vig_intensity)

    # ── 4. Create Text Layers ───────────────────────────────────────────────
    print("\n✍️  Rendering typography...")

    # Output of create_text_overlay modified to return (clip, total_height)
    
    font_hook = _find_font(FONT_CANDIDATES_TYPEWRITER, 95)
    font_reflect = _find_font(FONT_CANDIDATES_TYPEWRITER, 85)

    # Hook line: appears at 0.2s, fast fade-in over 0.3s to hook viewer instantly
    hook_appear_at = 0.2
    hook_duration = duration - hook_appear_at
    hook_overlay, hook_height = create_text_overlay(
        hook_line, font_hook, y_center=720, duration=hook_duration, glow=True
    )
    hook_overlay = apply_fade_in(hook_overlay, fade_duration=0.3)
    hook_overlay = hook_overlay.with_start(hook_appear_at).with_position("center")

    # Reflective line: appears at 3.5s, fade-in over 1.0s
    # Dynamically place it at least 80px below the hook text block to prevent overlap
    reflect_appear_at = 3.5
    reflect_duration = duration - reflect_appear_at
    
    # Calculate safe starting Y for reflective text based on hook text height
    # Total height of the hook block is hook_height. But y_center was the center of it.
    hook_bottom = 720 + (hook_height // 2)
    
    # We want the reflect text to start below the hook_bottom 
    # Let's say we want 60px padding between the bottom of the hook and the top of the reflect text
    padding_between_blocks = 60
    
    # Calculate how tall the reflect text will be approximately so we can give it a centered y
    try:
        reflect_lines = _wrap_text(reflective_line, font_reflect, REEL_WIDTH - 160, ImageDraw.Draw(Image.new('RGBA', (1,1))))
        reflect_line_h = font_reflect.size + 16
        reflect_total_h = len(reflect_lines) * max(reflect_line_h, int(font_reflect.size * 1.5))
    except Exception:
        reflect_total_h = font_reflect.size * 3 # rough fallback
        
    # The new center for reflect text so its top is at hook_bottom + padding
    reflect_y_center = hook_bottom + padding_between_blocks + (reflect_total_h // 2)
    
    reflect_overlay, _ = create_text_overlay(
        reflective_line, font_reflect, y_center=reflect_y_center, duration=reflect_duration,
        glow=True, color=(220, 220, 220)
    )
    reflect_overlay = apply_fade_in(reflect_overlay, fade_duration=1.0)
    reflect_overlay = reflect_overlay.with_start(reflect_appear_at).with_position("center")

    # Watermark: always visible
    watermark_layer = create_watermark_overlay(duration)

    # CTA: "Send this to someone who needs it" — appears in last 3 seconds
    cta_appear_at = max(duration - 3.0, reflect_appear_at + 2.0)
    cta_layer = create_cta_overlay(duration, appear_at=cta_appear_at)
    print(f"   📩 CTA appears at {cta_appear_at:.1f}s")

    # ── 5. Composite All Layers ─────────────────────────────────────────────
    print("\n🎞️  Compositing layers...")
    layers = [
        bg_clip,
        dim_layer,
        vignette_layer,
        hook_overlay,
        reflect_overlay,
        cta_layer,
        watermark_layer,
    ]

    video = CompositeVideoClip(layers)

    # ── 6. Audio Mixing ─────────────────────────────────────────────────────
    if trending_audio_path and os.path.exists(trending_audio_path):
        try:
            print(f"\n🎵 Mixing audio: {os.path.basename(trending_audio_path)}...")
            audio = AudioFileClip(trending_audio_path)

            # Loop if needed
            if audio.duration < duration:
                repeats = int(duration // audio.duration) + 1
                audio = concatenate_audioclips([audio] * repeats).subclipped(0, duration)
            else:
                audio = audio.subclipped(0, duration)

            # Volume ducking: 30% so music doesn't overpower text
            audio = audio.with_effects([afx.MultiplyVolume(0.3)])

            video = video.with_audio(audio)
            print("   ✅ Audio mixed at 30% volume")
        except Exception as e:
            print(f"   [WARN] Audio mixing failed: {e}. Exporting without audio.")

    # ── 7. Export ────────────────────────────────────────────────────────────
    print(f"\n📤 Exporting to {output_path}...")
    try:
        video.fps = FPS
        video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=FPS,
            preset="fast",
            ffmpeg_params=["-pix_fmt", "yuv420p"],
        )
    except Exception as e:
        print(f"[ERROR] Export failed: {e}")
        traceback.print_exc()
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        output_path = None
    finally:
        # Cleanup
        try:
            video.close()
            bg_clip.close()
            del video, bg_clip
        except:
            pass

    # Wait for Windows file lock release
    time.sleep(1)

    # Cleanup temp background
    if os.path.exists(bg_path):
        try:
            os.remove(bg_path)
        except:
            pass

    # Validate output
    if output_path and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"\n✅ Cinematic reel saved: {output_path} ({size_mb:.1f} MB)")
        return output_path
    else:
        print("[ERROR] Output file is missing or too small.")
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        return None


# ─── Legacy Compatibility ───────────────────────────────────────────────────────
# Keep the old function name working for content_flood.py
create_enhanced_reel = create_cinematic_reel
create_reel = create_cinematic_reel


if __name__ == "__main__":
    result = create_cinematic_reel(
        hook_line="Some people are just chapters.",
        reflective_line="Not everyone deserves a place in your story forever.",
        scene_query="cinematic dark ocean",
        output_path="test_cinematic.mp4",
    )
    if result:
        print(f"Test reel: {result}")
