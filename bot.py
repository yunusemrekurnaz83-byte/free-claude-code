import telebot
import os
import requests
import financedatabase as fd

# TELEGRAM ŞİFRESİ
TOKEN = os.environ.get("EMRE_BOT_TOKEN") 
bot = telebot.TeleBot(TOKEN)

# 🧠 6 MOTORLU YENİLMEZ YAPAY ZEKA AĞI
def ai_yanit_al(mesaj):
    hata_raporu = []
    
    # Standart OpenAI yapısını kullanan 5 farklı motoru sıraya diziyoruz
    motorlar = [
        ("GROQ", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "llama3-8b-8192"),
        ("DEEPSEEK", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat"),
        ("MISTRAL", "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "mistral-tiny"),
        ("XAI", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY", "grok-beta"),
        ("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_NIM_API_KEY", "meta/llama3-8b-instruct")
    ]

    # Motorları yukarıdan aşağıya sırayla dene. Biri cevap verirse direkt onu yolla!
    for isim, url, env_adi, model in motorlar:
        api_key = os.environ.get(env_adi)
        if not api_key:
            continue
            
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": model,
                "messages": [{"role": "system", "content": "Sen Emre AI'sın. Finans ve veri uzmanısın. Kısa ve net cevap ver."}, {"role": "user", "content": mesaj}]
            }
            resp = requests.post(url, headers=headers, json=data, timeout=7)
            if resp.status_code == 200:
                return f"⚡ [{isim}] " + resp.json()["choices"][0]["message"]["content"]
            else:
                hata_raporu.append(f"{isim} Red: {resp.status_code}")
        except Exception as e:
            hata_raporu.append(f"{isim} Çöktü")

    # İlk 5 motor çöktüyse Son Çare (Plan B): Google Gemini
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            data = {"contents": [{"parts": [{"text": "Sen Emre AI'sın. Yanıtla: " + mesaj}]}]}
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=10)
            if resp.status_code == 200:
                return "🧠 [GEMINI] " + resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                hata_raporu.append(f"Gemini Red: {resp.status_code}")
        except Exception as e:
            hata_raporu.append(f"Gemini Çöktü")

    # Eğer 6 sistemin 6'sı da patlarsa, bize neden patladıklarının raporunu ver
    if not hata_raporu:
        return "❌ Sistemde API şifresi bulunamadı! Lütfen InstaPods Env paneline şifreleri gir."
        
    detay = " | ".join(hata_raporu)
    return f"❌ 6 MOTOR DA ÇÖKTÜ!\n\nKral, kıyamet kopuyor herhalde, tüm API'ler patladı. Hata kodları:\n{detay}"

@bot.message_handler(commands=['start'])
def ana_menu(message):
    mesaj = "👑 EMRE AI 6 MOTORLU İMPARATORLUK AKTİF!\n\nKomutlar:\n/piyasa - Genel Liste\n/piyasa BTC-USD - Özel Arama"
    bot.reply_to(message, mesaj)

# 📊 GELİŞMİŞ VERİTABANI ARAMASI
@bot.message_handler(commands=['piyasa'])
def piyasa_durumu(message):
    komut = message.text.split()
    bot.reply_to(message, "📊 Veritabanı Taranıyor...")
    try:
        veri = fd.Cryptos().select()
        if len(komut) > 1:
            aranan = komut[1].upper()
            if aranan in veri.index:
                isim = veri.loc[aranan, 'name']
                bot.send_message(message.chat.id, f"✅ BULUNDU!\nSembol: {aranan}\nAdı: {isim}")
            else:
                bot.send_message(message.chat.id, f"❌ '{aranan}' bulunamadı.")
        else:
            liste = list(veri.index)[:10]
            bot.send_message(message.chat.id, f"🚨 Sistemdeki İlk 10 Varlık:\n{', '.join(liste)}")
    except Exception as e:
        bot.reply_to(message, f"❌ Veritabanı Hatası: {e}")

@bot.message_handler(func=lambda message: True)
def yapay_zeka_merkezi(message):
    yanit = ai_yanit_al(message.text)
    bot.reply_to(message, yanit)

print("Emre AI 6 Motorlu İmparatorluk Fişeklendi!")
bot.infinity_polling(timeout=10, long_polling_timeout=5)
