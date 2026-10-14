#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04_susun_prompt.py  (versi prompt 4)
====================================
Membangkitkan seluruh artefak tekstual eksperimen dari SATU berkas konfigurasi
(`konfigurasi_fitur.json`):

  * prompt_fitur_v4_<sidik>.txt   panggilan 1: citra pra + pasca -> fitur + deskripsi
  * prompt_kelas_v4_<sidik>.txt   panggilan 2: citra pasca saja  -> kelas kerusakan
  * skema_keluaran_<sidik>.json   skema kedua panggilan (dokumentasi Bab 3)
  * butir_formulir_evaluator_<sidik>.csv
  * tabel_definisi_operasional_<sidik>.csv   (Tabel Bab 3)
  * manifes_<sidik>.json          termasuk sidik SHA-256 setiap prompt

Mengapa dua panggilan (lihat 'desain_inferensi' pada konfigurasi):
  - dua fitur terpilih bergolongan PERUBAHAN, jadi wajib melihat citra pra;
  - uji kendali 23 September menunjukkan kelas paling terbaca dari citra pasca
    tunggal 448 piksel;
  - bila kelas diminta dalam prompt yang sama dengan fitur, model menurunkan
    kelas dari jawaban fiturnya sendiri, sehingga asosiasi fitur-kelas pada
    Bab 4 menjadi artefak prompt. Dua panggilan yang tidak saling melihat
    jawaban membuat asosiasi itu sah untuk dianalisis.

Enum pada formulir evaluator diambil dari objek fitur yang sama dengan prompt,
tidak diketik ulang, agar perbandingan evaluator-model sah.

Penggunaan:
    python 04_susun_prompt.py
    python 04_susun_prompt.py --konfig konfigurasi_fitur.json --out "Output Prompt"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

VERSI_PROMPT = 4
# v1: model menyalin daftar enum.
# v2: model menghindar ke 'tidak_jelas' (19 dari 20).
# v3: level dipisahkan dari kode tak teramati; aturan penghindaran dipersempit.
# v4: dua panggilan terpisah (fitur: pra+pasca; kelas: pasca saja), 3 kelas,
#     4 fitur hasil seleksi dua penilai.

KONFIG_BAWAAN = Path(__file__).resolve().parent / "konfigurasi_fitur.json"
OUT_BAWAAN = Path(__file__).resolve().parent / "Output Prompt"

BLOK_PERAN = (
    "[PERAN]\n"
    "Anda adalah penafsir citra satelit resolusi sangat tinggi yang bertugas menilai "
    "kerusakan bangunan setelah gempa bumi dan tsunami."
)

BLOK_PENANDA = (
    "Pada setiap citra terdapat satu kotak berwarna magenta di bagian tengah, "
    "dengan tanda bidik silang tepat di titik pusatnya. Bangunan yang harus Anda "
    "nilai adalah bangunan yang ditunjuk oleh bidik silang tersebut. Bangunan lain "
    "di dalam citra hanya konteks dan tidak dinilai. Ukuran kotak selalu sama untuk "
    "semua citra dan tidak menyatakan ukuran bangunan."
)

INPUT_FITUR = (
    "Anda menerima DUA citra dari petak tanah yang persis sama. Citra pertama adalah "
    "kondisi PRA-BENCANA. Citra kedua adalah kondisi PASCA-BENCANA."
)

INPUT_KELAS = "Anda menerima SATU citra, yaitu kondisi PASCA-BENCANA."


# --------------------------------------------------------------------------- #
# pemuatan dan pemeriksaan konfigurasi
# --------------------------------------------------------------------------- #

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
    if "rubrik_pasca" not in k["kelas"]:
        sys.exit("konfigurasi belum memuat kelas.rubrik_pasca (dibutuhkan prompt v4).")
    return k


def fitur_terpilih(k: dict) -> list[dict]:
    peta = {c["kunci"]: c for c in k["kandidat"]}
    return [peta[t] for t in k["seleksi"]["terpilih"]]


def sidik(k: dict) -> str:
    """Sidik delapan karakter dari daftar fitur terpilih, urutan diperhitungkan."""
    isi = "|".join(k["seleksi"]["terpilih"])
    return hashlib.sha256(isi.encode("utf-8")).hexdigest()[:8]


def hash_teks(teks: str) -> str:
    return hashlib.sha256(teks.encode("utf-8")).hexdigest()[:12]


# --------------------------------------------------------------------------- #
# prompt panggilan 1: fitur
# --------------------------------------------------------------------------- #

