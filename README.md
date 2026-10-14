# Ekstraksi Informasi Kerusakan Bangunan Pascabencana Menggunakan *Small Vision-Language Model* pada Citra Satelit Resolusi Sangat Tinggi

**(Studi Kasus: Bencana Gempa dan Tsunami Palu 2018)**

Repositori ini berisi kode artefak, kode pemodelan, dataset, dokumentasi sistem, dan panduan penggunaan skripsi di atas.

## Identitas

| Keterangan | Isi |
|---|---|
| Nama | Rizky Alif Ichwanto |
| NIM | 222212857 |
| Kelas | 4SD2 |
| Program studi | D-IV Komputasi Statistik, peminatan Sains Data |
| Perguruan tinggi | Politeknik Statistika STIS |
| Tahun lulus | 2026 |
| Dosen pembimbing | Dr. Eng. Arie Wahyu Wijayanto, S.S.T., M.T. |

## Ringkasan

Penelitian ini menerapkan *Small Vision-Language Model* (SVLM) berukuran 2–3 miliar parameter untuk mengekstraksi informasi kerusakan bangunan dari pasangan citra satelit sebelum dan sesudah gempa bumi dan tsunami Palu 2018 (dataset xBD, WorldView-2, sekitar 0,5 m/piksel). Ada tiga tujuan penelitian:

1. menyusun empat fitur visual kerusakan dari delapan kandidat;
2. menerapkan Qwen2.5-VL-3B dan InternVL3-2B secara *zero-shot*, ditambah *fine-tuning* LoRA pada Qwen2.5-VL-3B;
3. membuat prototipe aplikasi web untuk menyajikan hasilnya.

Hasil utamanya, kedua SVLM *zero-shot* setara tebakan konstan (akurasi seimbang 0,323 dan 0,333). *Fine-tuning* LoRA menaikkan akurasi seimbang menjadi 0,682 pada 385 bangunan uji. Prototipe lolos 94 dari 95 skenario *black-box testing* dan memperoleh skor *System Usability Scale* rata-rata 75,0.

## Struktur berkas

```
.
├── README.md                  ← berkas ini
├── artefak/
│   └── prototipe/             ← kode artefak: aplikasi web statis (index.html, assets/, data/, img/)
├── pemodelan/                 ← kode pemodelan, diurutkan menurut tahap penelitian
│   ├── README.md              ← urutan menjalankan skrip dan pemetaan ke folder kerja asli
│   ├── requirements.txt
│   ├── 01_inventarisasi/      ← inventarisasi label xBD Palu
│   ├── 02_sampel_dan_chip/    ← kerangka sampel, penarikan sampel, potongan citra, sampel latih
│   ├── 03_prompt/             ← konfigurasi fitur, penyusun prompt, pengurai keluaran
│   ├── 04_inferensi/          ← uji kendali, inferensi SVLM (Kaggle), uji kewajaran, model pembanding
│   ├── 05_finetuning/         ← fine-tuning LoRA Qwen2.5-VL-3B (Kaggle)
│   ├── 06_evaluasi/           ← formulir penilai dan skrip analisis Bab IV
│   └── 07_prototipe/          ← skrip penyusun data prototipe dan kode sumber aplikasi
├── dataset/
│   ├── README.md              ← sumber, lisensi, dan isi setiap berkas data
│   ├── publik/                ← data turunan xBD, keluaran model, dan tabel analisis
│   └── dummy/                 ← data penilai yang disamarkan (bukan data publik)
└── dokumentasi/
    ├── dokumentasi_sistem.md  ← arsitektur, alur data, teknologi, dan aturan tanya-jawab prototipe
    ├── Buku Pedoman Penggunaan Prototipe SVLM.pdf   ← panduan penggunaan
    └── instrumen/             ← templat formulir penilaian fitur, Sesi A, dan Sesi B
```

## Menjalankan prototipe

Prototipe tidak memerlukan server maupun instalasi.

1. Unduh atau *clone* repositori ini.
2. Buka `artefak/prototipe/index.html` dengan Google Chrome atau Microsoft Edge.
3. Peta dasar memerlukan koneksi internet. Tanpa internet, titik bangunan tetap ditampilkan menurut koordinatnya.

Prototipe juga dapat diunggah ke layanan situs statis mana pun dengan memakai folder `artefak/prototipe/` sebagai folder publikasi. Petunjuk lengkap ada di `dokumentasi/Buku Pedoman Penggunaan Prototipe SVLM.pdf`.

## Menjalankan ulang pemodelan

Urutan skrip, lingkungan komputasi, dan cara menyesuaikan jalur berkas dijelaskan di [`pemodelan/README.md`](pemodelan/README.md). Inferensi SVLM dan *fine-tuning* dijalankan di Kaggle Notebook (GPU NVIDIA T4 16 GB). Penyiapan data dan analisis dijalankan di komputer pribadi.

## Catatan data

- Citra dan label xBD mentah tidak disertakan karena ukurannya besar. Cara mengunduhnya dijelaskan di [`dataset/README.md`](dataset/README.md).
- Data penilaian dari penilai (ahli dan mahasiswa) tidak bersifat publik. Data ini hanya disertakan sebagai dummy minimal 5 baris, dengan identitas dan isian bebas yang disamarkan.
- Adapter LoRA (±120 MB) dan paket ZIP Kaggle tidak disertakan karena melampaui batas ukuran berkas repositori.
- Kunci API tidak disimpan dalam kode. Skrip model pembanding membaca kunci dari variabel lingkungan `OPENAI_API_KEY` atau `GEMINI_API_KEY`.

## Lisensi dan sitasi data

Citra dan label berasal dari dataset xBD (Gupta dkk., 2019, *xBD: A Dataset for Assessing Building Damage from Satellite Imagery*) melalui program xView2. Pemakaian ulang data turunan mengikuti ketentuan lisensi xBD/xView2.
