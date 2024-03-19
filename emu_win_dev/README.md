 # Emulator Windows Development

 Powershell scripts to configure Windows for Android Emulator Windows Development.

`emu_windows.ps1`

The script `emu_windows.ps1` is designed for non-gWindows machines, specifically those where a
regular user can start PowerShell with admin rights. When executed, the script will inherit admin
rights from the calling shell, allowing it to perform all configuration tasks as an administrator.

 `emu_windows_admin.ps1`

This script is tailored for use on a gWindows machine where regular users lack the ability
to run PowerShell as administrators. However, they are able to accept the Windows UAC
prompt when necessary. In this version, tasks requiring regular user privileges and those
that need admin rights are divided into two independent functions. For administrative tasks,
the script invokes itself as an independent process, prompting the UAC Windows prompt.

