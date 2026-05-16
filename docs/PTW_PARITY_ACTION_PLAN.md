# PTW Parity Action Plan — Reestruturação Olivas estilo PTW

**Data**: 2026-04-30 (revisado mesmo dia para diretriz "100% paridade + superação obrigatória")
**Autor**: derivado de `docs/PTW_TUTORIAL_AUDIT_v3.0.3.md`
**Diretriz governante**: `docs/PTW_TOTAL_PARITY_DIRECTIVE.md` ⚡ **NOVA**
**Matriz de superação**: `docs/PTW_SURPASSING_MATRIX.md` (167 linhas)
**Baseline**: Olivas v3.0.2
**Horizonte**: v3.0.3 → v4.0.0 (paridade total) → v4.1.0 (superação total)
**Origem**: 6ª garantia revisada do Master Protocol (Paridade Total + Superação Obrigatória)

> **⚠️ ATENÇÃO**: este plano foi atualizado em 2026-04-30 sob a nova
> diretriz formal: **"100% das funcionalidades do PTW devem estar
> presentes no Olivas, e o Olivas deve superá-las."**
>
> Não há mais "deferrals" ou items P2 nice-to-have. Todas as 167
> features do tutorial PTW (124 canônicas + sub-items operacionais)
> serão entregues até v4.0.0, com declaração explícita de ≥ 1
> dimensão de superação cada (das 8 dimensões formalizadas em
> `PTW_TOTAL_PARITY_DIRECTIVE.md §1.2`).

---

## 1. Contexto e premissas

A auditoria do **PTW Tutorial v8.0 (Abril 2019, 366 páginas)** mapeou
**124 funcionalidades** organizadas em 11 partes + Important Concepts.
A matriz Olivas vs PTW classificou cada item como:

| Status | Quantidade | % |
|--------|-----------|---|
| ✅ Atende plenamente | 12 | 9.7% |
| ✅ **Supera (única)** | 6 | 4.8% |
| ⚠️ Parcial / com gaps | 19 | 15.3% |
| ❌ Não atende | 84 | 67.7% |
| 🔍 Evidência ambígua | 3 | 2.4% |

**Conclusão crua**: ~68% das funcionalidades documentadas no tutorial
PTW **não estão implementadas** no Olivas. Mas:

- **Olivas SUPERA PTW em 6 frentes únicas** (NBR 17227, IEC 61850
  MMS+GOOSE+SV+BER, CRDT realtime collab, i18n PT/EN/ES,
  Plugin Marketplace, Docker)
- **Sprint A v3.0.2** (ANSI C37 core) já cobriu 4 itens A_FAULT
- **v3.0.1 audit CAPTOR** já mapeou 17 segments + 10 curves
- A maioria dos gaps (84) é **UI/editor faltante**, não algoritmo

## 2. Princípios estruturantes do plano

### 2.1 Master Protocol — 6 garantias permanentemente aplicadas

1. **Auditar** — cada release começa com audit do manual relevante
2. **Registrar** — TodoWrite + handoff doc + atualização SESSION_HANDOFF
3. **Anti-alucinação** — citar `§seção p. página` em toda fórmula
4. **Anti-crash/perda/regressão** — restore point + sweep targeted
5. **Restore point** — snapshot em `restore_points/v<X.Y.Z>_baseline/`
6. **Paridade+Superação vs PTW** — esta é a fonte deste plano

### 2.2 Estratégia de classificação (Tier 1/2/3 — TODOS são entregues)

⚠️ **Mudança de paradigma (2026-04-30)**: P2 não é mais "nice-to-have"
opcional. Sob a nova diretriz, **todos os 167 itens são entregues**.
Tier indica apenas **ordem de entrega**, não decisão de exclusão.

| Tier | Critério | # itens | Significado | Cobertura |
|------|----------|---------|-------------|-----------|
| **Tier 1** | Paridade fundacional | ~60 | Bloqueia uso comercial → sprints v3.0.3 a v3.5.0 | One-line editor, Component Editor, Load Flow, EE, TCC editor, Reports, Datablock, Scenarios |
| **Tier 2** | Paridade industrial | ~80 | Esperado por engenheiro profissional → sprints v3.5.0 a v3.7.0 | Libraries vendor, Templates, Custom Queries, Filter Design, Glove tables, Reliability lib, TMS, Reliability |
| **Tier 3** | Paridade completa | ~30 | Cobre 100% do tutorial → sprints v4.0.0 a v4.1.0 | Symbol Generator, Database Utilities, REGDEL→YAML, Aging Factor polynomial fit, Crystal Reports OSS-equivalent |

