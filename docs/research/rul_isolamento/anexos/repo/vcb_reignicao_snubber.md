# Mapa da área `vcb_reignicao_snubber` — Olivas Power System Studio

Repositório: `/home/user/olivas-power-system-studio` (HEAD `26d9248`, v4.0.0-beta). Objetivo do mapa: identificar, no pipeline VCB/VCB3 → MODEL de reignição → snubber, quais grandezas de surto (V_pk, dV/dt, número de reignições, energia) já são ou poderiam ser extraídas para alimentar um contador de estresse dielétrico do isolamento de estator de motores de indução de média tensão, e onde um módulo de prognóstico de degradação se encaixa sem reescrever o existente.

Legenda de epistemologia usada em todo o documento:

- **[F]** fato do repositório (código, teste, doc ou histórico git lido integralmente e citado por caminho:linha);
- **[V]** fato verificado por experimento executado nesta sessão (script no scratchpad; nenhum arquivo do repositório foi modificado);
- **[I]** inferência minha a partir de fatos;
- **[H]** hipótese a confirmar com o autor ou com o solver ATP.

Arquivos lidos integralmente: `app/preprocessor/vcb_model_emitter.py` (404 l.), `app/preprocessor/atp_templates/vcb_reignition.mod` (132 l.), `app/validation/validator_vcb.py` (213 l.), `app/core/parser.py` (808 l.), `app/core/project_model.py` (168 l.), `app/preprocessor/spec/models.py` (709 l.), `app/preprocessor/catalog.py` (327 l.; **não existe** `app/preprocessor/spec/catalog.py` — o caminho correto é `app/preprocessor/catalog.py`), `app/preprocessor/catalog_specs/VCB.ocomp`, `VCB3.ocomp`, `BREAKER.ocomp`, `MOTOR.ocomp`, `tests/test_pp_vcb.py` (665 l.), `tests/test_pp_vcb_model.py` (420 l.), `app/analysis/transient_metrics.py`, `app/postprocessor/trt_analyzer.py`, `app/simulation/results_reader.py`, trechos de `app/preprocessor/bridge_to_atp.py` (2461 l.; lidas as faixas 1-100, 1034-1200, 1870-2062, 2325-2410), `app/simulation/runner.py`, `app/standards/iec62271.py`, `app/core/serializer.py`, `app/llm/parametric.py`, e o arquivo de referência `trt_all_motors_dt_ea.atp` (867 l.), recuperado do histórico git (`git show ad308d5:trt_all_motors_dt_ea.atp`; removido do working tree em `404a995`). Cópia do arquivo de referência: `out/repo/_ref_trt_all_motors_dt_ea.atp`.

---

## 1. Inventário de arquivos e símbolos

### 1.1 `app/preprocessor/atp_templates/vcb_reignition.mod` (template ATP MODELS) [F]

| Bloco | Linhas | Conteúdo |
|---|---|---|
| Cabeçalho/referências | 1-39 | CIGRE WG A3.26 TB 570 (2014); EPRI (1989); Helmer & Lindmayer, ISDEIV 1996; descrição do algoritmo; limitação declarada: wiring TACS manual (v0.22.1) |
| `MODEL vcb_reignition` | 41 | nome do MODEL |
| `DATA` | 47-56 | `I_chop_mean {dflt: 5.0}` A; `I_chop_sigma {dflt: 1.0}` A; `didt_crit_0 {dflt: 16.0}` A/µs; `didt_sigma {dflt: 0.034}` A/µs²; `k_dielec {dflt: 17.0}` V/µs; `U0_dielec {dflt: 690.0}` V; `T_bounce {dflt: 5.0e-4}` s; `T_open {dflt: 0.05}` s; `Seed {dflt: 1}` |
| `INPUT` | 58-60 | `i_branch` (A), `v_branch` (V) |
| `OUTPUT` | 62-64 | `switch_cmd` (1 = fechada, 0 = aberta), `reign_count` (contador de reignições) |
| `VAR` | 66-73 | `state` (1 fechada, 0 aberta, 2 "reignindo" — **nunca atribuído** no EXEC), `t_contact`, `i_last`, `I_chop_rnd`, `didt_crit_t`, `U_dielec_t`, `zero_cross` |
| `INIT` | 75-84 | `I_chop_rnd := I_chop_mean + I_chop_sigma * normal(Seed)` (uma amostra por realização) |
| `EXEC` | 86-131 | ver Anexo A |

Descrição das variáveis físicas (fatos do template; interpretação física marcada [I]):

- `I_chop` (`I_chop_mean`, `I_chop_sigma`): corrente de corte (chopping) por polo, amostrada de N(µ, σ²) na inicialização (l. 83). O corte ocorre no cruzamento por zero se `|i_branch| < I_chop_rnd` (l. 96).
- **di/dt crítico**: `didt_crit_t = didt_crit_0 + didt_sigma·(t − T_open)·1e6` (l. 98) — cresce linearmente com o tempo desde o comando de abertura ("endurecimento" da câmara). Se `|Δi/Δt| > didt_crit_t·1e6` (A/s) no instante do corte, reignição imediata (`reign_count += 1`, permanece fechada; l. 99-102). [I] Critério de capacidade de interromper corrente de alta frequência.
- **Recuperação dielétrica**: `U_dielec_t = U0_dielec + k_dielec·(t − t_contact)·1e6` (l. 115), rampa linear em V/µs a partir da tensão residual `U0_dielec`. Se `|v_branch| > U_dielec_t` com a chave aberta → breakdown, `state := 1`, `switch_cmd := 1.0`, `reign_count += 1` (l. 116-121).
- `T_bounce`: tempo de rebote mecânico; o bloco `IF ((t − t_contact) > T_bounce)` (l. 123-126) está **vazio** (só comentário) — não tem efeito [F].
- `T_open`: instante do comando de abertura; a chave só abre em cruzamento por zero com `t ≥ T_open` (l. 94-96).
- **RRDS**: o termo não aparece neste template [F]. Ele aparece apenas no validador (`validator_vcb.py`) e no arquivo de referência (`RRDS_A`, `RRDS_B` — ver §1.9), que usa uma lei **quadrática** de suportabilidade `V_kV = RRDS_A·t_ms + RRDS_B·t_ms²` (ref. l. 140-142), incompatível com a lei linear do template. [I] RRDS = "rate of rise of dielectric strength" (taxa de recuperação da rigidez dielétrica); `k_dielec` do template é o análogo linear de `RRDS_A`.

Grandezas **não** calculadas pelo MODEL: pico de tensão, dV/dt no instante da reignição, instante de cada reignição, energia; `reign_count` é cumulativo e monotônico, sem carimbo de tempo [F].

### 1.2 `app/preprocessor/vcb_model_emitter.py` [F]

| Símbolo | Assinatura | Linhas | Função |
|---|---|---|---|
| `_TEMPLATE_PATH` | `Path` | 43-45 | caminho do template |
| `load_reignition_template()` | `-> str` (`@lru_cache(maxsize=1)`) | 48-61 | lê o template; `cache_clear()` para testes |
| `VCB_REIGNITION_PROPS` | `tuple[tuple[str,int],...]` | 74-83 | mapeia nome DATA → índice em `comp.properties` (VCB 1φ: 2..9) |
| `VCB3_REIGNITION_PROPS` | idem | 86-95 | VCB3: índices 6..13 |
| `VCB_REIGNITION_DEFAULTS` | `dict[str,str]` | 103-112 | defaults CIGRE ("5.0", "1.0", "16.0", "0.034", "17.0", "690.0", "5e-4", "1") |
| `_get_prop_value(comp, index, default="")` | `-> str` | 115-118 | leitura bruta da property |
| `vcb_needs_model(comp)` | `-> bool` | 121-154 | heurística *only-if-customized*: True se algum parâmetro de reignição difere numericamente do default (tol. 1e-9) |
| `build_use_block(comp, instance_name, t_open_value, *, phase=None)` | `-> list[str]` | 162-226 | `USE vcb_reignition AS <inst>`; INPUT `i_branch := I_<suf>`, `v_branch := V_<suf>` (nomes de `measurement_node_names`); DATA `T_open` + 8 params; OUTPUT `SWCMD_<inst> := switch_cmd`, `REIGN_<inst> := reign_count` |
| `build_vcb_tacs_wiring(comp, instance_name, branch_node1, branch_node2, *, phase=None)` | `-> list[str]` | 234-317 | emite cartões TACS `90<nome><n1><n2>` (corrente) e `91<nome><n1><n2>` (tensão). **Não é chamada por `bridge_to_atp.to_atp`** (única chamada fora do módulo: `tests/test_pp_v0_28_4_pro_onda4.py:217-323`) |
| `measurement_node_names(instance_name)` | `-> tuple[str,str]` | 320-332 | `("I_"+sufixo)[:6]`, `("V_"+sufixo)[:6]` com sufixo = últimos 4 chars do nome |
| `build_models_section(components)` | `-> list[str]` | 340-404 | `["/MODELS"] + template + USE...` (1 USE por VCB; 3 USE por VCB3 — `<nome>_A/_B/_C` com `T_open` por fase em props 0/2/4); lista vazia se nenhum VCB customizado |

