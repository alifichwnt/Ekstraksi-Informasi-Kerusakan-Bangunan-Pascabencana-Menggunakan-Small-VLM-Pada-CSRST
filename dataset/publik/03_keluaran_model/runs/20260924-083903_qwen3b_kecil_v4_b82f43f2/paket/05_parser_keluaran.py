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
    hasil_fitur = P.urai_fitur(teks_mentah_fitur, konfig)   # prompt v4, panggilan 1
    hasil_kelas = P.urai_kelas(teks_mentah_kelas, konfig)   # prompt v4, panggilan 2
    hasil_lama  = P.urai(teks_mentah, konfig)               # prompt v1-v3 (satu panggilan)
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
# pengurai desain dua panggilan (prompt v4)
# --------------------------------------------------------------------------- #

def _selaras_keyakinan(obj: dict, hasil: dict, catatan: list) -> None:
    try:
        y = float(obj.get("keyakinan"))
        hasil["keyakinan"] = min(max(y, 0.0), 1.0)
        if not 0.0 <= y <= 1.0:
            catatan.append("keyakinan di luar rentang, dipotong")
    except (TypeError, ValueError):
        hasil["keyakinan"] = None
        catatan.append("keyakinan tidak berupa bilangan")


def urai_fitur(mentah: str, konfig: dict) -> dict:
    """Panggilan 1 (citra pra + pasca): blok 'fitur' dan 'deskripsi'."""
    peta = {c["kunci"]: c for c in konfig["kandidat"]}
    terpilih = konfig["seleksi"]["terpilih"]
    tak = konfig["skala_pengukuran"]["kode_tak_teramati"]
    catatan: list[str] = []
    obj, tingkat = ambil_json(mentah or "")
    hasil: dict = {"f_terurai": obj is not None and isinstance(obj, dict),
                   "f_tingkat_perbaikan": NAMA_TINGKAT[tingkat],
                   "f_panjang_mentah": len(mentah or "")}
    if not hasil["f_terurai"]:
        hasil.update({f"fitur_{kk}": None for kk in terpilih})
        hasil.update({"fitur_lengkap": False, "jumlah_tidak_jelas": None,
                      "deskripsi": None, "f_sah": False,
                      "f_catatan": "tidak ditemukan objek JSON yang dapat diurai"})
        return hasil
    blok = obj.get("fitur")
    if not isinstance(blok, dict):
        # model kadang menaruh fitur langsung di tingkat atas
        blok = {kk: obj[kk] for kk in terpilih if kk in obj}
        if blok:
            catatan.append("fitur berada di tingkat atas, bukan di dalam 'fitur'")
        else:
            catatan.append("blok 'fitur' tidak ada")
    if "deskripsi" not in obj and isinstance(obj.get("fitur"), dict) and "deskripsi" in obj["fitur"]:
        obj["deskripsi"] = obj["fitur"].pop("deskripsi")
        catatan.append("deskripsi dinaikkan dari dalam blok 'fitur'")
    n_tj = 0
    for kk in terpilih:
        nilai, disel = selaraskan(blok.get(kk), peta[kk]["enum"])
        hasil[f"fitur_{kk}"] = nilai
        if nilai is None:
            catatan.append(f"fitur {kk} tidak dikenali")
        elif disel:
            catatan.append(f"fitur {kk} diselaraskan")
        n_tj += int(nilai == tak)
    hasil["jumlah_tidak_jelas"] = n_tj
    hasil["fitur_lengkap"] = all(hasil[f"fitur_{kk}"] is not None for kk in terpilih)
    d = obj.get("deskripsi")
    hasil["deskripsi"] = d.strip() if isinstance(d, str) and d.strip() else None
    if hasil["deskripsi"] is None:
        catatan.append("deskripsi kosong")
    hasil["f_sah"] = hasil["fitur_lengkap"] and hasil["deskripsi"] is not None
    hasil["f_catatan"] = "; ".join(catatan)
    return hasil


