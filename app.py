import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import json
import matplotlib.pyplot as plt
import time

st.set_page_config(page_title="AI Point Converter", layout="centered")

# =========================================================================
# STATE MANAGEMENT
# =========================================================================
if 'api_verified' not in st.session_state:
    st.session_state.api_verified = False
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'model_name' not in st.session_state:
    st.session_state.model_name = ""

st.title("⚡ AI Point Converter (MCA & TikTok)")

# =========================================================================
# HALAMAN 1: GERBANG VERIFIKASI API KEY
# =========================================================================
if not st.session_state.api_verified:
    st.write("Silakan hubungkan sistem dengan Google Gemini API terlebih dahulu.")
    
    api_key_input = st.text_input("🔑 Masukkan Gemini API Key (Awalan AIza...):", type="password")
    
    if st.button("Verifikasi & Hubungkan", type="primary"):
        if api_key_input:
            with st.spinner("Sedang memverifikasi kunci ke server Google..."):
                api_key_bersih = api_key_input.strip()
                genai.configure(api_key=api_key_bersih)
                
                try:
                    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    
                    if 'models/gemini-1.5-pro' in available_models:
                        st.session_state.model_name = 'gemini-1.5-pro'
                    elif 'models/gemini-1.5-flash' in available_models:
                        st.session_state.model_name = 'gemini-1.5-flash'
                    elif 'models/gemini-pro-vision' in available_models:
                        st.session_state.model_name = 'gemini-pro-vision'
                    else:
                        st.session_state.model_name = available_models[0]
                        
                    st.session_state.api_verified = True
                    st.session_state.api_key = api_key_bersih
                    st.rerun()
                    
                except Exception as e:
                    st.error("❌ Verifikasi Gagal! API Key salah, tidak valid, atau bermasalah.")
                    st.warning(f"Detail Error: {e}")
        else:
            st.warning("API Key tidak boleh kosong.")

