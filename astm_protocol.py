"""
Low-level ASTM E1381/E1394-97 framing over TCP.

Referensi byte-level: RESEARCH_LOG.md Fase 2, capture asli dari
CheckData/20260311/ASTM_LIS_CHeck_Sent.txt (software SAGES200 / MC-200).
"""
from __future__ import annotations

import logging
import socket
import time

log = logging.getLogger("bridge.astm")

ENQ = b"\x05"
ACK = b"\x06"
NAK = b"\x15"
STX = b"\x02"
ETX = b"\x03"
ETB = b"\x17"  # intermediate frame terminator (multi-frame record belum ada bukti dipakai MC-200)
EOT = b"\x04"
CR = b"\x0d"
LF = b"\x0a"


def checksum(frame_body: bytes) -> bytes:
    """
    Hitung checksum ASTM: jumlah semua byte dari frame-number sampai dengan
    ETX/ETB (inklusif), mod 256, direpresentasikan 2 digit hex UPPERCASE (ASCII).

    frame_body = frame_number_char + text_bytes + CR + ETX
    (persis apa yang ada di antara STX dan checksum di capture asli)
    """
    total = sum(frame_body) % 256
    return f"{total:02X}".encode("ascii")


def build_frame(frame_number: int, text: str) -> bytes:
    """
    Bangun 1 frame ASTM lengkap siap kirim:
    STX + frame_number + text + CR + ETX + checksum(2 hex) + CR + LF
    """
    fn_char = str(frame_number % 8).encode("ascii")  # ASTM frame number siklus 0-7 (biasa mulai dari 1)
    text_bytes = text.encode("ascii", errors="replace")
    body = fn_char + text_bytes + CR + ETX
    cs = checksum(body)
    return STX + body + cs + CR + LF


def parse_frame(raw: bytes) -> tuple[int, str] | None:
    """
    Parse 1 frame ASTM mentah (tanpa leading STX, sampai sebelum trailing CRLF)
    menjadi (frame_number, text). Return None kalau format tidak valid atau
    checksum tidak cocok.

    raw diharapkan: frame_number(1) + text + CR + ETX + checksum(2)
    """
    if len(raw) < 4:
        return None
    try:
        fn = int(chr(raw[0]))
    except ValueError:
        return None

    # cari ETX
    etx_idx = raw.find(ETX)
    if etx_idx == -1:
        return None

    body = raw[:etx_idx + 1]  # frame_number + text + CR + ETX
    given_cs = raw[etx_idx + 1: etx_idx + 3]
    expected_cs = checksum(body)
    if given_cs.upper() != expected_cs.upper():
        return None

    text = raw[1:etx_idx].rstrip(b"\r").decode("ascii", errors="replace")
    return fn, text


class AstmFrameError(Exception):
    """1 frame gagal diparse (checksum salah / ETX tidak ketemu / format rusak)
    -- BUKAN akhir transmisi. Caller WAJIB NAK supaya sender (MC-200)
    retransmit frame yang sama, sesuai ASTM E1394-97."""


class AstmProtocolError(Exception):
    """Kondisi protokol tidak wajar yang bridge sengaja tolak lanjutkan
    (mis. frame korup berturut-turut, atau transmisi tidak pernah EOT)."""


