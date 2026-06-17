import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import json
import pandas as pd
import io

# =========================================================================
# 🔑 PENGATURAN INTERNAL (Ubah Bagian Ini Sebelum Upload/Dijalankan)
# =========================================================================
GEMINI_API_KEY = "AQ.Ab8RN6Ia9d9C_DwEaZeeETi_COLRGARZEunDkG_lgyqERtaFfA" 
APP_PASSWORD = "VIDA123" 
# =========================================================================

# Konfigurasi Awal Halaman Web
st.set_page_config(page_title="AI Advanced Point System", layout="wide")

# 1. GERBANG KEAMANAN (PASSWORD GATE)
st.title("🔒 Akses Sistem Terproteksi")
input_sandi = st.text_input("Masukkan Sandi Aplikasi untuk Membuka Dashboard:", type="password")

if input_sandi != APP_PASSWORD:
    if input_sandi:
        st.error("❌ Sandi salah! Akses ditolak. Silakan periksa kembali sandi Anda.")
    else:
        st.info("💡 Masukkan sandi keamanan internal untuk mengaktifkan seluruh fitur rekap poin otomatis.")
    st.stop()

# 2. AKTIVASI AI
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Gagal mengaktifkan AI. Periksa kembali API Key di dalam kode. Error: {e}")
    st.stop()

# 3. DATABASE MASTER & ANTRIAN GAMBAR (Session State)
if "hosts_db" not in st.session_state:
    st.session_state.hosts_db = {
        "Eve": 0,
        "Armor": 43407,
        "Aries_Host1": 0,
        "Leo_Host1": 0,
        "Libra_Host1": 0
    }

if "image_queue" not in st.session_state:
    st.session_state.image_queue = [] # Tempat menampung gambar tanpa batas
if "temp_processed_data" not in st.session_state:
    st.session_state.temp_processed_data = None
if "discrepancy_active" not in st.session_state:
    st.session_state.discrepancy_active = False
if "discrepancy_value" not in st.session_state:
    st.session_state.discrepancy_value = 0

# Tampilan Utama Setelah Login Berhasil
st.success("🔓 Akses Diberikan. Selamat Datang di Dashboard Manajemen Poin.")
st.markdown("---")

# Tampilkan Database Host Saat Ini di Sidebar
st.sidebar.subheader("👥 Database Host Terdaftar")
st.sidebar.dataframe(
    pd.DataFrame(list(st.session_state.hosts_db.items()), columns=["Nama Host", "Total Poin Terkumpul"]), 
    use_container_width=True
)

# 4. AREA WORKSPACE UTAMA
tab1, tab2 = st.tabs(["📈 Rekap & Distribusi Poin", "🔬 Upload Analisis Performa"])

