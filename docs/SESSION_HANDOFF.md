# SESSION HANDOFF — Continuation Protocol

> **Propósito**: documento vivo lido pela **próxima sessão Claude**
> ao iniciar uma nova janela de contexto, garantindo continuidade
> sem perda de estado entre sessões.
>
> **Atualizado em**: 2026-05-01 (final da sessão v4.0.0-alpha → v4.0.0-beta — UAT preparation)
>
> Localização: `docs/SESSION_HANDOFF.md` (PRIMEIRO arquivo a ler
> ao iniciar nova sessão).

---

## 1. Contexto do projeto

**Olivas Power System Studio** — alternativa nacional brasileira a
SKM PTW / EasyPower / ETAP. Doutorado UFMG, Landerson Ferreira Silva.

* **Stack**: Python 3.11/3.13, PySide6, pytest
* **Path**: `D:/000 - UFMG - DOUTORADO/MVP/`
* **Versão atual**: **4.0.0-beta** (após sessão de 2026-05-01 — UAT prep)
* **Locale**: pt-BR (default), EN/ES via i18n

## 2. Master Protocol (7 garantias — 7ª NEW v3.1.0) — SEMPRE aplicar

1. **Auditar** (vX.Y.Z_BACKLOG_AUDIT.md) antes de qualquer mudança
2. **Registrar** (TodoWrite + docs versionados)
3. **Anti-alucinação** (citações de fonte primária; sem inventar)
4. **Anti-crash/perda/regressão** (Read-then-Edit; sweep antes/depois)
5. **Ponto de restauração** (snapshot em `restore_points/<versao>_baseline/`)
6. **Paridade Total + Superação Obrigatória vs PTW** (v3.0.3+ — endurecida em 2026-04-30):
   - **100% das features PTW** devem estar presentes em Olivas até v4.0.0
   - **Cada feature** implementada deve declarar **≥ 1 dimensão de superação**
     (das 8 formalizadas em `PTW_TOTAL_PARITY_DIRECTIVE.md §1.2`)
   - **Não há deferrals** — Tier 1/2/3 indica ordem, não exclusão
   - 8 critérios de aceite por release (ver `PTW_TOTAL_PARITY_DIRECTIVE.md §4`)
7. **Acessibilidade GUI obrigatória** ⚡ NOVA (v3.1.0+, vigência 2026-04-30):
   - **Toda feature backend implementada DEVE ter ponto de entrada GUI**
     (menu, toolbar, dialog, property panel ou paleta)
   - **Backend órfão é proibido** a partir de v3.1.0
   - 3 critérios adicionais (totalizando 11 critérios): trigger GUI documentado,
     deep GUI audit pós-sprint, smoke test manual descrito
   - Texto formal: `PTW_TOTAL_PARITY_DIRECTIVE.md §8.3`

Documentos mestres:
- **`docs/CONTEXT_PRESERVATION_PROTOCOL.md`** ⚡ NOVO (8ª garantia 2026-05-01) — leitura obrigatória ao iniciar nova sessão
- **`docs/SKIPPED_BACKLOG.md`** ⚡ persistente — débito técnico (14 itens, cap 15)
- `docs/v1.7.0_MASTER_PROTOCOL.md` (5 garantias originais)
- `docs/v1.6.0_SAFEGUARDS_PROTOCOL.md` (extensão)
- `docs/PTW_PARITY_OBJECTIVE.md` (6ª garantia — texto formal endurecido 2026-04-30)
- **`docs/PTW_TOTAL_PARITY_DIRECTIVE.md`** ⚡ (diretriz "100% + superação" — máxima autoridade)
- `docs/PTW_TUTORIAL_AUDIT_v3.0.3.md` (audit completo Tutorial v8.0 — 124 features canônicas)
- `docs/PTW_SURPASSING_MATRIX.md` (matriz 167 features × 8 dimensões de superação)
- `docs/PTW_PARITY_ACTION_PLAN.md` (roadmap operacional 10 sprints v3.0.3 → v4.1.0)

## 3. Estado atual (após v3.5.0)

