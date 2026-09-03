# Área `trt_transitorios_simulacao` — cadeia de simulação e análise de transitórios

Repositório: `/home/user/olivas-power-system-studio` (branch `claude/isolamento-degradacao-monitoramento-dr900x`, árvore de trabalho limpa; nada foi modificado).
Objetivo do mapeamento: identificar o que já existe na cadeia ATP → PL4 → métricas → relatório para que um futuro módulo de **perfil de estresse dielétrico** (contagem de surtos, extração pico-vale tipo *rainflow* em dV/dt e V_pk, agregação por evento de chaveamento) consuma as estruturas atuais sem reescrevê-las.

Legenda usada ao longo do texto: **[fato]** = verificado no código, com caminho e linha; **[inferência]** = conclusão minha a partir do código; **[hipótese]** = suposição a confirmar.

---

## 1. Inventário de arquivos e símbolos

### 1.1 `app/simulation/runner.py` (394 linhas) — execução do ATP

| Símbolo | Linha | Assinatura / conteúdo |
|---|---|---|
| `RunResult` (dataclass) | 11–19 | `success: bool`, `return_code: int`, `stdout: str`, `stderr: str`, `message: str`, `run_dir: str`, `log_file: str` |
| `_ATP_OUTPUT_EXTS` | 23 | `(".pl4", ".PL4", ".lis", ".LIS", ".pch", ".PCH", ".dbg", ".DBG")` |
| `AtpRunner.__init__` | 27 | `(executable_path: Optional[str] = None, timeout: int = 120)` |
| `AtpRunner.is_configured` | 33 | `() -> bool` |
| `AtpRunner._stream_subprocess` | 38–101 | drena stdout/stderr em threads; lança `TimeoutExpired` |
| `AtpRunner.kill_process` | 103–125 | cancelamento pela GUI |
| `AtpRunner.run` | 127–318 | `(atp_file_path, timeout=None, *, stdout_callback=None, stderr_callback=None, phase_callback=None) -> RunResult`; fases `"validating"…"done"` (145–152); sucesso = `returncode == 0 and "/ERROR/" not in stdout` (263–265) |
| `AtpRunner._create_run_dir` | 320–326 | cria `<dir_do_atp>/runs/<stem>_<YYYYmmdd_HHMMSS>/` |
| `AtpRunner._clean_outputs` | 328–336 | remove saídas antigas no diretório do executável |
| `AtpRunner._collect_outputs` | 338–372 | copia `.pl4/.lis/...` para `run_dir` **e** para o diretório do `.atp` |
| `AtpRunner._save_log` | 374–394 | grava `run_dir/execution.log` (metadados + stdout + stderr) |

**[fato]** O runner não lê resultados; apenas os posiciona. O `run_dir` fica em `RunResult.run_dir` (285), mas nenhum consumidor atual usa esse caminho para ler o PL4 (ver §2).

### 1.2 `app/simulation/results_reader.py` (405 linhas) — leitura PL4/LIS

| Símbolo | Linha | Assinatura / conteúdo |
|---|---|---|
| `AtpResults` (dataclass, mutável) | 15–43 | `file_path: str`, `variables: list[str]`, `time: list[float]`, `data: dict[str, list[float]]`, `delta_t: float`, `n_steps: int`; `get_variable(name)` (24, *case-insensitive*), `get_time_range()` (31), `summary()` (36) |
| `read_pl4` | 46–96 | `(filepath: str) -> AtpResults`; tenta GNUATP → Fortran → direto; exceções internas silenciadas (`except Exception: pass`, 71/80/89) |
| `_PL4_TYPE_LABELS` | 104–110 | `"4"→"v"`, `"7"→"c"`, `"8"→"i"`, `"9"→"TACS"`, `"14"→"v"` |
| `_format_pl4_varname` | 113–126 | nome final `"<label>(<node1>-<node2>)"` ou `"<label>(<node1>)"` |
| `_parse_pl4_gnuatp` | 129–189 | `delta_t` em offset 40 (`<f`, float32 LE), nomes de 16 bytes a partir do offset 80, registros `(1+n_vars)×float32` |
| `_parse_pl4_fortran` | 197–287 | registros com marcadores de 4 bytes; nomes de 6 ou 8 caracteres |
| `_parse_pl4_direct` | 295–356 | cabeçalho `n_vars, n_steps, delta_t` + nomes de 6 bytes |
| `_read_rec_marker` | 359–364 | helper |
| `read_lis` | 372–377 | `(filepath) -> str` — texto bruto, **sem parsing** |
| `find_result_files` | 385–405 | `(atp_filepath) -> dict[str, str]` com chaves `"pl4"`, `"lis"`; procura **apenas ao lado do `.atp`**, não em `runs/` |

**[fato]** Todos os dados são `float32` convertidos para `list[float]` Python (184–187); não há `numpy` neste módulo nem em `app/analysis/*`.
**[fato]** Não há metadado de unidade em `AtpResults` (volts vs kV; A vs kA): o PL4 é lido "como está".

### 1.3 `app/analysis/transient_metrics.py` (224 linhas) — métricas básicas e TRV

