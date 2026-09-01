"""
Parsing & pembangunan record ASTM level-tinggi (H/P/Q/O/R/L), khusus disesuaikan
dengan 2 "dialek":

1. Dialek MC-200/SAGES200 (di kabel, live socket) -- lihat RESEARCH_LOG.md Fase 2.
2. Dialek HS200 yang sudah dipahami backend SiLAKES (`WorklistController::
   generateAstmContent` / `parseOutputAstm`) -- dipakai saat bicara ke
   `/v3/lis/agent/output`, supaya ZERO perubahan di server produksi.

Bridge ini menjembatani #1 <-> #2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import datetime as dt


# ─── Parsing sisi MC-200 (masuk ke bridge) ──────────────────────────────────

def parse_query_record(text: str) -> str | None:
    """
    Q|1|^PAT1||ALL||||||||O  ->  "PAT1"  (accession/patient id yang ditanyakan)
    """
    fields = text.split("|")
    if not fields or fields[0] != "Q":
        return None
    if len(fields) < 3:
        return None
    raw = fields[2]  # contoh: "^PAT1"
    accession = raw.lstrip("^").strip()
    return accession or None


@dataclass
class RawResult:
    method_code: str
    value: str
    unit: str
    ref_range: str
    flag: str
    status: str
    completed_at: str  # YYYYMMDDHHMMSS mentah dari alat


def parse_r_record(text: str) -> RawResult | None:
    """
    Parse 1 baris R record mentah dari MC-200:
        R|1|^^^ALB|93.42|g/dL|3.40^5.60||N|F||||20260311111121

    Field index (0-based setelah split('|')):
        2 = method code (dibungkus ^^^, kadang jumlah ^ bervariasi)
        3 = value
        4 = unit
        5 = reference range (low^high)
        7 = abnormal flag
        8 = result status (F = Final)
        12 = completed_at (YYYYMMDDHHMMSS)

    CATATAN: posisi field ini didasarkan pada 1 contoh capture nyata (Fase 2).
    WAJIB dikonfirmasi ulang saat live test Fase 4 untuk device_test_code lain
    (ALT, AST, GLU, dst) -- kemungkinan besar sama karena ini bagian dari
    struktur ASTM E1394-97 standar, tapi belum 100% dibuktikan utk semua kode.
    """
    fields = text.split("|")
    if not fields or fields[0] != "R":
        return None
    if len(fields) < 9:
        return None

    raw_method = fields[2] if len(fields) > 2 else ""
    method_code = raw_method.split("^")[-1].strip()  # buang prefix ^^^

    return RawResult(
        method_code=method_code,
        value=(fields[3] if len(fields) > 3 else "").strip(),
        unit=(fields[4] if len(fields) > 4 else "").strip(),
        ref_range=(fields[5] if len(fields) > 5 else "").strip(),
        flag=(fields[7] if len(fields) > 7 else "").strip(),
        status=(fields[8] if len(fields) > 8 else "").strip(),
        completed_at=(fields[12] if len(fields) > 12 else "").strip(),
    )


def _extract_patient_id(p_fields: list[str]) -> str:
    """
    Cari Patient ID dari record P. Ada 2 varian posisi yang terbukti dipakai
    (lihat RESEARCH_LOG.md Fase 2):
      - field[3] "Practice Assigned Patient ID"  (dipakai contoh demo bawaan LIS di exe)
      - field[4] "Laboratory Assigned Patient ID" (dipakai capture NYATA MC-200 saat
        upload hasil, mis. "P|1|||7|||Serum|N||||||^" -> "7" di field[4])
    Ambil field[3] dulu kalau isi, fallback ke field[4], lalu field[2].
    WAJIB dikonfirmasi ulang saat Fase 4 posisi mana yg dipakai utk accession
    kustom kita ("P{id}-{id}" / "S{id}").
    """
    for idx in (3, 4, 2):
        if len(p_fields) > idx and p_fields[idx].strip():
            return p_fields[idx].strip()
    return ""


def group_results_by_patient(texts: list[str]) -> dict[str, list[RawResult]]:
    """
    Jalan berurutan lewat 1 record set (H/P/O/R/L campur), lacak accession
    aktif lewat record P terakhir, kumpulkan R record di bawahnya.
    Return {accession: [RawResult, ...]}.
    """
    groups: dict[str, list[RawResult]] = {}
    current_accession: str | None = None
    for t in texts:
        rtype = t.split("|", 1)[0] if t else ""
        if rtype == "P":
            fields = t.split("|")
            current_accession = _extract_patient_id(fields) or None
            if current_accession:
                groups.setdefault(current_accession, [])
        elif rtype == "R" and current_accession:
            r = parse_r_record(t)
            if r:
                groups[current_accession].append(r)
    return groups


def parse_pending_worklist_astm(astm_content: str) -> dict[str, dict]:
    """
    Parse `worklists.astm_content` (format server, lihat
    WorklistController::generateAstmContent) -> per KODE PENDEK:
        {short_code: {"real_accession": str, "name": str, "tests": [device_test_code, ...]}}

    KODE PENDEK ("01", "02", ...) dipakai supaya operator SAGES200 cukup ketik
    2 digit di layar sentuh alat, bukan accession panjang ("P7474-7856") --
    root cause utama lambatnya input multi-pasien (lihat RESEARCH_LOG.md,
    update 2026-08-31). Nomornya urutan record P dlm astm_content ini, SAMA
    dgn kolom `sequence` di worklist_surat_hasil_labs (WorklistController::
    generateAstmContent increment $pSeq dgn urutan identik) -- jadi kalau
    nanti ada fitur "print worklist" di SiLAKES, kode di kertas = kode ini.

    `real_accession` (accession panjang asli "P{id}-{id}"/"S{id}") WAJIB
    disimpan supaya saat hasil masuk dari alat (yg akan echo balik kode
    pendek ini sbg Patient ID-nya), bridge bisa translate balik ke accession
    asli sebelum POST /v3/lis/agent/output -- server SiLAKES cuma kenal pola
    accession asli utk link ke record pasien/sampel yg benar.
    """
    lines = astm_content.replace("\r\n", "\n").split("\n")
    out: dict[str, dict] = {}
    current: str | None = None
    fallback_seq = 0  # cadangan KALAU field[1] tidak berupa angka valid (seharusnya tidak pernah terjadi)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        fields = line.split("|")
        rtype = fields[0]
        if rtype == "P":
            real_accession = fields[3].strip() if len(fields) > 3 else ""
            name = fields[5].strip() if len(fields) > 5 else ""
            if real_accession:
                # BUG NYATA (2026-09-01): sebelumnya kode pendek dihitung dari
                # POSISI record P dalam astm_content INI SAJA (selalu 1,2,3...
                # per worklist), bukan dibaca dari field[1] record P itu sendiri.
                # Server (WorklistController::generateAstmContent) SEKARANG
                # menomori kode BERKELANJUTAN per hari (bukan reset tiap
                # worklist, lihat catatan di sana) supaya worklist baru tidak
                # pernah rebutan kode dgn worklist lama hari yg sama -- kalau
                # bridge di sini tetap hitung posisi lokal, kode di PDF Lembar
                # Kerja (mis. "03") tidak akan pernah cocok dgn kode yg
                # DIHARAPKAN bridge (tetap "01") -- operator ketik kode dari
                # PDF, bridge tidak mengenalinya. WAJIB baca field[1] literal.
                try:
                    seq = int(fields[1].strip())
                except (IndexError, ValueError):
                    fallback_seq += 1
                    seq = fallback_seq
                current = f"{seq:02d}"
                out[current] = {
                    "real_accession": real_accession,
                    "name": name.replace("^", " ").strip(),
                    "tests": [],
                }
            else:
                current = None
        elif rtype == "O" and current:
            code = fields[4].strip() if len(fields) > 4 else ""
            if code:
                out[current]["tests"].append(code)
    return out


def split_record_set(texts: list[str]) -> dict:
    """
    Kelompokkan 1 set record (hasil AstmSession.read_record_set) berdasarkan tipe.
    Return {"H": [...], "P": [...], "Q": [...], "O": [...], "R": [...], "L": [...]}
    """
    out: dict[str, list[str]] = {"H": [], "P": [], "Q": [], "O": [], "R": [], "L": [], "C": []}
    for t in texts:
        rtype = t.split("|", 1)[0] if t else ""
        if rtype in out:
            out[rtype].append(t)
    return out


# ─── Build balasan Query -> dikirim LIVE ke MC-200 (dialek SAGES200) ───────

def build_query_response_lines(accession: str, tests: list[str], patient_name: str = "") -> list[str]:
    """
    Bangun baris H/P/O/L untuk dikirim balik ke MC-200 sbg jawaban atas Host
    Query. Format di sini DISALIN PERSIS dari contoh yang TERBUKTI berhasil
    di capture asli (RESEARCH_LOG.md Fase 2, respons host "TBM-LIMS" 11 Maret
    -- transaksi itu selesai NORMAL tanpa abort/NAK, dan hasil parsing-nya
    tercatat cocok di LIS_Back_Item.txt: "Patient_ID=PAT1 ... Num=2 ALB ALP").

    Perbedaan KRUSIAL dari draft awal (yg cuma asumsi generik, terbukti GAGAL
    saat live test -- MC-200 nge-loop query terus karena tidak berhasil
    parse balasannya): SEMUA test WAJIB digabung dalam 1 BARIS O record saja
    (dipisah backtick, tiap kode dibungkus ^^^), BUKAN 1 baris O per test.

        O|1|PAT1|IPat1|^^^ABCD1`^^^ALB`^^^TBIL|R|...

    accession ditaruh di field[2] P record DAN field[2] O record (posisi yg
    sama dgn contoh asli), supaya konsisten dgn field mana pun yg dipakai
    parser MC-200 utk Patient_ID.
    """
    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    lines = [f"H|\\^&|||SiLAKES^HOST|||||Host|||1|{timestamp}"]

    name = patient_name or accession
    # field[2]=accession, field[3]=accession, field[4]=(kosong/reserved),
    # field[5]=nama -- posisi ini PERSIS meniru contoh capture asli yg
    # terbukti berhasil (P|1|PAT1|LPAT1|LPAT13...|Joshi^Pramila^V|...).
    # Percobaan sebelumnya nama kebetulan taruh di field[4] (kegeser 1),
    # makanya field Name kosong walau test list sudah benar kebaca.
    lines.append(f"P|1|{accession}|{accession}||{name}|||||||||||||||||||||||")

    tests_field = "`".join(f"^^^{code}" for code in tests)
    lines.append(f"O|1|{accession}|{accession}|{tests_field}|R|||||||||||SERUM||||||||||||||||O")

    lines.append("L|1|N")
    return lines


# ─── Normalisasi hasil MC-200 -> format flat HS200-compatible ─────────────
# (dikirim ke /v3/lis/agent/output, TIDAK menyentuh parser server produksi)

def build_silakes_output_astm(
    device_code: str,
    accession: str,
    results: list[RawResult],
) -> str:
    """
    Bangun ulang isi .astm dgn layout field YANG SAMA seperti yang diharapkan
    WorklistController::parseOutputAstm() di server (lihat docstring method
    tsb, format "HS200"):

        H|\\^&|||HS200^V1.0|||||Host||P|1|{timestamp}
        P|1||{accession}||{accession}||||...
        O|1|||{method}|False||||||||||Serum|||||||||||||||
        R|1|{method}||{unit}||||{value}||||{completed_at}|
        L||N

    Bridge cukup ganti "HS200" -> device_code MC-200 di H record (server tidak
    parse H record sama sekali, jadi aman); yang KRUSIAL adalah layout field
    P dan R harus identik supaya parser server yang sudah tervalidasi tetap
    bisa baca tanpa perubahan apa pun.
    """
    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    lines = [f"H|\\^&|||{device_code}^V1.0|||||Host||P|1|{timestamp}"]
    lines.append(f"P|1||{accession}||{accession}||||")

    for seq, r in enumerate(results, start=1):
        lines.append(f"O|{seq}|||{r.method_code}|False||||||||||Serum|||||||||||||||")

    for seq, r in enumerate(results, start=1):
        completed = r.completed_at or timestamp
        lines.append(f"R|{seq}|{r.method_code}||{r.unit}||||{r.value}||||{completed}|")

    lines.append("L||N")
    return "\r\n".join(lines)
