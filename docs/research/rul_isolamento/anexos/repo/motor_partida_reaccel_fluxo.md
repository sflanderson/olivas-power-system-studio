# Mapeamento da área `motor_partida_reaccel_fluxo` — Olivas Power System Studio

Repositório: `/home/user/olivas-power-system-studio` (HEAD `26d9248`, 2026-05-16; versão `VERSION_TUPLE = (4, 0, 0)` em `app/core/version.py:1959`). Todos os arquivos desta área entraram no histórico público em um único commit (`ad308d5`, 2026-05-15), portanto o `git log` não distingue a maturidade relativa dos módulos; as marcas de versão nos docstrings (v0.27.11, v0.28.1, v0.80, v0.94.0, v0.100.0, v0.102.0, v1.7.0, v3.8.1) são a única cronologia disponível.

Convenção de rotulagem usada neste documento:

* **[FATO]** — verificado por leitura do código/execução no repositório (caminho:linha).
* **[INFERÊNCIA]** — conclusão minha a partir dos fatos.
* **[HIPÓTESE]** — proposta de projeto ainda não validada.

Escopo: partida e reaceleração de motores, fluxo de potência (balanceado, desbalanceado, Monte Carlo, limites de Q), energização de barras, exemplo IEEE 399, e a existência (ou não) de suporte a contingência N-1, corte de carga (*load shedding*) e otimização multiobjetivo.

---

## 1. Inventário de arquivos e símbolos

### 1.1 `app/postprocessor/motor_starting.py` (560 linhas) — partida de motor (IEEE 399 §10)

| Símbolo | Assinatura / campos | Linhas | Observação [FATO] |
|---|---|---|---|
| `DEFAULT_VOLTAGE_DIP_LIMIT_PU` | `= 0.85` | 93 | Limite IEEE 399 (declarado no docstring l. 23). |
| `ABSOLUTE_MIN_VOLTAGE_LIMIT_PU` | `= 0.80` | 96 | Limite NEMA MG 1 (docstring l. 24). |
| `DEFAULT_START_TIME_FRACTION_LIMIT` | `= 0.70` | 99 | **Declarada e nunca usada** no módulo (critério `t_start < 0,7·t_LR` do docstring l. 25-26 não é aplicado). |
| `class StartingResult(str, Enum)` | `ACCEPTABLE / MARGINAL / UNACCEPTABLE` | 102-107 | |
| `class LoadType(str, Enum)` | `CONSTANT / LINEAR / QUADRATIC / CUBIC` | 114-145 | Curva T_carga ∝ ω^k. |
| `average_load_torque_factor(load_type) -> float` | 1, 1/2, 1/3, 1/4 | 148-168 | Torque médio da carga em 0→ω_n. |
| `@dataclass(frozen=True) class MotorStartingCase` | `motor_name, motor_rated_power_kW, motor_rated_voltage_kV, motor_rated_pf, motor_efficiency, locked_rotor_current_pu, starting_pf, starting_torque_pu, load_torque_pu, inertia_motor_kg_m2, bus_pre_fault_voltage_pu, bus_thevenin_impedance_ohm, bus_rated_voltage_kV, n_poles=4, frequency_Hz=60.0, load_type=None, bus_thevenin_impedance_complex: complex|None=None` | 171-251 | `__post_init__` (l. 248-251) força `LoadType.CONSTANT`. `bus_thevenin_impedance_ohm` está DEPRECATED (l. 178-179). |
| `@dataclass(frozen=True) class MotorStartingReport` | `motor_name, voltage_dip_pu, voltage_dip_pct, starting_current_kA, starting_apparent_power_MVA, starting_time_s, synchronous_speed_rpm, motor_impedance_ohm, acceptance, rationale: tuple[str,...], references` | 259-329 | `summary()` l. 306-329 (texto). |
| `motor_impedance_at_start_ohm(case) -> complex` | Z_M = (V²/S)/I_LR_pu, R/X de `starting_pf` | 337-364 | S = P/(η·fp). |
| `calculate_voltage_dip_pu(case) -> tuple[float, complex, complex]` | V_during/V_pre = Z_M/(Z_th+Z_M) | 367-407 | Usa Z_th complexo se fornecido (l. 391-394); senão heurística 10 %R/90 %X (l. 396-401). |
| `estimate_starting_time_s(case) -> float` | t = J·0,95·ω_s/(T_m,avg − T_load,avg) | 410-453 | Retorna `inf` se T_m ≤ T_load (l. 446-447). **Não depende da tensão** (T_m ∝ V² não modelado). |
| `synchronous_speed_rpm(f, p) -> float` | 120·f/p | 456-458 | |
| `classify_acceptance(V_during_pu) -> StartingResult` | > 0,85 / > 0,80 / ≤ 0,80 | 461-473 | Só tensão; tempo não entra na aceitação. |
| `analyze_motor_starting(case) -> MotorStartingReport` | pipeline completo | 481-560 | I_n (l. 500), I_LR (l. 501), I_during = I_LR·V_during/V_pre (l. 505), S_during (l. 508-509), aviso se t_start > 30 s "verificar curva I²t" (l. 537-541). |

### 1.2 `app/postprocessor/motor_reaccel.py` (261 linhas) — reaceleração (IEEE 399 §10.5), v0.102.0

| Símbolo | Assinatura / campos | Linhas | Observação [FATO] |
|---|---|---|---|
| `class ReaccelScenario(str, Enum)` | `VOLTAGE_DIP / BLACK_START / BUS_TRANSFER` | 60-64 | O cenário **não altera o algoritmo** (apenas rotula o resultado). |
| `@dataclass(frozen=True) class MotorState` | `motor_id, rated_power_kW, rated_voltage_V, inertia_kg_m2=1.0, rated_speed_rpm=1800, locked_rotor_current_pu=6.0, full_load_efficiency=0.92, full_load_power_factor=0.85` | 67-95 | `rated_torque_Nm` (l. 80-84), `rated_current_A` (l. 86-95). Tensão em **volts** (diverge de `MotorStartingCase`, em kV). |
| `@dataclass(frozen=True) class ReaccelResult` | `scenario, time_to_full_speed_s, v_dip_pu, v_recovery_time_s, motors_lost, motors_recovered, status, citation, warnings` | 98-140 | `passes` ⇔ v_dip ≥ 0,7 e status == "success" (l. 114-117). |
| `simulate_reaccel(motors, scenario=VOLTAGE_DIP, *, voltage_dip_duration_s=1.0, voltage_dip_level_pu=0.7, bus_capacity_kVA=10000.0) -> ReaccelResult` | | 148-261 | Σ inrush kVA (l. 185-189); `v_dip = max(0.3, 1 − 0.3·Σinrush/S_bus)` (l. 194-197); `v_dip_pu = min(dip_disturbio, dip_reaccel)` (l. 201); tempo `J_avg·ω_avg²/(max(v²,0.01)·100)` limitado a [0,5; 30] s (l. 211-216); motor "perdido" se v_dip < 0,5 (l. 225); `v_recovery = 0,7·t` (l. 239). `voltage_dip_duration_s` **não é usado** no cálculo. |

