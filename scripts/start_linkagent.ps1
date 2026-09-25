param(
    [ValidateSet("chrome", "edge", "opera", "brave", "vivaldi")]
    [string]$Browser,
    [switch]$IsolatedProfile,
    [switch]$DirectProfile,
    [switch]$RefreshProfile
)

$ErrorActionPreference = "Stop"
$port = 9222
$endpoint = "http://127.0.0.1:$port/json/version"

function Get-CdpVersion {
    try {
        return Invoke-RestMethod -Uri $endpoint -TimeoutSec 2
    } catch {
        return $null
    }
}

function Get-BrowserExecutable([string]$name) {
    $paths = @{
        chrome = @(
            "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
            "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
        )
        edge = @(
            "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
            "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
        )
        opera = @(
            "$env:LOCALAPPDATA\Programs\Opera\opera.exe",
            "$env:LOCALAPPDATA\Programs\Opera GX\opera.exe"
        )
        brave = @(
            "$env:ProgramFiles\BraveSoftware\Brave-Browser\Application\brave.exe",
            "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\Application\brave.exe"
        )
        vivaldi = @("$env:LOCALAPPDATA\Vivaldi\Application\vivaldi.exe")
    }
    return @($paths[$name] | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1)[0]
}

function Get-ProfileLayout([string]$name) {
    switch ($name) {
        chrome {
            $root = Join-Path $env:LOCALAPPDATA "Google\Chrome\User Data"
            $default = "Default"
        }
        edge {
            $root = Join-Path $env:LOCALAPPDATA "Microsoft\Edge\User Data"
            $default = "Default"
        }
        brave {
            $root = Join-Path $env:LOCALAPPDATA "BraveSoftware\Brave-Browser\User Data"
            $default = "Default"
        }
        vivaldi {
            $root = Join-Path $env:LOCALAPPDATA "Vivaldi\User Data"
            $default = "Default"
        }
        opera {
            $root = Join-Path $env:APPDATA "Opera Software\Opera Stable"
            $default = "Default"
        }
    }
    $statePath = Join-Path $root "Local State"
    if (Test-Path -LiteralPath $statePath) {
        try {
            $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
            if ($state.profile.last_used) {
                $default = [string]$state.profile.last_used
            }
        } catch {
            Write-Verbose "Could not read the last-used profile; using Default."
        }
    }
    return [pscustomobject]@{ Root = $root; ProfileDirectory = $default }
}

$existing = Get-CdpVersion
if ($existing) {
    if ($Browser -and $existing.Browser -notmatch "(?i)$Browser") {
        throw "CDP is already serving $($existing.Browser), not the requested $Browser browser. Select the browser that is already running or close it first."
    }
    Write-Output "LinkAgent browser is already running: $($existing.Browser)"
    exit 0
}

if (-not $Browser) {
    throw "Specify exactly one browser with -Browser chrome, -Browser edge, -Browser opera, -Browser brave, or -Browser vivaldi."
}

$executable = Get-BrowserExecutable $Browser
if (-not $executable) {
    throw "The requested $Browser browser is not installed or was not found."
}

$processNames = @{
    chrome = "chrome.exe"
    edge = "msedge.exe"
    opera = "opera.exe"
    brave = "brave.exe"
    vivaldi = "vivaldi.exe"
}
$alreadyRunning = @(Get-CimInstance Win32_Process -Filter "Name = '$($processNames[$Browser])'" -ErrorAction SilentlyContinue).Count -gt 0
if ($alreadyRunning) {
    throw "$Browser is already running without a LinkAgent CDP endpoint. Close every $Browser window, then run this script again. LinkAgent will not terminate your browser automatically."
}

$layout = Get-ProfileLayout $Browser
$profileRoot = Join-Path $env:USERPROFILE ".opencode\profiles"
$mirrorRoot = Join-Path $profileRoot "LinkAgent-$Browser"
$browserArgs = @(
    "--remote-debugging-address=127.0.0.1",
    "--remote-debugging-port=$port",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-session-crashed-bubble",
    "--hide-crash-restore-bubble",
    "https://www.google.com"
)

if ($IsolatedProfile) {
    New-Item -ItemType Directory -Path $mirrorRoot -Force | Out-Null
    $browserArgs = @(
        "--remote-debugging-address=127.0.0.1",
        "--remote-debugging-port=$port",
        "--user-data-dir=$mirrorRoot",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-session-crashed-bubble",
        "--hide-crash-restore-bubble",
        "https://www.google.com"
    )
    Write-Output "Using isolated $Browser profile: $mirrorRoot"
} elseif ($DirectProfile) {
    if (-not (Test-Path -LiteralPath $layout.Root -PathType Container)) {
        throw "The selected browser profile root was not found: $($layout.Root)"
    }
    $browserArgs = @(
        "--remote-debugging-address=127.0.0.1",
        "--remote-debugging-port=$port",
        "--profile-directory=$($layout.ProfileDirectory)",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-session-crashed-bubble",
        "--hide-crash-restore-bubble",
        "https://www.google.com"
    )
    Write-Output "Using direct $Browser profile: $($layout.ProfileDirectory)"
} else {
    if (-not (Test-Path -LiteralPath $layout.Root -PathType Container)) {
        throw "The selected browser profile root was not found: $($layout.Root)"
    }
    if ($RefreshProfile -or -not (Test-Path -LiteralPath (Join-Path $mirrorRoot $layout.ProfileDirectory) -PathType Container)) {
        New-Item -ItemType Directory -Path $mirrorRoot -Force | Out-Null
        $excludeNames = @(
            "Cache", "Code Cache", "GPUCache", "ShaderCache", "Crashpad",
            "OptimizationGuide", "component_crx_cache", "Safe Browsing"
        )
        $robocopyArgs = @(
            $layout.Root, $mirrorRoot, "/E", "/COPY:DAT", "/DCOPY:DAT",
            "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS", "/NP"
        )
        foreach ($name in $excludeNames) {
            $robocopyArgs += "/XD"
            $robocopyArgs += (Join-Path $layout.Root $name)
        }
        & robocopy @robocopyArgs | Out-Null
        if ($LASTEXITCODE -gt 7) {
            throw "Credential-preserving profile copy failed with robocopy exit code $LASTEXITCODE."
        }
    }
    $browserArgs = @(
        "--remote-debugging-address=127.0.0.1",
        "--remote-debugging-port=$port",
        "--user-data-dir=$mirrorRoot",
        "--profile-directory=$($layout.ProfileDirectory)",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-session-crashed-bubble",
        "--hide-crash-restore-bubble",
        "https://www.google.com"
    )
    Write-Output "Using credential-preserving $Browser profile mirror"
    Write-Output "Source profile: $($layout.Root) [$($layout.ProfileDirectory)]"
    Write-Output "Target profile: $mirrorRoot [$($layout.ProfileDirectory)]"
}

Write-Output "Credentials remain local and are not inspected by LinkAgent."
Start-Process -FilePath $executable -ArgumentList $browserArgs

$deadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Milliseconds 500
    $version = Get-CdpVersion
    if ($version) {
        Write-Output "LinkAgent browser started: $($version.Browser)"
        exit 0
    }
    if ((Get-Date) -ge $deadline) {
        throw "$Browser opened, but CDP did not become available on $endpoint. Fully close $Browser and retry."
    }
} while ($true)
