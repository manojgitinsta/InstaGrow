import os
import sys
import requests
from dotenv import load_dotenv

# Ensure Windows console handles emojis
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

def send_telegram_report(results_dict):
    """
    Sends a beautifully formatted daily report to a private Telegram chat.
    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        return False
        
    # Build the report message
    lines = ["🤖 *InstaGrow Cloud Report*"]
    lines.append("──────────────────────")
    
    all_success = True
    for job, success in results_dict.items():
        if not success:
            all_success = False
        status = "✅ Success" if success else "❌ FAILED"
        lines.append(f"• *{job.upper()}*: {status}")
        
    lines.append("──────────────────────")
    if all_success:
        lines.append("🎉 All systems operational.")
    else:
        lines.append("⚠️ Immediate Attention Required on Server.")
        
    message = "\n".join(lines)
    
    # Send via native Telegram API
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("   ✈️ Telegram report sent successfully!")
            return True
        else:
            print(f"   ⚠️ Telegram API rejected request: {response.text}")
            return False
    except Exception as e:
        print(f"   ⚠️ Telegram API error: {e}")
        return False


def send_telegram_video(video_path, caption=""):
    """
    Sends a video file (reel) to Telegram chat for manual review before posting.
    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("   ⚠️ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")
        return False

    if not os.path.exists(video_path):
        print(f"   ❌ Video file not found: {video_path}")
        return False

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"   📤 Sending reel to Telegram ({file_size_mb:.1f} MB)...")

    # Telegram Bot API supports videos up to 50MB via multipart upload
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"

    # Truncate caption to Telegram's 1024 char limit for video captions
    if len(caption) > 1024:
        caption = caption[:1020] + "..."

    try:
        with open(video_path, 'rb') as f:
            response = requests.post(
                url,
                data={
                    "chat_id": chat_id,
                    "caption": f"🎬 *New Reel Ready for Review*\n\n{caption}",
                    "parse_mode": "Markdown",
                },
                files={"video": (os.path.basename(video_path), f, "video/mp4")},
                timeout=300,  # 5 min timeout for large videos
            )

        if response.status_code == 200:
            print("   ✅ Reel sent to Telegram successfully!")
            return True
        else:
            print(f"   ⚠️ Telegram video upload failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Telegram video send error: {e}")
        return False

# Quick test via CLI
if __name__ == "__main__":
    test_data = {"Morning Story": True, "Afternoon Carousel": False}
    print("Sending test report...")
    if not send_telegram_report(test_data):
        print("   ❌ Test failed. Please check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
