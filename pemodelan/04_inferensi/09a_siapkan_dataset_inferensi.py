#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
09a_siapkan_dataset_inferensi.py
================================
Merakit DUA berkas zip untuk diunggah sebagai Kaggle Dataset.

  1. kaggle_chip_400.zip
     Chip pra dan pasca untuk 400 bangunan sampel besar, beserta sampel_besar.csv
     dan sampel_kecil.csv. Isinya tidak bergantung pada fitur maupun prompt,
     jadi CUKUP DIUNGGAH SATU KALI.

  2. kaggle_paket_eksperimen_v<versi>_<sidik>.zip
     konfigurasi_fitur.json, prompt v4, manifes prompt, 05_parser_keluaran.py.
     Ukurannya beberapa kilobita. Zip ini dibuat ulang SETIAP KALI konfigurasi
     atau prompt berubah (misalnya setelah penilaian dosen masuk), lalu
     diunggah sebagai VERSI BARU dari dataset paket di Kaggle.

Pemisahan ini supaya perubahan prompt tidak memaksa mengunggah ulang 180 MB chip.

Penggunaan (dari folder KOMPONEN_4):
    python 09a_siapkan_dataset_inferensi.py            # buat keduanya
    python 09a_siapkan_dataset_inferensi.py --paket    # hanya paket eksperimen
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("Butuh pandas. Jalankan:  pip install pandas")

AKAR = Path(r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\MANUVER SKRIPSI AFTER SENSUS")
K3 = AKAR / "KOMPONEN_3"
K4 = AKAR / "KOMPONEN_4"
SAMPEL_BESAR = K3 / "Output Sampel" / "sampel_besar.csv"
SAMPEL_KECIL = K3 / "Output Sampel" / "sampel_kecil.csv"
CHIP = K3 / "Output Chip"
PROMPT = K4 / "Output Prompt"
KONFIG = K4 / "konfigurasi_fitur.json"
PARSER = K4 / "05_parser_keluaran.py"
SUSUN = K4 / "04_susun_prompt.py"


def zip_chip(out: Path) -> None:
    sampel = pd.read_csv(SAMPEL_BESAR)
    hilang = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(SAMPEL_BESAR, "Output Sampel/sampel_besar.csv")
        z.write(SAMPEL_KECIL, "Output Sampel/sampel_kecil.csv")
        for _, r in sampel.iterrows():
            for sub, berkas in (("pra", r["chip_pra"]), ("pasca", r["chip_pasca"])):
                f = CHIP / sub / berkas
                if f.exists():
                    z.write(f, f"Output Chip/{sub}/{berkas}")
                else:
                    hilang.append(str(f))
    print(f" [chip]  {out.name}  {out.stat().st_size / 1e6:.1f} MB  "
          f"({len(sampel)} bangunan x 2 citra)")
    if hilang:
        print(f"   !! {len(hilang)} chip tidak ditemukan, contoh: {hilang[:3]}")


def zip_paket(out_dir: Path) -> Path:
    k = json.loads(KONFIG.read_text(encoding="utf-8"))
    manifes = sorted(PROMPT.glob("manifes_v*_*.json"), key=lambda f: f.stat().st_mtime)
    if not manifes:
        sys.exit("Tidak ada manifes prompt v4. Jalankan 04_susun_prompt.py dulu.")
    m = json.loads(manifes[-1].read_text(encoding="utf-8"))
    if m["fitur_terpilih"] != k["seleksi"]["terpilih"]:
        sys.exit("Manifes prompt tidak cocok dengan konfigurasi saat ini. "
                 "Jalankan ulang 04_susun_prompt.py.")
    nama = out_dir / f"kaggle_paket_eksperimen_v{m['versi_prompt']}_{m['sidik_fitur']}.zip"
    with zipfile.ZipFile(nama, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(KONFIG, "paket/konfigurasi_fitur.json")
        z.write(PARSER, "paket/05_parser_keluaran.py")
        z.write(SUSUN, "paket/04_susun_prompt.py")
        z.write(manifes[-1], f"paket/{manifes[-1].name}")
        for jenis in ("fitur", "kelas"):
            f = PROMPT / m["prompt"][jenis]["berkas"]
            z.write(f, f"paket/{f.name}")
    print(f" [paket] {nama.name}  {nama.stat().st_size / 1e3:.1f} KB  "
          f"(prompt v{m['versi_prompt']}, sidik {m['sidik_fitur']})")
    return nama


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--paket", action="store_true", help="hanya buat paket eksperimen")
    p.add_argument("--out", type=Path, default=K4)
    a = p.parse_args()
    for f in (SAMPEL_BESAR, SAMPEL_KECIL, KONFIG, PARSER, PROMPT):
        if not f.exists():
            sys.exit(f"Tidak ditemukan: {f}")
    a.out.mkdir(parents=True, exist_ok=True)
    print("=" * 74)
    if not a.paket:
        zip_chip(a.out / "kaggle_chip_400.zip")
    zip_paket(a.out)
    print("=" * 74)
    print(" Unggah ke Kaggle: Datasets > New Dataset.")
    print("  - kaggle_chip_400.zip        -> dataset baru, misal 'skripsi-alif-chip'")
    print("  - kaggle_paket_eksperimen_*  -> dataset baru, misal 'skripsi-alif-paket'")
    print("    (bila prompt berubah: buka dataset paket > New Version > unggah zip baru)")


if __name__ == "__main__":
    main()
