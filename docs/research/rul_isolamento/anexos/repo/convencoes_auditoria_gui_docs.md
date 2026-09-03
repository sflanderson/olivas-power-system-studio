# Mapa da área `convencoes_auditoria_gui_docs` — Olivas Power System Studio

Repositório: `/home/user/olivas-power-system-studio` (HEAD `26d9248`, branch `claude/isolamento-degradacao-monitoramento-dr900x`, árvore limpa; nada foi modificado). Versão declarada: `VERSION_TUPLE = (4, 0, 0)` + `PRE_RELEASE = "beta"` → `"4.0.0-beta"` [REPO: app/core/version.py:1959-1968].

Objetivo do mapa: consolidar as convenções transversais que QUALQUER novo módulo do produto deve cumprir — auditabilidade (SHA256, normas, limitações), laudo HTML/PDF, gating comercial, acessibilidade GUI ("7ª garantia"), i18n, versionamento, CHANGELOG, documentos canônicos de sessão, testes, CI, dependências e empacotamento — para que um futuro módulo de prognóstico de degradação de isolamento (RUL) de motores de indução MT entre no repositório sem violar nenhuma regra existente.

Legenda epistemológica (usada em todo o documento):

- **[REPO: caminho:linha]** — fato verificado por leitura do arquivo na linha citada;
- **[CÁLCULO PRÓPRIO]** — contagem/experimento executado nesta sessão (comando indicado);
- **[INFERÊNCIA]** — conclusão do mapeador a partir dos fatos;
- **[HIPÓTESE]** — proposta de projeto ainda não validada com o autor do repositório.

Arquivos lidos integralmente: `app/postprocessor/audit_trail.py` (424 l.), `app/commercial/feature_gates.py` (309 l.), `app/i18n/__init__.py` (180 l.), `tests/conftest.py` (42 l.), `requirements.txt` (8 l.), `Dockerfile` (43 l.), `docker-compose.yml` (37 l.), `.github/workflows/lint.yml` (70 l.), `.github/workflows/test.yml` (109 l.), `CHANGELOG.md` (197 l.), `docs/SESSION_HANDOFF.md` (303 l.), `docs/CONTEXT_PRESERVATION_PROTOCOL.md` (207 l.), `docs/PTW_TOTAL_PARITY_DIRECTIVE.md` (289 l.), `docs/SKIPPED_BACKLOG.md` (194 l.), `docs/v3.8.0_HANDOFF.md`, `docs/v4.0.0-beta_HANDOFF.md`, `docs/v3.1.0_GUI_AUDIT.md`, `README.md`, `ROADMAP.md`, `build/README.md`, `build/runtime_hook_community.py`. Lidos por trechos: `app/postprocessor/report_html.py` (1074 l.; faixas 1-110, 505-760, 1040-1074), `app/postprocessor/report_pdf.py` (1173 l.; 1-130, 127-300, 895-970, 1054-1173), `app/gui/main_window.py` (4348 l.; 170-200, 380-700, 885-935, 1060-1100, 2403-2470, 2835-2960, 3070-3110, 3245-3300, 3340-3510), `app/gui/analysis_dialogs.py` (1065 l.; 1-120, 661-800, 904-1065), `app/core/version.py` (1993 l.; 1-80, 1890-1993), `app/postprocessor/study_cache.py`, `app/postprocessor/studies/__init__.py`, `app/postprocessor/studies/short_circuit.py` (1-60), `app/postprocessor/reliability_monte_carlo.py` (1-70, 225-290), `app/gui/reliability_dialog.py` (outline), `app/gui/run_analysis_dialog.py` (outline), `app/gui/plot_dock_refresh.py` (1-70), `app/gui/schematic_pp/datablock_binder.py` (195-260), `app/plugins/registry.py` (1-60), `app/plugins/manifest.py` (1-80), `app/core/logging_config.py` (1-60), `docs/v1.7.0_MASTER_PROTOCOL.md` (1-120), `docs/PTW_SURPASSING_MATRIX.md` (1-60, l. 288), `docs/MONETIZATION_PLAN.md` (18-50), `docs/LICENSING.md` (grep), `docs/THIRD_PARTY_NOTICES.md` (1-80), `CONTRIBUTING_ATP_STUDIO.txt` (70-100, 215-240), e os testes `tests/test_pp_v0_92_audit_trail.py`, `tests/test_pp_v4_1_0_commercial_sprint1.py`, `tests/test_pp_v4_0_0_beta_readiness.py`, `tests/test_pp_v4_0_0_alpha_milestone.py`, `tests/test_pp_v3_8_0_reliability_mc.py`, `tests/test_pp_v3_6_0_reliability.py`, `tests/test_pp_v3_3_0_unbalanced_dialog.py`, `tests/test_pp_v2_0_0_docker.py`, `tests/test_pp_v0_31_0_ci.py`, `tests/test_pp_report_pdf.py` (outline/trechos).

---

## 1. Inventário de arquivos e símbolos

### 1.1 `app/postprocessor/audit_trail.py` (424 linhas) — primitivas de auditabilidade

| Símbolo | Assinatura / conteúdo | Linhas |
|---|---|---|
| Docstring de filosofia | 4 princípios de laudo defensável: identidade do cálculo (versão + hash + timestamp), rastreabilidade de norma, responsabilidade técnica (CREA/ART), limitações declaradas | 25-35 |
| `from app.commercial.feature_gates import Feature, requires_feature` | dependência do gating | 63 |
| `STANDARDS_CATALOG: dict[str, str]` | 13 chaves: `"IEC 60909-0"`, `"IEC 60909-1"`, `"IEEE 141"`, `"IEEE 242"`, `"IEEE 399"`, `"IEEE 1584"`, `"IEC 60255"`, `"NBR 17227"`, `"NBR 5410"`, `"NBR 14039"`, `"NBR 5419"`, `"NFPA 70E"`, `"NR-10"` → título completo | 73-87 |
| `citation(standard, section=None, equation=None, extra=None) -> str` | prefixo curto = `title.split(" — ")[0]`; norma não catalogada usa o nome literal (l. 113-115) | 90-127 |
| `compute_input_checksum(payload: Any) -> str` | `_to_jsonable` → `json.dumps(sort_keys=True, default=str)` → SHA256 hex (64 chars) | 135-161 |
| `_to_jsonable(obj)` | primitivos, dataclass (`dataclasses.asdict`), dict, list/tuple, set (ordenado), complex → `[re, im]`, fallback `repr` | 164-191 |
| `@dataclass AuditHeader` | campos `report_kind, software_name, software_version, timestamp_iso, input_checksum, standards_applied: list[str], responsible_engineer="", crea_number="", art_number="", notes=""`; métodos `to_text()` (221-257) e `to_html()` (259-291) | 199-291 |
| `@requires_feature(Feature.AUDIT_TRAIL_SHA256)` `make_audit_header(report_kind, inputs, standards_applied, *, responsible_engineer="", crea_number="", art_number="", notes="", software_name="Olivas Power System Studio") -> AuditHeader` | lê `VERSION` de `app.core.version` (311-314), `datetime.now().isoformat(timespec="seconds")` (320), `compute_input_checksum(inputs)` (321) | 294-327 |
| `KNOWN_LIMITATIONS: dict[str, str]` | 7 chaves: `sc_ib_far_only`, `sc_method_b_kappa`, `arc_flash_lv_only`, `arc_flash_3p_only`, `pf_positive_seq_only`, `pf_no_q_limits`, `coord_no_auto_dt_min` [CÁLCULO PRÓPRIO: regex sobre o arquivo → 7] | 338-382 |
| `format_limitations_block(applied_keys: list[str]) -> str` | texto plano; ignora chaves desconhecidas | 385-405 |
| `format_limitations_html(applied_keys: list[str]) -> str` | `<div class='audit-limitations'>…` ; retorna `""` se nenhuma chave válida | 408-424 |

Observações [REPO]:
- `make_audit_header` é a única função com gate neste módulo (l. 294); `compute_input_checksum`, `citation`, `AuditHeader` e os formatadores de limitações são livres (sem gate) [INFERÊNCIA a partir de 90-191, 199-291, 385-424].
- O timestamp NÃO é UTC nem carrega fuso (`datetime.now()`, l. 320) — relevante para reprodutibilidade de laudos (ver §6).
- `compute_input_checksum` é reutilizado por `app/postprocessor/study_cache.py:54,338` (`hash_study_inputs`) para invalidação de cache — o mesmo hash que aparece no laudo.

### 1.2 `app/commercial/feature_gates.py` (309 linhas) — gating comercial

| Símbolo | Conteúdo | Linhas |
|---|---|---|
| `_BUILD_EDITION_ENV = "OLIVAS_BUILD_EDITION"` | env var lida em `current_tier()`; `"community"` força `educational` | 37, 176-177 |
| `_TIER_ORDER` | `("invalid", "educational", "demo", "commercial", "pro_engineering", "enterprise")` | 45-52 |
| `class Feature` | constantes: `AUDIT_TRAIL_SHA256`, `PDF_PROFESSIONAL`, `AI_LAUDO`, `RELIABILITY_MC`, `ARC_FLASH_MC`, `POWER_FLOW_MC`, `PREMIUM_RELAY_LIBRARY`, `NBR_17227_TEMPLATE`, `MULTI_SEAT`, `WHITE_LABEL`, `ETAP_SKM_IMPORTER` (11 features) | 67-80 |
| `FEATURE_TIER_MAP: Dict[str, str]` | tier mínimo por feature (6× `commercial`, 2× `pro_engineering`, 3× `enterprise`) | 84-96 |
| `class LicenseRequiredError(RuntimeError)` | atributos `feature, required_tier, current_tier`; mensagem aponta "Ajuda → Ativar Licença" | 104-133 |
| `set_tier_override(tier)` / `_TIER_OVERRIDE` | override para testes/dev | 141-153 |
| `current_tier() -> str` | cadeia: override → env `community` → JWT (`license_server_client.check_active_license`) → HMAC legado em QSettings → `"educational"` | 156-203 |
| `is_feature_available(feature) -> bool` | feature NÃO catalogada → `True` (aberta) | 211-224 |
| `require_feature(feature) -> None` | levanta `LicenseRequiredError` | 227-244 |
| `requires_tier(tier)` | decorator por tier literal; valida nome | 250-286 |
| `requires_feature(feature)` | decorator que chama `require_feature` em cada invocação | 289-309 |

