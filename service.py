"""
BridgeService -- versi controllable dari bridge_server.py, dipakai GUI.

Logic ASTM/parsing/API call SAMA PERSIS dengan bridge_server.py (sudah
tervalidasi live terhadap MC-200 sungguhan di Fase 4) -- cuma dibungkus jadi
class yang bisa di-start()/stop() bersih dari thread lain (GUI event loop),
plus emit event terstruktur (log + stats) ke callback utk ditampilkan real-time.
"""
from __future__ import annotations

import logging
import socket
import threading
import time
from datetime import datetime, timezone

import astm_records as R
import settings as _settings
import silakes_client as api
from astm_protocol import AstmSession

log = logging.getLogger("bridge")


class BridgeService:
    # Kode pendek dianggap "milik worklist yang masih genuinely aktif" cuma
    # selama ini sejak terakhir di-cache. BUG NYATA (2026-09-01, laporan user):
    # _pending_cache tidak pernah dibersihkan sama sekali -- begitu worklist
    # lama (mis. sampel "Ahda", kode 01) selesai diproses, entrinya tetap
    # nyangkut selamanya. Server /v3/lis/agent/pending CUMA balikin worklist
    # status='pending' (langsung berubah jadi 'downloaded' begitu bridge poll
    # sekali), jadi TIDAK BISA dipakai sbg sinyal "worklist X masih dikerjakan"
    # -- worklist yg SEDANG aktif diproses operator pun sudah lama hilang dari
    # hasil /pending. Makanya deteksi kadaluarsa di sini pakai umur cache
    # (waktu sejak terakhir di-cache), bukan status server. 4 jam jauh lebih
    # dari cukup utk 1 sesi kerja 1 worklist (operator print lembar kerja,
    # ketik kode di alat, tunggu hasil -- biasanya selesai dlm hitungan menit
    # sampai puluhan menit), tapi cukup pendek utk memastikan worklist baru yg
    # dibuat berikutnya (kode ulang dari 01) tidak pernah tersandera worklist
    # lama yg sudah lama beres.
    CACHE_ENTRY_MAX_AGE_SECONDS = 4 * 3600

    def __init__(self, on_stats_change=None):
        """
        on_stats_change: callback(stats_dict) dipanggil tiap kali stats berubah
        (connections, results_sent, errors, dst). Log baris tetap lewat modul
        `logging` standar -- GUI attach logging.Handler sendiri (lihat gui_app.py).
        """
        self._stop_event = threading.Event()
        self._srv_socket: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._poll_thread: threading.Thread | None = None
        self._cache_lock = threading.Lock()
        self._pending_cache: dict[str, dict] = {}
        self._on_stats_change = on_stats_change

        self._started_at: datetime | None = None
        self.stats = {
            "running": False,
            "started_at": None,
            "connections_total": 0,
            "queries_answered": 0,
            "results_sent_ok": 0,
            "results_sent_error": 0,
            "last_error": None,
            "last_activity": None,
        }

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    def is_running(self) -> bool:
        return self.stats["running"]

    def start(self):
        if self.is_running():
            return
        self._stop_event.clear()
        s = _settings.get()

        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((s["listen_host"], int(s["listen_port"])))
        srv.listen(5)
        srv.settimeout(1.0)  # supaya accept() bisa dicek stop_event tiap 1 detik
        self._srv_socket = srv

        self._started_at = datetime.now(timezone.utc)
        self.stats.update({
            "running": True,
            "started_at": self._started_at.isoformat(),
            "connections_total": 0,
            "queries_answered": 0,
            "results_sent_ok": 0,
            "results_sent_error": 0,
            "last_error": None,
            "last_activity": None,
        })
        self._emit_stats()

        self._poll_thread = threading.Thread(target=self._poll_loop, name="poll", daemon=True)
        self._poll_thread.start()

        self._accept_thread = threading.Thread(target=self._accept_loop, name="accept", daemon=True)
        self._accept_thread.start()

        log.info("Bridge dimulai -- listen di %s:%s, device_code=%s", s["listen_host"], s["listen_port"], s["device_code"])

    def stop(self):
        if not self.is_running():
            return
        log.info("Menghentikan bridge...")
        self._stop_event.set()
        self.stats["running"] = False
        self._emit_stats()

        if self._srv_socket:
            try:
                self._srv_socket.close()
            except Exception:
                pass
            self._srv_socket = None

        log.info("Bridge dihentikan.")

    # ------------------------------------------------------------------ #
    # sampel manual (dikirim langsung dari form GUI, bypass worklist SiLAKES)
    # ------------------------------------------------------------------ #
    def add_manual_sample(self, accession: str, name: str, tests: list[str]) -> dict:
        """
        Selipkan 1 entri ke _pending_cache TANPA lewat worklist SiLAKES --
        dipakai form "Kirim Sampel" di GUI utk uji coba/pemakaian ad-hoc
        langsung dari bridge. worklist_id sengaja None (tidak ada baris
        worklist SiLAKES asli) -- mark_processing() akan gagal dgn wajar
        (sudah ditangani try/except di _handle_query) kalau dipanggil utk
        entri jenis ini; itu memang diharapkan, bukan bug.

        CATATAN: kalau MC-200 nanti kirim balik hasil utk accession ini,
        POST /v3/lis/agent/output ke SiLAKES CUMA akan sukses tersimpan
        kalau accession-nya match pola nyata "P{patient_id}-{shl_id}" atau
        "S{lab_sample_id}" yang BENAR ADA di database SiLAKES (lihat
        parseOutputAstm() di WorklistController.php). Accession sembarangan
        (mis. utk sekadar tes protokol) akan ditolak API di tahap itu --
        pengiriman ke alat & balasan Query tetap jalan normal, cuma
        penyimpanan hasil akhir ke SiLAKES yang butuh accession valid.
        """
        accession = (accession or "").strip()
        if not accession:
            raise ValueError("Patient ID / Sample ID tidak boleh kosong.")
        if not tests:
            raise ValueError("Pilih minimal 1 test.")

        with self._cache_lock:
            self._pending_cache[accession] = {
                "worklist_id": None,
                "filename": f"manual_{accession}.astm",
                "name": name or accession,
                "tests": list(tests),
                "cached_at": time.time(),
            }
        log.info("Sampel manual ditambahkan ke cache: accession=%s tests=%s", accession, tests)
        return {"accession": accession, "tests": tests}

    # ------------------------------------------------------------------ #
    # internal helpers
    # ------------------------------------------------------------------ #
    def _emit_stats(self):
        if self._on_stats_change:
            try:
                self._on_stats_change(dict(self.stats))
            except Exception:
                pass

    def _touch_activity(self):
        self.stats["last_activity"] = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------ #
    # polling worklist pending
    # ------------------------------------------------------------------ #
    def _poll_loop(self):
        s = _settings.get()
        log.info("Poll thread mulai, interval=%.1fs, device_code=%s", s["poll_interval_seconds"], s["device_code"])
        while not self._stop_event.is_set():
            try:
                s = _settings.get()
                worklists = api.get_pending(s["device_code"])
                for wl in worklists:
                    wl_id = wl["id"]
                    filename = wl["filename"]
                    astm_content = wl.get("astm_content") or ""
                    parsed = R.parse_pending_worklist_astm(astm_content)

                    with self._cache_lock:
                        for short_code, info in parsed.items():
                            existing = self._pending_cache.get(short_code)
                            if existing and existing.get("worklist_id") not in (None, wl_id):
                                age = time.time() - existing.get("cached_at", 0)
                                if age < self.CACHE_ENTRY_MAX_AGE_SECONDS:
                                    # Kode pendek ini kepakai worklist LAIN yg masih
                                    # cukup baru (kemungkinan genuinely masih
                                    # dikerjakan bersamaan) -- jangan timpa diam-diam,
                                    # cukup log biar kelihatan.
                                    log.warning(
                                        "Kode pendek %s tabrakan: worklist #%s (umur %.0f menit) vs #%s -- entri lama dipertahankan.",
                                        short_code, existing.get("worklist_id"), age / 60, wl_id,
                                    )
                                    continue
                                # Entri lama sudah lebih dari CACHE_ENTRY_MAX_AGE_SECONDS
                                # -- worklist itu nyaris pasti sudah lama beres/
                                # ditinggalkan, aman digantikan worklist baru ini.
                                log.info(
                                    "Kode pendek %s sebelumnya milik worklist #%s (umur %.0f menit, kadaluarsa) -- digantikan worklist baru #%s.",
                                    short_code, existing.get("worklist_id"), age / 60, wl_id,
                                )
                            self._pending_cache[short_code] = {
                                "worklist_id": wl_id,
                                "filename": filename,
                                "name": info["name"],
                                "tests": info["tests"],
                                "real_accession": info["real_accession"],
                                "cached_at": time.time(),
                            }

                    if parsed:
                        log.info("Worklist #%s (%s) di-cache: %d kode pendek", wl_id, filename, len(parsed))
                        api.mark_downloaded(wl_id)
                        api.post_monitor_event("info", f"Worklist {filename} diambil bridge ({len(parsed)} pasien)")
            except Exception as e:
                log.warning("Poll gagal: %s", e)

            self._stop_event.wait(_settings.get()["poll_interval_seconds"])

    # ------------------------------------------------------------------ #
    # TCP accept loop
    # ------------------------------------------------------------------ #
    def _accept_loop(self):
        srv = self._srv_socket
        while not self._stop_event.is_set():
            try:
                sock, addr = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break  # socket ditutup (stop() dipanggil)

            t = threading.Thread(target=self._handle_connection, args=(sock, addr), daemon=True)
            t.start()

    def _synth_filename(self, accession: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = accession.replace("/", "_").replace(" ", "_")
        return f"mc200_{safe}_{ts}.astm"

    def _handle_query(self, session: AstmSession, q_texts: list[str]):
        s = _settings.get()
        for qtext in q_texts:
            accession = R.parse_query_record(qtext)
            if not accession:
                log.warning("Q record tidak bisa di-parse: %r", qtext)
                continue

            with self._cache_lock:
                entry = self._pending_cache.get(accession)
                fallback_used = False
                if not entry and len(self._pending_cache) == 1:
                    # MC-200 (tombol LIS di Schedule) ternyata query pakai ID
                    # internalnya sendiri (mis. "S10001"), BUKAN accession
                    # custom kita ("P{id}-{id}") -- terbukti dari live test.
                    # Selama cuma ada 1 worklist pending, aman diasumsikan itu
                    # yang dimaksud. TODO: cari tahu pola penomoran S##### ini
                    # (kemungkinan nomor urut slot Schedule lokal SAGES200)
                    # supaya matching bisa presisi kalau nanti ada >1 worklist.
                    only_accession = next(iter(self._pending_cache))
                    entry = self._pending_cache[only_accession]
                    fallback_used = True
                    log.warning(
                        "Accession dari MC-200 (%s) tidak cocok cache, tapi cuma ada 1 worklist pending (%s) -- dipakai sbg fallback.",
                        accession, only_accession,
                    )

            if not entry or not entry["tests"]:
                log.info("Query utk accession=%s: TIDAK ADA di cache worklist pending.", accession)
                api.post_monitor_event("warning", f"MC-200 tanya accession {accession}, tidak ditemukan di worklist pending SiLAKES.")
                continue

            reply_accession = accession  # WAJIB balas pakai ID yg MC-200 query, bukan accession asli kita,
                                          # supaya MC-200 mengenali balasannya sbg jawaban atas query ini.
            log.info(
                "Query utk accession=%s%s -> balas %d test: %s",
                accession, " (fallback)" if fallback_used else "", len(entry["tests"]), entry["tests"],
            )
            lines = R.build_query_response_lines(reply_accession, entry["tests"], entry["name"])

            ok = session.send_enq_and_wait_ack()
            if not ok:
                log.error("MC-200 tidak ACK saat bridge coba jadi sender (balas Query) utk accession=%s", accession)
                api.post_monitor_event("error", f"MC-200 tidak merespons ENQ balasan utk accession {accession}")
                continue

            try:
                session.send_record_set(lines)
            except Exception as e:
                # Ini SATU-SATUNYA kegagalan yang berarti alat tidak menerima data.
                log.error("Gagal kirim balasan ASTM ke MC-200 utk accession=%s: %s", accession, e)
                api.post_monitor_event("error", f"Gagal kirim balasan ke alat utk {accession}: {e}")
                continue

            log.info("Berhasil kirim balasan Query utk accession=%s", accession)
            self.stats["queries_answered"] += 1
            self._touch_activity()
            self._emit_stats()

            try:
                api.mark_processing(entry["filename"], s["device_code"])
                api.post_monitor_event("processing", f"Worklist utk {accession} dikirim ke MC-200, alat mulai proses.")
            except Exception as e:
                # WAJAR gagal: status update ke SiLAKES ini per-WORKLIST, jadi
                # query ke-2/3/dst dlm worklist yg sama (atau sampel manual yg
                # tak punya baris worklist asli) memang akan selalu ditolak
                # API krn status sudah maju dari query pertama. Data ASTM ke
                # alat SUDAH terkirim sukses di atas -- jangan log ERROR di
                # sini, supaya kegagalan ASTM asli (di atas) tidak tertutupi
                # noise ini saat menangani puluhan sampel.
                log.debug("mark_processing gagal (biasanya wajar, lihat komentar kode) utk accession=%s: %s", accession, e)

    def _handle_results(self, all_texts: list[str]):
        s = _settings.get()
        groups = R.group_results_by_patient(all_texts)
        for reported_id, results in groups.items():
            if not results:
                continue

            # `reported_id` adalah apa pun yg alat echo balik sbg Patient ID-nya --
            # kalau ini kode pendek ("01") dari worklist, translate dulu ke
            # accession asli ("P7474-7856"/"S1") pakai cache, krn parseOutputAstm()
            # server CUMA kenal pola accession asli utk link ke record yg benar.
            with self._cache_lock:
                entry = self._pending_cache.get(reported_id)
            real_accession = entry["real_accession"] if entry and "real_accession" in entry else reported_id

            log.info("Hasil masuk utk kode=%s (accession=%s): %d parameter", reported_id, real_accession, len(results))

            astm_out = R.build_silakes_output_astm(s["device_code"], real_accession, results)
            filename = self._synth_filename(real_accession)
            log.debug("astm_content yg akan di-POST (accession=%s):\n%s", real_accession, astm_out)

            try:
                resp = api.post_output(filename, astm_out, s["device_code"])
                log.info("POST /output sukses utk %s -> %s", real_accession, resp.get("message") or resp)
                api.post_monitor_event("success", f"Hasil {real_accession} ({len(results)} parameter) berhasil diproses SiLAKES.")
                self.stats["results_sent_ok"] += 1
                self._touch_activity()
                self._emit_stats()
            except Exception as e:
                log.error("POST /output GAGAL utk accession=%s: %s", real_accession, e)
                api.post_monitor_event("error", f"Gagal kirim hasil {real_accession} ke SiLAKES: {e}")
                self.stats["results_sent_error"] += 1
                self.stats["last_error"] = f"accession {real_accession}: {e}"
                self._touch_activity()
                self._emit_stats()

    def _handle_connection(self, sock: socket.socket, addr):
        log.info("Koneksi masuk dari %s", addr)
        self.stats["connections_total"] += 1
        self._touch_activity()
        self._emit_stats()

        s = _settings.get()
        session = AstmSession(sock, timeout=s["socket_timeout_seconds"])
        try:
            # MC-200 bisa kirim BEBERAPA siklus ENQ...EOT berturut-turut di 1
            # koneksi TCP yang sama (mis. query pasien 1, lalu query pasien 2,
            # dst dalam 1 sesi Receive multi-pasien) sebelum akhirnya menutup
            # koneksi sendiri. Kalau bridge menutup socket segera setelah siklus
            # PERTAMA, ENQ pasien berikutnya yang dikirim MC-200 di koneksi yg
            # sama kena RST dari OS kita -- persis gejala "LIS send error:10054"
            # + "ERROR_RECV_FAILED" di log internal alat (ketemu 2026-08-31, alat
            # cuma query ulang pasien 1 terus, pasien 2+ tidak pernah sampai ke
            # bridge). Maka loop di sini sampai MC-200 sendiri yang menutup
            # (ConnectionError) atau idle (socket.timeout).
            while True:
                if not session.wait_enq():
                    log.warning("Byte pertama dari %s bukan ENQ, tutup koneksi.", addr)
                    break
                session.send_ack()

                texts = session.read_record_set()
                log.info("Terima %d record dari %s", len(texts), addr)
                for t in texts:
                    log.debug("  << %s", t)

                grouped = R.split_record_set(texts)

                if grouped["Q"]:
                    self._handle_query(session, grouped["Q"])

                if grouped["R"]:
                    self._handle_results(texts)

                if not grouped["Q"] and not grouped["R"]:
                    log.info("Record set dari %s tidak berisi Q maupun R (mis. cek koneksi H/L saja).", addr)

        except ConnectionError as e:
            log.info("Koneksi %s ditutup oleh MC-200: %s", addr, e)
        except socket.timeout:
            log.info("Koneksi %s idle (tidak ada aktivitas lagi), ditutup.", addr)
        except Exception as e:
            log.exception("Error tak terduga menangani koneksi %s: %s", addr, e)
        finally:
            try:
                sock.close()
            except Exception:
                pass
            log.info("Koneksi %s ditutup.", addr)
