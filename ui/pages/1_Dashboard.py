"""SorBI — BI Dashboard (v2 kapsamı).

Ekrandaki her sayı SQL'den gelir; 'SQL göster' ile şeffaftır (G-02 ilkesinin
dashboard'a taşınmış hâli). Filtreler sorguya parametre olarak iner.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import streamlit as st
from sqlalchemy import bindparam, create_engine, text

from app import config
from ui.ortak import giris_kapisi

st.set_page_config(page_title="SorBI — Dashboard", page_icon="📊", layout="wide")
giris_kapisi()
st.title("📊 Hizmet Analizi Dashboard")
st.caption("Demo hastane verisi — tüm göstergeler filtrelere göre canlı hesaplanır")


@st.cache_resource
def get_engine():
    return create_engine(config.DB_URL)


@st.cache_data(ttl=300)
def q(sql: str, params: dict = None) -> pd.DataFrame:
    params = params or {}
    stmt = text(sql)
    liste_paramlar = [bindparam(ad, expanding=True)
                      for ad, deger in params.items()
                      if isinstance(deger, (list, tuple))]
    if liste_paramlar:
        stmt = stmt.bindparams(*liste_paramlar)
    with get_engine().connect() as c:
        rs = c.execute(stmt, params)
        return pd.DataFrame(rs.fetchall(), columns=list(rs.keys()))


# ---------------- Filtre şeridi (ekran görüntüsündeki üst bar) ----------------
bolumler = q("SELECT ad FROM bolum ORDER BY ad")["ad"].tolist()
unvanlar = q("SELECT DISTINCT unvan FROM doktor ORDER BY unvan")["unvan"].tolist()
sehirler = q("SELECT DISTINCT sehir FROM hasta ORDER BY sehir")["sehir"].tolist()
tarih_araligi = q("SELECT MIN(tarih) mn, MAX(tarih) mx FROM randevu").iloc[0]

f1, f2, f3, f4, f5 = st.columns([2, 2, 2, 2, 3])
with f1:
    sec_bolum = st.multiselect("Bölüm", bolumler, placeholder="Tümü")
with f2:
    sec_unvan = st.multiselect("Doktor Unvanı", unvanlar, placeholder="Tümü")
with f3:
    sec_sehir = st.multiselect("Hasta Şehri", sehirler, placeholder="Tümü")
with f4:
    sec_odeme = st.multiselect("Ödeme Durumu", ["ODENDI", "BEKLIYOR", "GECIKTI"],
                               placeholder="Tümü")
with f5:
    d1, d2 = st.date_input("Tarih aralığı",
                           (date.fromisoformat(tarih_araligi["mn"]),
                            date.fromisoformat(tarih_araligi["mx"])))

# Filtreler -> WHERE parçaları (parametreli — SQL enjeksiyonu yok)
where, params = ["r.tarih BETWEEN :d1 AND :d2"], {"d1": str(d1), "d2": str(d2)}
if sec_bolum:
    where.append("b.ad IN :bolum");   params["bolum"] = tuple(sec_bolum)
if sec_unvan:
    where.append("d.unvan IN :unvan"); params["unvan"] = tuple(sec_unvan)
if sec_sehir:
    where.append("h.sehir IN :sehir"); params["sehir"] = tuple(sec_sehir)
odeme_where = "AND f.odeme_durumu IN :odeme" if sec_odeme else ""
if sec_odeme:
    params["odeme"] = tuple(sec_odeme)
W = " AND ".join(where)

BASE = f"""
FROM randevu r
JOIN doktor d  ON d.doktor_id = r.doktor_id
JOIN bolum b   ON b.bolum_id  = d.bolum_id
JOIN hasta h   ON h.hasta_id  = r.hasta_id
LEFT JOIN muayene m ON m.randevu_id = r.randevu_id
LEFT JOIN fatura f  ON f.muayene_id = m.muayene_id
WHERE {W}"""

# ---------------- KPI şeridi ----------------
kpi_sql = f"""
SELECT COUNT(DISTINCT r.randevu_id)                              AS randevu,
       COUNT(DISTINCT m.muayene_id)                              AS muayene,
       COALESCE(SUM(CASE WHEN 1=1 {odeme_where} THEN f.tutar END), 0) AS ciro,
       COALESCE(SUM(CASE WHEN f.odeme_durumu = 'GECIKTI' THEN f.tutar END), 0) AS geciken,
       100.0 * SUM(CASE WHEN r.durum = 'IPTAL'   THEN 1 ELSE 0 END) / COUNT(DISTINCT r.randevu_id) AS iptal_pct,
       100.0 * SUM(CASE WHEN r.durum = 'GELMEDI' THEN 1 ELSE 0 END) / COUNT(DISTINCT r.randevu_id) AS gelmedi_pct
{BASE}"""
k = q(kpi_sql, params).iloc[0]

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Randevu", f"{int(k['randevu']):,}".replace(",", "."))
c2.metric("Muayene", f"{int(k['muayene']):,}".replace(",", "."))
c3.metric("Ciro (TL)", f"{k['ciro']:,.0f}".replace(",", "."))
c4.metric("Geciken Tahsilat (TL)", f"{k['geciken']:,.0f}".replace(",", "."))
c5.metric("İptal Oranı", f"%{k['iptal_pct']:.1f}")
c6.metric("Gelmeme Oranı", f"%{k['gelmedi_pct']:.1f}")

st.divider()

# ---------------- Bar grafik: bölüm bazlı hizmet sayısı / ciro ----------------
metrik = st.radio("Gösterge", ["Muayene sayısı", "Ciro (TL)"], horizontal=True)
if metrik == "Muayene sayısı":
    bar_sql = f"SELECT b.ad AS bolum, COUNT(DISTINCT m.muayene_id) AS deger {BASE} GROUP BY b.ad ORDER BY deger DESC"
else:
    bar_sql = f"SELECT b.ad AS bolum, COALESCE(SUM(f.tutar),0) AS deger {BASE} {odeme_where} GROUP BY b.ad ORDER BY deger DESC"
bar = q(bar_sql, params)
st.subheader(f"Bölüm bazlı {metrik.lower()}")
if not bar.empty:
    st.bar_chart(bar.set_index("bolum")["deger"], height=300)
with st.expander("SQL göster"):
    st.code(bar_sql, language="sql")

# ---------------- Isı haritası: bölüm × ay pivot ----------------
st.subheader("Bölüm × Ay — muayene yoğunluğu")
piv_sql = f"""SELECT b.ad AS bolum, strftime('%Y-%m', r.tarih) AS ay,
COUNT(DISTINCT m.muayene_id) AS n {BASE} GROUP BY b.ad, ay"""
piv = q(piv_sql, params)
if not piv.empty:
    tablo = (piv.pivot(index="bolum", columns="ay", values="n")
                .fillna(0).astype(int))
    tablo["Toplam"] = tablo.sum(axis=1)
    tablo = tablo.sort_values("Toplam", ascending=False)

    # Isı haritası rengi (matplotlib'siz): beyaz -> koyu mavi
    deger_kolonlari = [c for c in tablo.columns if c != "Toplam"]
    vmax = float(tablo[deger_kolonlari].values.max()) or 1.0

    def _mavi(v):
        oran = min(float(v) / vmax, 1.0)
        r, g, b = int(255 - 190 * oran), int(255 - 130 * oran), int(255 - 40 * oran)
        metin = "white" if oran > 0.55 else "black"
        return f"background-color: rgb({r},{g},{b}); color: {metin}"

    boyayici = getattr(tablo.style, "map", None) or tablo.style.applymap
    st.dataframe(boyayici(_mavi, subset=deger_kolonlari), width="stretch")
with st.expander("SQL göster"):
    st.code(piv_sql, language="sql")

# ---------------- Doktor tablosu ----------------
st.subheader("Doktor bazlı özet")
dok_sql = f"""SELECT d.unvan || ' ' || d.ad || ' ' || d.soyad AS doktor, b.ad AS bolum,
COUNT(DISTINCT m.muayene_id) AS muayene, COALESCE(SUM(f.tutar),0) AS ciro,
100.0 * SUM(CASE WHEN r.durum='IPTAL' THEN 1 ELSE 0 END) / COUNT(DISTINCT r.randevu_id) AS iptal_pct
{BASE} GROUP BY d.doktor_id ORDER BY muayene DESC"""
dok = q(dok_sql, params)
if not dok.empty:
    dok["ciro"] = dok["ciro"].round(0)
    dok["iptal_pct"] = dok["iptal_pct"].round(1)
    st.dataframe(dok, width="stretch", height=300)

st.divider()

# ---------------- Yönetici Önerisi (LLM + kural tabanlı yedek) ----------------
st.subheader("🧭 Yönetici Önerisi")
st.caption("Filtrelenmiş verideki KPI'lardan üretilir. Yerel model varsa LLM yorumlar; "
           "yoksa kural tabanlı özet gösterilir. Hasta verisi modele gitmez — yalnız toplam sayılar.")


def kural_tabanli_ozet() -> list:
    oneriler = []
    if not bar.empty:
        oneriler.append(f"En yoğun bölüm **{bar.iloc[0]['bolum']}** "
                        f"({int(bar.iloc[0]['deger']):,} {metrik.lower()}). ".replace(",", ".")
                        + "Kapasite planlamasında önceliklendirin.")
        if len(bar) > 1:
            oneriler.append(f"En düşük hacimli bölüm **{bar.iloc[-1]['bolum']}** — "
                            "talep yaratma veya kaynakları yeniden dağıtma değerlendirilebilir.")
    if k["iptal_pct"] > 10:
        oneriler.append(f"İptal oranı **%{k['iptal_pct']:.1f}** — %10 eşiğinin üzerinde. "
                        "SMS hatırlatma / çevrimiçi yeniden planlama önerilir.")
    if k["gelmedi_pct"] > 8:
        oneriler.append(f"Gelmeme oranı **%{k['gelmedi_pct']:.1f}** yüksek. "
                        "Randevu teyit araması pilotu başlatılabilir.")
    if k["ciro"] > 0 and k["geciken"] / max(k["ciro"], 1) > 0.15:
        oneriler.append(f"Geciken tahsilat cironun **%{100*k['geciken']/k['ciro']:.0f}**'i "
                        f"({k['geciken']:,.0f} TL). Tahsilat takibi sıkılaştırılmalı.".replace(",", "."))
    if not dok.empty and dok["iptal_pct"].max() > 15:
        d_max = dok.loc[dok["iptal_pct"].idxmax()]
        oneriler.append(f"{d_max['doktor']} ({d_max['bolum']}) iptal oranı **%{d_max['iptal_pct']}** — "
                        "takvim yoğunluğu incelenmeli.")
    return oneriler or ["Seçili filtrelerde dikkat çeken bir sapma yok."]


col_btn, _ = st.columns([1, 3])
if col_btn.button("Yönetici özeti üret", type="primary"):
    ozet_verisi = {
        "donem": f"{d1} — {d2}",
        "kpi": {kk: (round(float(k[kk]), 1) if isinstance(k[kk], float) else int(k[kk]))
                for kk in ["randevu", "muayene", "ciro", "geciken", "iptal_pct", "gelmedi_pct"]},
        "bolum_dagilimi": bar.head(10).to_dict("records") if not bar.empty else [],
    }
    try:
        from app.generator import _ollama_chat, LlmError
        with st.spinner("Yerel model yorumluyor..."):
            cevap = _ollama_chat([
                {"role": "system", "content":
                 "Sen bir hastane yönetim danışmanısın. Sana verilen KPI özetinden yola çıkarak "
                 "Türkçe, madde işaretli, en fazla 5 maddelik somut bir yönetici önerisi yaz. "
                 "Sayı uydurma; yalnız verilen sayıları kullan."},
                {"role": "user", "content": str(ozet_verisi)}])
        st.markdown(cevap)
        st.caption("🖥️ Yerel model yorumu — veriler makineden çıkmadı.")
    except Exception:
        for o in kural_tabanli_ozet():
            st.markdown(f"- {o}")
        st.caption("⚙️ Kural tabanlı özet (yerel modele ulaşılamadı).")
