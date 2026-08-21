"""Uçtan uca akış (Böl. 12 swimlane'in kod hâli).

Soru → ön işleme → bağlam → üretim → K1 güven → K2 doğrulama → K3 yürütme → kayıt
"""
from dataclasses import dataclass, field

from app import audit, config, executor, generator, guven
from app.preprocess import resolve_dates
from app.schema_rag import ContextIndex
from app.validator import validate_and_transpile


@dataclass
class Answer:
    status: str                     # OK | DUSUK_GUVEN | RED | HATA
    sql: str = ""
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    rowcount: int = 0
    message: str = ""               # netleştirme sorusu ya da hata açıklaması
    mode: str = "local"
    elapsed_s: float = 0.0
    resolved_dates: list = field(default_factory=list)
    # B-7: sorgu çalıştı ve tablo döndü diye cevap doğru değildir. Bu liste
    # boşsa sistem şüphelenmiyor demektir — doğru olduğunu söylemiyor.
    bayraklar: list = field(default_factory=list)


_index: ContextIndex | None = None


def get_index() -> ContextIndex:
    global _index
    if _index is None:
        _index = ContextIndex()
    return _index


def reset_index() -> None:
    """Aktif bağlantı değişince RAG indeksini yeni şemayla yeniden kurar."""
    global _index
    _index = None


def _kolon_adlari(idx) -> set:
    return {k for kolonlar in (getattr(idx, "known_columns", None) or {}).values()
            for k in kolonlar}


def _bayrakla(idx: "ContextIndex", question: str, sql: str, ex) -> list:
    """K4: sessiz yanlış taraması (B-7).

    Çalıştırmadan SONRA koşar, çünkü sinyallerin yarısı sonucun kendisinde:
    sıfır satır, beklenmedik satır sayısı, soruyla uyuşmayan biçim. Hattı
    kesmez — `degerlendir` sözleşme gereği istisna fırlatmaz.
    """
    g = guven.degerlendir(
        question, sql, ex.rowcount, kolon_sayisi=len(ex.columns or []),
        satirlar=ex.rows,
        bilinen_degerler=getattr(idx, "bilinen_degerler", None),
        kolonlar=_kolon_adlari(idx),
        sozluk=(idx.glossary or {}).get("terms", {}),
        kapali=config.GUVEN_KAPALI)
    return g.mesajlar


def ask(question: str, user: str = "demo", mode: str = None,
        manual_sql: str = None) -> Answer:
    """manual_sql: kontrollü bypass (Böl. 12) — analist elle SQL girer;
    yine K2 doğrulamadan ve denetim izinden geçer, bayraklanır."""
    idx = get_index()

    if manual_sql:
        v = validate_and_transpile(manual_sql, target_dialect=config.TARGET_DIALECT,
                                   known_tables=idx.known_tables)
        if not v.ok:
            audit.write(user, question, manual_sql, "SOZDIZIM_RED", elle_yazildi=True)
            return Answer(status="RED", message=v.error)
        ex = executor.run(v.sql)
        audit.write(user, question, v.sql, ex.status, ex.rowcount,
                    "manual", ex.elapsed_s, elle_yazildi=True)
        if ex.status != "BASARILI":
            return Answer(status="HATA", sql=v.sql, message=ex.error)
        return Answer(status="OK", sql=v.sql, columns=ex.columns, rows=ex.rows,
                      rowcount=ex.rowcount, mode="manual", elapsed_s=ex.elapsed_s,
                      bayraklar=_bayrakla(idx, question, v.sql, ex))

    # 1-2: ön işleme (G-07/09) + bağlam (G-05/06)
    annotated, dates = resolve_dates(question)
    context, _tables = idx.retrieve(question)

    # 3: üretim (G-01)
    gen, used_mode = generator.generate(annotated, context, mode)

    # K1: güven eşiği (G-03)
    if gen["guven"] < config.CONFIDENCE_THRESHOLD:
        audit.write(user, question, gen.get("sql", ""), "DUSUK_GUVEN", mod=used_mode)
        msg = gen.get("aciklama") or "Sorunuz birden fazla şekilde yorumlanabilir."
        return Answer(status="DUSUK_GUVEN", sql=gen.get("sql", ""), mode=used_mode,
                      message=f"{msg} Soruyu biraz daha netleştirir misiniz?",
                      resolved_dates=dates)

    # K2: doğrulama + lehçe (G-10/18) — hata olursa TEK öz-onarım denemesi
    v = validate_and_transpile(gen["sql"], target_dialect=config.TARGET_DIALECT,
                               known_tables=idx.known_tables,
                               known_columns=idx.known_columns)
    if not v.ok:
        gen2, used_mode = generator.repair(annotated, context, gen["sql"], v.error, mode)
        v = validate_and_transpile(gen2["sql"], target_dialect=config.TARGET_DIALECT,
                                   known_tables=idx.known_tables,
                                   known_columns=idx.known_columns)
        if not v.ok:
            audit.write(user, question, gen2["sql"], "SOZDIZIM_RED", mod=used_mode)
            return Answer(status="RED", sql=gen2["sql"], message=v.error,
                          mode=used_mode, resolved_dates=dates)

    # K3: salt-okunur yürütme (G-14) — çalışma hatasında da TEK öz-onarım
    ex = executor.run(v.sql)
    if ex.status == "CALISMA_HATASI":
        gen3, used_mode = generator.repair(annotated, context, v.sql, ex.error, mode)
        v2 = validate_and_transpile(gen3["sql"], target_dialect=config.TARGET_DIALECT,
                                    known_tables=idx.known_tables,
                                    known_columns=idx.known_columns)
        if v2.ok:
            v = v2
            ex = executor.run(v.sql)
    audit.write(user, question, v.sql, ex.status, ex.rowcount, used_mode, ex.elapsed_s)
    if ex.status != "BASARILI":
        return Answer(status="HATA", sql=v.sql, message=ex.error,
                      mode=used_mode, resolved_dates=dates)

    return Answer(status="OK", sql=v.sql, columns=ex.columns, rows=ex.rows,
                  rowcount=ex.rowcount, mode=used_mode, elapsed_s=ex.elapsed_s,
                  resolved_dates=dates,
                  bayraklar=_bayrakla(idx, question, v.sql, ex))
