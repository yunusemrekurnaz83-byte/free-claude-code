# -*- coding: utf-8 -*-
"""
EMRE AI — V15 "ASENKRON KARARGAH + MENÜLÜ"
=================================
V14'e göre değişenler:
  1. Tamamen ASENKRON  -> aiohttp + AsyncTeleBot.
  2. HAFIZA            -> Her sohbet için son N mesaj tutuluyor.
  3. CONTEXT INJECTION -> Modele anlık fiyat sızdırılır.
  4. PİYASA HİSSİ      -> Fear & Greed Index, Long/Short oranı.
  5. DEVRE KESİCİ      -> Çöken motor 90 sn cezalı.
  6. GERÇEK SEMBOL     -> Binance exchangeInfo ile doğrulama.
  7. RATE LIMIT        -> Kullanıcı başına flood koruması.
  8. TradingView       -> Ayrı thread'de çalışır.
  9. MENÜ ENTEGRASYONU -> Telegram / menüsü otomatik yüklenir.
"""

import asyncio
import html
import logging
import os
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from telebot.async_telebot import AsyncTeleBot
from telebot.types import BotCommand
from tradingview_ta import TA_Handler, Interval

# ----------------------------------------------------------------------------
# AYARLAR
# ----------------------------------------------------------------------------

TOKEN = os.environ.get("EMRE_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("EMRE_BOT_TOKEN tanimli degil. Once token'i ortam degiskenine ekle.")

bot = AsyncTeleBot(TOKEN, parse_mode="HTML")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
log = logging.getLogger("emre-ai")

HAFIZA_UZUNLUGU = 8          
HAFIZA_TTL = 30 * 60         
MOTOR_TIMEOUT = 12           
MOTOR_CEZA_SURESI = 90       
KULLANICI_BEKLEME = 4        
TETIKLEYICILER = ["emrai", "emray", "emreai", "karargah", "asistan"]

TELEGRAM_LIMIT = 3900        

# ----------------------------------------------------------------------------
# ORTAK HTTP OTURUMU
# ----------------------------------------------------------------------------

_session: Optional[aiohttp.ClientSession] = None

async def oturum() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20),
            connector=aiohttp.TCPConnector(limit=60, ttl_dns_cache=300),
            headers={"User-Agent": "EmreAI/15.0"},
        )
    return _session

async def json_getir(url: str, timeout: float = 5.0, **kw) -> Optional[Any]:
    try:
        s = await oturum()
        async with s.get(url, timeout=aiohttp.ClientTimeout(total=timeout), **kw) as r:
            if r.status != 200:
                return None
            return await r.json(content_type=None)
    except Exception as e:
        log.debug("GET basarisiz %s -> %s", url, e)
        return None

# ----------------------------------------------------------------------------
# TTL CACHE
# ----------------------------------------------------------------------------

class TTLCache:
    def __init__(self, ttl: float):
        self.ttl = ttl
        self._d: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        kayit = self._d.get(key)
        if not kayit:
            return None
        zaman, deger = kayit
        if time.time() - zaman > self.ttl:
            self._d.pop(key, None)
            return None
        return deger

    def set(self, key: str, value: Any) -> Any:
        self._d[key] = (time.time(), value)
        return value

fiyat_cache = TTLCache(10)        
duygu_cache = TTLCache(600)       
oran_cache = TTLCache(300)        
sembol_cache = TTLCache(12 * 3600)  

# ----------------------------------------------------------------------------
# HTML ZIRHI + MESAJ BÖLÜCÜ
# ----------------------------------------------------------------------------

def html_temizle(metin: str) -> str:
    metin = re.sub(r"[*_`]+", "", metin or "")
    return html.escape(metin.strip())

def parcala(metin: str, limit: int = TELEGRAM_LIMIT) -> List[str]:
    if len(metin) <= limit:
        return [metin]
    parcalar, tampon = [], ""
    for satir in metin.split("\n"):
        if len(tampon) + len(satir) + 1 > limit:
            parcalar.append(tampon)
            tampon = satir
        else:
            tampon = f"{tampon}\n{satir}" if tampon else satir
    if tampon:
        parcalar.append(tampon)
    return parcalar

