@echo off
setlocal EnableDelayedExpansion
REM ============================================================
REM  SorBI - hizli denetim (LLM'siz, ~1 dk)
REM
REM  CI her push'ta aynisini kosar. Bu betik ayni dort kapiyi
REM  kendi makinende gormek icindir.
REM
REM     kontrol.bat          dort kapi
REM     kontrol.bat tam      + 101 soruluk olcum (Ollama ya da API)
REM ============================================================
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)
set HATA=0

echo [1/4] ruff
"%PY%" -m ruff check . || set HATA=1

echo [2/4] testler
"%PY%" -m pytest tests -q -p no:cacheprovider --no-cov || set HATA=1

echo [3/4] test seti butunlugu (gold-only)
"%PY%" eval\evaluate.py --gold-only || set HATA=1

echo [4/4] guven karnesi (mutasyon)
"%PY%" eval\guven_olcum.py || set HATA=1

if /i "%~1"=="tam" (
    echo.
    echo [+] 101 soruluk olcum
    "%PY%" eval\evaluate.py --doctor || set HATA=1
    "%PY%" eval\evaluate.py || set HATA=1
)

echo.
if !HATA! neq 0 (
    echo SONUC: KIRMIZI - yukaridaki ilk hataya bakin.
) else (
    echo SONUC: YESIL
)
pause
endlocal & exit /b %HATA%
