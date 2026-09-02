"""Gece koşumunun kanıtını, çalışılan daldan BAĞIMSIZ olarak uzak dala iter.

Neden gerekli — 2026-09-02'de bulundu (BULGU-24):

`gece-kosum.bat` şunu yapıyordu:

    git add docs/kanit docs/is-hatti/GUNLUK.md
    git commit -m "olcum: gece kosumu ..."
    git push origin HEAD:refs/heads/olcum-otomatik

Üç varsayım vardı ve üçü de yazıldığı gün doğruydu:

1. HEAD ölçüm dalıdır,
2. çalışma ağacında ölçümden başka bir iş yoktur,
3. HEAD'in itilmesi yalnız kanıtı taşır.

2026-08-29 akşamı İhsan `ip-46-cekirdek` dalını açtı (v4 çekirdeği,
68 dosya / 10.296 satır). O dal `olcum-otomatik`'in ucunun torunudur.
Üç varsayım da aynı anda düştü: kanıt commit'i onun özellik dalına
atılacak, `HEAD:refs/heads/olcum-otomatik` push'u **hızlı-ileri sarma
olarak başarılı olacak** ve yarım kalmış v4 çalışmasının tamamını
ölçüm dalına taşıyacaktı. Push reddedilmez — sessizce doğru çalışır ve
yanlış şeyi yapar.

Buradaki çözüm, dalı kontrol etmek DEĞİL. Dal kontrolü yine bir varsayım
olurdu ("beklediğim dal listesi doğrudur"). Bunun yerine kanıt commit'i
çalışma ağacının dalıyla hiç ilişkilendirilmez:

- ayrı bir indeks dosyası kullanılır (`GIT_INDEX_FILE`) — İhsan'ın
  hazırladığı indekse dokunulmaz,
- ağaç `origin/<dal>`'ın tepesinden okunur, HEAD'den değil,
- commit `commit-tree` ile doğrudan o tepeye çocuk yazılır,
- push edilen şey commit'in kendisidir, HEAD değil.

Sonuç: HEAD nerede olursa olsun itilen şey yalnızca kanıttır ve push
her zaman hızlı-ileri sarmadır. Çalışma ağacı, indeks ve HEAD okunmaz
bile.

Silme işlenmez (`git add <dizin>`, `-A` değil): kanıt ekle-only'dir,
yereldeki bir eksik uzaktakini düşüremez.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

VARSAYILAN_DAL = "olcum-otomatik"
VARSAYILAN_YOLLAR = ("docs/kanit", "docs/is-hatti/GUNLUK.md")
GECICI_INDEKS = "kanit-index"


class GitYok(RuntimeError):
    """git çalıştırılamıyor ya da burası bir depo değil."""


@dataclass(frozen=True)
class Sonuc:
    """Ne olduğu. `durum` makine okunur, `aciklama` insan okunur."""

    durum: str          # islendi | yeni_kanit_yok | push_dustu | git_yok | uzak_yok
    aciklama: str
    commit: str | None = None

    @property
    def basarili(self) -> bool:
        return self.durum in ("islendi", "yeni_kanit_yok")

    def ozet(self) -> str:
        """Tek satırlık makine okunur özet — log'a bu yazılır."""
        p = f" commit={self.commit}" if self.commit else ""
        return f"KANIT_IT durum={self.durum}{p}"


def _git(depo: Path, *arg: str, indeks: Path | None = None) -> subprocess.CompletedProcess:
    ortam = dict(os.environ)
    if indeks is not None:
        ortam["GIT_INDEX_FILE"] = str(indeks)
    # Kimlik: depo yapılandırmasına bağlı kalmasın diye commit-tree'ye
    # ortamdan verilir; İhsan'ın kendi kimliğiyle karışmaz.
    ortam.setdefault("GIT_AUTHOR_NAME", "SorBI gece kosumu")
    ortam.setdefault("GIT_AUTHOR_EMAIL", "gece@sorbi.local")
    ortam.setdefault("GIT_COMMITTER_NAME", "SorBI gece kosumu")
    ortam.setdefault("GIT_COMMITTER_EMAIL", "gece@sorbi.local")
    # S603/S607: kabuk yok, argümanlar liste olarak veriliyor ve hepsi bu
    # modülün kendi sabitleri ya da çağıranın verdiği dal/mesaj. "git" PATH'ten
    # çözülür; tam yolu sabitlemek Windows/Linux arasında taşınmaz olurdu.
    return subprocess.run(  # noqa: S603
        ["git", *arg],  # noqa: S607
        cwd=str(depo),
        env=ortam,
        capture_output=True,
        text=True,
        errors="replace",
    )