Pontos de uso no produto [REPO: grep `requires_feature(`]: `audit_trail.py:294`, `report_html.py:601` e `:1046` (`Feature.PDF_PROFESSIONAL`), `reliability_monte_carlo.py:242`, `power_flow_monte_carlo.py:174`, `arc_flash_monte_carlo.py:287`. Nenhum uso de `is_feature_available` fora do próprio módulo e dos testes — ou seja, a GUI não faz gray-out de menus hoje [INFERÊNCIA a partir do grep vazio em `app/gui`].

### 1.3 `app/postprocessor/report_html.py` (1074 linhas) — laudo HTML auto-contido

| Símbolo | Conteúdo | Linhas |
|---|---|---|
| Imports de auditoria | `KNOWN_LIMITATIONS, citation, format_limitations_html, make_audit_header` | 73-78 |
| `if TYPE_CHECKING: from app.postprocessor.bus_pipeline import BusPipelineReport` | o relatório é tipado ao `BusPipelineReport` | 80-82 |
| `_BUS_PIPELINE_LIMITATIONS` | tupla de 5 chaves de `KNOWN_LIMITATIONS` | 87-93 |
| `_BUS_PIPELINE_STANDARDS` | `("IEC 60909-0", "NBR 17227", "IEEE 1584", "IEEE 242", "NFPA 70E")` | 97-103 |
| `_plot_to_base64_png(fig, dpi=100)`, `_logo_data_uri()`, `_plot_tc_curves`, `_plot_arc_flash_boundary`, `_plot_motor_decay`, `_plot_topology_diagram` | helpers matplotlib (import lazy de numpy em 175, 254, 346) | 111-500 |
| `_HTML_CSS` (string privada) | CSS do laudo, inclui classes `.audit-header`, `.audit-limitations`, `.citation-footnote` | 505-598 |
| `@requires_feature(Feature.PDF_PROFESSIONAL)` `generate_html_report(report, *, responsible_engineer="", crea_number="", art_number="", notes="") -> str` | monta lista `sections` na ordem: audit header (636), header visual, KPIs, topologia, SC+AF, boundary, chains (cond.), relés (cond.), warnings (cond.), limitações (672), footer | 601-692 |
| `_build_audit_header_block(r, *, responsible_engineer, crea_number, art_number, notes) -> str` | `make_audit_header(report_kind=f"Análise consolidada — Barramento {r.bus_id}", inputs=r, standards_applied=list(_BUS_PIPELINE_STANDARDS), …)` → `header.to_html()` | 695-728 |
| `_build_limitations_block(r) -> str` | `format_limitations_html(list(_BUS_PIPELINE_LIMITATIONS))` — a lista é estática; os dois `if` condicionais (746-750) são `pass` | 731-751 |
| `_build_header`, `_build_kpi_block`, `_build_topology_section`, `_build_sc_arcflash_section` (usa `citation` por linha, docstring "Princípio 2"), `_build_arcflash_boundary_section`, `_build_topology_chains_section`, `_build_relay_section`, `_build_warnings_section`, `_build_footer` | seções | 754-1040 |
| `@requires_feature(Feature.PDF_PROFESSIONAL)` `save_html_report(report, path, *, responsible_engineer="", crea_number="", art_number="", notes="") -> None` | grava UTF-8 | 1046-1074 |

### 1.4 `app/postprocessor/report_pdf.py` (1173 linhas) — laudo PDF (matplotlib `PdfPages`)

| Símbolo | Conteúdo | Linhas |
|---|---|---|
| Docstring "Estratégia" | usa `matplotlib.backends.backend_pdf.PdfPages` "sem adicionar dependências externas (reportlab, weasyprint, etc.)" | 6-16 |
| Imports de auditoria | `KNOWN_LIMITATIONS, citation, make_audit_header` | 74-78 |
| `_BUS_PIPELINE_LIMITATIONS`, `_BUS_PIPELINE_STANDARDS` | duplicados de `report_html.py` (mesmos valores) | 85-99 |
| `_A4_WIDTH_IN = 8.27`, `_A4_HEIGHT_IN = 11.69` | layout A4 retrato | 108-109 |
| `_build_audit_cover_page(fig, report, *, responsible_engineer, crea_number, art_number, notes)` | capa: `make_audit_header(report_kind=f"Análise consolidada — Barramento {report.bus_id}", inputs=report, …)` (170-178); logo `app/resources/logo.png` (181-195); checksum 32 chars (l. 227); normas via `STANDARDS_CATALOG` (237-243); bloco de responsabilidade técnica (246-273); rodapé "Validade depende de revisão e assinatura por engenheiro habilitado" (292-298) | 127-300 |
| `_build_cover_page`, `_build_topology_page`, `_build_sc_arcflash_page`, `_build_arcflash_boundary_page`, `_build_tc_curves_page` (numpy lazy l. 799), `_build_relay_settings_pages` | páginas | 302-893 |
| `_build_limitations_page(fig, report)` | itera `_BUS_PIPELINE_LIMITATIONS` × `KNOWN_LIMITATIONS`; renderiza `[key]` + texto quebrado em ~78 chars | 895-967 |
| `_build_warnings_footer_page`, `_add_footer(fig, section)` | rodapé com `VERSION` (l. 1027) | 970-1052 |
| `save_pdf_report(report, path, *, responsible_engineer="", crea_number="", art_number="", notes="") -> None` | `matplotlib.use("Agg")` (1091); sequência de páginas 1096-1152; metadados `Title/Author/Subject/Keywords/CreationDate` (1155-1173) | 1054-1173 |

Observação [REPO]: `save_pdf_report` NÃO tem decorator `@requires_feature` (l. 1054), diferentemente de `save_html_report` (l. 1046 de `report_html.py`). O gate do PDF ocorre indiretamente via `make_audit_header` (l. 170 → `audit_trail.py:294`, `Feature.AUDIT_TRAIL_SHA256`) [INFERÊNCIA].

### 1.5 `app/gui/main_window.py` (4348 linhas) — registro dos diálogos de Análise

| Símbolo | Conteúdo | Linhas |
|---|---|---|
| Restauração de locale no boot | `self._settings.value("locale", "pt")` → `set_locale(saved_locale)` | 174-190 |
| `_build_menu(self)` | cria `QMenuBar`; menus `Arquivo` (402), `Editar` (429), `Análise` (442), `Ferramentas` (699), `Ajuda` (755), `Exemplos` (781), `Visualizar` (792) | 398-≈935 |
| Bloco do menu `Análise` | `analysis_menu = menu_bar.addMenu("Análise")` (442); padrão de registro: `act_x = analysis_menu.addAction("<emoji> <rótulo> (<norma>)...", self._on_<handler>)` + `act_x.setShortcut(...)` (opcional) + `act_x.setStatusTip("...")`; 26 chamadas `addAction` entre 442-690 [CÁLCULO PRÓPRIO: `sed -n '442,690p' | grep -c "analysis_menu.addAction("` → 26]; separadores em 452, 577, 625, 668, 677 | 442-690 |
| Exemplo canônico (Reliability, v3.6.0) | `act_reliability = analysis_menu.addAction("📊 Reliability Indices (IEEE 1366-2012)...", self._on_show_reliability)`; `setStatusTip("Calcula SAIFI/SAIDI/CAIDI/ASAI … Paridade PTW Tutorial §Part 10.")` | 529-537 |
| Ação "Relatório completo (HTML / PDF)" | `self._on_export_pipeline_report`; status tip cita "SHA256 + responsável + citações + limitações declaradas — ISO 9001 / NR-10" | 678-686 |
| Submenu `Visualizar → Resultados (gráficos das análises)` | 4 docks: `pf_voltage`, `sc_pie`, `tcc_overlay`, `mc_hist` via `self._ensure_plot_dock(kind)` | 891-918 |
| `_ensure_plot_dock(self, kind)` | lazy-create por `if/elif` sobre kind; `addDockWidget(Qt.RightDockWidgetArea, w)`; `populate_from_cache(self._study_cache())` | 1060-1100 |
| `_current_pp_project(self)` | `self.schematic_pp.scene.to_project()` | 2406-2416 |
| Handlers `_on_analyze_*` (SC/PF/motor/arc-flash) | assinatura `(self, *_qt_args, project=None, bus_id: str = "")`; `*_qt_args` absorve o `bool checked` do `QAction.triggered` (comentário 2418-2426); import lazy de `app.gui.analysis_dialogs` | 2428-2461 |
| Handlers `_on_show_*` (Track B v3.1.0, backfill "7ª garantia") | docstrings citam explicitamente "Backfill GUI sob 7ª garantia — expõe ao usuário todos os módulos backend … que estavam órfãos" | 2838-2960 |
| `_on_show_reliability(self, *_qt_args)` | `from app.gui.reliability_dialog import ReliabilityDialog; dlg = ReliabilityDialog(parent=self); dlg.exec()`; docstring "Acessibilidade: Master Protocol garantia 7ª (GUI obrigatória)" | 3070-3080 |
| `_on_show_plugins` | lista read-only de plugins/estudos registrados (`get_registered_studies`) — NÃO cria ações de menu | 3248-3300 |
| `_on_analyze_bus_pipeline`, `_on_export_pipeline_report` | delegam a `analysis_dialogs` | 3353-3363 |
| `_on_run_analysis_dialog(self)` | abre `RunAnalysisDialog`; conecta `analysis_requested(kind, bus_id)` a `_dispatch_analysis` | 3404-3426 |
| `_dispatch_analysis(self, kind, bus_id, pp_project)` | `kind ∈ {sc, coord, arc_flash, pf, motor, ct_sat, pipeline}` (docstring 3433); `if/elif` por kind (3444-3470); após sucesso chama `refresh_open_plot_docks(self)` (3476-3486); erros → `QMessageBox.critical` + console | 3428-3499 |
| `_study_cache(self)` | lazy `StudyCache()` em `self._studies_cache` | 3503-3510 |

### 1.6 `app/gui/analysis_dialogs.py` (1065 linhas) — padrão de diálogo de parâmetros

