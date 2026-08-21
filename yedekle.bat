@echo off
setlocal EnableDelayedExpansion
REM ============================================================
REM  SorBI - calismayi GitHub'a it
REM
REM  Neden var (bulgu, 2026-08-21):
REM  GitHub'daki depo 25 Temmuz'dan beri hic guncellenmemisti. v3 isinin
REM  TAMAMI - guven kontrolleri, olcum hatti, 320 test, CLAUDE.md, calisma
REM  duzeni - yalnizca yerel diskte duruyordu. Iki sonucu vardi:
REM     1. Tek nokta ariza: disk giderse alti haftalik is gider
REM     2. CI hic kosamadi - workflow dosyasi uzakta yoktu
REM
REM  Kullanim:
REM     yedekle.bat            calismayi isle ve it
REM     yedekle.bat /durum     ne itilecek, once bir bak
REM
REM  Cift tiklamak yeterli. Ilk seferde GitHub kimlik dogrulamasi
REM  isteyebilir - tarayici acilir, bir kez onaylarsiniz, sonra hatirlar.
REM ============================================================

cd /d "%~dp0"

if not exist "app\config.py" (
    echo HATA: burasi SorBI deposu degil.
    goto :son
)
where git >nul 2>&1
if errorlevel 1 (
    echo HATA: git kurulu degil. https://git-scm.com
    goto :son
)
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo HATA: burasi bir git deposu degil.
    goto :son
)

REM ---- takilmis kilit ----
REM  Bir kez oldu: .git\index.lock kaldi ve butun git islemleri durdu.
REM  Yalnizca calisan bir git yoksa temizlenir.
if exist ".git\index.lock" (
    tasklist /FI "IMAGENAME eq git.exe" 2>nul | find /I "git.exe" >nul
    if errorlevel 1 (
        del /F /Q ".git\index.lock" >nul 2>&1
        echo Takilmis .git\index.lock temizlendi.
    ) else (
        echo DIKKAT: baska bir git islemi calisiyor. Bitmesini bekleyin.
        goto :son
    )
)

for /f "usebackq delims=" %%B in (`git rev-parse --abbrev-ref HEAD 2^>nul`) do set DAL=%%B
if "!DAL!"=="" set DAL=master

echo ============================================================
echo  Dal: !DAL!
echo ============================================================
echo.
echo Islenecekler:
git status --short
echo.

if /i "%~1"=="/durum" (
    echo ------------------------------------------------------------
    echo Uzakta olmayan islemeler:
    git log --oneline origin/!DAL!..HEAD 2>nul || echo   ^(dal uzakta hic yok - hepsi itilecek^)
    echo ------------------------------------------------------------
    echo Itmek icin argumansiz calistirin: yedekle.bat
    goto :son
)

set STAMP=
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd HH:mm" 2^>nul`) do set STAMP=%%i

git add -A
git diff --cached --quiet
if not errorlevel 1 (
    echo Islenecek yeni degisiklik yok.
) else (
    git commit -m "SorBI v3 calismasi - !STAMP!" 
    if errorlevel 1 (
        echo HATA: commit yapilamadi.
        echo Git kimliginiz tanimli olmayabilir. Bir kez sunlari calistirin:
        echo     git config --global user.name "Ihsan Arvas"
        echo     git config --global user.email "arvass125@gmail.com"
        goto :son
    )
)

echo.
echo GitHub'a itiliyor...
git push -u origin !DAL!
if errorlevel 1 (
    echo.
    echo ------------------------------------------------------------
    echo Push basarisiz. En sik iki sebep:
    echo.
    echo  1^) Kimlik dogrulama yapilmamis.
    echo     En kolayi GitHub CLI:  https://cli.github.com
    echo     Kurduktan sonra bir kez:  gh auth login
    echo     Sonra bu betigi tekrar calistirin.
    echo.
    echo  2^) Uzak adres yanlis. Kontrol:
    git remote -v
    echo ------------------------------------------------------------
    goto :son
)

echo.
echo ============================================================
echo  TAMAM - calisma GitHub'da.
echo.
echo  Bundan sonra:
echo    - CI her push'ta kendiliginden kosar ^(yesil/kirmizi sinyal^)
echo    - gece kosumu kaniti olcum-otomatik dalina itebilir
echo    - disk giderse is gitmez
echo ============================================================

:son
echo.
echo Kapatmak icin bir tusa basin.
pause >nul
endlocal
