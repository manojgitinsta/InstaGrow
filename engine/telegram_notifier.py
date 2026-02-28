import os
import requests
from dotenv import load_dotenv

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

# Quick test via CLI
if __name__ == "__main__":
    test_data = {"Morning Story": True, "Afternoon Carousel": False}
    print("Sending test report...")
    send_telegram_report(test_data)
