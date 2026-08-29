"""Seçim (ADR-8) — modelin ürettiği TEK şey.

v3'te model serbest SQL üretiyordu ve hata yüzeyi altı boyutluydu: tablo
seçimi, JOIN yolu, tarih kolonu, filtre, toplama fonksiyonu, sözdizimi. Altısı
da sessizce yanlış olabiliyordu.

v4'te model bir `Secim` üretir: hangi ölçü, hangi boyut, hangi filtre, hangi
zaman tanesi. Geri kalan her şey anlam modelinde sabittir ve derleyici (İP-47)
tarafından deterministik olarak eklenir. Modelin hata yüzeyi dörde iner ve
dördü de ANLAM MODELİNİN SÖZLÜĞÜNE karşı sınanabilir — uydurulmuş bir ölçü adı
`Secim.kur()` içinde yakalanır, SQL'e hiç dönüşmez.

Sözleşme: `kur()` istisna fırlatmaz. Bilinmeyen bir ad `gecersiz` listesini
doldurur ve hat orada durur (kapalı devre — `validator.py` kalıbı).
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.cekirdek.tipler import Filtre, Zaman, ZamanTanesi

if TYPE_CHECKING:                                   # döngüsel içe aktarımı önler
    from app.cekirdek.anlam import AnlamModeli

SECIM_SEMA_SURUMU = 1

GECERLI_ISLECLER = frozenset(
    {"esittir", "esit_degil", "icinde", "araliginda", "buyuk", "kucuk", "icerir"}
)


@dataclass(frozen=True)
class Secim:
    """Bir iş sorusunun anlam modeli sözlüğüne çevrilmiş hâli."""

    olculer: tuple[str, ...] = ()
    boyutlar: tuple[str, ...] = ()
    filtreler: tuple[Filtre, ...] = ()
    zaman: Zaman | None = None
    sirala: str | None = None                # "<ad> artan" | "<ad> azalan"
    limit: int | None = None
    model_surumu: int = 0                    # SPEC F-5: damga bunu taşır
    gecersiz: tuple[str, ...] = ()           # doluysa hat burada durur

    @property
    def kurulabilir(self) -> bool:
        return not self.gecersiz and bool(self.olculer)

    # ------------------------------------------------------------------ kur

    @staticmethod
    def kur(model: AnlamModeli,
            olculer: Iterable[str] = (),
            boyutlar: Iterable[str] = (),
            filtreler: Iterable[Filtre] = (),
            zaman: Zaman | None = None,
            sirala: str | None = None,
            limit: int | None = None) -> Secim:
        """Seçimi anlam modeline karşı kurar. İSTİSNA FIRLATMAZ.

        Buradaki her kontrol, v3'te SQL üretildikten SONRA yakalanmaya
        çalışılan bir hata sınıfının karşılığıdır — ama artık üretimden ÖNCE
        ve metin ayrıştırmadan, çünkü seçim yapısaldır.

        Girdisi güvenilmeyen model çıktısıdır (`validator.py` ile aynı
        durum), o yüzden kapı her koşulda kapanır: beklenmeyen her hata
        `gecersiz` alanına düşer.
        """
        try:
            return Secim._kur(model, olculer, boyutlar, filtreler,
                              zaman, sirala, limit)
        except Exception as e:                      # noqa: BLE001 — kapalı devre
            return Secim(gecersiz=(f"Seçim kurulamadı "
                                   f"({type(e).__name__}: {e}).",))

    @staticmethod
    def _kur(model: AnlamModeli,
             olculer: Iterable[str],
             boyutlar: Iterable[str],
             filtreler: Iterable[Filtre],
             zaman: Zaman | None,
             sirala: str | None,
             limit: int | None) -> Secim:
        olculer = tuple(olculer)
        boyutlar = tuple(boyutlar)
        filtreler = tuple(filtreler)
        sorunlar: list[str] = []

        if not olculer:
            sorunlar.append("Hiç ölçü seçilmedi — sayılacak bir şey yok.")
        for ad in olculer:
            if ad not in model.olculer:
                sorunlar.append(f"'{ad}' diye bir ölçü yok. "
                                f"Var olanlar: {', '.join(sorted(model.olculer)) or '—'}")
        for ad in boyutlar:
            if ad not in model.boyutlar:
                sorunlar.append(f"'{ad}' diye bir boyut yok. "
                                f"Var olanlar: {', '.join(sorted(model.boyutlar)) or '—'}")

        for f in filtreler:
            if f.boyut not in model.boyutlar:
                sorunlar.append(f"Filtre bilinmeyen bir boyuta uygulanıyor: '{f.boyut}'.")
                continue
            if f.islec not in GECERLI_ISLECLER:
                sorunlar.append(f"'{f.islec}' geçerli bir işleç değil.")
            b = model.boyutlar[f.boyut]
            if b.sozluk:
                # Sözlük varsa filtre değeri o sözlükten gelmek ZORUNDA.
                # v3'te en sık sessiz yanlış buydu: model 'Kadın' yazıyor,
                # kolonda 'K' var, sorgu çalışıyor, sıfır satır dönüyor ve
                # kullanıcı bunu "kayıt yok" diye okuyor (eksen 4).
                bilinen = set(b.sozluk) | set(b.sozluk.values())
                for d in f.degerler:
                    if d not in bilinen:
                        sorunlar.append(
                            f"'{f.boyut}' boyutunda '{d}' diye bir değer yok. "
                            f"Olanlar: {', '.join(sorted(b.sozluk.values()))}")

        # Zaman kısıtı ancak bir olay tablosu üzerinden anlamlıdır.
        if zaman is not None:
            if not isinstance(zaman.tane, ZamanTanesi):
                sorunlar.append("Zaman tanesi geçersiz.")
            if not model.olay_tablolari():
                sorunlar.append("Zaman filtresi istendi ama modelde olay tablosu yok.")

        if sirala:
            hedef = sirala.rsplit(" ", 1)[0]
            if hedef not in set(olculer) | set(boyutlar):
                sorunlar.append(f"Sıralama '{hedef}' üzerinden isteniyor ama bu ad "
                                "seçimde yok.")
        if limit is not None and limit <= 0:
            sorunlar.append("Limit sıfır ya da negatif olamaz.")

        return Secim(olculer=olculer, boyutlar=boyutlar, filtreler=filtreler,
                     zaman=zaman, sirala=sirala, limit=limit,
                     model_surumu=model.surum, gecersiz=tuple(sorunlar))

    # ---------------------------------------------------------- serileştirme
    # G-1 (SPEC): modül ekranı v5'te yapılacak ama v4'ün veri yapıları onu
    # engellememeli. Bir seçim adlandırılıp saklanabilir olmalı ve saklandığı
    # anlam modeli sürümünü taşımalı.

    def to_dict(self) -> dict[str, Any]:
        return {
            "sema_surumu": SECIM_SEMA_SURUMU,
            "olculer": list(self.olculer),
            "boyutlar": list(self.boyutlar),
            "filtreler": [
                {"boyut": f.boyut, "islec": f.islec, "degerler": list(f.degerler)}
                for f in self.filtreler
            ],
            "zaman": None if self.zaman is None else {
                "tane": self.zaman.tane.value,
                "baslangic": self.zaman.baslangic,
                "bitis": self.zaman.bitis,
                "ifade": self.zaman.ifade,
            },
            "sirala": self.sirala,
            "limit": self.limit,
            "model_surumu": self.model_surumu,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @staticmethod
    def from_dict(d: Mapping[str, Any], model_surumu: int | None = None) -> Secim:
        """Sözlükten seçim kurar.

        `model_surumu` verilirse uyum denetlenir: farklı bir anlam modeli
        sürümüyle kaydedilmiş bir seçim SESSİZCE çalıştırılmaz. Ölçü adı aynı
        kalıp ifadesi değişmiş olabilir; o durumda eski seçim yeni modelde
        başka bir şey ölçer ve kimse fark etmez (İP-23'ün cetvel çürümesi
        dersinin seçim tarafı).
        """
        ds = d.get("sema_surumu", SECIM_SEMA_SURUMU)
        if ds != SECIM_SEMA_SURUMU:
            return Secim(gecersiz=(f"Seçim biçimi sürümü {ds}, beklenen "
                                   f"{SECIM_SEMA_SURUMU}.",))
        z = d.get("zaman")
        secim = Secim(
            olculer=tuple(d.get("olculer") or ()),
            boyutlar=tuple(d.get("boyutlar") or ()),
            filtreler=tuple(
                Filtre(boyut=f["boyut"], islec=f["islec"],
                       degerler=tuple(f.get("degerler") or ()))
                for f in (d.get("filtreler") or ())
            ),
            zaman=None if not z else Zaman(
                tane=ZamanTanesi(z["tane"]), baslangic=z.get("baslangic"),
                bitis=z.get("bitis"), ifade=z.get("ifade", "")),
            sirala=d.get("sirala"), limit=d.get("limit"),
            model_surumu=int(d.get("model_surumu", 0)),
        )
        if model_surumu is not None and secim.model_surumu != model_surumu:
            return Secim(
                **{**secim.to_dict_alanlari(),
                   "gecersiz": (f"Bu seçim anlam modeli sürüm "
                                f"{secim.model_surumu} ile kaydedildi; "
                                f"yürürlükteki sürüm {model_surumu}. "
                                "Seçim yeniden kurulmalı.",)})
        return secim

    def to_dict_alanlari(self) -> dict[str, Any]:
        """`dataclasses.replace` yerine açık alan kopyası — hata iletisi
        eklerken kullanılır."""
        return {"olculer": self.olculer, "boyutlar": self.boyutlar,
                "filtreler": self.filtreler, "zaman": self.zaman,
                "sirala": self.sirala, "limit": self.limit,
                "model_surumu": self.model_surumu}

    @staticmethod
    def from_json(metin: str, model_surumu: int | None = None) -> Secim:
        try:
            return Secim.from_dict(json.loads(metin), model_surumu)
        except Exception as e:                      # noqa: BLE001 — kapalı devre
            return Secim(gecersiz=(f"Seçim çözümlenemedi "
                                   f"({type(e).__name__}: {e}).",))


@dataclass(frozen=True)
class EslemeSonucu:
    """`Esleyici` portunun çıktısı — bir seçim, bir soru ya da bir hata.

    Üç sonuçtan tam biri olur:
      · secim.kurulabilir            → hat devam eder
      · netlestirme_sorusu dolu      → kullanıcıya bir kez sorulur (SPEC C-2)
      · hata dolu                    → soru "ifade edilemedi" olarak kapanır

    "İfade edilemedi" bir başarısızlık değil, tasarım gereği bir çıktıdır:
    tahmine dayalı bir cevap üretmektense cevapsız kalmak yeğdir (SPEC B-3).
    """

    secim: Secim = field(default_factory=Secim)
    netlestirme_sorusu: str = ""
    secenekler: tuple[str, ...] = ()
    onerilen_olcu: str = ""                  # SPEC B-3: eksik ölçü teklifi
    hata: str = ""
    ham_cikti: str = ""                      # teşhis için; denetim izine gider