### 1.3 `app/preprocessor/bridge_to_atp.py` (trechos VCB) [F]

| Símbolo | Linhas | Função |
|---|---|---|
| `from .vcb_model_emitter import build_models_section, vcb_needs_model` | 82 | únicas importações do emitter |
| `_convert_vcb_single_phase(comp, n1, n2, project) -> SwitchComponent` | 1072-1122 | emite `SwitchComponent(type_code="", t_close=props[1], t_open=props[0], ie="0", switch_type="VCB", semantic_type="vcb", is_new=True)`; se `vcb_needs_model` → warning "MODEL de reignição emitido ... Wiring TACS ... é MANUAL" (l. 1104-1110) |
| `_convert_vcb_three_phase(comp, key, node_map, project) -> list[SwitchComponent]` | 1124-1183 | 3 chaves, pinos (0,1)/(2,3)/(4,5), `semantic_type="vcb_3ph_A|B|C"`, `T_open/T_close` por fase (props 0-5) |
| `to_atp(project) -> AtpProject` | 1882-2060 | esqueleto `raw_lines` (l. 1922-1937): `BEGIN NEW DATA CASE`, comentário, cartão dT/Tmax (`1.E-6 .05`), cartão inteiro, `/BRANCH`... ; despacho VCB/VCB3 (l. 2015-2019); `_inject_tacs_section_if_needed` (l. 2052) e `_inject_models_section_if_needed` (l. 2058) ao final |
| `_inject_tacs_section_if_needed(atp, project)` | 2330-2363 | insere `/TACS HYBRID` em `INSERT_AT = 1` |
| `_inject_models_section_if_needed(atp, project)` | 2366-2402 | insere `build_models_section(...)` em `INSERT_AT = 1` (logo após `BEGIN NEW DATA CASE`), desloca `start_line/end_line` de BRANCH/SWITCH/SOURCE e `tail_lines` |

### 1.4 `app/core/parser.py` (leitura do `.atp` — fonte única da verdade) [F]

| Símbolo | Linhas | Relevância |
|---|---|---|
| `parse_file(filepath) -> AtpProject` | 53-144 | header → `/MODELS` → BRANCH/SWITCH/SOURCE/OUTPUT → classificação semântica → nós |
| `_find_section_boundaries` | 147-161 | reconhece apenas `/MODELS`, `/BRANCH`, `/SWITCH`, `/SOURCE`, `/OUTPUT` (não `/TACS`) |
| `_parse_models_section` | 200-274 | **exige** linha `MODELS` (l. 208) e `ENDMODELS` (l. 210); sem `MODELS` → warning e retorna sem parsear (l. 214-216); lê INPUT global `nome {v(NÓ)}` (l. 227-247) e OUTPUT global (l. 250-260) |
| `_parse_model_block` | 277-382 | DATA reconhecida só por regex `\{DFLT:(.+)\}` **maiúsculo** (l. 365); INPUT/OUTPUT/VAR como strings brutas; INIT/EXEC como texto |
| `_parse_use_block` | 385-463 | `USE X AS Y`; INPUT `a:= b`, DATA `a:= v`, OUTPUT `g:=l` |
| `_parse_switch_components` | 564-614 | colunas fixas; `tacs_output` = primeiro token após col. 64 (l. 592-600) |
| `_classify_branch` | 677-715 | **`semantic_type == "snubber"`** se `"SNUB"` ou `"SN"` nos nomes de nós **e** R e C presentes sem L (l. 684-686) — heurística de nome, não de topologia |
| `_classify_switch` | 718-739 | `"measuring"`, `"systematic"`, **`"vcb"`** se `tacs_output` e (`VCB`/`CB`/`DISJ` nos nós) (l. 727-729), `"tacs_controlled"`, `"time_controlled"` |
| `_extract_nodes` | 770-808 | nós também a partir de INPUT global `v(NÓ)` (l. 804) — não reconhece `i(...)` |

### 1.5 `app/core/project_model.py` [F]

`DataParam` (8-12), `InputMapping` (15-19), `OutputMapping` (22-26), `ModelDefinition` (29-41: `inputs/outputs/variables: list[str]`, `data: list[DataParam]`, `init_code`, `exec_code`, `raw_text`), `UseInstance` (44-54), `ModelsGlobalIO` (57-61), `BranchComponent` (64-80; `semantic_type` l. 76 cita "snubber"), `SwitchComponent` (83-99; `semantic_type` l. 95 cita "vcb"), `AtpProject` (142-168; `find_model`, `find_use`).

### 1.6 `app/validation/validator_vcb.py` [F]

| Símbolo | Linhas | Regra |
|---|---|---|
| `validate_vcb(project) -> list[ValidationMessage]` | 7-27 | filtra `models`/`uses` cujo nome começa com `VCB_`; se nenhum MODEL → `[]` |
| `_validate_vcb_model_structure` | 30-73 | **VCB-001** (ERRO) inputs esperados `{V_POS, V_NEG, I_CB}` ausentes; **VCB-002** (ERRO) outputs esperados `{SW_STATE, R_VAL, L_VAL, C_VAL, CB_STATE}` ausentes; **VCB-003** (AVISO) sem parâmetro `RRDS*` em DATA ("needed for TRV withstand") |
| `_validate_vcb_data_ranges` | 76-157 | remove sufixo de fase `rstRST` do nome; **VCB-010** `T_OPEN<0` (ERRO); **VCB-011** `T_OPEN>1 s` (AVISO); **VCB-012** `I_CHOP≤0` (ERRO); **VCB-013** `I_CHOP>20 A` (AVISO, "faixa típica 1-15 A"); **VCB-014/015** `RRDS_A/B ≤ 0` (AVISO); **VCB-016** `RCLOSED ≥ ROPEN` (ERRO); **VCB-017** `DIDT_CRIT ≤ 0` (ERRO) |
| `_validate_vcb_phases` | 160-177 | **VCB-020** (INFO) sufixos após `VCB_R` diferentes de {R,S,T} |
| `_validate_snubber_connection` | 180-213 | **VCB-030** (INFO) há USE de VCB mas nenhum USE com `SNUB` no nome; **VCB-031** (AVISO) output `CB_STATE*` de cada USE VCB não aparece em `inputs.mapped_to` do USE do snubber |

Chamadores: `app/gui/main_window.py:3781`, `app/llm/project_api.py:312`, `app/analysis/report_export.py:85`; teste `tests/test_validation.py:40-48` (depende do arquivo de referência, hoje ausente → `pytest.skip` via `tests/conftest.py:23-25`).

### 1.7 Specs e catálogo [F]

