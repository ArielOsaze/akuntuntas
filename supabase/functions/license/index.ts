// Edge Function: aktivasi & verifikasi lisensi AkunTuntas
//
// Seluruh keputusan lisensi diambil di sini, bukan di aplikasi desktop.
// Aplikasi hanya mengirim kunci lisensi dan sidik perangkat, lalu menerima
// jawaban yang sudah ditandatangani secara digital.
//
// Tanda tangan memakai Ed25519. Kunci privatnya dibuat di dalam server dan
// disimpan di tabel server_secrets yang hanya dapat dibaca peran layanan,
// jadi tidak pernah ikut terpasang di aplikasi. Aplikasi hanya memegang
// kunci publik, yang memang boleh diketahui siapa saja. Dengan begitu
// berkas lisensi tidak dapat dipalsukan dari sisi aplikasi.

import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

// Lisensi berlaku selamanya: tidak ada tanggal kedaluwarsa. Angka di bawah
// adalah masa berlaku satu tanda tangan, yaitu berapa lama aplikasi boleh
// dipakai tanpa menghubungi server sama sekali. Sesudah masa itu aplikasi
// tetap dapat dipakai, tetapi mengingatkan pengguna untuk menyambung
// internet supaya lisensi dapat diperiksa ulang, misalnya bila lisensi
// dicabut karena diperjualbelikan kembali.
const HARI_BERLAKU = 180;
const HARI_TENGGANG = 180;

// ------------------------------------------------------------------ utilitas

function hexKeBytes(hex: string): Uint8Array {
  const keluar = new Uint8Array(hex.length / 2);
  for (let i = 0; i < keluar.length; i++) {
    keluar[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return keluar;
}

function bytesKeHex(buf: ArrayBuffer | Uint8Array): string {
  const arr = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  return Array.from(arr).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function bytesKeBase64(buf: ArrayBuffer | Uint8Array): string {
  const arr = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let teks = "";
  for (const b of arr) teks += String.fromCharCode(b);
  return btoa(teks);
}

function base64KeBytes(b64: string): Uint8Array {
  const teks = atob(b64);
  const keluar = new Uint8Array(teks.length);
  for (let i = 0; i < teks.length; i++) keluar[i] = teks.charCodeAt(i);
  return keluar;
}

function balas(data: unknown, kode = 200): Response {
  return new Response(JSON.stringify(data), {
    status: kode,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "authorization, content-type, apikey",
    },
  });
}

function normalisasiKunci(kunci: string): string {
  return (kunci || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
}

// ------------------------------------------------------------------ kunci

type KunciTandaTangan = {
  privat: CryptoKey;
  publik: string;
};

let simpananKunci: KunciTandaTangan | null = null;

// Membaca kunci dari penyimpanan server, atau membuatnya sekali bila belum
// ada. Kunci privat disimpan dalam bentuk PKCS8 karena bentuk "raw" tidak
// didukung untuk kunci privat Ed25519. Kunci publik disimpan dalam bentuk
// mentah 32 byte, yang dipakai aplikasi untuk memeriksa tanda tangan.
async function ambilKunci(db: ReturnType<typeof createClient>): Promise<KunciTandaTangan> {
  if (simpananKunci) return simpananKunci;

  const { data } = await db
    .from("server_secrets")
    .select("nama, nilai")
    .in("nama", ["signing_private", "signing_public"]);

  const baris = data || [];
  const privatB64 = baris.find((b) => b.nama === "signing_private")?.nilai;
  const publikHex = baris.find((b) => b.nama === "signing_public")?.nilai;

  if (privatB64 && publikHex) {
    const privat = await crypto.subtle.importKey(
      "pkcs8",
      base64KeBytes(privatB64),
      { name: "Ed25519" },
      false,
      ["sign"],
    );
    simpananKunci = { privat, publik: publikHex };
    return simpananKunci;
  }

  const pasangan = await crypto.subtle.generateKey(
    { name: "Ed25519" },
    true,
    ["sign", "verify"],
  );
  const derPrivat = await crypto.subtle.exportKey("pkcs8", pasangan.privateKey);
  const rawPublik = await crypto.subtle.exportKey("raw", pasangan.publicKey);
  const b64Privat = bytesKeBase64(derPrivat);
  const hexPublik = bytesKeHex(rawPublik);

  await db.from("server_secrets").upsert([
    { nama: "signing_private", nilai: b64Privat },
    { nama: "signing_public", nilai: hexPublik },
  ], { onConflict: "nama" });

  const privat = await crypto.subtle.importKey(
    "pkcs8",
    base64KeBytes(b64Privat),
    { name: "Ed25519" },
    false,
    ["sign"],
  );
  simpananKunci = { privat, publik: hexPublik };
  return simpananKunci;
}

async function tandaTangani(kunci: CryptoKey, pesan: string): Promise<string> {
  const tanda = await crypto.subtle.sign(
    "Ed25519",
    kunci,
    new TextEncoder().encode(pesan),
  );
  return bytesKeHex(tanda);
}

// ------------------------------------------------------------------ inti

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "authorization, content-type, apikey",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
      },
    });
  }

  if (req.method !== "POST") {
    return balas({ ok: false, pesan: "Metode tidak didukung" }, 405);
  }

  try {
    return await tangani(req);
  } catch (e) {
    // Kesalahan tak terduga tetap dilaporkan supaya mudah ditelusuri,
    // tanpa membocorkan isi kunci atau data lisensi.
    return balas({
      ok: false,
      pesan: "Gangguan pada server lisensi.",
      rincian: e instanceof Error ? e.message : String(e),
    }, 500);
  }
});

