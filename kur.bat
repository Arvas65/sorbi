@echo off
setlocal EnableDelayedExpansion
REM ============================================================
REM  SorBI - paket kurulum betigi
REM
REM  Kullanim:
REM     kur.bat                       Downloads'taki en yeni sorbi-*.tar.gz
REM     kur.bat C:\yol\paket.tar.gz   belirli bir paket
REM     kur.bat paket.tar.gz /kontrolsuz    kurulumdan sonra kontrol.bat kosma
REM
REM  Ne yapar, sirasiyla:
REM     1. Burasi gercekten SorBI deposu mu, bakar
REM     2. Islenmemis git degisikligi varsa UYARIR ve sorar
REM     3. Arsivi ACMADAN once bozuk mu diye dogrular
REM     4. Uzerine yazilacak her seyi _yedek\<zaman>\ altina kopyalar
REM     5. Gecici klasore acip xcopy ile uzerine yazar
REM        (tar dogrudan uzerine yazamiyor: "Can't unlink" hatasi)
REM     6. Gece kosumunu Gorev Zamanlayici'ya kurar (komut yazma derdi biter)
REM     7. kontrol.bat ile dogrular
REM
REM  DOKUNMADIKLARI: .venv, .git, demo\ (veritabanin) ve docs\kanit\
REM  icindeki olcum ciktilari. Kanit korumasi paketin icerigine GUVENMEZ:
REM  ne gelirse gelsin, docs\kanit acilan kopyadan temizlenir.
REM ============================================================

cd /d "%~dp0"
set HATA=0
set UYARI=0

echo ============================================================
echo  SorBI paket kurulumu
echo ============================================================
echo.

REM ---- 1) burasi SorBI mi ----
if not exist "app\config.py" (
    echo HATA: burasi SorBI deposu degil ^(app\config.py yok^).
    echo Betigi depo kokune koyup oradan calistirin.
    goto :bitir_hata
)
if not exist "eval\evaluate.py" (
    echo HATA: eval\evaluate.py yok - depo eksik gorunuyor.
    goto :bitir_hata
)
echo [1/6] Depo dogrulandi: %CD%

REM ---- paketi bul ----
set PAKET=%~1
if "!PAKET!"=="" (
    for /f "usebackq delims=" %%F in (`dir /b /o-d "%USERPROFILE%\Downloads\sorbi-*.tar.gz" 2^>nul`) do (
        if "!PAKET!"=="" set PAKET=%USERPROFILE%\Downloads\%%F
    )
)
if "!PAKET!"=="" (
    echo HATA: paket bulunamadi.
    echo Downloads icinde sorbi-*.tar.gz yok. Yolu elle verin:
    echo     kur.bat C:\yol\paket.tar.gz
    goto :bitir_hata
)
if not exist "!PAKET!" (
    echo HATA: paket yok: !PAKET!
    goto :bitir_hata
)
echo       Paket: !PAKET!
echo.

REM ---- 2) islenmemis git degisikligi ----
echo [2/6] Islenmemis degisiklik kontrolu...
where git >nul 2>&1
if errorlevel 1 (
    echo       git yok, atlaniyor.
) else (
    set KIRLI=
    for /f "usebackq delims=" %%L in (`git status --porcelain 2^>nul`) do set KIRLI=1
    if defined KIRLI (
        echo.
        echo       DIKKAT: depoda islenmemis degisiklik var:
        git status --short
        echo.
        echo       Bunlar yedeklenecek ama uzerlerine yazilabilir.
        echo       Devam etmek icin bir tusa basin, vazgecmek icin Ctrl+C.
        pause >nul
    ) else (
        echo       temiz.
    )
)
echo.

REM ---- 3) arsiv saglam mi ----
echo [3/6] Arsiv dogrulaniyor...
tar -tzf "!PAKET!" >nul 2>&1
if errorlevel 1 (
    echo HATA: arsiv okunamadi ya da bozuk.
    echo Indirme yarim kalmis olabilir; tekrar indirin.
    goto :bitir_hata
)
set DOSYA_SAYISI=0
for /f "usebackq delims=" %%F in (`tar -tzf "!PAKET!"`) do set /a DOSYA_SAYISI+=1
echo       saglam - !DOSYA_SAYISI! girdi
echo.

REM ---- 4) yedek ----
set STAMP=
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm" 2^>nul`) do set STAMP=%%i
if "!STAMP!"=="" set STAMP=yedek
set YEDEK=_yedek\!STAMP!

