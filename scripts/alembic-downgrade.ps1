param(
    [string]$Revision = '-1',
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

Invoke-AlembicCommand -AlembicArgs @('downgrade', $Revision) -AdminUser $AdminUser -AdminPassword $AdminPassword
