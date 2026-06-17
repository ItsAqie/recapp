import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import json
import pandas as pd
import io

# Konfigurasi Halaman Web
st.set_page_config(page_title="AI Advanced Point System", layout="wide")
st.title("📊 Sistem AI Pemrosesan & Distribusi Poin Otomatis")
st.write("Sistem manajemen poin pintar berbasis AI Vision dengan kontrol selisih dan distribusi otomatis.")

# 1. DATABASE HOST BERJALAN (Disimpan dalam Session State agar tidak hilang saat refresh)
if "hosts_db" not in st.session_state:
    # Inisialisasi data awal internal (Nama akurat sesuai database manajemen)
    st.session_state.hosts_db = {
        "Eve": 0,
        "Armor": 43407,
        "Aries_Host1": 0,
        "Leo_Host1": 0,
        "Libra_Host1": 0
    }

if "temp_processed_data" not in st.session_state:
    st.session_state.temp_processed_data = None
if "discrepancy_active" not in st.session_state:
    st.session_state.discrepancy_active = False
if "discrepancy_value" not in st.session_state:
    st.session_state.discrepancy_value = 0

# 2. PENGATURAN API KEY (Sidebar)
st.sidebar.header("🔧 Konfigurasi AI")
api_key_input = st.sidebar.text_input("Masukkan Gemini API Key:", type="password")

if not api_key_input:
    st.info("💡 Silakan masukkan Gemini API Key Anda di sidebar kiri untuk mengaktifkan seluruh sistem AI.")
    st.stop()

# Aktivasi Gemini
genai.configure(api_key=api_key_input)
model = genai.GenerativeModel('gemini-1.5-flash')

# Tampilkan Database Host Saat Ini di Sidebar
st.sidebar.subheader("👥 Database Host Terdaftar")
st.sidebar.dataframe(pd.DataFrame(list(st.session_state.hosts_db.items()), columns=["Nama Host", "Total Poin Terkumpul"]), use_container_width=True)


# 3. AREA WORKSPACE UTAMA (Menggunakan Tab agar Rapih)
tab1, tab2 = st.tabs(["📈 Rekap & Distribusi Poin", "🔬 Upload Analisis Performa"])

