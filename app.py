import streamlit as st
import streamlit.components.v1 as components # Modul baru untuk nempel HTML TradingView
from supabase import create_client, Client
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Cuanderland Terminal", layout="wide")

st.title("🏗️ Cuanderland Trading Terminal")
st.write("Selamat datang di Markas Besar, Bung Arsitek!")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

tab_terminal, tab_screener = st.tabs(["🖥️ Terminal Utama", "📡 Radar Screener"])

# ==========================================
# RUANG 1: TERMINAL UTAMA & CHART
# ==========================================
with tab_terminal:
    col_kiri, col_kanan = st.columns([1, 2.5])

    with col_kiri:
        st.subheader("⭐ Tambah Watchlist")
        input_ticker = st.text_input("Kode Saham (Contoh: BBCA, NVDA)")
        input_bursa = st.selectbox("Pilih Bursa", ["IDX", "NYSE"])
        
        if st.button("Simpan Saham"):
            if input_ticker:
                try:
                    supabase.table("watchlist").insert({"ticker": input_ticker.upper(), "bursa": input_bursa}).execute()
                    st.success(f"Saham {input_ticker.upper()} masuk gudang!")
                    st.rerun() 
                except Exception as e:
                    st.error(f"Gagal menyimpan data: {e}")
            else:
                st.warning("Ketik kodenya dulu, Bung!")

        st.divider()

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
        st.subheader("📈 Analisa Teknikal (Powered by TradingView)")
        
        if 'data_saham' in locals() and data_saham:
            list_ticker = [f"{s['ticker']} ({s['bursa']})" for s in data_saham]
            pilihan = st.selectbox("Pilih saham dari Watchlist untuk dianalisa:", list_ticker)
            
            ticker_pilihan = pilihan.split(" ")[0]
            bursa_pilihan = pilihan.split("(")[1].replace(")", "")
            yf_ticker = f"{ticker_pilihan}.JK" if bursa_pilihan == "IDX" else ticker_pilihan
            
            # --- MENGATUR KODE EMITEN UNTUK TRADINGVIEW ---
            if bursa_pilihan == "IDX":
                tv_symbol = f"IDX:{ticker_pilihan}"
            else:
                tv_symbol = ticker_pilihan # Untuk saham US, biarkan namanya langsung (misal: NVDA)

            # --- MENANAM WIDGET TRADINGVIEW ---
            # Perhatikan penggunaan {{ dan }} agar kodenya tidak error saat digabung dengan Python
            html_tradingview = f"""
            <!-- TradingView Widget BEGIN -->
            <div class="tradingview-widget-container" style="height:600px;width:100%">
              <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
              {{
              "allow_symbol_change": true,
              "calendar": false,
              "details": true,
              "hide_side_toolbar": false,
              "hide_top_toolbar": false,
              "hide_legend": false,
              "hide_volume": false,
              "hotlist": true,
              "interval": "D",
              "locale": "en",
              "save_image": true,
              "style": "1",
              "symbol": "{tv_symbol}",
              "theme": "dark",
              "timezone": "Asia/Jakarta",
              "backgroundColor": "#0F0F0F",
              "gridColor": "rgba(242, 242, 242, 0.06)",
              "watchlist": [],
              "withdateranges": true,
              "range": "YTD",
              "show_popup_button": true,
              "popup_height": "650",
              "popup_width": "1000",
              "autosize": true
            }}
              </script>
            </div>
            <!-- TradingView Widget END -->
            """
            
            # Menampilkan HTML murni ke dalam Streamlit
            components.html(html_tradingview, height=600)

            # --- TETAP TAMPILKAN DATA FUNDAMENTAL ---
            st.divider()
            with st.spinner("Mengambil data Fundamental dari Yahoo Finance..."):
                try:
                    st.subheader(f"📊 Fundamental {ticker_pilihan}")
                    info = yf.Ticker(yf_ticker).info
                    
                    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                    with col_f1:
                        pe = info.get('trailingPE', 0)
                        st.metric("P/E Ratio", f"{pe:.2f}x" if pe else "N/A")
                    with col_f2:
                        pbv = info.get('priceToBook', 0)
                        st.metric("PBV", f"{pbv:.2f}x" if pbv else "N/A")
                    with col_f3:
                        roe = info.get('returnOnEquity', 0)
                        st.metric("ROE", f"{roe*100:.2f}%" if roe else "N/A")
                    with col_f4:
                        div = info.get('dividendYield', 0)
                        if div: div_str = f"{div:.2f}%" if div > 1 else f"{div*100:.2f}%"
                        else: div_str = "N/A"
                        st.metric("Div. Yield", div_str)
                except:
                    st.warning("Data fundamental gagal dimuat saat ini.")

        else:
            st.info("👈 Tambahkan saham ke Watchlist terlebih dahulu.")