- `app/preprocessor/spec/models.py`: `PropertyGroup.REIGNITION = "reignition"` (l. 117-118); `AtpEmissionKind` (l. 127-181) com `SWITCH_SIMPLE` (141), `MULTI_SWITCH` (144), `MODEL_USE` (169, "gera cartão USE de MODELS referenciando um .mod"), `TACS_SIGNAL` (172), `CUSTOM` (180); `BranchMapping` (382-413); `AtpEmissionSpec` (416-471; `model_ref` obrigatório para `MODEL_USE`, l. 448-450); `LLMHintsSpec` (474-501); `ComponentSpec` (509-709) com `properties_by_group` (707-709).
- `app/preprocessor/catalog_specs/VCB.ocomp`: 10 propriedades (l. 43-129): `T_open`, `T_close` (grupo timing), `I_chop`, `sigma_I_chop`, `didt_crit`, `didt_sigma`, `k_dielec`, `U0_dielec`, `T_bounce`, `Seed` (grupo reignition; descrições com faixas "EPRI 1989 típico 3-8 A", "câmara MT típica 10-30 A/µs", "17 V/µs = EPRI médio"); `atp_emission.kind: switch_simple` (l. 131-133); `llm_hints.typical_applications` inclui "Reignições múltiplas em desconexão de motor de indução" e "Validação de snubber RC" (l. 136-140); referências CIGRE TB 570, EPRI 1989, IEC 62271-100, IEEE C37.011 (l. 141-145).
- `VCB3.ocomp`: 6 pinos por fase (l. 32-56), 14 propriedades (l. 58-173), `atp_emission.kind: multi_switch, count: 3` com `property_mapping t_open/t_close` por fase (l. 175-193); `llm_hints` cita "pole-discrepancy" e "Reignições múltiplas em motores de indução (worst case 3φ)" (l. 195-211).
- `app/preprocessor/catalog.py`: `CatalogEntry` (33-55); `_ENTRIES` VCB/VCB3 (92-93); `get()` registry-first (156-167); `_PROPERTY_LABELS["VCB"]` (264-275) e `["VCB3"]` (278-293) — labels com unidades; `property_labels()` (319-327). Doc do módulo (l. 12-17): "cada `.ocomp` novo vira fonte única de verdade para seu código".
- `MOTOR.ocomp`: componente para contribuição de curto (IEC 60909-0 §6.5 / NBR 17227 §4.2.2), `custom_emitter: motor.emit_motor_metadata_lines` (l. 114-117) — emite **apenas comentários** no `.atp` (`app/preprocessor/motor.py:353`); não há modelo eletromagnético de motor para transitórios (o próprio spec recomenda SM ou "UM, v0.28.x", l. 20-23).
- `BREAKER.ocomp`: `atp_supported: false`; `mechanism: vacuum|SF6|...`, `operating_time_ms`, `arc_time_ms`, `vendor_model` (l. 81-145) — metadados eletrotécnicos, sem emissão ATP.

### 1.8 Pós-processamento existente [F]

- `app/simulation/runner.py`: `RunResult` (11-19), `AtpRunner.run(atp_file_path, timeout, *, stdout_callback, stderr_callback, phase_callback) -> RunResult` (127-318): copia `.atp` para o diretório do executável, roda, coleta `.pl4/.lis/.pch/.dbg` em `runs/<caso>_<ts>/` (`_collect_outputs`, 338-372) e grava `execution.log` (374-394). Sucesso = returncode 0 e sem `/ERROR/` no stdout (l. 268-270).
- `app/simulation/results_reader.py`: `AtpResults` (15-43: `variables`, `time`, `data: dict[str, list[float]]`, `delta_t`); `read_pl4` (46-96) com 3 layouts; `_PL4_TYPE_LABELS` (104-110): prefixo `4`/`14` → `v(NÓ)`, `7` → `c(N1-N2)` (corrente de ramo), `8` → `i(N1-N2)` (corrente de chave), **`9` → `TACS(nome)`** (saídas TACS/MODELS); `find_result_files` (385-405).
- `app/analysis/transient_metrics.py`: `TransientMetrics` (13-26: `peak_value`, `peak_time`, `min_value`, `rms_value`, `frequency_hz`, `damping_ratio`); `TrvMetrics` (29-38: `peak_trv_kv`, `peak_trv_time_us`, `rrrv_kv_per_us`, `first_pole_clear_time_us`, `withstand_ok`, `iec_uc_kv`, `iec_t3_us`); `compute_transient_metrics(time, values, name)` (41-88); `compute_trv_metrics(time, voltage, current_zero_time, rated_voltage_kv)` (91-159) — RRRV = pico/tempo-ao-pico (l. 131, *média*, não derivada máxima), envelope IEC simplificado `kpp=1.3`, `t3 = 4 µs/kV` (l. 150-157); `_find_zero_crossings` (204-215); `_find_peaks` (218-224). Consumidores: `main_window.py:2298`, `report_export.py:93`, `csv_export.py:48` (só `compute_transient_metrics`; **`compute_trv_metrics` não é chamado por nenhum módulo da aplicação**, só por `tests/test_analysis.py:67-79`).
- `app/postprocessor/trt_analyzer.py`: `TrtWaveform(time_s, voltage_kV, opening_time_s, label, phase)` (91-150); `TrtViolation` (158-164); `TrtAnalysisReport` (167-247: `u_c_observed_kV`, `t_to_peak_us`, `rrrv_max_kV_per_us`, margens, `severity`); `_moving_average_filter` (274-296); `_compute_max_rrrv(samples, *, window_us, consider_negative_slope, filter_window)` (299-360) — derivada máxima filtrada, `|slope|`; `analyze_trt(waveform, envelope, *, ...)` (372-487). Sem chamador na GUI (`grep -i trv|trt app/gui` vazio) [V].
- `app/standards/iec62271.py`: `peak_voltage_uc_kV(U_r, kpp, kaf)` (196-236); `TrtEnvelope2Param` (239-289) e `TrtEnvelope4Param` (291-351) com `voltage_at(t_us)`; `trt_envelope_2param` (353), `trt_envelope_4param` (386), `select_envelope_type` (426).
- `app/llm/parametric.py`: `SweepParameter(model_name, param_name, values)` (21-25), `run_parametric_sweep` (81), `linspace_values` (192) — varredura de DATA de USE via `serialize_project` + `AtpRunner`.
- `app/analysis/case_compare.py`: `compare_cases(a, b)` (37) — diff de header/MODEL/USE/contagens.

### 1.9 Arquivo de referência `trt_all_motors_dt_ea.atp` (histórico git, 867 l.) [F]

Gerado pelo ATPDraw em 08/04/2026 a partir de `D:\000 - UFMG - DOUTORADO\PATENTE\MVP\trt_all_motors_dt_ea.acp` (l. 3-4). [H] O segmento de caminho `PATENTE` sugere que o snubber ativo (Trabalho A) esteja em processo de patenteamento. Conteúdo:

- Cartões diversos: dT = 1 µs, Tmax = 45 ms, 60 Hz (l. 7-11).
- `/MODELS` … `MODELS` (l. 12-13); INPUT global `MM0001..MM0009 {v(NÓ)}` (l. 14-23); OUTPUT global de 21 sinais `XX00xx` (l. 24-45).
- `MODEL VCB_Rr` (l. 46-207), `VCB_Rs` (208-369), `VCB_Rt` (370-531): INPUT `V_POS*, V_NEG*, I_CB*`; OUTPUT `SW_STATE*, R_VAL*, L_VAL*, C_VAL*, CB_STATE*`; DATA (14): `T_OPEN, RRDS_A, RRDS_B, I_CHOP, DIDT_CRIT, RCLOSED, ROPEN, RARC, LCLOSED, LOPEN, LARC, CCLOSED, COPEN, CARC` (l. 64-78). Máquina de estados `CB_STATE`: 0 fechada → 1 (contatos separando; ramo com `RARC/LARC/CARC`) → 2 aberta (corte quando `|I_CB| ≤ I_CHOP` ou no cruzamento por zero; ramo `ROPEN/LOPEN/COPEN`) → 3 reignição quando `|V_CB| > 1,1·V_WITH` (l. 181-188) → volta a 2 no próximo zero de corrente (l. 190-205). Suportabilidade: `VWITHSTANDKV = RRDS_A·t_ms + RRDS_B·t_ms²` (l. 140-142) com `t_ms` medido desde o último zero de corrente com `|I_PREV| > 0,01` (l. 129-138).
- `MODEL SNUB_CTRL` (l. 532-582): INPUT `STA, STB, STC`; OUTPUT `GA_P, GA_N, GB_P, GB_N, GC_P, GC_N`; lógica: se qualquer `ST* > 1,9` (i.e., `CB_STATE ≥ 2` = pólo aberto após corte) → `FM := 1` com **latch** (l. 571-573); os seis gates recebem `FM`.
- USEs (l. 583-676): `T_OPEN` = 14,55 ms / 24,75 ms / 24,81 ms (discrepância de pólos); `RRDS_A = 0,801`, `RRDS_B = 1,226`; `I_CHOP` = 1–2 A; `DIDT_CRIT` = 5–15 A/µs; `ROPEN = 1e6`, `RARC = 20`, `LOPEN = 6e-7`, `LARC = 5e-5`, `COPEN = 6`, `CARC = 2e-5`; `SNUB_CTRL` recebe `XX0031/32/33 := CB_STATE r/s/t` (l. 666-668).
- `/BRANCH`: por fase, ramo **TYPE-91** controlado por TACS/MODELS (`91XX0004X0001CTACS  XX0009` = R controlada por `R_VAL`) seguido de ramos com `TACS CONTROL` para L (`XX0008 = L_VAL`) e C (`XX0007 = C_VAL`) (l. 683-700) — [I] modelo de arco/gap como RLC variável comandado pelo MODEL; resistor de neutro 12,009 Ω (l. 701); transformador (l. 702-731); impedância de fonte RL acoplada (l. 732-735); cargas RL em `01ATA/B/C` (l. 736-738; [I] equivalente de motores, coerente com o nome "all_motors"); **capacitores de 30 (unidade conforme COPT em branco; [I] µF) para terra em `XX0034/35/42`** (l. 739-741); resistores 1e10 Ω (l. 742-747); segmento JMARTI 13,8 kV (l. 748-820); cabo 4,16 kV (l. 821-834).
- `/SWITCH` (l. 835-851): por fase um **TYPE-13** `CLOSED` comandado por `SW_STATE` (`XX0010/18/26`) e dois `MEASURING` em série (l. 837-845); **seis TYPE-11** (válvulas) `X0002x↔XX003x` com parâmetros `3.E3  1.  .005` e gates `XX0036..XX0041` = `GA_P..GC_N` (l. 846-851) — [I] par antiparalelo de tiristores por fase comutando o capacitor de 30 (µF) ao terminal do motor: é o "active thyristor snubber" do título do Trabalho A. Coluna 80 = `2` nos TYPE-11 e `1` nos MEASURING (pedido de saída de tensão/corrente).
- `/SOURCE` (l. 852-856): três fontes TYPE-14, 11 718,43 V de pico, 60 Hz, ±120°, `TSTART = −50` ([I] ≈ 1,04 pu de 13,8 kV fase-terra de pico).
- `/OUTPUT` (l. 857-859): tensões em `X0029A-C`, `X0028A-C`, `01ATA-C`, `X0002A-C` (terminais do lado carga do disjuntor).
- [H] Os inputs `I_CB*` estão ligados a `MM0003/6/9 = v(XX0027/XX0019/XX0011)`, que são **nós** entre os dois `MEASURING` em série (l. 838-839, 841-842, 844-845), i.e., tensões de nó e não correntes de chave. Ou o ATPDraw resolve a corrente por outro mecanismo não visível no `.atp`, ou o wiring do `.acp` está equivocado (o corte por `|I_CB| ≤ I_CHOP` estaria operando sobre uma tensão de ~11 kV de pico). Verificar no `.acp`.

