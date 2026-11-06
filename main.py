import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import requests

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
GROK_KEY = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Selam! Ben Zeki Botum 😎\nBana bir şey sor, Grok ile cevaplayayım.")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not GROK_KEY:
        await update.message.reply_text("Grok anahtarı eklenmemiş, ama ben buradayım: " + user_text)
        return
    try:
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROK_KEY}", "Content-Type": "application/json"},
            json={
                "model": "grok-beta",
                "messages": [
                    {"role": "system", "content": "Sen Zeki Botum adında yardımsever, esprili bir asistansın. Türkçe cevap ver."},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.7
            },
            timeout=30
        )
        data = r.json()
        cevap = data["choices"][0]["message"]["content"]
        await update.message.reply_text(cevap)
    except Exception as e:
        print("Hata:", e)
        await update.message.reply_text("Bir hata oldu, tekrar dener misin?")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("HATA: BOT_TOKEN yok! Render Environment'a ekle.")
    else:
        print("Zeki Botum calisiyor...")
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
        app.run_polling()