| Símbolo | Conteúdo | Linhas |
|---|---|---|
| Docstring | "Cada função abre um QDialog para parâmetros, executa a análise e retorna um Optional[ResultObject]. Caller é responsável por exibir o resultado." | 1-16 |
| `show_result_dialog(parent, title, text, *, width=800, height=600) -> None` | `QPlainTextEdit` monoespaçado + botão "Copiar" + `Close`; `dlg.exec()` modal | 36-75 |
| `class ShortCircuitDialog(QDialog)` | `__init__(parent=None)`: `setWindowTitle`, `setModal(True)`, `resize`, `QFormLayout` com `QDoubleSpinBox` (range, valor default, `setSuffix(" kV")`), `QComboBox` com `addItem(rótulo, dado)`, `QCheckBox` com citação `"Trifásica (Ik''3) — IEC §4.3.1"`, `QDialogButtonBox(Ok|Cancel)`; `get_parameters() -> dict` | 78-177 |
| `run_short_circuit_analysis(parent, *, project=None, bus_id="", **kwargs)` | abre dialog, `if dlg.exec() != QDialog.Accepted: return`, monta caso, roda backend, `show_result_dialog` | 179-283 |
| `class MotorStartingDialog(QDialog)` / `run_motor_starting_analysis` | mesmo padrão; 11 campos físicos com faixas (ex.: `voltage_kV` 0.208-15.0, default 4.16 kV; `lr_ratio` 3-12, default 6.0) | 661-795 |
| `run_bus_pipeline_analysis(parent, project=None, *, bus_id="", **kwargs)` | guarda `project is None` (912-918); `QInputDialog.getItem` para escolher BUS (938-944); armazena no `results_cache` e refresca datablocks (955-958) | 904-965 |
| `_store_report_and_refresh_datablocks(parent, bus_id, report) -> int` | `parent.schematic_pp.scene.results_cache.set_pipeline_report(bus_id, report)` + `refresh_datablocks_from_cache` | 968-994 |
| `run_pipeline_report_export(parent, project=None) -> None` | escolhe BUS e formato (HTML/PDF) via `QInputDialog`; `QFileDialog.getSaveFileName`; chama `save_html_report` ou `save_pdf_report` SEM passar `responsible_engineer/crea/art/notes` (1048-1058) | 997-1065 |

Padrão alternativo (diálogo autocontido em arquivo próprio): `app/gui/reliability_dialog.py` — `class ReliabilityDialog(QDialog)` (l. 39), `__init__(parent: QWidget | None = None)` (50), botão "🎲 Monte Carlo (IEEE 493 presets)" (97-100), `_on_calculate` (164), `_on_run_monte_carlo` (198) com `try/except` que escreve `"❌ Erro Monte Carlo: {e}"` no `QPlainTextEdit` (226) [REPO].

### 1.7 Infraestrutura de estudos modulares e cache

| Arquivo | Símbolo | Linhas |
|---|---|---|
| `app/postprocessor/study_cache.py` | `class PrerequisiteError(Exception)` (74); `class CacheEntry` (103) com `is_valid_for(current_hash)` (113); `class StudyCache` (123) com `has_/get_/get_*_if_valid/set_` para `sc` (147-168), `coord` (170-194), `arc_flash` (196-218), `pf` (220-237), `motor_starting` (239-253), `ct_saturation` (255-269); `invalidate_bus` (271), `invalidate_all` (279), `status_summary` (290); `hash_study_inputs(project, bus_id, config) -> str` (310-338) reutilizando `compute_input_checksum` | — |
| `app/postprocessor/studies/__init__.py` | contrato: cada estudo expõe `run(project, bus_id, *, cache=None, config=None, auto_run_prereqs=True)` que verifica cache → prereqs → computa → grava → retorna dataclass tipado | 1-60 |
| `app/postprocessor/studies/short_circuit.py` | `class ShortCircuitStudyResult` (65), `run(...)` (107), `_compute_short_circuit` (176) | — |
| `app/gui/schematic_pp/datablock_binder.py` | `class DataBlockResultCache` (196) com namespaces `pipeline`/`sc`/`pf`: `set_pipeline_report` (217), `set_sc_result` (224), `set_pf_solution` (236), `all_bus_ids` (250), `clear` (257) | — |
| `app/gui/plot_widgets.py` | `_BasePlotDock(QDockWidget)` (45), `PowerFlowVoltageProfileDock` (192), `ScContributionPieDock` (273), `TccCurveOverlayDock` (339), `MonteCarloHistogramDock` (441) | — |
| `app/gui/plot_dock_refresh.py` | `_DOCK_ATTRS` (tupla com 4 nomes `_plot_dock_*`, l. 42-47); `refresh_open_plot_docks(main_window) -> int` (50) | — |
| `app/plugins/registry.py` | `register_study(name)` (40-62) — docstring afirma "O estudo aparece automaticamente no menu Análise" (l. 43-44), mas em `main_window.py` `get_registered_studies` é usado apenas na listagem read-only `_on_show_plugins` (3258-3263) [REPO] → afirmação do docstring NÃO se confirma no código [INFERÊNCIA] | — |

### 1.8 `app/i18n/__init__.py` (180 linhas) e `app/i18n/translations/{en,es}.json`

| Símbolo | Conteúdo | Linhas |
|---|---|---|
| `_SUPPORTED_LOCALES = ("pt", "en", "es")`, `_DEFAULT_LOCALE = "pt"` | PT é passthrough (sem JSON) | 54-55 |
| `_load_translations(locale)` | lê `translations/<locale>.json`; falha → `{}` | 68-76 |
| `set_locale(locale)`, `get_locale()`, `reset_locale()` | locale global com `threading.Lock` | 79-104 |
| `_(text: str) -> str` (alias `t`) | retorna `text` se PT ou chave ausente ("NUNCA inventa tradução") | 107-123 |
| `get_locale_choices()`, `get_coverage_stats()` | helpers de UI (v2.1.0) | 142-180 |
| `en.json` / `es.json` | 138 linhas com `":` cada [CÁLCULO PRÓPRIO: `grep -c '":'`]; bloco `_meta` (locale, name, coverage_pct=75, version=2.1.0, comment) + pares `"<string PT>": "<tradução>"` — a CHAVE é a própria string PT | — |

Adoção real [REPO: grep]: apenas `app/gui/main_window.py` e `app/gui/locale_picker_dialog.py` importam `app.i18n`; há 5 ocorrências de `_("` em `app/gui`. Os rótulos do menu `Análise` (442-690) são strings literais PT, não passam por `_()`. O readiness test (§1.12) verifica apenas paridade de chaves EN/ES, ≥ 100 chaves e valores não vazios — não verifica que a GUI use `_()` [INFERÊNCIA].

### 1.9 `app/core/version.py` (1993 linhas)

| Símbolo | Conteúdo | Linhas |
|---|---|---|
| Docstring-histórico | entradas `* X.Y.Z — descrição` (não estritamente ordenadas: 0.83… no topo l. 19-23; 2.0.0 em 162; 1.7.x em 264-329; 1.0.x em 1848-1899; 0.95/0.94 em 1925-1938) | 1-1956 |
| `VERSION_TUPLE = (4, 0, 0)`; `PRE_RELEASE = "beta"`; `PRODUCT_NAME`; `PRODUCT_TAGLINE`; `VERSION = "4.0.0-beta"` | fonte única da versão | 1959-1968 |
| `parse_version(s) -> tuple[int, ...]` (ignora sufixo) ; `is_newer(remote, local=VERSION)` | | 1971-1993 |

### 1.10 `CHANGELOG.md` (197 linhas) e `CHANGELOG_ATP_STUDIO.txt` (legado, 490 KB)

- Formato declarado: Keep a Changelog 1.1.0 + SemVer [REPO: CHANGELOG.md:3].
- Estrutura de entrada: `## [X.Y.Z] — YYYY-MM-DD` → subseções `### Added`, `### Changed`, `### Fixed`, `### Closed (SKIPPED_BACKLOG)`, `### Validated (no code changes)`, com bullets citando caminhos de arquivos e número de testes (ex.: l. 76-84 para 3.8.0: módulo `~280 LOC`, presets, botão GUI, "18 tests Reliability MC").
- Seções finais fixas: "Histórico anterior (v0.x → v3.4.0)" apontando para `docs/v<X.Y.Z>_HANDOFF.md` (174-177) e "Standards cobertos (cumulativo)" (181-193) — lista de 11 normas que deve ser atualizada quando uma nova norma entra.
- O `CHANGELOG_ATP_STUDIO.txt` usa outro formato (`[0.94.0] - TÍTULO` em caixa de `=`) e contém o "Driver do usuário" e "Diagnóstico" por release (l. 5-25) — legado, não referenciado pelo readiness test [INFERÊNCIA].

### 1.11 Documentos canônicos de processo (`docs/`, 93 arquivos, diretório plano; `docs/research` NÃO existe [CÁLCULO PRÓPRIO: `ls docs/research` → inexistente])