### 1.3 `app/postprocessor/power_flow.py` (807 linhas) — Newton-Raphson sequência positiva

| Símbolo | Assinatura / campos | Linhas | Observação [FATO] |
|---|---|---|---|
| `class BusType(str, Enum)` | `SLACK / PV / PQ` | 116-120 | |
| `@dataclass class PfBus` | `id, type, V_pu_set=1.0, theta_set_rad=0, P_pu_set=0, Q_pu_set=0, rated_voltage_kV=13.8, base_MVA=100, Q_min_pu=-1e9, Q_max_pu=1e9, original_type=None, V_pu_solved, theta_solved_rad, P_pu_solved, Q_pu_solved` | 128-197 | Mutável (não frozen). Convenção: carga com P **negativo** (l. 149-150, 681-682). |
| `@dataclass class PfBranch` | `from_bus, to_bus, R_pu=0, X_pu=0.1, B_pu=0, tap_ratio=1.0, description` | 200-240 | Modelo π; tap no lado `from`. |
| `@dataclass(frozen=True) class LineFlow` | `P/Q from, P/Q to, P_loss, Q_loss` | 248-258 | |
| `@dataclass(frozen=True) class PowerFlowSolution` | `converged, iterations, max_mismatch, bus_voltages_pu: dict, line_flows: tuple, total_losses_pu: complex` | 261-319 | `q_limit_violations` é anexado via `object.__setattr__` (l. 803-806). |
| `build_ybus(buses, branches) -> (bus_idx, Y)` | numpy | 327-372 | `ValueError` para barra desconhecida (l. 349-353) ou Z=0 (l. 357-360). |
| `solve_power_flow(buses, branches, tolerance=1e-6, max_iterations=50, verbose=False) -> PowerFlowSolution` | NR completo | 380-576 | Exige exatamente 1 SLACK (l. 413-418); laços Python O(n²) para P/Q (l. 458-467) e Jacobiano (l. 488-535); Jacobiano singular → `break` com `converged=False` (l. 538-542). Preenche `*_solved` nas barras (l. 551-555). |
| `_compute_line_flows(...)` | | 579-613 | |
| `@dataclass class PowerFlowSystem` | `base_MVA=100, buses, branches` + `add_slack` (639), `add_pv` (653, aceita `Q_min_pu/Q_max_pu`), `add_pq` (676), `add_branch` (693), `solve` (708), `get_bus` (721), `solve_with_q_limits(..., max_switching_iterations=5)` (732-807) | 621-807 | `solve_with_q_limits` **muta** `b.type` e `b.Q_pu_set` (l. 784-785, 792-793) e guarda `original_type` (l. 763-765). |

Docstring l. 81-89 declara: "Sem PV→PQ switching" (já superado pela v3.8.1) e **"Sem otimização (load shedding, FACTS)"** (l. 87).

### 1.4 `app/postprocessor/power_flow_unbalanced.py` (261 linhas) — v0.100.0

| Símbolo | Linhas | Observação [FATO] |
|---|---|---|
| `BusUnbalancedVoltage` (dataclass frozen; `unbalance_factor_pct` = V2/V1·100) | 49-85 | |
| `UnbalancedPFResult` (`per_bus`, `violations`, `unbalance_limit_pct=2.0`) | 88-120 | |
| `phase_to_sequence`, `sequence_to_phase` (Fortescue) | 133-174 | Corretas e reutilizáveis. |
| `analyze_unbalanced_pf(project, *, unbalance_limit_pct=2.0, base_voltage_pu=1.0, typical_unbalance_per_bus_pct=0.5)` | 182-261 | **Não resolve fluxo**: atribui V1 = base, V2 = 0,5 % fixo, V0 = 0 a todas as barras (l. 218-221). O próprio docstring (l. 199-200) adia o NR trifásico para "v0.100.1" (inexistente). |

### 1.5 `app/postprocessor/power_flow_monte_carlo.py` (292 linhas) — v0.80

| Símbolo | Linhas | Observação [FATO] |
|---|---|---|
| `PfUncertainty(load_P_cv_pct=20, load_Q_cv_pct=30, voltage_setpoint_cv_pct=1)` | 67-86 | |
| `PfMonteCarloResult` (P50/P5 V_min, P95 V_max, prob. violação < 0,95 / > 1,05) | 89-147 | |
| `_percentile`, `_sample_normal_truncated` (gaussiana **sem** truncamento, l. 171) | 150-171 | |
| `@requires_feature(Feature.POWER_FLOW_MC) run_pf_monte_carlo(pf_system, uncertainty, n_samples=500, *, random_seed=None, tolerance, max_iterations)` | 174-292 | Salva/restaura setpoints (l. 208-211, 254-256) — padrão reutilizável para laços de otimização. Docstring l. 13-15 e l. 52: **"Topologia fixa (N-1 ainda em backlog)"**. |

### 1.6 `app/postprocessor/bus_energization.py` (256 linhas) — v1.7.0

| Símbolo | Linhas | Observação [FATO] |
|---|---|---|
| `_INTERRUPTOR_TYPES = {"BREAKER","VCB","VCB3","FUSE","CONTACTOR","SWITCH","SW","DISC","DISCONNECTOR"}` | 49-52 | Inclui VCB — ponto de contato com a área de disjuntores a vácuo. |
| `_SOURCE_TYPE_FALLBACK` | 57-60 | |
| `class BusState(str, Enum)`: `LIVE / DEAD / UNKNOWN` | 63-67 | |
| `compute_energization(*, components, wires) -> dict[str, BusState]` | 111-181 | BFS; interruptor com `is_open=True` não propaga (l. 164-165). Aceita dicts simples. |
| `compute_energization_for_pp_project(pp_project)` | 189-256 | Lê propriedade `state/status ∈ {open, off, 1}` (l. 218-230). |

### 1.7 `app/examples/ieee399_motor_starting.py` (126 linhas)

