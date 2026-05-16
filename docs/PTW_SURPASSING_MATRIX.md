# PTW Surpassing Matrix — 124 features × dimensões de superação

**Data**: 2026-04-30
**Diretriz governante**: `docs/PTW_TOTAL_PARITY_DIRECTIVE.md`
**Audit base**: `docs/PTW_TUTORIAL_AUDIT_v3.0.3.md`
**Status**: ⏳ Vivo — preenchido incrementalmente a cada sprint

---

## Convenções

**Dimensões de superação** (ver `PTW_TOTAL_PARITY_DIRECTIVE.md §1.2`):

| # | Dimensão |
|---|----------|
| **1** | Profundidade técnica (mais normas / fórmulas mais recentes) |
| **2** | Abertura (API Pythonica + open-source) |
| **3** | Anti-alucinação (citações inline + golden tests) |
| **4** | Composição (combinável com outras features) |
| **5** | Internacionalização (PT/EN/ES) |
| **6** | Modernidade técnica (Docker, CRDT, IEC 61850, plugins) |
| **7** | UX (atalhos, undo, busca) |
| **8** | Custo (OSS + dual license) |

**Status**: ✅ entregue · 🚧 em sprint · ⏳ planejado · ⚪ pendente

**Tier**:
- **T1** = paridade fundacional (bloqueia uso comercial)
- **T2** = paridade industrial (esperado em ferramenta profissional)
- **T3** = paridade completa (cobre todo o tutorial)

---

## Important Concepts (§p.5–18) — 8 features

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 1 | Project file structure (.prj + auto-folder) (§p.5) | T1 | v3.1.0 | ⏳ | 2,5,6,8 | YAML schema versionado + i18n + Docker volume + OSS |
| 2 | Single component DB ↔ N one-lines (§p.5–6) | T1 | v3.1.0/v3.2.0 | ⏳ | 2,4,6 | Pydantic model único + multi-view + CRDT-friendly |
| 3 | Connecting Components rules (impedance, tie-breakers Pi) (§p.6–8) | T1 | v3.1.0 | ⏳ | 3,7 | Validation engine inline + diagnostics UI |
| 4 | Navigation (One-line, TCC, Reports, Component Editor, Libraries) (§p.8–9) | T1 | v3.1.0 | ⏳ | 7 | Atalhos PT-aware (F-keys + Ctrl combos descobríveis) |
| 5 | Datablocks (input/output, link DB) (§p.10–11) | T1 | v3.2.0 | ⏳ | 2,4 | Format engine plugável via Marketplace |
| 6 | Textblocks/Link Tags/Output Forms (§p.12–13) | T2 | v3.2.0 | ⏳ | 2,4 | Markdown + LaTeX + plugin extensions |
| 7 | Reports (4 tipos: RPT/RP2/Datablock/Crystal) (§p.13–15) | T1 | v3.4.0 | ⏳ | 2,5,6 | ReportLab/WeasyPrint + i18n + PDF/HTML/MD multi-format |
| 8 | Multiple Scenarios (§p.16–17) | T1 | v3.5.0 | ⏳ | 4,6 | Composto com CRDT (snapshot por branch) |

## Part 1 — Build System Model (§p.19–62) — 14 features

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 9 | Project>Options>Application (standard ANSI/IEC + units) (§p.20) | T1 | v3.1.0 | ⏳ | 1,4,5 | Toggle switch dual ANSI+IEC simultaneous + units PT/EN/ES |
| 10 | Project>New (auto-folder) (§p.20–21) | T1 | v3.1.0 | ⏳ | 2,8 | YAML versionado + git-friendly + OSS |
| 11 | One-line + Push-pin + zoom/grid (§p.21–24) | T1 | v3.1.0 | ⏳ | 2,7 | PySide6 QGraphicsView OSS + UNDO ilimitado dia-0 |
| 12 | Add bus + Util + TX + Cable + Load (§p.24–28) | T1 | v3.1.0 | ⏳ | 3 | Validation Pydantic com hint inline |
| 13 | Symbol Rotation 90° (§p.28–29) | T1 | v3.1.0 | ⏳ | 7 | Rotation sem perder pin orientation/connectivity |
| 14 | Save One-line .drw (§p.29) | T1 | v3.1.0 | ⏳ | 2,8 | Auto-save + git diff legível (YAML não binário) |
| 15 | Multiple one-lines + Copy/Paste (§p.30–34) | T1 | v3.1.0 | ⏳ | 4,6 | CRDT-aware copy/paste preserva sync state |
| 16 | Link Tags dinâmicos (§p.35–42) | T1 | v3.2.0 | ⏳ | 2,4 | URI-style links + plugin handlers |
| 17 | Legend Tags (Diamond, Hexagon) (§p.43–52) | T2 | v3.2.0 | ⏳ | 2,7 | SVG editável + custom shapes via plugin |
| 18 | Component Editor — Voltage entry, Bus Load Diversity (§p.52–54) | T1 | v3.2.0 | ⏳ | 1,3 | DAPPER 22 NEC categorias (já em v1.5.1) integradas |
| 19 | Cable Library (Copper Magnetic THHN 600V) (§p.54–55) | T1 | v3.2.0 | ⏳ | 1,5 | NEC + IEC + ABNT cabos brasileiros |
| 20 | Transformer Library (Oil/Dry, Calculator pu↔%R/%X) (§p.56–58) | T1 | v3.2.0 | ⏳ | 1,5 | + ABNT NBR 5356 + transformadores BR |
| 21 | Utility — fault contribution (MVA/kVA/Amps/pu) (§p.59) | T1 | v3.2.0 | ⏳ | 4 | Composta com IEC 60909 utility model |
| 22 | Datablock display Input Data + Toggle (§p.60–62) | T1 | v3.2.0 | ⏳ | 2,4 | Format plugável + filtros via plugin |

