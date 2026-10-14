#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04_susun_prompt.py
==================
Membangkitkan seluruh artefak tekstual eksperimen dari SATU berkas konfigurasi
(`konfigurasi_fitur.json`):

  * prompt untuk tiga konfigurasi penyajian masukan (a, b, c)
  * prompt lengan ablasi A (tanpa blok definisi fitur)
  * skema JSON keluaran
  * butir formulir evaluator

Alasan semuanya dibangkitkan dari satu sumber: enum pada formulir evaluator
WAJIB identik dengan enum pada keluaran model, jika tidak, perbandingan
evaluator-model tidak sah. Mengetik ulang daftar fitur di dua tempat adalah
cara paling umum hal itu rusak tanpa disadari.

Daftar enam fitur terpilih hanyalah satu baris di berkas konfigurasi. Ketika
penilaian dosen pembimbing masuk, ubah baris itu, jalankan ulang skrip ini,
dan seluruh artefak ikut berubah serempak. Chip dan sampel TIDAK perlu dibuat
ulang - keduanya tidak bergantung pada fitur terpilih.

Setiap prompt diberi sidik (hash) delapan karakter dari daftar fitur terpilih.
Sidik itu ikut ditulis pada nama berkas keluaran inferensi, sehingga setiap
hasil selalu dapat ditelusuri ke versi seleksi fitur yang melahirkannya.

Penggunaan:
    python 04_susun_prompt.py
    python 04_susun_prompt.py --konfig konfigurasi_fitur.json --out "Output Prompt"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

VERSI_PROMPT = 3   # v1: model menyalin daftar enum. v2: model menghindar ke 'tidak_jelas'.
                   # v3: level dipisahkan dari kode tak teramati, aturan penghindaran dipersempit.
KONFIG_BAWAAN = Path(__file__).resolve().parent / "konfigurasi_fitur.json"
OUT_BAWAAN = Path(__file__).resolve().parent / "Output Prompt"

PENYAJIAN = {
    "a": ("dua citra terpisah",
          "Anda menerima DUA citra. Citra pertama adalah kondisi PRA-BENCANA. "
          "Citra kedua adalah kondisi PASCA-BENCANA. Keduanya meliput petak tanah "
          "yang persis sama."),
    "b": ("satu citra gabungan berdampingan",
          "Anda menerima SATU citra yang memuat dua panel berdampingan. Panel kiri "
          "berlabel PRA-BENCANA, panel kanan berlabel PASCA-BENCANA. Keduanya "
          "meliput petak tanah yang persis sama."),
    "c": ("hanya citra pasca-bencana (ablasi)",
          "Anda menerima SATU citra, yaitu kondisi PASCA-BENCANA. Citra pra-bencana "
          "tidak tersedia."),
}

BLOK_PERAN = (
    "[PERAN]\n"
    "Anda adalah penafsir citra satelit resolusi sangat tinggi yang bertugas menilai "
    "kerusakan bangunan setelah bencana gempa bumi dan tsunami."
)

BLOK_PENANDA = (
    "Pada setiap citra terdapat satu kotak berwarna magenta di bagian tengah, "
    "dengan tanda bidik silang tepat di titik pusatnya. Bangunan yang harus Anda "
    "nilai adalah bangunan yang ditunjuk oleh bidik silang tersebut. Bangunan lain "
    "di dalam citra hanya berperan sebagai konteks dan tidak boleh dinilai. "
    "Ukuran kotak selalu sama untuk semua citra dan tidak menyatakan ukuran bangunan."
)

