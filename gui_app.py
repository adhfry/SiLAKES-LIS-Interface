"""
Entry point aplikasi desktop "SiLAKES LIS Interface".

Membungkus service.py (logic ASTM bridge yang sudah tervalidasi live thd
MC-200 sungguhan) dalam window native (pywebview) dgn UI Vue 3 modern.

ARSITEKTUR KOMUNIKASI JS <-> PYTHON (PENTING):
Awalnya pakai js_api bawaan pywebview (window.pywebview.api.*), tapi
TERBUKTI TIDAK ANDAL di kombinasi pywebview+WebView2+Windows ini -- gagal
konsisten ("belum siap") baik di exe hasil PyInstaller MAUPUN dijalankan
langsung via `python gui_app.py`, sementara evaluate_js (arah Python->JS)
tetap normal. Daripada terus menambal mekanisme yang rapuh, arah JS->Python
sekarang pakai HTTP LOKAL BIASA (server kecil di 127.0.0.1, lewat fetch() di
sisi JS) -- mekanisme yang jauh lebih teruji & tidak bergantung reflection
binding pywebview. pywebview cuma dipakai utk render window + evaluate_js
push (arah Python->JS, yang terbukti reliable).

Jalankan dev:   python gui_app.py            (load dari Vite dev server :5173)
Jalankan prod:  python gui_app.py --prod      (load dari gui/dist/index.html, hasil `npm run build`)
Build ke exe:   lihat build_exe.py / SiLAKES-LIS-Interface.spec
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
from datetime import datetime

import requests
import webview
from bottle import Bottle, request as bottle_request, response as bottle_response, run as bottle_run

import service
import settings as _settings

log = logging.getLogger("gui_app")

API_HOST = "127.0.0.1"
API_PORT = 8765

SUCCESS_HINTS = ("sukses", "berhasil")

# Bug kosmetik dikenal di pywebview + WebView2 di Windows: introspeksi
# window.native.AccessibilityObject kadang rekursif tak terbatas dan
# menghasilkan 1 baris log super panjang ("...Empty.Empty.Empty...").
# Tidak merusak fungsi apa pun, tapi jangan sampai membanjiri log.
_MAX_LOG_MESSAGE_CHARS = 4000


class TruncateNoiseFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if len(msg) > _MAX_LOG_MESSAGE_CHARS:
            record.msg = msg[:200] + f"... [dipotong, pesan asli {len(msg)} char -- kemungkinan bug internal pywebview, aman diabaikan]"
            record.args = ()
        return True


def _infer_level(record: logging.LogRecord) -> str:
    level = record.levelname.lower()
    if level == "critical":
        level = "error"
    if level == "info":
        msg_lower = record.getMessage().lower()
        if any(h in msg_lower for h in SUCCESS_HINTS):
            return "success"
    if level not in ("debug", "info", "warning", "error"):
        return "info"
    return level


class LogBridgeHandler(logging.Handler):
    """Forward setiap log record ke frontend Vue via evaluate_js (Python->JS, reliable)."""

    def __init__(self, window_getter):
        super().__init__()
        self._window_getter = window_getter

    def emit(self, record: logging.LogRecord):
        window = self._window_getter()
        if not window:
            return
        try:
            message = self.format(record)
            level = _infer_level(record)
            ts = datetime.fromtimestamp(record.created).isoformat()
            js = (
                "window.__bridgeOnLog && window.__bridgeOnLog("
                f"{json.dumps(level)}, {json.dumps(message)}, {json.dumps(ts)})"
            )
            window.evaluate_js(js)
        except Exception:
            pass


class BridgeApi:
    """Logic inti -- dipanggil dari route HTTP di bawah, bukan lagi dari js_api pywebview."""

    def __init__(self):
        self.window = None
        self.svc = service.BridgeService(on_stats_change=self._on_stats_change)

    def _on_stats_change(self, stats: dict):
        if not self.window:
            return
        try:
            self.window.evaluate_js(f"window.__bridgeOnStats && window.__bridgeOnStats({json.dumps(stats)})")
        except Exception:
            pass

    def start_bridge(self):
        log.info("start_bridge() dipanggil (HTTP)")
        result = {}
        done = threading.Event()

        def _worker():
            try:
                self.svc.start()
                result["ok"] = True
            except Exception as e:
                log.error("Gagal start bridge: %s", e)
                result["ok"] = False
                result["error"] = str(e)
            finally:
                done.set()

        threading.Thread(target=_worker, name="start_bridge_worker", daemon=True).start()
        done.wait(timeout=5)

        if done.is_set() and result.get("ok") is False:
            raise RuntimeError(result.get("error", "Gagal memulai bridge."))

        return {"running": self.svc.is_running(), "stats": self.svc.stats, "pending": not done.is_set()}

    def stop_bridge(self):
        log.info("stop_bridge() dipanggil (HTTP)")
        self.svc.stop()
        return {"running": self.svc.is_running(), "stats": self.svc.stats}

    def get_status(self):
        return {"running": self.svc.is_running(), "stats": self.svc.stats}

    def get_settings(self):
        return _settings.get()

    def save_settings(self, new_settings: dict):
        return _settings.save(new_settings)

    def ping_silakes(self):
        s = _settings.get()
        url = f"{s['silakes_base_url']}/v3/lis/agent/pending"
        try:
            r = requests.get(
                url,
                headers={"X-LIS-X": s["lis_secret_key"], "Accept": "application/json"},
                params={"device_code": s["device_code"]},
                timeout=6,
            )
            if r.status_code == 401:
                return {"ok": False, "message": "API terhubung, tapi LIS Secret Key salah (401)."}
            if not r.ok:
                return {"ok": False, "message": f"API membalas status {r.status_code}."}
            return {"ok": True, "message": "Terhubung ke SiLAKES API."}
        except requests.exceptions.Timeout:
            return {"ok": False, "message": "Timeout menghubungi SiLAKES API (cek internet)."}
        except requests.exceptions.ConnectionError:
            return {"ok": False, "message": "Tidak bisa terhubung ke SiLAKES API (cek internet/URL)."}
        except Exception as e:
            return {"ok": False, "message": f"Gagal menguji koneksi: {e}"}

    def open_data_folder(self):
        try:
            os.makedirs(_settings.APPDATA_DIR, exist_ok=True)
            os.startfile(_settings.APPDATA_DIR)  # noqa: S606 -- Windows only, disengaja
        except Exception as e:
            log.warning("Gagal buka folder data: %s", e)
        return True

    def send_sample(self, payload: dict):
        """
        Terima payload form "Kirim Sampel" dari GUI.

        CATATAN PENTING (dari bukti forensik CheckData/*/LIS_Back_Receive.txt
        & String IDS_CWorkList_34="Lab ID" / IDS_CWorkList_39="Patient ID" di
        Language/English.ini SAGES200): "Patient ID" dan "Sample ID"/"Lab ID"
        adalah 2 field BERBEDA di software alat, bukan sinonim. Dari live
        test nyata, tombol LIS di Schedule query pakai ID internal alat
        sendiri (mis. "S10001"), BUKAN Patient ID yang kita isi -- makanya
        di sini accession CACHE dipilih dari sample_id dulu (representasi
        "Lab ID"/nomor sampel), baru fallback ke patient_id kalau kosong.
        Kalau accession yg di-query MC-200 tetap tidak cocok persis,
        BridgeService._handle_query() sudah punya fallback: dipakai otomatis
        selama cuma ada 1 entri pending di cache.
        """
        if not self.svc.is_running():
            raise RuntimeError("Bridge belum aktif -- klik Start dulu sebelum kirim sampel.")

        patient_id = (payload.get("patient_id") or "").strip()
        sample_id = (payload.get("sample_id") or "").strip()
        accession = sample_id or patient_id
        name = (payload.get("name") or "").strip()
        tests = payload.get("tests") or []

        if not accession:
            raise ValueError("Sample ID atau Patient ID wajib diisi.")
        if not tests:
            raise ValueError("Pilih minimal 1 test.")

        return self.svc.add_manual_sample(accession, name, tests)


# ============================================================================
# HTTP API lokal (127.0.0.1 saja) -- pengganti js_api pywebview yang rapuh.
# ============================================================================
http_app = Bottle()
bridge_api = BridgeApi()


@http_app.hook("after_request")
def _cors():
    bottle_response.headers["Access-Control-Allow-Origin"] = "*"
    bottle_response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    bottle_response.headers["Access-Control-Allow-Headers"] = "Content-Type"


@http_app.route("/api/<path:path>", method="OPTIONS")
def _preflight(path):
    return ""


def _ok(data):
    bottle_response.content_type = "application/json"
    return json.dumps(data)


def _error(e, status=500):
    bottle_response.status = status
    bottle_response.content_type = "application/json"
    return json.dumps({"error": str(e)})


@http_app.post("/api/start")
def _http_start():
    try:
        return _ok(bridge_api.start_bridge())
    except Exception as e:
        return _error(e)


@http_app.post("/api/stop")
def _http_stop():
    try:
        return _ok(bridge_api.stop_bridge())
    except Exception as e:
        return _error(e)


@http_app.get("/api/status")
def _http_status():
    try:
        return _ok(bridge_api.get_status())
    except Exception as e:
        return _error(e)


@http_app.get("/api/settings")
def _http_get_settings():
    try:
        return _ok(bridge_api.get_settings())
    except Exception as e:
        return _error(e)


@http_app.post("/api/settings")
def _http_save_settings():
    try:
        payload = bottle_request.json or {}
        return _ok(bridge_api.save_settings(payload))
    except Exception as e:
        return _error(e)


@http_app.get("/api/ping_silakes")
def _http_ping_silakes():
    try:
        return _ok(bridge_api.ping_silakes())
    except Exception as e:
        return _error(e)


@http_app.post("/api/open_data_folder")
def _http_open_data_folder():
    try:
        return _ok({"ok": bridge_api.open_data_folder()})
    except Exception as e:
        return _error(e)


@http_app.post("/api/send_sample")
def _http_send_sample():
    try:
        payload = bottle_request.json or {}
        return _ok(bridge_api.send_sample(payload))
    except Exception as e:
        return _error(e, status=400)


# Daftar device_test_code yang sudah ter-mapping di device MC200 (id=2) di
# SiLAKES -- lihat RESEARCH_LOG.md. Hardcode sederhana (bukan fetch dinamis
# dari SiLAKES admin API, yang butuh auth Sanctum staf, bukan header X-LIS-X
# yang dipunyai bridge). Update manual kalau mapping test code berubah.
KNOWN_TEST_CODES = [
    "ALB", "UA", "TG", "T-CHOL", "AST", "ALT",
    "CREA", "UREA", "HDL-C", "LDL-C", "TBIL", "DBIL", "GLU",
]


@http_app.get("/api/known_tests")
def _http_known_tests():
    return _ok({"tests": KNOWN_TEST_CODES})


def _start_http_api_server():
    def _run():
        try:
            bottle_run(http_app, host=API_HOST, port=API_PORT, quiet=True, server="wsgiref")
        except Exception:
            log.exception("HTTP API server berhenti tak terduga")

    t = threading.Thread(target=_run, name="http_api", daemon=True)
    t.start()
    log.info("HTTP API lokal listen di http://%s:%s (dipakai frontend via fetch(), bukan js_api)", API_HOST, API_PORT)


def _resource_path(*parts: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def _setup_logging():
    log_dir = os.path.join(_settings.APPDATA_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"bridge-{datetime.now().strftime('%Y%m%d')}.log")

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(threadName)s %(name)s: %(message)s")
    noise_filter = TruncateNoiseFilter()

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    file_handler.addFilter(noise_filter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)
    console_handler.addFilter(noise_filter)
    root.addHandler(console_handler)


def main():
    _setup_logging()
    _start_http_api_server()

    prod = "--prod" in sys.argv
    dist_index = _resource_path("gui", "dist", "index.html")

    if prod or os.path.exists(dist_index):
        url = dist_index
    else:
        url = "http://localhost:5173"

    window = webview.create_window(
        "SiLAKES LIS Interface",
        url,
        width=1180,
        height=800,
        min_size=(960, 660),
        background_color="#0f172a",
    )
    bridge_api.window = window

    gui_handler = LogBridgeHandler(lambda: bridge_api.window)
    gui_handler.setLevel(logging.INFO)
    gui_handler.addFilter(TruncateNoiseFilter())
    logging.getLogger().addHandler(gui_handler)

    def _on_closing():
        bridge_api.svc.stop()

    window.events.closing += _on_closing

    webview.start(debug=False)


if __name__ == "__main__":
    main()
