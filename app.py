import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import re
import sqlite3

def load_and_clean_base_data():
    conn = sqlite3.connect('usgs.sqlite')
    query = """
    SELECT 
        e.id AS eventID, 
        e.place AS location, 
        e.mag AS magnitude, 
        e.depth, 
        e.time AS datetime,
        e.latitude,
        e.longitude,
        g.landslide_hazard_alert_value,
        g.liquefaction_hazard_alert_value
    FROM event e
    LEFT JOIN ground_failure g ON e.event_uuid = g.event_uuid
    """
    df_gempa = pd.read_sql_query(query, conn)
    conn.close()
        
    df_gempa['magnitude'] = pd.to_numeric(df_gempa['magnitude'], errors='coerce')
    df_gempa['depth'] = pd.to_numeric(df_gempa['depth'], errors='coerce')
    df_gempa['landslide_hazard_alert_value'] = pd.to_numeric(df_gempa['landslide_hazard_alert_value'], errors='coerce').fillna(0)
    df_gempa['liquefaction_hazard_alert_value'] = pd.to_numeric(df_gempa['liquefaction_hazard_alert_value'], errors='coerce').fillna(0)
    df_gempa = df_gempa.dropna(subset=['magnitude', 'depth', 'location', 'datetime'])
    
    try:
        df_gempa['datetime'] = pd.to_datetime(df_gempa['datetime'], unit='ms').dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        try:
            df_gempa['datetime'] = pd.to_datetime(df_gempa['datetime']).dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass
            
    try:
        df_sensor = pd.read_csv('katalog_sensor.tsv', sep='\t', low_memory=False)
        df_sensor = df_sensor.dropna(subset=['location'])
    except Exception:
        df_sensor = pd.DataFrame(columns=['code', 'location'])
        
    return df_gempa, df_sensor

def kelompokkan_pulau(loc):
    loc_lower = str(loc).lower()
    if 'sumatra' in loc_lower or 'sumatera' in loc_lower:
        return 'Wilayah Sumatra'
    elif 'java' in loc_lower or 'jawa' in loc_lower:
        return 'Wilayah Jawa'
    elif 'sulawesi' in loc_lower or 'celebes' in loc_lower:
        return 'Wilayah Sulawesi'
    elif 'nusa tenggara' in loc_lower or 'bali' in loc_lower or 'lombok' in loc_lower or 'ntt' in loc_lower or 'ntb' in loc_lower:
        return 'Wilayah Nusa Tenggara & Bali'
    elif 'molucca' in loc_lower or 'seram' in loc_lower or 'banda sea' in loc_lower or 'papua' in loc_lower or 'new guinea' in loc_lower or 'maluku' in loc_lower:
        return 'Wilayah Maluku & Papua'
    elif 'kalimantan' in loc_lower or 'borneo' in loc_lower:
        return 'Wilayah Kalimantan'
    else:
        return 'Luar Wilayah / Laut Lepas'

def ekstrak_nama_daerah(loc):
    loc_str = str(loc)
    cleaned = re.sub(r'\d+\s*km\s*(?:[NnSsEeWw]{1,3}|[BbTtLlaaroutd\s]*)\s*(?:of|dari)?', '', loc_str)
    cleaned = re.sub(r'(?i)\b(south|north|east|west|central|sea|strait|ocean|offshore|coast|of|indonesia|station|type|ex|cea|libra)\b', '', cleaned)
    cleaned = re.sub(r'(?i)\b(barat|timur|utara|selatan|daya|laut|tenggara|selat|pantai|luar|dalam|daerah|kota|kabupaten)\b', '', cleaned)
    cleaned = re.sub(r'[,\-()]+', ' ', cleaned)
    words = cleaned.split()
    if len(words) >= 1:
        nama = " ".join(words[:2]).strip().title()
        if len(nama) > 2:
            return nama
    return "Laut Lepas / Tidak Teridentifikasi"

