# Installs the "load" and "run" commands on Windows. Run once in PowerShell:
#   irm https://raw.githubusercontent.com/tianksongo-sketch/tetrispy/main/install.ps1 | iex

$GhUser  = "tianksongo-sketch"
$Raw     = "https://raw.githubusercontent.com/$GhUser/tetrispy/main"
$BinDir  = Join-Path $HOME "bin"

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
curl.exe -fsSL "$Raw/load.ps1" -o (Join-Path $BinDir "load.ps1")
if ($LASTEXITCODE -ne 0) { Write-Host "Download failed: $Raw/load.ps1"; return }
Write-Host "Installed: $BinDir\load.ps1"

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

Write-Host "Done. Open a new PowerShell window, then type:  load tetris   and then:  run"
