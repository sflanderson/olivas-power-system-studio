# Olivas — Objetivo Estratégico: Paridade Total + Superação Obrigatória vs PTW

> **Norte estratégico formal**, registrado em 2026-04-29 e
> **endurecido em 2026-04-30** com a diretriz explícita do usuário
> (Landerson Ferreira Silva, doutorando UFMG):
>
> *"Paridade em todos os níveis com PTW e superação. Sempre analise
> com profundidade e comparação com os manuais (análise profunda)
> para entender como fazer e como superar."* (2026-04-29)
>
> *"100% das funcionalidades do PTW devem estar presentes no Olivas,
> e o Olivas deve superá-las."* (2026-04-30) ⚡ **ENDURECIMENTO**
>
> Este documento é referenciado pelo Master Protocol (6ª garantia,
> revisada em 2026-04-30) e deve ser revisitado a cada release.
>
> **Documentos vinculados**:
> - `docs/PTW_TOTAL_PARITY_DIRECTIVE.md` — diretriz formal "100% + superação"
> - `docs/PTW_TUTORIAL_AUDIT_v3.0.3.md` — audit completo Tutorial PTW v8.0 (167 features)
> - `docs/PTW_SURPASSING_MATRIX.md` — matriz 167 features × 8 dimensões de superação
> - `docs/PTW_PARITY_ACTION_PLAN.md` — roadmap operacional 10 sprints v3.0.3 → v4.1.0

---

## 1. Objetivo formal

**Olivas Power System Studio** terá como norte estratégico contínuo:

1. **Paridade** com SKM PTW Power*Tools v11 em todas as 12 áreas
   funcionais documentadas:
   - DAPPER (Power Flow + Voltage Drop + Demand Load)
   - A_FAULT / IEC_FAULT (Short-Circuit ANSI + IEC)
   - CAPTOR (Coordination)
   - Arc-Flash (IEEE 1584 / NESC / NFPA 70E)
   - TMS (Transient Motor Starting)
   - I*SIM (Intelligent Simulation)
   - HI_WAVE (Harmonics IEEE 519)
   - Equipment Library (vendor-curated data)
   - Equipment Evaluation (Pass/Fail dashboard)
   - Coordination Evaluation
   - Auto Design (cable sizing)
   - Data Visualizer

2. **Superação** em vetores estratégicos onde Olivas tem vantagem
   estrutural:
   - Cobertura normativa BR (NBR 17227, NBR 5410, NR-10) nativa
   - Multi-standard arc-flash (8 standards já entregues vs 1 PTW)
   - Open-source dual model + plugin marketplace
   - Multi-language UI (PT/EN/ES)
   - IEC 61850 nativo (MMS+GOOSE+SV+BER)
   - Docker reproducibility
   - Modern stack (Python 3.11+, PySide6, async)

## 2. Metodologia obrigatória — Análise Profunda

A partir desta release, **toda nova feature** que toque uma área
PTW-paralela DEVE seguir:

### 2.1 Antes de qualquer linha de código

1. **Identificar manual PTW correspondente** em
   `D:/000 - UFMG - DOUTORADO/MVP/LIB/PTW_MANUAL/` (28 PDFs)
2. **Análise profunda do manual** via agent paralelo:
   - Extrair texto via `pdftotext -layout` ou Read tool com pages
   - Mapear features obrigatórias (paridade) com **citação seção/página**
   - Identificar limitações declaradas no manual (oportunidades de
     superação)
   - Produzir roadmap em sprints com critério de done objetivo
3. **Documentar no audit doc** da release:
   - Lista de features obrigatórias (paridade)
   - Lista de superações propostas
   - Citações verificáveis das fontes

### 2.2 Anti-alucinação reforçada

* Cada feature implementada DEVE ter referência a manual PTW
  citado (seção + página)
* Constantes técnicas (ex: ANSI moderately inverse A=0.3022) DEVEM
  vir do manual, não memorizadas
* Onde manual PTW falha (limitações declaradas), citar o gap como
  base da superação

### 2.3 Auditoria crítica em cada release

Cada release vX.Y.Z DEVE incluir, em seu handoff:
- Tabela comparativa **Olivas vs PTW** atualizada (incremento sobre
  matriz v3.0.0)
- Itens NOVOS de paridade alcançada
- Itens NOVOS de superação alcançada
- Backlog de paridade pendente

---

## 3. Primeira análise profunda — CAPTOR (executada em v3.0.1)

**Manual analisado**: `Reference-CAPTOR.pdf` (~175 pp., 2006-03-26)
**Método**: pdftotext -layout extração integral (5241 linhas)

### 3.1 Features OBRIGATÓRIAS para paridade CAPTOR

#### 3.1.1 17 Segment Types (§2.2.1-2.2.17)

