import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import json
import matplotlib.pyplot as plt

st.set_page_config(page_title="AI Point Converter", layout="centered")

st.title("⚡ AI Point Converter")
st.write("Ubah screenshot data spreadsheet menjadi gambar tabel bersih seketika.")

# 1. INPUT API KEY LANGSUNG DI LAYAR
api_key_input = st.text_input("🔑 Masukkan Gemini API Key (Awalan AIza...):", type="password")

if not api_key_input:
    st.info("💡 Silakan masukkan API Key Anda untuk mengaktifkan mesin converter.")
    st.stop()

# FITUR BARU: Bersihkan spasi tersembunyi di awal dan akhir kunci secara otomatis
api_key_bersih = api_key_input.strip()

# Aktivasi AI
try:
    genai.configure(api_key=api_key_bersih)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
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
        
        with st.spinner("AI sedang membaca angka dari gambar..."):
            try:
                from PIL import Image
                for file in uploaded_files:
                    img = Image.open(file)
                    
                    # Prompt khusus pembacaan tabel
                    prompt = "Gambar ini adalah tabel rekap performa host. Di bagian atas ada nama host (seperti UTA, JENV). Di kiri ada kategori. Tugasmu: Temukan baris dengan label 'TOTAL' atau 'ADJUSTED' di bagian bawah. Pasangkan setiap nama host dengan angka mereka di baris 'TOTAL'/'ADJUSTED'. Abaikan host bernama '-' dan abaikan tabel kecil di kanan. Kembalikan HANYA JSON array seperti ini: [{\"name\": \"UTA\", \"points\": 8015}]. Tanpa markdown apapun."
                    
                    response = model.generate_content([prompt, img])
                    
                    # Pembersihan teks output JSON yang sangat ketat
                    res_text = response.text.strip()
                    if res_text.startswith("```"):
                        res_text = res_text.replace("```json", "").replace("```", "").strip()
                    
                    data_part = json.loads(res_text)
                    all_data.extend(data_part)
                
                if not all_data:
                    st.error("AI tidak menemukan data yang sesuai format di gambar tersebut.")
                    st.stop()

                # Olah dan rapikan data
                df = pd.DataFrame(all_data)
                df['points'] = pd.to_numeric(df['points'])
                df_grouped = df.groupby('name', as_index=False).sum()
                df_sorted = df_grouped.sort_values(by='points', ascending=False).reset_index(drop=True)
                df_sorted.index += 1
                df_sorted.insert(0, 'Rank', df_sorted.index)
                df_sorted.rename(columns={'name': 'Nama Host', 'points': 'Total Poin'}, inplace=True)
                
                # Format angka menjadi ribuan
                df_sorted['Total Poin'] = df_sorted['Total Poin'].apply(lambda x: f"{int(x):,}")

                # Tampilkan Tabel di Web
                st.success("✅ Konversi Berhasil!")
                st.dataframe(df_sorted, use_container_width=True)
                
                # Buat Gambar Tabel PNG menggunakan Matplotlib
                fig_height = len(df_sorted) * 0.6 + 1.5
                fig, ax = plt.subplots(figsize=(8, fig_height))
                ax.axis('tight')
                ax.axis('off')
                ax.set_title("LAPORAN POIN HARIAN", fontsize=16, weight='bold', pad=20)
                
                table = ax.table(
                    cellText=df_sorted.values, 
                    colLabels=df_sorted.columns, 
                    cellLoc='center', 
                    loc='center', 
                    bbox=[0, 0, 1, 1]
                )
                
                table.set_fontsize(12)
                
                # Pewarnaan Tabel
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
                st.download_button(
                    label="📥 Download Tabel PNG", 
                    data=buf, 
                    file_name="Tabel_Rekap.png", 
                    mime="image/png"
                )
                
            except Exception as e:
                st.error("Terjadi kesalahan saat memproses gambar.")
                st.warning(f"Detail Error: {e}")