ATURAN = [
    "Nilailah HANYA bangunan yang ditunjuk bidik silang.",
    "Setiap field diisi TEPAT SATU pilihan. Jangan menyalin daftar pilihan. "
    "Jawaban yang masih memuat tanda | dianggap salah.",
    "Pilih \"tidak_jelas\" HANYA bila bangunan sasaran benar-benar tidak dapat dilihat, "
    "yaitu tertutup awan, bayangan pekat, atau tajuk pohon. Bila bangunannya terlihat, "
    "Anda HARUS memilih salah satu nilai yang pasti, sekalipun keputusannya sulit. "
    "\"tidak_jelas\" bukan jawaban untuk kasus yang sulit.",
    "Tetapkan kelas kerusakan berdasarkan jawaban fitur Anda sendiri di atas, bukan berdasarkan "
    "kesan umum terhadap citra.",
    "Jawab HANYA dengan satu objek JSON yang sah. Tanpa kalimat pembuka, tanpa "
    "penjelasan tambahan, tanpa pagar kode.",
    "Seluruh nilai selain field \"deskripsi\" harus persis salah satu pilihan yang "
    "disebutkan. Jangan membuat istilah baru.",
    "Field \"deskripsi\" berisi SATU kalimat bahasa Indonesia yang menerangkan "
    "kondisi bangunan sasaran, bukan pengulangan daftar fitur.",
]

ATURAN_TANPA_PRA = (
    "Karena citra pra-bencana tidak tersedia, hal yang hanya dapat dipastikan "
    "melalui perbandingan dengan kondisi sebelum bencana harus dijawab "
    "\"tidak_jelas\"."
)


def muat(konfig: Path) -> dict:
    if not konfig.exists():
        sys.exit(f"Berkas konfigurasi tidak ditemukan: {konfig}")
    k = json.loads(konfig.read_text(encoding="utf-8"))
    kunci_sah = {c["kunci"] for c in k["kandidat"]}
    terpilih = k["seleksi"]["terpilih"]
    salah = [t for t in terpilih if t not in kunci_sah]
    if salah:
        sys.exit(f"Kunci fitur tidak dikenal pada 'terpilih': {salah}")
    if len(terpilih) != len(set(terpilih)):
        sys.exit("Ada kunci fitur kembar pada 'terpilih'.")
    if not 1 <= len(terpilih) <= 6:
        sys.exit(f"Jumlah fitur terpilih harus 1 sampai 6, saat ini {len(terpilih)}.")
    return k


def fitur_terpilih(k: dict) -> list[dict]:
    peta = {c["kunci"]: c for c in k["kandidat"]}
    return [peta[t] for t in k["seleksi"]["terpilih"]]


def sidik(k: dict) -> str:
    """Sidik delapan karakter dari daftar fitur terpilih, urutan diperhitungkan."""
    isi = "|".join(k["seleksi"]["terpilih"])
    return hashlib.sha256(isi.encode("utf-8")).hexdigest()[:8]


def blok_definisi(fitur: list[dict], k: dict) -> str:
    """Definisi operasional lengkap: level dipisahkan dari kode tak teramati, dan
    skala ukurnya dinyatakan agar urutan tingkat terbaca oleh model."""
    baris = [f"[DEFINISI FITUR]",
             f"Nilailah {len(fitur)} hal berikut, satu per satu."]
    tak = k["skala_pengukuran"]["kode_tak_teramati"]
    for i, f in enumerate(fitur, 1):
        lv = f.get("level") or [e for e in f["enum"] if e != tak]
        if f.get("skala_ukur", "").startswith("ordinal"):
            pilihan = " -> ".join(f'"{e}"' for e in lv)
            ket = "bertingkat dari paling ringan ke paling berat"
        else:
            pilihan = " / ".join(f'"{e}"' for e in lv)
            ket = "pilih salah satu"
        baris.append(f"{i}. {f['label']} (kunci: {f['kunci']})")
        baris.append(f"   Definisi : {f['definisi']}")
        baris.append(f"   Pilihan  : {pilihan}   ({ket})")
        baris.append(f'   Bila bangunan tidak terlihat sama sekali: "{tak}"')
    return "\n".join(baris)


