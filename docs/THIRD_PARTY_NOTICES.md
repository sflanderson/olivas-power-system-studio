# Third-Party Notices — Olivas ATP Studio

Este documento lista todas as dependências de terceiros usadas pelo
Olivas ATP Studio, suas licenças e avisos de copyright exigidos por
cada licença.

Veja também: [`LICENSING.md`](LICENSING.md) para a política geral de
licenciamento e clean-room.

**Última atualização:** 2026-04-19 (sprint v0.21.8).

---

## 1. Dependências diretas (declaradas em `requirements.txt`)

### 1.1 PySide6 — GUI toolkit

- **Projeto:** PySide6 / Qt for Python
- **Mantenedor:** The Qt Company Ltd.
- **Licença:** LGPL v3 (com Qt exception) ou licença comercial Qt
- **Site:** <https://www.qt.io/qt-for-python>
- **Uso no Olivas:** toda a camada `app/gui/*` (janela principal, widgets,
  QGraphicsScene do editor visual, diálogos, undo stack).

**Aviso exigido:**

> Qt is Copyright (C) The Qt Company Ltd. and other contributors.
> Qt is available under the LGPL v3 with exceptions and GPL v3, as
> well as under a commercial license. See <https://www.qt.io/licensing>.

**Compliance:** o Olivas ATP Studio usa PySide6 via **linkagem dinâmica**
(carregamento em tempo de execução pelo Python), o que é permitido pela
LGPL. O usuário final pode substituir a biblioteca Qt por outra versão
compatível. Nenhuma modificação foi feita no Qt.

---

### 1.2 anthropic — SDK Claude API

- **Projeto:** anthropic-sdk-python
- **Mantenedor:** Anthropic PBC.
- **Licença:** MIT
- **Site:** <https://github.com/anthropics/anthropic-sdk-python>
- **Uso no Olivas:** `app/llm/agent.py`, integração opcional com Claude
  para o chat do assistente.

**Aviso:**

> Copyright (c) 2023–2026 Anthropic PBC. Distribuído sob MIT License.

---

### 1.3 matplotlib — plotting

- **Projeto:** matplotlib
- **Mantenedor:** John D. Hunter e contribuidores.
- **Licença:** PSF-based (BSD-compatível)
- **Site:** <https://matplotlib.org/>
- **Uso no Olivas:** `app/analysis/*`, geração de gráficos para relatório
  HTML e visualização básica de resultados.

**Aviso:**

> Matplotlib is Copyright (c) 2012– Matplotlib Development Team; All
> Rights Reserved. Licensed under the Matplotlib License (PSF-based).

---

### 1.4 pytest — test framework (dev-only)

- **Licença:** MIT
- **Uso:** suíte de testes, não embarcado em distribuição.

---

## 2. Dependências opcionais (usadas condicionalmente)

### 2.1 Pillow (PIL) — manipulação de imagens

- **Import condicional:** `app/analysis/report_export.py` (otimização de logo).
- **Licença:** HPND (MIT-like).
- **Aviso:** `Copyright (c) 1997–2011 by Secret Labs AB / 1995–2011 by Fredrik Lundh.`

### 2.2 pyqtgraph — plotting interativo

- **Status atual:** referenciado mas não obrigatório.
- **Licença:** MIT (se adotado formalmente, adicionar a `requirements.txt`).

---

## 3. Dependências **não** usadas (mas avaliadas)

Para registro da política clean-room:

| Pacote | Avaliado? | Decisão | Motivo |
|---|---|---|---|
| `numpy` | Sim | **Não adotar agora** | Evitar dep grande; usar `math` stdlib onde possível. Revisitar em v0.22.2+ (LCC) se cálculos matriciais forem necessários. |
| `scipy` | Sim | **Não adotar agora** | Mesma razão. LCC fitting pode precisar em v0.22.2+. |
| `pydantic` | Sim | **Adotada em v0.21.8** | Validação do schema `.ocomp`. Licença MIT. Ver §1.5. |
| `PyYAML` | Sim | **Adotada em v0.21.8** | Leitura/escrita de `.ocomp`. Licença MIT. Ver §1.6. |

### 1.5 pydantic — validação de modelos

- **Projeto:** pydantic v2
- **Mantenedor:** Samuel Colvin e contribuidores
- **Licença:** MIT
- **Site:** <https://docs.pydantic.dev/>
- **Uso no Olivas:** `app/preprocessor/spec/*` — modelos canônicos de
  `ComponentSpec`, exportação JSON Schema para tools da API Claude,
  validação bidirecional (YAML ↔ JSON ↔ Python).

**Aviso:** `Copyright (c) 2017 to present Pydantic Services Inc.
and individual contributors.`

### 1.6 PyYAML — serialização YAML

- **Projeto:** PyYAML
- **Licença:** MIT
- **Site:** <https://pyyaml.org/>
- **Uso no Olivas:** leitura e escrita de arquivos `.ocomp` (component spec).

**Aviso:** `Copyright (c) 2017-2021 Ingy döt Net; Copyright (c) 2006-2016 Kirill Simonov.`

---

## 4. Ferramentas externas NÃO embarcadas

Estas são ferramentas que o Olivas ATP Studio **invoca**, mas **não
distribui**:

### 4.1 ATP (EMTP-ATP) solver

- **Status:** não redistribuído. O usuário final deve ter sua própria
  licença ATP institucional obtida junto aos grupos regionais (CAUE,
  EEUG, Can/Am EMTP User Group, etc.).
- **Integração:** via `subprocess` em `app/simulation/runner.py`.

### 4.2 ATPDraw

- **Status:** não usado em runtime. Serviu apenas como **referência
  descritiva** (manual público) e **comparação de comportamento** em
  fase de projeto. Ver [`LICENSING.md`](LICENSING.md) §2 e §3.
- **Nenhum arquivo do ATPDraw está no repositório Olivas.**

### 4.3 Plotagem externa (PlotXY, GTPPlot)

- **Status:** usuário pode abrir arquivos `.pl4` nessas ferramentas se
  preferir; o Olivas não as invoca.

---

## 5. Conteúdo gerado pelo usuário

Arquivos `.atp` de teste no repositório (`tests/fixtures/*.atp`,
`trt_all_motors_dt_ea.atp`) foram **gerados e autorizados pelo autor
do projeto** (Eliandro), contêm apenas MODELS escritos pelo autor, e
não derivam de cases proprietários de terceiros.

---

## 6. Conformidade com as licenças

O Olivas ATP Studio cumpre as obrigações de cada licença:

- **LGPL (PySide6):** linkagem dinâmica; sem modificação do Qt; aviso
  presente; usuário pode relinkar.
- **MIT (anthropic, pytest, Pillow, pyqtgraph):** cópia do aviso de
  copyright será incluída no pacote de distribuição (v1.0.0).
- **PSF-based (matplotlib):** cópia do aviso incluída.
- **ATP solver / ATPDraw:** não redistribuídos, sem dependência binária.

---

## 7. Como atualizar este arquivo

Ao adicionar uma nova dependência:

1. Verifique a licença no PyPI ou no repositório upstream.
2. Confirme compatibilidade com a licença do Olivas (ver `LICENSING.md` §5).
3. Adicione uma nova seção aqui com: nome, mantenedor, licença, site,
   uso no Olivas, aviso de copyright.
4. Atualize `requirements.txt` no mesmo commit.
5. Se a licença for GPL/AGPL, **abra discussão antes de commitar** —
   pode forçar relicenciamento do Olivas.
