"""Çıkarım modu kararı — ADR-5 B'nin kodu (SPEC E-6, İP-45).

Kural tek cümle: **API modu yalnız sentetik demo veritabanında açılabilir.**
Müşteri bağlantısında istenen mod ne olursa olsun çıkarım yerelde koşar.

Neden bir kilit ve neden burada:
- ADR-5 "veri makineden çıkmaz" vaadini varsayılan olarak korumayı seçti.
  Vaadin bir ortam değişkenine (`SORBI_MODE=api`) bağlı kalması, v3'ün en
  pahalı hata sınıfıydı: söz belgede, uygulama bir ayarın hatırlanmasında
  (CLAUDE.md § 7, "gizlilik vaadini docstring'e yazmak").
- Karar sessiz verilmez (değişmez 6). Kilit devreye girdiğinde `not` dolu
  döner ve arayüz onu gösterir; kullanıcı neden yerelde koştuğunu bilir.

Demo olmanın tek ölçüsü dosyanın `config.DEMO_DIZINI` altında olmasıdır.
Bağlantı adı, arayüzdeki bir kutucuk ya da bir bayrak demo yapmaz — bunların
hepsi bir müşteri bağlantısına kazara verilebilir. Sunucu veritabanları
(Postgres vb.) bugün hiçbir koşulda demo sayılmaz; Faz C'deki Marmara demo
Postgres'i için açık bir izin listesi o gün eklenir ve testi o gün yazılır.

Bu modül yalnız stdlib + config import eder.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from app import config

YEREL = "local"
API = "api"


@dataclass(frozen=True)
class ModKarari:
    mod: str                 # "local" | "api"
    istenen: str
    not_: str = ""           # kilit devreye girdiyse neden — boş değilse gösterilir

    @property
    def kilitlendi(self) -> bool:
        return self.mod != self.istenen


def demo_mu(db_url: str) -> bool:
    """Bağlantı sentetik bir demo veritabanı mı? Şüphede HAYIR der.

    Yalnız `sqlite:///<yol>` biçimi ve yol `DEMO_DIZINI`'nin GERÇEKTEN altındaysa
    (sembolik bağ ve `..` çözülerek) evet. `startswith` ile ad karşılaştırması
    yapılmaz: `demo-musteri/` gibi bir kardeş dizin demo sayılmamalı.
    """
    if not isinstance(db_url, str) or not db_url.startswith("sqlite:///"):
        return False
    yol = db_url[len("sqlite:///"):].split("?", 1)[0]
    if yol.startswith("file:"):
        yol = yol[len("file:"):]
    if not yol or yol == ":memory:":
        return False
    try:
        dosya = os.path.realpath(yol)
        demo = os.path.realpath(config.DEMO_DIZINI)
        return os.path.commonpath([dosya, demo]) == demo
    except (ValueError, OSError):        # farklı sürücüler (Windows) ya da bozuk yol
        return False


def cikarim_modu(db_url: str, istenen: str | None = None) -> ModKarari:
    """Bu bağlantıda çıkarım nerede koşacak. İSTİSNA FIRLATMAZ.

    Tanınmayan bir istek de yerele düşer: kapalı devre (validator kalıbı).
    """
    istenen = (istenen if istenen is not None else config.MODE) or YEREL
    istenen = str(istenen).strip().lower()
    if istenen == YEREL:
        return ModKarari(YEREL, istenen)
    if istenen != API:
        return ModKarari(YEREL, istenen,
                         f"Tanınmayan mod '{istenen}'; çıkarım yerelde koşuyor.")
    if demo_mu(db_url):
        return ModKarari(API, istenen)
    return ModKarari(
        YEREL, istenen,
        "API modu yalnız sentetik demo veritabanlarında açılır (ADR-5 B). Bu "
        "bağlantı bir müşteri veritabanı; çıkarım yerelde koşuyor, veri makineden çıkmıyor.")
