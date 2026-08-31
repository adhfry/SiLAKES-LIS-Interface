"""
Validasi offline: pastikan astm_protocol.checksum() menghasilkan angka yang
SAMA PERSIS dengan checksum yang tercatat di log capture asli MC-200/SAGES200
(RESEARCH_LOG.md Fase 2). Tidak butuh koneksi ke alat sama sekali.

Sumber capture: CheckData/20260311/ASTM_LIS_CHeck_Sent.txt
    <STX>1H|\\^&|||SAGES|||||Host|||1|20260311103912<CR><ETX>B6<CR><LF>
    <STX>2Q|1|^PAT1||ALL||||||||O<CR><ETX>30<CR><LF>
    <STX>3L|1|N<CR><ETX>06<CR><LF>
"""
from astm_protocol import checksum, build_frame, parse_frame

CASES = [
    # (frame_number, text, expected_checksum_hex)
    (1, "H|\\^&|||SAGES|||||Host|||1|20260311103912", "B6"),
    (2, "Q|1|^PAT1||ALL||||||||O", "30"),
    (3, "L|1|N", "06"),
]

def main():
    all_ok = True
    for fn, text, expected in CASES:
        frame = build_frame(fn, text)
        got = frame[-4:-2].decode("ascii")  # 2 hex char sebelum CRLF penutup
        status = "OK" if got == expected else "MISMATCH"
        if got != expected:
            all_ok = False
        print(f"frame#{fn} text={text!r:55s} expected={expected} got={got}  [{status}]")

        # roundtrip: parse balik frame yg baru dibangun, pastikan checksum tervalidasi & text sama
        body_no_stx = frame[1:-2]  # buang leading STX dan trailing CRLF
        parsed = parse_frame(body_no_stx)
        assert parsed is not None, f"parse_frame gagal untuk frame#{fn}"
        parsed_fn, parsed_text = parsed
        assert parsed_fn == fn % 8, f"frame_number mismatch: {parsed_fn} != {fn % 8}"
        assert parsed_text == text, f"text mismatch: {parsed_text!r} != {text!r}"

    print()
    if all_ok:
        print("SEMUA CHECKSUM COCOK dengan capture asli MC-200. Implementasi framing valid.")
    else:
        print("ADA MISMATCH -- perbaiki algoritma checksum sebelum lanjut ke live test.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
