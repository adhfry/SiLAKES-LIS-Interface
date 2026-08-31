r"""
Konfigurasi bridge yang bisa diedit & disimpan lewat GUI (bukan cuma
env var / hardcode seperti config.py lama). Disimpan sbg JSON di
%APPDATA%\SiLAKES-MC200-Bridge\settings.json supaya persist antar restart
app & tidak perlu edit file kode.

config.py tetap ada sbg DEFAULT value & dipakai modul non-GUI (test offline,
dsb). Modul lain (silakes_client, bridge_server/service) baca nilai LIVE dari
sini lewat get_settings(), bukan langsung dari config module, supaya GUI bisa
ubah setting on-the-fly sebelum Start.
"""
from __future__ import annotations

import json
import os
import threading

import config as _defaults

APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SiLAKES-MC200-Bridge")
SETTINGS_PATH = os.path.join(APPDATA_DIR, "settings.json")

_lock = threading.Lock()

DEFAULTS = {
    "listen_host": _defaults.LISTEN_HOST,
    "listen_port": _defaults.LISTEN_PORT,
    "silakes_base_url": _defaults.SILAKES_BASE_URL,
    "lis_secret_key": _defaults.LIS_SECRET_KEY,
    "device_code": _defaults.DEVICE_CODE,
    "poll_interval_seconds": _defaults.POLL_INTERVAL_SECONDS,
    "http_timeout_seconds": _defaults.HTTP_TIMEOUT_SECONDS,
    # 300s (bukan 60s) -- MC-200 terbukti (2026-08-31, ERROR_CONN_CLOSED di log
    # alat) membuka koneksi TCP jauh SEBELUM operator selesai isi Position/
    # Patient ID & klik Receive di layar. Timeout pendek memotong koneksi itu
    # duluan sebelum sempat dipakai alat -- lihat RESEARCH_LOG.md.
    "socket_timeout_seconds": 300.0,
}

_current = dict(DEFAULTS)


def load() -> dict:
    global _current
    with _lock:
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                merged = dict(DEFAULTS)
                merged.update({k: v for k, v in saved.items() if k in DEFAULTS})
                _current = merged
            except Exception:
                _current = dict(DEFAULTS)
        else:
            _current = dict(DEFAULTS)
        return dict(_current)


def save(new_settings: dict) -> dict:
    global _current
    with _lock:
        merged = dict(_current)
        for k, v in new_settings.items():
            if k in DEFAULTS:
                merged[k] = v
        os.makedirs(APPDATA_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        _current = merged
        return dict(_current)


def get() -> dict:
    with _lock:
        return dict(_current)


# muat sekali saat modul di-import
load()