| Símbolo | Linha | Assinatura / conteúdo |
|---|---|---|
| `TransientMetrics` (dataclass) | 13–26 | `variable_name`, `peak_value`, `peak_time`, `min_value`, `min_time`, `rms_value`, `mean_value`, `frequency_hz: Optional`, `damping_ratio: Optional`, `settling_time: Optional` (**declarado e nunca calculado** — único uso é a própria declaração, verificado por `grep`), `n_samples` |
| `TrvMetrics` (dataclass) | 29–38 | `peak_trv_kv`, `peak_trv_time_us`, `rrrv_kv_per_us`, `first_pole_clear_time_us`, `withstand_ok: Optional[bool]`, `iec_uc_kv`, `iec_t3_us` |
| `compute_transient_metrics` | 41–88 | `(time: list[float], values: list[float], variable_name="") -> TransientMetrics`. Pico/mínimo **com sinal** (51–54); média/RMS (57–58); frequência por cruzamentos de zero (72–77, meio-período médio); amortecimento por decremento logarítmico entre `peaks[0]` e `peaks[2]` (80–86) |
| `compute_trv_metrics` | 91–159 | `(time, voltage, current_zero_time=0.0, rated_voltage_kv=None) -> TrvMetrics`. Entrada em **volts** (127: `/1000.0`); pico = máx de `abs()` após `current_zero_time` (122–128); **RRRV = pico_kV / t_pico_µs** (131: taxa **média** até o pico, não derivada instantânea); "primeiro polo" = instante em que `abs(v) ≥ 0,1·pico` (134–139); comparação IEC simplificada com `kpp=1.3`, `uc = 1.3·Ur·√2/√3`, `t3 = 4·uc` (149–157) |
| `format_transient_report` | 162–177 | texto PT-BR |
| `format_trv_report` | 180–196 | texto PT-BR |
| `_find_zero_crossings` | 204–215 | `(time, values) -> list[float]`; interpolação linear; só detecta `v[i]·v[i+1] < 0` (ignora amostra exatamente zero) |
| `_find_peaks` | 218–224 | `(values) -> list[int]`; máximos locais de `abs(v)` com desigualdade estrita (platôs são perdidos) |

**[fato]** A comparação IEC em `compute_trv_metrics` (149–157) **não usa `kaf`** e usa `t3 = 4·uc` "simplificado" — inconsistente com `app/standards/iec62271.py` (`peak_voltage_uc_kV`, 196–231, que aplica `kpp·kaf`). Existem, portanto, **duas definições de RRRV e duas de u_c** no repositório (ver §7).

### 1.4 `app/postprocessor/trt_analyzer.py` (487 linhas) — TRT vs envelope IEC 62271-100

| Símbolo | Linha | Assinatura / conteúdo |
|---|---|---|
| Docstring do módulo | 1–74 | fluxo de uso; métricas; referências citadas: IEC 62271-100:2021 §6.102.10, IEC 62271-200:2021, CIGRE TB 304 (71–73) |
| `TrtWaveform` (frozen dataclass) | 91–150 | `time_s: tuple[float,...]`, `voltage_kV: tuple[float,...]`, `opening_time_s: float`, `label=""`, `phase=""`; `__post_init__` (131–150) valida comprimento igual, ≥2 pontos, monotonicidade e `opening_time_s` dentro do intervalo. **Unidade: kV** |
| `TrtViolation` (frozen) | 158–164 | `t_us`, `v_observed_kV`, `v_envelope_kV`, `margin` |
| `TrtAnalysisReport` (frozen) | 167–247 | `passed`, `violations: tuple[TrtViolation,...]`, `u_c_observed_kV`, `t_to_peak_us`, `rrrv_max_kV_per_us`, `u_c_envelope_kV`, `rrrv_envelope_kV_per_us`, `margin_uc`, `margin_rrrv`, `duty: TestDuty`, `rated_voltage_kV`, `envelope_type`, `waveform_label`, `waveform_phase`, `source="IEC 62271-100:2021"`; propriedade `severity = max(margin_uc, margin_rrrv)` (202–204); `summary()` (206–247) |
| `Envelope` | 255 | `Union[TrtEnvelope2Param, TrtEnvelope4Param]` |
| `_samples_after_opening` | 258–271 | `(waveform) -> list[tuple[t_us_rel, v_kV]]` |
| `_moving_average_filter` | 274–296 | `(samples, window=5)`; média móvel central |
| `_compute_max_rrrv` | 299–360 | `(samples, *, window_us=None, consider_negative_slope=True, filter_window=5) -> float`; **máx de |Δv/Δt|** (kV/µs) após filtro; cita IEC 62271-100 §6.111.4 (313–316) |
| `_envelope_uc_and_rrrv` | 363–369 | extrai `(u_c, rrrv_ref)` do envelope |
| `analyze_trt` | 372–487 | `(waveform, envelope, *, rrrv_window_us=None, rrrv_filter_window=5, rrrv_consider_negative_slope=True) -> TrtAnalysisReport`; violação quando `abs(v) > envelope.voltage_at(t)` (451–462); `passed` exige zero violações e ambas as margens ≤ 1 (466–470) |

**[fato]** `analyze_trt`/`TrtWaveform` **não têm nenhum consumidor** em `app/gui`, `app/llm`, `app/postprocessor/report_html.py`, `report_pdf.py` ou `app/postprocessor/studies` (grep vazio). Só são exercitados em `tests/test_pp_trt_analyzer.py` e `tests/test_pp_v0_28_1.py` (265–350). A própria docstring (55–66) admite que o leitor PL4 "virá em v0.27.1.5" — ou seja, a ponte PL4 → `TrtWaveform` nunca foi escrita.

