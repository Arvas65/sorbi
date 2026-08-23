"""Şema keşfi + RAG bağlamı (G-05, G-06 — ADR-3).

G-05: Bağlantı tanımlandığında INFORMATION_SCHEMA/inspector ile tablo-kolon-ilişki
metaverisi otomatik keşfedilir, tablo başına bir 'belge' üretilir.
G-06: Terim sözlüğü belgeleri de indekse eklenir.

Chroma + çok dilli embedding varsayılan; kurulamazsa anahtar-kelime eşleşmesine
(preprocess.keywords + light_stem) otomatik düşer — demo her koşulda çalışır.
"""
import hashlib
import json
import logging

from sqlalchemy import create_engine, inspect, text

from app import config
from app.preprocess import keywords, light_stem

_log = logging.getLogger(__name__)

# Kişisel veri olma ihtimali yüksek kolon adları — değerleri asla örneklenmez.
# Bu bir SEZGİDİR, yetkili denetim `masked_columns` listesidir (G-16). Sezgi,
# müşteri şemasında o liste doldurulmadan önceki ilk savunmadır.
_KISISEL_DESENLER = (
    "tckn", "tc_kimlik", "kimlik", "telefon", "gsm", "email", "eposta", "e_posta",
    "adres", "iban", "kart", "sifre", "parola", "plaka", "pasaport", "sicil",
)


def ornek_degerler(eng, tablo: str, kolonlar: list[str], maskeli: set[str],
                   azami_farkli: int = 20, azami_uzunluk: int = 40) -> dict[str, list]:
    """Düşük kardinaliteli metin kolonlarının GERÇEK değerlerini örnekler.

    Neden gerekli (saha kaydı 2026-08-16, 3. ölçüm): 0 JOIN'li soruların yarısı
    yanlıştı ve sebep şemayı bilmemek değil, DEĞERLERİ bilmemekti. Model
    `unvan = 'Profesör'` yazıyor, kolonda `Prof. Dr.` var; `durum = 'İPTAL'`
    yazıyor, kolonda `IPTAL` var. İkincisi Türkçeye özgü bir tuzak: noktalı İ
    ile noktasız I aynı harf değildir ve sorgu sessizce 0 satır döndürür —
    hata vermez, yanlış cevap verir.

    GİZLİLİK: bu adım gerçek veri okur ve okuduğunu isteme koyar.
    - `masked_columns` (G-16) listesindeki kolonlar HİÇBİR ZAMAN örneklenmez
    - yalnız kısa metinler ve en fazla `azami_farkli` farklı değeri olan kolonlar
      alınır; serbest metin ve kimlik benzeri alanlar bu elekten geçmez
    - API modunda `SORBI_ORNEK_DEGER=0` ile tümden kapatılmalıdır
    """
    prep = eng.dialect.identifier_preparer
    bulunan: dict[str, list] = {}
    kucuk = {k.lower() for k in kolonlar}
    # Kişi tablosu sezgisi: hem 'ad' hem 'soyad' varsa bu bir kişi kaydıdır,
    # ikisi de örneklenmez. Yalnız 'ad' olan tablolar (bolum, islem) kalır —
    # 'Kardiyoloji', 'MR', 'Endoskopi' gibi değerler sorular için gereklidir.
    kisi_tablosu = {"ad", "soyad"} <= kucuk or {"isim", "soyisim"} <= kucuk
    try:
        with eng.connect() as conn:
            for k in kolonlar:
                kl = k.lower()
                if f"{tablo}.{kl}" in maskeli or kl in maskeli:
                    continue
                if kisi_tablosu and kl in ("ad", "soyad", "isim", "soyisim"):
                    continue
                if any(d in kl for d in _KISISEL_DESENLER):
                    continue
                # Tanımlayıcılar sürücünün kendi alıntılayıcısından geçiyor,
                # LIMIT tamsayıya zorlanıyor; birleştirilen tek şey şema adları.
                kq, tq, n = prep.quote(k), prep.quote(tablo), int(azami_farkli) + 1
                sorgu = f"SELECT DISTINCT {kq} FROM {tq} WHERE {kq} IS NOT NULL LIMIT {n}"  # noqa: S608
                try:
                    degerler = [r[0] for r in conn.execute(text(sorgu))]
                except Exception as e:      # noqa: BLE001 - tek kolon patlarsa keşif sürer
                    _log.debug("%s.%s örneklenemedi: %s", tablo, k, type(e).__name__)
                    continue
                if not degerler or len(degerler) > azami_farkli:
                    continue
                if not all(isinstance(v, str) for v in degerler):
                    continue
                if max(len(v) for v in degerler) > azami_uzunluk:
                    continue           # serbest metin — kategorik değil
                bulunan[k] = sorted(degerler)
    except Exception:                  # noqa: BLE001 - örnekleme isteğe bağlı bir zenginleştirme
        return {}
    return bulunan


