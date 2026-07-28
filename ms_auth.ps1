# ============================================================================
#  ms_auth.ps1  —  obtiene el REFRESH TOKEN de una cuenta Microsoft (Outlook/
#  Hotmail) usando el flujo device-code. NO instala nada (solo PowerShell).
#
#  Uso:   click derecho -> "Ejecutar con PowerShell"
#         o:  powershell -ExecutionPolicy Bypass -File ms_auth.ps1
#
#  Córrelo UNA VEZ POR CADA cuenta (hotmail y outlook.es).
#  Al final imprime el refresh token -> guárdalo como secret en GitHub.
# ============================================================================
$ErrorActionPreference = "Stop"

$clientId = Read-Host "Pega tu Application (client) ID de Azure"
$scope = "Mail.ReadWrite offline_access User.Read"

# 1) Pide el código de dispositivo
$dc = Invoke-RestMethod -Method Post `
    -Uri "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode" `
    -Body @{ client_id = $clientId; scope = $scope }

Write-Host ""
Write-Host "=== AUTORIZA LA CUENTA ===" -ForegroundColor Cyan
Write-Host "1) Abre en el navegador:  $($dc.verification_uri)" -ForegroundColor Cyan
Write-Host "2) Ingresa este codigo:   $($dc.user_code)" -ForegroundColor Yellow
Write-Host "3) Inicia sesion con la cuenta correcta y acepta los permisos."
Write-Host ""
Write-Host "Esperando a que autorices..." -ForegroundColor DarkGray

# 2) Espera (polling) a que el usuario autorice
$interval = [int]$dc.interval
$token = $null
while ($true) {
    Start-Sleep -Seconds $interval
    try {
        $token = Invoke-RestMethod -Method Post `
            -Uri "https://login.microsoftonline.com/common/oauth2/v2.0/token" `
            -Body @{
                grant_type  = "urn:ietf:params:oauth:grant-type:device_code"
                client_id   = $clientId
                device_code = $dc.device_code
            }
        break
    } catch {
        $err = $null
        try { $err = $_.ErrorDetails.Message | ConvertFrom-Json } catch {}
        if ($err -and $err.error -eq "authorization_pending") { continue }
        if ($err -and $err.error -eq "slow_down") { $interval += 5; continue }
        if ($err) { throw "Error: $($err.error_description)" }
        throw
    }
}

# 3) Muestra el refresh token
Write-Host ""
Write-Host "===== LISTO =====" -ForegroundColor Green
Write-Host "Copia este REFRESH TOKEN y guardalo como secret en GitHub:" -ForegroundColor Green
Write-Host "  (hotmail -> MS_REFRESH_TOKEN_1   ·   outlook.es -> MS_REFRESH_TOKEN_2)" -ForegroundColor DarkGray
Write-Host ""
Write-Host $token.refresh_token
Write-Host ""
Write-Host "Repite este script para la otra cuenta." -ForegroundColor DarkGray
