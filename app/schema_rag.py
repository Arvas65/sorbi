"""Şema keşfi + RAG bağlamı (G-05, G-06 — ADR-3).

G-05: Bağlantı tanımlandığında INFORMATION_SCHEMA/inspector ile tablo-kolon-ilişki
metaverisi otomatik keşfedilir, tablo başına bir 'belge' üretilir.
G-06: Terim sözlüğü belgeleri de indekse eklenir.

Chroma + çok dilli embedding varsayılan; kurulamazsa anahtar-kelime eşleşmesine
(preprocess.keywords + light_stem) otomatik düşer — demo her koşulda çalışır.
"""
import json
from typing import Optional

from sqlalchemy import create_engine, inspect

from app import config
from app.preprocess import keywords, light_stem


def discover_schema(db_url: Optional[str] = None) -> tuple[list[dict], dict[str, set]]:
    """Tablo başına belge (ad, kolonlar, FK) + kolon haritası {tablo: {kolonlar}}."""
    eng = create_engine(db_url or config.DB_URL)
    insp = inspect(eng)
    docs = []
    columns: dict[str, set] = {}
    for t in insp.get_table_names():
        col_names = [c["name"] for c in insp.get_columns(t)]
        columns[t.lower()] = {c.lower() for c in col_names}
        cols = [f"{c['name']} ({c['type']})" for c in insp.get_columns(t)]
        fks = [f"{t}.{fk['constrained_columns'][0]} -> {fk['referred_table']}.{fk['referred_columns'][0]}"
               for fk in insp.get_foreign_keys(t) if fk.get("constrained_columns")]
        text = f"TABLO {t}\nKOLONLAR: {', '.join(cols)}"
        if fks:
            text += f"\nILISKILER: {'; '.join(fks)}"
        docs.append({"id": f"table::{t}", "table": t, "text": text})
    eng.dispose()
    return docs, columns


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

    def __init__(self, db_url: Optional[str] = None):
        self.schema, self.known_columns = discover_schema(db_url)
        self.glossary = load_glossary()
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
        col = client.get_or_create_collection("sorbi_ctx", embedding_function=ef)
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
            res = self._chroma.query(query_texts=[question], n_results=k + len(self.terms))
            texts = res["documents"][0]
        else:
            picked = self._keyword_rank(question, self.schema, k)
            # terimler küçük; ilgili olanları anahtar kelimeyle ekle
            picked += self._keyword_rank(question, self.terms, 4)
            texts = [d["text"] for d in picked]
        tables = [t.split("TABLO ")[1].split("\n")[0] for t in texts if t.startswith("TABLO ")]
        return "\n\n".join(texts), tables
