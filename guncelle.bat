@echo off
setlocal
REM ============================================================
REM  SorBI - guncelle: GitHub'daki master'i cek, bagimliliklari
REM  kur, denetimi kos. Cift tiklamak yeter.
REM
REM  Islenmemis yerel degisiklik varsa DURUR; hicbir seyin
REM  uzerine yazmaz.
REM ============================================================
cd /d "%~dp0"

git diff --quiet && git diff --cached --quiet
if errorlevel 1 (
    echo Islenmemis yerel degisiklik var. Once onlari commit'leyin ya da saklayin:
    git status --short
    pause
    exit /b 1
)

git checkout master || goto :hata
git pull --ff-only origin master || goto :hata

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)
"%PY%" -m pip install -q -r requirements.txt || goto :hata

call kontrol.bat
endlocal
exit /b 0

:hata
echo.
echo GUNCELLEME YAPILMADI - yukaridaki hataya bakin.
pause
endlocal
exit /b 1
