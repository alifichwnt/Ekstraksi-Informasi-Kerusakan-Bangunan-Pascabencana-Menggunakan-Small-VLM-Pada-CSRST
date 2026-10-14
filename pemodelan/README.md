# Kode Pemodelan

Skrip di folder ini disusun menurut tahap CRISP-DM pada Bab III skripsi. Nomor di depan nama berkas adalah urutan pengerjaan saat penelitian. Karena tahap-tahapnya pernah berjalan bolak-balik, urutan nomor tidak selalu sama dengan urutan folder.

## Urutan dan fungsi skrip

| Folder | Berkas | Fungsi | Dijalankan di |
|---|---|---|---|
| 01_inventarisasi | `01_inventarisasi_xbd_palu.py` | Membaca seluruh label JSON xBD kejadian palu-tsunami dan menghasilkan inventaris bangunan, tile, dan grup akuisisi | Laptop |
| 02_sampel_dan_chip | `02_penarikan_sampel.py` | Membentuk kerangka sampel (saringan S1–S4, 33.060 bangunan) dan menarik sampel besar (400), sampel kecil (40), serta set pengembangan (15) | Laptop |
| 02_sampel_dan_chip | `03_ekstraksi_chip.py` | Memotong citra pra dan pasca 128 × 128 piksel, memperbesarnya ke 448 piksel (Lanczos), dan menggambar kotak magenta dengan bidik silang | Laptop |
| 02_sampel_dan_chip | `13_sampel_latih.py` | Menarik data latih (715) dan validasi (126) dari tile yang terpisah dari tile uji; opsi `--zip` membuat paket Kaggle | Laptop |
| 03_prompt | `konfigurasi_fitur.json` | Sumber tunggal definisi fitur, tingkat nilai, rubrik kelas, dan aturan prompt | – |
| 03_prompt | `04_susun_prompt.py` | Menyusun prompt versi 4 (panggilan fitur dan panggilan kelas), skema keluaran, dan butir formulir dari konfigurasi | Laptop |
| 03_prompt | `05_parser_keluaran.py` | Mengurai keluaran model menjadi JSON dengan lima tingkat perbaikan berjenjang | Laptop / Kaggle |
| 04_inferensi | `06a_siapkan_smoke_zip.py`, `06_smoke_test_svlm.ipynb` | Uji asap prompt versi 1–2 | Laptop / Colab |
| 04_inferensi | `07a_siapkan_dataset_kaggle.py`, `07_…ipynb`, `07k_…KAGGLE.ipynb` | Uji kendali penglihatan (empat cara penyajian citra) | Kaggle |
| 04_inferensi | `09a_siapkan_dataset_inferensi.py` | Menyiapkan paket chip dan prompt untuk Kaggle | Laptop |
| 04_inferensi | `09_inferensi_svlm_KAGGLE.ipynb` | Inferensi Qwen2.5-VL-3B dan InternVL3-2B *zero-shot* (dua panggilan per bangunan) | Kaggle T4 |
| 04_inferensi | `09p_…`, `09s_…`, `09d_…` | Uji bentuk pertanyaan, uji kewajaran (citra hitam/derau), dan diagnosa presisi float16 | Kaggle |
| 04_inferensi | `09o_pembanding_openai.py` | Model pembanding gpt-6-sol melalui OpenAI API (40 bangunan) | Laptop |
| 04_inferensi | `09g_pembanding_gemini.py` | Percobaan pembanding Gemini (dihentikan karena kuota; disimpan sebagai jejak) | Laptop |
| 04_inferensi | `10_rekap_run.py` | Merekap seluruh run menjadi `daftar_run.csv` | Laptop |
| 05_finetuning | `14_finetune_lora_qwen_KAGGLE.ipynb` | *Fine-tuning* LoRA (r = 16, α = 32, 3 *epoch*) untuk penentuan kelas, lalu inferensi pada data uji | Kaggle T4 |
| 06_evaluasi | `08_buat_formulir_seleksi.py` | Membuat formulir penilaian kandidat fitur (tujuan 1) | Laptop |
| 06_evaluasi | `11_buat_formulir_sesi_a.py`, `12_buat_formulir_sesi_b.py` | Membuat formulir deskripsi referensi (Sesi A) dan penilaian QUEST tersamar (Sesi B) | Laptop |
| 06_evaluasi | `15_analisis_bab4.py` | Seluruh analisis Bab IV: kesepakatan penilai, τ-b fitur–kelas, *confusion matrix*, bootstrap, McNemar, BLEU/METEOR/ROUGE, QUEST, α Krippendorff | Laptop |
| 06_evaluasi | `17_buat_formulir_prototipe.py`, `18_rekap_evaluasi_prototipe.py` | Skenario *black-box* dan SUS, serta rekap hasil uji prototipe | Laptop |
| 07_prototipe | `16_bangun_prototipe.py`, `prototipe_src/` | Memilih sumber data sesuai aturan Bab III, menyusun `data/data.js` dan 400 citra, lalu membangun prototipe | Laptop |

## Menjalankan ulang

Selama penelitian, skrip dijalankan dari folder kerja dengan susunan `KOMPONEN_1` sampai `KOMPONEN_8`. Untuk menjalankannya ulang, susun folder kerja dengan pemetaan berikut, lalu arahkan variabel lingkungan `SKRIPSI_AKAR` ke folder tersebut. Skrip `01`, `02`, `03`, `06a`, `07a`, dan `09a` memakai jalur tetap di bagian atas berkas, jadi jalurnya perlu disunting.

| Folder kerja asli | Isi di repositori ini |
|---|---|
| `KOMPONEN_1` | formulir penilaian fitur (`dataset/dummy/`, `dokumentasi/instrumen/`) |
| `KOMPONEN_2` | `pemodelan/01_inventarisasi/` + `dataset/publik/01_inventarisasi/` (sebagai `Output Inventarisasi`) |
| `KOMPONEN_3` | `pemodelan/02_sampel_dan_chip/` + `dataset/publik/02_sampel/` (sebagai `Output Sampel`, `Output Sampel Latih`); chip dibentuk ulang dengan `03_ekstraksi_chip.py` |
| `KOMPONEN_4` | `pemodelan/03_prompt/` sampai `pemodelan/07_prototipe/` (semua skrip dalam satu folder) |
| `KOMPONEN_5` | `dataset/publik/03_keluaran_model/` (folder `runs/` dan `daftar_run.csv`) |
| `KOMPONEN_6` | formulir penilai (`dataset/dummy/`, `dokumentasi/instrumen/`) dan `dataset/publik/05_kunci_penyamaran/` |
| `KOMPONEN_7` | `dataset/publik/04_analisis/` |
| `KOMPONEN_8` | `artefak/prototipe/` |

Data mentah xBD diunduh terpisah (lihat `dataset/README.md`). Skrip model pembanding memerlukan kunci API milik sendiri yang disimpan di variabel lingkungan `OPENAI_API_KEY` atau `GEMINI_API_KEY`. Kunci tidak boleh ditulis langsung di kode.

## Lingkungan

- Laptop: Python 3.13; pustaka di `requirements.txt` bagian "laptop".
- Kaggle Notebook: GPU NVIDIA T4 16 GB, PyTorch, `transformers` 4.51.3, `peft` 0.15.2, `accelerate`. Versi lengkap pustaka, revisi bobot model, dan jenis GPU tiap run tercatat pada `manifest.json` di setiap folder run.
- Benih acak: 42 untuk penarikan sampel, pelatihan, dan bootstrap.