def urai_kelas(mentah: str, konfig: dict) -> dict:
    """Panggilan 2 (citra pasca saja): 'kelas_kerusakan' dan 'keyakinan'.
    Kode tak teramati diterima sebagai jawaban sah tetapi TIDAK dipetakan ke
    kelas biner: penghindaran dicatat sebagai penghindaran."""
    kl = konfig["kelas"]
    tak = kl.get("kode_tak_teramati")
    catatan: list[str] = []
    obj, tingkat = ambil_json(mentah or "")
    hasil: dict = {"k_terurai": obj is not None and isinstance(obj, dict),
                   "k_tingkat_perbaikan": NAMA_TINGKAT[tingkat],
                   "k_panjang_mentah": len(mentah or "")}
    if not hasil["k_terurai"]:
        # upaya terakhir: satu-satunya kata kelas yang muncul di teks bebas
        t = re.sub(r"[^a-z_ ]", " ", (mentah or "").lower())
        t = re.sub(r"\btidak\s+rusak\b", "tidak_rusak", t)
        token = set(t.split())
        muncul = [c for c in kl["enum"] if c in token]
        if len(muncul) == 1:
            hasil.update({"kelas_kerusakan": muncul[0], "kelas_tak_teramati": False,
                          "kelas_biner": kl["pemetaan_biner"][muncul[0]], "keyakinan": None,
                          "k_tingkat_perbaikan": "kata_kelas_di_teks_bebas", "k_sah": True,
                          "k_catatan": "bukan JSON; satu kata kelas ditemukan di teks bebas"})
            return hasil
        hasil.update({"kelas_kerusakan": None, "kelas_tak_teramati": False,
                      "kelas_biner": None, "keyakinan": None, "k_sah": False,
                      "k_catatan": "tidak ditemukan objek JSON yang dapat diurai"})
        return hasil
    pilihan = list(kl["enum"]) + ([tak] if tak else [])
    kelas, disel = selaraskan(obj.get("kelas_kerusakan"), pilihan)
    hasil["kelas_kerusakan"] = kelas
    hasil["kelas_tak_teramati"] = (kelas == tak)
    hasil["kelas_biner"] = kl["pemetaan_biner"].get(kelas) if kelas else None
    if kelas is None:
        catatan.append("kelas_kerusakan tidak dikenali")
    elif disel:
        catatan.append("kelas_kerusakan diselaraskan")
    _selaras_keyakinan(obj, hasil, catatan)
    hasil["k_sah"] = kelas is not None
    hasil["k_catatan"] = "; ".join(catatan)
    return hasil


# --------------------------------------------------------------------------- #
# uji bawaan (desain dua panggilan)
# --------------------------------------------------------------------------- #

