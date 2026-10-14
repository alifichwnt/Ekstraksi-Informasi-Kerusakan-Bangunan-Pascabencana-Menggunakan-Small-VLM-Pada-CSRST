#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05_parser_keluaran.py
=====================
Pengurai keluaran SVLM yang toleran, beserta pemetaan kelas ke biner.

Model berukuran 2-3 miliar parameter sering tidak patuh pada perintah "jawab
hanya JSON": keluarannya dibungkus pagar kode, didahului kalimat pembuka,
memakai kutip tunggal, menyisipkan koma berlebih, atau memakai nilai enum yang
mirip tetapi tidak persis. Modul ini menangani semuanya secara berjenjang dan
MENCATAT pada tingkat mana perbaikan diperlukan.

Tingkat kegagalan penguraian (parsing failure rate) dan sebaran tingkat
perbaikan adalah temuan yang dilaporkan di Bab 4, bukan sesuatu yang disembunyikan.
Karena itu tidak ada keluaran yang dibuang diam-diam.

Modul ini tidak butuh GPU dan tidak bergantung pada model apa pun, sehingga
dapat diuji lebih dulu. Jalankan tanpa argumen untuk menjalankan uji bawaan:

    python 05_parser_keluaran.py

Penggunaan sebagai modul:

    from importlib import import_module
    P = import_module("05_parser_keluaran")
    hasil = P.urai(teks_mentah, konfig)
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

KONFIG_BAWAAN = Path(__file__).resolve().parent / "konfigurasi_fitur.json"

# tingkat perbaikan, makin besar makin jauh dari keluaran ideal
T_LANGSUNG = 0     # seluruh respons adalah JSON sah
T_PAGAR = 1        # JSON berada di dalam pagar kode
T_KURUNG = 2       # JSON diambil dari kurung kurawal seimbang pertama
T_BERSIH = 3       # perlu pembersihan sintaksis (kutip tunggal, koma berlebih)
T_TAMBAL = 4       # kurung kurawal tidak seimbang, ditutup paksa
T_GAGAL = 9        # tidak dapat diurai

NAMA_TINGKAT = {
    T_LANGSUNG: "langsung",
    T_PAGAR: "pagar_kode",
    T_KURUNG: "kurung_seimbang",
    T_BERSIH: "pembersihan_sintaksis",
    T_TAMBAL: "kurung_ditambal",
    T_GAGAL: "gagal",
}


# --------------------------------------------------------------------------- #
# pengambilan blok JSON
# --------------------------------------------------------------------------- #

def _kurung_seimbang(teks: str) -> str | None:
    """Ambil objek JSON pertama dengan menghitung kurung kurawal, sambil
    mengabaikan kurung yang berada di dalam string. Regex tidak dipakai di sini
    karena tidak dapat menangani objek bersarang seperti field 'fitur'."""
    mulai = teks.find("{")
    if mulai == -1:
        return None
    dalam_string = False
    lolos = False
    dalam = 0
    for i in range(mulai, len(teks)):
        c = teks[i]
        if lolos:
            lolos = False
            continue
        if c == "\\":
            lolos = True
            continue
        if c == '"':
            dalam_string = not dalam_string
            continue
        if dalam_string:
            continue
        if c == "{":
            dalam += 1
        elif c == "}":
            dalam -= 1
            if dalam == 0:
                return teks[mulai:i + 1]
    return None


def _bersihkan(blok: str) -> str:
    b = blok
    b = re.sub(r",\s*([}\]])", r"\1", b)                 # koma berlebih
    b = re.sub(r"(?<![\\\w])'([^'\n]*)'(?=\s*[:,}\]])", r'"\1"', b)  # kutip tunggal
    b = b.replace("“", '"').replace("”", '"')  # kutip melengkung
    b = re.sub(r"\bNone\b", "null", b)
    b = re.sub(r"\bTrue\b", "true", b)
    b = re.sub(r"\bFalse\b", "false", b)
    return b