| Documento | Papel | Trechos-chave |
|---|---|---|
| `docs/SESSION_HANDOFF.md` | "PRIMEIRO arquivo a ler" (l. 9-10); Master Protocol com 7 garantias listadas (24-43) + apontadores (45-54); tabela de releases com testes próprios (71-116); lista TRAVADA de arquivos não modificáveis (121-143); padrões de código (279-286); pegadinhas anti-alucinação (288-298) | 7ª garantia: "Toda feature backend implementada DEVE ter ponto de entrada GUI … Backend órfão é proibido a partir de v3.1.0 … Texto formal: PTW_TOTAL_PARITY_DIRECTIVE.md §8.3" (37-43) |
| `docs/CONTEXT_PRESERVATION_PROTOCOL.md` | 8ª garantia; ordem obrigatória de leitura (31-39); protocolos 3.1-3.6 (48-81); checklist de boot (120-129); ações proibidas (131-138) incluindo "❌ Adicionar feature backend sem trigger GUI (7ª garantia)" (134) e "❌ Codar fórmula técnica sem citação §seção p. NN" (136); ações obrigatórias (140-147) | §3.4 "Anti-falta-de-integração-GUI (7ª garantia)": trigger GUI documentado; audit pós-sprint cruzando `app/gui/`; órfão → P0; smoke test manual "Para usar X, user clica em..." (66-70). §3.5: cobertura mínima 80 % em módulos novos (75) |
| `docs/PTW_TOTAL_PARITY_DIRECTIVE.md` | 6ª garantia endurecida; 8 dimensões de superação (39-48); critérios de aceite de release (128-142); fluxo do sprint (146-154): "Engine: stdlib quando possível, Pydantic schemas" (150), "i18n desde dia-0: novas strings UI sempre passam por `_()`" (171) | **§8.3 existe** (l. 243-261): texto formal da 7ª garantia + critérios 9-11 (trigger GUI documentado antes do release; deep GUI audit cruzando `app/gui/main_window.py`; smoke test manual). Nota: no arquivo, §8.4 (224-241) aparece ANTES de §8.3 (243) [REPO] |
| `docs/SKIPPED_BACKLOG.md` | débito técnico persistente; política: cap 15, revisão bi-release, promoção forçada após 3 releases (164-172); "nenhum item entra sem (a) referência ao handoff que originou e (b) justificativa" (8-10); formato por item: estado anterior / implementado / tests / standards; histórico (176-194) | "Garantia 7ª compatible: nenhum item pulado pode violar a acessibilidade GUI; se violar, é P0 imediato" (171-172) |
| `docs/v1.7.0_MASTER_PROTOCOL.md` | 5 garantias originais: Auditar (`vX.Y.Z_BACKLOG_AUDIT.md`), Registrar, Anti-alucinação ("Sem golden value publicado: `@pytest.mark.skip` ao invés de inventar", 36), Anti-regressão (Read-then-Edit; "novos arquivos > edits"), Ponto de restauração (`restore_points/<versao>_baseline/`, gitignored) | 14-56 |
| `docs/v3.8.0_HANDOFF.md` | template de handoff de módulo novo: §1 Resumo, §2 tabela 8 garantias, §3-5 sprints, §6 arquivos novos/editados, §7 sweep, §8 Smoke Test Manual, §9 backlog, §10 "Anti-alucinação — limitações declaradas" por sprint, §11 métricas, §12 próxima sessão | 1-220 |
| `docs/v3.1.0_GUI_AUDIT.md` | template de "deep GUI audit": §A mapa de menus, §B tabela módulo backend × GUI × trigger, §C gaps priorizados, §E garantia | 1-115 |
| `docs/PTW_SURPASSING_MATRIX.md` | matriz feature PTW × dimensão de superação; feature 141 "Failure Rate / Repair Time Aging Factor (5th-order poly)" T2, v3.7.0, status ⏳, dim. 1, "+ Weibull + Bayesian update" (l. 288) — a feature PTW mais próxima de um RUL | — |
| `docs/MONETIZATION_PLAN.md` | tiers Community/Estudante/Pro Individual/Pro Engenharia/Empresarial (20-26); tabela de gate técnico por módulo (28-39): Monte Carlos são "Pro+" | — |
| `docs/LICENSING.md` / `docs/THIRD_PARTY_NOTICES.md` | mapa de licenças das dependências (LICENSING §4, l. 102-126); política clean-room (§3); THIRD_PARTY_NOTICES lista cada dependência direta com licença, uso no código e aviso exigido (1-80) | — |
| `CONTRIBUTING_ATP_STUDIO.txt` | §14 "MUDANÇAS DE ALTO IMPACTO" inclui "introdução de nova dependência crítica" e exige descrição com justificativa (l. 219-229) | — |
| `ROADMAP.md` | Quality Gates por sprint: tests 100 %, coverage ≥ 85 % (nota: CONTEXT_PRESERVATION diz 80 %), CHANGELOG entry, "Audit trail integrado (se análise)", smoke test em projeto real (32-38) | — |

### 1.12 Testes — `tests/conftest.py` (42 l.), nomenclatura e padrões

| Item | Fato | Fonte |
|---|---|---|
| `REF_FILE` | `trt_all_motors_dt_ea.atp` (removido do release público; fixture `ref_project` faz `pytest.skip` se ausente) | conftest.py:12-25 |
| Fixture autouse `_commercial_tier_override` | `set_tier_override("enterprise")` para todos os testes; `set_tier_override(None)` no teardown; testes de gating chamam `set_tier_override(None)` explicitamente | conftest.py:28-42 |
| Nomenclatura | `tests/test_pp_v<MAJOR>_<MINOR>_<PATCH>_<slug>.py` (ex.: `test_pp_v3_8_0_reliability_mc.py`, `test_pp_v4_1_0_commercial_sprint1.py`); 171 arquivos `test_pp_v*.py` [CÁLCULO PRÓPRIO: `ls tests/test_pp_v*.py | wc -l`]; GUI legado `tests/test_gui_v1_x_y_*.py`; sem `pytest.ini`/`pyproject.toml` [CÁLCULO PRÓPRIO: `ls` → inexistentes] | — |
| Fixture Qt | `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")` + fixture `qapp` module-scoped `QApplication.instance() or QApplication(sys.argv)` | test_pp_v3_8_0_reliability_mc.py:16-23; test_pp_v3_3_0_unbalanced_dialog.py:19-26 |
| Teste de wiring de menu (7ª garantia) | `inspect.getsource(main_window)` e asserts de presença do handler `_on_show_reliability` e do rótulo no menu | test_pp_v3_6_0_reliability.py:286-296 |
| Teste de diálogo | instanciar dialog sem `exec()`, checar `windowTitle`, valores default, clicar handler diretamente (`test_mc_handler_runs`) | test_pp_v3_8_0_reliability_mc.py:205-217; test_pp_v3_3_0_unbalanced_dialog.py:38-52 |
| Testes de gate | `TestGatesIntegration`: `*_blocked_at_educational` para audit_trail, report_html, 3 MCs; `test_gates_passthrough_at_enterprise` | test_pp_v4_1_0_commercial_sprint1.py:380-460 |
| **Restrição sobre novas features** | `test_tier_hierarchy_educational_blocks_all_paid` itera `FEATURE_TIER_MAP.keys()` e exige `is_feature_available(f) is False` em tier `educational` → toda feature nova catalogada deve ter tier ≥ `demo` | test_pp_v4_1_0_commercial_sprint1.py:368-375 |
| Restrição sobre `KNOWN_LIMITATIONS` | `expected_keys.issubset(...)` — apenas subconjunto; adicionar chaves não quebra | test_pp_v0_92_audit_trail.py:298-309 |
| Restrição sobre `STANDARDS_CATALOG` | `test_standards_catalog_minimum_count` verifica famílias mínimas — adicionar normas não quebra | test_pp_v0_92_audit_trail.py:76-90 |
| Readiness (produção) | versão deve começar por `"4."` e conter `alpha`/`beta` (readiness:29-37) ou `alpha/beta/rc` (alpha_milestone:33-37); paridade EN/ES exata (readiness:54-74); ≥ 100 chaves EN (76-82); valores não vazios (85-98); `CHANGELOG.md` menciona v4 (108); docs canônicos existem (117-127); `SKIPPED_BACKLOG` sem itens abertos (129); imports críticos (149-192); 8 garantias mencionadas (236-243) | tests/test_pp_v4_0_0_beta_readiness.py |
| Testes que fixam `requirements.txt`/CI | `test_pp_v0_31_0_ci.py:121-138` exige `pytest`, `PySide6`, `numpy` em `requirements.txt` e `ruff`, `matrix`, `ubuntu-latest`, `windows-latest`, `3.13`, `QT_QPA_PLATFORM`/`offscreen` nos workflows; `test_pp_v2_0_0_docker.py:22-59` exige `python:3.11`/`3.12`, `COPY app`, `COPY requirements.txt`, `HEALTHCHECK`, `offscreen` no Dockerfile e `olivas:2` no compose | — |
| Teste de integração de laudo | `TestReportHtmlIntegration` (audit header, citações por valor, bloco de limitações, engenheiro responsável) e `TestReportPdfIntegration.test_pdf_generates_with_audit_cover` | test_pp_v0_92_audit_trail.py:354-485 |

### 1.13 CI — `.github/workflows/lint.yml` (70 l.) e `test.yml` (109 l.)

| Job | Fato | Linhas |
|---|---|---|
| `lint` | Python 3.13; `ruff check app/ --select=E9,F63,F7,F82` **não bloqueante** (`|| true`); `ruff format --check` `continue-on-error` | lint.yml:11-39 |
| `imports` ("import smoke (sem GUI)") | instala APENAS `numpy pydantic PyYAML` (sem PySide6, sem matplotlib) e importa 12 módulos core (`app.standards.*`, `app.preprocessor.atp_format`, `app.postprocessor.short_circuit/power_flow/motor_starting/arc_flash/relay_coordination`) | lint.yml:41-70 |
| `test` | matriz ubuntu/windows × 3.11/3.12/3.13; `pip install -r requirements.txt` + `pytest pytest-cov pytest-timeout`; roda **lista explícita de 12 arquivos** (`test_pp_v4_1_0_commercial_sprint{1..5}`, `v4_0_0_beta_readiness`, `v2_0_0_commercial`, `v0_92_audit_trail`, `report_html`, `v0_44_monte_carlo`, `v0_80_pf_monte_carlo`, `v3_8_0_reliability_mc`) com `--cov` em `app.commercial`, `audit_trail`, `report_html` e os 3 MCs; `--timeout=60 --timeout-method=thread`; justificativa: testes legados abrem `dlg.exec()` modal e travam em headless (comentário 51-61) | test.yml:11-90 |

Consequência [INFERÊNCIA]: um novo arquivo de teste NÃO é executado no CI público a menos que seja acrescentado à lista de `test.yml:66-78`; um novo módulo core só é validado sem GUI se acrescentado a `lint.yml:57-69`.

### 1.14 Dependências e empacotamento

