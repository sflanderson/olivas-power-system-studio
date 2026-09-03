# Mapeamento da área "confiabilidade_eval_montecarlo" — Olivas Power System Studio

Repositório: `/home/user/olivas-power-system-studio` (versão declarada em `app/core/version.py` l. 1959–1968: `VERSION_TUPLE = (4, 0, 0)` + pré-release "beta"). Finalidade deste mapeamento: subsidiar o projeto de um módulo de prognóstico de degradação de isolamento (RUL com intervalo de confiança) para motores de indução de média tensão (MT), integrado ao padrão de "estudo modular" e ao Monte Carlo já existentes.

Convenção de rotulagem usada neste documento:

- **[F]** fato do repositório — verificado por leitura de código na linha citada;
- **[I]** inferência do mapeador a partir do código;
- **[H]** hipótese de projeto (não verificada; a validar antes de implementar).

Todas as linhas citadas referem-se ao estado atual do repositório (commit `26d9248`, `git log` de 2026-09-02).

---

## 1. Inventário de arquivos e símbolos

### 1.1 `app/postprocessor/reliability.py` (295 linhas) — índices IEEE 1366 e helpers IEEE 493 [F]

| Símbolo | Assinatura / campos | Linhas |
|---|---|---|
| `HOURS_PER_YEAR: float = 8760.0` | constante (ano não bissexto) | 35 |
| `class InterruptionEvent` (`@dataclass`) | `customers_interrupted: int`, `duration_hours: float`, `description: str = ""`; `__post_init__` valida `>= 0` e `> 0` | 43–70 |
| `class ComponentReliability` (`@dataclass`) | `name: str`, `mtbf_hours: float`, `mttr_hours: float`; propriedades `failure_rate_per_year` (= 8760/MTBF), `forced_outage_rate` (q = MTTR/(MTBF+MTTR)), `availability` | 73–118 |
| `class ReliabilityIndices` (`@dataclass`) | `saifi, saidi, caidi, asai: float`, `total_customers: int`, `n_events: int = 0`; `as_text_report()` | 121–158 |
| `calculate_saifi(events, total_customers) -> float` | Σ N_i / N_T | 166–188 |
| `calculate_saidi(events, total_customers) -> float` | Σ r_i·N_i / N_T | 191–211 |
| `calculate_caidi(saifi, saidi) -> float` | SAIDI/SAIFI; 0 se SAIFI = 0 | 214–221 |
| `calculate_asai(saidi) -> float` | (8760 − SAIDI)/8760, clamp [0,1] | 224–231 |
| `calculate_indices(events, total_customers) -> ReliabilityIndices` | one-shot | 234–251 |
| `system_failure_rate_series(components) -> float` | Σ λ_i | 259–267 |
| `system_unavailability_series(components) -> float` | Σ q_i (aprox. q pequeno) | 270–279 |
| `parallel_unavailability(components) -> float` | Π q_i | 282–295 |

Observações [F]: o módulo é puro (sem imports do app), sem gating comercial, sem dependência de projeto/topologia. O modelo de falha é implícito: taxa constante λ (exponencial). Não há função de risco h(t), nem Weibull, nem envelhecimento.

### 1.2 `app/postprocessor/reliability_monte_carlo.py` (346 linhas) — presets IEEE 493 e MC de índices [F]

| Símbolo | Assinatura / campos | Linhas |
|---|---|---|
| imports | `Feature, requires_feature` de `app.commercial.feature_gates`; `HOURS_PER_YEAR, ComponentReliability, InterruptionEvent, ReliabilityIndices, calculate_indices` de `reliability` | 33–40 |
| `class _IEEE493Preset` (`@dataclass(frozen=True)`) | `equipment_type: str`, `mtbf_hours: float`, `mttr_hours: float`, `description: str = ""` | 48–54 |
| `IEEE493_PRESETS: tuple[_IEEE493Preset, ...]` | 10 linhas (ver §1.2.1) | 57–118 |
| `get_preset(equipment_type) -> _IEEE493Preset` | `KeyError` se ausente | 121–129 |
| `list_preset_types() -> list[str]` | | 132–134 |
| `make_component_from_preset(name, equipment_type) -> ComponentReliability` | | 137–147 |
| `class MCResult` (`@dataclass`) | `n_simulations: int`, `n_years_per_run: int`, `saifi_distribution / saidi_distribution / caidi_distribution / asai_distribution: list[float]`; métodos `percentile(dist_name, p)` (interpolação linear), `confidence_interval(dist_name, alpha=0.10)`, `median`, `mean`, `as_text_report()` | 155–239 |
| `run_monte_carlo(components, *, customers_per_component=100, total_customers=1000, n_years=10, n_simulations=100, mttr_lognormal_sigma=0.5, seed=42) -> MCResult` | decorada com `@requires_feature(Feature.RELIABILITY_MC)` | 242–346 |

Algoritmo de `run_monte_carlo` [F]: `rng = random.Random(seed)` (l. 290); para cada componente, tempos entre falhas amostrados por inversa da CDF exponencial `-ln(U)/λ` com λ = 1/MTBF em h⁻¹ (l. 302–313); duração de reparo lognormal com μ = ln(MTTR) − σ²/2 e piso 0,01 h (l. 314–318); cada falha vira `InterruptionEvent` com `customers_per_component` clientes (l. 319–323); índices por corrida normalizados por `n_years` (l. 326–337). Declarações de limitação no docstring: falhas independentes, sem modo comum, "deferred multi-state Markov" (l. 21–23).

#### 1.2.1 Existe taxa de falha de motor MT nos presets? [F]

Sim, uma única linha, `induction_motor_400hp` (l. 94–99):

| Campo | Valor no código | Comentário no código |
|---|---|---|
| `mtbf_hours` | 43 800 h | `# λ ≈ 0.20/year` |
| `mttr_hours` | 144 h | `# 6 days` |
| `description` | "Induction motor 100-1000HP, 600V-15kV" | — |

Valores derivados (calculados por este mapeador executando o módulo): λ = 8760/43 800 = 0,2000 falhas/ano; q = 144/(43 800+144) = 3,28×10⁻³; A = 0,99672.

Ressalvas de anti-alucinação:

- [F] O docstring afirma origem "IEEE Std 493-2007 (Gold Book) Tab 3-1" (l. 5, 14, 44); `reliability.py` cita "IEEE 493-2007 §3.4" (l. 17, 111, 262, 277, 285). Nenhuma das duas referências foi verificada contra o texto da norma neste mapeamento — a norma não está disponível no ambiente. Tratar os números como "valores típicos codificados no repositório" e, ao usá-los em texto acadêmico, escrever [INSERIR CITAÇÃO] até conferir tabela e página.
- [I] A faixa "100–1000 HP, 600 V–15 kV" mistura BT e MT numa única classe; não há discriminação por classe de tensão (2,3 / 4,16 / 6,6 / 13,8 kV), por tipo de isolamento (VPI vs. resin-rich), por idade ou por regime de partidas. Para prognóstico de isolamento de estator MT esta granularidade é insuficiente.
- [F] Não há preset para disjuntor a vácuo especificamente; o mais próximo é `circuit_breaker_metalclad` (l. 70–75: MTBF 146 000 h, MTTR 90 h, "Metal-clad medium-voltage breaker (5-15kV)").
- [F] A GUI (`app/gui/reliability_dialog.py` l. 209–215) usa cinco presets fixos, incluindo `M1 = induction_motor_400hp`, sem ler o projeto.