| # | Segment | Seção PTW | Comportamento |
|---|---------|-----------|---------------|
| 1 | Fuse Curve | 2.2.1 (p. 2-9) | Pontos com tolerance opening+clearing |
| 2 | Time-Current Points | 2.2.2 (p. 2-10) | Pontos sem tolerance |
| 3 | Opening and Clearing Curve | 2.2.3 (p. 2-11) | Como #1 + shift por função |
| 4 | Time-Current Points with Multiple Curves | 2.2.4 (p. 2-12) | Linha vertical ajustável |
| 5 | Pickup (LT/ST/INST) PU | 2.2.5 (p. 2-13) | Vertical pickup com tolerância % |
| 6 | Pickup with Current Settings PU | 2.2.6 (p. 2-15) | #5 + current setting |
| 7 | IEC LTPU | 2.2.7 (p. 2-16) | Plug × Rated × CT × K |
| 8 | Pickup with Open-Clear Curve | 2.2.8 (p. 2-17) | Vertical + curva inclinada |
| 9 | Pickup with Open-Clear Bands | 2.2.9 (p. 2-19) | #8 com band ajustável |
| 10 | Pickup with Adj. Tolerance | 2.2.10 (p. 2-21) | Tolerância distinta por setting |
| 11 | Pickup with Horizontal Delay Band (Fillet) | 2.2.11 (p. 2-23) | Vertical+Horizontal+fillet radius |
| 12 | Delay Band (I^Slope-T) Seconds | 2.2.12 (p. 2-25) | Inclinada com slope calc |
| 13 | Delay Band com Open-Clear distintos | 2.2.13 (p. 2-27) | Slope opening ≠ clearing |
| 14 | I²t + Horizontal Delay | 2.2.14 (p. 2-28) | I²t com toggle |
| 15 | T = AD/((I/Ipu)^N − C) + BD + K | 2.2.15 (p. 2-29) | Eletromecânica/eletrônica clássica |
| 16 | T = SM(A + B(...) + D/(...)² + E/(...)³) | 2.2.16 (p. 2-30) | Polinomial motor protector |
| 17 | Fix Time Horizontal Line | 2.2.17 (p. 2-31) | Linha horizontal |

#### 3.1.2 10 ANSI/IEC standard curves (§2.8.2 p. 2-107)

```
Tipo  A        B         C       N        K        Nome
S     0.2663            -        1.2969   0.028    Short Inverse (ANSI)
L     5.6143   0.03393  1.000    1.0000   0.028    Long Inverse (ANSI)
D     0.4797            -        1.5625   0.028    Definite Time (ANSI)
M     0.3022   2.18592  1.000    0.5000   0.028    Moderately Inverse (ANSI)
I     8.9341            -        2.0938   0.028    Inverse (ANSI)
V     5.4678   0.21359  1.000    2.0469   0.028    Very Inverse (ANSI)
E     7.7624            -        2.0938   0.028    Extremely Inverse (ANSI)
B     1.4636   0.12840  1.000    1.0469   0.028    BS142 Very Inverse (IEC)
C     8.2506            -        2.0469   0.028    BS142 Extremely Inverse (IEC)
F     0.000    0.17966  1.000    0.0000   0.000    Fixed Time
```

Fonte verificável: PTW Reference-CAPTOR §2.8.2 p. 2-107.

#### 3.1.3 Multi-function relay (§1.4.3 p. 1-19/1-20)

> *"You can assign any number of 'functions' to a protection
> component and display any one of the functions on each TCC
> drawing. Typical functions may include: Phase; Earth; As-Found;
> Proposed; Initial Operation; Subsequent Operation."*

Modelo: 1 component → N functions, cada uma com settings
separados, todas armazenadas mas apenas 1 exibida por TCC drawing.

#### 3.1.4 Damage curves & starting curves (§1.1.1, 1.2.2)

* Cable damage (térmica + mecânica) — IEC 60364-4-43, IEEE 242
* Transformer damage — ANSI C57.109 Cat I/II/III/IV + inrush
* Motor starting — locked rotor + starting profile
* Generator damage — short-time/long-time

**Limitação declarada PTW (§3.1 p. 3-3)**: *"cable damage curves
may not show up because insufficient data exists in the DOS
format to convert them"*. **OPORTUNIDADE DE SUPERAÇÃO**.

#### 3.1.5 3-Tab pages (§1.3.2 p. 1-9)

- Tab 1: Identity (Cable / Transformer / Generator / Motor / Device)
- Tab 2: Curve (Damage / Starting / Setting) com Redraw
- Tab 3: Datablock (mesmo formato Component Editor)

#### 3.1.6 TCC drawing format (§1.4.4 p. 1-21)

- Eixos log-log com status bar coords dinâmicas
- Layout/Fault Current/Background tabs
- Fixed Aspect Ratio toggle
- Pen widths controláveis (mais grosso para curvas)
- Grid density 1-100 linhas/decade

