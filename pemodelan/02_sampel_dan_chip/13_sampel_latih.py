#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
13_sampel_latih.py
==================
Menarik SAMPEL LATIH dan SAMPEL VALIDASI untuk lengan fine-tuning (LoRA) SVLM.

Prinsip pemisahan data (wajib untuk kesahihan evaluasi):
  * Sampel uji (400 bangunan sampel besar, termasuk 40 sampel kecil dan 15 set
    pengembangan) TIDAK disentuh.
  * Pemisahan pada tingkat TILE: bangunan latih hanya diambil dari tile yang tidak
    memuat satu pun bangunan uji. Jadi tidak ada piksel, bangunan tetangga, maupun
    petak yang sama antara data latih dan data uji (mencegah kebocoran spasial).
  * Tugas yang dilatih: KELAS kerusakan dari citra PASCA saja (sama dengan panggilan
    kelas pada prompt v4). Citra pasca seluruh tile Palu berasal dari satu akuisisi
    (2018-10-01), sehingga tile di luar grup akuisisi terkunci boleh dipakai untuk
    pelatihan tanpa mengubah kondisi citra pasca. Grup akuisisi pra tetap dicatat.
  * Aturan kerangka sama dengan skrip 02: jendela 128 px utuh di dalam tile, sisi
    terpanjang <= 128 px, kelas minor-damage dan un-classified dibuang.

Komposisi (benih 42):
  major-damage : seluruh yang tersedia di tile latih (kelas paling langka)
  destroyed    : 300, maksimal 15 per tile
  no-damage    : 300, maksimal 15 per tile
  Validasi     : 15 persen per kelas (tingkat bangunan), hanya untuk memantau
                 pelatihan dan memilih epoch; bukan pengujian.

Nama chip diberi awalan 'L_' agar tidak pernah tertukar dengan chip uji di Kaggle.

Penggunaan (dari folder KOMPONEN_4):
    python 13_sampel_latih.py                 # tarik sampel -> KOMPONEN_3\\Output Sampel Latih
    (lalu ekstraksi chip dengan skrip 03, lihat pesan di akhir)
    python 13_sampel_latih.py --zip           # rakit zip untuk Kaggle setelah chip jadi
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("Butuh pandas. Jalankan:  pip install pandas")

