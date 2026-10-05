@echo off
chcp 65001 > nul
title AkunTuntas - Kamera Virtual
cd /d "%~dp0"

echo ======================================================================
echo   KAMERA VIRTUAL AKUNTUNTAS
echo ======================================================================
echo.
echo   Kamera USB Anda dikirim ke kamera virtual, dengan latar
echo   AkunTuntas sudah terpasang.
echo.
echo   DI TIKTOK LIVE STUDIO:
echo     1. Add source, pilih Camera
echo     2. Pilih perangkat: OBS Virtual Camera
echo     3. Letakkan di kotak kanan atas:
echo        X=646  Y=40  lebar=400  tinggi=300
echo.
echo   Tidak perlu Window capture. Sumbernya kamera asli dari TikTok.
echo.
echo   Tekan tombol apa saja untuk mulai. Tekan Ctrl+C untuk berhenti.
echo.
pause > nul

set PY=
if exist "C:\Users\ariel\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" (
    set PY=C:\Users\ariel\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe
) else (
    where python >nul 2>&1 && set PY=python
)

if "%PY%"=="" (
    echo   Python tidak ditemukan.
    pause
    exit /b 1
)

echo.
echo   Memeriksa kamera...
"%PY%" tools\cek_semua_kamera.py 2>nul | findstr /C:"index" /C:"kamera tersedia"

echo.
echo   Menjalankan...
"%PY%" -u tools\jendela_kamera.py --virtual --index 0

echo.
echo ======================================================================
echo   Kamera virtual dihentikan.
echo ======================================================================
pause > nul
