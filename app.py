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

# --- ANALISA MANDOR V2 (Ditingkatkan) ---
def analisa_mandor_v2(df, ticker):
    try:
        c = float(df['Close'].iloc[-1])
        h = float(df['High'].iloc[-1])
        l = float(df['Low'].iloc[-1])
        o = float(df['Open'].iloc[-1])
        v = float(df['Volume'].iloc[-1])
        v_avg = float(df['Volume'].tail(20).mean())
        
        ma20 = float(df['Close'].rolling(20).mean().iloc[-1])
        ma50 = float(df['Close'].rolling(50).mean().iloc[-1])
        
        # RSI 
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1.0 + rs)).iloc[-1]

        laporan = []
        if c > ma20 > ma50: laporan.append(f"🚀 **BULLISH:** {ticker} tren naik kuat.")
        elif c < ma20 < ma50: laporan.append(f"📉 **BEARISH:** Tekanan jual tinggi.")
        
        if v > v_avg * 1.5: laporan.append(f"🔥 **BOOM VOLUME:** Transaksi meledak!")
        if rsi > 70: laporan.append(f"⚠️ **OVERBOUGHT:** Hati-hati koreksi.")
        elif rsi < 30: laporan.append(f"✅ **OVERSOLD:** Murah, siap mantul.")
        
        return laporan
    except: return ["Analisa mandor tertunda karena data teknis belum lengkap."]

# ==========================================
# DATA & HEADER
# ==========================================
st.title("🏗️ Cuanderland Hybrid Dashboard")

try:
    res_w = supabase.table("watchlist").select("*").execute()
    list_ticker = [f"{s['ticker']} ({s['bursa']})" for s in res_w.data] if res_w.data else []
except: list_ticker = []

if not list_ticker:
    st.info("Watchlist kosong. Tambahkan saham di bawah.")
    # Kita biarkan lanjut agar user bisa isi watchlist
else:
    saham_aktif = st.selectbox("🎯 Fokus Saham:", list_ticker)
    t_aktif = saham_aktif.split(" ")[0]
    b_aktif = saham_aktif.split("(")[1].replace(")", "")
    tv_symbol = f"IDX:{t_aktif}" if b_aktif == "IDX" else t_aktif
    yf_ticker = f"{t_aktif}.JK" if b_aktif == "IDX" else t_aktif

    # --- BARIS ATAS: CHART & FUNDAMENTAL ---
    col_chart, col_fund = st.columns([3, 1])

    with col_chart:
        st.subheader(f"📈 Chart: {t_aktif}")
        html_tv = f"""
        <div style="height:600px;">
            <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
            {{ "autosize": true, "symbol": "{tv_symbol}", "interval": "D", "theme": "dark", "style": "1", "locale": "en", "studies": ["MASimple@tv-basicstudies"] }}
            </script>
        </div>
        """
        components.html(html_tv, height=600)

    with col_fund:
        st.subheader("📊 Fundamental")
        with st.spinner("Narik data..."):
            try:
                t = yf.Ticker(yf_ticker)
                inf = t.info
                # Cara tarik harga yang lebih aman untuk saham IDX
                price = inf.get('currentPrice') or inf.get('regularMarketPrice') or inf.get('previousClose') or "N/A"
                
                st.metric("Price", f"{price}")
                st.metric("PE Ratio", f"{inf.get('trailingPE', 'N/A')}")
                st.metric("PBV", f"{inf.get('priceToBook', 'N/A')}")
                st.metric("ROE", f"{inf.get('returnOnEquity', 0)*100:.1f}%" if inf.get('returnOnEquity') else "N/A")
                st.metric("Dividend", f"{inf.get('dividendYield', 0)*100:.1f}%" if inf.get('dividendYield') else "N/A")
            except:
                st.write("Server Yahoo sedang sibuk. Coba refresh beberapa saat lagi.")

    st.divider()

    # --- BARIS BAWAH: WATCHLIST & SCREENER ---
    col_watch, col_screen = st.columns([1, 1.2])

    with col_watch:
        st.subheader("⭐ Watchlist")
        with st.expander("Tambah Saham"):
            in_t = st.text_input("Kode Ticker")
            in_b = st.selectbox("Bursa", ["IDX", "NYSE"])
            if st.button("Simpan"):
                supabase.table("watchlist").insert({"ticker": in_t.upper(), "bursa": in_b}).execute()
                st.rerun()
        for item in list_ticker: st.text(f"• {item}")

    with col_screen:
        st.subheader("📡 Radar Screener")
        try:
            res_s = supabase.table("screener_results").select("*").execute()
            df_s = pd.DataFrame(res_s.data)
            if not df_s.empty:
                f_stat = st.multiselect("Saring Status:", df_s['status'].unique(), default=df_s['status'].unique())
                st.dataframe(df_s[df_s['status'].isin(f_stat)][['ticker', 'harga', 'status']], use_container_width=True, height=250)
        except: st.write("Data radar belum siap.")

    # --- AI LAB ---
    st.divider()
    st.subheader("🧪 AI Analyst Desk")
    df_ai = yf.download(yf_ticker, period="6mo", interval="1d", progress=False)
    if not df_ai.empty:
        if isinstance(df_ai.columns, pd.MultiIndex): df_ai.columns = df_ai.columns.get_level_values(0)
        
        # Grafik Lightweight (Hitam)
        c_data = []
        for idx, row in df_ai.iterrows():
            c_data.append({"time": idx.strftime('%Y-%m-%d'), "open": float(row['Open']), "high": float(row['High']), "low": float(row['Low']), "close": float(row['Close'])})
        
        lw_html = f"""
        <div id="c" style="height:400px; background:#0e1117;"></div>
        <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
        <script>
            const chart = LightweightCharts.createChart(document.getElementById('c'), {{ layout: {{ backgroundColor: '#0e1117', textColor: '#d1d4dc' }}, grid: {{ vertLines: {{ color: '#2b2b2b' }}, horzLines: {{ color: '#2b2b2b' }} }} }});
            chart.addCandlestickSeries().setData({json.dumps(c_data)});
            chart.timeScale().fitContent();
        </script>
        """
        components.html(lw_html, height=420)
        
        notes = analisa_mandor_v2(df_ai, t_aktif)
        with st.chat_message("assistant"):
            st.write(f"**Laporan Mandor untuk {t_aktif}:**")
            for n in notes: st.markdown(n)