## Part 2 — Run DAPPER System Studies (§p.63–76) — 7 features

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 23 | Run>Balanced System Studies (DL+LF+CompSC) (§p.63–64) | T1 | v3.3.0 | ⏳ | 1,3,4 | TDD Stevenson 3-bus + IEEE 14-bus inline citation |
| 24 | A_FAULT (sub-set já em v3.0.2 + B.1-B.8 em v3.0.3) (§p.63) | T1 | v3.0.2/v3.0.3 | ✅ | 1,2,3,4 | API embutível + cita §1.x.y inline + composta IEC + golden tests publicados |
| 25 | IEC_FAULT (IEC 60909) (§p.63, p.128) | T1 | v3.3.0 | ⏳ | 1,4 | Voltage Factor c (Tab 1-3) + ANSI side-by-side |
| 26 | Comprehensive SC (§p.63) | T1 | v3.3.0 | ⏳ | 3 | Validation Reference-Comprehensive vs IEEE 141 |
| 27 | Study Messages window c/ Edit Errors (§p.65) | T1 | v3.3.0 | ⏳ | 5,7 | Diagnostics i18n + clickable jump-to-error |
| 28 | Datablock Format Load Flow Power Data (§p.66) | T1 | v3.3.0 | ⏳ | 2,4 | Plugin Marketplace formats |
| 29 | Document>Report — Text/RP2/Crystal/CrystalXI (§p.67–69) | T1 | v3.4.0 | ⏳ | 2,5,6 | ReportLab + PDF/HTML/MD + i18n |
| 30 | Crystal Report Load Flow Report.rpt (§p.71) | T2 | v3.4.0 | ⏳ | 2,8 | OSS template Jinja2 (não-proprietário) |
| 31 | Datablock Report (spreadsheet) (§p.72–75) | T1 | v3.4.0 | ⏳ | 2,4 | XLSX + CSV + plugin custom formatters |

## Part 3 — CAPTOR TCC (§p.77–108) — 11 features (alavanca v3.0.1 audit)

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 32 | Add fuse + relay + LV breaker (§p.77–82) | T1 | v3.4.0 | ⏳ | 4,7 | Drag-drop direto + atalho de criação |
| 33 | Library — Cutler-Hammer fuse (§p.83) | T2 | v3.4.0 | ⏳ | 1,5 | + WEG/Schneider/Siemens BR + i18n catalog |
| 34 | Library — GE Multilin 745 relay (§p.84–85) | T2 | v3.4.0 | ⏳ | 1,5 | + relés BR Pextron/CHESF/Solamont |
| 35 | Library — Square D MX Micrologic LS (§p.86) | T2 | v3.4.0 | ⏳ | 1,4 | + plugin Marketplace para vendor-specific |
| 36 | Library — GE SF Spectra (§p.87–88) | T2 | v3.4.0 | ⏳ | 1,4 | mesma extensibilidade plugin |
| 37 | Go-To>Go To TCC Drawing (§p.89–91) | T1 | v3.4.0 | ⏳ | 7 | Atalho + multi-TCC tabs |
| 38 | TCC editing — drag pickup/curve (§p.92–95) | T1 | v3.4.0 | ⏳ | 1,3,7 | 17 segments + 10 IEC/ANSI curves (v3.0.1 audit) + drag interativo |
| 39 | INST OR / INST override segment (§p.93) | T1 | v3.4.0 | ⏳ | 1 | Mapeado em CAPTOR audit |
| 40 | Run>TCC Report (sort by Bus Voltage) (§p.99–101) | T1 | v3.4.0 | ⏳ | 2,5 | i18n + filterable + plugin export |
| 41 | TCC Settings datablock (§p.103–104) | T1 | v3.4.0 | ⏳ | 2,4 | Format plugável |
| 42 | Crystal Report TCC Static Trip Breakers (§p.105–107) | T2 | v3.4.0 | ⏳ | 2,5 | OSS template + i18n |
| 43 | Form Print — TCC & One-Line 8½×11 (§p.96–98) | T2 | v3.4.0 | ⏳ | 5,6 | + A4/A3 BR + PDF/SVG + Docker print server |

## Part 4 — Equipment Evaluation (§p.109–117) — 7 features

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 44 | Run>Equipment Evaluation (PD + Non-PD) (§p.109–110) | T1 | v3.3.0 | ⏳ | 1,3 | + NBR 14039 + IEC 62271 inline |
| 45 | Branch vs Bus + ANSI/IEC/Compreh selectors (§p.110–111) | T1 | v3.3.0 | ⏳ | 4 | Triplo-selector simultâneo (PTW = um por vez) |
| 46 | Filter por tipo (cable, 2-3W TX, motors, etc.) (§p.111) | T1 | v3.3.0 | ⏳ | 7 | Filtro multi-criteria + saved filters |
| 47 | Report button + Excel export (§p.112) | T1 | v3.3.0 | ⏳ | 2,5,6 | XLSX/CSV/PDF/MD + i18n + plugin |
| 48 | Datablock Device Evaluation Branch (§p.113) | T1 | v3.3.0 | ⏳ | 2,4 | Format plugável |
| 49 | Mark Components Failing (red) (§p.114) | T1 | v3.3.0 | ⏳ | 7 | + tooltip inline com causa + jump-to-fix |
| 50 | Project>Options>Equipment Evaluation user limits (§p.115–117) | T1 | v3.3.0 | ⏳ | 4,5 | YAML editável + i18n labels |

