# Installs the "load" and "run" commands on Windows. Run once in PowerShell:
#   irm https://raw.githubusercontent.com/tianksongo-sketch/tetrispy/main/install.ps1 | iex

$GhUser  = "tianksongo-sketch"
$Repo    = "tetrispy"
$Raw     = "https://raw.githubusercontent.com/$GhUser/$Repo/main"
$BinDir  = Join-Path $HOME "bin"

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

# 'load' and 'run' are small PowerShell/batch files kept in ~\bin
curl.exe -fsSL "$Raw/load.ps1" -o (Join-Path $BinDir "load.ps1")
if ($LASTEXITCODE -ne 0) { Write-Host "Download failed: $Raw/load.ps1"; return }

$runCmd = @'
@echo off
if "%~1"=="" (
  echo usage: run ^<game^>      example: run tetris
  exit /b 1
)
set "GAME=%USERPROFILE%\games\%~1\%~1.py"
if not exist "%GAME%" (
  echo %~1 is not installed. Type: load %~1
  exit /b 1
)
set "PY=python"
where python >nul 2>nul || set "PY=py"
"%PY%" "%GAME%" %2 %3 %4 %5 %6 %7 %8 %9
'@
Set-Content -Path (Join-Path $BinDir "run.cmd") -Value $runCmd -Encoding ASCII
Write-Host "Installed: $BinDir\load.ps1 and $BinDir\run.cmd"

# 'load' command in the PowerShell profile (added once)
$profileDir = Split-Path $PROFILE
New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Force -Path $PROFILE | Out-Null }
$fn = 'function load { & "$HOME\bin\load.ps1" @args }'
if (-not (Select-String -Path $PROFILE -Pattern 'load\.ps1' -Quiet)) {
  Add-Content -Path $PROFILE -Value $fn
}

# 'run' command: add the bin folder to your user PATH (added once)
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
  [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinDir", "User")
}

Write-Host "Done. Open a new PowerShell window, then type:  load tetris   and later:  run tetris"