def blok_rubrik(k: dict) -> str:
    baris = ["[RUBRIK KELAS KERUSAKAN]",
             "Tetapkan satu kelas kerusakan untuk bangunan sasaran."]
    for kelas in k["kelas"]["enum"]:
        baris.append(f"- \"{kelas}\": {k['kelas']['rubrik'][kelas]}")
    baris.append(f"- \"{k['kelas']['kode_tak_teramati']}\": bangunan sasaran tidak dapat dilihat "
                 f"sama sekali pada citra, sehingga kelasnya tidak dapat ditetapkan. "
                 f"Ini BUKAN tingkat kerusakan.")
    return "\n".join(baris)


def skema_keluaran(k: dict, fitur: list[dict], pakai_fitur: bool) -> dict:
    """Skema sebagai dokumentasi (masuk Bab 3 dan berkas skema_keluaran_*.json)."""
    isi: dict = {}
    if pakai_fitur:
        isi["fitur"] = {f["kunci"]: " | ".join(f["enum"]) for f in fitur}
    isi["kelas_kerusakan"] = " | ".join(k["kelas"]["enum"])
    isi["keyakinan"] = "bilangan desimal 0.0 sampai 1.0"
    isi["deskripsi"] = "satu kalimat bahasa Indonesia"
    return isi


def blok_format(k: dict, fitur: list[dict], pakai_fitur: bool) -> str:
    """Kerangka keluaran untuk DI DALAM prompt.

    Berbeda dengan skema dokumentasi di atas, kerangka ini TIDAK boleh
    menampilkan daftar pilihan sebagai nilai. Model berukuran 2-3 miliar
    parameter cenderung menyalin apa pun yang tampak sebagai nilai pada
    contoh terakhir yang dilihatnya; pada versi 1 prompt ini seluruh keluaran
    berisi salinan daftar enum, bukan pilihan. Karena itu nilai ditulis sebagai
    ruang isian di dalam tanda < >, ditambah satu contoh benar dan satu contoh
    salah pada tingkat FORMAT, bukan pada tingkat jawaban.

    Contoh format bukan contoh berlabel: tidak ada pasangan citra-jawaban di
    dalamnya, sehingga prompt tetap zero-shot.
    """
    baris = ["[FORMAT KELUARAN]",
             "Balas HANYA dengan satu objek JSON mengikuti kerangka di bawah.",
             "Setiap bagian di dalam tanda < > adalah ruang isian: GANTI seluruhnya, "
             "termasuk tanda < > itu sendiri, dengan satu jawaban Anda.",
             ""]
    isi = []
    if pakai_fitur:
        dalam = ",\n".join(
            f'    "{f["kunci"]}": "<pilih satu: {", ".join(f["enum"])}>"' for f in fitur)
        isi.append('  "fitur": {\n' + dalam + "\n  }")
    kelas_pilihan = list(k["kelas"]["enum"]) + [k["kelas"]["kode_tak_teramati"]]
    isi.append(f'  "kelas_kerusakan": "<pilih satu: {", ".join(kelas_pilihan)}>"')
    isi.append('  "keyakinan": <angka desimal antara 0.0 dan 1.0, tanpa tanda kutip>')
    isi.append('  "deskripsi": "<satu kalimat bahasa Indonesia>"')
    baris.append("{\n" + ",\n".join(isi) + "\n}")

    contoh_fitur = fitur[0] if (pakai_fitur and fitur) else None
    baris += ["",
              "Perhatikan bentuk pengisian yang benar:"]
    if contoh_fitur:
        baris += [f'  BENAR : "{contoh_fitur["kunci"]}": "{contoh_fitur["enum"][-1]}"',
                  f'  SALAH : "{contoh_fitur["kunci"]}": '
                  f'"{" | ".join(contoh_fitur["enum"])}"',
                  f'  SALAH : "{contoh_fitur["kunci"]}": '
                  f'"<pilih satu: {", ".join(contoh_fitur["enum"])}>"']
    baris += ['  BENAR : "keyakinan": 0.7',
              '  SALAH : "keyakinan": "angka desimal antara 0.0 dan 1.0"']
    return "\n".join(baris)