Suporte normativo em `app/standards/iec62271.py`: `TestDuty` (93), `GroundingType` (108), `_AMPLITUDE_FACTORS` (130–138), `_TYPICAL_RRRV` (145–153), `VOC_4PARAM_THRESHOLD_KV = 100.0` (159), `first_pole_factor_kpp` (167), `amplitude_factor_kaf` (182), `typical_rrrv_kV_per_us` (189), `peak_voltage_uc_kV` (196–231), `TrtEnvelope2Param` (240–288, `voltage_at` 281), `TrtEnvelope4Param` (292–350, `voltage_at` 340), `trt_envelope_2param` (353), `trt_envelope_4param` (386), `select_envelope_type` (426). **[fato]** Os valores de `kaf` e RRRV típicos são declarados no código como "valores típicos/representativos" (125–153), não como transcrição literal de tabela.

### 1.5 `app/analysis/case_compare.py` (152 linhas) — diff de **entradas**

| Símbolo | Linha |
|---|---|
| `ParamDiff` (`category`, `label`, `value_a`, `value_b`) | 14–20 |
| `CompareResult` (`file_a`, `file_b`, `diffs`, `summary_a`, `summary_b`; `has_diffs`) | 23–34 |
| `compare_cases(a: AtpProject, b: AtpProject) -> CompareResult` | 37–51 |
| `_compare_header` (delta_t, t_max, frequency) | 71–80 |
| `_compare_models` (defaults de DATA) / `_compare_uses` (valores atribuídos) / `_compare_counts` | 83–110 / 113–140 / 143–152 |

**[fato]** Compara projetos (`.atp`), não resultados (`AtpResults`). Não há comparação de formas de onda ou de métricas entre casos.

### 1.6 `app/analysis/csv_export.py` (66 linhas)

| Símbolo | Linha |
|---|---|
| `export_waveforms_csv(results: AtpResults, output_path) -> str` — cabeçalho `time_s` + variáveis | 18–34 |
| `export_metrics_csv(results, output_path) -> str` — roda `compute_transient_metrics` para todas as variáveis; lista **explícita** de campos (55–58) com `DictWriter(..., extrasaction="ignore")` | 37–66 |

**[fato]** Campos novos em `TransientMetrics` **não** aparecem no CSV a menos que sejam acrescentados à lista das linhas 55–58.

### 1.7 `app/analysis/report_export.py` (365 linhas)

| Símbolo | Linha |
|---|---|
| `_logo_base64` | 27–46 |
| `generate_html_report(project, pl4=None, messages=None) -> str` — auto-carrega PL4 via `find_result_files` (73–79); métricas para as 50 primeiras variáveis (88–93) | 57–99 |
| `_render_html(project, filename, timestamp, logo_b64, messages, metrics, pl4)` — tabela de métricas (146–160; seção 225–237) | 102–325 |
| `export_html_report(project, output_path)` | 328–332 |
| `export_pdf_report(project, output_path)` — depende de PySide6/QPrinter | 335–365 |

**[fato]** O HTML é montado por f-strings; comentário nas linhas 205–206 registra restrição de compatibilidade com Python 3.11 (sem f-strings aninhadas com mesmas aspas). CI testa 3.11/3.12/3.13 (`.github/workflows/test.yml:19`).

### 1.8 `app/validation/benchmarks.py` (635 linhas)

| Símbolo | Linha |
|---|---|
| `StudyType` (`SC`, `PF`, `AF`, `MS`, `COORD`, `SEQ`) — **não há tipo para transitório/TRT** | 48–54 |
| `BenchmarkCase` (frozen: `name`, `reference`, `description`, `inputs`, `expected`, `tolerance_pct`, `study_type`) | 57–85 |
| `BenchmarkResult` (frozen; `summary()`) | 88–114 |
| `ValidationReport` (frozen; `all_passed`, `summary()`) | 117–142 |
| `_check(case, computed) -> (passed, max_err, failed_keys)` — erro relativo percentual | 145–163 |
| Benchmarks: IEC 60909 Annex C (171), IEEE 9-bus subset (245), IEEE 1584 D.4 (349), Stevenson §11 (421), "Industrial petroquímica BR" (488, valores **não publicados/calibrados internamente**, 516–517) | |
| `_BENCHMARKS` (tupla de callables) / `run_all_benchmarks()` / `list_benchmark_names()` | 607–613 / 616–625 / 628–630 |

**[fato]** Nenhum benchmark cobre formas de onda, TRT ou RRRV. `numpy` é tratado como opcional (279–288).

### 1.9 Consumidores atuais da cadeia

| Consumidor | Linhas | O que faz |
|---|---|---|
| `app/gui/main_window.py` | 2285–2298 | `read_pl4` → `waveform.load_results(pl4)` → `compute_transient_metrics` para as 30 primeiras variáveis → `format_transient_report` |
| `app/gui/main_window.py` | 2324–2337, 2339–2368 | `_get_pl4_results`, exportação CSV de ondas/métricas |
| `app/gui/waveform_widget.py` | 122–140 | `load_results(results: AtpResults)`; plot matplotlib |
| `app/llm/project_api.py` | 364–384 | `export_csv(output_path, mode="metrics"|"waveforms")` |
| `app/llm/parametric.py` | `SweepParameter` 21–25, `SweepCase` 29–36, `SweepResult` 40–45, `run_parametric_sweep(base_file, parameters, runner, output_dir=None)` 81–166 | varredura cartesiana de `USE.DATA`; **não lê PL4**, guarda só `success/message/log_file` (152–157) e **não guarda `run_dir`** |

