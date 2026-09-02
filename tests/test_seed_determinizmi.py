"""BULGU-25 — demo verisinin üretimi takvimden bağımsızdır.

`demo/seed_data.py` docstring'inde "her çalıştırmada aynı veri" diye söz
veriyordu; o sözü tutan hiçbir şey yoktu. `random.seed(42)` rastgele diziyi
sabitliyor, `date.today()` ise tarihleri her gün kaydırıyordu.

Bedeli cetvelde çıktı: 43 altın çiftin 9'u zaman filtreli ve dokuzu da sabit
bir `satir_sayisi` iddia ediyor. 2026-09-02'de `zaman-hafta` **kod
değişmeden** düştü (80 -> 79); 1 Ekim'de ay ve çeyrek sınırında beşi birden
düşecekti.

Buradaki testlerin işi, o sözü **çalıştırılabilir** kılmak. CLAUDE.md § 7:
"varsayımı çalıştırılabilir bir kontrole çevir."
"""
from __future__ import annotations

import hashlib
import pathlib
import shutil
import sqlite3
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parents[1]
BETIK = KOK / "demo" / "seed_data.py"
SEMA = KOK / "demo" / "hospital_schema.sql"
DEMO_DB = KOK / "demo" / "hospital.db"

# Cetvelin kalibre edildiği veri. Bu sabit, 43 altın çiftin `satir_sayisi`
# değerlerinin ve 101 gold beklentisinin dayandığı veriyi tanımlar.
# Değişirse cetvel yeniden temellendirilmek zorundadır — o yüzden burada,
# gözle görülür bir yerde duruyor ve kendini güncellemiyor.
DONMUS_IMZA = "1cdbf8acca8f11fcf9adf76608df646c9921954e7f78c5e4d64f3658085f7c5a"


def imza(db: pathlib.Path) -> str:
    """Verinin parmak izi — dosyanın baytları değil.

    SQLite sayfa düzeni sürüme ve yazma sırasına göre değişebilir; satırlar
    değişmez. İddiamız veri hakkında, dosya biçimi hakkında değil.
    """
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        h = hashlib.sha256()
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                                "ORDER BY name"):
            h.update(f"[{t}]".encode())
            for satir in con.execute(f"SELECT * FROM {t}"):   # noqa: S608
                h.update(repr(satir).encode())
        return h.hexdigest()
    finally:
        con.close()


def tohumla(dizin: pathlib.Path, bugun: str | None = None) -> pathlib.Path:
    """Betiği İZOLE bir dizinde koşar.

    Doğrudan çağırmak deponun `demo/hospital.db`'sini ezerdi: bir testin
    yan etkisi olarak ölçümün dayandığı veriyi değiştirmek, tam da bu
    dosyanın anlattığı hatanın bir başka türü olurdu.
    """
    dizin.mkdir(parents=True, exist_ok=True)
    shutil.copy(BETIK, dizin / "seed_data.py")
    shutil.copy(SEMA, dizin / "hospital_schema.sql")
    ortam = {"PATH": "/usr/bin:/bin", "SYSTEMROOT": "C:\\Windows"}
    if bugun:
        ortam["SORBI_BUGUN"] = bugun
    # S603: girdi kullanıcıdan değil — `sys.executable` ve bu depodaki betiğin
    # tmp_path'e kopyası. Kabuk kullanılmıyor (shell=False), argümanlar liste
    # hâlinde. `tests/conftest.py` aynı gerekçeyle aynı muafiyeti taşıyor.
    r = subprocess.run([sys.executable, str(dizin / "seed_data.py")],  # noqa: S603
                       capture_output=True, text=True, env=ortam, timeout=180)
    assert r.returncode == 0, r.stderr[-500:]
    return dizin / "hospital.db"


# --------------------------------------------------------------------------- #
#  Sözün çalıştırılabilir hâli
# --------------------------------------------------------------------------- #

def test_uretim_donmus_imzayla_ayni(tmp_path):
    """Docstring'in vaadi. Bu test kırmızıya dönerse cetvel artık aynı
    veriyi ölçmüyordur — beklentiyi değil, sebebi araştır."""
    assert imza(tohumla(tmp_path / "a")) == DONMUS_IMZA


def test_iki_kosum_ayni_veriyi_verir(tmp_path):
    assert imza(tohumla(tmp_path / "b")) == imza(tohumla(tmp_path / "c"))


def test_seed_betigi_duvar_saatine_bakmaz():
    """Asıl kusur buydu: tek bir duvar saati çağrısı.

    Kaynak denetimi, imza testinin yakalayamayacağı bir şeyi yakalar —
    bugün doğru değeri üreten ama YARIN başka değer üretecek bir kod yolu.

    Metin araması değil AST: bu dosyanın ve betiğin docstring'leri kusuru
    ADIYLA anlatıyor. Metne bakan bir denetim kendi belgesine takılır ve
    o gürültüyü susturmanın tek yolu belgeyi kısaltmak olurdu.
    """
    import ast
    agac = ast.parse(BETIK.read_text(encoding="utf-8"))
    yasak = {"today", "now", "utcnow", "fromtimestamp", "time"}
    for d in ast.walk(agac):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute):
            assert d.func.attr not in yasak, (
                f"duvar saati çağrısı, satır {d.lineno}: .{d.func.attr}()")


def test_referans_gun_veriyi_gercekten_belirliyor(tmp_path):
    """Kaçış kapısı çalışıyor — ve günün veriyi belirlediğini kanıtlıyor.

    Bu test geçmezse `REFERANS_GUN` ölü bir sabittir ve determinizm başka
    bir sebepten geliyordur; o zaman donmuş imza yanlış şeyi koruyor demektir.
    """
    baska = imza(tohumla(tmp_path / "d", bugun="2026-03-01"))
    assert baska != DONMUS_IMZA


def test_depodaki_veritabani_cetvelin_dayandigi_veri():
    """Nöbetçi: diskteki `hospital.db` ile altın çiftler ayrışamaz.

    Biri veritabanını başka bir günle yeniden tohumlarsa 43 altın çiftin
    `satir_sayisi` iddiaları sessizce yanlış veriye bakmaya başlar. Bu test
    o anda öter — altın çiftlerin kendisi ötmeden.
    """
    assert imza(DEMO_DB) == DONMUS_IMZA
