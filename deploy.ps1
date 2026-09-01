param(
    [Parameter(Position = 0)]
    [string]$Message
)

$ErrorActionPreference = "Stop"
$repositoryRoot = $PSScriptRoot
Set-Location -LiteralPath $repositoryRoot

$branch = git branch --show-current
if (-not $branch) {
    throw "Unable to determine the current Git branch."
}

git status --short
if (-not (git status --porcelain)) {
    Write-Host "No changes to deploy. Pushing $branch to refresh the remote state."
    git push origin $branch
    exit $LASTEXITCODE
}

if (-not $Message) {
    $Message = Read-Host "Commit message"
}
if ([string]::IsNullOrWhiteSpace($Message)) {
    throw "A non-empty commit message is required."
}

git add .
git commit -m $Message
git push origin $branch
