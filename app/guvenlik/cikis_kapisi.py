"""Çıkış kapısı (ADR-10 § 3.3/5) — makineden dışarı giden HER LLM isteğinin tek denetimi.

`generator._api_chat` ilk iş olarak `kontrol()` çağırır. Kapı iki şey sorar:

1. **Bu çağrının izni var mı?** İzin yalnız `izin(db_url)` bağlamının içinde ve
   yalnız mod kararı (ADR-5 B, `akis.mod.cikarim_modu`) o bağlantı için API
   dediyse vardır. Varsayılan KAPALIDIR: izin bağlamı kurmayı unutan yeni bir
   kod yolu dışarı veri yollayamaz, engellenir. v3 yolunun İP-45 kilidini
   atlaması (bulgu 2026-09-30) tam olarak bu varsayımın tersiyle olmuştu.
2. **Gövdede hâlâ kişisel veri var mı?** Doğrulanmış algılayıcılar (TCKN, VKN,
   IBAN, kart, e-posta, telefon) ve o isteğe özgü yasaklı değerler (anlam
   modeli sözlüğünün gerçek değerleri). Tek bir bulgu, isteği durdurur.

Engelleme iletisi değer TAŞIMAZ, yalnız tür: ileti log'a ve arayüze gider.

Kapı bir ayarla kapatılamaz (değişmez 3). Yanlış pozitif, algılayıcı
düzeltilerek giderilir.
"""
from __future__ import annotations

import contextvars
from collections.abc import Iterable, Iterator
from contextlib import contextmanager

from app.akis.mod import API, ModKarari, cikarim_modu
from app.guvenlik.kisisel_veri import dogrulanmis, tr_kucuk


class GuvenlikEngeli(RuntimeError):
    """Dışarı gidecek istek güvenlik kapısında durduruldu. Hiçbir şey gönderilmedi."""


_izinli_baglanti: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "sorbi_api_izni", default=None)
_yasakli: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar(
    "sorbi_yasakli_degerler", default=())


@contextmanager
def izin(db_url: str, yasakli_degerler: Iterable[str] = (),
         istenen: str = API) -> Iterator[ModKarari]:
    """Bu bloğun içinde, `db_url` için API izinliyse dış çağrı yapılabilir.

    Dönen `ModKarari` çağırana ne olduğunu söyler; izin verilmediyse blok yine
    çalışır ama içindeki her `_api_chat` çağrısı `GuvenlikEngeli` ile durur.
    """
    karar = cikarim_modu(db_url, istenen)
    t1 = _izinli_baglanti.set(db_url if karar.mod == API else None)
    t2 = _yasakli.set(tuple(str(v) for v in yasakli_degerler if str(v).strip()))
    try:
        yield karar
    finally:
        _izinli_baglanti.reset(t1)
        _yasakli.reset(t2)


def _metinler(mesajlar) -> Iterator[str]:
    for m in mesajlar or ():
        if isinstance(m, dict):
            icerik = m.get("content")
            if isinstance(icerik, str):
                yield icerik
            elif isinstance(icerik, list):          # çok parçalı içerik biçimi
                for p in icerik:
                    if isinstance(p, dict) and isinstance(p.get("text"), str):
                        yield p["text"]
        elif isinstance(m, str):
            yield m


def denetle(mesajlar) -> list[str]:
    """Gövdedeki sorunların TÜR listesi (değer içermez). Boş = temiz."""
    sorunlar: list[str] = []
    yasakli = [(v, tr_kucuk(v)) for v in _yasakli.get()]
    for metin in _metinler(mesajlar):
        for b in dogrulanmis(metin):
            sorunlar.append(b.tur)
        if yasakli:
            kucuk = tr_kucuk(metin)
            for _, kv in yasakli:
                if _geciyor(kucuk, kv):
                    sorunlar.append("SOZLUK_DEGERI")
                    break
    return sorted(set(sorunlar))


def _geciyor(kucuk_metin: str, kucuk_deger: str) -> bool:
    """Anonimleştiriciyle AYNI eşleşme kuralı: başta sözcük sınırı, sonda ek
    serbest (Türkçe eklemeli); üç harften kısa değer yalnız tam sözcük.
    İki taraf farklı kural kullansaydı kapı, anonimleştiricinin bilerek
    geçirdiği şeyde alarm verir ya da jetonlamadığı şeyi kaçırırdı."""
    i = kucuk_metin.find(kucuk_deger)
    while i >= 0:
        j = i + len(kucuk_deger)
        bas_sinir = i == 0 or not kucuk_metin[i - 1].isalnum()
        son_sinir = len(kucuk_deger) >= 3 or j >= len(kucuk_metin) or not kucuk_metin[j].isalnum()
        if bas_sinir and son_sinir:
            return True
        i = kucuk_metin.find(kucuk_deger, i + 1)
    return False


def kontrol(mesajlar) -> None:
    """Gönderimden hemen önce çağrılır. Temizse döner, değilse `GuvenlikEngeli`."""
    if _izinli_baglanti.get() is None:
        raise GuvenlikEngeli(
            "Dış LLM çağrısı durduruldu: bu bağlantı için API izni yok. API modu "
            "yalnız sentetik demo veritabanlarında açılır (ADR-5 B, ADR-10). "
            "Hiçbir veri gönderilmedi.")
    sorunlar = denetle(mesajlar)
    if sorunlar:
        raise GuvenlikEngeli(
            "Dış LLM çağrısı durduruldu: gövdede kişisel veri kaldı "
            f"({', '.join(sorunlar)}). Hiçbir veri gönderilmedi.")
