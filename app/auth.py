"""Kimlik doğrulama ve roller (v2 — SaaS/pilot önkoşulu).

- Şifreler PBKDF2-SHA256 (100k tur, kullanıcı başına salt) ile saklanır;
  düz metin şifre HİÇBİR yerde tutulmaz.
- Roller: 'yonetici' (her şey + kullanıcı yönetimi) | 'analist' (kullanıcı
  yönetimi hariç her şey). Denetim izi (G-17) gerçek kimliğe bağlanır.
"""
import hashlib
import json
import os
import secrets

from app import config

KULLANICI_DOSYASI = os.path.join(config.HERE, ".sorbi", "users.json")
ROLLER = ("yonetici", "analist")
MIN_SIFRE = 8


def _hash(sifre: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", sifre.encode("utf-8"),
                               bytes.fromhex(salt_hex), 100_000).hex()


def kullanicilar() -> dict:
    try:
        with open(KULLANICI_DOSYASI, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _kaydet(veriler: dict) -> None:
    os.makedirs(os.path.dirname(KULLANICI_DOSYASI), exist_ok=True)
    with open(KULLANICI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veriler, f, ensure_ascii=False, indent=2)


def kullanici_ekle(ad: str, sifre: str, rol: str) -> None:
    if rol not in ROLLER:
        raise ValueError(f"Geçersiz rol: {rol}. Geçerli roller: {', '.join(ROLLER)}")
    if not ad or not ad.strip():
        raise ValueError("Kullanıcı adı boş olamaz.")
    if len(sifre) < MIN_SIFRE:
        raise ValueError(f"Şifre en az {MIN_SIFRE} karakter olmalı.")
    veriler = kullanicilar()
    salt = secrets.token_hex(16)
    veriler[ad.strip()] = {"salt": salt, "hash": _hash(sifre, salt), "rol": rol}
    _kaydet(veriler)


def dogrula(ad: str, sifre: str):
    """Başarılıysa rol döner, değilse None. Zamanlama saldırısına karşı sabit karşılaştırma."""
    k = kullanicilar().get(ad)
    if not k:
        return None
    if secrets.compare_digest(_hash(sifre, k["salt"]), k["hash"]):
        return k["rol"]
    return None


def sifre_degistir(ad: str, yeni_sifre: str) -> None:
    veriler = kullanicilar()
    if ad not in veriler:
        raise ValueError("Kullanıcı bulunamadı.")
    if len(yeni_sifre) < MIN_SIFRE:
        raise ValueError(f"Şifre en az {MIN_SIFRE} karakter olmalı.")
    salt = secrets.token_hex(16)
    veriler[ad].update({"salt": salt, "hash": _hash(yeni_sifre, salt)})
    _kaydet(veriler)


def kullanici_sil(ad: str) -> None:
    veriler = kullanicilar()
    if veriler.get(ad, {}).get("rol") == "yonetici" and \
       sum(1 for v in veriler.values() if v["rol"] == "yonetici") == 1:
        raise ValueError("Son yönetici silinemez.")
    veriler.pop(ad, None)
    _kaydet(veriler)
