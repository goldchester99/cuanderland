import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Cuanderland Terminal", layout="wide")

st.title("🏗️ Cuanderland Trading Terminal")
st.write("Selamat datang di Markas Besar!")

# --- KONEKSI KE SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

tab_terminal, tab_screener = st.tabs(["🖥️ Terminal Utama", "📡 Radar Screener"])

# ==========================================
# RUANG 1: TERMINAL UTAMA & TRADINGVIEW
# ==========================================
with tab_terminal:
    col_kiri, col_kanan = st.columns([1, 2.8])

    with col_kiri:
        st.subheader("⭐ Tambah Watchlist")
        input_ticker = st.text_input("Kode Saham (Contoh: BBCA, NVDA)")
        input_bursa = st.selectbox("Pilih Bursa", ["IDX", "NYSE"])
        
        if st.button("Simpan Saham"):
            if input_ticker:
                try:
                    supabase.table("watchlist").insert({"ticker": input_ticker.upper(), "bursa": input_bursa}).execute()
                    st.success(f"Saham {input_ticker.upper()} tersimpan!")
                    st.rerun() 
                except Exception as e:
                    st.error(f"Gagal simpan: {e}")

        st.divider()
        st.subheader("📋 Daftar Pantauan")
        try:
            response = supabase.table("watchlist").select("*").execute()
            data_saham = response.data
            if data_saham:
                for saham in data_saham:
                    st.info(f"**{saham['ticker']}** - {saham['bursa']}")
            else:
                st.write("Watchlist kosong.")
        except Exception as e:
            st.error(f"DB Error: {e}")

    with col_kanan:
        if 'data_saham' in locals() and data_saham:
            list_ticker = [f"{s['ticker']} ({s['bursa']})" for s in data_saham]
            pilihan = st.selectbox("Pilih saham untuk dianalisa:", list_ticker)
            
            ticker_pilihan = pilihan.split(" ")[0]
            bursa_pilihan = pilihan.split("(")[1].replace(")", "")
            yf_ticker = f"{ticker_pilihan}.JK" if bursa_pilihan == "IDX" else ticker_pilihan
            tv_symbol = f"IDX:{ticker_pilihan}" if bursa_pilihan == "IDX" else ticker_pilihan

            st.subheader(f"📈 Analisa Teknikal: {ticker_pilihan}")

            # --- TRADINGVIEW WIDGET (TINGGI 800PX) ---
            html_tradingview = f"""
            <div class="tradingview-widget-container" style="height:800px; width:100%;">
              <div class="tradingview-widget-container__widget" style="height:100%; width:100%;"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
              {{
              "autosize": true,
              "symbol": "{tv_symbol}",
              "interval": "D",
              "timezone": "Asia/Jakarta",
              "theme": "dark",
              "style": "1",
              "locale": "en",
              "allow_symbol_change": true,
              "details": true,
              "hotlist": true,
              "save_image": true,
              "withdateranges": true,
              "range": "YTD",
              "studies": ["MASimple@tv-basicstudies", "RSI@tv-basicstudies"]
            }}
              </script>
            </div>
            """
            components.html(html_tradingview, height=800) # Pastikan tinggi sinkron[cite: 1]

            # --- FUNDAMENTAL DATA ---
            st.divider()
            try:
                info = yf.Ticker(yf_ticker).info
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                with col_f1: st.metric("P/E Ratio", f"{info.get('trailingPE', 0):.2f}x")
                with col_f2: st.metric("PBV", f"{info.get('priceToBook', 0):.2f}x")
                with col_f3: st.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%")
                with col_f4:
                    div = info.get('dividendYield', 0)
                    div_str = f"{div:.2f}%" if div > 1 else f"{div*100:.2f}%"
                    st.metric("Div. Yield", div_str)
            except: st.warning("Data fundamental terbatas.")
        else:
            st.info("👈 Isi Watchlist dulu, Bung!")

# ==========================================
# RUANG 2: RADAR SCREENER (DATA PABRIK)
# ==========================================
with tab_screener:
    st.subheader("📡 Radar Screener Otomatis")
    col_s1, col_s2 = st.columns(2)
    with col_s1: target = st.radio("Target Scan:", ["Hanya Watchlist (Live)", "Seluruh Pasar IDX (Gudang)"])
    with col_s2: kriteria = st.selectbox("Pilih Filter:", ["Golden Cross", "Rebound", "Downtrend"])
    
    if st.button("Jalankan Radar"):
        if "Gudang" in target:
            res = supabase.table("screener_results").select("*").execute()
            df_gudang = pd.DataFrame(res.data)
            if not df_gudang.empty:
                # Filter berdasarkan kata kunci status
                mask = df_gudang['status'].str.contains(kriteria, case=False)
                st.dataframe(df_gudang[mask][['ticker', 'harga', 'status']], use_container_width=True)
            else: st.warning("Gudang kosong.")
        else:
            st.write("Melakukan live scan pada watchlist...")
            # (Gunakan logika live scan seperti di versi sebelumnya)