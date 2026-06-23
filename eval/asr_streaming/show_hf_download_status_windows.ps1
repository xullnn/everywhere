param(
  [Parameter(Mandatory = $true)]
  [string]$RepoId,

  [string]$DestinationRoot = "E:\LocalVoiceInputModels\hf",

  [string]$LogRoot = "E:\LocalVoiceInputModels\logs",

  [int]$Tail = 40
)

$ErrorActionPreference = "SilentlyContinue"

function Convert-ToSafeRepoName {
  param([string]$Value)
  return $Value.Replace("/", "__")
}

$safeRepoName = Convert-ToSafeRepoName $RepoId
$destination = Join-Path $DestinationRoot $safeRepoName
$stdout = Join-Path $LogRoot "$safeRepoName.out.log"
$stderr = Join-Path $LogRoot "$safeRepoName.err.log"

Write-Output ("repo=" + $RepoId)
Write-Output ("dest=" + $destination)

$processes = Get-CimInstance Win32_Process |
  Where-Object {
    $_.CommandLine -like "*download_hf_snapshot_windows.ps1*" -and
    $_.CommandLine -like "*$RepoId*"
  } |
  Select-Object ProcessId, CreationDate, CommandLine

if ($processes) {
  Write-Output "process=running"
  $processes | ConvertTo-Json -Depth 4
} else {
  Write-Output "process=not_found"
}

if (Test-Path $destination) {
  $files = Get-ChildItem -Path $destination -File -Recurse
  $bytes = ($files | Measure-Object -Property Length -Sum).Sum
  if (-not $bytes) {
    $bytes = 0
  }
  Write-Output ("files=" + $files.Count)
  Write-Output ("bytes=" + $bytes)
  Write-Output ("gib=" + [Math]::Round($bytes / 1GB, 3))
  Get-ChildItem -Path $destination -File -Recurse |
    Sort-Object Length -Descending |
    Select-Object -First 10 FullName, Length |
    ConvertTo-Json -Depth 4
} else {
  Write-Output "files=0"
  Write-Output "bytes=0"
}

if (Test-Path $stdout) {
  Write-Output "stdout_tail_begin"
  Get-Content -Path $stdout -Tail $Tail
  Write-Output "stdout_tail_end"
}

if (Test-Path $stderr) {
  Write-Output "stderr_tail_begin"
  Get-Content -Path $stderr -Tail $Tail
  Write-Output "stderr_tail_end"
}
