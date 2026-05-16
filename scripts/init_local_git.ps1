<#
.SYNOPSIS
    Inicializa repositório Git local do Olivas Power System Studio
    com clean-room policy aplicada.

.DESCRIPTION
    Prepara o diretório atual para publicação no GitHub:
      1. Verifica que .gitignore cobre paths proibidos
      2. git init (se ainda não for repo)
      3. Define main como branch padrão
      4. Faz auditoria de paths proibidos que escaparam ao gitignore
         — aborta se encontrar
      5. Faz primeiro commit "v4.0.0-beta — public release"

    NÃO executa push remoto — esse passo é manual (ou usa
    scripts/setup_github_repo.md).

.EXAMPLE
    .\scripts\init_local_git.ps1

.EXAMPLE
    .\scripts\init_local_git.ps1 -DryRun
    # Mostra o que seria feito sem alterar nada
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [string]$CommitMessage = "feat: initial public release v4.0.0-beta"
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    ✓ $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    ! $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "    ✗ $msg" -ForegroundColor Red }

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot

try {
    Write-Step "Diretório: $ProjectRoot"

    # -----------------------------------------------------------------------
    # 1) Verifica .gitignore
    # -----------------------------------------------------------------------
    Write-Step "Verificando .gitignore..."
    if (-not (Test-Path ".gitignore")) {
        Write-Err ".gitignore ausente — precisa ser criado antes."
        exit 1
    }
    $gitignore = Get-Content ".gitignore" -Raw
    $requiredPatterns = @(
        "GNUATP", "pre-processor", "_tmp_ptw", "library_relay",
        "restore_points", "api_keys.json", ".tmp.driveupload",
        "/LIB/", "/LIBRARY/"
    )
    $missing = @()
    foreach ($p in $requiredPatterns) {
        if ($gitignore -notmatch [regex]::Escape($p)) {
            $missing += $p
        }
    }
    if ($missing.Count -gt 0) {
        Write-Err ".gitignore não cobre: $($missing -join ', ')"
        Write-Err "Aborte e atualize o .gitignore primeiro."
        exit 2
    }
    Write-Ok ".gitignore cobre todos os paths proibidos"

    # -----------------------------------------------------------------------
    # 2) Audit pré-commit: paths proibidos presentes no disco?
    # -----------------------------------------------------------------------
    Write-Step "Auditando paths proibidos no disco..."
    $forbiddenPaths = @(
        "app\core\GNUATP",
        "pre-processor",
        "_tmp_ptw",
        "LIB",
        "LIBRARY",
        "library_relay",
        "restore_points",
        ".tmp.driveupload"
    )
    $present = @()
    foreach ($p in $forbiddenPaths) {
        if (Test-Path $p) { $present += $p }
    }
    if ($present.Count -gt 0) {
        Write-Warn "Os seguintes diretórios EXISTEM no disco e são"
        Write-Warn "proibidos pelo clean-room — o .gitignore os bloqueia,"
        Write-Warn "mas confirme que nenhum arquivo individual escapou:"
        foreach ($p in $present) { Write-Host "      - $p" -ForegroundColor DarkYellow }
    } else {
        Write-Ok "Nenhum diretório proibido presente no disco"
    }

    # -----------------------------------------------------------------------
    # 3) Verifica/instala Git
    # -----------------------------------------------------------------------
    Write-Step "Verificando Git instalado..."
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        Write-Err "Git não encontrado. Instale: https://git-scm.com/download/win"
        exit 3
    }
    Write-Ok ("Git: " + (git --version))

    # -----------------------------------------------------------------------
    # 4) git init (se necessário)
    # -----------------------------------------------------------------------
    Write-Step "Verificando se já é repositório Git..."
    if (Test-Path ".git") {
        Write-Ok "Já é repositório Git — preservando histórico"
    } else {
        if ($DryRun) {
            Write-Warn "DRY-RUN: rodaria 'git init --initial-branch=main'"
        } else {
            git init --initial-branch=main | Out-Null
            Write-Ok "Repositório Git inicializado (branch: main)"
        }
    }

    # -----------------------------------------------------------------------
    # 5) Confere user.name e user.email
    # -----------------------------------------------------------------------
    Write-Step "Verificando configuração de user..."
    $userName = git config --get user.name 2>$null
    $userEmail = git config --get user.email 2>$null
    if (-not $userName -or -not $userEmail) {
        Write-Warn "git config user.name ou user.email não configurados."
        Write-Warn "Defina globalmente (uma vez por máquina):"
        Write-Host "      git config --global user.name 'Seu Nome'" -ForegroundColor Gray
        Write-Host "      git config --global user.email 'seu@email.com'" -ForegroundColor Gray
    } else {
        Write-Ok "user.name=$userName / user.email=$userEmail"
    }

    # -----------------------------------------------------------------------
    # 6) Stage + commit inicial (apenas se houver mudanças)
    # -----------------------------------------------------------------------
    Write-Step "Verificando se há arquivos para commit..."
    $isRepo = (Test-Path ".git") -or -not $DryRun
    if (-not (Test-Path ".git") -and $DryRun) {
        Write-Warn "DRY-RUN: não é repo git ainda; após init, TODOS os"
        Write-Warn "arquivos rastreáveis seriam staged e comitados."
        $status = ""
    } else {
        $status = git status --porcelain 2>$null
    }
    if ([string]::IsNullOrWhiteSpace($status)) {
        if (Test-Path ".git") {
            Write-Ok "Nada para comitar (working tree clean)"
        }
    } else {
        $fileCount = ($status -split "`n").Count
        Write-Host "    $fileCount arquivo(s) modificado(s) / não rastreado(s)"

        if ($DryRun) {
            Write-Warn "DRY-RUN: rodaria 'git add -A' + 'git commit -m ...'"
            Write-Host "    Primeiros 20 arquivos que entrariam:" -ForegroundColor DarkGray
            ($status -split "`n") | Select-Object -First 20 | ForEach-Object {
                Write-Host "      $_" -ForegroundColor DarkGray
            }
        } else {
            git add -A 2>$null

            # Confirma que nenhum arquivo proibido foi staged
            Write-Step "Re-auditando staged (último gate antes do commit)..."
            $staged = git diff --cached --name-only 2>$null
            $leaked = @()
            foreach ($f in $staged) {
                foreach ($p in $forbiddenPaths) {
                    $norm = $p -replace '\\', '/'
                    if ($f -like "$norm/*" -or $f -like "*/$norm/*" -or $f -eq $norm) {
                        $leaked += $f
                    }
                }
                # secrets
                if ($f -match '\.env$|api_keys\.json$|\.pem$|\.key$|credentials\.json') {
                    $leaked += $f
                }
                # PDFs soltos (manuais de terceiros)
                if ($f -like "*.pdf") { $leaked += "PDF: $f" }
                # Lixo de drive sync
                if ($f -like "*tmp.driveupload*") { $leaked += "DRIVE: $f" }
                # Duplicatas Windows
                if ($f -like "*C*pia de *" -or $f -like "* - Copy.*") {
                    $leaked += "DUP: $f"
                }
            }
            if ($leaked.Count -gt 0) {
                Write-Err "VAZAMENTO DETECTADO em staged — abortando:"
                $leaked | Select-Object -Unique | ForEach-Object {
                    Write-Host "      - $_" -ForegroundColor Red
                }
                Write-Err "Atualize .gitignore e rode novamente."
                git reset 2>$null | Out-Null
                exit 4
            }
            Write-Ok "Staged limpo (zero vazamento)"

            git commit -m $CommitMessage | Out-Null
            $hash = git rev-parse --short HEAD 2>$null
            Write-Ok "Commit criado: $hash — $CommitMessage"
        }
    }

    # -----------------------------------------------------------------------
    # 7) Status final
    # -----------------------------------------------------------------------
    Write-Step "Status final:"
    git log --oneline -n 5 2>$null | ForEach-Object {
        Write-Host "    $_" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Step "Próximo passo: criar repositório remoto e fazer push."
    Write-Host "    Use uma das opções abaixo:" -ForegroundColor Gray
    Write-Host ""
    Write-Host "    [A] Via gh CLI (recomendado):" -ForegroundColor White
    Write-Host "        gh auth login" -ForegroundColor Gray
    Write-Host "        gh repo create olivas-power-system-studio --public --source=. --push --description 'Software de análise elétrica auditável (alternativa nacional a SKM PTW)'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "    [B] Via Claude in Chrome:" -ForegroundColor White
    Write-Host "        Siga o playbook em scripts/setup_github_repo.md" -ForegroundColor Gray
    Write-Host ""
    Write-Host "    [C] Manual no github.com:" -ForegroundColor White
    Write-Host "        1. Acesse https://github.com/new" -ForegroundColor Gray
    Write-Host "        2. Crie repo 'olivas-power-system-studio' (public, vazio)" -ForegroundColor Gray
    Write-Host "        3. Volte aqui e rode:" -ForegroundColor Gray
    Write-Host "             git remote add origin https://github.com/<USER>/olivas-power-system-studio.git" -ForegroundColor Gray
    Write-Host "             git push -u origin main" -ForegroundColor Gray
}
finally {
    Pop-Location
}
