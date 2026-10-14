/* Prototipe penyaji informasi kerusakan bangunan pascabencana (Palu 2018).
   Semua isi berasal dari data/data.js yang disusun skrip 16_bangun_prototipe.py dari run yang sudah
   dievaluasi. Aplikasi tidak menjalankan model dan tidak membangkitkan jawaban baru. */
(function () {
  "use strict";
  const D = window.DATA;
  const B = D.bangunan;
  const PER_KODE = Object.fromEntries(B.map((b) => [b.kode, b]));
  const KELAS = ["tidak_rusak", "rusak", "hancur"];
  const NAMA_KELAS = {
    tidak_rusak: "Tidak rusak",
    rusak: "Rusak",
    hancur: "Hancur",
  };
  const NAMA_XBD = {
    tidak_rusak: "no-damage",
    rusak: "major-damage",
    hancur: "destroyed",
  };
  const gaya = getComputedStyle(document.documentElement);
  const WARNA = Object.fromEntries(
    KELAS.map((k) => [k, gaya.getPropertyValue("--k-" + k).trim()]),
  );
  const FITUR = [
    "keutuhan_atap",
    "puing_sekitar",
    "wujud_bangunan",
    "sedimen_lumpur",
  ];
  const angka = (x, d = 0) =>
    Number(x).toLocaleString("id-ID", {
      minimumFractionDigits: d,
      maximumFractionDigits: d,
    });
  const persen = (x) => angka(x * 100, 0) + "%";
  const esc = (s) =>
    String(s ?? "").replace(
      /[&<>"]/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c],
    );
  const nilaiFitur = (f, v) =>
    v ? (D.label_level[f]?.[v] ?? v.replace(/_/g, " ")) : "tidak terbaca";
  const kodeAkhir = "PL-" + String(B.length).padStart(3, "0");
  const normKode = (s) => {
    const m = String(s || "")
      .trim()
      .toUpperCase()
      .match(/^(?:PL)?[\s-]*0*(\d{1,3})$/);
    return m ? "PL-" + String(Number(m[1])).padStart(3, "0") : null;
  };
  // berapa kali tiap kalimat deskripsi dipakai (untuk catatan keseragaman)
  const FREK_DESK = {};
  B.forEach((b) => {
    if (b.deskripsi) FREK_DESK[b.deskripsi] = (FREK_DESK[b.deskripsi] || 0) + 1;
  });

  /* ---------------------------------------------------------------- ikon (garis sederhana, tanpa berkas luar) */
  const JALUR = {
    meninggal:
      '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m17 8 5 5M22 8l-5 5"/>',
    hilang:
      '<circle cx="9" cy="7" r="4"/><path d="M3 21v-2a4 4 0 0 1 4-4h4"/><path d="M16.5 13.5a2.5 2.5 0 1 1 3 2.45V17"/><path d="M19.5 20.5h.01"/>',
    pengungsi:
      '<path d="M3.5 21 14 3"/><path d="M20.5 21 10 3"/><path d="M15.5 21 12 15l-3.5 6"/><path d="M2 21h20"/>',
    kerugian:
      '<rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>',
    bangunan:
      '<rect width="16" height="20" x="4" y="2" rx="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01"/>',
    tidak_rusak:
      '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
    rusak:
      '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    hancur:
      '<path d="M7.86 2h8.28L22 7.86v8.28L16.14 22H7.86L2 16.14V7.86z"/><path d="m15 9-6 6M9 9l6 6"/>',
    cocok:
      '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
  };
  const ikon = (n) =>
    `<svg class="ikon" viewBox="0 0 24 24" aria-hidden="true">${JALUR[n]}</svg>`;

  /* ---------------------------------------------------------------- tab */
  const tabs = document.querySelectorAll(".tab button");
  function bukaTab(nama) {
    tabs.forEach((b) =>
      b.setAttribute("aria-selected", String(b.dataset.tab === nama)),
    );
    document
      .querySelectorAll(".panel")
      .forEach((p) => p.classList.toggle("aktif", p.id === "tab-" + nama));
    if (nama === "dasbor" && peta) setTimeout(() => peta.invalidateSize(), 50);
    window.scrollTo({ top: 0 });
  }
  tabs.forEach((b) =>
    b.addEventListener("click", () => bukaTab(b.dataset.tab)),
  );
  const gulirKe = (el) => {
    if (window.innerWidth < 900)
      el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  /* ---------------------------------------------------------------- informasi umum (web story) */
  function bangunCerita() {
    const m = D.metrik,
      k = D.konteks;
    const hitung = (kls) => B.filter((b) => b.kelas === kls).length;
    const cm = m.matriks_lora;
    const baris = KELAS.map(
      (y, i) =>
        `<tr><th>${NAMA_XBD[y]}</th>${cm[i].map((v, j) => `<td class="${i === j ? "diag" : ""}">${v}</td>`).join("")}</tr>`,
    ).join("");
    const contoh = D.contoh
      .map((c) => {
        const b = PER_KODE[c];
        return `<figure><img src="${b.img}" alt="Citra sebelum dan sesudah bencana bangunan ${b.kode}" loading="lazy">
        <figcaption>${b.kode} · label xBD <b>${NAMA_XBD[b.xbd]}</b> · kiri sebelum, kanan sesudah</figcaption></figure>`;
      })
      .join("");
    document.getElementById("cerita").innerHTML = `
      <div class="adegan"><div class="nomor">1 · Kejadian</div>
        <h2>Palu, 28 September 2018</h2>
        <p>Gempa bumi yang disusul tsunami dan likuefaksi melanda Kota Palu dan sekitarnya. Dalam beberapa jam, puluhan ribu bangunan rusak atau hilang, dan petugas harus segera tahu bangunan mana yang terdampak.</p>
        <div class="angka-besar">
          <div>${ikon("meninggal")}<b>${angka(k.meninggal)}</b><span>jiwa meninggal</span></div>
          <div>${ikon("hilang")}<b>${angka(k.hilang)}</b><span>jiwa hilang</span></div>
          <div>${ikon("pengungsi")}<b>${angka(k.pengungsi)}</b><span>pengungsi</span></div>
          <div>${ikon("kerugian")}<b>Rp${angka(k.kerugian_triliun, 2)} T</b><span>kerusakan dan kerugian</span></div>
        </div>
        <p class="sumber">Sumber: ${esc(k.sumber)}</p>
      </div>
      <div class="adegan"><div class="nomor">2 · Data</div>
        <h2>Citra satelit sebelum dan sesudah</h2>
        <p>Prototipe ini memakai citra satelit resolusi sangat tinggi dari dataset xBD (sekitar 0,5 meter per piksel), direkam ${esc(D.meta.tanggal_pra)} dan ${esc(D.meta.tanggal_pasca)}. Dari ${angka(D.meta.kerangka)} bangunan Palu berlabel, ${angka(B.length)} bangunan sampel disajikan di sini. Bangunan yang dinilai selalu berada di tengah kotak magenta dengan bidik silang.</p>
        <div class="contoh">${contoh}</div>
      </div>
      <div class="adegan"><div class="nomor">3 · Cara kerja</div>
        <h2>Dari citra ke informasi kerusakan</h2>
        <ol class="langkah">
          <li>Empat tanda kerusakan yang tampak dari atas dipilih oleh peneliti dan ahli BPS: <b>keutuhan atap, puing di sekitar bangunan, wujud bangunan, dan sedimen/lumpur</b>.</li>
          <li>Small Vision-Language Model membaca pasangan citra dan menjawab keempat tanda itu beserta satu kalimat deskripsi.</li>
          <li>Kelas kerusakan (tidak rusak, rusak, hancur) ditentukan dari citra sesudah bencana.</li>
          <li>Semua hasil dihitung lebih dulu, dievaluasi, lalu disajikan di aplikasi ini.</li>
        </ol>
        <p class="kecil">Kelas pada aplikasi berasal dari ${esc(D.meta.sumber_kelas)}. Tanda kerusakan dan deskripsi berasal dari ${esc(D.meta.sumber_fitur)}. Pemilihan ini mengikuti aturan yang ditetapkan sebelum hasil dibaca: kelas dari model dengan akurasi seimbang tertinggi, tanda dan deskripsi dari model dengan skor akurasi penilaian manusia tertinggi.</p>
      </div>
      <div class="adegan"><div class="nomor">4 · Hasil</div>
        <h2>Seberapa sesuai dengan label xBD?</h2>
        <p>Tanpa pelatihan tambahan, kedua model kecil menjawab kelas yang hampir selalu sama untuk semua bangunan. Setelah dilatih ulang dengan LoRA, model mulai membedakan ketiga kelas: akurasi seimbang ${angka(m.lora_bacc, 2)} (tebakan acak = 0,33) pada ${angka(m.n)} bangunan uji.</p>
        <table class="matriks"><thead><tr><th>Label xBD ↓ / Model →</th><th>tidak rusak</th><th>rusak</th><th>hancur</th></tr></thead><tbody>${baris}</tbody></table>
        <p>Kelas <b>rusak</b> paling sulit: dari ${angka(cm[1].reduce((a, c) => a + c, 0))} bangunan major-damage, hanya ${angka(cm[1][1])} yang dikenali sebagai rusak. Bangunan <b>hancur</b> dan <b>tidak rusak</b> jauh lebih sering tepat.</p>
        <p class="kecil">Sebaran kelas pada aplikasi: tidak rusak ${hitung("tidak_rusak")}, rusak ${hitung("rusak")}, hancur ${hitung("hancur")} bangunan.</p>
      </div>
      <div class="adegan"><div class="nomor">5 · Batasan</div>
        <h2>Yang perlu diingat saat membaca hasil</h2>
        <ul class="poin">
          <li>Informasi pada prototipe ini dimaksudkan untuk membantu menentukan bangunan mana yang perlu diperiksa lebih dahulu. Informasi ini <b>tidak menggantikan pemeriksaan langsung di lapangan</b> oleh petugas, dan kelas dari model dapat keliru.</li>
          <li>Angka pada prototipe menggambarkan ${angka(B.length)} bangunan sampel, bukan seluruh bangunan di Kota Palu, sehingga tidak dapat dipakai untuk menaksir jumlah total bangunan rusak.</li>
          <li>Tanda kerusakan dan deskripsi hampir seragam: ${angka(m.deskripsi_sama)} dari ${angka(B.length)} bangunan memiliki kalimat deskripsi yang persis sama.</li>
          <li>Kelas dan tanda kerusakan berasal dari dua model yang berbeda, sehingga keduanya dapat tidak sejalan pada bangunan yang sama. Label xBD selalu ditampilkan sebagai pembanding.</li>
        </ul>
      </div>
      <div class="adegan"><div class="nomor">6 · Tentang prototipe</div>
        <h2>Seputar Prototipe dan Komponennya</h2>
        <ul class="poin">
          <li>Citra dan label pembanding: dataset xBD/xView2 (Gupta dkk., 2019), citra WorldView-2 Maxar melalui program Open Data.</li>
          <li>Kelas kerusakan: ${esc(D.meta.sumber_kelas)}, run <code>${esc(D.meta.run_kelas)}</code>.</li>
          <li>Tanda kerusakan dan deskripsi: ${esc(D.meta.sumber_fitur)}, run <code>${esc(D.meta.run_fitur)}</code>.</li>
          <li>Data prototipe disusun pada ${esc(D.meta.dibangun)} dari folder analisis <code>${esc(m.folder_analisis)}</code>.</li>
          <li>Peta dasar: © kontributor OpenStreetMap, dan © Esri. Citra dasar Esri bukan citra yang dipakai dalam penelitian.</li>
          <li>Prototipe ini disusun sebagai bagian dari skripsi Rizky Alif Ichwanto (4SD2), Program Studi D-IV Komputasi Statistik, Politeknik Statistika STIS, tahun akademik 2025/2026.</li>
        </ul>
      </div>
      <div class="adegan"><div class="nomor">7 · Identitas penyusun</div>
        <h2>Identitas Skripsi</h2>
        <p>Prototipe ini merupakan artefak dari skripsi berikut.</p>
        <dl class="identitas-skripsi">
          <dt>Nama</dt><dd>Rizky Alif Ichwanto</dd>
          <dt>NIM</dt><dd>222212857</dd>
          <dt>Kelas</dt><dd>4SD2</dd>
          <dt>Program studi</dt><dd>D-IV Komputasi Statistik, peminatan Sains Data, Politeknik Statistika STIS</dd>
          <dt>Tahun lulus</dt><dd>2026</dd>
          <dt>Judul skripsi</dt><dd>Ekstraksi Informasi Kerusakan Bangunan Pascabencana Menggunakan <i>Small Vision-Language Model</i> pada Citra Satelit Resolusi Sangat Tinggi (Studi Kasus: Bencana Gempa dan Tsunami Palu 2018)</dd>
          <dt>Dosen pembimbing</dt><dd>Dr. Eng. Arie Wahyu Wijayanto, S.S.T., M.T.</dd>
        </dl>
      </div>
      <div class="adegan ajakan">
        <h2>Jelajahi sendiri</h2>
        <p>Lihat sebaran bangunan pada peta, saring menurut kelas, atau ajukan pertanyaan tentang satu bangunan.</p>
        <p><button class="tombol" data-ke="dasbor">Buka Dashboard</button> <button class="tombol-sekunder" data-ke="tanya">Buka Tanya-Jawab</button></p>
      </div>`;
    document
      .querySelectorAll("[data-ke]")
      .forEach((b) => b.addEventListener("click", () => bukaTab(b.dataset.ke)));
  }

  /* ---------------------------------------------------------------- dashboard */
  const fKelas = document.getElementById("f-kelas"),
    fXbd = document.getElementById("f-xbd"),
    fCocok = document.getElementById("f-cocok"),
    fKode = document.getElementById("f-kode"),
    fGrid = document.getElementById("f-grid"),
    infoSaring = document.getElementById("info-saring");
  let peta = null,
    penanda = {},
    lapisGrid = null,
    terpilih = null,
    daftarKini = B;

  function tersaring() {
    return B.filter(
      (b) =>
        (!fKelas.value || b.kelas === fKelas.value) &&
        (!fXbd.value || b.xbd === fXbd.value) &&
        (!fCocok.value || (fCocok.value === "ya") === (b.kelas === b.xbd)),
    );
  }

  function kpi(list) {
    const n = list.length,
      cocok = list.filter((b) => b.kelas === b.xbd).length;
    const kepala = (ik, cls, teks) =>
      `<div class="kpi-kepala"><span class="kpi-ikon ${cls}">${ikon(ik)}</span><div class="ket">${teks}</div></div>`;
    const kotak = KELAS.map((k) => {
      const j = list.filter((b) => b.kelas === k).length;
      return `<div class="kpi">${kepala(k, k, "Kelas model: " + NAMA_KELAS[k])}<div class="angka">${angka(j)}</div>
        <div class="batang"><span style="width:${n ? (j / n) * 100 : 0}%;background:${WARNA[k]}"></span></div></div>`;
    }).join("");
    document.getElementById("kpi").innerHTML =
      `<div class="kpi">${kepala("bangunan", "", "Bangunan ditampilkan")}<div class="angka">${angka(n)}</div><div class="ket">dari ${angka(B.length)} bangunan sampel</div></div>` +
      kotak +
      `<div class="kpi">${kepala("cocok", "cocok", "Sesuai label xBD")}<div class="angka">${n ? persen(cocok / n) : "–"}</div><div class="ket">${angka(cocok)} dari ${angka(n)} bangunan</div></div>`;
  }

  function daftar(list) {
    document.getElementById("jumlah-daftar").textContent =
      `${angka(list.length)} bangunan`;
    document.getElementById("tbody").innerHTML =
      list
        .map(
          (b) =>
            `<tr data-kode="${b.kode}" class="${terpilih === b.kode ? "terpilih" : ""}"><td><b>${b.kode}</b></td>
        <td><span class="pill ${b.kelas}">${NAMA_KELAS[b.kelas]}</span></td><td>${NAMA_XBD[b.xbd]}</td>
        ${FITUR.map((f) => `<td>${esc(nilaiFitur(f, b.fitur[f]))}</td>`).join("")}</tr>`,
        )
        .join("") ||
      `<tr><td colspan="7" style="color:var(--tinta-3)">Tidak ada bangunan yang cocok dengan penyaring.</td></tr>`;
  }

  function isiPilihanKode(sel, list, teksKosong) {
    const lama = sel.value;
    sel.innerHTML =
      `<option value="">${teksKosong}</option>` +
      list
        .map(
          (b) =>
            `<option value="${b.kode}">${b.kode} · ${NAMA_KELAS[b.kelas]}</option>`,
        )
        .join("");
    if (list.some((b) => b.kode === lama)) sel.value = lama;
  }

  function catatanSeragam(b) {
    const n = FREK_DESK[b.deskripsi] || 0;
    return n > 1
      ? `<div class="seragam">Kalimat deskripsi ini sama persis untuk ${angka(n)} dari ${angka(B.length)} bangunan. Model cenderung memberi deskripsi yang seragam, sehingga deskripsi belum membedakan kondisi tiap bangunan.</div>`
      : "";
  }

  function detailHTML(b) {
    const cocok = b.kelas === b.xbd;
    return `<div class="kartu-judul"><span class="kode-besar">${b.kode}</span><span class="kecil">${angka(b.lat, 5)}, ${angka(b.lon, 5)}</span></div>
      <img src="${b.img}" alt="Citra sebelum dan sesudah bencana bangunan ${b.kode}">
      <div class="cap"><span>Sebelum (${esc(D.meta.tanggal_pra)})</span><span>Sesudah (${esc(D.meta.tanggal_pasca)})</span></div>
      <div class="baris-kelas">
        <div><div class="lbl">Kelas model</div><span class="pill ${b.kelas}">${NAMA_KELAS[b.kelas]}</span></div>
        <div><div class="lbl">Label xBD (pembanding)</div><b>${NAMA_XBD[b.xbd]}</b></div>
      </div>
      <div class="${cocok ? "cocok-ya" : "cocok-tidak"}">${cocok ? "✓ Kelas model sesuai dengan label xBD" : "✗ Kelas model tidak sesuai dengan label xBD"}</div>
      <table class="tabel-fitur">${FITUR.map((f) => `<tr><td>${esc(D.label_fitur[f])}</td><td>${esc(nilaiFitur(f, b.fitur[f]))}</td></tr>`).join("")}</table>
      <div class="deskripsi">${esc(b.deskripsi || "Deskripsi tidak tersedia.")}</div>
      ${catatanSeragam(b)}
      <div class="catatan">Kelas: ${esc(D.meta.sumber_kelas)}. Tanda kerusakan dan deskripsi: ${esc(D.meta.sumber_fitur)}. Keduanya dihitung sebelumnya dan dapat tidak sejalan.</div>
      <div class="aksi-detail"><button class="tombol-sekunder" type="button" id="ke-tanya">Tanyakan bangunan ini</button></div>`;
  }

  function pilih(kode, geser = true, gulir = false) {
    const b = PER_KODE[kode];
    if (!b) return;
    terpilih = kode;
    if (fKode.value !== kode)
      fKode.value = [...fKode.options].some((o) => o.value === kode)
        ? kode
        : "";
    const det = document.getElementById("detail");
    det.innerHTML = detailHTML(b);
    document.getElementById("ke-tanya").addEventListener("click", () => {
      setBgn(kode, true);
      bukaTab("tanya");
    });
    document
      .querySelectorAll("#tbody tr")
      .forEach((tr) =>
        tr.classList.toggle("terpilih", tr.dataset.kode === kode),
      );
    Object.entries(penanda).forEach(
      ([k, mk]) =>
        mk.setStyle &&
        mk.setStyle({
          weight: k === kode ? 3 : 1,
          color: k === kode ? "#1b1b1a" : "#ffffff",
        }),
    );
    if (peta && penanda[kode]) {
      penanda[kode].bringToFront();
      if (geser) peta.setView([b.lat, b.lon], Math.max(peta.getZoom(), 16));
    }
    document.querySelectorAll("#peta circle").forEach((c) => {
      const y = c.dataset.kode === kode;
      c.setAttribute("stroke", y ? "#1b1b1a" : "#fff");
      c.setAttribute("stroke-width", y ? 3 : 1);
      if (y) c.parentNode.appendChild(c);
    });
    if (gulir) gulirKe(det);
  }

  /* ringkasan per kotak grid ±1 km (0,01 derajat); bukan batas administrasi */
  const SEL = 0.01;
  function gambarGrid(list) {
    if (!peta) return;
    if (lapisGrid) {
      lapisGrid.remove();
      lapisGrid = null;
    }
    if (!fGrid.checked) return;
    const sel = {};
    list.forEach((b) => {
      const i = Math.floor(b.lat / SEL),
        j = Math.floor(b.lon / SEL),
        kunci = i + ":" + j;
      sel[kunci] = sel[kunci] || {
        i,
        j,
        n: 0,
        tidak_rusak: 0,
        rusak: 0,
        hancur: 0,
      };
      sel[kunci].n++;
      sel[kunci][b.kelas]++;
    });
    lapisGrid = L.layerGroup(
      Object.values(sel).map((s) => {
        const dominan = KELAS.reduce(
          (a, k) => (s[k] > s[a] ? k : a),
          "tidak_rusak",
        );
        return L.rectangle(
          [
            [s.i * SEL, s.j * SEL],
            [(s.i + 1) * SEL, (s.j + 1) * SEL],
          ],
          {
            color: WARNA[dominan],
            weight: 1.5,
            fillColor: WARNA[dominan],
            fillOpacity: 0.28,
            interactive: true,
          },
        ).bindTooltip(
          `<b>Kotak grid ±1 km</b><br>${s.n} bangunan sampel<br>tidak rusak ${s.tidak_rusak} · rusak ${s.rusak} · hancur ${s.hancur}<br><span style="color:#777">kelas menurut model</span>`,
          { sticky: true },
        );
      }),
    ).addTo(peta);
    Object.values(penanda).forEach(
      (mk) => peta.hasLayer(mk) && mk.bringToFront(),
    );
  }

  function segarkan() {
    const list = tersaring();
    daftarKini = list;
    kpi(list);
    daftar(list);
    isiPilihanKode(fKode, list, "Pilih kode…");
    const bagian = [];
    if (fKelas.value)
      bagian.push(`kelas model ${NAMA_KELAS[fKelas.value].toLowerCase()}`);
    if (fXbd.value) bagian.push(`label xBD ${NAMA_XBD[fXbd.value]}`);
    if (fCocok.value)
      bagian.push(
        fCocok.value === "ya" ? "sesuai label xBD" : "tidak sesuai label xBD",
      );
    infoSaring.textContent =
      (bagian.length
        ? `Menampilkan ${angka(list.length)} bangunan dengan ${bagian.join(", ")}.`
        : `Menampilkan seluruh ${angka(list.length)} bangunan.`) +
      " Penyaring langsung diterapkan setiap pilihan diubah.";
    infoSaring.classList.add("kilat");
    setTimeout(() => infoSaring.classList.remove("kilat"), 700);
    const ada = new Set(list.map((b) => b.kode));
    if (peta) {
      Object.entries(penanda).forEach(([k, mk]) => {
        if (ada.has(k)) mk.addTo(peta);
        else mk.remove();
      });
      gambarGrid(list);
      if (fKelas.value || fXbd.value || fCocok.value) {
        if (list.length) {
          peta.fitBounds(L.latLngBounds(list.map((b) => [b.lat, b.lon])), {
            padding: [20, 20],
            maxZoom: 16,
          });
        }
      } else {
        peta.setView([-0.9, 119.87], 10);
      }
    } else {
      document
        .querySelectorAll("#peta circle")
        .forEach(
          (c) => (c.style.display = ada.has(c.dataset.kode) ? "" : "none"),
        );
    }
  }

  function bangunPeta() {
    document.getElementById("legenda").innerHTML = KELAS.map(
      (k) =>
        `<span><i style="background:${WARNA[k]}"></i>${NAMA_KELAS[k]}</span>`,
    ).join("");
    const catatan = document.getElementById("catatan-peta");
    catatan.textContent =
      "Kotak grid dibuat dari koordinat bangunan sampel (±1 km per sisi), bukan batas kelurahan atau kecamatan.";
    if (window.L) {
      peta = L.map("peta", { preferCanvas: true });
      const atribusiOsm =
        '&copy; kontributor <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
      const jalan = L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        {
          subdomains: "abcd",
          maxZoom: 20,
          attribution:
            atribusiOsm +'',
        },
      );
      const jalanEsri = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        { maxZoom: 19, attribution: "Peta dasar &copy; Esri" },
      );
      const citra = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 19,
          attribution: "Citra dasar &copy; Esri (bukan citra penelitian)",
        },
      );
      jalan.addTo(peta);
      // bila penyedia peta jalan utama menolak, beralih otomatis ke penyedia cadangan
      let gagal = 0,
        muat = 0;
      jalan.on("tileload", () => muat++);
      jalan.on("tileerror", () => {
        if (++gagal >= 4 && muat === 0 && peta.hasLayer(jalan)) {
          peta.removeLayer(jalan);
          jalanEsri.addTo(peta);
          catatan.textContent =
            "Peta jalan utama tidak dapat dimuat, sehingga peta jalan cadangan (Esri) dipakai. " +
            catatan.textContent;
        }
      });
      jalanEsri.addTo(peta);
      L.control
        .layers({
          "Peta jalan Esri": jalanEsri,
          "Peta dasar Esri": citra,
        })
        .addTo(peta);
      B.forEach((b) => {
        penanda[b.kode] = L.circleMarker([b.lat, b.lon], {
          radius: 6,
          weight: 1,
          color: "#ffffff",
          fillColor: WARNA[b.kelas],
          fillOpacity: 0.95,
        })
          .bindTooltip(`${b.kode} · ${NAMA_KELAS[b.kelas]}`)
          .on("click", () => pilih(b.kode, false, true))
          .addTo(peta);
      });
      peta.setView([-0.9, 119.87], 10);
    } else {
      // cadangan tanpa internet: peta titik sederhana
      const lon = B.map((b) => b.lon),
        lat = B.map((b) => b.lat);
      const [x0, x1, y0, y1] = [
        Math.min(...lon),
        Math.max(...lon),
        Math.min(...lat),
        Math.max(...lat),
      ];
      const W = 600,
        H = 470,
        pad = 20,
        s = Math.min((W - 2 * pad) / (x1 - x0), (H - 2 * pad) / (y1 - y0));
      document.getElementById("peta").innerHTML =
        `<svg viewBox="0 0 ${W} ${H}" width="100%" height="100%">${B.map(
          (b) =>
            `<circle data-kode="${b.kode}" cx="${pad + (b.lon - x0) * s}" cy="${H - pad - (b.lat - y0) * s}" r="5" fill="${WARNA[b.kelas]}" stroke="#fff" style="cursor:pointer"><title>${b.kode}</title></circle>`,
        ).join("")}</svg>`;
      catatan.textContent =
        "Peta dasar tidak dapat dimuat (tanpa internet); titik digambar menurut koordinat. Ringkasan grid memerlukan peta dasar.";
      fGrid.disabled = true;
      document
        .querySelectorAll("#peta circle")
        .forEach((c) =>
          c.addEventListener("click", () => pilih(c.dataset.kode, true, true)),
        );
    }
  }

  function unduhCSV() {
    const kolom = [
      "kode",
      "lintang",
      "bujur",
      "kelas_model",
      "label_xbd",
      "sesuai_label_xbd",
      ...FITUR,
      "deskripsi",
    ];
    const kutip = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const baris = daftarKini.map((b) =>
      [
        b.kode,
        b.lat,
        b.lon,
        NAMA_KELAS[b.kelas],
        NAMA_XBD[b.xbd],
        b.kelas === b.xbd ? "ya" : "tidak",
        ...FITUR.map((f) => nilaiFitur(f, b.fitur[f])),
        b.deskripsi,
      ]
        .map(kutip)
        .join(";"),
    );
    const isi = "﻿" + [kolom.join(";"), ...baris].join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(
      new Blob([isi], { type: "text/csv;charset=utf-8" }),
    );
    a.download = `bangunan_palu2018_${daftarKini.length}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    infoSaring.textContent = `Berkas CSV berisi ${angka(daftarKini.length)} bangunan sesuai penyaring sedang diunduh.`;
  }

  [fKelas, fXbd, fCocok].forEach((el) =>
    el.addEventListener("change", segarkan),
  );
  fGrid.addEventListener("change", () => gambarGrid(daftarKini));
  fKode.addEventListener("change", () => {
    if (fKode.value) {
      pilih(fKode.value, true, true);
      infoSaring.textContent = `Bangunan ${fKode.value} dipilih dan ditampilkan.`;
    }
  });
  document.getElementById("f-unduh").addEventListener("click", unduhCSV);
  document.getElementById("f-reset").addEventListener("click", () => {
    fKelas.value = fXbd.value = fCocok.value = "";
    fGrid.checked = false;
    segarkan();
  });
  document.getElementById("tbody").addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-kode]");
    if (tr) pilih(tr.dataset.kode, true, true);
  });

  /* ---------------------------------------------------------------- tanya-jawab (aturan tetap) */
  let tBgn = null;
  const obrolan = document.getElementById("obrolan");
  const tKode = document.getElementById("t-kode");
  const ASAL = `Sumber: kelas dari ${D.meta.sumber_kelas}; tanda dan deskripsi dari ${D.meta.sumber_fitur}; label xBD sebagai pembanding.`;
  const PERTANYAAN = [
    {
      id: "kelas",
      grup: "Tentang bangunan terpilih",
      teks: "Apa kelas kerusakan bangunan ini?",
      pola: /kelas|tingkat kerusakan|seberapa (rusak|parah)|parah|rusak(kah)?\b|kondisi (bangunan|umum|keseluruhan)/,
    },
    {
      id: "atap",
      grup: "Tentang bangunan terpilih",
      teks: "Bagaimana kondisi atapnya?",
      pola: /atap/,
    },
    {
      id: "puing",
      grup: "Tentang bangunan terpilih",
      teks: "Apakah ada puing di sekitarnya?",
      pola: /puing|reruntuh|serpih|material|berserak/,
    },
    {
      id: "wujud",
      grup: "Tentang bangunan terpilih",
      teks: "Bagaimana wujud bangunannya?",
      pola: /wujud|bentuk|tapak|struktur|garis batas|runtuh/,
    },
    {
      id: "sedimen",
      grup: "Tentang bangunan terpilih",
      teks: "Apakah ada lumpur atau sedimen?",
      pola: /lumpur|sedimen|endap|tertimbun/,
    },
    {
      id: "deskripsi",
      grup: "Tentang bangunan terpilih",
      teks: "Apa deskripsi singkat bangunan ini?",
      pola: /deskripsi|jelaskan|gambarkan|ringkas|ceritakan/,
    },
    {
      id: "citra",
      grup: "Tentang bangunan terpilih",
      teks: "Tampilkan citra bangunan ini",
      pola: /citra|gambar|foto|tampilkan|lihat/,
    },
    {
      id: "cocok",
      grup: "Tentang bangunan terpilih",
      teks: "Apakah hasil model sesuai dengan label xBD?",
      pola: /xbd|label|sesuai|cocok|benar(kah)?/,
    },
    {
      id: "jumlah",
      grup: "Pertanyaan umum",
      teks: "Berapa banyak bangunan per kelas kerusakan?",
      pola: /(berapa|jumlah|banyak(nya)?|total).*(bangunan|rumah|kelas|hancur|rusak)|(bangunan|rumah|kelas).*(berapa|jumlah|total)/,
    },
    {
      id: "andal",
      grup: "Pertanyaan umum",
      teks: "Seberapa andal hasil ini?",
      pola: /andal|akurasi|akurat|seberapa (baik|tepat)|percaya|valid|tepat(kah)?/,
    },
    {
      id: "model",
      grup: "Pertanyaan umum",
      teks: "Model apa yang dipakai?",
      pola: /model|svlm|qwen|internvl|\bai\b|kecerdasan/,
    },
    {
      id: "data",
      grup: "Pertanyaan umum",
      teks: "Data apa yang dipakai?",
      pola: /data|sumber|dataset|kapan|tanggal|resolusi/,
    },
  ];
  const PER_ID = Object.fromEntries(PERTANYAAN.map((p) => [p.id, p]));
  const URUTAN_COCOK = [
    "jumlah",
    "cocok",
    "andal",
    "deskripsi",
    "citra",
    "atap",
    "puing",
    "sedimen",
    "wujud",
    "kelas",
    "model",
    "data",
  ];
  const DI_LUAR =
    /biaya|harga|rupiah|anggaran|korban|pemilik|penghuni|alamat|asuransi|ganti rugi|bantuan/;
  const PERLU_BGN = new Set([
    "kelas",
    "atap",
    "puing",
    "wujud",
    "sedimen",
    "deskripsi",
    "citra",
    "cocok",
  ]);
  let sudahDitanya = new Set();

  function gelembung(teks, siapa, asal, ekor = "") {
    const d = document.createElement("div");
    d.className = "gelembung " + siapa;
    d.innerHTML =
      teks + (asal ? `<span class="asal">${esc(asal)}</span>` : "") + ekor;
    obrolan.appendChild(d);
    d.querySelectorAll("[data-q]").forEach((b) =>
      b.addEventListener("click", () =>
        tanya(PER_ID[b.dataset.q].teks, b.dataset.q),
      ),
    );
    d.querySelectorAll("[data-semua]").forEach((b) =>
      b.addEventListener("click", tampilkanSemuaSaran),
    );
    d.querySelectorAll("[data-dasbor]").forEach((b) =>
      b.addEventListener("click", () => {
        const kode = b.dataset.dasbor;
        if (!daftarKini.some((x) => x.kode === kode)) {
          fKelas.value = fXbd.value = fCocok.value = "";
          segarkan();
        }
        bukaTab("dasbor");
        setTimeout(() => pilih(kode), 80);
      }),
    );
    obrolan.scrollTop = obrolan.scrollHeight;
    return d;
  }
  const chip = (id) =>
    `<button type="button" data-q="${id}">${esc(PER_ID[id].teks)}</button>`;

  function blokSaran(ids, judul = "Rekomendasi Pertanyaan", semua = true) {
    return `<span class="saran-judul">${judul}</span><div class="saran">${ids.map(chip).join("")}${semua ? '<button type="button" data-semua="1">Lihat semua pertanyaan</button>' : ""}</div>`;
  }
  function tampilkanSemuaSaran() {
    const grup = [...new Set(PERTANYAAN.map((p) => p.grup))];
    gelembung(
      "Berikut pertanyaan yang dapat saya jawab. Klik salah satu." +
        `<span class="saran-judul">Rekomendasi Pertanyaan</span>` +
        grup
          .map(
            (g) =>
              `<span class="saran-grup">${g}${g.startsWith("Tentang") && !tBgn ? " (pilih bangunan dulu)" : ""}</span><div class="saran">${PERTANYAAN.filter(
                (p) => p.grup === g,
              )
                .map((p) => chip(p.id))
                .join("")}</div>`,
          )
          .join(""),
      "sistem",
    );
  }
  function saranLanjut() {
    const bgn = PERTANYAAN.filter(
      (p) => PERLU_BGN.has(p.id) && !sudahDitanya.has(p.id),
    ).map((p) => p.id);
    const umum = PERTANYAAN.filter(
      (p) => !PERLU_BGN.has(p.id) && !sudahDitanya.has(p.id),
    ).map((p) => p.id);
    return (tBgn ? [...bgn, ...umum] : [...umum, ...bgn]).slice(0, 4);
  }

  function setBgn(kode, umumkan) {
    tBgn = PER_KODE[kode] || null;
    sudahDitanya = new Set(
      [...sudahDitanya].filter((id) => !PERLU_BGN.has(id)),
    );
    tKode.value = tBgn ? tBgn.kode : "";
    document
      .querySelectorAll("#t-galeri button")
      .forEach((b) =>
        b.classList.toggle("aktif", !!tBgn && b.dataset.kode === tBgn.kode),
      );
    document.getElementById("t-bgn").innerHTML = tBgn
      ? `Bangunan terpilih: <b>${tBgn.kode}</b> · kelas model <span class="pill ${tBgn.kelas}">${NAMA_KELAS[tBgn.kelas]}</span>`
      : "Belum ada bangunan dipilih. Pertanyaan umum tetap dapat diajukan.";
    if (tBgn && umumkan) {
      gelembung(
        `Bangunan <b>${tBgn.kode}</b> dipilih (kiri sebelum, kanan sesudah bencana).<img src="${tBgn.img}" alt="Citra bangunan ${tBgn.kode}">` +
          `<button type="button" class="tautan" data-dasbor="${tBgn.kode}">Lihat bangunan ini di Dashboard</button>` +
          blokSaran(["kelas", "atap", "puing", "cocok"]),
        "sistem",
      );
    }
  }

  function kenali(teks) {
    const t = teks.toLowerCase();
    if (DI_LUAR.test(t)) return "luar";
    for (const id of URUTAN_COCOK) if (PER_ID[id].pola.test(t)) return id;
    return null;
  }

  function jawab(id) {
    const m = D.metrik;
    if (PERLU_BGN.has(id) && !tBgn)
      return [
        "Pertanyaan ini tentang satu bangunan. Pilih bangunan dulu melalui daftar kode atau pasangan citra di bagian “Pilih bangunan”, atau sebutkan kodenya dalam pertanyaan (mis. PL-015).",
        null,
      ];
    const b = tBgn;
    const f = (k) => esc(nilaiFitur(k, b.fitur[k]));
    switch (id) {
      case "kelas":
        return [
          `Kelas kerusakan bangunan <b>${b.kode}</b> menurut model: <span class="pill ${b.kelas}">${NAMA_KELAS[b.kelas]}</span>. Label xBD sebagai pembanding: <b>${NAMA_XBD[b.xbd]}</b>.`,
          ASAL,
        ];
      case "atap":
        return [
          `Keutuhan atap bangunan <b>${b.kode}</b>: <b>${f("keutuhan_atap")}</b>.`,
          ASAL,
        ];
      case "puing":
        return [
          `Puing di sekitar bangunan <b>${b.kode}</b>: <b>${f("puing_sekitar")}</b>.`,
          ASAL,
        ];
      case "wujud":
        return [
          `Wujud bangunan <b>${b.kode}</b>: <b>${f("wujud_bangunan")}</b>.`,
          ASAL,
        ];
      case "sedimen":
        return [
          `Sedimen atau lumpur pada bangunan <b>${b.kode}</b>: <b>${f("sedimen_lumpur")}</b>.`,
          ASAL,
        ];
      case "deskripsi": {
        const n = FREK_DESK[b.deskripsi] || 0;
        return [
          `Deskripsi bangunan <b>${b.kode}</b>: “${esc(b.deskripsi || "tidak tersedia")}”` +
            (n > 1
              ? `<br><i>Catatan: kalimat yang sama persis dipakai untuk ${angka(n)} dari ${angka(B.length)} bangunan, sehingga deskripsi belum membedakan kondisi tiap bangunan.</i>`
              : ""),
          ASAL,
        ];
      }
      case "citra":
        return [
          `Citra bangunan <b>${b.kode}</b> (kiri sebelum, kanan sesudah bencana):<img src="${b.img}" alt="Citra bangunan ${b.kode}">`,
          `Citra: xBD, ${D.meta.tanggal_pra} dan ${D.meta.tanggal_pasca}.`,
        ];
      case "cocok":
        return [
          b.kelas === b.xbd
            ? `Ya. Kelas model untuk <b>${b.kode}</b> (${NAMA_KELAS[b.kelas]}) sesuai dengan label xBD (${NAMA_XBD[b.xbd]}).`
            : `Tidak. Kelas model untuk <b>${b.kode}</b> adalah ${NAMA_KELAS[b.kelas]}, sedangkan label xBD-nya ${NAMA_XBD[b.xbd]}.`,
          ASAL,
        ];
      case "jumlah": {
        const h = (k) => B.filter((x) => x.kelas === k).length;
        return [
          `Dari ${angka(B.length)} bangunan sampel pada aplikasi, kelas menurut model: tidak rusak ${angka(h("tidak_rusak"))}, rusak ${angka(h("rusak"))}, hancur ${angka(h("hancur"))}. Menurut label xBD: no-damage ${angka(B.filter((x) => x.xbd === "tidak_rusak").length)}, major-damage ${angka(B.filter((x) => x.xbd === "rusak").length)}, destroyed ${angka(B.filter((x) => x.xbd === "hancur").length)}.`,
          "Dihitung dari data aplikasi (sampel, bukan seluruh bangunan Palu).",
        ];
      }
      case "andal":
        return [
          `Pada ${angka(m.n)} bangunan uji, kelas dari model ini mencapai akurasi ${angka(m.lora_acc, 2)} dan akurasi seimbang ${angka(m.lora_bacc, 2)} (tebakan acak = 0,33). Ketepatan tiap kelas (F1): tidak rusak ${angka(m.lora_f1[0], 2)}, rusak ${angka(m.lora_f1[1], 2)}, hancur ${angka(m.lora_f1[2], 2)}; kelas rusak paling sering keliru. Tanda kerusakan dan deskripsi hampir seragam dan mendapat skor akurasi rata-rata ${angka(m.quest_akurasi_fitur, 2)} dari 5 menurut lima penilai.`,
          "Sumber: evaluasi pada Bab IV skripsi.",
        ];
      case "model":
        return [
          `Kelas kerusakan: ${esc(D.meta.sumber_kelas)}. Tanda kerusakan dan deskripsi: ${esc(D.meta.sumber_fitur)}. Kedua model berukuran kecil (2–3 miliar parameter) dan dijalankan sebelumnya pada GPU; aplikasi ini hanya menyajikan hasilnya.`,
          null,
        ];
      case "data":
        return [
          `Citra satelit dari dataset xBD (WorldView-2, sekitar 0,5 m per piksel), direkam ${esc(D.meta.tanggal_pra)} (sebelum) dan ${esc(D.meta.tanggal_pasca)} (sesudah). Aplikasi menyajikan ${angka(B.length)} bangunan sampel dari ${angka(D.meta.kerangka)} bangunan Palu berlabel.`,
          null,
        ];
    }
    return [null, null];
  }

  function tanya(teks, idPaksa) {
    gelembung(esc(teks), "pengguna");
    const kode = (teks.match(/PL[\s-]*\d{1,3}/i) || [])[0];
    if (kode) {
      const k = normKode(kode);
      if (PER_KODE[k]) setBgn(k, false);
      else {
        gelembung(
          `Kode ${esc(kode)} tidak ditemukan. Kode yang tersedia PL-001 sampai ${kodeAkhir}.` +
            blokSaran(saranLanjut()),
          "sistem",
        );
        return;
      }
    }
    const id = idPaksa || kenali(teks);
    if (id === "luar") {
      gelembung(
        "Maaf, informasi itu tidak tersedia. Prototipe ini hanya memuat kelas kerusakan, tanda kerusakan, deskripsi, dan citra bangunan sampel; data biaya, korban, atau penghuni tidak termasuk." +
          blokSaran(saranLanjut()),
        "sistem",
      );
      return;
    }
    if (!id) {
      gelembung(
        "Maaf, pertanyaan itu belum dapat saya kenali. Coba salah satu rekomendasi berikut." +
          blokSaran(saranLanjut()),
        "sistem",
      );
      return;
    }
    const [isi, asal] = jawab(id);
    if (!PERLU_BGN.has(id) || tBgn) sudahDitanya.add(id);
    gelembung(
      isi,
      "sistem",
      asal,
      blokSaran(saranLanjut(), "Rekomendasi pertanyaan berikutnya"),
    );
  }

  /* galeri pasangan citra tanpa kode (6 per halaman) */
  const PER_HAL = 6;
  let hal = 0;
  function gambarGaleri() {
    const jml = Math.ceil(B.length / PER_HAL);
    hal = (hal + jml) % jml;
    document.getElementById("t-hal").textContent =
      `halaman ${hal + 1} dari ${jml}`;
    document.getElementById("t-galeri").innerHTML = B.slice(
      hal * PER_HAL,
      (hal + 1) * PER_HAL,
    )
      .map(
        (b, i) =>
          `<button type="button" data-kode="${b.kode}" class="${tBgn && tBgn.kode === b.kode ? "aktif" : ""}" aria-label="Pasangan citra ${hal * PER_HAL + i + 1}">
        <img src="${b.img}" alt="Pasangan citra sebelum dan sesudah bencana" loading="lazy"></button>`,
      )
      .join("");
  }

  function bangunTanya() {
    isiPilihanKode(tKode, B, "Pilih kode bangunan…");
    tKode.addEventListener("change", () => {
      if (tKode.value) setBgn(tKode.value, true);
    });
    gambarGaleri();
    document.getElementById("t-galeri").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-kode]");
      if (b) {
        setBgn(b.dataset.kode, true);
        gulirKe(document.querySelector(".area-obrolan"));
      }
    });
    document.getElementById("t-sebelum").addEventListener("click", () => {
      hal--;
      gambarGaleri();
    });
    document.getElementById("t-sesudah").addEventListener("click", () => {
      hal++;
      gambarGaleri();
    });
    document.getElementById("t-acak").addEventListener("click", () => {
      hal = Math.floor(Math.random() * Math.ceil(B.length / PER_HAL));
      gambarGaleri();
    });
    document.getElementById("t-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const inp = document.getElementById("t-teks");
      if (inp.value.trim()) tanya(inp.value.trim());
      inp.value = "";
    });
    const grup = [...new Set(PERTANYAAN.map((p) => p.grup))];
    gelembung(
      "Halo. Saya menjawab pertanyaan baku tentang kerusakan bangunan dari hasil yang sudah dihitung. " +
        "Pilih bangunan di bagian “Pilih bangunan”, lalu klik salah satu rekomendasi di bawah atau ketik pertanyaan sendiri." +
        `<span class="saran-judul">Rekomendasi Pertanyaan</span>` +
        grup
          .map(
            (g) =>
              `<span class="saran-grup">${g}${g.startsWith("Tentang") ? " (pilih bangunan dulu)" : ""}</span><div class="saran">${PERTANYAAN.filter(
                (p) => p.grup === g,
              )
                .map((p) => chip(p.id))
                .join("")}</div>`,
          )
          .join(""),
      "sistem",
    );
  }

  bangunCerita();
  bangunPeta();
  segarkan();
  bangunTanya();

})();