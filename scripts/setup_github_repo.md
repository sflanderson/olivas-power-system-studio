# Playbook: Criar repositório GitHub do Olivas Power System Studio

> **Para quem é este documento?**
> - Operadores humanos que querem o passo-a-passo manual.
> - **Agente Claude in Chrome** (MCP `mcp__Claude_in_Chrome__*`)
>   executando como ferramenta automatizada.

## Pré-requisitos

Antes de executar este playbook:

1. ✅ `scripts/init_local_git.ps1` já foi executado com sucesso
   (working tree limpa, primeiro commit feito, zero vazamentos
   de paths proibidos).
2. ✅ Conta GitHub ativa do autor (Landerson Ferreira Silva ou
   organização `olivas` se já existente).
3. ✅ Para opção via Claude in Chrome: a extensão "Claude in
   Chrome" está conectada e o usuário está logado em github.com.

## Parâmetros do repositório

| Campo | Valor |
|-------|-------|
| **Owner** | `landerson-fs` (substitua pelo username/org real) |
| **Repository name** | `olivas-power-system-studio` |
| **Description** | `Software de análise elétrica auditável (IEC 60909, NBR 17227, IEEE 1584, IEEE 242, IEEE 399). Alternativa nacional brasileira a SKM PTW / ETAP / EasyPower. Desktop Python/PySide6 sob Apache 2.0.` |
| **Visibility** | **Public** |
| **Initialize with README** | **NO** (já temos `README.md` local) |
| **Add .gitignore** | **NO** (já temos `.gitignore` local) |
| **Choose a license** | **NO** (já temos `LICENSE.txt` local — Apache 2.0) |
| **Default branch** | `main` |

> **Importante:** NÃO marcar nenhuma opção de inicialização — o
> repositório local já contém README, LICENSE, NOTICE,
> .gitignore. Se o GitHub criar arquivos paralelos, o `git push`
> falhará com merge conflict.

---

## Opção A — `gh` CLI (mais simples, recomendada)

Se você tem o GitHub CLI instalado:

```powershell
# 1. Autenticar (uma vez por máquina)
gh auth login --web --git-protocol https

# 2. Criar repo + setar origin + push em uma única linha
gh repo create olivas-power-system-studio `
  --public `
  --source=. `
  --push `
  --description "Software de análise elétrica auditável (IEC 60909, NBR 17227, IEEE 1584, IEEE 242, IEEE 399). Alternativa nacional brasileira a SKM PTW / ETAP / EasyPower. Desktop Python/PySide6 sob Apache 2.0."

# 3. Conferir
gh repo view --web
```

Se não tem o `gh`, instale com `winget install GitHub.cli` (Windows)
ou ver <https://cli.github.com>.

---

## Opção B — Claude in Chrome (UI automation)

Sequência de ações para o agente Claude in Chrome. Cada passo
inclui o seletor/texto esperado para `find` ou `form_input`.

### Passo 1: navegar para a página de criação de repo

**Ferramenta:** `mcp__Claude_in_Chrome__navigate`
**URL:** `https://github.com/new`

**Verificação esperada após carregar:**
- Título da página contém "Create a New Repository"
- Existe campo de input com `aria-label="Owner"` ou label "Owner"
- Existe campo de input com nome "Repository name"

Se a página redirecionar para `/login`, parar e pedir ao usuário
que faça login manualmente. NÃO tentar automatizar login com
credenciais.

### Passo 2: confirmar owner

**Ferramenta:** `mcp__Claude_in_Chrome__find` + `mcp__Claude_in_Chrome__get_page_text`

Verificar que o owner mostrado é o esperado (`landerson-fs` ou
o que o usuário indicar). Se houver múltiplas opções (conta
pessoal + organizações), parar e perguntar ao usuário qual usar.

### Passo 3: preencher nome do repositório

**Ferramenta:** `mcp__Claude_in_Chrome__form_input`
**Seletor:** `input[name="repository[name]"]` ou
`input[aria-label="Repository name"]`
**Valor:** `olivas-power-system-studio`

**Verificação:** GitHub exibe checkmark verde "is available"
abaixo do campo. Se mostrar erro "name already exists", parar
e perguntar ao usuário se quer outro nome ou usar org diferente.

### Passo 4: preencher descrição

**Ferramenta:** `mcp__Claude_in_Chrome__form_input`
**Seletor:** `input[name="repository[description]"]` ou
`input[aria-label="Description (optional)"]`
**Valor:**
```
Software de análise elétrica auditável (IEC 60909, NBR 17227, IEEE 1584, IEEE 242, IEEE 399). Alternativa nacional brasileira a SKM PTW / ETAP / EasyPower. Desktop Python/PySide6 sob Apache 2.0.
```

### Passo 5: selecionar visibilidade Public

**Ferramenta:** `mcp__Claude_in_Chrome__find` para localizar o
radio button "Public", depois clicar.

