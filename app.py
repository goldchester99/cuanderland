import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import yfinance as yf
import pandas as pd
import json

st.set_page_config(page_title="Cuanderland Hybrid Terminal", layout="wide")

st.title("🏗️ Cuanderland Hybrid Terminal")
st.write("Terminal Trading Terintegrasi: Advanced Widget + AI Lightweight Lab.")

# --- KONEKSI KE SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# TAB MENU
tab_terminal, tab_screener, tab_ai_lab = st.tabs(["🖥️ Terminal Utama", "📡 Radar Screener", "🧪 AI Chart Lab"])

# --- LOAD WATCHLIST UNTUK DROPDOWN ---
try:
    response = supabase.table("watchlist").select("*").execute()
    data_saham = response.data
    list_ticker = [f"{s['ticker']} ({s['bursa']})" for s in data_saham] if data_saham else []
except:
    list_ticker = []

# ==========================================
# TAB 1: TERMINAL UTAMA (ADVANCED WIDGET)
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
        if list_ticker:
            for item in list_ticker:
                st.info(f"**{item}**")
        else:
            st.write("Watchlist kosong.")

    with col_kanan:
        if list_ticker:
            pilihan = st.selectbox("Pilih Saham (Deep Analysis):", list_ticker, key="tab1_select")
            ticker = pilihan.split(" ")[0]
            bursa = pilihan.split("(")[1].replace(")", "")
            tv_symbol = f"IDX:{ticker}" if bursa == "IDX" else ticker

            st.subheader(f"📈 Analisa Teknikal: {ticker}")
            html_adv = f"""
            <div style="height:750px;">
                <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
                {{
                  "autosize": true, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Asia/Jakarta",
                  "theme": "dark", "style": "1", "locale": "en", "hide_side_toolbar": false,
                  "allow_symbol_change": true, "save_image": true, "details": true, "hotlist": true,
                  "studies": ["MASimple@tv-basicstudies", "RSI@tv-basicstudies"]
                }}
                </script>
            </div>
            """
            components.html(html_adv, height=750)
        else:
            st.info("👈 Isi Watchlist dulu di kolom kiri, Bung!")

# ==========================================
# TAB 2: RADAR SCREENER (DATA PABRIK)
# ==========================================
with tab_screener:
    st.subheader("📡 Radar Hasil Scan Pabrik")
    try:
        res = supabase.table("screener_results").select("*").execute()
        if res.data:
            df_res = pd.DataFrame(res.data)
            st.dataframe(df_res[['ticker', 'harga', 'status']], use_container_width=True)
        else:
            st.warning("Belum ada data di gudang. Tunggu jadwal scan sore hari.")
    except:
        st.error("Gagal terhubung ke database gudang.")

# ==========================================
# TAB 3: AI CHART LAB (FIXED ERROR)
# ==========================================
with tab_ai_lab:
    st.subheader("🧪 AI Lightweight Lab")
    
    if list_ticker:
        pilihan_ai = st.selectbox("Pilih Saham (AI Analysis):", list_ticker, key="tab3_select")
        ticker_ai = pilihan_ai.split(" ")[0]
        yf_ticker = f"{ticker_ai}.JK" if "IDX" in pilihan_ai else ticker_ai
        
        with st.spinner(f"Merakit data {ticker_ai}..."):
            df_ai = yf.download(yf_ticker, period="6mo", interval="1d", progress=False)
            
            if not df_ai.empty:
                # --- PERBAIKAN ERROR: Flatten Multi-Index Columns ---
                if isinstance(df_ai.columns, pd.MultiIndex):
                    df_ai.columns = df_ai.columns.get_level_values(0)
                
                # Format data ke JSON untuk Lightweight Charts
                chart_data = []
                for index, row in df_ai.iterrows():
                    chart_data.append({
                        "time": index.strftime('%Y-%m-%d'),
                        "open": float(row['Open']),
                        "high": float(row['High']),
                        "low": float(row['Low']),
                        "close": float(row['Close'])
                    })
                
                # Visualisasi Lightweight Charts
                html_lw = f"""
                <div id="chart" style="height:500px; width:100%;"></div>
                <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
                <script>
                    const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
                        layout: {{ backgroundColor: '#0F0F0F', textColor: '#DDD' }},
                        grid: {{ vertLines: {{ color: '#222' }}, horzLines: {{ color: '#222' }} }},
                        timeScale: {{ borderColor: '#444' }}
                    }});
                    const candleSeries = chart.addCandlestickSeries();
                    candleSeries.setData({json.dumps(chart_data)});
                    chart.timeScale().fitContent();
                </script>
                """
                components.html(html_lw, height=520)
                
                # Analisa Singkat AI
                st.divider()
                st.info(f"🤖 **AI Analysis for {ticker_ai}:**")
                last_price = float(df_ai['Close'].iloc[-1])
                prev_price = float(df_ai['Close'].iloc[-2])
                change = ((last_price - prev_price) / prev_price) * 100
                st.write(f"Harga penutupan terakhir: **{last_price:,.0f}** ({change:+.2f}%)")
            else:
                st.error("Gagal menarik data dari Yahoo Finance.")
    else:
        st.info("Watchlist kosong.")