### 1.3 `app/postprocessor/equipment_eval.py` (472 linhas) — modelo de dados de avaliação [F]

| Símbolo | Assinatura / campos | Linhas |
|---|---|---|
| `class EquipmentInstance` (`@dataclass(frozen=True)`) | `equipment_id: str`, `equipment_type: str`, `rated_voltage_kV: float`, `rated_continuous_A: float`, `rated_interrupt_kA: float = 0.0`, `rated_asym_kA: float = 0.0`, `bus_voltage_kV: float = 0.0`, `duty: dict = {}`, `model_ref: Optional[str] = None`; tipos válidos `{"breaker","cable","transformer","generator","motor","bus","fuse","contactor"}` (l. 153–156); `get_duty(key, default)` (l. 163) | 62–165 |
| `class EvaluationReport` (`@dataclass(frozen=True)`) | `equipment_id`, `equipment_type`, `results: tuple[RuleResult, ...]`; métodos `passes()`, `warnings()`, `failures()`, `not_applicables()`, `passes_all()`, `has_failures()`, `has_warnings()`, `count_by_severity()`, `overall_status()` | 173–288 |
| `evaluate_equipment(equipment, rules, context=None) -> EvaluationReport` | aceita `RuleSet` ou `list[Rule]`; `full_context = dict(equipment.duty)` atualizado por `context` (context prevalece) | 296–341 |
| `evaluate_project(equipments, rules, context=None) -> list[EvaluationReport]` | | 344–360 |
| `_TYPE_MAP: dict[str, str]` | `"MOTOR": "motor"` (l. 381); `"VCB"/"VCB3": "breaker"` (l. 372–373) | 370–385 |
| `build_equipment_from_project(project, *, default_continuous_A=1200.0, default_interrupt_kA=25.0, default_voltage_kV=13.8) -> list[EquipmentInstance]` | extrai ratings por heurística textual das properties (l. 432–447); **`duty={}` com comentário "caller fills via study results"** (l. 458) | 388–463 |

Chaves de `duty` documentadas (l. 98–105): `I_load_A`, `I_design_A`, `I_fault_kA`, `ip_kA`, `V_drop_pct`. [I] O `duty` é um `dict` opaco — é o ponto natural para injetar grandezas de prognóstico (`rul_p50_years`, `life_consumed_pct` etc.) sem alterar a dataclass.

### 1.4 `app/postprocessor/equipment_eval_rules.py` (523 linhas) — os 9 critérios PTW [F]

| Símbolo | Aplicável a | Linhas |
|---|---|---|
| `_na(rule_id, target_id, msg, citation) -> RuleResult` | helper NOT_APPLICABLE | 54–60 |
| `_severity_from_pct(pct, warn_at_pct=70.0) -> RuleSeverity` | `>100` FAIL; `≥70` WARN; senão PASS | 63–76 |
| `_eval_voltage_rating` | todos os tipos | 84–121 |
| `_eval_interrupt_duty` | breaker, fuse | 129–165 |
| `_eval_asym_duty` | breaker | 173–207 |
| `_eval_load_flow_current` | cable, breaker, fuse, transformer (**motor excluído**, l. 225) | 215–249 |
| `_eval_design_load` | cable, breaker, transformer | 257–290 |
| `_eval_generator_capacity` | generator | 298–327 |
| `_eval_bus_voltage_drop` | bus | 335–362 |
| `_eval_branch_voltage_drop` | cable | 365–387 |
| `_eval_device_voltage_drop` | breaker, contactor, fuse | 390–419 |
| `RULE_EQ_*` (9 objetos `Rule`) | `applicable_to=(EquipmentInstance,)` | 427–497 |
| `PTW_EQUIPMENT_EVALUATION: RuleSet` | 9 regras | 505–519 |
| `ALL_PTW_EQUIPMENT_RULES: list[Rule]` | | 523 |

Verificação executada por este mapeador [F]: um `EquipmentInstance(equipment_type="motor", duty={"I_load_A": 150})` avaliado por `PTW_EQUIPMENT_EVALUATION` retorna 1 PASS (`EQ-VOLTAGE-RATING`) e 8 NOT_APPLICABLE. Ou seja, **para motores o dashboard atual é quase vazio** — há espaço para critérios novos sem colisão.

### 1.5 `app/postprocessor/equipment_eval_dashboard.py` (356 linhas) — HTML/CSV [F]

| Símbolo | Comportamento | Linhas |
|---|---|---|
| cores/labels | `_COLOR_*`, `_color_for_severity`, `_label_for_severity` | 43–72 |
| `_CSS` | CSS inline, sem dependências | 80–133 |
| `generate_html_dashboard(reports, project_title=..., norm_reference=...) -> str` | colunas = `rule_id`s únicos na ordem de aparição (l. 171–177); célula mostra label + `f" {evaluated_value:.0f}%"` (l. 254–255); tooltip = `message` | 141–282 |
| `_empty_html(title)` | | 285–294 |
| `export_csv(reports, sep=";") -> str` | colunas `<rule_id>_severity`, `<rule_id>_value_pct` (l. 325–327) | 302–356 |

[I] Como as colunas são derivadas dinamicamente dos `rule_id`s, uma regra nova aparece no dashboard sem alterar este arquivo. A única convenção implícita é que `evaluated_value` seja interpretável como percentual (formatação `:.0f%`, cabeçalho `_value_pct`).

### 1.6 `app/postprocessor/coord_rules.py` (409 linhas) — Rule Engine reutilizado pela avaliação [F]

| Símbolo | Campos / métodos | Linhas |
|---|---|---|
| `class RuleSeverity(str, Enum)` | `PASS="pass"`, `WARN="warn"`, `FAIL="fail"`, `NOT_APPLICABLE="n/a"` | 56–76 |
| `class RuleResult` (frozen) | `rule_id, target_id, severity, message, citation`, `evaluated_value: Optional[float] = None`, `expected_range: Optional[tuple] = None`; `is_pass/is_fail/is_warn/is_not_applicable` | 84–132 |
| `class Rule` (frozen) | `rule_id, description, citation, applicable_to: tuple, eval_func: Callable, severity_default`; `applies_to(target)`, `evaluate(target, context)` (retorna N/A se `isinstance` falha, l. 214–228) | 140–229 |
| `class RuleSet` (frozen) | `name, norm_reference, rules: tuple`; valida tipos e unicidade de `rule_id` (l. 272–290); `get_rule` | 237–300 |
| `class RuleEngine` | `apply_rule`, `apply_ruleset`, `apply_rulesets`, `filter_by_severity`, `group_by_severity`, `count_by_severity`, `has_failures`, `summary_line` | 308–409 |

### 1.7 `app/postprocessor/study_cache.py` (338 linhas) — cache de estudos por barra [F]

