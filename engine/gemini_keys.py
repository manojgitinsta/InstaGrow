"""
Gemini API Key Rotator — Distributes requests across multiple API keys.
═══════════════════════════════════════════════════════════════════════════════════
Reads GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3 from .env.
Automatically rotates to the next key when one hits a rate limit.
"""

import os
import random
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def get_all_keys():
    """Collect all valid Gemini API keys from .env."""
    keys = []
    for var in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
        key = os.getenv(var, "").strip()
        if key and key != "YOUR_KEY_HERE":
            keys.append(key)
    return keys


def get_gemini_client(preferred_index=None):
    """
    Returns a Gemini client using one of the available API keys.
    Rotates keys to distribute load.

    Args:
        preferred_index: Specific key index to use (0, 1, 2). If None, picks randomly.

    Returns:
        (client, api_key) tuple, or (None, None) if no keys available.
    """
    from google import genai

    keys = get_all_keys()
    if not keys:
        print("[ERROR] No Gemini API keys found in .env!")
        return None, None

    if preferred_index is not None and preferred_index < len(keys):
        key = keys[preferred_index]
    else:
        key = random.choice(keys)

    client = genai.Client(api_key=key)
    return client, key


def generate_with_rotation(prompt, temperature=0.8, models=None):
    """
    Generate content with automatic key rotation on rate limit errors.

    Tries each API key with each model, with retries and backoff.

    Args:
        prompt: The prompt string
        temperature: Generation temperature
        models: List of model names to try (default: ['gemini-2.0-flash', 'gemini-1.5-flash-latest'])

    Returns:
        Raw response text, or None on total failure.
    """
    import time
    from google import genai
    from google.genai import types

    if models is None:
        models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.5-flash-lite', 'gemini-2.0-flash-lite']

    keys = get_all_keys()
    if not keys:
        print("[ERROR] No Gemini API keys configured!")
        return None

    for model_name in models:
        for key_idx, key in enumerate(keys):
            key_label = f"Key {key_idx + 1}/{len(keys)}"

            for attempt in range(2):  # 2 attempts per key
                try:
                    if attempt > 0:
                        wait = 20
                        print(f"   [RETRY] {key_label} -> {model_name}, waiting {wait}s...")
                        time.sleep(wait)

                    print(f"[AI] {key_label} -> {model_name}...")
                    client = genai.Client(api_key=key)
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=temperature),
                    )

                    raw = response.text.strip()
                    # Clean markdown wrappers
                    if raw.startswith("```json"):
                        raw = raw[7:]
                    if raw.startswith("```"):
                        raw = raw[3:]
                    if raw.endswith("```"):
                        raw = raw[:-3]

                    print(f"   [OK] Success via {key_label} -> {model_name}")
                    return raw.strip()

                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        print(f"   [RATE LIMIT] {key_label} -> {model_name} exhausted")
                        continue  # Try next attempt or key
                    else:
                        print(f"   [ERROR] {key_label} -> {model_name}: {e}")
                        break  # Non-rate-limit error, skip this key for this model

        print(f"   [WARN] All keys exhausted for {model_name}")

    print("[ERROR] All API keys and models exhausted!")
    return None


if __name__ == "__main__":
    keys = get_all_keys()
    print(f"Found {len(keys)} Gemini API key(s) configured.")
    for i, k in enumerate(keys):
        print(f"  Key {i + 1}: {k[:12]}...{k[-4:]}")
