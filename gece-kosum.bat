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

REM ---- 3) sonucu git ile disari it ----
REM  DIKKAT: yalnizca kanit ve gunluk islenir. Ihsan'in yarim kalmis
REM  calismasina dokunulmaz; master'a hic dokunulmaz. Itilen yer ayri
REM  bir uzak dal: olcum-otomatik.
where git >nul 2>&1
if errorlevel 1 (
    echo [gece] git yok - sonuc yerelde kaldi >> "!NLOG!"
    goto :bitir
)

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo [gece] git deposu degil - sonuc yerelde kaldi >> "!NLOG!"
    goto :bitir
)

git add docs/kanit docs/is-hatti/GUNLUK.md >>"!NLOG!" 2>&1

git diff --cached --quiet
if not errorlevel 1 (
    echo [gece] islenecek yeni kanit yok >> "!NLOG!"
    goto :bitir
)

git -c user.name="SorBI gece kosumu" -c user.email="gece@sorbi.local" ^
    commit -m "olcum: gece kosumu !STAMP! (otomatik)" >>"!NLOG!" 2>&1
if errorlevel 1 (
    echo [gece] commit basarisiz >> "!NLOG!"
    goto :bitir
)
echo [gece] kanit islendi >> "!NLOG!"

git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo [gece] uzak depo tanimli degil - kanit yerelde kaldi >> "!NLOG!"
    goto :bitir
)
git push origin HEAD:refs/heads/olcum-otomatik >>"!NLOG!" 2>&1
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
REM  Son kosumun ne zaman ve nasil bittigi tek satirda - acilis kapisi bunu okur.
> "docs\kanit\SON-GECE-KOSUMU.txt" echo GECE_KOSUMU zaman=!STAMP! cikis=!SONUC! log=!NLOG!
endlocal & exit /b 0
