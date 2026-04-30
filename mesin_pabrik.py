import os
import time
import yfinance as yf
from supabase import create_client, Client

# Mengambil kunci dari brankas rahasia GitHub Actions
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 1. MEMBACA BUKU ABSEN (saham_idx.txt)
try:
    with open("saham_idx.txt", "r") as file:
        # Membaca setiap baris, membersihkan spasi, dan membuang baris kosong
        DAFTAR_SAHAM = [line.strip() for line in file if line.strip()]
except FileNotFoundError:
    print("ERROR: File saham_idx.txt tidak ditemukan!")
    exit()

print(f"PABRIK CUANDERLAND BEROPERASI... Total Target: {len(DAFTAR_SAHAM)} Saham")
hasil_scan = []

# 2. PROSES SCANNING
for i, ticker in enumerate(DAFTAR_SAHAM):
    yf_ticker = f"{ticker}.JK"
    print(f"[{i+1}/{len(DAFTAR_SAHAM)}] Menganalisa {ticker}...")
    
    try:
        df = yf.download(yf_ticker, period="3mo", progress=False)
        if not df.empty:
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA50'] = df['Close'].rolling(window=50).mean()
            
            close_t = float(df['Close'].iloc[-1].item())
            ma20_t = float(df['MA20'].iloc[-1].item())
            ma50_t = float(df['MA50'].iloc[-1].item())
            
            status = "Netral"
            if ma20_t > ma50_t and close_t > ma50_t:
                status = "🔥 Golden Cross"
            elif close_t > ma20_t:
                status = "📈 Rebound"
            elif close_t < ma20_t and close_t < ma50_t:
                status = "🔻 Downtrend"
                
            if status != "Netral":
                hasil_scan.append({
                    "ticker": ticker,
                    "bursa": "IDX",
                    "harga": close_t,
                    "status": status
                })
        
        # REM TANGAN: Jeda 0.5 detik per saham agar Yahoo tidak memblokir IP kita
        time.sleep(0.5) 
        
    except Exception as e:
        print(f"Gagal memproses {ticker}: {e}")

# 3. SIMPAN KE GUDANG SUPABASE
if len(hasil_scan) > 0:
    print("Membersihkan data kadaluarsa dari gudang...")
    supabase.table("screener_results").delete().eq("bursa", "IDX").execute()
    
    print(f"Menyimpan {len(hasil_scan)} saham pilihan ke Supabase...")
    supabase.table("screener_results").insert(hasil_scan).execute()
    print("PROSES SELESAI!")
else:
    print("Pasar sedang jelek. Tidak ada saham masuk kriteria.")