| Arquivo | Fato | Linhas |
|---|---|---|
| `requirements.txt` | 8 entradas: `PySide6>=6.6.0`, `anthropic>=0.90.0`, `matplotlib>=3.8.0`, `numpy>=1.24.0`, `pytest>=8.0.0`, `pydantic>=2.5.0`, `PyYAML>=6.0`, `openpyxl>=3.1.0` | 1-8 |
| Uso real de `numpy` em `app/` | 10 ocorrências, todas lazy (dentro de função) exceto `app/preprocessor/vector_fitting.py:54`; `power_flow.py:342,407`, `report_html.py:175,254,346`, `report_pdf.py:799`, `analysis_dialogs.py:558` [CÁLCULO PRÓPRIO: grep] | — |
| `scipy`, `pandas`, `sklearn`, `torch`, `reportlab`, `lifelines`, `statsmodels` | **nenhuma ocorrência** em `app/` [CÁLCULO PRÓPRIO: grep → 0 arquivos]; `report_pdf.py:9` menciona reportlab apenas para justificar sua não adoção | — |
| Política implícita "stdlib primeiro" | `reliability_monte_carlo.py:20-22`: "Apenas usa `random` stdlib (não numpy) para garantir reprodutibilidade via seed"; `PTW_TOTAL_PARITY_DIRECTIVE.md:150`: "Engine: stdlib quando possível, Pydantic schemas"; `README.md:163`: "Sem dependência em fornecedor proprietário" | — |
| `Dockerfile` | `python:3.11-slim`; instala libs Qt; `pip install -r requirements.txt` (24); `COPY app`, `COPY tests`, **`COPY docs`** (27-29); `QT_QPA_PLATFORM=offscreen`, `OLIVAS_HEADLESS=1`; healthcheck importa `VERSION`; entrypoint `pytest tests/ -q` | 4-43 |
| `.dockerignore` | inexistente [CÁLCULO PRÓPRIO] → tudo em `docs/` entra na imagem | — |
| `build/olivas_pro.spec` | `hiddenimports` inclui `matplotlib.backends.backend_{qt5agg,agg,pdf}` e `numpy` (45-54); `excludes` para clean-room (74-76) | — |
| `build/runtime_hook_community.py` | define `OLIVAS_BUILD_EDITION=community` antes de importar o app | 19-21 |
| `docs/THIRD_PARTY_NOTICES.md` | cada dependência direta tem seção com licença/uso/aviso — nova dependência exige nova seção [INFERÊNCIA a partir de 1-80] | — |

### 1.15 `app/core/logging_config.py` — logging auditável

`get_logger(name)`, `configure_logging(...)`, `log_engineering_event(...)`; convenções de nível (DEBUG passos; INFO eventos; WARNING fallbacks/limitações; ERROR falha; CRITICAL dados inconsistentes) [REPO: l. 19-45]; 26 arquivos em `app/` usam `get_logger` [CÁLCULO PRÓPRIO: grep -l | wc -l].

---

## 2. Fluxo de dados (como um estudo entra no laudo auditável)

```
[menu Análise] main_window._build_menu (442-690)
      │  addAction("<emoji> <rótulo> (<norma>)...", self._on_<x>) + setStatusTip
      ▼
[handler] main_window._on_<x>(self, *_qt_args, project=None, bus_id="")   (2428-2461 / 3070-3080)
      │  project = self._current_pp_project()  →  PpProject (scene.to_project())
      ▼
[diálogo] app/gui/analysis_dialogs.<X>Dialog(QDialog).get_parameters() -> dict   (78-177, 661-760)
      │  ou app/gui/<x>_dialog.py autocontido (reliability_dialog.py:39-226)
      ▼
[backend] app/postprocessor/<x>.py  (dataclass Case frozen → função analyze/run → dataclass Result com summary()/as_text_report())
      │  opcional: @requires_feature(Feature.X)  → LicenseRequiredError se tier insuficiente (feature_gates.py:289-309)
      │  opcional: StudyCache.set_<x>(id, result, hash_study_inputs(...))  (study_cache.py:162-269, 310-338)
      ▼
[exibição] show_result_dialog(parent, título, texto)  (analysis_dialogs.py:36-75)
      │  + DataBlockResultCache.set_*(bus_id, result) → refresh_datablocks_from_cache (datablock_binder.py:217-247; analysis_dialogs.py:968-994)
      │  + refresh_open_plot_docks(main_window) após _dispatch_analysis (main_window.py:3476-3486)
      ▼
[laudo]  report_html.generate_html_report(report, *, responsible_engineer, crea, art, notes)  (601-692)
         report_pdf.save_pdf_report(report, path, *, …)  (1054-1173)
      │  1º bloco: make_audit_header(report_kind, inputs=report, standards_applied=_X_STANDARDS, …)  → AuditHeader.to_html()/fig.text
      │      ├─ VERSION (version.py:1966)     ├─ timestamp datetime.now()   ├─ SHA256(compute_input_checksum(report))
      │      └─ STANDARDS_CATALOG[std] (títulos completos)
      │  corpo: citation("IEC 60909-0", "§4.3.1", "Eq.(31)") por valor calculado (report_html.py:863-919)
      │  penúltimo bloco: format_limitations_html(list(_X_LIMITATIONS)) ← KNOWN_LIMITATIONS (report_html.py:731-751; report_pdf.py:895-967)
      ▼
[GUI de exportação] run_pipeline_report_export (analysis_dialogs.py:997-1065): QInputDialog BUS → formato → QFileDialog → save_*_report
```

Fluxo de gating: `current_tier()` (feature_gates.py:156-203) resolve override de teste → env `OLIVAS_BUILD_EDITION=community` → JWT → HMAC legado → `educational`. Em testes, `tests/conftest.py:28-42` força `enterprise`. A GUI não consulta `is_feature_available` (sem gray-out); o erro `LicenseRequiredError` só aparece se o handler o capturar (ex.: `reliability_dialog.py:198-226` captura `Exception` genérica e mostra "❌ Erro Monte Carlo") [REPO].

Fluxo i18n: `MainWindow.__init__` restaura locale de `QSettings("locale")` (main_window.py:174-190) → `set_locale` → `_()` consulta `translations/<locale>.json` pela string PT como chave. Como os rótulos de menu não passam por `_()`, a troca de locale só afeta os pontos que usam `_()` (5 ocorrências) [REPO].

Fluxo de release/processo: `vX.Y.Z_BACKLOG_AUDIT.md` (auditar) → código + `tests/test_pp_vX_Y_Z_<slug>.py` → sweep targeted → `restore_points/` (local, gitignored) → `docs/vX.Y.Z_HANDOFF.md` + `SESSION_HANDOFF.md` (§3.2 tabela) + `SKIPPED_BACKLOG.md` + `PTW_SURPASSING_MATRIX.md` + `CHANGELOG.md` + `version.py` bump (PTW_TOTAL_PARITY_DIRECTIVE.md:128-154; CONTEXT_PRESERVATION_PROTOCOL.md:140-147).

---

## 3. Pontos de extensão concretos (arquivo:símbolo → como estender de forma incremental)

Todos os itens abaixo são [HIPÓTESE] de projeto ancoradas em [REPO]; nenhum foi implementado.

