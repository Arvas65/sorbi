"""Doğrulama katmanı (G-10, G-18) — sqlglot tabanlı.

G-18: SELECT dışındaki HER sorgu türü sözdizim düzeyinde reddedilir.
G-10: Model tek lehçe üretir (sqlite); hedef lehçeye burada çevrilir (ADR-4).
"""
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

BANNED = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
    exp.TruncateTable, exp.Grant, exp.Attach, exp.Set, exp.Command,
)


@dataclass
class ValidationResult:
    ok: bool
    sql: str = ""            # hedef lehçeye çevrilmiş güvenli SQL
    error: str = ""          # kullanıcı diliyle hata (Nielsen 9: ne oldu + ne yapmalı)
    tables: tuple = ()       # sorguda geçen tablolar (denetim + şema kontrolü)


def validate_and_transpile(raw_sql: str, source_dialect: str = "sqlite",
                           target_dialect: str = "sqlite",
                           known_tables: set | None = None,
                           known_columns: dict | None = None) -> ValidationResult:
    """Doğrulama katmanının SÖZLEŞMESİ: hiçbir girdi için istisna FIRLATMAZ.

    Bu katman bir güvenlik kapısıdır ve girdisi güvenilmeyen model çıktısıdır.
    Fırlatan bir kapı, çağıranın hata yolunda ne yaptığına bağımlı hale gelir;
    kapanan bir kapı ise her koşulda kapanır. Beklenmeyen her hata `ok=False`
    olarak döner — açık değil kapalı tarafa düşer.

    Saha kaydı (2026-08-16): model, istemdeki terim sözlüğünün bir parçasını
    SQL alanına kopyaladı; `sqlglot` kapanmamış tırnak yüzünden `TokenError`
    fırlattı. Yalnız `ParseError` yakalanıyordu, bu yüzden 50 soruluk ölçüm
    30. soruda tamamen çöktü ve 29 sorunun sonucu kayboldu.
    """
    try:
        return _dogrula(raw_sql, source_dialect, target_dialect, known_tables, known_columns)
    except Exception as e:      # noqa: BLE001 - kapı kapalı tarafa düşmek zorunda
        return ValidationResult(
            ok=False,
            error=f"Sorgu çözümlenemedi ({type(e).__name__}). "
                  "Üretilen metin geçerli bir SQL sorgusu değil. "
                  "Soruyu sadeleştirip yeniden deneyin.")