### 3.1 Restore points criados (27)

* `restore_points/v1.6.0_baseline/` ... `v3.4.0_baseline/`

### 3.2 SKIPPED_BACKLOG (11 itens — anti-esquecimento)

Lista persistente em `docs/SKIPPED_BACKLOG.md`. **Antes de v4.0.0
(Paridade Total) deve ser zerada.** Política: cap de 15 itens.

Para reverter: `cp -r restore_points/<versao>/app_snapshot app/`

### 3.2 Releases entregues (após CT-SAT v1.4.3)

| Versão | Tema | Testes próprios |
|--------|------|-----------------|
| v1.4.4 | CT Saturation Study completo | 33+ |
| v1.4.5 | User gate fixes (PTW patterns) | 13 |
| v1.5.0 | Plugin Marketplace | 39 |
| v1.5.1 | DAPPER 22 NEC categories | 35 |
| v1.6.0 | Arc-flash 8 standards | 51 |
| v1.7.0 | Polish + Master Protocol | 32 |
| v1.7.1 | Active state em components | 9 |
| v2.0.0 | Commercial (i18n + Docker + IEC 61850 + license) | 33 |
| v2.0.1 | Critical UX fixes (pin dots + multi-drag + plot refresh) | 8 |
| v2.0.2 | Pin categorization + topology validator | 10 |
| v2.0.3 | BREAKER 3 pinos + RELAY sem T1/T2 laterais | — (renderer) |
| v2.0.4 | Plot docks auto-refresh após F5 | 5 |
| v2.1.0 | i18n full coverage (58 → 132 strings EN/ES) | 12 |
| v2.1.1 | Locale Picker UI dialog | 7 |
| v2.2.0 | IEC 61850 GOOSE + SV stub mode | 21 |
| v2.2.1 | ASN.1 BER wire format (encoders + decoders) | 19 |
| v3.0.0 | CRDT Real-time Collab + Audit Findings + 2 Critical Fixes | 19 |
| v3.0.1 | Objetivo formal Paridade+Superação PTW + Deep CAPTOR audit | (audit-only) |
| v3.0.2 | ANSI C37 short-circuit core (A_FAULT Sprint A) | 20 |
| v3.0.3 | A_FAULT Sprint B — NACD + MF + decay + asym + single-phase + mis-coord | 103 |
| v3.0.4 | A_FAULT Sprint C — TX taps + Solution Methods + Plant §1.4.4 5 buses | 40 |
| v3.0.5 | A_FAULT Sprint D Final — AnsiFaultBus + AnsiFaultReport + 3 formatters + integration pipeline | 34 |
| v3.1.0 | Track B Backfill GUI — 5 dialogs A_FAULT + 7ª garantia formalizada | 53 |
| v3.1.1 | Track A One-line Editor PTW §Part 1 (push-pin + 3 components + linked_library + Tags) | 48 |
| v3.1.2 | Editor deferreds finalization (UI gray-out + Tag rendering + AddSeries + sidecar) | 24 |
| v3.1.3 | Wire integration (context menu Tags + link_tag_navigate + drop-on-wire + auto sidecar) | 20 |
| v3.2.0 | Component Editor Multipanel (N tabs por PropertyGroup + ícones + Datablock tab + linked_library wiring fix) | 12 |
| v3.3.0 | Tier 1 algorítmico — Unbalanced PF Dialog + kappa_method wire + IEEE 14-bus + build_equipment + KT/KG/KSO | 40 |
| v3.3.1 | Audit-driven deferreds — PowerFlow N-bus + EE auto-load + correction_factor + decay μ·q | 16 |
| v3.4.0 | TCC Editor extensions — C-lines (PPE constant IE) + TCC Report export + SKIPPED_BACKLOG persistente | 20 |
| v3.5.0 | Scenario Manager (PpScenario + ScenarioManager + Dialog) + 8ª garantia (CONTEXT_PRESERVATION_PROTOCOL) | 18 |
| v3.5.1 | SKIPPED_BACKLOG cleanup — A.3 (wire path-based detection) closed; A.1+A.2 deferred → v3.5.2 | 18 |
| v3.5.2 | A.1 (AddLinkTagDialog) + A.2 (MainWindow document registry) closed; categoria A 100% encerrada | 11 |
| v3.6.0 | Reliability module (SAIFI/SAIDI/CAIDI/ASAI + MTBF/MTTR + series/parallel) IEEE 1366-2012; ReliabilityDialog wired Análise menu | 35 |
| v3.6.2 | D.1 (C-lines paint real matplotlib overlay) + D.2 (multi-protection filter Phase/Ground combo) — categoria D 67% encerrada | 13 |
| v3.7.0 | B.2 (bus_role explicit slack/pv/pq) + B.3 (q_factor com motor_speed_gradient n_per_unit_per_second) — categoria B 50% encerrada; sprint paridade real PF iniciado | 19 |
| v3.7.1 | B.1 (Tr/CABLE/TLIN branch impedance real extraction; IEC 60076 + IEC 60364) — categoria B 75% encerrada | 22 |
| v3.7.2 | C.1 (PowerFlowDialog DEPRECATED banner) + C.2 (EquipmentEval hybrid demo+project mode) — categoria C 50% encerrada | 7 |
| v3.8.0 | Reliability Monte Carlo (IEEE 493 presets + time-series MC + 90% CI) — major feature add | 18 |
| v3.8.1 | C.3 (IEEE 14-bus fixture subset + golden) + C.4 (PV→PQ Q-limit switching, IEEE 399 §5.3.4) — Categoria C 100% encerrada | 14 |
| v3.8.2 | D.3 (TCC 3-tab pages Settings/Curves/Datablock) — Categoria D 100% encerrada | 12 |
| v3.9.0 | B.4 (fault distance walker auto-classify NEAR/FAR + n_per_unit_per_second from n_poles) — Categoria B 100% encerrada | 16 |
| v4.0.0-alpha | 🏆 PARIDADE TOTAL v1 — todas as 4 categorias 100% (A+B+C+D); SKIPPED_BACKLOG zerado; sweep total 219/219 | 16 |
| **v4.0.0-beta** | **UAT preparation: i18n EN/ES parity verified (133/133), CHANGELOG.md consolidado, production readiness checks (26 tests), sweep total 245/245** (atual) | **26** |

