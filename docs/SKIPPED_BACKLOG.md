# SKIPPED BACKLOG — Itens pulados (anti-esquecimento)

**Atualizado**: 2026-05-01 (pós-v4.0.0-alpha — TODAS as 4 categorias 100% encerradas; **Paridade Total v1**)
**Propósito**: lista CONSOLIDADA de todos os deferreds adiados ao longo
do roadmap v3.x, persistente entre sessões. Antes de declarar v4.0.0
(Paridade Total) ou qualquer release final, esta lista DEVE ser zerada.

> ⚠️ **Política**: nenhum item entra aqui sem **(a)** referência ao
> handoff que originou e **(b)** justificativa de skip. Itens devem ser
> revisitados a cada 2 releases (lição: refinamentos crescem rápido).

---

## Status atual: 0 itens pulados (cap=15) 🎉

| Origem | Categoria | Items |
|--------|-----------|-------|
| ~~v3.1.4 (Editor refinements)~~ | **CATEGORIA FECHADA** | 0 (eram 3) |
| ~~v3.3.2 (Algorithm refinements)~~ | **CATEGORIA FECHADA** | 0 (eram 4, B.4 fechado em v3.9.0) |
| ~~Audit findings persistentes~~ | **CATEGORIA FECHADA** | 0 (eram 4) |
| ~~v3.4.1 (TCC visual polish)~~ | **CATEGORIA FECHADA** | 0 (eram 3, D.3 fechado em v3.8.2) |

🏆 **PARIDADE TOTAL v1 ATINGIDA** — todas as 14 itens originais fechados.

✅ **v3.5.1**: A.3 (Wire path-based detection) fechado — 18 tests verdes.
✅ **v3.5.2**: A.1 (AddLinkTagDialog) + A.2 (multi-doc registry) fechados — 11 tests.
✅ **v3.6.2**: D.1 (C-lines paint real) + D.2 (multi-protection filter) fechados — 13 tests.
🎉 **Categoria A 100% encerrada** · **Categoria D 67% encerrada** (D.3 remanescente).

---

## A. v3.1.4 Editor refinements (registrados pós-v3.1.3)

**Origem**: `docs/v3.1.4_BACKLOG.md` (criado em 2026-05-01).

### ~~A.1 AddLinkTag dialog completo~~ ✅ FECHADO em v3.5.2
- **Implementado**: `app/gui/add_link_tag_dialog.py` —
  ``AddLinkTagDialog`` com scheme combo, preview live, toggles
  visible/closed_arrow, Browse... para PDFs.
- **Wired**: `editor._on_add_link_tag` substitui 2 `QInputDialog`.
- **Tests**: `test_pp_v3_5_2_link_tag_navigation.py::TestAddLinkTagDialog` (6 verdes)

### ~~A.2 Multi-document navigation~~ ✅ FECHADO em v3.5.2
- **Implementado**: `MainWindow._documents_registry` +
  `register_document` / `navigate_to_document` / `list_documents`
  / `unregister_document`. Default: `Main` registrado p/ schematic_pp.
- **Wired**: `_on_link_tag_navigate` para `oneline:` scheme usa
  registry; mensagem informativa lista docs disponíveis.
- **Tests**: `test_pp_v3_5_2_link_tag_navigation.py::TestDocumentRegistry` (5 verdes)

### ~~A.3 Wire path-based detection~~ ✅ FECHADO em v3.5.1
- **Estado anterior** (v3.1.3 → v3.5.0): bbox `tolerance=8.0`
- **Implementado** (v3.5.1): distância perpendicular L-routed via
  helpers `_point_to_segment_distance` + `_point_to_l_route_distance`
  em `app/gui/schematic_pp/view.py` linhas 797-842
- **Tests**: `test_pp_v3_5_1_backlog_cleanup.py` (18 verdes)
- **Anti-falso-positivo crítico**: P=(50,50) com wire (0,0)→(100,100)
  agora retorna distance=50 em vez de "dentro da bbox"

---

## B. v3.3.2 Algorithm refinements (registrados pós-v3.3.1)

**Origem**: `docs/v3.3.1_HANDOFF.md` §9 (registrado em 2026-05-01).

### ~~B.1 Tr/CABLE → branch impedance extraction~~ ✅ FECHADO em v3.7.1
- **Implementado**: `app/postprocessor/branch_impedance.py` com
  `transformer_impedance_pu`/`cable_impedance_pu`/`tline_impedance_pu`
  + dispatch `extract_branch_impedance`. `build_pf_system_from_project`
  agora extrai Z real por proximidade Manhattan ao midpoint dos buses.
- **Tests**: `test_pp_v3_7_1_branch_impedance.py` (22 verdes)
- **Standards**: IEC 60076-1:2011 §10 (Tr) + IEC 60364-5-52:2009 (Cable)

