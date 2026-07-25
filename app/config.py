"""SorBI yapılandırması. Ortam değişkenleriyle ezilebilir."""
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Model (ADR-1/5) ---
MODE = os.getenv("SORBI_MODE", "local")            # local | api
OLLAMA_URL = os.getenv("SORBI_OLLAMA_URL", "http://localhost:11434")
LOCAL_MODEL = os.getenv("SORBI_LOCAL_MODEL", "llama3.2:3b")
API_BASE = os.getenv("SORBI_API_BASE", "https://api.openai.com/v1")   # OpenAI-uyumlu
API_KEY = os.getenv("SORBI_API_KEY", "")
API_MODEL = os.getenv("SORBI_API_MODEL", "gpt-4o-mini")

# --- Veritabanı (G-14) ---
DB_URL = os.getenv("SORBI_DB_URL", f"sqlite:///{os.path.join(HERE, 'demo', 'hospital.db')}")
TARGET_DIALECT = os.getenv("SORBI_DIALECT", "sqlite")   # sqlite | postgres | tsql | mysql (ADR-4)
QUERY_TIMEOUT_S = int(os.getenv("SORBI_TIMEOUT", "30"))
MAX_ROWS = int(os.getenv("SORBI_MAX_ROWS", "1000"))

# --- RAG (ADR-3) ---
CHROMA_DIR = os.path.join(HERE, ".chroma")
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K_TABLES = 6

# --- Güven eşiği (G-03) ---
CONFIDENCE_THRESHOLD = 0.6

# --- Dosyalar ---
GLOSSARY_PATH = os.path.join(HERE, "demo", "glossary.json")
AUDIT_DB = os.path.join(HERE, ".audit.db")
