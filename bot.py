import telebot
import os
import requests
from tradingview_ta import TA_Handler, Interval

# ŞİFRELER
TOKEN = os.environ.get("EMRE_BOT_TOKEN") 
bot = telebot.TeleBot(TOKEN)

# TELEGRAM ÇÖKMESİNİ ENGELLEYEN ZIRH
def temizle_markdown(metin):
    # AI'nin Telegram'ı bozacak yıldız ve alt çizgilerini temizliyoruz
    return metin.replace("*", "").replace("_", "").replace("`", "")

# 🧠 ZIRHLI VE GÜNCEL YAPAY ZEKA AĞI
def ai_yanit_al(mesaj):
    hata_raporu = []
    
    # KAYA GİBİ SAĞLAM VE %100 ÇALIŞAN STANDART MODELLER (En düşük/hızlı)
    motorlar = [
        ("GROQ", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "llama3-8b-8192"),
        ("MISTRAL", "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "open-mistral-7b"), 
        ("XAI", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY", "grok-beta"),
        ("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_NIM_API_KEY", "meta/llama3-8b-instruct"),
        ("DEEPSEEK", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat") 
    ]

    for isim, url, env_adi, model in motorlar:
        api_key = os.environ.get(env_adi)
        if not api_key:
            continue
            
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": model,
                "messages": [{"role": "system", "content": "Sen profesyonel bir kripto analistisin. Kısa ve net cevap ver. Markdown(Yıldız vs) kullanma."}, {"role": "user", "content": mesaj}]
            }
            resp = requests.post(url, headers=headers, json=data, timeout=8)
            if resp.status_code == 200:
                yanit = resp.json()["choices"][0]["message"]["content"]
                return f"⚡ [{isim}] " + temizle_markdown(yanit)
            else:
                hata_raporu.append(f"{isim}({resp.status_code})")
        except Exception as e:
            hata_raporu.append(f"{isim}(Timeout)")

    # GOOGLE GEMINI (Son Çare)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            data = {"contents": [{"parts": [{"text": "Sen profesyonel bir kripto analistisin. Net cevap ver, yıldız kullanma: " + mesaj}]}]}
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=10)
            if resp.status_code == 200:
                yanit = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                return "🧠 [GEMINI] " + temizle_markdown(yanit)
            else:
                hata_raporu.append(f"GEMINI({resp.status_code})")
        except Exception as e:
            hata_raporu.append(f"GEMINI(Timeout)")

    if not hata_raporu:
        return "❌ InstaPods Env panelinde hiçbir API şifresi bulunamadı!"
        
    detay = " | ".join(hata_raporu)
    return f"❌ YAPAY ZEKA BAĞLANTISI KURULAMADI!\n\nŞifrelerin bitmiş veya sağlayıcılar çökmüş. Hatalar: {detay}"

@bot.message_handler(commands=['start'])
def ana_menu(message):
    mesaj = "👑 EMRE AI KARARGAHI AKTİF!\n\nKomutlar:\n/analiz BTCUSD - Detaylı TradingView Analizi\n\nAyrıca benimle serbest sohbet edebilirsin."
    bot.reply_to(message, mesaj)

# 📈 TRADINGVIEW CANLI ANALİZİ
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
        
        tavsiye = analiz.summary["RECOMMENDATION"]
        adx = round(analiz.indicators.get("ADX", 0), 2)
        rsi = round(analiz.indicators.get("RSI", 0), 2)
        macd = round(analiz.indicators.get("MACD.macd", 0), 2)
        sma50 = round(analiz.indicators.get("SMA50", 0), 2)
        sma200 = round(analiz.indicators.get("SMA200", 0), 2)
        
        bot.edit_message_text(f"🧠 Veri geldi, 6 Motorlu Emre AI strateji oluşturuyor...", chat_id=message.chat.id, message_id=mesaj_giden.message_id)

        veri_ozeti = f"{coin} için canlı teknik veriler: Sinyal={tavsiye}, Trend(ADX)={adx}, RSI={rsi}, MACD={macd}, SMA50={sma50}, SMA200={sma200}. Bu göstergeleri analiz et, alım mı satım mı mantıklı söyle. Cevabında ASLA yıldız veya kalın harf kullanma."
        
        ai_yorumu = ai_yanit_al(veri_ozeti)
        
        sonuc = f"📊 PRO TRADINGVIEW ANALİZİ: {coin}\n\n"
        sonuc += f"📈 Sinyal: {tavsiye}\n"
        sonuc += f"🌊 Trend Gücü (ADX): {adx}\n"
        sonuc += f"⚡ RSI: {rsi} | MACD: {macd}\n"
        sonuc += f"🎯 SMA50: {sma50} | SMA200: {sma200}\n\n"
        sonuc += f"🤖 EMRE AI YORUMU:\n{ai_yorumu}"
        
        bot.edit_message_text(sonuc, chat_id=message.chat.id, message_id=mesaj_giden.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Analiz Hatası: Borsa veya sembol bulunamadı. Lütfen tam sembolü girin (Örn: BTCUSD).", chat_id=message.chat.id, message_id=mesaj_giden.message_id)

@bot.message_handler(func=lambda message: True)
def serbest_sohbet(message):
    mesaj_giden = bot.reply_to(message, "🧠 Emre AI Düşünüyor...")
    yanit = ai_yanit_al(message.text)
    try:
        bot.edit_message_text(yanit, chat_id=message.chat.id, message_id=mesaj_giden.message_id)
    except:
        bot.send_message(message.chat.id, yanit)

print("Emre AI V7 Karargah Fişeklendi!")
bot.infinity_polling(timeout=20, long_polling_timeout=10)