* `run() -> ExampleResult` (l. 31-121): motor 1500 kW / 4,16 kV, η = 0,96, fp = 0,88, I_LR = 6 pu, fp_partida = 0,30, T_partida = 1,4 pu, J = 80 kg·m², V_pre = 0,97 pu, `bus_thevenin_impedance_ohm = 0.10` (l. 49), carga CONSTANT.
* Execução real (2026-09-02, `python -c "from app.examples.ieee399_motor_starting import run; print(run().summary())"`): **V_during = 0,9196 pu; dip = 5,19 %; I_partida = 1,402 kA; S_partida = 9,29 MVA; t→95 % = 4,50 s; ACCEPTABLE; [PASS]** [FATO].
* Inconsistência documental [FATO]: o docstring (l. 16) e o código (l. 49) usam Z_th = 0,10 Ω, mas a narrativa impressa (l. 85) afirma "Z_th = 0.5 Ω".
* Registrado em `app/examples/registry.py:80-88` (`ExampleEntry id="ieee399_motor_starting"`); contrato `ExampleResult` em `app/examples/__init__.py:48-108`.

### 1.8 Módulos adjacentes indispensáveis ao tema

| Arquivo | Símbolos relevantes | Linhas | Por que importa [FATO] |
|---|---|---|---|
| `app/preprocessor/motor.py` | `MotorParameters` (campos l. 140-150: `rated_voltage_kV=0.480, rated_power_kW=100, rated_pf, efficiency, locked_rotor_current_pu=6, starting_pf=0.30, n_poles=4, Td_pp_ms=20`), `rated_apparent_power_kVA` (155), `rated_current_A` (162), `locked_rotor_current_A` (168), `subtransient_reactance_pu` (179), `contribution_factor_at_time` (235-262, e^(−t/Td'')), `validate_motor` (270), `motor_to_sc_source` (320) | 86-430 | Modelo único de motor no pré-processador; **não tem inércia, torque de partida, classe térmica nem t_LR**. |
| `app/preprocessor/catalog_specs/MOTOR.ocomp` | propriedades por índice 0..8: `motor_type, rated_voltage_kV, rated_power_kW, rated_pf, efficiency, locked_rotor_current_pu, starting_pf, n_poles, Td_pp_ms` | — | O componente MOTOR do esquemático não carrega inércia, T_partida, classe de isolamento ou nº de partidas. |
| `app/postprocessor/bus_pipeline.py` | `_extract_motor_source(comp, warnings)` lê as propriedades **por índice posicional** (`comp.get(0..8)`) | 559-613 | Inserir propriedade no meio do `.ocomp` quebra a leitura; anexar no fim é seguro. |
| `app/preprocessor/equipment_catalog.py` | `EfficiencyClass` (IEC 60034-30-1, l. 85-91); `CatalogMotor` com `inertia_kg_m2` (l. 122) e `insulation_class: str = "F"` (l. 124), `starting_torque_pu`, `pull_up_torque_pu`, `breakdown_torque_pu`; `motor_catalog_to_parameters` (l. 554-573) **descarta** inércia, torques e classe de isolamento | 60-620 | Único lugar do repositório com "classe de isolamento"; a informação existe no catálogo mas não flui para os estudos. |
| `app/postprocessor/tcc_damage.py` | `MotorThermalCurve(motor_id, fla_A, locked_rotor_factor=6.0, locked_rotor_time_s=10.0, enabled=True)`; `K_motor() = tE·(I_LR/FLA)²` (551-557); `thermal_time_at_current(I)` = K/(I/FLA)² para I > 1,05·FLA (559-578); `thermal_points` (580-601) | 449-601 | Curva de dano térmico I²t do motor (limite de capacidade). Limitações declaradas: constante de tempo única, **sem HOT/COLD** (l. ~518-527). |
| `app/postprocessor/coord_rules_builtin.py` | `_eval_motor_thermal_below_locked_rotor` (599-659); `RULE_MOTOR_THERMAL_BELOW_LR` (662-668) | | Verifica proteção 49 abaixo de t_LR em I_LR (IEEE 242 §11.6). |
| `app/postprocessor/tcc_devices.py` | `MultiFunctionRelay.relay_51_50_49(...)` | 399-449 | Função 49 modelada como tempo definido (não réplica térmica). |
| `app/postprocessor/fault_decay.py` | `induction_motor_excluded(hp, cycles, *, hp_threshold=50, cycles_threshold_large=30, cycles_threshold_small=1)` (81-133); `gen_sync_decay_step` (24); `recalculate_trip_time` (136) | | Decaimento de contribuição de motor (regra PTW). |
| `app/postprocessor/reliability.py` | `ComponentReliability(name, mtbf_hours, mttr_hours)` com `failure_rate_per_year` (104), `forced_outage_rate` (109), `availability` (116); `calculate_indices` (234) | 43-295 | Base para converter "vida consumida" em λ(t). Distribuição exponencial apenas. |
| `app/postprocessor/reliability_monte_carlo.py` | `IEEE493_PRESETS` (59+), `run_monte_carlo` (243, `@requires_feature`), usa somente `random` stdlib (docstring l. 21-22) | | Padrão de MC reprodutível por seed. |
| `app/postprocessor/study_cache.py` | `StudyCache` (98) com slot `_motor_starting` (142), `has/get/set_motor_starting` (239-251), `invalidate_bus` (270-276), `hash_study_inputs(project, bus_id, config)` (309-338) | | **Nenhum chamador de `set_motor_starting` existe** fora do próprio módulo (grep em `app/` e `tests/`). |
| `app/postprocessor/studies/short_circuit.py` | `ShortCircuitStudyResult.z_thevenin_real_ohm / z_thevenin_imag_ohm` (83-84); `run(project, bus_id, *, cache, config, use_multi_hop=True, pre_fault_voltage_pu=None)` (107-169) | | Fornece o Z_th complexo que `MotorStartingCase.bus_thevenin_impedance_complex` espera — **mas ninguém faz essa ligação**. |
| `app/postprocessor/studies/__init__.py` | Convenção `run(project, bus_id, *, cache=None, config=None, auto_run_prereqs=True)` | 15-24 | Padrão para novos estudos modulares. |
| `app/gui/analysis_dialogs.py` | `build_pf_system_from_project(project, base_MVA=100)` (415-553); `run_power_flow_analysis` (556+); `MotorStartingDialog.get_parameters` (749-761); `run_motor_starting_analysis(parent, *, project=None, bus_id="")` (763-790) | | GUI de partida usa `|Z_th|` digitado (l. 785) e `V_pre` digitado (l. 784); `motor_name="MOTOR"` fixo (l. 774); `load_torque_pu=1.0` fixo (l. 781). Não lê o MOTOR do projeto. |
| `app/gui/main_window.py` | `_on_analyze_motor_starting` (2444-2450); `_on_analyze_motor_reaccel` (2735-2765): todo MOTOR vira `MotorState(rated_power_kW=200.0, rated_voltage_V=4160.0)` (l. 2749-2753) | | Reaceleração na GUI ignora os parâmetros reais dos motores. |
| `app/preprocessor/scenarios.py` | `PpScenario` (51), `ScenarioManager` (116): `clone_active`, `activate`, `promote_to_base`, `diff_with_base` | | Infra de "what-if" por cópia profunda do projeto — candidata a hospedar cenários de contingência [HIPÓTESE]. |
| `app/commercial/feature_gates.py` | `Feature` (71-83), `FEATURE_TIER_MAP` (87-99), `set_tier_override` (142-151) | | MC de PF e de confiabilidade são gated; `tests/conftest.py:27-40` força tier `enterprise` nos testes. |
| `app/postprocessor/audit_trail.py` | `KNOWN_LIMITATIONS` (338-383; chaves `pf_positive_seq_only`, `pf_no_q_limits`, ...), `format_limitations_block` (385), `compute_input_checksum` (135) | | Mecanismo oficial de "limitações declaradas" no laudo. |