**Sweep de regressão targeted**: 361 passed / 25 skipped / 0 failures
(v1.7.4 sweep, ratificando anti-perda).

### 3.3 Lista TRAVADA (anti-perda — NÃO TOCAR)

12 arquivos arc-flash core (v1.4.0 + v1.6.0):
* `app/postprocessor/arc_flash.py`, `app/standards/epri_arc_flash.py`,
  `app/standards/nbr17227.py`, `arc_flash_label.py`,
  `arc_flash_monte_carlo.py`, `arc_flash_comparison.py`,
  `nesc_2023_arc_flash.py`, `doughty_neal_arc_flash.py`,
  `dc_arc_flash.py`, `csa_z462_arc_flash.py`

5 arquivos CT Saturation:
* `ct_saturation.py`, `ct_saturation_io.py`, `ct_saturation_plots.py`

5 arquivos Plugins (v1.5.0):
* `manifest.py`, `lifecycle.py`, `security.py`, `registry.py`,
  `builtin/**`

3 arquivos DAPPER (v1.5.1):
* `dapper_catalog.py`, `dapper_io.py`, `studies/demand_load.py`

Arquivos v2.0.0 (Live SCADA + Docker + i18n + commercial):
* `app/i18n/__init__.py`, `app/integration/iec61850_client.py`,
  `app/commercial/license_key.py`, `app/commercial/telemetry.py`,
  `Dockerfile`, `docker-compose.yml`

## 4. Issues conhecidos (deferred / open)

### 4.1 Power Flow não roda em F5

* `solve_power_flow()` existe em `app/postprocessor/power_flow.py`
  mas **não é chamado** pelo run_analysis_dialog (F5)
* Logo `cache.has_pf()` sempre False → PF Voltage Profile dock
  fica em empty state mesmo após F5