async def guvenli_duzenle(chat_id: int, message_id: int, metin: str) -> None:
    parcalar = parcala(metin)
    try:
        await bot.edit_message_text(parcalar[0], chat_id=chat_id, message_id=message_id)
    except Exception:
        try:
            await bot.edit_message_text(
                html.escape(re.sub(r"<[^>]+>", "", parcalar[0])),
                chat_id=chat_id, message_id=message_id, parse_mode=None,
            )
        except Exception as e:
            log.warning("Mesaj duzenlenemedi: %s", e)
    for ek in parcalar[1:]:
        try:
            await bot.send_message(chat_id, ek)
        except Exception:
            pass

# ----------------------------------------------------------------------------
# HAFIZA
# ----------------------------------------------------------------------------

@dataclass
class Konusma:
    mesajlar: deque = field(default_factory=lambda: deque(maxlen=HAFIZA_UZUNLUGU))
    son_erisim: float = field(default_factory=time.time)

class Hafiza:
    def __init__(self):
        self._depo: Dict[str, Konusma] = {}

    @staticmethod
    def _anahtar(chat_id: int, user_id: int) -> str:
        return f"{chat_id}:{user_id}"

    def ekle(self, chat_id: int, user_id: int, rol: str, icerik: str) -> None:
        k = self._anahtar(chat_id, user_id)
        konusma = self._depo.setdefault(k, Konusma())
        konusma.mesajlar.append({"role": rol, "content": icerik[:1500]})
        konusma.son_erisim = time.time()

    def getir(self, chat_id: int, user_id: int) -> List[Dict[str, str]]:
        k = self._anahtar(chat_id, user_id)
        konusma = self._depo.get(k)
        if not konusma:
            return []
        if time.time() - konusma.son_erisim > HAFIZA_TTL:
            self._depo.pop(k, None)
            return []
        return list(konusma.mesajlar)

    def temizle(self, chat_id: int, user_id: int) -> None:
        self._depo.pop(self._anahtar(chat_id, user_id), None)

    def budama(self) -> None:
        simdi = time.time()
        olu = [k for k, v in self._depo.items() if simdi - v.son_erisim > HAFIZA_TTL]
        for k in olu:
            self._depo.pop(k, None)

hafiza = Hafiza()

# ----------------------------------------------------------------------------
# PİYASA VERİSİ
# ----------------------------------------------------------------------------

async def binance_sembolleri() -> set:
    onbellek = sembol_cache.get("semboller")
    if onbellek:
        return onbellek
    veri = await json_getir("https://api.binance.com/api/v3/exchangeInfo", timeout=15)
    semboller = set()
    if veri and "symbols" in veri:
        for s in veri["symbols"]:
            if s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING":
                semboller.add(s["baseAsset"].upper())
    if not semboller:
        semboller = {"BTC", "ETH", "BNB", "SOL", "XRP", "TRX", "AVAX", "DOGE", "ADA", "PAXG"}
    return sembol_cache.set("semboller", semboller)

async def fiyat_getir(coin: str) -> Optional[Dict[str, float]]:
    coin = coin.upper()
    onbellek = fiyat_cache.get(coin)
    if onbellek:
        return onbellek
    veri = await json_getir(
        f"https://api.binance.com/api/v3/ticker/24hr?symbol={coin}USDT", timeout=4
    )
    if not veri or "lastPrice" not in veri:
        return None
    sonuc = {
        "fiyat": float(veri["lastPrice"]),
        "degisim": float(veri.get("priceChangePercent", 0)),
        "hacim": float(veri.get("quoteVolume", 0)),
    }
    return fiyat_cache.set(coin, sonuc)

async def usdt_try() -> float:
    onbellek = fiyat_cache.get("__USDTTRY")
    if onbellek:
        return onbellek
    veri = await json_getir("https://api.binance.com/api/v3/ticker/price?symbol=USDTTRY", timeout=4)
    kur = float(veri["price"]) if veri and "price" in veri else 0.0
    return fiyat_cache.set("__USDTTRY", kur) if kur else 0.0

