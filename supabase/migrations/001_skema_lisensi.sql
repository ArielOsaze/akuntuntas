-- Skema sistem lisensi AkunTuntas
-- Dijalankan sekali di proyek Supabase akuntuntas-license.

-- ---------------------------------------------------------------- paket
create table if not exists products (
    code        text primary key,
    nama        text not null,
    harga       integer not null,
    max_device  integer not null default 1,
    fitur       jsonb not null default '{}'::jsonb,
    dibuat_pada timestamptz not null default now()
);

-- ---------------------------------------------------------------- lisensi
create table if not exists licenses (
    id                uuid primary key default gen_random_uuid(),
    license_key       text unique not null,
    product_code      text not null references products(code),
    status            text not null default 'aktif',
    pemilik_nama      text,
    pemilik_email     text,
    pemilik_wa        text,
    catatan           text,
    diterbitkan_pada  timestamptz not null default now(),
    kedaluwarsa_pada  timestamptz,
    dibuat_pada       timestamptz not null default now(),
    constraint status_sah check (status in ('aktif', 'ditangguhkan', 'dicabut'))
);

create index if not exists idx_licenses_key on licenses (license_key);
create index if not exists idx_licenses_status on licenses (status);

-- ---------------------------------------------------------------- perangkat
create table if not exists activations (
    id                  uuid primary key default gen_random_uuid(),
    license_id          uuid not null references licenses(id) on delete cascade,
    device_fingerprint  text not null,
    device_name         text,
    os_info             text,
    app_version         text,
    aktif               boolean not null default true,
    diaktifkan_pada     timestamptz not null default now(),
    terakhir_dilihat    timestamptz not null default now(),
    unique (license_id, device_fingerprint)
);

create index if not exists idx_activations_license on activations (license_id);
create index if not exists idx_activations_device on activations (device_fingerprint);

-- ---------------------------------------------------------------- riwayat
create table if not exists activation_log (
    id                  bigserial primary key,
    license_key         text,
    device_fingerprint  text,
    device_name         text,
    hasil               text not null,
    keterangan          text,
    ip_address          text,
    dibuat_pada         timestamptz not null default now()
);

create index if not exists idx_log_key on activation_log (license_key);
create index if not exists idx_log_waktu on activation_log (dibuat_pada desc);

-- ---------------------------------------------------------------- pesanan
create table if not exists orders (
    id              uuid primary key default gen_random_uuid(),
    order_code      text unique not null,
    product_code    text not null references products(code),
    nama_pembeli    text not null,
    email_pembeli   text not null,
    whatsapp        text,
    nama_usaha      text,
    jumlah          integer not null default 1,
    status          text not null default 'menunggu',
    catatan         text,
    license_id      uuid references licenses(id),
    dibuat_pada     timestamptz not null default now(),
    dibayar_pada    timestamptz,
    constraint status_order check (status in ('menunggu', 'dibayar', 'dibatalkan'))
);

create index if not exists idx_orders_status on orders (status);

-- ---------------------------------------------------------------- developer
create table if not exists developer_accounts (
    id          uuid primary key default gen_random_uuid(),
    email       text unique not null,
    nama        text not null,
    organisasi  text not null default 'Xinet Group',
    peran       text not null default 'developer',
    aktif       boolean not null default true,
    dibuat_pada timestamptz not null default now(),
    constraint peran_sah check (peran in ('developer', 'admin', 'pemilik'))
);

-- ---------------------------------------------------------------- pembuat kunci
-- Abjad tanpa huruf dan angka yang mudah tertukar (I, O, 0, 1).
create or replace function buat_kunci_lisensi() returns text
language plpgsql as $$
declare
    abjad  text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    hasil  text := 'ATNT';
    i      int;
    j      int;
    bagian text;
begin
    for i in 1..4 loop
        bagian := '';
        for j in 1..4 loop
            bagian := bagian || substr(abjad, 1 + floor(random() * length(abjad))::int, 1);
        end loop;
        hasil := hasil || '-' || bagian;
    end loop;
    return hasil;
end $$;

-- ---------------------------------------------------------------- terbitkan
-- Membuat lisensi baru sekaligus mengembalikan kuncinya.
create or replace function terbitkan_lisensi(
    p_product_code text,
    p_nama         text default null,
    p_email        text default null,
    p_wa           text default null,
    p_catatan      text default null
) returns text
language plpgsql as $$
declare
    kunci text;
    ulang int := 0;
begin
    if not exists (select 1 from products where code = p_product_code) then
        raise exception 'Paket tidak dikenal: %', p_product_code;
    end if;

    loop
        kunci := buat_kunci_lisensi();
        exit when not exists (select 1 from licenses where license_key = kunci);
        ulang := ulang + 1;
        if ulang > 20 then
            raise exception 'Gagal membuat kunci unik';
        end if;
    end loop;

    insert into licenses (license_key, product_code, pemilik_nama,
                          pemilik_email, pemilik_wa, catatan)
    values (kunci, p_product_code, p_nama, p_email, p_wa, p_catatan);

    return kunci;
end $$;

-- ---------------------------------------------------------------- pandangan
-- Ringkasan lisensi beserta jumlah perangkat terpakai.
create or replace view v_ringkasan_lisensi as
select
    l.license_key,
    p.nama            as paket,
    p.harga,
    p.max_device,
    l.status,
    l.pemilik_nama,
    l.pemilik_email,
    l.diterbitkan_pada,
    l.kedaluwarsa_pada,
    count(a.id) filter (where a.aktif) as perangkat_terpakai
from licenses l
join products p on p.code = l.product_code
left join activations a on a.license_id = l.id
group by l.id, p.nama, p.harga, p.max_device;

-- ---------------------------------------------------------------- keamanan
-- Hanya Edge Function (service role) yang boleh menyentuh tabel ini.
-- Kunci anonim tidak diberi akses sama sekali.
alter table products           enable row level security;
alter table licenses           enable row level security;
alter table activations        enable row level security;
alter table activation_log     enable row level security;
alter table orders             enable row level security;
alter table developer_accounts enable row level security;

revoke all on products           from anon, authenticated;
revoke all on licenses           from anon, authenticated;
revoke all on activations        from anon, authenticated;
revoke all on activation_log     from anon, authenticated;
revoke all on orders             from anon, authenticated;
revoke all on developer_accounts from anon, authenticated;
revoke all on v_ringkasan_lisensi from anon, authenticated;

-- ---------------------------------------------------------------- isi awal
insert into products (code, nama, harga, max_device, fitur) values
    ('standar', 'AkunTuntas Standar', 3499000, 1,
     '{"multi_entitas": false, "multi_cabang": false, "payroll_lanjutan": false,
       "dimensi": false, "pajak_lanjutan": false, "audit_lanjutan": false,
       "konsolidasi": false}'::jsonb),
    ('enterprise', 'AkunTuntas Enterprise', 5499000, 5,
     '{"multi_entitas": true, "multi_cabang": true, "payroll_lanjutan": true,
       "dimensi": true, "pajak_lanjutan": true, "audit_lanjutan": true,
       "konsolidasi": true}'::jsonb)
on conflict (code) do update set
    nama       = excluded.nama,
    harga      = excluded.harga,
    max_device = excluded.max_device,
    fitur      = excluded.fitur;
