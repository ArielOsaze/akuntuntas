# -*- mode: python ; coding: utf-8 -*-
"""
Konfigurasi PyInstaller untuk AkuntansiID
=========================================
Menghasilkan satu folder aplikasi (onedir) yang dijalankan dari
AkuntansiID.exe. Mode onedir dipilih agar aplikasi terbuka lebih cepat
dan lebih stabil dibanding onefile.

Jalankan:
    pyinstaller build.spec --noconfirm --clean
"""
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

ROOT = os.path.abspath(os.path.dirname(SPEC))  # noqa: F821
SRC = os.path.join(ROOT, "src")

# --------------------------------------------------------------------------
# Data yang perlu dibundel
# --------------------------------------------------------------------------
datas = []

# ikon & aset
aset_dir = os.path.join(ROOT, "assets")
if os.path.isdir(aset_dir):
    for berkas in os.listdir(aset_dir):
        datas.append((os.path.join(aset_dir, berkas), "assets"))

# app_info.json
info = os.path.join(ROOT, "app_info.json")
if os.path.isfile(info):
    datas.append((info, "."))

# dokumen referensi regulasi (agar pengguna dapat membaca aturan aslinya)
dok_dir = os.path.join(ROOT, "docs")
if os.path.isdir(dok_dir):
    for berkas in os.listdir(dok_dir):
        p = os.path.join(dok_dir, berkas)
        if os.path.isfile(p) and berkas.endswith((".txt", ".md", ".json")):
            datas.append((p, "docs"))
    # salinan teks regulasi resmi (versi ringan; PDF tidak dibundel)
    pajak_dir = os.path.join(dok_dir, "pajak2026")
    if os.path.isdir(pajak_dir):
        for berkas in os.listdir(pajak_dir):
            if berkas.endswith(".txt"):
                datas.append((os.path.join(pajak_dir, berkas),
                              os.path.join("docs", "pajak2026")))

# data Qt yang diperlukan (ikon, terjemahan)
datas += collect_data_files("PySide6")

# --------------------------------------------------------------------------
# Modul tersembunyi (diimpor dinamis)
# --------------------------------------------------------------------------
hiddenimports = [
    "sqlite3",
    "openpyxl",
    "reportlab",
    "reportlab.pdfbase._fontdata",
    "reportlab.pdfbase.ttfonts",
    "csv",
    "json",
    "hashlib",
    "secrets",
    "base64",
    "hmac",
    "datetime",
    "dataclasses",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]
hiddenimports += collect_submodules("akuntansi_id")

# --------------------------------------------------------------------------
# Pengecualian: buang modul berat yang tidak dipakai agar EXE lebih kecil
# --------------------------------------------------------------------------
excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    # numpy ikut terbawa lewat openpyxl tetapi tidak dipakai aplikasi.
    # Membuangnya menghemat sekitar 27 MB dan mengurangi titik gagal.
    "numpy",
    "numpy.random.tests",
    "pandas.tests",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.Qt3DCore",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtOpenGL",
    "PySide6.QtPdf",
    "PySide6.QtSvgWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtQml",
    "PySide6.QtQuickWidgets",
    "PySide6.QtSensors",
    "PySide6.QtSpatialAudio",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtStateMachine",
    "PySide6.QtUiTools",
]

