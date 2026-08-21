"""JOIN yolları üretimi (İP-03b).

2026-08-16 baseline ölçümünde doğrulama katmanının reddettiği 12 sorgunun 6'sı
birleştirme yolu hatasıydı: `muayene.hasta_id`, `fatura.bolum_id`,
`muayene.fatura_id` gibi var olmayan kısayol kolonları. Bu testler, o yolların
artık modele açıkça verildiğini garanti eder.

Hiçbiri LLM gerektirmez — yollar yabancı anahtar grafiğinden hesaplanır.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schema_rag import (  # noqa: E402
    ContextIndex,
    _komsuluk,
    discover_schema,
    en_kisa_yol,
    join_paths_doc,
    yollar,
)

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "demo", "hospital.db")
DB_URL = f"sqlite:///{DB}"


@pytest.fixture(scope="module")
def edges():
    if not os.path.exists(DB):
        pytest.skip("demo/hospital.db yok — önce: python demo/seed_data.py")
    _docs, _cols, e, _ = discover_schema(DB_URL)
    return e


# ------------------------------------------------------------------ graf

def test_yabanci_anahtarlar_kesfediliyor(edges):
    assert len(edges) >= 8
    ciftler = {(e["kaynak"], e["hedef"]) for e in edges}
    assert ("randevu", "hasta") in ciftler
    assert ("muayene", "randevu") in ciftler
    assert ("fatura", "muayene") in ciftler
    assert ("doktor", "bolum") in ciftler


def test_komsuluk_yonsuz(edges):
    g = _komsuluk(edges)
    assert any(k == "hasta" for k, _ in g["randevu"])       # çocuk -> ebeveyn
    assert any(k == "randevu" for k, _ in g["hasta"])       # ebeveyn -> çocuk


# --------------------------------------------------- baseline'da patlayan yollar

@pytest.mark.parametrize(("a", "b", "beklenen_ara"), [
    ("hasta", "fatura", {"randevu", "muayene"}),      # soru 43: muayene.hasta_id uydurdu
    ("bolum", "fatura", {"doktor", "randevu", "muayene"}),  # soru 37: fatura.bolum_id uydurdu
    ("doktor", "muayene", {"randevu"}),               # soru 36: doktor.muayene_id uydurdu
    ("muayene", "islem", {"muayene_islem"}),          # soru 42: fatura.islem_id uydurdu
])
def test_baseline_hatalarinin_yolu_uretiliyor(edges, a, b, beklenen_ara):
    metin, ara = join_paths_doc([a, b], edges)
    assert metin, f"{a} <-> {b} için yol üretilemedi"
    assert f"{a} <-> {b}" in metin
    assert beklenen_ara <= ara, f"ara tablolar eksik: {ara}"


def test_yol_gercek_kolonlardan_olusuyor(edges):
    """Üretilen her birleştirme koşulu şemada GERÇEKTEN var olan kolonlara işaret etmeli."""
    _docs, cols, _, _ = discover_schema(DB_URL)
    metin, _ = join_paths_doc(["hasta", "fatura", "bolum", "islem"], edges)
    for satir in metin.splitlines():
        if "<->" not in satir:
            continue
        for kosul in satir.split(": ", 1)[1].split(" AND "):
            for yan in kosul.split(" = "):
                tablo, kolon = yan.strip().split(".")
                assert tablo.lower() in cols, f"olmayan tablo: {tablo}"
                assert kolon.lower() in cols[tablo.lower()], f"olmayan kolon: {yan}"


# ------------------------------------------------------------------ alternatifler

def test_belirsiz_iliski_icin_alternatif_yol_sunuluyor(edges):
    """bolum <-> hasta iki anlama gelebilir: yatan hasta (yatis) ya da randevulu hasta.

    Yalnız en kısa yolu yazmak modeli sessizce yatis zincirine iter — düzeltmek
    istediğimiz hatanın aynısını üretmiş oluruz.
    """
    metin, _ = join_paths_doc(["bolum", "hasta"], edges)
    assert "alternatif" in metin
    assert "yatis" in metin and "randevu" in metin


def test_alternatif_yol_en_fazla_bir_adim_uzun(edges):
    g = _komsuluk(edges)
    bulunan = yollar(g, "bolum", "hasta")
    assert len(bulunan) == 2
    assert len(bulunan[1]) <= len(bulunan[0]) + 1


def test_iliskisiz_tablolar_icin_yol_yok():
    edges = [{"kaynak": "a", "kaynak_kolon": "b_id", "hedef": "b", "hedef_kolon": "id"},
             {"kaynak": "c", "kaynak_kolon": "d_id", "hedef": "d", "hedef_kolon": "id"}]
    g = _komsuluk(edges)
    assert en_kisa_yol(g, "a", "d") is None
    metin, ara = join_paths_doc(["a", "d"], edges)
    assert metin == "" and ara == set()


def test_azami_adim_sinirina_uyuluyor():
    """Uzun zincir: a-b-c-d-e. azami_adim=2 ile a'dan e'ye yol bulunmamalı."""
    edges = [{"kaynak": x, "kaynak_kolon": f"{y}_id", "hedef": y, "hedef_kolon": "id"}
             for x, y in [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")]]
    g = _komsuluk(edges)
    assert en_kisa_yol(g, "a", "e", azami_adim=2) is None
    assert en_kisa_yol(g, "a", "e", azami_adim=4) is not None


def test_tek_tablo_icin_yol_uretilmez(edges):
    metin, ara = join_paths_doc(["hasta"], edges)
    assert metin == "" and ara == set()


# ------------------------------------------------------------------ bağlam

def test_retrieve_join_yollarini_ve_ara_tablolari_ekliyor():
    """Uçtan uca: 'Bölümlere göre toplam ciro' (baseline soru 37, reddedilmişti)."""
    if not os.path.exists(DB):
        pytest.skip("demo/hospital.db yok")
    idx = ContextIndex(DB_URL)
    ctx, tables = idx.retrieve("Bölümlere göre toplam ciro nedir?")
    assert "JOIN YOLLARI" in ctx
    # bolum -> fatura yolundaki her tablonun ŞEMASI da bağlamda olmalı,
    # yoksa model yolu görür ama kolonlarını göremez
    for t in ("bolum", "doktor", "randevu", "muayene", "fatura"):
        assert f"TABLO {t}" in ctx, f"{t} şeması bağlamda yok"
        assert t in tables


# ------------------------------------------------------- bağlam bütçesi (saha kaydı)

def test_yol_sayisi_sinirlaniyor(edges):
    """9 tablo = 36 çift = 41 yol satırı = 5102 karakter; bağlamın geri kalanı 2068'di.

    Saha kaydı (2026-08-16 ikinci koşum): soru başına süre 20-30 sn'den 70-115 sn'ye
    çıktı. Doğru yolu vermek doğruluğu artırır, TÜM yolları vermek üretimi öldürür.
    """
    tum = ["bolum", "doktor", "hasta", "randevu", "muayene", "islem",
           "muayene_islem", "fatura", "yatis"]
    metin, _ = join_paths_doc(tum, edges)
    yol_satirlari = [s for s in metin.splitlines() if "<->" in s]
    assert len(yol_satirlari) <= 12
    assert len(metin) < 2500, f"JOIN bölümü hâlâ çok büyük: {len(metin)} karakter"


def test_soruyla_alakali_yol_en_uste_geliyor(edges):
    """Bütçe sınırlıysa hangi yolun yazılacağı önem kazanır — soru karar versin."""
    tum = ["bolum", "doktor", "hasta", "randevu", "muayene", "islem",
           "muayene_islem", "fatura", "yatis"]
    metin, _ = join_paths_doc(tum, edges, soru="En çok fatura tutarı üreten 5 doktor kim?")
    yol_satirlari = [s for s in metin.splitlines() if "<->" in s]
    assert yol_satirlari[0].startswith("doktor <-> fatura")


def test_butce_dar_olsa_da_ara_tablolar_dogru_kaliyor(edges):
    """Kesilen satırlar ara tablo listesini bozmamalı: yazılan her yolun
    tablolarının şeması bağlama girmeli, yazılmayanınki girmemeli."""
    tum = ["bolum", "doktor", "hasta", "randevu", "muayene", "islem",
           "muayene_islem", "fatura", "yatis"]
    metin, ara = join_paths_doc(tum, edges, azami_satir=3)
    yol_satirlari = [s for s in metin.splitlines() if "<->" in s]
    assert len(yol_satirlari) <= 3
    gecen = set()
    for satir in yol_satirlari:
        for kosul in satir.split(": ", 1)[1].split(" AND "):
            for yan in kosul.split(" = "):
                gecen.add(yan.strip().split(".")[0])
    assert ara <= gecen        # uydurma ara tablo yok


def test_istem_baglam_penceresine_sigiyor(edges):
    """Bağlam penceresini aşan istem SESSİZCE kırpılır — model şemanın bir kısmını
    hiç görmez ve emin bir şekilde yanlış cevap verir. Kaba bir üst sınır kontrolü:
    en kötü durumda (tüm tablolar seçili) istem, 8192 tokenlık pencerenin
    yarısını geçmemeli. Türkçe için ~2,5 karakter/token varsayılıyor."""
    from app import config
    from app.generator import SYSTEM_PROMPT
    from app.schema_rag import glossary_docs, load_glossary
    tum = ["bolum", "doktor", "hasta", "randevu", "muayene", "islem",
           "muayene_islem", "fatura", "yatis"]
    _docs, _cols, _, _ = discover_schema(DB_URL)
    sema = sum(len(d["text"]) for d in _docs)
    terim = sum(len(t["text"]) for t in glossary_docs(load_glossary()))
    yol, _ = join_paths_doc(tum, edges)
    toplam_karakter = len(SYSTEM_PROMPT) + sema + terim + len(yol) + 200
    tahmini_token = toplam_karakter / 2.5
    assert tahmini_token < config.NUM_CTX / 2, (
        f"istem ~{tahmini_token:.0f} token, pencere {config.NUM_CTX}")