def discover_schema(db_url: str | None = None, maskeli: set[str] | None = None
                    ) -> tuple[list[dict], dict[str, set], list[dict], dict[str, set]]:
    """Tablo başına belge + kolon haritası + yabancı anahtar kenarları + değer haritası.

    Dördüncü dönen değer (İP-03c): kolon adı → o kolonda geçen değerler kümesi.
    Zaten örneklenmiş olan bu bilgi şimdiye kadar yalnız isteme yazılıp
    atılıyordu; güven kontrolü (B-7) aynı veriyi çalıştırma SONRASINDA da
    kullanıyor — 'unvan = Profesör' yazıldığında kolonda yalnız 'Prof. Dr.'
    varsa bunu kullanıcıya söyleyebilmek için.

    Kenarlar (İP-03b): şema bir grafiktir ve tablo belgeleri bu grafiği yalnız
    parça parça gösterir — her tablo kendi ÇIKAN yabancı anahtarlarını yazar.
    Bir tablonun kendisine işaret eden ilişkiler o tablonun belgesinde görünmez.
    Baseline ölçümünde (2026-08-16) reddedilen 12 sorgunun 6'sı tam olarak bu
    yüzden kayboldu: model çok adımlı birleştirme yolunu kuramadı.
    """
    eng = create_engine(db_url or config.DB_URL)
    try:
        return _kesfet(eng, maskeli or set())
    finally:
        # try/finally: bir istisna dispose'u atlarsa havuzdaki bağlantı
        # açık kalıyor ve Windows'ta her koşumda ResourceWarning basıyordu.
        # Her koşumda görülen bir uyarı, okunmayan bir uyarıdır.
        eng.dispose()


def _kesfet(eng, maskeli: set[str]
            ) -> tuple[list[dict], dict[str, set], list[dict], dict[str, set]]:
    insp = inspect(eng)
    docs = []
    columns: dict[str, set] = {}
    edges: list[dict] = []
    degerler: dict[str, set] = {}
    for t in insp.get_table_names():
        col_names = [c["name"] for c in insp.get_columns(t)]
        columns[t.lower()] = {c.lower() for c in col_names}
        cols = [f"{c['name']} ({c['type']})" for c in insp.get_columns(t)]
        fks = []
        for fk in insp.get_foreign_keys(t):
            if not fk.get("constrained_columns") or not fk.get("referred_table"):
                continue
            kaynak_kolon = fk["constrained_columns"][0]
            hedef_tablo = fk["referred_table"]
            hedef_kolon = (fk.get("referred_columns") or [kaynak_kolon])[0]
            fks.append(f"{t}.{kaynak_kolon} -> {hedef_tablo}.{hedef_kolon}")
            edges.append({"kaynak": t, "kaynak_kolon": kaynak_kolon,
                          "hedef": hedef_tablo, "hedef_kolon": hedef_kolon})
        gövde = f"TABLO {t}\nKOLONLAR: {', '.join(cols)}"
        if fks:
            gövde += f"\nILISKILER: {'; '.join(fks)}"
        # Örnekleme HER ZAMAN yapılır; `ORNEK_DEGERLER` yalnız değerlerin
        # İSTEME YAZILIP YAZILMAYACAĞINI belirler (İP-19).
        #
        # Kısıt baştan yanlış yere konmuştu: gizlilik riski değerleri okumakta
        # değil, dış servise GÖNDERMEKTE. Uygulama zaten aynı veriyi sorgu
        # cevabı olarak okuyor. Kısıtı okumaya bağlayınca, API modunda güven
        # kontrolünün en isabetli ayağı (`bilinmeyen_deger`, mutasyon
        # karnesinde 35/0) tümden susuyordu — hem de veri hiç dışarı
        # çıkmadan, tamamen yerelde koşan bir kontrol olduğu hâlde.
        #
        # G-16 maskeleme kuralı değişmedi: maskeli kolonlar hiç örneklenmez.
        ornekler = ornek_degerler(eng, t, col_names, maskeli)
        for k, v in ornekler.items():
            # Kolon ADI ile anahtarlanır (tablo.kolon değil): üretilen SQL'de
            # kolon çoğu zaman takma adla nitelenir ve hangi tabloya ait
            # olduğunu çözmek ayrı bir iş. Aynı adlı kolonların değerleri
            # birleşir — yanlış alarm riskini düşürür, kaçırma riskini artırır.
            degerler.setdefault(k.lower(), set()).update(v)
        if ornekler and config.ORNEK_DEGERLER:
            satirlar = [f"  {k} = {' | '.join(v)}" for k, v in ornekler.items()]
            gövde += "\nDEĞERLER (bu kolonlarda GEÇEN TEK değerler bunlardır, "
            gövde += "filtrede aynen kullan):\n" + "\n".join(satirlar)
        docs.append({"id": f"table::{t}", "table": t, "text": gövde})
    return docs, columns, edges, degerler


