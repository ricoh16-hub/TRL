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

$commandArguments = @('revision', '-m', $Message)
if ($Autogenerate) {
    $commandArguments += '--autogenerate'
}

Invoke-AlembicCommand -AlembicArgs $commandArguments -AdminUser $AdminUser -AdminPassword $AdminPassword
