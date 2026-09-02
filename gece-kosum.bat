@echo off
setlocal EnableDelayedExpansion
REM ============================================================
REM  SorBI - gece kosumu (Windows Gorev Zamanlayici calistirir)
REM
REM  Kimse basinda degil. Bu yuzden:
REM    - hicbir adim tusa basmayi beklemez
REM    - hicbir adim Notepad acmaz
REM    - her sey docs\kanit altina yazilir
REM    - sonuc git ile ayri bir uzak dala itilir, boylece Claude
REM      sabah oturumunda okuyabilir ve Ihsan hicbir sey gondermez
REM
REM  Elle de calistirilabilir:  gece-kosum.bat
REM ============================================================

cd /d "%~dp0"

set STAMP=
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm" 2^>nul`) do set STAMP=%%i
if "!STAMP!"=="" set STAMP=gece

if not exist "docs\kanit" mkdir "docs\kanit"
set NLOG=docs\kanit\gece-!STAMP!.log

> "!NLOG!" echo SorBI gece kosumu - !STAMP!

REM ---- 1) sanal ortam ----
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

REM ---- 2) tam denetim + olcum ----
echo [gece] kontrol.bat tam /sessiz  >> "!NLOG!"
call kontrol.bat tam /sessiz
set SONUC=!errorlevel!
echo [gece] kontrol.bat cikis kodu: !SONUC! >> "!NLOG!"

REM  Son kosumun ozeti git add'DEN ONCE yazilir. Onceden en sonda yaziliyordu;
REM  dosya diskte dogruydu ama commit'e giremedigi icin ITILEN kopya her zaman
REM  bir kosum geriden geliyordu. Bulut nobeti bu yuzden dun geceyi bu gece
REM  sanabilirdi. (BULGU-13, 2026-08-23)
> "docs\kanit\SON-GECE-KOSUMU.txt" echo GECE_KOSUMU zaman=!STAMP! cikis=!SONUC! log=!NLOG!

REM ---- 3) tek seferlik gece gorevleri ----
REM  gece-gorev\ altindaki her .bat bir kez kosar ve bitti\ altina tasinir.
REM  Boylece bir deney icin Ihsan'dan bir sey calistirmasi istenmez; is
REM  gecenin sirasina birakilir.
REM  SIRA ONEMLI: gorevler git adiminin ONUNDE kosar, yoksa urettikleri
REM  kanit o gece itilmez ve bir gun gecikir.
if exist "gece-gorev\*.bat" (
    if not exist "gece-gorev\bitti" mkdir "gece-gorev\bitti"
    for %%G in ("gece-gorev\*.bat") do (
        echo [gece] gorev: %%~nxG >> "!NLOG!"
        call "%%G" >>"!NLOG!" 2>&1
        echo [gece] gorev cikis: !errorlevel! >> "!NLOG!"
        move /Y "%%G" "gece-gorev\bitti\" >nul 2>&1
    )
)

REM ---- 4) sonucu git ile disari it ----
REM  DIKKAT: itilen sey YALNIZ kanittir. Calisma agaci, indeks ve HEAD
REM  okunmaz bile; hangi dalda olundugu onemli degildir.
REM
REM  Eskiden burada dogrudan "git add + commit + push HEAD:..." vardi.
REM  Bu, HEAD'in bir olcum dali oldugunu varsayiyordu. 2026-08-29'da
REM  ip-46-cekirdek acildi ve varsayim dustu: kanit commit'i o ozellik
REM  dalina atilacak, push ise HIZLI-ILERI SARMA olarak BASARILI olup
REM  yarim kalmis v4 calismasinin tamamini olcum dalina tasiyacakti.
REM  Push reddedilmiyordu - sessizce dogru calisip yanlis seyi yapiyordu.
REM  (BULGU-24, 2026-09-02.  Ayrinti ve testler: eval\kanit_it.py)
where git >nul 2>&1
if errorlevel 1 (
    echo [gece] git yok - sonuc yerelde kaldi >> "!NLOG!"
    goto :bitir
)

python eval\kanit_it.py --mesaj "olcum: gece kosumu !STAMP! (otomatik)" >>"!NLOG!" 2>&1
if errorlevel 1 (
    echo [gece] PUSH BASARISIZ - kanit yerelde duruyor, kaybolmadi. >> "!NLOG!"
    echo [gece] En olasi sebep: GitHub kimlik dogrulamasi yapilmamis. >> "!NLOG!"
    echo [gece] Cozum: bir kez yedekle.bat calistirin. >> "!NLOG!"
    REM  Bu satir acilis kapisinda gorunur; sessizce kaybolmaz.
    > "docs\kanit\PUSH-SORUNU.txt" echo PUSH_BASARISIZ zaman=!STAMP! sebep=kimlik_dogrulama_muhtemel cozum=yedekle.bat
) else (
    echo [gece] push tamam: olcum-otomatik dali >> "!NLOG!"
    if exist "docs\kanit\PUSH-SORUNU.txt" del /Q "docs\kanit\PUSH-SORUNU.txt" >nul 2>&1
)

:bitir

echo [gece] bitti >> "!NLOG!"
REM  Son kosumun ozeti yukarida (kanit itilmeden once) yazildi; burada
REM  yeniden yazilmaz - yoksa itilen kopya hep bir kosum geriden gelir.
endlocal & exit /b 0