| # | Arquivo:símbolo | Como estender (incremental, sem quebrar o existente) |
|---|---|---|
| E1 | `app/commercial/feature_gates.py:67-80` `class Feature` e `:84-96` `FEATURE_TIER_MAP` | Adicionar `RUL_PROGNOSIS = "rul_prognosis"` e mapear para `"commercial"` (alinhado aos Monte Carlos, MONETIZATION_PLAN.md:33-36) ou `"pro_engineering"`. Obrigatório tier ≥ `demo` por causa de `test_pp_v4_1_0_commercial_sprint1.py:368-375`. Decorar a função de entrada do backend com `@requires_feature(Feature.RUL_PROGNOSIS)` como em `reliability_monte_carlo.py:242`. |
| E2 | `app/postprocessor/audit_trail.py:338-382` `KNOWN_LIMITATIONS` | Acrescentar chaves com prefixo `rul_` (ex.: `rul_reignition_count_user_premise`, `rul_no_insulation_model_in_docA`, `rul_arrhenius_single_stress`, `rul_ci_bootstrap_only`). Texto deve declarar a heurística e a norma/fonte, no mesmo estilo dos 7 existentes. `format_limitations_html` ignora chaves desconhecidas (415), logo a adição é segura. |
| E3 | `app/postprocessor/audit_trail.py:73-87` `STANDARDS_CATALOG` | Acrescentar apenas normas efetivamente citadas no código do módulo (anti-alucinação, CONTEXT_PRESERVATION_PROTOCOL.md:48-52). Candidatas a verificar antes de catalogar: IEC 60034-18-41 / IEC 60034-27-1 / IEEE 1434 / IEEE 43 / IEC 62271-100 / IEEE C37.011 — [INSERIR CITAÇÃO] para cada uma (títulos e anos a confirmar na fonte primária). `citation()` já funciona com normas não catalogadas (113-115), então o catálogo pode ser preenchido depois. |
| E4 | `app/postprocessor/audit_trail.py:294-327` `make_audit_header` | Reutilizar diretamente: `make_audit_header(report_kind=f"Prognóstico de isolamento — Motor {motor_id}", inputs=rul_case_or_result, standards_applied=list(_RUL_STANDARDS), …)`. `inputs` pode ser dataclass (aninhada) — `_to_jsonable` cobre dataclass/dict/list/complex (164-191). Séries temporais longas em `inputs` inflam o JSON antes do hash; preferir hashear um resumo determinístico (ver §6). |
| E5 | `app/postprocessor/report_html.py:601-692` `generate_html_report` e `report_pdf.py:1054-1173` `save_pdf_report` | NÃO estender: ambos são tipados a `BusPipelineReport` e usam `report.bus_id` (`report_html.py:720`, `report_pdf.py:171`). Criar `app/postprocessor/report_rul_html.py` e `report_rul_pdf.py` espelhando o padrão: tuplas `_RUL_LIMITATIONS`/`_RUL_STANDARDS` (cf. 87-103), `@requires_feature(Feature.PDF_PROFESSIONAL)` nas funções públicas (cf. 601, 1046), seção 1 = `make_audit_header(...).to_html()`, seções com `citation()` por valor, penúltima = `format_limitations_html`, footer com refs. Para reaproveitar CSS, importar `_HTML_CSS` (report_html.py:505) é possível mas acopla a nome privado — alternativa incremental: promover `_HTML_CSS` a `HTML_CSS` público mantendo alias. Para PDF, `_build_audit_cover_page` (127-300) só é reutilizável se receber `report_kind` como parâmetro em vez de derivar de `report.bus_id` (171) — mudança backward-compatible via kwarg opcional. |
| E6 | `app/gui/main_window.py:442-690` bloco `analysis_menu` | Inserir, por exemplo após `act_reliability` (529-537) ou após `act_reaccel` (653-660): `act_rul = analysis_menu.addAction("🧬 Prognóstico de isolamento / RUL — motor MT (…)...", self._on_show_rul_prognosis)`; `act_rul.setStatusTip("Estresse dielétrico de manobra VCB → degradação incremental → RUL com IC. …")`. Handler novo seguindo `_on_show_reliability` (3070-3080): import lazy do diálogo, `dlg = RulPrognosisDialog(parent=self, project=self._current_pp_project()); dlg.exec()`. Isso satisfaz a 7ª garantia (PTW_TOTAL_PARITY_DIRECTIVE.md:243-253) e o teste de wiring por `inspect.getsource` (test_pp_v3_6_0_reliability.py:286-296). |
| E7 | `app/gui/run_analysis_dialog.py:97-155` (`analyses` list + `_radios`) e `main_window._dispatch_analysis` 3444-3470 | Opcional (segunda porta de entrada): adicionar kind `"rul"` na lista de radios e um ramo `elif kind == "rul":` no dispatcher. A docstring 3433 enumera os kinds — atualizar. |
| E8 | `app/gui/analysis_dialogs.py` (padrão `XDialog(QDialog)` + `run_x_analysis`) ou arquivo próprio `app/gui/rul_prognosis_dialog.py` | Preferir arquivo próprio (padrão v3.6.0+: `reliability_dialog.py`, `unbalanced_pf_dialog.py`; "novos arquivos > edits", v1.7.0_MASTER_PROTOCOL.md:47). Estrutura: `class RulPrognosisDialog(QDialog)` com `__init__(parent=None, project=None)`, `QFormLayout` de `QDoubleSpinBox` com `setRange/setValue/setSuffix` e rótulos citando norma, botão de cálculo, `QPlainTextEdit` de resultado, `try/except` que captura `LicenseRequiredError` separadamente (mensagem "Ajuda → Ativar Licença", feature_gates.py:125-129) e demais exceções. Evitar `dlg.exec()` dentro de testes (test.yml:51-61). |
| E9 | `app/postprocessor/study_cache.py:123-290` `StudyCache` | Se o RUL depender de SC/motor starting como pré-requisito, adicionar `has_rul/get_rul/set_rul(motor_id, result, input_hash)` no mesmo padrão de `motor_starting` (239-253) e `ct_saturation` (255-269), e usar `hash_study_inputs` (310-338). Alternativa MVP: manter resultado apenas no diálogo, sem cache. |
| E10 | `app/gui/schematic_pp/datablock_binder.py:196-260` `DataBlockResultCache` | Para exibir RUL como datablock no esquemático: novo namespace `_rul_results` + `set_rul_result(motor_id, result)`/`get_rul_result`; incluir em `all_bus_ids`/`clear`. |
| E11 | `app/gui/main_window.py:891-918` (submenu de plots) + `:1060-1090` `_ensure_plot_dock` + `app/gui/plot_dock_refresh.py:42-47` `_DOCK_ATTRS` + `app/gui/plot_widgets.py:45` `_BasePlotDock` | Dock "📈 Curva de degradação / RUL com IC": nova classe `RulDegradationDock(_BasePlotDock)` com `populate_from_cache(cache)`; novo `elif kind == "rul_curve"`; acrescentar `"_plot_dock_rul_curve"` a `_DOCK_ATTRS`. |
| E12 | `app/i18n/translations/en.json` e `es.json` | Toda string nova exibida (rótulo de menu, título de diálogo, rótulos de campos, botões) deve ganhar par PT→EN e PT→ES em ambos os arquivos, mantendo paridade exata (readiness:54-74) e valores não vazios (85-98). Na GUI, envolver com `from app.i18n import _` (PTW_TOTAL_PARITY_DIRECTIVE.md:171). |
| E13 | `app/core/version.py:1959-1960` + docstring | Bump `VERSION_TUPLE` (minor: novo módulo) e nova entrada `* 4.1.0 — …` na docstring. Restrição: `test_pp_v4_0_0_beta_readiness.py:29-37` exige `"beta"` ou `"alpha"` no `VERSION`; `test_pp_v4_0_0_alpha_milestone.py:33-37` aceita `alpha/beta/rc`. Um bump para `4.1.0` sem sufixo ou com `rc` quebra o readiness — decisão a registrar (ver §6). |
| E14 | `CHANGELOG.md:7-25` | Nova seção `## [4.1.0-…] — AAAA-MM-DD` com `### Added` (módulo, dialog, testes, docs), `### Changed` (`version.py`, `feature_gates.py`, `audit_trail.py`, `main_window.py`, i18n), e atualizar "Standards cobertos (cumulativo)" (181-193). |
| E15 | `docs/` (plano) | Criar `docs/v4.1.0_BACKLOG_AUDIT.md` (antes de codar, v1.7.0_MASTER_PROTOCOL.md:16-23), `docs/v4.1.0_HANDOFF.md` (template `v3.8.0_HANDOFF.md`, com §8 Smoke Test Manual "Para usar RUL, o usuário clica em Análise → …" e §10 limitações declaradas), linha em `SESSION_HANDOFF.md:71-116`, entradas em `SKIPPED_BACKLOG.md` para tudo que for adiado (com origem + justificativa, l. 8-10), linha em `PTW_SURPASSING_MATRIX.md` (vincular à feature 141 "Aging Factor", l. 288, declarando dimensões 1, 3 e 4), lição em `CONTEXT_PRESERVATION_PROTOCOL.md:190-191`. |
| E16 | `docs/research/` (inexistente) | Proposta: `docs/research/rul_isolamento/` com `README.md` (índice + convenção de rotulagem [FATO/NORMA/LITERATURA/REPO/CÁLCULO/HIPÓTESE]), `fichamentos/`, `cross/`, `decisoes/` (ADR curtos). Não versionar PDFs de artigos (clean-room e direitos autorais — LICENSING.md §3/§6); apenas fichamentos e textos próprios. Como `Dockerfile:29` copia `docs/` inteiro para a imagem e não há `.dockerignore`, manter os arquivos pequenos (Markdown) ou criar `.dockerignore` excluindo `docs/research/` — a segunda opção exige ajuste no `test_pp_v2_0_0_docker.py`? Não: esse teste só verifica strings do `Dockerfile` (22-45), não a existência de `.dockerignore` [REPO]. |
| E17 | `tests/` | `tests/test_pp_v4_1_0_rul_prognosis.py` com classes: `TestCase/ResultDataclasses`, `TestGoldenValues` (valores publicados com comentário de fonte; sem golden → `@pytest.mark.skip`, v1.7.0_MASTER_PROTOCOL.md:36), `TestDeterminism` (seed), `TestAuditIntegration` (header + limitações no HTML/PDF), `TestGating` (`set_tier_override("educational")` + `LicenseRequiredError`), `TestDialog` (qapp offscreen, sem `exec()`), `test_main_window_wires_rul_action` (`inspect.getsource`). Cobertura ≥ 80 % (CONTEXT_PRESERVATION_PROTOCOL.md:75). |
| E18 | `.github/workflows/test.yml:66-78` e `lint.yml:57-69` | Acrescentar o novo arquivo de teste à lista explícita do job `test` e o novo módulo backend à lista de imports do job `imports` (que só tem `numpy pydantic PyYAML`); acrescentar `--cov=app.postprocessor.<rul_module>`. |
| E19 | `requirements.txt`, `Dockerfile`, `build/olivas_pro.spec:45-54`, `docs/THIRD_PARTY_NOTICES.md`, `docs/LICENSING.md §4` | Ver política de dependências em §4.7. |
| E20 | `app/plugins/registry.py:40-62` `register_study` | Rota alternativa (plugin) NÃO recomendada para o MVP: o estudo registrado não ganha ação de menu (main_window.py:3248-3300 apenas lista) → violaria a 7ª garantia sem trabalho adicional na GUI [INFERÊNCIA]. |

---

## 4. Convenções obrigatórias — checklist para QUALQUER módulo novo

Cada item cita a fonte que o impõe. Itens marcados (P) são de processo/documentação; (C) de código; (T) de teste/CI.

**4.1 Auditabilidade do laudo (C)**
1. Toda função de cálculo cita norma/fonte + seção + página/equação na docstring e nos comentários (`§seção p. NN`) — CONTEXT_PRESERVATION_PROTOCOL.md:49-52, 136; PTW_TOTAL_PARITY_DIRECTIVE.md:133, 218.
2. Resultado que vai a laudo passa por `make_audit_header(report_kind, inputs, standards_applied, …)` como PRIMEIRO bloco (audit_trail.py:294-327; report_html.py:633-643; report_pdf.py:1096-1104).
3. Cada valor numérico no laudo tem `citation(...)` ao lado (report_html.py:863-919, docstring "Princípio 2").
4. Heurísticas/simplificações do módulo entram em `KNOWN_LIMITATIONS` e são renderizadas por `format_limitations_html`/`_build_limitations_page` (audit_trail.py:335-337; README.md:135-151 lista as 7 atuais como "declaradas em todos os laudos").
5. Normas usadas entram em `STANDARDS_CATALOG` com título completo (audit_trail.py:71-87) e na lista "Standards cobertos" do `CHANGELOG.md:181-193`.
6. Fallbacks, clamps e limitações tocadas em runtime são logados com `get_logger(__name__)` em nível WARNING (logging_config.py:33-37).
7. Entradas físicas validadas em `__post_init__` (padrão `ArcFlashCase`, version.py: histórico 0.92.2; `reliability.py` valida `mtbf/mttr > 0` — ver `tests/test_pp_v3_6_0_reliability.py:86-90`).

**4.2 Gating comercial (C)**
8. Feature nova declarada em `Feature` + `FEATURE_TIER_MAP` com tier ≥ `demo` (feature_gates.py:67-96; teste sprint1:368-375); nunca usar string literal fora da classe (docstring 24-26).
9. Ponto de entrada caro decorado com `@requires_feature(Feature.X)`; a GUI captura `LicenseRequiredError` (feature_gates.py:104-133).
10. Relatórios HTML/PDF do módulo decorados com `@requires_feature(Feature.PDF_PROFESSIONAL)` (report_html.py:601, 1046).
11. Testes de gate: bloqueado em `educational`, liberado em `enterprise` (sprint1:380-460); lembrar que o `conftest` força `enterprise` (conftest.py:28-42).

