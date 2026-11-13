# load.ps1 - Windows version of "load". Downloads a game and starts it.
#   load tetris     ->  downloads and starts tetris
#   run             ->  starts the last loaded game again
param([string]$Name)

$GhUser   = "tianksongo-sketch"
$Repo     = "tetrispy"
$GamesDir = Join-Path $HOME "games"
$BinDir   = Join-Path $HOME "bin"

if (-not $Name) { Write-Host "usage: load <game>      example: load tetris"; exit 1 }
if ($Name -notmatch '^[a-zA-Z0-9_-]+$') { Write-Host "invalid game name: $Name"; exit 1 }

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) { Write-Host "Python 3 is required."; exit 1 }
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) { Write-Host "curl.exe is required (Windows 10 or newer)."; exit 1 }

$url = "https://raw.githubusercontent.com/$GhUser/$Repo/main/$Name/$Name.py"
$dir = Join-Path $GamesDir $Name
New-Item -ItemType Directory -Force -Path $dir, $BinDir | Out-Null
$target = Join-Path $dir "$Name.py"

Write-Host "Downloading $Name ..."
curl.exe -fsSL $url -o $target
if ($LASTEXITCODE -ne 0) { Write-Host "Download failed: $url"; exit 1 }

# 'run' starts the most recently loaded game
$runCmd = "@echo off`r`n`"$($py.Source)`" `"$target`" %*"
Set-Content -Path (Join-Path $BinDir "run.cmd") -Value $runCmd -Encoding ASCII

if ($env:Path -notlike "*$BinDir*") {
  Write-Host "Tip: add $BinDir to your PATH so 'run' works everywhere."
}

Write-Host "Starting $Name ... (next time, just type: run)"
& $py.Source $target
