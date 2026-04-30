import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import yfinance as yf
import pandas as pd
import json

st.set_page_config(page_title="Cuanderland Dashboard", layout="wide")

# --- KONEKSI SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- FUNGSI ANALISA MANDOR (Cerewet Edition) ---
def analisa_mandor_v2(df, ticker):
    # Ambil data terakhir
    c = float(df['Close'].iloc[-1])
    h = float(df['High'].iloc[-1])
    l = float(df['Low'].iloc[-1])
    o = float(df['Open'].iloc[-1])
    v = float(df['Volume'].iloc[-1])
    v_avg = float(df['Volume'].tail(20).mean())
    
    ma20 = float(df['Close'].rolling(20).mean().iloc[-1])
    ma50 = float(df['Close'].rolling(50).mean().iloc[-1])
    
    # Kalkulasi RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1.0 + rs)).iloc[-1]

    laporan = []
    
    # 1. Analisa Tren
    if c > ma20 > ma50:
        laporan.append(f"🚀 **BULLISH STRONG:** {ticker} sedang terbang tinggi di atas MA20 dan MA50. Tren naik sangat kuat.")
    elif c > ma20 and ma20 < ma50:
        laporan.append(f"📈 **POTENTIAL REVERSAL:** Harga mulai menembus MA20 ke atas. Ada tanda-tanda pembalikan arah!")
    elif c < ma20 < ma50:
        laporan.append(f"📉 **BEARISH:** Tren turun parah. Harga masih di bawah tekanan MA20.")

    # 2. Analisa Volume
    if v > v_avg * 1.5:
        laporan.append(f"🔥 **HIGH VOLUME:** Transaksi hari ini meledak {v/v_avg:.1f}x lipat dari biasanya. Ada akumulasi atau distribusi besar!")
    
    # 3. Analisa Candlestick Sederhana
    if c > o and (h - c) < (c - o) * 0.2:
        laporan.append(f"🟢 **SOLID GREEN:** Buyer mendominasi penuh hari ini tanpa perlawanan berarti.")
    elif c < o and (c - l) < (o - c) * 0.2:
        laporan.append(f"🔴 **SOLID RED:** Seller menang telak. Tekanan jual sangat masif.")

    # 4. Analisa Momentum (RSI)
    if rsi > 70: laporan.append(f"⚠️ **OVERBOUGHT:** RSI {rsi:.0f} (Jenuh Beli). Hati-hati rawan profit taking!")
    elif rsi < 30: laporan.append(f"✅ **OVERSOLD:** RSI {rsi:.0f} (Jenuh Jual). Harga sudah diskon besar, siap-siap pantulan!")
    
    return laporan

# ==========================================
# HEADER & WATCHLIST
# ==========================================
st.title("🏗️ Cuanderland Hybrid Dashboard")

try:
    res_w = supabase.table("watchlist").select("*").execute()
    data_w = res_w.data
    list_ticker = [f"{s['ticker']} ({s['bursa']})" for s in data_w] if data_w else []
except: list_ticker = []

if list_ticker:
    saham_aktif = st.selectbox("🎯 Fokus Saham:", list_ticker)
    t_aktif = saham_aktif.split(" ")[0]
    b_aktif = saham_aktif.split("(")[1].replace(")", "")
    tv_symbol = f"IDX:{t_aktif}" if b_aktif == "IDX" else t_aktif
    yf_ticker = f"{t_aktif}.JK" if b_aktif == "IDX" else t_aktif
else:
    st.warning("Tambahkan saham di kuadran bawah!")
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
        {{ "autosize": true, "symbol": "{tv_symbol}", "interval": "D", "theme": "dark", "style": "1", "locale": "en", "studies": ["MASimple@tv-basicstudies", "RSI@tv-basicstudies"] }}
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
    with st.expander("➕ Tambah Saham"):
        in_t = st.text_input("Kode")
        in_b = st.selectbox("Bursa", ["IDX", "NYSE"])
        if st.button("Simpan"):
            supabase.table("watchlist").insert({"ticker": in_t.upper(), "bursa": in_b}).execute()
            st.rerun()
    for item in list_ticker: st.text(f"• {item}")

with col_screen:
    st.subheader("📡 Interactive Screener")
    try:
        res_s = supabase.table("screener_results").select("*").execute()
        df_s = pd.DataFrame(res_s.data)
        if not df_s.empty:
            f_status = st.multiselect("Filter Status:", df_s['status'].unique(), default=df_s['status'].unique())
            df_f = df_s[df_s['status'].isin(f_status)]
            st.dataframe(df_f[['ticker', 'harga', 'status']], use_container_width=True, height=250)
    except: st.error("Koneksi Screener bermasalah.")

# ==========================================
# AI ANALYST DESK (DETAILED & FIXED)
# ==========================================
st.divider()
st.subheader("🧪 AI Analyst Desk (Detailed Lab)")

with st.spinner("Mandor sedang menghitung..."):
    df_ai = yf.download(yf_ticker, period="6mo", interval="1d", progress=False)
    
    if not df_ai.empty:
        # --- FIX: FLATTEN MULTI-INDEX ---
        if isinstance(df_ai.columns, pd.MultiIndex):
            df_ai.columns = df_ai.columns.get_level_values(0)
        
        # --- FIX: ENSURE SCALAR VALUES FOR JSON ---
        chart_data = []
        for idx, row in df_ai.iterrows():
            chart_data.append({
                "time": idx.strftime('%Y-%m-%d'),
                "open": float(row['Open'].item() if hasattr(row['Open'], 'item') else row['Open']),
                "high": float(row['High'].item() if hasattr(row['High'], 'item') else row['High']),
                "low": float(row['Low'].item() if hasattr(row['Low'], 'item') else row['Low']),
                "close": float(row['Close'].item() if hasattr(row['Close'], 'item') else row['Close'])
            })
        
        html_lw = f"""
        <div id="chart" style="height:400px; width:100%; background-color:#0e1117;"></div>
        <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
        <script>
            const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
                layout: {{ backgroundColor: '#0e1117', textColor: '#d1d4dc' }},
                grid: {{ vertLines: {{ color: '#2b2b2b' }}, horzLines: {{ color: '#2b2b2b' }} }},
            }});
            const candleSeries = chart.addCandlestickSeries();
            candleSeries.setData({json.dumps(chart_data)});
            chart.timeScale().fitContent();
        </script>
        """
        components.html(html_lw, height=420)
        
        # Komentar Mandor yang Lebih Detail
        notes = analisa_mandor_v2(df_ai, t_aktif)
        with st.chat_message("assistant"):
            st.write(f"**Laporan Teknis Mandor untuk {t_aktif}:**")
            for n in notes:
                st.markdown(n)
    else:
        st.error("Gagal menarik data untuk analisa AI.")