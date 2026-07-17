$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Venv = Join-Path $Root "desktop\.venv-build"
$Python = Join-Path $Venv "Scripts\python.exe"
$ReleaseBackend = Join-Path $Root "desktop\release\backend\ScholarNovaBackend"
$DistBackend = Join-Path $Root "dist\ScholarNovaBackend"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [ScriptBlock] $Command
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

function New-BuildVenv {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        Invoke-Checked { py -3.12 -m venv $Venv }
    } else {
        Invoke-Checked { python -m venv $Venv }
    }
}

if (Test-Path $Python) {
    $PreviousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & $Python -c "import sys, pip; import pip._internal.operations.build; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
    $BuildVenvExitCode = $LASTEXITCODE
    $ErrorActionPreference = $PreviousErrorAction
    if ($BuildVenvExitCode -ne 0) {
        Remove-Item -LiteralPath $Venv -Recurse -Force
        New-BuildVenv
    }
} else {
    New-BuildVenv
}

Invoke-Checked { & $Python -m ensurepip --upgrade }
Invoke-Checked { & $Python -m pip install --upgrade pip }
Invoke-Checked { & $Python -m pip install -r (Join-Path $Root "requirements-lock.txt") }
Invoke-Checked { & $Python -m pip install -e (Join-Path $Root "backend") --no-deps }
Invoke-Checked { & $Python -m pip install pyinstaller }
Invoke-Checked { & $Python -m PyInstaller (Join-Path $Root "scripts\packaging\ScholarNovaBackend.spec") --noconfirm --clean }

if (Test-Path $ReleaseBackend) {
    Remove-Item -LiteralPath $ReleaseBackend -Recurse -Force
}
New-Item -ItemType Directory -Force -Path (Split-Path $ReleaseBackend) | Out-Null
Copy-Item -LiteralPath $DistBackend -Destination $ReleaseBackend -Recurse -Force