| Símbolo | Assinatura / campos | Linhas |
|---|---|---|
| `class PrerequisiteError(Exception)` | `(study, bus_id, missing: list[str])` | 74–94 |
| `class CacheEntry` (frozen) | `result: Any`, `input_hash: str`; `is_valid_for(current_hash)` | 102–114 |
| `class StudyCache` (`@dataclass`) | campos `_sc`, `_coord`, `_arc_flash: dict[str, CacheEntry]`; `_power_flow: Optional[CacheEntry]` (1 por projeto); `_motor_starting: dict[str, CacheEntry]` (chave `motor_id`); `_ct_saturation: dict[str, CacheEntry]` (chave `ct_tag`) | 122–143 |
| SC | `has_sc`, `get_sc`, `get_sc_if_valid(bus_id, current_hash)`, `set_sc` (invalida `_coord` e `_arc_flash` do bus, l. 164–166) | 147–166 |
| Coord | `has_coord`, `get_coord`, `get_coord_if_valid`, `set_coord` (invalida `_arc_flash`, l. 192) | 170–192 |
| Arc-flash | `has_arc_flash`, `get_arc_flash`, `get_arc_flash_if_valid`, `set_arc_flash` | 196–216 |
| PF | `has_pf`, `get_pf`, `get_pf_if_valid`, `set_pf` | 220–235 |
| Motor starting | `has_motor_starting(motor_id)`, `get_motor_starting`, `set_motor_starting` (**sem variante `_if_valid`**) | 239–251 |
| CT saturation | `has_ct_saturation`, `get_ct_saturation`, `set_ct_saturation` | 255–267 |
| `invalidate_bus(bus_id)` | remove sc/coord/arc_flash/motor_starting/ct_saturation da chave | 271–277 |
| `invalidate_all()` | | 279–286 |
| `status_summary(bus_id) -> dict[str, str]` | só `sc`, `coord`, `arc_flash` | 290–302 |
| `hash_study_inputs(project, bus_id, config) -> str` | SHA256 (via `audit_trail.compute_input_checksum`) de **todos** os componentes (tipo, nome, x, y, rotação, mirror, props) + wires + `bus_id` + `config` | 310–338 |

### 1.8 `app/postprocessor/studies/` — padrão de "estudo modular" [F]

`studies/__init__.py` (68 linhas): contrato declarado no docstring (l. 15–23) — cada módulo expõe `run(project, bus_id, *, cache=None, config=None, auto_run_prereqs=True)` que (1) checa cache, (2) checa/auto-roda pré-requisitos ou lança `PrerequisiteError`, (3) computa, (4) grava no cache, (5) devolve dataclass tipada. Exporta `short_circuit`, `coordination`, `arc_flash_study` e seus tipos de resultado (l. 40–53, `__all__` l. 55–68). **`demand_load` e `voltage_drop` não são exportados** pelo pacote.

| Módulo | Resultado (frozen) | `run(...)` | Núcleo | Pré-requisitos |
|---|---|---|---|---|
| `short_circuit.py` (378) | `ShortCircuitStudyResult` l. 64–99: `bus_id, rated_voltage_kV, Ik_pp_kA, ip_kA, Ib_kA, Ik_steady_kA, kappa, r_over_x, voltage_factor_c, z_thevenin_real_ohm, z_thevenin_imag_ohm, n_sc_sources, sources_summary, n_neighbors, topology_chains, asymmetric_fault_result, decay_result, kappa_method_used, warnings` | l. 107–168 (`use_multi_hop`, `pre_fault_voltage_pu`) | `_compute_short_circuit` l. 176–378 | nenhum |
| `coordination.py` (232) | `CoordinationStudyResult` l. 72–92: `relay_suggestions, coordination_clearing_time_ms, effective_clearing_time_ms, has_AFD, sc_input_Ik_pp_kA, sc_input_kappa, warnings` | l. 100–170 | `_compute_coordination` l. 178–232 | SC |
| `arc_flash_study.py` (244) | `ArcFlashStudyResult` l. 142–164: `status: str = "computed"` (ou `"out_of_scope"`, `"no_clearing_time"`), `incident_energy_cal_cm2, arc_flash_boundary_mm, ppe_category, sc_input_Ibf_kA, coord_clearing_time_ms, out_of_scope_reason, warnings` | l. 172–250 | `_compute_arc_flash` l. 258–312 (try/except ValueError → out_of_scope l. 283–299) | SC + Coord |
| `voltage_drop.py` (326) | `VoltageDropResult` l. 85–140 (inclui campo `citation` l. 110–113 e `summary()`) | `run(project, *, cache=None, limit_pct, power_factor, default_segment_length_m)` l. 148–197 — **cache é stub** (`if False`, l. 187) | l. 205–326 | nenhum |
| `demand_load.py` (329) | `LoadEntry` l. 48–69, `CategoryResult` l. 77–93, `DemandReport` l. 96–173 | **não segue o contrato `run`**: `compute_demand(entries) -> DemandReport` l. 232–329, sem cache | — | nenhum |

Estrutura interna canônica (ex.: `arc_flash_study.run`) [F]: `h = hash_study_inputs(project, bus_id, ("arc_flash", config, ...))` (l. 203–206) → `cache.get_arc_flash_if_valid(bus_id, h)` (l. 207–209) → coleta de prereqs via `cache.get_sc/get_coord` (l. 215–217) → `PrerequisiteError` se `not auto_run_prereqs` (l. 224–229) → auto-run (l. 231–239) → `_compute_*` → `cache.set_arc_flash(bus_id, result, h)` (l. 246–248).

### 1.9 `app/postprocessor/arc_flash_monte_carlo.py` (403 linhas) — padrão MC "sensibilidade de parâmetros" [F]

| Símbolo | Campos / assinatura | Linhas |
|---|---|---|
| `class DistributionType(str, Enum)` | `NORMAL`, `LOGNORMAL`, `UNIFORM` | 83–87 |
| `_sample_normal_truncated(mean, sigma, rng, *, max_attempts=100)` | rejeição de negativos | 90–99 |
| `_sample_lognormal(mean, cv, rng)` | parametrização por média e CV | 102–117 |
| `_sample_uniform(mean, half_width, rng)` | | 120–126 |
| `class ArcFlashUncertainty` (frozen) | `Ibf_cv_pct=15.0`, `T_cv_pct=20.0`, `gap_cv_pct=5.0`, `D_cv_pct=10.0` + `*_distribution` | 134–165 |
| `class MonteCarloResult` (frozen) | `n_samples, n_invalid, samples_E_J_per_cm2: tuple, P50/P95/P99_J_per_cm2, mean, std, cv_pct, cat_distribution: dict`; propriedades `P50_cal_cm2` etc.; `summary()` com histograma ASCII | 173–246 |
| `_percentile(samples, p)` | p em [0,100], interpolação linear | 254–264 |
| `_sample_param(mean, cv_pct, dist, rng)` | | 267–284 |
| `run_monte_carlo(base_case, uncertainty, n_samples=2000, *, random_seed=None) -> MonteCarloResult` | `@requires_feature(Feature.ARC_FLASH_MC)`; import tardio de `arc_flash`/`nbr17227` (l. 314–317); laço l. 330–369 com contagem de inválidos; resultado vazio l. 371–380 | 287–403 |

Terceiro exemplar do padrão: `app/postprocessor/power_flow_monte_carlo.py` (292 linhas) — `PfUncertainty` l. 67–86, `PfMonteCarloResult` l. 89–147 (com `violation_prob_under_voltage`/`over_voltage`, l. 122–123), `_percentile` duplicado l. 150–159, `run_pf_monte_carlo` `@requires_feature(Feature.POWER_FLOW_MC)` l. 174–292 (restaura estado original do sistema ao final, l. 254–256).

[I] Os três MCs compartilham a mesma "assinatura de forma": (a) dataclass frozen de incerteza com CVs em %; (b) dataclass frozen de resultado com amostras brutas em `tuple`, percentis P5/P50/P95/P99, probabilidades de violação e `summary()`; (c) função `run_*` gateada por feature; (d) `random.Random(seed)` da stdlib; (e) `_percentile` local por interpolação linear. Nenhum é gravado no `StudyCache`.