with tab1:
    st.subheader("📸 Upload & Akumulasi Screenshot Poin")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        tipe_poin = st.selectbox("Pilih Tipe/Klasifikasi Poin:", ["PK", "Reguler", "Challenge Gift"])
    with col2:
        target_total_poin = st.number_input("Input Target/Total Poin Seharusnya (Untuk Validasi):", min_value=0, value=0, step=1000)
    with col3:
        toleransi_selisih = st.number_input("Toleransi Selisih Poin:", min_value=0, value=5000, step=500)

    # Slot Unggah Gambar Komponen Input Tanpa Batas
    uploaded_files = st.file_uploader(
        "Pilih satu atau beberapa gambar screenshot poin harian:", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True,
        key="screenshot_uploader"
    )
    
    # Tombol untuk memasukkan gambar yang dipilih ke dalam antrean permanen
    if uploaded_files:
        if st.button("➕ Tambahkan Gambar Berkas ke Antrean"):
            for f in uploaded_files:
                try:
                    img_obj = Image.open(f).convert("RGB")
                    st.session_state.image_queue.append(img_obj)
                except Exception as img_err:
                    st.error(f"Gagal memuat salah satu gambar: {img_err}")
            st.success(f"✅ Berhasil menambahkan {len(uploaded_files)} gambar ke dalam antrean!")
            st.rerun()

    # Tampilkan Status Antrean Gambar Saat Ini
    st.markdown("---")
    total_antrean = len(st.session_state.image_queue)
    if total_antrean > 0:
        st.info(f"📋 **Status Antrean:** Saat ini ada **{total_antrean} gambar** yang tersimpan di memori sistem dan siap diproses.")
        if st.button("🗑️ Kosongkan Seluruh Antrean Gambar"):
            st.session_state.image_queue = []
            st.success("Antrean gambar dikosongkan.")
            st.rerun()
    else:
        st.warning("⚠️ Antrean gambar kosong. Silakan upload gambar dan klik tombol 'Tambahkan Gambar Berkas ke Antrean' di atas.")

    template_file = st.file_uploader("Upload Gambar Background/Template Laporan Akhir:", type=["png", "jpg", "jpeg"], key="template_poin")

    # PROSES EKSTRAKSI DATA DARI ANTREAN
    if total_antrean > 0 and template_file:
        if st.button("🚀 Mulai Ekstrak & Hitung Semua Gambar Antrean"):
            all_extracted_data = []
            
            with st.spinner(f"AI sedang membaca {total_antrean} gambar dalam antrean secara berurutan..."):
                try:
                    for idx, raw_img in enumerate(st.session_state.image_queue):
                        prompt = """
                        Analisis gambar screenshot data poin berikut. Extract semua nama host dan jumlah poin mereka.
                        Pastikan ejaan nama sangat akurat (Contoh: 'Eve' jangan sampai dibaca 'Ive').
                        Kembalikan HANYA dalam format JSON array of objects tanpa teks markdown pembuka/penutup seperti ini:
                        [{"name": "NamaHost", "points": 10000}]
                        """
                        
                        response = model.generate_content([prompt, raw_img])
                        response_text = response.text.strip()
                        
                        if response_text.startswith("```"):
                            response_text = response_text.split("```")[1]
                            if response_text.startswith("json"):
                                response_text = response_text[4:]
                        
                        data_part = json.loads(response_text.strip())
                        all_extracted_data.extend(data_part)
                    
                    # Gabungkan data poin per host
                    df_raw = pd.DataFrame(all_extracted_data)
                    df_raw['points'] = pd.to_numeric(df_raw['points'])
                    df_grouped = df_raw.groupby('name', as_index=False).sum()
                    
                    total_terhitung = df_grouped['points'].sum()
                    selisih = total_terhitung - target_total_poin
                    
                    st.session_state.temp_processed_data = df_grouped.to_dict('records')
                    st.session_state.tipe_proses = tipe_poin
                    
                    if target_total_poin > 0 and abs(selisih) > toleransi_selisih:
                        st.session_state.discrepancy_active = True
                        st.session_state.discrepancy_value = selisih
                    else:
                        st.session_state.discrepancy_active = False
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Gagal memproses akumulasi gambar: {e}")

    # 5. PANEL KONTROL ERROR SELISIH
    if st.session_state.discrepancy_active:
        st.error(f"⚠️ Terdeteksi Selisih Poin Sangat Besar! Total Selisih: {st.session_state.discrepancy_value:,} Poin.")
        opsi_penanganan = st.radio("Metode Penanganan Selisih:", ["Bagi Rata ke Semua Host", "Masukkan Manual / Abaikan Selisih"])
        
        if st.button("Konfirmasi & Eksekusi Penanganan"):
            df_temp = pd.DataFrame(st.session_state.temp_processed_data)
            nilai_selisih_per_host = st.session_state.discrepancy_value / len(df_temp)
            
            if opsi_penanganan == "Bagi Rata ke Semua Host":
                df_temp['points'] = df_temp['points'] - nilai_selisih_per_host
                st.session_state.temp_processed_data = df_temp.to_dict('records')
            
            st.session_state.discrepancy_active = False
            st.success("Selisih berhasil ditangani!")
            st.rerun()

    # 6. AKUMULASI & CETAK GAMBAR FINAL
    if st.session_state.temp_processed_data and not st.session_state.discrepancy_active:
        df_final = pd.DataFrame(st.session_state.temp_processed_data)
        
        if st.session_state.tipe_proses == "PK":
            host_terkecil = min(st.session_state.hosts_db, key=st.session_state.hosts_db.get)
            st.info(f"ℹ️ Mode PK Aktif: Distribusi poin diprioritaskan untuk mendukung host dengan poin terkecil ({host_terkecil}).")
            
        for item in st.session_state.temp_processed_data:
            nama = item['name']
            poin = item['points']
            
            if nama not in st.session_state.hosts_db:
                st.session_state.hosts_db[nama] = 0
                st.toast(f"✨ Host Baru Tersimpan: {nama}")
                
            st.session_state.hosts_db[nama] += poin

        st.subheader("🖼️ Output Gambar Laporan Akhir")
        report_image = Image.open(template_file).convert("RGB")
        draw = ImageDraw.Draw(report_image)
        
        try:
            font_title = ImageFont.load_default(size=30)
            font_sub = ImageFont.load_default(size=22)
        except:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        start_x, start_y = 60, 160
        draw.text((start_x, start_y - 60), f"LAPORAN POIN - TIM LIVE ({st.session_state.tipe_proses})", fill=(255, 255, 255), font=font_title)
        
        df_sorted_report = df_final.sort_values(by='points', ascending=False)
        for index, row in df_sorted_report.iterrows():
            text_line = f"- {row['name']} : +{int(row['points']):,} Poin"
            draw.text((start_x, start_y), text_line, fill=(255, 255, 255), font=font_sub)
            start_y += 45
            
        st.image(report_image, caption="Hasil Laporan Final Siap Dikirim ke Kak Ayu", use_container_width=True)
        
        img_byte_arr = io.BytesIO()
        report_image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        st.download_button(
            label="📥 Download Gambar Laporan Akhir",
            data=img_byte_arr,
            file_name=f"laporan_final_{st.session_state.tipe_proses}.png",
            mime="image/png"
        )
        
        if st.button("Clear Buffer Harian & Reset Antrean"):
            st.session_state.temp_processed_data = None
            st.session_state.image_queue = [] # Bersihkan antrean untuk hari esok
            st.rerun()

with tab2:
    st.subheader("🔬 Modul Analisis Performa AI")
    st.write("Tempat khusus untuk analisis data grafik, durasi, atau retensi traffic.")
    
    analysis_file = st.file_uploader("Upload Gambar Grafik/Tabel Analisis:", type=["png", "jpg", "jpeg"], key="analysis_uploader")
    
    if analysis_file and st.button("🔮 Jelaskan Hasil Analisis"):
        with st.spinner("AI sedang menganalisis data visual..."):
            raw_analysis = Image.open(analysis_file)
            analysis_prompt = "Analisis gambar grafik performa streaming ini. Berikan poin penting perkembangan traffic dan strategi ringkas untuk pelaporan manajemen."
            analysis_response = model.generate_content([analysis_prompt, raw_analysis])
            st.success("📋 Hasil Analisis AI Selesai:")
            st.info(analysis_response.text)
