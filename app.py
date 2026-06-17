import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import json
import matplotlib.pyplot as plt

st.set_page_config(page_title="AI Point Converter", layout="centered")

st.title("⚡ AI Point Converter")
st.write("Ubah screenshot data spreadsheet menjadi gambar tabel bersih seketika.")

# 1. INPUT API KEY LANGSUNG DI LAYAR (Lebih Mudah)
api_key = st.text_input("🔑 Masukkan Gemini API Key (Awalan AIza...):", type="password")

if not api_key:
    st.warning("Silakan masukkan API Key Anda untuk mengaktifkan mesin converter.")
    st.stop()

# Aktivasi AI
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Kunci tidak valid: {e}")
    st.stop()

# 2. UPLOAD GAMBAR
st.markdown("---")
uploaded_files = st.file_uploader("📸 Upload Screenshot Tabel:", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# 3. PROSES KONVERSI & EXPORT
if uploaded_files:
    if st.button("🚀 Convert Sekarang", type="primary", use_container_width=True):
        all_data = []
        
        with st.spinner("Membaca angka dari gambar..."):
            try:
                from PIL import Image
                for file in uploaded_files:
                    img = Image.open(file)
                    prompt = "Gambar ini adalah tabel rekap performa host. Di bagian atas ada nama host (seperti UTA, JENV). Di kiri ada kategori. Tugasmu: Temukan baris dengan label 'TOTAL' atau 'ADJUSTED' di bagian bawah. Pasangkan setiap nama host dengan angka mereka di baris 'TOTAL'/'ADJUSTED'. Abaikan host bernama '-' dan abaikan tabel kecil di kanan. Kembalikan HANYA JSON array seperti ini: [{\"name\": \"UTA\", \"points\": 8015}]. Tanpa markdown."
                    
                    response = model.generate_content([prompt, img])
                    res_text = response.text.strip().replace("```json", "").replace("```", "").strip()
                    
                    data_part = json.loads(res_text)
                    all_data.extend(data_part)
                
                # Olah data
                df = pd.DataFrame(all_data)
                df['points'] = pd.to_numeric(df['points'])
                df_grouped = df.groupby('name', as_index=False).sum()
                df_sorted = df_grouped.sort_values(by='points', ascending=False).reset_index(drop=True)
                df_sorted.index += 1
                df_sorted.insert(0, 'Rank', df_sorted.index)
                df_sorted.rename(columns={'name': 'Nama Host', 'points': 'Total Poin'}, inplace=True)
                df_sorted['Total Poin'] = df_sorted['Total Poin'].apply(lambda x: f"{int(x):,}")

                # Tampilkan Tabel
                st.success("Konversi Berhasil!")
                st.dataframe(df_sorted, use_container_width=True)
                
                # Gambar Tabel PNG
                fig_height = len(df_sorted) * 0.6 + 1.5
                fig, ax = plt.subplots(figsize=(8, fig_height))
                ax.axis('tight')
                ax.axis('off')
                ax.set_title("LAPORAN POIN HARIAN", fontsize=16, weight='bold', pad=20)
                
                table = ax.table(cellText=df_sorted.values, colLabels=df_sorted.columns, cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
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

                # Tombol Download PNG
                st.download_button("📥 Download Tabel PNG", data=buf, file_name="Tabel_Rekap.png", mime="image/png")
                
            except Exception as e:
                st.error("Terjadi kesalahan saat membaca gambar. Pastikan gambar jelas.")
                st.write(e)
