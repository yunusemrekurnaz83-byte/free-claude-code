import os
import sys

print("Sistem kontrol ediliyor ve eksik kütüphaneler kuruluyor...")
os.system("pip install pyTelegramBotAPI tradingview-ta requests")

import telebot
import requests
from tradingview_ta import TA_Handler, Interval

TOKEN = os.environ.get("EMRE_BOT_TOKEN")
if not TOKEN:
    print("HATA: EMRE_BOT_TOKEN bulunamadı!")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)

def ai_yorumla(mesaj, sistem_mesaji="Sen Emre AI'sın. Üst düzey finans ve kripto analistisin. Kısa, havalı ve net konuşursun."):
    motorlar = [
        ("GROQ", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "llama-3.1-8b-instant"),
        ("DEEPSEEK", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat"),
        ("MISTRAL", "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "mistral-tiny"),
        ("XAI", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY", "grok-beta"),
        ("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_NIM_API_KEY", "meta/llama3-8b-instruct")
    ]
    
    # Motorları sırayla dene
    for isim, url, env_adi, model in motorlar:
        api_key = os.environ.get(env_adi)
        if not api_key: continue
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": model,
                "messages": [{"role": "system", "content": sistem_mesaji}, 
                             {"role": "user", "content": mesaj}]
            }
            resp = requests.post(url, headers=headers, json=data, timeout=7)
            if resp.status_code == 200:
                return f"⚡ [{isim}] " + resp.json()["choices"][0]["message"]["content"]
        except:
            continue # Hata verirse sessizce diğerine geç
    
    # Son Çare: GEMINI
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            data = {"contents": [{"parts": [{"text": sistem_mesaji + "\n\nKullanıcı Mesajı: " + mesaj}]}]}
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=10)
            if resp.status_code == 200:
                return "🧠 [GEMINI] " + resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except:
            pass
            
    return "❌ Zeka Motorları Çöktü! API Kotan dolmuş veya şifreler eksik olabilir."

@bot.message_handler(commands=['start'])
def ana_menu(message):
    bot.reply_to(message, "👑 EMRE AI: 6 MOTORLU PROFESYONEL ANALİZ AĞI AKTİF!\n\n- Sohbet etmek için direkt yazabilirsin.\n- Detaylı canlı analiz için: /analiz BTCUSD")

@bot.message_handler(commands=['analiz'])
def tv_analiz(message):
    komut = message.text.split()
    if len(komut) < 2:
        bot.reply_to(message, "Kral hangi coini inceleyeyim? Örnek: /analiz BTCUSD")
        return

    coin = komut[1].upper()
    mesaj_giden = bot.reply_to(message, f"📡 TradingView'den {coin} için 10+ profesyonel indikatör çekiliyor...")

    try:
        handler = TA_Handler(
            symbol=coin,
            screener="crypto",
            exchange="BINANCE",
            interval=Interval.INTERVAL_1_DAY
        )
        analiz = handler.get_analysis()
        ind = analiz.indicators
        
        # Devasa İndikatör Ordusu
        tavsiye = analiz.summary["RECOMMENDATION"]
        rsi = round(ind.get("RSI", 0), 2)
        macd = round(ind.get("MACD.macd", 0), 2)
        ema20 = round(ind.get("EMA20", 0), 2)
        sma50 = round(ind.get("SMA50", 0), 2)
        sma200 = round(ind.get("SMA200", 0), 2)
        adx = round(ind.get("ADX", 0), 2)
        stoch_k = round(ind.get("Stoch.K", 0), 2)
        
        # Yapay Zekaya Gönderilecek Özel Analist Emri
        ai_istek = f"""Aşağıdaki TradingView verileriyle profesyonel bir teknik analiz yap:
        Varlık: {coin} | Genel Sinyal: {tavsiye}
        RSI (Şişkinlik): {rsi} | MACD (Momentum): {macd} 
        ADX (Trend Gücü): {adx} | Stoch(K): {stoch_k}
        Hareketli Ortalamalar -> EMA20: {ema20} | SMA50: {sma50} | SMA200: {sma200}
        
        Lütfen 3 maddede: 
        1) İndikatörlerin uyumunu veya zıtlığını açıkla.
        2) Kısa ve orta vadeli yön beklentini söyle.
        3) Yatırımcı için strateji ve risk durumu ver."""
        
        bot.edit_message_text(f"🧠 Veriler toplandı! 6 Motorlu zeka ağı grafik okuyor...", chat_id=message.chat.id, message_id=mesaj_giden.message_id)
        
        sistem_msg = "Sen Wall Street seviyesinde usta bir teknik analistisin. Verileri en iyi sen yorumlarsın. Destan yazma, nokta atışı ve vurucu ol."
        ai_yorumu = ai_yorumla(ai_istek, sistem_msg)
        
        # Telegrama Şık Sunum
        sonuc = f"📊 **PRO TRADINGVIEW ANALİZİ: {coin}**\n\n"
        sonuc += f"📈 **Sinyal:** `{tavsiye}`\n"
        sonuc += f"🌊 **Trend Gücü (ADX):** `{adx}`\n"
        sonuc += f"⚡ **RSI:** `{rsi}` | **MACD:** `{macd}`\n"
        sonuc += f"🎯 **SMA50:** `{sma50}` | **SMA200:** `{sma200}`\n\n"
        sonuc += f"🤖 **EMRE AI YORUMU:**\n{ai_yorumu}"
        
        # Markdown hatalarını önlemek için parse_mode olmadan yollamayı deniyoruz (AI bazen bozuk markdown atar)
        try:
            bot.edit_message_text(sonuc, chat_id=message.chat.id, message_id=mesaj_giden.message_id, parse_mode="Markdown")
        except:
            bot.edit_message_text(sonuc, chat_id=message.chat.id, message_id=mesaj_giden.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ TV Hatası: {e}\n(Coin adını kontrol et, örn: BTCUSD)", chat_id=message.chat.id, message_id=mesaj_giden.message_id)

@bot.message_handler(func=lambda message: True)
def serbest_sohbet(message):
    mesaj_giden = bot.reply_to(message, "🧠 Emre AI Düşünüyor...")
    yanit = ai_yorumla(message.text)
    
    try:
        bot.edit_message_text(yanit, chat_id=message.chat.id, message_id=mesaj_giden.message_id, parse_mode="Markdown")
    except:
        bot.edit_message_text(yanit, chat_id=message.chat.id, message_id=mesaj_giden.message_id)

print("Emre AI Pro Sürüm Aktif!")
bot.infinity_polling(timeout=10, long_polling_timeout=5)