### 1.9 Testes existentes (contagem `def test_`)

`tests/test_pp_motor_starting.py` (35), `tests/test_pp_v0_102_0_motor_reaccel.py` (12), `tests/test_pp_power_flow.py` (31), `tests/test_pp_v0_80_pf_monte_carlo.py` (9), `tests/test_pp_v3_8_1_pf_q_limits.py` (14, com fixture IEEE 14 barras subconjunto de 5), `tests/test_pp_v1_7_0_bus_energization.py` (12), `tests/test_pp_v0_100_0_pf_unbalanced.py` (12), `tests/test_pp_v3_6_0_reliability.py` (35), `tests/test_pp_v3_8_0_reliability_mc.py` (18). O CI (`.github/workflows/test.yml`) executa apenas um subconjunto (inclui `test_pp_v0_80_pf_monte_carlo.py` e `test_pp_v3_8_0_reliability_mc.py`; **não** inclui `test_pp_motor_starting.py` nem reaccel); o sweep completo é local.

### 1.10 Resultado da busca por N-1, load shedding, NSGA, Pareto

[FATO] `grep -rnwiE` em `app/`, `tests/`, `docs/`, `scripts/`:

* `NSGA`, `pareto`, `multiobjetivo`, `multi-objective`, `pymoo`, `deap`, `arrhenius`, `montsinger`, `RUL`, `remaining useful life`: **zero ocorrências** em código.
* `weibull`: apenas em docs como item adiado (`docs/v3.6.0_HANDOFF.md:158`, `docs/PTW_SURPASSING_MATRIX.md:288` linha 141 "Failure Rate / Repair Time Aging Factor ... + Weibull + Bayesian update", status ⏳).
* `N-1`: `app/postprocessor/power_flow_monte_carlo.py:15` e `:52` (backlog declarado); `relay_coordination.py:469`, `report_pdf.py:1076`, `iec61850_sv.py:94` são usos aritméticos "N−1" sem relação com contingência.
* `load shedding`: `app/postprocessor/power_flow.py:87` ("Sem otimização (load shedding, FACTS)") e `app/standards/ansi_devices.py:325` (string descritiva da função ANSI 81: "Anti-ilhamento, load-shedding"). Nenhuma implementação.
* `conting*`: `docs/v3.6.0_HANDOFF.md:147-148` ("walker que enumera contingências deferred v3.6.x").
* `IEC 60034`: `motor_reaccel.py:10` (citação "IEC 60034-1 §11" sem uso numérico), `tcc_damage.py:513` (IEC 60034-12), `equipment_catalog.py:86` (IEC 60034-30-1 classes IE). Nenhuma tabela de classes térmicas (A/E/B/F/H) no código.
* `insulation_class`: somente `equipment_catalog.py:124,146` (campo string, não consumido).

**Conclusão [FATO]: não existe hoje qualquer suporte a contingência N-1, corte de carga, otimização multiobjetivo ou modelo de envelhecimento de isolamento.** O que existe são menções em docstrings/backlog e blocos construtivos reutilizáveis (Seção 3).

---

## 2. Fluxo de dados

### 2.1 Fluxo real hoje (GUI) [FATO]

```
.sch (PpProject)                              QDialog manual
  └─ MOTOR (props idx 0..8) ──► bus_pipeline._extract_motor_source ──► ScSource (SC apenas)
  └─ BUS/LOAD/Tr/CABLE ──► analysis_dialogs.build_pf_system_from_project ──► PowerFlowSystem
                                                                             └─ solve() ──► PowerFlowSolution ──► StudyCache.set_pf (analysis_dialogs ~l.590-600)
main_window._on_analyze_motor_starting (2444) ──► run_motor_starting_analysis (763)
   └─ MotorStartingDialog (valores digitados: P, V, fp, η, I_LR, fp_partida, T_partida, J, V_pre, |Z_th|, tipo de carga)
   └─ MotorStartingCase(bus_thevenin_impedance_ohm=|Z_th| digitado)  ← NÃO usa ShortCircuitStudyResult.z_thevenin_*
   └─ analyze_motor_starting ──► MotorStartingReport ──► show_result_dialog (texto)   ← NÃO grava em StudyCache._motor_starting
main_window._on_analyze_motor_reaccel (2735) ──► MotorState(200 kW, 4160 V) por MOTOR ──► simulate_reaccel ──► texto
```

### 2.2 Fluxo programático (exemplos/benchmarks) [FATO]

`app/examples/ieee399_motor_starting.py:37-54`, `app/validation/benchmarks.py:549-565` (usa `abs(Z_total)` do SC como `bus_thevenin_impedance_ohm`, l. 552-565) e `app/validation/etap_skm_crosscheck.py:353-371` constroem `MotorStartingCase` diretamente. Nenhum deles usa `bus_thevenin_impedance_complex`.

### 2.3 Encadeamento previsto pela arquitetura mas não fechado [INFERÊNCIA]

O docstring de `power_flow.py:16-42` e de `study_cache.py:11-16` descrevem "PF + MOTOR STARTING → SC → COORD → ARC-FLASH" e "Motor Starting usa PF como entrada opcional"; porém (a) o SC aceita `pre_fault_voltage_pu` (`studies/short_circuit.py:114`) mas ninguém o alimenta com `cache.get_pf()`; (b) o slot `_motor_starting` do cache nunca é escrito; (c) o Z_th do SC nunca chega à partida. A cadeia "PF → SC → partida" existe apenas como intenção.

### 2.4 Grandezas que atravessam as fronteiras (unidades) [FATO]

