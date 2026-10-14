#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_penarikan_sampel.py
======================
Penarikan sampel berstrata untuk pengujian Small Vision-Language Model pada
pasangan citra pra/pasca bencana xBD - studi kasus gempa bumi dan tsunami
Palu 2018.

Masukan  : keluaran skrip 01 (inventaris_palu_bangunan.csv, inventaris_palu_tile.csv)
Keluaran : sampel_besar.csv, sampel_kecil.csv, ringkasan_sampel.txt

Empat penyaringan kerangka sampel, berurutan:

  S1  Penguncian grup akuisisi     -> hanya tile dengan citra pra 2017-01-24
  S2  Pengecualian kelas takterpakai -> un-classified dibuang, minor-damage dibuang (n=1)
  S3  Pengecualian bangunan tepi    -> jendela 128 px harus utuh di dalam tile
  S4  Pengecualian bangunan besar   -> sisi terpanjang harus <= 128 px

Stratifikasi: no-damage / destroyed / major-damage, dengan kuota per tile agar
satu tile padat (mis. palu-tsunami_00000118) tidak mendominasi sampel.

Hanya pustaka standar Python + pandas. Tidak membuka citra, tidak butuh GPU.

Penggunaan:
    python 02_penarikan_sampel.py
    python 02_penarikan_sampel.py --inv "D:\\jalur\\lain" --out "D:\\keluaran"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("Butuh pandas. Jalankan:  pip install pandas")

# ---------------------------------------------------------------------------
# PARAMETER — ubah di sini bila desain berubah
# ---------------------------------------------------------------------------

INV_BAWAAN = Path(
    r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\MANUVER SKRIPSI AFTER SENSUS"
    r"\KOMPONEN_2\Output Inventarisasi"
)
OUT_BAWAAN = Path(
    r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\MANUVER SKRIPSI AFTER SENSUS"
    r"\KOMPONEN_3\Output Sampel"
)

GRUP_PRA = "2017-01-24"     # S1: tanggal akuisisi citra pra yang dikunci
SISI_JENDELA = 128          # ukuran jendela chip dalam piksel citra asli
UKURAN_TILE = 1024          # sisi tile xBD
KELAS_DIBUANG = ("un-classified", "minor-damage")

# Komposisi sampel besar: kelas xBD -> jumlah chip
KOMPOSISI_BESAR = {
    "no-damage": 200,
    "destroyed": 100,
    "major-damage": 100,
}
# Komposisi sampel kecil (subset dari sampel besar) untuk evaluasi manusia
KOMPOSISI_KECIL = {
    "no-damage": 20,
    "destroyed": 10,
    "major-damage": 10,
}

KUOTA_PER_TILE = 5          # maksimum chip per tile per stratum
BENIH = 42                  # seed acak, dikunci agar sampel dapat direproduksi

# ---------------------------------------------------------------------------


def garis(judul: str = "", lebar: int = 78) -> str:
    return judul.center(lebar, "=") if judul else "=" * lebar