def proses_level_pulau(df_gempa, df_sensor):
    df_g = df_gempa.copy()
    df_g['Alternatif'] = df_g['location'].apply(kelompokkan_pulau)
    df_g_filter = df_g[df_g['Alternatif'] != 'Luar Wilayah / Laut Lepas'].copy()
    
    tabel_kriteria = df_g_filter.groupby('Alternatif').agg(
        C1_Frekuensi=('eventID', 'count'),
        C2_Avg_Magnitudo=('magnitude', 'mean'),
        C3_Avg_Kedalaman=('depth', 'mean'),
        C4_Risiko_Longsor=('landslide_hazard_alert_value', 'mean'),
        C5_Risiko_Likuifaksi=('liquefaction_hazard_alert_value', 'mean')
    ).reset_index()
    
    df_s = df_sensor.copy()
    df_s['Alternatif'] = df_s['location'].apply(kelompokkan_pulau)
    df_s_counts = df_s[df_s['Alternatif'] != 'Luar Wilayah / Laut Lepas'].groupby('Alternatif').size().reset_index(name='C6_Jumlah_Sensor')
    
    tabel_final = pd.merge(tabel_kriteria, df_s_counts, on='Alternatif', how='left').fillna(0)
    return tabel_final, df_g_filter

def proses_level_daerah(df_gempa, df_sensor):
    df_g = df_gempa.copy()
    df_g['Alternatif'] = df_g['location'].apply(ekstrak_nama_daerah)
    df_g_filter = df_g[df_g['Alternatif'] != "Laut Lepas / Tidak Teridentifikasi"].copy()
    
    top_daerah = df_g_filter['Alternatif'].value_counts().head(15).index.tolist()
    df_g_top = df_g_filter[df_g_filter['Alternatif'].isin(top_daerah)].copy()

    tabel_kriteria = df_g_top.groupby('Alternatif').agg(
        C1_Frekuensi=('eventID', 'count'),
        C2_Avg_Magnitudo=('magnitude', 'mean'),
        C3_Avg_Kedalaman=('depth', 'mean'),
        C4_Risiko_Longsor=('landslide_hazard_alert_value', 'mean'),
        C5_Risiko_Likuifaksi=('liquefaction_hazard_alert_value', 'mean')
    ).reset_index()
    
    df_s = df_sensor.copy()
    df_s['Alternatif'] = df_s['location'].apply(ekstrak_nama_daerah)
    df_s_counts = df_s[df_s['Alternatif'].isin(top_daerah)].groupby('Alternatif').size().reset_index(name='C6_Jumlah_Sensor')
    
    tabel_final = pd.merge(tabel_kriteria, df_s_counts, on='Alternatif', how='left').fillna(0)
    return tabel_final, df_g_top

def hitung_weighted_product(df_kriteria, bobot_awal):
    total_bobot = sum(bobot_awal)
    w = [b / total_bobot for b in bobot_awal]
    
    w_perbaikan = [w[0], w[1], -w[2], w[3], w[4], -w[5]]
    
    vektor_s = []
    for index, row in df_kriteria.iterrows():
        val_c4 = row['C4_Risiko_Longsor'] if row['C4_Risiko_Longsor'] > 0 else 0.0001
        val_c5 = row['C5_Risiko_Likuifaksi'] if row['C5_Risiko_Likuifaksi'] > 0 else 0.0001
        val_c6 = row['C6_Jumlah_Sensor'] if row['C6_Jumlah_Sensor'] > 0 else 0.0001
        
        s_i = (
            (row['C1_Frekuensi'] ** w_perbaikan[0]) *
            (row['C2_Avg_Magnitudo'] ** w_perbaikan[1]) *
            (row['C3_Avg_Kedalaman'] ** w_perbaikan[2]) *
            (val_c4 ** w_perbaikan[3]) *
            (val_c5 ** w_perbaikan[4]) *
            (val_c6 ** w_perbaikan[5])
        )
        vektor_s.append(s_i)
        
    df_kriteria['Vektor_S'] = vektor_s
    total_s = sum(vektor_s)
    df_kriteria['Vektor_V'] = df_kriteria['Vektor_S'] / total_s
    df_hasil = df_kriteria.sort_values(by='Vektor_V', ascending=False).reset_index(drop=True)
    return df_hasil

