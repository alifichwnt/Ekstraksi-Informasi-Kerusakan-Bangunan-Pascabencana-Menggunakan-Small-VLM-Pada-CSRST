#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
10_rekap_run.py
===============
Menyusun DAFTAR RUN dari seluruh folder run yang sudah diunduh ke KOMPONEN_5/runs/.

Prinsip keterulangan:
  * Setiap folder runs/<RUN_ID>/ bersifat TETAP. Skrip ini tidak pernah mengubah
    mentah.jsonl maupun manifest.json milik run mana pun.
  * hasil_terurai.csv hanya dibuat bila belum ada. Bila parser diperbaiki dan run
    ingin diurai ulang, pakai --urai-ulang: hasilnya disimpan sebagai berkas BARU
    hasil_terurai_p<sidik-parser>.csv di samping yang lama.
  * Penguraian memakai konfigurasi dan parser SALINAN di runs/<RUN_ID>/paket/,
    bukan yang ada di laptop saat ini, sehingga run lama tetap diurai dengan aturan
    yang berlaku ketika run itu dijalankan.
  * daftar_run.csv adalah INDEKS turunan dari manifest; dibangun ulang setiap kali
    skrip ini dijalankan, karena isinya sepenuhnya ditentukan oleh folder run.

Penggunaan (dari folder KOMPONEN_4):
    python 10_rekap_run.py
    python 10_rekap_run.py --runs "..\\KOMPONEN_5\\runs" --urai-ulang
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("Butuh pandas. Jalankan:  pip install pandas")

RUNS_BAWAAN = Path(__file__).resolve().parent.parent / "KOMPONEN_5" / "runs"


def sha(path: Path, n: int = 12) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:n]


