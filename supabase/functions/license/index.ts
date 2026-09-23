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

import { createClient } from "npm:@supabase/supabase-js@2";

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

// Kunci disimpan tanpa tanda hubung, tetapi ditampilkan berkelompok empat
// huruf supaya mudah dibaca dan diketik ulang oleh pembeli.
function tampilkanKunci(kunci: string): string {
  const bersih = normalisasiKunci(kunci);
  const potongan: string[] = [];
  for (let i = 0; i < bersih.length; i += 4) {
    potongan.push(bersih.slice(i, i + 4));
  }
  return potongan.join("-");
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

// ------------------------------------------------------------------ rahasia

async function ambilRahasia(
  db: ReturnType<typeof createClient>,
  nama: string,
): Promise<string> {
  const { data } = await db
    .from("server_secrets")
    .select("nilai")
    .eq("nama", nama)
    .maybeSingle();
  return (data?.nilai || "").trim();
}

// ------------------------------------------------------------------ bantuan

// Nomor telepon harus berbentuk 08xxxxxxxxxx. Bentuk +62 atau 62 dirapikan
// dulu supaya iPaymu tidak menolak transaksi.
function rapikanTelepon(nomor: string): string {
  let angka = (nomor || "").replace(/[^0-9]/g, "");
  if (angka.startsWith("62")) angka = angka.slice(2);
  if (angka.startsWith("0")) angka = angka.slice(1);
  if (!angka) return "";
  return `0${angka}`;
}

function acakAman(panjang: number): string {
  const huruf = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const buf = new Uint8Array(panjang);
  crypto.getRandomValues(buf);
  let teks = "";
  for (const b of buf) teks += huruf[b % huruf.length];
  return teks;
}

// Menerbitkan kunci lisensi untuk satu pesanan yang sudah dibayar, lalu
// menandai pesanannya lunas. Dipakai bersama oleh panggilan webhook dan
// pemeriksaan status, supaya keduanya tidak menerbitkan kunci berkali-kali.
async function terbitkanUntukPesanan(
  db: ReturnType<typeof createClient>,
  pesanan: {
    id: string;
    order_code: string;
    product_code: string;
    nama_pembeli: string;
    email_pembeli: string;
    whatsapp?: string | null;
  },
  trxId: string,
): Promise<string | null> {
  const { data: kunciBaru } = await db.rpc("terbitkan_lisensi", {
    p_product_code: pesanan.product_code,
    p_nama: pesanan.nama_pembeli,
    p_email: pesanan.email_pembeli,
    p_wa: pesanan.whatsapp || null,
    p_catatan: `Pesanan ${pesanan.order_code}`,
  });

  if (!kunciBaru) return null;

  const { data: lisensi } = await db
    .from("licenses")
    .select("id, license_key")
    .eq("license_key", kunciBaru)
    .maybeSingle();

  await db.from("orders").update({
    status: "dibayar",
    dibayar_pada: new Date().toISOString(),
    trx_pembayaran: trxId,
    license_id: lisensi?.id || null,
    diperbarui_pada: new Date().toISOString(),
  }).eq("id", pesanan.id);

  return tampilkanKunci(kunciBaru as string);
}

// ------------------------------------------------------------------ admin

// Kata sandi tidak pernah disimpan apa adanya. Yang disimpan hanya sidik
// PBKDF2 beserta garamnya, sehingga isi tabel tidak dapat dipakai untuk
// masuk walau bocor.
async function sidikSandi(sandi: string, garam: string): Promise<string> {
  const bahan = new TextEncoder().encode(`${garam}:${sandi}`);
  const kunci = await crypto.subtle.importKey(
    "raw", bahan, { name: "PBKDF2" }, false, ["deriveBits"],
  );
  const bit = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt: new TextEncoder().encode(garam), iterations: 150000, hash: "SHA-256" },
    kunci,
    256,
  );
  return bytesKeHex(bit);
}

function acakToken(): string {
  const buf = new Uint8Array(32);
  crypto.getRandomValues(buf);
  return bytesKeHex(buf);
}

type AkunAdmin = { email: string; nama: string; peran: string };

// Memeriksa token sesi. Mengembalikan akun bila sesinya masih berlaku,
// atau null bila tidak. Sesi yang sudah lewat masa berlakunya dibersihkan.
async function periksaSesi(
  db: ReturnType<typeof createClient>,
  token: string,
): Promise<AkunAdmin | null> {
  if (!token || token.length !== 64) return null;

  const { data: sesi } = await db
    .from("admin_sessions")
    .select("email, kedaluwarsa_pada")
    .eq("token", token)
    .maybeSingle();

  if (!sesi) return null;

  if (new Date(sesi.kedaluwarsa_pada) < new Date()) {
    await db.from("admin_sessions").delete().eq("token", token);
    return null;
  }

  const { data: akun } = await db
    .from("developer_accounts")
    .select("email, nama, peran, aktif")
    .eq("email", sesi.email)
    .maybeSingle();

  if (!akun || !akun.aktif) return null;

  return { email: akun.email, nama: akun.nama, peran: akun.peran };
}

