import os
import requests
import urllib.parse
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

def send_whatsapp_report(results_dict):
    """
    Sends a WhatsApp message using the free CallMeBot API.
    Requires WHATSAPP_PHONE and WHATSAPP_API_KEY in .env
    """
    phone = os.getenv("WHATSAPP_PHONE")
    api_key = os.getenv("WHATSAPP_API_KEY")
    
    if not phone or not api_key:
        return False
        
    # Build the report message
    lines = ["🤖 *InstaGrow Cloud Report*"]
    lines.append("=====================")
    
    all_success = True
    for job, success in results_dict.items():
        if not success:
            all_success = False
        status = "✅ Success" if success else "❌ FAILED"
        lines.append(f"• {job.upper()}: {status}")
        
    lines.append("=====================")
    if all_success:
        lines.append("🎉 All systems operational.")
    else:
        lines.append("⚠️ Attention required on server.")
        
    message = "\n".join(lines)
    
    # Send via CallMeBot API
    try:
        encoded_message = urllib.parse.quote(message)
        url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_message}&apikey={api_key}"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("   📱 WhatsApp report sent successfully!")
            return True
        else:
            print(f"   ⚠️ WhatsApp API rejected request: {response.text}")
            return False
    except Exception as e:
        print(f"   ⚠️ WhatsApp API error: {e}")
        return False

# Quick test via CLI
if __name__ == "__main__":
    test_data = {"Morning Story": True, "Afternoon Carousel": False}
    print("Sending test report...")
    send_whatsapp_report(test_data)
