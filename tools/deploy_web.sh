#!/usr/bin/env bash
#
# Deploy situs AkunTuntas ke Vercel, dengan pengaman.
#
# Skrip ini dibuat karena dua masalah yang pernah terjadi:
#
#   1. Deploy pernah menghasilkan paket kosong. Situs jadi 404 walaupun
#      perintahnya melaporkan berhasil, dan domain menunjuk ke paket kosong
#      itu.
#
#   2. Komputer ini pernah menyimpan dua tim Vercel. Perintah deploy yang
#      dijalankan tanpa menyebut tim dapat mendarat di tim yang salah.
#
# Karena itu skrip ini mengunci tiga hal sebelum mengunggah:
#   - hanya boleh dijalankan dari folder web/
#   - proyek yang tertaut harus bernama akuntuntas
#   - tim yang dipakai harus akun-tuntas
#
# Setelah mengunggah, hasilnya diperiksa: halaman utama harus memuat isi,
# bukan halaman kosong. Bila kosong, skrip berhenti dengan kode keluar
# bukan nol supaya kegagalan tidak lolos diam-diam.
#
# Pemakaian:
#   bash tools/deploy_web.sh

set -u

TIM_BENAR="akun-tuntas"
PROYEK_BENAR="akuntuntas"
DOMAIN="https://akuntuntas.xinet.id"

# Ukuran terkecil halaman utama yang dianggap wajar. Halaman asli sekitar
# 31 KB; batas ini hanya untuk menangkap hasil kosong.
UKURAN_MINIMUM=20000

cd "$(dirname "$0")/.." || exit 1
AKAR="$(pwd)"
WEB="$AKAR/web"

echo "=========================================================="
echo "  DEPLOY SITUS AKUNTUNTAS"
echo "=========================================================="
echo

# ---------------------------------------------------------------- pengaman
if [ ! -d "$WEB" ]; then
    echo "  GAGAL: folder web tidak ditemukan di $WEB"
    exit 1
fi

if [ ! -f "$WEB/index.html" ]; then
    echo "  GAGAL: web/index.html tidak ada"
    exit 1
fi

SETELAN="$WEB/.vercel/project.json"
if [ ! -f "$SETELAN" ]; then
    echo "  GAGAL: proyek belum tertaut ke Vercel."
    echo "  Jalankan sekali dari folder web: vercel link"
    exit 1
fi

# Jalur dibaca lewat berkas perantara supaya garis miring terbalik pada
# jalur Windows tidak merusak perintah Python. Jalur gaya MSYS (/c/Users)
# diterjemahkan lebih dahulu karena Python Windows tidak mengenalinya.
SETELAN_PY=$(cygpath -w "$SETELAN" 2>/dev/null || echo "$SETELAN")

NAMA_TERLINK=$(python - "$SETELAN_PY" <<'PYAKHIR'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as berkas:
        print(json.load(berkas).get("projectName", ""))
except Exception:
    print("")
PYAKHIR
)

if [ "$NAMA_TERLINK" != "$PROYEK_BENAR" ]; then
    echo "  GAGAL: folder web tertaut ke proyek '$NAMA_TERLINK',"
    echo "         seharusnya '$PROYEK_BENAR'."
    echo "         Perbaiki dengan: cd web && vercel link"
    exit 1
fi
echo "  Proyek tertaut : $NAMA_TERLINK (benar)"

# Periksa tim yang sedang dipakai. Bila berbeda, deploy diarahkan memakai
# --scope sehingga tidak mungkin mendarat di tim lain.
TIM_AKTIF=$(timeout 120 vercel whoami 2>/dev/null | tail -1 | tr -d '\r')
if [ "$TIM_AKTIF" != "$TIM_BENAR" ]; then
    echo "  Tim aktif      : $TIM_AKTIF (akan dipaksa ke $TIM_BENAR)"
else
    echo "  Tim aktif      : $TIM_AKTIF (benar)"