class AstmSession:
    """
    Wrapper tipis di atas socket TCP untuk 1 koneksi MC-200 <-> bridge.
    Menyediakan primitives kirim/terima level rendah (ENQ/ACK/frame/EOT)
    dipakai baik saat bridge jadi RECEIVER (alat query) maupun SENDER
    (bridge push balasan/order).
    """

    def __init__(self, sock: socket.socket, timeout: float = 60.0):
        self.sock = sock
        self.sock.settimeout(timeout)
        self._buf = b""

    def _recv_exact_or_more(self, min_bytes: int = 1) -> bytes:
        while len(self._buf) < min_bytes:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Koneksi ditutup oleh remote (MC-200)")
            self._buf += chunk
        return self._buf

    def read_byte(self) -> bytes:
        self._recv_exact_or_more(1)
        b, self._buf = self._buf[:1], self._buf[1:]
        return b

    def read_until(self, terminator: bytes) -> bytes:
        while terminator not in self._buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Koneksi ditutup oleh remote (MC-200) saat read_until")
            self._buf += chunk
        idx = self._buf.find(terminator) + len(terminator)
        data, self._buf = self._buf[:idx], self._buf[idx:]
        return data

    def send(self, data: bytes):
        self.sock.sendall(data)

    # ---- receiver-side primitives -----------------------------------
    def wait_enq(self) -> bool:
        b = self.read_byte()
        return b == ENQ

    def send_ack(self):
        self.send(ACK)

    def send_nak(self):
        self.send(NAK)

    def read_one_frame(self) -> tuple[int, str] | None:
        """
        Baca 1 frame STX...CRLF penuh.
        Return (frame_number, text) kalau valid, atau None kalau EOT beneran.
        Raise AstmFrameError kalau byte pertama STX tapi checksum/format
        frame-nya rusak -- BUKAN EOT, caller wajib NAK (lihat read_record_set).

        BUG NYATA (2026-09-02, laporan user): sebelumnya frame rusak
        DIPERLAKUKAN SAMA PERSIS dengan EOT (sama-sama return None) --
        akibatnya read_record_set() diam-diam BERHENTI membaca di tengah
        transmisi 1 pasien tanpa pernah kirim NAK, sisa record (P/O/R/L
        setelah frame yang rusak) hilang tanpa jejak, dan MC-200 (yang masih
        menunggu ACK/NAK utk frame yg baru dikirim) macet menunggu sampai
        timeout lalu menyerah utk pasien itu -- persis gejala "1-2 dari 28
        pasien selalu gagal, beda-beda mana yg gagal tiap percobaan" karena
        checksum rusak/frame terpotong bisa kena pasien mana saja tergantung
        jitter jaringan/timing saat itu. Lihat RESEARCH_LOG.md.
        """
        b = self.read_byte()
        if b == EOT:
            return None
        if b != STX:
            # byte sampah / out-of-sync, buang dan coba lagi (best effort)
            return self.read_one_frame()
        raw = self.read_until(CR + LF)
        raw = raw[:-2]  # buang trailing CRLF
        parsed = parse_frame(raw)
        if parsed is None:
            raise AstmFrameError(f"Frame korup/tidak valid (checksum atau format salah): {raw!r}")
        return parsed

    def read_record_set(self, max_frames: int = 2000) -> list[str]:
        """
        Baca semua frame sampai EOT, kirim ACK per frame valid, NAK kalau
        frame korup (lalu tunggu MC-200 retransmit -- TIDAK berhenti baca).
        Return list of text (urut).

        `max_frames` cuma jaring pengaman terakhir (dulu 200 -- angka
        sembarang yang bisa kepotong duluan sebelum EOT beneran utk batch
        besar, mis. worklist Prolanis 9-test x puluhan pasien dalam 1
        transmisi; sekarang jauh lebih longgar & GAGAL EKSPLISIT/berisik
        kalau benar-benar kena, bukan diam-diam motong data spt sebelumnya).
        """
        texts: list[str] = []
        consecutive_bad_frames = 0
        frame_count = 0
        while frame_count < max_frames:
            try:
                parsed = self.read_one_frame()
            except AstmFrameError as e:
                consecutive_bad_frames += 1
                log.warning(
                    "Frame korup, kirim NAK supaya MC-200 retransmit (percobaan ke-%d): %s",
                    consecutive_bad_frames, e,
                )
                if consecutive_bad_frames > 5:
                    raise AstmProtocolError(
                        f"5 frame korup berturut-turut, koneksi kemungkinan rusak: {e}"
                    ) from e
                self.send_nak()
                continue

            consecutive_bad_frames = 0
            if parsed is None:
                return texts  # EOT beneran, transmisi selesai normal
            fn, text = parsed
            self.send_ack()
            texts.append(text)
            frame_count += 1

        raise AstmProtocolError(
            f"Melebihi {max_frames} frame dalam 1 transmisi tanpa EOT -- kemungkinan loop protokol tak wajar."
        )

    # ---- sender-side primitives ----------------------------------------
    def send_enq_and_wait_ack(self, retries: int = 3) -> bool:
        for _ in range(retries):
            self.send(ENQ)
            b = self.read_byte()
            if b == ACK:
                return True
            if b == NAK:
                time.sleep(0.3)
                continue
        return False

    def send_record_set(self, lines: list[str]):
        """Kirim beberapa record ASTM (H/P/O/L, dst) sbg frame terpisah, tiap frame nunggu ACK."""
        for i, line in enumerate(lines, start=1):
            frame = build_frame(i, line)
            for attempt in range(3):
                self.send(frame)
                b = self.read_byte()
                if b == ACK:
                    break
                # NAK atau timeout -> retry
            else:
                raise ConnectionError(f"Gagal kirim frame #{i} setelah 3x retry (tidak ada ACK)")
        self.send(EOT)