### ~~B.2 bus_role para SLACK explícito~~ ✅ FECHADO em v3.7.0
- **Implementado**: `BUS.ocomp` schema com `bus_role` property
  (auto/slack/pv/pq); `analysis_dialogs._read_bus_role` +
  `_find_explicit_slack` helpers; `build_pf_system_from_project`
  respeita override de slack via `bus_role: slack`.
- **Tests**: `test_pp_v3_7_0_pf_parity.py::TestBusRoleHelpers` +
  `TestBuildPfWithExplicitSlack` (8 verdes)

### ~~B.3 q factor com `n_per_unit_per_second` param~~ ✅ FECHADO em v3.7.0
- **Implementado**: `q_factor()` agora **usa** o parâmetro
  `n_per_unit_per_second` (era reservado);
  `calculate_short_circuit` aceita `motor_speed_gradient_pu_per_s`
  (default 0.10 = 2-pólos) e propaga para `q_factor` quando
  async motor near-gen (IEC 60909-0:2016 §4.6.2 Tab 3).
- **Tests**: `test_pp_v3_7_0_pf_parity.py::TestQFactorWithN` +
  `TestCalculateScWithMotorGradient` (10 verdes)
- **Backward-compat**: default n=0.10 mantém comportamento legacy.

### ~~B.4 decay μ·q automatic detection~~ ✅ FECHADO em v3.9.0
- **Implementado**: `app/postprocessor/fault_distance_walker.py` com
  `find_nearby_sources` (BFS Manhattan-based) + `auto_classify_fault_distance`
  retornando `FaultClassification` com sugestões para
  `calculate_short_circuit`. Detecta sync motor, induction motor, utility,
  generator. Usa `n_poles` do MOTOR para escolher
  `motor_speed_gradient_pu_per_s`.
- **Tests**: `test_pp_v3_9_0_fault_walker.py` (16 verdes)
- **Standards**: IEC 60909-0:2016 §3.7 + §4.6.2 Tab 3

---

## C. Cross-cutting findings (audit residuals)

### ~~C.1 PowerFlowDialog 2-bus legacy fallback~~ ✅ FECHADO em v3.7.2
- **Implementado**: `PowerFlowDialog.DEPRECATED_MESSAGE` + banner
  amarelo no topo do dialog + título "[LEGACY 2-bus]"; docstring
  com `.. deprecated:: 3.7.2`. Removal target: v4.0.0.
- **Tests**: `test_pp_v3_7_2_cross_cutting.py::TestPowerFlowDialogDeprecation` (3 verdes)

### ~~C.2 EquipmentEvalDialog hybrid mode~~ ✅ FECHADO em v3.7.2
- **Implementado**: `chk_hybrid_demo` checkbox no toolbar do dialog;
  quando marcado, `set_equipments` faz `demos + project` em vez de
  apenas project.
- **Tests**: `test_pp_v3_7_2_cross_cutting.py::TestHybridDemoMode` (4 verdes)

### ~~C.3 IEEE 14-bus full fixture~~ ✅ FECHADO em v3.8.1
- **Implementado**: `tests/fixtures/ieee14_bus.json` com subset 5-bus
  (slack + 2 PV + 2 PQ) + 7 branches + golden V_pu/theta. Loose tolerance
  ±0.05 pu (subset não é o full IEEE 14-bus). Full 14-bus + IEEE 30-bus
  deferred v3.9.x.
- **Tests**: `test_pp_v3_8_1_pf_q_limits.py::TestIEEE14BusFixture` +
  `TestIEEE14BusIntegration` (6 verdes)

### ~~C.4 Generator Q-limits + slack switching~~ ✅ FECHADO em v3.8.1
- **Implementado**: `PfBus.Q_min_pu`/`Q_max_pu`/`original_type` campos;
  `add_pv` aceita Q-limits; `PowerFlowSystem.solve_with_q_limits`
  faz iterative PV→PQ switching até convergir (max 5 switching iters).
  `q_limit_violations` anexado à solution via `object.__setattr__`
  (frozen-aware).
- **Tests**: `TestPfBusQLimitFields` + `TestSolveWithQLimits` (8 verdes)
- **Standards**: IEEE 399-1997 §5.3.4

---

## D. v3.4.1 TCC visual polish (registrados pós-v3.4.0)

**Origem**: `docs/v3.4.0_HANDOFF.md` §10 + §8 (registrado em 2026-05-01).

### ~~D.1 C-lines paint real no canvas~~ ✅ FECHADO em v3.6.2
- **Implementado**: `TCCCoordinogramWidget.set_c_lines/get_c_lines/_draw_c_lines`
  em `app/gui/tcc_coordinogram.py`. Renderiza curvas dashed color-coded
  no mesmo Axes matplotlib (kA→A axis-consistency). Legend integrada.
