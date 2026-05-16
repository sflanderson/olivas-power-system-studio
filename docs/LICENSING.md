# Licenciamento e Política Clean-Room — Olivas ATP Studio

**Versão do documento:** 1.0 (v0.21.8 sprint)
**Última atualização:** 2026-04-19
**Status:** vigente — qualquer contribuição ao repositório deve obedecer a esta política.

---

## 1. Motivação

O Olivas ATP Studio almeja **paridade funcional** com o ATPDraw como
pré-processador visual de arquivos ATP/EMTP, **sem** replicar código,
binários, recursos gráficos, arquivos de biblioteca ou qualquer
material protegido distribuído com o ATPDraw.

Este documento registra:

1. A política **clean-room** que governa o desenvolvimento.
2. O mapa de licenças das dependências.
3. A licença escolhida para o Olivas ATP Studio.
4. O que pode e o que **não pode** entrar no repositório.

---

## 2. Status do ATPDraw (referência externa)

- **Autoria:** Hans Kristian Høidalen (NTNU, Noruega), com contribuições
  de László Prikler e Francisco Peñaloza.
- **Implementação:** Embarcadero Delphi XE8, proprietário.
- **Distribuição:** requer licença válida do ATP (EMTP-ATP), com
  restrições de redistribuição especificadas no manual:

  > *"An ATP license is required to utilize the ATPDraw program and
  > this manual. Conversion of this manual to other formats and
  > distribution on any kind of media requires explicit permission
  > from the authors."* — ATPDraw Manual v7.7, Preface.

- **Formatos proprietários envolvidos:**
  `.acp` (projeto, ZIP + forms Delphi), `.sup` (support file de
  componente), `.scl` (Standard Component Library), `.mod` (MODELS),
  `.alc` (LCC), `.bct` (BCTRAN), `.xfr` (XFMR).

**Conclusão:** nenhum arquivo binário, texto, imagem, ícone, `.sup`,
`.scl`, `.acp`, `.alc`, `.pdf` ou `.mod` distribuído com o ATPDraw
pode ser incluído no repositório Olivas ATP Studio, exceto quando
gerado pelo **usuário final** em sua própria instalação e usado
**localmente** como entrada para importação.

---

## 3. Política Clean-Room

A equipe de desenvolvimento do Olivas ATP Studio adota uma abordagem
**clean-room** análoga à usada em reimplementações notórias de sistemas
proprietários (ex.: Wine, ReactOS, Compaq BIOS):

### 3.1 Fontes permitidas de informação sobre o ATPDraw

1. **Manual público do ATPDraw** (PDF do usuário) — usado como
   referência descritiva de comportamento e layout de cartões ATP, sob
   fair-use acadêmico. **Não é redistribuído**.
2. **Formato ATP/EMTP** de cartão (`.atp`) — **domínio público**, pois
   é um padrão aberto publicado há décadas na literatura científica
   (EMTP Theory Book, CAUE, etc.).
3. **Comportamento observável** do ATPDraw em uso normal (o que ele
   gera como saída para uma entrada do usuário).
4. **Literatura acadêmica** citando técnicas de simulação EMT: CIGRE
   WGs, IEEE PES, IEC 62271, etc.

### 3.2 Fontes **proibidas**

- ❌ Código-fonte Delphi do ATPDraw (não público, mas mesmo se vazasse
  não poderia ser consultado).
- ❌ Descompilação ou engenharia reversa de `Atpdraw.exe`.
- ❌ Inspeção interna dos arquivos `.scl`, `.sup`, `.acp` para extrair
  estruturas proprietárias — o que vimos no `MyFirst.acp` foi apenas
  uma olhada externa para confirmar que o formato é binário e
  incompatível com nossa arquitetura Python/YAML.
- ❌ Tradução literal de algoritmos de código Delphi.
- ❌ Cópia de bitmaps, ícones, cursores, fontes ou strings de UI.

### 3.3 Nomes, extensões e terminologia

Para evitar qualquer ambiguidade de origem:

| Conceito ATPDraw | Equivalente Olivas (proprietário nosso) |
|---|---|
| `.sup` (support file) | `.ocomp` (Olivas component spec, YAML) |
| `.acp` (project) | `.ops` (Olivas project spec, JSON ou ZIP-JSON) |
| `.scl` (Standard Component Library) | `app/preprocessor/catalog/` (diretório de `.ocomp`) |
| `.alc` (LCC config) | `.olcc` (v0.22.2+) |
| Nome de menu "Compress" | "Agrupar / Grupo hierárquico" |
| Nome de menu "Probes & 3-phase" | "Medidores e multifásicos" |

