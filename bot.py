import os
import sys

print("Sistem kontrol ediliyor...")
os.system("pip install pyTelegramBotAPI tradingview-ta requests")

import telebot
import requests
from tradingview_ta import TA_Handler, Interval

TOKEN = os.environ.get("EMRE_BOT_TOKEN")
if not TOKEN:
    print("HATA: EMRE_BOT_TOKEN bulunamadı!")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)

def ai_yorumla(mesaj):
    # Motorları en hızlı ve stabil olandan başlayarak sıraya diziyoruz
    motorlar = [
        ("DEEPSEEK", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat"),
        ("MISTRAL", "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "mistral-tiny"),
        ("GROQ", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "llama-3.1-8b-instant"),
        ("XAI", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY", "grok-beta"),
        ("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_NIM_API_KEY", "meta/llama3-8b-instruct")
    ]
    
    for isim, url, env_adi, model in motorlar:
        api_key = os.environ.get(env_adi)
        if not api_key: continue
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": model,
                "messages": [{"role": "system", "content": "Sen usta kripto analistisin. Gelen veriyi kısa ve çok net yorumla."}, 
                             {"role": "user", "content": mesaj}]
            }
            resp = requests.post(url, headers=headers, json=data, timeout=7)
            if resp.status_code == 200:
                return f"⚡ [{isim}] " + resp.json()["choices"][0]["message"]["content"]
        except:
            continue # Hata verirse diğer motora geç
    
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            data = {"contents": [{"parts": [{"text": "Usta kripto analisti olarak veriyi net yorumla: " + mesaj}]}]}
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=10)
            if resp.status_code == 200:
                return "🧠 [GEMINI] " + resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except:
            pass
            
    return "❌ Zeka Motorları Çöktü! API Kotan dolmuş olabilir."

@bot.message_handler(commands=['start'])
def ana_menu(message):
    bot.reply_to(message, "👑 EMRE AI: 6 MOTORLU TRADINGVIEW AĞI AKTİF!\n\nAnaliz için yaz:\n/analiz BTCUSD")

@bot.message_handler(commands=['analiz'])
def tv_analiz(message):
    komut = message.text.split()
    if len(komut) < 2:
        bot.reply_to(message, "Kral hangi coini inceleyeyim? Örnek: /analiz BTCUSD")
        return

    coin = komut[1].upper()
    mesaj_giden = bot.reply_to(message, f"📡 TradingView'den {coin} canlı verileri çekiliyor...")

    try:
        handler = TA_Handler(
            symbol=coin,
            screener="crypto",
            exchange="BINANCE",
            interval=Interval.INTERVAL_1_DAY
        )
        analiz = handler.get_analysis()
        
        tavsiye = analiz.summary["RECOMMENDATION"]
        rsi = round(analiz.indicators["RSI"], 2)
        macd = round(analiz.indicators["MACD.macd"], 2)
        
        veri_ozeti = f"Coin: {coin} | Sinyal: {tavsiye} | RSI: {rsi} | MACD: {macd}"
        
        bot.edit_message_text(f"🧠 Veri geldi! 6 Motorlu zeka ağı en hızlısını arıyor...", chat_id=message.chat.id, message_id=mesaj_giden.message_id)
        ai_yorumu = ai_yorumla(veri_ozeti)
        
        sonuc = f"📊 **TRADINGVIEW CANLI: {coin}**\n\n"
        sonuc += f"🔹 **TV Sinyali:** {tavsiye}\n"
        sonuc += f"🔹 **RSI:** {rsi}\n"
        sonuc += f"🔹 **MACD:** {macd}\n\n"
        sonuc += f"{ai_yorumu}"
        
        bot.edit_message_text(sonuc, chat_id=message.chat.id, message_id=mesaj_giden.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.edit_message_text(f"❌ TV Hatası: {e}", chat_id=message.chat.id, message_id=mesaj_giden.message_id)

@bot.message_handler(func=lambda message: True)
def bos_mesaj_yakala(message):
    bot.reply_to(message, "Kral, otonom sistemdeyiz. Sadece /analiz BTCUSD komutunu kullan.")

print("Emre AI 6 Motorlu TradingView Modülüyle Başladı!")
bot.infinity_polling(timeout=10, long_polling_timeout=5)
