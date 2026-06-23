param(
  [Parameter(Mandatory = $true)]
  [string]$RepoId,

  [string]$Revision = "main",

  [string]$BaseUrl = "https://huggingface.co",

  [string]$DestinationRoot = "E:\LocalVoiceInputModels\hf",

  [int]$Retries = 20,

  [int]$RetryDelaySeconds = 5
)

$ErrorActionPreference = "Stop"

function Convert-ToSafeRepoName {
  param([string]$Value)
  return $Value.Replace("/", "__")
}

function Escape-HuggingFacePath {
  param([string]$Path)
  $parts = $Path -split "/"
  $escaped = @()
  foreach ($part in $parts) {
    $escaped += [System.Uri]::EscapeDataString($part)
  }
  return ($escaped -join "/")
}

function Invoke-CurlDownload {
  param(
    [string]$Url,
    [string]$Target,
    [bool]$Resume
  )

  $targetDir = Split-Path -Parent $Target
  if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
  }

  $completeMarker = "$Target.complete"
  if (Test-Path $completeMarker) {
    Write-Output "skip     $Target"
    return
  }

  if ((-not $Resume) -and (Test-Path $Target)) {
    Remove-Item -Force $Target
  }

  $args = @(
    "-L",
    "--fail",
    "--silent",
    "--show-error",
    "--retry", "$Retries",
    "--retry-delay", "$RetryDelaySeconds",
    "--connect-timeout", "30",
    "-o", $Target,
    $Url
  )

  if ($Resume -and (Test-Path $Target)) {
    $args = @(
      "-L",
      "--fail",
      "--silent",
      "--show-error",
      "--retry", "$Retries",
      "--retry-delay", "$RetryDelaySeconds",
      "--connect-timeout", "30",
      "-C", "-",
      "-o", $Target,
      $Url
    )
  }

  Write-Output "download $Url"
  Write-Output "target   $Target"
  Write-Output ("resume   " + $Resume)
  & curl.exe @args
  if ($LASTEXITCODE -ne 0) {
    throw "curl failed with exit code $LASTEXITCODE for $Url"
  }
  Set-Content -Encoding ASCII -Path $completeMarker -Value "complete"
}

$safeRepoName = Convert-ToSafeRepoName $RepoId
$destination = Join-Path $DestinationRoot $safeRepoName
New-Item -ItemType Directory -Force -Path $destination | Out-Null

$base = $BaseUrl.TrimEnd("/")
$apiRepo = [System.Uri]::EscapeUriString($RepoId)
$apiUrl = "$base/api/models/$apiRepo/revision/$Revision"
$infoPath = Join-Path $destination "_snapshot_info.json"

Write-Output "repo     $RepoId"
Write-Output "revision $Revision"
Write-Output "base     $base"
Write-Output "dest     $destination"
Write-Output "api      $apiUrl"

& curl.exe -L --fail --silent --show-error --retry $Retries --retry-delay $RetryDelaySeconds --connect-timeout 30 -o $infoPath $apiUrl
if ($LASTEXITCODE -ne 0) {
  throw "curl failed with exit code $LASTEXITCODE for $apiUrl"
}
$modelInfo = Get-Content -Path $infoPath -Raw | ConvertFrom-Json

if (-not $modelInfo.siblings -or $modelInfo.siblings.Count -eq 0) {
  throw "No siblings returned by Hugging Face API for $RepoId at $Revision"
}

foreach ($sibling in $modelInfo.siblings) {
  $file = [string]$sibling.rfilename
  if ([string]::IsNullOrWhiteSpace($file)) {
    continue
  }
  $escapedFile = Escape-HuggingFacePath $file
  $url = "$base/$RepoId/resolve/$Revision/$escapedFile"
  $target = Join-Path $destination ($file -replace "/", [System.IO.Path]::DirectorySeparatorChar)
  $resume = $file -match "\.(safetensors|bin|pt|pth|tar|zip)$"
  Invoke-CurlDownload -Url $url -Target $target -Resume $resume
}

$totalBytes = 0
Get-ChildItem -Path $destination -File -Recurse | ForEach-Object {
  $totalBytes += $_.Length
}

Write-Output "completed $RepoId"
Write-Output ("files    " + ((Get-ChildItem -Path $destination -File -Recurse | Measure-Object).Count))
Write-Output ("bytes    " + $totalBytes)
Write-Output ("gib      " + [Math]::Round($totalBytes / 1GB, 3))
