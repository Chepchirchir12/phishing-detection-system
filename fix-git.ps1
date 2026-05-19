Param(
    [string]$ProjectPath = (Get-Location).Path
)

function Abort($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

try {
    $gitDir = (& git rev-parse --git-dir) 2>$null
} catch {
    Abort 'Git not found or not available in PATH.'
}

if (-not $gitDir) { Abort 'No git repository detected.' }

Write-Host "Git directory: $gitDir"
Write-Host "Project path: $ProjectPath"

if ($gitDir -eq (Join-Path $ProjectPath '.git')) {
    Write-Host 'Git is already local to the project. No action needed.' -ForegroundColor Green
    exit 0
}

Write-Host "It looks like Git is using a repository at: $gitDir" -ForegroundColor Yellow
Write-Host 'This is likely unintended. The script can rename (back up) that .git and initialize this project as a new repo.'

$answer = Read-Host 'Continue and rename the global .git to .git-backup? (Y/N)'
if ($answer -notmatch '^[Yy]') { Write-Host 'Aborted by user.'; exit 0 }

# Determine whether gitDir is a folder or file
if (Test-Path $gitDir -PathType Container) {
    $backupPath = "$gitDir-backup"
    Write-Host "Renaming folder '$gitDir' to '$backupPath'..."
    try {
        Rename-Item -Path $gitDir -NewName ($gitDir + '-backup') -ErrorAction Stop
        Write-Host 'Renamed successfully.' -ForegroundColor Green
    } catch {
        Write-Host 'Failed to rename. Try running PowerShell as Administrator.' -ForegroundColor Red
        Write-Host $_.Exception.Message
        exit 1
    }
} elseif (Test-Path $gitDir -PathType Leaf) {
    $backupFile = "$gitDir-backup"
    Write-Host "Renaming file '$gitDir' to '$backupFile'..."
    try {
        Rename-Item -Path $gitDir -NewName ($gitDir + '-backup') -ErrorAction Stop
        Write-Host 'Renamed successfully.' -ForegroundColor Green
    } catch {
        Write-Host 'Failed to rename. Try running PowerShell as Administrator.' -ForegroundColor Red
        Write-Host $_.Exception.Message
        exit 1
    }
} else {
    Write-Host 'The path reported by Git does not exist on disk. Please inspect manually.' -ForegroundColor Red
    exit 1
}

# Initialize repo inside project
Push-Location $ProjectPath
if (-not (Test-Path (Join-Path $ProjectPath '.git'))) {
    Write-Host 'Initializing new git repository in project...' -ForegroundColor Cyan
    & git init
    & git add -A
    try {
        & git commit -m "Initial commit"
        Write-Host 'Initial commit created.' -ForegroundColor Green
    } catch {
        Write-Host 'Commit failed (no files to commit or commit configuration missing).' -ForegroundColor Yellow
    }
} else {
    Write-Host 'A .git already exists in the project path. Skipping init.'
}
Pop-Location

Write-Host 'Done. Verify with `git rev-parse --show-toplevel` and `git status`.' -ForegroundColor Green