# --------------------------------------------------------------------------
# Analisis
# --------------------------------------------------------------------------
a = Analysis(  # noqa: F821
    [os.path.join(ROOT, "run.py")],
    pathex=[SRC, ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

icon_path = os.path.join(ROOT, "assets", "app.ico")
if not os.path.isfile(icon_path):
    icon_path = None

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AkunTuntas",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # aplikasi GUI — tanpa jendela hitam
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    version=os.path.join(ROOT, "version_info.txt")
    if os.path.isfile(os.path.join(ROOT, "version_info.txt")) else None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AkunTuntas",
)


# --------------------------------------------------------------------------
# Bersihkan berkas yang tidak dipakai aplikasi
# --------------------------------------------------------------------------
# PyInstaller membundel seluruh plugin Qt, termasuk yang tidak pernah
# dipanggil aplikasi ini (WebEngine, Quick, 3D, multimedia, sensor). Selain
# memperbesar unduhan, berkas yang tidak perlu menambah titik gagal saat
# dipindai antivirus di komputer pengguna.
def _bersihkan(folder: str) -> None:
    import shutil
    from pathlib import Path

    if not isinstance(folder, str):
        folder = os.path.join(ROOT, "dist", "AkunTuntas")

    PETA = {
        "plugins": [
            "assetimporters", "canbus", "designer", "geometryloaders",
            "geoservices", "multimedia", "networkinformation", "position",
            "qmllint", "qmltooling", "renderers", "renderplugins",
            "sceneparsers", "scxmldatamodel", "sensors", "sqldrivers",
            "texttospeech", "virtualkeyboard", "webview", "qml",
        ],
        "qml": ["QtQml", "QtQuick", "Qt3D", "QtCharts", "QtMultimedia",
                "QtSensors", "QtWebEngine", "QtWebChannel", "QtWebSockets",
                "QtQuick3D", "QtRemoteObjects", "QtScxml", "QtTest",
                "QtLocation", "QtPositioning", "QtBluetooth", "QtNfc",
                "QtTextToSpeech", "QtSpatialAudio"],
    }

    akar = os.path.join(folder, "_internal", "PySide6")
    for induk, daftar in PETA.items():
        for nama in daftar:
            p = os.path.join(akar, induk, nama)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)

    # Gaya tampilan Qt Quick tidak dipakai: antarmuka aplikasi ini memakai
    # Qt Widgets, bukan QML. Berkasnya dibuang agar bundel lebih ringan.
    for pola in ("qt6quickcontrols2*", "qt6quicktemplates2*", "qt6quickshapes*",
                 "qt6quicklayouts*", "qt6quickdialogs*", "qt6quickeffects*",
                 "qt6quickparticles*", "qt6quicktimeline*", "qt6quickwidgets*"):
        for f in Path(akar).glob(pola):
            try:
                f.unlink()
            except OSError:
                pass

    # berkas besar yang hanya dipakai fitur yang tidak dipakai
    for nama in ("qt6webenginecore.dll", "qt6quick.dll", "qt6quick3d.dll",
                 "qt6qml.dll", "qt6multimedia.dll", "qt6charts.dll",
                 "qt6designer.dll", "qt6help.dll", "qt6pdf.dll",
                 "qt6sensors.dll", "qt6texttospeech.dll", "qt6bluetooth.dll",
                 "qt6nfc.dll", "qt6positioning.dll", "qt6serialport.dll",
                 "qt6scxml.dll", "qt6statemachine.dll", "qt6test.dll",
                 "qt6sql.dll", "qt6datavisualization.dll", "qt6remoteobjects.dll",
                 "qt6webchannel.dll", "qt6websockets.dll", "qt6spatialaudio.dll"):
        p = os.path.join(akar, nama)
        if os.path.isfile(p):
            try:
                os.remove(p)
            except OSError:
                pass

    # Pustaka video dan audio FFmpeg yang ikut lewat Qt Multimedia. Aplikasi
    # ini tidak memutar media apa pun, jadi seluruh pustakanya dibuang.
    for pola in ("avcodec-*", "avformat-*", "avutil-*", "swscale-*",
                 "swresample-*"):
        for f in Path(akar).glob(pola):
            try:
                f.unlink()
            except OSError:
                pass

    # Sisa berkas QML, 3D, dan alat bantu Qt yang tidak dipanggil aplikasi.
    # Semuanya hanya menambah ukuran unduhan.
    for pola in ("qt6quick3d*", "qt63d*", "qt6shadertools*", "qt6graphs*",
                 "qt6qmlcompiler*", "qt6designercomponents*", "qmlls*",
                 "qmlformat*", "qmlscene*", "qmltestrunner*", "qmlcachegen*",
                 "qml*.exe", "v8_context_snapshot.debug.bin"):
        for f in Path(akar).glob(pola):
            try:
                if f.is_file():
                    f.unlink()
            except OSError:
                pass

    # Sumber daya Qt WebEngine: aplikasi tidak memakai peramban tertanam,
    # tetapi berkas ini ikut tersalin dan berukuran puluhan megabita.
    for pola in ("qtwebengine*", "*webengine*.pak", "*devtools*"):
        for f in Path(akar).glob(pola):
            try:
                f.unlink()
            except OSError:
                pass
    for nama in ("resources", "translations/qtwebengine_locales"):
        p = os.path.join(akar, nama)
        if os.path.isdir(p):
            for f in Path(p).glob("*webengine*"):
                try:
                    f.unlink()
                except OSError:
                    pass


_bersihkan(os.path.join(ROOT, "dist", "AkunTuntas"))