## Part 5 — Arc Flash Evaluation (§p.119–171) — 26 features

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 51 | Run>Arc Flash Evaluation (15 colunas) (§p.119–122) | T1 | v1.6.0 | ✅ | 1,5 | 8 standards side-by-side + PT/EN/ES |
| 52 | NFPA 70E 2015 Annex D.3 (§p.122) | T1 | v1.6.0 | ✅ | 1 | Cobre + version 2018/2021 |
| 53 | DC Annex D.5 (§p.124) | T1 | v1.6.0 | ✅ | 1 | DC NFPA 70E nativo |
| 54 | NESC 2012/2023 (§p.124–125) | T1 | v1.6.0 | ✅ | 1 | NESC 2023 (mais novo) |
| 55 | Detail vs Summary view (§p.125–126) | T1 | v1.6.0 | ✅(parcial) | 7 | + side-by-side comparison |
| 56 | Best/Worst Case Arc Flash scenarios (§p.126–127) | T1 | v3.5.0 | ⏳ | 4 | Composto com Scenario Manager |
| 57 | Custom Label + Work Permit (§p.127, p.148–149) | T1 | v3.4.0 | ⏳ | 2,5,6 | Designer drag-drop + i18n PT/EN/ES + PDF/SVG export |
| 58 | Standard & Unit options (§p.128–129) | T1 | v1.6.0 | ✅ | 1,5 | 8 standards + units PT/EN |
| 59 | Maximum Arcing Time Duration (default 2s) (§p.129–130) | T1 | v1.6.0/v3.0.3 | ✅(parcial) | 4 | Per-bus override + global default |
| 60 | Arcing Fault Tolerances (−15%/+10%, 38%, IEC) (§p.130–131) | T1 | v1.6.0/v3.0.3 | ✅(parcial) | 1,3 | Citação inline + dual-tolerance |
| 61 | Pre-Fault Voltage options (LF/PU All/PU per Bus + Tolerance) (§p.131–135) | T1 | v3.0.3 | ✅ | 1,3,4 | 4 modos PreFaultMode enum + 3 tolerâncias (Util/Cable/TX) + worst-case combinator + cita §Part 5 p.131-135 inline |
| 64a | Reduce Gen/Sync Motor Fault Contribution (§p.136-137) | T1 | v3.0.3 | ✅ | 1,3 | gen_sync_decay_step exponencial subtransient→steady com τ |
| 64b | Recalculate Trip Time (§p.137) | T1 | v3.0.3 | ✅ | 1,3 | recalculate_trip_time(curve, i_per_pickup) com curve callable |
| 65a | Induction Motor Cycles + hp exclude (§p.138) | T1 | v3.0.3 | ✅ | 1,3 | induction_motor_excluded com hp_threshold=50, 30-cycle steady-state |
| 72 | Check Upstream Mis-coordination + Levels Search (§p.144-145) | T1 | v3.0.3 | ✅ | 1,3,4 | upstream_search + mis_coordination_ratio + cleared_fault_threshold com defaults canônicos |
| 73 | Cleared Fault Threshold (§p.144-145) | T1 | v3.0.3 | ✅ | 3 | DEFAULT_CLEARED_FAULT_THRESHOLD=0.80 + is_main_cleared() |
| 125a | Single-phase Mid-Tap TX (§Part 9 p.247-250) | T1 | v3.0.3 | ✅ | 1,5 | split_phase_secondary_voltages + ABNT NBR 5440 cited + invariante físico V_AN+V_BN=V_LL |
| 126a | Per-Phase Load Phase A only (§Part 9 p.250) | T1 | v3.0.3 | ✅ | 1,3 | PerPhaseLoad dataclass + is_balanced + unbalance_factor + phase_only() helper |
| 24a | NACD-Ratio + 3 modes (ALL_REMOTE/PREDOMINANT/INTERPOLATED) (A_Fault §1.3.3, §1.3.7) | T1 | v3.0.3 | ✅ | 1,3,4 | NacdMode enum + GeneratorContribution + nacd_ratio validado contra 7 cases publicados (0.0/0.5410/0.5424/0.5456/0.5997/0.6778/1.0000) |
| 24b | Interrupting MF tables (Figs 1-1..1-15) (A_Fault §1.3.7, §1.3.8) | T1 | v3.0.3 | ✅ | 1,2,3 | mf_local/remote/interpolated + 4 BreakerCycles + 2 FaultTypes + 2 Standards (C37.5/C37.010), analytical Eq 7-1, ±10% vs gráficos interpolados |
| 24c | Asymmetrical Withstand Phase A + Average 3-φ (A_Fault §1.2.3) | T1 | v3.0.3 | ✅ | 1,3 | asym_withstand_phase_a (worst Phase A) + asym_withstand_average_3ph (IEEE 551 §7.6 form), achado: §1.5 não existe — está em §1.2.3 |
| 24d | Transformer Taps modeling (§1.4.2 p. 1-31/33) | T1 | v3.0.4 | ✅ | 1,2,3,5 | TransformerTap dataclass + NEMA 5-step + voltage_with_tap, NBR 5440 BR cited, V=1.0256 reproduzido |
| 24e | Solution Method E/Z vs E/X (§1.3.3 p. 1-9/1-11) | T1 | v3.0.4 | ✅ | 1,3,4 | SolutionMethod enum + x_over_r_from_complex_impedance + composta com separately-derived |
| 24f | C37.5 ↔ C37.010 conversion (§1.3.7 p. 1-19/1-20) | T1 | v3.0.4 | ✅ | 1,3 | convert_total_to_symmetrical + inverse, round-trip idempotente, asym_factor configurável |
| 24g | SLG vs 3-φ ratio (§1.4.2 p. 1-33) | T1 | v3.0.4 | ✅ | 1,3 | slg_vs_3ph_ratio(z0_over_z1) usando Sym Components + Stevenson Ch.12 |
| 24h | Plant §1.4.4 multi-bus reproduction (5 buses) | T1 | v3.0.4 | ✅ | 1,3 | 5 buses publicados validados: NACDs 0.5410/0.5424/0.5456, X/R 3.10/6.07/7.03, currents 8.558/8.786/10.560 kA |
| 24i | AnsiFaultBus unified container (LV+Mom+Int reports) | T1 | v3.0.5 | ✅ | 2,4,7 | Single dataclass para 3 reports + composição com 6 módulos v3.0.2-v3.0.4 |
| 24j | AnsiFaultReport multi-bus + 3 formatters (text/markdown/csv) | T1 | v3.0.5 | ✅ | 2,4,5,7 | Text=paridade PTW, Markdown=superação visual, CSV=Excel/Pandas roundtrip via stdlib |
| 24k | Pipeline end-to-end (TX taps + Pre-fault + decay + mis-coord) | T1 | v3.0.5 | ✅ | 4 | Composição testada de 6 módulos numa pipeline ANSI completa |
| 24l | Worst-case arc-flash scenario (V max + INTERPOLATED) | T1 | v3.0.5 | ✅ | 1,3,4 | Pre-Fault NO_LOAD_WITH_TAP + INTERPOLATED MF + Generator decay validado |
| 24m | 3 NACD modes consistency check (ALL_REMOTE/PREDOMINANT/INTERPOLATED) | T1 | v3.0.5 | ✅ | 1,3 | Validação que para NACD>0.5, PREDOMINANT == ALL_REMOTE (manual §1.4.3) |
| 24n | **AnsiShortCircuitDialog GUI** (acesso usuário) | T1 | v3.1.0 | ✅ | 2,4,7 | Menu Análise + atalho Ctrl+Shift+A; 3 tabs (Inputs/Generators/Reports); 17 testes |
| 24o | **PreFaultVoltageDialog GUI** | T1 | v3.1.0 | ✅ | 2,4,7 | Menu Análise; combined worst-case calculator live; 10 testes |
| 24p | **AnsiUtilitiesDialog GUI** (3-em-1: Mis-coord / Conversion / Tap) | T1 | v3.1.0 | ✅ | 2,4,7 | Menu Ferramentas; 3 tabs com testes interativos; 13 testes |
| 24q | **FaultDecayDialog GUI** (gen/sync/induction) | T1 | v3.1.0 | ✅ | 2,7 | Menu Análise; 10-point decay table; auto-update; 7 testes |
| 24r | **BalancedSystemStudiesDialog** (orchestrator §Part 2 p. 63) | T1 | v3.1.0 | ✅ | 2,4,7 | Menu Análise; 4 checkboxes + log progress; 6 testes |
| 24s | **7ª garantia formalizada** (Acessibilidade GUI obrigatória) | T1 | v3.1.0 | ✅ | 2,7 | PTW_TOTAL_PARITY_DIRECTIVE §8.3 — 0 órfãos backend permitido a partir de v3.1.0 |
| 11 | **Push-pin Mode** (TOOL_PIN, paleta → cross-cursor + cliques sucessivos) | T1 | v3.1.1 | ✅ | 2,7 | PTW Tutorial §Part 1 p.21-24 reproduzido. Esc/V volta SELECT. 13 testes. |
| (n) | **UTIL component type** (utility + MVAsc + X/R + grounding + SLG) | T1 | v3.1.1 | ✅ | 1,5 | UTIL.ocomp + UtilitySymbol; ABNT/ANSI/IEC inline. Modelo TX 3-φ + neutro. |
| (n+1) | **LOAD component type** (kW + kVAR + load_type NEC + per-phase) | T1 | v3.1.1 | ✅ | 1,5 | LOAD.ocomp + LoadSymbol; NEC 220.x diversity factor + per-phase A/B/C enable. |
| (n+2) | **FILTER component type** (single-tuned/double/high-pass/c-type) | T1 | v3.1.1 | ✅ | 1,5 | FILTER.ocomp + FilterSymbol; IEEE 519 + IEEE 1531. |
| 18a | **PpProperty.linked_library** (Library link gray-out model) | T1 | v3.1.1 | ✅ (model) | 2,4 | Tutorial §Part 1 p.55. Backward-compat (default None). UI gray-out visual deferred v3.1.2. |
| 19a | **PpLinkTag** (oneline:/tcc:/report:/pdf: targets) | T1 | v3.1.1 | ✅ (model) | 2,4 | Tutorial §Part 1 p.35-42. URI prefix scheme. UI rendering deferred v3.1.2. |
| 19b | **PpLegendTag** (Diamond/Hexagon/Circle/Rectangle shapes) | T1 | v3.1.1 | ✅ (model) | 2,4 | Tutorial §Part 1 p.43-52. 4 shapes válidos + cor configurable. UI rendering deferred. |
| 18b | **PropertyRow gray-out + Unlink button** (UI Library link visual) | T1 | v3.1.2 | ✅ (UI) | 2,7 | Tutorial §Part 1 p.55. PropertyRow.set_linked_library() + signal unlink_requested. |
| 19c | **LinkTagGraphicsItem** (rounded-rect + closed-arrow + click→signal) | T1 | v3.1.2 | ✅ (UI) | 1,2 | Tutorial §Part 1 p.35-42. Tag desenhado no canvas com QGraphicsObject. |
| 19d | **LegendTagGraphicsItem** (4 shapes pintados via QPainterPath) | T1 | v3.1.2 | ✅ (UI) | 1,2 | Tutorial §Part 1 p.43-52. Diamond/Hexagon/Circle/Rectangle. |
| 11a | **AddSeriesComponentCommand** (auto-bus-node em série) | T1 | v3.1.2 | ✅ (engine) | 1,4 | Tutorial §Part 1 p.27. Atomic redo/undo de wire-split + insert + 2 wires. |
| (Olivas-only) | **Sidecar JSON I/O** (.olivas.json backward-compat) | T1 | v3.1.2 | ✅ | 2,6 | Versionado + tolerant load. Save/load round-trip preservado. |
| 18c | **Context menu Inserir Link/Legend Tag** (right-click área vazia) | T1 | v3.1.3 | ✅ (UX) | 7 | view.py:_build_empty_canvas_menu + 4 shapes submenu + QInputDialog flow |
| 19e | **MainWindow link_tag_navigate** (4 schemes: tcc/report/pdf/oneline) | T1 | v3.1.3 | ✅ (integration) | 4,7 | QDesktopServices para PDF + roteamento tcc/report. oneline deferred v3.2.0+ |
| 11b | **Drop on wire → AddSeriesComponentCommand** (paleta drag para wire) | T1 | v3.1.3 | ✅ (UX) | 7 | view.dropEvent detecta WireItem (tolerance 8px) + emite signal especial |
| (Olivas-only) | **Auto sidecar save/load** (save_to_sch chama save_sidecar; idem load) | T1 | v3.1.3 | ✅ | 2,6 | Skip-write se project sem extensions; tolerant load |
| 9 | **Component Editor multipanel** (N tabs por PropertyGroup) | T1 | v3.2.0 | ✅ | 1,7 | PTW Tutorial §Part 1 p.52-60. Antes: 2 tabs. Agora: 1 tab por grupo + ícones unicode. |
| 9a | **Datablock tab integration** (📊 Datablocks tab quando há datablocks anexados) | T1 | v3.2.0 | ✅ | 4,7 | attach_datablock_tab + editor wiring. Inserido antes de Descrição. |
| 18d | **linked_library wiring fix retroativo** (PpProperty→PropertyRow) | T1 | v3.2.0 | ✅ (audit) | 7 | Fechou gap 7ª garantia descoberto em audit retroativo de v3.1.1. |
| 84a | **UnbalancedPowerFlowDialog** (3-φ + sequências 0/1/2 + open-phase) | T1 | v3.3.0 | ✅ | 7 | PTW Tutorial §Part 9 p.241. **FECHA violação 7ª garantia** detectada no audit pre-sprint. |
| 23a | **kappa_method dropdown wired** (IEC 60909 Methods A/B/C) | T1 | v3.3.0 | ✅ | 1,3 | IEC 60909-0:2016 §4.4.1.2. Pré-v3.3.0 dropdown era inerte; agora produz ip diferentes. |
| 16a | **IEEE 14-bus subset golden test** (NR LF validation) | T1 | v3.3.0 | ✅ | 3 | MATPOWER 7.1 case14.m. 5-bus subset preserva topologia challenge. |
| 30a | **build_equipment_from_project** (auto-extract PpProject → EquipmentInstance) | T1 | v3.3.0 | ✅ | 2,4 | PTW Tutorial §Part 4 p.109. 12 type-mappings + heuristic property parser. |
| 25a | **KT / KG / KSO impedance correction factors** | T1 | v3.3.0 | ✅ | 1,3 | IEC 60909-0:2016 §6.3.3 + §6.6.2 + §6.7. Validados golden numéricos. |
| 16b | **PowerFlow N-bus from PpProject** (build_pf_system_from_project) | T1 | v3.3.1 | ✅ | 4,7 | Tutorial §Part 2. Fecha gap §A.3 audit. Read BUS topology + LOAD components. |
| 30b | **EquipmentEvalDialog auto-load** (set_equipments do projeto) | T1 | v3.3.1 | ✅ | 4,7 | Fecha gap §C.3 audit. Ctrl+E mostra equipamentos do projeto, não demo. |
| 25b | **correction_factor em calculate_short_circuit** (KT × KG × KSO integrado) | T1 | v3.3.1 | ✅ | 1,3,4 | Fecha gap §D.5 audit. Caller pré-computa produto + passa via param. |
| 25c | **decay μ·q em calculate_short_circuit** (NEAR_TO_GENERATOR) | T1 | v3.3.1 | ✅ | 1,3 | Fecha gap §D.5 audit. IEC 60909-0:2016 §4.5. Substitui Ib=Ik=Ik'' hard-coded. |
| 83 | **C-lines on TCC** (constant Incident Energy overlay) | T1 | v3.4.0 | ✅ | 1,4 | PTW Tutorial §Part 5 p.163-165. NFPA 70E Annex H Tab H.3(b). 5 levels (1.2/4/8/25/40 cal/cm²) + color-coded. |
| 40 | **TCC Report export** (text/markdown/csv) | T1 | v3.4.0 | ✅ | 2,7 | PTW Tutorial §Part 3 p.99-101. 3 formatadores. CSV Excel-compatible. |
| (Olivas-only) | **SKIPPED_BACKLOG persistente** (anti-esquecimento) | (process) | v3.4.0 | ✅ | (process) | 11 itens consolidados; cap 15; revisão a cada 2 releases. |
| 113 | **Scenario Manager** (PpScenario + ScenarioManager + clone/diff/promote) | T1 | v3.5.0 | ✅ | 4 | PTW Tutorial §Part 11 p.319-347. PromotionMode (3 modos) + diff_with_base. Compose com CRDT (paradigmas distintos). |
| 113a | **ScenarioManagerDialog GUI** (clone/activate/diff/promote acessível) | T1 | v3.5.0 | ✅ | 7 | Ferramentas > Scenario Manager. PTW peach color highlight active. |
| (Olivas-only) | **8ª garantia Context Preservation** (continuidade entre sessões) | (process) | v3.5.0 | ✅ | (process) | CONTEXT_PRESERVATION_PROTOCOL.md formalizado. 14 critérios aceite. Anti-perda de contexto. |
| 62 | Fixed/Movable Bus Tap, Phase Shift, VFD Load Side (§p.135–136) | T1 | v3.3.0 | ⏳ | 1 | + IEC 61850 tap measurements |
| 63 | Defined Ground SLG/3P Fault % (§p.136) | T1 | v3.0.3 | ⏳ | 3 | Threshold configurável |
| 64 | Reduce Gen/Sync Motor Fault Contribution + Recalc Trip (§p.136–137) | T1 | v3.0.3 | 🚧 | 1,3 | + decay model citado IEEE C37 |
| 65 | Induction Motor Fault Cycles + hp exclude (§p.138) | T1 | v3.0.3 | ⏳ | 1 | + machine multipliers v3.0.2 |
| 66 | Fuses CL/Standard/Specified + ½ ¼ cycle reduction (§p.138–140) | T1 | v3.4.0 | ⏳ | 1 | CAPTOR 17 segments + current-limiting logic |
| 67 | Equipment-Specific IE Equations (§p.140) | T1 | v3.4.0 | ⏳ | 4 | Plugin Marketplace para vendor-specific |
| 68 | Report Options (5 modos Bus/PD/Bus+Line/etc.) (§p.141–143) | T1 | v3.4.0 | ⏳ | 2,5 | + i18n + plugin |
| 69 | Report Last Trip vs Main Device (§p.143) | T1 | v3.4.0 | ⏳ | 4 | Composto com TCC multi-function |
| 70 | EE Failed → Report IE/PPE / As Overdutied (§p.143) | T1 | v3.3.0 | ⏳ | 4 | Composto com EE module |
| 71 | Device Fail to Operate → Use Upstream (§p.143–144) | T1 | v3.4.0 | ⏳ | 1 | + reliability composição |
| 72 | Check Upstream Mis-coordination (§p.144–145) | T1 | v3.0.3 | 🚧 | 1,4 | Mis-coord ratio + levels-to-search + composta TCC |
| 73 | Cleared Fault Threshold (default 80%) (§p.144–145) | T1 | v3.0.3 | 🚧 | 3 | Citação inline §144 + configurável |
| 74 | Maintenance Mode (ARMS-style) (§p.145) | T1 | v3.4.0 | ⏳ | 1,6 | + IEC 61850 GOOSE-driven mode switch |
| 75 | Increase PPE Level by 1 marginal IE (§p.145) | T2 | v3.4.0 | ⏳ | 7 | UI hint + auto-bump configurável |
| 76 | PPE Table NFPA 70E 2015 Annex H Table H.3(b) (§p.146–148) | T1 | v3.4.0 | ⏳ | 1,5 | + NR-10 categorias BR + i18n |
| 77 | ArcFlash menu (Bus Detail, Custom Label, Work Permit, etc.) (§p.148–151) | T1 | v3.4.0 | ⏳ | 5,7 | + atalhos + i18n menu |
| 78 | Additional IE & Flash Boundary working distances (§p.151–153) | T1 | v3.4.0 | ⏳ | 1 | N working distances unbounded |
| 79 | Shock Approach Boundary Table (§p.153–154) | T1 | v3.4.0 | ⏳ | 1 | + NR-10 + IEC 61936 |
| 80 | Glove Class (ASTM D 120-95) (§p.154–155) | T2 | v3.4.0 | ⏳ | 1,5 | + IEC 60903 + ABNT |
| 81 | Report Data and Order — 20 fields (§p.155–158) | T2 | v3.4.0 | ⏳ | 7 | Drag-drop reorder + saved presets |
| 82 | Notes Section *N1–*N23 (§p.158–159) | T2 | v3.4.0 | ⏳ | 5 | i18n notes + clickable definitions |
| 83 | C-lines (Constant IE) on TCC (§p.163–165) | T1 | v3.4.0 | ⏳ | 1,4 | Composto Arc Flash + TCC |
| 84 | Accumulated Energy from Multiple Contributions (staircase) (§p.166–168) | T1 | v1.6.0/v3.4.0 | ✅(parcial) | 1,3 | + plot waterfall visual |
| 85 | Min/Max Faults effect on PPE (§p.169) | T1 | v3.0.3 | ⏳ | 1 | + tolerance bands |
| 86 | 3-Phase vs Arcing Fault relationship (§p.170) | T2 | v1.6.0 | ✅ | 3 | Citação IEEE 1584 inline |
| 87 | Important Assumptions (15 itens) (§p.170–171) | T2 | v3.4.0 | ⏳ | 3,5 | Lista i18n com toggles override |

