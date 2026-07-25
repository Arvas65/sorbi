"""SorBI — soru ekranı (Böl. 10: SQL paneli her zaman görünür, G-02).
Çalıştırma: streamlit run ui/streamlit_app.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from app import audit, config, pipeline

st.set_page_config(page_title="SorBI", page_icon="🩺", layout="wide")

st.title("SorBI")
st.caption("Türkçe sor, SQL'i ve cevabı gör — demo: özel hastane veritabanı")

with st.sidebar:
    st.subheader("Ayarlar")
    mode = st.radio("Model modu", ["local", "api"], index=0,
                    help="local: Ollama (veri makineden çıkmaz — KVKK varsayılanı). "
                         "api: OpenAI-uyumlu servis (kişisel veri maskeli gider).")
    if mode == "api" and not config.API_KEY:
        st.warning("SORBI_API_KEY tanımlı değil; yerel moda düşülecek.")
    st.caption(f"Model: {config.LOCAL_MODEL if mode == 'local' else config.API_MODEL}")
    st.caption(f"Hedef lehçe: {config.TARGET_DIALECT}")
    kullanici = st.text_input("Kullanıcı adı (denetim izi için)", value="demo")

tab_soru, tab_gecmis, tab_sema = st.tabs(["Soru", "Denetim izi", "Şema"])

with tab_soru:
    ornekler = [
        "Geçen ay en çok muayene yapan 5 doktor kim?",
        "Bu yıl bölümlere göre toplam ciro nedir?",
        "Son çeyrekte randevusuna gelmeyen hasta sayısı kaç?",
        "Şu anda yatan hasta sayısı bölümlere göre nedir?",
        "Geciken faturaların toplam tutarı ne kadar?",
    ]
    st.caption("Örnekler: " + " · ".join(ornekler[:3]))

    soru = st.text_input("Sorunuz (Türkçe):", placeholder=ornekler[0])

    with st.expander("Analist modu — elle SQL (kontrollü bypass, denetim izine bayraklı yazılır)"):
        manual_sql = st.text_area("SELECT sorgusu:", height=100,
                                  help="Yalnızca SELECT; aynı doğrulama ve denetimden geçer.")

    if st.button("Sor", type="primary") and (soru or manual_sql):
        ans = None
        with st.spinner("Sorgu üretiliyor..."):
            try:
                ans = pipeline.ask(soru or "(elle SQL)", user=kullanici, mode=mode,
                                   manual_sql=manual_sql.strip() or None)
            except Exception as e:
                st.error(f"⚠️ {e}")
                st.stop()

        # Durum şeridi (Nielsen 1: durum görünür — renk + ikon + metin)
        etiket = {"local": "🖥️ yerel model", "api": "☁️ API (maskeli)", "manual": "⌨️ elle SQL"}
        st.caption(f"Mod: {etiket.get(ans.mode, ans.mode)} · süre: {ans.elapsed_s} sn")

        if ans.resolved_dates:
            st.info("Tarih çözümleme (kural tabanlı, G-07): " + "; ".join(
                f"“{d['ifade']}” → {d['baslangic']} … {d['bitis']}" for d in ans.resolved_dates))

        if ans.status == "DUSUK_GUVEN":
            st.warning(f"🤔 {ans.message}")
            if ans.sql:
                st.code(ans.sql, language="sql")
        elif ans.status == "RED":
            st.error(f"🚫 {ans.message}")
            if ans.sql:
                st.code(ans.sql, language="sql")
        elif ans.status == "HATA":
            st.error(f"⚠️ {ans.message}")
            st.code(ans.sql, language="sql")
        else:
            col_sonuc, col_sql = st.columns([3, 2])
            with col_sql:
                st.subheader("Üretilen SQL")  # G-02: her zaman görünür
                st.code(ans.sql, language="sql")
            with col_sonuc:
                st.subheader(f"Sonuç ({ans.rowcount} satır)")
                df = pd.DataFrame(ans.rows, columns=ans.columns)
                sayisal = [c for c in df.columns[1:]
                           if pd.api.types.is_numeric_dtype(df[c])]
                if len(df.columns) >= 2 and sayisal and 1 < len(df) <= 50:
                    t_tablo, t_grafik = st.tabs(["Tablo", "Grafik"])
                    with t_tablo:
                        st.dataframe(df, width="stretch")
                    with t_grafik:
                        try:
                            st.bar_chart(df.set_index(df.columns[0])[sayisal])
                        except Exception:
                            st.caption("Bu sonuç grafik olarak çizilemedi.")
                else:
                    st.dataframe(df, width="stretch")
                st.download_button("CSV indir",
                                   df.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="sorbi_sonuc.csv", mime="text/csv")

with tab_gecmis:
    st.subheader("Denetim izi (G-17)")
    kayitlar = audit.recent(100)
    if kayitlar:
        st.dataframe(pd.DataFrame(kayitlar, columns=[
            "zaman (UTC)", "kullanıcı", "soru", "durum", "satır", "mod", "süre (sn)"]),
            width="stretch")
    else:
        st.caption("Henüz kayıt yok.")

with tab_sema:
    st.subheader("Veritabanı şeması")
    st.caption("Model bu şemayı görür — soru sorarken tablo/kolon adlarına bakmak isteyebilirsiniz.")
    try:
        from sqlalchemy import create_engine, inspect, text as _text
        _eng = create_engine(config.DB_URL)
        _insp = inspect(_eng)
        for _t in _insp.get_table_names():
            with _eng.connect() as _c:
                _n = _c.execute(_text(f'SELECT COUNT(*) FROM "{_t}"')).scalar()
            with st.expander(f"{_t}  ({_n} satır)"):
                _cols = _insp.get_columns(_t)
                st.table(pd.DataFrame(
                    [{"kolon": c["name"], "tip": str(c["type"])} for c in _cols]))
                with _eng.connect() as _c:
                    _rs = _c.execute(_text(f'SELECT * FROM "{_t}" LIMIT 5'))
                    st.caption("İlk 5 satır:")
                    st.dataframe(pd.DataFrame(_rs.fetchall(), columns=list(_rs.keys())),
                                 width="stretch")
        _eng.dispose()
    except Exception as e:
        st.error(f"Şema okunamadı: {e}")
