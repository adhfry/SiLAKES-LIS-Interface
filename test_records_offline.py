"""
Validasi offline layer astm_records.py memakai data nyata dari capture Fase 2
(RESEARCH_LOG.md) dan format generateAstmContent() milik backend SiLAKES.
Tidak butuh jaringan / alat sama sekali.
"""
import astm_records as R


def test_parse_query():
    text = "Q|1|^PAT1||ALL||||||||O"
    acc = R.parse_query_record(text)
    assert acc == "PAT1", f"expected PAT1, got {acc!r}"
    print(f"[OK] parse_query_record -> {acc!r}")


def test_parse_r_record():
    text = "R|1|^^^ALB|93.42|g/dL|3.40^5.60||N|F||||20260311111121"
    r = R.parse_r_record(text)
    assert r is not None
    assert r.method_code == "ALB", r.method_code
    assert r.value == "93.42", r.value
    assert r.unit == "g/dL", r.unit
    assert r.flag == "N", r.flag
    assert r.status == "F", r.status
    assert r.completed_at == "20260311111121", r.completed_at
    print(f"[OK] parse_r_record -> {r}")


def test_group_results_by_patient():
    texts = [
        "H|\\^&|||BioResult^3.6^11052213||||||||E-1394-97|20260311111121",
        "P|1|||7|||Serum|N||||||^",
        "O|1|^7^^^|SAGES 200^||S|20260311111121|||||||||1||||||||||O",
        "R|1|^^^ALB|93.42|g/dL|3.40^5.60||N|F||||20260311111121",
        "L|1|N",
    ]
    groups = R.group_results_by_patient(texts)
    assert "7" in groups, groups.keys()
    assert len(groups["7"]) == 1
    assert groups["7"][0].method_code == "ALB"
    print(f"[OK] group_results_by_patient -> {groups}")


def test_build_silakes_output_astm_matches_server_parser_layout():
    """
    Pastikan output normalisasi kita menghasilkan posisi field yang PERSIS
    sesuai yang dibaca WorklistController::parseOutputAstm() di server
    (field[2]=method, field[4]=unit, field[8]=value, field[12]=completed_at
    utk R record; field[3]=accession utk P record).
    """
    results = [
        R.RawResult(method_code="ALB", value="93.42", unit="g/dL", ref_range="3.40^5.60",
                    flag="N", status="F", completed_at="20260311111121"),
        R.RawResult(method_code="UA", value="5.10", unit="mg/dL", ref_range="",
                    flag="", status="F", completed_at="20260311111500"),
    ]
    astm = R.build_silakes_output_astm("MC200", "P194-20", results)
    lines = astm.split("\r\n")

    p_line = next(l for l in lines if l.startswith("P|"))
    p_fields = p_line.split("|")
    assert p_fields[3] == "P194-20", p_fields

    r_lines = [l for l in lines if l.startswith("R|")]
    assert len(r_lines) == 2
    f0 = r_lines[0].split("|")
    assert f0[2] == "ALB", f0
    assert f0[4] == "g/dL", f0
    assert f0[8] == "93.42", f0
    assert f0[12] == "20260311111121", f0

    print("[OK] build_silakes_output_astm layout cocok dgn parseOutputAstm server:")
    print(astm)


def test_parse_pending_worklist_astm():
    """Format ini PERSIS keluaran generateAstmContent() milik server."""
    astm = (
        "H|\\^&|||SiLAKES^HOST|||||P|1|20260831120000\r\n"
        "P|1||P194-20||DOE^JOHN||19800101|M\r\n"
        "O|1|||ALB|False||||||||||Serum|||||||||||||||\r\n"
        "O|2|||UA|False||||||||||Serum|||||||||||||||\r\n"
        "L||N"
    )
    # BARU (fitur kode pendek, lihat RESEARCH_LOG.md 2026-08-31): hasil di-key
    # pakai KODE PENDEK 2-digit ("01","02",...) sesuai urutan record P, BUKAN
    # accession asli lagi -- accession asli sekarang ada di sub-key
    # "real_accession". Test ini sempat basi (tidak di-update sejak refactor
    # itu) sampai ditemukan lewat kegagalan nyata saat menjalankan test suite.
    parsed = R.parse_pending_worklist_astm(astm)
    assert "01" in parsed
    assert parsed["01"]["real_accession"] == "P194-20"
    assert parsed["01"]["tests"] == ["ALB", "UA"], parsed
    assert "DOE" in parsed["01"]["name"]
    print(f"[OK] parse_pending_worklist_astm -> {parsed}")


def main():
    tests = [
        test_parse_query,
        test_parse_r_record,
        test_group_results_by_patient,
        test_build_silakes_output_astm_matches_server_parser_layout,
        test_parse_pending_worklist_astm,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {t.__name__}: {e}")
    print()
    if failed:
        print(f"{failed} test GAGAL.")
    else:
        print("SEMUA test offline record-layer LULUS.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