## Part 6 — Motor Starting / TMS (§p.173–195) — 9 features

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 88 | Convert Bus-Node to Bus + add ind motor 100hp (§p.173–175) | T1 | v3.6.0 | ⏳ | 7 | UNDO + visual feedback |
| 89 | Snap-shot Status Running→Starting + Const kVA→Const Z (§p.176–181) | T1 | v3.6.0 | ⏳ | 4 | Composto LF + TMS |
| 90 | Run>Transient Motor Starting (§p.181–183) | T1 | v3.6.0 | ⏳ | 1,3 | scipy.solve_ivp + golden NEMA MG-1 |
| 91 | TMS Data Channel View (§p.184) | T1 | v3.6.0 | ⏳ | 7 | Multi-channel sync + zoom/pan |
| 92 | TMS-Motors window (model + load + WK² + controller) (§p.184–185) | T1 | v3.6.0 | ⏳ | 1 | + IEC 60034 motor classes |
| 93 | Library — Typical Graphical Motor + 100HP Fan Exponential (§p.185–187) | T2 | v3.6.0 | ⏳ | 1,5 | + WEG/Siemens BR motors |
| 94 | Dynamic Events tab (Off Line, Start Motor, Trip) (§p.187) | T1 | v3.6.0 | ⏳ | 6 | + IEC 61850 GOOSE-driven events |
| 95 | Run TMS + Plot Motor Speed/Bus V (§p.188–189) | T1 | v3.6.0 | ⏳ | 7 | + matplotlib QtAgg interactive |
| 96 | Auto Transformer starter (tap 0.85, time 15s) (§p.190–191) | T1 | v3.6.0 | ⏳ | 1 | + soft-starter + VFD models |
| 97 | Plot Properties Graph Color Monochrome+Symbol (§p.192) | T2 | v3.6.0 | ⏳ | 7,5 | Theme switcher + i18n labels |