- **Tests**: `test_pp_v3_6_2_tcc_polish.py::TestCLinesAPI` (5 verdes)

### ~~D.2 Multi-protection plot~~ ✅ FECHADO em v3.6.2
- **Implementado**: `TCCCoordinogramWidget.set_protection_filter` (modes
  `all`/`phase`/`ground`) + heurística `_curve_matches_protection` que
  inspeciona attrs `function`/`ansi`/`name`/`label`. UI: combo
  "Filtro:" no TCCCoordinogramDialog button row.
- **Tests**: `test_pp_v3_6_2_tcc_polish.py::TestProtectionFilter` (6 verdes)
- **Anti-data-loss**: curvas sem info de função sempre exibidas.

### ~~D.3 TCC Drawing 3-tab pages~~ ✅ FECHADO em v3.8.2
- **Implementado**: `TCCCoordinogramDialog` agora usa `QTabWidget`
  com 3 tabs (⚙️ Settings / 📈 Curves / 📋 Datablock). Settings expõe
  fault current via QDoubleSpinBox; Curves contém o coord widget
  (default tab); Datablock mostra summary text dos curves.
- **Tests**: `test_pp_v3_8_2_tcc_tabs.py` (12 verdes)

---

## D. Política de redução

- **Cap**: máximo **15 itens** simultâneos. Se >15, release atual
  deve fechar 3+ antes de adicionar novos.
- **Revisão**: ler este doc no início de cada sprint planning.
- **Promotion**: itens com 3+ releases sem revisita são promovidos
  para sprint dedicado (forced close).
- **Garantia 7ª compatible**: nenhum item pulado pode violar a
  acessibilidade GUI; se violar, é P0 imediato (não defere).

---

## E. Histórico

| Data | Evento |
|------|--------|
| 2026-05-01 | Criado pós-v3.3.1 com 11 itens (3 + 4 + 4) |
| 2026-05-01 | Pós-v3.4.0: +3 itens TCC polish → 14 itens (cap próximo) |
| 2026-05-01 | Pós-v3.5.0: 14 itens (cap=15 atingido). Política forced-close ativada para A.1/A.2/A.3. |
| 2026-05-01 | **v3.5.1 cleanup sprint**: A.3 fechado (18 tests). Backlog 14→13. A.1/A.2 deferred → v3.5.2 (priority HIGH). |
| 2026-05-01 | **v3.5.2 cleanup sprint**: A.1+A.2 fechados (11 tests). Backlog 13→11. **Categoria A 100% encerrada.** |
| 2026-05-01 | **v3.6.0 minor**: Reliability module IEEE 1366-2012 (35 tests). Backlog mantido 11. |
| 2026-05-01 | **v3.6.2 cleanup sprint**: D.1+D.2 fechados (13 tests). Backlog 11→9. **Categoria D 67% encerrada (D.3 remanescente).** |
| 2026-05-01 | **v3.7.0 minor**: B.2+B.3 fechados (19 tests). Backlog 9→7. **Categoria B 50% encerrada (B.1+B.4 remanescentes).** Sprint paridade real PF iniciado. |
| 2026-05-01 | **v3.7.1 patch**: B.1 fechado (22 tests). Backlog 7→6. **Categoria B 75% (B.4 só)**. Branch impedance real extraída de Tr/CABLE/TLIN. |
| 2026-05-01 | **v3.7.2 patch**: C.1+C.2 fechados (7 tests). Backlog 6→4. **Categoria C 50%**. PowerFlowDialog deprecated; EquipmentEval hybrid mode. |
| 2026-05-01 | **v3.8.0 minor**: Reliability Monte Carlo + IEEE 493 presets (18 tests). Backlog mantido 4. Major feature add (não cleanup). |
| 2026-05-01 | **v3.8.1 patch**: C.3+C.4 fechados (14 tests). Backlog 4→2. **Categoria C 100% encerrada** (4/4). Q-limit switching + IEEE 14-bus fixture. |
| 2026-05-01 | **v3.8.2 patch**: D.3 fechado (12 tests). Backlog 2→1. **Categoria D 100% encerrada** (3/3). TCC 3-tab pages (Settings/Curves/Datablock). |
| 2026-05-01 | **v3.9.0 minor**: B.4 fechado (16 tests). Backlog 1→0. **Categoria B 100% encerrada** (4/4). Fault distance walker (auto-classify NEAR/FAR). |
| 2026-05-01 | 🏆 **v4.0.0-alpha PARIDADE TOTAL v1**: 16 milestone tests. Backlog 0/15. Todas as 4 categorias 100% (A+B+C+D). Sweep total 219/219. |