Este arquivo é a única instância de "snubber" com semântica de circuito no repositório: o token `snubber` nos módulos Python restringe-se a (i) heurística de nome em `parser._classify_branch` (`SNUB`/`SN` + RC), (ii) cor/legenda "Switch (Snubber)" para chaves **TYPE-11** em `app/gui/topology_widget.py:108-109` e `app/gui/schematic/editor_widget.py:437-438`, (iii) `_validate_snubber_connection`, (iv) filtro `semantic_type` no agente LLM (`app/llm/agent.py:104`). Não existe componente `.ocomp` de snubber nem emissor de snubber no preprocessor [F].

### 1.10 Testes [F]

- `tests/test_pp_vcb.py`: `TestCatalog` (125), `TestPropertyLabels` (152), `TestPinGeometry` (199), `TestCoalescenceVCB3` (243), `TestBridgeVCB1` (299: `switch_type=="VCB"`, `semantic_type=="vcb"`, warning de reignição só com parâmetro customizado), `TestBridgeVCB3` (362: 3 chaves, `vcb_3ph_A/B/C`, `T_open` por fase), `TestVCB3Renderer` (494), `TestEditorVCB3` (546), `TestPropertyPanelVCB3` (582). Requer PySide6 (`importorskip`, l. 40).
- `tests/test_pp_vcb_model.py`: `TestTemplateLoading` (95: presença de `MODEL vcb_reignition`, dos 9 DATA, de "CIGRE"/"A3.26", de `switch_cmd`), `TestVcbNeedsModel` (136), `TestBuildUseBlock` (185), `TestBuildModelsSection` (247: 1 MODEL + N USE), `TestToAtpIntegration` (301: `/MODELS` antes de `/BRANCH`; `sections["BRANCH"].start_line > 50`; serialização preserva ordem `/MODELS,/BRANCH,/SWITCH,/SOURCE`), `TestPropertyMappingIntegrity` (400). Docstring (l. 17-20) declara fora de escopo: execução do solver, wiring automático, validação semântica do MODELS.
- `tests/test_pp_v0_28_4_pro_onda4.py::TestVcbMeasuringWiring` (217-323): cartões 90/91, nomes únicos por instância, coerência USE↔wiring.
- `tests/test_parser.py::TestModels/TestUses` (20-90) e `tests/test_validation.py::TestValidatorVcb` (40-48): contra o arquivo de referência (4 MODELs, 14 DATA, 17 VAR, 3 IN, 5 OUT; `SNUB_CTRL` 3 IN, 6 OUT, 7 VAR) — hoje `skip` por ausência do arquivo.
- `tests/test_pp_trt_analyzer.py`: envelopes IEC e `analyze_trt` com formas de onda sintéticas. `tests/test_analysis.py::TestTrvMetrics` (67-79).

---

## 2. Fluxo de dados

### 2.1 Duas linhagens de modelagem de VCB coexistem [F][I]

**Linhagem L1 — "ATP Studio" (arquivo `.atp` externo, gerado no ATPDraw):**

```
trt_all_motors_dt_ea.atp  ──parse_file──▶ AtpProject{models: VCB_Rr/Rs/Rt, SNUB_CTRL; uses; switches(TYPE-13, MEASURING, TYPE-11); branches(TYPE-91 + TACS CONTROL)}
       │                                          │
       │                                          ├─▶ validate_vcb (VCB-001…031)  ─▶ GUI/relatório/LLM
       │                                          ├─▶ _classify_switch → "vcb" / _classify_branch → "snubber" (heurísticas de nome)
       │                                          └─▶ serialize_project (edição in-place de USE/DATA; parametric.run_parametric_sweep)
       └──AtpRunner.run──▶ .pl4/.lis ──read_pl4──▶ AtpResults ──compute_transient_metrics──▶ GUI/CSV/HTML
```

Física: arco RLC variável + suportabilidade quadrática RRDS (por polo) + snubber tiristorizado a capacitor comandado por `SNUB_CTRL`. Coerente com o título do Trabalho A [I].

**Linhagem L2 — preprocessor Qucs-like (v0.22.1 → v0.28.4-PRO):**

```
PpProject{VCB/VCB3 .ocomp, props 0..9 | 0..13}
   ├─ _convert_vcb_*  ─▶ SwitchComponent(type_code="", switch_type="VCB")   [chave a tempo, sem controle externo]
   └─ vcb_needs_model ─▶ build_models_section ─▶ raw_lines[1:1] = ["/MODELS", template, "USE … AS DJ1", …]
                                                     (sem "MODELS"/"ENDMODELS", sem INPUT/OUTPUT globais, sem cartões 90/91)
```

Física: chopping gaussiano + di/dt crítico linear + recuperação dielétrica linear; contador `reign_count` interno ao MODEL.

### 2.2 Estado real da cadeia L2 (experimento de ida-e-volta) [V]

Script `scratchpad/roundtrip_vcb.py` (VCB 1φ com `I_chop = 8 A`, resistor de 100 Ω; `to_atp` → `serialize_project` → `parse_file` → `validate_project`/`validate_vcb`; saída em `out/repo/_roundtrip_vcb.atp`):

