"""Eşleyici (İP-53a) — `Esleyici` portunun LLM uygulaması. Hattın TEK stokastik parçası.

Görevi dar: Türkçe soruyu anlam modelinin SÖZLÜĞÜNDEKİ adlarla bir `Secim`e
çevirmek. SQL yazmaz, kolon adı görmez, tarih hesaplamaz.

Üç iş LLM'den bilinçli olarak alındı ve yerelde, deterministik yapılır:

1. **Tarih aralığı.** "geçen ay" → `preprocess.resolve_dates`. Model bir
   takvim değildir; v3'te göreli tarihler en sık sessiz yanlış kaynağıydı.
2. **Filtre değerinin sözlüğe oturtulması.** Model kullanıcının yazdığını
   yazar ("kardiyoloji"); onu sözlükteki kanonik değere ("Kardiyoloji")
   Türkçe büyük/küçük harf kuralıyla burada biz bağlarız.
3. **Değerlerin gizliliği.** API modunda (ADR-5 B, değişmez 3) sözlükteki
   değer listeleri gerçek kolon değerleridir ve dışarı ÇIKMAZ: isteme yalnız
   ölçü/boyut adları gider. (2) sayesinde doğruluk bundan etkilenmez.
4. **Sorunun anonimleştirilmesi** (ADR-10). API modunda soru dışarı çıkmadan
   önce jetonlanır: kişi adı, TCKN, IBAN, sözlük değeri ... → `[KISI_1]`,
   `[DEGER_1]`. Model jetonu kopyalar; jeton burada, yerelde gerçeğine döner.
   Kasa yalnız bu çağrı boyunca bellekte yaşar.

Sözleşme (portlar.Esleyici): `esle()` İSTİSNA FIRLATMAZ. Dönen `Secim`
henüz anlam modeline karşı DOĞRULANMAMIŞTIR — o iş `Secim.kur()`'undur ve
akış katmanında yapılır. Eşleyici yalnız sözlüğü görür, modeli görmez.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable

from app.cekirdek.secim import EslemeSonucu, Secim
from app.cekirdek.tipler import Filtre, Zaman, ZamanTanesi
from app.guvenlik.anonimlestirici import Kasa, anonimlestir
from app.preprocess import resolve_dates

Sohbet = Callable[[list[dict]], str]

_SISTEM = """Sen bir iş zekâsı soru eşleyicisisin. SQL YAZMAZSIN.
Görevin: kullanıcının Türkçe sorusunu, aşağıdaki SÖZLÜKTE tanımlı ölçü ve boyut
ADLARIYLA ifade edilmiş bir JSON seçimine çevirmek.

Kurallar:
- Yalnız sözlükte "ad" alanında geçen adları kullan. Ad uydurma, çevirme, çoğul yapma.
- Soru sözlükteki ölçülerle ifade edilemiyorsa "ifade_edilemez" alanına kısa gerekçe yaz.
- Soru iki farklı ölçüye eşit derecede uyuyorsa TAHMİN ETME: "netlestirme" alanına
  tek bir soru, "secenekler" alanına aday ölçü adlarını yaz.
- Filtre değerini kullanıcının yazdığı gibi yaz. Soruda [DEGER_1], [KISI_1] gibi köşeli
  parantezli jetonlar varsa onları DEĞİŞTİRMEDEN, köşeli parantezleriyle kopyala.
- Tarih aralığı HESAPLAMA; yalnız zaman kırılımı istendiyse (günlük/haftalık/aylık/
  çeyreklik/yıllık) "zaman_tanesi" alanına gun|hafta|ay|ceyrek|yil yaz.
- İşleçler: esittir, esit_degil, icinde, araliginda, buyuk, kucuk, icerir.
- "sirala" biçimi: "<ad> azalan" ya da "<ad> artan"; ad seçimde olmalı.