**4.3 Acessibilidade GUI — "7ª garantia" (C/P)** — confirmada em `docs/PTW_TOTAL_PARITY_DIRECTIVE.md:243-261` (§8.3), `docs/SESSION_HANDOFF.md:37-43`, `docs/CONTEXT_PRESERVATION_PROTOCOL.md:66-70,134`, `docs/SKIPPED_BACKLOG.md:171-172`.
12. Todo módulo backend tem ação no menu `Análise` (ou toolbar/dialog/property panel/paleta) ANTES de fechar o release (critério 9, l. 251).
13. Ação registrada no padrão `addAction("<emoji> <rótulo> (<norma>)...", handler)` + `setStatusTip` (main_window.py:529-537); handler `_on_show_<x>(self, *_qt_args)` com import lazy do diálogo (3070-3080); assinatura com `*_qt_args` obrigatória (comentário 2418-2426).
14. Deep GUI audit pós-sprint cruzando `app/gui/main_window.py` (critério 10, l. 252; template `docs/v3.1.0_GUI_AUDIT.md`).
15. Smoke test manual no handoff: "Para usar X, o usuário clica em…" (critério 11, l. 253; exemplo `v3.8.0_HANDOFF.md:144-152`).
16. Diálogo modal (`setModal(True)`), `QFormLayout`, spin boxes com `setRange/setValue/setSuffix`, rótulos citando norma (analysis_dialogs.py:81-177; 661-745); resultado via `show_result_dialog` ou `QPlainTextEdit` interno; `try/except` defensivo (reliability_dialog.py:198-226; SESSION_HANDOFF.md:286).
17. Após estudo, refrescar docks/datablocks (main_window.py:3476-3486; analysis_dialogs.py:955-958) — best-effort.

**4.4 i18n (C/T)**
18. Strings de UI novas passam por `_()` (PTW_TOTAL_PARITY_DIRECTIVE.md:171) e ganham chaves idênticas em `en.json` E `es.json` (readiness:54-74); valores não vazios (85-98); chave = string PT literal (en.json l. 9-…).
19. Docstrings e comentários permanecem em PT (SESSION_HANDOFF.md:281).

**4.5 Versionamento, CHANGELOG e docs canônicos (P)**
20. `version.py`: bump de `VERSION_TUPLE` + entrada na docstring; não bumpar antes dos 8 critérios de aceite (PTW_TOTAL_PARITY_DIRECTIVE.md:128-142); manter sufixo `alpha/beta/rc` enquanto os testes de readiness/milestone existirem (§1.12).
21. `CHANGELOG.md`: seção Keep-a-Changelog com Added/Changed/Fixed e contagem de testes (7-25, 76-84).
22. `docs/vX.Y.Z_BACKLOG_AUDIT.md` antes de codar; `docs/vX.Y.Z_HANDOFF.md` ao fechar (template `v3.8.0_HANDOFF.md`, 12 seções); atualizar `SESSION_HANDOFF.md` (§3.2 tabela + §5), `SKIPPED_BACKLOG.md` (origem + justificativa; cap 15), `PTW_SURPASSING_MATRIX.md` (≥ 1 dimensão de superação), `CONTEXT_PRESERVATION_PROTOCOL.md §7` (lições) — CONTEXT_PRESERVATION_PROTOCOL.md:140-147; PTW_TOTAL_PARITY_DIRECTIVE.md:232-235.
23. Nunca editar arquivos da "lista TRAVADA" (SESSION_HANDOFF.md:121-143): arc-flash core, CT saturation, plugins core, DAPPER, `app/i18n/__init__.py`, `iec61850_client.py`, `license_key.py`, `telemetry.py`, `Dockerfile`, `docker-compose.yml`. Consequência: novas traduções vão nos JSON, não no `__init__.py`; mudanças de dependência NÃO podem tocar o `Dockerfile` sem decisão explícita do autor.
24. Restore point local em `restore_points/<versao>_baseline/` antes de tocar código (v1.7.0_MASTER_PROTOCOL.md:49-56; gitignored, `.gitignore` l. "/restore_points/").
25. Read-then-Edit; "novos arquivos > edits cirúrgicos"; campos novos `Optional[...] = None` (CONTEXT_PRESERVATION_PROTOCOL.md:55-58).

**4.6 Testes e CI (T)**
26. Arquivo `tests/test_pp_v<MAJOR>_<MINOR>_<PATCH>_<slug>.py`; `QT_QPA_PLATFORM=offscreen` + fixture `qapp`; sem `dlg.exec()` (test.yml:51-61).
27. Golden values com comentário de fonte; sem fonte → `skip` (v1.7.0_MASTER_PROTOCOL.md:34-36); ≥ 5 testes e ≥ 80 % de cobertura do módulo (PTW_TOTAL_PARITY_DIRECTIVE.md:135; CONTEXT_PRESERVATION_PROTOCOL.md:75).
28. Teste de wiring de menu por `inspect.getsource(main_window)` (test_pp_v3_6_0_reliability.py:286-296).
29. Sweep targeted verde antes do bump (`pytest tests/test_pp_v4_*.py -q`, README.md:176-179).
30. Adicionar o arquivo de teste a `test.yml:66-78` e o módulo a `lint.yml:57-69`; o módulo deve importar sem PySide6 e sem matplotlib no nível de módulo (job `imports` instala só numpy/pydantic/PyYAML).
31. `ruff check --select=E9,F63,F7,F82` limpo (lint.yml:32) — apenas erros graves; formatação não bloqueia.

**4.7 Política de dependências novas (C/P)**
32. Dependências já permitidas (declaradas e instaladas no CI/Docker): `numpy`, `matplotlib`, `pydantic`, `PyYAML`, `openpyxl`, `PySide6`, `anthropic`, `pytest` (requirements.txt:1-8). `scipy`, `pandas`, `scikit-learn`, `lifelines`, `statsmodels`, `torch` são NOVAS (ausentes em `app/`, `requirements.txt`, `Dockerfile`, specs PyInstaller e `THIRD_PARTY_NOTICES.md`).
33. Regra vigente: "stdlib quando possível" (PTW_TOTAL_PARITY_DIRECTIVE.md:150); precedente do Monte Carlo usa `random`/`math` da stdlib mesmo com numpy disponível (reliability_monte_carlo.py:20-22); os PDFs evitaram reportlab (report_pdf.py:6-10). Uma nova dependência é "mudança de alto impacto" com justificativa obrigatória (CONTRIBUTING_ATP_STUDIO.txt:219-229).
34. Se inevitável: (a) `requirements.txt` com versão mínima; (b) seção em `docs/THIRD_PARTY_NOTICES.md` e linha no mapa de licenças `docs/LICENSING.md §4`; (c) `hiddenimports` em `build/olivas_pro.spec` e `olivas_community.spec`; (d) `lint.yml:55` (job imports) e cobertura em `test.yml`; (e) `Dockerfile` rebuild (arquivo TRAVADO — decisão do autor); (f) import lazy dentro de função para não quebrar o smoke import; (g) `pytest.importorskip` nos testes (padrão `test_pp_v1_4_4_ct_study_plots.py:20-24`).
35. Recomendação para o MVP de RUL [HIPÓTESE]: implementar com `math`/`random`/`statistics` (stdlib) + `numpy` (já permitido, uso lazy) — ajuste de Arrhenius/potência inversa por mínimos quadrados em log, bootstrap para IC e contagem rainflow são implementáveis sem scipy. Reservar scipy/lifelines para uma fase posterior, condicionada aos passos do item 34.

---

## 5. Lacunas identificadas

| # | Lacuna | Evidência |
|---|---|---|
| L1 | Não existe `docs/research/`; `docs/` é plano (93 arquivos) e nomeado por release (`v<X.Y.Z>_<TIPO>.md`) — não há lugar convencionado para revisão bibliográfica/fichamentos | [CÁLCULO PRÓPRIO: `ls docs`] |
| L2 | Os geradores de laudo são monomórficos (`BusPipelineReport`): não há interface genérica "seção de laudo" reutilizável por outros estudos; `_BUS_PIPELINE_*` e `_build_audit_cover_page` derivam `report_kind` de `bus_id` | report_html.py:80-103, 695-728; report_pdf.py:85-99, 127-178 |
| L3 | `run_pipeline_report_export` não coleta `responsible_engineer/crea/art/notes` na GUI — os campos do audit header ficam "(a preencher)" apesar do README prometer "preencher CREA + ART" | analysis_dialogs.py:1048-1058; README.md:87 |
| L4 | `save_pdf_report` não tem `@requires_feature` próprio (gate só via `make_audit_header`) — assimetria com `save_html_report` | report_pdf.py:1054; report_html.py:1046 |
| L5 | Nenhum uso de `is_feature_available` na GUI: menus não são acinzentados por tier; `LicenseRequiredError` chega ao usuário como exceção genérica | grep em `app/gui` (0 ocorrências); reliability_dialog.py:226 |
| L6 | i18n: apenas 2 arquivos de GUI importam `app.i18n`; rótulos do menu `Análise` são literais PT; diretriz "i18n desde dia-0" não é verificada por teste | §1.8; PTW_TOTAL_PARITY_DIRECTIVE.md:171 |
| L7 | `register_study` promete aparecer no menu `Análise`, mas só é listado em diálogo read-only | registry.py:43-44 vs main_window.py:3248-3300 |
| L8 | `KNOWN_LIMITATIONS` e `STANDARDS_CATALOG` são dicionários globais únicos — sem namespace por módulo; chaves de módulos diferentes convivem no mesmo dict (risco de colisão de nomes) | audit_trail.py:73-87, 338-382 |
| L9 | Timestamp do audit header sem fuso (`datetime.now()`); checksum inclui o objeto `report` inteiro (não separa entradas de saídas) — "Checksum (inputs)" na verdade hasheia o resultado consolidado | audit_trail.py:320-321; report_html.py:719-722 (`inputs=r`, onde `r` é o relatório) |
| L10 | CI público executa lista fixa de 12 arquivos; sweep total (5568 testes) só local com display | test.yml:51-78; README.md:165-179 |
| L11 | Testes de readiness/milestone exigem sufixo `alpha/beta/rc` e prefixo `4.` na versão — bloqueiam um release final `4.x.y` sem revisar esses testes | readiness:29-37; alpha_milestone:28-37 |
| L12 | Não há `.dockerignore`; `Dockerfile` copia `docs/` inteiro; `Dockerfile` está na lista TRAVADA | Dockerfile:27-29; SESSION_HANDOFF.md:140-143 |
| L13 | `PTW_TOTAL_PARITY_DIRECTIVE.md` tem §8.4 antes de §8.3 (ordem invertida) — risco de leitura equivocada de "§8.3" | l. 224-261 |
| L14 | Nenhuma feature PTW mapeada cobre RUL/prognóstico; a mais próxima é #141 "Aging Factor (5th-order poly)" (T2, ⏳); logo, o RUL deve ser declarado como superação (dim. 1/3/4) e não como paridade | PTW_SURPASSING_MATRIX.md:288; PTW_TUTORIAL_AUDIT_v3.0.3.md:157, 290 |
| L15 | Nenhum código/documento do repositório trata de RUL, prognóstico, Arrhenius, Weibull ou envelhecimento de isolamento de motor (apenas `insulation_class` em catálogos e limites térmicos de cabo) | grep em `app/` e `docs/` (§ leituras) |