def blok_definisi(fitur: list[dict], k: dict) -> str:
    tak = k["skala_pengukuran"]["kode_tak_teramati"]
    baris = ["[DEFINISI FITUR]",
             f"Nilailah {len(fitur)} hal berikut untuk bangunan sasaran, satu per satu."]
    for i, f in enumerate(fitur, 1):
        lv = f.get("level") or [e for e in f["enum"] if e != tak]
        if f.get("skala_ukur", "").startswith("ordinal"):
            pilihan = " -> ".join(f'"{e}"' for e in lv)
            ket = "bertingkat dari paling ringan ke paling berat"
        else:
            pilihan = " / ".join(f'"{e}"' for e in lv)
            ket = "pilih salah satu"
        cara = ("bandingkan citra pra dan pasca" if f.get("butuh_pra")
                else "lihat citra pasca")
        baris.append(f"{i}. {f['label']} (kunci: {f['kunci']}; {cara})")
        baris.append(f"   Definisi : {f['definisi']}")
        baris.append(f"   Pilihan  : {pilihan}   ({ket})")
    baris.append(f'Untuk setiap fitur, jawab "{tak}" HANYA bila bangunan sasaran '
                 f"tidak terlihat sama sekali.")
    return "\n".join(baris)


ATURAN_FITUR = [
    "Nilailah HANYA bangunan yang ditunjuk bidik silang.",
    "Setiap fitur diisi TEPAT SATU pilihan. Jangan menyalin daftar pilihan.",
    "Pilih \"tidak_jelas\" HANYA bila bangunan sasaran benar-benar tertutup awan, "
    "bayangan pekat, atau tajuk pohon. Bila bangunannya terlihat, pilih salah satu "
    "nilai yang pasti, sekalipun keputusannya sulit.",
    "Nilai setiap fitur secara terpisah. Anda TIDAK diminta menetapkan kelas kerusakan.",
    "Field \"deskripsi\" berisi SATU kalimat bahasa Indonesia dengan kata-kata Anda "
    "sendiri tentang apa yang tampak pada bangunan sasaran. Jangan menyalin kalimat "
    "definisi di atas.",
    "Jawab HANYA dengan satu objek JSON yang sah. Tanpa kalimat pembuka, tanpa "
    "penjelasan, tanpa pagar kode.",
]


# Contoh format memakai field rekaan, bukan fitur atau kelas yang sebenarnya.
# Pada v2-v3 contoh BENAR memakai nilai sungguhan ("hilang"), yang berisiko
# menjadi jangkar jawaban bagi model kecil. Dengan field rekaan, model hanya
# belajar BENTUK pengisian, tidak mendapat petunjuk isi.
CONTOH_FORMAT = [
    "",
    "Bentuk pengisian (contoh rekaan, bukan jawaban):",
    '  BENAR : "contoh_field": "pilihan_b"',
    '  SALAH : "contoh_field": "pilihan_a | pilihan_b | pilihan_c"',
    '  SALAH : "contoh_field": "<pilih satu: pilihan_a, pilihan_b, pilihan_c>"',
]


def blok_format_fitur(fitur: list[dict]) -> str:
    """Nilai ditulis sebagai ruang isian < >, bukan daftar pilihan, karena pada
    prompt v1 model 2-3 miliar parameter menyalin daftar pilihan apa adanya.
    Contoh BENAR/SALAH berada pada tingkat format, bukan jawaban, sehingga
    prompt tetap zero-shot."""
    dalam = ",\n".join(
        f'    "{f["kunci"]}": "<pilih satu: {", ".join(f["enum"])}>"' for f in fitur)
    return "\n".join([
        "[FORMAT KELUARAN]",
        "Balas HANYA dengan satu objek JSON mengikuti kerangka di bawah. Setiap bagian "
        "di dalam tanda < > adalah ruang isian: GANTI seluruhnya, termasuk tanda < >, "
        "dengan satu jawaban Anda.",
        "",
        "{\n  \"fitur\": {\n" + dalam + "\n  },\n"
        "  \"deskripsi\": \"<satu kalimat bahasa Indonesia>\"\n}",
    ] + CONTOH_FORMAT)


def susun_prompt_fitur(k: dict, fitur: list[dict]) -> str:
    bagian = [BLOK_PERAN, "", "[INPUT]", INPUT_FITUR, BLOK_PENANDA, "",
              blok_definisi(fitur, k), "", "[ATURAN]"]
    bagian += [f"{i}. {a}" for i, a in enumerate(ATURAN_FITUR, 1)]
    bagian += ["", blok_format_fitur(fitur)]
    return "\n".join(bagian) + "\n"