Yalnız şu JSON'u döndür, başka hiçbir şey yazma:
{"olculer": [], "boyutlar": [], "filtreler": [{"boyut": "", "islec": "", "degerler": []}],
 "zaman_tanesi": null, "sirala": null, "limit": null,
 "netlestirme": "", "secenekler": [], "ifade_edilemez": ""}"""

def _tr_kucuk(s: str) -> str:
    """Türkçe küçük harf: 'I'→'ı', 'İ'→'i'. str.lower() 'İ'yi 'i̇' yapar."""
    return s.replace("I", "ı").replace("İ", "i").lower().strip()


def _istem_sozlugu(sozluk: dict, degerleri_gonder: bool) -> dict:
    """İsteme giden sözlük. API modunda değer listeleri düşer (değişmez 3)."""
    boyutlar = []
    for b in sozluk.get("boyutlar", []):
        g = {"ad": b.get("ad"), "gosterim": b.get("gosterim"), "tarih_mi": b.get("tarih_mi", False)}
        if degerleri_gonder:
            g["degerler"] = list(b.get("degerler") or [])
        boyutlar.append(g)
    return {"olculer": [{"ad": o.get("ad"), "gosterim": o.get("gosterim"), "birim": o.get("birim")}
                        for o in sozluk.get("olculer", [])],
            "boyutlar": boyutlar}


def _json_ayikla(metin: str) -> dict | None:
    m = re.search(r"\{.*\}", metin or "", re.DOTALL)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError):
        return None
    return d if isinstance(d, dict) else None


def _liste(x) -> tuple[str, ...]:
    if x is None:
        return ()
    if isinstance(x, str):
        return (x,) if x.strip() else ()
    if isinstance(x, (list, tuple)):
        return tuple(str(v) for v in x if v is not None and str(v).strip())
    return ()


def _degeri_oturt(boyut: str, deger: str, sozluk: dict) -> str:
    """Kullanıcının yazdığı değeri sözlükteki kanonik değere bağlar.

    Birebir, sonra Türkçe büyük/küçük harf duyarsız eşleşme. Eşleşme yoksa
    değer OLDUĞU GİBİ döner — `Secim.kur` onu "böyle bir değer yok" diye
    reddeder. Burada tahmin yapılmaz (ör. en yakın dizi): yanlış bir değere
    sessizce bağlamak, v3'ün 'Kadın'/'K' sessiz yanlışının kendisidir.
    """
    b = next((x for x in sozluk.get("boyutlar", []) if x.get("ad") == boyut), None)
    degerler = list((b or {}).get("degerler") or [])
    if deger in degerler:
        return deger
    aday = [d for d in degerler if _tr_kucuk(d) == _tr_kucuk(deger)]
    return aday[0] if len(aday) == 1 else deger


def _zaman(soru: str, tane_ham) -> tuple[Zaman | None, str]:
    """Aralık yerelde çözülür; tane modelden gelir (yoksa AY). (Zaman, not)"""
    _, bulunan = resolve_dates(soru)
    tane = None
    if isinstance(tane_ham, str) and tane_ham.strip():
        try:
            tane = ZamanTanesi(tane_ham.strip().lower())
        except ValueError:
            return None, f"Model geçersiz bir zaman tanesi döndürdü: '{tane_ham}'."
    if not bulunan and tane is None:
        return None, ""
    if len(bulunan) > 1:
        ifadeler = ", ".join(b["ifade"] for b in bulunan)
        return None, f"Soruda birden fazla zaman ifadesi var ({ifadeler}); hangisi?"
    if bulunan:
        b = bulunan[0]
        return Zaman(tane=tane or ZamanTanesi.AY, baslangic=b["baslangic"],
                     bitis=b["bitis"], ifade=b["ifade"]), ""
    return Zaman(tane=tane), ""


class LlmEsleyici:
    """`portlar.Esleyici` uygulaması.

    `sohbet`: `[{"role", "content"}] -> str`. Yerel mod için
    `generator._ollama_chat`, API modu için `generator._api_chat` (bkz.
    `sohbet_sec`). Testte sahte bir işlev.
    `degerleri_gonder`: yalnız YEREL modda True olabilir. False iken (API modu)
    soru ayrıca anonimleştirilir (ADR-10).
    """

    def __init__(self, sohbet: Sohbet, degerleri_gonder: bool = False) -> None:
        self._sohbet = sohbet
        self._degerleri_gonder = degerleri_gonder

    def istem(self, soru: str, sozluk: dict) -> list[dict]:
        """Giden mesajlar — `soru` burada ZATEN anonimleştirilmiş olmalıdır
        (`esle` bunu yapar). Ayrı ve açık, çünkü Sınır 1 testi bunu denetler."""
        govde = json.dumps(_istem_sozlugu(sozluk, self._degerleri_gonder),
                           ensure_ascii=False, sort_keys=True)
        return [{"role": "system", "content": _SISTEM},
                {"role": "user", "content": f"SÖZLÜK:\n{govde}\n\nSORU: {soru}\n\nJSON:"}]

    def esle(self, soru: str, sozluk: dict) -> EslemeSonucu:
        try:
            return self._esle(soru, sozluk)
        except Exception as e:                      # noqa: BLE001 — kapalı devre, port sözleşmesi
            return EslemeSonucu(hata=f"Eşleme yapılamadı ({type(e).__name__}: {e}).")

    def _esle(self, soru: str, sozluk: dict) -> EslemeSonucu:
        if not isinstance(soru, str) or not soru.strip():
            return EslemeSonucu(hata="Soru boş.")
        if self._degerleri_gonder:
            giden, kasa = soru, Kasa()             # yerel mod: makineden çıkmıyor
        else:
            giden, kasa = anonimlestir(soru, sozluk)
        ham = self._sohbet(self.istem(giden, sozluk))
        d = _json_ayikla(ham)
        if d is None:
            return EslemeSonucu(hata="Model çıktısı JSON olarak çözümlenemedi.", ham_cikti=str(ham)[:2000])

        neden = str(d.get("ifade_edilemez") or "").strip()
        if neden:
            return EslemeSonucu(
                hata=f"Bu soru mevcut ölçülerle ifade edilemiyor: {kasa.geri_cevir(neden)}",
                ham_cikti=ham[:2000])
        soru_geri = str(d.get("netlestirme") or "").strip()
        if soru_geri:
            # Kullanıcıya gösterilen metin yerelde gerçeğine döner; ham_cikti
            # (denetim izi) jetonlu kalır — kişisel veri taşımaz.
            return EslemeSonucu(netlestirme_sorusu=kasa.geri_cevir(soru_geri),
                                secenekler=_liste(d.get("secenekler")), ham_cikti=ham[:2000])

        zaman, zaman_notu = _zaman(soru, d.get("zaman_tanesi"))
        if zaman_notu:
            return EslemeSonucu(netlestirme_sorusu=zaman_notu, ham_cikti=ham[:2000])

        filtreler = []
        for f in d.get("filtreler") or []:
            if not isinstance(f, dict) or not f.get("boyut"):
                continue
            boyut = str(f["boyut"])
            filtreler.append(Filtre(
                boyut=boyut, islec=str(f.get("islec") or "esittir"),
                degerler=tuple(_degeri_oturt(boyut, kasa.geri_cevir(v), sozluk)
                               for v in _liste(f.get("degerler")))))

        limit = d.get("limit")
        try:
            limit = int(limit) if limit not in (None, "") else None
        except (TypeError, ValueError):
            limit = None

        secim = Secim(olculer=_liste(d.get("olculer")), boyutlar=_liste(d.get("boyutlar")),
                      filtreler=tuple(filtreler), zaman=zaman,
                      sirala=(str(d["sirala"]).strip() or None) if d.get("sirala") else None,
                      limit=limit)
        return EslemeSonucu(secim=secim, ham_cikti=ham[:2000])


def sohbet_sec(mod: str) -> Sohbet:
    """Mod kararına (`akis.mod.cikarim_modu`) göre gerçek sohbet işlevi."""
    from app import generator
    return generator._api_chat if mod == "api" else generator._ollama_chat