def _tambal_kurung(teks: str) -> str | None:
    """Tutup paksa objek JSON yang kurung kurawalnya kurang.

    InternVL3-2B kerap lupa menutup objek "fitur", sehingga seluruh keluaran
    menjadi JSON tak sah. Isinya sebenarnya utuh, hanya kurungnya kurang.
    Penambalan dicatat sebagai tingkat perbaikan tersendiri agar kejadiannya
    tetap terlihat pada laporan Bab 4, bukan disembunyikan.
    """
    mulai = teks.find("{")
    if mulai == -1:
        return None
    dalam_string = lolos = False
    dalam = 0
    for c in teks[mulai:]:
        if lolos:
            lolos = False
            continue
        if c == "\\":
            lolos = True
            continue
        if c == '"':
            dalam_string = not dalam_string
            continue
        if dalam_string:
            continue
        if c == "{":
            dalam += 1
        elif c == "}":
            dalam -= 1
    return teks[mulai:].rstrip() + "}" * dalam if dalam > 0 else None


def _bongkar_sarang(obj: dict) -> tuple[dict, bool]:
    """Naikkan field yang salah tersarang di dalam "fitur" ke tingkat atas.

    Akibat kurung yang kurang, "kelas_kerusakan", "keyakinan" dan "deskripsi"
    dapat ikut masuk ke dalam objek "fitur". Posisinya dikembalikan agar
    penilaian isi tidak terpengaruh kesalahan tanda baca.
    """
    fitur = obj.get("fitur")
    if not isinstance(fitur, dict):
        return obj, False
    pindah = [k for k in ("kelas_kerusakan", "keyakinan", "deskripsi")
              if k not in obj and k in fitur]
    for k in pindah:
        obj[k] = fitur.pop(k)
    return obj, bool(pindah)


def ambil_json(mentah: str) -> tuple[dict | None, int]:
    """Kembalikan (objek, tingkat_perbaikan)."""
    teks = mentah.strip()
    try:
        return json.loads(teks), T_LANGSUNG
    except json.JSONDecodeError:
        pass

    pagar = re.search(r"```(?:json)?\s*(.+?)```", teks, re.DOTALL | re.IGNORECASE)
    if pagar:
        try:
            return json.loads(pagar.group(1).strip()), T_PAGAR
        except json.JSONDecodeError:
            teks = pagar.group(1)

    blok = _kurung_seimbang(teks)
    if blok is not None:
        try:
            return json.loads(blok), T_KURUNG
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(_bersihkan(blok)), T_BERSIH
        except json.JSONDecodeError:
            pass
    # kurung tidak seimbang atau isinya tetap tak terurai: coba tutup paksa
    tambal = _tambal_kurung(teks)
    if tambal:
        for calon in (tambal, _bersihkan(tambal)):
            try:
                return json.loads(calon), T_TAMBAL
            except json.JSONDecodeError:
                continue
    return None, T_GAGAL


# --------------------------------------------------------------------------- #
# penyelarasan nilai enum
# --------------------------------------------------------------------------- #

def _baku(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)
    return re.sub(r"[^a-z0-9_]", "", s)


def selaraskan(nilai, enum: list[str]) -> tuple[str | None, bool]:
    """Cocokkan nilai ke salah satu anggota enum.
    Kembalikan (nilai_terselaraskan, perlu_penyelarasan)."""
    if nilai is None:
        return None, True
    if isinstance(nilai, str) and nilai in enum:
        return nilai, False
    b = _baku(nilai)
    peta = {_baku(e): e for e in enum}
    if b in peta:
        return peta[b], True
    # kecocokan sebagian: "atap rusak sebagian" -> "rusak_sebagian"
    kandidat = [e for e in enum if _baku(e) in b or b in _baku(e)]
    if len(kandidat) == 1:
        return kandidat[0], True
    return None, True


# --------------------------------------------------------------------------- #
# pengurai utama
# --------------------------------------------------------------------------- #