# =========================================================================
# HALAMAN 2: APLIKASI UTAMA
# =========================================================================
else:
    genai.configure(api_key=st.session_state.api_key)
    model = genai.GenerativeModel(st.session_state.model_name)
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.success(f"✅ Sistem Terhubung! (Model: {st.session_state.model_name.replace('models/', '')})")
    with col2:
        if st.button("Logout"):
            st.session_state.api_verified = False
            st.session_state.api_key = ""
            st.session_state.model_name = ""
            st.rerun()

    st.markdown("---")
    st.write("Upload campuran gambar **Tabel Poin MCA** dan **TikTok Analytics/Match** sekaligus.")
    
    uploaded_files = st.file_uploader("📸 Upload Screenshot (Bisa pilih banyak file):", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

    if uploaded_files:
        if st.button("🚀 Convert & Gabungkan Poin", type="primary", use_container_width=True):
            all_data = []
            
            progress_text = "Membaca gambar..."
            my_bar = st.progress(0, text=progress_text)
            total_files = len(uploaded_files)
            
            with st.spinner("AI sedang menganalisis data visual..."):
                try:
                    from PIL import Image
                    for i, file in enumerate(uploaded_files):
                        img = Image.open(file)
                        
                        # =========================================================================
                        # PROMPT AI YANG SUDAH DIBEKALI ATURAN SOLO & MVP 2 HOST
                        # =========================================================================
                        prompt = """
                        Gambar ini berisi data poin performa host. Bentuknya bisa berupa tabel rekap (MCA/Spreadsheet) ATAU screenshot analitik/pertandingan TikTok.
                        Tugasmu: Ekstrak nama host dan total poin/pendapatan (diamond/koin/adjusted) mereka berdasarkan aturan berikut:
                        
                        ATURAN EKSTRAKSI:
                        1. Jika gambar adalah tabel MCA: Cari baris 'TOTAL' atau 'ADJUSTED' di bagian bawah, pasangkan dengan nama host di bagian atas.
                        2. Jika gambar adalah TikTok Analytics biasa: Ekstrak nama akun/host dan total koin/diamond yang tertera.
                        3. ATURAN KHUSUS SOLO & MVP: Jika ada data kategori 'Solo MVP', gabungkan nilainya menjadi satu kesatuan poin 'Solo'. 
                        4. ATURAN PK/MATCH: Jika screenshot menampilkan match/pertandingan yang HANYA berisi 2 host (PK 1v1), maka anggap itu adalah perebutan poin MVP. Kamu wajib mengekstrak dan menggunakan nilai poin yang terbaru/final yang tertera di layar untuk masing-masing host.
                        
                        Abaikan host yang bernama '-' atau data yang kosong. 
                        Pastikan ejaan nama akurat (contoh: 'Eve' bukan 'Ive').
                        Kembalikan HANYA format JSON array persis seperti ini: [{"name": "UTA", "points": 8015}]. Tanpa teks markdown apapun.
                        """
                        
                        response = model.generate_content([prompt, img])
                        
                        res_text = response.text.strip()
                        if res_text.startswith("```"):
                            res_text = res_text.replace("```json", "").replace("```", "").strip()
                        
                        data_part = json.loads(res_text)
                        all_data.extend(data_part)
                        
                        progress_percentage = int(((i + 1) / total_files) * 100)
                        my_bar.progress(progress_percentage, text=f"Selesai membaca gambar {i+1} dari {total_files}")
                        
                        if i < total_files - 1:
                            time.sleep(4)
                    
                    if not all_data:
                        st.error("AI tidak menemukan data yang sesuai format di gambar tersebut.")
                        st.stop()

                    # OLAH DATA & GABUNGKAN POIN
                    df = pd.DataFrame(all_data)
                    df['points'] = pd.to_numeric(df['points'])
                    df['name'] = df['name'].astype(str).str.upper().str.strip()
                    
                    df_grouped = df.groupby('name', as_index=False).sum()
                    
                    df_sorted = df_grouped.sort_values(by='points', ascending=False).reset_index(drop=True)
                    df_sorted.index += 1
                    df_sorted.insert(0, 'Rank', df_sorted.index)
                    df_sorted.rename(columns={'name': 'Nama Host', 'points': 'Total Poin'}, inplace=True)
                    
                    df_sorted['Total Poin'] = df_sorted['Total Poin'].apply(lambda x: f"{int(x):,}")

                    st.success("✅ Ekstraksi dan Penggabungan Berhasil!")
                    st.dataframe(df_sorted, use_container_width=True)
                    
                    # GAMBAR TABEL PNG
                    fig_height = len(df_sorted) * 0.6 + 1.5
                    fig, ax = plt.subplots(figsize=(8, fig_height))
                    ax.axis('tight')
                    ax.axis('off')
                    ax.set_title("LAPORAN GABUNGAN POIN HARIAN", fontsize=16, weight='bold', pad=20)
                    
                    table = ax.table(
                        cellText=df_sorted.values, 
                        colLabels=df_sorted.columns, 
                        cellLoc='center', 
                        loc='center', 
                        bbox=[0, 0, 1, 1]
                    )
                    
                    table.set_fontsize(12)
                    
                    for (row, col), cell in table.get_celld().items():
                        if row == 0:
                            cell.set_text_props(weight='bold', color='white')
                            cell.set_facecolor('#2E7D32')
                        elif row % 2 == 0:
                            cell.set_facecolor('#F5F5F5')

                    buf = io.BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
                    buf.seek(0)
                    plt.close(fig)

                    st.download_button(
                        label="📥 Download Tabel Rekap Gabungan (PNG)", 
                        data=buf, 
                        file_name="Tabel_Rekap_Gabungan.png", 
                        mime="image/png"
                    )
                    
                except Exception as e:
                    st.error("Terjadi kesalahan saat memproses data.")
                    st.warning(f"Detail Error: {e}")
