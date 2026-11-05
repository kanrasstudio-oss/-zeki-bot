import os
import json
import logging
import re
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from openai import OpenAI

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
GROK_KEY = os.getenv("GROK_API_KEY")
MEMORY_FILE = "memory.json"

grok_client = None
if GROK_KEY:
    try:
        grok_client = OpenAI(api_key=GROK_KEY, base_url="https://api.x.ai/v1")
        logger.info("Grok baglandi.")
    except Exception as e:
        logger.error(f"Grok baglanamadi: {e}")

def hafizayi_oku():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "kullanici_bilgisi" not in data:
                data["kullanici_bilgisi"] = {}
            if "konusmalar" not in data:
                data["konusmalar"] = []
            if "ogrenilenler" not in data:
                data["ogrenilenler"] = []
            if "hedefler" not in data:
                data["hedefler"] = []
            if "notlar" not in data:
                data["notlar"] = []
            return data
    except:
        return {"kullanici_bilgisi": {}, "konusmalar": [], "ogrenilenler": [], "hedefler": [], "notlar": []}

def hafizaya_yaz(data):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Hafiza hatasi: {e}")

hafiza = hafizayi_oku()

def hafiza_ozeti():
    ad = hafiza["kullanici_bilgisi"].get("ad", "bilinmiyor")
    bilgiler = hafiza["kullanici_bilgisi"]
    ogr = hafiza["ogrenilenler"][-10:]
    son_konusma = hafiza["konusmalar"][-5:]
    return f"Ad: {ad}, Bilgiler: {bilgiler}, Ogrendikleri: {ogr}, Son konusmalar: {son_konusma}"

def akilli_ogren(mesaj):
    alt = mesaj.lower().strip()
    m = re.search(r'adım\s+([a-zçğıöşü]+)', alt)
    if m:
        hafiza["kullanici_bilgisi"]["ad"] = m.group(1).capitalize()
        hafizaya_yaz(hafiza)
    if "seviyorum" in alt or "severim" in alt or "bayılıyorum" in alt:
        if mesaj not in hafiza["ogrenilenler"]:
            hafiza["ogrenilenler"].append(mesaj)
            hafiza["ogrenilenler"] = hafiza["ogrenilenler"][-100:]
            hafizaya_yaz(hafiza)
    if "hedefim" in alt or "istiyorum" in alt:
        if mesaj not in hafiza["hedefler"]:
            hafiza["hedefler"].append(mesaj)
            hafizaya_yaz(hafiza)
    if alt.startswith("not et") or alt.startswith("hatırla") or alt.startswith("kaydet"):
        not_metni = mesaj.replace("not et", "").replace("hatırla", "").replace("kaydet", "").strip()
        if not_metni:
            hafiza["notlar"].append({"zaman": datetime.now().isoformat(), "not": not_metni})
            hafizaya_yaz(hafiza)
            return "not"
    return True

def grok_cevap(mesaj):
    if not grok_client:
        return None
    try:
        ozet = hafiza_ozeti()
        response = grok_client.chat.completions.create(
            model="grok-3-mini",
            messages=[
                {"role": "system", "content": f"Sen kullanicinin en yakin, zeki, samimi asistanisin. Turkce konus, kisa ve dogal ol, robot gibi konusma. Kullanici hakkinda bildiklerin: {ozet} Adini biliyorsan kullan. Asla uydurma, bilmiyorsan bunu tam bilmiyorum de."},
                {"role": "user", "content": mesaj}
            ],
            max_tokens=600,
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Grok hatasi: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad = hafiza["kullanici_bilgisi"].get("ad", "")
    if ad:
        await update.message.reply_text(f"Hos geldin {ad}! Seni hatirliyorum. Grok da acik, ne istersen sor.")
    else:
        await update.message.reply_text("Selam! Ben senin zeki asistaninim. Hafizam var + Grok zekasi var. Adin ne?")

async def hafiza_goster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad = hafiza["kullanici_bilgisi"].get("ad", "henuz bilmiyorum")
    notlar = hafiza["notlar"][-5:]
    mesaj = f"Hafizamda bunlar var:\n\nAdin: {ad}\nOgrendiklerim: {len(hafiza['ogrenilenler'])} sey\nHedeflerin: {len(hafiza['hedefler'])} tane\nNotlarin: {len(hafiza['notlar'])} tane\n\nSon notlarin:\n"
    for n in notlar:
        mesaj += f"- {n['not']}\n"
    await update.message.reply_text(mesaj)

async def sifirla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global hafiza
    hafiza = {"kullanici_bilgisi": {}, "konusmalar": [], "ogrenilenler": [], "hedefler": [], "notlar": []}
    hafizaya_yaz(hafiza)
    await update.message.reply_text("Hafizayi sifirladim. Yeniden tanisalim, adin ne?")

async def cevapla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return
        mesaj = update.message.text.strip()
        if not mesaj:
            return
        hafiza["konusmalar"].append({"zaman": datetime.now().isoformat(), "mesaj": mesaj})
        hafiza["konusmalar"] = hafiza["konusmalar"][-200:]
        sonuc = akilli_ogren(mesaj)
        if sonuc == "not":
            await update.message.reply_text("Not ettim, unutmayacagim.")
            return
        hafizaya_yaz(hafiza)
        alt = mesaj.lower()
        if alt in ["/hafiza", "hafizamda ne var", "ne hatirliyorsun"]:
            await hafiza_goster(update, context)
            return
        cevap = grok_cevap(mesaj)
        if not cevap:
            ad = hafiza["kullanici_bilgisi"].get("ad", "")
            if "nasilsin" in alt:
                cevap = f"Iyiyim {ad}, sen nasilsin?" if ad else "Iyiyim, sen nasilsin?"
            elif "selam" in alt or "merhaba" in alt:
                cevap = f"Selam {ad}!" if ad else "Selam!"
            else:
                cevap = "Anladim, hafizama ekledim. Grok'a su an ulasamiyorum ama ben buradayim."
        await update.message.reply_text(cevap)
    except Exception as e:
        logger.error(f"Cevap hatasi: {e}")
        try:
            await update.message.reply_text("Kucuk bir takilma oldu ama buradayim, tekrar yazar misin?")
        except:
            pass

def main():
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN yok! Render Env'e ekle.")
        return
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hafiza", hafiza_goster))
    app.add_handler(CommandHandler("sifirla", sifirla))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cevapla))
    logger.info("Bot + Grok calisiyor...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
