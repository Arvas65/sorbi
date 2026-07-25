"""SQL üretimi (G-01, G-03, G-15, G-16) — Ollama yerel varsayılan, OpenAI-uyumlu API opsiyonel.

G-16: API moduna giden istemde kişisel veri değeri bulunamaz — istem yalnız şema
metaverisi + soru içerir; soru içindeki TCKN benzeri diziler yine de maskelenir.
"""
import json
import re

import requests

from app import config


class LlmError(RuntimeError):
    """Model servisine ulaşılamadı / model hata verdi — kullanıcıya anlaşılır mesaj."""


def _ollama_chat(messages: list) -> str:
    """Ollama'ya istek atar; ağ/HTTP hatalarını anlaşılır LlmError'a çevirir."""
    try:
        r = requests.post(f"{config.OLLAMA_URL}/api/chat", json={
            "model": config.LOCAL_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 400},
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

SYSTEM_PROMPT = """Sen Türkçe soruları SQL'e çeviren bir asistansın. Kurallar:
1. YALNIZCA SQLite lehçesinde tek bir SELECT sorgusu üret. Başka hiçbir şey yazma.
2. Yalnızca sana verilen şemadaki tablo ve kolonları kullan. Tablo/kolon UYDURMA.
3. [TARIH ARALIĞI: ...] açıklaması varsa o mutlak tarihleri kullan; kendin tarih hesaplama.
4. TERIM tanımları iş terimlerinin şema karşılığıdır; onlara uy.
5. Çıktını şu JSON ile ver: {"sql": "...", "guven": 0.0-1.0, "aciklama": "tek cümle"}
   guven: sorunun şemayla ne kadar net eşleştiğine dair dürüst öz değerlendirmen.
   Soru belirsizse guven değerini 0.6'nın altında ver ve aciklama alanına hangi
   bilginin eksik olduğunu yaz."""

_TCKN = re.compile(r"\b\d{11}\b")


def mask_question(q: str) -> str:
    """G-16: soru içinde geçebilecek kimlik benzeri değerleri maskele (API modu)."""
    return _TCKN.sub("[KIMLIK-NO]", q)


def _parse(content: str) -> dict:
    m = re.search(r"\{.*\}", content, re.DOTALL)
    if not m:
        # model düz SQL döndürdüyse tolere et
        sql = re.sub(r"^```(sql)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
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
                            "temperature": 0.1},
                      timeout=60)
    r.raise_for_status()
    return _parse(r.json()["choices"][0]["message"]["content"])


def generate(question: str, context: str, mode: str = None) -> tuple[dict, str]:
    """Dönen: (sonuç, kullanılan mod). API başarısızsa yerele düşer (Böl. 9 son-değer)."""
    mode = mode or config.MODE
    if mode == "api" and config.API_KEY:
        try:
            return generate_api(question, context), "api"
        except Exception:
            pass  # yerel moda düş
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
                                    "temperature": 0.1},
                              timeout=60)
            r.raise_for_status()
            return _parse(r.json()["choices"][0]["message"]["content"]), "api"
        except Exception:
            pass
    content = _ollama_chat([{"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": fix_prompt}])
    return _parse(content), "local"
