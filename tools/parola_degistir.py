"""Bir kullanıcının parolasını değiştirir. Parola ekrana yazılmaz.

NEDEN VAR (BULGU-15, 2026-08-23):
`.sorbi/users.json` dosyası `884f8d9` commit'inde **herkese açık** depoya
itilmişti. İçinde admin'in `salt` + PBKDF2 `hash`'i var. Dosyayı takipten
çıkarmak onu geçmişten SİLMEZ — hâlâ orada. Parolayı değiştirmek, dışarı
sızmış olan hash'i **değersiz** kılar; yapılması gereken ilk iş budur.

Parola `getpass` ile alınır: ekrana yazılmaz, komut geçmişine düşmez, hiçbir
dosyaya kaydedilmez. Saklanan şey yalnız yeni salt ve yeni hash.

Kullanım:  python tools/parola_degistir.py [kullanıcı adı]
"""
import getpass
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

try:
    from app import auth
except ModuleNotFoundError as e:
    print(f"HATA: '{e.name}' bulunamadı. Sanal ortam etkin mi?\n"
          r"  .venv\Scripts\activate   (Windows)" "\n"
          "  source .venv/bin/activate  (Linux/Mac)", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    print()
    print("=" * 62)
    print(" SorBI — parola değiştirme")
    print("=" * 62)

    kullanicilar = auth.kullanicilar()
    if not kullanicilar:
        print("\nHiç kullanıcı yok (.sorbi/users.json boş ya da yok).")
        return 1

    print("\nKayıtlı kullanıcılar:")
    for ad, k in kullanicilar.items():
        print(f"  - {ad}  ({k.get('rol', '?')})")

    if len(sys.argv) > 1:
        ad = sys.argv[1].strip()
    else:
        varsayilan = "admin" if "admin" in kullanicilar else next(iter(kullanicilar))
        ad = input(f"\nHangi kullanıcı? [{varsayilan}] ").strip() or varsayilan

    if ad not in kullanicilar:
        print(f"\nHATA: '{ad}' diye bir kullanıcı yok.")
        return 1

    print(f"\nEn az {auth.MIN_SIFRE} karakter. Yazdığınız ekranda görünmez.")
    print("ÖNERİ: eski hash depoda olduğu için yeni parola eskisiyle hiç")
    print("       benzeşmesin — parola yöneticisinin ürettiği rastgele bir")
    print("       dize en iyisi.")

    yeni = getpass.getpass("\nYeni parola       : ")
    tekrar = getpass.getpass("Yeni parola (yine): ")

    if yeni != tekrar:
        print("\nHATA: iki giriş aynı değil. HİÇBİR ŞEY DEĞİŞMEDİ.")
        return 1

    if auth.dogrula(ad, yeni):
        print("\nHATA: yeni parola eskisiyle aynı. Sızmış hash bu parolayı "
              "koruyor; değiştirmenin anlamı kalmaz. HİÇBİR ŞEY DEĞİŞMEDİ.")
        return 1

    try:
        auth.sifre_degistir(ad, yeni)
    except ValueError as e:
        print(f"\nHATA: {e}  HİÇBİR ŞEY DEĞİŞMEDİ.")
        return 1

    # Yazdık demek yetmez; yazdığımızın çalıştığını göstermek gerekir.
    if not auth.dogrula(ad, yeni):
        print("\nHATA: kayıt yazıldı ama doğrulama geçmedi. Elle kontrol edin: "
              f"{auth.KULLANICI_DOSYASI}")
        return 1

    print(f"\nTAMAM — '{ad}' kullanıcısının parolası değişti.")
    print("Yeni salt ve yeni hash yazıldı; GitHub'daki eski hash artık")
    print("hiçbir işe yaramıyor.")
    print("\n`.sorbi/` artık .gitignore'da — bu dosya bir daha depoya girmez.")
    print("Geçmişteki kopya ayrı bir karardır (bkz. IP-33/VERIFY.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
