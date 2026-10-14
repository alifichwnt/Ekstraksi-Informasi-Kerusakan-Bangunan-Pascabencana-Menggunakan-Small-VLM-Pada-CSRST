#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
09o_pembanding_openai.py
========================
Menjalankan model komersial OpenAI (ChatGPT, lewat OpenAI API) sebagai PEMBANDING,
dengan desain yang identik dengan SVLM dan dengan skrip 09g:

  * prompt yang SAMA persis (prompt_fitur_v4 dan prompt_kelas_v4),
  * chip yang SAMA (448 x 448, pra dan pasca, dikirim sebagai PNG base64),
  * dua panggilan per bangunan: fitur (pra+pasca) dan kelas (pasca saja),
  * format run yang SAMA (runs/<RUN_ID>/manifest.json, mentah.jsonl, paket/,
    log_berjalan.txt, waktu_komputasi.json).

Latar penggantian dari Gemini: kuota tingkat gratis gemini-3.6-flash hanya sekitar
20 permintaan per hari (80 dibutuhkan), sedangkan tingkat berbayar Gemini pada akun
peneliti mensyaratkan prabayar minimum IDR 500.000. Run Gemini yang terhenti (2 dari 40
bangunan) dipertahankan sebagai jejak, tidak dianalisis.

Persiapan satu kali (laptop, tanpa GPU):
    pip install openai pandas pillow
    1. platform.openai.com > Billing > tambah kredit (minimum USD 5)
    2. platform.openai.com > API keys > Create new secret key
    3. PowerShell:  $env:OPENAI_API_KEY="isi_kunci_anda"
       (atau simpan kunci di berkas teks di luar folder skripsi, pakai --kunci)

Penggunaan (dari folder KOMPONEN_4):
    python 09o_pembanding_openai.py --daftar-model
    python 09o_pembanding_openai.py --model <nama> --batas 3   # uji cepat 3 bangunan
    python 09o_pembanding_openai.py --model <nama>             # 40 bangunan sampel kecil
    python 09o_pembanding_openai.py --lanjutkan "..\\KOMPONEN_5\\runs\\<RUN_ID>"

Catatan metodologis (Bab 3 dan keterbatasan Bab 5):
  * Suhu 0 bila model menerimanya; beberapa model penalaran menolak parameter suhu,
    dan dalam hal itu panggilan diulang tanpa suhu dan hal tersebut DICATAT.
  * Nama model yang benar-benar melayani (response.model) dan system_fingerprint
    dicatat per panggilan, karena model API dapat diperbarui penyedia.
  * Token penalaran (reasoning tokens) dicatat bila model mengembalikannya.
  * Kemungkinan kontaminasi data (model pernah melihat xBD) tidak dapat diperiksa.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import sys
import time
from pathlib import Path

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("Butuh pandas. Jalankan:  pip install pandas")

AKAR = Path(os.environ.get("SKRIPSI_AKAR",
             r"F:\KULIAH STIS\TINGKAT IV - SD\SKRIPSWEET\MANUVER SKRIPSI AFTER SENSUS"))
K3, K4 = AKAR / "KOMPONEN_3", AKAR / "KOMPONEN_4"
RUNS = AKAR / "KOMPONEN_5" / "runs"
CHIP = K3 / "Output Chip"
KONFIG = K4 / "konfigurasi_fitur.json"
PARSER = K4 / "05_parser_keluaran.py"
PROMPT_DIR = K4 / "Output Prompt"


def sha(x, n: int = 12) -> str:
    b = x.read_bytes() if isinstance(x, Path) else str(x).encode("utf-8")
    return hashlib.sha256(b).hexdigest()[:n]


def klien(arg):
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("Butuh pustaka openai. Jalankan:  pip install openai")
    kunci = (Path(arg.kunci).read_text().strip() if arg.kunci
             else os.environ.get("OPENAI_API_KEY"))
    if not kunci:
        sys.exit("Kunci API tidak ditemukan. Set OPENAI_API_KEY atau pakai --kunci berkas.txt")
    # coba ulang SDK dimatikan: coba ulang ditangani panggil() agar tercatat
    return OpenAI(api_key=kunci, max_retries=0, timeout=300)