### 1.10 Fontes de sinal relevantes (VCB/reignição) — fora da área, mas alimentam a cadeia

| Arquivo | Linha | Conteúdo |
|---|---|---|
| `app/preprocessor/atp_templates/vcb_reignition.mod` | 47–56 | DATA: `I_chop_mean` (A), `I_chop_sigma`, `didt_crit_0` (A/µs), `didt_sigma` (A/µs²), `k_dielec` (V/µs), `U0_dielec` (V), `T_bounce` (s), `T_open` (s), `Seed` |
| idem | 58–64 | INPUT `i_branch`, `v_branch`; OUTPUT `switch_cmd` (1/0), `reign_count` (contador acumulado de reignições) |
| idem | 83 | `I_chop_rnd` amostrado **uma vez por simulação** (Monte Carlo por `Seed`) |
| idem | 113–121 | recuperação dielétrica linear `U_dielec_t = U0_dielec + k_dielec·(t − t_contact)·1e6`; *breakdown* quando `abs(v_branch) > U_dielec_t` → `reign_count += 1` |
| `app/preprocessor/vcb_model_emitter.py` | 103–112 | defaults CIGRE WG A3.26 (declarados como tal na docstring, 99) |
| idem | 222–224 | OUTPUT globais `SWCMD_<instância>` e `REIGN_<instância>` |
| idem | 234–317, 320–332 | wiring TACS-90 (corrente `I_<suf4>`) e TACS-91 (tensão `V_<suf4>`) por instância; sufixo = últimos 4 caracteres do nome (299–301) |
| `app/validation/validator_vcb.py` | 7–27, 180–213 | valida modelos `VCB_*` (I_CHOP, RRDS_A/B, DIDT_CRIT, T_OPEN) e conexão `CB_STATE → SNUB_CTRL` (snubber) |
| `app/core/parser.py` | 686, 729 | classificação semântica de chaves: `"snubber"`, `"vcb"` |

**[inferência]** As saídas `REIGN_<inst>` e `SWCMD_<inst>` chegam ao PL4 como variáveis TACS/MODELS (label `"TACS"` se o parser GNUATP identificar o prefixo `"9"`, `results_reader.py:108`). Isso precisa ser confirmado com um PL4 real, pois **não há nenhum PL4 de exemplo no repositório** (`find . -iname "*.pl4"` vazio) e o `.atp` de referência dos testes (`tests/conftest.py:12`, `trt_all_motors_dt_ea.atp`) foi removido no release público (docstring 17–20).

---

## 2. Fluxo de dados

```
.atp ──AtpRunner.run()──▶ runs/<stem>_<ts>/{stem.pl4, stem.lis, execution.log}
        (runner.py:127)          + cópia ao lado do .atp (_collect_outputs, 338–372)
                                             │
              find_result_files(atp_path) ◀──┘  (results_reader.py:385 — só olha ao lado do .atp)
                       │
                  read_pl4() ─▶ AtpResults{variables, time, data[var] = list[float], delta_t, n_steps}
                (results_reader.py:46)
                       │
      ┌────────────────┼───────────────────────────────────────────┐
      ▼                ▼                                           ▼
compute_transient_metrics   export_waveforms_csv / export_metrics_csv     waveform_widget.load_results
(transient_metrics.py:41)   (csv_export.py:18 / 37)                        (GUI)
      │
      ▼
TransientMetrics ─▶ format_transient_report (GUI, main_window.py:2298)
                 ─▶ generate_html_report → _render_html (report_export.py:57/102)
                 ─▶ ProjectAPI.export_csv (llm/project_api.py:364)

Ramo isolado (sem ponte com PL4 hoje):
TrtWaveform(time_s, voltage_kV, opening_time_s) ──analyze_trt(envelope)──▶ TrtAnalysisReport
(trt_analyzer.py:91)                 (372)   ▲                                  (167)
                                             └── trt_envelope_2param/4param (standards/iec62271.py:353/386)

Ramo isolado 2:
compute_trv_metrics(time, voltage_V, current_zero_time, rated_voltage_kv) ──▶ TrvMetrics
(transient_metrics.py:91) — sem consumidor fora de tests/test_analysis.py:67–81
```

**[fato]** Não há persistência de métricas por execução: `runs/<stem>_<ts>/` contém apenas PL4/LIS/log (`runner.py:374–394`). Um módulo de prognóstico que precise de **histórico** de estresse por evento não encontra nenhum formato de série temporal de métricas no repositório.

**[fato]** Dependências entre camadas (verificadas por grep): `app/analysis` importa `app/simulation`, `app/core`, `app/validation`; `app/postprocessor` **não** importa `app/analysis` nem `app/simulation`; `app/analysis` **não** importa `app/postprocessor`. O `ARCHITECTURE_ATP_STUDIO.txt` (linhas 13–25) documenta camadas 1–6 (CORE, VALIDATION, SIMULATION, ANALYSIS, LLM, GUI); `app/postprocessor` e `app/standards` são posteriores e não constam dessa lista.

---

## 3. Pontos de extensão concretos (incrementais, sem reescrita)

Ordenados do menos ao mais invasivo. Todos preservam assinaturas existentes.

