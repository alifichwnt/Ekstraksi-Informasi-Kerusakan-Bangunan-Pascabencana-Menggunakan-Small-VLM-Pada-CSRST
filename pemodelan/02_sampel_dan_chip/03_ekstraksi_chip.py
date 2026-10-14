#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03_ekstraksi_chip.py
====================
Ekstraksi chip citra pra/pasca bencana untuk pengujian Small Vision-Language
Model - studi kasus gempa bumi dan tsunami Palu 2018 (dataset xBD).

Masukan  : sampel_besar.csv / sampel_kecil.csv (keluaran skrip 02)
           berkas .tif tile xBD
Keluaran : tiga varian penyajian masukan, untuk pilot perbandingan
             pra/     chip pra-bencana 448 x 448 px
             pasca/   chip pasca-bencana 448 x 448 px
             gabung/  pra dan pasca berdampingan dalam satu berkas

Prinsip yang dipegang:

  1. Jendela chip BERUKURAN TETAP 128 x 128 px pada citra asli, lalu diperbesar
     ke 448 x 448 px. Skala tanah setiap chip karena itu identik.
  2. Kotak penanda bangunan sasaran BERUKURAN TETAP (64 px pada skala asli),
     bukan mengikuti bounding box poligon. Kotak yang mengikuti poligon akan
     membocorkan ukuran bangunan hasil anotasi ke dalam masukan model,
     padahal ukuran itu berkorelasi dengan kelas kerusakan.
  3. Nama berkas memakai potongan UID, bukan kelas kerusakan, agar label tidak
     bocor ke evaluator manusia maupun ke berkas keluaran model.

Penggunaan:
    python 03_ekstraksi_chip.py
    python 03_ekstraksi_chip.py --sampel "...\\sampel_kecil.csv" --out "...\\chip_kecil"
    python 03_ekstraksi_chip.py --batas 5          # uji cepat lima chip pertama
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    import tifffile
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    sys.exit("Butuh pandas, Pillow, numpy, tifffile. Jalankan:\n"
             "    pip install pandas pillow numpy tifffile")

Image.MAX_IMAGE_PIXELS = None

# ---------------------------------------------------------------------------
# PARAMETER
# ---------------------------------------------------------------------------

CITRA_BAWAAN = Path(
    r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\KOMPONEN PENDUKUNG\SUMBER DATA"
    r"\Data Citra Kasus Kerusakan Bangunan\XView2-Dataset\Palu2018\images"
)
SAMPEL_BAWAAN = Path(
    r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\MANUVER SKRIPSI AFTER SENSUS"
    r"\KOMPONEN_3\Output Sampel\sampel_besar.csv"
)
OUT_BAWAAN = Path(
    r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\MANUVER SKRIPSI AFTER SENSUS"
    r"\KOMPONEN_3\Output Chip"
)

SISI_JENDELA = 128       # jendela pada citra asli (piksel)
SISI_KELUARAN = 448      # sisi chip setelah diperbesar
KOTAK_PENANDA = 64       # kotak penanda pada skala asli; TETAP untuk semua chip
TEBAL_GARIS = 3          # tebal garis kotak pada skala keluaran
WARNA_PENANDA = (255, 0, 255)   # magenta: praktis tidak muncul di citra alami
CELAH_GABUNG = 12        # lebar pemisah pada varian gabung
TINGGI_JUDUL = 34        # tinggi pita judul pada varian gabung


