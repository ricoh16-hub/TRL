param(
    [string]$AgentFilePath = "",
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($AgentFilePath)) {
    $AgentFilePath = Join-Path $env:USERPROFILE '.vscode\extensions\ms-windows-ai-studio.windows-ai-studio-0.34.0-win32-x64\resources\lmt\chatAgents\AIAgentExpert.agent.md'
}

if (-not (Test-Path $AgentFilePath)) {
    throw "File agent tidak ditemukan: $AgentFilePath"
}

$content = Get-Content -Path $AgentFilePath -Raw
$pattern = '\[Microsoft Foundry: Deploy Hosted Agent\]\(azure-ai-foundry\.commandPalette\.deployWorkflow\)'
$replacement = 'Microsoft Foundry: Deploy Hosted Agent'

$match = [regex]::Match($content, $pattern)
if (-not $match.Success) {
    if ($content -match 'use the Microsoft Foundry: Deploy Hosted Agent command from the VS Code Command Palette') {
        Write-Output 'PATCH_ALREADY_APPLIED'
        Write-Output "TARGET=$AgentFilePath"
        exit 0
    }

    throw 'Pola link rusak tidak ditemukan. Kemungkinan versi extension sudah berubah.'
}

$updated = [regex]::Replace($content, $pattern, $replacement, 1)

if ($DryRun) {
    Write-Output 'PATCH_PREVIEW_OK'
    Write-Output "TARGET=$AgentFilePath"
    exit 0
}

$backupPath = "$AgentFilePath.bak"
if (-not (Test-Path $backupPath)) {
    Copy-Item -Path $AgentFilePath -Destination $backupPath -Force
}

Set-Content -Path $AgentFilePath -Value $updated -Encoding utf8

Write-Output 'PATCH_APPLIED'
Write-Output "TARGET=$AgentFilePath"
Write-Output "BACKUP=$backupPath"