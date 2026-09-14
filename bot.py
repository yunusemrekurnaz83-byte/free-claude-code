,import telebot
import os
import requests
from tradingview_ta import TA_Handler, Interval

# ŞİFRELER
TOKEN = os.environ.get("EMRE_BOT_TOKEN") 
GROQ_KEY = os.environ.get("GROQ_API_KEY")
bot = telebot.TeleBot(TOKEN)

# SADECE GROQ KULLANIYORUZ (Şimşek hızında)
def ai_yorumla(gercek_veri):
    if not GROQ_KEY: return "❌ Groq şifresi eksik!"
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
        # Yapay zekaya sadece gerçek veriyi yorumlamasını emrediyoruz
        prompt = f"Sen usta bir kripto analistisin. Şu anki canlı TradingView verilerini yorumla. Başka bir şey uydurma. Veri: {gercek_veri}"
        data = {
            "model": "llama3-8b-8192", 
            "messages": [{"role": "user", "content": prompt}]
        }
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Zeka Çöktü: {e}"

@bot.message_handler(commands=['start'])
def ana_menu(message):
    bot.reply_to(message, "👑 EMRE AI: TRADINGVIEW BAĞLANTISI AKTİF!\n\nCanlı analiz için yaz:\n/analiz BTCUSD\n/analiz ETHUSD")

# 📈 TRADINGVIEW CANLI VERİ ÇEKİCİ
@bot.message_handler(commands=['analiz'])
def tv_analiz(message):
    komut = message.text.split()
    if len(komut) < 2:
        bot.reply_to(message, "Kral hangi coini inceleyeyim? Örnek: /analiz BTCUSD")
        return

    coin = komut[1].upper()
    mesaj = bot.reply_to(message, f"📡 TradingView'den {coin} canlı verileri çekiliyor...")

    try:
        # TradingView'e bağlan (Günlük Grafik, Binance Borsası)
        handler = TA_Handler(
            symbol=coin,
            screener="crypto",
            exchange="BINANCE",
            interval=Interval.INTERVAL_1_DAY
        )
        
        analiz = handler.get_analysis()
        
        # O saniyelik gerçek veriler
        tavsiye = analiz.summary["RECOMMENDATION"]
        rsi = round(analiz.indicators["RSI"], 2)
        macd = round(analiz.indicators["MACD.macd"], 2)
        
        veri_ozeti = f"Coin: {coin}\nTV Genel Kararı: {tavsiye}\nRSI: {rsi}\nMACD: {macd}"
        
        # Gerçek veriyi AI'a gönderip yorumlatıyoruz
        bot.edit_message_text(f"🧠 Veri geldi, Emre AI yorumluyor...", chat_id=message.chat.id, message_id=mesaj.message_id)
        ai_yorumu = ai_yorumla(veri_ozeti)
        
        # Sonucu Telegram'a yolla
        sonuc = f"📊 **TRADINGVIEW CANLI RAPOR: {coin}**\n\n"
        sonuc += f"🔹 **Sinyal:** {tavsiye}\n"
        sonuc += f"🔹 **RSI:** {rsi}\n"
        sonuc += f"🔹 **MACD:** {macd}\n\n"
        sonuc += f"🧠 **Emre AI Yorumu:**\n{ai_yorumu}"
        
        bot.edit_message_text(sonuc, chat_id=message.chat.id, message_id=mesaj.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.edit_message_text(f"❌ TradingView Hatası: Bu coin bulunamadı veya borsa yanlış. Hata: {e}", chat_id=message.chat.id, message_id=mesaj.message_id)

print("Emre AI TradingView Modülüyle Başladı!")
bot.infinity_polling(timeout=10, long_polling_timeout=5)