**Regra**: Tier 1 antes de Tier 2, Tier 2 antes de Tier 3 — **mas todos
são entregues**. Releases não fecham com items pendentes do tier
da release.

### 2.3 Princípio das 3 camadas

Cada release respeita 3 camadas independentes:

| Camada | Foco | Responsável |
|--------|------|-------------|
| **Engine** (algoritmos + standards) | Fórmulas testáveis, stdlib-only quando possível | `app/standards/`, `app/postprocessor/` |
| **UI** (editor + visualization) | PySide6/Qt, command pattern para UNDO | `app/gui/`, `app/preprocessor/` |
| **I/O** (libraries + reports + persistence) | Pydantic schemas, JSON/YAML, ReportLab | `app/io/`, `app/library/` |

Isso permite TDD na engine antes da UI estar pronta (modelo seguido
em v3.0.2 com `app/standards/ansi_c37.py`).

## 3. Roadmap consolidado (10 sprints v3.0.3 → v4.1.0)

⚠️ **Atualizado** sob nova diretriz: incluído **v4.1.0 — Surpassing Pass**
para garantir ≥ 1 dimensão de superação por feature antes de declarar
"superação total".

| # | Versão | Foco principal | Tier dominante | Esforço | Duração | Cobertura PTW |
|---|--------|----------------|----------------|---------|---------|---------------|
| 1 | **v3.0.3** | A_FAULT Sprint B + Single-phase + Pre-fault tolerance + Mis-coord | T1 | M | 2 sem | 25/167 (15%) |
| 2 | **v3.1.0** | One-line Editor foundation + UNDO stack + Symbol library | T1 | XL | 6–8 sem | 35/167 (21%) |
| 3 | **v3.2.0** | Component Editor + Datablock engine + Library link/unlink + Cable/TX libs | T1 | L | 4–5 sem | 50/167 (30%) |
| 4 | **v3.3.0** | Load Flow + EE + Unbalanced + IEC 60909 hardening | T1 | L | 4–5 sem | 70/167 (42%) |
| 5 | **v3.4.0** | TCC Editor interativo + Reports system + C-lines + Multi-protection | T1+T2 | L | 4–5 sem | 95/167 (57%) |
| 6 | **v3.5.0** | Scenario Manager + Data Visualizer + Find + Templates + Custom Queries | T1+T2 | L | 4 sem | 120/167 (72%) |
| 7 | **v3.6.0** | TMS — Transient Motor Starting (full) | T1+T2 | XL | 6 sem | 130/167 (78%) |
| 8 | **v3.7.0** | Reliability module + HIWAVE foundation | T1+T2 | XL | 6 sem | 145/167 (87%) |
| 9 | **v4.0.0** | HIWAVE + ISIM (full) + Symbol Generator + Form Layout + **Tier 3 cleanup** | T2+T3 | XXL | 10–12 sem | **167/167 (100%) PARIDADE TOTAL** |
| 10 | **v4.1.0** | **Surpassing Pass** — auditar cada feature, garantir ≥1 dim. superação documentada | (todos) | M | 2–3 sem | **167/167 + ≥ 1 dim. superação cada — SUPERAÇÃO TOTAL** |

**Esforço total**: ~52 sprints-semana ≈ **10–13 meses** (1 dev senior + colaboração).
**Marco "paridade funcional mínima de mercado"**: fim de v3.5.0 (~5 meses, 72% de cobertura).
**Marco "paridade total"**: fim de v4.0.0 (~10 meses, 100% das 167 features).
**Marco "superação total"**: fim de v4.1.0 (~13 meses, 100% das features × ≥ 1 dimensão de superação).

## 4. Sprints detalhados — primeiros 4 (próximas 13 semanas)

### Sprint v3.0.3 — A_FAULT Sprint B + Single-phase + Pre-fault tolerance (2 sem) 🚀 PRÓXIMO

**Objetivo**: completar gaps de SC e arc flash de baixo esforço alto impacto.

| Sub-sprint | Entrega | TDD | Cita |
|------------|---------|-----|------|
| B.1 | NACD-Ratio + Remote-only contribution factor | 6 testes | A_FAULT §1.4-1.4.3 |
| B.2 | Interrupting Multiplying Factor (MF) tables | 8 testes | A_FAULT §1.4 + C37.010 Tab 1-3 |
| B.3 | Pre-Fault Voltage tolerance (LF/PU All/PU per Bus + Util/Cable/TX Min/Reg/Max) | 10 testes | Tutorial §Part 5 p.131–135 |
| B.4 | Generator/Sync Motor decay step + Recalculate Trip Time | 6 testes | Tutorial §Part 5 p.136–137 |
| B.5 | Single-phase Mid-Tap TX (split-phase 240/120V) + per-phase load | 8 testes | Tutorial §Part 9 p.247–252 |
| B.6 | Mis-coordination ratio + Levels to Search (upstream) | 4 testes | Tutorial §Part 5 p.144–145 |

