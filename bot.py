import telebot
import os
import financedatabase as fd

# DİKKAT: fcc-server'ın botu çalmasını engellemek için şifre adını değiştirdik!
# Artık InstaPods'a TELEGRAM_BOT_TOKEN değil, EMRE_BOT_TOKEN yazacağız.
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
        cryptos = fd.Cryptos()
        veri = cryptos.options('currency')
        mesaj = f"🚨 Emre Veri Ağı Aktif!\nKripto işlem para birimleri:\n{veri[:5]}"
        bot.send_message(message.chat.id, mesaj)
    except Exception as e:
        bot.reply_to(message, f"❌ Veritabanı Hatası: {e}")

@bot.message_handler(func=lambda message: True)
def yapay_zeka_merkezi(message):
    # İleride Groq/Gemini API kodlarını tam buraya gömeceğiz!
    bot.reply_to(message, "Modüller yükleniyor kral... Şu an Yapay Zeka bağlantısı ve Crash Monitor entegrasyonu için altyapı hazırlanıyor.")

print("Emre AI Bot Başlatıldı - Fişeklendi!")
# Botun kapanmaması için sonsuz döngü
bot.infinity_polling(timeout=10, long_polling_timeout=5)
