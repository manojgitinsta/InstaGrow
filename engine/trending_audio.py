"""
Cinematic Audio Selector — Picks mood-appropriate instrumental tracks.
Defaults to soft, emotional, cinematic audio. No phonk or high-energy tracks.
"""

import os
import random

# Pre-loaded audio library (drop real .mp3 files into audio_lib/)
CINEMATIC_AUDIOS = {
    "ethereal_ambient_sad.mp3": ["heart", "breakup", "lonely", "alone", "unseen", "painful", "pain", "letting go", "moving on"],
    "dramatic_orchestra_hook.mp3": ["time", "regret", "journey", "mistakes", "past", "chance", "fight", "strength", "comeback"],
    "trending_lofi_beat.mp3": ["love", "peace", "beautiful", "soul", "joy", "patience", "calm", "self respect"],
}

# Default for all cinematic reels
DEFAULT_TRACK = "ethereal_ambient_sad.mp3"


def ensure_audio_exists():
    """Creates the audio_lib folder and downloads a sample if needed."""
    audio_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "audio_lib")
    os.makedirs(audio_dir, exist_ok=True)
    sample_path = os.path.join(audio_dir, "sample.mp3")
    if not os.path.exists(sample_path):
        import urllib.request
        sample_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
        try:
            print("   Downloading sample audio for testing...")
            urllib.request.urlretrieve(sample_url, sample_path)
        except Exception as e:
            print(f"   [WARN] Failed to download sample: {e}")
            return

    import shutil
    audio_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "audio_dir")
    for audio in CINEMATIC_AUDIOS:
        path = os.path.join(audio_dir, audio)
        if not os.path.exists(path):
            try:
                shutil.copy(sample_path, path)
            except Exception as e:
                print(f"   [WARN] Failed to copy {audio}: {e}")


def get_cinematic_audio(quote_text=""):
    """
    Select the most appropriate cinematic audio track based on quote keywords.
    Always returns a soft, emotional track — never phonk or high-energy.
    """
    ensure_audio_exists()
    quote_lower = quote_text.lower()

    audio_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "audio_lib")
    for track, keywords in CINEMATIC_AUDIOS.items():
        if any(word in quote_lower for word in keywords):
            path = os.path.join(audio_dir, track)
            if os.path.exists(path):
                print(f"   🎵 Matched audio: {track}")
                return path

    # Default to ambient/sad for cinematic mood
    audio_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "audio_lib")
    path = os.path.join(audio_dir, DEFAULT_TRACK)
    if os.path.exists(path):
        print(f"   🎵 Default cinematic audio: {DEFAULT_TRACK}")
        return path

    return None


# Legacy compatibility
get_contextual_trending_audio = get_cinematic_audio


if __name__ == "__main__":
    print(get_cinematic_audio("I feel so unseen and lonely"))
    print(get_cinematic_audio("Keep fighting for yourself"))
    print(get_cinematic_audio("Just a random thought"))
