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
    # Yapay zekadan gelen metni HTML formatına uygun hale getirir (çökmesini engeller)
    metin = metin.replace("*", "").replace("_", "").replace("`", "")
    return html.escape(metin)

# 🧠 6 MOTORLU YENİLMEZ YAPAY ZEKA AĞI
def ai_yanit_al(mesaj, analiz_mi=False):
    hata_raporu = []
    
    # Motorlar (DEEPSEEK 1 NUMARALI ANA BEYİN)
    motorlar = [
        ("DEEPSEEK", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat"),
        ("GROQ", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "llama-3.1-8b-instant"),
        ("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_NIM_API_KEY", "meta/llama-3.1-8b-instruct"),
        ("MISTRAL", "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "mistral-tiny"),
        ("XAI", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY", "grok-beta")
    ]

    if analiz_mi:
        sistem_mesaji = "Sen usta bir kripto analistisin. Sana verilen göstergeleri kullanarak, sadece 2 cümlelik, kısa, net ve keskin bir strateji ver. Kesinlikle destan yazma."
    else:
        sistem_mesaji = "Sen Emre AI'sın. Kullanıcı selam verirse sıcak bir şekilde selam al. Sohbet etmek isterse kısa, net, samimi kripto sohbeti yap. Şaka yapabilirsin ama uzatma."

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
            resp = requests.post(url, headers=headers, json=data, timeout=12)
            if resp.status_code == 200:
                yanit = resp.json()["choices"][0]["message"]["content"]
                return isim, html_temizle(yanit)
            else:
                hata_raporu.append(f"{isim}({resp.status_code})")
        except Exception:
            hata_raporu.append(f"{isim}(Timeout)")

    # Son Çare: GEMINI
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            gemini_prompt = f"{sistem_mesaji} Soru: {mesaj}"
            data = {"contents": [{"parts": [{"text": gemini_prompt}]}]}
            resp = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=12)
            if resp.status_code == 200:
                yanit = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                return "GEMINI", html_temizle(yanit)
            else:
                hata_raporu.append(f"GEMINI({resp.status_code})")
        except Exception:
            hata_raporu.append("GEMINI(Timeout)")

    detay = " | ".join(hata_raporu)
    return "HATA", f"Zeka Motorları Çöktü! {detay}"

@bot.message_handler(commands=['start'])
def ana_menu(message):
    mesaj = "<b>👑 EMRE AI MERKEZ KARARGAHI</b>\n\nKomutlar:\n/piyasa - Genel Liste\n/analiz BTC - Canlı TradingView Sinyali"
    bot.reply_to(message, mesaj, parse_mode="HTML")

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
                bot.send_message(message.chat.id, f"✅ BULUNDU!\nSembol: <b>{aranan}</b>\nAdı: <i>{isim}</i>", parse_mode="HTML")
            else:
                bot.send_message(message.chat.id, f"❌ '{aranan}' veritabanında bulunamadı. Lütfen /analiz komutunu kullanın.")
        else:
            liste = list(veri.index)[:10]
            bot.send_message(message.chat.id, f"🚨 <b>Sistemdeki İlk 10 Varlık:</b>\n{', '.join(liste)}", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Veritabanı Hatası: {e}")

# 📈 TRADINGVIEW CANLI VERİ ÇEKİCİ (TAM ENTEGRE V14)
@bot.message_handler(commands=['analiz'])
def tv_analiz(message):
    komut = message.text.split()
    if len(komut) < 2:
        bot.reply_to(message, "Kral hangi coini inceleyeyim? Örnek: /analiz BTC")
        return

    # USDT çifti zorunlu yapılıyor (Binance'de çalışması için)
    coin_ham = komut[1].upper()
    coin = coin_ham.replace("USDT", "").replace("USD", "") # Temizle
    
    mesaj_giden = bot.reply_to(message, f"📡 TradingView'den <b>{coin}</b> canlı verileri çekiliyor...", parse_mode="HTML")

    try:
        handler = TA_Handler(
            symbol=f"{coin}USDT", # Doğrudan Binance standart formatı
            screener="crypto",
            exchange="BINANCE",
            interval=Interval.INTERVAL_1_DAY
        )
        analiz = handler.get_analysis()
        
        # Göstergeler
        tavsiye = analiz.summary.get("RECOMMENDATION", "BİLİNMİYOR")
        adx = round(analiz.indicators.get("ADX", 0), 2)
        rsi = round(analiz.indicators.get("RSI", 0), 2)
        macd = round(analiz.indicators.get("MACD.macd", 0), 2)
        sma50 = round(analiz.indicators.get("SMA50", 0), 2)
        sma200 = round(analiz.indicators.get("SMA200", 0), 2)
        stoch = round(analiz.indicators.get("Stoch.K", 0), 2)
        cci = round(analiz.indicators.get("CCI20", 0), 2)
        mom = round(analiz.indicators.get("Mom", 0), 2)
        ema20 = round(analiz.indicators.get("EMA20", 0), 2)
        
        veri_ozeti = f"Sinyal: {tavsiye}, ADX: {adx}, RSI: {rsi}, Stoch: {stoch}, MACD: {macd}, CCI: {cci}, Momentum: {mom}, EMA20: {ema20}, SMA50: {sma50}, SMA200: {sma200}."
        
        bot.edit_message_text(f"🧠 Veri geldi, Yapay Zeka yorumluyor...", chat_id=message.chat.id, message_id=mesaj_giden.message_id)
        
        # Zeka motorundan kısa yorumu al
        motor_adi, ai_yorumu = ai_yanit_al(veri_ozeti, analiz_mi=True)
        
        # DEVASA WALL STREET TABLOSU
        sonuc = f"📊 <b>PRO TRADINGVIEW ANALİZİ: {coin}</b>\n"
        sonuc += f"📈 <b>Genel Sinyal:</b> <code>{tavsiye}</code>\n"
        sonuc += f"🌊 <b>Trend Gücü (ADX):</b> <code>{adx}</code>\n"
        sonuc += f"⚡ <b>RSI:</b> <code>{rsi}</code> | <b>Stoch:</b> <code>{stoch}</code>\n"
        sonuc += f"🌀 <b>MACD:</b> <code>{macd}</code> | <b>CCI:</b> <code>{cci}</code>\n"
        sonuc += f"🚀 <b>Momentum:</b> <code>{mom}</code>\n"
        sonuc += f"🎯 <b>EMA20:</b> <code>{ema20}</code>\n"
        sonuc += f"🛡️ <b>SMA50:</b> <code>{sma50}</code> | <b>SMA200:</b> <code>{sma200}</code>\n\n"
        sonuc += f"🤖 <b>EMRE AI YORUMU:</b>\n"
        sonuc += f"<blockquote>⚡ [{motor_adi}] Strateji:\n\n{ai_yorumu}</blockquote>\n"
        sonuc += f"<i>⚠️ YTD (Yatırım Tavsiyesi Değildir)</i>"
        
        bot.edit_message_text(sonuc, chat_id=message.chat.id, message_id=mesaj_giden.message_id, parse_mode="HTML")

    except Exception as e:
        bot.edit_message_text(f"❌ TradingView Hatası: '{coin}USDT' Binance'de bulunamadı veya veri çekilemedi. Hata: {e}", chat_id=message.chat.id, message_id=mesaj_giden.message_id)

# 💬 SOHBET VE OTOMATİK HESAPLAYICI (TASARRUF MODU)
@bot.message_handler(func=lambda message: True)
def serbest_sohbet(message):
    mesaj = message.text
    
    # 1. Aşama: RADAR (Sayı + Coin İsmi var mı?)
    pattern = r'(?i)\b(\d+(?:\.\d+)?)\s*(?:adet|tane)?\s*([A-Za-zÇŞĞÜÖİçşğüöı]{2,8})\b'
    match = re.search(pattern, mesaj)
    
    # SADECE MİKTAR VE COİN YAZILDIYSA (Örn: "0.5 BNB") YAPAY ZEKAYI BOŞA YORMA!
    sadece_hesap_mi = False
    temiz_mesaj = re.sub(pattern, '', mesaj).strip().lower()
    # Eğer cümlede başka kelime yoksa veya sadece "kaç tl, hesapla" gibi kelimeler varsa
    if match and (not temiz_mesaj or len(temiz_mesaj) < 3 or temiz_mesaj in ["kaç", "kaç tl", "ne kadar", "hesapla", "kaç dolar"]):
        sadece_hesap_mi = True 

    hesap_metni = ""
    if match:
        miktar = float(match.group(1))
        coin = match.group(2).upper()
        ozel_isimler = {"ALTIN": "PAXG", "GOLD": "PAXG", "GUMUS": "XAG", "GÜMÜŞ": "XAG"}
        hedef_coin = ozel_isimler.get(coin, coin)
        
        try:
            # Binance'den canlı fiyat çekimi
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

    # 2. Aşama: Eğer sadece "0.5 BNB" dendiyse YZ'yi hiç kullanma, token israfı yapma!
    if sadece_hesap_mi and hesap_metni:
        bot.reply_to(message, hesap_metni.strip(), parse_mode="HTML") # Sadece hesabı verip bitir
        return

    # 3. Aşama: Eğer normal bir sohbet cümlesiyse YZ'yi devreye sok (ve varsa hesabı da ekle)
    mesaj_giden = bot.reply_to(message, "🧠 Emre AI Düşünüyor...")
    motor_adi, yanit = ai_yanit_al(mesaj, analiz_mi=False)
    
    sonuc = f"<blockquote>{yanit}</blockquote>\n<i>⚡ {motor_adi}</i>"
    if hesap_metni:
        sonuc += hesap_metni
    
    try:
        bot.edit_message_text(sonuc, chat_id=message.chat.id, message_id=mesaj_giden.message_id, parse_mode="HTML")
    except Exception:
        bot.edit_message_text(yanit, chat_id=message.chat.id, message_id=mesaj_giden.message_id)

print("Emre AI V14 Karargah Tüm Özellikleriyle Geri Döndü!")
bot.infinity_polling(timeout=20, long_polling_timeout=10)
