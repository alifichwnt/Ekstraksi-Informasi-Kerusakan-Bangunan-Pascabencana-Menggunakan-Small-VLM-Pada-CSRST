#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
16_bangun_prototipe.py
======================
Skrip penyusun data prototipe (tujuan 3). Mengambil keluaran run yang sudah dievaluasi, label xBD,
potongan citra, dan metrik evaluasi, lalu menyusunnya menjadi aplikasi web statis yang dapat dibuka
langsung di peramban (tanpa server, tanpa menjalankan model).

Aturan pemilihan sumber data (Bab III 3.2.6, ditetapkan sebelum hasil dibaca):
  * kelas kerusakan  -> SVLM dengan akurasi seimbang tertinggi pada n = 385  = Qwen2.5-VL-3B + LoRA
  * tanda & deskripsi -> SVLM dengan skor akurasi QUEST tertinggi di antara model yang keluaran
                         fitur/deskripsinya sah                              = InternVL3-2B (zero-shot)
  * label xBD ditampilkan berdampingan sebagai pembanding.
Skrip memeriksa ulang aturan ini terhadap folder analisis terbaru (15_analisis_bab4.py) dan berhenti
bila hasilnya tidak cocok dengan konstanta di bawah.

Keluaran: KOMPONEN_8/prototipe_<YYYYmmdd-HHMM>/ (index.html, assets/, data/data.js, img/,
manifest_prototipe.json) + zip dengan nama yang sama untuk dibagikan ke penguji.

Penggunaan (dari folder KOMPONEN_4, setelah 15_analisis_bab4.py dijalankan):
    pip install pandas pillow
    python 16_bangun_prototipe.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

try:
    import pandas as pd
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("Butuh pandas dan pillow. Jalankan:  pip install pandas pillow")