## Part 7 — Harmonic Analysis HIWAVE (§p.197–213) — 9 features

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 98 | Motor Harmonic Source Subview + Typical 6 Pulse IGBT (§p.197–198) | T1 | v3.7.0/v4.0.0 | ⏳ | 1 | + IEC 61000-3-6 spectra |
| 99 | Run>Harmonic Analysis (HIWAVE) (§p.199) | T1 | v3.7.0/v4.0.0 | ⏳ | 1,3 | + Prony + Welch validation |
| 100 | HIWAVE Study-Case-Plot (§p.200–202) | T1 | v3.7.0/v4.0.0 | ⏳ | 7 | Multi-case overlay |
| 101 | Distortion plots (CBL/XF Δ-Y phase shift) (§p.202) | T1 | v3.7.0/v4.0.0 | ⏳ | 1 | Phase domain dedicated |
| 102 | Capacitor 100 kVAR add (§p.203–205) | T1 | v3.7.0/v4.0.0 | ⏳ | 1 | + IEEE 1531 design helper |
| 103 | Filter Design (Capacitor Bank kVAR↔μF) (§p.205) | T1 | v3.7.0/v4.0.0 | ⏳ | 1,7 | Wizard + i18n |
| 104 | Case2 vs Case1 — 13th harmonic resonance (§p.206) | T1 | v3.7.0/v4.0.0 | ⏳ | 4 | Composto Scenarios |
| 105 | Single Tuned Filter (Order 4.8) (§p.207) | T1 | v3.7.0/v4.0.0 | ⏳ | 1 | + double-tuned + high-pass IEEE 519 |
| 106 | Frequency Scan Plot Z(f) (§p.208) | T1 | v3.7.0/v4.0.0 | ⏳ | 1,7 | Interactive zoom + resonance markers |
| 107 | Harmonics Datablock + HIWAVE.rpt (§p.210–212) | T1 | v3.7.0/v4.0.0 | ⏳ | 2,5 | XLSX/PDF/MD + i18n |

