# SorBI — on-prem / pilot kurulum imajı
FROM python:3.11-slim

WORKDIR /app

# Bağımlılıklar (katman önbelleği için önce requirements)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Demo veritabanları imaj içinde üretilir (sentetik veri — gerçek veri yok)
RUN python demo/seed_data.py && python demo/seed_satis.py

# Kalıcı veriler (kullanıcılar, profiller, denetim izi, RAG önbelleği) volume'a
VOLUME ["/app/.sorbi"]

EXPOSE 8501

# Ollama ayrı konteynerde ya da host'ta çalışır (docker-compose.yml'e bakın)
ENV SORBI_OLLAMA_URL=http://ollama:11434

HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "ui/streamlit_app.py", \
     "--server.address=0.0.0.0", "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
