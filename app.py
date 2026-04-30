import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Cuanderland Terminal", layout="wide")

st.title("🏗️ Cuanderland Trading Terminal")
st.write("Selamat datang di Markas Besar, Bung Arsitek!")

# --- KONEKSI KE SUPABASE ---
# Mengambil kunci rahasia dari setting Streamlit
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- FORM TAMBAH WATCHLIST ---
st.subheader("⭐ Tambah ke Watchlist")
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    input_ticker = st.text_input("Kode Saham (Contoh: BBCA, NVDA)")
with col2:
    input_bursa = st.selectbox("Pilih Bursa", ["IDX", "NYSE"])
with col3:
    st.write("") # Sekadar spasi agar tombol sejajar
    st.write("")
    if st.button("Simpan Saham"):
        if input_ticker:
            try:
                # Perintah memasukkan data ke tabel 'watchlist'
                supabase.table("watchlist").insert({
                    "ticker": input_ticker.upper(), 
                    "bursa": input_bursa
                }).execute()
                st.success(f"Saham {input_ticker.upper()} berhasil masuk ke gudang!")
            except Exception as e:
                st.error(f"Gagal menyimpan data: {e}")
        else:
            st.warning("Ketik dulu kode sahamnya, Bung!")

st.divider()

# --- MENAMPILKAN ISI WATCHLIST ---
st.subheader("📋 Daftar Saham Pantauan")

try:
    # Perintah menarik semua data dari tabel 'watchlist'
    response = supabase.table("watchlist").select("*").execute()
    data_saham = response.data
    
    if data_saham:
        # Menampilkan data dalam bentuk kolom yang rapi
        for saham in data_saham:
            st.info(f"**{saham['ticker']}** - Bursa: {saham['bursa']}")
    else:
        st.write("Belum ada saham yang dipantau. Silakan tambah di atas.")
except Exception as e:
    st.error(f"Gagal mengambil data dari database: {e}")