def buka_tile(folder: Path, tile: str, fase: str) -> Image.Image:
    """fase: 'pre' atau 'post'.

    Dua hal yang perlu dicatat mengenai berkas .tif xBD pada salinan ini:

    a. Nama berkas disusun dari id tile, BUKAN dari metadata.img_name di dalam
       JSON xBD (yang keliru menyebut ekstensi .png).
    b. Rasternya bertipe int16 tiga kanal, sehingga Pillow tidak dapat
       membacanya langsung. Nilai pikselnya sendiri sudah berada pada rentang
       0-255, jadi konversi ke uint8 cukup dilakukan dengan pemotongan
       (clip) tanpa peregangan kontras apa pun. Ini disengaja: peregangan
       kontras per citra akan membuat citra pra dan pasca mendapat pemetaan
       radiometri yang berbeda, sehingga menimbulkan perbedaan semu yang
       dapat disalahartikan model sebagai kerusakan.
    """
    berkas = folder / f"{tile}_{fase}_disaster.tif"
    if not berkas.exists():
        raise FileNotFoundError(berkas)
    arr = tifffile.imread(berkas)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    arr = arr[..., :3]
    if arr.dtype != np.uint8:
        if arr.max() > 255:
            raise ValueError(
                f"{berkas.name}: nilai piksel melebihi 255 (maks {arr.max()}). "
                "Berkas ini butuh peregangan kontras; hentikan dan tentukan "
                "aturan peregangan yang sama untuk pra dan pasca."
            )
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def potong(tile_img: Image.Image, x_min: int, y_min: int) -> Image.Image:
    kotak = (x_min, y_min, x_min + SISI_JENDELA, y_min + SISI_JENDELA)
    return tile_img.crop(kotak).resize((SISI_KELUARAN, SISI_KELUARAN),
                                       Image.Resampling.LANCZOS)


def beri_penanda(chip: Image.Image) -> Image.Image:
    """Kotak penanda berukuran tetap + bidik silang pada titik pusat bangunan.

    Kotak saja tidak cukup. Pada permukiman padat Palu, jendela 128 px memuat
    rata-rata enam bangunan, sehingga kotak 64 px kerap masih memuat dua sampai
    tiga atap. Bidik silang menunjuk titik pusat poligon bangunan sasaran
    secara tepat, sementara kotak tetap berperan sebagai penunjuk cakupan.
    Keduanya berukuran tetap sehingga tidak membocorkan ukuran bangunan.
    """
    skala = SISI_KELUARAN / SISI_JENDELA
    tengah = SISI_KELUARAN / 2
    gambar = ImageDraw.Draw(chip)

    sisi = KOTAK_PENANDA * skala
    a, b = tengah - sisi / 2, tengah + sisi / 2
    gambar.rectangle([a, a, b, b], outline=WARNA_PENANDA, width=TEBAL_GARIS)

    # bidik silang: empat tanda pendek yang mengarah ke pusat, pusatnya
    # dibiarkan kosong agar atap bangunan sasaran tetap terlihat
    panjang = 11 * skala           # panjang tiap tanda, pada skala asli
    celah = 5 * skala              # jarak kosong di sekitar titik pusat
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        gambar.line(
            [tengah + dx * celah, tengah + dy * celah,
             tengah + dx * (celah + panjang), tengah + dy * (celah + panjang)],
            fill=WARNA_PENANDA, width=TEBAL_GARIS,
        )
    return chip


def huruf(ukuran: int = 20) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for nama in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(nama, ukuran)
        except OSError:
            continue
    return ImageFont.load_default()


def gabungkan(pra: Image.Image, pasca: Image.Image) -> Image.Image:
    lebar = SISI_KELUARAN * 2 + CELAH_GABUNG
    kanvas = Image.new("RGB", (lebar, SISI_KELUARAN + TINGGI_JUDUL), (255, 255, 255))
    kanvas.paste(pra, (0, TINGGI_JUDUL))
    kanvas.paste(pasca, (SISI_KELUARAN + CELAH_GABUNG, TINGGI_JUDUL))
    g = ImageDraw.Draw(kanvas)
    f = huruf(22)
    g.text((SISI_KELUARAN / 2, TINGGI_JUDUL / 2), "PRA-BENCANA",
           fill=(0, 0, 0), font=f, anchor="mm")
    g.text((SISI_KELUARAN * 1.5 + CELAH_GABUNG, TINGGI_JUDUL / 2), "PASCA-BENCANA",
           fill=(0, 0, 0), font=f, anchor="mm")
    return kanvas


