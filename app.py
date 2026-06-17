import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import io
import os
from datetime import datetime
import matplotlib.pyplot as plt

# =========================================================================
# 🔑 PENGATURAN INTERNAL
# =========================================================================
GEMINI_API_KEY = "AQ.Ab8RN6Ia9d9C_DwEaZeeETi_COLRGARZEunDkG_lgyqERtaFfA" 
APP_PASSWORD = "1231" 
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

# Fungsi untuk Menggambar Tabel Dataframe menjadi File Gambar (PNG)
def create_table_image(df, title):
    # Rapikan dan urutkan data
    df_sorted = df.sort_values(by='points', ascending=False).reset_index(drop=True)
    df_sorted.index = df_sorted.index + 1
    df_sorted.insert(0, 'Rank', df_sorted.index)
    df_sorted.rename(columns={'name': 'Nama Host', 'points': 'Total Poin'}, inplace=True)
    
    # Format angka ribuan
    df_sorted['Total Poin'] = df_sorted['Total Poin'].apply(lambda x: f"{int(x):,}")

    # Kalkulasi ukuran gambar berdasarkan jumlah baris (host)
    fig_height = len(df_sorted) * 0.6 + 1.5
    fig, ax = plt.subplots(figsize=(8, fig_height))
    ax.axis('tight')
    ax.axis('off')
    
    # Judul Tabel
    ax.set_title(title, fontsize=16, weight='bold', pad=20)

    # Pembuatan Tabel Visual
    table = ax.table(
        cellText=df_sorted.values,
        colLabels=df_sorted.columns,
        cellLoc='center',
        loc='center',
        bbox=[0, 0, 1, 1]
    )

    table.auto_set_font_size(False)
    table.set_fontsize(12)

    # Mewarnai Header Tabel (Hijau Gelap)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#2E7D32')
        else:
            # Mewarnai baris genap/ganjil agar mudah dibaca
            if row % 2 == 0:
                cell.set_facecolor('#F5F5F5')

    # Simpan plot ke memori (BytesIO) sebagai PNG beresolusi tinggi (300dpi)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close(fig)
    return buf

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
    st.header("➕ Buat Folder Rekap Baru")
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            tipe_poin = st.selectbox("Klasifikasi Poin:", ["PK", "Reguler", "Challenge Gift", "Event Khusus"])
        with col2:
            nama_sesi = st.text_input("Nama Grup / Sesi (Misal: Leo Sesi 1):", value=f"Rekap {datetime.now().strftime('%d %b %H:%M')}")
        
        if st.button("📁 Buat Folder Sekarang", type="primary"):
            folder_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            st.session_state.history_db[folder_id] = {
                "label": f"{nama_sesi} ({tipe_poin})",
                "tipe": tipe_poin,
                "data": [] 
            }
            save_history(st.session_state.history_db)
            
            st.session_state.current_folder = folder_id
            st.rerun()

else:
    folder_id = st.session_state.current_folder
    folder_data = st.session_state.history_db[folder_id]
    
    st.header(f"📂 {folder_data['label']}")
    st.markdown("---")
    
    # JIKA DATA KOSONG (WAKTUNYA UPLOAD SCREENSHOT)
    if not folder_data.get('data'):
        with st.chat_message("ai"):
            st.write("Folder ini siap menampung gambar screenshot tabel Anda. Sistem akan otomatis menghitung baris TOTAL/ADJUSTED dari gambar yang diunggah.")
        
        uploaded_files = st.file_uploader(
            "Upload Screenshot Spreadsheet Poin:", 
            type=["png", "jpg", "jpeg"], 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            if st.button("🪄 Ekstrak & Hitung Angka (Tanpa Template)", type="primary", use_container_width=True):
                all_extracted_data = []
                
                with st.spinner("AI sedang memindai tabel dan mencocokkan nama dengan baris TOTAL..."):
                    try:
                        import google.generativeai as genai
                        from PIL import Image
                        
                        for file in uploaded_files:
                            raw_img = Image.open(file)
                            
                            prompt = "Gambar ini adalah tabel rekap performa host. Di bagian atas tabel terdapat baris nama-nama host (seperti UTA, JENV, RUBIE, dll). Di sebelah kiri terdapat label kategori poin. Tugasmu: Temukan baris dengan label 'TOTAL' atau 'ADJUSTED' di bagian bawah tabel utama. Pasangkan setiap nama host di atas dengan angka mereka yang berada di baris 'TOTAL' atau 'ADJUSTED' tersebut. Abaikan host yang bernama '-' atau kolom yang kosong. Abaikan tabel-tabel kecil di sebelah kanan. Pastikan ejaan nama akurat (contoh: 'Eve' bukan 'Ive'). Kembalikan HANYA format JSON array persis seperti ini: [{\"name\": \"UTA\", \"points\": 8015}, {\"name\": \"JENV\", \"points\": 2796}]. Jangan tambahkan teks markdown apapun."
                            
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
                        
                        st.session_state.history_db[folder_id]['data'] = df_grouped.to_dict('records')
                        save_history(st.session_state.history_db)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Gagal memproses gambar: {e}")

    # JIKA DATA SUDAH TERISI (WAKTUNYA EDIT & EXPORT KE PNG)
    else:
        with st.chat_message("ai"):
            st.write("✅ **Ekstraksi Selesai!** Jika ada kesalahan nominal karena gambar buram, klik langsung pada tabel di bawah untuk merevisinya. Setelah itu, tekan tombol Cetak ke PNG.")
        
        df = pd.DataFrame(folder_data['data'])
        edited_df = st.data_editor(
            df, 
            use_container_width=True, 
            num_rows="dynamic",
            key=f"editor_{folder_id}"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Simpan Tabel", use_container_width=True):
                st.session_state.history_db[folder_id]['data'] = edited_df.to_dict('records')
                save_history(st.session_state.history_db)
                st.success("Tabel di-update!")
        with col2:
            if st.button("⚠️ Hapus Data (Reset Folder)", use_container_width=True):
                st.session_state.history_db[folder_id]['data'] = []
                save_history(st.session_state.history_db)
                st.rerun()
                
        st.markdown("---")
        st.subheader("🖨️ Export Laporan Akhir")
        
        if st.button("📤 Generate & Export Tabel ke PNG", type="primary", use_container_width=True):
            with st.spinner("Membuat gambar tabel resolusi tinggi..."):
                judul_tabel = f"LAPORAN POIN - {folder_data['label']}"
                
                # Fungsi pembuat gambar tabel dipanggil di sini
                tabel_png = create_table_image(edited_df, judul_tabel)
                
                df_sorted = edited_df.sort_values(by='points', ascending=False)
                teks_wa = f"Halo Kak Ayu, berikut adalah laporan {folder_data['tipe']} tim untuk sesi ini:\n\n"
                
                for index, row in df_sorted.iterrows():
                    teks_wa += f"• {row['name']}: {int(row['points']):,} Poin\n"
                    
                teks_wa += "\nTabel rekap visual terlampir pada gambar. Terima kasih, Kak.\n- Aqie"
                
                with st.chat_message("ai"):
                    st.image(tabel_png, caption="Tabel Siap Diunduh", use_container_width=True)
                    
                    st.download_button(
                        label="📥 Download Tabel PNG",
                        data=tabel_png,
                        file_name=f"Rekap_Tabel_{folder_data['label']}.png",
                        mime="image/png"
                    )
                    
                    st.markdown("**Salin Teks di Bawah untuk Laporan Cepat:**")
                    st.text_area("Teks Siap Salin:", value=teks_wa, height=250)
