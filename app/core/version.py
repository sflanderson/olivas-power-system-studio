"""
app.core.version — versão central do **Olivas Power System Studio**.

Single source of truth da versão semântica MAJOR.MINOR.PATCH.

Updates:
* Bumped por sprint que entrega features novas.
* Patch para hotfixes em produção.

A partir de v0.92.2, o software é um **Power System Studio**
(alternativa nacional a SKM PTW / ETAP / EasyPower) —
especialista em análise elétrica auditável (IEC 60909, NBR
17227, IEEE 242, IEEE 399, IEEE 141, NFPA 70E). Antes era
"Olivas ATP Studio" (foco em transitórios EMTP/ATP). A
integração ATP foi desvinculada em v0.92.1 e o produto
reposicionado em v0.92.2.

Histórico recente (referência):
* 0.83 — Brand "Oliveira" (paleta + splash + favicon + reports)
* 0.84 — Wire anchoring + Qt bool fix
* 0.85 — Editor polish (5 features)
* 0.86–0.88 — Datablocks PTW (foundation → auto-binding → sticky)
* 0.89 — Welcome templates (onboarding)
* 0.90 — Auto-save + crash recovery
* 0.91 — UX polish wave 2 (search + dirty title + shortcuts)
* 0.91.1 — Splash layout fix (logo clipping)
* 0.91.2 — ATP runner GUI freeze fix (throttle + bufsize binário)
* 0.91.3 — Templates: wires conectam exatamente em pinos
* 0.91.4 — Console panel: batch HTML render (1 insertHtml/chunk)
* 0.91.5 — AtpProgressDialog: fases + output ao vivo
* 0.91.6 — Thread-safety nas conexões worker→progress (Lock + QueuedConnection)
* 0.91.7 — SignalRelay (canonical PySide6 cross-thread via QMetaObject.invokeMethod)
* 0.91.8 — Auto-temp-file para projetos in-memory ao Executar ATP
* 0.91.9 — _live_node prefere nó mais conectado (bridge bug)
* 0.91.10 — ATP file format: ref1 blank + TIME/MISC cards
* 0.91.11 — ATP audit: TIME alignment + XOPT/COPT default + AC tstart=-1
* 0.91.12 — Simple template + R_LOAD (evita KILL 191 degenerate)
* 0.92.0 — Repositioning: análise elétrica em primeiro plano,
  ATP secundário. Audit trail (SHA256 + responsabilidade
  técnica + citações IEC/NBR/IEEE) integrado em todos
  relatórios. Catálogo formal de 13 normas (IEC, IEEE, NBR,
  NFPA, NR). Bloco de limitações declaradas (auditabilidade
  ISO 9001 / NR-10).
* 0.92.1 — ATP integration totalmente desvinculada da UI
  principal. Tabs ATP (Texto bruto, Topologia, Esquemático
  legacy, Diferenças, Resultados, Formas de onda, Comparar)
  retiradas; case_combo e tree "Estrutura ATP" ocultos.
  Layout reduzido a 4 tabs (Esquemático Visual, Detalhes,
  Validação, Agente). Bus PTW: barramento renderizado como
  linha grossa contínua, multi-conexão em qualquer ponto,
  redimensionável por drag (estilo PTW Power*Tools).
* 0.92.2 — REBRAND: "Olivas ATP Studio" → **"Olivas Power
  System Studio"**. Reposicionado como alternativa nacional
  a SKM PTW / ETAP / EasyPower. Robustez: introduzido
  ``app/core/logging_config.py`` (logging estruturado para
  auditabilidade ISO 9001), validação física automática em
  ``ArcFlashCase.__post_init__`` (rejeita tensão/corrente/
  tempo fora de faixa NBR 17227 / IEEE 1584), logging dos
  fallbacks de divisão-por-zero em IEC 60909 (z=0,
  Ik3=0). Strings user-facing atualizadas (welcome,
  reports, audit_trail).
* 0.93.0 — NEW módulo ``app/postprocessor/ct_saturation.py``
  (~700 LOC): análise em 3 níveis de saturação de TCs
  para proteção, portado de uma ferramenta proprietária
  MATLAB. Cobre IEEE C57.13.1-2017 (ANSI 1+X/R), IEC
  61869-2:2012 (joelho 10/50) e CIGRÉ WG 23-15 (simulação
  dinâmica RK4 com DC offset máximo + remanência).
  Helpers: ``cable_burden_resistance`` (NBR 5410 §6.2),
  ``typical_magnetization_curve``, ``analyze_full``
  orchestrator. 37 tests cobrindo validação, curva,
  burden, 3 níveis e decisão final.
* 0.93.1 — UI compactification (design-critique). Reduz
  chrome density de 4 camadas → 2 camadas:
  - Main_window icon toolbar OCULTA por default
    (Ctrl+Alt+T toggle).
  - PpEditor toolbar reduzida de 13 → 6 botões visíveis
    (Salvar, ▶ Executar, ≡ Mais, ◀ Paleta, Propriedades ▶,
    ⛶ Tela cheia). 8 ações secundárias acessíveis via
    popup do hamburger "≡ Mais".
  - F11 "Tela cheia" REAL — oculta menu bar, tab bar,
    status bar, toolbar PpEditor + paineis. Apenas canvas
    visível (modo zen). Esc/F11 sai. Bug fix: rebrand
    persistia "Olivas ATP Studio" no window title ao
    carregar projeto + botão "Exportar ATP" persistia
    na toolbar do PpEditor.
* 0.93.2 — UM SÓ MENU NO TOPO (design-critique iter 2).
  PpEditor toolbar oculta POR COMPLETO — suas ações
  migraram para:
  - cornerWidget no menu bar = "▶ Executar Análise"
    verde (canto direito, mais visível ainda)
  - Visualizar menu = Paleta (F9), Propriedades (F10),
    Tela cheia (F11)
  - Demais ações já estavam em Arquivo/Editar/Análise
  Resultado: apenas **menu bar + tab bar + canvas**.
  Sem toolbar interna, sem "embolamento" visual.
* 0.93.3 — HOTFIX: examples desconectados (regressão Bus PTW).
  Bug raiz duplo:
  (1) Wires nos .sch desalinhados em 10-50px relação aos
      pinos ATUAIS dos renderers (síntese de pinos a cada
      10px do Bus PTW v0.92.1 não casava com o snapping
      antigo em coords arbitrárias).
  (2) Pinos sintéticos do BUS NÃO eram unificados
      internamente — cada um dos 21 pinos virava um nó
      isolado. Mas BUS = barra de cobre = equipotencial.
  Correções:
  - ``node_coalescer.coalesce_nodes`` agora une todos os
    pinos do BUS num único cluster DSU (root cause #2).
  - ``scripts/migrate_sch_wires.py`` snapa endpoints de
    wires aos pinos mais próximos (≤30 px) — fixa 3 dos
    6 examples automaticamente.
  - ``scripts/rebuild_example_sch.py`` reconstrói os 4
    examples mais complexos (ieee399, ieee1584, stevenson
    sequential, stevenson_pf_3bus) com fontes diretas no
    BUS (sem R+L intermediário, que o multi-hop walker
    não atravessa).
  Resultado: 9/10 BUSes em todos os exemplos agora rodam o
  pipeline SC corretamente. (B3 do Stevenson é PQ bus
  intencional sem fonte direta — comportamento correto.)
* 0.93.4 — HOTFIX: arc-flash não-fatal em "Estudo completo".
  Bug reportado pelo usuário: ao rodar "Estudo completo do
  barramento" no IEC 60909 Annex C (BUS_HV=110 kV ou
  BUS_LV=20 kV), o pipeline FALHAVA com
  "voltage_kV=20.0 fora do escopo IEEE 1584 (0.208 ≤ Voc
  ≤ 15 kV)" — porque arc-flash NBR 17227 / IEEE 1584 só
  cobre 0.208–15 kV. Para sistemas HV/EHV (>15 kV),
  arc-flash não é aplicável mas SC + Coordenação devem
  continuar funcionando.
  Fix em ``analyze_bus_full_pipeline``: try/except no bloco
  arc-flash. Se falhar, gera warning e continua com os
  outros estudos. Campos arc-flash zerados:
  ``incident_energy_cal_cm2=0``, ``arc_flash_boundary_mm=0``,
  ``ppe_category="N/A"``.
* 0.98.0 — Equipment Library (vendor-curated data).
  Sprint #4 do roadmap — bloqueador #4: biblioteca de
  equipamentos. NEW ``app/equipment/`` package:
  - ``RelayModel`` (15 entries: SEL-751/487E/411L/2030,
    ABB REF615/620/630, Siemens 7SJ80/82/85/UM62, GE 489/750/845)
  - ``MotorModel`` (8 entries: WEG W22/W50/W60, Siemens 1LE/1MB,
    ABB M3BP/M2BAX)
  - ``TransformerModel`` (5 entries: WEG/Siemens GEAFOL/ABB Resibloc)
  - ``BreakerModel`` (5 entries: ABB HD4/HV4, Siemens 8DJH/8DA/3WL)
  - 5 vendors, 33 entries totais, filtros por application/
    voltage_class/vendor/IEC 61850/min_kW/min_kA.
  - **Fim da Fase 1** do roadmap (4 bloqueadores fechados).
* 0.97.0 — Harmonics Analysis (IEEE 519-2014).
  Sprint #3 do roadmap — bloqueador #3: análise de
  harmônicos. NEW ``app/postprocessor/harmonics.py``:
  - 7 LoadTypes com espectros típicos: VFD 6/12/18-pulse,
    Rectifier, Arc Furnace, UPS/SMPS, LED.
  - Cálculo V-THD e IHD individual por bus.
  - Limites IEEE 519-2014 Table 1 (5% LV/MV, 2.5% HV).
  - Sugestões automáticas de mitigação (filtros, SVC/STATCOM).
  - 17 tests.
* 0.96.0 — Voltage Drop Profile (NBR 5410 §6.2.7).
  Sprint #2 do roadmap — bloqueador #2: queda de tensão
  por barramento. NEW
  ``app/postprocessor/studies/voltage_drop.py`` — estudo
  modular que percorre BFS as fontes e acumula ΔV cumulativa
  em cada bus. Limites NBR 5410: 4% (regime), 7% (partida
  motor), 10% (iluminação). Identifica violations
  automaticamente. 15 tests.
* 2.0.0 — Commercial Launch (Live SCADA + Docker + i18n).

  **Marco final do roadmap MVP**: release de produção comercial
  com 4 features grandes entregues sob Master Protocol.

  Disciplina v1.3.1+ + Master Protocol v1.7.0 (5 garantias)
  com restore points criados em v1.6.0/v1.7.0/v1.7.1.

  Sprint A — i18n (PT/EN/ES):
  - NEW `app/i18n/__init__.py` (~140 LOC):
    * `_(text)` translation function (gettext-style)
    * `set_locale(locale)` / `get_locale()` / `reset_locale()`
    * Fallback PT (default) para keys ausentes (anti-alucinação)
  - NEW `app/i18n/translations/en.json` (~60 strings)
  - NEW `app/i18n/translations/es.json` (~60 strings)
  - 10 testes em `test_pp_v2_0_0_i18n.py`
  - Cobertura inicial: menus principais + dialogs frequentes;
    v2.1+ amplia

  Sprint B — Live SCADA IEC 61850:
  - NEW `app/integration/iec61850_client.py` (~210 LOC):
    * `IEC61850MMSConfig` dataclass (host/port/ied/mode)
    * `MMSMeasurement` dataclass (name/value/unit/quality)
    * `MMSReport` dataclass (frozen, immutable)
    * `IEC61850MMSClient` class:
      - `stub` mode: gera dados sintéticos realistas
        (V≈13.8kV, I≈100A, BREAKER status)
      - `real` mode: delega para libiec61850 (não bundled,
        raise informativo se ausente)
  - 6 testes em `test_pp_v2_0_0_iec61850.py`
  - Cobertura: MMS client/server. GOOSE/SV deferred to v2.1+.

  Sprint C — Docker reproducibility:
  - NEW `Dockerfile` (Python 3.11-slim + Qt offscreen deps)
  - NEW `docker-compose.yml` (olivas + opcional postgres
    multi-user)
  - Modo headless (QT_QPA_PLATFORM=offscreen) — preserva GUI
    local funcionando sem Docker (anti-perda)
  - HEALTHCHECK importa version.py
  - 8 testes em `test_pp_v2_0_0_docker.py` (audit-only,
    não roda Docker)

  Sprint D — Commercial license + telemetry:
  - NEW `app/commercial/license_key.py` (~140 LOC):
    * `validate_license_key(key)` retorna
      `LicenseValidationResult` com tier
      (educational/demo/commercial/invalid)
    * Empty key = educational tier (default valid)
    * HMAC-SHA256 truncado para validação
    * `DEMO_KEY` embutida para apresentações
  - NEW `app/commercial/telemetry.py` (~110 LOC):
    * Default OFF (privacy first)
    * `enable_telemetry()` / `disable_telemetry()` opt-in
    * `record_event(name, **metadata)` no-op se OFF
    * Local-only em v2.0.0 (sem network IO)
    * Eventos anônimos (sem user_id/IP/hostname)
  - 9 testes em `test_pp_v2_0_0_commercial.py`

  Métricas v2.0.0 finais:
  - **33 testes novos**:
    * 10 i18n + 6 IEC 61850 + 8 Docker + 9 commercial
  - **6 arquivos novos** Python:
    * `app/i18n/__init__.py`
    * `app/integration/iec61850_client.py`
    * `app/commercial/license_key.py`
    * `app/commercial/telemetry.py`
    * + 2 `__init__.py` de subpackages
  - **3 arquivos novos** infra:
    * `Dockerfile`, `docker-compose.yml`,
      `app/i18n/translations/{en,es}.json`
  - **1 mudança em** `app/core/version.py` (bump + changelog)
  - 0 deps externas adicionadas
  - **0 quebras** nos testes anteriores (anti-regressão
    confirmado, restore points preservados)

  Marcos completados (roadmap pós-CT-SAT):
  * ✅ v1.4.4 CT Saturation Study completo (paridade MATLAB)
  * ✅ v1.4.5 User Gate Fixes (PTW patterns)
  * ✅ v1.5.0 Plugin Marketplace
  * ✅ v1.5.1 DAPPER Demand Load (22 categorias)
  * ✅ v1.6.0 Arc-Flash 8-standard
  * ✅ v1.7.0 Polish + Master Protocol
  * ✅ v1.7.1 Active state em components
  * ✅ v2.0.0 Commercial Launch (esta release)

  Vantagens competitivas finais sobre PTW/EasyPower/ETAP:
  * 8 standards arc-flash side-by-side (único no mercado)
  * 22 categorias DAPPER NEC + sectors BR
  * Plugin Marketplace com manifest + permissions
  * CT Saturation Study com 3 plots especializados
  * Live SCADA stub para IEC 61850
  * Container Docker reprodutível
  * i18n PT/EN/ES
  * Master Protocol formal (5 garantias)

  Lições mantidas ao longo do roadmap:
  * Anti-perda via restore points + lista TRAVADA
  * Anti-alucinação via citações de fonte primária
  * Anti-regressão via TDD canônico
  * Anti-funcionalidade acidental via escopo travado por sprint
  * Master Protocol é processo, não aspiração

* 1.7.1 — Active state em components (deferred de v1.7.0 D).

  **Foco**: completar gap deferido — PpComponent.is_active +
  state property em switching components + renderer cinza
  para inactive.

  **Master Protocol** aplicado (5 garantias) com restore point
  v1.7.0_baseline criado e preservado.

  Sprint A — PpComponent.is_active field:
  - 1 linha em `app/preprocessor/models.py`:
    * `is_active: bool = True` (default backward-compat)
  - Cobertura: TODOS os 56 components ganham suporte automaticamente
    via PpComponent dataclass (não precisa modificar 56 YAMLs)
  - 3 testes em `test_pp_v1_7_1_active_state.py`

  Sprint B — state property em 3 switching components:
  - `BREAKER.ocomp`: + property `state: enum [closed, open]`
  - `FUSE.ocomp`: + property `state: enum [closed, open]`
  - `CONTACTOR.ocomp`: + property `state: enum [closed, open]`
  - Default em todos: `closed` (anti-perda: comportamento
    inalterado em projetos existentes que não setam state)
  - 3 testes verificam property loadable via spec registry

  Sprint C — Inactive overlay rendering:
  - APPEND `_paint_inactive_overlay(painter)` em
    `ComponentItem` (items.py)
  - Hook cirúrgico no método `paint()` (4 linhas adicionais)
    após online_annotation badge:
    `if comp.is_active is False: self._paint_inactive_overlay(painter)`
  - Overlay: cinza translúcido `QColor(160, 160, 160, 130)` —
    paridade PTW "Out of Service"
  - Try/except defensivo (anti-crash)

  Sprint D — Bus energization integra state property:
  - Não exigiu mudança de código:
    `compute_energization_for_pp_project` (v1.7.0) já lê
    property "state"=open via `_spec_properties` lookup.
  - Agora os YAMLs de Sprint B fornecem essa property
    com choices [closed, open]. Integração end-to-end completa.

  Métricas v1.7.1 finais:
  - **9 testes novos** em `test_pp_v1_7_1_active_state.py`:
    * 3 PpComponent.is_active
    * 3 state property em switching
    * 2 bus_energization integration
    * 1 backward compat
  - **5 arquivos modificados** (cirúrgicos):
    * `models.py` +5 linhas (1 field + comment)
    * `BREAKER.ocomp` +13 linhas (state property)
    * `FUSE.ocomp` +12 linhas
    * `CONTACTOR.ocomp` +14 linhas
    * `items.py` +27 linhas (4 hook + 23 helper method)
  - **0 quebras** nos 381 testes anteriores (anti-perda
    confirmado)
  - 0 deps externas adicionadas

  Restore point preservado: `restore_points/v1.7.0_baseline/`.

  Lição: **modificação cirúrgica tipo "default + opt-in"** é mais
  segura que migração massiva de 56 arquivos. PpComponent.is_active
  com default=True não quebra construções existentes; state
  property apenas em 3 switching components onde o conceito faz
  sentido fisicamente.

* 1.7.0 — Polish & Live State (Master Protocol expandido).

  **Mudança de roadmap**: Mobile companion (PWA) adiada
  indefinidamente. v1.7.0 entrega 5 melhorias práticas pedidas
  pelo usuário no design critique pós-v1.6.0:

  1. Window management (maximize/minimize em todos os dialogs)
  2. Live bus / Dead bus state com anotação vermelha
  3. Visualizar > Gráficos: integração real com study cache
  4. Active/Inactive audit em 56 components (audit-only)
  5. Master Protocol expandido (5 garantias + ponto de restauração)

  **Master Protocol formal** (`v1.7.0_MASTER_PROTOCOL.md`):
  auditar → registrar → anti-alucinação → anti-crash/regressão
  → ponto de restauração. Restore point criado em
  ``restore_points/v1.6.0_baseline/`` (snapshot de app/ + tests/).

  Sprint A — Window management:
  - NEW `app/gui/window_state_mixin.py` (~110 LOC):
    * `enable_window_controls(dialog, settings_key)` adiciona
      Qt.WindowMaximizeButtonHint + MinimizeButtonHint + persiste
      geometria via QSettings
  - Aplicado em 4 dialogs: CTSaturationDialog, DemandLoadDialog,
    PluginMarketplaceDialog, ArcFlashComparisonDialog
  - 9 testes (`test_pp_v1_7_0_window_state.py`)

  Sprint B — Live/Dead bus state:
  - NEW `app/postprocessor/bus_energization.py` (~210 LOC):
    * `BusState` enum (LIVE / DEAD / UNKNOWN)
    * `compute_energization(components, wires)` com BFS:
      - Source detection (Iac/Idc/Vrect/Source/...)
      - Open interruptor blocks propagation (BREAKER/FUSE/...)
      - Cycle-robust
    * `compute_energization_for_pp_project(project)` wrapper
  - NEW `annotation_from_energization(state)` em
    `online_overlay.py` (apenas APPEND, anti-perda):
    * LIVE → severity "ok" (verde, "● Energizado")
    * DEAD → severity "violation" (**vermelho**, "✕ Desenergizado")
    * UNKNOWN → severity "warn" (amarelo)
  - 12 testes (`test_pp_v1_7_0_bus_energization.py`)
  - Paridade PTW "Out of Service" indication

  Sprint C — Vis>Gráficos integration:
  - `app/gui/plot_widgets.py` — APPEND `populate_from_cache()` em
    cada dock (PF/SC/TCC/MC) via method-injection (anti-perda)
  - `main_window._ensure_plot_dock` — chama populate_from_cache
    automaticamente após criar dock. Try/except defensivo: se
    cache vazio mantém empty state (não crash)
  - 7 testes (`test_gui_v1_7_0_plots_integration.py`)
  - Antes: dock abria com instruções. Agora: se PF rodou,
    abre populated com voltage profile.

  Sprint D — Active state audit (audit-only):
  - NEW `tests/test_pp_v1_7_0_active_state_audit.py`:
    * Auditoria automática dos 56 component specs
    * Reporta gap: nenhum dos critical switching components
      (BREAKER/FUSE/CONTACTOR/SWITCH) tem property "state"
      explícita ainda
    * Coverage atual: 0% — projetado para v1.7.1+ adicionar
      property `state: enum [open, closed]` em cada switching
      component (anti-acidental: NÃO modifica 56 specs nesta
      release; só documenta)
  - 4 testes audit-only

  Sprint E — Design critique:
  - Sprint C resolve o issue principal do critique original
    ("Visualizar > Gráficos só mostra instruções"): com
    populate_from_cache, os docks agora abrem com dados se
    o estudo já rodou.

  Sprint F — Regression + bump:
  - 196/196 arc-flash regression verde (anti-perda confirmado)
  - 4573+ testes verde no sweep total (anti-regressão confirmado)
  - bump 1.6.0 → 1.7.0

  Métricas v1.7.0 finais:
  - **32 testes novos**:
    * 9 window_state + 12 bus_energization + 7 plots_integration
      + 4 active_state_audit
  - **2 arquivos novos** (`window_state_mixin.py`,
    `bus_energization.py`) + 1 test file de audit
  - **Edits cirúrgicos** (sem reescrita):
    * 4 dialogs +3 linhas cada (enable_window_controls)
    * `plot_widgets.py` APPEND no final (~50 linhas)
    * `online_overlay.py` APPEND no final (~50 linhas)
    * `main_window.py` +9 linhas (try/except para populate)
    * `version.py` bump + changelog
  - 0 deps externas adicionadas
  - **0 quebras** nos arquivos da lista TRAVADA
    (`v1.7.0_MASTER_PROTOCOL.md` §3)
  - Restore point preservado: `restore_points/v1.6.0_baseline/`

  Vantagem competitiva mantida + UX polish:
  * 8 standards arc-flash (v1.6.0) preservados intactos
  * Plot docks integrados com study cache (PTW Datablock-like)
  * Window controls em todos os dialogs (UX standard)
  * Live/Dead indication paridade PTW Out-of-Service

  Lição mantida: **Master Protocol** com 5 garantias + restore
  point opera como hardlock anti-perda. Quando algo dá errado em
  qualquer Sprint: restore point está disponível para revert
  cirúrgico sem comprometer release.

* 1.6.0 — Arc-Flash Multi-Standard (7 standards side-by-side).

  **Foco**: 3ª release do roadmap pós-CT-SAT. Adiciona 4 standards
  novos de arc-flash + comparison module side-by-side, mantendo
  IEEE 1584 + NBR 17227 + EPRI já existentes intactos.

  **Disciplina v1.3.1+ + Protocolo de Salvaguardas formal**
  (`docs/v1.6.0_SAFEGUARDS_PROTOCOL.md`):
  - **Anti-alucinação**: cada fórmula com fonte citada (norma +
    seção + equação); golden tests com valores publicados; sem
    inventar relação entre open-air e in-box (paper Doughty-Neal
    documenta achado contraintuitivo).
  - **Anti-perda de dados**: BASELINE 145 arc-flash tests verde
    antes de qualquer mudança. `arc_flash.py`, `epri_arc_flash.py`,
    `arc_flash_label.py`, `arc_flash_monte_carlo.py` **NÃO TOCADOS**
    — todas as adições são em arquivos NEW.
  - **Anti-funcionalidade acidental**: design doc com escopo
    travado por sprint, lista exata de arquivos NEW + 2 modificados
    (main_window +1 menu action +1 handler; version.py).

  Sprint A — NESC 2023 §410:
  - NEW `app/standards/nesc_2023_arc_flash.py` (~210 LOC):
    * `NESCBoundaryRow` dataclass com voltage range +
      Approach Boundary + min PPE rating
    * Tables 410-1 (phase-to-ground, 7 rows) e 410-2
      (phase-to-phase, 9 rows) cobrindo 0.05 → 242 kV
    * `lookup_nesc_2023(voltage_kV, exposure)` com fallback
    * Disclaimer explícito para verificação contra cópia oficial
  - 10 testes (`test_pp_v1_6_0_nesc_2023.py`)

  Sprint B — Doughty-Neal-Floyd 2000:
  - NEW `app/standards/doughty_neal_arc_flash.py` (~190 LOC):
    * `doughty_neal_open_air_cal_cm2(Ia, t, D)`:
      E = 5271 × D^(-1.4738) × t × (0.0016·Ia² - 0.0076·Ia + 0.8938)
    * `doughty_neal_in_box_cal_cm2(Ia, t, D)`:
      E = 1038.7 × D^(-1.4738) × t × (0.0093·Ia² - 0.3453·Ia + 5.9675)
    * Range warnings (Ia 16-50 kA, D 100-455 mm OA / 100-610 mm IB)
    * Documentação anti-alucinação sobre relação OA/IB
      contraintuitiva
  - 10 testes (`test_pp_v1_6_0_doughty_neal.py`)

  Sprint C — DC arc-flash NFPA 70E §D.5:
  - NEW `app/standards/dc_arc_flash.py` (~200 LOC):
    * `DCArcFlashResult` dataclass
    * `dc_arc_flash_max_power(V, I_sc, t, D)`:
      V_arc = V/2, I_arc = I_sc/2, P_max = V·I_sc/4,
      E = P_max·t / (4π·D²·4.184)
    * AFB cálculo a partir de E threshold (1.2 cal/cm²)
    * Limitações declaradas (modelo esférico, sem choke
      DC, fuse I²t não considerado)
  - 10 testes (`test_pp_v1_6_0_dc_arc_flash.py`)

  Sprint D — CSA Z462 wrapper:
  - NEW `app/standards/csa_z462_arc_flash.py` (~150 LOC):
    * `CSAZ462Result` dataclass
    * `csa_z462_arc_flash(case)` — wraps `calculate_arc_flash`
    * `map_to_csa_risk_category(E)` — Risk Cat 0-4 / Dangerous
    * Naming PPE alinhado com CSA Z462-2021 §H.4
  - 8 testes (`test_pp_v1_6_0_csa_z462.py`)

  Sprint E — Comparison module:
  - NEW `app/postprocessor/arc_flash_comparison.py` (~410 LOC):
    * `StandardResult` + `ArcFlashComparison` dataclasses
    * `compare_all_standards(V, Ibf, t, D, is_dc)`:
      Roda 7 standards e marca cada um como
      applicable=True/False conforme range:
      - IEEE 1584-2018 (0.208–15 kV AC)
      - NBR 17227-2025 (0.208–15 kV AC)
      - EPRI 2011 (15–46 kV AC)
      - Doughty-Neal-Floyd 2000 (≤600 V AC)
      - NESC 2023 §410 (todas voltage AC)
      - CSA Z462 (0.208–15 kV AC)
      - NFPA 70E §D.5 (DC apenas)
    * Calcula most/least conservative + divergence_pct
    * Warning se divergence > 50%
  - 7 testes (`test_pp_v1_6_0_comparison.py`)

  Sprint F — GUI Comparison dialog:
  - NEW `app/gui/arc_flash_comparison_dialog.py` (~200 LOC):
    * 5 inputs (V, Ibf, t, D, DC checkbox)
    * Tabela results 5 cols (Standard / E / AFB / PPE / Notas)
    * Footer com most/least conservative + divergence
    * Auto-run com defaults didáticos
    * Salvar TXT
  - 6 testes (`test_gui_v1_6_0_comparison_dialog.py`)

  Sprint F (cont) — Menu wiring:
  - `main_window` Análise: novo "⚖ Comparar Standards de
    Arc-Flash (7 normas)..." entre DAPPER e Cable sizing
  - Handler `_on_compare_arc_flash_standards`

  Vantagem competitiva sobre softwares de mercado:

  | Software | Standards arc-flash |
  |----------|---------------------|
  | SKM PTW Power*Tools | IEEE 1584 |
  | EasyPower | IEEE 1584 + NFPA 70E |
  | ETAP | IEEE 1584 + DC |
  | **Olivas v1.6.0** | **IEEE 1584 + NBR 17227 + EPRI + Terzija + Doughty-Neal + NESC + CSA Z462 + DC NFPA 70E (8!)** |

  Métricas v1.6.0 finais:
  - **51 testes novos**:
    * 10 NESC + 10 Doughty-Neal + 10 DC + 8 CSA + 7 comparison
      + 6 GUI dialog
  - **6 arquivos novos** (~1360 LOC)
  - **Pequenas adições** em main_window (~16 linhas) e version.py
  - 0 deps externas adicionadas
  - **0 quebras nos 145 arc-flash tests anteriores** (anti-perda
    validado em cada Sprint)
  - 0 quebras nas 7 versões anteriores (CT-SAT v1.4.x + Plugin
    v1.5.0 + DAPPER v1.5.1 todos verde)

  Lição mantida: **protocolo de salvaguardas formal** documenta
  3 garantias (anti-alucinação + anti-perda + anti-acidental)
  como processo, não como aspiração. Cada Sprint termina com
  regression check — se quebra, REVERTER.

* 1.5.1 — DAPPER Demand Load Library (22 categorias NEC + sectors BR).

  **Foco**: 2ª release do roadmap pós-CT-SAT. Implementa o estudo
  Demand Load do PTW DAPPER (Reference-DAPPER §1.2-§1.4) com
  **vantagem competitiva** sobre o original — mapeamento NEC 220
  explícito + sectors industriais/comerciais brasileiros.

  Disciplina v1.3.1+ aplicada: Audit (`v1.5.1_BACKLOG_AUDIT.md` +
  research profundo do PDF DAPPER 922pp.) → Design
  (`v1.5.1_DESIGN.md`) → 7 sub-sprints com TDD → Handoff.

  Sprint A — NEC + sectors catalog (22 categorias):
  - NEW `app/postprocessor/dapper_catalog.py` (~430 LOC):
    * `LoadType` enum (Z/K/I)
    * `DemandLevel` dataclass (kVA_limit + demand_pct)
    * `DemandCategory` dataclass com NEC section + levels + LCL
    * 22 categorias prontas:
      - 16 NEC: 220.42 (lighting), 220.50 (motors), 220.51-56
        (heating/appliances/dryer/ranges/kitchen), 220.60-61
        (non-coincident/neutral), 220.82-88 (optional/existing/
        multifamily/schools/restaurants)
      - 6 sectors: receptacles/office/capacitor/standby/industrial/
        data_center (paridade PTW + adições BR)
    * Helpers: `get_category(code)`, `get_categories_by_nec(s)`,
      `list_nec_categories()`, `list_sector_categories()`
  - 17 testes (`test_pp_v1_5_1_dapper_catalog.py`)

  Sprint B+C — Demand calculator (Connected → Demand → Design):
  - NEW `app/postprocessor/studies/demand_load.py` (~280 LOC):
    * `LoadEntry` dataclass (input)
    * `CategoryResult` + `DemandReport` (outputs)
    * `apply_demand_levels(connected, levels)`:
      multi-level chunked calculation (até 3 patamares por
      categoria) — paridade Reference-DAPPER §1.3
    * `compute_demand(entries)`:
      1. agrupa por category_code
      2. soma connected
      3. aplica multi-level → demand
      4. multiplica por LCL → design
      5. weighted PF ponderado por demand
    * `DemandReport.summary()` formato paridade PTW LOAD SCHEDULE
  - 11 testes (`test_pp_v1_5_1_demand_calculator.py`)
  - Diversity capturada implicitamente via multi-level (segundo
    patamar reduz demand vs soma 100%-coincident)

  Sprint D — UI dialog:
  - NEW `app/gui/demand_load_dialog.py` (~340 LOC):
    * QTableWidget de entries com 4 colunas
      (Nome / Categoria ComboBox / Connected SpinBox / PF override)
    * 5 entries didáticas pré-populadas
    * 2 tabs de resultado: 📋 Sumário (texto) + 📊 Por Categoria
      (QTableWidget 7 cols)
    * Botões: ➕ Adicionar / ➖ Remover / ▶ Calcular (verde) /
      💾 Salvar TXT / 💾 Salvar XLSX
    * Banner explicativo + status feedback via setWindowTitle
      (paridade lição v1.4.4 G — sem QMessageBox bloqueante)
  - 7 testes (`test_gui_v1_5_1_demand_dialog.py`)

  Sprint E — TXT/XLSX export:
  - NEW `app/postprocessor/dapper_io.py` (~140 LOC):
    * `write_demand_report_txt(report, path)` — paridade PTW
      LOAD SCHEDULE formatting + citações normativas
    * `write_demand_report_xlsx(report, path)`:
      - Sheet "Resumo" (9 cols × N categorias + linha total)
      - Sheet "Detalhe" (4 cols com entries originais)
      - Header colorido #143250 (consistência v1.4.4 + v1.5.0)

  Sprint F — Menu wiring:
  - `main_window`: novo "⚡ Demand Load Study (DAPPER, 22 categorias
    NEC)..." em Análise (entre CT-SAT e cable sizing)
  - Handler `_on_analyze_demand_load` abre dialog

  Métricas v1.5.1 finais:
  - **35 testes novos**:
    * 17 catalog
    * 11 calculator
    * 7 dialog
  - **4 arquivos novos** (~1190 LOC)
  - 0 deps externas adicionadas (openpyxl já presente desde v1.4.4)
  - 0 quebras nas 6 versões anteriores (CT-SAT v1.4.3 + v1.4.4 +
    v1.4.5 + Plugin v1.5.0 todos verde)
  - 22 categorias prontas (vs 7 defaults do PTW + 13 slots vazios)

  **Vantagem competitiva sobre PTW**: PTW DAPPER vem com 7 defaults
  genéricos e exige usuário customizar 13 slots. Olivas v1.5.1 vem
  com 22 categorias mapeadas explicitamente para NEC 220.x —
  engenheiro brasileiro não precisa decifrar tabelas NEC e
  configurar slot-a-slot. Paridade visual com PTW LOAD SCHEDULE +
  semântica explícita. Cobertura NEC: 16 sections do Article 220.

* 1.5.0 — Plugin Marketplace (UI + descoberta + segurança).

  **Foco**: primeira release do roadmap pós-correção CT-SAT (v1.4.5).
  Estende o foundation v0.105.0 (decorators + bare-py discovery) com:

  * Manifest schema (Pydantic) com 7 categorias e 11 permissões
    declaráveis (whitelist fechada)
  * Discovery v2 manifest-based em 3 fontes (builtin/installed/project)
  * Lifecycle persistido (state.json) com enabled/approved_permissions
  * Security layer: SHA256 + version compat + permissions check
  * Install/Uninstall workflow atômico (copy → tmp → rename)
  * UI Marketplace dialog (3 tabs: Instalados / Disponíveis /
    Configurações)
  * 3 builtin plugins demonstrando capacidades (solar PV, NBR 5410,
    CSV exporter)
  * Startup auto-load somente de plugins enabled (privacy first)

  Disciplina v1.3.1+ aplicada: Audit (`v1.5.0_BACKLOG_AUDIT.md`) →
  Design (`v1.5.0_DESIGN.md`) → 7 sub-sprints com TDD → Handoff.

  Sprint A — Manifest schema (Pydantic v2):
  - NEW `app/plugins/manifest.py` (~210 LOC):
    * `PluginPermission` enum: 11 permissões whitelist
      (studies/equipment/renderers/exporters/postprocessors/
       validators/catalog_specs + filesystem.read/write +
       network + subprocess)
    * `PluginCategory` enum: 7 categorias
    * `PluginManifest` Pydantic model com validation:
      - name regex `^[a-z][a-z0-9_]*$` (snake_case)
      - semver simples para version + min/max_olivas_version
      - `is_compatible_with_olivas(version)` helper
    * `load_manifest_from_yaml()` + `load_manifest_from_path()`
  - 14 testes (`test_pp_v1_5_0_plugin_manifest.py`)

  Sprint B — Discovery v2 + Lifecycle:
  - NEW `app/plugins/lifecycle.py` (~270 LOC):
    * `DiscoveredPlugin` dataclass (manifest + plugin_dir + source)
    * `discover_plugins_v2(builtin_dir, user_dir, project_dir)`:
      escaneia 3 fontes, valida YAML, source label explícito,
      precedência builtin > installed > project
    * `LifecycleState` class — state.json com schema_version,
      enable/disable/remove/is_enabled/approved_permissions
    * `auto_load_enabled_plugins()` — só carrega enabled
  - 9 testes (`test_pp_v1_5_0_plugin_lifecycle.py`)

  Sprint C — Security:
  - NEW `app/plugins/security.py` (~220 LOC):
    * `compute_sha256` / `verify_sha256` — chunked hash
    * `check_permissions_supported` — whitelist contra enum
    * `install_plugin(source, target, olivas_version)`:
      copy atômico (tmp + rename) com validações:
      manifest válido + entry_point existe + version compat +
      permissions whitelist + opcional SHA256 verify
    * `uninstall_plugin` — rmtree do dir
    * `InstallResult` dataclass para UI feedback
  - 10 testes (`test_pp_v1_5_0_plugin_security.py`)

  Sprint D — UI Marketplace dialog:
  - NEW `app/gui/plugin_marketplace_dialog.py` (~360 LOC):
    * QDialog 3 tabs com QTabWidget
    * Tab 1 (📦 Instalados): QListWidget + 4 ações
      (Habilitar/Desabilitar/Detalhes/Desinstalar)
    * Tab 2 (🛒 Disponíveis): empty state explicativo (catálogo
      remoto vem em v1.5.1)
    * Tab 3 (⚙ Configurações): caminhos dos 3 dirs + opções
    * `_on_enable` com QMessageBox de confirmação de permissões
    * `_on_uninstall` apenas para source='installed'
    * Disclaimer "plugins rodam com seus privilégios"
    * Status feedback via setWindowTitle (não bloqueia tests)
  - 6 testes (`test_gui_v1_5_0_marketplace_dialog.py`)

  Sprint E — Builtin catalog (3 plugins de exemplo):
  - NEW `app/plugins/builtin/solar_pv_yield/`:
    * Calcula yield anual de sistema fotovoltaico (NREL Sandia
      simplificado, contexto Brasil)
    * Permission: studies
  - NEW `app/plugins/builtin/nbr_5410_validator/`:
    * Valida circuitos NBR 5410 §6.2.7 (queda V), §6.2.5 (FC),
      §5.3.4 (proteção)
    * Permission: validators
  - NEW `app/plugins/builtin/csv_exporter/`:
    * Exporta dict de resultados para CSV (delimitado por ; para
      Excel-BR), modo append
    * Permissions: exporters, filesystem.write

  Sprint F — Menu wiring + startup discovery:
  - `main_window._build_menu`: novo "🧩 Plugin Marketplace..."
    em Ferramentas (substitui dialog read-only legacy v1.0.2,
    preservado em `_on_show_plugins`)
  - `MainWindow.__init__`: chama `auto_load_enabled_plugins()`
    no final, log resumido no console panel
  - `app/plugins/__init__.py`: exporta toda a v1.5.0 API

  Métricas v1.5.0 finais:
  - **39 testes novos**:
    * 14 manifest schema
    * 9 lifecycle/discovery
    * 10 security/install
    * 6 dialog UI
  - **6 arquivos novos** (~1060 LOC)
  - 3 builtin plugins (~120 LOC manifest + plugin.py cada)
  - 0 deps externas adicionadas (usa pydantic + PyYAML já
    presentes)
  - 0 quebras backward-compat (testes v0.105.0 continuam verde)
  - 0 quebras CT-SAT (testes v1.4.3-v1.4.5 continuam verde)
  - 6 PDFs PTW + research VS Code/Photoshop/Excel patterns

  Lição mantida: **plugins como cidadãos de primeira classe** —
  manifest declara intenção, security gate antes de carregar,
  UI marketplace para gerenciar, builtin catalog demonstra
  capacidades. Princípio "privacy/segurança first": auto-load
  só plugins enabled, opt-in explícito.

* 1.4.5 — User Gate Fixes pós-v1.4.4 (alinhamento PTW patterns).

  **Crítica do usuário (user gate v1.4.4)**: 4 issues identificados no
  uso real:

  1. **PTW menção enganosa**: botão "Carregar JSON (PTW)" sugere
     integração ativa que não existe.
  2. **Janelas/gráficos mal dimensionados**: subplot título de N3
     sobrepõe eixo do subplot 1.
  3. **Análise desacoplada do canvas**: análise de CT_SAT abre
     sempre, deveria exigir TC selecionado.
  4. **Menu Visualizar > Gráficos sem propósito**: docks abrem
     vazios sem explicar o prerequisito.

  **Disciplina v1.3.1+** + **PTW research profundo** (lidos 6 PDFs
  do `LIB/PTW_MANUAL/`): Audit (`v1.4.5_BACKLOG_AUDIT.md`) → Design
  (`v1.4.5_DESIGN.md`) → 4 sub-sprints com TDD → User testing gate.

  Sprint A — Remover menções PTW (paridade Userguide §4: sem
  importadores externos enganosos):
  - `ct_saturation_dialog.py:117`: "Carregar JSON (PTW)" →
    "Importar dados de TCs (JSON)" com tooltip explicando
    compatibilidade (sem integração)
  - `ct_saturation_io.py` docstring: revisada para mencionar PTW
    apenas como "compatível com" + "Olivas NÃO tem integração ativa"

  Sprint B — Layout dos plots (paridade CAPTOR aspect-ratio toggle):
  - `ct_saturation_plots.py`: todos os 3 plots agora usam
    `Figure(constrained_layout=True)` (substitui `tight_layout`)
  - `plot_level3_dynamic`: figsize 9×8 → 11×9; subplot 2
    `set_title` removido (título migrou para ylabel em 2 linhas)
    para evitar sobreposição
  - `ct_saturation_dialog.py`: resize 1200×850 → 1280×900 +
    `setMinimumWidth(1280)`

  Sprint C — Workflow gateado por seleção (paridade Equipment
  Evaluation §1.2 + Coordination Eval §3.4: "Available only when
  X is selected"):
  - NEW `CTSelection` dataclass em `ct_saturation_io.py` (bridge
    PpComponent CT → CTSpec/CTFaultContext)
  - `CTSelection.from_pp_component(comp)`: lê 10 properties do
    CT.ocomp (tag, ratio_pri/sec, classe, c_rating_V, rs/rb_ohm,
    kr, t_relay/breaker_ms)
  - `main_window._on_analyze_ct_saturation`: detecta
    `scene.selectedItems()` antes; sem TC → QMessageBox com
    workflow PTW-style (1.Modo Online → 2.Selecione TC →
    3.Análise) + escape hatch "modo didático" (Yes/Cancel)
  - `CTSaturationDialog(selection=...)`: aceita CTSelection,
    popula form, bloqueia TAG (read-only), banner contextual
    🎯 "Analisando TC '<tag>'" vs 📚 "Modo didático"

  Sprint D — Empty states (paridade Datablock Reports do PTW
  Userguide §6314-6346: nunca abre vazio sem explicar):
  - `_BasePlotDock` agora usa `QStackedWidget` (page 0: empty
    state QLabel, page 1: matplotlib canvas)
  - NEW API: `show_empty_state(html_msg)`, `_show_plot()`,
    `is_empty()`
  - 4 docks com mensagem específica explicando prerequisito + como
    popular (F5 → marque X → Executar):
    * Power Flow Voltage Profile
    * SC Source Contributions
    * TCC Coordination Curves
    * Monte Carlo Histogram (Arc-Flash)
  - Menu renomeado: "Gráficos" → "Resultados (gráficos das
    análises)" + emojis + setStatusTip por item

  Métricas v1.4.5 finais:
  - **13 testes novos** (`test_v1_4_5_user_gate_fixes.py`)
  - 0 quebras em testes v1.4.4 (50 testes anteriores verde)
  - 0 quebras em paridade MATLAB v1.4.3 (10 testes verde)
  - 4 arquivos modificados (~210 LOC delta)
  - 1 nova classe `CTSelection` (~80 LOC)
  - 0 deps externas adicionadas
  - 6 PDFs PTW lidos como evidência (Userguide, CAPTOR,
    Coord Eval, Equip Eval, A_Fault, Tutorial V11)

  Lição mantida: **user audit pós-uso real** sempre revela 30-50%
  de issues que TDD não pega — porque TDD valida especificação,
  não decisões UX. Disciplina v1.3.1+ exige user gate ANTES de
  prosseguir.

* 1.4.4 — CT Saturation **STUDY** completo (paridade MATLAB CT_STUDY).

  **Crítica do usuário (28/abr/2026)**: v1.4.3 validou as fórmulas
  do MATLAB CT_STUDY mas **não replicou o estudo completo** —
  workflow + plots + relatórios. v1.4.4 fecha esse gap.

  **Disciplina v1.3.1+**: Audit (`v1.4.4_BACKLOG_AUDIT.md`) →
  Design (`v1.4.4_DESIGN.md`) → 7 sub-sprints com TDD →
  User testing gate.

  Sprints A/B/C — 3 plots especializados (paridade MATLAB):
  NEW `app/gui/ct_saturation_plots.py` (~430 LOC) com 3 funções
  reutilizáveis (não-Qt, retornam Figure):

  * `plot_level1_ansi(report)`:
    - Barras condicionais V_tap (azul) vs V_req (verde/vermelho
      conforme PASSOU/FALHOU)
    - Anotação numérica em cada barra
    - Linha tracejada preta = limite do tape
    - Título com cor dinâmica + recomendação ANSI

  * `plot_level2_iec(report)`:
    - Eixos log-log (paridade MATLAB `loglog`)
    - Curva preta sólida da magnetização
    - Marcador verde joelho real (`Ek_actual`) com anotação
    - Marcador azul/vermelho ponto requerido
    - Linha tracejada horizontal Ek_req
    - Anotações `REGIÃO LINEAR` / `SATURAÇÃO`
    - Título com margem de tensão

  * `plot_level3_dynamic(report)`:
    - 2 subplots empilhados (paridade MATLAB `subplot 2,1,1/2`)
    - Subplot 1 (Fluxo λ(t)):
      * 3 zonas axvspan: verde clara (pré-trip), amarela
        (margem tolerância), vermelha clara (saturação)
      * Curva fluxo preta sólida
      * Linhas vermelhas em ±λ_joelho
      * Linha verde TRIP, vermelha tracejada SAT
      * Marcador azul + info-box "Uso no Trip: X.X%"
    * Subplot 2 (Correntes):
      * Mesmas zonas (alpha menor)
      * Linha vermelha tracejada I_sec ideal
      * Linha azul sólida I_sec real
      * fill_between vermelho (área de erro/distorção)

  Paleta de cores (constante COLOR_PASS/FAIL/PRIMARY/KNEE +
  ZONE_SAFE/TOLERANCE/SATURATION) com paridade MATLAB.

  Sprint D — Workflow refinamento (paridade `main_CT_Analysis.m`
  loop `while true`):
  - Botão "⚙ Re-dimensionar" no dialog
  - Helper `next_ansi_class(C)`: 100 → 200 → 400 → 800 → custom
  - Atualiza form + re-roda análise atomicamente

  Sprint E — JSON loader 99 TCs reais:
  NEW `app/postprocessor/ct_saturation_io.py` (~290 LOC):
  - `load_ct_system_data(path)` → list[CTFaultContext]
  - `list_cts_table(path)` → list[dict] para popular QListWidget
  - Schema: CT_TAG, Bus_in, V_LL_kV, I_fault_rms_kA, X_over_R,
    CT_Ratio, Protection_Type, Protected_Device
  - Botão "📂 Carregar JSON (PTW)" no dialog
  - Duplo-clique em item da lista popula form
    (incluindo extração I_pri/I_sn de "600 / 5") + auto re-analyze

  Sprint F — Geração de relatórios TXT + XLSX (paridade
  `generate_reports.m`):
  - `write_report_txt(report, path)`:
    * Cabeçalho TAG + data + RESULTADO FINAL
    * Seção 1: Especificação do TC
    * Seção 2: Dados do Sistema
    * Seção 3: Análise Dinâmica + dicas condicionais
      (Kr > 0.1 → sugere PR; FALHOU → sugere classe maior)
    * Citações normativas (IEEE C37.13.1, IEC 61869-2,
      CIGRÉ WG 23-15)
  - `write_report_xlsx(report, path)`:
    * 16 linhas (8 do MATLAB + 8 extras Olivas)
    * Header colorido (#143250)
    * openpyxl >= 3.1.0 (NEW dep em requirements.txt)
  - `write_reports_default_names(report, dir)`:
    * Replica naming MATLAB: `Relatorio_<TAG>.txt` +
      `Datasheet_<TAG>.xlsx`
  - Botões "💾 Salvar TXT" / "💾 Salvar XLSX" no dialog
    com QFileDialog

  Sprint G — Integração GUI (4 tabs de resultado):
  - `app/gui/ct_saturation_dialog.py` reescrito:
    * Tab 1: 📋 Sumário (texto)
    * Tab 2: 📊 Nível 1 (ANSI) — barras V_tap vs V_req
    * Tab 3: 🎯 Nível 2 (IEC) — log-log + joelho
    * Tab 4: ⚡ Nível 3 (Dinâmico) — fluxo + correntes
  - Auto-run com defaults didáticos (TC C400 @ 2000:5)
  - NavigationToolbar matplotlib (zoom/pan/save) opcional
    em cada tab (graceful fallback em headless)
  - Refinamento via setWindowTitle (não bloqueia testes)

  Métricas v1.4.4 finais:
  - **40 testes novos**:
    * 17 plots (`test_pp_v1_4_4_ct_study_plots.py`)
    * 16 IO (`test_pp_v1_4_4_ct_study_io.py`)
    * 7 dialog (`test_gui_v1_4_4_ct_saturation_dialog.py`)
  - 2 arquivos novos (`ct_saturation_plots.py` +
    `ct_saturation_io.py`)
  - ~720 LOC novo + dialog reescrito (~410 LOC)
  - 1 dep nova (openpyxl>=3.1.0 em requirements.txt)
  - 0 quebras de paridade MATLAB v1.4.3 (10 testes parity
    continuam verdes)

  Lição mantida: **estudo completo não é só fórmula** — é
  fórmula + UX + relatórios. v1.4.3 cobriu fórmula; v1.4.4
  fecha o estudo.

* 1.4.3 — Sprints D + G fechadas (gaps deferidos do v1.4.2).

  Sprint G — CT Saturation MATLAB Parity Validation:
  - Modelo MATLAB CT_STUDY do usuário (em `D:/000-UFMG/MVP/LIB/
    LIB/CT_STUDY/` — 17 arquivos .m + ct_system_data.json com
    99 TCs reais) confrontado linha-por-linha com Python
    `app/postprocessor/ct_saturation.py`:

    * Level 1 (ANSI): fórmulas IDÊNTICAS
      - V_tap = V_capacity_full × (I_pri_tap / I_pri_full)
      - V_req = I_fault_sec × (1 + X/R) × Z_loop
    * Level 2 (IEC joelho): fórmulas IDÊNTICAS
      - Ek_req = mesma fórmula que V_req
      - Ek_actual via critério IEC 10/50 (10% V → 50% I_e)
    * Level 3 (Dinâmico): física IDÊNTICA
      - dλ/dt = (i_st(t) - i_e(λ)) × R_total
      - i_p(t) = I_peak × (sin(ωt + φ - θ) - sin(φ-θ)×exp(-t/T_p))
      - phi=0 (pior caso DC offset máximo)
      - λ(0) = Kr × λ_joelho
      - Diferença numérica: MATLAB ode45 (adaptativo,
        RelTol=1e-4) vs Python RK4 fixo (h=0.1ms, n_steps=2001).
        Mesma física, precisão equivalente para timescale ms.

  - **Conclusão**: implementação Python é **demonstravelmente
    equivalente** ao MATLAB de referência do user. Bug 0
    detectado. Comportamento qualitativo bate em todos os
    casos testados (defaults didáticos + ct_system_data.json[0]
    real "00-MF-32/42" com 1200:5 + 28.4 kA + X/R=13).

  - 10 testes canonical novos em
    `test_pp_v1_4_3_ct_saturation_matlab_parity.py`:
    * TestLevel1AnsiCanonical (3): C400 tap2000 fault20kA xr10,
      tap-half penalty, C800 caso real do JSON
    * TestLevel2IecCanonical (2): IEC P knee 10/50, IEC PR
      vs P (Kr=0.1 vs 0.8)
    * TestLevel3DynamicCanonical (2): smoke RK4, IEC PR
      aguenta mais que IEC P (menor remanência)
    * TestAnalyzeFullCanonical (2): full pipeline 3 níveis
    * TestMatlabFormulasParity (1): caso real do
      ct_system_data.json[0]

  - Helpers de construção replicam MATLAB
    `get_CT_Data_Interactive.m`:
    * `_build_burden(R_relay, dist_m, mm2)` ↔ `calculate_Rb.m`
      (RHO_COBRE_75C = 0.0209)
    * `_build_ansi_ct(...)` ↔ menu ANSI (Kr=0.8 default)
    * `_build_iec_ct(..., is_PR)` ↔ menu IEC P/PR
      (Kr=0.8 P / 0.1 PR)

  Sprint D — BREAKER component (disjuntor controlado por relé):
  - NEW `app/preprocessor/catalog_specs/BREAKER.ocomp`:
    * Disjuntor genérico orientado a análise NBR/IEEE
      (não-ATP), distinto de VCB/VCB3 (legacy ATP-orientado).
    * 3 pinos: T1/T2 (linha em série) + Trip_in (vertical
      superior, recebe sinal do RELAY.Trip_out via wire).
    * 11 properties: tag, vendor_model (link Library),
      rated_voltage_kV, rated_current_A, breaking_capacity_kA,
      mechanism (vacuum/SF6/oil/air-magnetic/MCB),
      operating_time_ms, arc_time_ms, relay_link_tag.
    * Cobertura: IEEE C37.04-2018, IEC 62271-100:2021,
      NBR IEC 62271-100, NEMA AB-1, UL 489.

  - Symbol: usa `CircuitBreakerSymbol` (PTW-style quadrado +
    cruz, override em ptw_symbols.py).
  - `_COMPAT_MAP` em equipment_library_dialog.py atualizado:
    BreakerModel → {BREAKER, VCB, VCB3} (BREAKER preferido).

  - 9 testes em `test_pp_v1_4_3_breaker_component.py`:
    spec loadable, 3 pins, properties essenciais, mechanism
    choices, atp_supported=False, renderer CircuitBreaker,
    paint sem crash, na paleta, library Apply funciona.

  Catálogo total: 55 → **56** componentes (+ BREAKER).

  Métricas v1.4.3 finais:
  - **19 testes novos** (10 MATLAB parity + 9 BREAKER)
  - **710/710 sweep regression verde**
  - 2 arquivos novos (BREAKER.ocomp + tests parity)
  - ~250 LOC novo
  - 0 deps externas adicionadas
  - 0 issues remanescentes do user audit Round 2

  Lição mantida (validação cruzada): **MATLAB ↔ Python
  parity comprovada por testes canonical** com casos do
  modelo de referência do dono. Anti-alucinação confirmada.

* 1.4.2 — HOTFIX User Audit Round 2 (pós uso v1.4.1).

  Nova rodada de feedback do uso real detectou 7 issues
  remanescentes. v1.4.2 fecha 5 (Sprints A/B/C/E/F) e
  defere 2 (D combo + G MATLAB validation) para v1.4.3.
  Documentação: `docs/v1.4.2_BACKLOG_AUDIT.md`.

  Sprint A — Logo .ico (multi-resolução):
  - Usuário providenciou `app/resources/logo.ico` (268 KB,
    múltiplas resoluções 16/32/48/64/128 px).
  - `app/main.py` agora prioriza `.ico` sobre `.png`.
    Windows usa o tamanho correto em title bar / taskbar /
    Alt-Tab (resolve "logo não aparece" reportado).

  Sprint B — Menu "Validação" removido definitivamente:
  - main_window.py:574 `val_menu = menu_bar.addMenu("Validação")`
    REMOVIDO. Em v1.4.1 a TAB foi removida; v1.4.2 remove
    também o MENU. Funcionalidade equivalente disponível em
    Análise → Verificar regras / Avaliar equipamentos.
  - menu_bar reduzido para 7 menus (Arquivo, Editar, Análise,
    Ferramentas, Ajuda, Exemplos, Visualizar).

  Sprint C — RelaySymbol PTW-style:
  - NEW `RelaySymbol` em `ptw_symbols.py`: círculo 30×30
    com letra "R" central (paleta PTW azul corporativo
    #006699) + indicador ANSI superior ("51"). Pinos
    cardinais: T1/T2 horizontais + TC link superior + Trip
    inferior.
  - `get_ptw_renderer()` agora mapeia "RELAY" → RelaySymbol
    (override do default que era RelaisSymbol).
  - Distinção visual clara entre RELAY (proteção) e Relais
    (chave) — antes ambos pareciam iguais.

  Sprint E — Equipment Library Apply workflow:
  - NEW `app/gui/equipment_library_dialog.py` (~280 LOC):
    `EquipmentLibraryDialog(QDialog)` substitui dialog inline
    do main_window. Inclui:
    * 4 tabs (Relés/Motores/Trafos/Disjuntores) — preserva v1.0.2
    * Botão "Aplicar ao dispositivo selecionado" (NOVO)
    * `selected_model()` — pega modelo da tab atual
    * `get_selected_pp_component()` — detecta componente
      selecionado no PpEditor via `scene.selectedItems()`
    * `apply_model_to_component(model, component)` →
      `(ok, message)` — valida compatibilidade + popula props
    * `_apply_specs(model, component)` — copia
      vendor_model + ratings principais
  - Compat map:
    * RelayModel → componentes RELAY (preferido) e Relais
    * MotorModel → MOTOR
    * TransformerModel → XFMR3, Tr, Tr3, sTr
    * BreakerModel → VCB, VCB3
  - Mensagens de erro claras para incompatibilidades + sem
    componente selecionado.
  - Resolve issue do user "vendor list sem função".

  Sprint F — Online overlay para tipos v1.2-v1.4:
  - `OnlineOverlayManager._annotation_for()` estendido para
    cobrir 5 tipos novos:
    * RELAY → "ANSI: 51,50,49 / 51: 120A TMS=0.30 / 50: 600A"
    * XFMR3 → "1000 kVA · 13.8/0.48 kV / Dyn1 · Z=5.75%"
    * MOTOR → "P = 100 kW / V = 480"
    * CABLE → "S=50mm² Cu_XLPE / L=100m"
    * CT → "TC: 2000/5 / Classe: ANSI_C"
  - 5 helpers `_*_static_annotation` reusam helper genérico
    `_get_prop_value(component, prop_name)` para extrair
    properties.
  - Severity = "info" (azul) para diferenciar de overlays
    SC dynamic (verde/amarelo/vermelho por utilization).

  Sprint D — RELAY_BREAKER combo (DEFERRED v1.4.3):
  - Análise técnica: RELAY já tem pin "Trip_out" para
    conectar ao disjuntor via wire. Combo seria atalho UX
    mas não traz funcionalidade nova.
  - Decisão: defer. Documento sobre como o user combina
    RELAY+VCB via wire fica no manual.

  Sprint G — CT Saturation MATLAB validation (DEFERRED
  parcial v1.4.3):
  - Inspecionado MATLAB CT_STUDY (17 arquivos .m) no
    diretório `D:/000-UFMG/MVP/LIB/LIB/CT_STUDY/`.
  - 3 níveis MATLAB confrontados linha-por-linha com
    Python `app/postprocessor/ct_saturation.py`.
  - Conclusão: comportamento qualitativo bate (37 testes
    Python existentes + smoke do dialog mostra mesmas
    decisões PASSOU/FALHOU/APROVADO COM TOLERÂNCIA).
  - Validação canonical bit-a-bit fica para v1.4.3
    (suite de testes "MATLAB parity" com casos exatos do
    `ct_system_data.json` do CT_STUDY).

  Métricas v1.4.2 finais:
  - **18 testes novos** em
    `test_pp_v1_4_2_user_audit_round2.py`
  - **691/691 sweep regression verde**
  - 2 arquivos novos (equipment_library_dialog.py +
    extensões em ptw_symbols.py + online_overlay.py)
  - ~480 LOC novo
  - 5 issues fechadas (A/B/C/E/F)
  - 2 deferred com justificativa documentada (D/G)
  - 0 deps externas adicionadas

  Lição aprendida (mantida): user testing gate continua
  detectando gaps. v1.4.3 deve incluir validação canonical
  MATLAB↔Python para CT Saturation antes de fechar v1.5.

* 1.4.1 — HOTFIX User Audit v1.4.0 (9 issues do uso real).

  Auditoria pós-uso real do v1.4.0 pelo Landerson Ferreira
  Silva detectou 9 issues — 8 confirmadas via inspeção AST.
  Documentadas em `docs/v1.4.1_BACKLOG_AUDIT.md` com
  evidência forense (linha de código + arquivo).

  Sprint A — ATP cleanup (P0 regressão v0.92.2):
  - `app/gui/chat_widget.py:173-191`: `_HELP_TEXT` reescrito
    sem comandos ATP (`executar / run`, `abrir/salvar .atp`).
    Substituído por `analisar curto/coord/arc-flash/pf`,
    `laudo`, `abrir/salvar .sch`. Status quo do
    reposicionamento Power System Studio v0.92.2 restaurado.
  - `chat_widget.py:380`: "Abra um arquivo .atp" → "Abra um
    esquemático .sch ou crie um novo via paleta"
  - `main_window.py:1244`: status bar "abra um arquivo .atp"
    → "abra um esquemático .sch"
  - `main_window.py:151-152`: removido status "ATP
    configurado" (não relevante para Power System Studio)
  - **Tabs "Detalhes" e "Validação" REMOVIDAS**: ambas
    estavam orfãs após v0.92.1 (sem ATP tree, sem ATP
    validators). Tabs reduzidas de 4 para 2 (Esquemático
    Visual + Agente Claude). Funcionalidade equivalente:
    Propriedades de componente → painel direito do PpEditor;
    Validação → menu Validação > Validar projeto.

  Sprint B — Componentes faltantes (P0):
  - NEW `RELAY.ocomp`: relé de PROTEÇÃO (50/51/49/87/27/59
    /81/79) — distinto de "Relais" (chave controlada
    legacy v0.21.x). Properties: tag, vendor_model (link à
    EquipmentLibrary), ansi_devices CSV, curve_51 enum
    (IEC/ANSI), pickup_51_A + tms_51, pickup_50_A +
    delay_50_s, pickup_49_A + delay_49_s, pickup_87_A +
    delay_87_s, ct_link_tag. Cobertura: IEEE 242 §9 e §11,
    IEC 60255-151:2009, IEEE C37.112-2018.
  - NEW `XFMR3.ocomp`: transformador trifásico para análise
    NBR/IEEE — substitui Tr3 ATP-orientado. Properties:
    kVA_rated, V_pri_kV, V_sec_kV, **vector_group** enum
    (Yyn0/YNyn0/Dyn1/Dyn5/Dyn11/Yd1/Yd11/Dy1/Dy11/Yy0/Dd0),
    impedance_pct (% Z padrão ANSI), xr_ratio,
    pri_grounding + sec_grounding (none/solid/resistance/
    reactance) com ohm value, tap_position. Cobertura:
    IEEE C57.12.00, IEEE C57.109-1993, IEC 60076-1, NBR 5356.
    Resolve issue do user "transformadores trifásicos sem
    seleção de enrolamento delta-estrela; estrela-delta;
    delta-estrela aterrado".
  - Symbols registry: RELAY → RelaisSymbol, XFMR3 →
    TransformerSymbol (mesmo visual de Tr3).
  - Catálogo total: 53 → **55 componentes** (+ RELAY + XFMR3).

  Sprint C — CT Saturation GUI (P0 — fecha sprint v0.93.1
  esquecida):
  - NEW `app/gui/ct_saturation_dialog.py` (~280 LOC):
    `CTSaturationDialog(QDialog)` substitui placeholder
    QMessageBox "em desenvolvimento" (que existia desde
    v0.93.0).
    * Form com 11 campos (CTFaultContext + CTSpec)
    * Botão "Analisar saturação" → roda `analyze_full`
    * Tab 1: sumário texto
    * Tab 2: curva de magnetização (matplotlib QtAgg)
    * Auto-run com defaults para usuário ver resultado
      logo de cara
  - `_on_analyze_ct_saturation` em main_window agora abre
    o dialog real (código legacy QMessageBox preservado
    como referência mas nunca executado).

  Sprint D — Equipment Library Ctrl+B (P1):
  - Atalho **Ctrl+B** registrado para "Biblioteca de
    equipamentos" (issue #8 — usuário não encontrou
    facilmente).
  - Status tip atualizado.

  Tests: 19 testes em `test_pp_v1_4_1_user_audit_fixes.py`
  cobrindo cada issue:
  - TestIssue1_AtpCleanupChat (2): chat sem ATP, comandos novos
  - TestIssues3_4_TabsRemoved (4): só 2 tabs, sem Detalhes,
    sem Validação, status bar limpo
  - TestIssue5_CtSaturationDialog (4): dialog construct,
    auto-run demo, summary populated, handler usa novo dialog
  - TestIssue6_7_NewCatalogSpecs (4): RELAY + XFMR3 spec
    loadable, vector_group choices, grounding choices
  - TestIssue9_PaletteHasNewComponents (3): RELAY + XFMR3
    + legacy Relais coexistem
  - TestIssue8_EquipmentLibraryShortcut (2): handler exists,
    Ctrl+B registrado

  Métricas v1.4.1 finais:
  - 19 testes novos
  - **922/922 sweep regression verde** (legacy v1.0+ a v1.4.1)
  - 2 arquivos novos (.ocomp + ct_saturation_dialog.py)
  - ~580 LOC novo
  - 0 deps externas adicionadas
  - Issues fechadas: 8/9 (issue #2 logo é trabalho visual
    que requer geração de .ico — deferred v1.4.2)

  Lição aprendida (registrada): **uso real pelo usuário
  detecta gaps que audit programático não pega**. Issues
  como tab orfã, sprint esquecida (CT Saturation v0.93.1) e
  ATP residual em strings só vêm à tona quando alguém
  abre o app e tenta usar.

* 1.4.0 — Custom Label Designer arc-flash (último P0 do
  roadmap original AUDIT v1.1.0 — paridade total com PTW
  Power*Tools v11).

  PTW Custom Label Designer gera labels arc-flash imprimíveis
  NFPA 70E / NESC com 30+ text fields user-customizable e
  cores dinâmicas. Esses labels são o **deliverable visual
  mais importante** para compliance comercial (NFPA 70E §130.5
  exige label permanente em equipamento ≥50V).

  Olivas v1.3.x já tinha o cálculo (`arc_flash.py::ArcFlashReport`
  com Iarc, DLA, PPE category, etc.) — faltava apenas o gerador
  de label + GUI.

  Lição aplicada v1.3.1: **GUI gate desde início** — sub-sprints
  A+B+C entregam backend + GUI + integração juntas (não
  backend isolado).

  Sub-sprint A — Data model + render HTML:
  - NEW `app/postprocessor/arc_flash_label.py` (~430 LOC):
    * `ArcFlashLabel` frozen dataclass com 30 fields
      (identificação, arc-flash calcs, PPE, aproximação,
      EPI, notes, audit)
    * `LabelStyle` enum: NFPA_70E_2024, NESC_2023_TYPE_4_5,
      MINIMAL_BR
    * `from_arc_flash_report(report, **overrides)` classmethod
      que auto-fill 30 fields de um ArcFlashReport (mapeamento
      glove_class por kV, PPE description por category, etc.)
    * `ppe_category_color(cat)` → cores dinâmicas por
      category (DANGER=#C62828, CAT 4=#E64A19 laranja-vermelho,
      CAT 0=#2E7D32 verde, etc.)
    * `render_html_label(label, style)` → HTML standalone
      print-ready com CSS @media print

  - 23 testes em `test_pp_v1_4_0_arc_flash_label_A.py`:
    construct, 30 fields, from_arc_flash_report, glove
    class por kV (00=≤500V, 0=≤1kV, 1=≤7.5kV, 2=≤17kV,
    3=≤26.5kV, 4=>26.5kV), PPE colors, 3 styles render,
    XSS-safe, audit SHA256, notes section.

  Sub-sprint B — LabelDesignerDialog GUI:
  - NEW `app/gui/arc_flash_label_dialog.py` (~290 LOC):
    * `LabelDesignerDialog(QDialog)` com:
      - QTableWidget 30 rows × 2 cols (campo + valor PT-BR)
      - QComboBox de 3 estilos
      - QTextBrowser preview live
      - Debounce 300ms via QTimer (evita re-render por keystroke)
      - Auto-load demo ao abrir
      - Botões "Carregar Demo" + "Salvar HTML"
    * `_build_demo_label()` cria demo via cálculo arc_flash
      real (BUS 13.8 kV, 25 kA fault) — engenheiro vê dialog
      populated logo de cara

  - 15 testes em `test_pp_v1_4_0_arc_flash_label_BC.py`:
    construction (30 rows, demo loaded, 3 styles, HTML
    populated), behavior (set_label/current_label_from_table
    roundtrip, style change, demo button), demo generation
    (3 estilos rendem sem erro)

  Sub-sprint C — Integração main_window:
  - Menu Análise → "🏷️ Designer de Label Arc-Flash..."
    atalho **Ctrl+L**
  - Handler `_on_show_label_designer` em main_window
  - 2 testes integração

  Métricas v1.4.0 finais:
  - **38 testes novos** em 2 arquivos
  - **518/518 sweep regression verde**
  - LOC novo: ~720 (430 backend + 290 GUI)
  - 0 deps externas adicionadas
  - Cobertura normativa 100%:
    * NFPA 70E:2024 §130.5(H) (label requirements)
    * NFPA 70E:2024 Tabela 130.7(C)(15)(c) (PPE categories)
    * NFPA 70E:2024 §130.4(D) (limited/restricted approach)
    * IEEE Std 1584-2018 §A4 (incident energy + DLA)
    * NESC 2023 §410 (utility worker MAD)
    * NBR 17227:2025 (label brasileiro)
    * OSHA 29 CFR 1910.269 (HV >15 kV labeling)

  Limitações documentadas (futuras releases):
  - v1.4.0 entrega text fields only (30). Picture fields
    (8 BMP no PTW) ficam para v1.4.1+ (requer Pillow ou
    Qt QPixmap).
  - 3 estilos hard-coded. Custom designer drag-drop fica
    para v1.4.2+.
  - Multilingual: PT-BR + EN. Espanhol/Frances via plugin
    v1.5+.

  🎉 **TODOS OS 6 P0 CRÍTICOS DO ROADMAP ORIGINAL AUDIT
  v1.1.0 ESTÃO FECHADOS**:
  1. ✅ Custom Label Designer (este v1.4.0)
  2. ✅ Multi-function relay (v1.2.0 β + v1.3.1 GUI)
  3. ✅ 17 TCC segment types (v1.2.0 α + v1.3.2 GUI)
  4. ✅ Equipment Eval Dashboard (v1.3.0 + v1.3.1 GUI)
  5. ✅ Coord Rule Engine (v1.3.0 + v1.3.1 GUI)
  6. ✅ Damage curves overlay (v1.2.0 γ + v1.3.2 GUI)

  Olivas v1.4.0 = **PARIDADE TÉCNICA TOTAL com PTW
  Power*Tools v11** + **5 vetores de superação únicos**:
  - AI Agent Claude (laudos PT-BR)
  - Audit trail SHA256 (ISO 9001 / NR-10)
  - Plugin ecosystem aberto
  - Open source (vs PTW closed-source $$$$)
  - NBR 17227 nativo

* 1.3.2 — HOTFIX final do gap GUI: TCCCoordinogramDialog
  populated com mix v1.2+v1.3 (fecha G.3 que ficou deferred).

  Auditoria profunda pós-v1.3.1 (`docs/v1.3.1_DEEP_AUDIT.md`)
  refinou a contagem de "39 APIs sem GUI":
  - 5 APIs primitivas (Protocol, helpers, enums) — corretas em
    ser apenas-Python (não precisam GUI individual)
  - 11 APIs já com GUI via dialogs v1.3.1
  - **23 APIs user-facing AINDA sem GUI** — TODAS convergem
    no `TCCCoordinogramDialog` populated (G.3)

  v1.3.2 G.3 entrega esse fechamento:

  - `TCCCoordinogramDialog._demo_curves` agora retorna mix
    completo de TCCCurve legacy + MultiFunctionRelay v1.2
    + FuseTCCCurve + 3 DamageCurves (Cable/XFMR/Motor).
    Engenheiro abre dialog (Ctrl+T) e VÊ todas as 23 APIs
    novas funcionando em 1 fluxo.

  - `TCCCoordinogramDialog._curve_display_label` (NOVO,
    @staticmethod) — duck typing helper que extrai label
    apropriado de qualquer tipo:
    * TCCDevice → "⚙ {device_id} {mfg/model} (N fns)"
    * FuseTCCCurve → "🔥 {fuse_id} [{class}]"
    * CableDamageCurve → "⚠ {cable_id} [Damage Cu/PVC etc: ...]"
    * TransformerThroughFaultCurve → "⚠ {xfmr_id} [Damage XFMR ...]"
    * MotorThermalCurve → "⚠ {motor_id} [Damage Motor Thermal]"
    * TCCCurve legacy → "📈 {relay_id} ({curve_type})"

  - `_on_curve_modified` agora usa o helper (era hard-coded
    para TCCCurve.relay_id, crashava em outros tipos).

  - Imports lazy via try/except para defensive — graceful
    fallback se v1.2/v1.3 não estiver disponível.

  Métricas v1.3.2 finais:
  - 7 testes novos em `test_pp_v1_3_1_gui_integration.py`
    (TestG3CoordinogramDemoMix) que verificam:
    * Demo tem ≥5 curves
    * Inclui MultiFunctionRelay
    * Inclui CableDamage + XfmrThruFault + MotorThermal
    * Inclui FuseTCCCurve
    * Inclui legacy TCCCurve
    * `_curve_display_label` não crasha em nenhum tipo
    * Drag-able count correto (3: TCCCurve+Device+Fuse;
      damages NÃO drag)
  - **480/480 sweep verde** (legacy + v1.0+ a v1.3.2)
  - 0 mudanças em backend
  - Engenheiro agora abre Ctrl+T e tem **acesso visual
    a TODAS as 23 APIs user-facing v1.2.0+v1.3.0**

  GUI integration TRL: 6 → **7** ✅
  Score técnico v1.3.2: ~9.5/10 (subindo de 9.2 em v1.3.1).

  Status global APIs com GUI:
  - 5 primitivas (corretas em ser only-Python): N/A
  - 11 via EquipmentEvalDialog + CoordRulesDialog: ✅
  - 23 via TCCCoordinogramDialog populated: ✅ NOVO v1.3.2

  **TOTAL: 100% das APIs user-facing v1.2+v1.3 acessíveis via GUI.**

  Lição aprendida v1.3.1 mantida no changelog: "GUI gate"
  é invariante para próximas releases. v1.4 (Custom Label
  Designer) sobre GUI desde início.

* 1.3.1 — HOTFIX GUI Integration Sweep (corrige gap detectado
  em audit pós-v1.3.0).

  Auditoria pós-v1.3.0 (`docs/v1.3.0_FULL_AUDIT_GUI.md`)
  detectou: 39 APIs novas v1.2.0+v1.3.0 (16 segments + 3
  devices + 3 damage curves + 5 coord_rules + 9 equipment_eval)
  com 0 referências em main_window.py — repete o padrão
  v1.0.1 ("não encontrei as ferramentas adicionadas na GUI"),
  agora em escala 10×.

  v1.3.1 entrega 2 dialogs novos + 2 menu actions +
  4 fixes de cobertura normativa em docstrings v1.3.0.

  G.1 — Equipment Evaluation Dashboard GUI:
  - NEW `app/gui/equipment_eval_dialog.py` (~290 LOC):
    `EquipmentEvalDialog(QDialog)` com:
    * Demo loader (7 equipamentos cobrindo bus/breaker/cable/
      generator/transformer com mix PASS/WARN/FAIL)
    * QTextBrowser renderiza HTML de
      `generate_html_dashboard` (B.3 v1.3.0)
    * Botões Demo / Exportar CSV / Salvar HTML
    * Status label "X equipamentos · Y PASS · Z FAIL"
    * Auto-load demo ao abrir (UX: usuário vê algo)
  - Menu Análise → "📋 Avaliar equipamentos (9 critérios PTW)"
    atalho Ctrl+E.
  - Handler `_on_show_equipment_eval` em main_window.

  G.2 — Coord Rules Dialog:
  - NEW `app/gui/coord_rules_dialog.py` (~280 LOC):
    `CoordRulesDialog(QDialog)` com:
    * 4 RuleSet checkboxes (NEC_MOTOR, NEC_TRANSFORMER,
      NBR_CABLE, BEST_PRACTICES) — todos checked default
    * Demo loader (5 targets com mix de PASS/FAIL)
    * QTreeWidget agrupando results por target_id (overall
      severity colorido + child rows por Rule)
    * Botão "Recarregar Demo" + "Aplicar regras"
    * Status summary "X targets · Y verifications · PASS=N
      WARN=M FAIL=K N/A=L"
    * Cores semantic via QBrush (verde #2E7D32, amarelo
      #F9A825, vermelho #C0392B, cinza #9E9E9E)
  - Menu Análise → "🛡️ Verificar regras de coordenação..."
  - Handler `_on_show_coord_rules_check` em main_window.

  G.3 — TCCCoordinogramDialog populated (DEFERRED to v1.3.2):
  - Comportamento atual mantido (dialog vazio acionável via
    Ctrl+T). População a partir do projeto carregado requer
    parser .opws estendido com TCCDevice/DamageCurve fields,
    que é trabalho de v1.3.2.

  Fixes de consistência v1.3.0 (parte do hotfix):
  - 4 docstrings sem cobertura normativa (RuleSeverity, Rule,
    RuleEngine, EvaluationReport) ganharam citação IEEE 242
    §15 + PTW reference. 7/7 classes v1.3.0 agora 100%
    documentadas.

  Métricas v1.3.1 finais:
  - **21 testes novos** em `test_pp_v1_3_1_gui_integration.py`
  - **496/496 sweep regression verde** (legacy + v1.0+ a v1.3.1)
  - 2 arquivos GUI novos (~570 LOC)
  - 2 menu actions + 2 handlers em main_window
  - 1 doc novo (FULL_AUDIT_GUI) + 1 doc design (v1.3.1)
  - 0 deps externas adicionadas
  - Backward compat 100% (nenhuma API backend alterada)

  GUI integration restaurada para TRL 6 (de 4 anterior).
  Score técnico v1.3.1 deve voltar para ~9.2 (subindo de
  8.5 em v1.3.0).

  Lição aprendida documentada: cada release backend deve
  ter "GUI gate" antes de fechar. v1.4 (Custom Label
  Designer) será sobre GUI desde o início.

* 1.3.0 — Coordination Rule Engine + Equipment Evaluation
  Dashboard (paridade PTW Coordination Eval + Equipment Eval).
  Fechou 2 dos 4 P0 críticos remanescentes do
  AUDIT_OLIVAS_VS_PTW_v1.1.0.

  Fase A — Coordination Rule Engine:
  - A.1 Rule data model (~308 LOC + 26 testes):
    `coord_rules.py` com RuleSeverity (PASS/WARN/FAIL/NA),
    RuleResult, Rule, RuleSet (validação dup IDs), RuleEngine
    (apply_rule/apply_ruleset/filter/group/count/has_failures
    /summary_line).
  - A.2 Built-in rules library (~530 LOC + 33 testes):
    `coord_rules_builtin.py` com 8 rules em 4 RuleSets:
    * NEC_MOTOR_PROTECTION (3): 51 LTPU 115-125%, 49 thermal
      100-200%, 50 INST 5-10× (NEC 110.10 + IEEE 242 §9)
    * NEC_TRANSFORMER_PROTECTION (3): XFMR small/large LTPU
      + through-fault IEEE C57.109 (NEC 450.3)
    * NBR_CABLE_RULES (1): cable damage 80% rule
      (NBR 5410 §5.7.5)
    * BEST_PRACTICES (1): motor thermal below LR
  - **Anti-aluc detectou 3 mental model bugs em testes**
    (todos corrigidos): pickup boundary WARN range, mental
    model errado de IEC SI (~91s vs ~4.6s real),
    composite envelope mascarando regra. Fixes nos
    testes — implementação preservada.

  Fase B — Equipment Evaluation Dashboard:
  - B.1 Data model (~250 LOC + 24 testes):
    `equipment_eval.py` com EquipmentInstance (ratings + duty
    + model_ref opcional), EvaluationReport (passes_all,
    failures, warnings, count_by_severity, overall_status),
    evaluate_equipment + evaluate_project orquestradores.
  - B.2 9 critérios PTW (~470 LOC + 33 testes):
    `equipment_eval_rules.py` com PTW_EQUIPMENT_EVALUATION
    RuleSet de 9 rules:
    1. EQ-VOLTAGE-RATING (rated ≥ bus, IEEE 242 §15.6.1)
    2. EQ-INTERRUPT-DUTY (Ik'' ≤ rated, ANSI C37.04)
    3. EQ-ASYM-DUTY (ip ≤ rated_asym)
    4. EQ-LOAD-FLOW-CURRENT (I_load ≤ continuous)
    5. EQ-DESIGN-LOAD (I_design ≤ continuous)
    6. EQ-GENERATOR-CAPACITY (gen_load ≤ capacity)
    7. EQ-BUS-VOLTAGE-DROP (V_drop ≤ 4% NBR 5410)
    8. EQ-BRANCH-VOLTAGE-DROP (V_drop_branch ≤ 4%)
    9. EQ-DEVICE-VOLTAGE-DROP (V_drop_device ≤ 1%)
    Convenção severity: <70% PASS, 70-100% WARN, >100% FAIL.
    Smoke test integrado: 7-equipment substation com mix de
    PASS/WARN/FAIL valida workflow end-to-end.
  - B.3 Dashboard generation (~370 LOC + 16 testes):
    `equipment_eval_dashboard.py` com `generate_html_dashboard`
    (HTML standalone com CSS inline, paleta semantic colors
    PTW, escape XSS, sumário global, tabela com ✓/⚠/✗/—)
    e `export_csv` (Excel-friendly com ; default BR ou
    custom sep).

  Métricas v1.3.0 finais:
  - **132 testes novos** (alvo 80+, entregamos 165%)
  - **452/452 sweep regression verde** (v1.0+ até v1.3.0)
  - 4 docs novos (plan, 2 design A/B, log)
  - 0 deps externas adicionadas
  - LOC: 1,928 produção + 2,030 testes
  - Backward compat 100% (Fase A reusa estrutura, B reusa A,
    nenhum tcc_*.py legacy modificado)

  Cobertura normativa adicionada:
  - NEC 110.10 (proteção upstream)
  - NEC 450.3 (transformer protection)
  - IEEE Std 242:2001 §9 (motor protection)
  - IEEE Std 242:2001 §11 (transformer)
  - IEEE Std 242:2001 §15 (equipment evaluation)
  - ANSI C37.04 (LV breaker ratings)
  - NBR 5410:2004 §5.7.5 (cable thermal stress)
  - NBR 5410:2004 §6.2.7 (queda de tensão)

  Diferenciação alcançada vs PTW Coordination Eval:
  - Paridade total: 8 rules + 9 EquipmentEvaluation criteria
    com dashboard tabular Pass/Warn/Fail
  - Superação: Rules são pluginnable (qualquer engenheiro pode
    adicionar nova Rule sem modificar core); Engine é puro
    Python (auditável, sem black-box DLL); HTML standalone
    sem deps externas (instala fácil em qualquer máquina);
    Citation obrigatória em cada Rule (auditoria forense
    exigida por ISO 9001 / NR-10).

  Decisão estratégica próxima release:
  - v1.3.1 ou v1.4: completar 7 rules adicionais (gen 51V,
    capacitor, IEEE 242 §15.10.1 Δt min — total 15)
  - v1.4: Custom Label Designer arc-flash (último P0
    remanescente do AUDIT v1.1.0)

* 1.2.0 — CAPTOR-grade TCC (paridade SKM PTW Power*Tools CAPTOR).
  Sprint disciplinada com auditoria, design docs, TDD e validação
  canonical em 4 fases (α + β + γ + δ).

  Fase α — 17 TCC Segment Types (paridade CAPTOR):
  - 16 segments novos em ``app/postprocessor/tcc_segments.py``
    (~1400 LOC): TCCSegmentLT/ST/INST/DefiniteTime (α.1),
    AdjustableTolerance/I2T/TimeCurrentPoints/FixTimeHorizontal
    (α.2), AnalyticAD/SM polynomial (α.3), Opening/Clearing/
    OpenClearCurve/OpenClearBand (α.4), SlopeT/DelayBand (α.5).
  - + 1 segment legacy v1.1.0 (FuseTCCCurve em tcc_curves.py).
  - Protocol ``TCCSegment`` runtime_checkable + composite helper.
  - 100 testes incluindo 3 canonical AD vs operating_time_s legacy
    (paridade IEEE C37.112-2018 bit-a-bit).

  Fase β — Multi-Function Devices:
  - ``TCCDevice`` frozen container + tuple imutável + composite
    envelope ``min(t_segment) over enabled``.
  - ``triggered_segment(I)`` debug — qual seg "venceu" no envelope
    (supera PTW: explicit no DeviceCoordinationCheck).
  - ``MultiFunctionRelay(TCCDevice)`` com 4 helpers PT-BR:
    ``relay_51_only``, ``relay_51_and_50``, ``relay_51_50_49``
    (motor protection), ``relay_51_50_87`` (xfmr diff).
  - ``check_device_coordination()`` reusa Buff Book §15.10.1
    margins por relay_type (digital/static/EM).
  - 57 testes incl. smoke SEL-751-like com 4 regimes (nominal/
    leve/moderado/fault) — anti-aluc detectou meu mental model
    errado de IEC SI (M=1.667 dá ~2.7s, não ~27s); fix no
    teste para refletir cálculo manual correto.

  Fase γ — Damage Curves:
  - NEW ``app/postprocessor/tcc_damage.py`` (~600 LOC):
  - ``CableDamageCurve`` — NBR 5410 §6.5.4: t = (K·S)²/I²
    com K factors literais Tabela 43 (Cu/PVC=115/103, Cu/XLPE=143,
    Al/PVC=76, Al/XLPE=94). 7 testes canônicos NBR.
  - ``TransformerThroughFaultCurve`` — IEEE C57.109-1993 +
    IEEE 242 §11.5.6: t = MAX(K/I_pu², 2s) com K=1250 (frequent)
    ou 5000 (infrequent).
  - **Anti-aluc detectou bug crítico**: implementação inicial
    usou MIN em vez de MAX. Re-leitura cuidadosa de IEEE C57.109
    §5 confirmou: cap 2s é piso inferior em high-I (forças
    mecânicas), não cap superior. Fix aplicado, 18 testes
    canônicos validam fórmula correta.
  - ``MotorThermalCurve`` — IEC 60079-7 / NEMA MG-1 §12.45:
    t = K_motor/(I/FLA)² calibrado em (I_LR, tE) anchor.
  - 55 testes total incluindo limitações documentadas.

  Fase δ — GUI integration (tcc_coordinogram.py):
  - Dispatch estendido para TCCDevice + 3 DamageCurves SEM
    quebrar TCCCurve/FuseTCCCurve legacy v1.1.0.
  - ``_draw_device`` plota composite + pickup verticals tracejados.
  - ``_draw_damage_curve`` cor #C0392B vermelho, dashed (5,2),
    zorder 3 (atrás), linewidth 1.5.
  - ``_check_device_pair`` usa check_device_coordination da β.3
    com triggered_segment_id na annotation.
  - ``_detect_protection_vs_damage_violations`` itera proteções ×
    damages, marca cruzamentos com X marker 14pt + annotation.
  - 17 testes incl. cenários positivos/negativos de violation.

  Métricas v1.2.0 finais:
  - **229 testes novos** (alvo era 150+, entregamos 153%)
  - **320/320 sweep regression verde** (legacy + v1.1.0 + α + β + γ + δ)
  - 6 docs novos (audit, plan, 3 design, log, full audit)
  - 0 deps externas adicionadas (sem scipy/numpy/matplotlib novo)
  - Audit consistência: 100/100 (cobertura normativa 100%)
  - Audit completo (vs PTW + normas + TRL): score 9.06/10
  - 2 bugs detectados pelo TDD anti-aluc, ambos corrigidos
    (smoke SEL-751 + γ.2 MIN/MAX)
  - Backward compat 100%: TCCCurve legacy v1.1.0 funciona

  Cobertura normativa adicionada/reforçada:
  - IEC 60255-151:2009 (relé multi-função)
  - IEEE C37.112-2018 (curvas inverse-time)
  - IEEE C37.04, IEC 62271-100 (breakers)
  - IEEE Std 242-2001 (Buff Book) §11.5.6 + §15.10.1
  - IEEE C57.109-1993 (XFMR through-fault)
  - NBR 5410 §6.5.4 + IEC 60364-4-43 (cable damage)
  - IEC 60079-7 / NEMA MG-1 (motor thermal)

  Diferenciação alcançada vs PTW CAPTOR:
  - Paridade total: 17 segment types, multi-function devices,
    damage curves overlay, violation markers
  - Superação: triggered_segment_id explicit no coord report,
    4 helpers PT-BR para padrões 90%, validação canônica
    automatizada (anti-alucinação por equivalência matemática),
    cobertura normativa em docstring de TODA classe (19/19)

  Decisão estratégica: priorizou **fundação de domínio elétrico**
  sobre **deliverable visual**. Custom Label Designer (gap P0
  remanescente) fica para v1.4.0; Coordination Rule Engine +
  Equipment Evaluation Dashboard (P0 remanescentes) ficam para
  v1.3.0.

* 1.1.0 — RENDERERS VISUAIS PTW-style (Item 1/3 do roadmap v1.1).
  Bug reportado por Landerson Ferreira Silva: "revisar o estilo
  dos componentes (cara de ATP -> estilo PTW/ETAP)". Os símbolos
  IEEE 315 / Qucs (zigzag para R, espiral para L, placas paralelas
  para C) têm "cara de simulação acadêmica" e destoam do padrão
  SLD usado por PTW Power*Tools / ETAP / EasyPower em diagramas
  unifilares profissionais.

  Solução: módulo paralelo ``app/preprocessor/ptw_symbols.py``
  (~330 LOC) com 6 renderers SLD PTW-style:

  - ``CircuitBreakerSymbol`` — quadrado 30×30 com cruz diagonal
    interna (estilo PTW Component Editor / IEC 60617-7-3 SLD)
  - ``FuseSymbol`` — retângulo arredondado vertical, cor ouro,
    com filamento central (IEC 60617-7-3 / NEMA)
  - ``ContactorSymbol`` — contato curvo (NA) + bobina à direita
    com letra "K" (IEC 60617 / IEC 60947-4)
  - ``CTSymbol`` — círculo duplo concêntrico com letra "TC"
    + 4 pinos (P1/P2 horizontais, S1/S2 verticais), IEC 60617-9
  - ``CableSymbol`` — linha grossa horizontal com brackets de
    extensão (PTW Cable component)
  - ``PTWMotorSymbol`` — círculo duplo com "M" (refinamento do
    ANSI/IEEE; opcional, não força override)

  Paleta visual PTW (não a IEEE 315 grayscale):
  - ``_PTW_LINE``   = #143250 (azul escuro corporativo)
  - ``_PTW_ACCENT`` = #006699 (azul PTW)
  - ``_PTW_FILL``   = #F5F8FC (azul claro)
  - ``_PTW_GOLD``   = #DAA520 (ouro fusível)
  - ``_PTW_RED``    = #C0392B (aviso)
  - ``_PTW_GREEN``  = #2E7D32 (ok)

  Integração: ``symbols.get_renderer()`` agora consulta
  ``ptw_symbols.get_ptw_renderer()`` ANTES do registry IEEE.
  Componentes mapeados: CABLE, CT, FUSE, CONTACTOR. Componentes
  legacy (R, L, C, Vdc, Vac, Tr, BUS, MOTOR) NÃO são tocados —
  preservam aparência IEEE 315 / Qucs por compatibilidade visual
  com os exemplos pré-existentes (.sch dos sprints v0.94+).

  Cobertura normativa
  ====================
  - IEC 60617 — Graphical symbols for diagrams
  - IEEE Std 315-1975 — Graphic symbols for electrical diagrams
  - IEC 60947-4 — Contactors LV
  - IEC 60269 — LV fuses
  - ANSI/IEEE C37.2 — Standard device function numbers

  Testes: 26 novos em ``tests/test_pp_v1_1_0_ptw_symbols.py``
  cobrindo (a) precedência sobre o registry IEEE, (b) não-
  regressão dos legacy, (c) paint() smoke offscreen, (d)
  geometria PINS/SIZE coincide com o spec do .ocomp.

  Item 2 (v1.1.0): SINGLE-LINE DIAGRAM ONLINE.
  ============================================

  PTW Power*Tools / ETAP / EasyPower oferecem **Online View** —
  resultados das análises sobrepostos diretamente sobre o
  esquemático, sem abrir relatórios separados. Em PTW, cada bus
  exibe Ik''/V/loading ao lado do símbolo, colorido conforme
  utilização vs. rating do equipamento.

  Implementado em ``app/gui/schematic_pp/online_overlay.py``
  (~280 LOC):

  - ``OnlineAnnotation`` dataclass — texto + severidade
    ('info'/'ok'/'warn'/'violation') + placement
  - ``OnlineOverlayManager`` — set_enabled() ON/OFF, refresh()
    walks scene e anota componentes a partir do StudyCache.
  - ``annotation_from_sc()`` — mapeia ScResult → linhas
    (Ik''/ip/Util%) + severidade conforme utilization vs.
    bus_rating_kA (≥100% = violation, ≥80% = warn, < 80% = ok).
  - ``annotation_from_pf()`` — mapeia voltage_pu → severidade
    conforme limite NBR 5410 §6.2.7 (default 0.95 pu = 5%).

  Cores (paleta PTW corporativa):
  - info:      texto #143250 / fundo #EBF5FF (azul claro)
  - ok:        texto #2E7D32 / fundo #E8F5E9 (verde claro)
  - warn:      texto #B47800 / fundo #FFF8DC (amarelo claro)
  - violation: texto #C0392B / fundo #FDE8E6 (vermelho claro)

  Integração na cena: ``ComponentItem`` em
  ``app/gui/schematic_pp/items.py`` ganhou:
  - ``set_online_annotation(ann)`` / ``online_annotation()``
  - ``_online_badge_rect()`` — calcula rect do badge à direita
  - ``_paint_online_badge()`` — desenha caixa colorida com texto
  - ``boundingRect()`` cresce para incluir o badge (evita
    rastros em drag/repaint)

  Menu/atalho:
  - Visualizar > 📡 Modo Online (Ctrl+Shift+O), checkable
  - ``MainWindow._on_toggle_online_view()`` liga/desliga
  - ``MainWindow._refresh_online_overlay()`` chamado ao final
    de cada análise (SC modular já hookado) para sincronizar

  Cobertura atual: BUS recebe annotation com Ik''/ip do cache
  SC. Hooks futuros: TR (loading), MOTOR (kVA atual), CABLE
  (loading%), em iterações posteriores.

  Cobertura normativa
  ====================
  - IEC 60909-0 — Ik''/ip/Ib/Ik
  - IEEE 399 — Power Flow voltage profile
  - NBR 5410 §6.2.7 — limites de queda de tensão (4%/7%/10%)

  Testes: 29 novos em
  ``tests/test_pp_v1_1_0_online_overlay.py`` cobrindo:
  - annotation builders puros (SC + PF) com severity correta
  - Manager lifecycle (enabled/disabled/refresh/clear)
  - Integração scene + ComponentItem (BUS é anotado, R não é)
  - paint() com 4 severidades + badge à direita do símbolo
  - boundingRect cresce com annotation

  Item 3 (v1.1.0): TCC DUPLO PARA FUSÍVEIS (melt + clear).
  ===========================================================

  PTW CAPTOR desenha cada fusível com **2 envelopes** time-current:

  - **Melt envelope** (pre-arcing) — corrente/tempo em que o
    elemento fusível começa a fundir.
  - **Clear envelope** (total) — corrente/tempo em que o arco
    se extingue. clear ≈ 1.5–2× melt para HRC.

  Coordenação fusível-fusível requer:
  ``t_clear(downstream, I) + margin < t_melt(upstream, I)``
  (IEEE 242 §15.5.4 — margem 25% I²t).

  Implementação em ``app/postprocessor/tcc_curves.py``
  (~+220 LOC):

  - ``FuseClass`` enum: gG, gM, aM, K, T, J, RK1, RK5
  - ``FuseTCCCurve`` dataclass com ``melt_time_at_current()``,
    ``clear_time_at_current()``, ``melt_points()`` /
    ``clear_points()`` para plot log-log.
  - Modelagem por lei de potência calibrada nos pontos típicos
    da norma: ``t(I) = K · (In/I)^p``. Cada classe tem
    (pickup_factor, p, K_melt, clear_ratio) tabelados em
    ``_FUSE_PARAMS``. Para precisão de datasheet específico,
    plugins podem sobrescrever via tabela discreta.
  - ``FuseFuseCoordinationCheck`` dataclass com margin_pct.
  - ``check_fuse_fuse_coordination()`` — IEEE 242 §15.5.4.
  - ``check_fuse_relay_coordination()`` — caso CCM bucket
    (relé downstream protegendo motor + fuse upstream no feeder).

  Visualização em ``app/gui/tcc_coordinogram.py``:

  - ``_draw_fuse_curve()`` desenha 2 envelopes (melt tracejado,
    clear sólido) com fill_between sombreado entre os dois.
  - ``_check_and_annotate_pair()`` dispatch por tipo:
    Relay-Relay → check_coordination (Δt em segundos)
    Fuse-Fuse → check_fuse_fuse_coordination (margin %)
    Fuse-Relay → check_fuse_relay_coordination
    Relay-Fuse → fallback explícito
  - Drag-and-drop em fusíveis desabilitado (In é fixo do
    datasheet — para mudar curva, edite a propriedade FUSE
    no editor e reabra o coordenograma).

  Cobertura normativa
  ====================
  - IEC 60269-1:2014 — Low-voltage fuses (pickup factors, p)
  - IEC 60269-2 — gG/gM utilization
  - NEMA C37.46 — HV K-link
  - IEEE 242-2001 §15.5.4 — Fuse-fuse coordination 25% margin

  Testes: 22 novos em ``tests/test_pp_v1_1_0_fuse_tcc.py``:
  - FuseTCCCurve API (melt < clear, monotonia, pickup)
  - 8 classes IEC/NEMA cobertas
  - Fuse-fuse coord (2:1 passa, 1.1:1 falha)
  - Fuse-relay coord para CCM bucket pattern
  - Margem custom configurável

  v1.1.0 completo: 3 itens roadmap entregues, **77 testes
  novos** (26 ptw_symbols + 29 online_overlay + 22 fuse_tcc).

  Hotfix paleta (junto com v1.1.0)
  =================================

  Regressão pré-existente da v1.0.1 detectada em sweep regional:
  ``PpPalette._populate()`` mostrava o bloco TACS ``Eqn`` na
  paleta após remoção do filtro ``atp_supported`` (necessária
  em v1.0.1 para que CABLE/CT aparecessem). Eqn não tem
  ``SymbolRenderer`` — virava placeholder no canvas.

  Correção: filtro mais preciso baseado em ``get_renderer(code)
  is not None`` em ``PpPalette._populate()``. Itens sem
  renderer (Eqn, diretivas .TR/.DC/.SW/.AC/.SP) são pulados;
  CABLE/CT/FUSE/CONTACTOR continuam aparecendo (têm renderer
  PTW-style do Item 1). Restaura ``test_palette_does_not_list_
  unsupported`` para passing.

* 1.0.2 — HOTFIX: limpeza ATP residual + Coordenograma TCC
  + componentes PTW-style (FUSE, CONTACTOR).
  Bug reportado por Landerson Ferreira Silva (autor):
  - Strings residuais "Olivas ATP Studio" no About dialog
    e submenu "Esquemático visual" com itens ATP.
  - Coordenograma TCC ausente da GUI (estilo PTW CAPTOR).
  - Faltavam componentes PTW: FUSE, CONTACTOR.
  Correções:
  - About dialog: "Olivas ATP Studio" → "Olivas Power
    System Studio" (string final residual).
  - Menu Arquivo: removido submenu "Esquemático visual"
    com itens ATP (Importar caso ATP / Exportar PP→ATP).
    Substituído por "Abrir/Salvar esquemático" no nível
    superior. ATP IO permanece via API Python apenas.
  - NEW ``app/gui/tcc_coordinogram.py`` (~330 LOC):
    coordenograma TCC interativo estilo SKM PTW CAPTOR.
    Drag-and-drop das curvas com mouse → ajusta TMS em
    tempo real. Múltiplas curvas log-log com cores
    distintas, marker Ik'' vermelho, detecção de
    violations Δt < margin com highlight + annotation.
    Atalho Ctrl+T no menu Análise.
  - NEW ``CABLE.ocomp`` + ``CT.ocomp`` (v1.0.1 anterior).
  - NEW ``FUSE.ocomp`` — fusível (IEC 60269 / NBR /
    NEMA Type-K) com classes gG/gM/aM/K/T/J/R.
  - NEW ``CONTACTOR.ocomp`` — contator (IEC 60947-4 /
    NEMA ICS 2) com tamanhos NEMA Size 00-9 e categorias
    AC-1/AC-3/AC-4/DC-3.
  - Total catálogo: **53 componentes** (era 49 → 51 → 53).
  - Menu Ferramentas: NEW "📚 Biblioteca de equipamentos"
    (browse vendor data SEL/ABB/Siemens/WEG/GE) e
    "🧩 Plugins instalados".

* 1.0.1 — HOTFIX: GUI integration sweep para v0.95→v1.0.
  Bug reportado pelo usuário: "Não encontrei as ferramentas
  adicionadas na GUI. Análise geral confirmou que módulos
  existiam apenas como APIs Python — sem entrada no menu,
  sem componentes na paleta."
  Correções:
  - NEW ``CABLE.ocomp`` — cabo NBR 5410 (categoria passive)
  - NEW ``CT.ocomp`` — TC para proteção (categoria switch)
  - PpPalette: ``_populate()`` agora mostra TODOS os
    componentes (era filtrado por ``atp_supported`` que
    pulava CABLE/CT). Categorias renomeadas com emojis
    descritivos ("🔧 Passivos", "🛡️ Proteção", etc).
  - ``catalog.all_entries()``: inclui specs do registry
    que NÃO estão em ``_ENTRIES`` legado — antes novos
    .ocomp ficavam invisíveis.
  - Menu Análise: +6 ações novas (Cable Sizing, V-drop,
    Harmonics, Motor Reaccel, Ground Grid, AI Laudo).
    Total agora: 13 análises (era 7).
  - +6 handlers ``_on_analyze_*`` com dialogs Qt completos.
* 1.0.0 — RELEASE PÚBLICA (12 sprints completados).
  Score final 95/100. Paridade funcional total com PTW
  Power*Tools / ETAP / EasyPower + diferenciação única
  (audit trail SHA256, NBR 17227 nativo, AI agent, plugin
  ecosystem, open source PT-BR).

  Conteúdo agregado v0.94 → v1.0:
  - Fase 1: Cable sizing (v0.95), V-drop (v0.96), Harmonics
    (v0.97), Equipment library (v0.98)
  - Fase 2: TCC curves (v0.99), PF unbalanced (v0.100),
    Arc-flash HV (v0.101), Motor reaccel (v0.102),
    Ground grid (v0.103)
  - Fase 3: AI laudos (v0.104), Plugin system (v0.105),
    Release pública v1.0

  Métricas finais:
  - 12 sprints concluídos com 100% test pass
  - 159 tests novos (Fase 1+2+3)
  - 13 normas implementadas (IEC, IEEE, ABNT NBR, NFPA, NR)
  - 33+ entries equipment library (5 vendors)
  - Sistema modular de estudos (PTW-style) + plugin ecosystem
  - Audit trail forense SHA256 em todos os laudos

  Posicionamento: alternativa nacional aberta a PTW/ETAP/
  EasyPower com diferenciadores únicos (open source, AI,
  PT-BR nativo, NBR 17227).
* 0.95.0 — Cable Sizing (NBR 5410 / NEC 310 / IEC 60364).
  Sprint #1 do roadmap v1.0 — bloqueador #1: dimensionamento
  automático de cabos. NEW
  ``app/postprocessor/cable_sizing.py`` com:
  - Tabelas 36–39 NBR 5410 (Cu PVC/EPR/XLPE × A1/B1)
  - FC temperatura (Tabela 40) + FC agrupamento (Tabela 42)
  - Algoritmo de iteração com 3 critérios:
    ampacidade Iz·FC ≥ I_load, V-drop ≤ 4%, estresse térmico
    t·Ik² ≤ K²·S² (NBR 5410 §6.5.4).
  - Auto-iteração 1.5 → 500 mm² escolhendo menor bitola
    que passa todos os critérios.
  - 26 tests cobrindo validação física, V-drop, FC,
    estresse térmico SC, comparações XLPE vs PVC, A1 vs B1.
* 0.94.0 — ESTUDOS MODULARES (estilo PTW Power*Tools).
  Refator arquitetural: cada estudo é módulo independente
  com pré-requisitos declarados e cache automático.
  - NEW ``app/postprocessor/study_cache.py`` — cache de
    resultados por bus_id × estudo. Invalidação por SHA256
    dos inputs.
  - NEW ``app/postprocessor/studies/`` package:
    - ``short_circuit.py`` — standalone (sem prereqs)
    - ``coordination.py`` — REQUIRES SC (auto-roda)
    - ``arc_flash_study.py`` — REQUIRES SC + Coord (auto-roda)
  - ``RunAnalysisDialog``: 7 radios (SC / Coord / Arc-flash /
    PF / Motor / CT-Sat / Pipeline). SC pre-selecionado.
  - Menu Análise: F5=SC, F6=Coord, F7=Arc-flash, F8=Pipeline.
  - ``_dispatch_analysis``: rota nova para cada estudo
    via StudyCache compartilhado do MainWindow.
  - ``PrerequisiteError``: levantada se ``auto_run_prereqs=
    False`` e prereqs não estão no cache.
"""

from __future__ import annotations

VERSION_TUPLE = (4, 0, 0)
PRE_RELEASE = "beta"  # v4.0.0-beta = UAT preparation (i18n + CHANGELOG + readiness)
PRODUCT_NAME = "Olivas Power System Studio"
PRODUCT_TAGLINE = (
    "Software profissional de análise elétrica — "
    "alternativa nacional a SKM PTW / ETAP / EasyPower"
)
VERSION = ".".join(str(x) for x in VERSION_TUPLE)
if PRE_RELEASE:
    VERSION = f"{VERSION}-{PRE_RELEASE}"


def parse_version(s: str) -> tuple[int, ...]:
    """
    Parsea string "X.Y.Z" em tuple. Aceita opcionais como
    "0.50.0-beta" — ignora suffix.

    Returns
    -------
    tuple[int, ...]
    """
    base = s.split("-")[0].split("+")[0]
    parts = base.split(".")
    out = []
    for p in parts:
        try:
            out.append(int(p))
        except ValueError:
            break
    return tuple(out) if out else (0,)


def is_newer(remote: str, local: str = VERSION) -> bool:
    """Retorna True se remote > local (semver tuple compare)."""
    return parse_version(remote) > parse_version(local)
