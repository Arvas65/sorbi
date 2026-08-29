"""SorBI yapılandırması. Ortam değişkenleriyle ezilebilir."""
import os
from datetime import date

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Model (ADR-1/5) ---
MODE = os.getenv("SORBI_MODE", "local")            # local | api
OLLAMA_URL = os.getenv("SORBI_OLLAMA_URL", "http://localhost:11434")
# Taban model — ADR-1 rev.2 (2026-08-16). Ölçümle seçildi, tahminle değil:
# aynı 50 soruluk sette qwen2.5-coder:7b %68, llama3.2:3b %38 (McNemar
# p = 2,8e-4). Varsayılan 2026-08-21'e kadar hâlâ 3b'ydi — karar yazıldı ama
# koda inmemişti; `--doctor` çıktısında yakalandı. Karar ile kod arasındaki
# bu boşluk sessizce yanlış modeli ölçmemize yol açacaktı.
LOCAL_MODEL = os.getenv("SORBI_LOCAL_MODEL", "qwen2.5-coder:7b-instruct")
# Bağlam penceresi. Ollama varsayılanı 4096; şema + JOIN yolları + istem bunu
# zorlayabilir ve AŞAN KISIM SESSİZCE KIRPILIR — model şemanın bir bölümünü hiç
# görmeden cevap üretir. Bu, sessiz yanlışın (B-7) fark edilmesi en zor kaynağıdır.
NUM_CTX = int(os.getenv("SORBI_NUM_CTX", "8192"))
NUM_PREDICT = int(os.getenv("SORBI_NUM_PREDICT", "400"))
# Belirlenimci üretim. temperature=0.1 ve sabit olmayan tohum, aynı istem için
# koşumdan koşuma farklı SQL üretiyordu; 50 soruluk bir sette bu ±7 puanlık
# gürültü demek (saha kaydı 2026-08-16: aynı gün dört ölçüm, farkların hiçbiri
# istatistiksel olarak ayırt edilebilir değildi). A/B karşılaştırması yapabilmek
# için üretim önce TEKRARLANABİLİR olmalı.
TEMPERATURE = float(os.getenv("SORBI_TEMPERATURE", "0"))
SEED = int(os.getenv("SORBI_SEED", "42"))
# OpenAI-uyumlu uç nokta. Varsayılan Gemini'nin uyumluluk katmanı: İhsan'ın
# ücretsiz anahtarı var ve yerel 7B modelin p95'i 32,8 sn (G-12 hedefi 10 sn).
# Başka bir sağlayıcı için yalnız bu üç değişken değişir; kod aynı kalır.
API_BASE = os.getenv("SORBI_API_BASE",
                     "https://generativelanguage.googleapis.com/v1beta/openai")
API_KEY = os.getenv("SORBI_API_KEY", "")
API_MODEL = os.getenv("SORBI_API_MODEL", "gemini-3.7-flash")
# Ücretsiz katmanda istekler arası bekleme (sn). Hız sınırına takılmamak
# ölçümü kurtarır: 429 alan bir soru, modelin bilmediği bir soru gibi
# görünür ve doğruluğu sahte biçimde düşürür.
API_BEKLEME_S = float(os.getenv("SORBI_API_BEKLEME", "0"))

# `seed` isteğe konsun mu (BULGU-08/17).
#   boş / "auto" -> gönder, uç nokta reddederse bir kez alansız dene ve hatırla
#   "0"          -> hiç gönderme
#   "1"          -> her zaman gönder (reddedilirse hata görünür kalsın)
# Varsayılan `auto`: Gemini'nin OpenAI katmanı bu alanı tanımıyor
# (HTTP 400 "Unknown name \"seed\""), OpenAI ve vLLM tanıyor. Sağlayıcıya
# göre elle ayar yapmak zorunda kalmak, unutulan bir bayrak demektir.
_seed_ayar = os.getenv("SORBI_API_SEED", "auto").strip().lower()
API_SEED_GONDER = None if _seed_ayar in ("", "auto") else _seed_ayar not in ("0", "false", "hayir")

# --- Veritabanı (G-14) ---
DB_URL = os.getenv("SORBI_DB_URL", f"sqlite:///{os.path.join(HERE, 'demo', 'hospital.db')}")
TARGET_DIALECT = os.getenv("SORBI_DIALECT", "sqlite")   # sqlite | postgres | tsql | mysql (ADR-4)
QUERY_TIMEOUT_S = int(os.getenv("SORBI_TIMEOUT", "30"))
MAX_ROWS = int(os.getenv("SORBI_MAX_ROWS", "1000"))