def muat(inv: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    f_bangunan = inv / "inventaris_palu_bangunan.csv"
    f_tile = inv / "inventaris_palu_tile.csv"
    for f in (f_bangunan, f_tile):
        if not f.exists():
            sys.exit(f"Berkas tidak ditemukan: {f}\nJalankan dulu skrip 01.")
    return pd.read_csv(f_bangunan), pd.read_csv(f_tile)


def saring(bangunan: pd.DataFrame, tile: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Empat penyaringan berurutan. Mengembalikan kerangka sampel + jejak audit."""
    jejak: list[str] = []
    n0 = len(bangunan)
    jejak.append(f"{'Populasi awal (seluruh bangunan berlabel)':<52}{n0:>8,}")

    df = bangunan.merge(tile[["tile", "pra_tanggal"]], on="tile", how="left")
    df["grup_pra"] = df["pra_tanggal"].str[:10]

    # S1 — penguncian grup akuisisi
    df = df[df["grup_pra"] == GRUP_PRA]
    jejak.append(f"{f'S1 grup akuisisi pra {GRUP_PRA}':<52}{len(df):>8,}")

    # S2 — kelas yang tidak dipakai
    df = df[~df["kelas_xbd"].isin(KELAS_DIBUANG)]
    jejak.append(f"{'S2 buang un-classified dan minor-damage':<52}{len(df):>8,}")

    # S3 — bangunan tepi
    r = SISI_JENDELA / 2
    utuh = (
        (df["pusat_x_px"] - r >= 0)
        & (df["pusat_y_px"] - r >= 0)
        & (df["pusat_x_px"] + r <= UKURAN_TILE)
        & (df["pusat_y_px"] + r <= UKURAN_TILE)
    )
    df = df[utuh]
    jejak.append(f"{f'S3 jendela {SISI_JENDELA} px utuh di dalam tile':<52}{len(df):>8,}")

    # S4 — bangunan lebih besar dari jendela
    df = df[df["sisi_terpanjang_px"] <= SISI_JENDELA]
    jejak.append(f"{f'S4 sisi terpanjang <= {SISI_JENDELA} px':<52}{len(df):>8,}")

    jejak.append(f"{'KERANGKA SAMPEL AKHIR':<52}{len(df):>8,}"
                 f"   ({len(df) / n0 * 100:.1f}% dari populasi awal)")
    return df.reset_index(drop=True), jejak


def tarik_strata(kerangka: pd.DataFrame, komposisi: dict[str, int],
                 kuota_tile: int, benih: int) -> pd.DataFrame:
    """Acak sederhana berstrata dengan pembatasan jumlah per tile."""
    potongan = []
    for kelas, n_target in komposisi.items():
        sub = kerangka[kerangka["kelas_xbd"] == kelas]
        if sub.empty:
            sys.exit(f"Kerangka sampel tidak memuat kelas '{kelas}'.")
        # acak seluruh baris dulu, lalu ambil maksimal `kuota_tile` per tile
        acak = sub.sample(frac=1.0, random_state=benih)
        terbatas = acak.groupby("tile", sort=False).head(kuota_tile)
        if len(terbatas) < n_target:
            sys.exit(
                f"Kelas '{kelas}': hanya {len(terbatas)} unit tersedia dengan "
                f"kuota {kuota_tile}/tile, sedangkan target {n_target}. "
                f"Naikkan KUOTA_PER_TILE atau turunkan target."
            )
        potongan.append(terbatas.head(n_target))
    hasil = pd.concat(potongan, ignore_index=True)
    return hasil.sample(frac=1.0, random_state=benih).reset_index(drop=True)


def tarik_subset(besar: pd.DataFrame, komposisi: dict[str, int],
                 benih: int) -> pd.DataFrame:
    potongan = [
        besar[besar["kelas_xbd"] == kelas].sample(n=n, random_state=benih)
        for kelas, n in komposisi.items()
    ]
    hasil = pd.concat(potongan, ignore_index=True)
    return hasil.sample(frac=1.0, random_state=benih).reset_index(drop=True)


def rapikan(df: pd.DataFrame) -> pd.DataFrame:
    """Susun kolom keluaran dan tambahkan nama berkas chip."""
    d = df.copy()
    d["chip_pra"] = d["uid"].str.slice(0, 8) + "_pra.png"
    d["chip_pasca"] = d["uid"].str.slice(0, 8) + "_pasca.png"
    d["jendela_x_min"] = (d["pusat_x_px"] - SISI_JENDELA / 2).round().astype(int)
    d["jendela_y_min"] = (d["pusat_y_px"] - SISI_JENDELA / 2).round().astype(int)
    kolom = [
        "uid", "tile", "kelas_xbd", "kelas_biner",
        "pusat_x_px", "pusat_y_px", "sisi_terpanjang_px", "luas_poligon_px2",
        "jendela_x_min", "jendela_y_min", "lon", "lat",
        "chip_pra", "chip_pasca",
    ]
    return d[kolom]


def blok_ringkas(nama: str, df: pd.DataFrame) -> list[str]:
    baris = [f"\n {nama}", " " + "-" * 76]
    tab = df["kelas_xbd"].value_counts()
    for kelas in KOMPOSISI_BESAR:
        n = int(tab.get(kelas, 0))
        baris.append(f" {kelas:<16}{n:>6}   {n / len(df) * 100:>5.1f}%")
    n_rusak = int((df["kelas_biner"] == "rusak").sum())
    baris.append(f" {'-> biner rusak':<16}{n_rusak:>6}   {n_rusak / len(df) * 100:>5.1f}%")
    baris.append(f" {'JUMLAH':<16}{len(df):>6}")
    baris.append(f" Tile terlibat   {df['tile'].nunique():>6}"
                 f"   (maks {int(df['tile'].value_counts().max())} chip dari satu tile)")
    baris.append(f" Ukuran bangunan  median {df['sisi_terpanjang_px'].median():.1f} px"
                 f" | p10 {df['sisi_terpanjang_px'].quantile(.1):.1f}"
                 f" | p90 {df['sisi_terpanjang_px'].quantile(.9):.1f}")
    return baris


def main() -> None:
    p = argparse.ArgumentParser(description="Penarikan sampel berstrata xBD Palu 2018")
    p.add_argument("--inv", type=Path, default=INV_BAWAAN, help="folder keluaran skrip 01")
    p.add_argument("--out", type=Path, default=OUT_BAWAAN, help="folder keluaran sampel")
    p.add_argument("--benih", type=int, default=BENIH, help="seed acak")
    a = p.parse_args()

    bangunan, tile = muat(a.inv)
    kerangka, jejak = saring(bangunan, tile)
    besar = tarik_strata(kerangka, KOMPOSISI_BESAR, KUOTA_PER_TILE, a.benih)
    kecil = tarik_subset(besar, KOMPOSISI_KECIL, a.benih)

    a.out.mkdir(parents=True, exist_ok=True)
    f_kerangka = a.out / "kerangka_sampel.csv"
    f_besar = a.out / "sampel_besar.csv"
    f_kecil = a.out / "sampel_kecil.csv"
    rapikan(kerangka).to_csv(f_kerangka, index=False)
    rapikan(besar).to_csv(f_besar, index=False)
    rapikan(kecil).to_csv(f_kecil, index=False)

    # -------------------------------------------------------------- ringkasan
    L = [garis(), garis(" RINGKASAN PENARIKAN SAMPEL "), garis(), ""]
    L.append(f" Grup akuisisi dikunci : pra {GRUP_PRA} -> pasca 2018-10-01")
    L.append(f" Jendela chip          : {SISI_JENDELA} x {SISI_JENDELA} px")
    L.append(f" Benih acak            : {a.benih}")
    L.append(f" Kuota per tile        : {KUOTA_PER_TILE} chip per stratum")
    L.append("")
    L.append(" [1]  JEJAK PENYARINGAN KERANGKA SAMPEL")
    L.append(" " + "-" * 76)
    L += [" " + j for j in jejak]
    L.append("")
    L.append(" [2]  SEBARAN KERANGKA SAMPEL MENURUT KELAS")
    L.append(" " + "-" * 76)
    tab = kerangka["kelas_xbd"].value_counts()
    for kelas in KOMPOSISI_BESAR:
        n = int(tab.get(kelas, 0))
        tersedia = (kerangka[kerangka["kelas_xbd"] == kelas]
                    .groupby("tile").head(KUOTA_PER_TILE).shape[0])
        L.append(f" {kelas:<16}{n:>8,}   tersedia setelah kuota tile: {tersedia:>6,}"
                 f"   target: {KOMPOSISI_BESAR[kelas]:>4}")
    L += blok_ringkas("[3]  SAMPEL BESAR (pengujian otomatis)", besar)
    L += blok_ringkas("[4]  SAMPEL KECIL (evaluasi manusia, subset sampel besar)", kecil)
    L.append("")
    L.append(" [5]  BERKAS KELUARAN")
    L.append(" " + "-" * 76)
    for f in (f_kerangka, f_besar, f_kecil):
        L.append(f" {f.name:<28}{f}")
    L.append("")
    L.append(garis())

    teks = "\n".join(L)
    print(teks)
    (a.out / "ringkasan_sampel.txt").write_text(teks, encoding="utf-8")


if __name__ == "__main__":
    main()