# ------------------------------------------------------------------ JOIN yolları

def _komsuluk(edges: list[dict]) -> dict[str, list[tuple]]:
    """Yönsüz komşuluk: {tablo: [(komsu, birlestirme_kosulu), ...]}"""
    g: dict[str, list[tuple]] = {}
    for e in edges:
        kosul = f"{e['kaynak']}.{e['kaynak_kolon']} = {e['hedef']}.{e['hedef_kolon']}"
        g.setdefault(e["kaynak"], []).append((e["hedef"], kosul))
        g.setdefault(e["hedef"], []).append((e["kaynak"], kosul))
    return g


def yollar(g: dict[str, list[tuple]], a: str, b: str,
           azami_adim: int = 4, azami_yol: int = 2) -> list[list[str]]:
    """a ile b arasındaki birleştirme yolları, kısadan uzuna.

    En kısa yolu tek doğru cevap saymak tehlikelidir: `bolum` ile `hasta` arasında
    en kısa yol yatış zinciridir (2 adım), ama soru ayakta muayeneyi kastediyorsa
    doğru yol randevu zinciridir (3 adım). Tek yol yazmak, modeli sessizce yanlış
    zincire iter — düzeltmek istediğimiz hatanın aynısını biz üretmiş oluruz.

    Bu yüzden en kısa yola ek olarak, ondan en fazla bir adım uzun ALTERNATİF
    yollar da döndürülür ve modele seçenek olarak sunulur.
    """
    if a == b or a not in g or b not in g:
        return []
    bulunan: list[list[str]] = []
    kuyruk = [(a, [], {a})]
    while kuyruk:
        dugum, kosullar, gorulen = kuyruk.pop(0)
        if len(kosullar) >= azami_adim:
            continue
        for komsu, kosul in g.get(dugum, []):
            if komsu in gorulen:
                continue
            yeni = [*kosullar, kosul]
            if komsu == b:
                if bulunan and len(yeni) > len(bulunan[0]) + 1:
                    return bulunan            # daha uzunları anlamsız
                bulunan.append(yeni)
                if len(bulunan) >= azami_yol:
                    return bulunan
                continue                       # bu daldan devam etme
            kuyruk.append((komsu, yeni, gorulen | {komsu}))
    return bulunan


def en_kisa_yol(g: dict[str, list[tuple]], a: str, b: str,
                azami_adim: int = 4) -> list[str] | None:
    """Geriye dönük uyumluluk: yalnız en kısa yol."""
    y = yollar(g, a, b, azami_adim, azami_yol=1)
    return y[0] if y else None


def join_paths_doc(tables: list[str], edges: list[dict], azami_adim: int = 4,
                   azami_satir: int = 12, soru: str | None = None) -> tuple[str, set[str]]:
    """Verilen tablolar arasındaki birleştirme yollarını açık açık yazar.

    Dönen: (belge metni, yolda geçen ARA tablolar).
    Ara tablolar önemlidir: hasta ile fatura'yı birleştirmek için randevu ve
    muayene tablolarının kolonları da bağlamda bulunmalıdır, yoksa model
    yolu görür ama kullanamaz.

    Yollar yalnız SEÇİLEN tablolar için üretilir; 200 tablolu bir kurumsal
    şemada bütün çiftleri üretmek bağlamı patlatırdı.
    """
    g = _komsuluk(edges)
    benzersiz = list(dict.fromkeys(tables))

    # Alaka sıralaması: soru hangi tablolardan bahsediyorsa o çiftlerin yolu önce yazılır.
    # 9 tablolu demo şemada bile 36 çift var; hepsini yazmak bağlamı üçe katlıyor ve
    # üretimi ölçülebilir biçimde yavaşlatıyor (2026-08-16 sonrası saha gözlemi).
    kokler = set(keywords(soru)) if soru else set()

    def puan(t: str) -> int:
        return len(kokler & {light_stem(w) for w in t.lower().replace("_", " ").split()})

    ciftler = [(a, b) for i, a in enumerate(benzersiz) for b in benzersiz[i + 1:]]
    ciftler.sort(key=lambda ab: -(puan(ab[0]) + puan(ab[1])))

    satirlar = []
    ara_tablolar: set[str] = set()
    for a, b in ciftler:
        if len(satirlar) >= azami_satir:
            break
        bulunan = yollar(g, a, b, azami_adim)
        for sira, yol in enumerate(bulunan):
            if sira and len(satirlar) >= azami_satir - 1:
                break                      # bütçe darsa önce alternatifler kesilir
            etiket = f"{a} <-> {b}" + (" (alternatif)" if sira else "")
            satirlar.append(f"{etiket}: " + " AND ".join(yol))
            for kosul in yol:
                for yan in kosul.split(" = "):
                    tablo = yan.split(".")[0].strip()
                    if tablo not in benzersiz:
                        ara_tablolar.add(tablo)
    if not satirlar:
        return "", set()
    basli = ("JOIN YOLLARI (birleştirme koşullarını buradan al, kendin tahmin etme.\n"
             "Bir çift için 'alternatif' satırı varsa sorunun anlamına uygun olanı seç):\n"
             + "\n".join(satirlar))
    return basli, ara_tablolar