def _dogrula(raw_sql: str, source_dialect: str, target_dialect: str,
             known_tables: set | None, known_columns: dict | None) -> ValidationResult:
    sql = (raw_sql or "").strip().rstrip(";")
    if not sql:
        return ValidationResult(ok=False, error="Model boş bir sorgu üretti.")

    # Tek ifade zorunlu (";" ile ikinci ifade sokulamaz)
    try:
        statements = sqlglot.parse(sql, read=source_dialect)
    except sqlglot.errors.SqlglotError as e:
        return ValidationResult(ok=False, error=f"Sorgu çözümlenemedi: {str(e)[:200]}. "
                                                "Soruyu sadeleştirip yeniden deneyin.")
    if len(statements) != 1 or statements[0] is None:
        return ValidationResult(ok=False, error="Tek bir sorgu bekleniyor; birden fazla ifade reddedildi.")

    tree = statements[0]

    # G-18: yalnız SELECT (CTE'li/UNION'lı SELECT dahil)
    root = tree
    if isinstance(root, exp.With):
        root = root.this
    if not isinstance(root, (exp.Select, exp.Union)):
        return ValidationResult(ok=False, error="Yalnızca okuma (SELECT) sorguları çalıştırılır. "
                                                "Veri değiştirme talebi reddedildi.")
    for node in tree.walk():
        if isinstance(node, BANNED):
            return ValidationResult(ok=False, error="Sorgu, izin verilmeyen bir işlem içeriyor "
                                                    f"({type(node).__name__}). Yalnızca SELECT çalıştırılır.")

    # Sorgunun KENDİ tanımladığı adlar — bunlar tabloya ait değildir ama geçerlidir.
    #
    # Saha kaydı (2026-08-16, ikinci ölçüm): reddedilen 10 sorgunun 9'u
    # `ORDER BY ciro`, `ORDER BY randevu_sayisi`, `ORDER BY ortalama` gibi
    # SELECT TAKMA ADLARIYDI. Yani doğrulama katmanı, tamamen geçerli SQL'i
    # "halüsinasyon" diye reddediyordu — accuracy'yi kendi elimizle bastırmışız.
    # İstem sertleştirmesi modele "hesapla ve adlandır" dedikçe bu yanlış pozitif
    # daha da sık tetiklendi.
    takma_adlar = {a.alias.lower() for a in tree.find_all(exp.Alias) if a.alias}
    cte_adlari = {c.alias.lower() for c in tree.find_all(exp.CTE) if c.alias}
    # Türetilmiş tablolar: FROM (SELECT ...) x
    for sq in tree.find_all(exp.Subquery):
        if sq.alias:
            cte_adlari.add(sq.alias.lower())

    # Şemada olmayan tablo → halüsinasyon yakalama (B7: sessiz hataya karşı ilk savunma)
    tables = tuple(sorted({t.name for t in tree.find_all(exp.Table)}))
    if known_tables is not None:
        # CTE ve türetilmiş tablo adları şemada aranmaz — sorgunun içinde tanımlıdırlar
        unknown = [t for t in tables if t.lower() not in known_tables
                   and t.lower() not in cte_adlari]
        if unknown:
            return ValidationResult(ok=False, tables=tables,
                                    error=f"Sorgu, şemada bulunmayan tablo içeriyor: {', '.join(unknown)}. "
                                          "Soruyu farklı kelimelerle sormayı deneyin.")

    # Kolon halüsinasyonu yakalama (B7): takma ad -> gerçek tablo çözülür,
    # olmayan kolon çalıştırılmadan reddedilir; hata mesajı öz-onarım için besleyicidir
    if known_columns:
        alias_map = {}
        for t in tree.find_all(exp.Table):
            alias_map[(t.alias or t.name).lower()] = t.name.lower()
        query_tables = set(alias_map.values())
        for col in tree.find_all(exp.Column):
            cname = col.name.lower()
            if cname == "*":
                continue
            if col.table:  # nitelenmiş: T2.muayene_id
                real = alias_map.get(col.table.lower(), col.table.lower())
                if real in cte_adlari or col.table.lower() in cte_adlari:
                    continue          # CTE / türetilmiş tablo — şemada aranmaz
                cols = known_columns.get(real)
                if cols is not None and cname not in cols:
                    return ValidationResult(
                        ok=False, tables=tables,
                        error=f"'{real}' tablosunda '{col.name}' kolonu yok. "
                              f"Bu tablonun kolonları: {', '.join(sorted(cols))}")
            else:      # niteliksiz: sorgudaki tabloların en az birinde olmalı
                if cname in takma_adlar:
                    continue          # sorgunun kendi tanımladığı ad (SELECT ... AS x)
                if query_tables and not any(cname in known_columns.get(t, set())
                                            for t in query_tables):
                    return ValidationResult(
                        ok=False, tables=tables,
                        error=f"'{col.name}' kolonu sorgudaki tabloların hiçbirinde yok "
                              f"({', '.join(sorted(query_tables))}).")

    # G-10: hedef lehçeye çeviri
    try:
        out = sqlglot.transpile(sql, read=source_dialect, write=target_dialect, pretty=True)[0]
    except Exception as e:  # transpile edilemeyen uç durum
        return ValidationResult(ok=False, tables=tables,
                                error=f"Sorgu hedef veritabanı lehçesine çevrilemedi: {e}")

    return ValidationResult(ok=True, sql=out, tables=tables)
