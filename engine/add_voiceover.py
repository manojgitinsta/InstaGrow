import asyncio
import edge_tts

async def generate_voiceover(text, output_file="voiceover.mp3", voice="en-US-ChristopherNeural"):
    """
    Generates an MP3 voiceover from text using Microsoft Edge TTS (FREE).
    Voices:
    - en-US-ChristopherNeural (Male) - Great for motivation
    - en-US-AriaNeural (Female)
    - en-GB-SoniaNeural (British)
    """
    print(f"🎙️ Generating Free AI Voiceover ({voice})...")
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        print(f"✅ Voiceover saved to {output_file}")
        return output_file
    except Exception as e:
        print(f"❌ Error generating voiceover: {e}")
        return None

def create_voiceover(text, output_file="voiceover.mp3"):
    """
    Wrapper to run the async function synchronously.
    """
    try:
        asyncio.run(generate_voiceover(text, output_file))
        return output_file
    except Exception as e:
        print(f"Sync wrapper error: {e}")
        return None

if __name__ == "__main__":
    create_voiceover("This is a test of the free Edge TTS system.", "test_voice.mp3")
