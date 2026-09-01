"""
Sama seperti test_loopback.py tapi menguji BridgeService (service.py) --
class controllable yang dipakai GUI -- bukan bridge_server.py versi CLI lama.
Pastikan refactor start()/stop() tidak merusak logic yang sudah tervalidasi.
"""
import atexit
import socket
import time

import settings as _settings
import silakes_client as api
from astm_protocol import ENQ, ACK, EOT, build_frame
from service import BridgeService

# BUG NYATA (2026-09-01): save() menulis ke %APPDATA%\SiLAKES-MC200-Bridge\
# settings.json -- file YANG SAMA dipakai aplikasi GUI asli, TIDAK ADA
# isolasi test sama sekali. Menjalankan test ini sambil bridge asli sedang
# aktif di lapangan diam-diam mengubah listen_host/listen_port-nya jadi
# 127.0.0.1:17124 (tidak lagi bisa dihubungi MC-200 lewat jaringan) dan TIDAK
# PERNAH dikembalikan -- baru ketahuan lewat insiden nyata. Snapshot dulu
# settings asli SEBELUM ditimpa, kembalikan via atexit supaya selalu
# ter-restore apa pun hasil test-nya (lulus/gagal/exception).
_original_settings = _settings.load()
_settings.save({"listen_port": 17124, "listen_host": "127.0.0.1"})
atexit.register(lambda: _settings.save(_original_settings))
HOST = "127.0.0.1"

calls = {"mark_processing": [], "post_output": [], "monitor": []}


def fake_mark_processing(filename, device_code=None):
    calls["mark_processing"].append((filename, device_code))
    return {}


def fake_post_output(filename, astm_content, device_code=None):
    calls["post_output"].append((filename, astm_content, device_code))
    return {"message": "ok (mock)"}


def fake_post_monitor_event(event_type, message, device_code=None):
    calls["monitor"].append((event_type, message))
    return {}


api.mark_processing = fake_mark_processing
api.post_output = fake_post_output
api.post_monitor_event = fake_post_monitor_event
api.mark_downloaded = lambda *a, **k: {}
api.get_pending = lambda *a, **k: []  # matikan poll asli, cache diisi manual di test

stats_history = []
svc = BridgeService(on_stats_change=lambda s: stats_history.append(s))
svc.start()
time.sleep(0.3)

assert svc.is_running(), "service harus running setelah start()"


def client_send_and_expect_ack(sock, data):
    sock.sendall(data)
    resp = sock.recv(1)
    assert resp == ACK, f"expected ACK, got {resp!r}"


# --- skenario query ---
with svc._cache_lock:
    svc._pending_cache["PAT1"] = {"worklist_id": 1, "filename": "t.astm", "name": "PAT1", "tests": ["ALB", "UA"]}

sock = socket.create_connection((HOST, 17124), timeout=5)
sock.settimeout(5)
sock.sendall(ENQ)
assert sock.recv(1) == ACK
client_send_and_expect_ack(sock, build_frame(1, "Q|1|^PAT1||ALL||||||||O"))
sock.sendall(EOT)

b = sock.recv(1)
assert b == ENQ, f"expected ENQ balik dari service, dapat {b!r}"
sock.sendall(ACK)
frames = []
while True:
    b = sock.recv(1)
    if b == EOT:
        break
    buf = b
    while not buf.endswith(b"\r\n"):
        buf += sock.recv(1)
    frames.append(buf)
    sock.sendall(ACK)
sock.close()
all_text = b"".join(frames).decode()
assert "ALB" in all_text and "PAT1" in all_text
print("[OK] BridgeService: skenario Query berhasil (sama seperti bridge_server.py lama)")

# --- skenario result upload ---
sock = socket.create_connection((HOST, 17124), timeout=5)
sock.settimeout(5)
sock.sendall(ENQ)
assert sock.recv(1) == ACK
lines = [
    "H|\\^&|||BioResult^3.6^11052213||||||||E-1394-97|20260311111121",
    "P|1|||7|||Serum|N||||||^",
    "O|1|^7^^^|SAGES 200^||S|20260311111121|||||||||1||||||||||O",
    "R|1|^^^ALB|93.42|g/dL|3.40^5.60||N|F||||20260311111121",
    "L|1|N",
]
for i, line in enumerate(lines, start=1):
    client_send_and_expect_ack(sock, build_frame(i, line))
sock.sendall(EOT)
time.sleep(0.3)
sock.close()

assert calls["post_output"], "post_output harus terpanggil"
print("[OK] BridgeService: skenario result upload berhasil, post_output terpanggil")

assert svc.stats["connections_total"] == 2
assert svc.stats["queries_answered"] == 1
assert svc.stats["results_sent_ok"] == 1
assert len(stats_history) >= 3, "on_stats_change harus terpanggil beberapa kali"
print(f"[OK] stats akhir: {svc.stats}")
print(f"[OK] stats_history terekam {len(stats_history)} update")

svc.stop()
time.sleep(0.2)
assert not svc.is_running()
print("[OK] stop() berhasil, is_running() == False")

print("\nSEMUA TEST BridgeService LULUS.")