def susun_prompt(k: dict, fitur: list[dict], varian: str, pakai_fitur: bool) -> str:
    nama, kalimat_input = PENYAJIAN[varian]
    aturan = list(ATURAN)
    if varian == "c":
        aturan.insert(1, ATURAN_TANPA_PRA)
    if not pakai_fitur:
        aturan = [a for a in aturan
                  if "tidak_jelas" not in a or "citra pra-bencana" in a]
        aturan.insert(1, "Jika kondisi bangunan tidak dapat Anda pastikan dari citra, "
                         "pilih kelas yang paling sesuai dan turunkan nilai "
                         "\"keyakinan\".")

    bagian = [BLOK_PERAN, "",
              "[INPUT]", kalimat_input, BLOK_PENANDA, ""]
    if pakai_fitur:
        bagian += [blok_definisi(fitur, k), ""]
    bagian += [blok_rubrik(k), "",
               "[ATURAN]"]
    bagian += [f"{i}. {a}" for i, a in enumerate(aturan, 1)]
    bagian += ["", blok_format(k, fitur, pakai_fitur)]
    return "\n".join(bagian) + "\n"


def butir_evaluator(fitur: list[dict], k: dict) -> list[dict]:
    """Butir formulir evaluator. Enum sengaja disalin dari objek fitur yang sama
    dengan yang dipakai prompt, bukan diketik ulang."""
    butir = [{"no": i, "jenis": "pilihan", "kunci": f["kunci"],
              "skala_ukur": f.get("skala_ukur", ""),
              "pertanyaan": f["label"], "keterangan": f["definisi"],
              "pilihan": " / ".join(f["enum"])}
             for i, f in enumerate(fitur, 1)]
    butir.append({"no": len(fitur) + 1, "jenis": "isian_bebas", "kunci": "deskripsi",
                  "skala_ukur": "-",
                  "pertanyaan": "Tuliskan satu kalimat yang menerangkan kondisi "
                                "bangunan yang ditunjuk bidik silang.",
                  "keterangan": "Kalimat ini menjadi rujukan bagi metrik teks "
                                "(BLEU, METEOR, ROUGE).",
                  "pilihan": ""})
    butir.append({"no": len(fitur) + 2, "jenis": "pilihan", "kunci": "kelas_biner",
                  "skala_ukur": "nominal biner",
                  "pertanyaan": "Menurut Anda, bangunan tersebut termasuk?",
                  "keterangan": "Dipakai sebagai pemeriksaan mutu evaluator "
                                "terhadap label xBD.",
                  "pilihan": "tidak rusak / rusak"})
    return butir


