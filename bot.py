import telebot
import os
import requests
import financedatabase as fd
from tradingview_ta import TA_Handler, Interval
import html
import re

# ŞİFRELER
TOKEN = os.environ.get("EMRE_BOT_TOKEN") 
bot = telebot.TeleBot(TOKEN)

# 🛡️ TELEGRAM ÇÖKÜŞ ÖNLEYİCİ (HTML ZIRHI)
def html_temizle(metin):
    metin = metin.replace("*", "").replace("_", "").replace("`", "")
    return html.escape(metin)

# 🧠 YENİLMEZ YAPAY ZEKA AĞI (DEEPSEEK LİDER)
def ai_yanit_al(mesaj, analiz_mi=False):
    hata_raporu = []
    
    motorlar = [
        ("DEEPSEEK", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat"),
        ("GROQ", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "llama-3.1-8b-instant"),
        ("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_NIM_API_KEY", "meta/llama-3.1-8b-instruct"),
        ("MISTRAL", "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "mistral-tiny"),
        ("XAI", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY", "grok-beta")
    ]

    # AI Karakteri: Analizde profesyonel, sohbette eğlenceli ve laf sokan
    if analiz_mi:
        sistem_mesaji = "Sen usta bir kripto tradersın. Verilen göstergeleri (RSI, MACD, Stoch vb.) incele, 2 cümleyle net bir strateji (AL/SAT/BEKLE) ver. Destan yazma, aşırı ciddi ve profesyonel ol."
    else:
        sistem_mesaji = "Sen Emre AI'sın. Biri boş yaparsa veya trol derse eğlen, laf sok. Ciddi bir şey sorarsa net cevap ver. Destan yazma, kısa ve samimi konuş."

    for isim, url, env_adi, model in motorlar:
        api_key = os.environ.get(env_adi)
        if not api_key:
            continue
            
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": model,
                "messages": [{"role": "system", "content": sistem_mesaji}, {"role": "user", "content": mesaj}]
            }
            resp = requests.post(url, headers=headers, json=data, timeout=15)
            if resp.status_code == 200:
                yanit = resp.json()["choices"][0]["message"]["content"]
                return isim, html_temizle(yanit)
            else:
                hata_raporu.append(f"{isim}({resp.status_code})")
        except Exception:
            hata_raporu.append(f"{isim}(Timeout)")

    return "HATA", f"Motorlar Çöktü! {hata_raporu}"

@bot.message_handler(commands=['start'])
def ana_menu(message):
    mesaj = "<b>👑 EMRE AI MERKEZ KARARGAHI</b>\n\n/piyasa - Genel Liste\n/analiz BTC - Tam Entegre TV Analizi"
    bot.reply_to(message, mesaj, parse_mode="HTML")

# Büyük harf-küçük harf bug'ı düzeltildi!
@bot.message_handler(commands=['piyasa', 'PIYASA', 'PİYASA'])
def piyasa_durumu(message):
    komut = message.text.split()
    bot.reply_to(message, "📊 Veritabanı Taranıyor...")
    try:
        veri = fd.Cryptos().select()
        if len(komut) > 1:
            aranan = komut[1].upper()
            if aranan in veri.index:
                isim = veri.loc[aranan, 'name']
                bot.send_message(message.chat.id, f"✅ BULUNDU!\nSembol: <b>{aranan}</b>\nAdı: <i>{isim}</i>", parse_mode="HTML")
            else:
                bot.send_message(message.chat.id, f"❌ '{aranan}' bulunamadı.")
        else:
            liste = list(veri.index)[:10]
            bot.send_message(message.chat.id, f"🚨 <b>Sistemdeki İlk 10 Varlık:</b>\n{', '.join(liste)}", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Veritabanı Hatası: {e}")

# 📈 TRADINGVIEW KOMBİNE ANALİZ (İSTEDİĞİN FORMAT)
@bot.message_handler(commands=['analiz', 'ANALİZ', 'Analiz'])
def tv_analiz(message):
    komut = message.text.split()
    if len(komut) < 2:
        bot.reply_to(message, "Kral hangi coini inceleyeyim? Örnek: /analiz AVAX")
        return

    coin = komut[1].upper()
    # USDT düzeltmesi
    if not coin.endswith("USD") and not coin.endswith("USDT"):
        tv_coin = f"{coin}USDT"
    else:
        tv_coin = coin
        coin = coin.replace("USDT", "").replace("USD", "")

    mesaj_giden = bot.reply_to(message, f"📡 TradingView'den <b>{coin}</b> derin verileri çekiliyor...", parse_mode="HTML")

    try:
        handler = TA_Handler(
            symbol=tv_coin,
            screener="crypto",
            exchange="BINANCE",
            interval=Interval.INTERVAL_1_DAY
        )
        analiz = handler.get_analysis()
        inds = analiz.indicators
        
        # Temel İndikatörler
        tavsiye = analiz.summary.get("RECOMMENDATION", "NÖTR")
        adx = round(inds.get("ADX", 0), 2)
        rsi = round(inds.get("RSI", 0), 2)
        macd = round(inds.get("MACD.macd", 0), 2)
        sma50 = round(inds.get("SMA50", 0), 2)
        sma200 = round(inds.get("SMA200", 0), 2)
        
        # Ekstra Wall Street İndikatörleri (Daha fazla destek)
        ema20 = round(inds.get("EMA20", 0), 2)
        stoch_k = round(inds.get("Stoch.K", 0), 2)
        cci = round(inds.get("CCI20", 0), 2)
        mom = round(inds.get("Mom", 0), 2)
        
        veri_ozeti = f"Sinyal:{tavsiye}, ADX:{adx}, RSI:{rsi}, MACD:{macd}, SMA50:{sma50}, SMA200:{sma200}, EMA20:{ema20}, Stoch:{stoch_k}, CCI:{cci}, Momentum:{mom}."
        
        bot.edit_message_text(f"🧠 Veriler harmanlanıyor, {coin} için strateji üretiliyor...", chat_id=message.chat.id, message_id=mesaj_giden.message_id)
        
        motor_adi, ai_yorumu = ai_yanit_al(veri_ozeti, analiz_mi=True)
        
        # KUSURSUZ BİRLEŞTİRİLMİŞ ŞABLON
        sonuc = f"📊 <b>PRO TRADINGVIEW ANALİZİ: {coin}</b>\n\n"
        sonuc += f"📈 <b>Genel Sinyal:</b> <code>{tavsiye}</code>\n"
        sonuc += f"🌊 <b>Trend Gücü (ADX):</b> <code>{adx}</code>\n"
        sonuc += f"⚡ <b>RSI:</b> <code>{rsi}</code> | <b>Stoch:</b> <code>{stoch_k}</code>\n"
        sonuc += f"🌀 <b>MACD:</b> <code>{macd}</code> | <b>CCI:</b> <code>{cci}</code>\n"
        sonuc += f"🚀 <b>Momentum:</b> <code>{mom}</code>\n"
        sonuc += f"🎯 <b>EMA20:</b> <code>{ema20}</code>\n"
        sonuc += f"🛡️ <b>SMA50:</b> <code>{sma50}</code> | <b>SMA200:</b> <code>{sma200}</code>\n\n"
        sonuc += f"🤖 <b>EMRE AI YORUMU:</b>\n"
        sonuc += f"<blockquote>⚡ [{motor_adi}] {ai_yorumu}</blockquote>\n"
        sonuc += f"<i>⚠️ YTD (Yatırım Tavsiyesi Değildir)</i>"
        
        bot.edit_message_text(sonuc, chat_id=message.chat.id, message_id=mesaj_giden.message_id, parse_mode="HTML")

    except Exception as e:
        bot.edit_message_text(f"❌ TV Verisi alınamadı. {coin} Binance'de bulunmuyor olabilir.", chat_id=message.chat.id, message_id=mesaj_giden.message_id)

# 💬 SOHBET VE OTOMATİK HESAPLAYICI (Örn: 0.05 BNB)
@bot.message_handler(func=lambda message: True)
def serbest_sohbet(message):
    mesaj = message.text
    hesap_metni = ""
    
    # Radar: Sadece "0.05 BNB" veya "100 TRX" yazısını algılar
    pattern = r'(?i)\b(\d+(?:\.\d+)?)\s*(?:adet|tane)?\s*([A-Za-zÇŞĞÜÖİçşğüöı]{2,8})\b'
    match = re.search(pattern, mesaj)
    
    if match:
        miktar = float(match.group(1))
        coin = match.group(2).upper()
        ozel_isimler = {"ALTIN": "PAXG", "GOLD": "PAXG", "GUMUS": "XAG", "GÜMÜŞ": "XAG"}
        hedef_coin = ozel_isimler.get(coin, coin)
        
        try:
            dolar_url = f"https://api.binance.com/api/v3/ticker/price?symbol={hedef_coin}USDT"
            dolar_resp = requests.get(dolar_url, timeout=3).json()
            if "price" in dolar_resp:
                fiyat_usd = float(dolar_resp["price"])
                kur_url = "https://api.binance.com/api/v3/ticker/price?symbol=USDTTRY"
                kur_resp = requests.get(kur_url, timeout=3).json()
                usdt_tl = float(kur_resp["price"]) if "price" in kur_resp else 34.0
                
                toplam_usd = miktar * fiyat_usd
                toplam_tl = toplam_usd * usdt_tl
                
                hesap_metni = f"\n\n🧮 <b>HIZLI HESAP ({miktar} {coin}):</b>\n💵 <b>${toplam_usd:,.2f}</b> (USDT)\n🇹🇷 <b>₺{toplam_tl:,.2f}</b> (TL)"
        except:
            pass

    # Chat için YZ çağrısı
    motor_adi, yanit = ai_yanit_al(mesaj, analiz_mi=False)
    
    sonuc = f"<blockquote>{yanit}</blockquote>\n<i>⚡ {motor_adi}</i>{hesap_metni}"
    try:
        bot.reply_to(message, sonuc, parse_mode="HTML")
    except:
        bot.reply_to(message, yanit + html_temizle(hesap_metni))

print("Emre AI V13 Entegre Karargah Aktif!")
bot.infinity_polling(timeout=20, long_polling_timeout=10)
