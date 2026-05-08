<#
.SYNOPSIS
  Lists annotated validation tags (validated/silqqms-*) and resolved commit SHAs for SilqQMS traceability.

.DESCRIPTION
  Quality-of-life helper for SW.SLQ010/SW.SLQ011/SW.SLQ012 — does not modify Git state.
  Run from repository root: .\scripts\git_show_validation_designation.ps1
#>

$ErrorActionPreference = 'Stop'

$root = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $root

try {
  git fetch --tags --quiet 2>$null
} catch {
  # Offline or no remote; continue with local tags
}

$tags = @(git tag -l 'validated/silqqms-*' 2>$null)
if ($tags.Count -eq 0) {
  Write-Host 'No tags matching validated/silqqms-* found.'
  Write-Host 'Create one from main after validation freeze (see docs/design-assessment/Resources/GIT_BRANCH_RUNBOOK.md).'
  Pop-Location
  exit 0
}

Write-Host "SilqQMS validation tags:`n"
foreach ($t in $tags) {
  $t = $t.Trim()
  if (-not $t) { continue }
  # Peel annotated tag to commit (tag^{}); avoid PowerShell interpreting braces
  $peel = '{0}^{{}}' -f $t
  $full = git rev-parse $peel 2>$null
  if (-not $full) {
    Write-Host "  Tag: $t"
    Write-Host "  SHA: (could not resolve)"
    Write-Host ""
    continue
  }
  $short = git rev-parse --short=7 $full
  Write-Host "  Tag: $t"
  Write-Host "  SHA: $full ($short)"
  Write-Host ""
}

Pop-Location