async def korku_acgozluluk() -> Optional[Dict[str, str]]:
    onbellek = duygu_cache.get("fng")
    if onbellek:
        return onbellek
    veri = await json_getir("https://api.alternative.me/fng/?limit=1", timeout=6)
    try:
        kayit = veri["data"][0]
        tr = {
            "Extreme Fear": "Aşırı Korku", "Fear": "Korku", "Neutral": "Nötr",
            "Greed": "Açgözlülük", "Extreme Greed": "Aşırı Açgözlülük",
        }
        etiket = kayit.get("value_classification", "")
        sonuc = {"deger": kayit["value"], "etiket": tr.get(etiket, etiket)}
        return duygu_cache.set("fng", sonuc)
    except Exception:
        return None

async def long_short(coin: str) -> Optional[Dict[str, float]]:
    coin = coin.upper()
    onbellek = oran_cache.get(f"ls:{coin}")
    if onbellek:
        return onbellek
    veri = await json_getir(
        "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
        f"?symbol={coin}USDT&period=15m&limit=1", timeout=6
    )
    try:
        kayit = veri[0]
        sonuc = {
            "oran": float(kayit["longShortRatio"]),
            "long": float(kayit["longAccount"]) * 100,
            "short": float(kayit["shortAccount"]) * 100,
        }
        return oran_cache.set(f"ls:{coin}", sonuc)
    except Exception:
        return None

async def funding(coin: str) -> Optional[float]:
    veri = await json_getir(
        f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={coin.upper()}USDT", timeout=5
    )
    try:
        return float(veri["lastFundingRate"]) * 100
    except Exception:
        return None

async def piyasa_konteksti(mesaj: str) -> str:
    semboller = await binance_sembolleri()
    adaylar = {k.upper() for k in re.findall(r"[A-Za-z]{2,10}", mesaj)}
    bulunan = [c for c in adaylar if c in semboller][:4]
    if not bulunan:
        bulunan = ["BTC"] 

    gorevler = [fiyat_getir(c) for c in bulunan] + [korku_acgozluluk(), long_short(bulunan[0])]
    sonuclar = await asyncio.gather(*gorevler, return_exceptions=True)

    fiyatlar = sonuclar[: len(bulunan)]
    fng = sonuclar[len(bulunan)] if not isinstance(sonuclar[len(bulunan)], Exception) else None
    ls = sonuclar[-1] if not isinstance(sonuclar[-1], Exception) else None

    satirlar = []
    for coin, veri in zip(bulunan, fiyatlar):
        if isinstance(veri, dict):
            satirlar.append(f"{coin}: ${veri['fiyat']:,.4f} (24s %{veri['degisim']:+.2f})")
    if isinstance(fng, dict):
        satirlar.append(f"Korku&Açgözlülük Endeksi: {fng['deger']}/100 ({fng['etiket']})")
    if isinstance(ls, dict):
        satirlar.append(
            f"{bulunan[0]} Long/Short: {ls['oran']:.2f} "
            f"(Long %{ls['long']:.0f} / Short %{ls['short']:.0f})"
        )
    if not satirlar:
        return ""
    return (
        "[CANLI PİYASA VERİSİ — bu rakamlar gerçek ve şu andır. "
        "Fiyat sorulursa SADECE bunları kullan, asla kendi kafandan rakam uydurma]\n"
        + "\n".join(satirlar)
    )

# ----------------------------------------------------------------------------
# YAPAY ZEKA AĞI
# ----------------------------------------------------------------------------

@dataclass
class Motor:
    isim: str
    url: str
    env: str
    model: str
    tip: str = "openai"