async function catatJejak(
  db: ReturnType<typeof createClient>,
  email: string,
  tindakan: string,
  keterangan: string,
) {
  await db.from("admin_jejak").insert({ email, tindakan, keterangan });
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
  // iPaymu mengirim panggilan webhook dengan bentuk isi yang berbeda dari
  // aplikasi, jadi isi mentahnya dibaca lebih dulu lalu disesuaikan.
  let isi: Record<string, string>;
  try {
    const teks = await req.text();
    const tipe = req.headers.get("content-type") || "";

    if (tipe.includes("application/x-www-form-urlencoded")) {
      const hasil: Record<string, string> = {};
      for (const [k, v] of new URLSearchParams(teks)) hasil[k] = v;
      isi = hasil;
    } else {
      isi = JSON.parse(teks);
    }
  } catch {
    return balas({ ok: false, pesan: "Permintaan tidak sah" }, 400);
  }

  const db = createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: { persistSession: false },
  });

  // Panggilan webhook dari iPaymu tidak menyertakan field aksi, tetapi selalu
  // membawa acuan pesanan dan nomor transaksi. Keduanya dipakai untuk
  // mengenalinya.
  const adaAcuan = !!(isi.referenceId || isi.reference_id);
  const adaTrx = !!(isi.trx_id || isi.trxId || isi.TransactionId);
  const aksi = isi.aksi || (adaAcuan && adaTrx ? "notify" : "aktivasi");

  // ---------------------------------------------------------- beli lisensi
  // Membuat pesanan baru lalu meminta halaman pembayaran ke iPaymu. Kunci
  // lisensi belum dibuat di sini: kunci baru diterbitkan setelah pembayaran
  // benar-benar terkonfirmasi, supaya tidak ada kunci yang bocor tanpa
  // pembayaran.
  if (aksi === "beli") {
    const paketKode = (isi.paket || "").trim().toLowerCase();
    const nama = (isi.nama || "").trim().slice(0, 120);
    const email = (isi.email || "").trim().slice(0, 160);
    const wa = rapikanTelepon(isi.whatsapp || "");
    const usaha = (isi.usaha || "").trim().slice(0, 160);

    if (!nama || !email || !wa) {
      return balas({
        ok: false,
        pesan: "Nama, email, dan nomor WhatsApp wajib diisi.",
      }, 400);
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      return balas({ ok: false, pesan: "Alamat email tidak sah." }, 400);
    }

    const { data: paket } = await db
      .from("products")
      .select("code, nama, harga, max_device")
      .eq("code", paketKode)
      .maybeSingle();

    if (!paket) {
      return balas({ ok: false, pesan: "Paket lisensi tidak dikenal." }, 404);
    }

    // Kode pesanan dipakai sebagai acuan pembayaran. Bentuknya harus unik dan
    // mudah dibaca saat pembeli menghubungi kami.
    const kodePesanan = `AT-${Date.now().toString(36).toUpperCase()}-${acakAman(4)}`;
    const jumlah = paket.harga as number;

    const { data: pesanan, error: galatPesanan } = await db
      .from("orders")
      .insert({
        order_code: kodePesanan,
        product_code: paket.code,
        nama_pembeli: nama,
        email_pembeli: email,
        whatsapp: wa,
        nama_usaha: usaha || null,
        jumlah,
        status: "menunggu",
        acuan_pembayaran: kodePesanan,
      })
      .select("id, order_code")
      .single();

    if (galatPesanan || !pesanan) {
      return balas({ ok: false, pesan: "Gagal membuat pesanan." }, 500);
    }

    // iPaymu hanya menerima permintaan dari alamat IP yang terdaftar, dan
    // hanya mengizinkan beberapa domain tertentu pada tautan kembali. Server
    // NexShop sudah memenuhi keduanya, jadi permintaan pembuatan transaksi
    // dititipkan lewat jembatan di sana.
    const alamatJembatan = await ambilRahasia(db, "jembatan_alamat");
    const rahasiaJembatan = await ambilRahasia(db, "jembatan_rahasia");
    const alamatSitus = await ambilRahasia(db, "alamat_situs") ||
      "https://akuntuntas.xinet.id";

    if (!alamatJembatan || !rahasiaJembatan) {
      return balas({
        ok: false,
        pesan: "Pembayaran daring belum siap. Hubungi akuntuntas@gmail.com.",
      }, 503);
    }

    try {
      const jawabanJembatan = await fetch(`${alamatJembatan}/bayar`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-jembatan-rahasia": rahasiaJembatan,
        },
        body: JSON.stringify({
          referenceId: kodePesanan,
          jumlah,
          namaPaket: `Lisensi ${paket.nama}`,
          nama,
          email,
          wa,
          returnUrl: `${alamatSitus}/selesai.html?pesanan=${kodePesanan}`,
          notifyUrl: "https://nexshop.cloud/api/akuntuntas/webhook",
          cancelUrl: `${alamatSitus}/batal.html?pesanan=${kodePesanan}`,
        }),
      });

      const jawaban = await jawabanJembatan.json() as {
        ok?: boolean;
        sesi?: string;
        tautan?: string;
        pesan?: string;
      };

      if (!jawaban.ok || !jawaban.tautan) {
        await db.from("orders")
          .update({ catatan: `iPaymu menolak: ${jawaban.pesan || "tanpa keterangan"}` })
          .eq("id", pesanan.id);
        return balas({
          ok: false,
          pesan: "Pembayaran gagal dibuat. Coba lagi atau hubungi kami.",
        }, 502);
      }

      await db.from("orders").update({
        sesi_pembayaran: jawaban.sesi || "",
        acuan_pembayaran: kodePesanan,
        diperbarui_pada: new Date().toISOString(),
      }).eq("id", pesanan.id);

      return balas({
        ok: true,
        pesanan: kodePesanan,
        tautan_bayar: jawaban.tautan,
        jumlah,
        nama_paket: paket.nama,
      });
    } catch (e) {
      await db.from("orders")
        .update({ catatan: `Gangguan jembatan: ${e instanceof Error ? e.message : String(e)}` })
        .eq("id", pesanan.id);
      return balas({
        ok: false,
        pesan: "Tidak dapat menghubungi layanan pembayaran. Coba lagi.",
      }, 502);
    }
  }

  // ---------------------------------------------------------- status pesanan
  // Dipakai halaman selesai untuk menampilkan kunci lisensi setelah pembeli
  // membayar. Status diambil dari catatan kami sendiri; bila masih menunggu,
  // kami tanyakan sekali ke iPaymu supaya pembeli tidak perlu menunggu
  // webhook yang mungkin belum sampai.
  if (aksi === "status") {
    const kodePesanan = (isi.pesanan || "").trim().toUpperCase();
    if (!kodePesanan) {
      return balas({ ok: false, pesan: "Kode pesanan wajib diisi." }, 400);
    }

    const { data: pesanan } = await db
      .from("orders")
      .select("id, order_code, product_code, nama_pembeli, email_pembeli, whatsapp, nama_usaha, jumlah, status, license_id, trx_pembayaran, dibayar_pada, dibuat_pada")
      .eq("order_code", kodePesanan)
      .maybeSingle();

    if (!pesanan) {
      return balas({ ok: false, pesan: "Pesanan tidak ditemukan." }, 404);
    }

    // Keterangan paket dipakai pada kwitansi, jadi namanya diambil dari tabel
    // paket, bukan kodenya.
    const { data: paketPesanan } = await db
      .from("products")
      .select("code, nama, max_device")
      .eq("code", pesanan.product_code)
      .maybeSingle();

    // Rincian ini dipakai halaman kwitansi supaya pembeli dapat mencetak atau
    // menyimpan bukti pembelian tanpa meminta ke penjual.
    const rincian = {
      nama_pembeli: pesanan.nama_pembeli,
      email_pembeli: pesanan.email_pembeli,
      whatsapp: pesanan.whatsapp,
      nama_usaha: pesanan.nama_usaha,
      jumlah: pesanan.jumlah,
      nama_paket: paketPesanan?.nama || "AkunTuntas",
      max_device: paketPesanan?.max_device || 1,
      trx_pembayaran: pesanan.trx_pembayaran,
      dibayar_pada: pesanan.dibayar_pada,
      dibuat_pada: pesanan.dibuat_pada,
    };

    if (pesanan.status === "dibayar" && pesanan.license_id) {
      const { data: lisensi } = await db
        .from("licenses")
        .select("license_key")
        .eq("id", pesanan.license_id)
        .maybeSingle();

      if (lisensi) {
        return balas({
          ok: true,
          status: "dibayar",
          kunci: tampilkanKunci(lisensi.license_key),
          nama_pembeli: pesanan.nama_pembeli,
          nama_paket: pesanan.product_code,
          rincian,
        });
      }
    }

    // Bila masih menunggu, status ditanyakan sendiri ke iPaymu lewat jembatan
    // supaya pembeli tidak perlu menunggu panggilan webhook yang mungkin belum
    // sampai. Ini juga menutup kemungkinan webhook gagal diterima.
    if (pesanan.status === "menunggu" && pesanan.trx_pembayaran) {
      const alamatJembatan = await ambilRahasia(db, "jembatan_alamat");
      const rahasiaJembatan = await ambilRahasia(db, "jembatan_rahasia");

      if (alamatJembatan && rahasiaJembatan) {
        try {
          const jawabanJembatan = await fetch(`${alamatJembatan}/status`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "x-jembatan-rahasia": rahasiaJembatan,
            },
            body: JSON.stringify({ trxId: pesanan.trx_pembayaran }),
          });
          const periksa = await jawabanJembatan.json() as {
            ok?: boolean;
            status?: string;
            jumlah?: number | string;
          };

          if (periksa.ok) {
            const statusBayar = String(periksa.status || "").toLowerCase();
            if (statusBayar === "berhasil" || statusBayar === "success") {
              const hasil = await terbitkanUntukPesanan(db, pesanan, String(pesanan.trx_pembayaran));
              if (hasil) {
                return balas({
                  ok: true,
                  status: "dibayar",
                  kunci: hasil,
                  nama_pembeli: pesanan.nama_pembeli,
                  nama_paket: pesanan.product_code,
                  rincian,
                });
              }
            }
          }
        } catch {
          // Bila pemeriksaan gagal, pembeli tetap melihat status menunggu dan
          // halaman akan mencoba lagi.
        }
      }
    }

    return balas({
      ok: true,
      status: pesanan.status,
      nama_pembeli: pesanan.nama_pembeli,
      jumlah: pesanan.jumlah,
      rincian,
    });
  }

  // ---------------------------------------------------------- webhook iPaymu
  // iPaymu memanggil alamat ini setelah pembeli membayar. Isi panggilan tidak
  // dipercaya begitu saja: status selalu ditanyakan ulang ke iPaymu, karena
  // alamat webhook ini terbuka untuk umum dan bisa dipalsukan.
  if (aksi === "notify") {
    const acuan = (isi.referenceId || isi.reference_id || "").trim();
    const trxId = (isi.trx_id || isi.trxId || isi.TransactionId || "").trim();

    if (!acuan || !trxId) {
      return balas({ ok: false, pesan: "Panggilan tidak lengkap." }, 400);
    }

    const { data: pesanan } = await db
      .from("orders")
      .select("id, order_code, product_code, nama_pembeli, email_pembeli, whatsapp, nama_usaha, jumlah, status")
      .eq("order_code", acuan)
      .maybeSingle();

    if (!pesanan) {
      return balas({ ok: false, pesan: "Pesanan tidak ditemukan." }, 404);
    }

    if (pesanan.status === "dibayar") {
      return balas({ ok: true, pesan: "Pesanan sudah dibayar." });
    }

    // Pemeriksaan status juga dititipkan lewat jembatan karena iPaymu hanya
    // menerima permintaan dari alamat IP yang terdaftar di sana.
    const alamatJembatan = await ambilRahasia(db, "jembatan_alamat");
    const rahasiaJembatan = await ambilRahasia(db, "jembatan_rahasia");

    if (!alamatJembatan || !rahasiaJembatan) {
      await db.from("orders").update({
        catatan: "Webhook: jembatan pembayaran belum diatur",
        diperbarui_pada: new Date().toISOString(),
      }).eq("id", pesanan.id);
      return balas({ ok: false, pesan: "Jembatan pembayaran belum diatur." }, 503);
    }

    try {
      const jawabanJembatan = await fetch(`${alamatJembatan}/status`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-jembatan-rahasia": rahasiaJembatan,
        },
        body: JSON.stringify({ trxId }),
      });

      const periksa = await jawabanJembatan.json() as {
        ok?: boolean;
        status?: string;
        jumlah?: number | string;
        acuan?: string;
        pesan?: string;
      };

      if (!periksa.ok) {
        await db.from("orders").update({
          catatan: `Webhook: ${periksa.pesan || "gagal memeriksa"}`,
          diperbarui_pada: new Date().toISOString(),
        }).eq("id", pesanan.id);
        return balas({ ok: false, pesan: "Gagal memeriksa pembayaran." }, 502);
      }

      const statusBayar = String(periksa.status || "").toLowerCase();
      const jumlahBayar = Number(periksa.jumlah || 0);

      if (statusBayar !== "berhasil" && statusBayar !== "success") {
        await db.from("orders").update({
          catatan: `Webhook: status ${statusBayar || "tidak dikenal"}`,
          diperbarui_pada: new Date().toISOString(),
        }).eq("id", pesanan.id);
        return balas({ ok: true, pesan: "Pembayaran belum berhasil." });
      }

      if (jumlahBayar > 0 && jumlahBayar < pesanan.jumlah) {
        await db.from("orders").update({
          catatan: `Jumlah dibayar kurang: ${jumlahBayar} dari ${pesanan.jumlah}`,
          diperbarui_pada: new Date().toISOString(),
        }).eq("id", pesanan.id);
        return balas({ ok: false, pesan: "Jumlah pembayaran tidak sesuai." }, 400);
      }

      // Terbitkan kunci lisensi untuk pesanan ini.
      const kunciTampil = await terbitkanUntukPesanan(db, pesanan, trxId);
      if (!kunciTampil) {
        return balas({ ok: false, pesan: "Gagal menerbitkan lisensi." }, 500);
      }

      return balas({ ok: true, pesan: "Pembayaran diterima." });
    } catch (e) {
      await db.from("orders").update({
        catatan: `Gagal memeriksa pembayaran: ${e instanceof Error ? e.message : String(e)}`,
        diperbarui_pada: new Date().toISOString(),
      }).eq("id", pesanan.id);
      return balas({ ok: false, pesan: "Gagal memeriksa pembayaran." }, 502);
    }
  }


  // ================================================================== admin
  // Seluruh aksi di bawah ini hanya untuk pengelola lisensi. Setiap aksi
  // memerlukan token sesi yang sah, kecuali pendaftaran sandi pertama kali.

  // ---------------------------------------------------------- daftar sandi
  // Dipakai sekali saat pemilik menyiapkan kata sandi pertama. Bila sandi
  // sudah pernah dibuat, aksi ini menolak supaya tidak bisa dipakai orang
  // lain untuk mengambil alih dashboard.
  if (aksi === "admin-daftar") {
    const email = (isi.email || "").trim().toLowerCase();
    const sandi = (isi.sandi || "").trim();

    if (!email || sandi.length < 10) {
      return balas({
        ok: false,
        pesan: "Email wajib diisi dan kata sandi minimal 10 huruf.",
      }, 400);
    }

    const { data: akun } = await db
      .from("developer_accounts")
      .select("email, aktif")
      .eq("email", email)
      .maybeSingle();

    if (!akun || !akun.aktif) {
      return balas({ ok: false, pesan: "Email ini bukan pengelola lisensi." }, 403);
    }

    const { data: sudahAda } = await db
      .from("admin_kredensial")
      .select("email")
      .eq("email", email)
      .maybeSingle();

    if (sudahAda) {
      return balas({
        ok: false,
        pesan: "Kata sandi sudah pernah dibuat. Masuk seperti biasa.",
      }, 409);
    }

    const garam = acakToken().slice(0, 32);
    await db.from("admin_kredensial").insert({
      email,
      garam,
      cincangan: await sidikSandi(sandi, garam),
    });

    await catatJejak(db, email, "daftar", "Kata sandi dashboard dibuat");
    return balas({ ok: true, pesan: "Kata sandi berhasil dibuat." });
  }

  // ---------------------------------------------------------- masuk
  if (aksi === "admin-masuk") {
    const email = (isi.email || "").trim().toLowerCase();
    const sandi = (isi.sandi || "").trim();

    if (!email || !sandi) {
      return balas({ ok: false, pesan: "Email dan kata sandi wajib diisi." }, 400);
    }

    // Batasi percobaan gagal supaya sandi tidak bisa ditebak berulang kali.
    const sejak = new Date(Date.now() - 15 * 60 * 1000).toISOString();
    const { count: gagal } = await db
      .from("admin_gagal_masuk")
      .select("*", { count: "exact", head: true })
      .eq("email", email)
      .gte("dibuat_pada", sejak);

    if ((gagal || 0) >= 8) {
      return balas({
        ok: false,
        pesan: "Terlalu banyak percobaan gagal. Coba lagi dalam 15 menit.",
      }, 429);
    }

    const { data: kredensial } = await db
      .from("admin_kredensial")
      .select("garam, cincangan")
      .eq("email", email)
      .maybeSingle();

    if (!kredensial) {
      await db.from("admin_gagal_masuk").insert({ email });
      return balas({ ok: false, pesan: "Email atau kata sandi salah." }, 401);
    }

    const cocok = await sidikSandi(sandi, kredensial.garam) === kredensial.cincangan;
    if (!cocok) {
      await db.from("admin_gagal_masuk").insert({ email });
      return balas({ ok: false, pesan: "Email atau kata sandi salah." }, 401);
    }

    const { data: akun } = await db
      .from("developer_accounts")
      .select("nama, peran, aktif")
      .eq("email", email)
      .maybeSingle();

    if (!akun || !akun.aktif) {
      return balas({ ok: false, pesan: "Akun ini tidak aktif." }, 403);
    }

    const token = acakToken();
    const kedaluwarsa = new Date(Date.now() + 12 * 60 * 60 * 1000);

    await db.from("admin_sessions").insert({
      token,
      email,
      kedaluwarsa_pada: kedaluwarsa.toISOString(),
    });

    await catatJejak(db, email, "masuk", "Berhasil masuk dashboard");
    return balas({
      ok: true,
      token,
      nama: akun.nama,
      peran: akun.peran,
      kedaluwarsa: kedaluwarsa.toISOString(),
    });
  }

  // ---------------------------------------------------------- ganti sandi
  if (aksi === "admin-ganti-sandi") {
    const token = (isi.token || "").trim();
    const akun = await periksaSesi(db, token);
    if (!akun) {
      return balas({ ok: false, pesan: "Sesi sudah berakhir. Masuk ulang." }, 401);
    }

    const sandi = (isi.sandi || "").trim();
    if (sandi.length < 10) {
      return balas({ ok: false, pesan: "Kata sandi baru minimal 10 huruf." }, 400);
    }

    const garam = acakToken().slice(0, 32);
    await db.from("admin_kredensial").update({
      garam,
      cincangan: await sidikSandi(sandi, garam),
      diganti_pada: new Date().toISOString(),
    }).eq("email", akun.email);

    // Seluruh sesi lain diputus supaya sandi lama tidak bisa dipakai lagi.
    await db.from("admin_sessions").delete().eq("email", akun.email).neq("token", token);

    await catatJejak(db, akun.email, "ganti-sandi", "Kata sandi diganti");
    return balas({ ok: true, pesan: "Kata sandi berhasil diganti." });
  }

  // ---------------------------------------------------------- keluar
  if (aksi === "admin-keluar") {
    const token = (isi.token || "").trim();
    if (token) await db.from("admin_sessions").delete().eq("token", token);
    return balas({ ok: true, pesan: "Sudah keluar." });
  }

  // ---------------------------------------------------------- ikhtisar
  if (aksi === "admin-ikhtisar") {
    const akun = await periksaSesi(db, (isi.token || "").trim());
    if (!akun) {
      return balas({ ok: false, pesan: "Sesi sudah berakhir. Masuk ulang." }, 401);
    }

    const hitung = async (tabel: string, saring?: (q: any) => any) => {
      let q = db.from(tabel).select("*", { count: "exact", head: true });
      if (saring) q = saring(q);
      const { count } = await q;
      return count || 0;
    };

    const jumlahLisensi = await hitung("licenses");
    const lisensiAktif = await hitung("licenses", (q) => q.eq("status", "aktif"));
    const perangkatAktif = await hitung("activations", (q) => q.eq("aktif", true));
    const pesananLunas = await hitung("orders", (q) => q.eq("status", "dibayar"));
    const pesananMenunggu = await hitung("orders", (q) => q.eq("status", "menunggu"));

    const { data: lunas } = await db
      .from("orders")
      .select("jumlah")
      .eq("status", "dibayar");
    const pendapatan = (lunas || []).reduce(
      (jml, b) => jml + Number(b.jumlah || 0), 0,
    );

    // Pemasangan terakhir dipakai untuk melihat aplikasi benar-benar dipakai.
    const { data: aktivitas } = await db
      .from("activation_log")
      .select("license_key, device_name, hasil, keterangan, dibuat_pada")
      .order("dibuat_pada", { ascending: false })
      .limit(12);

    return balas({
      ok: true,
      ikhtisar: {
        jumlah_lisensi: jumlahLisensi,
        lisensi_aktif: lisensiAktif,
        perangkat_aktif: perangkatAktif,
        pesanan_lunas: pesananLunas,
        pesanan_menunggu: pesananMenunggu,
        pendapatan,
      },
      aktivitas: aktivitas || [],
    });
  }

  // ---------------------------------------------------------- daftar lisensi
  if (aksi === "admin-lisensi") {
    const akun = await periksaSesi(db, (isi.token || "").trim());
    if (!akun) {
      return balas({ ok: false, pesan: "Sesi sudah berakhir. Masuk ulang." }, 401);
    }

    const cari = (isi.cari || "").trim();
    let q = db
      .from("licenses")
      .select("id, license_key, product_code, status, pemilik_nama, pemilik_email, pemilik_wa, catatan, diterbitkan_pada, kedaluwarsa_pada")
      .order("diterbitkan_pada", { ascending: false })
      .limit(200);

    if (cari) {
      const pola = `%${cari}%`;
      q = q.or(
        `license_key.ilike.${pola},pemilik_nama.ilike.${pola},` +
        `pemilik_email.ilike.${pola},catatan.ilike.${pola}`,
      );
    }

    const { data: daftar } = await q;

    // Jumlah perangkat dipakai untuk menampilkan pemakaian tiap lisensi.
    const { data: semuaPerangkat } = await db
      .from("activations")
      .select("license_id, aktif");
    const pakai: Record<string, number> = {};
    for (const d of semuaPerangkat || []) {
      if (!d.aktif) continue;
      pakai[d.license_id] = (pakai[d.license_id] || 0) + 1;
    }

    return balas({
      ok: true,
      lisensi: (daftar || []).map((l) => ({
        ...l,
        kunci: tampilkanKunci(l.license_key),
        perangkat_terpakai: pakai[l.id] || 0,
      })),
    });
  }

  // ---------------------------------------------------------- buat lisensi
  if (aksi === "admin-buat-lisensi") {
    const akun = await periksaSesi(db, (isi.token || "").trim());
    if (!akun) {
      return balas({ ok: false, pesan: "Sesi sudah berakhir. Masuk ulang." }, 401);
    }

    const paketKode = (isi.paket || "standar").trim().toLowerCase();
    const nama = (isi.nama || "").trim().slice(0, 120);
    const email = (isi.email || "").trim().slice(0, 160);
    const wa = (isi.whatsapp || "").trim().slice(0, 30);
    const catatan = (isi.catatan || "").trim().slice(0, 200);

    if (!nama) {
      return balas({ ok: false, pesan: "Nama pemilik lisensi wajib diisi." }, 400);
    }

    const { data: paket } = await db
      .from("products")
      .select("code, nama, max_device")
      .eq("code", paketKode)
      .maybeSingle();

    if (!paket) {
      return balas({ ok: false, pesan: "Paket tidak dikenal." }, 404);
    }

    const { data: kunciBaru, error: galatBuat } = await db.rpc("terbitkan_lisensi", {
      p_product_code: paket.code,
      p_nama: nama,
      p_email: email || null,
      p_wa: wa || null,
      p_catatan: catatan || `Dibuat oleh ${akun.email}`,
    });

    if (galatBuat || !kunciBaru) {
      return balas({ ok: false, pesan: "Gagal membuat lisensi." }, 500);
    }

    await catatJejak(
      db, akun.email, "buat-lisensi",
      `${paket.nama} untuk ${nama} (${tampilkanKunci(kunciBaru as string)})`,
    );

    return balas({
      ok: true,
      kunci: tampilkanKunci(kunciBaru as string),
      nama_paket: paket.nama,
      max_device: paket.max_device,
    });
  }

  // ---------------------------------------------------------- ubah lisensi
  if (aksi === "admin-ubah-lisensi") {
    const akun = await periksaSesi(db, (isi.token || "").trim());
    if (!akun) {
      return balas({ ok: false, pesan: "Sesi sudah berakhir. Masuk ulang." }, 401);
    }

    const kunci = normalisasiKunci(isi.kunci || "");
    const statusBaru = (isi.status || "").trim().toLowerCase();

    if (!kunci || !["aktif", "ditangguhkan", "dicabut"].includes(statusBaru)) {
      return balas({ ok: false, pesan: "Kunci dan status wajib diisi dengan benar." }, 400);
    }

    const { data: lisensi } = await db
      .from("licenses")
      .select("id, pemilik_nama")
      .eq("license_key", kunci)
      .maybeSingle();

    if (!lisensi) {
      return balas({ ok: false, pesan: "Lisensi tidak ditemukan." }, 404);
    }

    await db.from("licenses").update({ status: statusBaru }).eq("id", lisensi.id);

    // Bila lisensi dicabut, seluruh perangkatnya dilepas supaya tidak bisa
    // dipakai lagi.
    if (statusBaru !== "aktif") {
      await db.from("activations").update({ aktif: false }).eq("license_id", lisensi.id);
    }

    await catatJejak(
      db, akun.email, "ubah-lisensi",
      `${tampilkanKunci(kunci)} menjadi ${statusBaru}`,
    );

    return balas({ ok: true, pesan: `Status lisensi diubah menjadi ${statusBaru}.` });
  }

  // ---------------------------------------------------------- lepas perangkat
  if (aksi === "admin-lepas-perangkat") {
    const akun = await periksaSesi(db, (isi.token || "").trim());
    if (!akun) {
      return balas({ ok: false, pesan: "Sesi sudah berakhir. Masuk ulang." }, 401);
    }

    const idPerangkat = (isi.perangkat || "").trim();
    if (!idPerangkat) {
      return balas({ ok: false, pesan: "Perangkat wajib dipilih." }, 400);
    }

    const { data: perangkat } = await db
      .from("activations")
      .select("id, device_name, license_id")
      .eq("id", idPerangkat)
      .maybeSingle();

    if (!perangkat) {
      return balas({ ok: false, pesan: "Perangkat tidak ditemukan." }, 404);
    }

    await db.from("activations").update({ aktif: false }).eq("id", perangkat.id);
    await catatJejak(
      db, akun.email, "lepas-perangkat",
      `Perangkat ${perangkat.device_name || perangkat.id} dilepas`,
    );

    return balas({ ok: true, pesan: "Perangkat berhasil dilepas." });
  }

  // ---------------------------------------------------------- pesanan
  if (aksi === "admin-pesanan") {
    const akun = await periksaSesi(db, (isi.token || "").trim());
    if (!akun) {
      return balas({ ok: false, pesan: "Sesi sudah berakhir. Masuk ulang." }, 401);
    }

    const { data: pesanan } = await db
      .from("orders")
      .select("order_code, product_code, nama_pembeli, email_pembeli, whatsapp, nama_usaha, jumlah, status, trx_pembayaran, dibuat_pada, dibayar_pada")
      .order("dibuat_pada", { ascending: false })
      .limit(200);

    return balas({ ok: true, pesanan: pesanan || [] });
  }

  // ---------------------------------------------------------- perangkat
  if (aksi === "admin-perangkat") {
    const akun = await periksaSesi(db, (isi.token || "").trim());
    if (!akun) {
      return balas({ ok: false, pesan: "Sesi sudah berakhir. Masuk ulang." }, 401);
    }

    // Diurutkan menurut waktu dibuat, bukan waktu dilihat terakhir, karena
    // kolom itu boleh kosong pada perangkat yang belum pernah menghubungi
    // server lagi.
    const { data: perangkat } = await db
      .from("activations")
      .select("id, license_id, device_fingerprint, device_name, os_info, app_version, terakhir_dilihat, aktif, diaktifkan_pada")
      .order("diaktifkan_pada", { ascending: false })
      .limit(200);

    // Nama pemilik ditempelkan supaya daftar mudah dibaca.
    const { data: daftarLisensi } = await db
      .from("licenses")
      .select("id, license_key, pemilik_nama");
    const peta: Record<string, { kunci: string; pemilik: string }> = {};
    for (const l of daftarLisensi || []) {
      peta[l.id] = {
        kunci: tampilkanKunci(l.license_key),
        pemilik: l.pemilik_nama || "-",
      };
    }

    return balas({
      ok: true,
      perangkat: (perangkat || []).map((d) => ({
        ...d,
        kunci: peta[d.license_id]?.kunci || "-",
        pemilik: peta[d.license_id]?.pemilik || "-",
      })),
    });
  }

  // ---------------------------------------------------------- jejak
  if (aksi === "admin-jejak") {
    const akun = await periksaSesi(db, (isi.token || "").trim());
    if (!akun) {
      return balas({ ok: false, pesan: "Sesi sudah berakhir. Masuk ulang." }, 401);
    }

    const { data: jejak } = await db
      .from("admin_jejak")
      .select("email, tindakan, keterangan, dibuat_pada")
      .order("dibuat_pada", { ascending: false })
      .limit(100);

    return balas({ ok: true, jejak: jejak || [] });
  }

  // ---------------------------------------------------------- kunci publik
  // Dipakai sekali saat menyiapkan aplikasi. Kunci publik memang boleh
  // diketahui siapa saja dan ditanam di aplikasi.
  if (aksi === "kunci-publik") {
    const kunci = await ambilKunci(db);
    return balas({ ok: true, kunci_publik: kunci.publik });
  }

  // ---------------------------------------------------------- periksa kunci
  // Dipakai halaman unduhan di situs. Tujuannya hanya memastikan kunci benar
  // benar terdaftar sebelum tautan berkas pemasang diberikan. Perangkat tidak
  // didaftarkan di sini karena pemeriksaan dilakukan dari peramban, bukan dari
  // aplikasi.
  if (aksi === "periksa") {
    const kunci = normalisasiKunci(isi.kunci || "");
    if (!kunci) {
      return balas({ ok: false, pesan: "Kunci lisensi wajib diisi." }, 400);
    }

    const { data: lisensi } = await db
      .from("licenses")
      .select("id, license_key, product_code, status, pemilik_nama, kedaluwarsa_pada")
      .eq("license_key", kunci)
      .maybeSingle();

    if (!lisensi) {
      await db.from("activation_log").insert({
        license_key: kunci,
        hasil: "ditolak",
        keterangan: "Periksa dari situs: kunci tidak dikenal",
      });
      return balas({ ok: false, pesan: "Kunci lisensi tidak dikenal." }, 404);
    }

    if (lisensi.status !== "aktif") {
      await db.from("activation_log").insert({
        license_key: kunci,
        hasil: "ditolak",
        keterangan: `Periksa dari situs: status ${lisensi.status}`,
      });
      return balas({ ok: false, pesan: "Lisensi ini sudah tidak aktif." }, 403);
    }

    if (lisensi.kedaluwarsa_pada &&
        new Date(lisensi.kedaluwarsa_pada) < new Date()) {
      return balas({ ok: false, pesan: "Masa berlaku lisensi sudah berakhir." }, 403);
    }

    const { data: paket } = await db
      .from("products")
      .select("code, nama, max_device")
      .eq("code", lisensi.product_code)
      .maybeSingle();

    const berkas = await db
      .from("server_secrets")
      .select("nilai")
      .eq("nama", "tautan_pemasang")
      .maybeSingle();

    await db.from("activation_log").insert({
      license_key: kunci,
      hasil: "periksa",
      keterangan: "Periksa dari situs unduhan",
    });

    return balas({
      ok: true,
      paket: paket?.code || lisensi.product_code,
      nama_paket: paket?.nama || "AkunTuntas",
      max_device: paket?.max_device || 1,
      pemilik: lisensi.pemilik_nama || "",
      tautan: berkas.data?.nilai || "",
    });
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
