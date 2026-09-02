@echo off
REM ============================================================================
REM  it2.bat  --  IP-33'un isini commit'lere boler ve iter.
REM
REM  Onceki it.bat gibi: her adimin ne tasidigi yaninda yazili, PUSH EN SONDA
REM  ve onay istiyor. Farkli olarak bu betik ONCE DOGRULUYOR: testler kirmizi
REM  ya da ruff kirliyse hicbir sey commit edilmez.
REM
REM  Sebep: bugun tam olarak bunun eksikligi bir hataya yol acti. `seed`
REM  duzeltmesi (BULGU-08) olculmeden itilseydi API yolu kirik gidecekti;
REM  kontrol.bat yakaladi (BULGU-17). Kapi betigin icinde olmali.
REM ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

REM  --- On kosul: git index'i temiz olmali ---------------------------------
REM  Asagidaki adimlarin hepsi "git add <yol>" + "git commit" kaliginda.
REM  Bare commit STAGE'DEKI HER SEYI isler; index'te onceden bekleyen bir sey
REM  varsa yanlis commit'e karisir. Bu yuzden once bakiyoruz.
git diff --cached --quiet
if errorlevel 1 (
    echo.
    echo  DURDU: git index'inde zaten bekleyen degisiklikler var:
    git diff --cached --name-only
    echo.
    echo  Bu betik commit'leri kendi gruplarina ayiriyor; bekleyen bir sey
    echo  varsa yanlis gruba karisir. Once onlari isleyin ya da
    echo  "git reset" ile stage'i bosaltin, sonra tekrar kosun.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  0a) TAKIPTEN CIKARMA - .sorbi/ (BULGU-15)
echo ============================================================
REM  .sorbi/ altinda git'in hala takip ettigi ne varsa cikarilir.
REM  users.json daha once cikarildi; connections.json HALA takipteydi ve
REM  test bunu yakaladi. Dosya su an bos ({}), yani sizmis bir sir YOK -
REM  ama connections.py parolayi baglanti URL'sinin ICINE gomuyor
REM  (kullanici:sifre@host). Ilk Postgres baglantisinda o dosya parola
REM  tasiyacakti ve HERKESE ACIK depoya gidecekti.
REM
REM  Dosyalar diskte kalir; yalnizca git takibinden cikar.

git ls-files ".sorbi" > "%TEMP%\sorbi_takip.txt" 2>nul
for /f "usebackq delims=" %%F in ("%TEMP%\sorbi_takip.txt") do (
    echo   takipten cikariliyor: %%F
    git rm --cached -q "%%F" || goto :hata
)

for %%X in ("%TEMP%\sorbi_takip.txt") do if %%~zX equ 0 (
    echo   .sorbi altinda takip edilen dosya yok - zaten temiz.
) else (
    git commit -m "BULGU-15: .sorbi/ takipten cikarildi - baglanti URL'leri parola tasiyor" || goto :hata
)

echo.
echo ============================================================
echo  0b) DOGRULAMA - kirmizi bir seyle commit yapilmaz
echo ============================================================

echo.
echo [1/3] ruff...
"%PY%" -m ruff check . || goto :dogrulama_kirmizi

echo.
echo [2/3] testler...
"%PY%" -m pytest tests/ -q || goto :dogrulama_kirmizi

