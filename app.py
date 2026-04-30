import streamlit as st
from supabase import create_client, Client
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Cuanderland Terminal", layout="wide")

st.title("🏗️ Cuanderland Trading Terminal")
st.write("Selamat datang di Markas Besar, Bung Arsitek!")

# --- KONEKSI KE SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- MEMBAGI LAYAR JADI 2 KOLOM ---
# Kolom kiri (ukuran 1), Kolom kanan (ukuran 2.5)
col_kiri, col_kanan = st.columns([1, 2.5])

with col_kiri:
    # --- FORM TAMBAH WATCHLIST ---
    st.subheader("⭐ Tambah Watchlist")
    input_ticker = st.text_input("Kode Saham (Contoh: BBCA, NVDA)")
    input_bursa = st.selectbox("Pilih Bursa", ["IDX", "NYSE"])
    
    if st.button("Simpan Saham"):
        if input_ticker:
            try:
                supabase.table("watchlist").insert({
                    "ticker": input_ticker.upper(), 
                    "bursa": input_bursa
                }).execute()
                st.success(f"Saham {input_ticker.upper()} masuk gudang!")
                # Refresh paksa biar langsung muncul di bawah
                st.rerun() 
            except Exception as e:
                st.error(f"Gagal menyimpan data: {e}")
        else:
            st.warning("Ketik kodenya dulu, Bung!")

    st.divider()

    # --- MENAMPILKAN ISI WATCHLIST ---
    st.subheader("📋 Daftar Pantauan")
    try:
        response = supabase.table("watchlist").select("*").execute()
        data_saham = response.data
        
        if data_saham:
            for saham in data_saham:
                st.info(f"**{saham['ticker']}** - {saham['bursa']}")
        else:
            st.write("Belum ada saham yang dipantau.")
    except Exception as e:
        st.error(f"Gagal mengambil data dari database: {e}")

with col_kanan:
    # --- MENAMPILKAN CHART TEKNIKAL ---
    st.subheader("📈 Analisa Teknikal (Candlestick)")
    
    if 'data_saham' in locals() and data_saham:
        # Bikin dropdown otomatis dari database Watchlist Bung
        list_ticker = [f"{s['ticker']} ({s['bursa']})" for s in data_saham]
        pilihan = st.selectbox("Pilih saham dari Watchlist untuk dianalisa:", list_ticker)
        
        # Pecah teks untuk dapatkan kode murninya
        ticker_pilihan = pilihan.split(" ")[0]
        bursa_pilihan = pilihan.split("(")[1].replace(")", "")
        
        # Format khusus Yahoo Finance (saham Indo butuh akhiran .JK)
        yf_ticker = f"{ticker_pilihan}.JK" if bursa_pilihan == "IDX" else ticker_pilihan
        
        with st.spinner(f"Menarik data {ticker_pilihan}..."):
            try:
                # Tarik data harga 3 bulan terakhir
                df = yf.download(yf_ticker, period="3mo", progress=False)
                
                if not df.empty:
                    # Gambar Chart Candlestick
                    fig = go.Figure(data=[go.Candlestick(x=df.index,
                                    open=df['Open'].squeeze(),
                                    high=df['High'].squeeze(),
                                    low=df['Low'].squeeze(),
                                    close=df['Close'].squeeze())])
                    
                    fig.update_layout(
                        title=f"Pergerakan Harga {ticker_pilihan} (3 Bulan Terakhir)",
                        yaxis_title="Harga",
                        xaxis_title="Tanggal",
                        template="plotly_dark", # Tema gelap biar elegan
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    
                    # Hilangkan slider zoom otomatis di bawah chart biar rapi
                    fig.update_xaxes(rangeslider_visible=False) 
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"Data tidak ditemukan. Pastikan kode saham benar.")
            except Exception as e:
                st.error(f"Gagal memuat chart: {e}")
    else:
        st.info("👈 Tambahkan saham ke Watchlist terlebih dahulu untuk melihat Chart-nya.")