def tutup(*citra: Image.Image | None) -> None:
    for c in citra:
        if c is not None:
            c.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Ekstraksi chip pra/pasca xBD Palu 2018")
    p.add_argument("--sampel", type=Path, default=SAMPEL_BAWAAN)
    p.add_argument("--citra", type=Path, default=CITRA_BAWAAN)
    p.add_argument("--out", type=Path, default=OUT_BAWAAN)
    p.add_argument("--batas", type=int, default=0, help="olah N baris pertama saja (uji)")
    a = p.parse_args()

    if not a.sampel.exists():
        sys.exit(f"Berkas sampel tidak ditemukan: {a.sampel}\nJalankan dulu skrip 02.")
    if not a.citra.is_dir():
        sys.exit(f"Folder citra tidak ditemukan: {a.citra}")

    sampel = pd.read_csv(a.sampel)
    if a.batas:
        sampel = sampel.head(a.batas)
    # urut menurut tile: satu tile cukup dibuka sekali untuk seluruh chip di dalamnya
    sampel = sampel.sort_values("tile").reset_index(drop=True)

    for sub in ("pra", "pasca", "gabung"):
        (a.out / sub).mkdir(parents=True, exist_ok=True)

    tile_aktif: str | None = None
    img_pra: Image.Image | None = None
    img_pasca: Image.Image | None = None
    berhasil, gagal = 0, []
    catatan = []

    for i, (_, baris) in enumerate(sampel.iterrows()):
        tile = baris["tile"]
        try:
            if tile != tile_aktif:
                tutup(img_pra, img_pasca)
                img_pra = buka_tile(a.citra, tile, "pre")
                img_pasca = buka_tile(a.citra, tile, "post")
                tile_aktif = tile
                print(f"  tile {tile} dibuka", flush=True)
            # selalu terpenuhi: tile_aktif hanya terisi setelah kedua citra terbuka
            assert img_pra is not None and img_pasca is not None

            x, y = int(baris["jendela_x_min"]), int(baris["jendela_y_min"])
            c_pra = beri_penanda(potong(img_pra, x, y))
            c_pasca = beri_penanda(potong(img_pasca, x, y))

            c_pra.save(a.out / "pra" / baris["chip_pra"], optimize=True)
            c_pasca.save(a.out / "pasca" / baris["chip_pasca"], optimize=True)
            gabungkan(c_pra, c_pasca).save(
                a.out / "gabung" / baris["chip_pra"].replace("_pra", "_gabung"),
                optimize=True)

            catatan.append({
                "uid": baris["uid"], "tile": tile,
                "kelas_xbd": baris["kelas_xbd"], "kelas_biner": baris["kelas_biner"],
                "chip_pra": baris["chip_pra"], "chip_pasca": baris["chip_pasca"],
                "chip_gabung": baris["chip_pra"].replace("_pra", "_gabung"),
                "jendela_x_min": x, "jendela_y_min": y,
                "sisi_jendela_px": SISI_JENDELA, "sisi_keluaran_px": SISI_KELUARAN,
                "kotak_penanda_px": KOTAK_PENANDA,
            })
            berhasil += 1
        except Exception as e:  # noqa: BLE001
            gagal.append((baris["uid"], tile, repr(e)))

        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(sampel)} chip selesai", flush=True)

    tutup(img_pra, img_pasca)

    pd.DataFrame(catatan).to_csv(a.out / "katalog_chip.csv", index=False)

    print("\n" + "=" * 78)
    print(" RINGKASAN EKSTRAKSI CHIP")
    print("=" * 78)
    print(f" Sampel diproses   : {len(sampel)}")
    print(f" Chip berhasil     : {berhasil}  (x3 varian = {berhasil * 3} berkas)")
    print(f" Chip gagal        : {len(gagal)}")
    for uid, tile, e in gagal[:10]:
        print(f"   !! {tile} {uid[:8]}  {e}")
    print(f" Jendela           : {SISI_JENDELA} px -> {SISI_KELUARAN} px "
          f"(skala {SISI_KELUARAN / SISI_JENDELA:.1f}x)")
    print(f" Kotak penanda     : {KOTAK_PENANDA} px tetap, magenta, di tengah chip")
    print(f" Folder keluaran   : {a.out}")
    print(f" Katalog           : {a.out / 'katalog_chip.csv'}")
    print("=" * 78)


if __name__ == "__main__":
    main()