---

## 6. Riscos técnicos para o módulo de RUL

| # | Risco | Fonte | Mitigação [HIPÓTESE] |
|---|---|---|---|
| R1 | Violação da 7ª garantia: backend de RUL sem diálogo/menu → release reaberto como draft e item P0 | PTW_TOTAL_PARITY_DIRECTIVE.md:243-261; CONTEXT_PRESERVATION_PROTOCOL.md:66-70 | Entregar backend + `RulPrognosisDialog` + ação de menu + teste `inspect.getsource` no MESMO sprint (E6, E8, E17) |
| R2 | Feature nova mapeada a `educational` (ou não mapeada) quebra `test_tier_hierarchy_educational_blocks_all_paid` ou fica aberta no bundle Community | sprint1:368-375; feature_gates.py:218-224 | Mapear `RUL_PROGNOSIS` a `commercial`/`pro_engineering` (E1) |
| R3 | Anti-alucinação: a premissa "5-7 reignições por ciclo" não consta do Documento A (contexto do orquestrador); codificá-la como constante sem fonte viola CONTEXT_PRESERVATION_PROTOCOL.md:48-52 e v1.7.0_MASTER_PROTOCOL.md:32-38 | idem | Parametrizar `n_reignitions_per_operation` como ENTRADA do usuário (spin box) com default documentado como [HIPÓTESE do usuário]; registrar em `KNOWN_LIMITATIONS` (`rul_reignition_count_user_premise`); golden tests apenas com valores publicados ou `skip` |
| R4 | Dependência nova (scipy/pandas/lifelines) quebra o job `imports` (só numpy/pydantic/PyYAML), incha PyInstaller/Docker e exige `THIRD_PARTY_NOTICES`/`LICENSING` e `Dockerfile` (TRAVADO) | lint.yml:50-55; build/README.md ("180-250 MB"); SESSION_HANDOFF.md:140-143 | Stdlib + numpy lazy (item 35); se necessário, seguir item 34 integralmente |
| R5 | Módulo importar `matplotlib`/`PySide6` no topo → falha no smoke import sem GUI e no healthcheck Docker | lint.yml:56-70; Dockerfile:37-38 | Separar `app/postprocessor/<rul>.py` (puro) de `app/gui/<rul>_dialog.py`; plots com import lazy (padrão report_html.py:175) |
| R6 | Hash de inputs com séries temporais longas (formas de onda ATP) → JSON gigante e hash lento; `_to_jsonable` faz `repr` de objetos desconhecidos (numpy arrays viram `repr` truncado → hash não determinístico entre versões do numpy) | audit_trail.py:164-191 | Hashear um resumo determinístico (parâmetros do caso + estatísticas por evento + `sha256` do arquivo PL4) e declarar isso em `KNOWN_LIMITATIONS` |
| R7 | Reprodutibilidade estatística (IC por bootstrap/MC): sem `seed` explícito o laudo muda a cada execução, contradizendo o princípio "mesmo input → mesmo checksum/relatório" | audit_trail.py:135-139; reliability_monte_carlo.py:20-22, 250 (`seed: int | None = 42`) | Parâmetro `seed` obrigatório no caso (default 42), incluído no payload do checksum; usar `random.Random(seed)` |
| R8 | Testes de readiness/milestone fixam sufixo de pré-release e prefixo `4.`; bump de versão pode quebrar 3 testes do subset CI | readiness:29-37; alpha_milestone:28-37 | Manter `PRE_RELEASE` (`beta`/`rc` — nota: readiness aceita só `alpha`/`beta`) ou atualizar os testes na mesma release, registrando no handoff |
| R9 | Paridade i18n: adicionar chave só em `en.json` quebra `test_en_es_key_parity`; valor vazio quebra `test_no_empty_translations` | readiness:54-98 | Adicionar pares completos EN e ES em conjunto |
| R10 | `dlg.exec()` em testes novos → deadlock em CI headless | test.yml:51-61 | Instanciar diálogo e chamar handlers diretamente (padrão test_pp_v3_8_0_reliability_mc.py:205-226) |
| R11 | Colisão/namespace em `KNOWN_LIMITATIONS`/`STANDARDS_CATALOG` globais; `README.md:65-66` anuncia "13 normas" e "7 limitações" — números que mudam ao estender | audit_trail.py:73-87, 338-382; README.md:65-66, 135-151 | Prefixo `rul_` nas chaves; atualizar README e CHANGELOG "Standards cobertos" |
| R12 | Novo teste não roda no CI público se não for adicionado à lista explícita; cobertura não medida | test.yml:66-90 | E18 |
| R13 | Laudo de RUL sem os campos de responsabilidade técnica (L3) — para um prognóstico com implicação de manutenção/segurança, o bloco CREA/ART em branco enfraquece a defensabilidade que o produto promete | README.md:37-47; report_pdf.py:292-298 | Diálogo de exportação do RUL coleta engenheiro/CREA/ART/notas e os repassa a `save_*_report` |
| R14 | Documentos de pesquisa em `docs/` entram na imagem Docker e no bundle (sem `.dockerignore`; specs excluem só a lista clean-room) | Dockerfile:29; build/README.md | E16: apenas Markdown pequeno; sem PDFs de terceiros; considerar `.dockerignore` (não toca o `Dockerfile`) |
| R15 | Rotulagem de fonte: a superação declarada na `PTW_SURPASSING_MATRIX` exige citar manual/norma; para RUL não há feature PTW de referência (L14) | PTW_TOTAL_PARITY_DIRECTIVE.md:50-52, 133-134 | Declarar como "feature além do PTW" no bloco final da matriz (como #124-128, l. 114-118), com dimensões 1, 3, 4 e citações dos artigos fichados |

---

## Anexo A — Assinaturas públicas a reutilizar (resumo para o projetista)

```python
# app/postprocessor/audit_trail.py
citation(standard: str, section: str | None = None, equation: str | None = None, extra: str | None = None) -> str            # l. 90
compute_input_checksum(payload: Any) -> str                                                                                    # l. 135
class AuditHeader(report_kind, software_name, software_version, timestamp_iso, input_checksum, standards_applied,
                  responsible_engineer="", crea_number="", art_number="", notes="")  .to_text() / .to_html()                   # l. 199
@requires_feature(Feature.AUDIT_TRAIL_SHA256)
make_audit_header(report_kind: str, inputs: Any, standards_applied: list[str], *, responsible_engineer="", crea_number="",
                  art_number="", notes="", software_name="Olivas Power System Studio") -> AuditHeader                          # l. 294
format_limitations_block(applied_keys: list[str]) -> str   /   format_limitations_html(applied_keys: list[str]) -> str         # l. 385 / 408

# app/commercial/feature_gates.py
class Feature: AUDIT_TRAIL_SHA256, PDF_PROFESSIONAL, AI_LAUDO, RELIABILITY_MC, ARC_FLASH_MC, POWER_FLOW_MC, ...              # l. 67
FEATURE_TIER_MAP: Dict[str, str]                                                                                               # l. 84
class LicenseRequiredError(RuntimeError)  (feature, required_tier, current_tier)                                               # l. 104
set_tier_override(tier: str | None) -> None ; current_tier() -> str ; is_feature_available(feature) -> bool                    # l. 144 / 156 / 211
require_feature(feature) -> None ; requires_tier(tier) ; requires_feature(feature)                                             # l. 227 / 250 / 289

# app/postprocessor/study_cache.py
class StudyCache: has_/get_/set_<study>(id, result, input_hash) ; invalidate_bus ; invalidate_all ; status_summary            # l. 123
hash_study_inputs(project, bus_id: str, config: Any) -> str                                                                    # l. 310

# app/gui/analysis_dialogs.py
show_result_dialog(parent, title: str, text: str, *, width=800, height=600) -> None                                            # l. 36
run_<x>_analysis(parent, *, project=None, bus_id: str = "", **kwargs) -> None                                                  # l. 179 / 554 / 763 / 867

# app/gui/main_window.py
_on_show_<x>(self, *_qt_args) -> None  (import lazy + dlg.exec())                                                              # l. 3070
_current_pp_project(self) -> PpProject | None                                                                                  # l. 2406
_ensure_plot_dock(self, kind: str)                                                                                             # l. 1060
_dispatch_analysis(self, kind: str, bus_id: str, pp_project) -> None                                                           # l. 3428

# app/i18n
_(text: str) -> str ; set_locale(locale) ; get_locale() ; get_coverage_stats() -> dict                                         # l. 107 / 79 / 97 / 158

# app/core/version.py
VERSION_TUPLE, PRE_RELEASE, VERSION, PRODUCT_NAME, parse_version(s), is_newer(remote, local=VERSION)                           # l. 1959-1993
```

## Anexo B — Comandos usados para contagens

```bash
sed -n '442,690p' app/gui/main_window.py | grep -c "analysis_menu.addAction("     # 26
ls tests/test_pp_v*.py | wc -l                                                     # 171
grep -c '":' app/i18n/translations/en.json app/i18n/translations/es.json           # 138 / 138
grep -rln "import scipy\|from scipy\|import pandas\|from pandas\|import sklearn\|reportlab\|lifelines\|statsmodels" app   # (vazio)
grep -rn "requires_feature(" app --include=*.py | grep -v feature_gates.py         # 6 usos
grep -rln "from app.i18n import" app --include=*.py                                # 3 arquivos (main_window, locale_picker, i18n)
ls docs/research                                                                    # inexistente
ls pyproject.toml setup.cfg ruff.toml pytest.ini .dockerignore                     # inexistentes
```