### 3.1 Novo módulo `app/analysis/dielectric_stress.py` (zero mudanças nos existentes)

Consome diretamente:

- `AtpResults.get_variable(name)` (`results_reader.py:24`) e `AtpResults.delta_t` (21) para obter `(time, v)` e o passo de integração.
- `compute_transient_metrics` (`transient_metrics.py:41`) para `peak_value/min_value/rms/frequency/damping` por variável — reutilizar como "métricas globais" do perfil.
- `_find_zero_crossings` (204) e `_find_peaks` (218) para extrair sequência de extremos (base de uma contagem pico-vale / *rainflow* simplificado). São privados por convenção de nome, mas importáveis; **recomendação**: adicionar em `transient_metrics.py` dois aliases públicos `find_zero_crossings = _find_zero_crossings` e `find_peaks = _find_peaks` (2 linhas, aditivo), como já ocorre com o teste que importa `_compute_max_rrrv` diretamente (`tests/test_pp_v0_28_1.py:274`).
- `_compute_max_rrrv` (`trt_analyzer.py:299`) para RRRV por evento com filtro/janela consistentes com o analisador existente. Assinatura recebe `list[tuple[t_us, v_kV]]`, portanto basta montar os pares.
- `_moving_average_filter` (274) para condicionar `v(t)` antes de derivar.

Saída sugerida (nova dataclass frozen, no mesmo estilo de `TrtAnalysisReport`): `DielectricStressProfile{variable_name, n_events, events: tuple[SwitchingEvent,...], histogram_vpk: ..., histogram_dvdt: ..., trt_reports: tuple[TrtAnalysisReport,...], source, notes}` — cada `SwitchingEvent` embrulha um `TrtAnalysisReport` (167) sem alterá-lo.

### 3.2 Ponte PL4 → `TrtWaveform` (função nova, ao lado de `analyze_trt`)

`trt_waveform_from_results(results: AtpResults, var_name: str, opening_time_s: float, *, scale_to_kV: float = 1e-3, label="", phase="") -> TrtWaveform` — usa `results.time`, `results.get_variable(var_name)` e converte V→kV (a docstring de `trt_analyzer.py:55–66` prevê exatamente esta ponte). Não modifica `TrtWaveform` (91).

### 3.3 Segmentação por evento a partir das saídas do MODEL

- Instantes de abertura: transições 1→0 em `SWCMD_<inst>` (`vcb_model_emitter.py:223`).
- Instantes de reignição: incrementos de `REIGN_<inst>` (224).
- Alternativa quando o MODEL não é emitido (TYPE-13 simples): cruzamentos de zero da corrente `I_<suf4>` (TACS-90, 303–309) via `_find_zero_crossings`.

Cada instante vira um `opening_time_s` para `analyze_trt` ou `current_zero_time` para `compute_trv_metrics` (91). Isso resolve, sem tocar nos analisadores, a limitação de ambos aceitarem **um único** instante.

### 3.4 `TransientMetrics` — campos opcionais aditivos

Adicionar em `transient_metrics.py:13–26` campos com default (`max_abs_dvdt: Optional[float] = None`, `n_peaks: Optional[int] = None`, `n_zero_crossings: Optional[int] = None`) e preenchê-los em `compute_transient_metrics` (41–88) — retrocompatível porque a dataclass já usa defaults. Para chegarem ao CSV, acrescentar os nomes à lista de `export_metrics_csv` (`csv_export.py:55–58`); para chegarem ao HTML, acrescentar colunas em `_render_html` (`report_export.py:146–160` e 229–232).

### 3.5 Relatório HTML — seção opcional

`generate_html_report(project, pl4=None, messages=None)` (`report_export.py:57`): adicionar parâmetro `extra_sections: Optional[list[str]] = None` e concatenar antes do rodapé (`{metrics_section}` na linha 318). O módulo novo gera seu próprio fragmento HTML. Alternativa sem tocar em `report_export.py`: escrever um segundo relatório dedicado (padrão já usado por `app/postprocessor/report_html.py`).

### 3.6 `benchmarks.py` — benchmark de transitório sintético

Adicionar `TRANSIENT = "TRT"` a `StudyType` (48–54) e um `_bench_trt_synthetic()` que gere uma TRV analítica (por exemplo, `(1 − cos)` amortecida de circuito LC, sem PL4) e verifique `u_c_observed_kV`, `rrrv_max_kV_per_us` e `n_events` contra valores fechados; registrar em `_BENCHMARKS` (607–613). Os testes atuais já constroem ondas sintéticas assim (`tests/test_pp_trt_analyzer.py:250–292`, `tests/test_analysis.py:23–37`).

### 3.7 `find_result_files` — aceitar `run_dir`

`results_reader.py:385`: acrescentar kwarg opcional `run_dir: Optional[str] = None` que, se informado, procura primeiro em `run_dir`. Permite ligar `RunResult.run_dir` (`runner.py:285`) ao leitor sem alterar `AtpRunner`.

### 3.8 `SweepCase` — guardar `run_dir`

`app/llm/parametric.py:29–36`: adicionar `run_dir: str = ""` e atribuir `case.run_dir = run_result.run_dir` após a linha 152. Com isso, uma varredura em `Seed` (DATA do `vcb_reignition`, `.mod:56`) vira um Monte Carlo cujos PL4 podem ser agregados pelo módulo de estresse (distribuição de `reign_count`, V_pk, dV/dt por semente).

