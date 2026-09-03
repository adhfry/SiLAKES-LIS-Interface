"""
Regresi utk BUG NYATA (2026-09-02, laporan user): studi kasus 28 data pasien
dari MC-200 (device mendukung s.d. 40), 1-2 di antaranya SELALU gagal saat
Receive -- beda-beda mana yang gagal tiap percobaan.

Root cause (astm_protocol.py::AstmSession.read_one_frame/read_record_set,
SEBELUM fix): frame yang gagal parse (checksum salah/rusak) diperlakukan
IDENTIK dengan EOT (sama-sama return None) -- read_record_set() diam-diam
BERHENTI membaca sisa frame TANPA pernah kirim NAK. MC-200 (yang masih
menunggu ACK/NAK utk frame yang baru dikirim) macet sampai timeout lalu
menyerah utk pasien itu -- kena pasien mana saja tergantung timing/jitter
transmisi saat itu.

Test ini mensimulasikan PERSIS skenario itu: kirim beberapa frame hasil utk
1 pasien, TAPI salah satu frame di TENGAH batch sengaja dirusak checksumnya
dulu (spt frame yg kena jitter jaringan), lalu setelah bridge NAK, client
retransmit frame yang SAMA (benar) -- persis perilaku sender ASTM asli.
Assert SEMUA parameter tetap sampai ke post_output(), tidak ada yang hilang.
"""
import atexit
import socket
import time

import settings as _settings
import silakes_client as api
from astm_protocol import ACK, EOT, ENQ, NAK, build_frame
from service import BridgeService

# Isolasi settings.json dari instance bridge asli yg mungkin aktif di lapangan
# (lihat catatan identik di test_service_loopback.py).
_original_settings = _settings.load()
_settings.save({"listen_port": 17125, "listen_host": "127.0.0.1"})
atexit.register(lambda: _settings.save(_original_settings))
HOST = "127.0.0.1"

calls = {"post_output": []}
api.mark_processing = lambda *a, **k: {}
api.post_output = lambda filename, astm_content, device_code=None: (
    calls["post_output"].append((filename, astm_content, device_code)) or {"message": "ok (mock)"}
)
api.post_monitor_event = lambda *a, **k: {}
api.mark_downloaded = lambda *a, **k: {}
api.get_pending = lambda *a, **k: []

svc = BridgeService()
svc.start()
time.sleep(0.3)
assert svc.is_running()


def corrupt(frame: bytes) -> bytes:
    """Rusak 1 frame yg sudah dibangun build_frame(): balik 2 digit checksum-nya
    jadi salah, TAPI struktur frame (STX/CR/ETX/CRLF) tetap utuh -- persis
    simulasi 1 frame yg datanya korup di tengah jalan, bukan frame yg cacat
    total (supaya benar-benar menguji jalur checksum-mismatch, bukan
    jalur "byte sampah")."""
    assert frame.endswith(b"\r\n")
    body_and_cs = frame[1:-2]  # buang STX di depan & CRLF di belakang
    etx_idx = body_and_cs.find(b"\x03")
    good_cs = body_and_cs[etx_idx + 1: etx_idx + 3]
    bad_cs = b"00" if good_cs != b"00" else b"11"
    corrupted = body_and_cs[:etx_idx + 1] + bad_cs
    return b"\x02" + corrupted + b"\r\n"


sock = socket.create_connection((HOST, 17125), timeout=5)
sock.settimeout(5)

sock.sendall(ENQ)
assert sock.recv(1) == ACK, "bridge harus ACK ENQ pertama"

lines = [
    "H|\\^&|||BioResult^3.6^11052213||||||||E-1394-97|20260311111121",
    "P|1|||42|||Serum|N||||||^",
    "O|1|^42^^^|SAGES 200^||S|20260311111121|||||||||1||||||||||O",
    "R|1|^^^ALB|93.42|g/dL|3.40^5.60||N|F||||20260311111121",
    "R|2|^^^UA|5.10|mg/dL|||N|F||||20260311111122",   # <- frame ini akan dikirim RUSAK dulu
    "R|3|^^^CREA|0.80|mg/dL|||N|F||||20260311111123",
    "L|1|N",
]

bad_frame_index = 5  # frame ke-5 = baris R|2 (UA), 1-indexed spt build_frame(i, ...): 1=H,2=P,3=O,4=R(ALB),5=R(UA)
for i, line in enumerate(lines, start=1):
    frame = build_frame(i, line)
    if i == bad_frame_index:
        sock.sendall(corrupt(frame))
        resp = sock.recv(1)
        assert resp == NAK, f"bridge HARUS NAK frame korup, dapat {resp!r} -- ini bug yg sedang diperbaiki"
        # sender ASTM asli retransmit frame YANG SAMA (benar) setelah NAK
        sock.sendall(frame)
        resp2 = sock.recv(1)
        assert resp2 == ACK, f"bridge harus ACK setelah retransmit benar, dapat {resp2!r}"
    else:
        sock.sendall(frame)
        resp = sock.recv(1)
        assert resp == ACK, f"frame #{i} ({line!r}) diharapkan ACK, dapat {resp!r}"

sock.sendall(EOT)
time.sleep(0.3)
sock.close()

assert calls["post_output"], "post_output HARUS terpanggil -- kalau tidak, seluruh batch hilang"
filename, astm_content, device_code = calls["post_output"][0]
assert "ALB" in astm_content, "hasil ALB (sebelum frame korup) hilang dari output"
assert "UA" in astm_content, "hasil UA (frame yg sempat korup) hilang dari output -- BUG belum fix"
assert "CREA" in astm_content, "hasil CREA (setelah frame korup) hilang dari output -- BUG belum fix (data setelah titik korup ikut kepotong)"
print("[OK] Frame korup di tengah batch: bridge NAK, client retransmit, SEMUA 3 parameter (ALB, UA, CREA) sampai utuh ke post_output.")
print(f"--- astm_content yg di-POST ---\n{astm_content}")

svc.stop()
time.sleep(0.2)
assert not svc.is_running()

print("\nSEMUA TEST frame-recovery LULUS.")
