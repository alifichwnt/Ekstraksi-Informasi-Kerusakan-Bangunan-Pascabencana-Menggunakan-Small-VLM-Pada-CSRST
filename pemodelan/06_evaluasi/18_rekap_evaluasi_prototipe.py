#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
18_rekap_evaluasi_prototipe.py
==============================
Rekap evaluasi prototipe (tujuan 3) dari ekspor Google Sheets (Google Form evaluasi artefak):
  (1) Black-box testing: status Berhasil/Gagal per skenario B01-B19 dan per evaluator.
  (2) System Usability Scale versi bahasa Indonesia (Sharfina dan Santoso, 2017), 10 butir skala 1-5:
        skor = 2,5 x [ sum(butir ganjil - 1) + sum(5 - butir genap) ]      (Brooke, 1996)
      dibandingkan dengan rerata acuan 68 (Lewis, 2018) dan batas kategori Bangor dkk. (2009):
      50,9 (OK), 71,4 (good), 85,5 (excellent).
  (3) Pemeriksaan pola jawaban seragam (semua butir SUS bernilai sama). Respons yang terdeteksi TIDAK dibuang dari hasil
      utama karena aturan pengecualian tidak ditetapkan sebelum pengumpulan data; hasil tanpa respons tersebut dilaporkan
      sebagai analisis sensitivitas.
Nama dan alamat email evaluator tidak disalin ke keluaran; evaluator diidentifikasi dengan kode EVAL01-EVAL05.

