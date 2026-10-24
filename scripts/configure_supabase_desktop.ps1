$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot ".env"

if (-not (Test-Path $envPath)) {
    throw "Arquivo .env não encontrado. Abra o terminal na pasta do projeto e copie .env.example para .env antes de executar este script."
}

$lines = [System.Collections.Generic.List[string]]::new()
Get-Content -LiteralPath $envPath | ForEach-Object { $lines.Add($_) }

function Get-EnvValue([string]$Name) {
    foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Name))=(.*)$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return ""
}

function Set-EnvValue([string]$Name, [string]$Value) {
    $pattern = "^\s*$([regex]::Escape($Name))="
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $lines[$i] = "$Name=$Value"
            return
        }
    }
    $lines.Add("$Name=$Value")
}

$ownerId = Get-EnvValue "ATLAS_OWNER_USER_ID"
if ([string]::IsNullOrWhiteSpace($ownerId)) {
    $ownerId = Read-Host "UUID do seu usuário no Supabase Auth"
}
if ($ownerId -notmatch '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$') {
    throw "ATLAS_OWNER_USER_ID não parece ser um UUID válido."
}

$serviceRole = Get-EnvValue "SUPABASE_SERVICE_ROLE_KEY"
if ([string]::IsNullOrWhiteSpace($serviceRole)) {
    $secureValue = Read-Host "Cole a chave service_role do projeto Atlas AI (entrada oculta)" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
    try {
        $serviceRole = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}
if ([string]::IsNullOrWhiteSpace($serviceRole)) {
    throw "A chave service_role é obrigatória para o modo pessoal sem login."
}

Set-EnvValue "ATLAS_API_HOST" "127.0.0.1"
Set-EnvValue "ATLAS_MEMORY_BACKEND" "supabase"
Set-EnvValue "ATLAS_DESKTOP_NO_LOGIN" "true"
Set-EnvValue "ATLAS_OWNER_USER_ID" $ownerId
Set-EnvValue "SUPABASE_URL" "https://bsjsskufdaycdaymmhwe.supabase.co"
Set-EnvValue "SUPABASE_KEY" "sb_publishable_5klSiVUGEq6ulu_fsZU-4A_E4qmruKY"
Set-EnvValue "SUPABASE_SERVICE_ROLE_KEY" $serviceRole

[System.IO.File]::WriteAllLines($envPath, $lines, [System.Text.UTF8Encoding]::new($false))
Write-Host ""
Write-Host "Configuração salva em .env." -ForegroundColor Green
Write-Host "A chave administrativa não foi exibida. Não envie .env ao GitHub."
Write-Host "Reinicie o backend e abra o Atlas AI."