### 1.10 Infraestrutura transversal usada pela área [F]

| Arquivo | Símbolo | Linhas | Papel |
|---|---|---|---|
| `app/commercial/feature_gates.py` | `class Feature` (`RELIABILITY_MC`, `ARC_FLASH_MC`, `POWER_FLOW_MC` …) | 67–79 | catálogo de features |
| | `FEATURE_TIER_MAP` | 83–95 | tier mínimo por feature (os 3 MCs = "commercial") |
| | `LicenseRequiredError` | 103– | exceção ao chamar sem tier |
| | `set_tier_override`, `current_tier`, `is_feature_available`, `require_feature`, `requires_tier`, `requires_feature` | 144, 156, 211, 227, 250, 289 | API de gating |
| `app/postprocessor/audit_trail.py` | `STANDARDS_CATALOG` | 73– | títulos completos de normas (sem IEC 60034, IEEE 1434, IEEE 43) |
| | `citation(standard, section, equation, extra)` | 90–132 | rodapé de citação |
| | `compute_input_checksum(payload)` | 135–161 | SHA256 estável (usado pelo cache) |
| | `class AuditHeader`, `make_audit_header(...)` (`@requires_feature(AUDIT_TRAIL_SHA256)`) | 200–292, 295–327 | cabeçalho de laudo |
| | `KNOWN_LIMITATIONS`, `format_limitations_block/html` | 338–, 385, 408 | limitações declaradas por chave |
| `app/plugins/registry.py` | `register_study(name)` decorator; `get_registered_studies()` | 40–61, 166 | registro de estudo custom (`fn(project, **kwargs)`); docstring afirma aparecer no menu Análise (l. 44–45) — integração GUI não verificada neste mapeamento |
| `app/gui/main_window.py` | ação de menu Reliability / Equipment Eval | 529–548 | pontos de entrada GUI |
| | `_on_show_reliability`, `_on_show_equipment_eval` | 3070–3080, 3082–3101 | handlers |
| | despachante modular (`kind ∈ {sc, coord, arc_flash, pf, motor, ct_sat, pipeline}`) | 3430–3500 | |
| | `_study_cache()` (lazy, 1 por janela), `_reset_study_cache()` | 3505–3517 | ciclo de vida do cache |
| | `_on_analyze_short_circuit_modular` | 3556–3580 | exemplo de uso do estudo modular + `show_result_dialog` + refresh de docks |
| `app/gui/reliability_dialog.py` | `ReliabilityDialog`; botão MC l. 98–103; `_on_run_monte_carlo` | 39–228 | GUI de confiabilidade (componentes fixos, l. 209–215) |
| `app/gui/equipment_eval_dialog.py` | `set_equipments`, `run_evaluation` | 260–298 | GUI de avaliação |
| `app/gui/plot_widgets.py` | `populate_from_cache` do dock MC espera `cache.has_montecarlo()/get_montecarlo()` — **inexistentes em `StudyCache`** | 527–538 | stub de integração MC↔cache |
| `app/gui/analysis_dialogs.py` | `show_result_dialog(parent, title, text, *, width=800, height=600)` | 36– | diálogo de texto reutilizável |
| `app/gui/async_runner.py` | `AtpRunWorker`, `make_run_thread` | 128, 267 | padrão de execução em thread (hoje só ATP) |

Testes existentes da área [F]: `tests/test_pp_v3_6_0_reliability.py`, `tests/test_pp_v3_8_0_reliability_mc.py`, `tests/test_pp_v1_3_0_equipment_eval_B1.py`, `..._rules_B2.py`, `..._dashboard_B3.py`, `tests/test_pp_v0_94_0_modular_studies.py`, `tests/test_pp_v0_44_monte_carlo.py`, `tests/test_pp_v0_80_pf_monte_carlo.py`. `tests/conftest.py` l. 28–42 tem fixture autouse `_commercial_tier_override` que fixa tier `enterprise` (para `@requires_feature` não bloquear). Execução-base neste ambiente (sem PySide6 e sem pydantic): 138 passaram; 1 falha + 5 erros exclusivamente por `ModuleNotFoundError: PySide6`; `test_pp_v0_94_0_modular_studies.py` não coleta por falta de `pydantic`. [I] Portanto o núcleo não-GUI da área está verde.

---

## 2. Fluxo de dados

### 2.1 Confiabilidade (IEEE 1366 / IEEE 493) [F]

```
IEEE493_PRESETS ──get_preset──► make_component_from_preset ──► ComponentReliability
                                                                     │
ReliabilityDialog._on_run_monte_carlo (5 componentes fixos) ─────────┤
                                                                     ▼
                                     run_monte_carlo(components, ..., seed)
                                        exponencial(λ=1/MTBF) + lognormal(MTTR)
                                        ► InterruptionEvent[] por corrida
                                        ► calculate_indices ► SAIFI/SAIDI/CAIDI/ASAI
                                                                     ▼
                                     MCResult ──as_text_report──► QPlainTextEdit
```

Características: sem leitura de `PpProject`; sem `StudyCache`; sem `AuditHeader`; sem HTML/PDF; a semântica "clientes interrompidos" é de distribuição (IEEE 1366), não de disponibilidade de ativo industrial.

### 2.2 Avaliação de equipamentos [F]

```
PpProject.components ──build_equipment_from_project──► EquipmentInstance[] (duty={})
                                                            │  (ratings por heurística de texto)
EquipmentEvalDialog.set_equipments ─────────────────────────┤
                                                            ▼
                      evaluate_project(equipments, PTW_EQUIPMENT_EVALUATION, context)
                         └─ para cada Rule: eval_func(target, duty∪context) → RuleResult
                                                            ▼
                      EvaluationReport[] ──► generate_html_dashboard / export_csv ──► QTextBrowser / arquivo
```

Característica decisiva [F]: o `duty` operacional **não é preenchido** a partir dos estudos (`duty={}`, l. 458 de `equipment_eval.py`); os resultados de SC/PF/V-drop existentes no `StudyCache` não fluem para a avaliação. [I] Quem preencher `duty` (por `dataclasses.replace`) controla tudo o que o dashboard mostra — é aí que um índice de saúde/RUL entra sem modificar nada.

### 2.3 Estudos modulares [F]

```
project + bus_id ──hash_study_inputs(project, bus_id, ("sc", config, ...))──► h
      │                                                                        │
      ▼                                                                        ▼
studies.short_circuit.run ──cache.get_sc_if_valid(bus_id,h)──hit?──► ShortCircuitStudyResult
      │ miss                                                                   ▲
      ▼                                                                        │
_compute_short_circuit (bus_pipeline: find_bus_component, multihop_walker, net.calculate_at_bus,
                        κ Method B/C, decay μ·q, faltas assimétricas) ─► cache.set_sc(bus_id, r, h)
      │
      ├──► coordination.run (usa cache.get_sc) ─► CoordinationStudyResult ─► cache.set_coord
      └──► arc_flash_study.run (usa sc + coord) ─► ArcFlashStudyResult ─► cache.set_arc_flash
GUI: main_window._on_analyze_*_modular ─► show_result_dialog ─► _refresh_plot_docks / _refresh_online_overlay
```

Cadeia de invalidação: `set_sc` limpa coord+arc_flash do bus; `set_coord` limpa arc_flash; hash cobre a topologia inteira (qualquer edição invalida tudo silenciosamente).