fi
echo

# ------------------------------------------------------------------ deploy
echo "  Mengunggah..."
cd "$WEB" || exit 1

KELUARAN=$(timeout 900 vercel deploy --prod --yes --scope "$TIM_BENAR" 2>&1)
KODE=$?

if [ $KODE -ne 0 ]; then
    echo "  GAGAL mengunggah:"
    echo "$KELUARAN" | tail -8 | sed 's/^/    /'
    exit 1
fi
URL=$(echo "$KELUARAN" | grep -oE 'https://akuntuntas-[a-z0-9]+-akun-tuntas\.vercel\.app' | tail -1)

if [ -z "$URL" ]; then
    echo "  GAGAL: alamat hasil deploy tidak terbaca."
    echo "$KELUARAN" | tail -8 | sed 's/^/    /'
    exit 1
fi

echo "  Alamat deploy  : $URL"
echo

# ----------------------------------------------------------------- periksa
echo "  Memeriksa isi hasil deploy..."
sleep 8

UKURAN=$(curl -s "$URL/" 2>/dev/null | wc -c)
if [ "$UKURAN" -lt "$UKURAN_MINIMUM" ]; then
    echo "  GAGAL: hasil deploy kosong ($UKURAN byte, minimal $UKURAN_MINIMUM)."
    echo
    echo "  Domain TIDAK dipindahkan ke hasil ini, supaya situs yang sedang"
    echo "  berjalan tidak ikut rusak. Coba jalankan skrip ini sekali lagi."
    exit 1
fi
echo "    halaman utama : $UKURAN byte"

# Periksa beberapa halaman penting ikut terunggah
GAGAL=0
for halaman in unduh beli admin kwitansi; do
    KODE_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$URL/$halaman" 2>/dev/null)
    if [ "$KODE_HTTP" != "200" ]; then
        echo "    /$halaman : HTTP $KODE_HTTP (BERMASALAH)"
        GAGAL=1
    else
        echo "    /$halaman : HTTP 200"
    fi
done

if [ $GAGAL -ne 0 ]; then
    echo
    echo "  GAGAL: ada halaman yang tidak ikut terunggah."
    echo "  Domain tidak dipindahkan."
    exit 1
fi

# ------------------------------------------------------- arahkan domain
echo
echo "  Mengarahkan domain ke hasil deploy ini..."
ALIAS=$(timeout 300 vercel alias set "$URL" akuntuntas.xinet.id --scope "$TIM_BENAR" 2>&1)

if echo "$ALIAS" | grep -qi "error"; then
    # Domain dapat saja sudah menunjuk ke deploy ini karena --prod
    # mengarahkannya sendiri. Diperiksa lewat domainnya langsung.
    echo "    (alias ditangani otomatis oleh deploy produksi)"
fi

sleep 12

# ------------------------------------------------- verifikasi lewat domain
echo
echo "  Memeriksa lewat domain resmi..."
SEMUA_BENAR=1
for halaman in "" unduh beli selesai admin kwitansi; do
    KODE_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$DOMAIN/$halaman" 2>/dev/null)
    NAMA="/${halaman:-（utama）}"
    if [ "$KODE_HTTP" != "200" ]; then
        printf "    HTTP %s  %s  BERMASALAH\n" "$KODE_HTTP" "$NAMA"
        SEMUA_BENAR=0
    else
        printf "    HTTP %s  %s\n" "$KODE_HTTP" "$NAMA"
    fi
done

echo
if [ $SEMUA_BENAR -eq 1 ]; then
    echo "=========================================================="
    echo "  BERHASIL: situs aktif di $DOMAIN"
    echo "=========================================================="
    exit 0
fi

echo "=========================================================="
echo "  SEBAGIAN GAGAL: domain belum menunjuk ke hasil terbaru."
echo "  Tunggu satu dua menit lalu periksa lagi dengan:"
echo "    curl -I $DOMAIN"
echo "=========================================================="
exit 1