async function tangani(req: Request): Promise<Response> {
  let isi: Record<string, string>;
  try {
    isi = await req.json();
  } catch {
    return balas({ ok: false, pesan: "Permintaan tidak sah" }, 400);
  }

  const db = createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: { persistSession: false },
  });

  const aksi = isi.aksi || "aktivasi";

  // ---------------------------------------------------------- kunci publik
  // Dipakai sekali saat menyiapkan aplikasi. Kunci publik memang boleh
  // diketahui siapa saja dan ditanam di aplikasi.
  if (aksi === "kunci-publik") {
    const kunci = await ambilKunci(db);
    return balas({ ok: true, kunci_publik: kunci.publik });
  }

  const kunciLisensi = normalisasiKunci(isi.kunci || "");
  const sidik = (isi.sidik || "").trim();
  const namaPerangkat = (isi.nama_perangkat || "").slice(0, 120);
  const osInfo = (isi.os_info || "").slice(0, 120);
  const versiApp = (isi.versi_app || "").slice(0, 40);

  if (!kunciLisensi || !sidik) {
    return balas({ ok: false, pesan: "Kunci lisensi dan sidik perangkat wajib" }, 400);
  }

  // ---------------------------------------------------------- cari lisensi
  const { data: lisensi, error: galatLisensi } = await db
    .from("licenses")
    .select("id, license_key, product_code, status, pemilik_nama, pemilik_email, kedaluwarsa_pada")
    .eq("license_key", kunciLisensi)
    .maybeSingle();

  if (galatLisensi) {
    return balas({ ok: false, pesan: "Gangguan pada server lisensi" }, 500);
  }

  async function catat(hasil: string, keterangan: string) {
    await db.from("activation_log").insert({
      license_key: kunciLisensi,
      device_fingerprint: sidik,
      device_name: namaPerangkat,
      hasil,
      keterangan,
    });
  }

  if (!lisensi) {
    await catat("ditolak", "Kunci tidak dikenal");
    return balas({ ok: false, pesan: "Kunci lisensi tidak dikenal." }, 404);
  }

  if (lisensi.status !== "aktif") {
    const sebab = lisensi.status === "dicabut"
      ? "Lisensi ini sudah dicabut."
      : "Lisensi ini sedang ditangguhkan.";
    await catat("ditolak", `Status: ${lisensi.status}`);
    return balas({ ok: false, pesan: sebab }, 403);
  }

  if (lisensi.kedaluwarsa_pada &&
      new Date(lisensi.kedaluwarsa_pada) < new Date()) {
    await catat("ditolak", "Lisensi kedaluwarsa");
    return balas({ ok: false, pesan: "Masa berlaku lisensi sudah berakhir." }, 403);
  }

  // ---------------------------------------------------------- paket
  const { data: paket } = await db
    .from("products")
    .select("code, nama, max_device, fitur")
    .eq("code", lisensi.product_code)
    .maybeSingle();

  if (!paket) {
    await catat("ditolak", "Paket tidak ditemukan");
    return balas({ ok: false, pesan: "Paket lisensi tidak ditemukan." }, 500);
  }

  // ---------------------------------------------------------- perangkat
  const { data: terdaftar } = await db
    .from("activations")
    .select("id, device_fingerprint, device_name, aktif")
    .eq("license_id", lisensi.id)
    .eq("aktif", true);

  const daftar = terdaftar || [];
  const iniSudahAda = daftar.find((d) => d.device_fingerprint === sidik);
  const terpakai = daftar.length;

  // ---------------------------------------------------------- lepas perangkat
  if (aksi === "lepas") {
    if (!iniSudahAda) {
      await catat("ditolak", "Perangkat tidak terdaftar");
      return balas({ ok: false, pesan: "Perangkat ini tidak terdaftar." }, 404);
    }
    await db.from("activations")
      .update({ aktif: false })
      .eq("id", iniSudahAda.id);
    await catat("lepas", `Perangkat dilepas: ${namaPerangkat}`);
    return balas({ ok: true, pesan: "Perangkat berhasil dilepas." });
  }

  // ---------------------------------------------------------- batas perangkat
  if (!iniSudahAda && terpakai >= paket.max_device) {
    const pesan = paket.max_device === 1
      ? "Lisensi ini sudah dipakai di perangkat lain. Lisensi Standar hanya " +
        "untuk 1 perangkat. Lepas perangkat lama lebih dulu, atau tingkatkan " +
        "ke paket Enterprise untuk multi perangkat."
      : `Lisensi ini sudah dipakai di ${terpakai} perangkat. ` +
        `Batas paket ${paket.nama} adalah ${paket.max_device} perangkat.`;
    await catat("ditolak", `Batas perangkat tercapai (${terpakai}/${paket.max_device})`);
    return balas({ ok: false, pesan }, 409);
  }

  // ---------------------------------------------------------- daftarkan
  if (iniSudahAda) {
    await db.from("activations")
      .update({
        terakhir_dilihat: new Date().toISOString(),
        app_version: versiApp,
        device_name: namaPerangkat,
        os_info: osInfo,
      })
      .eq("id", iniSudahAda.id);
  } else {
    const { error: galatDaftar } = await db.from("activations").insert({
      license_id: lisensi.id,
      device_fingerprint: sidik,
      device_name: namaPerangkat,
      os_info: osInfo,
      app_version: versiApp,
    });
    if (galatDaftar) {
      await catat("gagal", galatDaftar.message);
      return balas({ ok: false, pesan: "Gagal mendaftarkan perangkat." }, 500);
    }
  }

  // ---------------------------------------------------------- tanda tangan
  const sekarang = new Date();
  const berlakuSampai = new Date(sekarang);
  berlakuSampai.setDate(berlakuSampai.getDate() + HARI_BERLAKU);

  const tenggangSampai = new Date(berlakuSampai);
  tenggangSampai.setDate(tenggangSampai.getDate() + HARI_TENGGANG);

  const muatan = {
    kunci: lisensi.license_key,
    sidik,
    paket: paket.code,
    fitur: paket.fitur,
    max_device: paket.max_device,
    pemilik: lisensi.pemilik_nama || "",
    diterbitkan: sekarang.toISOString(),
    berlaku_sampai: berlakuSampai.toISOString(),
    tenggang_sampai: tenggangSampai.toISOString(),
  };

  const muatanTeks = JSON.stringify(muatan);
  const kunciTanda = await ambilKunci(db);
  const tanda = await tandaTangani(kunciTanda.privat, muatanTeks);

  await catat(
    iniSudahAda ? "verifikasi" : "aktivasi",
    `Perangkat: ${namaPerangkat} (${terpakai + (iniSudahAda ? 0 : 1)}/${paket.max_device})`,
  );

  return balas({
    ok: true,
    muatan: muatanTeks,
    tanda,
    paket: paket.code,
    nama_paket: paket.nama,
    perangkat_terpakai: terpakai + (iniSudahAda ? 0 : 1),
    max_device: paket.max_device,
  });
}