* **Plano**: v1.7.3 (próximo sprint) — adicionar PF ao run dialog
* Lugar para fix: `app/gui/main_window.py::_on_run_analysis_dialog`

### 4.2 BASELINE 4573 testes — sweep total nunca passou completamente em 1 run

* Problema é runner pytest no Windows com 4647 testes coletados
* Targeted sweeps (77, 397, 196 etc) **todos passam**
* Recomendação: usuário rodar `pytest tests/ -q --tb=line >
  full_sweep.txt 2>&1` em terminal próprio para confirmar baseline

### 4.3 56 component specs sem state property

* Apenas 3 (BREAKER/FUSE/CONTACTOR) têm `state` em YAML
* Outros 53 podem se beneficiar (paridade PTW Out-of-Service)
* **Plano**: v1.7.3+ (defer; baixa prioridade)

## 5. Pedido user em curso (2026-04-30 — última sessão)

* ✅ **v3.0.3 Sprint B** A_FAULT (103 testes backend)
* ✅ **v3.0.4 Sprint C** A_FAULT (40 testes backend)
* ✅ **v3.0.5 Sprint D Final** A_FAULT (34 testes backend) — backend FECHADO
* ✅ **v3.1.0 Track B Backfill GUI** (53 testes GUI) — 7ª garantia ⚡ NEW:
  - B-1 ANSI Short Circuit Dialog (Ctrl+Shift+A) — 17 testes
  - B-2 Pre-Fault Voltage Settings dialog — 10 testes
  - B-3 ANSI Utilities (Mis-coord/Conversion/Tap) — 13 testes
  - B-4 Fault Decay temporal dialog — 7 testes
  - B-5 Balanced System Studies orchestrator — 6 testes
  - **5 dialogs novos GUI** wired ao menu (0 órfãos restantes)
* ✅ Cumulativo v3.0.x A_FAULT: **197 testes** (20+103+40+34) backend
  - D.1 AnsiFaultBus unified (LV+Mom+Int reports) (11 testes)
  - D.2 AnsiFaultReport + 3 formatters (text/markdown/csv) (10 testes)
  - D.3 Golden text reproduction §1.4.4 5 buses (8 testes)
  - D.4 Integration pipeline (composição 6 módulos v3.0.x) (5 testes)
* ✅ Cumulativo v3.0.x A_FAULT: **197 testes** (20+103+40+34)
* ✅ Sweep regression **308 verdes** (v2.x + v3.x cumulativo, +53 v3.1.0)
* ✅ Restore point v3.1.0_baseline (19º total)
* ✅ Cobertura PTW Tutorial: **38/167 (23%)** — era 33 → +5 v3.1.0 (acessível!)
* ✅ Backend A_FAULT órfãos GUI: **0/0** ⬇ era 10/10 antes
* ⏳ **Próxima sessão**: **v3.1.1 — One-line Editor foundation** (Tier 1
  XL, 6-8 sem) — canvas gráfico interativo (QGraphicsView + push-pin +
  symbols + UNDO). Track A do roadmap original.
  Alternativas:
  - v3.1.2 — Mis-coordination multi-device search
  - v3.1.3 — Pre-Fault Voltage QSettings persistence
  - v3.0.6 — DAPPER solver foundation

## 6. Próximos passos sugeridos para nova sessão

### 6.1 Imediato

1. Aguardar user testing gate visual de v2.0.1:
   * Abrir Olivas
   * Ver pin dots cinza/azul nos componentes (BREAKER, RELAY, CT etc)
   * Selecionar 2+ componentes, arrastar — wires devem seguir
   * F5 com SC marcado → dock SC abre populado
2. Se gate passou: pode proceder para v1.7.3

### 6.2 v1.7.3 (próximo sprint sugerido)

* **Adicionar Power Flow ao run dialog** (issue 4.1)
* Hook `solve_power_flow()` em `_on_run_analysis_dialog` quando
  checkbox "Power Flow" estiver marcado