def load_glossary() -> dict:
    try:
        with open(config.GLOSSARY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"terms": {}, "masked_columns": []}


def glossary_docs(gl: dict) -> list[dict]:
    return [{"id": f"term::{k}", "table": None, "text": f"TERIM '{k}' = {v}"}
            for k, v in gl.get("terms", {}).items()]


class ContextIndex:
    """Soru → ilgili tablo belgeleri + terim belgeleri."""

    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or config.DB_URL
        self.glossary = load_glossary()
        # G-16: maskeli kolonlar örneklemeye GİRMEZ — değerleri isteme kopyalanamaz
        self.maskeli = {m.lower() for m in self.glossary.get("masked_columns", [])}
        (self.schema, self.known_columns, self.edges,
         self.bilinen_degerler) = discover_schema(self.db_url, self.maskeli)
        self._doc_by_table = {d["table"].lower(): d["text"] for d in self.schema}
        self.terms = glossary_docs(self.glossary)
        self.known_tables = {d["table"].lower() for d in self.schema}
        self._chroma = None
        try:
            self._init_chroma()
        except Exception:
            self._chroma = None  # anahtar-kelime fallback

    def _init_chroma(self):
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        client = chromadb.PersistentClient(path=config.CHROMA_DIR)
        ef = SentenceTransformerEmbeddingFunction(model_name=config.EMBED_MODEL)
        # Koleksiyon adı bağlantıya bağlı — farklı DB'lerin şemaları karışmaz
        ad = "sorbi_ctx_" + hashlib.md5(self.db_url.encode(), usedforsecurity=False).hexdigest()[:10]
        col = client.get_or_create_collection(ad, embedding_function=ef)
        all_docs = self.schema + self.terms
        existing = set(col.get()["ids"])
        new = [d for d in all_docs if d["id"] not in existing]
        if new:
            col.add(ids=[d["id"] for d in new], documents=[d["text"] for d in new])
        self._chroma = col

    def _keyword_rank(self, question: str, docs: list[dict], k: int) -> list[dict]:
        stems = set(keywords(question))
        scored = []
        for d in docs:
            doc_stems = {light_stem(w) for w in d["text"].lower().replace("_", " ").split()}
            scored.append((len(stems & doc_stems), d))
        scored.sort(key=lambda x: -x[0])
        return [d for s, d in scored[:k] if s > 0] or docs[:k]

    def retrieve(self, question: str, k: int = None) -> tuple[str, list[str]]:
        """Dönen: (bağlam metni, seçilen tablo adları)."""
        k = k or config.TOP_K_TABLES
        if self._chroma is not None:
            # Koleksiyonda tablo ve terim belgeleri KARIŞIK duruyor. n_results=k+terim
            # istemek 21 belgenin 19'unu geri getiriyordu — yani "en ilgili 6 tablo"
            # seçimi hiç çalışmıyordu. Fazlasını isteyip türe göre ayırıyoruz.
            res = self._chroma.query(query_texts=[question],
                                     n_results=min(k + len(self.terms) + 6,
                                                   len(self.schema) + len(self.terms)))
            tumu = res["documents"][0]
            tablo_metinleri = [t for t in tumu if t.startswith("TABLO ")][:k]
            terim_metinleri = [t for t in tumu if t.startswith("TERIM ")][:4]
            texts = tablo_metinleri + terim_metinleri
        else:
            picked = self._keyword_rank(question, self.schema, k)
            # terimler küçük; ilgili olanları anahtar kelimeyle ekle
            picked += self._keyword_rank(question, self.terms, 4)
            texts = [d["text"] for d in picked]
        tables = [t.split("TABLO ")[1].split("\n")[0] for t in texts if t.startswith("TABLO ")]

        # İP-03b: birleştirme yollarını açıkça yaz ve yolda geçen ara tabloların
        # şemasını da bağlama ekle (yoksa model yolu görür ama kolonları göremez).
        yol_metni, ara = join_paths_doc(tables, self.edges, soru=question)
        if yol_metni:
            for ara_tablo in sorted(ara):
                doc = self._doc_by_table.get(ara_tablo.lower())
                if doc and doc not in texts:
                    texts.append(doc)
                    tables.append(ara_tablo)
            texts.append(yol_metni)

        return "\n\n".join(texts), tables