AKAR = Path(os.environ.get("SKRIPSI_AKAR",
             r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\MANUVER SKRIPSI AFTER SENSUS"))
INV = AKAR / "KOMPONEN_2" / "Output Inventarisasi"
SAMPEL_BESAR = AKAR / "KOMPONEN_3" / "Output Sampel" / "sampel_besar.csv"
OUT = AKAR / "KOMPONEN_3" / "Output Sampel Latih"
CHIP_LATIH = AKAR / "KOMPONEN_3" / "Output Chip Latih"
ZIP = AKAR / "KOMPONEN_4" / "kaggle_latih.zip"

BENIH = 42
SISI_JENDELA, UKURAN_TILE = 128, 1024
KELAS = ["no-damage", "major-damage", "destroyed"]
TARGET = {"no-damage": 300, "destroyed": 300, "major-damage": None}   # None = semua
KUOTA_TILE = {"no-damage": 15, "destroyed": 15, "major-damage": None}
PROPORSI_VALIDASI = 0.15


def tarik() -> None:
    b = pd.read_csv(INV / "inventaris_palu_bangunan.csv")
    t = pd.read_csv(INV / "inventaris_palu_tile.csv")
    uji = pd.read_csv(SAMPEL_BESAR)
    tile_uji = set(uji["tile"])

    L = ["JEJAK PENYARINGAN SAMPEL LATIH", f"  populasi berlabel               {len(b):>7,}"]
    b = b.merge(t[["tile", "pra_tanggal"]], on="tile", how="left")
    b["grup_pra"] = b["pra_tanggal"].str[:10]
    b = b[b["kelas_xbd"].isin(KELAS)]
    L.append(f"  3 kelas dipakai                 {len(b):>7,}")
    r = SISI_JENDELA / 2
    b = b[(b.pusat_x_px - r >= 0) & (b.pusat_y_px - r >= 0) &
          (b.pusat_x_px + r <= UKURAN_TILE) & (b.pusat_y_px + r <= UKURAN_TILE) &
          (b.sisi_terpanjang_px <= SISI_JENDELA)]
    L.append(f"  jendela utuh & <= 128 px        {len(b):>7,}")
    b = b[~b["tile"].isin(tile_uji)]
    L.append(f"  di luar {len(tile_uji)} tile uji             {len(b):>7,}  ({b.tile.nunique()} tile)")

    potong = []
    for k in KELAS:
        sub = b[b.kelas_xbd == k].sample(frac=1.0, random_state=BENIH)
        if KUOTA_TILE[k]:
            sub = sub.groupby("tile", sort=False).head(KUOTA_TILE[k])
        if TARGET[k]:
            if len(sub) < TARGET[k]:
                sys.exit(f"{k}: hanya {len(sub)} tersedia, target {TARGET[k]}")
            sub = sub.head(TARGET[k])
        n_val = round(len(sub) * PROPORSI_VALIDASI)
        sub = sub.assign(peran=["validasi"] * n_val + ["latih"] * (len(sub) - n_val))
        potong.append(sub)
    s = pd.concat(potong).sample(frac=1.0, random_state=BENIH).reset_index(drop=True)
    s["chip_pra"] = "L_" + s["uid"].str.slice(0, 8) + "_pra.png"
    s["chip_pasca"] = "L_" + s["uid"].str.slice(0, 8) + "_pasca.png"
    if s["chip_pasca"].duplicated().any():
        sys.exit("Nama chip kembar (awalan uid 8 karakter sama). Perlu penamaan lain.")
    s["jendela_x_min"] = (s["pusat_x_px"] - r).round().astype(int)
    s["jendela_y_min"] = (s["pusat_y_px"] - r).round().astype(int)
    kolom = ["uid", "tile", "kelas_xbd", "kelas_biner", "peran", "grup_pra",
             "pusat_x_px", "pusat_y_px", "sisi_terpanjang_px", "jendela_x_min", "jendela_y_min",
             "chip_pra", "chip_pasca"]
    OUT.mkdir(parents=True, exist_ok=True)
    s[kolom].to_csv(OUT / "sampel_latih.csv", index=False)

    L += ["", "KOMPOSISI (baris = kelas)", pd.crosstab(s.kelas_xbd, s.peran, margins=True).to_string(),
          "", f"tile terlibat: {s.tile.nunique()} | tile uji yang tumpang tindih: "
              f"{len(set(s.tile) & tile_uji)} (harus 0)",
          "", "sebaran grup akuisisi pra:", s.grup_pra.value_counts().to_string()]
    teks = "\n".join(L)
    (OUT / "ringkasan_sampel_latih.txt").write_text(teks, encoding="utf-8")
    print(teks)
    k3 = AKAR / "KOMPONEN_3"
    print("\nLangkah berikutnya, ekstraksi chip (dari folder KOMPONEN_3):")
    print(f'  python 03_ekstraksi_chip.py --sampel "{OUT / "sampel_latih.csv"}" --out "{CHIP_LATIH}"')
    print("Lalu kembali ke KOMPONEN_4:  python 13_sampel_latih.py --zip")


def rakit_zip() -> None:
    s = pd.read_csv(OUT / "sampel_latih.csv")
    hilang = [f for f in s["chip_pasca"] if not (CHIP_LATIH / "pasca" / f).exists()]
    if hilang:
        sys.exit(f"{len(hilang)} chip pasca latih belum ada, contoh {hilang[:3]}. Jalankan skrip 03 dulu.")
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(OUT / "sampel_latih.csv", "latih/sampel_latih.csv")
        z.write(OUT / "ringkasan_sampel_latih.txt", "latih/ringkasan_sampel_latih.txt")
        for f in s["chip_pasca"]:
            z.write(CHIP_LATIH / "pasca" / f, f"latih/pasca_latih/{f}")
    print(f"zip siap: {ZIP}  ({ZIP.stat().st_size / 1e6:.1f} MB, {len(s)} chip pasca)")
    print("Unggah ke Kaggle sebagai dataset baru, misal 'skripsi-alif-latih'.")


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--zip", action="store_true", help="rakit zip Kaggle dari chip yang sudah diekstrak")
    arg = a.parse_args()
    rakit_zip() if arg.zip else tarik()


if __name__ == "__main__":
    main()
