function ConvertTo-PlainText {
    param(
        [System.Security.SecureString]$SecureValue
    )

    if ($null -eq $SecureValue) {
        return $null
    }

    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    }
    finally {
        if ($bstr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }
}

function Get-ProjectRoot {
    return (Split-Path -Parent $PSScriptRoot)
}

function Get-PythonExe {
    $projectRoot = Get-ProjectRoot
    $venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (Test-Path $venvPython) {
        return $venvPython
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }

    throw 'Python executable tidak ditemukan. Pastikan virtual environment sudah tersedia.'
}

function Invoke-AlembicCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$AlembicArgs,
        [string]$AdminUser,
        [System.Security.SecureString]$AdminPassword
    )

    $projectRoot = Get-ProjectRoot
    $pythonExe = Get-PythonExe

    Push-Location $projectRoot
    try {
        if ([string]::IsNullOrWhiteSpace($AdminUser) -eq $false) {
            $env:DB_ADMIN_USER = $AdminUser
        }
        $plainPassword = ConvertTo-PlainText $AdminPassword
        if ([string]::IsNullOrWhiteSpace($plainPassword) -eq $false) {
            $env:DB_ADMIN_PASSWORD = $plainPassword
        }

        & $pythonExe -m alembic @AlembicArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Alembic command gagal dengan exit code $LASTEXITCODE"
        }
    }
    finally {
        Remove-Item Env:DB_ADMIN_USER -ErrorAction SilentlyContinue
        Remove-Item Env:DB_ADMIN_PASSWORD -ErrorAction SilentlyContinue
        Pop-Location
    }
}

function Read-AdminPassword {
    return (Read-Host 'Masukkan DB admin password' -AsSecureString)
}
