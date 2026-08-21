@echo off
setlocal EnableDelayedExpansion
REM ============================================================
REM  SorBI - otomatik kosum kurulumu
REM
REM  Amac: Ihsan'in bir daha komut yazmamasi. Windows Gorev
REM  Zamanlayici her gece kosumu kendisi baslatir.
REM
REM  Kullanim:
REM     otomatik.bat            kur (varsa gunceller)
REM     otomatik.bat /kaldir    kaldir
REM     otomatik.bat /durum     ne kurulu, ne zaman kosacak
REM     otomatik.bat /simdi     zamani beklemeden bir kez kos
REM
REM  Kurulan gorev:
REM     "SorBI gece kosumu"  - her gece 03:00
REM        ruff + testler + gold saglik + karne + 101 soruluk olcum
REM        sonucu docs\kanit altina yazar ve olcum-otomatik dalina iter
REM
REM  Yonetici hakki GEREKMEZ - gorev kullanici duzeyinde kurulur.
REM  Kosabilmesi icin bilgisayarin acik ve kullanicinin oturum acmis
REM  olmasi gerekir; kacan kosum ertesi gece telafi edilir.
REM ============================================================

cd /d "%~dp0"
set GOREV=SorBI gece kosumu
set SAAT=03:00

if /i "%~1"=="/kaldir" goto :kaldir
if /i "%~1"=="/durum"  goto :durum
if /i "%~1"=="/simdi"  goto :simdi

REM ---------------------------------------------------------- kur
echo ============================================================
echo  SorBI otomatik kosum kurulumu
echo ============================================================
echo.

if not exist "gece-kosum.bat" (
    echo HATA: gece-kosum.bat bulunamadi.
    echo Bu betik depo kokunden calistirilmali.
    goto :son
)
if not exist "app\config.py" (
    echo HATA: burasi SorBI deposu degil.
    goto :son
)

set KOMUT="%CD%\gece-kosum.bat"
schtasks /Create /TN "!GOREV!" /TR !KOMUT! /SC DAILY /ST !SAAT! /F >nul 2>&1
if errorlevel 1 (
    echo HATA: gorev olusturulamadi.
    echo Gorev Zamanlayici kisitli olabilir. Su komutu elle deneyin:
    echo    schtasks /Create /TN "!GOREV!" /TR !KOMUT! /SC DAILY /ST !SAAT! /F
    goto :son
)

echo  Kuruldu.
echo.
echo    Gorev : !GOREV!
echo    Saat  : her gece !SAAT!
echo    Kosan : %CD%\gece-kosum.bat
echo.
echo  Her gece sunlar kendiliginden olacak:
echo    - ruff, testler, gold saglik, guven karnesi
echo    - 101 soruluk olcum ^(Ollama acikas^)
echo    - sonuc docs\kanit altina yazilir
echo    - olcum-otomatik dalina itilir, Claude sabah okur
echo.
echo  Artik komut yazmaniz gerekmiyor.
echo.
echo  Vazgecmek icin:  otomatik.bat /kaldir
echo  Denemek icin  :  otomatik.bat /simdi
echo ============================================================
goto :son

REM ---------------------------------------------------------- kaldir
:kaldir
schtasks /Delete /TN "!GOREV!" /F >nul 2>&1
if errorlevel 1 (
    echo Kurulu bir gorev bulunamadi ^(zaten kaldirilmis olabilir^).
) else (
    echo Kaldirildi: !GOREV!
    echo Artik gece kosumu olmayacak.
)
goto :son

REM ---------------------------------------------------------- durum
:durum
echo ============================================================
schtasks /Query /TN "!GOREV!" /FO LIST 2>nul | findstr /C:"TaskName" /C:"Next Run" /C:"Status" /C:"Last Run" /C:"Last Result" /C:"Sonraki" /C:"Durum"
if errorlevel 1 echo Kurulu gorev yok. Kurmak icin: otomatik.bat
echo ------------------------------------------------------------
if exist "docs\kanit\SON-GECE-KOSUMU.txt" (
    type "docs\kanit\SON-GECE-KOSUMU.txt"
) else (
    echo Henuz bir gece kosumu yapilmadi.
)
echo ============================================================
goto :son

REM ---------------------------------------------------------- simdi
:simdi
echo Gece kosumu simdi baslatiliyor. Bu 25-40 dakika surebilir.
echo Kapatmadan birakabilirsiniz; hicbir yerde tusa basmaniz gerekmez.
echo.
call gece-kosum.bat
echo.
echo Bitti. Ozet:
if exist "docs\kanit\SON-GECE-KOSUMU.txt" type "docs\kanit\SON-GECE-KOSUMU.txt"
goto :son

:son
endlocal