def main():
    st.set_page_config(page_title="SPK Mitigasi Gempa Komprehensif", layout="wide")
    
    st.title("Sistem Pendukung Keputusan Mitigasi Bencana Gempa Bumi")
    st.subheader("Optimasi Alokasi Anggaran Pemantauan Seismik Berbasis Metode Weighted Product (WP)")
    st.markdown("---")
    
    with st.spinner("Sinkronisasi basis data relasional dan spasial sensor..."):
        df_gempa, df_sensor = load_and_clean_base_data()
        
    tab1, tab2 = st.tabs(["Perhitungan SPK 6 Kriteria", "Visualisasi Log Historis & Distribusi Sensor"])
    
    with tab1:
        st.markdown("### Pengaturan Cakupan Wilayah Analisis")
        level_analisis = st.selectbox(
            "Pilih Tingkat Deteksi Wilayah Yang Ingin Dianalisis:",
            ["Tingkat Makro (Per Pulau/Wilayah Besar)", "Tingkat Mikro (Per Kota/Daerah Spesifik Kritis)"]
        )
        
        st.markdown("---")
        
        if level_analisis == "Tingkat Makro (Per Pulau/Wilayah Besar)":
            tabel_kriteria, _ = proses_level_pulau(df_gempa, df_sensor)
            label_jenis = "Pulau/Wilayah"
        else:
            tabel_kriteria, _ = proses_level_daerah(df_gempa, df_sensor)
            label_jenis = "Kota/Daerah"
            
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"#### Matriks Kriteria Keputusan 6 Dimensi Hibrida ({label_jenis})")
            st.dataframe(tabel_kriteria, use_container_width=True)
            st.info("**Aturan Sifat Kriteria:** C1 (Frekuensi), C2 (Magnitudo), C4 (Risiko Longsor), dan C5 (Risiko Likuifaksi) bertindak sebagai **Benefit**. Sedangkan C3 (Avg Kedalaman) dan C6 (Jumlah Sensor Eksisting) bertindak sebagai **Cost**.")
            
        with col2:
            st.markdown("#### Pembobotan Parameter Mitigasi & Pengawasan")
            st.write("Sesuaikan prioritas instansi (Skala 1 - 5):")
            b1 = st.slider("Bobot C1 - Frekuensi Kejadian Gempa", 1, 5, 5)
            b2 = st.slider("Bobot C2 - Rata-rata Kekuatan (Magnitudo)", 1, 5, 4)
            b3 = st.slider("Bobot C3 - Rata-rata Kedalaman Sesar", 1, 5, 4)
            b4 = st.slider("Bobot C4 - Potensi Dampak Tanah Longsor", 1, 5, 3)
            b5 = st.slider("Bobot C5 - Potensi Dampak Likuifaksi", 1, 5, 3)
            b6 = st.slider("Bobot C6 - Urgensi Kelangkaan Jaringan Sensor", 1, 5, 4)
            
            bobot_user = [b1, b2, b3, b4, b5, b6]
            
            st.markdown("---")
            hitung_tombol = st.button(f"Hitung Prioritas Anggaran Kombinasi", type="primary", use_container_width=True)
            
        if hitung_tombol:
            st.markdown("---")
            st.markdown(f"#### Rekomendasi Alokasi Anggaran Strategis - {label_jenis}")
            
            hasil_wp = hitung_weighted_product(tabel_kriteria.copy(), bobot_user)
            
            st.dataframe(
                hasil_wp[['Alternatif', 'C1_Frekuensi', 'C2_Avg_Magnitudo', 'C3_Avg_Kedalaman', 'C4_Risiko_Longsor', 'C5_Risiko_Likuifaksi', 'C6_Jumlah_Sensor', 'Vektor_V']], 
                use_container_width=True
            )
            
            fig_wp = px.bar(
                hasil_wp, x='Vektor_V', y='Alternatif', orientation='h',
                title=f'Grafik Preferensi Kelayakan Anggaran Penguatan Mitigasi (Vektor V) - {label_jenis}',
                labels={'Vektor_V': 'Nilai Preferensi Akhir (Vektor V)', 'Alternatif': label_jenis},
                text_auto='.4f', color='Vektor_V', color_continuous_scale='Reds'
            )
            fig_wp.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False)
            st.plotly_chart(fig_wp, use_container_width=True)
            
            alternatif_utama = hasil_wp.iloc[0]['Alternatif']
            nilai_tertinggi = hasil_wp.iloc[0]['Vektor_V']
            st.success(f"**Rekomendasi Kebijakan Konkrit:** Wilayah **{alternatif_utama}** divalidasi secara matematis menempati **Peringkat Prioritas Utama** dengan preferensi tertinggi sebesar **{nilai_tertinggi:.4f}**, dipicu oleh kombinasi aktivitas seismik ekstrem dan keterbatasan stasiun pemantauan.")

    with tab2:
        st.markdown("### Log Aktivitas & Pemetaan Geospatial Seismik Indonesia")
        
        _, df_pulau_all = proses_level_pulau(df_gempa, df_sensor)
        list_pulau = ["Semua Wilayah Indonesia"] + sorted(df_pulau_all['Alternatif'].unique().tolist())
        pulau_terpilih = st.selectbox("Pilih Wilayah/Pulau untuk Ditampilkan:", list_pulau)
        
        if pulau_terpilih == "Semua Wilayah Indonesia":
            df_filtered_historis = df_pulau_all.copy()
            df_filtered_sensor = df_sensor.copy()
        else:
            df_filtered_historis = df_pulau_all[df_pulau_all['Alternatif'] == pulau_terpilih].copy()
            df_sensor_copy = df_sensor.copy()
            df_sensor_copy['Alternatif'] = df_sensor_copy['location'].apply(kelompokkan_pulau)
            df_filtered_sensor = df_sensor_copy[df_sensor_copy['Alternatif'] == pulau_terpilih].copy()
            
        st.markdown("---")
        
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Total Gempa Terekam ({pulau_terpilih})", f"{len(df_filtered_historis):,} Kejadian")
        m2.metric("Rata-rata Kekuatan Gempa", f"{df_filtered_historis['magnitude'].mean():.2f} SR")
        m3.metric("Stasiun Sensor Terpasang", f"{len(df_filtered_sensor):,} Unit Sensor")
        
        st.markdown("---")
        
        st.markdown(f"#### Peta Sebaran Titik Gempa Bumi - {pulau_terpilih}")
        st.write("Ukuran titik mencerminkan Kekuatan Gempa (SR), sedangkan gradasi warna menunjukkan Kedalaman Pusat Gempa (Km):")
        
        df_map_sample = df_filtered_historis.sample(n=min(1500, len(df_filtered_historis)), random_state=42)
        
        fig_map = px.scatter_geo(
            df_map_sample,
            lat='latitude',
            lon='longitude',
            color='depth',
            size='magnitude',
            hover_name='location',
            hover_data={'magnitude': True, 'depth': True, 'datetime': True, 'latitude': False, 'longitude': False},
            title=f'Peta Sebaran Titik Episenter Gempa ({pulau_terpilih})',
            color_continuous_scale='Reds_r',
            labels={'depth': 'Kedalaman (Km)', 'magnitude': 'Magnitudo (SR)'},
            projection="mercator"
        )
        
        fig_map.update_geos(
            fitbounds="locations",
            visible=True,
            showcountries=True,
            countrycolor="#cbd5e1",
            showland=True,
            landcolor="#f1f5f9",
            showocean=True,
            oceancolor="#e0f2fe",
            showlakes=True,
            lakecolor="#e0f2fe"
        )
        fig_map.update_layout(height=550, margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)
        
        st.markdown("---")
        
        col_graph1, col_graph2 = st.columns([3, 2])
        
        with col_graph1:
            st.markdown(f"#### Log Detail Kejadian Gempa Aktual - {pulau_terpilih}")
            st.dataframe(
                df_filtered_historis[['datetime', 'Alternatif', 'location', 'magnitude', 'depth', 'landslide_hazard_alert_value', 'liquefaction_hazard_alert_value']].sort_values(by='datetime', ascending=False), 
                use_container_width=True,
                height=380
            )
            
        with col_graph2:
            st.markdown(f"#### Distribusi Kekuatan Gempa (SR)")
            fig_hist = px.histogram(
                df_filtered_historis, x='magnitude', nbins=20,
                title=f'Histogram Magnitudo Gempa di {pulau_terpilih}',
                labels={'magnitude': 'Kekuatan Gempa (SR)', 'count': 'Frekuensi Kejadian'},
                color_discrete_sequence=['#dc2626']
            )
            fig_hist.update_layout(bargap=0.1, plot_bgcolor='rgba(0,0,0,0)', height=380)
            st.plotly_chart(fig_hist, use_container_width=True)

if __name__ == '__main__':
    main()