with tab1:
    st.subheader("📸 Upload Screenshot Poin")
    
    # Form Input Parameter Pengolahan
    col1, col2, col3 = st.columns(3)
    with col1:
        tipe_poin = st.selectbox("Pilih Tipe/Klasifikasi Poin:", ["PK", "Reguler", "Challenge Gift"])
    with col2:
        target_total_poin = st.number_input("Input Target/Total Poin Seharusnya (Untuk Validasi):", min_value=0, value=0, step=1000)
    with col3:
        toleransi_selisih = st.number_input("Toleransi Selisih Poin:", min_value=0, value=5000, step=500)

    # Upload Banyak Gambar Sekaligus
    uploaded_screenshots = st.file_uploader("Upload satu atau beberapa screenshot poin harian:", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    template_file = st.file_uploader("Upload Gambar Background/Template Laporan Akhir:", type=["png", "jpg", "jpeg"], key="template_poin")

    # PROSES UTAMA
    if uploaded_screenshots and template_file and st.button("🚀 Ekstrak & Hitung Poin"):
        all_extracted_data = []
        
        with st.spinner("AI sedang membaca seluruh gambar..."):
            try:
                for idx, file in enumerate(uploaded_screenshots):
                    raw_img = Image.open(file)
                    
                    prompt = """
                    Analisis gambar screenshot data poin berikut. Extract semua nama host dan jumlah poin mereka.
                    Pastikan ejaan nama sangat akurat (Contoh: 'Eve' jangan sampai dibaca 'Ive').
                    Kembalikan HANYA dalam format JSON array of objects tanpa teks markdown pembuka/penutup seperti ini:
                    [{"name": "NamaHost", "points": 10000}]
                    """
                    
                    response = model.generate_content([prompt, raw_img])
                    response_text = response.text.strip()
                    
                    # Pembersihan format json markdown jika ada
                    if response_text.startswith("```"):
                        response_text = response_text.split("```")[1]
                        if response_text.startswith("json"):
                            response_text = response_text[4:]
                    
                    data_part = json.loads(response_text.strip())
                    all_extracted_data.extend(data_part)
                
                # Gabungkan data jika ada nama yang dobel dari beberapa screenshot
                df_raw = pd.DataFrame(all_extracted_data)
                df_raw['points'] = pd.to_numeric(df_raw['points'])
                df_grouped = df_raw.groupby('name', as_index=False).sum()
                
                total_terhitung = df_grouped['points'].sum()
                selisih = total_terhitung - target_total_poin
                
                # Simpan data sementara ke state
                st.session_state.temp_processed_data = df_grouped.to_dict('records')
                st.session_state.tipe_proses = tipe_poin
                
                # CEK ERROR SELISIH SANGAT BANYAK
                if target_total_poin > 0 and abs(selisih) > toleransi_selisih:
                    st.session_state.discrepancy_active = True
                    st.session_state.discrepancy_value = selisih
                else:
                    st.session_state.discrepancy_active = False
                    # Jalankan akumulasi normal jika aman
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Gagal memproses gambar: {e}")

    # 4. POP-UP PANEL KONTROL ERROR SELISIH (Simulasi Modal Modalbox)
    if st.session_state.discrepancy_active:
        st.error(f"⚠️ Terdeteksi Selisih Poin Sangat Besar! Total Selisih: {st.session_state.discrepancy_value:,} Poin.")
        st.write("Silakan pilih opsi penanganan di bawah ini untuk melanjutkan penggabungan data:")
        
        opsi_penanganan = st.radio("Metode Penanganan Selisih:", ["Bagi Rata ke Semua Host", "Masukkan Manual / Abaikan Selisih"])
        
        if st.button("Konfirmasi & Eksekusi Penanganan"):
            df_temp = pd.DataFrame(st.session_state.temp_processed_data)
            nilai_selisih_per_host = st.session_state.discrepancy_value / len(df_temp)
            
            if opsi_penanganan == "Bagi Rata ke Semua Host":
                # Kurangi atau tambahkan selisih secara merata
                df_temp['points'] = df_temp['points'] - nilai_selisih_per_host
                st.session_state.temp_processed_data = df_temp.to_dict('records')
            
            st.session_state.discrepancy_active = False
            st.success("Selisih berhasil ditangani!")
            st.slots_calculated = True # Flag pemicu cetak gambar

    # 5. LOGIKA AKUMULASI, DISTRIBUSI PK, & CETAK GAMBAR
    if st.session_state.temp_processed_data and not st.session_state.discrepancy_active:
        df_final = pd.DataFrame(st.session_state.temp_processed_data)
        
        # Logika Tambahan: Jika Tipe PK, cari poin terkecil di database untuk diberikan bonus/sisa poin jika ada
        if st.session_state.tipe_proses == "PK":
            # Cari host dengan poin terkecil saat ini di database terdaftar
            host_terkecil = min(st.session_state.hosts_db, key=st.session_state.hosts_db.get)
            st.info(f"ℹ️ Mode PK Aktif: Jika ada penyesuaian nilai lebih, sistem memprioritaskan dukungan ke host poin terkecil saat ini ({host_terkecil}).")
            
        # Update / Masukkan ke Database Utama Berjalan
        for item in st.session_state.temp_processed_data:
            nama = item['name']
            poin = item['points']
            
            # Jika nama baru belum ada di database, otomatis tambahkan
            if nama not in st.session_state.hosts_db:
                st.session_state.hosts_db[nama] = 0
                st.toast(f"✨ Host Baru Terdeteksi & Tersimpan: {nama}")
                
            # Tambahkan poin harian ke dalam database master
            st.session_state.hosts_db[nama] += poin

        # Buat Gambar Output Laporan Akhir
        st.subheader("🖼️ Output Gambar Laporan Akhir")
        report_image = Image.open(template_file).convert("RGB")
        draw = ImageDraw.Draw(report_image)
        
        try:
            font_title = ImageFont.load_default(size=30)
            font_sub = ImageFont.load_default(size=22)
        except:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        # Cetak data terupdate ke atas template gambar
        start_x, start_y = 60, 160
        draw.text((start_x, start_y - 60), f"LAPORAN POIN - TIM LIVE ({st.session_state.tipe_proses})", fill=(255, 255, 255), font=font_title)
        
        # Urutkan berdasarkan performa tertinggi untuk dicetak di gambar laporan harian
        df_sorted_report = df_final.sort_values(by='points', ascending=False)
        for index, row in df_sorted_report.iterrows():
            text_line = f"- {row['name']} : +{int(row['points']):,} Poin"
            draw.text((start_x, start_y), text_line, fill=(255, 255, 255), font=font_sub)
            start_y += 45
            
        st.image(report_image, caption="Hasil Laporan Final Siap Dikirim", use_container_width=True)
        
        # Sediakan Tombol Download Gambar
        img_byte_arr = io.BytesIO()
        report_image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        st.download_button(
            label="📥 Download Gambar Laporan Akhir",
            data=img_byte_arr,
            file_name=f"laporan_final_{st.session_state.tipe_proses}.png",
            mime="image/png"
        )
        
        # Tombol Reset untuk pemrosesan hari berikutnya
        if st.button("Clear Buffer Harian"):
            st.session_state.temp_processed_data = None
            st.rerun()


with tab2:
    st.subheader("🔬 Modul Analisis Performa AI")
    st.write("Tempat khusus untuk mengunggah screenshot grafik analisis penonton, durasi, atau retensi traffic.")
    
    analysis_file = st.file_uploader("Upload Gambar Grafik/Tabel Analisis:", type=["png", "jpg", "jpeg"], key="analysis_uploader")
    
    if analysis_file and st.button("🔮 Jelasakan Hasil Analisis"):
        with st.spinner("AI sedang mendalami data grafik..."):
            raw_analysis = Image.open(analysis_file)
            
            analysis_prompt = """
            Analisis gambar grafik/data performa live streaming berikut.
            Berikan poin-poin kesimpulan penting mengenai perkembangan traffic penonton, jam sibuk, atau retensi gift.
            Gunakan gaya bahasa profesional, lugas, dan berikan rekomendasi strategi konkret yang siap dilaporkan ke manajemen/atasan.
            """
            
            analysis_response = model.generate_content([analysis_prompt, raw_analysis])
            st.success("📋 Hasil Analisis AI Selesai:")
            st.info(analysis_response.text)