### 2.4 Grandezas de motor: onde nascem [F]

- Componente `MOTOR` do esquemático (`app/preprocessor/catalog_specs/MOTOR.ocomp`): propriedades por índice — 0 `motor_type`, 1 `rated_voltage_kV`, 2 `rated_power_kW`, 3 `rated_pf`, 4 `efficiency`, 5 `locked_rotor_current_pu`, 6 `starting_pf`, 7 `n_poles`, 8 `Td_pp_ms`. Lidas em `bus_pipeline._extract_motor_source` (l. 559–613) via `comp.get(idx)`.
- `app/preprocessor/motor.py`: `MotorParameters` (l. 98–150, mesmos campos), `rated_current_A` (l. 162), `locked_rotor_current_A` (l. 168), `motor_to_sc_source` (l. 320).
- `app/postprocessor/motor_starting.py`: `MotorStartingCase` (l. 172–256) → `analyze_motor_starting` (l. 481) → `MotorStartingReport` (l. 260–333) com `starting_current_kA`, `starting_time_s`, `voltage_dip_pu`; cacheado por `motor_id` em `StudyCache._motor_starting` (chamado pelo despachante `kind == "motor"`, main_window l. 3466).
- `app/postprocessor/tcc_damage.py`: `MotorThermalCurve` (l. 450–600): `fla_A`, `locked_rotor_factor=6.0`, `locked_rotor_time_s=10.0` (tE), `K_motor()` l. 551–557, `thermal_time_at_current` l. 559.
- `app/postprocessor/motor_reaccel.py`: `MotorState` (l. 68–96), `ReaccelResult` (l. 99–145).

---

## 3. Pontos de extensão concretos (incrementais, sem reescrita)

Ordem sugerida do menor ao maior acoplamento. Cada item indica arquivo:símbolo → como estender.

### 3.1 `app/commercial/feature_gates.py:Feature` (l. 67–79) e `FEATURE_TIER_MAP` (l. 83–95)
Adicionar constante `INSULATION_RUL = "insulation_rul_prognosis"` e entrada no mapa (tier "commercial", coerente com os três MCs). Nada mais muda; `requires_feature` (l. 289) já resolve pelo nome. Nos testes o `conftest` já libera.

### 3.2 Novo módulo de cálculo `app/postprocessor/insulation_prognosis.py` (padrão de `arc_flash_monte_carlo.py`)
Estrutura espelhada [I]:
- `class InsulationStressInputs(frozen)` — grandezas de estresse (térmico, elétrico, ambiental, mecânico) com defaults;
- `class InsulationUncertainty(frozen)` — CVs em % e `DistributionType` por parâmetro (reutilizar `DistributionType`, `_sample_param`, `_percentile` por import direto de `arc_flash_monte_carlo`, ou copiar localmente — a convenção do repo até aqui foi copiar, cf. `_percentile` triplicado);
- `class RulPrognosisResult(frozen)` — `n_samples, n_invalid, samples_rul_years: tuple, P05/P50/P95_rul_years, mean, std, cv_pct, prob_failure_before_horizon, life_consumed_pct_p50, warnings: tuple, citation: str, limitations_keys: tuple`, com `summary()`;
- `run_rul_monte_carlo(inputs, uncertainty, n_samples=2000, *, random_seed=None)` decorada com `@requires_feature(Feature.INSULATION_RUL)`; `rng = random.Random(random_seed)`.
Sem tocar em nenhum módulo existente.

### 3.3 `app/postprocessor/reliability.py:ComponentReliability` (l. 73–118) — envelhecimento sem quebrar λ constante
Não alterar a classe (o MC de índices depende de `mtbf_hours` constante, l. 303). Criar em módulo novo `class AgingComponentReliability(ComponentReliability)` acrescentando `weibull_beta: float = 1.0`, `weibull_eta_hours: Optional[float] = None`, `age_hours: float = 0.0` e método `hazard_per_hour(t)`; com `beta = 1` degenera para o caso atual (compatibilidade). [H] A hipótese de fundo — que uma Weibull ou um modelo Arrhenius–IEC 60034-18 seja o adequado — precisa de fundamentação bibliográfica; o repositório não contém nenhum dos dois.

### 3.4 `app/postprocessor/reliability_monte_carlo.py:run_monte_carlo` (l. 242–346) — processo não homogêneo
Não modificar. Criar `run_monte_carlo_aging(components: Iterable[AgingComponentReliability], ...)` no módulo novo, reaproveitando `InterruptionEvent`, `calculate_indices`, `MCResult` (a dataclass `MCResult` aceita as quatro distribuições; pode ser reutilizada como está). A amostragem de tempos de falha com h(t) crescente exige *thinning* ou inversa da função de risco acumulada; o laço l. 302–313 (inversa exponencial) serve de molde.

### 3.5 `app/postprocessor/reliability_monte_carlo.py:IEEE493_PRESETS` (l. 57–118) — presets MT
Duas opções incrementais: (a) acrescentar linhas novas ao tuple (`_IEEE493Preset` é frozen mas o tuple é só uma sequência; `get_preset` varre linearmente, l. 123–125) — p. ex. `induction_motor_mv_4kV`, `induction_motor_mv_13kV`, `vacuum_circuit_breaker_mv`; (b) manter `IEEE493_PRESETS` intacto e criar `MV_MOTOR_PRESETS` no módulo novo, com dataclass própria contendo `source: str` obrigatório (anti-alucinação). Recomenda-se (b) até que a Tab 3-1 seja conferida; `list_preset_types()` (l. 132) da GUI continuará funcionando.

### 3.6 `app/postprocessor/study_cache.py:StudyCache` (l. 122–302) — slot de cache por motor
Acrescentar campo `_insulation_prognosis: dict[str, CacheEntry] = field(default_factory=dict)` após l. 143 e métodos `has_/get_/get_..._if_valid/set_insulation_prognosis(motor_id, result, input_hash)` no padrão de `_motor_starting` (l. 239–251), porém **com** variante `_if_valid` (padrão SC, l. 154–160). Incluir a chave em `invalidate_bus` (l. 271–277) e `invalidate_all` (l. 279–286). Campo com `default_factory` é compatível com as chamadas `StudyCache()` existentes (main_window l. 3510, testes). Opcional: expor `has_montecarlo/get_montecarlo` para satisfazer o stub de `plot_widgets.py` l. 532–533.

### 3.7 Novo estudo modular `app/postprocessor/studies/insulation_prognosis.py`
Assinatura conforme contrato do pacote (l. 15–23 de `studies/__init__.py`), com chave `motor_id` em vez de `bus_id`:
`run(project, motor_id, *, cache=None, config=None, bus_id=None, auto_run_prereqs=True) -> InsulationPrognosisStudyResult`.
Pré-requisitos e de onde vêm [I]:
- SC na barra do motor → `cache.get_sc(bus_id)`: `Ik_pp_kA`, `ip_kA`, `z_thevenin_*` (estresse eletrodinâmico/térmico em falta; impedância para partida);
- Motor starting → `cache.get_motor_starting(motor_id)`: `starting_current_kA`, `starting_time_s` (I²t por partida);
- PF opcional → `cache.get_pf()`: `bus_voltages_pu` (`power_flow.PowerFlowSolution` l. 262–301) para sobretensão/subtensão de regime.
Resultado frozen com `status: str` ("computed" | "insufficient_data" | "out_of_scope"), `warnings: tuple`, `citation: str`, `limitations_keys: tuple`, seguindo `ArcFlashStudyResult` (l. 142–164) e `VoltageDropResult.citation` (l. 110). Registrar o módulo em `studies/__init__.py` (import l. 40–44 e `__all__` l. 55–68) — a única alteração em arquivo existente deste item.
Chave de cache: `hash_study_inputs(project, motor_id, ("insulation_rul", config, n_samples, seed))` (l. 310–338). Alternativa de menor atrito para protótipo de pesquisa: `@register_study("insulation_rul")` de `app/plugins/registry.py` (l. 40–61), sem tocar no pacote `studies`.

