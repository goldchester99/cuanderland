import os
import time
import requests
import yfinance as yf
from supabase import create_client, Client

# Mengambil kunci dari brankas rahasia GitHub Actions
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def kirim_telegram(pesan):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
        try:
            requests.post(api_url, json=payload)
        except Exception as e:
            print("Gagal kirim Telegram:", e)

# 1. MEMBACA BUKU ABSEN (saham_idx.txt)
try:
    with open("saham_idx.txt", "r") as file:
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
        
        # Jeda 0.5 detik per saham
        time.sleep(0.5) 
        
    except Exception as e:
        print(f"Gagal memproses {ticker}: {e}")

# 3. SIMPAN KE GUDANG & KIRIM LAPORAN TELEGRAM
if len(hasil_scan) > 0:
    print("Membersihkan data kadaluarsa dari gudang...")
    supabase.table("screener_results").delete().eq("bursa", "IDX").execute()
    
    print(f"Menyimpan {len(hasil_scan)} saham pilihan ke Supabase...")
    supabase.table("screener_results").insert(hasil_scan).execute()
    
    # Merangkum Laporan untuk Telegram
    jml_gc = sum(1 for s in hasil_scan if s["status"] == "🔥 Golden Cross")
    jml_rebound = sum(1 for s in hasil_scan if s["status"] == "📈 Rebound")
    jml_downtrend = sum(1 for s in hasil_scan if s["status"] == "🔻 Downtrend")

    pesan = f"🏗️ **LAPORAN HARIAN MANDOR CUANDERLAND** 🏗️\n\n"
    pesan += f"Pabrik selesai memindai *{len(DAFTAR_SAHAM)} saham IDX*.\n"
    pesan += f"Ditemukan *{len(hasil_scan)} saham* masuk radar hari ini:\n\n"
    pesan += f"🔥 Golden Cross: {jml_gc} saham\n"
    pesan += f"📈 Rebound: {jml_rebound} saham\n"
    pesan += f"🔻 Downtrend: {jml_downtrend} saham\n\n"
    pesan += f"Segera buka Terminal Cuanderland untuk eksekusi, Bung!"
    
    kirim_telegram(pesan)
    print("PROSES SELESAI!")
else:
    pesan_kosong = f"🏗️ **LAPORAN HARIAN MANDOR CUANDERLAND** 🏗️\n\nPabrik selesai memindai *{len(DAFTAR_SAHAM)} saham IDX*.\nPasar sedang jelek, tidak ada saham yang memenuhi kriteria hari ini."
    kirim_telegram(pesan_kosong)
    print("Pasar sedang jelek. Laporan kosong terkirim.")