1. `raw_lines[0] = "BEGIN NEW DATA CASE"`, `raw_lines[1] = "/MODELS"`, template nas linhas 2-135, `USE vcb_reignition AS DJ1` na 136 e **só na linha 155 aparecem o cartão de comentário e o cartão dT/Tmax** (`1.E-6 .05`). Isto decorre de `INSERT_AT = 1` (`bridge_to_atp.py:2384`), fixado em v0.22.1 quando `/BRANCH` ocupava a linha 1; os cartões TIME/MISC foram inseridos nas linhas 1-3 em v0.91.10/11 (`CHANGELOG_ATP_STUDIO`; `version.py` histórico) sem atualizar o offset. [I] Ordem de cartões inválida para o ATP (os cartões diversos são posicionais e antecedem `/MODELS`, como no arquivo de referência l. 7-12) — [INSERIR CITAÇÃO ATP Rule Book, seção de *miscellaneous data cards*]. Os testes existentes não detectam (`test_pp_vcb_model.py:327-340` só checam `/MODELS` < `/BRANCH` e `start_line > 50`).
2. INPUT do USE: `i_branch := I_DJ1_`, `v_branch := V_DJ1_` — nomes **não declarados** em nenhum lugar do arquivo (`build_vcb_tacs_wiring` não é invocada por `to_atp`). Warning emitido pela bridge: "Wiring TACS ... é MANUAL nesta versão".
3. Chave emitida: `('', 'N0003', 'N0004', t_close=1e9, t_open=0.05, 'VCB')` — chave a tempo; `switch_cmd` não tem destino (o arquivo de referência usa TYPE-13 com nome do sinal na coluna 65-70, l. 837).
4. Re-parse: `models = []`, `uses = []`, warning `"Keyword MODELS not found inside /MODELS section"`; a chave é reclassificada como `time_controlled` (perde a semântica `vcb`); `validate_vcb` → `[]` (o MODEL emitido é invisível à validação). Ainda que a palavra-chave existisse, `_parse_model_block` não leria os DATA do template (`{dflt: …}` minúsculo vs regex `DFLT:`), e `_validate_vcb_model_structure` apontaria VCB-001/002/003, pois `vcb_reignition` começa com `VCB_` mas tem interface `i_branch/v_branch → switch_cmd/reign_count`.

Conclusão [I]: L2 entrega hoje (a) parametrização e edição rica na GUI/LLM (painel "Reignição", `llm_hints`), (b) um template revisável do algoritmo CIGRE, (c) contagem interna de reignições **não observável** fora do MODEL. Não entrega simulação fechada em malha nem quantidade alguma no `.pl4`. A cadeia observável de ponta a ponta (parser → validador → runner → PL4 → métricas) só existe para L1, e L1 depende de um arquivo hoje fora do working tree.

### 2.3 O `.atp` como fonte única da verdade [F]

- `ORQUESTRADOR_AGENTE_ATP_STUDIO.txt:169-181`: "1. O .atp é a fonte única da verdade. 2. O agente não deve tratá-lo apenas como texto bruto. 3. ... duas camadas: texto bruto e modelo semântico. 4. ... preservar rastreabilidade. 5. ... evitar alterações cegas." e (l. 195-199) a imagem do circuito "não é fonte única da verdade".
- `CONTRIBUTING_ATP_STUDIO.txt:23-30`: princípios "1. o arquivo .atp é a fonte única da verdade; 2. parsing e GUI desacoplados; 3. alterações incrementais; 4. o modelo semântico é a base da inteligência do sistema; 5. robustez e rastreabilidade; 6. compatibilidade com ATP vale mais do que embelezamento".
- `README_ATP_STUDIO.txt` (removido em `404a995`, l. 22-27): "Arquivo .atp como fonte única da verdade; ATP/EMTP como motor de cálculo".
- Implementação: `serializer.py:38-118` reescreve apenas linhas marcadas `modified/deleted/is_new` e blocos USE `modified`, preservando bytes do restante ("preserving the exact bytes of anything that wasn't edited", l. 1-17). `AtpProject.raw_lines` é o texto integral; `sections[...]` são índices sobre ele.
- Tensão arquitetural [I]: a partir de v0.92 o produto foi reposicionado ("ATP secundário", `app/core/version.py:10-16`) e o pipeline L2 gera `.atp` a partir de `PpProject`/`.ocomp` (cujo doc diz que pydantic é o "single source of truth" do **componente**, `spec/__init__.py:8`). Para um módulo de prognóstico, a regra prática que emerge é: o `.atp` efetivamente **executado** (copiado para `runs/<caso>_<ts>/` pelo runner) + seu `.pl4` são a verdade do caso; qualquer grandeza de estresse deve ser rastreável a esse par de arquivos (SHA256 via `audit_trail.compute_input_checksum`).

---

## 3. Pontos de extensão concretos (incrementais)

| # | Arquivo : símbolo | Como estender sem reescrever |
|---|---|---|
| E1 | `app/preprocessor/atp_templates/vcb_reignition.mod` : `OUTPUT`/`VAR`/`EXEC` (l. 62-73, 86-131) | Adicionar VAR e OUTPUT `t_last_reign` (instante da última reignição), `v_reign_pk` (`abs(v_branch)` no passo do breakdown), `dvdt_reign` (`(v_branch − v_last)/timestep` no breakdown) e `n_reign_hf` (reignições por di/dt, l. 101) separado de `n_reign_diel` (l. 120); incrementá-los nos dois pontos onde `reign_count` já é incrementado. Nenhuma alteração de DATA → `VCB_REIGNITION_PROPS` e `TestTemplateLoading` continuam válidos. Preencher o bloco vazio `T_bounce` (l. 123-126) com bloqueio de novas reignições (estado "aberta definitiva"). |
| E2 | `app/preprocessor/vcb_model_emitter.py` : `build_use_block` (l. 221-224) | Espelhar os novos OUTPUT (`TREIG_<inst>`, `VPK_<inst>`, …) mantendo `SWCMD_/REIGN_`. Adicionar função nova `build_models_record_block(instances) -> list[str]` que emita `RECORD` dos outputs para o `.pl4` ([I] mecanismo MODELS `RECORD … AS nome`; [INSERIR CITAÇÃO manual MODELS/ATP Rule Book]); `results_reader._PL4_TYPE_LABELS["9"] = "TACS"` (l. 108) já rotula essas colunas como `TACS(nome)`. |
| E3 | `app/preprocessor/vcb_model_emitter.py` : `build_models_section` (l. 340-404) | Envolver a saída com as linhas `MODELS` (após `/MODELS`) e `ENDMODELS` (antes de retornar), e emitir INPUT global `I_<suf> {i(N1-N2)}` / `V_<suf> {v(N1)}` ([I] sintaxe do arquivo de referência l. 14-23 para `v(...)`; para corrente, [INSERIR CITAÇÃO]) e OUTPUT global `SWCMD_<inst>`, `REIGN_<inst>` — requer passar os nós da chave (disponíveis em `to_atp` via `node_map`). Isso torna a seção parseável por `parser._parse_models_section` (l. 208-216). Ajustar `test_pp_vcb_model.py::TestBuildModelsSection` para contar `MODELS`/`ENDMODELS`. |
| E4 | `app/preprocessor/bridge_to_atp.py` : `_inject_models_section_if_needed` (l. 2366-2402) | Trocar `INSERT_AT = 1` por índice calculado (`atp.sections["BRANCH"].start_line` antes do shift), colocando `/MODELS` **depois** dos cartões dT/Tmax e antes de `/BRANCH`. Teste novo: `raw_lines.index("/MODELS") > índice do cartão "1.E-6"`. Mesma correção em `_inject_tacs_section_if_needed` (l. 2348). |
| E5 | `app/preprocessor/bridge_to_atp.py` : `_convert_vcb_single_phase` / `_convert_vcb_three_phase` (l. 1072-1183) | Quando `vcb_needs_model(comp)`: emitir `type_code="13"`, `switch_type="CLOSED"`, e `tacs_output = f"SWCMD_{inst}"[:6]` (o `serializer._format_switch_line` já reserva o campo — verificar largura, l. 164-191), mais dois `MEASURING` como no arquivo de referência (l. 838-839) para obter `i(...)`. Alternativa mais fiel a L1: emitir ramos TYPE-91 + `TACS CONTROL` (ref. l. 683-688) e reutilizar o MODEL `VCB_R*` como segundo template `vcb_rlc_arc.mod`. Sem alterar o caminho legado (defaults CIGRE ⇒ chave simples), preservando `TestBridgeVCB1/3`. |
| E6 | `app/preprocessor/vcb_model_emitter.py` : `VCB_REIGNITION_PROPS` + `VCB.ocomp`/`VCB3.ocomp` | Adicionar propriedades **ao final** (índices 10+/14+) para não deslocar layout: `n_reign_max`, `rrds_a`, `rrds_b` (lei quadrática L1), `dielectric_law: enum[linear, quadratic]`; `TestPropertyMappingIntegrity` guarda os 8 nomes atuais. |
| E7 | `app/validation/validator_vcb.py` : `validate_vcb` (l. 11-12) | Adicionar segunda família de regras `VCB-04x` para MODELs cujo nome comece por `VCB_REIGN`/`vcb_reignition` (interface `i_branch/v_branch/switch_cmd/reign_count`), mantendo `VCB-00x` para a interface L1. Adicionar `VCB-032`: USE de VCB sem `RECORD` dos contadores (aviso "reignições não observáveis no PL4"). Tornar o regex de DATA do parser case-insensitive (`parser.py:365`, `re.IGNORECASE`) — mudança de 1 linha, compatível com `DFLT:`. |
| E8 | `app/core/parser.py` : `_classify_branch` (l. 684-686) e `_classify_switch` (l. 727-733) | Acrescentar `semantic_type="thyristor_snubber"` para chaves TYPE-11 cujo `tacs_output` case com um OUTPUT de USE contendo `SNUB`/`G?_P|N` (dados já em `project.uses[*].outputs`), e `"vcb"` também para TYPE-13 cujo `tacs_output` case com OUTPUT `SW_STATE*`/`SWCMD_*`. Hoje a GUI já colore TYPE-11 como "Switch (Snubber)" por tipo, não por semântica (`topology_widget.py:108`). |
| E9 | `app/analysis/transient_metrics.py` : novo módulo irmão `app/analysis/dielectric_stress.py` | Consumir `AtpResults` (`results_reader.py:15-43`) e produzir `DielectricStressMetrics` por nó de terminal de motor: `v_pk`, `v_pk_pu` (base = `header.frequency`/tensão nominal de `MOTOR.ocomp.rated_voltage_kV`), `dvdt_max` (reutilizar `trt_analyzer._compute_max_rrrv`, l. 299-360, com filtro e janela), `n_reign` (contagem de eventos: zero-crossings de `i(N1-N2)` da chave com `|di/dt|` alto, ou coluna `TACS(REIGN_*)` quando E2 existir), `t_rise` (10-90 % do primeiro front), `n_events_above(k·U_n)`, energia `∫ v·i dt` em ramo do snubber (`c(N1-N2)` × `v(N)`), e o **acumulador** `∑ f(v_pk, dvdt)`. Registrar em `app/postprocessor/audit_trail.STANDARDS_CATALOG` (l. 71-84) as normas de referência (IEC 60034-18-41/-42, IEC 62271-100, NEMA MG 1 Part 31 — [INSERIR CITAÇÃO exata das seções]). |
| E10 | `app/postprocessor/studies/__init__.py` (padrão `run(project, bus_id, *, cache=None, config=None, auto_run_prereqs=True)`, l. 13-24) e `app/postprocessor/study_cache.py` | Criar `studies/insulation_prognosis.py` com `run(...)` que declare pré-requisitos (resultado `.pl4` do caso; opcionalmente `short_circuit`), use `StudyCache` (l. 123) e `hash_study_inputs` (l. 310); resultado tipado `InsulationPrognosisResult` (dataclass frozen) com trilha de auditoria (`make_audit_header`, l. 295). |
| E11 | `app/llm/parametric.py` : `run_parametric_sweep` (l. 81) e `SweepParameter` (l. 21) | Varredura de `Seed`/`I_chop_sigma`/`T_OPEN` por fase (Monte Carlo de reignições) já é possível sobre USE DATA de um `.atp` L1; acoplar um *collector* (callback pós-caso) que rode E9 sobre cada `.pl4` e agregue distribuições de `n_reign`, `v_pk`. |
| E12 | `app/plugins/registry.py` : `register_study(name)` (l. 40) | Alternativa de baixo acoplamento: empacotar o prognóstico como plugin (`@register_study("insulation_prognosis")`), sem tocar os arquivos da lista travada do Master Protocol. |
| E13 | `app/preprocessor/catalog_specs/` : novo `SNUBBER.ocomp` (`kind: custom`, `custom_emitter`) | Emitir, por fase, capacitor para terra + par TYPE-11 antiparalelo com gates nomeados + `USE SNUB_CTRL` (template `atp_templates/snub_ctrl.mod` copiado de ref. l. 532-582). Entradas: `CB_STATE`/`SWCMD_*` das instâncias VCB. Requer E3 (OUTPUT global). |