### 3.8 Regras de avaliação para motor — novo módulo `app/postprocessor/equipment_eval_rules_prognosis.py`
Não editar os 9 critérios. Definir `Rule`s novas com `applicable_to=(EquipmentInstance,)` e `eval_func` que retorna `_na` quando `target.equipment_type != "motor"` ou quando faltar a chave em `ctx`/`duty` — exatamente como `_eval_generator_capacity` (l. 298–327). Sugestão de `rule_id`s: `EQ-INSULATION-LIFE-CONSUMED` (evaluated_value = vida consumida em %, severidade por `_severity_from_pct`), `EQ-INSULATION-RUL-HORIZON` (RUL P05 vs. horizonte de manutenção, em %), `EQ-MOTOR-LOAD-CURRENT` (o critério 4 exclui motor, l. 225 — este preenche a lacuna com `I_load_A/FLA`). Compor `PTW_EQUIPMENT_EVALUATION_PLUS = RuleSet(name=..., norm_reference=..., rules=PTW_EQUIPMENT_EVALUATION.rules + (...))`; `RuleSet.__post_init__` garante unicidade de ids (l. 283–290). O dashboard (§1.5) absorve as colunas automaticamente.

### 3.9 Preenchimento de `duty` a partir do cache — nova função `fill_duty_from_cache(equipments, cache, project) -> list[EquipmentInstance]`
Colocar em módulo novo (ou ao fim de `equipment_eval.py`, no padrão "method injection" usado em `plot_widgets.py` l. 595–600 para não tocar classes existentes). Como `EquipmentInstance` é frozen, usar `dataclasses.replace(eq, duty={**eq.duty, "I_fault_kA": sc.Ik_pp_kA, "ip_kA": sc.ip_kA, "rul_p50_years": ...})`. Fecha o comentário "caller fills via study results" (l. 458) e alimenta as regras de §3.8. Chamada natural: `main_window._on_show_equipment_eval` (l. 3082–3101), entre `build_equipment_from_project` e `dlg.set_equipments`.

### 3.10 GUI (7ª garantia do Master Protocol — obrigatória)
- Menu: nova `analysis_menu.addAction(...)` ao lado de l. 529–548 de `main_window.py`, handler `_on_show_insulation_prognosis` no padrão de `_on_show_reliability` (l. 3070–3080);
- Diálogo `app/gui/insulation_prognosis_dialog.py` no padrão de `reliability_dialog.py` (QDialog modal, `QPlainTextEdit` com `summary()`, botão MC). Para amostras grandes, usar thread (`app/gui/async_runner.py:make_run_thread`, l. 267, hoje específico do ATP — [H] generalizável);
- Tratar `LicenseRequiredError` (feature_gates l. 103) exibindo mensagem, como o `try/except Exception` de `reliability_dialog.py` l. 216–227.

### 3.11 Laudo e auditoria
- `audit_trail.STANDARDS_CATALOG` (l. 73–): acrescentar chaves das normas de isolamento efetivamente usadas (ex.: "IEC 60034-18-41", "IEEE 1434", "IEEE 43", "IEC 60034-27") — somente após confirmar título/ano [INSERIR CITAÇÃO];
- `audit_trail.KNOWN_LIMITATIONS` (l. 338–): adicionar chaves como `rul_model_based_no_measurements`, `rul_single_stress_arrhenius`, `rul_presets_unverified`, para que `format_limitations_block` (l. 385) as imprima no laudo;
- `make_audit_header("Prognóstico de isolamento", inputs, standards_applied=[...])` (l. 295) no cabeçalho do HTML; HTML de tabela reutilizando `generate_html_dashboard` (§1.5) ou o `_CSS` (l. 80–133).

### 3.12 Acoplamento com VCB/TRT (trabalho A) — insumos já existentes para "estresse dielétrico por manobra" [F]
- Parâmetros do modelo estatístico de reignição por componente `VCB/VCB3` (defaults em `app/gui/schematic_pp/editor.py` l. 1591–1620: `I_chop` 5 A, σ 1 A, `di/dt_crit` 16 A/µs, `k_dielec` 17 V/µs, `U0_dielec` 690 V, `T_bounce` 5e-4 s); layout dos índices em `app/preprocessor/vcb_model_emitter.py:VCB_REIGNITION_PROPS` (l. 74–);
- Template ATP `app/preprocessor/atp_templates/vcb_reignition.mod` (CIGRE WG A3.26; saídas `switch_cmd` e `reign_count` — "contador de reignições (para pós-processamento)");
- Pós-processamento de forma de onda: `app/postprocessor/trt_analyzer.py` (`TrtWaveform` l. 91–150; `TrtAnalysisReport` l. 167–247 com `u_c_observed_kV`, `rrrv_max_kV_per_us`, `margin_uc`, `margin_rrrv`, `severity`; `analyze_trt` l. 372–487), `app/analysis/transient_metrics.py` (`TransientMetrics.peak_value` l. 13–25; `TrvMetrics` l. 29–37; `compute_transient_metrics` l. 41; `compute_trv_metrics` l. 91), `app/simulation/results_reader.py:read_pl4` (l. 46);
- Envelopes normativos: `app/standards/iec62271.py` (`TestDuty` l. 93, `GroundingType` l. 108, `trt_envelope_2param` l. 353, `trt_envelope_4param` l. 386).
[H] Um "contador de eventos de sobretensão por manobra" (nº de reignições, pico em pu, RRRV) por motor, acumulado ao longo do tempo, é a ponte natural entre o trabalho A e a taxa de envelhecimento elétrico do módulo de prognóstico. Não existe hoje nenhum acumulador desse tipo; a integração ATP foi desvinculada em v0.92.1 (`version.py` docstring), logo esse insumo depende de execução externa do ATP + leitura de PL4.

### 3.13 Cenários N-1 (trabalho B) [F/I]
`app/preprocessor/scenarios.py` (`PpScenario` l. 51, `ScenarioManager` l. 116) oferece snapshots/branches do projeto. [I] Um estudo de prognóstico avaliado por cenário (base vs. N-1 com religamento/partida de motores grandes) pode ser expresso como `run(scenario.project, motor_id, ...)` por cenário, sem alteração no manager. O `hash_study_inputs` diferencia automaticamente os cenários porque cobre componentes e wires.

---

## 4. Grandezas já disponíveis relevantes a estresse dielétrico/térmico