**Saídas concretas**:
- `app/standards/ansi_c37.py` — extensões NACD, MF tables, decay
- `app/standards/single_phase.py` — split-phase TX modeling
- `app/postprocessor/pre_fault_voltage.py` — tolerance handling
- `tests/test_pp_v3_0_3_*.py` — 42 testes
- `docs/v3.0.3_HANDOFF.md`
- Restore point #16 `v3.0.3_baseline`

**User Testing Gate**: `python -c "from app.standards.ansi_c37 import nacd_ratio; ..."` smoke test verde.

---

### Sprint v3.1.0 — One-line Editor Foundation + UNDO (6–8 sem) 🏗️ FUNDAÇÃO

**Objetivo**: dar ao Olivas o seu **canvas gráfico interativo**, motor de qualquer modelagem.

| Sub-sprint | Entrega | Stack |
|------------|---------|-------|
| α | QGraphicsScene/QGraphicsView setup + grid/snap/page guides | PySide6 6.x |
| β | Symbol library (Bus, Util, TX 2W/3W, Cable, Load, Motor, Fuse, Relay, Breaker, Capacitor, Gen, Filter, Pi) | SVG + QGraphicsItem custom |
| γ | Push-pin placement (toolbar drag → click drop) | Mouse event chain |
| δ | Symbol rotation 90°/180°/270° + flip | QTransform |
| ε | Auto-bus-node em série de impedâncias | Topology graph |
| ζ | Multi-document (N one-lines compartilhando DB) | Tab manager + shared model |
| η | UNDO/REDO stack (command pattern) | QUndoStack + commands |

**Decisões arquiteturais críticas**:
- **Modelo único** ↔ N views: `OlivasModel` (Pydantic) é fonte de verdade, drws são views.
- **Command pattern desde dia 0**: sem isso, retrofitar UNDO depois é caro.
- **Componentes existentes (BREAKER 3 pinos, RELAY sem T1/T2)**: reutilizar especificações de `app/components/`.

**Saídas**:
- `app/gui/oneline_editor.py` (~800 LOC)
- `app/gui/symbols/*.py` (~14 arquivos)
- `app/core/command.py` — UNDO infra
- `tests/test_pp_v3_1_0_oneline_editor_smoke.py` (~25 testes UI)
- `docs/v3.1.0_HANDOFF.md`

**User Testing Gate**: criar uma one-line com 5 componentes, salvar, fechar, reabrir, fazer 10 mudanças, UNDO 10× → estado original.

---

### Sprint v3.2.0 — Component Editor + Datablock engine (4–5 sem)

**Objetivo**: dar UI completa de edição de parâmetros + display de resultados.

| Sub-sprint | Entrega |
|------------|---------|
| α | Component Editor multipanel (tabs) — Bus, Cable, TX, Util, Load, Motor, Gen, etc. |
| β | Library link/unlink mechanism (gray-out fields quando linked) |
| γ | Datablock format engine (attribute templates `%1.0` `%2mps` `%a`, vector specs Phase Sum/Max/A/B/C/AB/BC/CA, formats R+jI/Mag+Angle/Mag+PF/Mag) |
| δ | Datablock display em one-line + TCC + Component Editor |
| ε | Cable Library (Copper/Al, THHN/THWN, magnetic/non-mag, voltage class) — popular com NEC + IEC tables |
| ζ | Transformer Library (Oil Air, Dry, Pole Mount, Single-Phase Mid-Tap) + Calculator pu→%R/%X |
| η | User Defined DB Fields (text/number/date/time/currency) + queryable |

**Saídas**:
- `app/gui/component_editor.py` (~1200 LOC)
- `app/library/cable_library.py`, `transformer_library.py`
- `app/visualization/datablock.py` — engine
- `tests/test_pp_v3_2_0_*.py`

---

### Sprint v3.3.0 — Load Flow + Equipment Evaluation + Unbalanced (4–5 sem)

**Objetivo**: completar o trio "Run Balanced System Studies" do PTW Part 2.

