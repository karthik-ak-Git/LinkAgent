# LinkAgent Native Messaging Host Registration Script
# Run as Administrator to register the native messaging host for Chrome

$ErrorActionPreference = "Stop"

# Paths
$HOST_NAME = "com.linkagent.bridge"
$HOST_PATH = Join-Path $PSScriptRoot "host.py"
$EXTENSION_ID = "linkagent-extension-id"

# Registry paths for Chrome
$CHROME_REG_PATH = "HKLM:\SOFTWARE\Google\Chrome\NativeMessagingHosts\$HOST_NAME"
$CHROME_USER_REG_PATH = "HKCU:\SOFTWARE\Google\Chrome\NativeMessagingHosts\$HOST_NAME"

# Registry paths for Edge
$EDGE_REG_PATH = "HKLM:\SOFTWARE\Microsoft\Edge\NativeMessagingHosts\$HOST_NAME"
$EDGE_USER_REG_PATH = "HKCU:\SOFTWARE\Microsoft\Edge\NativeMessagingHosts\$HOST_NAME"

# Registry paths for Opera
$OPERA_REG_PATH = "HKLM:\SOFTWARE\Opera Software\NativeMessagingHosts\$HOST_NAME"
$OPERA_USER_REG_PATH = "HKCU:\SOFTWARE\Opera Software\NativeMessagingHosts\$HOST_NAME"

# Create host manifest JSON
$manifest = @{
    name = $HOST_NAME
    description = "LinkAgent Browser Bridge Native Host"
    path = $HOST_PATH
    type = "stdio"
    allowed_origins = @(
        "chrome-extension://$EXTENSION_ID/"
    )
} | ConvertTo-Json -Depth 3

# Write manifest file
$manifestPath = Join-Path $PSScriptRoot "com.linkagent.bridge.json"
$manifest | Out-File -FilePath $manifestPath -Encoding UTF8
Write-Host "Created manifest: $manifestPath" -ForegroundColor Green

# Function to register host
function Register-Host {
    param(
        [string]$RegistryPath,
        [string]$BrowserName
    )
    
    try {
        $parentPath = Split-Path $RegistryPath -Parent
        if (-not (Test-Path $parentPath)) {
            New-Item -Path $parentPath -Force | Out-Null
        }
        Set-ItemProperty -Path $RegistryPath -Name "(Default)" -Value $manifestPath
        Write-Host "Registered for $BrowserName at: $RegistryPath" -ForegroundColor Green
    }
    catch {
        Write-Host "Failed to register for $BrowserName : $_" -ForegroundColor Yellow
    }
}

# Register for all browsers (both HKLM and HKCU)
Write-Host "`nRegistering native messaging host..." -ForegroundColor Cyan

# Chrome
Register-Host $CHROME_REG_PATH "Chrome (Machine)"
Register-Host $CHROME_USER_REG_PATH "Chrome (User)"

# Edge
Register-Host $EDGE_REG_PATH "Edge (Machine)"
Register-Host $EDGE_USER_REG_PATH "Edge (User)"

# Opera
Register-Host $OPERA_REG_PATH "Opera (Machine)"
Register-Host $OPERA_USER_REG_PATH "Opera (User)"

Write-Host "`nRegistration complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Install the LinkAgent extension in Chrome/Edge/Opera" -ForegroundColor White
Write-Host "2. Update extension ID in this script and re-run if needed" -ForegroundColor White
Write-Host "3. Test with: echo '{""command"":""ping""}' | python host.py" -ForegroundColor White