AKAR = Path(os.environ.get("SKRIPSI_AKAR",
            r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\MANUVER SKRIPSI AFTER SENSUS"))
RUNS = AKAR / "KOMPONEN_5" / "runs"
SAMPEL = AKAR / "KOMPONEN_3" / "Output Sampel"
CHIP = AKAR / "KOMPONEN_3" / "Output Chip"
ANALISIS = AKAR / "KOMPONEN_7"
SUMBER_APP = Path(__file__).resolve().parent / "prototipe_src"
KELUAR = AKAR / "KOMPONEN_8"

RUN_KELAS = ("Qwen2.5-VL-3B + LoRA", "20260925-100029_qwen3b-lora_besar_v4_b82f43f2")
RUN_FITUR = ("InternVL3-2B (zero-shot)", "20260924-213226_ivl2b_besar_v4_b82f43f2")
PETA_XBD = {"no-damage": "tidak_rusak", "major-damage": "rusak", "destroyed": "hancur"}
KELAS = ["tidak_rusak", "rusak", "hancur"]
FITUR = ["keutuhan_atap", "puing_sekitar", "wujud_bangunan", "sedimen_lumpur"]
SISI_THUMB = 256

# Konteks kejadian (dikutip di Bab I; sumber: Rencana Induk Pemulihan dan Pembangunan Kembali Wilayah
# Pascabencana Provinsi Sulawesi Tengah, 14 Des 2018, memuat data BNPB)
KONTEKS = {"meninggal": 2096, "hilang": 1373, "pengungsi": 173552, "kerugian_triliun": 18.48,
           "sumber": "Pemerintah Provinsi Sulawesi Tengah (2018), Rencana Induk Pemulihan dan Pembangunan Kembali "
                     "Wilayah Pascabencana, mengutip data BNPB (korban per 7 November 2018; kerusakan dan kerugian "
                     "per 26 Oktober 2018)."}


def sha(p: Path, n: int = 12) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:n]


def berkas_terurai(d: Path) -> Path:
    calon = sorted(d.glob("hasil_terurai_p*.csv"), key=lambda f: f.stat().st_mtime)
    return calon[-1] if calon else d / "hasil_terurai.csv"


def analisis_terbaru() -> Path:
    calon = sorted(p for p in ANALISIS.glob("analisis_*") if p.is_dir())
    if not calon:
        sys.exit("Folder KOMPONEN_7/analisis_* belum ada. Jalankan 15_analisis_bab4.py dulu.")
    return calon[-1]


def periksa_aturan(a: Path) -> dict:
    m = pd.read_csv(a / "T2a_metrik_klasifikasi.csv")
    m385 = m[m.himpunan == "n385"].set_index("model")
    terbaik_kelas = m385["akurasi_seimbang"].idxmax()
    q = pd.read_csv(a / "T2c_rerata_quest.csv")
    qa = q[(q.kriteria == "Akurasi") & (q.model.isin(["Qwen2.5-VL-3B", "InternVL3-2B"]))].set_index("model")["rerata"]
    terbaik_fitur = qa.idxmax()
    if terbaik_kelas != RUN_KELAS[0] or terbaik_fitur != RUN_FITUR[0].split(" (")[0]:
        sys.exit(f"Aturan sumber data tidak cocok dengan analisis: kelas={terbaik_kelas}, fitur={terbaik_fitur}. "
                 "Perbarui RUN_KELAS/RUN_FITUR.")
    lora = m385.loc[RUN_KELAS[0]]
    cm = pd.read_csv(a / "T2a_matriks_n385_Qwen2.5-VL-3B_LoRA.csv", index_col=0)[KELAS].values.tolist()
    return {"n": int(lora["n"]), "lora_acc": float(lora["akurasi"]), "lora_bacc": float(lora["akurasi_seimbang"]),
            "lora_f1": [float(lora[f"f1_{k}"]) for k in KELAS], "matriks_lora": cm,
            "quest_akurasi_fitur": float(qa[terbaik_fitur]), "folder_analisis": a.name}


def main():
    a = analisis_terbaru()
    metrik = periksa_aturan(a)
    konfig = json.loads((RUNS / RUN_FITUR[1] / "paket" / "konfigurasi_fitur.json").read_text(encoding="utf-8"))
    kand = {c["kunci"]: c for c in konfig["kandidat"]}

    besar = pd.read_csv(SAMPEL / "sampel_besar.csv")
    kecil = set(pd.read_csv(SAMPEL / "sampel_kecil.csv")["uid"])
    calon = besar[~besar["uid"].isin(kecil)]
    dev = set(pd.concat([g.sample(5, random_state=42) for _, g in calon.groupby("kelas_xbd")])["uid"])

    kls = pd.read_csv(berkas_terurai(RUNS / RUN_KELAS[1])).drop_duplicates("uid").set_index("uid")
    ftr = pd.read_csv(berkas_terurai(RUNS / RUN_FITUR[1])).drop_duplicates("uid").set_index("uid")

    waktu = datetime.datetime.now()
    out = KELUAR / f"prototipe_{waktu:%Y%m%d-%H%M}"
    (out / "img").mkdir(parents=True)
    (out / "assets").mkdir()
    (out / "data").mkdir()

    b = besar.sort_values(["lat", "lon"], ascending=[False, True]).reset_index(drop=True)
    bangunan = []
    for i, r in b.iterrows():
        kode = f"PL-{i + 1:03d}"
        pra, pasca = Image.open(CHIP / "pra" / r.chip_pra).convert("RGB"), Image.open(CHIP / "pasca" / r.chip_pasca).convert("RGB")
        kanvas = Image.new("RGB", (SISI_THUMB * 2 + 6, SISI_THUMB), (255, 255, 255))
        kanvas.paste(pra.resize((SISI_THUMB, SISI_THUMB), Image.LANCZOS), (0, 0))
        kanvas.paste(pasca.resize((SISI_THUMB, SISI_THUMB), Image.LANCZOS), (SISI_THUMB + 6, 0))
        kanvas.save(out / "img" / f"{kode}.jpg", quality=82, optimize=True)
        k, f = kls.loc[r.uid], ftr.loc[r.uid]
        kelas = k["kelas_kerusakan"] if k["kelas_kerusakan"] in KELAS else None
        if kelas is None:
            sys.exit(f"{r.uid}: kelas LoRA tidak sah ({k['kelas_kerusakan']})")
        bangunan.append({
            "kode": kode, "uid": r.uid, "lon": round(float(r.lon), 7), "lat": round(float(r.lat), 7),
            "xbd": PETA_XBD[r.kelas_xbd], "kelas": kelas,
            "fitur": {x: (f[f"fitur_{x}"] if isinstance(f[f"fitur_{x}"], str) else None) for x in FITUR},
            "deskripsi": f["deskripsi"] if isinstance(f["deskripsi"], str) else "",
            "himpunan": "pengembangan" if r.uid in dev else ("kecil" if r.uid in kecil else "besar"),
            "img": f"img/{kode}.jpg"})

    contoh = []
    for x in KELAS:
        cocok = [bb for bb in bangunan if bb["xbd"] == x and bb["kelas"] == x and bb["himpunan"] != "pengembangan"]
        contoh.append(cocok[len(cocok) // 2]["kode"])
    deskripsi_terbanyak = pd.Series([bb["deskripsi"] for bb in bangunan]).value_counts().iloc[0]

    label_level = {x: {lv: lv.replace("_", " ") for lv in kand[x]["level"]} for x in FITUR}
    for x in FITUR:
        label_level[x]["tidak_jelas"] = "tidak jelas (tidak teramati)"
    data = {
        "meta": {"tahun": "2026", "dibangun": f"{waktu:%d-%m-%Y %H:%M}", "tanggal_pra": "24 Januari 2017",
                 "tanggal_pasca": "1 Oktober 2018", "kerangka": 33060,
                 "sumber_kelas": RUN_KELAS[0], "sumber_fitur": RUN_FITUR[0],
                 "run_kelas": RUN_KELAS[1], "run_fitur": RUN_FITUR[1]},
        "konteks": KONTEKS,
        "metrik": {**metrik, "deskripsi_sama": int(deskripsi_terbanyak)},
        "label_fitur": {x: kand[x]["label"] for x in FITUR},
        "label_level": label_level, "contoh": contoh, "bangunan": bangunan}
    (out / "data" / "data.js").write_text("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    shutil.copy(SUMBER_APP / "index.html", out / "index.html")
    shutil.copy(SUMBER_APP / "app.css", out / "assets" / "app.css")
    shutil.copy(SUMBER_APP / "app.js", out / "assets" / "app.js")
    if (SUMBER_APP / "logo-stis.png").exists():
        shutil.copy(SUMBER_APP / "logo-stis.png", out / "assets" / "logo-stis.png")
    else:
        print("Peringatan: prototipe_src/logo-stis.png tidak ada; kepala halaman tampil tanpa logo.")
    (out / "BACA_SAYA.txt").write_text(
        "Cara membuka prototipe\n1. Ekstrak seluruh isi zip ke satu folder.\n2. Buka berkas index.html dengan Google Chrome "
        "atau Microsoft Edge (klik dua kali).\n3. Peta dasar memerlukan internet; tanpa internet titik tetap digambar menurut koordinat.\n"
        "4. Panduan lengkap: Buku Pedoman Penggunaan Prototipe (berkas .docx terpisah).\n",
        encoding="utf-8")
    (out / "manifest_prototipe.json").write_text(json.dumps({
        "dibangun": waktu.isoformat(timespec="seconds"), "skrip_sha": sha(Path(__file__)),
        "run_kelas": RUN_KELAS, "run_fitur": RUN_FITUR, "folder_analisis": a.name,
        "masukan": {str(p.relative_to(AKAR)): sha(p) for p in
                    [SAMPEL / "sampel_besar.csv", berkas_terurai(RUNS / RUN_KELAS[1]), berkas_terurai(RUNS / RUN_FITUR[1])]},
        "sumber_app": {p.name: sha(p) for p in SUMBER_APP.iterdir() if p.is_file()},
        "n_bangunan": len(bangunan)}, ensure_ascii=False, indent=2), encoding="utf-8")
    z = shutil.make_archive(str(out), "zip", root_dir=out.parent, base_dir=out.name)
    ukuran = sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) / 1e6
    print(f"Prototipe: {out} ({len(bangunan)} bangunan, {ukuran:.1f} MB)\nZip untuk penguji: {z}")
    print(f"Contoh web story: {', '.join(contoh)} | deskripsi terbanyak dipakai {deskripsi_terbanyak} kali")


if __name__ == "__main__":
    main()
