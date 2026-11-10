$ErrorActionPreference = 'Stop'
if (Get-Command python -CommandType Application -ErrorAction SilentlyContinue) {
    & python -B (Join-Path $PSScriptRoot 'Run.py') @args
} else {
    & py -3 -B (Join-Path $PSScriptRoot 'Run.py') @args
}
exit $LASTEXITCODE