def _zorunlu(depo: Path, *arg: str, indeks: Path | None = None) -> str:
    p = _git(depo, *arg, indeks=indeks)
    if p.returncode != 0:
        raise GitYok(f"git {' '.join(arg)} -> {p.returncode}: {p.stderr.strip()}")
    return p.stdout.strip()


def depo_mu(depo: Path) -> bool:
    p = _git(depo, "rev-parse", "--is-inside-work-tree")
    return p.returncode == 0 and p.stdout.strip() == "true"


def uzak_tepe(depo: Path, uzak: str, dal: str) -> str | None:
    """`uzak/dal`'ın güncel tepesi. Yoksa None (dal henüz yaratılmamış)."""
    _git(depo, "fetch", uzak, dal)          # başarısızsa yerel kopyayla devam
    for ref in (f"refs/remotes/{uzak}/{dal}", "FETCH_HEAD"):
        p = _git(depo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout.strip()
    return None


def kanit_it(
    depo: Path,
    yollar=VARSAYILAN_YOLLAR,
    uzak: str = "origin",
    dal: str = VARSAYILAN_DAL,
    mesaj: str = "olcum: gece kosumu (otomatik)",
    it: bool = True,
) -> Sonuc:
    """Kanıtı `uzak/dal`'a iter. HEAD, indeks ve çalışma ağacı DEĞİŞMEZ."""
    depo = Path(depo)
    if not depo_mu(depo):
        return Sonuc("git_yok", "burasi bir git deposu degil")

    p = _git(depo, "remote", "get-url", uzak)
    if p.returncode != 0:
        return Sonuc("uzak_yok", f"uzak depo tanimli degil: {uzak}")

    taban = uzak_tepe(depo, uzak, dal)

    indeks = Path(_zorunlu(depo, "rev-parse", "--git-dir"))
    if not indeks.is_absolute():
        indeks = depo / indeks
    indeks = indeks / GECICI_INDEKS
    indeks.unlink(missing_ok=True)

    try:
        if taban:
            _zorunlu(depo, "read-tree", taban, indeks=indeks)
        else:
            _zorunlu(depo, "read-tree", "--empty", indeks=indeks)

        var_olan = [y for y in yollar if (depo / y).exists()]
        if var_olan:
            # --ignore-removal ŞART: git 2.0'dan beri `git add <dizin>`
            # SİLMEYİ de işler. Taban uzak daldan okunduğu için, yerelde
            # olmayan her eski kanıt "silinmiş" görünür ve uzaktan
            # düşerdi. Kanıt ekle-only'dir (CLAUDE.md § 3.5).
            _zorunlu(depo, "add", "--ignore-removal", "--", *var_olan, indeks=indeks)

        agac = _zorunlu(depo, "write-tree", indeks=indeks)

        if taban:
            taban_agac = _zorunlu(depo, "rev-parse", f"{taban}^{{tree}}")
            if agac == taban_agac:
                return Sonuc("yeni_kanit_yok", "uzak daldakiyle ayni agac")

        arg = ["commit-tree", agac, "-m", mesaj]
        if taban:
            arg[2:2] = ["-p", taban]
        commit = _zorunlu(depo, *arg)

        if not it:
            return Sonuc("islendi", "kuru kosum - itilmedi", commit)

        p = _git(depo, "push", uzak, f"{commit}:refs/heads/{dal}")
        if p.returncode != 0:
            return Sonuc("push_dustu", (p.stderr or p.stdout).strip()[:400], commit)
        return Sonuc("islendi", f"{uzak}/{dal} guncellendi", commit)
    except GitYok as e:
        return Sonuc("git_yok", str(e))
    finally:
        indeks.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description="Gece kanitini uzak dala iter (daldan bagimsiz).")
    a.add_argument("--depo", default=".")
    a.add_argument("--dal", default=VARSAYILAN_DAL)
    a.add_argument("--uzak", default="origin")
    a.add_argument("--mesaj", default="olcum: gece kosumu (otomatik)")
    a.add_argument("--kuru", action="store_true", help="commit'i yaz ama itme")
    n = a.parse_args(argv)

    s = kanit_it(Path(n.depo), dal=n.dal, uzak=n.uzak, mesaj=n.mesaj, it=not n.kuru)
    print(s.ozet())
    print(s.aciklama)
    # Kanıt her hâlükârda diskte duruyor; çıkış kodu gece koşumunu
    # kırmızıya çevirmesin diye yalnız gerçek push düşüşünde 1.
    return 0 if s.basarili else 1


if __name__ == "__main__":
    sys.exit(main())