* `cache.set_pf(result, hash)` para popular o cache
* Refresh dock PF (já implementado em v2.0.1)
* TDD: golden values de Stevenson 3-bus exemplo

### 6.3 v1.7.x acumulado (deferred)

* state property em mais 53 component specs
* Cobertura completa i18n (atual ~35% das strings UI)
* IEC 61850 GOOSE/SV (deferido em v2.0.0)

## 7. Comandos úteis para nova sessão

```bash
# Verificar versão
cd "D:/000 - UFMG - DOUTORADO/MVP"
python -c "from app.core.version import VERSION; print(VERSION)"
# Esperado: 3.0.3

# Smoke test v3.0.3 NACD (golden Case §1.4.3 Case 2)
python -c "
from app.standards.ansi_c37 import GeneratorContribution, nacd_ratio
gens = [
    GeneratorContribution('UTIL', 'PROC_A', 9.401, z_external_pu=2.0, xd_pu=1.0),
    GeneratorContribution('G1', 'PROC_A', 1.307, z_external_pu=0.10, xd_pu=0.20),
]
print(f'NACD = {nacd_ratio(gens, 13.871):.4f}')  # Esperado: 0.6778
"

# Sprint B full suite (103 testes)
python -m pytest tests/test_pp_v3_0_3_*.py -q
# Esperado: 103 passed

# Targeted sweep regression
python -m pytest tests/test_pp_v3_0_3_*.py tests/test_pp_v3_0_2_ansi_c37.py tests/test_pp_v3_0_0_crdt.py -q
# Esperado: 123 passed (sem regressão)

# Sweep targeted (rápido)
python -m pytest tests/test_pp_v1_7_2_ux_fixes.py \
  tests/test_pp_v1_7_1_active_state.py \
  tests/test_pp_v1_7_0_window_state.py \
  tests/test_pp_v2_0_0_*.py -q

# Ler audit recente
cat docs/v1.7.2_BACKLOG_AUDIT.md
cat docs/v2.0.0_HANDOFF.md
```

## 8. Glossário rápido

| Termo | Significado |
|-------|-------------|
| BUS | Barramento elétrico |
| CT | Transformador de Corrente |
| TC | (PT) Transformador de Corrente — sinônimo CT |
| CT-SAT | Análise de saturação de TC (3 níveis) |
| DAPPER | Demand Load study (estilo PTW) |
| TCC | Time-Current Characteristic (curvas coordenação) |
| Trip_in | Pin de entrada de trip do BREAKER |
| live/dead bus | Energizado / desenergizado (NBR 5410, IEC 61850) |
| MMS | Manufacturing Message Specification (IEC 61850-8-1) |
| Master Protocol | 5 garantias formalizadas para qualquer mudança |
| Lista TRAVADA | Arquivos NÃO modificáveis (anti-perda) |
| Restore point | Snapshot completo de app/ + tests/ |

## 9. Padrões de código a manter

* PT como locale default (não traduzir docstrings/comentários)
* Citações de norma + seção em todas as fórmulas
  (IEEE 1584-2018 §6.5 Eq. 8, NBR 5410 §6.2, etc)
* Anti-perda: Read-then-Edit; novos arquivos > edits
* Pydantic para schemas (ComponentSpec, PluginManifest, etc)
* Try/except defensivo em paint hooks (anti-crash)

## 10. Anti-alucinação — pegadinhas conhecidas

* **NÃO inventar fórmula** — Doughty-Neal-Floyd in-box vs open-air
  tem ordering empírico contraintuitivo (paper original 2000)
* **NÃO assumir que classe Pydantic permite extra=allow** —
  ComponentSpec usa `extra="forbid"`, adicionar field exige
  modificação do schema
* **NÃO subscript dict.get com default=None sem checar** — comum
  em `PpComponent.properties` (lista de PpProperty, não dict)
* **NÃO chamar populate_from_cache de PF dock no F5** — `cache.set_pf`
  ainda não é chamado pelo run dialog (issue 4.1 acima)

---

**Esta é a fonte de verdade entre sessões.** Atualizar SEMPRE
antes de fechar uma sessão longa.