* `MotorStartingCase`: kW (eixo), kV (LL), pu, kg·m², Ω. `MotorStartingReport`: kA, MVA, s, rpm, Ω.
* `MotorState` (reaccel): kW, **V**, kg·m², rpm. `simulate_reaccel`: kVA.
* `PfBus`: pu sobre `base_MVA` (100) e `rated_voltage_kV` (13,8 default); cargas com P < 0.
* `MotorThermalCurve`: A, s; `K_motor` em pu²·s.
* `ComponentReliability`: horas; λ em 1/ano.

---

## 3. Pontos de extensão concretos (incrementais, sem reescrita)

Ordem sugerida do menor para o maior acoplamento.

| # | Arquivo:símbolo | Como estender | Compatibilidade |
|---|---|---|---|
| E1 | `app/postprocessor/motor_starting.py:MotorStartingCase` (l. 229-246) | Anexar **no fim**, com defaults, campos opcionais: `locked_rotor_time_cold_s: float|None=None`, `locked_rotor_time_hot_s: float|None=None`, `insulation_class: str|None=None` (A/E/B/F/H, IEC 60034-1), `starts_per_hour: float|None=None`, `winding_thermal_time_constant_s: float|None=None`, `ambient_temp_C: float=40.0`. | Dataclass frozen; campos com default no fim não quebram os 4 chamadores (GUI l. 773-788, exemplo l. 37-53, benchmarks l. 553-565, crosscheck l. 359-370). |
| E2 | `motor_starting.py:estimate_starting_time_s` (l. 410-453) | Adicionar parâmetro opcional `voltage_pu: float|None=None`; se dado, `T_motor_avg *= voltage_pu**2` (torque de indução ∝ V²). Chamar de `analyze_motor_starting` com `V_during_pu` (l. 511). | Default `None` preserva o comportamento e os 35 testes de `tests/test_pp_motor_starting.py`. |
| E3 | `motor_starting.py:analyze_motor_starting` (l. 481-560) | Após l. 511, se `case.locked_rotor_time_*_s` fornecido: aplicar `DEFAULT_START_TIME_FRACTION_LIMIT` (l. 99, hoje inerte) e rebaixar `acceptance` para MARGINAL/UNACCEPTABLE por tempo; adicionar `rationale`. Preencher novos campos opcionais em `MotorStartingReport` (E4). | Sem alterar `classify_acceptance` (que testes cobrem em l. 125-149). |
| E4 | `motor_starting.py:MotorStartingReport` (l. 290-304) | Anexar campos com default: `start_i2t_kA2_s: float|None=None` (= `starting_current_kA²·starting_time_s`), `thermal_utilization_pu: float|None=None` (= I²t_partida / K_motor·FLA²), `hot_start_margin_s`. Atualizar `summary()` condicionalmente. | Frozen; defaults no fim. |
| E5 | **Novo** `app/postprocessor/motor_thermal_stress.py` | Função pura `compute_start_thermal_stress(report: MotorStartingReport, curve: MotorThermalCurve, *, n_starts_per_hour=None) -> StartThermalStress` (dataclass frozen: I²t, fração da capacidade térmica consumida por partida `I²t/K`, tempo de resfriamento mínimo entre partidas dado `winding_thermal_time_constant_s`). Reutiliza `tcc_damage.MotorThermalCurve.K_motor` (l. 551-557). | Zero mudanças em módulos existentes. |
| E6 | **Novo** `app/postprocessor/insulation_aging.py` | Modelo térmico de isolamento: (i) elevação de temperatura por partida a partir de I²t (adiabático, exigindo massa de cobre/capacidade térmica como entrada declarada); (ii) fator de envelhecimento Arrhenius/Montsinger (regra de "10 K" para classes IEC 60034-1 — a constante e a temperatura de referência por classe devem vir de tabela citada; ver §5); (iii) acúmulo linear (Miner) de vida consumida por evento e por regime; (iv) `remaining_life_fraction`. Sem numpy (segue `reliability_monte_carlo.py` que usa apenas stdlib). Declarar limitações em `audit_trail.KNOWN_LIMITATIONS` (l. 338) com chaves novas, p. ex. `aging_single_hotspot`, `aging_arrhenius_only`. | Módulo novo; dataclasses frozen; `summary()` textual como os demais. |
| E7 | **Novo** `app/postprocessor/studies/motor_starting_study.py` | Seguir a convenção `run(project, bus_id, *, cache=None, config=None, auto_run_prereqs=True)` (`studies/__init__.py:15-24`): prereq SC → obter `complex(z_thevenin_real_ohm, z_thevenin_imag_ohm)` (`short_circuit.py:83-84`) para `bus_thevenin_impedance_complex`; opcional PF → `cache.get_pf().bus_voltages_pu[bus_id]` para `bus_pre_fault_voltage_pu`; ler MOTOR do projeto via `bus_pipeline._extract_motor_source` (l. 559) + novas propriedades (E9); gravar em `cache.set_motor_starting` (`study_cache.py:246-251`, hoje sem uso). Exportar em `studies/__init__.py`. | Fecha a cadeia PF→SC→partida sem tocar `motor_starting.py`. GUI passa a poder substituir o diálogo manual por este estudo. |
| E8 | `app/gui/analysis_dialogs.py:run_motor_starting_analysis` (l. 763-790) | Se `project` e `bus_id` fornecidos e SC em cache: pré-preencher `zth_ohm`/`bus_v_pu` ou chamar E7; manter o diálogo como fallback. `main_window._on_analyze_motor_reaccel` (l. 2735-2765): substituir o `MotorState(200 kW, 4160 V)` fixo por leitura de `rated_power_kW`/`rated_voltage_kV` do MOTOR (índices 2 e 1 do `.ocomp`). | Mudança local na GUI. |
| E9 | `app/preprocessor/catalog_specs/MOTOR.ocomp` | **Anexar ao final** (após `Td_pp_ms`, índice 8) propriedades: `inertia_kg_m2`, `starting_torque_pu`, `load_type`, `insulation_class`, `locked_rotor_time_cold_s`, `locked_rotor_time_hot_s`, `starts_per_hour_max`, `winding_thermal_time_constant_s`. Ampliar `MotorParameters` (`motor.py:140-150`) com os mesmos campos (defaults) e `_extract_motor_source` com `_pf(9..)`. Estender `equipment_catalog.motor_catalog_to_parameters` (l. 554-573) para propagar `inertia_kg_m2`, `starting_torque_pu`, `insulation_class` já existentes em `CatalogMotor` (l. 116-125). | A leitura posicional (`bus_pipeline.py:590-604`) permanece válida se apenas se anexa. Verificar também `bridge_to_atp.py:2011` e testes `tests/test_pp_registry_guard.py` (conta 49 `.ocomp`; não muda ao alterar propriedades). |
| E10 | **Novo** `app/postprocessor/contingency.py` (N-1 sobre `PowerFlowSystem`) | `enumerate_n1(system) -> Iterator[Contingency]` (remoção de cada `PfBranch`; abertura de interruptor via `bus_energization.compute_energization` para detectar ilhamento antes de chamar `solve_power_flow` e evitar Jacobiano singular, l. 538-542); `run_contingency_screen(system, *, tolerance, max_iterations) -> ContingencyReport` com V_min, barras violadas (< 0,95 / limite de partida 0,80/0,85), fluxos; padrão salvar/restaurar setpoints copiado de `power_flow_monte_carlo.py:208-256` e restaurar `type/Q_pu_set/original_type` mutados por `solve_with_q_limits` (l. 763-799). Reaproveitar `PfBranch` intacto: contingência = lista sem o ramo. | Sem alterar `power_flow.py`. `copy.deepcopy(system)` por contingência é aceitável para < 100 barras. |
| E11 | **Novo** `app/postprocessor/load_shedding_optimizer.py` (ou pacote `app/postprocessor/optimization/`) | Vetor de decisão: bits de corte por carga PQ (`PfBus.P_pu_set/Q_pu_set`) + sequência/instante de partida dos motores grandes; avaliação por indivíduo: (1) E10 para a contingência; (2) `analyze_motor_starting` com `bus_thevenin_impedance_complex` derivado do Z de Thevenin pós-contingência (obtido do SC modular ou da inversa de Y-bus de `build_ybus`, l. 327-372 — [HIPÓTESE], requer validação); (3) `simulate_reaccel` só como *screening* (ver §7); (4) E5/E6 como objetivo de estresse térmico. Objetivos: kW cortado, pior dip, vida consumida; restrições: `classify_acceptance ≠ UNACCEPTABLE`, PF convergido. NSGA-II implementado em Python puro com `random.Random(seed)` (mesma filosofia de `reliability_monte_carlo.py`), com `numpy` opcional (já em `requirements.txt`); **não** introduzir `pymoo`/`scipy` sem decisão de dependência (`docs/THIRD_PARTY_NOTICES.md:98` registra "scipy: não adotar agora"). Surrogates de regressão (título do trabalho B) podem substituir (1)-(2) por modelos ajustados sobre amostras geradas por `run_pf_monte_carlo` [HIPÓTESE]. Gate comercial opcional: nova constante em `Feature` + entrada em `FEATURE_TIER_MAP` (`feature_gates.py:71-99`). | Nenhuma alteração nos solvers. |
| E12 | `app/postprocessor/reliability.py:ComponentReliability` (l. 73-120) e `reliability_monte_carlo.run_monte_carlo` (l. 243) | Função nova `aging_adjusted_failure_rate(base: ComponentReliability, life_consumed_fraction) -> ComponentReliability` (E6 → λ); amostrador Weibull opcional ao lado do exponencial (item adiado em `docs/v3.6.0_HANDOFF.md:158`). | Aditivo. |
| E13 | `app/postprocessor/audit_trail.py:KNOWN_LIMITATIONS` (l. 338-383) | Registrar limitações dos novos modelos para aparecerem em `format_limitations_block`/HTML (l. 385-427). | Aditivo. |
| E14 | `app/examples/registry.py` (l. 80-88) + `app/examples/__init__.py:ExampleResult` | Novo exemplo executável (partida + estresse térmico + vida consumida) com `expected` vindos de fonte citável; teste em `tests/test_pp_v<versão>_<feature>.py`. | Padrão do repositório. |
| E15 | `app/preprocessor/scenarios.py:ScenarioManager` (l. 116) | [HIPÓTESE] Representar cada contingência/plano de corte como `PpScenario` clonado (interruptor `state=open`), permitindo `diff_with_base` e reaproveitar a GUI de cenários (`main_window.py:723-728`). | Sem mudanças no manager. |

