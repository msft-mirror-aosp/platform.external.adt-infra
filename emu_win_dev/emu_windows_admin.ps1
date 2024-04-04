# Configure gWindows for Android Emulator Windows Development

# Execute the script from a non-admin shell. 
# Admin privileges will be requested when needed.

function Emu-Windows-Admin-Tasks {

  Write-Output "Running administrator tasks`n"

  # Disable Windows Defender Real-time monitoring
  Set-MpPreference -DisableRealtimeMonitoring $true
  
  # Enable developer mode.
  Write-Output "`nEnabling developer mode ..."
  & reg add 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock' /t REG_DWORD /f /v 'AllowDevelopmentWithoutDevLicense' /d '1'

  # Enable long paths.
  Write-Output "`nEnabling long paths ..."
  & reg add 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem' /t REG_DWORD /f /v 'LongPathsEnabled' /d '1'

  # Install Chocolatey
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

  ## Install curl
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
  
  # Install certifi
  Write-Host "`nInstalling certifi..."
  pip install certifi
  $cert_path = python -c "import certifi; print(certifi.where())"
  [Environment]::SetEnvironmentVariable('REQUESTS_CA_BUNDLE', $cert_path)
  [Environment]::SetEnvironmentVariable('SSL_CERT_FILE', $cert_path)  

  # Apply System-wide Git configurations
  Write-Output "`nApplying system-wide git configurations ..."
  ### Make sure symlink option is on
  $env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
  git config --system core.symlinks true
  
  ## Add %USERPROFILE%\bin to PATH
  Write-Output "`nAdding %USERPROFILE%\bin to PATH ..."
  $CurMachinePath = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
  $Env:Path = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
  $UserProfileBinPath = $env:USERPROFILE + '\bin'
  if (-Not ($CurMachinePath -split ";" -contains $UserProfileBinPath)) {
     Write-Output "`nAdding "%USERPROFILE%\bin" to Path"
     [Environment]::SetEnvironmentVariable('Path', $CurMachinePath + ';' + $UserProfileBinPath, 'Machine')
  }

  Write-Output "`nAll admistrator tasks were completed successfully"
  Start-Sleep 5
}

function Emu-Windows-User-Tasks {

  $FullName = $args[$args.IndexOf("-FullName") + 1]
  $Email = $args[$args.IndexOf("-Email") + 1]
  
  Write-Output "`nRunning regular user tasks"
  Start-Sleep 1
  
  ## Configure Git
  Write-Output "`nConfiguring Git ..."

  ### Make sure symlink option is on
  $env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine')

  git config --global user.name $FullName
  git config --global user.email $Email
  git config --global core.symlinks true
  git config --global core.longpaths true
  
  # Obtaining Repo for Windows

  Write-Host "`nInstalling repo..."

  if (-not (Test-Path "$env:USERPROFILE\bin")) {
      New-Item "$env:USERPROFILE\bin" -ItemType Directory > $null
  }

  Push-Location "$env:USERPROFILE\bin"
  curl -o repo http://storage.googleapis.com/git-repo-downloads/repo
  '@call python %~dp0repo %*' | Out-File -FilePath "$env:USERPROFILE\bin\repo.cmd" -Encoding OEM
  Pop-Location

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
   
}

# Script begins here
# Self-elevating routine based on:
# https://learn.microsoft.com/en-us/archive/blogs/virtual_pc_guy/a-self-elevating-powershell-script

$ErrorActionPreference = 'Stop'
$ConfirmPreference = 'None'

# Get the ID and security principal of the current user account
$myWindowsID = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$myWindowsPrincipal = new-object System.Security.Principal.WindowsPrincipal($myWindowsID)
 
# Get the security principal for the Administrator role
$adminRole = [System.Security.Principal.WindowsBuiltInRole]::Administrator
  
# Check to see if we are currently running "as Administrator"
if ($myWindowsPrincipal.IsInRole($adminRole)) {

    if (-not ($args -contains "-admin")) {
      # Running as an admistrator is only allowed when the script calls itself with the "-admin" parameter.
      throw 'Please DO NOT run this script with administrator privileges. We will request elevation when needed.'
    }    
    Start-Sleep 3
    $Host.UI.RawUI.WindowTitle = $myInvocation.MyCommand.Definition + " (Administrator tasks)"

    try {
      Emu-Windows-Admin-Tasks
    } 
    catch {
      Write-Host "$($_.Exception.Message)"
      Start-Sleep 15
      exit 1
    }

} else {
    # Regular (initial) flow        
    Write-Output "`nStarted script '$($myInvocation.MyCommand.name)' as a regular user"
    
    $FullName = Read-Host "`n[git config] Please enter your full name" # for later use
    $Email = Read-Host "`n[git config] Please enter your email" # for later use
    
    # Create ae new process that will perform admistrative tasks
    $newProcess = new-object System.Diagnostics.ProcessStartInfo "PowerShell";
    
    # Specify the current script path and name as a parameter
    $newProcess.Arguments =  "$($myInvocation.MyCommand.Definition) -admin"
    
    # Indicate that the process should be elevated
    $newProcess.Verb = "runas"    
   
    # Start the process
    Write-Output "`nRunning Administrator tasks ..."
    Write-Output "`nStarting a new process will Admin privileges ..."
    $p = [System.Diagnostics.Process]::Start($newProcess)    
    
    # Check the status of the admin subprocess
    if ($p -eq $null) {
        Write-Error "Failed to start the subprocess."     
        exit 1
    }
    Start-Sleep 5    
    $p.WaitForExit();   
        
    if ($p.ExitCode -ne 0) {
        exit 1
    }
    Write-Output "`nAdministrator tasks completed!"
    
    Write-Output "`nPerforming additional tasks"
    Start-Sleep 3
    Emu-Windows-User-Tasks -FullName $FullName -Email $Email
}

Write-Output "`nThe script $($myInvocation.MyCommand.name) finished successfully!"