### 3.9 Exposição sem tocar a GUI

`app/plugins/registry.py:40` — `@register_study("dielectric_stress")` registra a função no menu Análise e em `app.postprocessor.studies` (docstring 42–52). Se preferir seguir o padrão `studies/`, cada módulo expõe `run(project, bus_id, *, cache=None, config=None, ...) -> <Result>` (`app/postprocessor/studies/__init__.py:15–24`; exemplo `studies/short_circuit.py:107–115`).

### 3.10 Proveniência

`app/postprocessor/audit_trail.py:compute_input_checksum(payload)` (SHA-256 estável de dataclasses/dicts) e `citation(standard, section, equation)` (catálogo `STANDARDS_CATALOG`, 67–80). **[fato]** `IEC 62271-100` **não** está no catálogo; `citation("IEC 62271-100", ...)` cai no *fallback* de nome direto (linhas 113–115), o que funciona, mas sem título completo. Incluir os parâmetros de filtro/janela (`rrrv_filter_window`, `rrrv_window_us`, `delta_t`) no payload do checksum, pois alteram contagens.

---

## 4. Grandezas já disponíveis relevantes a estresse dielétrico/térmico

### 4.1 Dielétrico (forma de onda)

| Grandeza | Onde | Observações |
|---|---|---|
| V_pk (máx e mín com sinal) e instantes | `TransientMetrics.peak_value/peak_time/min_value/min_time` (`transient_metrics.py:16–20`, 51–54) | por variável, toda a janela |
| V_pk absoluto pós-abertura e t_pico | `TrtAnalysisReport.u_c_observed_kV/t_to_peak_us` (181–182; cálculo 435–441) | por evento, requer `opening_time_s` |
| RRRV médio até o pico (kV/µs) | `TrvMetrics.rrrv_kv_per_us` (34; cálculo 131) | definição "média" |
| máx |dV/dt| filtrado (kV/µs) | `TrtAnalysisReport.rrrv_max_kV_per_us` (183; `_compute_max_rrrv` 299–360) | definição "instantânea"; filtro média móvel `window=5`; considera inclinação negativa |
| Margens vs envelope IEC 62271-100 e lista de violações `(t, v_obs, v_env)` | `TrtAnalysisReport.margin_uc/margin_rrrv/violations` (178–191; 449–465) | envelope é de **disjuntor**, não de isolamento de motor |
| Cruzamentos de zero (instantes interpolados) | `_find_zero_crossings` (204–215) | base para contagem de meios-ciclos |
| Índices de extremos locais de |v| | `_find_peaks` (218–224) | base para sequência pico-vale |
| Frequência dominante e razão de amortecimento | `TransientMetrics.frequency_hz/damping_ratio` (23–24; 72–86) | estimativas grosseiras (meio-período médio; decremento entre 1º e 3º picos) |
| RMS e média | `TransientMetrics.rms_value/mean_value` (21–22) | |
| Passo de integração e número de amostras | `AtpResults.delta_t/n_steps` (21–22) | necessário para validar resolução de dV/dt |
| Contador de reignições e comando de chave por instância de VCB | `REIGN_<inst>`, `SWCMD_<inst>` (`vcb_model_emitter.py:223–224`; `.mod:62–64`) | **[hipótese]** disponíveis no PL4 se o usuário solicitar saída MODELS/TACS |
| Parâmetros dielétricos do VCB (k_dielec V/µs, U0_dielec V, I_chop, di/dt crítico) | `.mod:47–56`; `vcb_model_emitter.py:103–112` | entradas de modelo, não medidas |
| Envelopes IEC (u_c, t_3, u_1, t_1, t_2, RRRV de referência) | `standards/iec62271.py:240–350` | |

### 4.2 Térmico (nenhum sinal de temperatura; apenas curvas-limite)

| Grandeza | Onde | Observações |
|---|---|---|
| Curva de dano térmico de motor `t(I) = K/(I/FLA)²`, `K = tE·(I_LR/FLA)²` | `app/postprocessor/tcc_damage.py:MotorThermalCurve` (450–600; `K_motor` 551, `thermal_time_at_current` 559) | single-time-constant; docstring declara limitação para motores MT grandes (518–521) |
| Fração do tempo térmico permitida na partida (0,70) e alerta `t_start > 30 s` | `motor_starting.py:98`, 538–541 | |
| Classe de isolamento (string `"F"`) em catálogo | `app/preprocessor/equipment_catalog.py:124` | metadado, sem modelo Arrhenius/IEC 60034 |
| Contribuição de curto do motor (IEC 60909 §6.5), sem cartão UM | `app/preprocessor/motor.py:1–70`, 357 | não há modelo dinâmico de motor para ATP |

**[fato]** Não existe no repositório nenhuma implementação de Weibull, Arrhenius, *rainflow*, *surge counting*, RUL ou prognóstico (grep por `rainflow|weibull|arrhenius|remaining useful|RUL|prognos` retornou apenas termos de isolação de cabos/catálogo). O único módulo de confiabilidade (`app/postprocessor/reliability.py`) é de índices IEEE 1366 (SAIFI/SAIDI/MTBF/MTTR).

---

## 5. Lacunas (o que NÃO existe)