Masukan : KOMPONEN_6/Formulir/*(Responses)*.csv (ekspor terbaru)
Keluaran: KOMPONEN_7/evaluasi_prototipe_<YYYYmmdd-HHMMSS>/
          00_ringkasan_evaluasi_prototipe.md, T3_blackbox_matriks.csv, T3_sus_per_evaluator.csv, T3_sus_ringkas.csv,
          T3_sus_kontribusi_butir.csv, T3_identitas_perangkat.csv, T3_masukan_terbuka.csv, manifest_evaluasi_prototipe.json

Penggunaan (dari folder KOMPONEN_4):
    python 18_rekap_evaluasi_prototipe.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("Butuh pandas dan numpy. Jalankan:  pip install pandas numpy")

AKAR = Path(os.environ.get("SKRIPSI_AKAR",
            r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\MANUVER SKRIPSI AFTER SENSUS"))
FORMULIR = AKAR / "KOMPONEN_6" / "Formulir"
KELUAR = AKAR / "KOMPONEN_7"
ACUAN_SUS = 68.0
BATAS_BANGOR = [(85.5, "excellent"), (71.4, "good"), (50.9, "OK")]
JUMLAH_SKENARIO, JUMLAH_BUTIR = 19, 10


def koma(x, d=2) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def kategori(skor: float) -> str:
    for batas, nama in BATAS_BANGOR:
        if skor >= batas:
            return nama
    return "di bawah OK"


def skor_sus(butir: np.ndarray) -> np.ndarray:
    """butir: matriks n x 10 bernilai 1-5 berurutan butir 1..10."""
    ganjil, genap = butir[:, 0::2], butir[:, 1::2]
    return 2.5 * ((ganjil - 1).sum(axis=1) + (5 - genap).sum(axis=1))


def kontribusi(butir: np.ndarray) -> np.ndarray:
    """Kontribusi 0-4 per butir (butir positif = nilai - 1, butir negatif = 5 - nilai)."""
    positif = (np.arange(JUMLAH_BUTIR) % 2 == 0)
    return np.where(positif, butir - 1, 5 - butir)


def ringkas(skor: pd.Series, label: str) -> dict:
    return {"himpunan": label, "n": int(skor.size), "rerata": skor.mean(), "simpangan_baku": skor.std(ddof=1),
            "median": skor.median(), "minimum": skor.min(), "maksimum": skor.max(),
            "kategori_rerata": kategori(skor.mean()), "di_atas_68": bool(skor.mean() > ACUAN_SUS)}


def cari_kolom(kolom: list[str], pola: str) -> dict[int, str]:
    hasil = {}
    for k in kolom:
        m = re.match(pola, k.strip(), flags=re.I)
        if m:
            hasil[int(m.group(1))] = k
    return dict(sorted(hasil.items()))


def main():
    calon = sorted(FORMULIR.glob("*Responses*.csv"), key=lambda p: p.stat().st_mtime)
    if not calon:
        sys.exit(f"Ekspor Google Form (*Responses*.csv) tidak ditemukan di {FORMULIR}")
    sumber = calon[-1]
    d = pd.read_csv(sumber, dtype=str).fillna("")
    d.columns = [re.sub(r"\s+", " ", c).strip() for c in d.columns]

    kode_kol = next(c for c in d.columns if c.lower().startswith("kode evaluator"))
    d["kode"] = d[kode_kol].str.strip().str.upper()
    if d["kode"].duplicated().any():
        sys.exit(f"Kode evaluator ganda: {d.loc[d['kode'].duplicated(), 'kode'].tolist()} — hapus respons uji/ganda dulu.")
    d = d.sort_values("kode").reset_index(drop=True)

    kol_b = cari_kolom(list(d.columns), r"^B(\d{2})\b")
    kol_s = cari_kolom(list(d.columns), r"^SUS\s*(\d{2})\b")
    if len(kol_b) != JUMLAH_SKENARIO or len(kol_s) != JUMLAH_BUTIR:
        sys.exit(f"Kolom tidak lengkap: {len(kol_b)} skenario, {len(kol_s)} butir SUS.")

    # ---------------------------------------------------------------- black-box
    status = d[list(kol_b.values())].apply(lambda s: s.str.strip().str.capitalize())
    tidak_sah = ~status.isin(["Berhasil", "Gagal"])
    if tidak_sah.values.any():
        sys.exit("Ada status black-box selain Berhasil/Gagal.")
    matriks = pd.DataFrame({"skenario": [re.sub(r"\s+", " ", kol_b[i]).strip() for i in kol_b]})
    for j, kode in enumerate(d["kode"]):
        matriks[kode] = ["B" if v == "Berhasil" else "G" for v in status.iloc[j].values]
    matriks["jumlah_berhasil"] = (status == "Berhasil").sum(axis=0).values
    matriks["n_evaluator"] = len(d)
    total_b, total = int((status == "Berhasil").values.sum()), status.size

    # ---------------------------------------------------------------- SUS
    butir = d[list(kol_s.values())].apply(pd.to_numeric, errors="coerce")
    if butir.isna().values.any() or not butir.isin([1, 2, 3, 4, 5]).values.all():
        sys.exit("Ada jawaban SUS kosong atau di luar 1-5.")
    X = butir.values.astype(int)
    skor = pd.Series(skor_sus(X), index=d["kode"])
    seragam = pd.Series(X.std(axis=1) == 0, index=d["kode"])
    kol_perangkat = next((c for c in d.columns if c.lower().startswith("perangkat")), None)
    kol_peramban = next((c for c in d.columns if c.lower().startswith("peramban")), None)
    per_eval = pd.DataFrame({"kode": d["kode"],
                             "perangkat": d[kol_perangkat] if kol_perangkat else "",
                             **{f"butir_{i:02d}": X[:, i - 1] for i in range(1, JUMLAH_BUTIR + 1)},
                             "skor_sus": skor.values, "kategori_bangor": [kategori(s) for s in skor.values],
                             "jawaban_seragam": seragam.values})
    baris = [ringkas(skor, "semua evaluator (hasil utama)")]
    if seragam.any():
        baris.append(ringkas(skor[~seragam], "tanpa jawaban seragam (sensitivitas)"))
    tabel_ringkas = pd.DataFrame(baris)
    kontrib = pd.DataFrame({"butir": list(range(1, JUMLAH_BUTIR + 1)),
                            "arah": ["positif" if i % 2 == 1 else "negatif" for i in range(1, JUMLAH_BUTIR + 1)],
                            "pernyataan": [re.sub(r"^SUS\s*\d{2}\s*[-–]\s*", "", kol_s[i]).strip() for i in kol_s],
                            "rerata_jawaban": X.mean(axis=0), "rerata_kontribusi_0_4": kontribusi(X).mean(axis=0)})

    # ---------------------------------------------------------------- identitas & masukan (tanpa nama/email)
    identitas = pd.DataFrame({"kode": d["kode"], "waktu_kirim": d.get("Timestamp", ""),
                              "perangkat": d[kol_perangkat] if kol_perangkat else "",
                              "peramban": d[kol_peramban] if kol_peramban else ""})
    kol_terbuka = [c for c in d.columns if c.lower().startswith(("bagian prototipe", "bagian yang", "catatan"))]
    masukan = d[["kode"] + kol_terbuka].copy()

    # ---------------------------------------------------------------- tulis
    waktu = datetime.datetime.now()
    out = KELUAR / f"evaluasi_prototipe_{waktu:%Y%m%d-%H%M%S}"
    out.mkdir(parents=True)
    matriks.to_csv(out / "T3_blackbox_matriks.csv", index=False)
    per_eval.to_csv(out / "T3_sus_per_evaluator.csv", index=False)
    tabel_ringkas.to_csv(out / "T3_sus_ringkas.csv", index=False)
    kontrib.to_csv(out / "T3_sus_kontribusi_butir.csv", index=False)
    identitas.to_csv(out / "T3_identitas_perangkat.csv", index=False)
    masukan.to_csv(out / "T3_masukan_terbuka.csv", index=False)

    gagal = [(matriks.loc[i, "skenario"], k) for i in range(len(matriks)) for k in d["kode"] if matriks.loc[i, k] == "G"]
    md = [f"# Rekap evaluasi prototipe (tujuan 3)\n",
          f"Sumber: `{sumber.name}` ({len(d)} respons; kode {', '.join(d['kode'])}). Disusun {waktu:%d-%m-%Y %H:%M}.\n",
          "## Black-box testing",
          f"- {total_b} dari {total} hasil uji berhasil ({koma(100 * total_b / total, 1)}%).",
          f"- Skenario berhasil pada semua evaluator: {int((matriks['jumlah_berhasil'] == len(d)).sum())} dari {len(matriks)}.",
          "- Hasil gagal: " + ("; ".join(f"{s} oleh {k}" for s, k in gagal) if gagal else "tidak ada") + ".\n",
          "## System Usability Scale",
          "| Evaluator | Perangkat | Skor SUS | Kategori | Jawaban seragam |", "|---|---|---|---|---|"]
    md += [f"| {r.kode} | {r.perangkat} | {koma(r.skor_sus, 1)} | {r.kategori_bangor} | {'ya' if r.jawaban_seragam else 'tidak'} |"
           for r in per_eval.itertuples()]
    md.append("")
    for r in tabel_ringkas.itertuples():
        md.append(f"- {r.himpunan}: n = {r.n}, rerata {koma(r.rerata)} (simpangan baku {koma(r.simpangan_baku)}), median "
                  f"{koma(r.median)}, rentang {koma(r.minimum, 1)}–{koma(r.maksimum, 1)}; kategori {r.kategori_rerata}; "
                  f"{'di atas' if r.di_atas_68 else 'tidak di atas'} acuan 68.")
    md.append("\nKontribusi rata-rata per butir (0–4): " +
              ", ".join(f"butir {int(r.butir)} {koma(r.rerata_kontribusi_0_4)}" for r in kontrib.itertuples()) + ".")
    md.append("\nCatatan: respons dengan jawaban seragam tetap masuk hasil utama (tidak ada aturan pengecualian yang ditetapkan "
              "sebelum pengumpulan data); n kecil sehingga skor dibaca deskriptif tanpa uji inferensial.")
    (out / "00_ringkasan_evaluasi_prototipe.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "manifest_evaluasi_prototipe.json").write_text(json.dumps({
        "dibuat": waktu.isoformat(timespec="seconds"),
        "skrip_sha": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12],
        "masukan": {sumber.name: hashlib.sha256(sumber.read_bytes()).hexdigest()[:12]},
        "n_respons": len(d)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print((out / "00_ringkasan_evaluasi_prototipe.md").read_text(encoding="utf-8"))
    print(f"Keluaran: {out}")


if __name__ == "__main__":
    main()
