import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import json
import pandas as pd
import io

# Konfigurasi Halaman Web
st.set_page_config(page_title="AI Point Recaper", layout="centered")
st.title("📊 Aplikasi Rekap Poin Otomatis AI")
st.write("Ubah screenshot data poin menjadi gambar laporan akhir secara instan.")

# 1. INPUT API KEY & PENGATURAN (Sidebar)
st.sidebar.header("🔧 Pengaturan Aplikasi")
api_key_input = st.sidebar.text_input("Masukkan Gemini API Key:", type="password")

# Petunjuk jika API Key belum diisi
if not api_key_input:
    st.info("💡 Silakan masukkan Gemini API Key Anda di sidebar sebelah kiri untuk memulai.")
    st.stop()

# Aktivasi AI Gemini
genai.configure(api_key=api_key_input)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. AREA UPLOAD FILE
st.subheader("📁 Upload Berkas")
screenshot_file = st.file_uploader("1. Upload Screenshot Poin Harian (Format PNG/JPG):", type=["png", "jpg", "jpeg"])
template_file = st.file_uploader("2. Upload Gambar Background Laporan / Template (Format PNG/JPG):", type=["png", "jpg", "jpeg"])

# Jalankan proses jika kedua file sudah diupload
if screenshot_file and template_file:
    if st.button("🚀 Proses & Hitung Poin Otomatis"):
        with st.spinner("AI sedang membaca gambar dan menghitung poin..."):
            try:
                # Konversi file upload menjadi objek gambar PIL
                raw_screenshot = Image.open(screenshot_file)
                
                # Prompt instruksi khusus untuk AI Vision
                prompt = """
                Analisis gambar screenshot live streaming berikut. 
                Ekstrak semua nama host dan jumlah poin atau Challenge Gift (CG) yang mereka peroleh.
                Pastikan akurasi ejaan nama sangat tepat (contoh: perhatikan nama seperti 'Eve', jangan sampai tertulis 'Ive').
                Kembalikan hasilnya HANYA dalam format JSON array of objects seperti ini tanpa teks tambahan apapun:
                [{"name": "NamaHost", "points": 150000}]
                Pastikan output bersih dari tanda ```json atau teks pembuka/penutup lainnya agar bisa langsung diproses sistem.
                """
                
                # Kirim ke Gemini AI
                response = model.generate_content([prompt, raw_screenshot])
                response_text = response.text.strip()
                
                # Bersihkan response jika AI tidak sengaja memberikan markdown formatting
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                response_text = response_text.strip()
                
                # Parsing teks menjadi data tabel Python
                data_poin = json.loads(response_text)
                
                # Urutkan berdasarkan poin tertinggi (Ranking)
                df = pd.DataFrame(data_poin)
                df['points'] = pd.to_numeric(df['points'])
                df = df.sort_values(by='points', ascending=False).reset_index(drop=True)
                
                st.success("✅ AI Berhasil Membaca & Menghitung Data!")
                
                # Tampilkan tabel preview di web
                st.subheader("📋 Preview Data Tabel")
                st.dataframe(df, use_container_width=True)
                
                # 3. PROSES GENERATE GAMBAR OUTPUT (Pillow)
                st.subheader("🖼️ Hasil Gambar Laporan Akhir")
                
                # Buka gambar template latar belakang
                report_image = Image.open(template_file).convert("RGB")
                draw = ImageDraw.Draw(report_image)
                
                # Menggunakan default font bawaan Pillow yang mendukung pengaturan ukuran otomatis
                try:
                    font_title = ImageFont.load_default(size=32)
                    font_content = ImageFont.load_default(size=24)
                except:
                    font_title = ImageFont.load_default()
                    font_content = ImageFont.load_default()
                
                # Koordinat awal penulisan teks di atas gambar laporan
                # Sesuaikan X dan Y ini dengan ruang kosong pada gambar template Anda
                start_x = 50
                start_y = 150
                line_height = 40
                
                # Tulis Judul Laporan di gambar
                draw.text((start_x, start_y - 60), "LAPORAN PERFORMA TIM", fill=(255, 255, 255), font=font_title)
                
                # Tulis data host satu per satu ke gambar
                for index, row in df.iterrows():
                    ranking_text = f"Rank {index+1}: {row['name']} - {row['points']:,} Poin"
                    
                    # Cetak teks ke gambar template (Warna putih: 255,255,255)
                    draw.text((start_x, start_y), ranking_text, fill=(255, 255, 255), font=font_content)
                    start_y += line_height
                
                # Tampilkan hasil gambar akhir di halaman web
                st.image(report_image, caption="Gambar Laporan Siap Kirim", use_container_width=True)
                
                # Sediakan Tombol Download Gambar
                img_byte_arr = io.BytesIO()
                report_image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                st.download_button(
                    label="📥 Download Gambar Laporan",
                    data=img_byte_arr,
                    file_name="laporan_poin_harian.png",
                    mime="image/png"
                )
                
            except Exception as e:
                st.error(f"Terjadi kesalahan sistem: {e}")
                st.warning("Tips: Pastikan screenshot yang diupload memiliki tulisan angka poin yang jelas.")