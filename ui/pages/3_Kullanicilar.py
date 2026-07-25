"""SorBI — Kullanıcı yönetimi (yalnızca yönetici)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

from app import auth
from ui.ortak import giris_kapisi

st.set_page_config(page_title="SorBI — Kullanıcılar", page_icon="👥", layout="wide")
giris_kapisi(gereken_rol="yonetici")
st.title("👥 Kullanıcı Yönetimi")

col_liste, col_yeni = st.columns(2)

with col_liste:
    st.subheader("Mevcut kullanıcılar")
    for ad, k in auth.kullanicilar().items():
        with st.expander(f"{ad} · {k['rol']}"):
            yeni = st.text_input("Yeni şifre", type="password", key=f"yeni_{ad}")
            c1, c2 = st.columns(2)
            if c1.button("Şifreyi değiştir", key=f"sd_{ad}"):
                try:
                    auth.sifre_degistir(ad, yeni)
                    st.success("Şifre değiştirildi.")
                except ValueError as e:
                    st.error(str(e))
            if c2.button("Sil", key=f"sil_{ad}"):
                try:
                    auth.kullanici_sil(ad)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

with col_yeni:
    st.subheader("Yeni kullanıcı")
    with st.form("yeni_kullanici", clear_on_submit=True):
        ad = st.text_input("Kullanıcı adı")
        sifre = st.text_input(f"Şifre (en az {auth.MIN_SIFRE} karakter)", type="password")
        rol = st.selectbox("Rol", auth.ROLLER,
                           format_func=lambda r: {"yonetici": "Yönetici (her şey + kullanıcı yönetimi)",
                                                  "analist": "Analist (kullanıcı yönetimi hariç)"}[r])
        if st.form_submit_button("Ekle", type="primary"):
            try:
                auth.kullanici_ekle(ad, sifre, rol)
                st.success(f"{ad} eklendi.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
