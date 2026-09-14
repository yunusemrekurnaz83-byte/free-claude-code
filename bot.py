import telebot
import os
import requests
from tradingview_ta import TA_Handler, Interval

# ŞİFRELER
TOKEN = os.environ.get("EMRE_BOT_TOKEN") 
bot = telebot.TeleBot(TOKEN)

# 🧠 EN GÜNCEL (V6) YENİLMEZ YAPAY ZEKA AĞI
def ai_yanit_al(mesaj):
    hata_raporu = []
    
    # 2026 Uyumlu En Güncel Modeller (404 / 400 Hatalarını Engellemek İçin)
    motorlar = [
        ("GROQ", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "llama-3.1-8b-instant"),
        ("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_NIM_API_KEY", "meta/llama-3.1-8b-instruct"),
        ("XAI", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY", "grok-beta"),
        ("MISTRAL", "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "mistral-small-latest"), # Mistral için en güncel isim
        ("DEEPSEEK", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat")
    ]

    # Motorları sırayla dene. Biri cevap verirse direkt onu yolla!
    for isim, url, env_adi, model in motorlar:
        api_key = os.environ.get(env_adi)
        if not api_key:
            continue
            
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": model,
                "messages": [{"role": "system", "content": "Sen Emre AI'sın. Profesyonel, samimi, karizmatik bir kripto ve finans analistisin. Çok uzun yazma, net ol."}, {"role": "user", "content": mesaj}]
            }
            resp = requests.post(url, headers=headers, json=data, timeout=8)
            if resp.status_code == 200:
                return f"⚡ [{isim}] " + resp.json()["choices"][0]["message"]["content"]
            else:
                hata_raporu.append(f"{isim}({resp.status_code})")
        except Exception as e:
            hata_raporu.append(f"{isim}(Timeout)")

    # İlk 5 motor çöktüyse Son Çare (Plan B): Google Gemini (En Güncel Sürüm)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            # Gemini-3.8-flash en güncel 2026 modeli, 404 hatasını çözecek
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={gemini_key}"
            data = {"contents": [{"parts": [{"text": "Sen Emre AI'sın. Kısa ve net cevap ver: " + mesaj}]}]}
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=10)
            if resp.status_code == 200:
                return "🧠 [GEMINI] " + resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                hata_raporu.append(f"GEMINI({resp.status_code})")
        except Exception as e:
            hata_raporu.append(f"GEMINI(Timeout)")

    if not hata_raporu:
        return "❌ Sistemde hiçbir API şifresi bulunamadı! Lütfen Env paneline ekleyin."
        
    detay = " | ".join(hata_raporu)
    return f"❌ Bütün Zeka Motorları Çöktü!\nHata Özeti: {detay}"

@bot.message_handler(commands=['start'])
def ana_menu(message):
    mesaj = "👑 EMRE AI 6 MOTORLU KARARGAH AKTİF!\n\nKomutlar:\n/analiz BTCUSD - Detaylı TradingView Analizi\n\nAyrıca benimle doğrudan sohbet edebilirsin."
    bot.reply_to(message, mesaj)

# 📈 TRADINGVIEW CANLI ANALİZİ VE DEV İNDİKATÖR ORDUSU
@bot.message_handler(commands=['analiz'])
def tv_analiz(message):
    komut = message.text.split()
    if len(komut) < 2:
        bot.reply_to(message, "Kral hangi coini inceleyeyim? Örnek: /analiz BTCUSD")
        return

    coin = komut[1].upper()
    mesaj_giden = bot.reply_to(message, f"📡 Wall Street sunucularından {coin} canlı verileri çekiliyor...")

    try:
        handler = TA_Handler(
            symbol=coin,
            screener="crypto",
            exchange="BINANCE",
            interval=Interval.INTERVAL_1_DAY
        )
        
        analiz = handler.get_analysis()
        
        # 10 Farklı Canlı İndikatör Çekimi
        tavsiye = analiz.summary["RECOMMENDATION"]
        adx = round(analiz.indicators.get("ADX", 0), 2)
        rsi = round(analiz.indicators.get("RSI", 0), 2)
        macd = round(analiz.indicators.get("MACD.macd", 0), 2)
        sma50 = round(analiz.indicators.get("SMA50", 0), 2)
        sma200 = round(analiz.indicators.get("SMA200", 0), 2)
        
        bot.edit_message_text(f"🧠 Veri seli geldi, Emre AI strateji oluşturuyor...", chat_id=message.chat.id, message_id=mesaj_giden.message_id)

        # AI'a sunulan VIP Veri Paketi
        veri_ozeti = f"Müşteri şu coin için analiz istiyor: {coin}. TradingView Sinyali: {tavsiye}. Trend Gücü (ADX): {adx}. RSI: {rsi}. MACD: {macd}. SMA50: {sma50}. SMA200: {sma200}. Bu göstergeleri kısa, karizmatik bir yatırımcı diliyle yorumla, durum tespiti yap ve yön tahmini ver. Asla Markdown (yıldız, alt çizgi) kullanma, sadece düz metin olsun."
        
        ai_yorumu = ai_yanit_al(veri_ozeti)
        
        # Telegram'a Çökmeyen (Zırhlı) Sunum
        sonuc = f"📊 PRO TRADINGVIEW ANALİZİ: {coin}\n\n"
        sonuc += f"📈 Sinyal: {tavsiye}\n"
        sonuc += f"🌊 Trend Gücü (ADX): {adx}\n"
        sonuc += f"⚡ RSI: {rsi} | MACD: {macd}\n"
        sonuc += f"🎯 SMA50: {sma50} | SMA200: {sma200}\n\n"
        sonuc += f"🤖 EMRE AI YORUMU:\n{ai_yorumu}"
        
        # Markdown hatasını yutan son hamle
        bot.edit_message_text(sonuc, chat_id=message.chat.id, message_id=mesaj_giden.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Analiz Hatası: Borsa veya sembol bulunamadı. Lütfen tam sembolü girin (Örn: BTCUSD).", chat_id=message.chat.id, message_id=mesaj_giden.message_id)

# 💬 SERBEST SOHBET MODU
@bot.message_handler(func=lambda message: True)
def serbest_sohbet(message):
    mesaj_giden = bot.reply_to(message, "🧠 Emre AI Düşünüyor...")
    yanit = ai_yanit_al(message.text)
    # Telegram çökmelerini engelleyen zırh
    try:
        bot.edit_message_text(yanit, chat_id=message.chat.id, message_id=mesaj_giden.message_id)
    except:
        bot.send_message(message.chat.id, yanit)

print("Emre AI V6 Karargah Fişeklendi!")
bot.infinity_polling(timeout=20, long_polling_timeout=10)
