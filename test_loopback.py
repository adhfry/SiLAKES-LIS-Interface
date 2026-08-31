"""
Test end-to-end loopback: bridge_server jadi TCP server sungguhan di
localhost, 1 thread berperan sbg "MC-200 palsu" yang mengirim byte PERSIS
seperti capture asli (RESEARCH_LOG.md Fase 2). Panggilan ke SiLAKES API
di-mock (tidak butuh jaringan/API key asli).

Menguji 2 skenario:
  1. MC-200 kirim Host Query -> bridge harus balas jadi sender dgn worklist
     yang sudah di-cache.
  2. MC-200 kirim hasil (P+R records) -> bridge harus panggil post_output
     dgn accession & hasil yang benar (via mock).
"""
import socket
import threading
import time

import bridge_server as bs
import config
from astm_protocol import ENQ, ACK, EOT, build_frame

config.LISTEN_PORT = 17123  # port bebas utk test, hindari bentrok port 123 asli
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


bs.api.mark_processing = fake_mark_processing
bs.api.post_output = fake_post_output
bs.api.post_monitor_event = fake_post_monitor_event
bs.api.mark_downloaded = lambda *a, **k: {}


def start_test_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, config.LISTEN_PORT))
    srv.listen(5)

    def loop():
        while True:
            sock, addr = srv.accept()
            threading.Thread(target=bs.handle_connection, args=(sock, addr), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    time.sleep(0.2)
    return srv


def client_send_and_expect_ack(sock, data):
    sock.sendall(data)
    resp = sock.recv(1)
    assert resp == ACK, f"expected ACK, got {resp!r}"


def scenario_1_host_query():
    print("=== Skenario 1: Host Query (MC-200 nanya worklist utk PAT1) ===")

    with bs._cache_lock:
        bs._pending_cache["PAT1"] = {
            "worklist_id": 1,
            "filename": "test_worklist.astm",
            "name": "PAT1",
            "tests": ["ALB", "UA"],
        }

    sock = socket.create_connection((HOST, config.LISTEN_PORT), timeout=5)
    sock.settimeout(5)

    # MC-200 kirim ENQ, tunggu ACK dari bridge
    sock.sendall(ENQ)
    assert sock.recv(1) == ACK, "bridge tidak ACK ENQ dari client"

    # MC-200 kirim frame Q persis seperti capture asli
    q_text = "Q|1|^PAT1||ALL||||||||O"
    client_send_and_expect_ack(sock, build_frame(1, q_text))
    sock.sendall(EOT)

    # sekarang bridge harus BALIK jadi sender: kita (client) harus terima ENQ darinya
    b = sock.recv(1)
    assert b == ENQ, f"bridge tidak kirim ENQ balik utk jawab Query, dapat: {b!r}"
    sock.sendall(ACK)

    received_frames = []
    while True:
        b = sock.recv(1)
        if b == EOT:
            break
        assert b == b"\x02", f"expected STX, got {b!r}"  # STX
        buf = b""
        while not buf.endswith(b"\r\n"):
            buf += sock.recv(1)
        received_frames.append(buf)
        sock.sendall(ACK)

    sock.close()

    all_text = b"".join(received_frames).decode("ascii", errors="replace")
    assert "ALB" in all_text, all_text
    assert "UA" in all_text, all_text
    assert "PAT1" in all_text, all_text
    print(f"[OK] Bridge membalas Query dgn {len(received_frames)} frame, berisi ALB & UA utk PAT1.")
    print(f"[OK] mark_processing terpanggil: {calls['mark_processing']}")
    assert calls["mark_processing"], "mark_processing tidak pernah dipanggil"


def scenario_2_result_upload():
    print("\n=== Skenario 2: MC-200 upload hasil (P + R record asli) ===")
    sock = socket.create_connection((HOST, config.LISTEN_PORT), timeout=5)
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

    time.sleep(0.3)  # beri waktu thread server proses & panggil (mock) post_output
    sock.close()

    assert calls["post_output"], "post_output tidak pernah dipanggil"
    filename, astm_content, device_code = calls["post_output"][-1]
    assert device_code == "MC200", device_code
    assert "ALB" in astm_content, astm_content
    assert "93.42" in astm_content, astm_content
    print(f"[OK] post_output terpanggil dgn accession terdeteksi dari P record, filename={filename}")
    print("--- astm_content yang dikirim ke SiLAKES (format HS200-compatible) ---")
    print(astm_content)


def main():
    start_test_server()
    scenario_1_host_query()
    scenario_2_result_upload()
    print("\nSEMUA SKENARIO LOOPBACK LULUS. Protokol siap diuji live (Fase 4).")


if __name__ == "__main__":
    main()