def muat_parser(path: Path):
    spec = importlib.util.spec_from_file_location(f"parser_{sha(path)}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def urai_run(d: Path, parser_path: Path | None = None) -> pd.DataFrame:
    """Urai mentah.jsonl sebuah run memakai konfigurasi salinan run itu sendiri."""
    konfig = json.loads((d / "paket" / "konfigurasi_fitur.json").read_text(encoding="utf-8"))
    P = muat_parser(parser_path or (d / "paket" / "05_parser_keluaran.py"))
    mentah = [json.loads(b) for b in (d / "mentah.jsonl").read_text(encoding="utf-8").splitlines()
              if b.strip()]
    baris = []
    for m in mentah:
        h = {k: m.get(k) for k in ("uid", "tile", "kelas_xbd", "model", "run_id",
                                   "detik_fitur", "detik_kelas")}
        h.update(P.urai_fitur(m.get("mentah_fitur") or "", konfig))
        h.update(P.urai_kelas(m.get("mentah_kelas") or "", konfig))
        baris.append(h)
    df = pd.DataFrame(baris)
    df["label_kelas"] = df["kelas_xbd"].map(konfig["kelas"]["pemetaan_xbd"])
    return df


def f1_makro(y: pd.Series, p: pd.Series, kelas: list[str]) -> float:
    f = []
    for c in kelas:
        tp = ((p == c) & (y == c)).sum()
        fp = ((p == c) & (y != c)).sum()
        fn = ((p != c) & (y == c)).sum()
        f.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return float(sum(f) / len(f))


def ringkas(df: pd.DataFrame, kelas: list[str]) -> dict:
    n = len(df)
    sah = df[df["kelas_kerusakan"].isin(kelas)]
    # kelas di luar tiga kelas sah (gagal urai atau tidak_jelas) dihitung SALAH
    # pada metrik 'penuh', dan dikeluarkan pada metrik 'sah'
    pred_penuh = df["kelas_kerusakan"].where(df["kelas_kerusakan"].isin(kelas), "__salah__")
    return {
        "n": n,
        "fitur_sah": int(df["f_sah"].sum()),
        "kelas_sah": int(len(sah)),
        "kelas_tidak_jelas": int(df["kelas_tak_teramati"].sum()),
        "akurasi_penuh": round(float((pred_penuh == df["label_kelas"]).mean()), 4) if n else None,
        "f1_makro_penuh": round(f1_makro(df["label_kelas"], pred_penuh, kelas), 4) if n else None,
        "akurasi_sah": round(float((sah["kelas_kerusakan"] == sah["label_kelas"]).mean()), 4)
                       if len(sah) else None,
    }


def waktu_run(d: Path, m: dict) -> dict:
    """Ringkasan waktu komputasi untuk indeks. Sumber utama waktu_komputasi.json yang ditulis
    notebook 09 / skrip 09g; run lama (sebelum berkas itu ada) dihitung dari mentah.jsonl."""
    f = d / "waktu_komputasi.json"
    if f.exists():
        w = json.loads(f.read_text(encoding="utf-8"))
    else:
        mentah = [json.loads(b) for b in (d / "mentah.jsonl").read_text(encoding="utf-8").splitlines()
                  if b.strip()]
        v = pd.Series([(x.get("detik_fitur") or 0) + (x.get("detik_kelas") or 0) for x in mentah
                       if not (x.get("galat_fitur") or x.get("galat_kelas"))], dtype=float)
        w = {"per_bangunan": {"rerata": round(v.mean(), 2), "median": round(v.median(), 2),
                              "total_detik": round(v.sum(), 1)} if len(v) else {}}
    pb = w.get("per_bangunan") or {}
    return {"detik_per_bangunan_rerata": pb.get("rerata"),
            "detik_per_bangunan_median": pb.get("median"),
            "detik_inferensi_total": pb.get("total_detik"),
            "detik_muat_model": w.get("detik_muat_model"),
            "jam_dinding_menit": w.get("jam_dinding_loop_menit", w.get("jam_dinding_menit")),
            "memori_gpu_puncak_gb": w.get("memori_gpu_puncak_inferensi_gb")}


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--runs", type=Path, default=RUNS_BAWAAN)
    a.add_argument("--urai-ulang", action="store_true",
                   help="urai ulang semua run dengan parser di folder ini (berkas baru)")
    arg = a.parse_args()
    if not arg.runs.exists():
        sys.exit(f"Folder run tidak ditemukan: {arg.runs}")

    parser_kini = Path(__file__).resolve().parent / "05_parser_keluaran.py"
    daftar = []
    for d in sorted(p for p in arg.runs.iterdir() if (p / "manifest.json").exists()):
        m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        if m.get("jenis") in ("pengembangan", "kewajaran"):
            print(f" .  {d.name}: run {m.get('jenis')}, tidak masuk indeks inferensi")
            continue
        f_m = d / "mentah.jsonl"
        if f_m.exists() and not f_m.read_text(encoding="utf-8").strip():
            print(f" .  {d.name}: mentah.jsonl kosong (run gagal sejak awal), dilewati")
            continue
        if not f_m.exists() or not (d / "paket").exists():
            print(f" !! {d.name}: mentah.jsonl atau paket/ tidak ada, dilewati")
            continue
        f_hasil = d / "hasil_terurai.csv"
        if not f_hasil.exists():
            urai_run(d).to_csv(f_hasil, index=False, encoding="utf-8-sig")
            print(f" +  {d.name}: hasil_terurai.csv dibuat")
        if arg.urai_ulang:
            f_baru = d / f"hasil_terurai_p{sha(parser_kini, 8)}.csv"
            if not f_baru.exists():
                urai_run(d, parser_kini).to_csv(f_baru, index=False, encoding="utf-8-sig")
                print(f" +  {d.name}: {f_baru.name} dibuat (parser kini)")
        df = pd.read_csv(f_hasil)
        kelas = json.loads((d / "paket" / "konfigurasi_fitur.json").read_text(encoding="utf-8"))["kelas"]["enum"]
        e = m.get("eksperimen", {})
        daftar.append({
            "run_id": m["run_id"], "status": m.get("status"), "model": m["model"]["nama"],
            "revisi_model": (m["model"].get("revisi") or "")[:12],
            "sampel": m["sampel"]["nama"], "uji_cepat": m.get("uji_cepat"),
            "versi_prompt": e.get("versi_prompt"), "sidik_fitur": e.get("sidik_fitur"),
            "status_seleksi": e.get("status_seleksi"),
            "waktu_mulai_utc": m.get("waktu_mulai_utc"), "durasi_menit": m.get("durasi_menit"),
            "platform": m.get("lingkungan", {}).get("platform"),
            "gpu": m.get("lingkungan", {}).get("gpu"),
            **ringkas(df, kelas),
            **waktu_run(d, m),
            "catatan": m.get("catatan"),
        })
    if not daftar:
        sys.exit("Belum ada run yang sah di folder runs.")
    out = arg.runs.parent / "daftar_run.csv"
    pd.DataFrame(daftar).to_csv(out, index=False, encoding="utf-8-sig")
    tampil = ["run_id", "model", "sampel", "n", "kelas_sah", "akurasi_penuh", "f1_makro_penuh",
              "detik_per_bangunan_rerata", "status"]
    print("\n" + pd.DataFrame(daftar)[tampil].to_string(index=False))
    print(f"\nindeks ditulis: {out}")


if __name__ == "__main__":
    main()
