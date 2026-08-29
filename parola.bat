@echo off
REM ============================================================================
REM  parola.bat  --  bir kullanicinin parolasini degistirir.
REM
REM  NEDEN (BULGU-15, 2026-08-23): .sorbi\users.json 884f8d9 commit'inde
REM  HERKESE ACIK depoya itildi; icinde admin salt + hash var. Dosyayi
REM  takipten cikarmak onu gecmisten SILMEZ. Parolayi degistirmek, sizmis
REM  hash'i degersiz kilar.
REM
REM  Parola ekrana yazilmaz, komut gecmisine dusmez, dosyaya kaydedilmez.
REM ============================================================================
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

"%PY%" tools\parola_degistir.py %*
set SONUC=%errorlevel%

echo.
if %SONUC% neq 0 (
    echo Parola DEGISMEDI. Yukaridaki hatayi giderip tekrar deneyin.
)
pause
endlocal & exit /b %SONUC%