UJI_FITUR = [
    ("JSON bersih", """{"fitur":{"keutuhan_atap":"utuh","puing_sekitar":"tidak_ada",
      "wujud_bangunan":"tidak_berubah","sedimen_lumpur":"tidak_ada"},
      "deskripsi":"Rumah beratap seng masih berdiri utuh."}""", True, True),
    ("pagar kode + kalimat pembuka", """Berikut jawabannya:
```json
{"fitur":{"keutuhan_atap":"hilang","puing_sekitar":"meluas_menutupi_petak",
"wujud_bangunan":"tidak_lagi_berupa_bangunan","sedimen_lumpur":"menutupi_seluruhnya"},
"deskripsi":"Tapak bangunan tertimbun lumpur."}
```""", True, True),
    ("gaya tulis enum berbeda + kutip tunggal", """{'fitur': {'keutuhan_atap': 'Rusak Sebagian',
      'puing_sekitar': 'terbatas di sekitar bangunan', 'wujud_bangunan': 'berubah sebagian',
      'sedimen_lumpur': 'Tidak Ada',}, 'deskripsi': 'Sebagian atap runtuh.',}""", True, True),
    ("kurung 'fitur' tidak ditutup (pola InternVL3)", """{
  "fitur": {
    "keutuhan_atap": "utuh",
    "puing_sekitar": "tidak_ada",
    "wujud_bangunan": "tidak_berubah",
    "sedimen_lumpur": "tidak_jelas"
 ,
 "deskripsi": "Bangunan tampak utuh."
}""", True, True),
    ("fitur di tingkat atas", """{"keutuhan_atap":"utuh","puing_sekitar":"tidak_ada",
      "wujud_bangunan":"tidak_berubah","sedimen_lumpur":"tidak_ada",
      "deskripsi":"Bangunan utuh."}""", True, True),
    ("satu fitur hilang", """{"fitur":{"keutuhan_atap":"utuh","puing_sekitar":"tidak_ada",
      "wujud_bangunan":"tidak_berubah"},"deskripsi":"Bangunan utuh."}""", True, False),
    ("menyalin daftar pilihan", """{"fitur":{"keutuhan_atap":"utuh | rusak_sebagian | hilang",
      "puing_sekitar":"tidak_ada","wujud_bangunan":"tidak_berubah","sedimen_lumpur":"tidak_ada"},
      "deskripsi":"x"}""", True, False),
    ("model menolak", "Maaf, saya tidak dapat menilai citra ini.", False, False),
]

UJI_KELAS = [
    ("JSON bersih", '{"kelas_kerusakan":"hancur","keyakinan":0.8}', True, "hancur"),
    ("keyakinan string + pagar", '```json\n{"kelas_kerusakan":"rusak","keyakinan":"0.6"}\n```',
     True, "rusak"),
    ("tidak_rusak jangan terbaca rusak", '{"kelas_kerusakan":"Tidak Rusak","keyakinan":0.9}',
     True, "tidak_rusak"),
    ("kode tak teramati", '{"kelas_kerusakan":"tidak_jelas","keyakinan":0.2}', True, "tidak_jelas"),
    ("teks bebas satu kelas", "Bangunan ini hancur total.", True, "hancur"),
    ("teks bebas ambigu", "Bisa rusak, bisa juga hancur.", False, None),
    ("teks bebas 'tidak rusak'", "Menurut saya bangunan ini tidak rusak.", True, "tidak_rusak"),
    ("menyalin daftar pilihan", '{"kelas_kerusakan":"tidak_rusak | rusak | hancur","keyakinan":0.5}',
     False, None),
]


def _uji() -> int:
    konfig = json.loads(KONFIG_BAWAAN.read_text(encoding="utf-8"))
    print("=" * 78)
    print(" UJI PENGURAI KELUARAN (desain dua panggilan)")
    print("=" * 78)
    gagal = 0
    print(" Panggilan FITUR")
    for nama, mentah, hrp_urai, hrp_sah in UJI_FITUR:
        h = urai_fitur(mentah, konfig)
        ok = h["f_terurai"] == hrp_urai and h["f_sah"] == hrp_sah
        gagal += not ok
        print(f"  {'OK ' if ok else '!! '} {nama:<44} tingkat={h['f_tingkat_perbaikan']:<22} "
              f"sah={h['f_sah']}")
        if h.get("f_catatan"):
            print(f"       catatan: {h['f_catatan']}")
    print(" Panggilan KELAS")
    for nama, mentah, hrp_sah, hrp_kelas in UJI_KELAS:
        h = urai_kelas(mentah, konfig)
        ok = h["k_sah"] == hrp_sah and h["kelas_kerusakan"] == hrp_kelas
        gagal += not ok
        print(f"  {'OK ' if ok else '!! '} {nama:<44} kelas={str(h['kelas_kerusakan']):<12} "
              f"tingkat={h['k_tingkat_perbaikan']}")
    n = len(UJI_FITUR) + len(UJI_KELAS)
    print("-" * 78)
    print(f" {n - gagal}/{n} kasus sesuai harapan")
    print("=" * 78)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(_uji())
