"""
Bridge PoC: SiLAKES API <-> MC-200 (SAGES200).

Jalan sbg TCP server ASTM di jaringan lokal lab (lihat ARCHITECTURE.md untuk
alasan kenapa harus begini, bukan API<->MC-200 langsung). MC-200 selalu jadi
initiator koneksi (terbukti Fase 2), jadi bridge ini WAJIB jadi server yang
listen, bukan client.

Alur:
  - Thread polling: ambil worklist 'pending' dari SiLAKES tiap
    POLL_INTERVAL_SECONDS, cache di memori per accession, mark 'downloaded'.
  - Thread per koneksi MC-200: terima ENQ -> baca record set.
      * Kalau ada Q (Host Query)  -> balas jadi sender, kirim worklist yg
        di-cache utk accession itu (kalau ada).
      * Kalau ada R (result)      -> normalisasi ke format HS200-compatible,
        POST ke /v3/lis/agent/output.

STATUS: PoC utk validasi protokol (Fase 3). Belum battle-tested utk
concurrency tinggi / reconnect handling penuh -- cukup utk 1 instrumen.
"""
from __future__ import annotations

import logging
import socket
import threading
import time
from datetime import datetime

import astm_records as R
import config
import silakes_client as api
from astm_protocol import AstmSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s",
)
log = logging.getLogger("bridge")

# accession -> {"worklist_id": int, "filename": str, "name": str, "tests": [str, ...]}
_cache_lock = threading.Lock()
_pending_cache: dict[str, dict] = {}


def poll_loop():
    log.info("Poll thread mulai, interval=%.1fs, device_code=%s", config.POLL_INTERVAL_SECONDS, config.DEVICE_CODE)
    while True:
        try:
            worklists = api.get_pending(config.DEVICE_CODE)
            for wl in worklists:
                wl_id = wl["id"]
                filename = wl["filename"]
                astm_content = wl.get("astm_content") or ""
                parsed = R.parse_pending_worklist_astm(astm_content)

                with _cache_lock:
                    for accession, info in parsed.items():
                        _pending_cache[accession] = {
                            "worklist_id": wl_id,
                            "filename": filename,
                            "name": info["name"],
                            "tests": info["tests"],
                        }

                if parsed:
                    log.info("Worklist #%s (%s) di-cache: %d accession", wl_id, filename, len(parsed))
                    api.mark_downloaded(wl_id)
                    api.post_monitor_event("info", f"Worklist {filename} diambil bridge ({len(parsed)} pasien)")
        except Exception as e:
            log.warning("Poll gagal: %s", e)

        time.sleep(config.POLL_INTERVAL_SECONDS)


def _synth_filename(accession: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = accession.replace("/", "_").replace(" ", "_")
    return f"mc200_{safe}_{ts}.astm"


def handle_query(session: AstmSession, q_texts: list[str]):
    for qtext in q_texts:
        accession = R.parse_query_record(qtext)
        if not accession:
            log.warning("Q record tidak bisa di-parse: %r", qtext)
            continue

        with _cache_lock:
            entry = _pending_cache.get(accession)

        if not entry or not entry["tests"]:
            log.info("Query utk accession=%s: TIDAK ADA di cache worklist pending. Diabaikan (alat akan lihat kosong).", accession)
            api.post_monitor_event("warning", f"MC-200 tanya accession {accession}, tidak ditemukan di worklist pending SiLAKES.")
            continue

        log.info("Query utk accession=%s -> balas %d test: %s", accession, len(entry["tests"]), entry["tests"])
        lines = R.build_query_response_lines(accession, entry["tests"], entry["name"])

        ok = session.send_enq_and_wait_ack()
        if not ok:
            log.error("MC-200 tidak ACK saat bridge coba jadi sender (balas Query) utk accession=%s", accession)
            api.post_monitor_event("error", f"MC-200 tidak merespons ENQ balasan utk accession {accession}")
            continue

        try:
            session.send_record_set(lines)
            log.info("Berhasil kirim balasan Query utk accession=%s", accession)
            api.mark_processing(entry["filename"], config.DEVICE_CODE)
            api.post_monitor_event("processing", f"Worklist utk {accession} dikirim ke MC-200, alat mulai proses.")
        except Exception as e:
            log.error("Gagal kirim balasan Query utk accession=%s: %s", accession, e)
            api.post_monitor_event("error", f"Gagal kirim balasan Query utk {accession}: {e}")


def handle_results(all_texts: list[str]):
    groups = R.group_results_by_patient(all_texts)
    for accession, results in groups.items():
        if not results:
            continue
        log.info("Hasil masuk utk accession=%s: %d parameter", accession, len(results))

        astm_out = R.build_silakes_output_astm(config.DEVICE_CODE, accession, results)
        filename = _synth_filename(accession)
        log.info("astm_content yg akan di-POST (accession=%s):\n%s", accession, astm_out)

        try:
            resp = api.post_output(filename, astm_out, config.DEVICE_CODE)
            log.info("POST /output sukses utk %s -> %s", accession, resp.get("message") or resp)
            api.post_monitor_event("success", f"Hasil {accession} ({len(results)} parameter) berhasil diproses SiLAKES.")
        except Exception as e:
            log.error("POST /output GAGAL utk accession=%s: %s", accession, e)
            api.post_monitor_event("error", f"Gagal kirim hasil {accession} ke SiLAKES: {e}")


def handle_connection(sock: socket.socket, addr):
    log.info("Koneksi masuk dari %s", addr)
    session = AstmSession(sock)
    try:
        if not session.wait_enq():
            log.warning("Byte pertama dari %s bukan ENQ, tutup koneksi.", addr)
            return
        session.send_ack()

        texts = session.read_record_set()
        log.info("Terima %d record dari %s", len(texts), addr)
        for t in texts:
            log.debug("  << %s", t)

        grouped = R.split_record_set(texts)

        if grouped["Q"]:
            handle_query(session, grouped["Q"])

        if grouped["R"]:
            handle_results(texts)  # perlu urutan asli (P mendahului R), bukan versi grouped

        if not grouped["Q"] and not grouped["R"]:
            log.info("Record set dari %s tidak berisi Q maupun R (mis. cek koneksi H/L saja).", addr)

    except ConnectionError as e:
        log.warning("Koneksi %s putus: %s", addr, e)
    except Exception as e:
        log.exception("Error tak terduga menangani koneksi %s: %s", addr, e)
    finally:
        try:
            sock.close()
        except Exception:
            pass
        log.info("Koneksi %s ditutup.", addr)


def main():
    if not config.LIS_SECRET_KEY:
        log.warning("LIS_SECRET_KEY belum diisi (config.py / env BRIDGE nya) -- panggilan API akan gagal 401.")

    poll_thread = threading.Thread(target=poll_loop, name="poll", daemon=True)
    poll_thread.start()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((config.LISTEN_HOST, config.LISTEN_PORT))
    srv.listen(5)
    log.info("Bridge ASTM TCP server listen di %s:%d", config.LISTEN_HOST, config.LISTEN_PORT)

    try:
        while True:
            sock, addr = srv.accept()
            t = threading.Thread(target=handle_connection, args=(sock, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        log.info("Dihentikan oleh user (Ctrl+C).")
    finally:
        srv.close()


if __name__ == "__main__":
    main()