1. **Série temporal de dV/dt**: só existe o máximo escalar (`_compute_max_rrrv`); não há função que devolva `dv/dt(t)` ou seu histograma.
2. **Contagem de surtos / pico-vale / rainflow**: inexistente. `_find_peaks` devolve índices, mas sem pareamento pico-vale, sem amplitude de ciclo, sem histograma.
3. **Segmentação multi-evento**: `compute_trv_metrics` (um `current_zero_time`) e `analyze_trt` (um `opening_time_s`) são mono-evento; reignições múltiplas (o cenário do trabalho A) exigem laço externo.
4. **Detecção automática do instante de corte** a partir da corrente do VCB: não há; `_find_zero_crossings` é privada e usada só para frequência.
5. **Leitura de `reign_count`/`switch_cmd` do PL4**: nenhum módulo consome as saídas do MODEL de reignição.
6. **Mapeamento variável PL4 → componente**: nomes são nós (`"v(NODE1-NODE2)"`, `results_reader.py:113–126`); não há tabela "esta variável é o terminal do motor M1 / a câmara do VCB DJ1".
7. **Unidades**: `AtpResults` não carrega unidade; `compute_trv_metrics` assume V (127), `TrtWaveform` assume kV (100–103). Não há conversão centralizada.
8. **Métricas de energia/integrais**: sem `∫v² dt`, `∫|dv/dt| dt`, tempo de subida 10–90 %, largura de pulso, número de oscilações acima de limiar.
9. **Domínio da frequência**: sem FFT/espectro (matplotlib e numpy estão em `requirements.txt`, mas a cadeia de análise não os usa).
10. **Critério de estresse para isolamento de motor** (por exemplo, IEC 60034-18-41/-42, IEC TS 60034-25 — [INSERIR CITAÇÃO]): só existe envelope de **disjuntor** (IEC 62271-100). Usar `margin_uc` como proxy de estresse do estator é uma **inferência de modelagem**, não um fato normativo.
11. **Persistência/histórico de métricas por execução** e **agregação Monte Carlo** (ver §3.8): `runs/` guarda só PL4/LIS/log; `SweepCase` não guarda PL4 nem métricas.
12. **Benchmark de transitório** em `benchmarks.py` e PL4 de referência no repositório (nenhum `.pl4` versionado; `.atp` de referência removido).
13. **`settling_time`**: declarado (`transient_metrics.py:25`) e nunca calculado.
14. **Parsing do `.lis`**: `read_lis` devolve texto bruto; extremos que o ATP imprime no `.lis` não são extraídos.
15. **Modelo dinâmico de motor MT no ATP** (cartão UM): não emitido (`motor.py:357`), então a tensão nos terminais do motor depende de modelagem manual no `.atp`.
16. **Snubber no pré-processador**: só validação de conexão `SNUB_CTRL` no validador (`validator_vcb.py:180–213`); grep por `snubber` em `app/preprocessor` vazio — não há emissor de snubber (ativo ou passivo).

---

## 6. Convenções que um novo módulo deve seguir

Extraídas do código lido (não de documentação prescritiva, exceto onde indicado):

1. **Dataclasses**: entradas e resultados como `@dataclass`; resultados **frozen** com tuplas em vez de listas (`TrtWaveform` 91, `TrtAnalysisReport` 167, `BenchmarkCase` 57). Validação em `__post_init__` com `ValueError` e mensagem contendo os valores (`trt_analyzer.py:131–150`, `tcc_damage.py:535–548`). `CONTRIBUTING_ATP_STUDIO.txt:95` — "preferir dataclasses para entidades de domínio".
2. **Unidades no nome do campo**: sufixos `_kV`, `_us`, `_kV_per_us`, `_s`, `_A`, `_ohm`, `_pu` (`trt_analyzer.py:181–191`, `iec62271.py:269–274`, `studies/short_circuit.py:68–84`). Na camada `app/analysis` antiga o padrão é minúsculo (`peak_trv_kv`, `rrrv_kv_per_us`); o padrão mais recente (`postprocessor`/`standards`) usa `kV` — seguir o recente.
3. **Sem numpy na cadeia de análise**: `transient_metrics.py`, `trt_analyzer.py`, `results_reader.py`, `csv_export.py` são Python puro com `list[float]`/`tuple`; `benchmarks.py:279–288` trata numpy como opcional. Se numpy for usado, fazer *import* guardado.
4. **Docstrings em PT-BR** com seções "Fluxo de uso", "Métricas calculadas", "Referências", "Limitações declaradas/documentadas" e citação normativa inline com seção (`trt_analyzer.py:1–74`, `tcc_damage.py:1–46`, `reliability.py:1–24`, `iec62271.py:1–79`). Marcação de versão nos comentários (`v0.28.1`, `v0.91.5`).
5. **Método `summary() -> str`** nos relatórios (`TrtAnalysisReport.summary` 206, `BenchmarkResult.summary` 98, `AtpResults.summary` 36) e campo `source: str` com a norma de origem (`TrtAnalysisReport.source` 199; envelopes 274/328).
6. **Parâmetros de algoritmo como kwargs *keyword-only* com defaults retrocompatíveis** (`analyze_trt` 372–378; `_compute_max_rrrv` 299–305; `AtpRunner.run` 127–134).
7. **Camadas**: `app/analysis` pode importar `app/simulation`, `app/core`, `app/validation`; nada em `app/analysis`/`app/postprocessor` importa GUI ou LLM (`ARCHITECTURE_ATP_STUDIO.txt:23–25`). Hoje `analysis` e `postprocessor` não se importam mutuamente; um módulo novo que precise de ambos deve escolher um lado e importar na direção `analysis → postprocessor` (postprocessor já importa só `standards`), evitando ciclo.
8. **Proveniência e citação**: `audit_trail.compute_input_checksum` e `citation(...)`; `hash_study_inputs` (`study_cache.py:310`) para cache por *bus*.
9. **Feature gates**: decorators `@requires_feature(Feature.X)` (`app/commercial/feature_gates.py:289`) existem e os testes forçam tier `"enterprise"` (`tests/conftest.py:28–42`). Não gatear métricas básicas.
10. **Testes**: `tests/test_pp_<modulo>.py` com ondas sintéticas em Python puro (`tests/test_analysis.py:23–37`; `tests/test_pp_trt_analyzer.py:250–292`), classes `Test*`, `pytest.approx`. O fixture `ref_project` pode fazer *skip* (`conftest.py:15–24`); não depender dele.
11. **Compatibilidade Python 3.11–3.13**: evitar f-strings aninhadas com as mesmas aspas (`report_export.py:205–206`); `from __future__ import annotations` em todos os módulos.
12. **Nomes ATP de 6 caracteres**: qualquer nome de nó/variável gerado deve respeitar `fmt_node` e o limite de 6 (`vcb_model_emitter.py:299–301, 320–332`).
13. **Idioma**: mensagens de usuário em PT-BR (`format_transient_report` 165–176; `runner.py:269–277`), identificadores em inglês.

