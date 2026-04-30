import streamlit as st
from supabase import create_client, Client
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

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

# --- MEMBUAT RUANGAN (TABS) ---
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
        st.subheader("📈 Analisa Teknikal & Trading Plan")
        
        if 'data_saham' in locals() and data_saham:
            list_ticker = [f"{s['ticker']} ({s['bursa']})" for s in data_saham]
            pilihan = st.selectbox("Pilih saham dari Watchlist untuk dianalisa:", list_ticker)
            
            ticker_pilihan = pilihan.split(" ")[0]
            bursa_pilihan = pilihan.split("(")[1].replace(")", "")
            yf_ticker = f"{ticker_pilihan}.JK" if bursa_pilihan == "IDX" else ticker_pilihan
            
            col_plan1, col_plan2, col_plan3 = st.columns(3)
            with col_plan1:
                harga_entry = st.number_input("Garis Entry", value=0.0, step=10.0)
            with col_plan2:
                harga_tp = st.number_input("Garis Take Profit", value=0.0, step=10.0)
            with col_plan3:
                harga_sl = st.number_input("Garis Stop Loss", value=0.0, step=10.0)

            with st.spinner(f"Merakit data {ticker_pilihan}..."):
                try:
                    df = yf.download(yf_ticker, period="6mo", progress=False)
                    
                    if not df.empty:
                        df['MA20'] = df['Close'].rolling(window=20).mean()
                        df['MA50'] = df['Close'].rolling(window=50).mean()

                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                        
                        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'].squeeze(), high=df['High'].squeeze(), low=df['Low'].squeeze(), close=df['Close'].squeeze(), name="Harga"), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'].squeeze(), line=dict(color='blue', width=1), name='MA20'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MA50'].squeeze(), line=dict(color='orange', width=1), name='MA50'), row=1, col=1)
                        
                        colors = ['green' if close >= open else 'red' for close, open in zip(df['Close'].squeeze(), df['Open'].squeeze())]
                        fig.add_trace(go.Bar(x=df.index, y=df['Volume'].squeeze(), marker_color=colors, name='Volume'), row=2, col=1)
                        
                        if harga_entry > 0: fig.add_hline(y=harga_entry, line_dash="dash", line_color="blue", annotation_text="ENTRY", row=1, col=1)
                        if harga_tp > 0: fig.add_hline(y=harga_tp, line_dash="solid", line_color="green", annotation_text="TAKE PROFIT", row=1, col=1)
                        if harga_sl > 0: fig.add_hline(y=harga_sl, line_dash="dashdot", line_color="red", annotation_text="STOP LOSS", row=1, col=1)

                        fig.update_layout(title=f"Grafik {ticker_pilihan}", template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20), showlegend=False, height=500)
                        fig.update_xaxes(rangeslider_visible=False) 
                        st.plotly_chart(fig, use_container_width=True)

                        st.divider()
                        st.subheader(f"📊 Fundamental & Sinyal {ticker_pilihan}")
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
                            if div:
                                div_str = f"{div:.2f}%" if div > 1 else f"{div*100:.2f}%"
                            else:
                                div_str = "N/A"
                            st.metric("Div. Yield", div_str)
                        
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
                except Exception as e:
                    st.error(f"Gagal memuat chart: {e}")
        else:
            st.info("👈 Tambahkan saham ke Watchlist terlebih dahulu.")

# ==========================================
# RUANG 2: RADAR SCREENER
# ==========================================
with tab_screener:
    st.subheader("📡 Radar Screener Otomatis")
    
    # DAFTAR SAHAM BLUECHIP UNTUK DITES SCAN
    TOP_IDX = [
        "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "GOTO", "AMMN", 
        "BREN", "TPIA", "ADRO", "UNVR", "ICBP", "INDF", "KLBF", "PGAS", 
        "PTBA", "UNTR", "ITMG", "ANTM", "MEDC", "AKRA", "BRPT", "CPIN", "POGO"
    ]

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        target_scan = st.radio("Target Scan:", ["Hanya Watchlist Saya", "Top 25 Saham IDX (Bluechips)"])
    with col_s2:
        kriteria = st.selectbox("Pilih Kriteria Screener:", [
            "1. Golden Cross (MA20 Nembus MA50 ke atas)",
            "2. Harga Rebound (Harga Close > MA20)",
            "3. Strong Downtrend (Harga < MA20 & MA50)"
        ])
    
    if st.button("Jalankan Radar Sekarang"):
        # Tentukan daftar saham yang mau di-scan berdasarkan pilihan
        if target_scan == "Hanya Watchlist Saya":
            if 'data_saham' in locals() and data_saham:
                list_scan = [{"ticker": s['ticker'], "bursa": s['bursa']} for s in data_saham]
            else:
                list_scan = []
                st.error("Watchlist masih kosong!")
        else:
            list_scan = [{"ticker": t, "bursa": "IDX"} for t in TOP_IDX]

        if len(list_scan) > 0:
            hasil_scan = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_saham = len(list_scan)
            
            for i, saham in enumerate(list_scan):
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
                        
                        # Logika Screener
                        if "Golden Cross" in kriteria:
                            if ma20_terakhir > ma50_terakhir and close_terakhir > ma50_terakhir:
                                hasil_scan.append({"Ticker": ticker, "Bursa": bursa, "Harga": round(close_terakhir, 2), "Status": "🔥 Golden Cross"})
                        
                        elif "Rebound" in kriteria:
                            if close_terakhir > ma20_terakhir:
                                hasil_scan.append({"Ticker": ticker, "Bursa": bursa, "Harga": round(close_terakhir, 2), "Status": "📈 Rebound"})
                                
                        elif "Downtrend" in kriteria:
                            if close_terakhir < ma20_terakhir and close_terakhir < ma50_terakhir:
                                hasil_scan.append({"Ticker": ticker, "Bursa": bursa, "Harga": round(close_terakhir, 2), "Status": "🔻 Downtrend"})
                                
                except Exception as e:
                    pass 
                
                progress_bar.progress((i + 1) / total_saham)
            
            status_text.text("Analisa Selesai!")
            
            st.divider()
            if len(hasil_scan) > 0:
                st.success(f"Berhasil menemukan {len(hasil_scan)} saham yang masuk kriteria!")
                df_hasil = pd.DataFrame(hasil_scan)
                st.dataframe(df_hasil, use_container_width=True)
            else:
                st.warning("Tidak ada saham yang memenuhi kriteria ini hari ini.")