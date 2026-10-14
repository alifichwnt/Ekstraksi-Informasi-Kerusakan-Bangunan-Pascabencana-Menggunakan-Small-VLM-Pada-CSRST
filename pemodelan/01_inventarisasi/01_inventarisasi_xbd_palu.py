"""
================================================================================
 SKRIPSI — Ekstraksi Informasi Kerusakan Bangunan Pascabencana Menggunakan SVLM
            pada Citra Satelit Resolusi Sangat Tinggi
            Studi Kasus: Gempa Bumi dan Tsunami Palu 2018

 Rizky Alif Ichwanto (222212857, 4SD2) — D-IV Komputasi Statistik, Polstat STIS

 LANGKAH 01 : INVENTARISASI DATASET xBD / xView2 — palu-tsunami
 Versi 2 — disesuaikan dengan direktori Palu2018 yang sudah dikonsolidasikan
================================================================================

 APA YANG DIHASILKAN
 -------------------
   1. inventaris_palu_bangunan.csv   satu baris per BANGUNAN
        tile, uid, kelas xBD, kelas biner, bbox, ukuran, centroid piksel,
        centroid lon/lat, dan penanda apakah bangunan menabrak lantai 128 px

   2. inventaris_palu_tile.csv       satu baris per TILE
        jumlah bangunan per kelas + metadata akuisisi pra & pasca lengkap
        (tanggal, off-nadir, azimut & elevasi matahari, resolusi, catalog id)

   3. inventaris_palu_akuisisi.csv   satu baris per KOMBINASI AKUISISI
        ringkasan pasangan citra pra-pasca yang dipakai di seluruh tile
        --> bahan tabel konfound akuisisi untuk Bab 4 (Data Understanding)

   4. Ringkasan yang dicetak ke layar
        DISTRIBUSI KELAS --> angka pembenaran binarisasi di Bab 3
        STATISTIK UKURAN --> dasar penetapan jendela chip 128 px
        PEMERIKSAAN MUTU --> pasangan pra/pasca, citra hilang, label anomali

 SIFAT SKRIP
 -----------
   - Hanya membaca file label JSON. Citra .tif TIDAK dibuka sama sekali.
   - Hanya memakai pustaka standar Python. Tidak perlu pip install apa pun.
   - Tidak butuh GPU. Selesai dalam hitungan menit di laptop.

 CARA MENJALANKAN
 ----------------
   Langsung  :  python 01_inventarisasi_xbd_palu.py
   Atau      :  python 01_inventarisasi_xbd_palu.py --root "D:\\..." --out "D:\\..."
================================================================================
"""

import os
import re
import csv
import json
import glob
import argparse
from collections import Counter, defaultdict

# ==============================================================================
# KONFIGURASI BAWAAN — ubah di sini bila lokasi berpindah
# ==============================================================================

ROOT = (r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\KOMPONEN PENDUKUNG"
        r"\SUMBER DATA\Data Citra Kasus Kerusakan Bangunan\XView2-Dataset\Palu2018")

OUT_DIR = (r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET"
           r"\MANUVER SKRIPSI AFTER SENSUS\KOMPONEN_2\Output Inventarisasi")

DISASTER = "palu-tsunami"

# Jendela chip yang disepakati: sisi = max(sisi_bbox * FAKTOR_MARGIN, LANTAI_PX)
FAKTOR_MARGIN = 1.5
LANTAI_PX = 128

# Pemetaan kelas xBD ke kelas biner (keputusan bimbingan final)
PETA_BINER = {
    "no-damage":    "tidak_rusak",
    "minor-damage": "rusak",
    "major-damage": "rusak",
    "destroyed":    "rusak",
    # 'un-classified' sengaja tidak dipetakan: ditandai DIKECUALIKAN,
    # dikeluarkan dari populasi sampel, tetapi jumlahnya tetap dilaporkan.
}

URUTAN_KELAS = ["no-damage", "minor-damage", "major-damage", "destroyed", "un-classified"]

# ==============================================================================