#### 3.1.7 Select-a-Device dialog (§1.3.3 p. 1-11)

Read-only browser sobre Library — *"reduces the risk of
accidentally changing Library data"*. Identification Report via
"Report Selected".

### 3.2 Oportunidades de SUPERAÇÃO identificadas

| # | Limitação CAPTOR | Como Olivas pode superar |
|---|-----------------|---------------------------|
| 1 | Damage curve gap (§3.1 p. 3-3 declara dados insuficientes) | Schema YAML versionado + biblioteca built-in (IEC/ANSI) |
| 2 | 17 segment types redundantes (combinatórios) | Unificar em 4 primitives + decorators (PickupVertical + OpenClearCurve + HorizontalDelay + EquationCurve) |
| 3 | Re-entrada manual de manufacturer constants | Embutir IEC 60255-151 + IEEE C37.112 como first-class |
| 4 | 1 function/TCC apenas | Mostrar N functions simultâneas (50+51 sobrepostos) com layers |
| 5 | DOS legacy import | Schema YAML com migração automática |
| 6 | Sem CIM/IEC 61850 nativo | Import direto SCD/CID (relay vendor data) + COMTRADE export |
| 7 | TCC Reference Voltage por TCC | Auto-shift por turns ratio + anotação visual |
| 8 | Sem validação automatizada | Selectivity verifier auto (0.3s margin, arc-flash gates) |
| 9 | Datablock = "spreadsheet" 2000s | JSON/XLSX/PDF com hash auditável |
| 10 | Plug-in API ausente | Python plugin API para custom segment types |

### 3.3 Roadmap sugerido CAPTOR-paridade-superação (5 sprints)

| Sprint | Tema | Esforço |
|--------|------|---------|
| v3.1.0 | Segment Engine (4 primitives → 17 types) + Renderer log-log | L |
| v3.1.1 | Library + 10 IEEE/IEC curves nativas + Select-a-Device | M |
| v3.1.2 | Multi-function model + Damage curves catalog | L |
| v3.1.3 | TCC Drawing 3-tab + Datablock + JSON/XLSX/PDF export | L |
| v3.1.4 | Validation engine + Plugin API + CIM/IEC 61850 import | XL |

---

## 4. Limitações declaradas (anti-alucinação)

* CAPTOR manual analisado é de **2006-03-26** (PTW pré-V11).
  Features posteriores a 2006 não estão neste manual.
  Recomendado complementar com `PTW Version 11 Enhancements.pdf`
  e `Reference-Coordination Evaluation.pdf` em release futura.
* Figuras/screenshots não foram lidas (apenas legendas).
  **Geometria precisa do fillet radius e color schemes precisam
  revisão visual manual antes de implementar UI**.
* Há erro tipográfico declarado em §2.2.15 p. 2-29 (default 1.05
  do Minimum Pickup multiplier escrito como "1.5" — confiar em 1.05).

---

## 5. Releases planejadas com aplicação deste objetivo

| Release | Manual PTW alvo | Foco paridade |
|---------|----------------|---------------|
| v3.0.1 | (este doc + restore) | Registrar objetivo formal |
| v3.0.2 | Reference-A_Fault.pdf | ANSI legacy SC (NACD, Test PF/X/R) |
| v3.0.3 | Reference-EquipmentEvaluation.pdf | Equipment Eval Dashboard |
| v3.1.0-v3.1.4 | Reference-CAPTOR.pdf (este audit) | 5 sprints CAPTOR |
| v3.2.0 | Multi-User PTW Library/Project.pdf | Multi-user collab + library sharing |
| v3.3.0 | Reference-HI_Wave.pdf | Harmonics depth (vs Olivas current implementation) |
| v3.4.0 | PTW Version 11 Enhancements.pdf | Deltas modernos (post-2006) |
| v3.5.0 | Reference-Auto_Design.pdf | Auto-design unificado |
| v3.6.0 | Reference-Autodesk Revit-SKM.pdf | BIM/CAD integration |

---

## 6. Como esta diretiva interage com Master Protocol

A diretiva de "paridade + superação + análise profunda" é a
**6ª garantia** do Master Protocol (extensão das 5 originais
documentadas em `v1.7.0_MASTER_PROTOCOL.md`):

1. Auditar
2. Registrar
3. Anti-alucinação
4. Anti-crash/perda/regressão
5. Ponto de restauração
6. **Paridade + superação vs PTW** (esta diretiva)

A 6ª garantia é checada em todo audit doc:
*"Esta release contribui para paridade ou superação vs PTW? Cita
manual?"*

Releases sem aplicação direta (ex: bug fix interno) podem documentar
"N/A" honestamente — anti-alucinação preserva integridade.
