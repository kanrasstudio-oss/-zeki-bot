import os
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import requests

# Loglama ayarları
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Render Environment (Çevresel Değişkenler) üzerinden token ve anahtarları alıyoruz
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROK_API_KEY = os.getenv("GROK_API_KEY")

# xAI (Grok) API Endpoint
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

def ask_grok(prompt: str) -> str:
    """Grok API'ye istek atarak otonom asistan rolünde profesyonel yanıt alır."""
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "Sen Büşra'nın kişisel otonom iş asistanı ve operasyon yöneticisisin. "
        "Görevin; Büşra'nın işlerini büyütmek, analiz etmek, müşteri bulmak, stratejik öneriler sunmak "
        "ve mail/metin içerikleri hazırlamaktır. "
        "Sen karar almaz, planı ve taslağı hazırlar, Büşra'nın onayına sunarsın. "
        "Her yanıtında profesyonel, analitik, yönlendirici ve çözüm odaklı ol. "
        "İş süreçlerini adım adım planla ve uygulanabilir net çıktılar sun."
    )
    
    payload = {
        "model": "grok-beta",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(GROK_API_URL, json=payload, headers=headers, timeout=45)
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            logger.error(f"Grok API Hatası: {response.status_code} - {response.text}")
            return "Üzgünüm, şu an analiz yaparken bir API hatası oluştu."
    except Exception as e:
        logger.error(f"Bağlantı hatası: {e}")
        return f"Bağlantı hatası oluştu: {str(e)}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telegram'dan gelen komutları/istekleri işler ve Grok'a yönlendirir."""
    user_message = update.message.text
    user_name = update.effective_user.first_name
    
    logger.info(f"Komut alındı ({user_name}): {user_message}")
    
    # Kullanıcıya operasyonun başladığını bildirelim
    processing_msg = await update.message.reply_text("Strateji analiz ediliyor, plan hazırlanıyor...")
    
    # Grok'tan profesyonel yanıt al (Blocking isteği thread havuzunda çalıştırarak event loop'u bloklamıyoruz)
    loop = asyncio.get_running_loop()
    reply_text = await loop.run_in_executor(None, ask_grok, user_message)
    
    # Bildirim mesajını silip gerçek yanıtı iletelim
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
    await update.message.reply_text(reply_text)

async def main():
    if not TELEGRAM_TOKEN or not GROK_API_KEY:
        logger.error("TELEGRAM_TOKEN veya GROK_API_KEY tanımlanmamış! Lütfen Render Environment ayarlarını kontrol et.")
        return

    # Telegram Bot uygulamasını başlat
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Tüm metin mesajlarını yakala
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Otonom Asistan Bot başlatılıyor...")
    
    # Asenkron olarak botu başlat ve çalıştır
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # Botun kapanmaması için sonsuz döngü
    stop_signal = asyncio.Event()
    await stop_signal.wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot durduruldu.")
