"""SQL üretimi (G-01, G-03, G-15, G-16) — Ollama yerel varsayılan, OpenAI-uyumlu API opsiyonel.

G-16: API moduna giden istemde kişisel veri değeri bulunamaz — istem yalnız şema
metaverisi + soru içerir; soru içindeki TCKN benzeri diziler yine de maskelenir.
"""
import json
import logging
import re

import requests

from app import config

_log = logging.getLogger(__name__)

# API çağrısı başarısız olduğunda yerele düşülür. Bu bilinçli bir tasarım
# (Böl. 9 son-değer davranışı) ama SESSİZ olması bilinçli değildi: hatanın
# ne olduğunu kimse görmüyordu ve saha teşhisi imkânsızdı — anahtar süresi mi
# doldu, kota mı bitti, ağ mı kapalı, hiçbiri ayırt edilemiyordu (İP-15).
# Son hata burada tutulur; arayüz mod etiketinin yanında gösterebilir.
SON_API_HATASI: str | None = None


def _api_dususu(e: Exception, nerede: str) -> None:
    global SON_API_HATASI
    SON_API_HATASI = f"{type(e).__name__}: {str(e)[:200]}"
    _log.warning("API modu başarısız (%s), yerel modele düşülüyor: %s",
                 nerede, SON_API_HATASI)


class LlmError(RuntimeError):
    """Model servisine ulaşılamadı / model hata verdi — kullanıcıya anlaşılır mesaj."""


def _ollama_chat(messages: list) -> str:
    """Ollama'ya istek atar; ağ/HTTP hatalarını anlaşılır LlmError'a çevirir."""
    try:
        r = requests.post(f"{config.OLLAMA_URL}/api/chat", json={
            "model": config.LOCAL_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": config.TEMPERATURE,
                    "seed": config.SEED,
                    "num_predict": config.NUM_PREDICT,
                    "num_ctx": config.NUM_CTX},
        }, timeout=120)
    except requests.exceptions.ConnectionError:
        raise LlmError(
            f"Ollama'ya ulaşılamadı ({config.OLLAMA_URL}). Ollama çalışıyor mu? "
            "Kurulu değilse https://ollama.com adresinden kurun; kuruluysa uygulamayı başlatın.")
    except requests.exceptions.Timeout:
        raise LlmError(
            "Yerel model 120 saniyede yanıt vermedi. Makine yoğun olabilir; "
            "biraz bekleyip yeniden deneyin veya daha küçük bir model seçin.")
    if not r.ok:
        detay = ""
        try:
            detay = r.json().get("error", "")[:200]
        except Exception:
            detay = r.text[:200]
        raise LlmError(
            f"Yerel model hata verdi (HTTP {r.status_code}). {detay}\n"
            f"Terminalde şunu deneyin: ollama run {config.LOCAL_MODEL} \"merhaba\" — "
            "o da hata veriyorsa Ollama'yı ve GPU sürücünüzü güncelleyin ya da CPU'ya zorlayın "
            "(OLLAMA_LLM_LIBRARY=cpu_avx2).")
    return r.json()["message"]["content"]

# İstem sertleştirmesi (İP-03b) — her kural, 2026-08-16 baseline ölçümünde
# GÖZLENMİŞ bir hata türüne karşılık gelir. Kural eklerken ölçümü kaynak göster.
SYSTEM_PROMPT = """Sen Türkçe soruları SQL'e çeviren bir asistansın. Kurallar:

1. YALNIZCA SQLite lehçesinde tek bir SELECT sorgusu üret. Başka hiçbir şey yazma.

2. Tablo ve kolon adlarını şemada YAZILDIĞI GİBİ, harfi harfine kopyala.
   Türkçe adları İngilizceye ÇEVİRME. Şemada 'cinsiyet' yazıyorsa 'sex' ya da
   'gender' yazma; 'doktor_id' yazıyorsa 'doctor_id' yazma. Şemada olmayan hiçbir
   tablo ya da kolon adı kullanma.

3. Birleştirme (JOIN) koşullarını "JOIN YOLLARI" bölümünden aynen al. Kendin
   ilişki tahmin etme. Bir tablo çifti için birden fazla yol verilmişse sorunun
   anlamına uygun olanı seç ve seçimini aciklama alanında bir cümleyle belirt.
   İki tabloyu birleştirmek için ara tablolardan geçmen gerekiyorsa, yoldaki
   TÜM tabloları sorguya dahil et.

4. Sayılar, oranlar ve toplamlar HESAPLANIR, kolon olarak aranmaz.
   'kaç', 'sayısı', 'toplam', 'ortalama', 'oran' geçen sorularda COUNT / SUM /
   AVG kullan. 'randevu_sayisi' ya da 'gelme_orani' gibi bir kolon şemada
   yoksa onu sen hesapla.

5. [TARIH ARALIĞI: ...] açıklaması varsa o mutlak tarihleri kullan; kendin tarih
   hesaplama.

6. TERIM tanımları iş terimlerinin şema karşılığıdır; onlara uy.

7. Çıktını şu JSON ile ver: {"sql": "...", "guven": 0.0-1.0, "aciklama": "tek cümle"}
   guven: sorunun şemayla ne kadar net eşleştiğine dair dürüst öz değerlendirmen.
   Soru belirsizse ya da hangi birleştirme yolunun doğru olduğundan emin değilsen
   guven değerini 0.6'nın altında ver ve aciklama alanına neyin eksik olduğunu yaz.
   Emin olmadığın halde yüksek guven vermek, yanlış cevabı doğru gibi göstermek
   demektir; bu en kötü sonuçtur.

ÖRNEK 1
SORU: Kadın hastaların sayısı nedir?
JSON: {"sql": "SELECT COUNT(*) FROM hasta WHERE cinsiyet = 'K'", "guven": 0.95,
"aciklama": "hasta tablosundaki cinsiyet kolonu sayıldı"}

ÖRNEK 2 (ara tablolardan geçen birleştirme)
JOIN YOLLARI satırı: doktor <-> fatura: randevu.doktor_id = doktor.doktor_id AND
muayene.randevu_id = randevu.randevu_id AND fatura.muayene_id = muayene.muayene_id
SORU: En çok fatura tutarı üreten 5 doktor kim?
JSON: {"sql": "SELECT d.ad, d.soyad, SUM(f.tutar) AS toplam FROM doktor d JOIN randevu r
ON r.doktor_id = d.doktor_id JOIN muayene m ON m.randevu_id = r.randevu_id JOIN fatura f
ON f.muayene_id = m.muayene_id GROUP BY d.doktor_id ORDER BY toplam DESC LIMIT 5",
"guven": 0.9, "aciklama": "verilen yol izlendi, tutar toplandı"}"""