## Part 8 — Transient Stability ISIM (§p.216–237) — 11 features

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 108 | Add Generator (1000 kVA, PQ, 40kW/30kVAR) (§p.216–218) | T1 | v4.0.0 | ⏳ | 1 | + IEC 60034 + IEEE 1110 |
| 109 | Run>Industrial Simulation (ISIM) (§p.219–222) | T1 | v4.0.0 | ⏳ | 1,3 | scipy stiff + golden Anderson-Fouad |
| 110 | Generator models (Round Rotor / Salient / Gas Turbine) (§p.222–224) | T1 | v4.0.0 | ⏳ | 1 | + IEEE Std 1110 6 models |
| 111 | Exciter (1979 IEEE Type 1 etc.) (§p.223) | T1 | v4.0.0 | ⏳ | 1 | + IEEE 421.5-2016 (mais novo) |
| 112 | Governor (General Use, IEEE) (§p.224) | T1 | v4.0.0 | ⏳ | 1 | + IEEE PES task force models |
| 113 | Utility Infinite Bus / Infinite Machine (§p.224–225) | T1 | v4.0.0 | ⏳ | 4 | Composto LF |
| 114 | Custom Motor Model — Double Cage Flux + Estimator (§p.226–230) | T2 | v4.0.0 | ⏳ | 1 | + IEEE 112 + IEC 60034-2-1 |
| 115 | Bus Apply/Clear Fault events (8 cycles @60Hz) (§p.231) | T1 | v4.0.0 | ⏳ | 6 | + IEC 61850 GOOSE-driven |
| 116 | Trip Generator event (§p.232) | T1 | v4.0.0 | ⏳ | 6 | + IEC 61850 GOOSE |
| 117 | Motor Off Line + Start @5s (§p.232) | T1 | v4.0.0 | ⏳ | 4 | Composto TMS |
| 118 | Plot channels Gen/Util/Motor/Bus V & f (§p.233–234) | T1 | v4.0.0 | ⏳ | 7 | Multi-axis sync + interactive |
| 119 | Maximum Sim Time 50s (§p.234) | T1 | v4.0.0 | ⏳ | 1 | Adaptive step + timeout per study |
| 120 | Speed Deviation + Bus V plots (§p.235–236) | T1 | v4.0.0 | ⏳ | 7 | + frequency stability metrics |

