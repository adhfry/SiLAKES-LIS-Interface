"""
Konfigurasi bridge PoC. Untuk PoC lokal, isi manual di bawah / lewat env var.
JANGAN commit LIS_SECRET_KEY asli ke git manapun.
"""
import os

# --- Sisi MC-200 (TCP server yang dijalankan bridge ini) -------------------
LISTEN_HOST = os.environ.get("BRIDGE_LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("BRIDGE_LISTEN_PORT", "123"))  # sesuai TCPPort di Setup200.reg

# --- Sisi SiLAKES API --------------------------------------------------------
SILAKES_BASE_URL = os.environ.get("SILAKES_BASE_URL", "https://api.silakes.labkesdasumenep.id/api")
LIS_SECRET_KEY = os.environ.get("LIS_SECRET_KEY", "")  # JANGAN hardcode di sini -- isi lewat GUI Settings (tersimpan di %APPDATA%, di luar source control)
DEVICE_CODE = os.environ.get("BRIDGE_DEVICE_CODE", "MC200")

POLL_INTERVAL_SECONDS = float(os.environ.get("BRIDGE_POLL_INTERVAL", "3.5"))  # samakan pola HS200 watcher

HTTP_TIMEOUT_SECONDS = 10