echo.
echo [3/3] guven karnesi (LLM'siz)...
"%PY%" eval\guven_olcum.py > "%TEMP%\karne.txt" 2>&1
if errorlevel 1 (
    type "%TEMP%\karne.txt"
    goto :dogrulama_kirmizi
)
findstr /C:"KARNE_OZET" "%TEMP%\karne.txt"

echo.
echo  Dogrulama yesil. Devam ediliyor.
echo.
pause

REM --------------------------------------------------------------------------
echo.
echo ============================================================
echo  1) Guven kontrolleri (B-7) - IP-03c triyajinin kod tarafi
echo ============================================================
REM  B7R-03  filtresiz artik zaman ve durum daraltmasini goruyor (%59 -^> %83)
REM  B7R-06  bilinen_degerler tablo.kolon anahtari + takma ad cozumlemesi
REM  B7R-01  sema_ortusmez kolon adlarina da bakiyor (yanlis alarm 7 -^> 3)
REM  yeni    deger_uyumsuz ve distinct_eksik kontrolleri
git add app/guven.py app/schema_rag.py tests/test_guven_b7r.py
git commit -m "IP-03c: B7R-01/03/06 duzeltmeleri + deger_uyumsuz ve distinct_eksik kontrolleri" || goto :hata

REM --------------------------------------------------------------------------
echo.
echo ============================================================
echo  2) B7R-05 - guven bayraklari denetim izine
echo ============================================================
REM  denetim.guven_kodlari kolonu (yerinde goc; ekleme-yalniz kayit korunuyor)
REM  audit.guven_karnesi() ile SAHA sayimi. Saha karnesi artik tahmin degil.
git add app/audit.py app/pipeline.py tests/test_audit_guven.py
git commit -m "B7R-05: guven bayraklari denetim izine yaziliyor; saha karnesi sayilabilir" || goto :hata

REM --------------------------------------------------------------------------
echo.
echo ============================================================
echo  3) BULGU-N4 - suit sessizce atlamiyor
echo ============================================================
REM  conftest.py ice aktarma aninda tohumluyor; skipif ve kosullu pytest.skip
REM  alti yerden silindi. DB silinmis halde: 422 gecti, 0 atlandi.
REM  Onceden cogu test atlaniyor ve pytest yine cikis kodu 0 veriyordu.
git add tests/conftest.py tests/test_suit_dururlugu.py ^
        tests/test_connections.py tests/test_eval_testset.py tests/test_executor.py ^
        tests/test_eval_runner.py tests/test_join_paths.py tests/test_ornek_degerler.py
git commit -m "BULGU-N4: suit kosula bagli atlamiyor; conftest tohumluyor, testle kilitli" || goto :hata

REM --------------------------------------------------------------------------
echo.
echo ============================================================
echo  4) BULGU-08/17 - api modunda belirlenim
echo ============================================================
REM  seed istege gercekten konuyor. Uc nokta tanimiyorsa (Gemini: HTTP 400
REM  "Unknown name seed") bir kez alansiz tekrar deneniyor ve OGRENILIYOR.
REM  Damga artik ne gonderdigimizi degil, uc noktanin ne KABUL ETTIGINI yazar.
git add app/generator.py app/config.py tests/test_api_modu.py
git commit -m "BULGU-08/17: seed istege konuyor; uc nokta tanimiyorsa alansiz devam, damga gercegi yazar" || goto :hata

REM --------------------------------------------------------------------------
echo.
echo ============================================================
echo  5) BULGU-05/06/09/10 + YENI-C - olcum hattinin durustlugu
echo ============================================================
REM  BULGU-09/10  regresyon kapisi esli McNemar karari
REM               (bozulan - duzelen ^>= 3 VE p ^< 0,05)
REM               eski "3 puan" esigi olculen gurultunun ALTINDAYDI (~%45)
REM  BULGU-05     damgali docs/kanit/sonuclar-*.json
REM  BULGU-06     "yakalanan" -^> "reddedilen"; karne tarafi "bayraklanan"
REM  YENI-C       soru bazinda gercek mod kaydi
git add eval/evaluate.py tests/test_regresyon_kapisi.py tests/test_rapor_durustlugu.py
git commit -m "BULGU-05/06/09/10 + YENI-C: regresyon kapisi McNemar'a bagli, rapor iki tanimi ayiriyor" || goto :hata