| Sub-sprint | Entrega | Algoritmo |
|------------|---------|-----------|
| α | Newton-Raphson Load Flow (PV/PQ/Slack buses) | NR full Jacobian |
| β | Gauss-Seidel + Fast Decoupled (alternativas para sistemas grandes) | GS, FDLF |
| γ | Transformer tap + phase shift + VFD load side | Off-nominal transforms |
| δ | Constant kVA / Constant Z / Constant I load models | Per-load type field |
| ε | IEC 60909 hardening (Voltage Factor c, Tab 1-3, b/c/n curves) | IEC SC method |
| ζ | Equipment Evaluation module (rating vs duty + continuous) | Pass/fail engine |
| η | EE: Mark Failed (red highlight) + Input Data Eval | Visual feedback |
| θ | EE: Project>Options>Equipment Evaluation user limits | Settings dialog |
| ι | Unbalanced Load Flow + UB_LF/UB_SC datablocks Phase A/B/C | Sequence components |

**Saídas**:
- `app/postprocessor/load_flow.py` — NR/GS/FDLF
- `app/postprocessor/equipment_evaluation.py`
- `app/standards/iec60909_voltage_factor.py` — extensão
- 3 docks GUI novos
- `tests/test_pp_v3_3_0_*.py` (~80 testes)

**Validação**: Stevenson 3-bus + IEEE 14-bus golden values.

## 5. Gaps superações (vantagens já existentes)

Devem ser **mantidas e divulgadas**:

| Vantagem | Versão | Tutorial PTW menciona? |
|----------|--------|------------------------|
| **NBR 17227** (norma BR arc-flash) | v1.6.0 | ❌ Único no mundo 🏆 |
| **i18n PT/EN/ES** (132 strings × 3 locales) | v2.0.0/v2.1.0 | ❌ Só EN |
| **Live SCADA IEC 61850** (MMS + GOOSE + SV + BER) | v2.0.0/v2.2.0/v2.2.1 | ❌ Não cobre IEC 61850 |
| **CRDT realtime collab** (Lamport + LWW + ORSet) | v3.0.0 | ❌ Só Scenarios paralelos |
| **Plugin Marketplace** | v1.5.0/v1.5.1 | ❌ Closed-source |
| **Docker + Python 3.13** | v2.0.0 | ❌ Windows + FlexLM |
| **CSA Z462 + Doughty-Neal + EPRI + DC arc-flash + Terzija** | v1.6.0 | ⚠️ Só IEEE 1584 + NFPA 70E + NESC |
| **8 standards arc-flash side-by-side** | v1.6.0 | ❌ Só 1 standard ativo por vez |
| **CT Saturation 3-níveis (ANSI/IEC/dynamic)** | v1.4.4 | ❌ Não dedicado |

**Recomendação**: capítulo de marketing "Olivas vs PTW: 6 vantagens
únicas" no website + README.

## 6. Convergência crítica: CRDT ≠ Scenarios

**ALERTA arquitetural** descoberto na auditoria:

| Conceito | Olivas (v3.0.0) | PTW (Tutorial §Part 11 p.319–344) |
|----------|-----------------|-----------------------------------|
| **CRDT (Olivas)** | Edição **sincronizada** entre múltiplos usuários no mesmo modelo | (não tem) |
| **Scenarios (PTW)** | (não tem) | Branches **paralelos** dentro do mesmo arquivo, com Promote-to-Base |

**São paradigmas distintos.** Olivas precisa **adicionar** Scenarios em
v3.5.0 sem perder o CRDT. A infra CRDT pode ser reaproveitada para
**snapshot** (LWW Register para pin de scenario), mas a semântica
"branching + merge" exige novo módulo.

## 7. Limitações declaradas (anti-alucinação)