# --------------------------------------------------------------------------- #
# prompt panggilan 2: kelas
# --------------------------------------------------------------------------- #

def blok_rubrik_pasca(k: dict) -> str:
    kl = k["kelas"]
    baris = ["[RUBRIK KELAS KERUSAKAN]",
             "Tetapkan satu kelas kerusakan untuk bangunan sasaran."]
    for kelas in kl["enum"]:
        baris.append(f'- "{kelas}": {kl["rubrik_pasca"][kelas]}')
    baris.append(f'- "{kl["kode_tak_teramati"]}": bangunan sasaran tertutup awan, bayangan '
                 f"pekat, atau tajuk pohon sehingga tidak dapat dilihat. Ini BUKAN tingkat "
                 f"kerusakan.")
    return "\n".join(baris)


ATURAN_KELAS = [
    "Nilailah HANYA bangunan yang ditunjuk bidik silang.",
    "Pilih TEPAT SATU kelas. Bila bangunan sasaran terlihat, Anda HARUS memilih salah "
    "satu dari tiga kelas kerusakan, sekalipun keputusannya sulit.",
    "Jawab HANYA dengan satu objek JSON yang sah. Tanpa kalimat pembuka, tanpa "
    "penjelasan, tanpa pagar kode.",
]


def blok_format_kelas(k: dict) -> str:
    kl = k["kelas"]
    pilihan = list(kl["enum"]) + [kl["kode_tak_teramati"]]
    return "\n".join([
        "[FORMAT KELUARAN]",
        "Balas HANYA dengan satu objek JSON berikut. GANTI setiap ruang isian < >, "
        "termasuk tanda < >, dengan jawaban Anda.",
        "",
        "{\n"
        f'  "kelas_kerusakan": "<pilih satu: {", ".join(pilihan)}>",\n'
        '  "keyakinan": <angka desimal antara 0.0 dan 1.0, tanpa tanda kutip>\n'
        "}",
    ] + CONTOH_FORMAT + [
        '  BENAR : "keyakinan": 0.7',
        '  SALAH : "keyakinan": "angka desimal antara 0.0 dan 1.0"',
    ])


def susun_prompt_kelas(k: dict) -> str:
    bagian = [BLOK_PERAN, "", "[INPUT]", INPUT_KELAS, BLOK_PENANDA, "",
              blok_rubrik_pasca(k), "", "[ATURAN]"]
    bagian += [f"{i}. {a}" for i, a in enumerate(ATURAN_KELAS, 1)]
    bagian += ["", blok_format_kelas(k)]
    return "\n".join(bagian) + "\n"


# --------------------------------------------------------------------------- #
# artefak turunan
# --------------------------------------------------------------------------- #

def skema_keluaran(k: dict, fitur: list[dict]) -> dict:
    kl = k["kelas"]
    return {
        "panggilan_fitur": {
            "fitur": {f["kunci"]: " | ".join(f["enum"]) for f in fitur},
            "deskripsi": "satu kalimat bahasa Indonesia",
        },
        "panggilan_kelas": {
            "kelas_kerusakan": " | ".join(list(kl["enum"]) + [kl["kode_tak_teramati"]]),
            "keyakinan": "bilangan desimal 0.0 sampai 1.0",
        },
    }


def butir_evaluator(fitur: list[dict], k: dict) -> list[dict]:
    kl = k["kelas"]
    butir = [{"no": i, "jenis": "pilihan", "kunci": f["kunci"],
              "skala_ukur": f.get("skala_ukur", ""),
              "pertanyaan": f["label"], "keterangan": f["definisi"],
              "pilihan": " / ".join(f["enum"])}
             for i, f in enumerate(fitur, 1)]
    n = len(fitur)
    butir.append({"no": n + 1, "jenis": "isian_bebas", "kunci": "deskripsi",
                  "skala_ukur": "-",
                  "pertanyaan": "Tuliskan satu kalimat yang menerangkan kondisi "
                                "bangunan yang ditunjuk bidik silang.",
                  "keterangan": "Rujukan bagi metrik teks (BLEU, ROUGE-L, METEOR).",
                  "pilihan": ""})
    butir.append({"no": n + 2, "jenis": "pilihan", "kunci": "kelas_kerusakan",
                  "skala_ukur": kl.get("skala_ukur", "ordinal"),
                  "pertanyaan": "Menurut Anda, bangunan tersebut termasuk kelas apa?",
                  "keterangan": " | ".join(f"{c}: {kl['rubrik'][c]}" for c in kl["enum"]),
                  "pilihan": " / ".join(list(kl["enum"]) + [kl["kode_tak_teramati"]])})
    return butir


