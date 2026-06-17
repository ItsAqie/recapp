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
GEMINI_API_KEY = "AQ.Ab8RN6Ia9d9C_DwEaZeeETi_COLRGARZEunDkG_lgyqERtaFfA" 
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
    st.session_state.current_folder = "Buat Folder Baru ➕"

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

# =========================================================================
# SIDEBAR (NAVIGASI FOLDER)
# =========================================================================
st.sidebar.title("📁 Direktori Rekap")
st.sidebar.button("➕ Buat Folder Baru", on_click=lambda: st.session_state.update(current_folder="Buat Folder Baru ➕"), use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("Folder Tersimpan:")

for folder_id in reversed(list(st.session_state.history_db.keys())):
    folder_label = st.session_state.history_db[folder_id].get("label", folder_id)
    if st.sidebar.button(f"📂 {folder_label}", key=f"btn_{folder_id}", use_container_width=True):
        st.session_state.current_folder = folder_id

# =========================================================================
# AREA KERJA UTAMA
# =========================================================================
if st.session_state.current_folder == "Buat Folder Baru ➕":
    # ---------------------------------------------------------
    # HALAMAN 1: PEMBUATAN FOLDER KOSONG
    # ---------------------------------------------------------
    st.header("➕ Buat Folder Rekap Baru")
    st.write("Buat wadah foldernya terlebih dahulu. Anda bisa mengisi screenshot dan merekap datanya nanti.")
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            tipe_poin = st.selectbox("Klasifikasi Poin / Tipe Sesi:", ["PK", "Reguler", "Challenge Gift", "Event Khusus"])
        with col2:
            nama_sesi = st.text_input("Nama Folder:", value=f"Rekap {datetime.now().strftime('%d %b %H:%M')}")
        
        if st.button("📁 Buat Folder Sekarang", type="primary"):
            folder_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Buat struktur folder kosong (data masih array kosong)
            st.session_state.history_db[folder_id] = {
                "label": f"{nama_sesi} ({tipe_poin})",
                "tipe": tipe_poin,
                "data": [] # Belum ada data
            }
            save_history(st.session_state.history_db)
            
            # Langsung arahkan (buka) folder yang baru dibuat
            st.session_state.current_folder = folder_id
            st.rerun()

else:
    # ---------------------------------------------------------
    # HALAMAN 2: DI DALAM FOLDER
    # ---------------------------------------------------------
    folder_id = st.session_state.current_folder
    folder_data = st.session_state.history_db[folder_id]
    
    st.header(f"📂 {folder_data['label']}")
    st.markdown("---")
    
    # KONDISI A: FOLDER MASIH KOSONG (Waktunya Upload & Ekstrak)
    if not folder_data.get('data'):
        with st.chat_message("ai"):
            st.write("Folder ini masih kosong. Silakan unggah *screenshot* poin untuk mulai direkap oleh sistem AI.")
        
        uploaded_files = st.file_uploader(
            "Pilih satu atau beberapa gambar screenshot poin:", 
            type=["png", "jpg", "jpeg"], 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            if st.button("🪄 Ekstrak & Rekap Gambar ke Folder Ini", type="primary", use_container_width=True):
                all_extracted_data = []
                
                with st.spinner("AI sedang mengekstrak angka dari gambar..."):
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
                        
                        # Simpan hasil
