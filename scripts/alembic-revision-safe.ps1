param(
    [Parameter(Mandatory = $true)]
    [string]$Message,
    [switch]$Autogenerate,
    [string]$AdminUser,
    [System.Security.SecureString]$AdminPassword
)

. "$PSScriptRoot\alembic-common.ps1"

if ($AdminUser -and $null -eq $AdminPassword -and $env:DB_ADMIN_PASSWORD) {
    $AdminPassword = ConvertTo-SecureString $env:DB_ADMIN_PASSWORD -AsPlainText -Force
}

if ($AdminUser -and $null -eq $AdminPassword) {
    $AdminPassword = Read-AdminPassword
}

$revisionArgs = @('revision', '-m', $Message)
if ($Autogenerate) {
    $revisionArgs += '--autogenerate'
}

Invoke-AlembicCommand -AlembicArgs $revisionArgs -AdminUser $AdminUser -AdminPassword $AdminPassword

$projectRoot = Get-ProjectRoot
$latestRevision = Get-ChildItem (Join-Path $projectRoot 'alembic\versions') -File |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1

if ($latestRevision) {
    Write-Host "Revision terbaru: $($latestRevision.FullName)" -ForegroundColor Green
}

Write-Host ''
Write-Host 'Checklist aman setelah membuat revision:' -ForegroundColor Yellow
Write-Host '1. Review upgrade() dan downgrade().' -ForegroundColor Yellow
Write-Host '2. Hindari operasi destructive dalam satu step bila bisa dibuat bertahap.' -ForegroundColor Yellow
Write-Host '3. Untuk kolom NOT NULL: add nullable -> backfill -> set NOT NULL.' -ForegroundColor Yellow
Write-Host '4. Jalankan alembic upgrade head di environment uji sebelum production.' -ForegroundColor Yellow
