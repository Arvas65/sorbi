@echo off
REM ============================================================
REM  Tek seferlik: Gemini (API modu) ile 101 soruluk olcum
REM
REM  Gerekce: yerel 7B modelin p95'i 32.8 sn, G-12 hedefi 10 sn.
REM  Ihsan'in ucretsiz Gemini anahtari var. Bu kosum "API modu bu isi
REM  yapabiliyor mu" sorusunu olcumle cevaplar - tahminle degil.
REM
REM  ONKOSUL: SORBI_API_KEY tanimli olmali. Yoksa kosum atlanir.
REM
REM  GIZLILIK: baglamdaki DEGERLER bloklari mask_context ile kosulsuz
REM  dusuruluyor - gercek kolon degerleri Google'a GITMEZ. Sema
REM  metaverisi (tablo/kolon adlari) gider. Demo verisi zaten sentetik.
REM
REM  KOTA: ucretsiz katmanda hiz siniri var. Soru basina 4 sn bekleme
REM  konuyor; 429 alinirsa artan araliklarla 4 kez deneniyor ve yine
REM  olmazsa o soru "kota_asildi" diye AYRI sayiliyor - dogruluk kaybi
REM  gibi raporlanmiyor.
REM ============================================================
cd /d "%~dp0\.."
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

REM  Standart gece kosumu zaten API modunda kostuysa bu deney AYNI olcumu
REM  ikinci kez alir: bosuna 101 istek, bosuna kota. Atla.
if /i "%SORBI_MODE%"=="api" (
    echo [deney] Standart kosum zaten API modunda - ikinci Gemini olcumu atlandi.
    exit /b 0
)

if "%SORBI_API_KEY%"=="" (
    echo [deney] SORBI_API_KEY tanimli degil - Gemini olcumu ATLANDI.
    echo [deney] Anahtari kalici tanimlamak icin bir kez:
    echo [deney]     setx SORBI_API_KEY "buraya-anahtar"
    exit /b 0
)

set SORBI_MODE=api
set SORBI_API_BEKLEME=4

echo [deney] API modu ortam kontrolu
python eval\evaluate.py --doctor --mode api
if errorlevel 1 (
    echo [deney] API hazir degil - olcum ALINMADI.
    set SORBI_MODE=
    set SORBI_API_BEKLEME=
    exit /b 0
)

echo [deney] Gemini ile 101 soruluk olcum
python eval\evaluate.py --mode api

set SORBI_MODE=
set SORBI_API_BEKLEME=
exit /b 0