---

## 4. Grandezas já disponíveis relevantes a estresse dielétrico/térmico

| Grandeza | Onde é calculada | Estado [FATO] | Uso para prognóstico [INFERÊNCIA] |
|---|---|---|---|
| Corrente de rotor bloqueado I_LR (A) | `motor.py:168 locked_rotor_current_A`; `motor_starting.py:501` | Disponível | Amplitude do estresse térmico por partida. |
| Corrente de partida com afundamento, I_during = I_LR·V_during/V_pre | `motor_starting.py:505` → `starting_current_kA` | Disponível | Base do I²t. |
| Tensão durante a partida V_during (pu) e dip (%) | `calculate_voltage_dip_pu` (367-407); `analyze_motor_starting` 489-492 | Disponível; Z_th complexo suportado mas não alimentado pela GUI | Estresse dielétrico indireto (subtensão prolonga a partida); não há sobretensão de manobra aqui (área VCB). |
| Tempo de aceleração t_start (s) | `estimate_starting_time_s` (410-453) | Disponível; independente de V; torque médio constante | Duração do estresse; combinado com I_during² dá I²t. |
| Potência aparente de partida S_during (MVA), Z_M, Z_th | `analyze_motor_starting` 508-509; `calculate_voltage_dip_pu` | Disponível | Dimensionamento de alimentação/partida sequencial. |
| Capacidade térmica do motor K = t_E·(I_LR/FLA)² e t_permitido(I) | `tcc_damage.MotorThermalCurve.K_motor` (551-557), `thermal_time_at_current` (559-578) | Disponível (curva única, sem hot/cold) | Denominador da "fração de capacidade térmica usada por partida". |
| Verificação 49 vs t_LR | `coord_rules_builtin.py:599-668` | Disponível | Restrição de proteção no otimizador. |
| Decaimento de contribuição e^(−t/Td'') | `motor.py:235-262` | Disponível (Td'' 20 ms default) | Irrelevante ao térmico; relevante à área SC/VCB. |
| Σ inrush kVA, v_dip de reaceleração, motores em stall | `motor_reaccel.py:185-236` | Disponível, mas heurístico (ver §7) | Screening de reaceleração após contingência. |
| Tensões de barra, fluxos e perdas (PF) | `solve_power_flow` 551-576 | Disponível | Base para N-1. |
| Q-limits PV→PQ | `solve_with_q_limits` 732-807 | Disponível | Realismo de geradores locais em contingência. |
| P5/P50 de V_min, probabilidade de violação | `run_pf_monte_carlo` 269-292 | Disponível (gated) | Incerteza de carga para surrogates. |
| Estado live/dead por interruptor (inclui VCB) | `compute_energization` 111-181 | Disponível | Detectar ilhamento antes do PF em N-1. |
| λ, MTTR, disponibilidade, presets IEEE 493 | `reliability.py:104-120`; `reliability_monte_carlo.py:59+` | Disponível | Destino do RUL: vida consumida → λ(t). |
| Classe de isolamento (string) | `equipment_catalog.py:124` | Existe só no catálogo; não consumida | Entrada do modelo IEC 60034-1. |
| Fator térmico ambiente | apenas para cabos (`cable_sizing.py:222-240`) | Não existe para motores | Precisa ser criado (E1). |