def daftar_model(c) -> None:
    print("Model pada kunci ini (pilih model GPT yang menerima masukan citra):")
    for m in sorted(c.models.list(), key=lambda m: m.id):
        if m.id.startswith(("gpt", "o", "chat")):
            print("  ", m.id)
    print("\nCek dukungan citra dan harga di https://developers.openai.com/api/docs/pricing")


SUHU_DITOLAK: set[str] = set()


def panggil(c, model: str, gambar: list[Path], teks: str, maks_ulang: int = 6):
    import base64
    isi = [{"type": "image_url",
            "image_url": {"url": "data:image/png;base64," + base64.b64encode(g.read_bytes()).decode()}}
           for g in gambar]
    isi.append({"type": "text", "text": teks})
    tunggu = 20
    for coba in range(1, maks_ulang + 1):
        kw = {} if model in SUHU_DITOLAK else {"temperature": 0}
        try:
            t_api = time.time()
            r = c.chat.completions.create(model=model, messages=[{"role": "user", "content": isi}], **kw)
            u = getattr(r, "usage", None)
            det = getattr(u, "completion_tokens_details", None)
            return {"teks": r.choices[0].message.content,
                    "model_version": getattr(r, "model", None),
                    "system_fingerprint": getattr(r, "system_fingerprint", None),
                    "suhu": kw.get("temperature", "bawaan model"),
                    "token_masuk": getattr(u, "prompt_tokens", None),
                    "token_keluar": getattr(u, "completion_tokens", None),
                    "token_berpikir": getattr(det, "reasoning_tokens", None) if det else None,
                    # waktu panggilan yang BERHASIL saja (latensi API), tanpa waktu tunggu ulang
                    "detik_api": round(time.time() - t_api, 2),
                    "galat": None, "percobaan": coba}
        except Exception as e:  # kuota, jaringan, server sibuk, parameter ditolak
            pesan_penuh = str(e)
            pesan = f"{type(e).__name__}: {pesan_penuh[:300]}"
            if "temperature" in pesan_penuh and model not in SUHU_DITOLAK and \
                    ("unsupported" in pesan_penuh.lower() or "not support" in pesan_penuh.lower()):
                SUHU_DITOLAK.add(model)
                print("     ! model menolak parameter suhu; dilanjutkan dengan suhu bawaan (dicatat)")
                continue
            if "insufficient_quota" in pesan_penuh or "billing" in pesan_penuh.lower():
                return {"teks": None, "percobaan": coba,
                        "galat": "KUOTA_HARIAN: saldo/kuota API habis. " + pesan_penuh[:400]}
            if coba == maks_ulang:
                return {"teks": None, "galat": pesan, "percobaan": coba}
            if coba == 1:
                print("     ! pesan galat lengkap:\n" + pesan_penuh[:1500])
            print(f"     ! {pesan[:90]} ... tunggu {tunggu} s")
            time.sleep(tunggu)
            tunggu = min(tunggu * 2, 300)


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--model", help="nama model OpenAI, lihat --daftar-model")
    a.add_argument("--sampel", choices=["kecil", "besar"], default="kecil")
    a.add_argument("--batas", type=int, default=None)
    a.add_argument("--jeda", type=float, default=2.0,
                   help="detik antarpanggilan agar tidak melewati batas per menit")
    a.add_argument("--kunci", help="berkas teks berisi kunci API (opsional)")
    a.add_argument("--catatan", default="pembanding komersial, zero-shot")
    a.add_argument("--tingkat", choices=["gratis", "berbayar"], default="berbayar",
                   help="tingkat layanan API (dicatat per panggilan)")
    a.add_argument("--daftar-model", action="store_true")
    a.add_argument("--lanjutkan", type=Path, help="folder run yang terhenti karena kuota")
    arg = a.parse_args()

    c = klien(arg)
    if arg.daftar_model:
        daftar_model(c)
        return

    if arg.lanjutkan:
        DIR = arg.lanjutkan
        MAN = json.loads((DIR / "manifest.json").read_text(encoding="utf-8"))
        model = MAN["model"]["nama"]
        konfig_path = DIR / "paket" / "konfigurasi_fitur.json"
        f_sampel = K3 / "Output Sampel" / f"sampel_{MAN['sampel']['nama']}.csv"
        batas = MAN.get("batas")
        MAN.setdefault("riwayat_lanjut", []).append(
            {"waktu_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             "tingkat": arg.tingkat})
    else:
        if not arg.model:
            sys.exit("Sebutkan --model. Lihat pilihan dengan --daftar-model.")
        model, batas = arg.model, arg.batas
        konfig_path = KONFIG
        f_sampel = K3 / "Output Sampel" / f"sampel_{arg.sampel}.csv"

    konfig = json.loads(konfig_path.read_text(encoding="utf-8"))
    tanda_manifes = (DIR / "paket") if arg.lanjutkan else PROMPT_DIR
    f_man = sorted(tanda_manifes.glob("manifes_v*_*.json"), key=lambda f: f.stat().st_mtime)[-1]
    MP = json.loads(f_man.read_text(encoding="utf-8"))
    if MP["fitur_terpilih"] != konfig["seleksi"]["terpilih"]:
        sys.exit("Manifes prompt tidak cocok dengan konfigurasi. Jalankan ulang 04_susun_prompt.py.")
    PROMPT = {j: (f_man.parent / MP["prompt"][j]["berkas"]).read_text(encoding="utf-8")
              for j in ("fitur", "kelas")}
    for j in PROMPT:
        assert sha(PROMPT[j]) == MP["prompt"][j]["sha256_12"], f"prompt {j} berubah dari manifes"

    sampel = pd.read_csv(f_sampel)
    if batas:
        sampel = sampel.groupby("kelas_xbd", group_keys=False).head(max(1, batas // 3)).head(batas)

    if not arg.lanjutkan:
        mulai = datetime.datetime.now(datetime.timezone.utc)
        kode = "oai-" + model.replace("gpt-", "").replace(".", "")
        run_id = (f"{mulai:%Y%m%d-%H%M%S}_{kode}_{arg.sampel}{batas or ''}"
                  f"_v{MP['versi_prompt']}_{MP['sidik_fitur']}")
        DIR = RUNS / run_id
        DIR.mkdir(parents=True, exist_ok=False)
        (DIR / "paket").mkdir()
        for f in (konfig_path, PARSER, f_man, f_man.parent / MP["prompt"]["fitur"]["berkas"],
                  f_man.parent / MP["prompt"]["kelas"]["berkas"]):
            shutil.copy(f, DIR / "paket" / f.name)
        MAN = {
            "run_id": run_id, "status": "berjalan",
            "waktu_mulai_utc": mulai.isoformat(timespec="seconds"),
            "catatan": arg.catatan, "uji_cepat": bool(batas), "batas": batas,
            "model": {"nama": model, "repo": "OpenAI API (chat.completions)", "tingkat_awal": arg.tingkat,
                      "revisi": None, "dtype": None},
            "lingkungan": {"platform": "laptop", "python": platform.python_version(),
                           "gpu": None, "sdk": "openai"},
            "eksperimen": {"sidik_fitur": MP["sidik_fitur"], "versi_prompt": MP["versi_prompt"],
                           "versi_konfigurasi": konfig.get("_versi_konfigurasi"),
                           "status_seleksi": konfig["seleksi"]["status"],
                           "fitur_terpilih": konfig["seleksi"]["terpilih"],
                           "sha_konfigurasi": sha(konfig_path), "sha_parser": sha(PARSER),
                           "sha_prompt_fitur": MP["prompt"]["fitur"]["sha256_12"],
                           "sha_prompt_kelas": MP["prompt"]["kelas"]["sha256_12"],
                           "desain": "dua panggilan: fitur(pra+pasca) dan kelas(pasca)"},
            "sampel": {"nama": arg.sampel, "n": int(len(sampel)), "sha_csv": sha(f_sampel),
                       "komposisi": sampel["kelas_xbd"].value_counts().to_dict()},
            "dekode": {"temperature": 0.0, "ukuran_citra": 448, "jeda_detik": arg.jeda},
            "catatan_metodologis": [
                "Model API dapat diperbarui penyedia; model_version dicatat per panggilan.",
                "Data API OpenAI secara bawaan tidak dipakai untuk pelatihan; chip berasal dari dataset publik xBD.",
                "Kemungkinan kontaminasi data (model pernah melihat xBD) tidak dapat diperiksa.",
            ],
        }

    def simpan():
        (DIR / "manifest.json").write_text(json.dumps(MAN, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    simpan()

    F = DIR / "mentah.jsonl"
    selesai = set()
    if F.exists():
        selesai = {json.loads(b)["uid"] for b in F.read_text(encoding="utf-8").splitlines() if b.strip()}
    sisa = sampel[~sampel["uid"].isin(selesai)]
    print(f"RUN {DIR.name}\n  model {model} | sudah {len(selesai)} | sisa {len(sisa)}")

    import importlib.util
    spec = importlib.util.spec_from_file_location("parser05", DIR / "paket" / "05_parser_keluaran.py")
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)
    F_LOG = DIR / "log_berjalan.txt"

    def catat(teks: str) -> None:
        print(teks)
        with F_LOG.open("a", encoding="utf-8") as lg:
            lg.write(teks + "\n")

    catat(f"=== {DIR.name} | mulai {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M:%S} UTC"
          f" | sudah {len(selesai)} | sisa {len(sisa)} ===")
    berhenti = None
    with F.open("a", encoding="utf-8") as fh:
        for i, r in enumerate(sisa.itertuples(index=False), 1):
            baris = {"uid": r.uid, "tile": r.tile, "kelas_xbd": r.kelas_xbd, "model": model,
                     "run_id": DIR.name}
            pra, pasca = CHIP / "pra" / r.chip_pra, CHIP / "pasca" / r.chip_pasca
            for jenis, gambar in (("fitur", [pra, pasca]), ("kelas", [pasca])):
                t0 = time.time()
                h = panggil(c, model, gambar, PROMPT[jenis])
                baris.update({f"mentah_{jenis}": h["teks"], f"galat_{jenis}": h["galat"],
                              # detik_<jenis> = latensi panggilan yang berhasil (setara 'detik'
                              # pada run SVLM); termasuk ulang = ditambah waktu tunggu 503/429
                              f"detik_{jenis}": h.get("detik_api"),
                              f"detik_termasuk_ulang_{jenis}": round(time.time() - t0, 2),
                              f"percobaan_{jenis}": h.get("percobaan"),
                              f"model_version_{jenis}": h.get("model_version"),
                              f"token_{jenis}": [h.get("token_masuk"), h.get("token_keluar")],
                              f"token_berpikir_{jenis}": h.get("token_berpikir"),
                              f"system_fingerprint_{jenis}": h.get("system_fingerprint"),
                              f"suhu_{jenis}": h.get("suhu"),
                              f"tingkat_{jenis}": arg.tingkat})
                if h["galat"] and h["galat"].startswith("KUOTA_HARIAN"):
                    berhenti = h["galat"]
                    break
                time.sleep(arg.jeda)
            if berhenti:
                break   # baris yang belum lengkap TIDAK ditulis, akan diulang saat dilanjutkan
            baris["detik_total"] = round((baris["detik_fitur"] or 0) + (baris["detik_kelas"] or 0), 2)
            baris["selesai_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
            fh.write(json.dumps(baris, ensure_ascii=False) + "\n")
            fh.flush()
            hf = P.urai_fitur(baris.get("mentah_fitur") or "", konfig)
            hk = P.urai_kelas(baris.get("mentah_kelas") or "", konfig)
            fitur_teks = ", ".join(f"{k.split('_')[0]}={hf.get('fitur_' + k)}"
                                   for k in konfig["seleksi"]["terpilih"])
            galat = " | GALAT" if (baris["galat_fitur"] or baris["galat_kelas"]) else ""
            catat(f"[{len(selesai) + i:>4}/{len(sampel)}] uid={r.uid} | {r.tile} | "
                  f"chip={r.chip_pra},{r.chip_pasca} | xBD={r.kelas_xbd} | "
                  f"kelas={hk.get('kelas_kerusakan')} | {fitur_teks} | "
                  f"{(baris['detik_fitur'] or 0) + (baris['detik_kelas'] or 0):.1f}s{galat}")

    semua = [json.loads(b) for b in F.read_text(encoding="utf-8").splitlines() if b.strip()]
    sah_w = [m for m in semua if not (m.get("galat_fitur") or m.get("galat_kelas"))]

    def statistik(nilai):
        v = sorted(float(x) for x in nilai if x is not None)
        if not v:
            return {}
        n = len(v)
        rerata = sum(v) / n
        sd = (sum((x - rerata) ** 2 for x in v) / (n - 1)) ** 0.5 if n > 1 else 0.0
        med = v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
        p95 = v[min(n - 1, round(0.95 * (n - 1)))]
        return {"n": n, "total_detik": round(sum(v), 1), "rerata": round(rerata, 2),
                "median": round(med, 2), "sd": round(sd, 2), "min": round(v[0], 2),
                "p95": round(p95, 2), "maks": round(v[-1], 2)}

    WAKTU = {
        "satuan": "detik",
        "cakupan": ("latensi panggilan API yang berhasil (jaringan + antrean + komputasi server); "
                    "tidak setara dengan waktu GPU lokal SVLM; tanpa jeda antarpanggilan "
                    f"{arg.jeda} s dan tanpa waktu tunggu coba ulang"),
        "per_panggilan_fitur": statistik(m.get("detik_fitur") for m in sah_w),
        "per_panggilan_kelas": statistik(m.get("detik_kelas") for m in sah_w),
        "per_bangunan": statistik(m.get("detik_total") for m in sah_w),
        "per_bangunan_termasuk_ulang": statistik(
            (m.get("detik_termasuk_ulang_fitur") or 0) + (m.get("detik_termasuk_ulang_kelas") or 0)
            for m in sah_w),
        "jumlah_panggilan_diulang": sum(1 for m in semua for j in ("fitur", "kelas")
                                        if (m.get(f"percobaan_{j}") or 1) > 1),
        "jeda_antarpanggilan_detik": arg.jeda,
    }
    try:
        t0_run = datetime.datetime.fromisoformat(MAN["waktu_mulai_utc"])
        WAKTU["jam_dinding_menit"] = round(
            (datetime.datetime.now(datetime.timezone.utc) - t0_run).total_seconds() / 60, 1)
    except (KeyError, ValueError):
        pass
    MAN["waktu_komputasi"] = WAKTU
    (DIR / "waktu_komputasi.json").write_text(json.dumps(WAKTU, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
    pb = WAKTU["per_bangunan"]
    if pb:
        catat(f"WAKTU (latensi API, detik): per bangunan rerata {pb['rerata']} | median {pb['median']}"
              f" | sd {pb['sd']} | min {pb['min']} | maks {pb['maks']} | total {pb['total_detik']}"
              f" | jam dinding {WAKTU.get('jam_dinding_menit')} menit")
    n_ada = len(semua)
    versi = {json.loads(b).get("model_version_kelas") for b in F.read_text(encoding="utf-8").splitlines() if b.strip()}
    MAN["model"]["revisi"] = ", ".join(sorted(v for v in versi if v)) or None
    MAN["n_selesai"] = n_ada
    if berhenti:
        MAN["status"] = "terputus"
        print(f"\n!! Berhenti karena kuota: {berhenti[:500]}")
        print(f"   Lanjutkan besok:  python {Path(__file__).name} --lanjutkan \"{DIR}\"")
    else:
        MAN["status"] = "selesai" if n_ada >= len(sampel) else "terputus"
        MAN["waktu_selesai_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    simpan()
    print(f"\n{n_ada}/{len(sampel)} bangunan tersimpan di {F}")
    print("Berikutnya: python 10_rekap_run.py")


if __name__ == "__main__":
    main()
