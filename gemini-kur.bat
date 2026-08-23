@echo off
setlocal EnableDelayedExpansion
REM ============================================================
REM  SorBI - Gemini (API modu) kurulumu
REM
REM  Anahtari bir kez sorar, kalici olarak tanimlar ve gercekten
REM  calisip calismadigini DENER. Bir daha calistirmaniz gerekmez.
REM
REM     gemini-kur.bat            kur ve dogrula
REM     gemini-kur.bat /kaldir    yerel moda geri don
REM     gemini-kur.bat /durum     su an hangi mod, hangi model
REM ============================================================

cd /d "%~dp0"

if /i "%~1"=="/kaldir" goto :kaldir
if /i "%~1"=="/durum"  goto :durum

echo ============================================================
echo  SorBI - Gemini kurulumu
echo ============================================================
echo.
echo  Anahtariniz yoksa: https://aistudio.google.com/apikey
echo.

if not "%SORBI_API_KEY%"=="" (
    echo  Zaten tanimli bir anahtar var.
    set /p DEGISTIR="  Degistirmek ister misiniz? (e/H): "
    if /i not "!DEGISTIR!"=="e" goto :moda_al
)

set ANAHTAR=
set /p ANAHTAR="  Gemini API anahtarini yapistirin: "
if "!ANAHTAR!"=="" (
    echo.
    echo  Anahtar girilmedi - vazgecildi.
    goto :son
)
setx SORBI_API_KEY "!ANAHTAR!" >nul
set SORBI_API_KEY=!ANAHTAR!
echo  Anahtar kaydedildi.

:moda_al
setx SORBI_MODE api >nul
set SORBI_MODE=api
echo  Mod: api  ^(Ollama'ya artik ihtiyac yok^)
echo.

if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

echo  Gercekten calisiyor mu, deniyoruz...
echo ------------------------------------------------------------
python eval\evaluate.py --doctor --mode api
set SONUC=!errorlevel!
echo ------------------------------------------------------------
echo.
if !SONUC! NEQ 0 (
    echo  KURULUM TAMAMLANMADI - yukaridaki hataya bakin.
    echo.
    echo  En sik iki sebep:
    echo    1^) Anahtar yanlis ya da yetkisiz
    echo    2^) Model adi degismis. Su an: %SORBI_API_MODEL%
    echo       Baska bir model denemek icin:
    echo          setx SORBI_API_MODEL "gemini-3.1-flash-lite"
    echo.
    echo  Yerel moda donmek icin:  gemini-kur.bat /kaldir
) else (
    echo  HAZIR. Bu gece olcum Gemini ile kosacak.
    echo.
    echo  Not: baglamdaki gercek kolon degerleri Google'a GITMEZ
    echo  ^(mask_context^). Yalnizca sema metaverisi gider.
)
goto :son

:kaldir
setx SORBI_MODE local >nul
echo Yerel moda donuldu. Ollama'yi baslatmayi unutmayin:  ollama serve
goto :son

:durum
echo ============================================================
if "%SORBI_API_KEY%"=="" (echo  Anahtar : tanimli DEGIL) else (echo  Anahtar : tanimli)
if "%SORBI_MODE%"==""     (echo  Mod     : local ^(varsayilan^)) else (echo  Mod     : %SORBI_MODE%)
if "%SORBI_API_MODEL%"==""(echo  Model   : gemini-3.7-flash ^(varsayilan^)) else (echo  Model   : %SORBI_API_MODEL%)
echo ============================================================
goto :son

:son
echo.
echo Kapatmak icin bir tusa basin.
pause >nul
endlocal