# ==========================================
# RUANG 2: RADAR SCREENER
# ==========================================
with tab_screener:
    st.subheader("📡 Radar Screener Otomatis")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        target_scan = st.radio("Target Scan:", ["Hanya Watchlist Saya (Live Scan)", "Seluruh Pasar IDX (Data Pabrik)"])
    with col_s2:
        kriteria = st.selectbox("Pilih Kriteria Screener:", [
            "1. Golden Cross (MA20 Nembus MA50 ke atas)",
            "2. Harga Rebound (Harga Close > MA20)",
            "3. Strong Downtrend (Harga < MA20 & MA50)"
        ])
    
    if st.button("Jalankan Radar Sekarang"):
        if target_scan == "Seluruh Pasar IDX (Data Pabrik)":
            with st.spinner("Mengambil data matang dari pabrik..."):
                try:
                    response = supabase.table("screener_results").select("*").execute()
                    data_pabrik = response.data
                    
                    if data_pabrik:
                        hasil_filter = []
                        for row in data_pabrik:
                            if "Golden Cross" in kriteria and row['status'] == "🔥 Golden Cross":
                                hasil_filter.append(row)
                            elif "Rebound" in kriteria and row['status'] == "📈 Rebound":
                                hasil_filter.append(row)
                            elif "Downtrend" in kriteria and row['status'] == "🔻 Downtrend":
                                hasil_filter.append(row)
                                
                        st.divider()
                        if len(hasil_filter) > 0:
                            st.success(f"Ditemukan {len(hasil_filter)} saham dari pabrik!")
                            df_hasil = pd.DataFrame(hasil_filter)[['ticker', 'bursa', 'harga', 'status']]
                            st.dataframe(df_hasil, use_container_width=True)
                        else:
                            st.warning("Tidak ada saham di pabrik yang memenuhi kriteria ini.")
                    else:
                        st.error("Gudang pabrik kosong. Pastikan GitHub Actions sudah berjalan.")
                except Exception as e:
                    st.error(f"Gagal mengambil data pabrik: {e}")

        else:
            if 'data_saham' in locals() and data_saham:
                hasil_scan = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                total_saham = len(data_saham)
                
                for i, saham in enumerate(data_saham):
                    ticker = saham['ticker']
                    bursa = saham['bursa']
                    yf_ticker = f"{ticker}.JK" if bursa == "IDX" else ticker
                    status_text.text(f"Menganalisa {ticker}... ({i+1}/{total_saham})")
                    try:
                        df_scan = yf.download(yf_ticker, period="3mo", progress=False)
                        if not df_scan.empty:
                            df_scan['MA20'] = df_scan['Close'].rolling(window=20).mean()
                            df_scan['MA50'] = df_scan['Close'].rolling(window=50).mean()
                            close_terakhir = df_scan['Close'].iloc[-1].item()
                            ma20_terakhir = df_scan['MA20'].iloc[-1].item()
                            ma50_terakhir = df_scan['MA50'].iloc[-1].item()
                            
                            if "Golden Cross" in kriteria and (ma20_terakhir > ma50_terakhir and close_terakhir > ma50_terakhir):
                                hasil_scan.append({"ticker": ticker, "bursa": bursa, "harga": round(close_terakhir, 2), "status": "🔥 Golden Cross"})
                            elif "Rebound" in kriteria and (close_terakhir > ma20_terakhir):
                                hasil_scan.append({"ticker": ticker, "bursa": bursa, "harga": round(close_terakhir, 2), "status": "📈 Rebound"})
                            elif "Downtrend" in kriteria and (close_terakhir < ma20_terakhir and close_terakhir < ma50_terakhir):
                                hasil_scan.append({"ticker": ticker, "bursa": bursa, "harga": round(close_terakhir, 2), "status": "🔻 Downtrend"})
                    except: pass 
                    progress_bar.progress((i + 1) / total_saham)
                
                status_text.text("Analisa Selesai!")
                st.divider()
                if len(hasil_scan) > 0:
                    st.success(f"Berhasil menemukan {len(hasil_scan)} saham dari Watchlist!")
                    st.dataframe(pd.DataFrame(hasil_scan), use_container_width=True)
                else:
                    st.warning("Tidak ada saham Watchlist yang memenuhi kriteria.")
            else:
                st.error("Watchlist masih kosong!")