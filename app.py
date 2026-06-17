import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import json
import pandas as pd
import io
import os
from datetime import datetime

# =========================================================================
# 🔑 PENGATURAN INTERNAL
# =========================================================================
GEMINI_API_KEY = "MAQ.Ab8RN6Ia9d9C_DwEaZeeETi_COLRGARZEunDkG_lgyqERtaFfA" 
APP_PASSWORD = "VIDA123" 
DB_FILE = "database_riwayat.json"
# =========================================================================

# Konfigurasi Halaman Web
st.set_page_config(page_title="AI Point System", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_history(history_data):
    with open(DB_FILE, 'w') as f:
        json.dump(history_data, f, indent=4)

if "history_db" not in st.session_state:
    st.session_state.history_db = load_history()
if "current_folder" not in st.session_state:
    st.session_state.current_folder = "Buat Rekap Baru ✧"

# GERBANG KEAMANAN
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Akses Sistem Manajemen")
    input_sandi = st.text_input("Masukkan sandi keamanan untuk mengakses panel ini:", type="password")
    if input_sandi == APP_PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif input_sandi:
        st.error("❌ Sandi salah. Akses ditolak.")
    st.stop()

# AKTIVASI AI
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Gagal mengaktifkan AI. Error: {e}")
    st.stop()

# SIDEBAR (RIWAYAT)
st.sidebar.title("📁 Riwayat Rekap")
st.sidebar.button("➕ Buat Rekap Baru", on_click=lambda: st.session_state.update(current_folder="Buat Rekap Baru ✧"), use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("Folder Hari Sebelumnya:")

for folder_id in reversed(list(st.session_state.history_db.keys())):
    folder_label = st.session_state.history_db[folder_id].get("label", folder_id)
    if st.sidebar.button(f"📄 {folder_label}", key=f"btn_{folder_id}", use_container_width=True):
        st.session_state.current_folder = folder_id

# AREA KERJA UTAMA
if st.session_state.current_folder == "Buat Rekap Baru ✧":
    with st.chat_message("ai"):
        st.write("✨ **Halo! Saya siap merekap data hari ini.** Silakan atur tipe sesi dan unggah screenshot yang ingin dihitung.")
    
    col1, col2 = st.columns(2)
    with col1:
        tipe_poin = st.selectbox("Klasifikasi Poin:", ["PK", "Reguler", "Challenge Gift", "Event Khusus"])
    with col2:
        nama_sesi = st.text_input("Beri Nama Folder Ini:", value=f"Rekap {datetime.now().strftime('%d %b %H:%M')}")

    st.markdown("### 📤 Upload Data Poin")
    uploaded_files = st.file_uploader(
        "Pilih gambar screenshot poin (Bisa pilih banyak sekaligus):", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )
    
    template_file = st.file_uploader("Upload Gambar Background Laporan (Template):", type=["png", "jpg", "jpeg"])

    # TOMBOL KIRIM & REKAP
    if uploaded_files and template_file:
        st.markdown("---")
        if st.button("📤 Kirim & Rekap Data", type="primary", use_container_width=True):
            all_extracted_data = []
            
            with st.chat_message("ai"):
                with st.spinner("Sedang mengekstrak data dari gambar..."):
                    try:
                        for file in uploaded_files:
                            raw_img = Image.open(file)
                            prompt = """
                            Analisis gambar screenshot data poin berikut. Extract semua nama host dan jumlah poin mereka.
                            Pastikan ejaan nama akurat (contoh 'Eve' bukan 'Ive').
                            Kembalikan HANYA format JSON array: [{"name": "NamaHost", "points": 10000}]
                            """
                            response = model.generate_content([prompt, raw_img])
                            response_text = response.text.strip()
                            
                            if response_text.startswith("```"):
                                response_text = response_text.split("```")[1]
                                if response_text.startswith("json"):
                                    response_text = response_text[4:]
                            
                            data_part = json.loads(response_text.strip())
                            all_extracted_data.extend(data_part)
                        
                        df_raw = pd.DataFrame(all_extracted_data)
                        df_raw['points'] = pd.to_numeric(df_raw['points'])
                        df_grouped = df_raw.groupby('name', as_index=False).sum()
                        
                        folder_id = datetime.now().strftime('%Y%m%d_%H%M%S')
                        
                        # Bagian yang sebelumnya error sudah diperbaiki dengan tanda kurung yang lengkap
                        st.session_state.history_db[folder_id] = {
                            "label": f"{nama_sesi} ({tipe_poin})",
                            "tipe": tipe_poin,
                            "data": df_grouped.to_dict('records')
                        }
                        
                        save_history(st.session_state.history_db)
                        
                        st.session_state.current_folder = folder_id
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal memproses gambar: {e}")

else:
    # MODE BUKA FOLDER (EDIT, CETAK & KIRIM PESAN)
    folder_id = st.session_state.current_folder
    folder_data = st.session_state.history_db[folder_id]
    
    with st.chat_message("ai"):
        st.write(f"📂 **Membuka Folder:** `{folder_data['label']}`")
        st.write("Silakan koreksi angka pada tabel di bawah jika ada selisih, lalu cetak laporannya.")
    
    df = pd.DataFrame(folder_data['data'])
    edited_df = st.data_editor(
        df, 
        use_container_width=True, 
        num_rows="dynamic",
        key=f"editor_{folder_id}"
    )
    
    if st.button("💾 Simpan Perubahan Tabel"):
        st.session_state.history_db[folder_id]['data'] = edited_df.to_dict('records')
        save_history(st.session_state.history_db)
        st.success("Perubahan disimpan!")
    
    st.markdown("---")
    st.markdown("### 🖨️ Cetak & Kirim Laporan")
    template_file_re = st.file_uploader("Upload Template Gambar Background:", type=["png", "jpg", "jpeg"], key=f"tpl_{folder_id}")
    
    if template_file_re and st.button("📤 Generate Gambar & Teks Pesan", type="primary", use_container_width=True):
        report_image = Image.open(template_file_re).convert("RGB")
        draw = ImageDraw.Draw(report_image)
        
        try:
            font_title = ImageFont.load_default(size=30)
            font_sub = ImageFont.load_default(size=22)
        except:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        start_x, start_y = 60, 160
        draw.text((start_x, start_y - 60), f"LAPORAN POIN - {folder_data['tipe']}", fill=(255, 255, 255), font=font_title)
        
        df_sorted = edited_df.sort_values(by='points', ascending=False)
        
        # Susun Teks Otomatis untuk Pelaporan ke Atasan
        teks_wa = f"Halo Kak Ayu, berikut adalah rekap {folder_data['tipe']} tim untuk sesi ini:\n\n"
        
        for index, row in df_sorted.iterrows():
            nama = row['name']
            poin = int(row['points'])
            
            # Tulis ke Gambar
            text_line = f"- {nama} : +{poin:,} Poin"
            draw.text((start_x, start_y), text_line, fill=(255, 255, 255), font=font_sub)
            start_y += 45
            
            # Tambahkan ke Teks WA
            teks_wa += f"• {nama}: {poin:,} Poin\n"
            
        teks_wa += "\nDetail performa selengkapnya ada pada gambar terlampir. Terima kasih, Kak.\n- Aqie"
            
        with st.chat_message("ai"):
            st.image(report_image, caption="Laporan Siap Diunduh", use_container_width=True)
            
            img_byte_arr = io.BytesIO()
            report_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            st.download_button(
                label="📥 Download Gambar Laporan",
                data=img_byte_arr,
                file_name=f"Laporan_{folder_data['label']}.png",
                mime="image/png"
            )
            
            st.markdown("**Salin Teks di Bawah untuk Laporan Cepat:**")
            st.text_area("Teks Siap Salin:", value=teks_wa, height=250)