REM --------------------------------------------------------------------------
echo.
echo ============================================================
echo  6) B7R-08 / BULGU-04 - mutant havuzu durustlesti
echo ============================================================
REM  Havuza gercek model hatasina benzeyen dort aile eklendi:
REM  deger_takasi, karsilastirma, distinct_dus, join_ici_disi. 239 -^> 306.
REM  Yakalama %83,3 -^> %72,5'e DUSTU (havuzun kolayligi gorundu), sonra yeni
REM  kontrollerle %80,1'e cikti. Gereksiz bayrak bastan sona 1/101.
git add eval/guven_olcum.py
git commit -m "B7R-08: mutant havuzuna gercekci hata aileleri; karne %%83,3 -^> %%80,1 ama DURUST" || goto :hata

REM --------------------------------------------------------------------------
echo.
echo ============================================================
echo  7) BULGU-15 - kimlik korumasi
echo ============================================================
REM  .sorbi/users.json HERKESE ACIK depoya itilmisti (884f8d9). Parola
REM  dondu; takipten cikarma 0a'da yapildi. Bu commit KORUMAYI ekliyor:
REM  test_depo_hijyeni.py ayni hatanin tekrarini kirmiziya dondurur.
REM  Gecmisteki kopya ayri bir karar - bkz. IP-33/VERIFY.md.
git add .gitignore tests/test_depo_hijyeni.py tools/parola_degistir.py parola.bat
git commit -m "BULGU-15: kimlik deposu korumasi + parola degistirme araci" || goto :hata

REM --------------------------------------------------------------------------
echo.
echo ============================================================
echo  8) YENI-A/B + belgeler
echo ============================================================
REM  ADR-3 (RAG) ve ADR-4 (sqlglot) yazildi; ADR-5 taslagi depoya indi.
REM  CLAUDE.md artik IKI karneyi ayri yaziyor: mutasyon %80,1 - saha %20.
REM  CI'a LLM'siz B-7 karnesi eklendi.
git add CLAUDE.md .github/workflows/ci.yml docs/is-hatti/v3/ADR docs/is-hatti/v3/IP-03c ^
        docs/is-hatti/v3/IP-33 docs/is-hatti/GUNLUK.md
git commit -m "YENI-A/B: ADR-3/4/5 depoda, CLAUDE.md iki karneyi ayiriyor, CI'a B-7 karnesi" || goto :hata

REM --------------------------------------------------------------------------
echo.
echo ============================================================
echo  9) Kanit dosyalari
echo ============================================================
git add docs/kanit
git commit -m "olcum: 08-23 kontrol kosumu kanitlari" || echo (kanitta degisiklik yoktu)

REM --------------------------------------------------------------------------
echo.
echo === Kalan (bilerek commit edilmedi) ===
git status --short
echo.
echo === Yapilan commit'ler ===
git log --oneline origin/ip-01-02-altyapi..HEAD

echo.
echo ============================================================
echo  ITME ADIMI. Yukaridaki listeyi onaylamiyorsaniz Ctrl+C.
echo  Hedef: origin/ip-01-02-altyapi
echo ============================================================
pause
git push origin ip-01-02-altyapi || goto :hata

echo.
echo BITTI. Sirada:
echo   - CI'in ilk yesil kosumu:  https://github.com/Arvas65/sorbi/actions
echo   - ADR-5 Ship karari:       docs\is-hatti\v3\ADR\ADR-5-api-modu.md
goto :son

:dogrulama_kirmizi
echo.
echo ============================================================
echo  DOGRULAMA KIRMIZI - hicbir sey commit edilmedi.
echo  Once yukaridaki hatayi giderin, sonra bu betigi tekrar kosun.
echo ============================================================
pause
exit /b 1

:hata
echo.
echo HATA: bir commit adimi basarisiz oldu. Hicbir sey ITILMEDI;
echo yapilmis commit'ler yerinde duruyor. Sorunu giderip betigi
echo tekrar kosabilirsiniz - biten adimlar "commit edilecek bir sey
echo yok" deyip gececek.
pause
exit /b 1

:son
echo.
pause
endlocal
