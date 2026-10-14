# Dokumentasi Sistem Prototipe

## 1. Gambaran umum

Prototipe "Informasi Kerusakan Bangunan Pascabencana" adalah aplikasi web statis yang menyajikan hasil ekstraksi *Small Vision-Language Model* (SVLM) untuk 400 bangunan sampel gempa bumi dan tsunami Palu, 28 September 2018. Prototipe ini tidak menjalankan model secara langsung. Seluruh hasil dihitung lebih dahulu pada tahap pemodelan, dievaluasi, lalu dikemas menjadi berkas data yang dibaca aplikasi. Dengan cara ini, setiap informasi yang tampil dapat ditelusuri ke run model yang telah dievaluasi.

Versi di repositori ini adalah *build* `prototipe_20260927-1500`, versi yang diuji oleh evaluator. Setelah sidang, versi ini ditambah bagian 7 "Identitas penyusun" pada menu Informasi Umum, dan logo pada kepala halaman dibuat dapat diklik untuk memuat ulang halaman. Data dan citra tidak berubah.

## 2. Arsitektur dan alur data

```
Run model terpilih (dataset/publik/03_keluaran_model)    Label xBD dan sampel (dataset/publik/02_sampel)
Tabel analisis (dataset/publik/04_analisis)               Potongan citra pra & pasca (03_ekstraksi_chip.py)
                       │                                              │
                       └──────────────► 16_bangun_prototipe.py ◄──────┘
                                         (Python: pandas, Pillow)
                                                  │
                                                  ▼
            artefak/prototipe/
              ├── index.html          kerangka halaman dan tiga menu
              ├── assets/app.js       logika aplikasi (penyaring, peta, tanya-jawab)
              ├── assets/app.css      tampilan, termasuk tata letak ponsel
              ├── assets/logo-stis.png
              ├── data/data.js        seluruh data bangunan dan metrik (window.DATA)
              └── img/PL-001.jpg … PL-400.jpg   pasangan citra sebelum | sesudah
                                                  │
                                                  ▼
                              Peramban pengguna (Chrome/Edge, laptop atau ponsel)
                              + Leaflet 1.9.4 dan peta dasar (memerlukan internet)
```

### Aturan pemilihan sumber data

Aturan ini ditetapkan sebelum hasil evaluasi dibaca (Bab III skripsi), dan diperiksa ulang oleh `16_bangun_prototipe.py` terhadap folder analisis.

| Komponen | Aturan | Sumber terpilih |
|---|---|---|
| Kelas kerusakan | Akurasi seimbang tertinggi pada 385 bangunan | Qwen2.5-VL-3B + LoRA (0,682) |
| Empat tanda kerusakan dan deskripsi | Skor akurasi QUEST tertinggi di antara SVLM yang keluaran fiturnya sah | InternVL3-2B *zero-shot* (3,02) |
| Pembanding | Selalu ditampilkan | Label xBD |

## 3. Teknologi

| Bagian | Teknologi |
|---|---|
| Aplikasi | HTML, CSS, dan JavaScript tanpa kerangka kerja |
| Peta | Leaflet 1.9.4 (cdnjs); peta dasar CARTO Voyager (data OpenStreetMap), cadangan Esri World Street Map, dan lapisan Esri World Imagery sebagai latar. Bila peta dasar tidak termuat, titik digambar dengan SVG menurut koordinat |
| Penyusun data | Python 3 (pandas, Pillow) |
| Hosting | Situs statis; tidak memerlukan basis data maupun server aplikasi |

## 4. Struktur data (`data/data.js`)

Berkas berisi satu objek `window.DATA` dengan kunci berikut:

| Kunci | Isi |
|---|---|
| `meta` | Tanggal citra pra dan pasca, ukuran kerangka sampel, nama model dan identitas run sumber, waktu penyusunan data |
| `konteks` | Angka dampak bencana Palu (meninggal, hilang, pengungsi, kerusakan dan kerugian) beserta sumbernya |
| `metrik` | Ringkasan evaluasi: akurasi, akurasi seimbang, F1 makro, *confusion matrix* model LoRA, skor QUEST, dan jumlah deskripsi yang identik |
| `label_fitur`, `label_level` | Nama tampilan fitur dan tingkat nilainya |
| `contoh` | Kode bangunan contoh untuk bagian Data pada web story |
| `bangunan` | 400 catatan bangunan |

Contoh satu catatan bangunan:

```json
{"kode": "PL-001", "uid": "e315dd32-…", "lon": 119.8525, "lat": -0.7063,
 "xbd": "tidak_rusak", "kelas": "tidak_rusak",
 "fitur": {"keutuhan_atap": "rusak_sebagian", "puing_sekitar": "terbatas_di_sekitar_bangunan",
           "wujud_bangunan": "berubah_sebagian", "sedimen_lumpur": "menutupi_sebagian"},
 "deskripsi": "Bangunan rusak sebagian, …", "himpunan": "besar", "img": "img/PL-001.jpg"}
```

