import time
import requests

# بيانات البوت سنضعها هنا لاحقًا
TELEGRAM_BOT_TOKEN = "PUT_YOUR_TELEGRAM_TOKEN_HERE"
CHAT_ID = "PUT_YOUR_CHAT_ID_HERE"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": message
    })

while True:
    send_telegram("🟡 فحص حالة طلب الفيزا...")
    time.sleep(60)