| Grandeza | Onde | Natureza | Observação |
|---|---|---|---|
| V nominal do motor, kW, cosφ, η, I_LR/I_n, cosφ partida, polos, Td'' | `MOTOR.ocomp`; `MotorParameters` (`motor.py` l. 98–150) | placa | sem classe de isolamento no componente de projeto |
| I nominal (FLA) e I_LR em A | `motor.py:rated_current_A` l. 162, `locked_rotor_current_A` l. 168 | derivada | |
| Classe térmica de isolamento | `app/preprocessor/equipment_catalog.py:CatalogMotor.insulation_class = "F"` (l. 124) | catálogo | **não** existe em `MotorModel` (`app/equipment/library.py` l. 82–108) nem no `MOTOR.ocomp` |
| Curva de dano térmico I²t do motor (tE, K_motor) | `tcc_damage.py:MotorThermalCurve` l. 450–600 | modelo 1 constante de tempo | docstring l. 496 "Class B insulation"; limitações l. 518–527 (sem hot/cold, sem 2 constantes) |
| Corrente e tempo de partida, afundamento de tensão | `motor_starting.py:MotorStartingReport` l. 260–333 | por partida | insumo direto de I²t por partida; aviso se t_start > 30 s (l. 537) |
| Reaceleração (tempo, v_dip) | `motor_reaccel.py:ReaccelResult` l. 99–145 | por evento | |
| Ik'', ip, Ib, Z_th na barra | `ShortCircuitStudyResult` l. 64–99 | falta | estresse eletrodinâmico/térmico em curto |
| Tempo de eliminação de falta | `CoordinationStudyResult.effective_clearing_time_ms` l. 83 | proteção | duração do estresse de falta |
| Tensão de barra em pu | `power_flow.PowerFlowSolution.bus_voltages_pu` l. 285 | regime | sobre/subtensão sustentada |
| Queda de tensão % | `VoltageDropResult.per_bus_pct` l. 90 | regime | |
| Rating de tensão vs. barra | `EQ-VOLTAGE-RATING` (`equipment_eval_rules.py` l. 84–121) | estático | |
| TRV: u_c observado, RRRV, margens, severidade | `TrtAnalysisReport` l. 167–247 | transitório por manobra | requer forma de onda (ATP/PL4) |
| Pico/frequência/amortecimento de transitório | `TransientMetrics` l. 13–25 | transitório | idem |
| Parâmetros de reignição do VCB e contador `reign_count` | editor l. 1591–1620; `vcb_reignition.mod` | modelo estatístico | contador só existe dentro do ATP; wiring TACS manual |
| λ, MTTR, q, A por componente | `ComponentReliability` l. 103–118 | confiabilidade | λ constante |
| Preset de motor (λ = 0,20/ano, MTTR 144 h) | `IEEE493_PRESETS` l. 94–99 | confiabilidade | ver §1.2.1 |
| SAIFI/SAIDI/CAIDI/ASAI com IC 90 % | `MCResult` l. 155–239 | sistema | métrica de distribuição, não de ativo |

---

## 5. Lacunas (o que NÃO existe) [F, salvo indicação]