**Regra:** quando houver coincidência inevitável (ex.: o cartão ATP
final é **o mesmo**, pois é o formato do solver), documenta-se que a
coincidência é exigida pelo **destino** (ATP), não importada da fonte
(ATPDraw).

---

## 4. Mapa de licenças — dependências atuais

Estado em 2026-04-19 (`requirements.txt`):

| Pacote | Versão | Licença | Compatibilidade | Notas |
|---|---|---|---|---|
| `PySide6` | ≥6.6.0 | LGPL v3 (+ exceção Qt) | ✅ ok para proprietário | Dynamic linking via Python é permitido. Usuário pode substituir Qt se quiser. |
| `anthropic` | ≥0.90.0 | MIT | ✅ permissiva | Opcional, integração Claude. |
| `matplotlib` | ≥3.8.0 | PSF-based (BSD-compatível) | ✅ permissiva | |
| `pytest` | ≥8.0.0 | MIT | ✅ permissiva | Dev-only. |
| `Pillow` | opcional | HPND (MIT-like) | ✅ permissiva | Via matplotlib, relatório HTML. |
| `pyqtgraph` (se usado) | — | MIT | ✅ permissiva | Verificar se está em uso real. |

**Avaliação:**

- Nenhuma dependência GPL no caminho direto. O projeto **não é obrigado
  a ser GPL**.
- PySide6 (LGPL) permite que o Olivas ATP Studio seja distribuído sob
  qualquer licença (incluindo proprietária comercial), desde que:
  1. Linkagem seja dinâmica (automática no Python).
  2. O usuário possa substituir a biblioteca Qt.
  3. Avisos de copyright do Qt sejam preservados (fazemos isso em
     `docs/THIRD_PARTY_NOTICES.md`, criado em sprint próxima).

---

## 5. Escolha de licença para o Olivas ATP Studio

### 5.1 Opções consideradas

| Licença | Prós | Contras |
|---|---|---|
| **Apache 2.0** | Permissiva, proteção explícita de patente, compatível com comercial e acadêmico, aceita em muitos ecossistemas | Não obriga upstream a publicar derivadas |
| **MIT** | Máxima simplicidade e permissividade | Sem cláusula de patente explícita |
| **BSD-3-Clause** | Similar a MIT | Idem |
| **GPL v3** | Copyleft forte: derivadas obrigatoriamente abertas | Impede uso em produto fechado; incompatível com parcerias industriais que queiram embutir em produto proprietário |
| **LGPL v3** | Copyleft de biblioteca | Dificulta distribuição binária desktop |
| **AGPL v3** | Fecha o loophole de SaaS | Restritivo demais para uso academico normal |

### 5.2 Escolha preliminar: **Apache 2.0**

**Justificativa:**

1. O Olivas ATP Studio é ferramenta de doutorado + possível produto
   comercial futuro. Licença permissiva mantém as portas abertas.
2. Apache 2.0 adiciona **proteção explícita de patente**, importante
   porque alguns algoritmos de EMT (ex.: VCB statistical reignition,
   XFMR fitting) têm literatura de patente associada — protege
   usuários e contribuidores.
3. Compatível com todas as dependências atuais (LGPL, MIT, BSD, PSF).
4. Aceita pela comunidade acadêmica e industrial.

**⚠ Decisão final pendente de confirmação do autor do projeto**
(Eliandro). Se ele preferir GPL v3 (copyleft forte), a licença pode
ser trocada antes da v1.0.0 sem quebra — todo o código até agora é
dele.

### 5.3 `LICENSE.txt` na raiz

Será criado em passo seguinte desta sprint, contendo o texto integral
da Apache 2.0 + aviso "Copyright (c) 2025-2026 Eliandro ..." (a ser
preenchido pelo autor). **Não é adicionado automaticamente** — depende
de confirmação explícita do autor sobre a licença.

---

## 6. Lista negra do repositório

Os seguintes tipos de arquivo **nunca** devem ser adicionados ao
repositório Olivas ATP Studio (nem a pacotes de distribuição):

1. `*.exe` — binários executáveis do ATPDraw, ATP ou qualquer
   ferramenta de terceiro.
2. `*.scl`, `*.sup`, `*.acp`, `*.alc`, `*.bct`, `*.xfr` — arquivos
   originados do ATPDraw.
3. `*.mod` proveniente do ATPDraw (p.ex. `flash.mod`). MODELS escritos
   pelo autor ficam em `app/preprocessor/models_library/` com cabeçalho
   próprio.
4. PDF do manual do ATPDraw ou de outras ferramentas proprietárias.
5. Bitmaps, ícones, cursores, fontes ou recursos gráficos do ATPDraw.
6. Arquivos `.pl4` e `.lis` reais de projetos de terceiros (contêm
   dados de clientes). Apenas arquivos gerados por exemplos próprios.
