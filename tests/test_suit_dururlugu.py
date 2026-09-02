"""Süitin kendisi hakkındaki değişmezler.

Bir test süiti de çürüyebilir ve çürürken hata vermez. BULGU-N4 tam olarak
buydu: `demo/hospital.db` yokken testlerin çoğu `skipif` ile atlanıyor,
pytest yine çıkış kodu 0 veriyordu. Yeşil ışık yanıyor, testler koşmuyor.

Bu dosya o hatanın geri gelmesini engelliyor. Ölçüm hattında `İP-23` cetvelin
çürümesini kilitlemişti; bu, aynı işin süit tarafındaki hâli.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(HERE)

# İçinde koşula bağlı atlamaya izin verilen dosyalar. Bu denetleyicinin kendisi
# dışında boş olması esastır: yeni bir istisna eklenecekse gerekçesi buraya
# yazılır ve gözle görülür.
SKIPIF_SERBEST: set[str] = {"test_suit_dururlugu.py"}

# Yorum ya da metin içinde geçen "skipif" kelimesi değil, gerçek kullanımı arar.
ATLAMA = re.compile(r"pytest\.mark\.(skipif|skip)\b|\bpytest\.skip\(")


def _test_dosyalari():
    """`tests/` altındaki TÜM test dosyaları — alt dizinler dâhil.

    Bir zamanlar yalnız `os.listdir(HERE)` idi: tek dizin. `tests/cekirdek/`
    2026-08-29'da açıldı ve denetim onu hiç görmedi; içine altı `skipif`
    birikti (2026-09-03'te bulundu). Nöbetçinin kendisi kör noktalıydı ve
    körlüğü sessizdi — "0 atlama" diye söz veren docstring'in altında altı
    atlama duruyordu.

    Ders, ürünün kendisinde kovaladığımızın aynısı: **kapsamı daralan bir
    denetim, geçtiğini söylemeye devam eder.**
    """
    for kok, dizinler, dosyalar in os.walk(HERE):
        dizinler[:] = [d for d in dizinler if d != "__pycache__"]
        for ad in sorted(dosyalar):
            if ad.startswith("test_") and ad.endswith(".py"):
                yol = os.path.join(kok, ad)
                yield os.path.relpath(yol, HERE).replace(os.sep, "/"), yol


def test_denetim_alt_dizinleri_de_tariyor():
    """Denetimin kendi kapsamının nöbetçisi.

    Az önceki hata denetimin BULDUĞU şeyde değil, BAKMADIĞI yerdeydi.
    Kapsam sessizce daralabilen bir şeyse, o da kilitlenmelidir.
    """
    adlar = [ad for ad, _ in _test_dosyalari()]
    assert any("/" in ad for ad in adlar), (
        "Denetim yalnız tests/ kökünü tarıyor; alt dizinler kör nokta."
    )


def test_hicbir_test_dosyasi_kosul_bagli_atlanmiyor():
    """`skipif`, bir testi koşmamış hâle getirip yine yeşil gösterir.

    Bir dosyanın varlığına bağlı atlama, ortama bağlı bir cetvel demektir:
    aynı kod aynı commit'te bir makinede 363 test, diğerinde 19 test koşar
    ve ikisi de "geçti" der. Eksik veri, testi atlamanın değil, üretmenin
    (bkz. `conftest.py`) sebebidir.
    """
    suclu = []
    for ad, yol in _test_dosyalari():
        if ad in SKIPIF_SERBEST:
            continue
        for no, satir in enumerate(open(yol, encoding="utf-8"), 1):
            if satir.lstrip().startswith("#") or not ATLAMA.search(satir):
                continue
            suclu.append(f"{ad}:{no}: {satir.strip()[:90]}")
    assert not suclu, (
        "Koşula bağlı atlama bulundu. Atlanan test, koşmamış testtir:\n  "
        + "\n  ".join(suclu)
    )


def test_demo_veritabanlari_tohumlanmis_durumda():
    """`conftest.py` içe aktarma anında tohumluyor mu — sonucu burada görülür."""
    for db in ("hospital.db", "satis.db"):
        yol = os.path.join(KOK, "demo", db)
        assert os.path.exists(yol), (
            f"demo/{db} yok. conftest.py onu üretmeliydi; üretmediyse süitin "
            "geri kalanı sessizce anlamsızlaşır."
        )
        assert os.path.getsize(yol) > 0, f"demo/{db} boş."


def test_conftest_tohumlamayi_ice_aktarma_aninda_yapiyor():
    """Fixture'a taşınırsa BULGU-N4 sessizce geri gelir — `skipif` toplama
    sırasında değerlendirilir, session fixture'ı o an henüz koşmamıştır."""
    metin = open(os.path.join(HERE, "conftest.py"), encoding="utf-8").read()
    assert "@pytest.fixture" not in metin, (
        "conftest.py tohumlamayı fixture'a taşımış. Toplama sırasında koşmaz; "
        "skipif'ler yine 'dosya yok' görür."
    )
    assert re.search(r"^_tohumla\(\)", metin, re.MULTILINE), (
        "conftest.py modül düzeyinde _tohumla() çağırmıyor."
    )