_TCKN = re.compile(r"\b\d{11}\b")


def mask_question(q: str) -> str:
    """G-16: soru içinde geçebilecek kimlik benzeri değerleri maskele (API modu)."""
    return _TCKN.sub("[KIMLIK-NO]", q)


_SQL_BASI = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)


def _sql_gibi_mi(metin: str) -> bool:
    """Model bazen istemin bir parçasını (şema, terim sözlüğü) SQL alanına kopyalıyor.
    Böyle bir metni doğrulama katmanına vermek, orayı çöp ayıklayıcısı yapar."""
    return bool(_SQL_BASI.match(metin or ""))


def _parse(content: str) -> dict:
    m = re.search(r"\{.*\}", content, re.DOTALL)
    if not m:
        # model düz SQL döndürdüyse tolere et
        sql = re.sub(r"^```(sql)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
        if not _sql_gibi_mi(sql):
            return {"sql": "", "guven": 0.0,
                    "aciklama": "Model, SELECT ile başlayan bir sorgu üretmedi."}
        return {"sql": sql, "guven": 0.5, "aciklama": ""}
    try:
        d = json.loads(m.group(0))
        return {"sql": d.get("sql", ""), "guven": float(d.get("guven", 0.5)),
                "aciklama": d.get("aciklama", "")}
    except (json.JSONDecodeError, ValueError):
        return {"sql": "", "guven": 0.0, "aciklama": "Model çıktısı çözümlenemedi."}


def _user_prompt(question: str, context: str) -> str:
    return f"ŞEMA VE TERIMLER:\n{context}\n\nSORU: {question}\n\nJSON:"


def generate_local(question: str, context: str) -> dict:
    content = _ollama_chat([{"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": _user_prompt(question, context)}])
    return _parse(content)


def generate_api(question: str, context: str) -> dict:
    """G-15/G-16: opsiyonel dış servis — soru maskeli gider, veri değeri asla gitmez."""
    r = requests.post(f"{config.API_BASE}/chat/completions",
                      headers={"Authorization": f"Bearer {config.API_KEY}"},
                      json={"model": config.API_MODEL,
                            "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                         {"role": "user",
                                          "content": _user_prompt(mask_question(question), context)}],
                            "temperature": config.TEMPERATURE},
                      timeout=60)
    r.raise_for_status()
    return _parse(r.json()["choices"][0]["message"]["content"])


def generate(question: str, context: str, mode: str = None) -> tuple[dict, str]:
    """Dönen: (sonuç, kullanılan mod). API başarısızsa yerele düşer (Böl. 9 son-değer)."""
    mode = mode or config.MODE
    if mode == "api" and config.API_KEY:
        try:
            return generate_api(question, context), "api"
        except Exception as e:      # noqa: BLE001 - son-değer: yerele düş, ama SESSİZCE DEĞİL
            _api_dususu(e, "generate")
    return generate_local(question, context), "local"


def repair(question: str, context: str, bad_sql: str, error: str,
           mode: str = None) -> tuple[dict, str]:
    """Öz-onarım (DIN-SQL yaklaşımı): hatalı SQL + hata mesajı modele geri verilir,
    tek düzeltme denemesi yapılır. Pipeline en fazla bir kez çağırır."""
    fix_prompt = (f"{_user_prompt(question, context)}\n\n"
                  f"ÖNCEKİ DENEMEN:\n{bad_sql}\n\n"
                  f"HATA: {error}\n\n"
                  "Bu hatayı düzelt. Yalnızca şemada VAR OLAN tablo ve kolonları kullan; "
                  "ILISKILER satırlarındaki FK yönlerine dikkat et. Aynı JSON formatında cevap ver.")
    mode = mode or config.MODE
    if mode == "api" and config.API_KEY:
        try:
            r = requests.post(f"{config.API_BASE}/chat/completions",
                              headers={"Authorization": f"Bearer {config.API_KEY}"},
                              json={"model": config.API_MODEL,
                                    "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                                 {"role": "user", "content": mask_question(fix_prompt)}],
                                    "temperature": config.TEMPERATURE},
                              timeout=60)
            r.raise_for_status()
            return _parse(r.json()["choices"][0]["message"]["content"]), "api"
        except Exception as e:      # noqa: BLE001 - son-değer: yerele düş, ama SESSİZCE DEĞİL
            _api_dususu(e, "repair")
    content = _ollama_chat([{"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": fix_prompt}])
    return _parse(content), "local"
