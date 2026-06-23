param(
  [Parameter(Mandatory = $true)]
  [string]$RepoId,

  [string]$Revision = "main",

  [string]$BaseUrl = "https://huggingface.co",

  [string]$DestinationRoot = "E:\LocalVoiceInputModels\hf",

  [string]$ScriptPath = "E:\LocalVoiceInputModels\bin\download_hf_snapshot_windows.ps1",

  [string]$LogRoot = "E:\LocalVoiceInputModels\logs"
)

$ErrorActionPreference = "Stop"

function Convert-ToSafeRepoName {
  param([string]$Value)
  return $Value.Replace("/", "__")
}

if (-not (Test-Path $ScriptPath)) {
  throw "Download script not found: $ScriptPath"
}

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$safeRepoName = Convert-ToSafeRepoName $RepoId
$stdout = Join-Path $LogRoot "$safeRepoName.out.log"
$stderr = Join-Path $LogRoot "$safeRepoName.err.log"
$cmdPath = Join-Path $LogRoot "$safeRepoName.run.cmd"

$commandLine = @(
  "@echo off",
  "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" -RepoId `"$RepoId`" -Revision `"$Revision`" -BaseUrl `"$BaseUrl`" -DestinationRoot `"$DestinationRoot`" > `"$stdout`" 2> `"$stderr`""
) -join [Environment]::NewLine

Set-Content -Encoding ASCII -Path $cmdPath -Value $commandLine

$process = Start-Process `
  -FilePath "cmd.exe" `
  -ArgumentList @("/c", $cmdPath) `
  -WindowStyle Hidden `
  -PassThru

Write-Output "started"
Write-Output ("repo=" + $RepoId)
Write-Output ("base=" + $BaseUrl)
Write-Output ("pid=" + $process.Id)
Write-Output ("stdout=" + $stdout)
Write-Output ("stderr=" + $stderr)
Write-Output ("cmd=" + $cmdPath)
Write-Output ("dest=" + (Join-Path $DestinationRoot $safeRepoName))