## Part 9 — Single-Phase / Unbalanced 3-Phase (§p.238–258) — 9 features

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 121 | Run>Unbalanced/Single Phase Studies (§p.239) | T1 | v3.3.0 | ⏳ | 1,3 | + Fortescue inline + golden Stevenson |
| 122 | UB_LF Current Datablock (§p.240–241) | T1 | v3.3.0 | ⏳ | 2 | Format plugável |
| 123 | Open-phase scenario (uncheck Phase A) (§p.241–242) | T1 | v3.3.0 | ⏳ | 4 | Composto Scenarios |
| 124 | UB Sequence Currents Datablock (§p.245–247) | T1 | v3.3.0 | ⏳ | 1 | + zero-seq fault analysis |
| 125 | Single-phase Mid-Tap TX 100kVA 240V (§p.247–250) | T1 | v3.0.3 | 🚧 | 1,5 | + ABNT BR transformers + split-phase rural |
| 126 | LOAD-0002 100A phase A only (§p.250) | T1 | v3.0.3 | ⏳ | 1 | + per-phase balanced/unbalanced toggle |
| 127 | UB_SC-SLG Datablock (§p.254) | T1 | v3.3.0 | ⏳ | 4 | Composto A_FAULT v3.0.2 |
| 128 | Crystal Report LF A,B,C Phases.rpt (§p.256–257) | T2 | v3.4.0 | ⏳ | 2,5 | OSS template + i18n |

## Part 10 — Distribution Reliability (§p.260–290) — 15 features

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 129 | Reliability indices (MTBF/λ/MTTF/MTTR/EENS/ECOST) (§p.260–261) | T1 | v3.7.0 | ⏳ | 1,3 | IEEE 493 inline |
| 130 | IEEE indices (SAIFI/SAIDI/CAIDI/ASAI/ASUI/EENS/AENS) (§p.260, p.273–275) | T1 | v3.7.0 | ⏳ | 1,3 | IEEE 1366-2012 inline + ANEEL DEC/FEC BR |
| 131 | Reliability Data sub-view per component (§p.261–267) | T1 | v3.7.0 | ⏳ | 4 | Composto Component Editor |
| 132 | Customer Reliability Data lib (IEEE/Hale-Arno) (§p.261–267) | T2 | v3.7.0 | ⏳ | 1,5 | + ANEEL/Aneel tabs BR |
| 133 | Cable termination failures (§p.264) | T2 | v3.7.0 | ⏳ | 1 | Detalhamento por end + per-phase |
| 134 | Switching time (disconnect switch) (§p.264) | T1 | v3.7.0 | ⏳ | 1 | + manual/auto isolation logic |
| 135 | Run>Reliability study setup (§p.268–270) | T1 | v3.7.0 | ⏳ | 7 | Wizard + saved presets |
| 136 | Custom Setting Components (per-component override) (§p.270) | T1 | v3.7.0 | ⏳ | 4 | YAML override per project |
| 137 | Utility System Configurations (7 choices) (§p.276–280) | T1 | v3.7.0 | ⏳ | 1,4 | Propst-Doan PCIC 2000-02 inline + Scenarios |
| 138 | Utility System Evaluation (Reliability/Operability/Maint weighted) (§p.277–280) | T1 | v3.7.0 | ⏳ | 1 | Multi-criteria decision (MCDM) |
| 139 | Distribution System Configurations (8 choices) (§p.281–285) | T1 | v3.7.0 | ⏳ | 1 | + ANEEL PRODIST BR layouts |
| 140 | Custom Damage Function library (§p.286) | T2 | v3.7.0 | ⏳ | 1,5 | + custos BR R$/MWh ANEEL |
| 141 | Failure Rate / Repair Time Aging Factor (5th-order poly) (§p.288–290) | T2 | v3.7.0 | ⏳ | 1 | + Weibull + Bayesian update |

## Part 11 — Advanced Topics (§p.292–366) — 28 features

| # | Feature PTW | Tier | Versão | Status | Dim. superação | Como supera |
|---|-------------|------|--------|--------|----------------|-------------|
| 142 | Project>Copy As / Backup / Merge (§p.292) | T1 | v3.5.0 | ⏳ | 2 | git-friendly + auto-merge |
| 143 | Project>Options (App, OneLine, Lib, TCC) (§p.292–294) | T1 | v3.5.0 | ⏳ | 5 | i18n + saved presets |
| 144 | Document>Export — DXF/WMF/EMF/Clipboard (§p.294) | T2 | v3.5.0 | ⏳ | 2 | + SVG + PDF + JSON |
| 145 | Form Print + Form Layout (§p.295–297) | T2 | v3.5.0 | ⏳ | 5,7 | + A4 BR + drag-drop layout |
| 146 | Symbol Generator program (§p.298) | T2 | v3.5.0 | ⏳ | 2,4 | SVG + plugin Marketplace |
| 147 | Custom Datablock Formats (template syntax) (§p.298–303) | T1 | v3.2.0 | ⏳ | 2,4 | Plugin formats + Jinja2 |
| 148 | Custom Queries (All 2W TX etc.) (§p.303–306) | T1 | v3.5.0 | ⏳ | 2,4 | SQL-like + plugin |
| 149 | User Defined DB Fields (text/number/date/time/currency) (§p.306) | T1 | v3.2.0 | ⏳ | 2,4 | Pydantic schema extensible |
| 150 | Component Clone (multi-copy + new names) (§p.307–309) | T2 | v3.5.0 | ⏳ | 7 | UNDO + bulk rename |
| 151 | Copy Data / Paste Data (§p.311) | T2 | v3.5.0 | ⏳ | 7 | + selective field copy |
| 152 | Default Project Data (§p.312) | T2 | v3.5.0 | ⏳ | 4 | + per-locale defaults |
| 153 | Template Files (One-line Templates, toolbar 0–9) (§p.313–317) | T1 | v3.5.0 | ⏳ | 4,7 | + Marketplace templates |
| 154 | Scenario Manager full (Clone, Activate&Exit, Diff, Promote) (§p.319–344) | T1 | v3.5.0 | ⏳ | 4,6 | + CRDT-aware merge + Git-style branches |
| 155 | Data Visualizer (Components/Scenarios/Datablock/Query) (§p.326–345) | T1 | v3.5.0 | ⏳ | 2,4,7 | + filter/sort/group + plugin views |
| 156 | Global Change Data Visualizer (replace/scale) (§p.340–342) | T1 | v3.5.0 | ⏳ | 7 | + UNDO bulk + dry-run preview |
| 157 | Database Utilities (recover + re-index) (§p.348) | T2 | v3.5.0 | ⏳ | 2 | OSS + automated + idempotent |
| 158 | UNDO unlimited steps (§p.349) | T1 | v3.1.0 | ⏳ | 7 | Command pattern dia-0 + cross-document UNDO |
| 159 | Find Component in any one-line/TCC (§p.350–351) | T1 | v3.5.0 | ⏳ | 5,7 | + fuzzy search + i18n |
| 160 | Data State (Incomplete/Estimated/Complete/Verified) + Color (§p.352–353) | T1 | v3.5.0 | ⏳ | 4,7 | Workflow flags + filterable |
| 161 | Auto-generate one-line for TCC (§p.354–356) | T2 | v3.5.0 | ⏳ | 7 | Smart layout heuristic |
| 162 | Plot Multi-Protection (Phase + Ground) same TCC (§p.357–360) | T1 | v3.4.0 | ⏳ | 1,4 | N functions sim (PTW = 2) |
| 163 | Registry Entries / REGDEL (§p.361) | T3 | v3.7.0 | ⏳ | 6,8 | YAML/.env (não Windows registry) → cross-platform |
| 164 | On-line Help context-sensitive (§p.362) | T1 | v3.5.0 | ⏳ | 5 | i18n PT/EN/ES + clickable manual links |
| 165 | Reference Manuals on CD (§p.363) | T2 | v3.4.0+ | ⏳ | 6,8 | Online docs + i18n + searchable |
| 166 | Managing Libraries — copy/paste, ~ prefix sort (§p.364–365) | T1 | v3.5.0 | ⏳ | 2,4 | + Marketplace + version pinning |
| 167 | Project Backup (project + libs only used) (§p.365) | T1 | v3.5.0 | ⏳ | 2 | git-zip + diff-friendly |