# --- RAG (ADR-3) ---
CHROMA_DIR = os.getenv("SORBI_CHROMA_DIR", os.path.join(HERE, ".chroma"))
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K_TABLES = 6
# Düşük kardinaliteli kolonların gerçek değerlerini İSTEME EKLE (bkz. schema_rag).
# API modunda KAPATILMALIDIR: bu değerler gerçek veridir ve dış servise gider.
#
# DİKKAT (İP-19): bu bayrak yalnız İSTEMİ etkiler, örneklemeyi değil. Değerler
# her hâlükârda okunur ve güven kontrolüne (B-7) verilir — o kontrol tamamen
# yerelde koşar, hiçbir şey dışarı çıkmaz. Kapatmayı okumaya bağlamak, API
# modunda en isabetli sessiz-yanlış sinyalini boşuna susturuyordu.
ORNEK_DEGERLER = os.getenv("SORBI_ORNEK_DEGER", "1") not in ("0", "false", "False")

# --- Güven eşiği (G-03) ---
CONFIDENCE_THRESHOLD = 0.6

# --- Sessiz yanlış taraması (B-7 / İP-03c) ---
# Bir kontrol ancak ÖLÇÜLMÜŞ yanlış alarm oranı yüzünden kapatılır; koddan
# silmek yerine kapatmak, sonraki ölçümün aynı çizelgeyle karşılaştırılmasını
# sağlar. `SORBI_GUVEN_KAPALI=` (boş) vererek hepsi açılabilir.
#
# Varsayılan kapalı ikili — mutasyon karnesi (101 gold + 240 mutant):
#
#   hepsi açık                    yakalama %82,5   yanlış alarm %6,9 (7/101)
#   sema_ortusmez kapalı          yakalama %81,7   yanlış alarm %2,0 (2/101)
#   + bicim_sayi kapalı           yakalama %81,2   yanlış alarm %1,0 (1/101)
#
# 1,3 puan yakalama karşılığında yanlış alarm yediye bölünüyor. Bu takas
# bilerek yapıldı: sürekli bağıran bir uyarı okunmaz hâle gelir ve o noktadan
# sonra sessiz yanlış geri döner — yani gürültü, kaçırmadan pahalıdır.
_GUVEN_KAPALI_VARSAYILAN = "sema_ortusmez,bicim_sayi"
GUVEN_KAPALI = {k.strip() for k in
                os.getenv("SORBI_GUVEN_KAPALI", _GUVEN_KAPALI_VARSAYILAN).split(",")
                if k.strip()}

# --- Ölçüm referans tarihi (İP-23) ---
# Test setinin 101 sorusundan 13'ü zamana bağlı ("geçen ay", "son 7 gün",
# "bugün"). Demo verisi 2026-08-16'da tohumlandı ve orada bitiyor; gerçek
# takvim ilerledikçe bu sorular sessizce boşalıyor. 2026-08-20'de "bugün
# bekleyen randevu" artık HER ZAMAN 0 dönüyordu — yani cetvelin kendisi
# çürüyordu ve iki ölçüm arasındaki fark koda mı takvime mi ait, ayırt
# edilemiyordu.
#
# `SORBI_BUGUN` verilirse "bugün" o güne sabitlenir: hem soru ön işlemesi
# (G-07) hem SQL içindeki date('now') aynı günü görür. Ölçüm koşucuları
# bunu varsayılan olarak açar; üretimde boştur, yani gerçek bugün geçerlidir.
BUGUN = os.getenv("SORBI_BUGUN", "").strip()


def bugun() -> date:
    """Ölçümlerin 'bugün'ü. SORBI_BUGUN yoksa gerçek tarih.

    Bozuk bir değerde SESSİZCE bugüne düşmez, hata verir. Yazım hatası olan
    bir referans tarih (`SORBI_BUGUN=2026-8-16`) sessizce gerçek takvime
    düşseydi, ölçüm bozulur ve bunu kimse fark etmezdi — B-7'de kovaladığımız
    sessiz yanlışın ölçüm hattındaki tam karşılığı bu olurdu.
    """
    if not BUGUN:
        return date.today()
    try:
        return date.fromisoformat(BUGUN)
    except ValueError as e:
        raise ValueError(
            f"SORBI_BUGUN geçersiz: {BUGUN!r}. YYYY-AA-GG bekleniyor "
            f"(örn. 2026-08-16). Ölçümü gerçek tarihle koşmak için "
            f"değişkeni tümden kaldırın.") from e


# --- Dosyalar ---
GLOSSARY_PATH = os.path.join(HERE, "demo", "glossary.json")
AUDIT_DB = os.getenv("SORBI_AUDIT_DB", os.path.join(HERE, ".audit.db"))
