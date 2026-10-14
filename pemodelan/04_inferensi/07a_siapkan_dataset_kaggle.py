#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
07a_siapkan_dataset_kaggle.py
=============================
Merakit satu berkas zip untuk diunggah sebagai Kaggle Dataset.

Kaggle memasang dataset secara read-only di /kaggle/input/<nama>/ dan membuka
isi zip secara otomatis, sehingga cukup satu berkas yang diunggah. Susunan
folder di dalam zip dipertahankan; notebook mencari berdasarkan nama berkas,
bukan berdasarkan susunan folder.

Dua mode:

    python 07a_siapkan_dataset_kaggle.py               # ringkas: 3 uid untuk uji kendali
    python 07a_siapkan_dataset_kaggle.py --lengkap     # semua 400 chip, untuk pilot & run penuh

Mode ringkas menghasilkan zip beberapa megabita saja sehingga cepat diunggah.
Mode lengkap sekitar 270 MB dan hanya perlu diunggah satu kali; setelah itu
dataset yang sama dipakai untuk seluruh tahap berikutnya.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("Butuh pandas. Jalankan:  pip install pandas")

AKAR = Path(r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\MANUVER SKRIPSI AFTER SENSUS")
SAMPEL_KECIL = AKAR / "KOMPONEN_3" / "Output Sampel" / "sampel_kecil.csv"
SAMPEL_BESAR = AKAR / "KOMPONEN_3" / "Output Sampel" / "sampel_besar.csv"
CHIP = AKAR / "KOMPONEN_3" / "Output Chip"
PROMPT = AKAR / "KOMPONEN_4" / "Output Prompt"

KELAS_UJI = ("no-damage", "major-damage", "destroyed")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--lengkap", action="store_true",
                   help="sertakan seluruh chip sampel besar (±270 MB)")
    p.add_argument("--per-kelas", type=int, default=1,
                   help="mode ringkas: jumlah uid per kelas (bawaan 1)")
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()

    for jalur in (SAMPEL_KECIL, CHIP, PROMPT):
        if not jalur.exists():
            sys.exit(f"Tidak ditemukan: {jalur}")

    if a.lengkap:
        sampel = pd.read_csv(SAMPEL_BESAR)
        nama = a.out or AKAR / "KOMPONEN_4" / "kaggle_skripsi_alif_LENGKAP.zip"
    else:
        s = pd.read_csv(SAMPEL_KECIL)
        potongan = [s[s["kelas_xbd"] == k].head(a.per_kelas) for k in KELAS_UJI]
        sampel = pd.concat(potongan, ignore_index=True)
        nama = a.out or AKAR / "KOMPONEN_4" / "kaggle_skripsi_alif_RINGKAS.zip"

    berkas_prompt = sorted(PROMPT.glob("prompt_*.txt")) + sorted(PROMPT.glob("manifes_*.json"))
    if not berkas_prompt:
        sys.exit(f"Tidak ada berkas prompt di {PROMPT}. Jalankan skrip 04 dulu.")

    nama.parent.mkdir(parents=True, exist_ok=True)
    hilang = []
    with zipfile.ZipFile(nama, "w", zipfile.ZIP_DEFLATED) as z:
        for f in berkas_prompt:
            z.write(f, f"Output Prompt/{f.name}")

        # sampel_kecil.csv adalah berkas yang dicari notebook untuk menentukan chip;
        # isinya diganti dengan potongan yang benar-benar ikut di dalam zip
        sementara = nama.parent / "_sampel_kaggle.csv"
        sampel.to_csv(sementara, index=False)
        z.write(sementara, "Output Sampel/sampel_kecil.csv")
        sementara.unlink()
        if a.lengkap:
            z.write(SAMPEL_KECIL, "Output Sampel/sampel_kecil_asli.csv")
            z.write(SAMPEL_BESAR, "Output Sampel/sampel_besar.csv")

        for _, r in sampel.iterrows():
            trio = [("pra", r["chip_pra"]), ("pasca", r["chip_pasca"]),
                    ("gabung", str(r["chip_pra"]).replace("_pra", "_gabung"))]
            for sub, berkas in trio:
                f = CHIP / sub / berkas
                if f.exists():
                    z.write(f, f"Output Chip/{sub}/{berkas}")
                else:
                    hilang.append(str(f))

    print("=" * 74)
    print(" DATASET KAGGLE SIAP")
    print("=" * 74)
    print(f" Mode        : {'LENGKAP' if a.lengkap else 'RINGKAS'}")
    print(f" Berkas      : {nama}")
    print(f" Ukuran      : {nama.stat().st_size / 1e6:.1f} MB")
    print(f" Chip        : {len(sampel)} uid x 3 varian")
    print(f" Prompt      : {len(berkas_prompt)} berkas")
    print("\n Komposisi kelas:")
    for kelas, n in sampel["kelas_xbd"].value_counts().items():
        print(f"   {kelas:<16}{n}")
    if hilang:
        print(f"\n !! {len(hilang)} chip tidak ditemukan:")
        for h in hilang[:10]:
            print("   ", h)
    print("=" * 74)
    print(" Unggah: kaggle.com > Datasets > New Dataset > seret berkas zip ini.")
    print(" Lalu di notebook: Add Input > pilih dataset tersebut.")


if __name__ == "__main__":
    main()
