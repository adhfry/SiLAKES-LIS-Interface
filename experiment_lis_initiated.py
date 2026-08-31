"""
Eksperimen: begitu MC-200 connect, BRIDGE yang proaktif kirim <ENQ> duluan
(role dibalik dari asumsi awal), lalu kalau dapat <ACK>, kirim H+L minimal
("tidak ada worklist"). Log SEMUA byte mentah (hex) apa pun yang terjadi,
supaya kita punya bukti byte-level walau hipotesis ini salah.
"""
import socket
import time

HOST = "0.0.0.0"
PORT = 123

ENQ, ACK, NAK, STX, ETX, EOT, CR, LF = (
    b"\x05", b"\x06", b"\x15", b"\x02", b"\x03", b"\x04", b"\x0d", b"\x0a"
)


def checksum(body: bytes) -> bytes:
    return f"{sum(body) % 256:02X}".encode("ascii")


def build_frame(n: int, text: str) -> bytes:
    body = str(n % 8).encode() + text.encode("ascii") + CR + ETX
    return STX + body + checksum(body) + CR + LF


def hexdump(b: bytes) -> str:
    return " ".join(f"{x:02x}" for x in b) + f"   ascii={b!r}"


srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind((HOST, PORT))
srv.listen(1)
print(f"[experiment] listen di {HOST}:{PORT}, menunggu 1 koneksi MC-200...")

sock, addr = srv.accept()
print(f"[experiment] koneksi masuk dari {addr}")
sock.settimeout(10)

# 1. Coba dengar dulu sebentar (1.5 detik) -- siapa tahu MC-200 tetap kirim duluan
sock.settimeout(1.5)
try:
    data = sock.recv(4096)
    if data:
        print(f"[experiment] MC-200 kirim duluan (tanpa kita pancing): {hexdump(data)}")
    else:
        print("[experiment] koneksi ditutup MC-200 sebelum kita sempat kirim apa pun.")
        sock.close()
        srv.close()
        raise SystemExit(0)
except socket.timeout:
    print("[experiment] 1.5 detik pertama sepi, bridge sekarang proaktif kirim <ENQ>...")

    sock.settimeout(10)
    sock.sendall(ENQ)
    print("[experiment] >> kirim ENQ")

    try:
        resp = sock.recv(1)
        print(f"[experiment] << terima: {hexdump(resp)}")

        if resp == ACK:
            print("[experiment] MC-200 ACK! Kirim H+L minimal (no worklist)...")
            lines = ["H|\\^&|||SiLAKES^HOST|||||Host|||1|" + time.strftime("%Y%m%d%H%M%S"), "L|1|N"]
            for i, line in enumerate(lines, start=1):
                frame = build_frame(i, line)
                sock.sendall(frame)
                print(f"[experiment] >> frame#{i}: {hexdump(frame)}")
                ack = sock.recv(1)
                print(f"[experiment] << {hexdump(ack)}")
            sock.sendall(EOT)
            print("[experiment] >> EOT")

            # dengar lagi 5 detik siapa tahu MC-200 balas dgn Q/R sungguhan
            sock.settimeout(5)
            try:
                more = sock.recv(4096)
                print(f"[experiment] << (setelah EOT) {hexdump(more)}")
            except socket.timeout:
                print("[experiment] tidak ada balasan lanjutan dalam 5 detik.")
        elif resp == NAK:
            print("[experiment] MC-200 balas NAK -- dia menolak kita jadi sender.")
        else:
            print(f"[experiment] MC-200 balas byte tak terduga: {resp!r}")

    except socket.timeout:
        print("[experiment] TIDAK ADA balasan sama sekali dalam 10 detik setelah kirim ENQ.")

except ConnectionError as e:
    print(f"[experiment] koneksi error: {e}")

sock.close()
srv.close()
print("[experiment] selesai.")