def uraikan_wkt(wkt):
    """Ambil daftar titik (x, y) dari cincin terluar string WKT POLYGON."""
    if not wkt:
        return []
    m = re.search(r"\(\((.*?)\)\)", wkt, flags=re.S)
    if not m:
        return []
    titik = []
    for pasangan in m.group(1).split(","):
        bagian = pasangan.strip().split()
        if len(bagian) >= 2:
            try:
                titik.append((float(bagian[0]), float(bagian[1])))
            except ValueError:
                pass
    return titik


def luas_shoelace(titik):
    """Luas poligon (satuan piksel persegi)."""
    n = len(titik)
    if n < 3:
        return 0.0
    total = 0.0
    for i in range(n):
        x1, y1 = titik[i]
        x2, y2 = titik[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def persentil(terurut, p):
    if not terurut:
        return 0.0
    n = len(terurut)
    idx = min(n - 1, max(0, int(round(p * (n - 1)))))
    return terurut[idx]


def cari_folder_label(root):
    """Terima root berupa folder Palu2018, folder labels, atau folder induk."""
    kandidat = [
        os.path.join(root, "labels"),
        root,
    ]
    for k in kandidat:
        if os.path.isdir(k) and glob.glob(os.path.join(k, f"{DISASTER}_*_post_disaster.json")):
            return k
    # pencarian rekursif sebagai jaring pengaman
    pola = os.path.join(root, "**", f"{DISASTER}_*_post_disaster.json")
    hasil = glob.glob(pola, recursive=True)
    if hasil:
        return os.path.dirname(hasil[0])
    return None


def main():
    ap = argparse.ArgumentParser(description="Inventarisasi label xBD palu-tsunami")
    ap.add_argument("--root", default=ROOT, help="folder Palu2018 (berisi images/ dan labels/)")
    ap.add_argument("--out", default=OUT_DIR, help="folder keluaran CSV")
    arg = ap.parse_args()

    root = arg.root
    out_dir = arg.out

    folder_label = cari_folder_label(root)
    if folder_label is None:
        raise SystemExit(
            "Tidak ditemukan file label dengan pola "
            f"'{DISASTER}_*_post_disaster.json' di bawah:\n  {root}\n"
            "Periksa kembali nilai --root atau konstanta ROOT."
        )

    folder_citra = os.path.join(os.path.dirname(folder_label), "images")
    ada_folder_citra = os.path.isdir(folder_citra)

    os.makedirs(out_dir, exist_ok=True)

    berkas_post = sorted(glob.glob(os.path.join(folder_label, f"{DISASTER}_*_post_disaster.json")))

    print("=" * 78)
    print(" INVENTARISASI xBD — palu-tsunami")
    print("=" * 78)
    print(f" Folder label : {folder_label}")
    print(f" Folder citra : {folder_citra if ada_folder_citra else '(tidak ditemukan)'}")
    print(f" Tile pasca   : {len(berkas_post)}")
    print()

    baris_bangunan = []
    baris_tile = []
    hitung_kelas = Counter()
    sisi_semua = []
    akuisisi = Counter()

    # pemeriksaan mutu
    tile_tanpa_label_pra = []
    tile_tanpa_citra = []
    tile_tanpa_bangunan = []
    poligon_rusak = 0
    uid_ganda = 0
    uid_terlihat = set()

    for i, path_post in enumerate(berkas_post, start=1):
        nama_tile = os.path.basename(path_post).replace("_post_disaster.json", "")
        path_pre = os.path.join(folder_label, nama_tile + "_pre_disaster.json")

        with open(path_post, "r", encoding="utf-8") as f:
            data_post = json.load(f)

        data_pre = None
        if os.path.exists(path_pre):
            with open(path_pre, "r", encoding="utf-8") as f:
                data_pre = json.load(f)
        else:
            tile_tanpa_label_pra.append(nama_tile)

        if ada_folder_citra:
            for akhiran in ("_pre_disaster.tif", "_post_disaster.tif"):
                if not os.path.exists(os.path.join(folder_citra, nama_tile + akhiran)):
                    tile_tanpa_citra.append(nama_tile + akhiran)

        meta_post = data_post.get("metadata", {})
        meta_pre = (data_pre or {}).get("metadata", {})

        fitur_xy = data_post.get("features", {}).get("xy", [])
        fitur_ll = data_post.get("features", {}).get("lng_lat", [])
        peta_ll = {f.get("properties", {}).get("uid"): f.get("wkt") for f in fitur_ll}

        kelas_tile = Counter()

        for f in fitur_xy:
            prop = f.get("properties", {})
            if prop.get("feature_type") != "building":
                continue

            uid = prop.get("uid")
            subtype = prop.get("subtype", "tanpa_label")

            titik = uraikan_wkt(f.get("wkt", ""))
            if len(titik) < 3:
                poligon_rusak += 1
                continue

            if uid in uid_terlihat:
                uid_ganda += 1
            uid_terlihat.add(uid)

            xs = [t[0] for t in titik]
            ys = [t[1] for t in titik]
            x_min, x_maks = min(xs), max(xs)
            y_min, y_maks = min(ys), max(ys)
            lebar = x_maks - x_min
            tinggi = y_maks - y_min
            sisi = max(lebar, tinggi)
            sisi_jendela = max(sisi * FAKTOR_MARGIN, LANTAI_PX)

            lon = lat = ""
            titik_ll = uraikan_wkt(peta_ll.get(uid))
            if titik_ll:
                lon = round(sum(t[0] for t in titik_ll) / len(titik_ll), 8)
                lat = round(sum(t[1] for t in titik_ll) / len(titik_ll), 8)

            baris_bangunan.append({
                "tile": nama_tile,
                "uid": uid,
                "kelas_xbd": subtype,
                "kelas_biner": PETA_BINER.get(subtype, "DIKECUALIKAN"),
                "bbox_x_min": round(x_min, 2),
                "bbox_y_min": round(y_min, 2),
                "bbox_x_maks": round(x_maks, 2),
                "bbox_y_maks": round(y_maks, 2),
                "lebar_px": round(lebar, 2),
                "tinggi_px": round(tinggi, 2),
                "sisi_terpanjang_px": round(sisi, 2),
                "luas_poligon_px2": round(luas_shoelace(titik), 2),
                "pusat_x_px": round((x_min + x_maks) / 2.0, 2),
                "pusat_y_px": round((y_min + y_maks) / 2.0, 2),
                "sisi_jendela_px": round(sisi_jendela, 2),
                "kena_lantai_128": int(sisi * FAKTOR_MARGIN < LANTAI_PX),
                "lon": lon,
                "lat": lat,
            })

            hitung_kelas[subtype] += 1
            kelas_tile[subtype] += 1
            sisi_semua.append(sisi)

        if sum(kelas_tile.values()) == 0:
            tile_tanpa_bangunan.append(nama_tile)

        kunci_akuisisi = (
            meta_pre.get("capture_date", ""), meta_post.get("capture_date", ""),
            meta_pre.get("catalog_id", ""), meta_post.get("catalog_id", ""),
            meta_pre.get("off_nadir_angle", ""), meta_post.get("off_nadir_angle", ""),
            meta_pre.get("sun_azimuth", ""), meta_post.get("sun_azimuth", ""),
            meta_pre.get("sun_elevation", ""), meta_post.get("sun_elevation", ""),
            meta_pre.get("pan_resolution", ""), meta_post.get("pan_resolution", ""),
        )
        akuisisi[kunci_akuisisi] += 1

        baris_tile.append({
            "tile": nama_tile,
            "jumlah_bangunan": sum(kelas_tile.values()),
            "no_damage": kelas_tile.get("no-damage", 0),
            "minor_damage": kelas_tile.get("minor-damage", 0),
            "major_damage": kelas_tile.get("major-damage", 0),
            "destroyed": kelas_tile.get("destroyed", 0),
            "un_classified": kelas_tile.get("un-classified", 0),
            "ada_kelas_rusak": int(sum(kelas_tile.get(k, 0) for k in
                                       ("minor-damage", "major-damage", "destroyed")) > 0),
            "pra_tanggal": meta_pre.get("capture_date", ""),
            "pasca_tanggal": meta_post.get("capture_date", ""),
            "pra_catalog_id": meta_pre.get("catalog_id", ""),
            "pasca_catalog_id": meta_post.get("catalog_id", ""),
            "pra_off_nadir": meta_pre.get("off_nadir_angle", ""),
            "pasca_off_nadir": meta_post.get("off_nadir_angle", ""),
            "pra_azimut_matahari": meta_pre.get("sun_azimuth", ""),
            "pasca_azimut_matahari": meta_post.get("sun_azimuth", ""),
            "pra_elevasi_matahari": meta_pre.get("sun_elevation", ""),
            "pasca_elevasi_matahari": meta_post.get("sun_elevation", ""),
            "pra_resolusi_pan": meta_pre.get("pan_resolution", ""),
            "pasca_resolusi_pan": meta_post.get("pan_resolution", ""),
            "pra_gsd": meta_pre.get("gsd", ""),
            "pasca_gsd": meta_post.get("gsd", ""),
            "sensor": meta_post.get("sensor", ""),
            "lebar_tile_px": meta_post.get("width", ""),
            "tinggi_tile_px": meta_post.get("height", ""),
        })

        if i % 50 == 0:
            print(f"   ... {i}/{len(berkas_post)} tile diproses")

    if not baris_bangunan:
        raise SystemExit(
            "Tile ditemukan tetapi tidak ada bangunan yang berhasil dibaca.\n"
            "Kemungkinan struktur JSON berbeda. Kirimkan satu file label untuk diperiksa."
        )

    # --------------------------------------------------------------- tulis CSV
    p_bangunan = os.path.join(out_dir, "inventaris_palu_bangunan.csv")
    with open(p_bangunan, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(baris_bangunan[0].keys()))
        w.writeheader(); w.writerows(baris_bangunan)

    p_tile = os.path.join(out_dir, "inventaris_palu_tile.csv")
    with open(p_tile, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(baris_tile[0].keys()))
        w.writeheader(); w.writerows(baris_tile)

    p_akuisisi = os.path.join(out_dir, "inventaris_palu_akuisisi.csv")
    kolom_ak = ["jumlah_tile", "pra_tanggal", "pasca_tanggal", "pra_catalog_id",
                "pasca_catalog_id", "pra_off_nadir", "pasca_off_nadir",
                "pra_azimut_matahari", "pasca_azimut_matahari",
                "pra_elevasi_matahari", "pasca_elevasi_matahari",
                "pra_resolusi_pan", "pasca_resolusi_pan"]
    with open(p_akuisisi, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(kolom_ak)
        for kunci, jml in akuisisi.most_common():
            w.writerow([jml] + list(kunci))

    # ---------------------------------------------------------------- ringkasan
    total = sum(hitung_kelas.values())
    n_tidak_rusak = hitung_kelas.get("no-damage", 0)
    n_rusak = sum(hitung_kelas.get(k, 0) for k in ("minor-damage", "major-damage", "destroyed"))
    n_populasi = n_tidak_rusak + n_rusak
    garis = "=" * 78

    print("\n" + garis)
    print(" RINGKASAN INVENTARISASI")
    print(garis)
    print(f" Jumlah tile      : {len(berkas_post)}")
    print(f" Jumlah bangunan  : {total:,}")

    print("\n [1]  DISTRIBUSI KELAS KERUSAKAN  — angka untuk Bab 3 dan Bab 4")
    print(" " + "-" * 76)
    print(f" {'Kelas xBD':<18}{'Jumlah':>12}{'Persen':>11}   {'Kelas biner':<14}")
    print(" " + "-" * 76)
    for k in URUTAN_KELAS + sorted(set(hitung_kelas) - set(URUTAN_KELAS)):
        if hitung_kelas.get(k):
            n = hitung_kelas[k]
            print(f" {k:<18}{n:>12,}{n/total*100:>10.2f}%   {PETA_BINER.get(k, 'DIKECUALIKAN'):<14}")
    print(" " + "-" * 76)
    if n_populasi:
        print(f" {'BINER tidak_rusak':<18}{n_tidak_rusak:>12,}{n_tidak_rusak/n_populasi*100:>10.2f}%")
        print(f" {'BINER rusak':<18}{n_rusak:>12,}{n_rusak/n_populasi*100:>10.2f}%")
        print(f" {'POPULASI SAMPEL':<18}{n_populasi:>12,}    (un-classified dikecualikan)")
        nisbah = (n_tidak_rusak / n_rusak) if n_rusak else float("inf")
        print(f" {'Nisbah ketimpangan':<18}{nisbah:>12.1f} : 1")

    sisi_semua.sort()
    print("\n [2]  UKURAN BANGUNAN — sisi terpanjang bounding box (piksel)")
    print(" " + "-" * 76)
    print(f" n={len(sisi_semua):,}   min={sisi_semua[0]:.1f}   p10={persentil(sisi_semua,0.10):.1f}"
          f"   median={persentil(sisi_semua,0.50):.1f}   p90={persentil(sisi_semua,0.90):.1f}"
          f"   max={sisi_semua[-1]:.1f}")
    kecil = sum(1 for v in sisi_semua if v < 40)
    lantai = sum(1 for v in sisi_semua if v * FAKTOR_MARGIN < LANTAI_PX)
    print(f" Bangunan < 40 px                 : {kecil:,} ({kecil/len(sisi_semua)*100:.1f}%)")
    print(f" Menabrak lantai jendela {LANTAI_PX} px    : {lantai:,} ({lantai/len(sisi_semua)*100:.1f}%)")

    print("\n [3]  KOMBINASI AKUISISI CITRA PRA-PASCA")
    print(" " + "-" * 76)
    for kunci, jml in akuisisi.most_common(10):
        (pra_t, pasca_t, _, _, pra_on, pasca_on,
         pra_az, pasca_az, pra_el, pasca_el, pra_res, pasca_res) = kunci
        print(f" {jml:>4} tile | pra {str(pra_t)[:10]} -> pasca {str(pasca_t)[:10]}")
        print(f"             off-nadir {pra_on} -> {pasca_on} | "
              f"azimut {pra_az} -> {pasca_az} | elevasi {pra_el} -> {pasca_el}")
        print(f"             resolusi pan {pra_res} -> {pasca_res}")
    if len(akuisisi) > 10:
        print(f" ... dan {len(akuisisi)-10} kombinasi lain (lihat inventaris_palu_akuisisi.csv)")

    print("\n [4]  PEMERIKSAAN MUTU")
    print(" " + "-" * 76)
    def lapor(label, daftar):
        tanda = "OK " if not daftar else "!! "
        cth = "" if not daftar else "   contoh: " + ", ".join(map(str, daftar[:3]))
        print(f" {tanda}{label:<44}{len(daftar):>6}{cth}")
    lapor("Tile tanpa label pra-bencana", tile_tanpa_label_pra)
    lapor("Berkas citra .tif tidak ditemukan", tile_tanpa_citra)
    lapor("Tile tanpa bangunan sama sekali", tile_tanpa_bangunan)
    print(f" {'OK ' if not poligon_rusak else '!! '}"
          f"{'Poligon tidak terbaca (dilewati)':<44}{poligon_rusak:>6}")
    print(f" {'OK ' if not uid_ganda else '!! '}"
          f"{'UID bangunan ganda':<44}{uid_ganda:>6}")

    print("\n [5]  BERKAS KELUARAN")
    print(" " + "-" * 76)
    for p in (p_bangunan, p_tile, p_akuisisi):
        print("  " + p)
    print(garis)
    print(" Kirimkan blok [1] sampai [4] di atas untuk penetapan komposisi sampel.")
    print(garis)


if __name__ == "__main__":
    main()