Kode bangunan PL-001 sampai PL-400 diurutkan menurut lintang dari utara ke selatan. `kelas` adalah keluaran model, sedangkan `xbd` adalah label pembanding. Keduanya memakai kelas `tidak_rusak`, `rusak`, dan `hancur`.

## 5. Menu dan fungsi

### Informasi Umum (*web story*)

Tujuh bagian dibaca berurutan: (1) Kejadian, (2) Data, (3) Cara kerja, (4) Hasil, (5) Batasan, (6) Tentang prototipe (sumber data dan identitas run), dan (7) Identitas penyusun.

### Dashboard

- Lima kotak ringkasan: jumlah bangunan yang ditampilkan, jumlah per kelas model, dan persentase kesesuaian dengan label xBD.
- Penyaring menurut kelas model, label xBD, dan kesesuaian. Penyaring langsung diterapkan dan dapat digabung.
- Daftar pilihan kode bangunan yang isinya mengikuti penyaring, tombol Atur ulang, dan tombol Unduh CSV (data tersaring, pemisah titik koma, UTF-8).
- Peta titik bangunan dengan pilihan peta dasar dan sakelar ringkasan per kotak grid ±1 km. Kotak grid dibentuk dari koordinat sampel, bukan batas wilayah administrasi.
- Panel rincian: pasangan citra, kelas model, label xBD, penanda kesesuaian, empat tanda kerusakan, deskripsi, catatan keseragaman deskripsi, dan tombol "Tanyakan bangunan ini".
- Daftar bangunan hasil penyaringan.

### Tanya-Jawab

Menu ini memberi nuansa percakapan tanpa model bahasa. Pertanyaan dicocokkan dengan pola kata kunci, dan jawabannya disusun dari data yang telah dihitung. Pengguna memilih bangunan melalui daftar kode atau galeri pasangan citra (6 per halaman, dengan tombol Sebelumnya, Berikutnya, dan Acak).

Dua belas pertanyaan baku:

| Kelompok | Pertanyaan |
|---|---|
| Tentang bangunan terpilih | Apa kelas kerusakan bangunan ini? · Bagaimana kondisi atapnya? · Apakah ada puing di sekitarnya? · Bagaimana wujud bangunannya? · Apakah ada lumpur atau sedimen? · Apa deskripsi singkat bangunan ini? · Tampilkan citra bangunan ini · Apakah hasil model sesuai dengan label xBD? |
| Umum | Berapa banyak bangunan per kelas kerusakan? · Seberapa andal hasil ini? · Model apa yang dipakai? · Data apa yang dipakai? |

Aturan tambahan:

- Kode bangunan yang disebut di dalam pertanyaan (misalnya "bagaimana atap PL-015?") langsung dikenali. Kode yang tidak ada (misalnya PL-999) dijawab dengan pemberitahuan bahwa kode tidak ditemukan.
- Pertanyaan tentang bangunan yang diajukan sebelum bangunan dipilih dijawab dengan permintaan untuk memilih bangunan lebih dahulu.
- Pertanyaan di luar cakupan data (biaya, harga, anggaran, korban, pemilik, penghuni, alamat, asuransi, ganti rugi, bantuan) dijawab bahwa informasinya tidak tersedia.
- Setiap jawaban mencantumkan sumber (kelas dari Qwen2.5-VL-3B + LoRA; tanda dan deskripsi dari InternVL3-2B) dan diikuti tombol rekomendasi pertanyaan berikutnya.

## 6. Pengujian

Pengujian dilakukan oleh lima mahasiswa sebagai pengguna proksi melalui Google Form (27–28 September 2026).

| Pengujian | Hasil |
|---|---|
| *Black-box testing*, 19 skenario partisi ekuivalensi (B01–B19) × 5 evaluator | 94 dari 95 berhasil (98,9 persen); B14 (kode di dalam pertanyaan) 4 dari 5 |
| *System Usability Scale* versi bahasa Indonesia | Rata-rata 75,0 (median 80,0), di atas rata-rata umum 68, kategori *good* |

## 7. Batasan

- Prototipe menyajikan 400 bangunan sampel dari satu pasangan akuisisi citra (24 Januari 2017 dan 1 Oktober 2018), bukan seluruh bangunan di Kota Palu.
- Kelas dan tanda kerusakan berasal dari dua model berbeda, sehingga keduanya dapat tidak sejalan pada bangunan yang sama. Selain itu, 319 dari 400 kalimat deskripsi identik.
- Informasi ditujukan untuk membantu menentukan urutan pemeriksaan bangunan, bukan menggantikan pemeriksaan lapangan.
- Prototipe tidak dapat memproses citra baru tanpa menjalankan ulang skrip pemodelan.

## 8. Panduan penggunaan

Panduan langkah demi langkah untuk setiap menu tersedia di `Buku Pedoman Penggunaan Prototipe SVLM.pdf` pada folder ini.
