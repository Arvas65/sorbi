"""SorBI — Bağlantı Yöneticisi (v2: kullanıcı veritabanını arayüzden seçer).

Şifreler diske yazılmaz; yalnız bu oturumun belleğinde tutulur (KVKK/G-14 uyumu).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

from app import config, connections

st.set_page_config(page_title="SorBI — Bağlantı", page_icon="🔌", layout="wide")
st.title("🔌 Veritabanı Bağlantısı")

# Aktif bağlantı durumu
aktif = st.session_state.get("aktif_baglanti_adi", "demo (hospital.db)")
st.info(f"**Aktif bağlantı:** {aktif} · lehçe: `{config.TARGET_DIALECT}`")

TIP_ETIKET = {"sqlite": "SQLite dosyası", "postgres": "PostgreSQL",
              "mysql": "MySQL / MariaDB", "mssql": "SQL Server (MSSQL)"}

col_yeni, col_kayitli = st.columns(2)

# ---------------- Yeni bağlantı ----------------
with col_yeni:
    st.subheader("Yeni bağlantı")
    tip = st.selectbox("Veritabanı tipi", list(TIP_ETIKET), format_func=TIP_ETIKET.get)

    bilgiler = {"tip": tip}
    if tip == "sqlite":
        bilgiler["dosya"] = st.text_input("Dosya yolu", placeholder="C:\\veri\\ornek.db")
    else:
        c1, c2 = st.columns([3, 1])
        bilgiler["host"] = c1.text_input("Sunucu", placeholder="localhost")
        bilgiler["port"] = c2.number_input("Port", value=connections.DESTEKLENEN[tip]["port"])
        bilgiler["veritabani"] = st.text_input("Veritabanı adı")
        c3, c4 = st.columns(2)
        bilgiler["kullanici"] = c3.text_input("Kullanıcı")
        bilgiler["sifre"] = c4.text_input("Şifre", type="password",
                                          help="Diske yazılmaz; yalnız bu oturumda tutulur.")
        st.warning("G-14: Bu hesabın **salt-okunur** yetkili olması kurulum önkoşuludur. "
                   "SorBI yazma sorgularını sözdizimde reddeder ama ikinci savunma hattı "
                   "veritabanı yetkisidir.")

    profil_adi = st.text_input("Profil adı (kaydetmek için)", placeholder="ör. uretim-postgres")

    b1, b2 = st.columns(2)
    if b1.button("Bağlantıyı test et", type="secondary"):
        url = connections.build_url(**bilgiler)
        st.session_state["test_sonuc"] = connections.test_connection(url)
    if (r := st.session_state.get("test_sonuc")):
        (st.success if r["ok"] else st.error)(r["mesaj"])
        if r["tablolar"]:
            st.caption("Tablolar: " + ", ".join(r["tablolar"][:15])
                       + (" ..." if len(r["tablolar"]) > 15 else ""))

    if b2.button("Bağlan ve kullan", type="primary"):
        url = connections.build_url(**bilgiler)
        r = connections.test_connection(url)
        if not r["ok"]:
            st.error(r["mesaj"])
        else:
            with st.spinner("Şema keşfediliyor, RAG indeksi kuruluyor..."):
                connections.aktifle(url, connections.DESTEKLENEN[tip]["lehce"])
            ad = profil_adi or f"{TIP_ETIKET[tip]}"
            st.session_state["aktif_baglanti_adi"] = ad
            if profil_adi:
                connections.profil_kaydet(profil_adi, bilgiler)
            st.success(f"Bağlandı: {ad} — {r['mesaj']} SOR sayfası artık bu veritabanını kullanıyor.")
            st.rerun()

# ---------------- Kayıtlı profiller ----------------
with col_kayitli:
    st.subheader("Kayıtlı profiller")
    profiller = connections.profilleri_yukle()
    if not profiller:
        st.caption("Henüz kayıtlı profil yok. Soldan bir bağlantı kurup profil adı vererek kaydedin.")
    for ad, b in profiller.items():
        with st.expander(f"{ad}  ·  {TIP_ETIKET.get(b.get('tip'), b.get('tip'))}"):
            st.json({k: v for k, v in b.items() if k != "tip"})
            if b.get("tip") != "sqlite":
                b = dict(b)
                b["sifre"] = st.text_input("Şifre", type="password", key=f"pw_{ad}",
                                           help="Profillerde şifre saklanmaz; her bağlanışta girilir.")
            p1, p2 = st.columns(2)
            if p1.button("Bağlan", key=f"bag_{ad}", type="primary"):
                url = connections.build_url(**b)
                r = connections.test_connection(url)
                if not r["ok"]:
                    st.error(r["mesaj"])
                else:
                    with st.spinner("Şema keşfediliyor..."):
                        connections.aktifle(url, connections.DESTEKLENEN[b["tip"]]["lehce"])
                    st.session_state["aktif_baglanti_adi"] = ad
                    st.rerun()
            if p2.button("Sil", key=f"sil_{ad}"):
                connections.profil_sil(ad)
                st.rerun()

    st.divider()
    if st.button("Demo veritabanına dön (hospital.db)"):
        demo_url = f"sqlite:///{os.path.join(config.HERE, 'demo', 'hospital.db')}"
        connections.aktifle(demo_url, "sqlite")
        st.session_state["aktif_baglanti_adi"] = "demo (hospital.db)"
        st.rerun()
