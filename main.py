import os
import requests
from flask import Flask, request
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
GROK_KEY = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")

app = Flask(__name__)
bot_app = Application.builder().token(BOT_TOKEN).build()

async def start(update, context):
    await update.message.reply_text("Selam! Ben Zeki Botum 😎\nBana bir şey sor, Grok ile cevaplayayım.")

async def chat(update, context):
    text = update.message.text
    if not GROK_KEY:
        await update.message.reply_text("Buradayım: " + text)
        return
    try:
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROK_KEY}", "Content-Type": "application/json"},
            json={
                "model": "grok-beta",
                "messages": [
                    {"role": "system", "content": "Sen Zeki Botum adında yardımsever, esprili bir asistansın. Türkçe cevap ver."},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.7
            },
            timeout=30
        )
        cevap = r.json()["choices"][0]["message"]["content"]
        await update.message.reply_text(cevap)
    except Exception as e:
        print("Hata:", e)
        await update.message.reply_text("Bir hata oldu, tekrar dener misin?")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

@app.route("/")
def home():
    return "Zeki Botum calisiyor!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return "ok"

@app.route("/setwebhook")
def setwebhook():
    # Render adresin neyse onu buraya yazacaksın
    base_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not base_url:
        return "RENDER_EXTERNAL_URL yok"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={base_url}/webhook"
    r = requests.get(url)
    return r.text

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
