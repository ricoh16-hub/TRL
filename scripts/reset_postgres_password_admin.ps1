[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingPlainTextForPassword', 'NewPassword', Justification='Script intentionally updates a local .env file with the generated PostgreSQL password.')]
param(
    [string]$NewPassword = "",
    [string]$PgVersion = "16",
    [string]$DbUser = "postgres",
    [string]$DbName = "app_db",
    [string]$EnvFilePath = "",
    [string]$LogFile = ""
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($EnvFilePath)) {
    $EnvFilePath = Join-Path $projectRoot '.env'
}
if ([string]::IsNullOrWhiteSpace($LogFile)) {
    $LogFile = Join-Path $projectRoot 'reset_postgres_admin.log'
}

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    Write-Output $line
    Add-Content -Path $LogFile -Value $line
}

Set-Content -Path $LogFile -Value ""

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Script ini harus dijalankan di PowerShell 'Run as Administrator'."
}

Write-Log "Running with Administrator privileges"

if ([string]::IsNullOrWhiteSpace($NewPassword)) {
    $NewPassword = "Pg#" + ([Guid]::NewGuid().ToString('N').Substring(0, 12))
}

$root = "C:\Program Files\PostgreSQL\$PgVersion"
$hba = Join-Path $root "data\pg_hba.conf"
$psql = Join-Path $root "bin\psql.exe"
$pgctl = Join-Path $root "bin\pg_ctl.exe"
$serviceName = "postgresql-x64-$PgVersion"
$backup = "$hba.copilot.bak"
$envFile = $EnvFilePath
$dataDir = Join-Path $root "data"

if (-not (Test-Path $hba)) { throw "pg_hba.conf tidak ditemukan: $hba" }
if (-not (Test-Path $psql)) { throw "psql tidak ditemukan: $psql" }
if (-not (Test-Path $pgctl)) { throw "pg_ctl tidak ditemukan: $pgctl" }

Write-Log "Found PostgreSQL files for version $PgVersion"

Copy-Item $hba $backup -Force
Write-Log "Backup created: $backup"

try {
    $raw = Get-Content $hba -Raw
    $raw = $raw -replace '(?m)^(host\s+all\s+all\s+127\.0\.0\.1/32\s+)scram-sha-256', '$1trust'
    $raw = $raw -replace '(?m)^(host\s+all\s+all\s+::1/128\s+)scram-sha-256', '$1trust'
    Set-Content $hba $raw -Encoding ASCII
    Write-Log "Temporarily changed localhost auth to trust"

    & $pgctl reload -D $dataDir | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "pg_ctl reload gagal saat set trust (exit=$LASTEXITCODE)"
    }
    Write-Log "PostgreSQL config reloaded (trust active)"

    $probeOutput = & $psql -h localhost -U $DbUser -d postgres -c "SELECT current_user;" 2>&1
    $probeExit = $LASTEXITCODE
    foreach ($line in $probeOutput) { Write-Log ("psql probe: " + $line) }
    if ($probeExit -ne 0) {
        throw "Koneksi psql probe gagal saat mode trust (exit=$probeExit)"
    }

    $alterOutput = & $psql -h localhost -U $DbUser -d postgres -c "ALTER USER $DbUser WITH PASSWORD '$NewPassword';" 2>&1
    $alterExit = $LASTEXITCODE
    foreach ($line in $alterOutput) { Write-Log ("psql alter: " + $line) }
    if ($alterExit -ne 0) {
        throw "ALTER USER gagal (exit=$alterExit)"
    }
    Write-Log "Password for user '$DbUser' updated"

    $restore = Get-Content $hba -Raw
    $restore = $restore -replace '(?m)^(host\s+all\s+all\s+127\.0\.0\.1/32\s+)trust', '$1scram-sha-256'
    $restore = $restore -replace '(?m)^(host\s+all\s+all\s+::1/128\s+)trust', '$1scram-sha-256'
    Set-Content $hba $restore -Encoding ASCII
    Write-Log "Restored localhost auth to scram-sha-256"

    & $pgctl reload -D $dataDir | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "pg_ctl reload gagal saat restore scram (exit=$LASTEXITCODE)"
    }
    Write-Log "PostgreSQL config reloaded (scram active)"

    @(
        "DB_USER=$DbUser",
        ('DB_PASSWORD="' + $NewPassword + '"'),
        "DB_HOST=localhost",
        "DB_PORT=5432",
        "DB_NAME=$DbName"
    ) | Set-Content -Path $envFile -Encoding ASCII
    Write-Log "Updated .env file: $envFile"

    $env:PGPASSWORD = $NewPassword
    $verifyOutput = & $psql -h localhost -U $DbUser -d postgres -c "SELECT current_user;" 2>&1
    $verifyExit = $LASTEXITCODE
    foreach ($line in $verifyOutput) { Write-Log ("psql verify: " + $line) }
    if ($verifyExit -ne 0) {
        throw "Verifikasi login psql gagal setelah reset password (exit=$verifyExit)"
    }
    Write-Log "Verified psql login with new password"

    Write-Output "RESET_OK"
    Write-Output "UPDATED_ENV=$envFile"
    Write-Output "NEW_PASSWORD=$NewPassword"
    Write-Log "RESET_OK"
}
catch {
    Write-Log ("ERROR: " + $_.Exception.Message)
    if (Test-Path $backup) {
        Copy-Item $backup $hba -Force
        Write-Log "pg_hba.conf restored from backup"
        try {
            & $pgctl reload -D $dataDir | Out-Null
            Write-Log "PostgreSQL config reloaded after rollback"
        } catch {
            Write-Log ("WARN: reload after rollback gagal: " + $_.Exception.Message)
            try {
                Restart-Service -Name $serviceName -Force
                Write-Log "Service restarted after rollback"
            } catch {
                Write-Log ("WARN: service restart after rollback gagal: " + $_.Exception.Message)
            }
        }
    }
    throw
}