7. Código Delphi (`.pas`, `.dfm`, `.dpr`).

### 6.1 `.gitignore` (aplicado em v0.21.8)

Ver `.gitignore` na raiz — versão aplicada nesta sprint, bloqueando
todos os padrões acima.

**Nota:** arquivos de teste como `trt_all_motors_dt_ea.atp` no root
são cartões ATP **gerados pelo usuário** e contêm apenas MODELS
escritos pelo autor — são permitidos como fixtures.

### 6.2 Ferramentas vendorizadas no repo local (status pré-v0.21.8)

O repositório local do autor contém, por razões de conveniência de
desenvolvimento, as seguintes ferramentas externas que o Olivas
**invoca** como subprocesso. Elas não são linkadas em runtime, nem
partes do código Olivas. Status legal:

#### Qucs (em `pre-processor/`)

- **Licença:** GNU GPL v2 — arquivo `pre-processor/COPYING` já presente.
- **Origem:** <http://qucs.sourceforge.net/>
- **Relação com Olivas:** o Olivas usa Qucs apenas como ferramenta de
  pré-processamento externa opcional (schematic editor alternativo).
  Chama `qucs.exe` como subprocesso. Não há mistura de código-fonte.
- **Compatibilidade:** GPL v2 permite **agregação** (distribuir junto
  com software de outras licenças) sem forçar a outra obra a adotar
  GPL, desde que sejam obras claramente separadas (mere aggregation,
  GPL v2 §2). Olivas (Apache 2.0) + Qucs (GPL v2) satisfaz isso.
- **Ação recomendada:** antes de qualquer publicação/venda do Olivas:
  1. Confirmar que o Qucs em `pre-processor/` é a versão oficial
     não-modificada.
  2. Se o autor modificou Qucs, precisa publicar as modificações
     sob GPL v2 (obrigação do copyleft).
  3. Considerar remover Qucs do tarball do Olivas e tornar um
     download opcional, para simplificar o pacote de distribuição.

#### GNUATP / ATP binaries (em `app/core/GNUATP/`)

- **Licença:** **RESTRITA**. O ATP (EMTP-ATP) é licenciado apenas a
  usuários de grupos regionais (CAUE, EEUG, Can/Am). A licença do ATP
  **proíbe** redistribuição.
- **Origem:** CAUE / distribuição autorizada ao Prof. Eliandro.
- **Status atual:** arquivos `*.exe` estão no diretório local do autor
  sob a licença institucional de UFMG/CAUE. **NÃO podem ser enviados
  para um repositório público**.
- **Ação obrigatória antes de qualquer push público:**
  1. `git rm -r --cached app/core/GNUATP/` para não subir os binários.
  2. Documentar em `README.md` que o usuário deve obter sua própria
     licença do ATP e configurar o path via `ATP_EXECUTABLE_PATH`.
  3. O `.gitignore` desta sprint já bloqueia `*.exe` — os binários
     atuais continuam no disco local mas não subirão para push futuro.

#### Recomendação para v0.21.9+

Separar o runner ATP em um módulo de configuração (`atp_runner_config.py`)
que lê o caminho do executável via variável de ambiente. Isso
desacopla Olivas de binários específicos e simplifica o compliance.

---

## 7. Obrigações ao contribuir

Qualquer PR (interno ou externo) ao Olivas ATP Studio:

1. Deve incluir a afirmação: "Esta contribuição é original, ou deriva
   apenas de fontes listadas em §3.1 de `docs/LICENSING.md`."
2. Não deve incluir arquivos da lista negra (§6).
3. Se consultar o manual do ATPDraw, deve citar a seção como inspiração
   funcional, **não** copiar trechos literais.
4. Novos MODELS/templates devem ter cabeçalho de copyright do autor e
   referência à literatura.

---

## 8. Histórico de revisões

| Data | Versão | Autor | Mudança |
|---|---|---|---|
| 2026-04-19 | 1.0 | Claude (sprint v0.21.8) | Documento inicial. Política clean-room, mapa de licenças, Apache 2.0 preliminar. |

---

## 9. Referências

- ATPDraw Manual v7.7, Preface. NTNU, junho 2025. Usado sob fair use
  acadêmico como referência descritiva. **Não redistribuído**.
- EMTP Theory Book. H. W. Dommel, BPA, 1986.
- GNU licenses: <https://www.gnu.org/licenses/>
- Apache License 2.0: <https://www.apache.org/licenses/LICENSE-2.0>
- Qt Licensing: <https://www.qt.io/licensing>
- Clean-room design, Wikipedia:
  <https://en.wikipedia.org/wiki/Clean-room_design>
