; ==========================================================================
; Skrip installer Windows untuk AkunTuntas (Inno Setup 6)
; ==========================================================================
; Menghasilkan satu berkas installer: AkunTuntas-1.0.0-Setup.exe
;
; Jalankan setelah build PyInstaller selesai:
;   iscc installer.iss
;
; Fitur installer:
;   - Memasang aplikasi ke Program Files (atau folder pilihan pengguna)
;   - Membuat shortcut di Start Menu dan Desktop (opsional)
;   - Menyediakan pilihan lokasi penyimpanan data
;   - Menawarkan membuat cadangan data sebelum uninstall
;   - Registrasi uninstaller agar aplikasi dapat dihapus dari Control Panel
; ==========================================================================

#define NamaAplikasi "AkunTuntas"
#define VersiAplikasi "1.1.3"
#define Penerbit "Xinet Group"
#define Deskripsi "Pembukuan & Pajak Perusahaan Indonesia"
#define NamaExe "AkunTuntas.exe"

[Setup]
AppId={{8F3A2C71-4D5B-4E9A-9C21-7B6E4A3D2F18}
AppName={#NamaAplikasi}
AppVersion={#VersiAplikasi}
AppVerName={#NamaAplikasi} {#VersiAplikasi}
AppPublisher={#Penerbit}
AppComments={#Deskripsi}
; Keterangan penerbit yang muncul di Control Panel dan di tab Detail berkas.
; Nilai ini juga dipakai Windows untuk mengisi kolom Company pada properti
; berkas, sehingga asal aplikasi jelas meski belum ditandatangani secara
; digital.
VersionInfoCompany={#Penerbit}
VersionInfoDescription={#Deskripsi}
VersionInfoProductName={#NamaAplikasi}
VersionInfoProductVersion={#VersiAplikasi}
VersionInfoVersion={#VersiAplikasi}.0
VersionInfoCopyright=Hak cipta 2026 {#Penerbit}
AppPublisherURL=https://akuntuntas.xinet.id
AppSupportURL=https://akuntuntas.xinet.id
AppUpdatesURL=https://akuntuntas.xinet.id/unduh.html
DefaultDirName={autopf}\{#NamaAplikasi}
DefaultGroupName={#NamaAplikasi}
DisableProgramGroupPage=yes
; Pemasangan versi baru menimpa versi lama, bukan menumpuk di folder
; berbeda. Inno Setup mengenali versi lama lewat AppId yang sama, lalu
; menghapus berkas lamanya lebih dulu.
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousTasks=yes
; Aplikasi ditutup otomatis bila sedang berjalan, supaya berkasnya tidak
; terkunci saat diganti. Tanpa ini, pemasangan gagal dengan pesan bahwa
; berkas sedang dipakai.
CloseApplications=yes
RestartApplications=no
; Halaman pemilihan folder tidak perlu ditampilkan lagi saat memperbarui,
; karena foldernya sudah diketahui dari pemasangan sebelumnya.
DisableDirPage=auto
DisableReadyPage=no
LicenseFile=LICENSE.txt
OutputDir=installer_output
OutputBaseFilename=AkunTuntas-{#VersiAplikasi}-Setup
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#NamaExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
DisableWelcomePage=no
ShowLanguageDialog=no
AllowNoIcons=yes

[Languages]
Name: "indonesia"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Buat pintasan di &Desktop"; GroupDescription: "Pintasan tambahan:"
Name: "quicklaunchicon"; Description: "Buat pintasan di &Quick Launch"; GroupDescription: "Pintasan tambahan:"; Flags: unchecked

[Files]
; Seluruh isi hasil build PyInstaller
Source: "dist\AkunTuntas\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Dokumen pendamping
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[InstallDelete]
; Bersihkan isi folder aplikasi sebelum berkas baru dipasang.
;
; Tanpa ini, berkas dari versi lama yang tidak lagi ada di versi baru akan
; tertinggal. Sisa berkas itu membuat aplikasi memuat modul lama sehingga
; perbaikan tidak terasa meski versi baru sudah dipasang, dan ukuran folder
; terus bertambah setiap pembaruan.
;
; Hanya folder aplikasi yang dibersihkan. Data pembukuan berada di
; %LOCALAPPDATA%\AkunTuntas dan tidak disentuh sama sekali.
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\*.exe"
Type: files; Name: "{app}\*.dll"
Type: files; Name: "{app}\*.pyd"

[Icons]
Name: "{group}\{#NamaAplikasi}"; Filename: "{app}\{#NamaExe}"; Comment: "{#Deskripsi}"
Name: "{group}\Panduan Pengguna"; Filename: "{app}\README.md"
Name: "{group}\Buka Folder Data"; Filename: "{localappdata}\AkunTuntas"; Comment: "Folder penyimpanan data pembukuan"
Name: "{group}\Hapus {#NamaAplikasi}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#NamaAplikasi}"; Filename: "{app}\{#NamaExe}"; Tasks: desktopicon; Comment: "{#Deskripsi}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#NamaAplikasi}"; Filename: "{app}\{#NamaExe}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#NamaExe}"; Description: "Jalankan {#NamaAplikasi} sekarang"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Tidak ada proses yang perlu dihentikan otomatis

[Code]
// ---------------------------------------------------------------------------
// Cek apakah aplikasi sedang berjalan sebelum instalasi/uninstalasi
// ---------------------------------------------------------------------------
function AplikasiBerjalan(): Boolean;
var
  Hasil: Integer;
begin
  Result := False;
  if Exec('cmd.exe', '/c tasklist /FI "IMAGENAME eq {#NamaExe}" | find /i "{#NamaExe}" >nul',
          '', SW_HIDE, ewWaitUntilTerminated, Hasil) then
    Result := (Hasil = 0);
end;

function InitializeSetup(): Boolean;
var
  VersiWindows: TWindowsVersion;
  Pesan: String;
  BarisBaru: String;
begin
  Result := True;

  // Qt 6 memerlukan Windows 10 versi 1809 (build 17763) atau lebih baru.
  // Pemeriksaan ini memberi pesan yang jelas, bukan kegagalan diam.
  GetWindowsVersionEx(VersiWindows);
  if VersiWindows.Major < 10 then
  begin
    MsgBox('AkunTuntas memerlukan Windows 10 atau Windows 11.' + #13#10#13#10 +
           'Komputer ini memakai Windows versi lama yang belum didukung.' + #13#10#13#10 +
           'Silakan pasang di komputer bersistem Windows 10 versi 1809 ' +
           'atau lebih baru.',
           mbCriticalError, MB_OK);
    Result := False;
    exit;
  end;

  if (VersiWindows.Major = 10) and (VersiWindows.Build < 17763) then
  begin
    // Pakai Chr(13)+Chr(10) dan bukan #13#10 karena Inno Setup membaca tanda
    // pagar di awal baris sebagai perintah preprocessor.
    BarisBaru := Chr(13) + Chr(10);
    Pesan := 'AkunTuntas memerlukan Windows 10 versi 1809 atau lebih baru.' +
             BarisBaru + BarisBaru +
             'Versi Windows di komputer ini: ' +
             IntToStr(VersiWindows.Major) + '.' + IntToStr(VersiWindows.Minor) +
             ' (build ' + IntToStr(VersiWindows.Build) + ').' +
             BarisBaru + BarisBaru +
             'Silakan perbarui Windows lewat Windows Update, lalu jalankan ' +
             'pemasangan ini lagi.';
    MsgBox(Pesan, mbCriticalError, MB_OK);
    Result := False;
    exit;
  end;

  if AplikasiBerjalan() then
  begin
    if MsgBox('Aplikasi AkunTuntas sedang berjalan.' + #13#10#13#10 +
              'Tutup aplikasi terlebih dahulu sebelum melanjutkan instalasi.' + #13#10#13#10 +
              'Klik OK setelah aplikasi ditutup, atau Batal untuk membatalkan.',
              mbError, MB_OKCANCEL) = IDCANCEL then
      Result := False;
  end;
end;

// ---------------------------------------------------------------------------
// Tawarkan membuat cadangan data sebelum uninstall
// ---------------------------------------------------------------------------
function InitializeUninstall(): Boolean;
var
  FolderData: String;
  FolderCadangan: String;
  Hasil: Integer;
begin
  Result := True;
  FolderData := ExpandConstant('{localappdata}\AkunTuntas');

  if DirExists(FolderData) then
  begin
    { Mode senyap: jangan tanya apa pun, cukup cadangkan data lalu lanjut. }
    if UninstallSilent then
    begin
      FolderCadangan := ExpandConstant('{userdocs}\Cadangan AkunTuntas');
      if not DirExists(FolderCadangan) then
        ForceDirectories(FolderCadangan);
      Exec('cmd.exe',
           '/c xcopy "' + FolderData + '" "' + FolderCadangan + '" /E /I /Y',
           '', SW_HIDE, ewWaitUntilTerminated, Hasil);
      exit;
    end;

    if MsgBox('Ditemukan data pembukuan Anda di:' + #13#10 +
              FolderData + #13#10#13#10 +
              'Data ini TIDAK akan dihapus oleh proses uninstall.' + #13#10#13#10 +
              'Buat cadangan data terlebih dahulu sebelum melanjutkan?',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      FolderCadangan := ExpandConstant('{userdocs}\Cadangan AkunTuntas');
      if not DirExists(FolderCadangan) then
        ForceDirectories(FolderCadangan);
      if Exec('cmd.exe',
              '/c xcopy "' + FolderData + '" "' + FolderCadangan + '" /E /I /Y',
              '', SW_HIDE, ewWaitUntilTerminated, Hasil) then
        MsgBox('Cadangan data disimpan di:' + #13#10 + FolderCadangan,
               mbInformation, MB_OK)
      else
        MsgBox('Cadangan gagal dibuat. Salin folder data secara manual.',
               mbError, MB_OK);
    end;

    if MsgBox('Hapus juga seluruh data pembukuan?' + #13#10#13#10 +
              'PERINGATAN: tindakan ini TIDAK DAPAT dibatalkan.' + #13#10 +
              FolderData, mbConfirmation, MB_YESNO) = IDYES then
    begin
      DelTree(FolderData, True, True, True);
      MsgBox('Seluruh data pembukuan telah dihapus.', mbInformation, MB_OK);
    end;
  end;
end;

// ---------------------------------------------------------------------------
// Tampilkan informasi lokasi data pada halaman akhir
// ---------------------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // buat folder data agar pengguna mudah menemukannya
    ForceDirectories(ExpandConstant('{localappdata}\AkunTuntas'));
    ForceDirectories(ExpandConstant('{localappdata}\AkunTuntas\backup'));
  end;
end;