**Não calculado hoje** [FATO]: I²t de partida; número de partidas/hora (só docstring `motor_starting.py:27`); temperatura de enrolamento/ponto quente; constante de tempo térmica; curvas hot/cold; vida consumida; RUL.

---

## 5. Lacunas (o que NÃO existe)

1. **Modelo térmico de isolamento**: nenhuma equação de Arrhenius/Montsinger, nenhuma tabela de classes térmicas IEC 60034-1, nenhuma temperatura de enrolamento. Único vestígio é o campo string `insulation_class` em `equipment_catalog.py:124`.
2. **I²t de partida e contador de partidas**: `DEFAULT_START_TIME_FRACTION_LIMIT` (l. 99) inerte; `N_starts/hora` apenas citado (l. 27). `MotorThermalCurve` mede capacidade, não consumo.
3. **Dependência t_start(V)**: `estimate_starting_time_s` não usa a tensão; sob afundamento severo o tempo (e o I²t) fica subestimado.
4. **Curva torque × velocidade e simulação dinâmica (TMS)**: todo o bloco "Part 6 — Motor Starting / TMS" da matriz de paridade está pendente (`docs/PTW_SURPASSING_MATRIX.md:211-222`, linhas 88-97, status ⏳; a linha 90 prevê "scipy.solve_ivp + golden NEMA MG-1" e a 92 "+ IEC 60034 motor classes").
5. **Reaceleração física**: `simulate_reaccel` é heurística (constantes 0,3 e 100 sem base declarada; `voltage_dip_duration_s` ignorado; cenário não muda o cálculo; tempo saturado em 30 s — ver §7).
6. **Contingência N-1 / ilhamento / corte de carga**: inexistentes (§1.10). `solve_power_flow` não detecta ilhas (Jacobiano singular → `converged=False` silencioso, l. 538-542).
7. **Otimização (NSGA-II/III, Pareto, surrogates)**: inexistente; nenhuma dependência de otimização em `requirements.txt` (PySide6, anthropic, matplotlib, numpy, pytest, pydantic, PyYAML, openpyxl).
8. **PF desbalanceado real**: `analyze_unbalanced_pf` é placeholder analítico (l. 218-221).
9. **Ligação PF→SC→partida no cache**: `set_motor_starting` sem chamadores; `pre_fault_voltage_pu` do SC nunca alimentado; GUI da partida não lê MOTOR do projeto.
10. **Modelo de motor no esquemático**: `MOTOR.ocomp` sem inércia, torque de partida, t_LR, classe térmica, partidas/hora; `motor_catalog_to_parameters` descarta os campos que o catálogo já tem.
11. **Confiabilidade dependente de idade**: só exponencial; Weibull/aging adiados (`docs/v3.6.0_HANDOFF.md:158`; matriz linha 141).
12. **Sobretensões de manobra / reignição de VCB no contexto de partida**: fora deste módulo; `bus_energization` conhece tipos `VCB/VCB3` apenas como interruptores topológicos.
13. **Dados de referência normativos para validação**: os "expected" do exemplo IEEE 399 são limiares (0,85 pu; < 5 s), não valores de exemplo trabalhado da norma; para um módulo de envelhecimento será preciso um caso de referência citável ([INSERIR CITAÇÃO] para constantes de Arrhenius/Montsinger por classe térmica — não há nada no repositório).

---

## 6. Convenções que um novo módulo deve seguir

[FATO], extraídas de `CONTRIBUTING_ATP_STUDIO.txt` §5-6, `ARCHITECTURE_ATP_STUDIO.txt` §1, `studies/__init__.py`, `audit_trail.py`, `feature_gates.py`, `conftest.py`, workflows CI e dos módulos lidos:

1. **Camadas**: dependências fluem de cima para baixo (GUI → postprocessor → preprocessor/standards → core); nada em `app/postprocessor` importa `app/gui`. Cálculo novo vai em `app/postprocessor/` (ou `app/postprocessor/studies/` se for estudo com prereqs); dados normativos/tabelas em `app/standards/`; parâmetros de equipamento em `app/preprocessor/` + `catalog_specs/*.ocomp`.
2. **Nomenclatura**: arquivos e funções `snake_case`, classes `PascalCase`, Python ≥ 3.11 (`from __future__ import annotations`), sufixos de unidade nos nomes (`_kW`, `_kV`, `_pu`, `_ohm`, `_s`, `_kA`, `_kg_m2`).
3. **Entidades**: `@dataclass(frozen=True)` para casos/resultados; campos novos sempre **no fim e com default**; resultados expõem `summary() -> str`, `warnings: tuple[str, ...]`, `citation`/`references` com norma + seção; `rationale` explicando a decisão.
4. **Docstring de módulo** em PT-BR com seções "Motivação / Modelagem (equações em blocos `::`) / Limitações conhecidas / Referências"; equações e limites citam norma e seção (anti-alucinação declarada em `coord_rules_builtin.py:5-6`, `reliability.py:19-24`).
5. **Limitações declaradas** via `audit_trail.KNOWN_LIMITATIONS` + `format_limitations_block`; hashes de entrada via `compute_input_checksum`/`hash_study_inputs`.
6. **Estudos modulares**: `run(project, bus_id, *, cache=None, config=None, auto_run_prereqs=True)`; checar `cache.get_*_if_valid(hash)`; gravar com `cache.set_*`; levantar `PrerequisiteError` quando faltar prereq e `auto_run_prereqs=False`.
7. **Reprodutibilidade**: Monte Carlo e heurísticas estocásticas com `random.Random(seed)`; sem efeitos colaterais (salvar/restaurar estado, `test_no_side_effects` em `tests/test_pp_v0_80_pf_monte_carlo.py:85`).
8. **Dependências**: `numpy` permitido (PF já usa; `requirements.txt`); `scipy` explicitamente não adotado (`docs/THIRD_PARTY_NOTICES.md:98`); módulos "leves" preferem stdlib (`reliability_monte_carlo.py:21-22`). Novas dependências são "mudança de alto impacto" (`CONTRIBUTING` §14).
9. **Gating comercial**: funções pesadas/premium usam `@requires_feature(Feature.X)`; nomes só via constantes de `Feature`; testes herdam tier `enterprise` do `conftest.py`.
10. **Testes**: `tests/test_pp_v<MAJOR>_<MINOR>_<PATCH>_<feature>.py`, classes `Test*`, sem `QDialog.exec()` (CI headless faz deadlock — comentário em `.github/workflows/test.yml`); exemplos executáveis em `app/examples/` registrados em `registry.py` retornando `ExampleResult`.
11. **Lint**: ruff em modo leniente (`E9,F63,F7,F82`), `ruff format --check` não bloqueante.
12. **i18n/laudo**: strings de resultado em PT-BR; relatórios HTML/PDF consomem `summary()` e `KNOWN_LIMITATIONS`.
13. **Registro**: toda entrega atualiza `CHANGELOG.md` (Keep a Changelog) e `app/core/version.py` (histórico + `VERSION_TUPLE`).

