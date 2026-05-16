# Scripts utilitários

Helpers fora do core do aplicativo. Não fazem parte do build do
binário Pro/Community — são ferramentas de desenvolvimento e
operação.

## Publicação no GitHub

| Arquivo | Propósito |
|---------|-----------|
| [`init_local_git.ps1`](init_local_git.ps1) | Inicializa repo Git local, valida `.gitignore`, audita paths proibidos, faz primeiro commit |
| [`setup_github_repo.md`](setup_github_repo.md) | Playbook para criar repositório remoto (via `gh` CLI ou Claude in Chrome) |

### Sequência recomendada

```powershell
# 1. Preparar repositório local com clean-room audit
.\scripts\init_local_git.ps1

# 2. Conferir o que entrará no push (opcional)
git log --oneline
git ls-files | Select-Object -First 30

# 3. Criar remoto + push
#    Opção A — gh CLI (rápido)
gh repo create olivas-power-system-studio --public --source=. --push --description "Software de análise elétrica auditável..."

#    Opção B — Claude in Chrome ou manual
#    Seguir scripts/setup_github_repo.md
```

## Outras utilidades (legacy)

| Arquivo | Propósito |
|---------|-----------|
| [`migrate_sch_wires.py`](migrate_sch_wires.py) | Migração antiga de schematics |
| [`rebuild_example_sch.py`](rebuild_example_sch.py) | Reconstrói exemplos de schematic |
