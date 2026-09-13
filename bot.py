import telebot
import os
import requests
import financedatabase as fd

# ŞİFRELERİ ÇEKİYORUZ
TOKEN = os.environ.get("EMRE_BOT_TOKEN") 
GROQ_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TOKEN)

# ÇİFT MOTORLU YAPAY ZEKA MODÜLÜ (Biri çökerse diğeri çalışır)
def ai_yanit_al(mesaj):
    # 1. Aşama: Groq'u Dene (Şimşek Hızında)
    if GROQ_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
            data = {
                "model": "llama3-8b-8192", 
                "messages": [{"role": "system", "content": "Sen Emre AI'sın. Finans ve veri analizi uzmanısın. Kısa ve net cevap ver."}, {"role": "user", "content": mesaj}]
            }
            resp = requests.post(url, headers=headers, json=data, timeout=5)
            if resp.status_code == 200:
                return "⚡ [GROQ] " + resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass # Hata verirse sessizce Gemini'ye geç
    
    # 2. Aşama: Groq çöktüyse Gemini'yi Dene (Ağır Abimiz)
    if GEMINI_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
            headers = {"Content-Type": "application/json"}
            data = {"contents": [{"parts": [{"text": "Sen Emre AI'sın. Yanıtla: " + mesaj}]}]}
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            if resp.status_code == 200:
                return "🧠 [GEMINI] " + resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            pass
    
    return "❌ Yapay Zeka Motorları şu an yanıt veremiyor veya API şifreleri eksik."

@bot.message_handler(commands=['start'])
def ana_menu(message):
    mesaj = (
        "👑 EMRE AI MERKEZ KARARGAHI\n\n"
        "✅ Ana Beyin: Aktif\n"
        "✅ Çift Motorlu AI (Groq + Gemini): Aktif\n"
        "✅ FinanceDatabase: Aktif\n"
        "⏳ Crash Monitor: Hazırlanıyor...\n\n"
        "Bana herhangi bir şey yazarak zekamı test edebilirsin!"
    )
    bot.reply_to(message, mesaj)

@bot.message_handler(commands=['piyasa'])
def piyasa_durumu(message):
    bot.reply_to(message, "📊 Veritabanı taranıyor...")
    try:
        kriptolar = fd.Cryptos()
        veri = list(kriptolar.select().index)[:5]
        bot.send_message(message.chat.id, f"🚨 Sistemdeki İlk 5 Kripto:\n{', '.join(veri)}")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {e}")

# Gelen Bütün Mesajları Yapay Zekaya Gönder
@bot.message_handler(func=lambda message: True)
def yapay_zeka_merkezi(message):
    yanit = ai_yanit_al(message.text)
    bot.reply_to(message, yanit)

print("Emre AI Tüm Modüllerle Fişeklendi!")
bot.infinity_polling(timeout=10, long_polling_timeout=5)