---

## 7. Riscos técnicos

1. **`simulate_reaccel` não é fisicamente consistente** [FATO]: `base_reaccel_time_s = J·ω²/(max(v²,0,01)·100)` (l. 211-214) tem dimensão de energia/100, não de tempo; execução com 3 motores de 1500 kW, J = 80 kg·m², 4160 V dá `time_to_full_speed_s = 30,00 s` tanto com `bus_capacity_kVA = 100 000` (v_dip = 0,700, SUCCESS) quanto com `10 000` (v_dip = 0,300, FAILURE). Usar essa saída como duração de estresse térmico contaminaria qualquer modelo de vida. Recomendação: tratar como *screening* qualitativo e reimplementar a dinâmica (E2/E7) antes de alimentar E6.
2. **t_start independente da tensão** (`estimate_starting_time_s`) → I²t subestimado justamente nos casos críticos (rede fraca, pós-contingência). E2 corrige com compatibilidade.
3. **Z_th da partida vem de dígito manual** (`analysis_dialogs.py:785`) com heurística 90 % indutiva (`motor_starting.py:396-401`); o Z_th complexo do SC existe e não é usado. Resultados de dip na GUI e no estudo programático podem divergir.
4. **Leitura posicional das propriedades do MOTOR** (`bus_pipeline.py:590-604`): inserir propriedades fora do fim do `.ocomp` desloca índices silenciosamente.
5. **Dataclasses frozen com muitos chamadores**: campos obrigatórios novos quebram GUI, exemplo, benchmarks e crosscheck; usar defaults (E1/E4).
6. **Custo do solver em laços de otimização**: `solve_power_flow` recalcula P/Q e Jacobiano com laços Python O(n²) por iteração (l. 458-467, 488-535); para NSGA-II com população × gerações × contingências, o custo pode ser proibitivo acima de dezenas de barras. Mitigações: vetorizar com numpy (aditivo), cachear Y-bus por topologia, surrogates (trabalho B).
7. **Mutação de estado em `solve_with_q_limits`** (l. 784-785, 792-793): reutilizar o mesmo `PowerFlowSystem` entre indivíduos exige restaurar `type`, `Q_pu_set` e `original_type`; padrão de restauração existe em `power_flow_monte_carlo.py:254-256` mas não cobre `type`.
8. **Ilhamento em N-1**: sem detecção de ilhas, remover um ramo pode produzir Jacobiano singular e `converged=False` sem diagnóstico (l. 538-542); usar `compute_energization` antes de resolver.
9. **Topologia de PF derivada do esquemático é heurística** (`build_pf_system_from_project`: cadeia sequencial de barras l. 517-553, cargas atribuídas por distância Manhattan l. 474-500, tensão base fixa 13,8 kV l. 530) — inadequada para enumerar contingências reais. Para o trabalho B, construir `PowerFlowSystem` explicitamente ou implementar um extrator baseado em `wires`/pinos (`bus_pipeline.find_neighbors_of_bus`, l. 234).
10. **`StudyCache.hash_study_inputs` percorre todo o projeto** (l. 309-338) a cada consulta; em laços de otimização, evitar o cache por projeto e trabalhar em memória com `PowerFlowSystem`.
11. **Unidades inconsistentes entre módulos**: `MotorState.rated_voltage_V` (volts) versus `MotorStartingCase.motor_rated_voltage_kV`; `MotorThermalCurve.fla_A` em A versus `starting_current_kA` em kA. Conversões explícitas obrigatórias.
12. **`power_flow_unbalanced` não é solver**; qualquer análise de desequilíbrio (estresse térmico por sequência negativa) exigiria implementação nova.
13. **Gating comercial em MC** (`@requires_feature`): código de otimização que chame `run_pf_monte_carlo` herda a exigência de tier `commercial`; nos testes o `conftest` resolve, mas em runtime "educational" a chamada levanta `LicenseRequiredError` (`feature_gates.py:108-135`).
14. **Ausência de valores de referência citáveis** para validar envelhecimento (§5 item 13); o padrão do repositório exige `expected` com fonte. Sem fonte verificada, marcar [INSERIR CITAÇÃO] e não inventar constantes.
15. **Inconsistência documental no exemplo IEEE 399** (Z_th 0,10 Ω no código vs 0,5 Ω na narrativa) — pequena, mas o exemplo é usado em laudo/GUI; corrigir ao tocar o arquivo.
16. **CI não executa os testes de partida/reaceleração** (subset em `.github/workflows/test.yml`); regressões nessa área só aparecem no sweep local.

---

## Anexo — chamadores e superfícies de contato (para planejamento de mudanças)

* `analyze_motor_starting`: `app/gui/analysis_dialogs.py:789`, `app/examples/ieee399_motor_starting.py:54`, `app/validation/benchmarks.py:565`, `app/validation/etap_skm_crosscheck.py:371`.
* `simulate_reaccel`: `app/gui/main_window.py:2760`, `tests/test_pp_v0_102_0_motor_reaccel.py`.
* `solve_power_flow`/`PowerFlowSystem`: `app/gui/analysis_dialogs.py:437-604`, `app/postprocessor/power_flow_monte_carlo.py:202-243`, `app/examples/stevenson_pf_3bus.py:45-60`, `app/validation/benchmarks.py:291-305`, `app/validation/etap_skm_crosscheck.py:279-294`, `tests/test_pp_v3_3_0_ieee14_golden.py`.
* `compute_energization`: `app/gui/schematic_pp/online_overlay.py:485-492`.
* `StudyCache.get_pf`: `app/gui/plot_widgets.py:554`; `voltage_drop.py:187` (chamada morta, `if False`).