echo [4/6] Yedek aliniyor: !YEDEK!
mkdir "!YEDEK!" 2>nul
for %%D in (app eval tests ui docs) do (
    if exist "%%D" xcopy "%%D" "!YEDEK!\%%D\" /E /I /Q /Y /H >nul
)
for %%F in (CLAUDE.md pyproject.toml kontrol.bat kur.bat) do (
    if exist "%%F" copy /Y "%%F" "!YEDEK!\" >nul
)
if exist ".claude" xcopy ".claude" "!YEDEK!\.claude\" /E /I /Q /Y /H >nul
if exist ".github" xcopy ".github" "!YEDEK!\.github\" /E /I /Q /Y /H >nul
echo       alindi.
echo.

REM ---- 5) ac ve uzerine yaz ----
set GECICI=%TEMP%\sorbi_kur_!STAMP!
echo [5/6] Paket aciliyor...
if exist "!GECICI!" rmdir /S /Q "!GECICI!" 2>nul
mkdir "!GECICI!" 2>nul
tar -xzf "!PAKET!" -C "!GECICI!"
if errorlevel 1 (
    echo HATA: arsiv acilamadi.
    goto :bitir_hata
)
REM  KANIT KORUMASI: paketin ne tasidigina bakilmaksizin, docs\kanit
REM  icindeki olcum ciktilari ve karne gecmisi gecici klasorden SILINIR;
REM  boylece bu makinenin kaniti hicbir kurulumda ezilemez. Paketleyen
REM  kisi hata yapsa bile kanit guvende olur - nitekim bir kez yapildi:
REM  paket, paketleyenin KARNE-GECMIS.log dosyasini tasiyordu.
if exist "!GECICI!\docs\kanit" (
    for %%K in ("!GECICI!\docs\kanit\*") do (
        if /i not "%%~nxK"==".gitkeep" del /Q "%%K" >nul 2>&1
    )
    echo       kanit korumasi: paketten gelen olcum ciktilari atlandi
)

REM  tar dogrudan depo uzerine acilamiyor - salt-okunur dosyalarda
REM  "Can't unlink already-existing object" veriyor. Once gecici klasore,
REM  sonra xcopy /R ile uzerine.
xcopy "!GECICI!\*" "." /E /Y /R /H /Q >nul
if errorlevel 1 (
    echo HATA: dosyalar kopyalanamadi.
    echo Depoyu bir editorde ya da Streamlit'te acik biraktiysaniz kapatin.
    goto :bitir_hata
)
rmdir /S /Q "!GECICI!" 2>nul
echo       kuruldu.
echo.

REM ---- 6) otomatik kosumu kur ----
REM  Ihsan'in istegi (2026-08-21): "her seferinde komut yazmak istemiyorum".
REM  Zaten cift tikladigi betik bu; otomatigi de burada kuruyoruz ki
REM  ayrica bir sey calistirmasi gerekmesin. Kaldirmak: otomatik.bat /kaldir
echo [6/7] Otomatik gece kosumu...
if exist "otomatik.bat" (
    call otomatik.bat >nul 2>&1
    schtasks /Query /TN "SorBI gece kosumu" >nul 2>&1
    if errorlevel 1 (
        echo       kurulamadi - elle: otomatik.bat
        set UYARI=1
    ) else (
        echo       kuruldu: her gece 03:00, komut yazmaniza gerek yok
        echo       kaldirmak icin: otomatik.bat /kaldir
    )
) else (
    echo       otomatik.bat yok, atlandi.
)
echo.

REM ---- 7) dogrula ----
echo [7/7] Dogrulama...
if /i "%~2"=="/kontrolsuz" (
    echo       atlandi ^(/kontrolsuz verildi^)
    goto :bitir_ok
)
if not exist "kontrol.bat" (
    echo       kontrol.bat yok - dogrulama atlandi.
    goto :bitir_ok
)
echo.
echo ------------------------------------------------------------
call kontrol.bat
goto :son

:bitir_ok
echo.
echo ============================================================
echo  KURULUM TAMAM
echo.
echo  Yedek:  %CD%\!YEDEK!
echo.
echo  Bundan sonra komut yazmaniza gerek yok - gece kosumu kurulu.
echo  Yine de elle bakmak isterseniz:
echo     otomatik.bat /durum    son kosum ne zaman, ne oldu
echo     otomatik.bat /simdi    zamani beklemeden bir kez kos
echo     kontrol.bat            hizli denetim
echo ============================================================
goto :son

:bitir_hata
set HATA=1
echo.
echo ============================================================
echo  KURULUM YAPILMADI - depo degismedi.
echo ============================================================

:son
endlocal