1. Nenhum modelo de envelhecimento/prognóstico: busca por `RUL`, `remaining useful`, `prognos`, `Arrhenius`, `Weibull`, `partial discharge`, `descarga parcial`, `thermal aging`, `hot spot`, `Montsinger`, `IEC 60034-18`, `IEEE 1434`, `IEEE 43`, `polarization index` em `*.py/*.md` do repositório retorna zero ocorrências (exceto `docs/PTW_SURPASSING_MATRIX.md` l. 288, item #141 "Failure Rate / Repair Time Aging Factor (5th-order poly) … + Weibull + Bayesian update", com status ⏳ pendente; toda a Part 10 Reliability, itens 129–141, está ⏳ em l. 272–288).
2. Nenhuma função de risco variável no tempo; `ComponentReliability` e o MC de índices assumem λ constante.
3. Nenhuma ingestão de medições de campo (DP, IR/PI, tan δ, capacitância, temperatura de enrolamento, horas de operação, nº de partidas, histórico de manobras) — não há dataclass, parser CSV nem propriedade de componente para isso.
4. Nenhum vínculo entre `reliability_monte_carlo` e o projeto/topologia/`StudyCache` (GUI usa 5 componentes fixos, l. 209–215 do diálogo). Item PTW #131 "Reliability Data sub-view per component" pendente.
5. Nenhum preset de confiabilidade específico para motor MT nem para disjuntor a vácuo; presets não verificados contra a norma (§1.2.1).
6. Avaliação de equipamentos: 8 de 9 critérios são N/A para motor; critério de corrente de carga exclui motor (l. 225); `duty` nunca é preenchido pelos estudos (l. 458).
7. Nenhum MC é gravado no `StudyCache`; o stub `has_montecarlo/get_montecarlo` esperado por `plot_widgets.py` (l. 532–533) não existe.
8. `StudyCache.get_motor_starting` não tem variante `_if_valid`; `status_summary` cobre só 3 estudos; cache de `voltage_drop.run` é inoperante (`if False`, l. 187); `demand_load` não segue o contrato `run`.
9. `STANDARDS_CATALOG` (audit_trail l. 73–) não contém normas de isolamento de máquinas; `KNOWN_LIMITATIONS` (l. 338–) não contém chaves de prognóstico.
10. Classe de isolamento existe apenas em `CatalogMotor` (catálogo de fabricantes), não no componente do esquemático nem em `MotorModel`.
11. Nenhum acumulador de eventos de manobra/sobretensão por motor; `reign_count` só existe dentro do MODELS do ATP e o wiring TACS é manual (cabeçalho do template).
12. Nenhum modelo térmico com duas constantes de tempo (rotor/estator) ou partida a quente/frio (limitação declarada em `tcc_damage.py` l. 518–527).
13. Ambiente de execução desta sessão: `PySide6` e `pydantic` ausentes — testes GUI e `test_pp_v0_94_0_modular_studies.py` não rodam aqui (não é lacuna do repositório, mas condiciona a validação local).

---

## 6. Convenções que um novo módulo deve seguir [F]

1. **Cabeçalho de módulo** em PT-BR com etiqueta de versão (`"""vX.Y.Z — ..."""` ou `app.postprocessor.<mod> — ... (vX.Y.Z)`), seções "Filosofia/Motivação", "API/Uso" com exemplo `::`, "Cobertura normativa"/"Referências" e "Anti-alucinação"/"Limitações declaradas" (cf. `reliability.py` l. 1–24; `reliability_monte_carlo.py` l. 1–24; `arc_flash_monte_carlo.py` l. 1–65; `voltage_drop.py` l. 41–50).
2. **Identificadores em inglês, docstrings/mensagens em PT-BR**; unidades no nome do campo (`_kA`, `_ms`, `_pct`, `_pu`, `_hours`, `_years`).
3. **Dataclasses `frozen=True`** para entradas e resultados; sequências como `tuple` (não `list`) em resultados frozen; `warnings: tuple[str, ...] = field(default_factory=tuple)`; campo `citation: str` e/ou `references: tuple[str, ...]` no resultado; método `summary()` (MCs/estudos) ou `as_text_report()` (reliability) retornando texto multilinha.
4. **Validação em `__post_init__`** com `ValueError` e mensagem incluindo o valor recebido (cf. `ComponentReliability` l. 91–101, `EquipmentInstance` l. 127–161).
5. **Monte Carlo**: `random.Random(seed)` da stdlib (reprodutibilidade; docstring l. 20–22 de `reliability_monte_carlo.py` declara explicitamente "não numpy", embora `numpy>=1.24.0` esteja em `requirements.txt` l. 4); percentis por interpolação linear; contagem de amostras inválidas; resultado "vazio" bem definido quando não há amostras válidas (l. 371–380 de `arc_flash_monte_carlo.py`); testes de reprodutibilidade por seed (`test_pp_v3_8_0_reliability_mc.py` l. 142–160).
6. **Gating comercial**: `@requires_feature(Feature.X)` na função `run_*`, constante em `Feature` e entrada em `FEATURE_TIER_MAP`; nunca strings soltas (feature_gates l. 22–24).
7. **Imports tardios** dentro de funções para evitar ciclos (`arc_flash_monte_carlo.py` l. 314–317; `equipment_eval.py` l. 218, 228, 323; `arc_flash_study.py` l. 196, 263–267).
8. **Estudo modular**: assinatura `run(project, <id>, *, cache=None, config=None, auto_run_prereqs=True)`; hash por `hash_study_inputs(project, id, (<tag>, config, ...params))`; `get_*_if_valid` antes de computar; `PrerequisiteError(study=, bus_id=, missing=[...])` em modo estrito; núcleo em `_compute_*`; `status` como string enumerada com fallback gracioso em vez de exceção para fora de escopo; `set_*` ao final; exportar no `studies/__init__.py`.
9. **Regras**: `Rule(rule_id="EQ-...", description, citation, applicable_to=(EquipmentInstance,), eval_func)`; `eval_func` devolve `NOT_APPLICABLE` quando faltam dados (nunca exceção); `evaluated_value` em % (dashboard formata `:.0f%`); `expected_range=(min, max)`; severidade por `_severity_from_pct`; ids únicos por `RuleSet`.
10. **Logging**: `from app.core.logging_config import get_logger; log = get_logger(__name__)` (`demand_load.py` l. 35–40; `voltage_drop.py` l. 59–67).
11. **Auditoria**: citações via `audit_trail.citation`, checksum via `compute_input_checksum`, limitações por chave em `KNOWN_LIMITATIONS`; laudo com `AuditHeader`.
12. **Testes**: arquivo `tests/test_pp_vX_Y_Z_<feature>.py`, classes `TestXxx`, docstring listando cobertura e critério de aceite (cf. `test_pp_v1_3_0_equipment_eval_rules_B2.py` l. 1–17: "PASS + WARN + FAIL + NA" por critério); GUI com fixture `qapp` e `QT_QPA_PLATFORM=offscreen`; tier já sobrescrito pelo `conftest`.
13. **Processo (Master Protocol, `docs/SESSION_HANDOFF.md` l. 24–46)**: auditoria em `docs/vX.Y.Z_BACKLOG_AUDIT.md`, design doc antes do código (`docs/v1.3.0_FASE_B_DESIGN.md` é o exemplo desta área), ponto de restauração, **ponto de entrada GUI obrigatório** (7ª garantia; "backend órfão é proibido"), declaração de "dimensão de superação vs. PTW" (6ª), registro no `CHANGELOG.md` (Keep a Changelog, PT-BR) e bump em `app/core/version.py:VERSION_TUPLE` (l. 1959).
14. **Anti-alucinação em dados**: todo número tabelado leva comentário de origem na linha (cf. `IEEE493_PRESETS` l. 58–117) e o docstring cita norma/seção; quando a origem não for verificada, o campo `description`/`source` deve dizê-lo.

---

## 7. Riscos técnicos

1. **Incoerência de modelo probabilístico** [I]: misturar λ constante (`ComponentReliability`, `run_monte_carlo`) com função de risco crescente (RUL) sem separar claramente as abstrações produz índices inconsistentes; as fórmulas série/paralelo (l. 259–295) são aproximações de q pequeno e não valem para hazard variável. Mitigação: classe derivada + MC próprio (§3.3–3.4), nunca alteração in-place.
2. **Presets não verificáveis** [F]: os valores de `IEEE493_PRESETS` não foram conferidos contra a norma; usar em tese/artigo exige [INSERIR CITAÇÃO]. Um preset de motor MT inventado sem fonte contraria a convenção 14 e o Master Protocol (3ª garantia).
3. **RUL puramente model-based** [I]: sem ingestão de medições (lacuna 3), qualquer intervalo de confiança refletirá apenas incerteza paramétrica (CVs escolhidos) e não incerteza de estado do ativo. Risco de sobre-afirmação para a demanda C-Level; o laudo deve carregar chave em `KNOWN_LIMITATIONS` explicitando isso.
4. **Heurística de ratings** [F]: `build_equipment_from_project` infere kV/A/kA por faixa numérica e substring (l. 436–447) — pode atribuir ratings errados a motores. O módulo de prognóstico deve ler o `MOTOR` pelos índices do `.ocomp` (padrão `_extract_motor_source`, l. 571–583), não pela heurística.
5. **Modelo térmico simplificado** [F]: `MotorThermalCurve` é de constante de tempo única, sem hot/cold, e o próprio docstring (l. 518–522) recomenda 2 constantes para "grandes alta tensão" — exatamente o alvo do módulo. Estimativas de temperatura de enrolamento a partir dela serão grosseiras.
6. **Custo de invalidação do cache** [F]: `hash_study_inputs` cobre todos os componentes e wires (l. 321–337); qualquer edição no esquemático invalida o prognóstico e força novo MC. Manter `n_samples` moderado e/ou cachear por `motor_id` com hash restrito aos insumos do motor ([H] exigiria função de hash própria).
7. **Bloqueio de GUI** [F/I]: os MCs rodam síncronos no diálogo (`reliability_dialog.py` l. 217–224); um MC de RUL com thinning sobre décadas × milhares de amostras em Python puro pode congelar a UI. `async_runner.py` existe mas é específico do ATP.
8. **Gating e exceções** [F]: função gateada lança `LicenseRequiredError` fora de tier; a GUI deve capturar (o diálogo atual usa `except Exception`, l. 225). Testes sem o `conftest` (ex.: scripts) precisam de `set_tier_override("enterprise")`.
9. **Deriva de API** [F]: `plot_widgets.py` já espera `has_montecarlo/get_montecarlo` no cache (l. 532–533) que não existem; adicionar slots ao `StudyCache` deve respeitar esses nomes ou o dock continuará em estado vazio.
10. **Colisão de nomes** [F]: `run_monte_carlo` existe em `reliability_monte_carlo` e em `arc_flash_monte_carlo`; importar por módulo (`from app.postprocessor import reliability_monte_carlo as rmc`) para evitar confusão em código e em texto.
11. **Semântica dos índices** [I]: SAIFI/SAIDI/"clientes" (IEEE 1366) não representam disponibilidade de um motor de processo; para o contexto industrial (hipótese óleo e gás) as métricas relevantes são disponibilidade, tempo de parada esperado, EENS/ECOST (item PTW #129 pendente) — o módulo deve definir suas próprias métricas em vez de reaproveitar `ReliabilityIndices`.
12. **Dependência de ATP para estresse por manobra** [F]: `reign_count`, TRV e picos exigem simulação externa e leitura de PL4; a integração ATP está desvinculada desde v0.92.1. Sem isso, o acoplamento com o trabalho A fica restrito a parâmetros de placa do VCB (defaults do editor) — [H] insuficiente para quantificar reignições reais.
13. **Importações circulares** [I]: um módulo de regras que importe `studies` ou `study_cache` no topo pode fechar ciclo com `equipment_eval` ↔ `coord_rules`; manter imports tardios (convenção 7).
14. **Ambiente de validação** [F]: sem `PySide6`/`pydantic` neste contêiner, testes GUI e de estudos modulares não podem ser executados aqui; a validação completa (sweep) requer ambiente local conforme `README.md` l. 165–180.
