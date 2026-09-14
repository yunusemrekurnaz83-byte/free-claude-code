<!-- ... existing code ... -->
            resp = requests.post(url, headers=headers, json=data, timeout=15) # Zaman aşımını 15 saniyeye çıkardık
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
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=15) # Zaman aşımını 15 saniyeye çıkardık
<!-- ... existing code ... -->
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
<!-- ... existing code ... -->
def serbest_sohbet(message):
    mesaj_giden = bot.reply_to(message, "🧠 Emre AI Düşünüyor...")
    yanit = ai_yorumla(message.text)
    
    try:
        bot.edit_message_text(yanit, chat_id=message.chat.id, message_id=mesaj_giden.message_id, parse_mode="Markdown")
    except:
        bot.edit_message_text(yanit, chat_id=message.chat.id, message_id=mesaj_giden.message_id) # Düz metin yolla

print("Emre AI Pro Sürüm Aktif!")
bot.infinity_polling(timeout=10, long_polling_timeout=5)
