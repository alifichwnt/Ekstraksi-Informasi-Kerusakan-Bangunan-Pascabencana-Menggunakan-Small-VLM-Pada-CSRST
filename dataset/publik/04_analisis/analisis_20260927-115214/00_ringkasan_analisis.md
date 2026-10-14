# Ringkasan Analisis Bab IV

Dijalankan 27-09-2026 11:52. Skrip `15_analisis_bab4.py`. Angka dengan koma desimal. n = 385 (sampel besar tanpa 15 bangunan set pengembangan) dan n = 40 (sampel kecil).

## Tujuan 1 — Kesepakatan penilai kepentingan fitur

Penilai dengan formulir lengkap: Peneliti, Ahli BPS MSSD (formulir dosen kosong → tidak dianalisis).

| Kandidat | Peneliti | Ahli BPS MSSD | Selisih |
|---|---|---|---|
| Keutuhan atap | 5 (#1) | 5 (#1) | +0 |
| Puing di sekitar bangunan | 5 (#1) | 4 (#3) | -1 |
| Wujud bangunan | 4 (#3) | 5 (#1) | +1 |
| Perubahan radiometri | 2 (#5) | 3 (#5) | +1 |
| Perubahan tekstur | 1 (#7) | 3 (#5) | +2 |
| Sedimen atau lumpur pada atap dan halaman | 3 (#4) | 4 (#3) | +1 |
| Bentuk dinding | 1 (#7) | 2 (#8) | +1 |
| Bangunan bergeser, terputar, atau miring dari tapak semula | 2 (#5) | 3 (#5) | +1 |

Irisan empat besar: **4 dari 4** (Keutuhan atap, Puing di sekitar bangunan, Wujud bangunan, Sedimen atau lumpur pada atap dan halaman). Spearman ρ = 0,881 (p = 0,0039); Kendall τ-b = 0,792 (p = 0,0120); Krippendorff α ordinal = 0,702. Rerata skor: Peneliti 2,88; Ahli BPS MSSD 3,62. n = 8 butir → koefisien pelengkap, bukan dasar keputusan.


### Asosiasi fitur–kelas (Kendall τ-b; fitur ordinal keluaran model vs label xBD)

| Model | n | keutuhan_atap | puing_sekitar | wujud_bangunan | sedimen_lumpur |
|---|---|---|---|---|---|
| Qwen2.5-VL-3B | 385 | t.d. | t.d. | t.d. | t.d. |
| InternVL3-2B | 385 | 0,122* | 0,122* | 0,122* | 0,122* |
| gpt-6-sol | 39 | 0,618* | 0,522* | 0,638* | 0,427* |

`*` p < 0,05; t.d. = tidak dapat dihitung karena jawaban fitur konstan. LoRA tidak diikutkan (0/40 keluaran fitur sah). Rincian + τ-b terhadap kelas model sendiri: `T1_asosiasi_fitur_kelas.csv`.


## Tujuan 2(a) — Confusion matrix terhadap label xBD


**Sampel besar tanpa set pengembangan (n = 385)**

| Model | Akurasi | Akurasi seimbang [95%] | F1 makro [95%] | κ | κ linear | F1 tr/r/h | Biner F1 | tidak sah |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-VL-3B | 0,239 | 0,323 [0,310–0,333] | 0,129 [0,110–0,146] | -0,013 | -0,016 | 0,00/0,00/0,39 | 0,654 | 0 |
| InternVL3-2B | 0,506 | 0,333 [0,333–0,333] | 0,225 [0,208–0,238] | 0,001 | 0,004 | 0,67/0,00/0,00 | 0,010 | 0 |
| Qwen2.5-VL-3B + LoRA | 0,727 | 0,682 [0,640–0,724] | 0,677 [0,630–0,721] | 0,551 | 0,664 | 0,81/0,41/0,81 | 0,786 | 0 |

**Sampel kecil (n = 40)**

| Model | Akurasi | Akurasi seimbang [95%] | F1 makro [95%] | κ | κ linear | F1 tr/r/h | Biner F1 | tidak sah |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-VL-3B | 0,225 | 0,300 [0,222–0,333] | 0,122 [0,061–0,182] | -0,042 | -0,051 | 0,00/0,00/0,37 | 0,644 | 0 |
| InternVL3-2B | 0,500 | 0,333 [0,333–0,333] | 0,222 [0,173–0,263] | 0,000 | 0,000 | 0,67/0,00/0,00 | 0,000 | 0 |
| Qwen2.5-VL-3B + LoRA | 0,750 | 0,700 [0,554–0,840] | 0,695 [0,522–0,835] | 0,592 | 0,667 | 0,86/0,50/0,73 | 0,842 | 0 |
| gpt-6-sol | 0,325 | 0,433 [0,295–0,559] | 0,323 [0,210–0,422] | 0,107 | 0,237 | 0,00/0,30/0,67 | 0,632 | 2 |

κ memakai 4 kategori (tidak sah = kategori tersendiri); κ linear hanya pada jawaban sah. Pembanding acak untuk akurasi seimbang 3 kelas = 1/3.

**Uji McNemar (α = 5%)**

| Himpunan | A vs B | hanya A benar | hanya B benar | uji | p |
|---|---|---|---|---|---|
| n385 | Qwen2.5-VL-3B + LoRA vs Qwen2.5-VL-3B | 203 | 15 | chi-kuadrat terkoreksi | < 0,0001 |
| n385 | Qwen2.5-VL-3B + LoRA vs InternVL3-2B | 113 | 28 | chi-kuadrat terkoreksi | < 0,0001 |
| n385 | InternVL3-2B vs Qwen2.5-VL-3B | 195 | 92 | chi-kuadrat terkoreksi | < 0,0001 |
| n40 | gpt-6-sol vs Qwen2.5-VL-3B | 6 | 2 | eksak binomial | 0,2891 |
| n40 | gpt-6-sol vs InternVL3-2B | 13 | 20 | chi-kuadrat terkoreksi | 0,2963 |
| n40 | Qwen2.5-VL-3B + LoRA vs gpt-6-sol | 22 | 5 | chi-kuadrat terkoreksi | 0,0021 |

## Tujuan 2(b) — Evaluasi otomatis deskripsi (acuan: 5 deskripsi Sesi A)

Huruf kecil, tanpa stemmer/sinonim (METEOR = exact match), ROUGE = F1 terbaik antaracuan; BLEU korpus.

| Sistem | Protokol | BLEU-1 | BLEU-4 | METEOR | ROUGE-1 | ROUGE-2 | ROUGE-L |
|---|---|---|---|---|---|---|---|
| Qwen2.5-VL-3B | vs 5 acuan | 0,722 | 0,113 | 0,184 | 0,299 | 0,076 | 0,257 |
| Qwen2.5-VL-3B | vs 4 acuan (rerata 5 lipatan) | 0,661 | 0,094 | 0,178 | 0,290 | 0,070 | 0,249 |
| InternVL3-2B | vs 5 acuan | 0,702 | 0,069 | 0,152 | 0,263 | 0,069 | 0,223 |
| InternVL3-2B | vs 4 acuan (rerata 5 lipatan) | 0,626 | 0,053 | 0,144 | 0,251 | 0,059 | 0,212 |
| gpt-6-sol | vs 5 acuan | 0,628 | 0,048 | 0,159 | 0,265 | 0,042 | 0,201 |
| gpt-6-sol | vs 4 acuan (rerata 5 lipatan) | 0,578 | 0,036 | 0,152 | 0,255 | 0,037 | 0,193 |
| Manusia (rerata) | vs 4 acuan | 0,495 | 0,120 | 0,305 | 0,346 | 0,120 | 0,249 |

Perbandingan setara: baris 'vs 4 acuan' (model) dibandingkan dengan 'Manusia (rerata)'. Rincian per evaluator: `T2b_metrik_teks.csv`.

| Sistem | Kalimat unik /40 | Rerata kata | Memuat 5-gram prompt | Proporsi 4-gram dari prompt |
|---|---|---|---|---|
| Qwen2.5-VL-3B | 4 | 16,2 | 0,23 | 0,10 |
| InternVL3-2B | 6 | 16,6 | 0,00 | 0,07 |
| gpt-6-sol | 40 | 17,3 | 0,03 | 0,00 |
| Manusia EVAL01 | 12 | 63,2 | 1,00 | 0,05 |
| Manusia EVAL02 | 20 | 12,5 | 0,00 | 0,00 |
| Manusia EVAL03 | 29 | 5,3 | 0,00 | 0,00 |
| Manusia EVAL04 | 3 | 11,3 | 0,00 | 0,00 |
| Manusia EVAL05 | 24 | 51,9 | 1,00 | 0,31 |

## Tujuan 2(c) — Evaluasi manusia QUEST (Sesi B)

| Model | Akurasi [95%] | Relevansi [95%] | Kepuasan [95%] |
|---|---|---|---|
| Qwen2.5-VL-3B | 2,46 [2,22–2,71] | 3,10 [2,95–3,25] | 2,49 [2,30–2,67] |
| InternVL3-2B | 3,02 [2,73–3,31] | 3,17 [3,02–3,33] | 2,79 [2,58–2,99] |
| gpt-6-sol | 3,52 [3,24–3,81] | 3,87 [3,68–4,06] | 3,53 [3,26–3,79] |

Krippendorff α (5 penilai × 120 unit): Akurasi ordinal 0,256 (interval 0,257); Relevansi ordinal -0,030 (interval -0,029); Kepuasan ordinal 0,228 (interval 0,233). Ambang: ≥ 0,800 andal; 0,667–0,800 tentatif; < 0,667 tidak memadai.

Pelengkap (tidak direncanakan di Bab III; boleh dipakai sebagai pendukung): Friedman per kriteria, blok = bangunan: Akurasi χ² = 26,72, p < 0,0001; Relevansi χ² = 24,63, p < 0,0001; Kepuasan χ² = 31,85, p < 0,0001. Wilcoxon berpasangan (Holm) di `T2c_uji_perbedaan_pelengkap.csv`.


## Ukuran pendukung — kepatuhan format dan komputasi

| Model | Kelas terurai | Tingkat urai kelas | Kelas tidak sah | Fitur lengkap sah | Tingkat urai fitur | s/panggilan kelas | s/bangunan | GPU puncak (GB) |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-VL-3B | 1,000 | {"pagar_kode": 400} | 0,000 | 1,000 (n=400) | {"pagar_kode": 400} | 1,99 | 8,97 | 8,18 |
| InternVL3-2B | 1,000 | {"pagar_kode": 400} | 0,000 | 1,000 (n=400) | {"pagar_kode": 400} | 3,05 | 11,83 | 4,72 |
| Qwen2.5-VL-3B + LoRA | 1,000 | {"langsung": 400} | 0,000 | 0,000 (n=40) | {"langsung": 40} | 1,82 | – | 8,62 |
| gpt-6-sol | 1,000 | {"langsung": 40} | 0,050 | 1,000 (n=40) | {"langsung": 40} | 6,12 | 15,54 | – |

Tingkat urai: 'langsung' = JSON terbaca apa adanya; 'pagar_kode' = JSON dibungkus blok kode markdown lalu dilepas pengurai (bukan kesalahan isi); 'gagal' = tidak ada objek JSON yang dapat diurai.

gpt-6-sol: latensi API (jaringan + antrean + server), tidak setara dengan waktu GPU lokal. LoRA: waktu pelatihan 75,6 menit (T4).

