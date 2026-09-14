import telebot
import os
import requests
from tradingview_ta import TA_Handler, Interval

# Token Kontrolü
TOKEN = os.environ.get("EMRE_BOT_TOKEN")
if not TOKEN:
    print("KRİTİK HATA: EMRE_BOT_TOKEN bulunamadı!")

bot = telebot.TeleBot(TOKEN)

def ai_yorumla(mesaj, sistem_mesaji="Sen Emre AI'sın. Finans, veri ve kripto uzmanısın. Kısa, net, profesyonel ve stratejik cevaplar ver."):
    # Model isimleri ve URL'ler 404/400 hatalarına karşı en güncel sürümlerle değiştirildi!
    motorlar = [
        ("GROQ", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "llama3-8b-8192"),
        ("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_NIM_API_KEY", "meta/llama3-70b-instruct"),
        ("MISTRAL", "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "mistral-small-latest"),
        ("XAI", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY", "grok-beta"),
        ("DEEPSEEK", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat")
    ]

    hatalar = []

    # Bütün motorları sırayla dene
    for isim, url, env_adi, model in motorlar:
        api_key = os.environ.get(env_adi)
        if not api_key:
            continue

        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": sistem_mesaji},
                    {"role": "user", "content": mesaj}
                ]
            }
            # Zaman aşımını 15 saniyeye çıkardık ki analizler yarım kalmasın
            resp = requests.post(url, headers=headers, json=data, timeout=15) 
            if resp.status_code == 200:
                return f"⚡ [{isim}] " + resp.json()["choices"][0]["message"]["content"]
            else:
                hatalar.append(f"{isim}({resp.status_code})")
        except Exception as e:
            hatalar.append(f"{isim}(Timeout)")
            continue # Hata verirse sessizce diğerine geç
    
    # Son Çare: GEMINI (404 hatasına karşı latest eklendi)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={gemini_key}"
            data = {"contents": [{"parts": [{"text": sistem_mesaji + "\n\nKullanıcı Mesajı: " + mesaj}]}]}
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=15)
            if resp.status_code == 200:
                return "🧠 [GEMINI] " + resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                hatalar.append(f"GEMINI({resp.status_code})")
        except:
            hatalar.append("GEMINI(Timeout)")

    if not hatalar:
        return "❌ Sistemde hiçbir API şifresi bulunamadı! Lütfen Env paneline ekleyin."

    return "❌ Bütün Zeka Motorları Çöktü!\nHata Özeti: " + " | ".join(hatalar)

@bot.message_handler(commands=['start'])
def ana_menu(message):
    mesaj = "👑 EMRE AI PRO KARARGAH AKTİF!\n\nKomutlar:\n/analiz BTCUSD - Canlı TradingView Analizi\n\nBunun dışında bana doğrudan bir şey yazıp sohbet edebilirsin."
    bot.reply_to(message, mesaj)

@bot.message_handler(commands=['analiz'])
def tv_analiz(message):
    komut = message.text.split()
    if len(komut) < 2:
        bot.reply_to(message, "Kral hangi varlığı inceleyeyim? Örnek: /analiz BTCUSD")
        return

    coin = komut[1].upper()
    mesaj_giden = bot.reply_to(message, f"📡 {coin} için Wall Street sunucularından anlık veri çekiliyor...")

    try:
        # TradingView verisi çekme (Gelişmiş İndikatörler)
        handler = TA_Handler(
            symbol=coin,
            screener="crypto",
            exchange="BINANCE",
            interval=Interval.INTERVAL_1_DAY
        )
        analiz = handler.get_analysis()

        tavsiye = analiz.summary["RECOMMENDATION"]
        rsi = round(analiz.indicators.get("RSI", 0), 2)
        macd = round(analiz.indicators.get("MACD.macd", 0), 2)
        adx = round(analiz.indicators.get("ADX", 0), 2)
        sma50 = round(analiz.indicators.get("SMA50", 0), 2)
        sma200 = round(analiz.indicators.get("SMA200", 0), 2)

        bot.edit_message_text(f"🧠 Veriler alındı, Emre AI strateji üretiyor...", chat_id=message.chat.id, message_id=mesaj_giden.message_id)

        # AI'a verilen özel rol ve veri
        istek = f"Varlık: {coin}\nSinyal: {tavsiye}\nRSI: {rsi} MACD: {macd}\nADX (Trend Gücü): {adx}\nSMA50: {sma50} SMA200: {sma200}"
        rol = "Sen Wall Street'in en iyi kripto analistisin. Gelen TradingView verilerini kısaca yorumla, piyasanın yönünü (boğa/ayı) tahmin et ve stratejik tavsiye ver."
        
        ai_yorumu = ai_yorumla(istek, sistem_mesaji=rol)

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
            bot.edit_message_text(sonuc, chat_id=message.chat.id, message_id=mesaj_giden.message_id) # Düz metin yolla

    except Exception as e:
        bot.edit_message_text(f"❌ Analiz Hatası: Borsa veya sembol bulunamadı. Lütfen tam sembolü girin (Örn: BTCUSD). Detay: {e}", chat_id=message.chat.id, message_id=mesaj_giden.message_id)

@bot.message_handler(func=lambda message: True)
def serbest_sohbet(message):
    mesaj_giden = bot.reply_to(message, "🧠 Emre AI Düşünüyor...")
    yanit = ai_yorumla(message.text)
    
    # Telegram Markdown Hatasına Karşı Titanyum Zırh
    try:
        bot.edit_message_text(yanit, chat_id=message.chat.id, message_id=mesaj_giden.message_id, parse_mode="Markdown")
    except:
        bot.edit_message_text(yanit, chat_id=message.chat.id, message_id=mesaj_giden.message_id) # Düz metin yolla

print("Emre AI Pro Sürüm Aktif!")
bot.infinity_polling(timeout=20, long_polling_timeout=10)