def urai(mentah: str, konfig: dict) -> dict:
    """Ubah satu keluaran mentah model menjadi satu baris hasil yang siap dianalisis."""
    peta_kandidat = {c["kunci"]: c for c in konfig["kandidat"]}
    terpilih = konfig["seleksi"]["terpilih"]
    kelas_enum = konfig["kelas"]["enum"]
    ke_biner = konfig["kelas"]["pemetaan_biner"]

    hasil: dict = {
        "terurai": False,
        "tingkat_perbaikan": NAMA_TINGKAT[T_GAGAL],
        "catatan": [],
        "panjang_mentah": len(mentah or ""),
    }

    obj, tingkat = ambil_json(mentah or "")
    hasil["tingkat_perbaikan"] = NAMA_TINGKAT[tingkat]
    if obj is None or not isinstance(obj, dict):
        hasil["catatan"] = "tidak ditemukan objek JSON yang dapat diurai"
        hasil["sah_penuh"] = False
        return hasil
    hasil["terurai"] = True
    obj, dibongkar = _bongkar_sarang(obj)
    if dibongkar:
        hasil["catatan"].append("field dinaikkan dari dalam blok 'fitur'")

    # kelas kerusakan. Kode tak teramati diterima sebagai jawaban sah, tetapi TIDAK
    # dipetakan ke kelas biner: penghindaran dicatat sebagai penghindaran, bukan
    # disamarkan menjadi "tidak_rusak".
    tak_kelas = konfig["kelas"].get("kode_tak_teramati")
    pilihan_kelas = list(kelas_enum) + ([tak_kelas] if tak_kelas else [])
    kelas, diselaraskan = selaraskan(obj.get("kelas_kerusakan"), pilihan_kelas)
    hasil["kelas_kerusakan"] = kelas
    hasil["kelas_tak_teramati"] = (kelas == tak_kelas)
    if kelas is None:
        hasil["catatan"].append("kelas_kerusakan tidak dikenali")
    elif diselaraskan:
        hasil["catatan"].append("kelas_kerusakan diselaraskan")
    hasil["kelas_biner"] = ke_biner.get(kelas) if kelas else None

    # fitur
    blok_fitur = obj.get("fitur")
    if not isinstance(blok_fitur, dict):
        blok_fitur = {}
        if terpilih:
            hasil["catatan"].append("blok 'fitur' tidak ada")
    n_tidak_jelas = 0
    for kunci in terpilih:
        enum = peta_kandidat[kunci]["enum"]
        nilai, diselaraskan = selaraskan(blok_fitur.get(kunci), enum)
        hasil[f"fitur_{kunci}"] = nilai
        if nilai is None:
            hasil["catatan"].append(f"fitur {kunci} tidak dikenali")
        elif diselaraskan:
            hasil["catatan"].append(f"fitur {kunci} diselaraskan")
        if nilai == "tidak_jelas":
            n_tidak_jelas += 1
    hasil["jumlah_tidak_jelas"] = n_tidak_jelas
    hasil["fitur_lengkap"] = all(hasil.get(f"fitur_{k}") is not None for k in terpilih)

    # keyakinan
    try:
        y = float(obj.get("keyakinan"))
        hasil["keyakinan"] = min(max(y, 0.0), 1.0)
        if not 0.0 <= y <= 1.0:
            hasil["catatan"].append("keyakinan di luar rentang, dipotong")
    except (TypeError, ValueError):
        hasil["keyakinan"] = None
        hasil["catatan"].append("keyakinan tidak berupa bilangan")

    # deskripsi
    d = obj.get("deskripsi")
    hasil["deskripsi"] = d.strip() if isinstance(d, str) else None
    if not hasil["deskripsi"]:
        hasil["catatan"].append("deskripsi kosong")
    else:
        hasil["jumlah_kata_deskripsi"] = len(hasil["deskripsi"].split())

    hasil["sah_penuh"] = (
        hasil["terurai"] and hasil["kelas_biner"] is not None
        and hasil["fitur_lengkap"] and bool(hasil["deskripsi"])
    )
    hasil["catatan"] = "; ".join(hasil["catatan"])
    return hasil


# --------------------------------------------------------------------------- #
# uji bawaan
# --------------------------------------------------------------------------- #

