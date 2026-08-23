# Gece görev kuyruğu

Buraya konan her `.bat` dosyası, gece koşumunun sonunda **bir kez** çalışır ve
`bitti/` altına taşınır. Amaç: İhsan'dan bir şey çalıştırmasını istemek yerine,
işi gecenin sırasına bırakmak.

Kullanımı bilinçli olarak dar: tek seferlik deneyler ve ölçümler. Kalıcı hale
gelmesi gereken bir şey varsa `gece-kosum.bat`'a yazılır, buraya değil.

Her görev kendi çıktısını `docs/kanit/` altına yazmalıdır; buradan dönen tek
şey çıkış kodudur.