def tulis_csv(path: Path, kolom: list[str], baris: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=kolom)
        w.writeheader()
        w.writerows(baris)


def main() -> None:
    p = argparse.ArgumentParser(description="Pembangkit prompt v4 dan artefak turunannya")
    p.add_argument("--konfig", type=Path, default=KONFIG_BAWAAN)
    p.add_argument("--out", type=Path, default=OUT_BAWAAN)
    a = p.parse_args()

    k = muat(a.konfig)
    fitur = fitur_terpilih(k)
    sid = sidik(k)
    a.out.mkdir(parents=True, exist_ok=True)

    teks_fitur = susun_prompt_fitur(k, fitur)
    teks_kelas = susun_prompt_kelas(k)
    f_fitur = a.out / f"prompt_fitur_v{VERSI_PROMPT}_{sid}.txt"
    f_kelas = a.out / f"prompt_kelas_v{VERSI_PROMPT}_{sid}.txt"
    f_fitur.write_text(teks_fitur, encoding="utf-8")
    f_kelas.write_text(teks_kelas, encoding="utf-8")

    (a.out / f"skema_keluaran_{sid}.json").write_text(
        json.dumps(skema_keluaran(k, fitur), ensure_ascii=False, indent=2), encoding="utf-8")

    tulis_csv(a.out / f"butir_formulir_evaluator_{sid}.csv",
              ["no", "jenis", "kunci", "skala_ukur", "pertanyaan", "keterangan", "pilihan"],
              butir_evaluator(fitur, k))

    terpilih = k["seleksi"]["terpilih"]
    tulis_csv(a.out / f"tabel_definisi_operasional_{sid}.csv",
              ["no", "kandidat", "kelompok", "golongan", "butuh_citra_pra", "skala_ukur",
               "level", "kode_tak_teramati", "definisi_operasional", "rujukan_level",
               "keteramatan", "status"],
              [{"no": c["no"], "kandidat": c["label"], "kelompok": c["kelompok"],
                "golongan": c.get("golongan", ""),
                "butuh_citra_pra": "ya" if c.get("butuh_pra") else "tidak",
                "skala_ukur": c.get("skala_ukur", ""),
                "level": " > ".join(c.get("level", [])),
                "kode_tak_teramati": c.get("kode_tak_teramati", ""),
                "definisi_operasional": c["definisi"],
                "rujukan_level": c.get("rujukan_level", ""),
                "keteramatan": c.get("keteramatan", ""),
                "status": "TERPILIH" if c["kunci"] in terpilih else "tidak dipakai"}
               for c in k["kandidat"]])

    manifes = {
        "sidik_fitur": sid,
        "versi_prompt": VERSI_PROMPT,
        "versi_konfigurasi": k.get("_versi_konfigurasi"),
        "status_seleksi": k["seleksi"]["status"],
        "fitur_terpilih": terpilih,
        "golongan_fitur_terpilih": {f["kunci"]: f.get("golongan") for f in fitur},
        "kelas_enum": k["kelas"]["enum"],
        "kode_tak_teramati": k["kelas"]["kode_tak_teramati"],
        "pemetaan_biner": k["kelas"]["pemetaan_biner"],
        "prompt": {
            "fitur": {"berkas": f_fitur.name, "sha256_12": hash_teks(teks_fitur),
                      "citra": ["pra", "pasca"], "kata": len(teks_fitur.split())},
            "kelas": {"berkas": f_kelas.name, "sha256_12": hash_teks(teks_kelas),
                      "citra": ["pasca"], "kata": len(teks_kelas.split())},
        },
    }
    (a.out / f"manifes_v{VERSI_PROMPT}_{sid}.json").write_text(
        json.dumps(manifes, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 78)
    print(" PEMBANGKITAN PROMPT v%d DAN ARTEFAK TURUNAN" % VERSI_PROMPT)
    print("=" * 78)
    print(f" Status seleksi fitur : {k['seleksi']['status']}")
    print(f" Sidik fitur          : {sid}")
    for i, f in enumerate(fitur, 1):
        print(f"   {i}. {f['label']:<44}{f.get('golongan',''):<11}"
              f"{'/'.join(f.get('level', []))}")
    print("\n Prompt:")
    for nama, m in manifes["prompt"].items():
        print(f"   {m['berkas']:<34} {m['kata']:>4} kata  sha={m['sha256_12']}  "
              f"citra={'+'.join(m['citra'])}")
    print(f"\n Folder keluaran      : {a.out}")
    print("=" * 78)


if __name__ == "__main__":
    main()