---

## 4. Grandezas já disponíveis relevantes a estresse dielétrico/térmico

| Grandeza | Onde existe hoje | Estado | Observações |
|---|---|---|---|
| Pico de tensão (V_pk), instante do pico, mínimo, RMS, média | `transient_metrics.compute_transient_metrics` (41-88) sobre qualquer coluna do `.pl4` | Disponível na GUI (`main_window.py:2298`), CSV e HTML | Sem base pu; sem janela pós-abertura |
| V_pk pós-zero de corrente, RRRV média, tempo ao pico, 1º polo | `compute_trv_metrics` (91-159) | Implementado, **sem chamador** na aplicação | RRRV = pico/tempo (média), não derivada máxima |
| dV/dt máximo filtrado (`rrrv_max_kV_per_us`), `u_c_observed`, violações vs envelope IEC 62271-100, severidade | `trt_analyzer.analyze_trt` (372-487), `_compute_max_rrrv` (299-360) | Implementado e testado; sem integração com `.pl4` nem GUI | Requer `TrtWaveform` em kV e `opening_time_s`; o envelope é de **disjuntor**, não de isolamento de motor |
| Envelope `u_c`, `t3`, `kpp`, `kaf` | `iec62271.py` (167-236, 239-351) | Disponível | Idem |
| Número de reignições | `vcb_reignition.mod:reign_count` (l. 64, 101, 120); `VCB_R*` do arquivo de referência não conta (só transita `CB_STATE` 2↔3) | Interno ao MODEL; **não observável** (sem RECORD, sem wiring) | Ver E1/E2 |
| Corrente de chave `i(N1-N2)`, corrente de ramo `c(N1-N2)`, tensões `v(N)`, sinais MODELS/TACS `TACS(nome)` | `results_reader.read_pl4` + `_PL4_TYPE_LABELS` (104-110) | Disponível se o `.atp` pedir saída (col. 80 do SWITCH; `/OUTPUT`; RECORD) | Tensão de terminal do motor no arquivo de referência: `v(X0002A/B/C)` (l. 857-859) |
| dT, Tmax, frequência | `parser._parse_header` (164-197) → `HeaderInfo` | Disponível | Base para converter passos em µs |
| Parâmetros do disjuntor (I_chop, σ, di/dt, k_dielec, U0, T_bounce, RRDS_A/B, R/L/C de arco) | `.ocomp` (L2) ou `UseInstance.data` (L1) | Disponível/editável (GUI, LLM, `parametric.py`) | Insumo de Monte Carlo |
| Dados de motor | `MOTOR.ocomp` (`rated_voltage_kV`, `rated_power_kW`, `locked_rotor_current_pu`, `Td_pp_ms`), `preprocessor/motor.py` | Só para curto-circuito/partida | Sem capacitância de enrolamento, sem nível de isolamento (BIL/impulso), sem classe térmica |
| Térmico | `postprocessor/tcc_damage.MotorThermalCurve` (l. 450+): curva de dano térmico de rotor bloqueado `K_motor = tE·(I_LR/FLA)²`, `t = K_motor/(I/FLA)²`, `tE` default 10 s "motor padrão Class B insulation" (IEC 60079-7 §6.4.2, NEMA MG-1 §12.45); `CableDamageCurve` (l. 117, NBR 5410 §6.5.4); `cable_sizing.Insulation` (l. 90: PVC/EPR/XLPE só para ampacidade); `BREAKER.ocomp.arc_time_ms`; `motor_starting.py` (`t_start < 0,7·t_locked_rotor_thermal`, "N_starts/hora NEMA MG 1 §20.43", l. 1-50) | Limites de dano I²t e critérios de partida | Não há temperatura de enrolamento, ciclos térmicos acumulados nem modelo de envelhecimento (Arrhenius / classes IEC 60034-1); o próprio módulo declara limitação "single-time-constant" |
| Energia | Apenas energia incidente de arco elétrico (`standards/nbr17227.py`, `epri_arc_flash.py`) | Fora do domínio | Não há `∫v·i dt` para ramos/snubber; a saída "power and energy" do ATP (col. 80 = 4 no SWITCH; [INSERIR CITAÇÃO ATP Rule Book]) não é solicitada por nenhum emissor |
| Índices de confiabilidade (MTBF/MTTR, SAIFI/SAIDI, Monte Carlo exponencial/lognormal) | `postprocessor/reliability.py`, `reliability_monte_carlo.py` (IEEE 1366/493) | Disponível (gated `Feature.RELIABILITY_MC`) | Camada onde um RUL de isolamento poderia ser convertido em taxa de falha por componente (`ComponentReliability`) |