CONTOH = [
    # (nama kasus, teks mentah, harapan terurai, harapan sah_penuh)
    ("JSON bersih", """{"fitur":{"keutuhan_atap":"utuh","perubahan_radiometri":"tidak_ada",
      "perubahan_wujud":"tidak_ada","sedimen_lumpur":"tidak_ada","bangunan_hilang":"tidak_ada",
      "puing_sekitar":"tidak_ada"},"kelas_kerusakan":"tidak_rusak","keyakinan":0.9,
      "deskripsi":"Bangunan tampak utuh dan tidak berubah."}""", True, True),

    ("dibungkus pagar kode + kalimat pembuka", """Berikut hasil analisis saya:
```json
{"fitur":{"keutuhan_atap":"hilang","perubahan_radiometri":"ada","perubahan_wujud":"ada",
"sedimen_lumpur":"ada","bangunan_hilang":"ada","puing_sekitar":"ada"},
"kelas_kerusakan":"rusak_total","keyakinan":0.85,"deskripsi":"Bangunan hancur total."}
```
Semoga membantu.""", True, True),

    ("kutip tunggal dan koma berlebih", """{'fitur': {'keutuhan_atap': 'rusak_sebagian',
      'perubahan_radiometri': 'ada', 'perubahan_wujud': 'ada', 'sedimen_lumpur': 'tidak_ada',
      'bangunan_hilang': 'tidak_ada', 'puing_sekitar': 'ada',},
      'kelas_kerusakan': 'rusak_sedang', 'keyakinan': 0.7,
      'deskripsi': 'Sebagian atap runtuh.',}""", True, True),

    ("enum berbeda gaya penulisan", """{"fitur":{"keutuhan_atap":"Rusak Sebagian",
      "perubahan_radiometri":"ADA","perubahan_wujud":"ada","sedimen_lumpur":"Tidak Ada",
      "bangunan_hilang":"tidak ada","puing_sekitar":"ada"},
      "kelas_kerusakan":"Rusak Sedang","keyakinan":"0.6",
      "deskripsi":"Atap rusak sebagian dan ada puing."}""", True, True),

    ("keyakinan di luar rentang", """{"fitur":{"keutuhan_atap":"utuh","perubahan_radiometri":"tidak_ada",
      "perubahan_wujud":"tidak_ada","sedimen_lumpur":"tidak_ada","bangunan_hilang":"tidak_ada",
      "puing_sekitar":"tidak_ada"},"kelas_kerusakan":"tidak_rusak","keyakinan":95,
      "deskripsi":"Bangunan utuh."}""", True, True),

    ("satu fitur hilang", """{"fitur":{"keutuhan_atap":"utuh","perubahan_radiometri":"tidak_ada",
      "perubahan_wujud":"tidak_ada","sedimen_lumpur":"tidak_ada","bangunan_hilang":"tidak_ada"},
      "kelas_kerusakan":"tidak_rusak","keyakinan":0.8,"deskripsi":"Bangunan utuh."}""", True, False),

    ("objek bersarang, ada kurawal di dalam string", """{"fitur":{"keutuhan_atap":"utuh",
      "perubahan_radiometri":"tidak_ada","perubahan_wujud":"tidak_ada","sedimen_lumpur":"tidak_ada",
      "bangunan_hilang":"tidak_ada","puing_sekitar":"tidak_ada"},"kelas_kerusakan":"tidak_rusak",
      "keyakinan":0.9,"deskripsi":"Format keluaran memakai tanda { dan } di dalam kalimat."}""",
     True, True),

    ("model menolak menjawab", "Maaf, saya tidak dapat menganalisis citra satelit.", False, False),

    ("JSON terpotong", """{"fitur":{"keutuhan_atap":"utuh","perubahan_radiometri":"tidak""",
     False, False),

    ("kurung 'fitur' tidak ditutup (pola InternVL3)", """```json
{
  "fitur": {
    "keutuhan_atap": "utuh",
    "perubahan_radiometri": "tidak_ada",
    "perubahan_wujud": "tidak_ada",
    "sedimen_lumpur": "tidak_jelas",
    "bangunan_hilang": "tidak_jelas",
    "puing_sekitar": "tidak_jelas"
 ,
 "kelas_kerusakan": "tidak_rusak",
 "keyakinan": "1.0",
 "deskripsi": "Bangunan masih dikenali sebagai bangunan, atap utuh."
}
```""", True, True),
]


def _uji() -> int:
    konfig = json.loads(KONFIG_BAWAAN.read_text(encoding="utf-8"))
    lebar = 44
    print("=" * 78)
    print(" UJI PENGURAI KELUARAN")
    print("=" * 78)
    gagal = 0
    for nama, mentah, hrp_urai, hrp_sah in CONTOH:
        h = urai(mentah, konfig)
        ok = (h["terurai"] == hrp_urai) and (h.get("sah_penuh", False) == hrp_sah)
        gagal += 0 if ok else 1
        tanda = "OK  " if ok else "!!  "
        print(f" {tanda}{nama:<{lebar}} tingkat={h['tingkat_perbaikan']:<22}"
              f"biner={str(h.get('kelas_biner')):<12}")
        if h["catatan"]:
            print(f"      catatan: {h['catatan']}")
    print("-" * 78)
    print(f" {len(CONTOH) - gagal}/{len(CONTOH)} kasus sesuai harapan")
    print("=" * 78)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(_uji())
