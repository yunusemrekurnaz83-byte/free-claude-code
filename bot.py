import telebot
import os
import financedatabase as fd # İşte kütüphaneyi burada çağırıyoruz!

# BotFather'dan aldığın token
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") 
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Emre Veri Ağı'nın Grup ID'si (Bunu daha sonra bulup buraya yazacağız)
VERI_AGI_ID = "-100XXXXXXXXXX" 

@bot.message_handler(commands=['piyasa'])
def piyasa_durumu(message):
    bot.reply_to(message, "Kral veritabanına bağlanıyorum, bekle...")
    try:
        # FinanceDatabase'den veri çekiyoruz (örnek: kriptolar)
        cryptos = fd.Cryptos()
        veri = cryptos.options('currency') # Kriptoların hangi para birimlerinde işlem gördüğünü alalım
        
        mesaj = f"🚨 Emre AI Veri Ağı\n\nFinanceDatabase Aktif!\nKripto pazarındaki işlem gören para birimlerinden bazıları:\n{veri[:5]}"
        bot.send_message(message.chat.id, mesaj)
    except Exception as e:
        bot.reply_to(message, f"Hata oluştu kral: {e}")

print("Emre AI, FinanceDatabase ile birlikte uyandı!")
bot.polling(none_stop=True)
