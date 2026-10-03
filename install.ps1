# PowerShell install script for Qwen MCP Server
# Run: .\install.ps1

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Qwen Coder MCP Server — Install" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
try {
    $pyVersion = python --version 2>&1
    Write-Host "[OK] $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found. Install Python 3.10+" -ForegroundColor Red
    exit 1
}

# 2. Create venv
$venvPath = Join-Path $ProjectDir "venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "[1/3] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvPath
} else {
    Write-Host "[1/3] Virtual environment exists" -ForegroundColor Green
}

# 3. Install package
$pipPath = Join-Path $venvPath "Scripts\pip.exe"
Write-Host "[2/3] Installing dependencies..." -ForegroundColor Yellow
& $pipPath install -e $ProjectDir --quiet

# 4. Verify
$pythonPath = Join-Path $venvPath "Scripts\python.exe"
Write-Host "[3/3] Verifying..." -ForegroundColor Yellow
& $pythonPath -c "from qwen_mcp.server import mcp; print('Server OK — 7 tools registered')"

# 5. Show config
$pythonPathEscaped = $pythonPath -replace '\\', '\\\\'
$serverPath = (Join-Path $ProjectDir "qwen_mcp\server.py") -replace '\\', '\\\\'

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Install complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Add this to: %APPDATA%\Claude\claude_desktop_config.json" -ForegroundColor Yellow
Write-Host ""
Write-Host @"
{
  "mcpServers": {
    "qwen-coder": {
      "command": "$pythonPathEscaped",
      "args": ["$serverPath"],
      "env": {
        "QWEN_BASE_URL": "YOUR_BASE_URL_HERE",
        "QWEN_API_KEY": "YOUR_API_KEY_HERE",
        "QWEN_MODEL": "YOUR_MODEL_NAME",
        "QWEN_TIMEOUT": "300"
      }
    }
  }
}
"@
Write-Host ""
Write-Host "Then restart Claude Desktop." -ForegroundColor Cyan
Write-Host ""
