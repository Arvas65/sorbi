@echo off
REM ============================================================================
REM  it.bat  --  uc gecedir diskte bekleyen isi commit'lere boler ve iter.
REM  Hazirlayan: bulut oturumu, 2026-08-23. PUSH ADIMI EN SONDA VE ONAY ISTER.
REM
REM  Calistirmadan once: bu dosyayi bir kez okuyun. Her commit'in ne tasidigi
REM  yaninda yaziyor. Begenmediginiz bir adimi silin; sira bozulmaz.
REM ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo === 0) Durum ===
git rev-parse --abbrev-ref HEAD
git status --short | find /c /v "" > "%TEMP%\n.txt"
set /p N=<"%TEMP%\n.txt"
echo Degisen/takipsiz dosya sayisi: %N%
echo.
pause

REM --------------------------------------------------------------------------
REM  1) Satir sonu normalizasyonu.
REM     Depo .bat dosyalarini LF ile sakliyordu, disk CRLF uretiyor; sonuc
REM     656 satirlik SAHTE diff (kur.bat 428, otomatik.bat 228 - ikisinde de
REM     tek bir gercek degisiklik yok). Once kurali koy, sonra normalize et;
REM     boylece gercek degisiklikler bir sonraki commit'te tek basina gorunur.
REM --------------------------------------------------------------------------
echo === 1) .gitattributes + renormalize ===
git add .gitattributes .gitignore
git commit -m "gitattributes: bat CRLF, kaynak LF; gitignore: kimlik deposu ve arac ciktilari" || goto :hata
git add --renormalize .
git commit -m "satir sonlarini .gitattributes'a gore normalize et" || echo (normalize edilecek bir sey yoktu)

REM --------------------------------------------------------------------------
REM  2) Kimlik deposunu takipten cikar. (BULGU-15)
REM     .sorbi/users.json admin salt+hash tasiyor ve 884f8d9'de ITILMIS.
REM     Bu adim yeni kosumlari korur; gecmisteki kopya icin PAROLA DONDURUN.
REM     Dosya diskte kalir, yalnizca git takibinden cikar.
REM --------------------------------------------------------------------------
echo === 2) .sorbi/users.json takipten cikiyor ===
git rm --cached -q .sorbi/users.json .coverage yok-boyle-bir-dosya-yok.db 2>nul
git commit -m "BULGU-15: kimlik deposu ve arac ciktilari takipten cikarildi" || echo (cikarilacak bir sey yoktu)

REM --------------------------------------------------------------------------
REM  3) IP-30 - api modunda baglam maskelemesi.  ADR-5 onkosulu O-1 ve O-2.
REM     generator.mask_context() + tests/test_api_modu.py.
REM     BU COMMIT OLMADAN depodaki api modu gercek veri degerlerini disari
REM     gonderiyor. Uc gecedir acik olan en agir madde.
REM --------------------------------------------------------------------------
echo === 3) IP-30 api gizliligi ===
git add app/generator.py app/config.py app/schema_rag.py tests/test_api_modu.py
git commit -m "IP-30: api modunda baglami maskele - gercek deger disari cikmaz (G-13/G-16)" || goto :hata

REM --------------------------------------------------------------------------
REM  4) IP-31 - kota korumasi + kosum gecmisi.  ADR-5 onkosulu O-3.
REM --------------------------------------------------------------------------
echo === 4) IP-31 kota korumasi ===
git add eval/kosum_gecmisi.py tests/test_kosum_gecmisi.py eval/guven_olcum.py
git commit -m "IP-31: kota korumasi ve kosum gecmisi" || goto :hata

REM --------------------------------------------------------------------------
REM  5) Olcum hatti.  IP-26 (karsilastirilamaz genisletmesi) +
REM     bu geceki BULGU-03/08/09/12/14 duzeltmeleri + 10 yeni test.
REM --------------------------------------------------------------------------
echo === 5) olcum hatti ===
git add eval/evaluate.py eval/tarih_sabitle.py ^
        tests/test_eval_runner.py tests/test_guven_olcum.py ^
        tests/test_ornek_degerler.py tests/test_rapor_durustlugu.py
git commit -m "IP-26 + BULGU-03/08/09/12/14: rapor durustlugu, G-12 kapsami, damgada belirlenim" || goto :hata

REM --------------------------------------------------------------------------
REM  6) Betikler ve belgeler.  BULGU-13 (SON-GECE-KOSUMU git add oncesine).
REM --------------------------------------------------------------------------
echo === 6) betikler + belgeler ===
git add gece-kosum.bat kontrol.bat kur.bat otomatik.bat yedekle.bat ^
        gemini-kur.bat gece-gorev CLAUDE.md ^
        docs/is-hatti/BACKLOG.md docs/is-hatti/GUNLUK.md
git commit -m "BULGU-13: SON-GECE-KOSUMU git add oncesine alindi; gemini kurulumu; gunluk" || goto :hata

REM --------------------------------------------------------------------------
REM  7) Kanit dosyalari. Ekle-only; uzerine yazilmaz.
REM --------------------------------------------------------------------------
echo === 7) kanit ===
git add docs/kanit
git commit -m "olcum: 08-22 ve 08-23 gece kosumlarinin kanit dosyalari" || echo (kanitta degisiklik yoktu)

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
echo BITTI. Bundan sonra:
echo   - ADR-5 onkosullari O-1, O-2, O-3 kapandi.
echo   - .sorbi/users.json GECMISTE duruyor: admin parolasini degistirin.
goto :son

:hata
echo.
echo HATA: bir adim basarisiz oldu. Hicbir sey itilmedi; commit'ler yerinde.
echo Sorunu duzeltip bu betigi tekrar calistirabilirsiniz - yapilmis adimlar
echo "commit edilecek bir sey yok" deyip gececek.
exit /b 1

:son
endlocal