## Olivas-only superações (não no Tutorial PTW)

Features que **não constam** no PTW Tutorial mas Olivas já oferece —
mantém-se como vantagem competitiva permanente:

| # | Feature Olivas | Versão | Dim. superação total |
|---|---------------|--------|---------------------|
| 168 | NBR 17227 (norma BR arc-flash) | v1.6.0 | 1, 5 — única no mundo 🏆 |
| 169 | EPRI 2011 arc-flash | v1.6.0 | 1, 4 |
| 170 | Doughty-Neal-Floyd 2000 | v1.6.0 | 1 |
| 171 | Terzija arc-flash | v1.6.0 | 1 |
| 172 | CSA Z462 arc-flash | v1.6.0 | 1 |
| 173 | DC NFPA 70E §D.5 dedicado | v1.6.0 | 1 |
| 174 | 8-standard arc-flash side-by-side | v1.6.0 | 4 |
| 175 | CT Saturation 3-níveis (ANSI/IEC/dynamic) | v1.4.4 | 1, 3, 4 |
| 176 | IEC 61850 MMS live | v2.0.0 | 1, 6 |
| 177 | IEC 61850 GOOSE | v2.2.0 | 1, 6 |
| 178 | IEC 61850 SV (Sampled Values) | v2.2.0 | 1, 6 |
| 179 | IEC 61850 ASN.1 BER wire format | v2.2.1 | 1, 6 |
| 180 | CRDT Lamport Clock | v3.0.0 | 4, 6 |
| 181 | CRDT LWW Register | v3.0.0 | 4, 6 |
| 182 | CRDT OR-Set | v3.0.0 | 4, 6 |
| 183 | Plugin Marketplace YAML manifest + SHA256 | v1.5.0 | 2, 6 |
| 184 | DAPPER 22 NEC categories + sectors BR | v1.5.1 | 1, 5 |
| 185 | Docker reproducibility | v2.0.0 | 6, 8 |
| 186 | i18n PT/EN/ES (132 strings × 3) | v2.0.0/v2.1.0 | 5 |
| 187 | Locale Picker dialog | v2.1.1 | 5, 7 |
| 188 | Live/Dead bus algorithm BFS | v1.7.0 | 1 |
| 189 | Active state tracking 56 specs | v1.7.1 | 4 |
| 190 | Plot dock auto-refresh | v2.0.4 | 7 |

---

## Tabela resumo

| Categoria | Total | ✅ entregue | 🚧 em sprint | ⏳ planejado | ⚪ pendente |
|-----------|-------|-------------|--------------|--------------|-------------|
| Important Concepts (8) | 8 | 0 | 0 | 8 | 0 |
| Part 1 Build (14) | 14 | 0 | 0 | 14 | 0 |
| Part 2 DAPPER (9) | 9 | 0 (parcial v3.0.2) | 0 | 9 | 0 |
| Part 3 CAPTOR (12) | 12 | 0 (audit v3.0.1) | 0 | 12 | 0 |
| Part 4 EE (7) | 7 | 0 | 0 | 7 | 0 |
| Part 5 Arc Flash (37) | 37 | 11 | 6 | 20 | 0 |
| Part 6 TMS (10) | 10 | 0 | 0 | 10 | 0 |
| Part 7 HIWAVE (10) | 10 | 0 | 0 | 10 | 0 |
| Part 8 ISIM (13) | 13 | 0 | 0 | 13 | 0 |
| Part 9 UB/SP (8) | 8 | 0 | 1 | 7 | 0 |
| Part 10 Reliability (13) | 13 | 0 | 0 | 13 | 0 |
| Part 11 Advanced (26) | 26 | 0 | 0 | 26 | 0 |
| **PTW Tutorial total** | **167** | **42 (25.1%)** ⬆ +4 v3.1.1 | **0** | **125 (74.9%)** | **0** |
| **+ Olivas-only superações (23)** | 190 | 66 (34.7%) entregue ⬆ | 0 | 125 | 0 |

**Observação metodológica**: o número 167 reflete enumeração granular
desta matriz (algumas features do tutorial original foram subdivididas
em sub-itens executáveis). A auditoria base usa 124 como número
canônico de "linhas no tutorial"; a expansão para 167 aqui é por
clareza operacional.

## Compromisso

**Esta matriz é o contrato vinculante** entre release e diretriz.
Toda release deve atualizar esta matriz movendo features de ⏳ para
🚧 ou ✅, declarando explicitamente as dimensões de superação na
coluna correspondente.

A última linha de cada release no handoff doc deve ler:
> *"Matriz `PTW_SURPASSING_MATRIX.md` atualizada: +N features ✅, +M
> features 🚧 para próximo sprint."*
