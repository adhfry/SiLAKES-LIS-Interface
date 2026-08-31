"""
Build "SiLAKES LIS Interface" jadi 1 file .exe standalone (Windows).

Urutan:
  1. `npm run build` di gui/ -> hasil gui/dist/ (Vue 3 production build)
  2. PyInstaller (onefile) membundel gui_app.py + service.py + astm_* +
     gui/dist/ jadi 1 executable di dist/SiLAKES-LIS-Interface.exe

Jalankan:  python build_exe.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
GUI_DIR = ROOT / "gui"
DIST_DIR = GUI_DIR / "dist"


def run(cmd: list[str], cwd: Path):
    print(f"\n$ {' '.join(cmd)}   (cwd={cwd})")
    result = subprocess.run(cmd, cwd=str(cwd), shell=(sys.platform == "win32"))
    if result.returncode != 0:
        print(f"GAGAL (exit {result.returncode}): {' '.join(cmd)}")
        sys.exit(result.returncode)


def main():
    print("=== 1/2: Build frontend Vue (npm run build) ===")
    run(["npm", "run", "build"], cwd=GUI_DIR)

    if not (DIST_DIR / "index.html").exists():
        print(f"ERROR: {DIST_DIR / 'index.html'} tidak ditemukan setelah build frontend.")
        sys.exit(1)

    print("\n=== 2/2: Build executable (PyInstaller) ===")
    # Bersihkan hasil build lama supaya tidak ada file basi ikut ke-bundle
    for stale in (ROOT / "build", ROOT / "dist"):
        if stale.exists():
            shutil.rmtree(stale)

    run(
        [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "SiLAKES-LIS-Interface.spec",
        ],
        cwd=ROOT,
    )

    exe_path = ROOT / "dist" / "SiLAKES-LIS-Interface" / "SiLAKES-LIS-Interface.exe"
    if exe_path.exists():
        print(f"\nBUILD SELESAI: {exe_path}")
        print("Salin seluruh folder 'dist/SiLAKES-LIS-Interface/' ke PC target (bukan cuma file .exe-nya).")
    else:
        print("\nBuild PyInstaller selesai tapi .exe tidak ditemukan di lokasi yang diharapkan -- cek output di atas.")


if __name__ == "__main__":
    main()
