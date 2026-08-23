@echo off
REM ============================================================
REM  Tek seferlik deney: num_ctx 8192 gecikmeye ne kadar mal oluyor?
REM
REM  Gerekce:
REM     16 Agustos   num_ctx=4096   p50 14.4  p95 21.2   acc %62
REM     22 Agustos   num_ctx=8192   p50 21.7  p95 32.8   acc %56
REM  Iki kosum arasinda referans gun DE degisti; fark num_ctx'e mal
REM  edilemez. Bu deney tek degiskeni oynatir.
REM
REM  num_ctx YALNIZ Ollama parametresidir. Yerel model kapaliysa ya da
REM  sistem API moduna alinmissa bu deneyin anlami yoktur ve kosmaz.
REM  (Ilk surumu bu kontrolu yapmiyordu: Ollama kapaliyken 101 sorunun
REM  hepsi baglanti hatasi verip SAHTE bir cokus raporlayacakti.)
REM ============================================================
cd /d "%~dp0\.."
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

if /i "%SORBI_MODE%"=="api" (
    echo [deney] Sistem API modunda - num_ctx deneyi ANLAMSIZ, atlandi.
    exit /b 0
)

echo [deney] Yerel model hazir mi
python eval\evaluate.py --doctor --mode local >nul 2>&1
if errorlevel 1 (
    echo [deney] Ollama hazir degil - num_ctx deneyi ATLANDI.
    echo [deney] Yerel olcum icin: ollama serve
    exit /b 0
)

set SORBI_NUM_CTX=4096
echo [deney] num_ctx=4096 ile 101 soruluk olcum
python eval\evaluate.py --mode local
set SORBI_NUM_CTX=
exit /b 0
