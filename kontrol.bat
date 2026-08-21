@echo off
setlocal EnableDelayedExpansion
REM ============================================================
REM  SorBI - olcum kontrol betigi
REM
REM  Kullanim:
REM     kontrol.bat        hizli kontrol (~1-2 dk, LLM gerekmez)
REM     kontrol.bat tam    hizli kontrol + 101 soruluk olcum (~25-40 dk)
REM
REM  Her sey docs\kanit\kontrol-<zaman>.log dosyasina yazilir.
REM  Betik bittiginde o dosyanin yolunu soyler; Claude'a onu gonder.
REM
REM  NOT: bu dosya bilerek Turkce karaktersiz yazildi. Windows komut
REM  isteminde kod sayfasi degisken; bir tanilama betiginin kendisi
REM  okunamaz hale gelirse tanilama yapamaz.
REM ============================================================

cd /d "%~dp0"

REM ---- beklenen degerler ----
REM Karne sayilari BURADA TUTULMUYOR. Ilk surumde tutuluyordu ve yanlisti:
REM sayilar yazildiklari makinenin verisine aitti, baska bir kopyada
REM "gerileme" gibi gorundu. Karne artik kendi gecmisiyle karsilastiriliyor
REM (docs\kanit\KARNE-GECMIS.log). Burada yalnizca makineden bagimsiz
REM olanlar duruyor.
set BEKLENEN_TEST=320
set BEKLENEN_GOLD=101

set HATA=0
set UYARI=0
set GPU_YOK=0

REM ---- zaman damgasi ----
set STAMP=
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm" 2^>nul`) do set STAMP=%%i
if "!STAMP!"=="" set STAMP=kosum

if not exist "docs\kanit" mkdir "docs\kanit"
set LOG=docs\kanit\kontrol-!STAMP!.log

echo ============================================================
echo  SorBI kontrol - !STAMP!
echo  Log: !LOG!
echo ============================================================
echo.

> "!LOG!" echo SorBI kontrol raporu - !STAMP!
>>"!LOG!" echo Dizin: %CD%
>>"!LOG!" echo.

REM ============================================================
REM  0) Sanal ortam
REM ============================================================
echo [0/6] Sanal ortam...
if not defined VIRTUAL_ENV (
    if exist ".venv\Scripts\activate.bat" (
        call ".venv\Scripts\activate.bat"
        echo       .venv etkinlestirildi.
    ) else (
        echo       HATA: sanal ortam yok ve .venv bulunamadi.
        echo       Yapilacak:  python -m venv .venv
        echo                   .venv\Scripts\activate
        echo                   pip install -r requirements\dev.txt
        goto :son
    )
) else (
    echo       zaten etkin.
)
>>"!LOG!" echo === PYTHON ===
python -c "import sys;print(sys.version);print(sys.executable)" >>"!LOG!" 2>&1

REM ---- gerekli paketler kurulu mu ----
python -m ruff --version >nul 2>&1
if errorlevel 1 (
    echo       ruff yok, gelistirme bagimliliklari kuruluyor...
    python -m pip install -r requirements\dev.txt >>"!LOG!" 2>&1
    python -m ruff --version >nul 2>&1
    if errorlevel 1 (
        echo       HATA: ruff kurulamadi. Ayrinti: !LOG!
        set HATA=1
        goto :son
    )
    echo       kuruldu.
)
echo.

REM ============================================================
REM  1) ruff
REM ============================================================
echo [1/6] ruff check ...
>>"!LOG!" echo. & >>"!LOG!" echo === RUFF ===
python -m ruff check . >>"!LOG!" 2>&1
if errorlevel 1 (
    echo       BASARISIZ - ayrinti log'da
    set HATA=1
) else (
    echo       temiz
)
echo.

REM ============================================================
REM  2) testler
REM ============================================================
echo [2/6] pytest ...
>>"!LOG!" echo. & >>"!LOG!" echo === PYTEST ===
python -m pytest tests\ --cov=app --cov=eval >>"!LOG!" 2>&1
if errorlevel 1 (
    echo       BASARISIZ - ayrinti log'da
    set HATA=1
) else (
    findstr /C:"!BEKLENEN_TEST! passed" "!LOG!" >nul
    if errorlevel 1 (
        echo       gecti, ama test sayisi beklenenden farkli ^(beklenen !BEKLENEN_TEST!^)
        set UYARI=1
    ) else (
        echo       !BEKLENEN_TEST! test gecti
    )
)
echo.

