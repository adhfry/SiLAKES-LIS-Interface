"""
Klien HTTP tipis untuk endpoint /v3/lis/agent/* SiLAKES.
Semua request wajib header X-LIS-X (lihat VerifyLisKey middleware di server).

Baca setting LIVE dari settings.get() (bisa diubah GUI sebelum bridge di-Start),
bukan dari config.py statis, supaya GUI settings panel efektif tanpa restart app.
"""
from __future__ import annotations

import logging

import requests

import settings as _settings

log = logging.getLogger("silakes_client")


def _headers() -> dict:
    return {
        "X-LIS-X": _settings.get()["lis_secret_key"],
        "Accept": "application/json",
    }


def get_pending(device_code: str | None = None) -> list[dict]:
    """GET /v3/lis/agent/pending -> list worklist status='pending' utk device ini."""
    s = _settings.get()
    device_code = device_code or s["device_code"]
    url = f"{s['silakes_base_url']}/v3/lis/agent/pending"
    r = requests.get(url, headers=_headers(), params={"device_code": device_code}, timeout=s["http_timeout_seconds"])
    r.raise_for_status()
    data = r.json()
    return data.get("data", {}).get("worklists", [])


def mark_downloaded(worklist_id: int) -> dict:
    s = _settings.get()
    url = f"{s['silakes_base_url']}/v3/lis/agent/downloaded/{worklist_id}"
    r = requests.post(url, headers=_headers(), timeout=s["http_timeout_seconds"])
    r.raise_for_status()
    return r.json()


def mark_processing(filename: str, device_code: str | None = None) -> dict:
    s = _settings.get()
    device_code = device_code or s["device_code"]
    url = f"{s['silakes_base_url']}/v3/lis/agent/processing"
    r = requests.post(
        url, headers=_headers(),
        json={"filename": filename, "device_code": device_code},
        timeout=s["http_timeout_seconds"],
    )
    r.raise_for_status()
    return r.json()


def post_output(filename: str, astm_content: str, device_code: str | None = None) -> dict:
    s = _settings.get()
    device_code = device_code or s["device_code"]
    url = f"{s['silakes_base_url']}/v3/lis/agent/output"
    r = requests.post(
        url, headers=_headers(),
        json={"filename": filename, "device_code": device_code, "astm_content": astm_content},
        timeout=s["http_timeout_seconds"],
    )
    if not r.ok:
        log.error("POST /output response body (status=%s): %s", r.status_code, r.text)
    r.raise_for_status()
    return r.json()


def post_monitor_event(event_type: str, message: str, device_code: str | None = None) -> dict:
    """POST /v3/lis/agent/monitor -- dashboard live monitoring Vue.js."""
    s = _settings.get()
    device_code = device_code or s["device_code"]
    url = f"{s['silakes_base_url']}/v3/lis/agent/monitor"
    try:
        r = requests.post(
            url, headers=_headers(),
            json={"device_code": device_code, "event_type": event_type, "message": message},
            timeout=s["http_timeout_seconds"],
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:  # monitoring gagal jangan sampai bikin bridge crash
        log.warning("Gagal kirim monitor event: %s", e)
        return {}
