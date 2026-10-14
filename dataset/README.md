# Dataset

## Sumber data utama

Data citra dan label kerusakan berasal dari dataset **xBD** (Gupta dkk., 2019) yang dirilis melalui kompetisi xView2 (https://xview2.org). Yang dipakai adalah kejadian `palu-tsunami`: 196 tile citra WorldView-2 berukuran 1.024 × 1.024 piksel (sekitar 0,5 m/piksel), masing-masing dengan citra prabencana, citra pascabencana, dan label poligon bangunan berformat JSON. Dataset xBD terbuka untuk umum dengan lisensi CC BY-NC-SA 4.0. Ketentuan lengkapnya dapat dilihat di situs xView2.

Citra dan label mentah tidak disertakan di repositori ini karena ukurannya besar. Unduh dataset xBD dari situs xView2, lalu jalankan `pemodelan/01_inventarisasi/01_inventarisasi_xbd_palu.py` untuk membentuk ulang inventaris bangunan.

## `publik/` — data yang boleh dibuka untuk umum

| Folder | Isi |
|---|---|
| `01_inventarisasi/` | Inventaris 55.789 bangunan xBD Palu (`inventaris_palu_bangunan.csv`), ringkasan per tile, dan metadata lima grup akuisisi citra prabencana |
| `02_sampel/` | Kerangka sampel (33.060 bangunan), sampel besar (400), sampel kecil (40), data latih dan validasi *fine-tuning* (715 dan 126), katalog potongan citra uji dan latih, serta ringkasan penarikan sampel |
| `03_keluaran_model/` | Satu folder untuk setiap run model (manifes, keluaran mentah, hasil penguraian, catatan waktu komputasi, paket prompt) beserta `daftar_run.csv`. Adapter LoRA dan paket ZIP tidak disertakan karena ukurannya |
| `04_analisis/` | Tabel hasil analisis Bab IV (`analisis_20260927-115214`): kesepakatan penilai, asosiasi fitur–kelas, metrik klasifikasi, uji McNemar, metrik teks, QUEST, dan α Krippendorff |
| `05_kunci_penyamaran/` | Kunci kode bangunan E01–E40 dan penyamaran Model A/B/C pada formulir Sesi A dan Sesi B |

Run final yang dianalisis:

| Model | Run |
|---|---|
| Qwen2.5-VL-3B (*zero-shot*) | `20260924-145022_qwen3b_besar_v4_b82f43f2` |
| InternVL3-2B (*zero-shot*) | `20260924-213226_ivl2b_besar_v4_b82f43f2` |
| gpt-6-sol (pembanding) | `20260924-162858_oai-6-sol_kecil_v4_b82f43f2` |
| Qwen2.5-VL-3B + LoRA | `20260925-100029_qwen3b-lora_besar_v4_b82f43f2` |

Run lain disimpan sebagai jejak pengembangan (uji coba, uji bentuk pertanyaan, uji kewajaran, diagnosa presisi, dan percobaan Gemini).

## `dummy/` — data penilai yang tidak bersifat publik

Data dari penilai manusia dikumpulkan sendiri oleh peneliti dan tidak dibuka untuk umum. Folder ini hanya berisi contoh struktur data, minimal 5 baris, dengan data sensitif disamarkan (`[DISAMARKAN]`).

| Berkas | Isi asli | Yang disamarkan |
|---|---|---|
| `penilaian_fitur_dummy.csv` | Skor kepentingan 8 kandidat fitur dari 2 penilai (tujuan 1) | nama, instansi, alasan |
| `sesi_a_deskripsi_referensi_dummy.csv` | Contoh deskripsi referensi dari 5 mahasiswa (Sesi A) | identitas diganti kode EVAL01–EVAL05 |
| `sesi_b_skor_quest_dummy.csv` | Contoh skor QUEST (akurasi, relevansi, kepuasan) Sesi B | identitas diganti kode EVAL01–EVAL05 |
| `uji_prototipe_blackbox_sus_dummy.csv` | Hasil *black-box testing* dan SUS dari 5 mahasiswa | waktu pengisian, email, nama, kelas, dan isian bebas |

Nama penilai ahli juga disamarkan pada salinan `konfigurasi_fitur.json` di repositori ini. Karena itu, sidik berkas tersebut tidak lagi sama dengan nilai `sha_konfigurasi` yang tercatat di manifes run.