def main() -> None:
    p = argparse.ArgumentParser(description="Pembangkit prompt dan artefak turunannya")
    p.add_argument("--konfig", type=Path, default=KONFIG_BAWAAN)
    p.add_argument("--out", type=Path, default=OUT_BAWAAN)
    a = p.parse_args()

    k = muat(a.konfig)
    fitur = fitur_terpilih(k)
    sid = sidik(k)
    a.out.mkdir(parents=True, exist_ok=True)

    berkas = []
    for varian in ("a", "b", "c"):
        teks = susun_prompt(k, fitur, varian, pakai_fitur=True)
        f = a.out / f"prompt_{varian}_v{VERSI_PROMPT}_{sid}.txt"
        f.write_text(teks, encoding="utf-8")
        berkas.append((f, len(teks.split())))
    # lengan ablasi: prompt tanpa blok definisi fitur, memakai penyajian b
    teks = susun_prompt(k, fitur, "b", pakai_fitur=False)
    f = a.out / f"prompt_ablasiA_v{VERSI_PROMPT}_{sid}.txt"
    f.write_text(teks, encoding="utf-8")
    berkas.append((f, len(teks.split())))

    (a.out / f"skema_keluaran_{sid}.json").write_text(
        json.dumps(skema_keluaran(k, fitur, True), ensure_ascii=False, indent=2),
        encoding="utf-8")

    import csv
    with (a.out / f"butir_formulir_evaluator_{sid}.csv").open(
            "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["no", "jenis", "kunci", "skala_ukur",
                                           "pertanyaan", "keterangan", "pilihan"])
        w.writeheader()
        w.writerows(butir_evaluator(fitur, k))

    with (a.out / f"tabel_definisi_operasional_{sid}.csv").open(
            "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "no", "kandidat", "kelompok", "golongan", "butuh_citra_pra", "skala_ukur",
            "level", "kode_tak_teramati", "definisi_operasional", "rujukan_level",
            "keteramatan", "status"])
        w.writeheader()
        for c in k["kandidat"]:
            w.writerow({
                "no": c["no"], "kandidat": c["label"], "kelompok": c["kelompok"],
                "golongan": c.get("golongan", ""),
                "butuh_citra_pra": "ya" if c.get("butuh_pra") else "tidak",
                "skala_ukur": c.get("skala_ukur", ""),
                "level": " > ".join(c.get("level", [])),
                "kode_tak_teramati": c.get("kode_tak_teramati", ""),
                "definisi_operasional": c["definisi"],
                "rujukan_level": c.get("rujukan_level", ""),
                "keteramatan": c.get("keteramatan", ""),
                "status": "TERPILIH" if c["kunci"] in k["seleksi"]["terpilih"] else "tidak dipakai",
            })

    (a.out / f"manifes_{sid}.json").write_text(json.dumps({
        "sidik_fitur": sid,
        "versi_prompt": VERSI_PROMPT,
        "status_seleksi": k["seleksi"]["status"],
        "sumber_seleksi": k["seleksi"]["sumber"],
        "fitur_terpilih": k["seleksi"]["terpilih"],
        "golongan_fitur_terpilih": {t: next(c["golongan"] for c in k["kandidat"] if c["kunci"] == t)
                                    for t in k["seleksi"]["terpilih"]},
        "butuh_citra_pra": [t for t in k["seleksi"]["terpilih"]
                            if next(c["butuh_pra"] for c in k["kandidat"] if c["kunci"] == t)],
        "kelas_enum": k["kelas"]["enum"],
        "pemetaan_biner": k["kelas"]["pemetaan_biner"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 78)
    print(" PEMBANGKITAN PROMPT DAN ARTEFAK TURUNAN")
    print("=" * 78)
    print(f" Status seleksi fitur : {k['seleksi']['status']}")
    print(f" Sumber               : {k['seleksi']['sumber']}")
    if k["seleksi"]["status"] != "FINAL":
        print(f" Akan diganti         : {k['seleksi'].get('akan_diganti', '-')}")
    print(f" Sidik fitur          : {sid}")
    print(f" Versi prompt         : v{VERSI_PROMPT}")
    print(f" Fitur terpilih       : {len(fitur)}")
    for i, f in enumerate(fitur, 1):
        print(f"   {i}. {f['label']:<44}{f.get('golongan',''):<11}"
              f"{f.get('skala_ukur',''):<16}{'/'.join(f.get('level', []))}")
    n_pra = sum(1 for f in fitur if f.get("butuh_pra"))
    print(f"\n Fitur golongan PERUBAHAN (wajib ada citra pra): {n_pra} dari {len(fitur)}")
    if n_pra:
        print("   -> konfigurasi masukan yang hanya memberi citra pasca TIDAK dapat")
        print("      menjawab fitur-fitur ini; jawaban yang benar adalah kode tak teramati.")
    print("\n Berkas prompt:")
    for f, n in berkas:
        print(f"   {f.name:<34} {n:>4} kata")
    print(f"\n Folder keluaran      : {a.out}")
    print("=" * 78)
    if k["seleksi"]["status"] != "FINAL":
        print(" PERINGATAN: seleksi fitur belum final. Hasil inferensi yang memakai")
        print(" prompt ini hanya sah sebagai uji coba pipeline, bukan hasil penelitian.")
        print("=" * 78)


if __name__ == "__main__":
    main()
