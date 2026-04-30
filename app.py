import streamlit as st
from supabase import create_client, Client
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    # --- MENAMPILKAN CHART TEKNIKAL & TRADING PLAN ---
    st.subheader("📈 Analisa Teknikal & Trading Plan")
    
    if 'data_saham' in locals() and data_saham:
        list_ticker = [f"{s['ticker']} ({s['bursa']})" for s in data_saham]
        pilihan = st.selectbox("Pilih saham dari Watchlist untuk dianalisa:", list_ticker)
        
        ticker_pilihan = pilihan.split(" ")[0]
        bursa_pilihan = pilihan.split("(")[1].replace(")", "")
        yf_ticker = f"{ticker_pilihan}.JK" if bursa_pilihan == "IDX" else ticker_pilihan
        
        # --- INPUT TRADING PLAN ---
        st.write("**Corek-corek Target (Otomatis tampil di grafik):**")
        col_plan1, col_plan2, col_plan3 = st.columns(3)
        with col_plan1:
            harga_entry = st.number_input("Garis Entry", value=0.0, step=10.0)
        with col_plan2:
            harga_tp = st.number_input("Garis Take Profit", value=0.0, step=10.0)
        with col_plan3:
            harga_sl = st.number_input("Garis Stop Loss", value=0.0, step=10.0)

        with st.spinner(f"Merakit data {ticker_pilihan}..."):
            try:
                # 1. TARIK DATA TEKNIKAL (CHART)
                df = yf.download(yf_ticker, period="6mo", progress=False)
                
                if not df.empty:
                    df['MA20'] = df['Close'].rolling(window=20).mean()
                    df['MA50'] = df['Close'].rolling(window=50).mean()

                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                        vertical_spacing=0.03, row_heights=[0.7, 0.3])
                    
                    fig.add_trace(go.Candlestick(x=df.index,
                                    open=df['Open'].squeeze(), high=df['High'].squeeze(),
                                    low=df['Low'].squeeze(), close=df['Close'].squeeze(),
                                    name="Harga"), row=1, col=1)
                    
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'].squeeze(), line=dict(color='blue', width=1), name='MA20'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA50'].squeeze(), line=dict(color='orange', width=1), name='MA50'), row=1, col=1)
                    
                    colors = ['green' if close >= open else 'red' for close, open in zip(df['Close'].squeeze(), df['Open'].squeeze())]
                    fig.add_trace(go.Bar(x=df.index, y=df['Volume'].squeeze(), marker_color=colors, name='Volume'), row=2, col=1)
                    
                    if harga_entry > 0:
                        fig.add_hline(y=harga_entry, line_dash="dash", line_color="blue", annotation_text="ENTRY", row=1, col=1)
                    if harga_tp > 0:
                        fig.add_hline(y=harga_tp, line_dash="solid", line_color="green", annotation_text="TAKE PROFIT", row=1, col=1)
                    if harga_sl > 0:
                        fig.add_hline(y=harga_sl, line_dash="dashdot", line_color="red", annotation_text="STOP LOSS", row=1, col=1)

                    fig.update_layout(title=f"Grafik Profesional {ticker_pilihan}", template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20), showlegend=False, height=500)
                    fig.update_xaxes(rangeslider_visible=False) 
                    st.plotly_chart(fig, use_container_width=True)

                    # 2. TARIK DATA FUNDAMENTAL & SINYAL
                    st.divider()
                    st.subheader(f"📊 Fundamental & Sinyal {ticker_pilihan}")
                    
                    # Ambil info fundamental dari Yahoo Finance
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
                        st.metric("Div. Yield", f"{div*100:.2f}%" if div else "N/A")
                    
                    # Logika Sinyal Sederhana berdasarkan MA
                    last_close = df['Close'].iloc[-1].item()
                    last_ma20 = df['MA20'].iloc[-1].item()
                    last_ma50 = df['MA50'].iloc[-1].item()

                    st.write("**Kesimpulan Sinyal Teknikal (Berdasarkan Tren):**")
                    if last_close > last_ma20 and last_ma20 > last_ma50:
                        st.success("🟢 **STRONG BUY** (Harga di atas MA20 & MA50, Uptrend kuat)")
                    elif last_close > last_ma20 and last_close < last_ma50:
                        st.info("🟡 **HOLD / SPECULATIVE BUY** (Harga mulai memotong MA20, bersiap rebound)")
                    elif last_close < last_ma20 and last_close < last_ma50:
                        st.error("🔴 **STRONG SELL** (Harga di bawah MA20 & MA50, Downtrend kuat)")
                    else:
                        st.warning("⚪ **NETRAL** (Konsolidasi / Sideways)")

                else:
                    st.warning(f"Data tidak ditemukan. Pastikan kode saham benar.")
            except Exception as e:
                st.error(f"Gagal memuat chart: {e}")
    else:
        st.info("👈 Tambahkan saham ke Watchlist terlebih dahulu untuk melihat Chart-nya.")