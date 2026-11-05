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

# Render Environment üzerinden token ve anahtarları alıyoruz
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROK_API_KEY")  # Render'da anahtarı GROK_API_KEY olarak kaydettiğin için buradan okuyoruz

# Groq API Endpoint ve Güncel Modeli
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def ask_groq(prompt: str) -> str:
    """Groq API'ye istek atarak otonom asistan rolünde yanıt alır."""
    if not GROQ_API_KEY:
        return "Hata: GROK_API_KEY Render Environment içerisinde tanımlı değil!"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "Sen Büşra'nın kişisel otonom iş asistanı ve operasyon yöneticisisin. "
        "Görevin; Büşra'nın işlerini büyütmek, analiz etmek, müşteri bulmak, stratejik öneriler sunmak "
        "ve mail/metin içerikleri hazırlamaktır. "
        "Sen karar almaz, planı ve taslağı hazırlar, Büşra'nın onayına sunarsın. "
        "Her yanıtında profesyonel, analitik, yönlendirici ve çözüm odaklı ol."
    )
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=45)
        logger.info(f"Groq API Yanıt Kodu: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            return f"API Hatası (Kod {response.status_code}): {response.text}"
    except Exception as e:
        logger.error(f"Bağlantı hatası: {e}")
        return f"Bağlantı hatası oluştu: {str(e)}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telegram'dan gelen mesajları işler ve Groq'a yönlendirir."""
    user_message = update.message.text
    user_name = update.effective_user.first_name
    
    logger.info(f"Komut alındı ({user_name}): {user_message}")
    
    processing_msg = await update.message.reply_text("Strateji analiz ediliyor, plan hazırlanıyor...")
    
    loop = asyncio.get_running_loop()
    reply_text = await loop.run_in_executor(None, ask_groq, user_message)
    
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
    await update.message.reply_text(reply_text)

async def main():
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        logger.error("TELEGRAM_TOKEN veya GROK_API_KEY tanımlanmamış!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Otonom Asistan Bot başlatılıyor...")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    stop_signal = asyncio.Event()
    await stop_signal.wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot durduruldu.")
