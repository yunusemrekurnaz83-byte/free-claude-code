import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import requests
import financedatabase as fd
from tradingview_ta import TA_Handler, Interval
import html
import re

# ŞİFRELER
TOKEN = os.environ.get("EMRE_BOT_TOKEN") 
bot = telebot.TeleBot(TOKEN)

# 🛡️ TELEGRAM ÇÖKÜŞ ÖNLEYİCİ
def html_temizle(metin):
    metin = metin.replace("*", "").replace("_", "").replace("`", "")
    return html.escape(metin)

# 🧠 6 MOTORLU YENİLMEZ YAPAY ZEKA AĞI
def ai_motoru(mesaj, analiz_mi=False):
    hata_raporu = []
    motorlar = [
        ("DEEPSEEK", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat"),
        ("GROQ", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "llama-3.1-8b-instant"),
        ("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_NIM_API_KEY", "meta/llama-3.1-8b-instruct"),
        ("MISTRAL", "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "mistral-tiny"),
        ("XAI", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY", "grok-beta")
    ]

    if analiz_mi:
        sistem_mesaji = "Sen efsanevi bir kripto traderısın. Sana verilen indikatör verilerine bakarak kullanıcılara maksimum 2 cümlelik, çok kısa ve net bir piyasa yönü/stratejisi sun. Asla uzatma."
    else:
        sistem_mesaji = "Sen Emre AI adında efsanevi, zeki ve samimi bir kripto botusun. Kullanıcı sohbet ederse kısa ve eğlenceli cevap ver, biri saçmalarsa laf sok."

    for isim, url, env_adi, model in motorlar:
        api_key = os.environ.get(env_adi)
        if not api_key:
            continue
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {"model": model, "messages": [{"role": "system", "content": sistem_mesaji}, {"role": "user", "content": mesaj}]}
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            if resp.status_code == 200:
                yanit = resp.json()["choices"][0]["message"]["content"]
                return isim, html_temizle(yanit)
            else:
                hata_raporu.append(f"{isim}({resp.status_code})")
        except Exception:
            hata_raporu.append(f"{isim}(Timeout)")

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            data = {"contents": [{"parts": [{"text": f"{sistem_mesaji} Soru: {mesaj}"}]}]}
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=10)
            if resp.status_code == 200:
                return "GEMINI", html_temizle(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
        except Exception:
            pass

    return "HATA", "Motorlar Çöktü!"

@bot.message_handler(commands=['start'])
def ana_menu(message):
    mesaj = "<b>👑 EMRE AI MERKEZ KARARGAHI</b>\n\nKomutlar:\n/piyasa - Genel Liste\n/analiz BTC - Etkileşimli Kontrol Paneli\n\n<i>💡 İpucu: İlk 1000 coin ve Değerli Madenler (Altın) desteklenir.\nSohbete '1000 TRX kaç TL' veya '5 Altın kaç Dolar' yazarak anında hesaplatabilirsin!</i>"
    bot.reply_to(message, mesaj, parse_mode="HTML")

# 📈 İNTERAKTİF KONTROL PANELİ
@bot.message_handler(commands=['analiz'])
def interaktif_analiz(message):
    komut = message.text.split()
    if len(komut) < 2:
        bot.reply_to(message, "Kral hangi coini inceleyeyim? Örnek: /analiz AVAX")
        return

    coin = komut[1].upper()
    # Binance'de coinler USDT ile listelenir, USD hatasını düzeltiyoruz!
    if not coin.endswith("USD") and not coin.endswith("USDT"):
        tv_coin = f"{coin}USDT" 
    else:
        tv_coin = coin
        coin = coin.replace("USDT", "").replace("USD", "") 

    # Butonları oluştur
    markup = InlineKeyboardMarkup()
    btn_gosterge = InlineKeyboardButton("📊 İndikatörleri Göster", callback_data=f"indikatör_{tv_coin}")
    btn_ai = InlineKeyboardButton("🧠 AI Yorumu Al", callback_data=f"ai_{tv_coin}")
    btn_fiyat = InlineKeyboardButton("💵 Fiyat ve Çeviri", callback_data=f"fiyat_{coin}")
    
    markup.row(btn_gosterge)
    markup.row(btn_ai)
    markup.row(btn_fiyat)

    bot.send_message(message.chat.id, f"⚡ <b>{coin} İÇİN KONTROL PANELİ</b>\n\nNeye bakmak istersin kral?", reply_markup=markup, parse_mode="HTML")

# BUTON TIKLAMALARINI YÖNETEN FONKSİYON
@bot.callback_query_handler(func=lambda call: True)
def buton_islem(call):
    islem, hedef_coin = call.data.split('_')
    
    bot.answer_callback_query(call.id, "Veriler çekiliyor...")

    if islem == "indikatör":
        try:
            handler = TA_Handler(symbol=hedef_coin, screener="crypto", exchange="BINANCE", interval=Interval.INTERVAL_1_DAY)
            analiz = handler.get_analysis()
            
            # Eksik indikatörlerin hepsini geri getirdik
            tavsiye = analiz.summary.get("RECOMMENDATION", "NÖTR")
            rsi = round(analiz.indicators.get("RSI", 0), 2)
            macd = round(analiz.indicators.get("MACD.macd", 0), 2)
            adx = round(analiz.indicators.get("ADX", 0), 2)
            sma50 = round(analiz.indicators.get("SMA50", 0), 2)
            sma200 = round(analiz.indicators.get("SMA200", 0), 2)
            
            metin = f"📊 <b>GÜNLÜK İNDİKATÖRLER: {hedef_coin}</b>\n\n"
            metin += f"📈 Sinyal: <code>{tavsiye}</code>\n"
            metin += f"🌊 Trend Gücü (ADX): <code>{adx}</code>\n"
            metin += f"⚡ RSI: <code>{rsi}</code> | MACD: <code>{macd}</code>\n"
            metin += f"🎯 SMA50: <code>{sma50}</code> | SMA200: <code>{sma200}</code>"
            
            bot.send_message(call.message.chat.id, metin, parse_mode="HTML")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ TV verisi alınamadı. Coin Binance'de bulunmuyor olabilir.")

    elif islem == "ai":
        mesaj = bot.send_message(call.message.chat.id, "🧠 Emre AI grafikleri inceliyor...")
        try:
            handler = TA_Handler(symbol=hedef_coin, screener="crypto", exchange="BINANCE", interval=Interval.INTERVAL_1_DAY)
            analiz = handler.get_analysis()
            
            tavsiye = analiz.summary.get("RECOMMENDATION", "NÖTR")
            rsi = round(analiz.indicators.get("RSI", 0), 2)
            macd = round(analiz.indicators.get("MACD.macd", 0), 2)
            adx = round(analiz.indicators.get("ADX", 0), 2)
            
            # AI artık bütün verilere bakarak analiz yapıyor
            veri_ozeti = f"Coin: {hedef_coin}, TV Sinyali: {tavsiye}, Trend Gücü(ADX): {adx}, RSI: {rsi}, MACD: {macd}."
            motor_adi, ai_yorumu = ai_motoru(veri_ozeti, analiz_mi=True)
            
            metin = f"🤖 <b>EMRE AI STRATEJİSİ [{motor_adi}]:</b>\n"
            metin += f"<blockquote>{ai_yorumu}</blockquote>\n<i>YTD</i>"
            bot.edit_message_text(metin, chat_id=call.message.chat.id, message_id=mesaj.message_id, parse_mode="HTML")
        except:
            bot.edit_message_text("❌ Yorum alınamadı.", chat_id=call.message.chat.id, message_id=mesaj.message_id)

    elif islem == "fiyat":
        try:
            # Binance üzerinden anlık USDT fiyatını alıyoruz
            dolar_url = f"https://api.binance.com/api/v3/ticker/price?symbol={hedef_coin}USDT"
            dolar_resp = requests.get(dolar_url).json()
            if "price" in dolar_resp:
                fiyat_usd = float(dolar_resp["price"])
                
                # Anlık Dolar/TL kurunu basitçe bir API'den alalım veya Binance'den USDT/TRY çekelim
                kur_url = "https://api.binance.com/api/v3/ticker/price?symbol=USDTTRY"
                kur_resp = requests.get(kur_url).json()
                usdt_tl = float(kur_resp["price"]) if "price" in kur_resp else 34.0
                
                fiyat_tl = fiyat_usd * usdt_tl
                
                metin = f"💵 <b>{hedef_coin} ANLIK FİYAT ÇEVİRİSİ</b>\n\n"
                metin += f"🇺🇸 USDT: <b>${fiyat_usd:,.2f}</b>\n"
                metin += f"🇹🇷 TL: <b>₺{fiyat_tl:,.2f}</b>\n\n"
                metin += f"<i>(Anlık Kur: 1 USDT = {usdt_tl:.2f} TL)</i>"
                
                bot.send_message(call.message.chat.id, metin, parse_mode="HTML")
            else:
                bot.send_message(call.message.chat.id, "❌ Binance'te bu coin bulunamadı.")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Fiyat çekilirken hata oluştu: {e}")

# 💬 SOHBET MODU (EĞLENCE, KISA CEVAP VE OTOMATİK HESAPLAYICI)
@bot.message_handler(func=lambda message: True)
def serbest_sohbet(message):
    mesaj = message.text
    hesap_metni = ""
    
    # SÜPER HIZLI RADAR: Sadece "0.05 BNB" veya "100 TRX" yazmak yeterli! "Kaç TL" demeye gerek yok.
    pattern = r'(?i)\b(\d+(?:\.\d+)?)\s*(?:adet|tane)?\s*([A-Za-zÇŞĞÜÖİçşğüöı]{2,8})\b'
    match = re.search(pattern, mesaj)
    
    if match:
        miktar = float(match.group(1))
        coin = match.group(2).upper()
        
        # Değerli maden kelimelerini Kripto karşılıklarıyla eşleştir
        ozel_isimler = {"ALTIN": "PAXG", "GOLD": "PAXG", "GUMUS": "XAG", "GÜMÜŞ": "XAG"}
        hedef_coin = ozel_isimler.get(coin, coin)
        
        try:
            # Binance üzerinden anlık fiyat avı
            dolar_url = f"https://api.binance.com/api/v3/ticker/price?symbol={hedef_coin}USDT"
            dolar_resp = requests.get(dolar_url, timeout=3).json()
            if "price" in dolar_resp:
                fiyat_usd = float(dolar_resp["price"])
                
                # Kur bilgisi
                kur_url = "https://api.binance.com/api/v3/ticker/price?symbol=USDTTRY"
                kur_resp = requests.get(kur_url, timeout=3).json()
                usdt_tl = float(kur_resp["price"]) if "price" in kur_resp else 34.0
                
                toplam_usd = miktar * fiyat_usd
                toplam_tl = toplam_usd * usdt_tl
                
                hesap_metni = f"\n\n🧮 <b>HIZLI HESAP ({miktar} {coin.upper()}):</b>\n💵 <b>${toplam_usd:,.2f}</b> (USDT)\n🇹🇷 <b>₺{toplam_tl:,.2f}</b> (TL)"
        except:
            pass

    motor_adi, yanit = ai_motoru(mesaj, analiz_mi=False)
    sonuc = f"<blockquote>{yanit}</blockquote>\n<i>⚡ {motor_adi}</i>{hesap_metni}"
    
    try:
        bot.reply_to(message, sonuc, parse_mode="HTML")
    except:
        bot.reply_to(message, html_temizle(yanit) + html_temizle(hesap_metni))

print("Emre AI V12 Butonlu İmparatorluk Aktif!")
bot.infinity_polling(timeout=20, long_polling_timeout=10)