REM ============================================================
REM  3) gold SQL sagligi
REM ============================================================
echo [3/6] gold SQL sagligi ^(LLM'siz^) ...
>>"!LOG!" echo. & >>"!LOG!" echo === GOLD-ONLY ===
python eval\evaluate.py --gold-only >>"!LOG!" 2>&1
findstr /C:"101/101" "!LOG!" >nul
if errorlevel 1 (
    echo       BASARISIZ - 101/101 degil. Veri seti ya da paket bozuk.
    set HATA=1
) else (
    echo       101/101 calisiyor
)
echo.

REM ============================================================
REM  4) guven kontrolu karnesi
REM ============================================================
echo [4/6] guven kontrolu karnesi ^(LLM'siz^) ...
set KARNE=docs\kanit\karne-!STAMP!.txt
python eval\guven_olcum.py > "!KARNE!" 2>&1
>>"!LOG!" echo. & >>"!LOG!" echo === GUVEN KARNESI ===
type "!KARNE!" >>"!LOG!"

REM Karne, sonunda tek satirlik makine okunur ozet basiyor:
REM   KARNE_OZET gun=... gold=... alarm=... mutant=... yakalanan=...
REM Betik hizalamaya degil BU satira bakar.
set KARNE_SATIR=
for /f "usebackq delims=" %%L in (`findstr /B /C:"KARNE_OZET" "!KARNE!"`) do set KARNE_SATIR=%%L
if "!KARNE_SATIR!"=="" (
    echo       HATA: karne ozet satiri yok - betik cokmus olabilir.
    set HATA=1
) else (
    echo       !KARNE_SATIR!
    set BEKLENEN_SATIR=KARNE_OZET gun=!BEKLENEN_GUN! gold=101 alarm=!BEKLENEN_ALARM! mutant=!BEKLENEN_MUTANT! yakalanan=!BEKLENEN_YAKALAMA!
    if "!KARNE_SATIR!"=="!BEKLENEN_SATIR!" (
        echo       beklendigi gibi.
    ) else (
        echo       DIKKAT: beklenenden farkli.
        echo       beklenen: !BEKLENEN_SATIR!
        set UYARI=1
    )
)
echo.

REM ============================================================
REM  5) ortam sagligi (Ollama / GPU)
REM ============================================================
echo [5/6] ortam sagligi ^(--doctor^) ...
set DOC=docs\kanit\doctor-!STAMP!.txt
python eval\evaluate.py --doctor > "!DOC!" 2>&1
set DOCRC=!errorlevel!
>>"!LOG!" echo. & >>"!LOG!" echo === DOCTOR ===
type "!DOC!" >>"!LOG!"

if !DOCRC! NEQ 0 (
    echo       Ollama hazir degil - ayrinti log'da
    echo       Tam olcum bu haliyle ALINMAMALI.
    set UYARI=1
) else (
    echo       Ollama hazir
    set DOC_SATIR=
    for /f "usebackq delims=" %%L in (`findstr /B /C:"DOCTOR_OZET" "!DOC!"`) do set DOC_SATIR=%%L
    if not "!DOC_SATIR!"=="" echo       !DOC_SATIR!
    REM Taban model ADR-1 rev.2 ile ayni mi? (Bir kez ayrismisti: karar
    REM yazildi, koda inmedi ve olcum yanlis modelle alinacakti.)
    echo !DOC_SATIR! | findstr /C:"model=qwen2.5-coder" >nul
    if errorlevel 1 (
        echo       DIKKAT: taban model ADR-1'deki qwen2.5-coder:7b degil.
        echo       Modeli cekin:  ollama pull qwen2.5-coder:7b-instruct
        set UYARI=1
    )
    echo !DOC_SATIR! | findstr /C:"hizlandirma=cpu" >nul
    if not errorlevel 1 (
        echo       DIKKAT: model CPU'da calisiyor - GPU devrede degil.
        echo       Olcumu ALMA. Once Ollama'yi durdurup: setx OLLAMA_VULKAN 0
        echo       sonra yeniden baslatin. Daha once p50'yi 24 sn'den 7 sn'ye indirmisti.
        set UYARI=1
        set GPU_YOK=1
    )
)
echo.

REM ============================================================
REM  6) tam olcum (istege bagli)
REM ============================================================
echo [6/6] tam olcum...
if /i "%~1"=="tam" (
    if !DOCRC! NEQ 0 (
        echo       ATLANDI - Ollama hazir degil.
        set UYARI=1
    ) else if "!GPU_YOK!"=="1" (
        echo       ATLANDI - model CPU'da. Bu olcum G-12 icin anlamsiz olurdu.
        set UYARI=1
    ) else (
        echo       101 soru kosuluyor, 25-40 dakika surebilir. Bekleyin...
        >>"!LOG!" echo. & >>"!LOG!" echo === TAM OLCUM ===
        python eval\evaluate.py >>"!LOG!" 2>&1
        if errorlevel 1 (
            echo       BASARISIZ - ayrinti log'da
            set HATA=1
        ) else (
            echo       bitti.
        )
    )
) else (
    echo       atlandi ^(calistirmak icin: kontrol.bat tam^)
)

:son
echo.
echo ============================================================
if "!HATA!"=="1" (
    echo  SONUC: HATA VAR - asagidaki log'u Claude'a gonder
) else (
    if "!UYARI!"=="1" (
        echo  SONUC: gecti, ama DIKKAT edilecek noktalar var
    ) else (
        echo  SONUC: her sey beklendigi gibi
    )
)
echo.
echo  Gonderilecek dosya:
echo     %CD%\!LOG!
echo ============================================================
echo.
REM Sessiz mod: zamanlanmis kosumda kimse tusa basmaz ve Notepad acilmamalidir.
REM Interaktif bir adim, otomatik kosumu sonsuza kadar bekletir.
set SESSIZ=0
if /i "%~1"=="/sessiz" set SESSIZ=1
if /i "%~2"=="/sessiz" set SESSIZ=1
if "!SESSIZ!"=="0" (
    if exist "!LOG!" (
        echo Log'u simdi acmak icin bir tusa basin, atlamak icin Ctrl+C.
        pause >nul
        notepad "!LOG!"
    )
)
endlocal & exit /b %HATA%
