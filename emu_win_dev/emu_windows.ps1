# Configure non-gWindows for Android Emulator Windows Development.
# Execute the script from Powershell with admin rights.

#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$ConfirmPreference = 'None'

# Disable Windows Defender Real-time monitoring.
Set-MpPreference -DisableRealtimeMonitoring $true

# Enable developer mode.
Write-Output "`nEnabling developer mode ..."
& reg add 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock' /t REG_DWORD /f /v 'AllowDevelopmentWithoutDevLicense' /d '1'

# Enable long paths.
Write-Output "`nEnabling long paths ..."
& reg add 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem' /t REG_DWORD /f /v 'LongPathsEnabled' /d '1'

# MAIN WINDOWS EMU TASKS

$FullName = Read-Host '[git config] Please enter your full name'
$Email = Read-Host '[git config] Please enter your email'

## Install Chocolatey

try {
    choco
}
catch {
    Write-Output "`nInstalling Chocolatey"
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    choco feature enable -n allowGlobalConfirmation
}

## Install Visual Studio 2019
Write-Output "`nInstalling Visual Studio 2019"
choco install visualstudio2019-workload-vctools

Write-Output "`nInstalling curl"
choco install curl

## Install Git
Write-Output "`nInstalling Git ..."
choco install git

## Install Python3
Write-Output "`nInstalling Python 3 ..."
choco install python312 --params="'/InstallDir:C:\python3'"
Write-Output "`nCreate Python3 symbolic link"
New-Item -ItemType SymbolicLink -Path 'C:\python3\python3.exe' -Target 'C:\python3\python.exe' -Force > $null

## Install VSCode
Write-Output "`nInstalling VS Code ..."
choco install vscode vscode-cpptools
Write-Output "`nInstalling VS Code plugins ..."
$env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
code --install-extension 'ms-vscode.cpptools'
code --install-extension 'ms-vscode.cmake-tools'

## Install Rust
Write-Output "`nInstalling Rust ..."
choco install rust-ms
## Add '.cargo\bin' to Path
$CurMachinePath = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
$CargoBinPath = $env:USERPROFILE + '\.cargo\bin'
if (-Not ($CurMachinePath -split ";" -contains $CargoBinPath)) {
   Write-Output "`nAdding '.cargo\bin' to Path"
   [Environment]::SetEnvironmentVariable('Path', $CurMachinePath + ';' + $UserProfileBinPath, 'User') > $null
}

## Configure Git
Write-Output "`nConfiguring Git ..."

### Make sure symlink option is on
$env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine')

git config --global user.name $FullName
git config --global user.email $Email
git config --global core.symlinks true
git config --system core.symlinks true
git config --global core.longpaths true

# Installing certifi
Write-Host "`nInstalling certifi..."
pip install certifi
$cert_path = python -c "import certifi; print(certifi.where())"
[Environment]::SetEnvironmentVariable('REQUESTS_CA_BUNDLE', $cert_path)
[Environment]::SetEnvironmentVariable('SSL_CERT_FILE', $cert_path)

# Obtaining Repo for Windows

Write-Host "`nInstalling repo..."

if (-not (Test-Path "$env:USERPROFILE\bin")) {
    New-Item "$env:USERPROFILE\bin" -ItemType Directory > $null
}

Push-Location "$env:USERPROFILE\bin"
curl -o repo http://storage.googleapis.com/git-repo-downloads/repo
'@call python %~dp0repo %*' | Out-File -FilePath "$env:USERPROFILE\bin\repo.cmd" -Encoding OEM
Pop-Location

## Add %USERPROFILE%\bin to PATH
$CurMachinePath = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
$Env:Path = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
$UserProfileBinPath = $env:USERPROFILE + '\bin'
if (-Not ($CurMachinePath -split ";" -contains $UserProfileBinPath)) {
   Write-Output "`nAdding "%USERPROFILE%\bin" to Path"
   [Environment]::SetEnvironmentVariable('Path', $CurMachinePath + ';' + $UserProfileBinPath, 'Machine')
}

## Initialize the repository

if (-not (Test-Path "$env:USERPROFILE\src\emu-master-dev")) {
    Write-Output "`nCreating 'emu-master-dev' folder ..."
    New-Item "$env:USERPROFILE\src\emu-master-dev" -ItemType Directory -Force > $null
}

Push-Location "$env:USERPROFILE\src\emu-master-dev"
Write-Output "`nInitializing the repository"
$Env:Path = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
repo init -u https://android.googlesource.com/platform/manifest -b emu-master-dev

## Sync the repository

Write-Output "`nSyncing the repository"
repo sync --no-tags --optimized-fetch --prune
Push-Location ".\external\qemu"
android\rebuild
Pop-Location
Pop-Location

