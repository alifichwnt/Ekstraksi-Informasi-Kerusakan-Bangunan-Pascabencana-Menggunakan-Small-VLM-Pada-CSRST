#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06a_siapkan_smoke_zip.py
========================
Menyiapkan `smoke.zip` untuk diunggah ke Colab pada sel 4 notebook smoke test.

Isinya: dua berkas prompt, potongan sampel berisi N chip pertama, dan ketiga
varian chip untuk N chip tersebut. Dijalankan lokal, tanpa GPU.

    python 06a_siapkan_smoke_zip.py
    python 06a_siapkan_smoke_zip.py --n 5
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
SAMPEL = AKAR / "KOMPONEN_3" / "Output Sampel" / "sampel_kecil.csv"
CHIP = AKAR / "KOMPONEN_3" / "Output Chip"
PROMPT = AKAR / "KOMPONEN_4" / "Output Prompt"
KELUARAN = AKAR / "KOMPONEN_4" / "smoke.zip"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=5, help="jumlah chip (bawaan 5)")
    p.add_argument("--sampel", type=Path, default=SAMPEL)
    p.add_argument("--chip", type=Path, default=CHIP)
    p.add_argument("--prompt", type=Path, default=PROMPT)
    p.add_argument("--out", type=Path, default=KELUARAN)
    a = p.parse_args()

    for jalur in (a.sampel, a.chip, a.prompt):
        if not jalur.exists():
            sys.exit(f"Tidak ditemukan: {jalur}")

    berkas_prompt = sorted(a.prompt.glob("prompt_a_*.txt")) + \
                    sorted(a.prompt.glob("prompt_b_*.txt"))
    if len(berkas_prompt) < 2:
        sys.exit(f"Prompt a dan b tidak lengkap di {a.prompt}. Jalankan skrip 04 dulu.")

    sampel = pd.read_csv(a.sampel).head(a.n)
    a.out.parent.mkdir(parents=True, exist_ok=True)

    hilang = []
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in berkas_prompt:
            z.write(f, f.name)
        potongan = a.out.parent / "_sampel_smoke.csv"
        sampel.to_csv(potongan, index=False)
        z.write(potongan, "sampel_kecil.csv")
        potongan.unlink()

        for _, r in sampel.iterrows():
            trio = [("pra", r["chip_pra"]), ("pasca", r["chip_pasca"]),
                    ("gabung", r["chip_pra"].replace("_pra", "_gabung"))]
            for sub, nama in trio:
                f = a.chip / sub / nama
                if f.exists():
                    z.write(f, f"{sub}/{nama}")
                else:
                    hilang.append(str(f))

    print("=" * 74)
    print(" SMOKE ZIP SIAP")
    print("=" * 74)
    print(f" Berkas      : {a.out}")
    print(f" Ukuran      : {a.out.stat().st_size / 1e6:.2f} MB")
    print(f" Chip        : {len(sampel)} uid x 3 varian")
    print(f" Prompt      : {', '.join(f.name for f in berkas_prompt)}")
    print("\n Komposisi kelas chip yang ikut:")
    for kelas, n in sampel["kelas_xbd"].value_counts().items():
        print(f"   {kelas:<16}{n}")
    if hilang:
        print(f"\n !! {len(hilang)} berkas chip tidak ditemukan:")
        for h in hilang[:10]:
            print("   ", h)
    print("=" * 74)
    print(" Unggah berkas ini pada sel 4 notebook 06_smoke_test_svlm.ipynb")


if __name__ == "__main__":
    main()
