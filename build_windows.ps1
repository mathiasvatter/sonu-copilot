$ErrorActionPreference = 'Stop'

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $rootDir

if (Test-Path 'dist') {
    Remove-Item -Recurse -Force 'dist'
}

$appName = 'Sonu Co-Pilot'
$entryPoint = 'main.py'
$iconPath = 'icons/sonu.ico'
$appVersion = '0.0.1'

$activateScripts = @(
    '.venv/Scripts/Activate.ps1',
    'venv/Scripts/Activate.ps1'
)

foreach ($script in $activateScripts) {
    if (Test-Path $script) {
        . $script
        break
    }
}

python -m pip install --upgrade pyinstaller

pyinstaller `
  --noconfirm `
  --clean `
  --windowed `
  --onefile `
  --name "$appName" `
  --icon "$iconPath" `
  --add-data "icons;icons" `
  --add-data "theme;theme" `
  --paths "$rootDir" `
  "$entryPoint"

if (Test-Path 'build') {
    Remove-Item -Recurse -Force 'build'
}

$specPath = Join-Path $rootDir ("$appName.spec")
if (Test-Path $specPath) {
    Remove-Item -Force $specPath
}

Write-Host "Build complete: dist/$appName/$appName.exe (Version $appVersion)"