1. **Tutorial é v8.0 (Abril 2019)** — features do PTW pós-2019 (v9, v10, v11) **não estão neste audit**. Recomenda-se complementar com **Release Notes SKM v9-v11** em audit futuro.
2. **Tutorial é didático, não exaustivo** — profundidade técnica de cada módulo está nos manuais Reference (DAPPER, CAPTOR já mapeado, A_FAULT já mapeado, IEC_FAULT, Equipment Eval, Arc Flash, TMS, HIWAVE, ISIM, Reliability, Multi-User Library/Project). Recomenda-se aquisição/extração desses PDFs antes de v3.4.0+.
3. **Itens marcados 🔍 ambíguos** (#10 Bus Load Diversity, #44 Arcing Fault Tolerances, #100 Application standard toggle) precisam inspeção do código fonte v3.0.x antes da classificação definitiva ser confiável.
4. **Esforço estimado é heurístico** (1 dev senior). Real depende de:
   - Cobertura de testes existentes
   - Refatoração necessária (ex: novos componentes pedem alterar `ComponentSpec` schema)
   - Validação contra IEEE/IEC examples (golden values demoram)
5. **Recomendação não-técnica**: validar este plano com 1 engenheiro PTW user (NDA) em 1–2 sessões para calibrar Severidades.

## 8. Métricas e indicadores de sucesso

| Indicador | Baseline v3.0.2 | Meta v3.5.0 | Meta v4.0.0 |
|-----------|-----------------|-------------|-------------|
| Funcionalidades PTW Tutorial cobertas | 18/124 (15%) | 80/124 (65%) | 110/124 (89%) |
| Funcionalidades PTW Tutorial superadas | 6 únicas | 8 únicas | 10+ únicas |
| Testes próprios | ~191 (recent) + ~360 (full) | +200 | +400 |
| Restore points | 15 | 22 | 27 |
| Manuais PTW auditados profundamente | 2 (CAPTOR + A_FAULT) + Tutorial | +5 | +9 |
| Master Protocol garantias aplicadas | 6/6 | 6/6 (mantido) | 6/6 (mantido) |

## 9. Riscos identificados

| # | Risco | Mitigação |
|---|-------|-----------|
| 1 | One-line editor (v3.1.0) é XL — pode estourar timeline | Quebrar em 7 sub-sprints; entregar α-β-γ sem ε-ζ-η se necessário |
| 2 | Load Flow NR pode ter bugs sutis sem golden tests | TDD com Stevenson 3-bus + IEEE 14-bus desde sub-sprint α |
| 3 | TCC Editor pede matplotlib custom canvas — risco de performance | Profile early; alternativa Qt nativo ou Plotly |
| 4 | Reports (.RPT + Crystal-equivalent) pode pedir 3rd-party libs pesados | Avaliar ReportLab vs WeasyPrint vs Jinja2+wkhtmltopdf cedo |
| 5 | TMS/HIWAVE/ISIM pedem solver ODE robusto | Considerar SciPy `solve_ivp` ou própria implementação Runge-Kutta-Fehlberg |
| 6 | Reference manuals (DAPPER, IEC_FAULT, etc.) podem não estar disponíveis | Complementar com IEEE Color Books (141, 399, 493, 1015) + IEC 60909 + IEEE 1366 |
| 7 | Scaling para projetos grandes (1000+ buses) | Testar com IEEE 118-bus em v3.3.0+ |
| 8 | UI/UX não-PTW-style pode confundir users PTW | Manter convenções PTW (push-pin, Component Editor tabs, Datablock format) |

## 10. Próxima sessão — checklist v3.0.3 (Sprint B)

1. [ ] Audit `Reference-A_Fault.pdf` §1.4-1.4.3 (NACD + MF tables) — agente paralelo
2. [ ] Restore point `v3.0.2_baseline` já criado (15º) ✅
3. [ ] TDD `tests/test_pp_v3_0_3_nacd.py` (Sprint B.1)
4. [ ] Implementar `app/standards/ansi_c37.py::nacd_ratio()` + `interrupting_mf()`
5. [ ] TDD + impl Pre-Fault Voltage tolerance (B.3)
6. [ ] TDD + impl Single-phase Mid-Tap TX (B.5) — pode virar `app/standards/single_phase.py`
7. [ ] Sweep targeted regression
8. [ ] Bump 3.0.2 → 3.0.3 em `app/core/version.py`
9. [ ] Doc `docs/v3.0.3_HANDOFF.md`
10. [ ] Update `docs/SESSION_HANDOFF.md`
11. [ ] Restore point `v3.0.3_baseline` (16º)

---

## Anexos

- **Auditoria completa**: `docs/PTW_TUTORIAL_AUDIT_v3.0.3.md` (124 features, 4 seções A-D)
- **Manual referência**: `D:\000 - UFMG - DOUTORADO\MVP\LIB\PTW Tutorial.pdf`
- **Texto extraído**: `/tmp/ptw_tutorial.txt` (6447 linhas, 366 páginas)
- **Outros audits PTW**: `docs/PTW_PARITY_OBJECTIVE.md` (CAPTOR + A_FAULT já cobertos)
- **Releases prévias**: `docs/v1.5.0_HANDOFF.md` ... `docs/v3.0.2_HANDOFF.md`

**Status**: ✅ Plano de ação registrado. Próximo passo = Sprint v3.0.3.