---

## 5. Lacunas (o que NÃO existe)

1. **Malha fechada MODEL ↔ rede na linhagem L2**: `switch_cmd` não comanda a chave; `i_branch/v_branch` não são medidos; `build_vcb_tacs_wiring` é órfã (§1.2, §2.2) [F][V].
2. **Seção `/MODELS` emitida inválida para o próprio parser** (sem `MODELS`/`ENDMODELS`, sem INPUT/OUTPUT globais, `dflt` minúsculo) e **posicionada antes dos cartões dT/Tmax** [V].
3. **Nenhuma grandeza de reignição chega ao `.pl4`**: sem `RECORD`, sem carimbo de tempo por evento, sem V_pk/dV/dt por evento; `reign_count` só existe dentro do MODEL [F].
4. **Sem módulo de estresse dielétrico**: não há V_pk em pu da tensão nominal do motor, contagem de eventos acima de limiar, tempo de frente (10-90 %), taxa de repetição, nem acumulador/contador de estresse. `grep -i "degrada|isolamento|RUL|remaining useful|aging|insulation"` em `app/**/*.py` só encontra: `cable_sizing.Insulation` (tipo de isolação de cabo para ampacidade), `tcc_damage.py` (curvas de dano térmico I²t de cabo/transformador/motor, "Class B insulation" como default de `tE`), `system_prompt.py:38` ("coordenação de isolamento e para-raios ZnO", só texto de prompt) e `laudo_generator.py:57` (uso não técnico). Nenhuma ocorrência de RUL, envelhecimento, ou estresse dielétrico de enrolamento [V].
5. **Sem modelo de isolamento do motor**: `MOTOR.ocomp` não tem capacitância de enrolamento, distribuição de tensão entre espiras, BIL, classe térmica ou histórico de operação; não há representação de alta frequência do motor (o cabo 4,16 kV e a carga RL do arquivo de referência são o proxy) [F].
6. **Sem snubber como componente**: nenhum `.ocomp`, nenhum emissor, nenhum template `SNUB_CTRL` no preprocessor; a única implementação está no `.atp` de referência fora do working tree [F]. O validador (`VCB-030/031`) só reconhece o snubber pela subcadeia `SNUB` no nome do MODEL.
7. **Sem energia dissipada** (arco, snubber, resistor de amortecimento) — nenhum emissor pede saída de potência/energia; nenhum pós-processador integra `v·i` [F].
8. **Sem ligação PL4 → TRV/TRT**: `compute_trv_metrics` e `analyze_trt` não têm chamador de aplicação; não há detecção automática de `opening_time_s` (zero de corrente) a partir de `i(N1-N2)` [V].
9. **Sem multi-realização orquestrada para L2**: `parametric.py` varre DATA de USE em `.atp` já parseado (L1); não há varredura de `Seed` sobre `PpProject`/`.ocomp` nem agregação estatística de contadores [F].
10. **Sem modelo térmico/envelhecimento** (Arrhenius, IEC 60034-1 classes, ciclos de partida NEMA MG 1) além de critérios de aceitação de partida [F].
11. **Fixture de referência ausente** no working tree: 40+ testes (`test_parser.py`, `test_validation.py`, `test_analysis.py` via `REF_FILE`) fazem `skip`; a linhagem L1 está sem cobertura executável no CI público [F].
12. **Validação do MODELS pelo solver**: nenhum teste executa o ATP (`test_pp_vcb_model.py:17-20`); as funções `normal(Seed)`, `timestep`, `abs` do template não foram validadas contra o interpretador MODELS [F].

---

## 6. Convenções que um novo módulo deve seguir

1. **`.atp` executado + `.pl4` como verdade do caso**; toda grandeza derivada deve citar o par (SHA256 via `audit_trail.compute_input_checksum`, l. 135) e o `run_dir` do `RunResult` (`runner.py:11-19`) [F].
2. **Camadas**: parsing em `app/core`, validação em `app/validation` (retornar `list[ValidationMessage]` com `Severity` e código `XXX-NNN`, `validator_models.py:9-19`), execução/leitura em `app/simulation`, métricas em `app/analysis` ou estudo em `app/postprocessor/studies` com `run(project, bus_id, *, cache, config, auto_run_prereqs)`, resultado `@dataclass(frozen=True)` e `summary()` textual (padrão `TrtAnalysisReport`, l. 206-247) [F].
3. **Emissão ATP**: inserir linhas em `AtpProject.raw_lines` e deslocar `sections[*].start_line/end_line` e `tail_lines` (padrão `_inject_*`, `bridge_to_atp.py:2366-2402`), nunca estender o `serializer` (decisão registrada em `CHANGELOG_ATP_STUDIO.txt:9816-9822`); campos fixos via `atp_format.fmt_node/fmt_num` (`atp_format.py:49-147`), nomes de nó ≤ 6 caracteres (`ATP_NAME_MAX_LEN = 6`, `bridge_to_atp.py:93`); templates MODELS como arquivo estático em `atp_templates/` (decisão em `CHANGELOG_ATP_STUDIO.txt:9801-9808`) [F].
4. **Filosofia "exporte o que dá, avise o que faltou"**: limitações vão para `AtpProject.warnings`, não para exceções (`bridge_to_atp.py:1889-1892`; decisão "warning educativo em vez de erro" em `CHANGELOG_ATP_STUDIO.txt:9823-9829`) [F].
5. **Specs `.ocomp`** (pydantic v2, `extra="forbid"`): novas propriedades **ao final** da lista (o índice é o contrato com `PpComponent.properties`), `group` adequado (`PropertyGroup.REIGNITION`/`THERMAL`/`ADVANCED`), `unit`, `min/max`, `description`, `example`, `llm_hints` com `references`, `common_mistakes`, `alternatives`; teste em `tests/test_pp_catalog_specs.py` [F].
6. **Anti-alucinação (Master Protocol, `docs/v1.7.0_MASTER_PROTOCOL.md` §1.3)**: cada fórmula com norma + seção + equação (padrão de docstring de `iec62271.py`, `reliability.py`); valores numéricos em testes com comentário de origem; sem golden value publicado → `@pytest.mark.skip`; registrar normas em `audit_trail.STANDARDS_CATALOG` (l. 71-84) e usar `citation()` (l. 90) [F].
7. **Anti-regressão**: Read-then-Edit, adições > modificações, arquivos novos > edições cirúrgicas, lista travada de arquivos (arc-flash, CT saturation, plugins, DAPPER — `MASTER_PROTOCOL.md` §3), sweep antes/depois; `restore_points/` (não versionado) [F].
8. **Testes**: `tests/test_pp_<versao>_<tema>.py` (228 de 246 arquivos seguem `test_pp_*`), PySide6 opcional via `pytest.importorskip`, fixtures sem GUI quando possível, timeout 60 s no CI (`.github/workflows/test.yml:66-90`, subconjunto CI-safe; sweep total local) [F].
9. **Versão/registro**: bump em `app/core/version.py`; entrada em `CHANGELOG.md` (Keep a Changelog) e handoff em `docs/vX.Y.Z_HANDOFF.md`; "backend órfão é proibido" — toda feature precisa de ponto de entrada na GUI (7ª garantia, `docs/SESSION_HANDOFF.md` §2) [F].
10. **Gating comercial**: recursos Monte Carlo usam `@requires_feature(Feature.*)` (`app/commercial/feature_gates.py:67-80, 289`); testes recebem tier `enterprise` por `conftest` (l. 28-42) [F].
11. **Idioma/estilo**: docstrings e mensagens em português técnico, unidades SI explícitas, referências CIGRE/IEC/IEEE nos cabeçalhos de módulo; nomes de sinais ATP em maiúsculas ≤ 6 chars [F].

---

## 7. Riscos técnicos

