"""Süit koşmadan önce demo veritabanlarını garanti eder.

Neden bir fixture değil de içe aktarma anında (BULGU-N4, 2026-08-21 → 08-23):
`pytest.mark.skipif(not os.path.exists(DB))` ifadesi **toplama sırasında**
değerlendirilir. Bir session fixture'ı o an henüz koşmamıştır, dolayısıyla
`skipif` yine "dosya yok" görür ve testleri atlar. Tohumlamanın `conftest.py`
içe aktarılırken yapılması gerekiyor — pytest bu dosyayı toplamadan önce okur.

Bu düzeltmenin asıl derdi hız değil, **dürüstlük.** `demo/hospital.db` yokken
süitin çoğu sessizce atlanıyor ve pytest yine **çıkış kodu 0** veriyordu:
yeşil ışık yanıyor ama testlerin çoğu hiç koşmamış. Bu, ürünün kendisinde
kovaladığımız sessiz yanlışın cetveldeki hâlidir (CLAUDE.md § 3.4).

Atlanan test, koşmamış testtir. Bu dosyadan sonra süitte 0 atlama olmalı —
`tests/test_suit_dururlugu.py` bunu kilitliyor.
"""
import os
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (üretilecek dosya, üreten betik)
VERITABANLARI = [
    (os.path.join(KOK, "demo", "hospital.db"), os.path.join(KOK, "demo", "seed_data.py")),
    (os.path.join(KOK, "demo", "satis.db"), os.path.join(KOK, "demo", "seed_satis.py")),
]


def _tohumla() -> None:
    for db, betik in VERITABANLARI:
        if os.path.exists(db):
            continue
        if not os.path.exists(betik):
            raise RuntimeError(
                f"{os.path.relpath(db, KOK)} yok ve onu üreten "
                f"{os.path.relpath(betik, KOK)} de yok. Süit bu hâlde anlamlı koşamaz."
            )
        # check=True: tohumlama sessizce başarısız olursa süit yeşil görünmemeli.
        # S603: girdi kullanıcıdan değil — `sys.executable` ve bu depodaki sabit
        # bir yol. Kabuk kullanılmıyor (shell=False), argümanlar liste hâlinde.
        subprocess.run([sys.executable, betik], check=True, cwd=KOK,  # noqa: S603
                       stdout=subprocess.DEVNULL)
        if not os.path.exists(db):
            raise RuntimeError(f"{betik} koştu ama {db} üretilmedi.")


_tohumla()
