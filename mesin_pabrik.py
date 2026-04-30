import os
import yfinance as yf
from supabase import create_client, Client

# Mengambil kunci dari brankas rahasia GitHub Actions
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Bung bisa taruh 850 saham IDX di sini. 
# Sebagai contoh, saya pasang 15 saham dulu. Sisanya tinggal ditambah pakai koma.
DAFTAR_SAHAM = [
    "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "GOTO", "AMMN", 
    "ADRO", "PGAS", "PTBA", "ITMG", "UNVR", "ICBP", "MEDC"
]

print("PABRIK CUANDERLAND BEROPERASI...")
hasil_scan = []

for ticker in DAFTAR_SAHAM:
    yf_ticker = f"{ticker}.JK"
    print(f"Menganalisa {ticker}...")
    try:
        # Tarik data
        df = yf.download(yf_ticker, period="3mo", progress=False)
        if not df.empty:
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA50'] = df['Close'].rolling(window=50).mean()
            
            # Wajib dikonversi ke float biasa agar bisa masuk ke Supabase
            close_t = float(df['Close'].iloc[-1].item())
            ma20_t = float(df['MA20'].iloc[-1].item())
            ma50_t = float(df['MA50'].iloc[-1].item())
            
            # Logika Filter
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
    except Exception as e:
        print(f"Gagal memproses {ticker}: {e}")

# Proses Simpan ke Gudang
if len(hasil_scan) > 0:
    print("Membersihkan data kadaluarsa dari gudang...")
    # Hapus data lama agar tidak dobel
    supabase.table("screener_results").delete().eq("bursa", "IDX").execute()
    
    print(f"Menyimpan {len(hasil_scan)} saham pilihan ke Supabase...")
    supabase.table("screener_results").insert(hasil_scan).execute()
    print("PROSES SELESAI!")
else:
    print("Pasar sedang jelek. Tidak ada saham masuk kriteria.")