| # | Risco | Evidência | Mitigação |
|---|---|---|---|
| R1 | Construir o contador de estresse sobre L2 sem antes fechar a malha e corrigir a emissão produz arquivos que o ATP provavelmente rejeita (ordem de cartões, seção sem `MODELS`) e que o próprio parser ignora | §2.2 [V] | E3, E4, E5 primeiro; teste de ida-e-volta como o do scratchpad; validar 1 caso no solver |
| R2 | Duas físicas de disjuntor incompatíveis (linear `U0 + k·t` vs quadrática `RRDS_A·t + RRDS_B·t²`; reignição por di/dt "imediata" no template vs transição 3→2 no arquivo de referência) sem documento que as reconcilie | §1.1, §1.9 | Parametrizar a lei (E6) e documentar a escolha com fonte primária (CIGRE TB 570; Helmer & Lindmayer 1996 — [INSERIR CITAÇÃO com página]) |
| R3 | O validador `VCB-00x` codifica a interface **privada** do arquivo de referência (`V_POS/I_CB/RRDS`), que não está no repositório público; qualquer MODEL cujo nome comece por `VCB_` (inclusive `vcb_reignition`) gera ERRO se for parseado | `validator_vcb.py:11-12, 30-73`; §2.2 | E7 (famílias de regra por interface) |
| R4 | Possível erro de wiring no arquivo de referência (`I_CB* := v(nó)`) — se confirmado, os resultados TRT/reignição já obtidos com ele podem estar comprometidos | §1.9 [H] | Verificar no `.acp`; comparar `v(XX0027)` com `i(X0001A-XX0027)` no `.pl4` |
| R5 | Falta de cobertura executável de L1 no CI público (fixture removida) → regressões silenciosas em parser/validador/TRT | §5 item 11 | Criar fixture sintética mínima (MODELS + TYPE-13 + MEASURING + TYPE-11) que reproduza a estrutura sem dados proprietários |
| R6 | Métricas de dV/dt dependem de dT (1 µs no arquivo de referência) e do filtro de média móvel (`_compute_max_rrrv`, janela 5) — valores de estresse podem variar com o passo e com o filtro | `trt_analyzer.py:274-296` | Fixar dT e parâmetros de filtro como parte do "caso" (entram no SHA256); estudar sensibilidade |
| R7 | `read_pl4` tenta três layouts e retorna o primeiro que "parece" válido (`results_reader.py:66-96`); variável `TACS(nome)` para saídas MODELS só no layout GNUATP | l. 104-126 | Testar com `.pl4` reais do ATP usado pelo autor; validar contagem de colunas contra `/OUTPUT` + RECORD |
| R8 | `MOTOR.ocomp` emite apenas comentários (`emit_motor_metadata_lines`) — em L2 o motor não existe eletricamente; qualquer simulação de surto em L2 usa carga RL/SM como proxy | `motor.py:353`; `MOTOR.ocomp:20-23` | Documentar explicitamente; para L2, fornecer template de motor HF (RL + capacitâncias) como `custom_emitter` |
| R9 | `reign_count` é monotônico e único por USE; em VCB3 há 3 USE com `Seed` idêntico → realizações correlacionadas (o próprio `VCB3.ocomp:208` lista isso como erro comum) | `build_use_block` usa o mesmo `Seed` para A/B/C (l. 216-220) | Derivar `Seed + k` por fase no emitter |
| R10 | Interpretação de unidades no arquivo de referência (`COPEN = 6`, `LCLOSEDs = 1.` vs `0.002` nas outras fases; `LARC = 5e-5`) sugere inconsistências de parametrização no caso de origem | ref. l. 589-656 | Confirmar unidades com XOPT/COPT em branco (mH/µF) e com o autor antes de reutilizar como *golden case* |
| R11 | Dependências: `pydantic`/`PyYAML` são obrigatórios para importar `app.preprocessor` (falha em ambiente limpo); `PySide6` para testes de GUI | §2.2 (instalação necessária para o experimento) | Módulo de prognóstico deve depender só de `app.simulation`, `app.analysis`, `app.core` quando possível |
| R12 | Licenciamento/clean-room: o template cita CIGRE TB 570 e EPRI 1989 como fonte do algoritmo; não há verificação linha a linha registrada; TB 570 trata de arco interno em GIS (título no template l. 7-9), não de reignição em VCB | `vcb_reignition.mod:6-12`; `docs/LICENSING.md` | Revisar a atribuição bibliográfica; para reignição em VCB as fontes canônicas são Helmer & Lindmayer (1996), Glinkowski et al. (1997), Popov et al. — [INSERIR CITAÇÃO] |

---

## Anexo A — Semântica do `EXEC` de `vcb_reignition.mod` (l. 86-131) [F]

```
zero_cross := (i_last * i_branch < 0)                               -- l. 88-91
IF state = 1 AND t >= T_open THEN                                    -- l. 94
  IF zero_cross AND |i_branch| < I_chop_rnd THEN                     -- l. 96
    didt_crit_t := didt_crit_0 + didt_sigma*(t - T_open)*1e6         -- l. 98  [A/µs]
    IF |(i_branch - i_last)/timestep| > didt_crit_t*1e6 THEN         -- l. 99  [A/s]
      reign_count += 1        (reignição por di/dt; permanece fechada)  -- l. 101
    ELSE
      state := 0; t_contact := t; switch_cmd := 0.0                  -- l. 105-107 (corte)
IF state = 0 THEN                                                    -- l. 113
  U_dielec_t := U0_dielec + k_dielec*(t - t_contact)*1e6             -- l. 115 [V]
  IF |v_branch| > U_dielec_t THEN
    state := 1; switch_cmd := 1.0; reign_count += 1                  -- l. 118-120 (breakdown)
  IF (t - t_contact) > T_bounce THEN  (vazio)                        -- l. 123-126
i_last := i_branch                                                   -- l. 130
```

Observações [I]: (i) após uma reignição dielétrica, a chave volta a `state = 1` e o próximo zero de corrente (inclusive de alta frequência) reaplica o critério de di/dt — comportamento compatível com interrupção de corrente HF; (ii) `T_close` do componente nunca chega ao MODEL (não há pré-arco/*prestrike* no fechamento); (iii) não há limite superior de reignições nem "abertura definitiva" — a rampa `k_dielec` é o único mecanismo de extinção.

## Anexo B — Comparação de interfaces dos MODELs

| Item | `vcb_reignition` (L2, template) | `VCB_Rr/Rs/Rt` (L1, referência) |
|---|---|---|
| INPUT | `i_branch`, `v_branch` | `V_POS`, `V_NEG`, `I_CB` |
| OUTPUT | `switch_cmd`, `reign_count` | `SW_STATE`, `R_VAL`, `L_VAL`, `C_VAL`, `CB_STATE` |
| DATA | 9 (`I_chop_mean/sigma`, `didt_crit_0/sigma`, `k_dielec`, `U0_dielec`, `T_bounce`, `T_open`, `Seed`) | 14 (`T_OPEN`, `RRDS_A/B`, `I_CHOP`, `DIDT_CRIT`, R/L/C ×{CLOSED, OPEN, ARC}) |
| Suportabilidade | linear `U0 + k·Δt` (V/µs) | quadrática `RRDS_A·t_ms + RRDS_B·t_ms²` (kV), fator 1,1 |
| Estocástico | `normal(Seed)` em `I_chop` | determinístico |
| Acoplamento à rede | nenhum emitido (previsto: TYPE-13 + TACS 90/91) | TYPE-13 (`SW_STATE`) + TYPE-91 R controlada + `TACS CONTROL` L e C + 2 MEASURING |
| Snubber | não | `SNUB_CTRL` → 6 TYPE-11 (gates `G?_P/N`), latch por `CB_STATE ≥ 2` |
| Contador de reignições | `reign_count` (interno) | nenhum |
| Validador | ignorado (não parseado); se parseado → VCB-001/002/003 | `VCB-00x` satisfeitas (`test_validation.py:44-48`) |

## Anexo C — Saída do experimento de ida-e-volta [V]

Script: `scratchpad/roundtrip_vcb.py`; arquivo gerado: `out/repo/_roundtrip_vcb.atp`.

```
WARNINGS: VCB 'DJ1': MODEL de reignição emitido no bloco /MODELS. Wiring TACS (...) é MANUAL nesta versão ...
switch emitido: type_code='' N0003 N0004 t_close=1000000000 t_open=0.05 switch_type=VCB semantic=vcb
raw_lines[0..1] = BEGIN NEW DATA CASE, /MODELS ; USE ... AS DJ1 na linha 136 ; cartão dT/Tmax na linha 155-156
reparse: models=[] uses=[] ; parser warnings=['Keyword MODELS not found inside /MODELS section']
switch reparseado: ('', 'N0003', 'N0004', 'VCB', tacs_output='', 'time_controlled')
validate_project: SYN-005 (/SOURCE vazio), SYN-005 (/OUTPUT vazio) ; validate_vcb: []
```
