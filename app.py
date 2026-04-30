import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import yfinance as yf
import pandas as pd
import json
import numpy as np

st.set_page_config(page_title="Cuanderland Dashboard", layout="wide")

# --- KONEKSI SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- FUNGSI ANALISA AI (SI MANDOR) ---
def analisa_mandor(df, ticker):
    # Flatten columns jika multi-index
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    last_close = float(df['Close'].iloc[-1])
    ma20 = float(df['Close'].rolling(20).mean().iloc[-1])
    ma50 = float(df['Close'].rolling(50).mean().iloc[-1])
    
    # Simple RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1,0 + rs)).iloc[-1]

    # Logika Komentar
    komentar = []
    if last_close > ma20 > ma50:
        komentar.append(f"🟢 **STRENGHT:** {ticker} dalam tren naik (Uptrend) yang kokoh. Posisi harga di atas MA20 dan MA50.")
    elif last_close < ma20 < ma50:
        komentar.append(f"🔴 **BEWARE:** Tren sedang turun tajam. Hindari 'tangkap pisau jatuh' sebelum ada konfirmasi rebound.")
    
    if rsi > 70: komentar.append(f"⚠️ **OVERBOUGHT:** RSI di level {rsi:.0f}. Sudah terlalu jenuh beli, rawan aksi ambil untung (profit taking).")
    elif rsi < 30: komentar.append(f"✅ **OVERSOLD:** RSI di level {rsi:.0f}. Sudah jenuh jual, ada potensi rebound teknikal.")
    else: komentar.append(f"⚖️ **NEUTRAL:** RSI stabil di {rsi:.0f}, pergerakan harga masih mencari arah.")

    return komentar

# ==========================================
# HEADER & LOGIC DATA
# ==========================================
st.title("🏗️ Cuanderland Hybrid Dashboard")

try:
    res_w = supabase.table("watchlist").select("*").execute()
    data_w = res_w.data
    list_ticker = [f"{s['ticker']} ({s['bursa']})" for s in data_w] if data_w else []
except: list_ticker = []

# Pilih Saham Aktif untuk Dashboard
if list_ticker:
    saham_aktif = st.selectbox("🎯 Fokus Saham:", list_ticker)
    t_aktif = saham_aktif.split(" ")[0]
    b_aktif = saham_aktif.split("(")[1].replace(")", "")
    tv_symbol = f"IDX:{t_aktif}" if b_aktif == "IDX" else t_aktif
    yf_ticker = f"{t_aktif}.JK" if b_aktif == "IDX" else t_aktif
else:
    st.warning("Tambahkan saham ke Watchlist di kuadran bawah!")
    st.stop()

# ==========================================
# BARIS ATAS: CHART & FUNDAMENTAL
# ==========================================
col_chart, col_fund = st.columns([3, 1])

with col_chart:
    st.subheader(f"📈 Chart: {t_aktif}")
    html_tv = f"""
    <div style="height:600px;">
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
        {{
          "autosize": true, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Asia/Jakarta",
          "theme": "dark", "style": "1", "locale": "en", "hide_side_toolbar": false,
          "allow_symbol_change": true, "details": false, "hotlist": false,
          "studies": ["MASimple@tv-basicstudies", "RSI@tv-basicstudies"]
        }}
        </script>
    </div>
    """
    components.html(html_tv, height=600)

with col_fund:
    st.subheader("📊 Fundamental")
    try:
        info = yf.Ticker(yf_ticker).info
        st.metric("Price", f"{info.get('currentPrice', 'N/A')}")
        st.metric("P/E Ratio", f"{info.get('trailingPE', 0):.2f}x")
        st.metric("PBV", f"{info.get('priceToBook', 0):.2f}x")
        st.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%")
        st.metric("Div. Yield", f"{info.get('dividendYield', 0)*100:.2f}%")
    except: st.write("Data fundamental tidak tersedia.")

st.divider()

# ==========================================
# BARIS BAWAH: WATCHLIST & SCREENER
# ==========================================
col_watch, col_screen = st.columns([1, 1.2])

with col_watch:
    st.subheader("⭐ Watchlist Manager")
    with st.expander("➕ Tambah Saham Baru"):
        in_t = st.text_input("Kode (Ticker)")
        in_b = st.selectbox("Bursa", ["IDX", "NYSE"])
        if st.button("Simpan"):
            supabase.table("watchlist").insert({{"ticker": in_t.upper(), "bursa": in_b}}).execute()
            st.success("Tersimpan!")
            st.rerun()
    
    # List Ticker Sederhana
    for item in list_ticker:
        st.text(f"• {item}")

with col_screen:
    st.subheader("📡 Interactive Screener")
    # Bagian ini yang Bung tanyakan "Gimana mau screening?"
    try:
        res_s = supabase.table("screener_results").select("*").execute()
        df_s = pd.DataFrame(res_s.data)
        
        if not df_s.empty:
            # Filter Interaktif
            filter_status = st.multiselect("Saring Status:", df_s['status'].unique(), default=df_s['status'].unique())
            search_t = st.text_input("Cari Ticker...")
            
            # Aplikasi Filter
            df_filtered = df_s[df_s['status'].isin(filter_status)]
            if search_t:
                df_filtered = df_filtered[df_filtered['ticker'].str.contains(search_t.upper())]
            
            st.dataframe(df_filtered[['ticker', 'harga', 'status']], use_container_width=True, height=300)
        else:
            st.info("Pabrik belum scan hari ini.")
    except: st.error("Koneksi Radar terputus.")

# ==========================================
# AI ANALYST DESK (DETAILED LAB)
# ==========================================
st.divider()
st.subheader("🧪 AI Analyst Desk (Detailed Lab)")

df_ai = yf.download(yf_ticker, period="6mo", interval="1d", progress=False)
if not df_ai.empty:
    # Flatten Columns Fix
    if isinstance(df_ai.columns, pd.MultiIndex):
        df_ai.columns = df_ai.columns.get_level_values(0)

    # Lightweight Chart Fix (Hitam & Transparan)
    c_data = []
    for idx, row in df_ai.iterrows():
        c_data.append({{"time": idx.strftime('%Y-%m-%d'), "open": float(row['Open']), "high": float(row['High']), "low": float(row['Low']), "close": float(row['Close'])}})
    
    html_lw = f"""
    <div id="chart" style="height:400px; width:100%; background-color: #0e1117;"></div>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
            width: document.getElementById('chart').offsetWidth,
            height: 400,
            layout: {{ backgroundColor: '#0e1117', textColor: '#d1d4dc' }},
            grid: {{ vertLines: {{ color: 'rgba(42, 46, 57, 0.5)' }}, horzLines: {{ color: 'rgba(42, 46, 57, 0.5)' }} }},
            timeScale: {{ borderColor: 'rgba(197, 203, 206, 0.8)' }},
        }});
        const candleSeries = chart.addCandlestickSeries({{ upColor: '#26a69a', downColor: '#ef5350', borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350' }});
        candleSeries.setData({json.dumps(c_data)});
        chart.timeScale().fitContent();
    </script>
    """
    components.html(html_lw, height=420)
    
    # Komentar AI yang Lebih Cerdas
    notes = analisa_mandor(df_ai, t_aktif)
    with st.chat_message("assistant"):
        st.write(f"**Analisa Teknis Mandor untuk {t_aktif}:**")
        for n in notes:
            st.write(n)