MOTORLAR: List[Motor] = [
    Motor("DEEPSEEK", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat"),
    Motor("GROQ", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "llama-3.3-70b-versatile"),
    Motor("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_NIM_API_KEY", "meta/llama-3.1-70b-instruct"),
    Motor("MISTRAL", "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "mistral-small-latest"),
    Motor("XAI", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY", "grok-2-latest"),
    Motor("GEMINI", "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
          "GEMINI_API_KEY", "gemini-1.5-flash", tip="gemini"),
]

_ceza: Dict[str, float] = defaultdict(float)

def _cezali_mi(isim: str) -> bool:
    return time.time() < _ceza[isim]

async def _motor_cagir(motor: Motor, mesajlar: List[Dict[str, str]], api_key: str) -> str:
    s = await oturum()
    zaman_asimi = aiohttp.ClientTimeout(total=MOTOR_TIMEOUT)

    if motor.tip == "gemini":
        sistem = "\n".join(m["content"] for m in mesajlar if m["role"] == "system")
        icerik = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in mesajlar if m["role"] in ("user", "assistant")
        ]
        govde = {"contents": icerik, "systemInstruction": {"parts": [{"text": sistem}]}}
        url = f"{motor.url}?key={api_key}"
        async with s.post(url, json=govde, timeout=zaman_asimi) as r:
            if r.status != 200:
                raise RuntimeError(f"HTTP {r.status}")
            veri = await r.json()
            return veri["candidates"][0]["content"]["parts"][0]["text"]

    govde = {
        "model": motor.model,
        "messages": mesajlar,
        "temperature": 0.7,
        "max_tokens": 700,
    }
    basliklar = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with s.post(motor.url, json=govde, headers=basliklar, timeout=zaman_asimi) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        veri = await r.json()
        return veri["choices"][0]["message"]["content"]

async def ai_yanit_al(
    mesaj: str,
    chat_id: int = 0,
    user_id: int = 0,
    analiz_mi: bool = False,
    kontekst: str = "",
    hafiza_kullan: bool = True,
) -> Tuple[str, str]:
    if analiz_mi:
        sistem = (
            "Sen usta bir kripto analistisin. Verilen göstergeleri kullanarak SADECE 2 cümlelik, "
            "kısa, net ve keskin bir strateji ver. Destan yazma, maddeleme yapma."
        )
    else:
        sistem = (
            "Sen Emre AI'sın; Telegram'daki bir kripto karargahının asistanısın. "
            "Kısa, net, samimi konuş; gerekirse şaka yap ama uzatma. "
            "Konuşma geçmişini dikkate al. Fiyat konusunda ASLA tahmin yürütme: "
            "sana verilen canlı piyasa verisi dışında rakam telaffuz etme, veri yoksa 'anlık veriye bakayım' de."
        )

    mesajlar: List[Dict[str, str]] = [{"role": "system", "content": sistem}]
    if kontekst:
        mesajlar.append({"role": "system", "content": kontekst})
    if hafiza_kullan:
        mesajlar.extend(hafiza.getir(chat_id, user_id))
    mesajlar.append({"role": "user", "content": mesaj})

    hatalar = []
    for motor in MOTORLAR:
        api_key = os.environ.get(motor.env)
        if not api_key or _cezali_mi(motor.isim):
            continue
        try:
            ham = await _motor_cagir(motor, mesajlar, api_key)
            if not ham or not ham.strip():
                raise RuntimeError("bos yanit")
            if hafiza_kullan:
                hafiza.ekle(chat_id, user_id, "user", mesaj)
                hafiza.ekle(chat_id, user_id, "assistant", ham.strip())
            return motor.isim, html_temizle(ham)
        except asyncio.TimeoutError:
            _ceza[motor.isim] = time.time() + MOTOR_CEZA_SURESI
            hatalar.append(f"{motor.isim}(timeout)")
        except Exception as e:
            _ceza[motor.isim] = time.time() + MOTOR_CEZA_SURESI
            hatalar.append(f"{motor.isim}({e})")

    log.error("Tum motorlar dustu: %s", " | ".join(hatalar))
    return "HATA", "Zeka motorlarının hepsi şu an meşgul. Birkaç saniye sonra tekrar dene."

# ----------------------------------------------------------------------------
# FLOOD KORUMASI
# ----------------------------------------------------------------------------

_son_istek: Dict[int, float] = defaultdict(float)

def cok_hizli_mi(user_id: int) -> bool:
    simdi = time.time()
    if simdi - _son_istek[user_id] < KULLANICI_BEKLEME:
        return True
    _son_istek[user_id] = simdi
    return False

# ----------------------------------------------------------------------------
# KOMUTLAR
# ----------------------------------------------------------------------------

@bot.message_handler(commands=["start", "yardim", "help"])
async def ana_menu(message):
    metin = (
        "<b>👑 EMRE AI — KARARGAH V15</b>\n\n"
        "<b>/analiz</b> BTC 4s — TradingView canlı sinyal + AI strateji\n"
        "<b>/piyasa</b> — En çok yükselen/düşen 5 coin\n"
        "<b>/duygu</b> — Korku &amp; Açgözlülük + Long/Short\n"
        "<b>/unut</b> — Botun seninle olan sohbet hafızasını siler\n\n"
        "<i>Sohbet için mesajında \"emrai\" veya \"karargah\" de. "
        "\"0.5 BNB kaç TL\" gibi yazarsan hesabı AI'ı hiç yormadan anında yaparım.</i>"
    )
    await bot.reply_to(message, metin)

@bot.message_handler(commands=["unut"])
async def unut(message):
    hafiza.temizle(message.chat.id, message.from_user.id)
    await bot.reply_to(message, "🧹 Tamam, aramızda konuşulanları unuttum. Sıfırdan başlıyoruz.")

@bot.message_handler(commands=["duygu", "korku"])
async def duygu_komutu(message):
    fng, ls, btc = await asyncio.gather(
        korku_acgozluluk(), long_short("BTC"), fiyat_getir("BTC")
    )
    satir = ["<b>🌡️ PİYASA NABZI</b>\n"]
    if isinstance(btc, dict):
        satir.append(f"₿ <b>BTC:</b> <code>${btc['fiyat']:,.0f}</code> (24s %{btc['degisim']:+.2f})")
    if isinstance(fng, dict):
        bar_dolu = int(int(fng["deger"]) / 10)
        bar = "█" * bar_dolu + "░" * (10 - bar_dolu)
        satir.append(f"😨 <b>Korku/Açgözlülük:</b> <code>{fng['deger']}/100</code> — {fng['etiket']}\n<code>{bar}</code>")
    if isinstance(ls, dict):
        satir.append(
            f"⚔️ <b>BTC Long/Short:</b> <code>{ls['oran']:.2f}</code>\n"
            f"🟢 Long %{ls['long']:.0f} | 🔴 Short %{ls['short']:.0f}"
        )
    fr = await funding("BTC")
    if fr is not None:
        satir.append(f"💸 <b>Funding:</b> <code>%{fr:.4f}</code>")
    if len(satir) == 1:
        satir.append("Veri kaynaklarına şu an ulaşılamıyor.")
    await bot.reply_to(message, "\n".join(satir))

@bot.message_handler(commands=["piyasa"])
async def piyasa_durumu(message):
    veri = await json_getir("https://api.binance.com/api/v3/ticker/24hr", timeout=15)
    if not veri:
        await bot.reply_to(message, "❌ Piyasa verisine şu an ulaşılamıyor.")
        return
    usdt = [
        d for d in veri
        if d["symbol"].endswith("USDT") and float(d.get("quoteVolume", 0)) > 20_000_000
        and not re.search(r"(UP|DOWN|BULL|BEAR)USDT$", d["symbol"])
    ]
    usdt.sort(key=lambda d: float(d["priceChangePercent"]), reverse=True)
    yukselen, dusen = usdt[:5], usdt[-5:][::-1]

    def satirla(liste):
        return "\n".join(
            f"<code>{d['symbol'].replace('USDT',''):<6}</code> "
            f"${float(d['lastPrice']):,.4f}  <b>%{float(d['priceChangePercent']):+.2f}</b>"
            for d in liste
        )

    metin = (
        "<b>📊 24 SAATLİK PİYASA</b>\n\n"
        f"🚀 <b>EN ÇOK YÜKSELEN</b>\n{satirla(yukselen)}\n\n"
        f"🩸 <b>EN ÇOK DÜŞEN</b>\n{satirla(dusen)}\n\n"
        "<i>Yalnızca hacmi 20M$ üzeri pariteler listelenir.</i>"
    )
    await bot.reply_to(message, metin)

ZAMAN_HARITASI = {
    "15m": (Interval.INTERVAL_15_MINUTES, "15 Dakikalık"),
    "15dk": (Interval.INTERVAL_15_MINUTES, "15 Dakikalık"),
    "1h": (Interval.INTERVAL_1_HOUR, "1 Saatlik"),
    "1s": (Interval.INTERVAL_1_HOUR, "1 Saatlik"),
    "4h": (Interval.INTERVAL_4_HOURS, "4 Saatlik"),
    "4s": (Interval.INTERVAL_4_HOURS, "4 Saatlik"),
    "1d": (Interval.INTERVAL_1_DAY, "Günlük"),
    "1g": (Interval.INTERVAL_1_DAY, "Günlük"),
    "1w": (Interval.INTERVAL_1_WEEK, "Haftalık"),
    "1hft": (Interval.INTERVAL_1_WEEK, "Haftalık"),
}

def _tv_cek(coin: str, periyot) -> Dict[str, Any]:
    handler = TA_Handler(
        symbol=f"{coin}USDT", screener="crypto", exchange="BINANCE", interval=periyot
    )
    analiz = handler.get_analysis()
    g = analiz.indicators
    return {
        "tavsiye": analiz.summary.get("RECOMMENDATION", "BİLİNMİYOR"),
        "al": analiz.summary.get("BUY", 0),
        "sat": analiz.summary.get("SELL", 0),
        "notr": analiz.summary.get("NEUTRAL", 0),
        "ADX": g.get("ADX", 0), "RSI": g.get("RSI", 0), "MACD": g.get("MACD.macd", 0),
        "Stoch": g.get("Stoch.K", 0), "CCI": g.get("CCI20", 0), "Mom": g.get("Mom", 0),
        "EMA20": g.get("EMA20", 0), "SMA50": g.get("SMA50", 0), "SMA200": g.get("SMA200", 0),
        "kapanis": g.get("close", 0),
    }

@bot.message_handler(commands=["analiz"])
async def tv_analiz(message):
    komut = message.text.split()
    if len(komut) < 2:
        await bot.reply_to(message, "Kral hangi coini inceleyeyim? Örnek: <code>/analiz BTC 4s</code>")
        return

    coin = re.sub(r"(USDT|USD|TRY)$", "", komut[1].upper())
    periyot, periyot_adi = Interval.INTERVAL_1_DAY, "Günlük"
    if len(komut) > 2 and komut[2].lower() in ZAMAN_HARITASI:
        periyot, periyot_adi = ZAMAN_HARITASI[komut[2].lower()]

    bekleme = await bot.reply_to(
        message, f"📡 <b>{coin} ({periyot_adi})</b> verileri çekiliyor..."
    )

    try:
        tv, fng, ls, fr = await asyncio.gather(
            asyncio.to_thread(_tv_cek, coin, periyot),
            korku_acgozluluk(),
            long_short(coin),
            funding(coin),
            return_exceptions=True,
        )
        if isinstance(tv, Exception):
            raise tv
    except Exception as e:
        await guvenli_duzenle(
            message.chat.id, bekleme.message_id,
            f"❌ <b>{coin}USDT</b> Binance'de bulunamadı veya veri çekilemedi.\n<i>{html.escape(str(e)[:150])}</i>",
        )
        return

    r = lambda x: round(float(x or 0), 2)

    ozet = (
        f"Periyot: {periyot_adi}, Fiyat: {tv['kapanis']}, Sinyal: {tv['tavsiye']} "
        f"(Al:{tv['al']} Sat:{tv['sat']} Nötr:{tv['notr']}), ADX: {r(tv['ADX'])}, RSI: {r(tv['RSI'])}, "
        f"Stoch: {r(tv['Stoch'])}, MACD: {r(tv['MACD'])}, CCI: {r(tv['CCI'])}, Mom: {r(tv['Mom'])}, "
        f"EMA20: {r(tv['EMA20'])}, SMA50: {r(tv['SMA50'])}, SMA200: {r(tv['SMA200'])}"
    )
    if isinstance(fng, dict):
        ozet += f", Piyasa Duygusu: {fng['deger']}/100 {fng['etiket']}"
    if isinstance(ls, dict):
        ozet += f", Long/Short: {ls['oran']:.2f}"
    if isinstance(fr, float):
        ozet += f", Funding: %{fr:.4f}"

    await guvenli_duzenle(
        message.chat.id, bekleme.message_id,
        f"🧠 Veri geldi, {periyot_adi} grafik yorumlanıyor..."
    )

    motor_adi, yorum = await ai_yanit_al(ozet, analiz_mi=True, hafiza_kullan=False)

    sonuc = (
        f"📊 <b>PRO ANALİZ: {coin}</b> ⏳ <b>({periyot_adi})</b>\n"
        f"💵 <b>Fiyat:</b> <code>{tv['kapanis']}</code>\n"
        f"📈 <b>Genel Sinyal:</b> <code>{tv['tavsiye']}</code> "
        f"(🟢{tv['al']} / 🔴{tv['sat']} / ⚪{tv['notr']})\n"
        f"🌊 <b>Trend Gücü (ADX):</b> <code>{r(tv['ADX'])}</code>\n"
        f"⚡ <b>RSI:</b> <code>{r(tv['RSI'])}</code> | <b>Stoch:</b> <code>{r(tv['Stoch'])}</code>\n"
        f"🌀 <b>MACD:</b> <code>{r(tv['MACD'])}</code> | <b>CCI:</b> <code>{r(tv['CCI'])}</code>\n"
        f"🚀 <b>Momentum:</b> <code>{r(tv['Mom'])}</code>\n"
        f"🎯 <b>EMA20:</b> <code>{r(tv['EMA20'])}</code>\n"
        f"🛡️ <b>SMA50:</b> <code>{r(tv['SMA50'])}</code> | <b>SMA200:</b> <code>{r(tv['SMA200'])}</code>\n"
    )
    if isinstance(fng, dict):
        sonuc += f"😨 <b>Piyasa Duygusu:</b> <code>{fng['deger']}/100</code> ({fng['etiket']})\n"
    if isinstance(ls, dict):
        sonuc += f"⚔️ <b>Long/Short:</b> <code>{ls['oran']:.2f}</code> (🟢%{ls['long']:.0f} / 🔴%{ls['short']:.0f})\n"
    if isinstance(fr, float):
        sonuc += f"💸 <b>Funding:</b> <code>%{fr:.4f}</code>\n"

    sonuc += (
        f"\n🤖 <b>EMRE AI YORUMU</b>\n"
        f"<blockquote>⚡ [{motor_adi}]\n\n{yorum}</blockquote>\n"
        f"<i>⚠️ YTD (Yatırım Tavsiyesi Değildir)</i>"
    )
    await guvenli_duzenle(message.chat.id, bekleme.message_id, sonuc)

# ----------------------------------------------------------------------------
# SERBEST SOHBET + HIZLI HESAP
# ----------------------------------------------------------------------------

MIKTAR_DESENI = re.compile(
    r"(?i)\b(\d+(?:[.,]\d+)?)\s*(?:adet|tane)?\s*([A-Za-z]{2,10})\b"
)

async def hizli_hesap(mesaj: str) -> Tuple[str, bool]:
    eslesme = MIKTAR_DESENI.search(mesaj)
    if not eslesme:
        return "", False

    miktar = float(eslesme.group(1).replace(",", "."))
    ham = eslesme.group(2).upper()
    takma = {"ALTIN": "PAXG", "GOLD": "PAXG", "GUMUS": "PAXG", "BITCOIN": "BTC", "ETHER": "ETH"}
    coin = takma.get(ham, ham)

    semboller = await binance_sembolleri()
    if coin not in semboller:
        return "", False

    veri, kur = await asyncio.gather(fiyat_getir(coin), usdt_try())
    if not veri:
        return "", False

    toplam_usd = miktar * veri["fiyat"]
    metin = (
        f"🧮 <b>HIZLI HESAP ({miktar:g} {coin})</b>\n"
        f"💵 <b>${toplam_usd:,.2f}</b>\n"
    )
    if kur:
        metin += f"🇹🇷 <b>₺{toplam_usd * kur:,.2f}</b>\n"
    metin += f"<i>Birim: ${veri['fiyat']:,.4f} • 24s %{veri['degisim']:+.2f}</i>"

    kalan = MIKTAR_DESENI.sub("", mesaj).strip().lower()
    kalan = re.sub(r"[^\wçşğüöı ]", "", kalan)
    sadece_hesap = len(kalan) < 12 or kalan in {
        "kaç", "kac", "kaç tl", "kac tl", "ne kadar", "hesapla", "kaç dolar", "kac dolar", "eder"
    }
    return metin, sadece_hesap

@bot.message_handler(func=lambda m: bool(m.text))
async def serbest_sohbet(message):
    mesaj = message.text

    hesap_metni, sadece_hesap = await hizli_hesap(mesaj)
    if hesap_metni and sadece_hesap:
        await bot.reply_to(message, hesap_metni)
        return

    mesaj_kucuk = mesaj.lower()
    cagrildi = any(re.search(rf"\b{k}\b", mesaj_kucuk) for k in TETIKLEYICILER)
    yanit_mi = bool(
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.is_bot
    )
    ozel_mi = message.chat.type == "private"
    if not (cagrildi or yanit_mi or ozel_mi):
        return

    if cok_hizli_mi(message.from_user.id):
        return

    bekleme = await bot.reply_to(message, "🧠 Karargah düşünüyor...")
    kontekst = await piyasa_konteksti(mesaj)

    motor_adi, yanit = await ai_yanit_al(
        mesaj,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        kontekst=kontekst,
    )

    sonuc = f"<blockquote>{yanit}</blockquote>\n<i>⚡ {motor_adi}</i>"
    if hesap_metni:
        sonuc += f"\n\n{hesap_metni}"
    await guvenli_duzenle(message.chat.id, bekleme.message_id, sonuc)

# ----------------------------------------------------------------------------
# ARKA PLAN GÖREVİ + BAŞLATICI + MENÜ KURULUMU
# ----------------------------------------------------------------------------

async def bakimci():
    while True:
        try:
            hafiza.budama()
            await binance_sembolleri()
        except Exception as e:
            log.debug("Bakim hatasi: %s", e)
        await asyncio.sleep(600)

async def main():
    await binance_sembolleri()
    asyncio.create_task(bakimci())
    
    # --- MENÜYÜ BURAYA EKLİYORUZ ---
    try:
        komutlar = [
            BotCommand("start", "👑 Ana menü ve komut listesi"),
            BotCommand("analiz", "📊 Canlı TradingView sinyali (örn: /analiz BTC 1s)"),
            BotCommand("piyasa", "🚀 En çok yükselen ve düşen coinler"),
            BotCommand("duygu", "😨 Korku/Açgözlülük ve Long/Short oranı"),
            BotCommand("unut", "🧹 Sohbet hafızasını temizler")
        ]
        await bot.set_my_commands(komutlar)
        log.info("Telegram komut menüsü basariyla ayarlandi.")
    except Exception as e:
        log.warning("Menu ayarlanamadi: %s", e)
    # -------------------------------

    aktif = [m.isim for m in MOTORLAR if os.environ.get(m.env)]
    log.info("Emre AI V15 ayakta. Aktif motorlar: %s", ", ".join(aktif) or "YOK")
    try:
        await bot.infinity_polling(timeout=30, request_timeout=60)
    finally:
        if _session and not _session.closed:
            await _session.close()

if __name__ == "__main__":
    asyncio.run(main())
