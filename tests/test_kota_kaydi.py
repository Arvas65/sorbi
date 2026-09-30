"""Kota her koşumda rapora bir satırla girer — aşım olmasa da (BULGU-35).

Kusur şuydu: `_kota_uyarisi` yalnız aşım varsa konuşuyor, sıfırda boş dize
dönüyordu. Böylece **ölçüldü ve sıfır**, **alan hiç yok** (İP-31 öncesi şema)
ve **alan None** üç durumu raporda birbirinden ayırt edilemez hâle geliyordu:
üçünde de `.md` dosyasında "kota" sözcüğü hiç geçmiyordu.

Bedeli ölçüldü: 2026-09-05 ve 2026-09-06 nöbetlerinin ikisi de bu sayıyı
raporda **arayıp bulamadı** ve hükmü ham JSON'a dayandırmak zorunda kaldı.
Bir sayının yokluğu, o sayının sıfır olduğu anlamına gelmez.

Bu testlerin asıl işi tek bir şeyi sabitlemek: **sessizlik bir değer değildir.**
"""
from eval import evaluate


def _r(dogru, asama):
    return {"dogru": dogru, "asama": asama, "sure_s": 1.0, "zorluk": "kolay",
            "join": 0, "onarim": False, "soru": "x"}


def test_sifir_kota_da_raporda_anilir():
    """Asıl kusur: sıfır, sessizlikten çıkarılmak zorunda kalıyordu."""
    o = evaluate.ozetle([_r(True, "esit")] * 3 + [_r(False, "sonuc_farkli")])
    satir = evaluate._kota_satiri(o)
    assert "kota_asildi=0" in satir
    assert "olculebilen=4" in satir


def test_alan_yoksa_sifir_varsayilmaz():
    """İP-31 öncesi şemada alan yoktu; 'ölçülmedi' ile 'sıfır' aynı şey değil."""
    satir = evaluate._kota_satiri({"n": 101})
    assert "olculmedi" in satir
    assert "kota_asildi=0" not in satir


def test_none_da_sifir_varsayilmaz():
    satir = evaluate._kota_satiri({"n": 101, "kota_asildi": None})
    assert "olculmedi" in satir


def test_alansiz_ozet_ile_sifir_ozet_farkli_konusur():
    """BULGU-35'in tam ifadesi. Bu iki çağrı eskiden ikisi de "" dönüyordu."""
    sifir = evaluate.ozetle([_r(True, "esit")])
    assert evaluate._kota_satiri(sifir) != evaluate._kota_satiri({"n": 1})


def test_asim_varken_satir_sayiyi_tasir():
    o = evaluate.ozetle([_r(True, "esit")] * 2 + [_r(False, "kota_asildi: x")] * 2)
    satir = evaluate._kota_satiri(o)
    assert "kota_asildi=2" in satir and "olculebilen=2" in satir


def test_uyari_islevi_degistirilmedi():
    """`_kota_uyarisi` bir ALARM'dır ve yalnız aşımda konuşmalı.

    Yeni satır onun yerine geçmez, yanına gelir: alarm ile kayıt ayrı
    işlerdir. Bu test, kaydı eklerken alarmı gürültüye çevirmediğimizi
    sabitler (BULGU-19: her koşumda ateşlenen bir alarm, alarm değildir).
    """
    assert evaluate._kota_uyarisi(evaluate.ozetle([_r(True, "esit")])) == ""
    o = evaluate.ozetle([_r(True, "esit")] * 2 + [_r(False, "kota_asildi: x")] * 2)
    assert "KULLANILAMAZ" in evaluate._kota_uyarisi(o)