**Seletor preferido:** `input[type="radio"][value="public"]`
**Fallback por texto:** localizar elemento com texto "Public"
e clicar no radio button correspondente.

**Verificação:** o radio Public fica marcado e o radio Private
desmarcado.

### Passo 6: garantir que NENHUMA opção de inicialização está marcada

**Verificar (e DESMARCAR se necessário):**

- `input[name="repository[auto_init]"]` (Add a README file) → **NÃO marcar**
- `select[name="repository[gitignore_template]"]` (Add .gitignore) → **None**
- `select[name="repository[license_template]"]` (Choose a license) → **None**

Razão: estes arquivos já existem no repo local. Inicializar
no GitHub criaria conflito no primeiro `git push`.

### Passo 7: clicar "Create repository"

**Ferramenta:** `mcp__Claude_in_Chrome__find` + click
**Texto do botão:** `Create repository` (literal)
**Seletor preferido:** `button[type="submit"]` dentro do form
`form[action="/repositories"]`.

**Verificação após clique:**
- URL muda para `https://github.com/<owner>/olivas-power-system-studio`
- Página mostra "Quick setup — if you've done this kind of thing before"
- Existe bloco de código com comandos `git remote add origin ...`

### Passo 8: extrair URL HTTPS do remote

**Ferramenta:** `mcp__Claude_in_Chrome__get_page_text` ou
`mcp__Claude_in_Chrome__find`

Localizar o input de URL HTTPS no cabeçalho ("Code" tab ou
no bloco "…or push an existing repository") com valor no
formato:

```
https://github.com/<owner>/olivas-power-system-studio.git
```

Copiar este URL.

### Passo 9: voltar ao terminal e fazer push

⚠ **Esta parte NÃO é executada pelo Claude in Chrome** — é
instrução de output para o usuário.

```powershell
# No diretório D:\000 - UFMG - DOUTORADO\MVP\
git remote add origin https://github.com/<OWNER>/olivas-power-system-studio.git
git push -u origin main
```

Se já há remote `origin` configurado:
```powershell
git remote set-url origin https://github.com/<OWNER>/olivas-power-system-studio.git
git push -u origin main
```

### Passo 10: verificar publicação

**Ferramenta:** `mcp__Claude_in_Chrome__navigate` para
`https://github.com/<owner>/olivas-power-system-studio`.

**Verificações:**
- `README.md` é renderizado na home
- Arquivo `LICENSE.txt` está presente
- Diretório `app/`, `tests/`, `docs/`, `legal/`, `infra/`,
  `build/`, `scripts/` aparecem
- **Diretórios proibidos NÃO aparecem**: `GNUATP`,
  `pre-processor`, `_tmp_ptw`, `LIBRARY`, `restore_points`,
  `library_relay/SEL`. Se algum aparecer, ALERTAR o usuário —
  é uma violação clean-room que precisa de correção urgente
  (reescrever histórico com `git filter-repo`).

---

## Pós-criação (manual, qualquer opção)

Após o repositório existir:

### Topics

Adicionar topics relevantes (Settings → About → ⚙):
- `power-systems`
- `electrical-engineering`
- `iec-60909`
- `arc-flash`
- `nbr-17227`
- `python`
- `pyside6`
- `brasil`
- `engenharia-eletrica`
- `simulation`

### Branch protection

Settings → Branches → "Add rule" para `main`:
- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
- ✅ Require linear history
- ❌ Allow force pushes
- ❌ Allow deletions

### Secrets do GitHub Actions (futuro)

Settings → Secrets and variables → Actions:
- `RESEND_API_KEY` (apenas se houver workflow de e-mail)
- `CLOUDFLARE_API_TOKEN` (para deploy do Worker)

### Releases

Após push da `main`, criar release v4.0.0-beta:
```powershell
gh release create v4.0.0-beta --notes-file CHANGELOG.md --prerelease
```

---

## Segurança e responsabilidade

- ⚠ **Nunca usar este playbook em sessão automatizada sem
  supervisão** quando a operação envolve criação de recursos
  públicos. Confirme com o usuário antes do **Passo 7** (clique
  em "Create repository").
- ⚠ Após o push, **verifique manualmente** que nenhum segredo
  vazou olhando os primeiros 20 arquivos do commit no GitHub web.
- ⚠ Se vazamento de segredo for detectado, rotacione o segredo
  imediatamente (revogar API key, etc) e considere reescrever
  histórico com `git filter-repo` antes que o conteúdo seja
  indexado em search engines.

## Idempotência

Este playbook é seguro de re-executar:
- Opção A (`gh`): o comando falha com mensagem clara se o repo
  já existe.
- Opção B (Chrome): o Passo 3 detecta "name already exists" e
  pede intervenção humana.

Em ambos os casos, o segundo push (`git push -u origin main`) é
idempotente para repo já vazio (apenas envia commits que faltam).
