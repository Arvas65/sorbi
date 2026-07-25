"""Sayfalar arası ortak bileşenler: giriş kapısı + oturum çubuğu."""
import streamlit as st

from app import auth


def giris_kapisi(gereken_rol: str = None) -> str:
    """Her sayfanın başında çağrılır. Girilmemişse giriş formu gösterir ve durur.
    Dönen: oturum açan kullanıcı adı."""
    # İlk kurulum: hiç kullanıcı yoksa yönetici hesabı oluşturt
    if not auth.kullanicilar():
        st.title("SorBI — İlk Kurulum")
        st.info("Henüz kullanıcı yok. Önce bir **yönetici** hesabı oluşturun.")
        with st.form("ilk_kurulum"):
            ad = st.text_input("Kullanıcı adı")
            s1 = st.text_input(f"Şifre (en az {auth.MIN_SIFRE} karakter)", type="password")
            s2 = st.text_input("Şifre (tekrar)", type="password")
            if st.form_submit_button("Yönetici hesabını oluştur", type="primary"):
                if s1 != s2:
                    st.error("Şifreler uyuşmuyor.")
                else:
                    try:
                        auth.kullanici_ekle(ad, s1, "yonetici")
                        st.success("Hesap oluşturuldu — şimdi giriş yapın.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
        st.stop()

    # Giriş
    if "kullanici" not in st.session_state:
        st.title("SorBI — Giriş")
        with st.form("giris"):
            ad = st.text_input("Kullanıcı adı")
            sifre = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş", type="primary"):
                rol = auth.dogrula(ad, sifre)
                if rol:
                    st.session_state["kullanici"] = ad
                    st.session_state["rol"] = rol
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı.")
        st.stop()

    # Oturum çubuğu
    with st.sidebar:
        st.caption(f"👤 **{st.session_state['kullanici']}** · {st.session_state['rol']}")
        if st.button("Çıkış yap"):
            for k in ("kullanici", "rol"):
                st.session_state.pop(k, None)
            st.rerun()

    # Rol kontrolü
    if gereken_rol and st.session_state["rol"] != gereken_rol:
        st.error(f"Bu sayfa yalnızca **{gereken_rol}** rolüne açık.")
        st.stop()

    return st.session_state["kullanici"]