---

## 7. Riscos técnicos

1. **Duas definições de RRRV coexistem**: média até o pico (`transient_metrics.py:131`) vs. máximo instantâneo filtrado (`trt_analyzer.py:299–360`). Um perfil de estresse deve escolher uma e registrá-la no `source`/docstring; misturar as duas em um mesmo histograma invalida comparações.
2. **Duas definições de u_c IEC**: `compute_trv_metrics` (149–157, sem `kaf`, `t3 = 4·uc`) vs. `iec62271.peak_voltage_uc_kV` (196–231). O campo `withstand_ok` de `TrvMetrics` não deve ser usado em conclusão científica.
3. **Ambiguidade de unidade V/kV** entre `AtpResults` (sem unidade), `compute_trv_metrics` (V) e `TrtWaveform` (kV): erro de 10³ silencioso é o modo de falha mais provável da ponte PL4 → TRT.
4. **Precisão float32 e derivada numérica**: dados PL4 são `float32` (`results_reader.py:184`); `dV/dt = Δv/Δt` com `Δt` de sub-µs amplifica quantização. O filtro de média móvel (`window=5`) e a janela `window_us` alteram contagens de surtos — precisam entrar no checksum de proveniência e em análise de sensibilidade.
5. **Resolução temporal vs. tempo de subida**: contagem de surtos de reignição depende de `delta_t` do ATP ser muito menor que o tempo de subida das frentes; o módulo deve validar `AtpResults.delta_t` e emitir aviso, pois nada na cadeia atual faz isso.
6. **Heurísticas do leitor PL4**: três estratégias com exceções silenciadas (`read_pl4` 66–90); em caso de *fallback* errado, os dados podem estar deslocados sem erro. A validação `data_size % record_bytes == 0` (170–173) protege só o formato GNUATP.
7. **Memória**: listas Python; um caso com 10⁶ passos × 50 variáveis gera 5·10⁷ objetos `float` (várias centenas de MB). O módulo de estresse deve processar variável por variável e não copiar `AtpResults`.
8. **Colisão de nomes TACS**: sufixo de 4 caracteres (`vcb_model_emitter.py:299–301`) — instâncias com mesmos 4 últimos caracteres colidem; afeta a segmentação por `I_<suf>`/`V_<suf>`.
9. **Monte Carlo do VCB**: `I_chop_rnd` é sorteado uma vez por execução (`.mod:83`); variabilidade exige varredura em `Seed` via `run_parametric_sweep` (chaves `"USE.param"`, resolvidas por `project.find_use`, `parametric.py:121`). Sem a extensão do §3.8 não há como recuperar os PL4 de cada semente.
10. **Envelope de disjuntor ≠ suportabilidade do estator**: `margin_uc`/`margin_rrrv` medem adequação do VCB (IEC 62271-100). Transportar isso para "estresse do isolamento do motor" é hipótese de modelagem que precisa de critério próprio ([INSERIR CITAÇÃO] IEC 60034-18-41/-42 ou equivalente) — o repositório não fornece.
11. **Ausência de PL4 e `.atp` de referência versionados**: qualquer teste de integração real ficará fora do CI público (`conftest.py:15–24` já faz *skip*); o módulo deve ser testável com ondas sintéticas.
12. **`settling_time` nunca calculado** e `_find_peaks` com desigualdade estrita (platôs/dupla amostra igual perdidos) — se reutilizados sem correção, subcontam extremos em sinais com saturação numérica.
13. **`find_result_files` ignora `runs/`**: reprocessar históricos exige apontar manualmente para `runs/<stem>_<ts>/<stem>.pl4`.
14. **`export_metrics_csv` com lista fixa de campos** (`csv_export.py:55–58`): campos novos são descartados silenciosamente (`extrasaction="ignore"`).
15. **Relatório HTML monolítico** (`_render_html`, 102–325): inserir seções por edição de f-string é frágil; preferir relatório separado ou o parâmetro `extra_sections` do §3.5.
