import telebot
import os
import financedatabase as fd

# DİKKAT: fcc-server'ın botu çalmasını engellemek için şifre adını EMRE_BOT_TOKEN yaptık!
# InstaPods'ta Env sekmesine EMRE_BOT_TOKEN=SeninBotFatherSifren olarak eklediğinden emin ol.
TOKEN = os.environ.get("EMRE_BOT_TOKEN") 
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def ana_menu(message):
    mesaj = (
        "👑 EMRE AI Merkez Karargahı Aktif!\n\n"
        "Sistem Durumu:\n"
        "✅ Ana Beyin Bağlantısı: Başarılı\n"
        "✅ FinanceDatabase: Hazır\n"
        "⏳ US Stock Crash Monitor: Beklemede\n"
        "⏳ TradingView Sinyal Ağı: Beklemede\n\n"
        "Komutlar:\n"
        "/piyasa - Finansal veritabanını test et"
    )
    bot.reply_to(message, mesaj)

@bot.message_handler(commands=['piyasa'])
def piyasa_durumu(message):
    bot.reply_to(message, "📊 FinanceDatabase'e bağlanıyorum kral, bekle...")
    try:
        # FinanceDatabase güncel sürüm kodları
        kriptolar = fd.Cryptos()
        
        # Veritabanından ilk 5 kripto sembolünü çekiyoruz (Hatasız yeni yöntem)
        veri = list(kriptolar.select().keys())[:5] 
        
        mesaj = f"🚨 Emre Veri Ağı Aktif!\n\nSistemdeki ilk 5 Kripto Varlık:\n{', '.join(veri)}"
        bot.send_message(message.chat.id, mesaj)
    except Exception as e:
        bot.reply_to(message, f"❌ Veritabanı Hatası: {e}")

@bot.message_handler(func=lambda message: True)
def yapay_zeka_merkezi(message):
    # Bir sonraki adımda Groq veya Gemini yapay zekasını buraya ekleyeceğiz!
    bot.reply_to(message, "Modüller yükleniyor kral... Şu an Yapay Zeka bağlantısı ve Crash Monitor entegrasyonu için altyapı hazırlanıyor.")

print("Emre AI Bot Başlatıldı - Fişeklendi!")
# Botun kapanmaması için sonsuz döngü
bot.infinity_polling(timeout=10, long_polling_timeout=5)
