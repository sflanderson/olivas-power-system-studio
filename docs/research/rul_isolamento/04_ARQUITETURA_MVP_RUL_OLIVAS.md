# Etapa 3 (parte 2) — Arquitetura do MVP de RUL e *Asset Health Index* no Olivas Power System Studio

**Objetivo.** Documentar a arquitetura do MVP de prognóstico de vida útil remanescente (RUL) do isolamento estatórico de motores de indução de média tensão (2,3 a 13,8 kV) no Olivas Power System Studio, registrando **o que já foi implementado nesta sessão** (pacote `app/postprocessor/prognosis/`, 4 módulos mais a fachada, 3 052 linhas de código, 142 testes verdes) com rastreabilidade `arquivo:linha`, e **o que falta** para fechar uma release conforme os oito critérios de aceite do projeto.

**Diagnóstico.** O núcleo computacional existe e é puro (sem I/O, sem GUI, sem estado global) [REPO: `app/postprocessor/prognosis/__init__.py:8-11`]. Ele **não** está integrado a nenhuma das seis convenções obrigatórias do repositório: não há `Feature` comercial, não há ação de menu (violação em aberto da 7ª garantia), não há chaves em `STANDARDS_CATALOG`/`KNOWN_LIMITATIONS` globais, não há laudo HTML/PDF, não há strings i18n, não há entrada em `CHANGELOG.md`/`version.py`. Além disso, o repositório **não** possui, hoje, cadeia automática ATP → PL4 → perfil de estresse: o `AtpRunner` posiciona arquivos mas nenhum consumidor lê o PL4 a partir de `RunResult.run_dir` [REPO: `docs/research/rul_isolamento/anexos/repo/trt_transitorios_simulacao.md:29`, verificado contra `app/simulation/runner.py:285,338-372`]. Duas premissas do enunciado da tarefa são **corrigidas** aqui: (i) não existe motor de física em C++ neste projeto — a árvore não contém um único arquivo `.cpp`/`.cc`/`.hpp` [CÁLCULO PRÓPRIO: `find . -name "*.cpp" -o -name "*.cc" -o -name "*.hpp"` → vazio]; (ii) o `RRRV` do repositório é uma taxa **média** até o pico, não a derivada instantânea que o vetor de estresse exige [REPO: `app/analysis/transient_metrics.py:131`].

**Arquivos consultados.**

| Caminho | Uso nesta etapa |
|---|---|
| `/home/user/olivas-power-system-studio/app/postprocessor/prognosis/__init__.py` | API pública, `KNOWN_LIMITATIONS` (11 chaves) |
| `/home/user/olivas-power-system-studio/app/postprocessor/prognosis/stress_profile.py` | `StressEvent`, `StressProfile`, `extract_stress_events` |
| `/home/user/olivas-power-system-studio/app/postprocessor/prognosis/damage_models.py` | D1–D7, `CombinedDamageAccumulator`, ψ(D) |
| `/home/user/olivas-power-system-studio/app/postprocessor/prognosis/rul_estimator.py` | EKF, `RulPrediction`, `rul_from_damage` |
| `/home/user/olivas-power-system-studio/app/postprocessor/prognosis/health_index.py` | AHI 0–100, pesos, limiares, `explain()` |
| `/home/user/olivas-power-system-studio/tests/test_pp_prognosis_core.py` | 142 testes; mapeamento equação→teste |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/01_ETAPA1_monitoramento_degradacao_isolamento.md` | D1–D7 (§5.4), γ(t) (§6), T1 (§3.3) |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/02_ETAPA2_cruzamento_A_x_B.md` | eq. (5.1)–(5.3), monotonicidade perversa (§5.2) |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/anexos/repo/convencoes_auditoria_gui_docs.md` | pontos de extensão E1–E20, checklist 4.1–4.7, riscos R1–R15 |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/anexos/repo/trt_transitorios_simulacao.md` | cadeia ATP→PL4→métricas |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/anexos/repo/vcb_reignicao_snubber.md` | divergência linear × parabólica de RRDS |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/anexos/pesquisa/entrega_trabalho_computacional.md` | forma de entrega do trabalho computacional |
| `app/commercial/feature_gates.py`, `app/postprocessor/audit_trail.py`, `report_html.py`, `report_pdf.py`, `app/gui/main_window.py`, `app/gui/analysis_dialogs.py`, `app/core/version.py`, `app/simulation/runner.py`, `app/simulation/results_reader.py`, `app/analysis/transient_metrics.py`, `app/postprocessor/trt_analyzer.py`, `app/postprocessor/motor_starting.py`, `app/preprocessor/vcb_model_emitter.py`, `app/preprocessor/atp_templates/vcb_reignition.mod`, `requirements.txt`, `.github/workflows/test.yml`, `CHANGELOG.md`, `ROADMAP.md`, `ARCHITECTURE_ATP_STUDIO.txt` | pontos de integração, verificados por leitura direta |
| `.../scratchpad/papers_AB/txt/A_sepoc_snubber.txt`, `.../B_sepoc_load_shedding.txt` | Tabelas II e III de A; Tabela III de B |

**Arquivos afetados.** Criado nesta etapa: apenas este documento. Criados **antes** nesta sessão: os 5 arquivos do pacote `prognosis/` e `tests/test_pp_prognosis_core.py`. **Nenhum arquivo pré-existente do repositório foi modificado** — a §2 lista as alterações pendentes.

**Estratégia.** (1) Mapear a cadeia em camadas funcionais ISO 13374 e ancorar cada camada em um componente real, distinguindo o que roda em Python no repositório, o que é binário externo e o que ainda não existe. (2) Enumerar arquivo por arquivo o que foi criado, o que criar e o que alterar, com dependência explícita. (3) Fixar contratos de dados versionados entre camadas. (4) Provar, por `arquivo:linha` e por teste, que D1–D7 e (5.1)–(5.2) estão implementadas. (5) Definir o plano de validação com *fixtures* derivadas das Tabelas III de A e de B e métricas de prognóstico. (6) Roadmap por versão contra os 8 critérios de aceite. (7)–(8) Riscos e limitações declarados.

**Limitações.** Este documento descreve arquitetura e código verificado; **não** entrega integração GUI, laudo, i18n nem gate comercial — todos permanecem pendentes. Os parâmetros dos modelos de dano continuam **não calibrados** para mica-epóxi pré-formada de MT; nenhum número de RUL produzido pelo módulo é citável como valor fechado [REPO: `app/postprocessor/prognosis/damage_models.py:377-380`]. O texto normativo da ISO 13374-1 **não foi acessado** nesta sessão: as seis camadas são usadas como vocabulário de organização, não como declaração de conformidade.

**Próximo passo recomendado.** Abrir `docs/v4.1.0_BACKLOG_AUDIT.md` e executar o Sprint 1 da §6 (`Feature.RUL_PROGNOSIS` + `RulPrognosisDialog` + ação de menu + teste de *wiring*), que é o único caminho para retirar o módulo da condição de *backend* órfão proibida desde a v3.1.0 [REPO: `docs/research/rul_isolamento/anexos/repo/convencoes_auditoria_gui_docs.md:171`, citando `docs/SESSION_HANDOFF.md:37-43`].

---

## 1. Fluxo de dados do gêmeo digital em camadas funcionais

### 1.1 Vocabulário de camadas e ressalva de conformidade

As seis camadas funcionais **DA → DM → SD → HA → PA → AG** (aquisição de dados, manipulação de dados, detecção de estado, avaliação de saúde, avaliação prognóstica, geração de recomendação) são a decomposição canônica de sistemas de monitoramento de condição [NORMA: ISO 13374-1:2003, blocos funcionais — **texto normativo NÃO acessado nesta sessão**; ver §8, item L-N1]. Elas são usadas aqui como **vocabulário de organização da arquitetura**, e nenhuma alegação de conformidade formal é feita. A exigência de nível de confiança explícito na saída prognóstica, essa sim, foi verificada e está citada no código [NORMA: ISO 13381-1:2015, 3.3 e 3.9, citada em `app/postprocessor/prognosis/__init__.py:55-56` e em `rul_estimator.py:397-399`].

### 1.2 Onde entra o Python e onde entram os motores de física

**Correção de premissa — não há C++ neste projeto.** A árvore do repositório não contém nenhum arquivo `.cpp`, `.cc` ou `.hpp` [CÁLCULO PRÓPRIO: varredura `find`, resultado vazio]. Todo o código do produto é Python, e as dependências declaradas são `PySide6`, `anthropic`, `matplotlib`, `numpy`, `pytest`, `pydantic`, `PyYAML`, `openpyxl` [REPO: `requirements.txt:1-8`]. Portanto **nenhum motor de física será escrito em C++ neste projeto**, e a arquitetura do MVP não pressupõe compilação nativa.

Os motores de física dividem-se em dois regimes, com naturezas distintas:

| Regime | Motor | Natureza | Papel do Olivas |
|---|---|---|---|
| Transitório eletromagnético (µs–ms) | ATP/EMTP (executável externo, invocado por *subprocess*) | **Binário externo de terceiro**, caminho configurado pelo usuário; o repositório não o compila nem o distribui [REPO: `app/simulation/runner.py:27-36,167-179`] | Emite o `.atp`, invoca o executável, coleta `.pl4/.lis/.pch/.dbg` e grava `execution.log` [REPO: `app/simulation/runner.py:127-318,338-372,374-394`] |
| Regime permanente e quase-estático (s–h) | Fluxo de potência, curto-circuito, partida de motor, TCC, arc-flash, confiabilidade | **Python puro dentro do repositório** [REPO: `app/postprocessor/power_flow.py`, `short_circuit.py`, `motor_starting.py`, `reliability.py` — inventário em `app/postprocessor/`] | Executa integralmente; não há motor externo |

O `.atp` é o **artefato canônico** da camada de transitórios: a arquitetura declarada do produto é `.atp → parser → modelo semântico → GUI/LLM/validação → serializer → .atp` [REPO: `ARCHITECTURE_ATP_STUDIO.txt:12-14`]. Ou seja, o modelo semântico é reconstruível a partir do arquivo e o arquivo é reconstruível a partir do modelo — o `.atp` é a fonte única da verdade do caso de transitório, e o `hash` desse arquivo é o candidato natural a identificador de proveniência do perfil de estresse (§3.4).

**Ressalva de método sobre o Documento B.** O Documento B resolve fluxo de potência em OpenDSS com otimização NSGA-II/III e *surrogate* de regressão *ridge* [FATO: doc B, p. 1-3]. O OpenDSS **não** é integrado ao repositório: nenhum módulo de `app/` o invoca [CÁLCULO PRÓPRIO: varredura do inventário de `app/postprocessor/`, `app/simulation/`, `app/analysis/`]. O que o Olivas executa hoje em regime permanente é o seu **próprio** fluxo de potência em Python. Nenhuma integração com OpenDSS é assumida nesta arquitetura; a ligação com B entra pela taxa λ de manobras severas, que é **entrada** do módulo (§3.2), não resultado de uma simulação acoplada.

### 1.3 A cadeia, camada por camada

```
┌─ DA — Data Acquisition ────────────────────────────────────────────────────┐
│ (a) SIMULAÇÃO: .atp (fonte única da verdade) ──▶ ATP/EMTP externo          │
│     [REPO: app/simulation/runner.py:127-318]  ──▶ .pl4 / .lis / .pch       │
│ (b) CAMPO (não implementado): oscilografia de manobra, sensor de DP,       │
│     RTD/fibra de ponto quente, ensaios IR/PI e tan δ  ──▶ CSV/COMTRADE     │
└────────────────────────────────────────────────────────────────────────────┘
                                   │  (fronteira de I/O)
┌─ DM — Data Manipulation ──────────┴────────────────────────────────────────┐
│ Leitura PL4 → AtpResults(variables, time, data, delta_t, n_steps)          │
│   [REPO: app/simulation/results_reader.py:15-43,46-96]                     │
│ Localização de resultados: find_result_files  [ibid.:385-405]              │
│ Métricas herdadas: TrvMetrics / analyze_trt                                │
│   [REPO: app/analysis/transient_metrics.py:29-38,91-159;                   │
│          app/postprocessor/trt_analyzer.py:92,168,299,372]                 │
│ ▶ EXTRAÇÃO DO VETOR DE ESTRESSE (implementado):                            │
│   extract_stress_events(time_s, voltage_kV, threshold_kV, …)               │
│   [REPO: app/postprocessor/prognosis/stress_profile.py:405-672]            │
│   saída: StressProfile{ s_{m,j} = [V_pk, T1, dv/dt, E, n_r, θ] }           │
└────────────────────────────────────────────────────────────────────────────┘
┌─ SD — State Detection ────────────────────────────────────────────────────┐
│ Estatísticas e triagem do perfil: peak_max_kV, dvdt_max_kV_per_us,         │
│   T1_min_us, energy_total_J, theta_max_C, events_above(threshold),         │
│   equivalent_events(n)  [REPO: stress_profile.py:269-356]                  │
│ Avisos de qualidade de amostragem (passo grosseiro, frente subamostrada,   │
│   Nyquist)  [REPO: stress_profile.py:519-527,626-640]                      │
│ Margem de coordenação γ(t) = U_w(t)/U_s  [REPO: damage_models.py:864-881]  │
└────────────────────────────────────────────────────────────────────────────┘
┌─ HA — Health Assessment ──────────────────────────────────────────────────┐
│ CombinedDamageAccumulator: D = D_th + D_el + D_sin  (5.1)-(5.2)           │
│   [REPO: damage_models.py:699-1060]                                       │
│ AssetHealthIndex 0-100 + explain() + traffic_light                        │
│   [REPO: health_index.py:256-578]                                         │
└────────────────────────────────────────────────────────────────────────────┘
┌─ PA — Prognostic Assessment ──────────────────────────────────────────────┐
│ Caminho determinístico: rul_from_damage(D, dD/dt);                        │
│   rul_operations(); rul_years(λ_m)                                        │
│   [REPO: rul_estimator.py:470-494; damage_models.py:998-1037]             │
│ Caminho estocástico: EkfRulEstimator → RulPrediction (RUL + IC)           │
│   [REPO: rul_estimator.py:166-467]                                        │
└────────────────────────────────────────────────────────────────────────────┘
┌─ AG — Advisory Generation ─────────────────── (NÃO IMPLEMENTADO) ─────────┐
│ make_audit_header + citation + format_limitations_html                    │
│   [REPO: audit_trail.py:294-327,90-127,408-420]                           │
│ report_rul_html.py / report_rul_pdf.py  (a criar)                         │
│ RulPrognosisDialog + ação no menu Análise  (a criar — 7ª garantia)        │
└────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 O que existe, o que é externo e o que falta — por camada

| Camada | Componente real | Estado | Evidência |
|---|---|---|---|
| DA (transitório) | ATP/EMTP externo via `AtpRunner.run` | **Externo, existente**; sucesso = `returncode == 0` e ausência de `/ERROR/` no *stdout* | [REPO: `app/simulation/runner.py:127-318`, critério em `:263-265` conforme `anexos/repo/trt_transitorios_simulacao.md:14`] |
| DA (campo) | Oscilografia, DP, RTD, IR/PI, tan δ | **Não implementado**; entradas do usuário | [REPO: `prognosis/__init__.py:200-219` — `rul_measurement_point`, `rul_thermal_state_not_derived`] |
| DM (leitura) | `read_pl4` → `AtpResults` | **Existente**; sem metadado de unidade (V × kV) e com exceções silenciadas | [REPO: `app/simulation/results_reader.py:46-96`; `anexos/repo/trt_transitorios_simulacao.md:38,40`] |
| DM (ponte PL4 → perfil) | adaptador `AtpResults` → `extract_stress_events` | **Falta**; nenhum consumidor lê PL4 a partir de `RunResult.run_dir` | [REPO: `anexos/repo/trt_transitorios_simulacao.md:14`] |
| DM (extração) | `extract_stress_events` | **Implementado**, 142 testes verdes | [REPO: `stress_profile.py:405`; teste `tests/test_pp_prognosis_core.py:170-311`] |
| SD | estatísticas de `StressProfile`, `warnings`, γ(t) | **Implementado** | [REPO: `stress_profile.py:269-356`; `damage_models.py:845-881`] |
| HA | `CombinedDamageAccumulator`, `AssetHealthIndex` | **Implementado** | [REPO: `damage_models.py:699`; `health_index.py:256`] |
| PA | `EkfRulEstimator`, `rul_from_damage` | **Implementado**; IC por método delta, não Weibull/Monte Carlo | [REPO: `rul_estimator.py:383-467`; limitação `rul_interval_delta_method` em `__init__.py:227-233`] |
| AG | laudo, diálogo, menu, i18n, gate | **Falta integralmente** | [REPO: `prognosis/__init__.py:70-74`] |

### 1.5 Correção do encadeamento de métricas herdadas

O módulo `transient_metrics` calcula `rrrv = peak_trv_kv / peak_trv_time_us`, isto é, a **taxa média** do zero de corrente até o pico [REPO: `app/analysis/transient_metrics.py:131`]. O `trt_analyzer` calcula, esse sim, uma inclinação máxima filtrada por média móvel em janela configurável [REPO: `app/postprocessor/trt_analyzer.py:274-360,372-446`]. Nenhum dos dois expõe **contagem de excursões** acima de um limiar, que é o que o acumulador de Miner exige.

Isso justifica arquiteturalmente a decisão já tomada no código: `extract_stress_events` mede o tempo de frente pela definição normativa $T_1 = 1{,}67\,(t_{90\%} - t_{30\%})$ [NORMA: IEC 60034-15:2009, §2.4, implementado em `stress_profile.py:553-584` com os fatores em `:77-81`], e a razão $V_{pk}/\mathrm{RRRV}$ é exposta **apenas** como `StressEvent.front_time_from_rrrv_us`, explicitamente rotulada como indicativa [REPO: `stress_profile.py:203-213`; fundamento em Etapa 1 §3.3]. A razão física: o pico é atingido após a escalada por reignições sucessivas e a maior RRRV pode pertencer a outra fase, de modo que $V_{pk}/\mathrm{RRRV}$ não é um tempo de frente [FATO: Etapa 1, §3.3].

---

## 2. Inventário de arquivos: criado, a criar, a alterar

Legenda de ação: **[C]** criado nesta sessão; **[N]** a criar; **[A]** a alterar (mudança mínima, retrocompatível).

### 2.1 Pacote de prognóstico — o que já existe

| Arquivo | Ação | Símbolo | Responsabilidade | Dependência |
|---|---|---|---|---|
| `app/postprocessor/prognosis/__init__.py` | [C] | `__all__` (`:120-159`), `KNOWN_LIMITATIONS` (`:168-248`, 11 chaves com prefixo `rul_`) | Fachada da API pública e catálogo local de limitações no padrão de `audit_trail.py:338-382` | `damage_models`, `health_index`, `rul_estimator`, `stress_profile` |
| `app/postprocessor/prognosis/stress_profile.py` | [C] | `StressEvent` (`:111`), `StressProfile` (`:228`), `extract_stress_events` (`:405`), `IEC_60034_15_T1_FACTOR` (`:77`) | Vetor de estresse $s_{m,j}$ por reignição; extração de excursões, $T_1$ normativo, dv/dt de frente, energia, agrupamento em manobras, avisos de amostragem | stdlib (`math`, `dataclasses`) — **sem numpy** |
| `app/postprocessor/prognosis/damage_models.py` | [C] | D1–D6 (`:122,158,188,216,261,294,324`), `DamageModelParams` (`:374`), `supportable_events`/`event_damage` (`:531,616`), `psi_linear` (`:647`), `ThermalInterval` (`:680`), `CombinedDamageAccumulator` (`:699`) | Leis de vida, D7 nos dois modos de normalização e acumulador (5.1)–(5.2) com γ(t), ψ(D), RUL em manobras e anos | `stress_profile`; stdlib |
| `app/postprocessor/prognosis/rul_estimator.py` | [C] | `RulPrediction` (`:110`), `EkfRulEstimator` (`:166`), `rul_from_damage` (`:470`) | EKF de 3 estados $[I,\alpha,\beta]$ sobre $I(t)=\alpha e^{\beta t}$; IC por método delta com quantil de `statistics.NormalDist`; caminho determinístico | `numpy` (já em `requirements.txt:4`), stdlib |
| `app/postprocessor/prognosis/health_index.py` | [C] | `AssetHealthIndex` (`:256`), `HealthIndexWeights` (`:88`), `HealthIndexThresholds` (`:149`), `HealthContribution` (`:223`), `DEFAULT_BANDS` (`:79`) | AHI 0–100 com renormalização sobre componentes disponíveis e decomposição explicável somando 100 % | stdlib |
| `tests/test_pp_prognosis_core.py` | [C] | 11 classes de teste, 142 casos | Cobertura do núcleo, incluindo *guards* de arquitetura (`:1157` não importa GUI/plot; `:1174` não faz I/O) | `pytest` |

**Verificação de execução** [CÁLCULO PRÓPRIO]: `python -m pytest tests/test_pp_prognosis_core.py -q` → `142 passed in 0.34s`.

### 2.2 Integrações pendentes com as convenções do repositório

| Arquivo | Ação | Símbolo | Responsabilidade | Dependência |
|---|---|---|---|---|
| `app/commercial/feature_gates.py` | [A] | `class Feature` (`:67-80`) e `FEATURE_TIER_MAP` (`:84-96`) | Acrescentar `RUL_PROGNOSIS = "rul_prognosis"` mapeado a `"commercial"` (alinhado aos três Monte Carlos, `:88-90`); decorar o ponto de entrada com `@requires_feature` | Nenhuma; tier ≥ `demo` é obrigatório sob o teste de hierarquia [REPO: `anexos/repo/convencoes_auditoria_gui_docs.md:E1`] |
| `app/gui/rul_prognosis_dialog.py` | [N] | `RulPrognosisDialog(QDialog)` | Diálogo modal com `QFormLayout`, *spin boxes* com `setRange/setValue/setSuffix`, rótulos citando norma, `QPlainTextEdit` de resultado, captura separada de `LicenseRequiredError` | `PySide6`; padrão de `app/gui/analysis_dialogs.py:78-284,661-797` |
| `app/gui/main_window.py` | [A] | bloco `analysis_menu` (`:442`), padrão `act_reliability` (`:529-533`), handler `_on_show_reliability` (`:3070`) | Ação `act_rul = analysis_menu.addAction("<emoji> Prognóstico de isolamento / RUL …", self._on_show_rul_prognosis)` + `setStatusTip` + handler `_on_show_rul_prognosis(self, *_qt_args)` com import *lazy* — **7ª garantia** | `rul_prognosis_dialog` |
| `app/gui/analysis_dialogs.py` | [A] (opcional) | `run_pipeline_report_export` (`:997`) | Segunda porta de entrada para exportação do laudo de RUL, coletando engenheiro/CREA/ART/notas (lacuna L3 do mapa de convenções) | `report_rul_html`, `report_rul_pdf` |
| `app/postprocessor/audit_trail.py` | [A] | `STANDARDS_CATALOG` (`:73-87`, hoje 13 normas), `KNOWN_LIMITATIONS` (`:338-382`, hoje 7 chaves) | Acrescentar as normas efetivamente citadas no código (IEC 60034-15:2009, IEC 60034-18-41:2014, IEC 60034-27-2/-3/-4, IEC 60071-1:2019, ABNT NBR 17094-3:2018, NEMA MG 1 Parte 31, ISO 13381-1:2015) e as 11 chaves `rul_*` já escritas em `prognosis/__init__.py:168-248` | Nenhuma; `format_limitations_html` ignora chaves desconhecidas [REPO: `audit_trail.py:408-420`] |
| `app/postprocessor/report_rul_html.py` | [N] | `generate_rul_html_report`, `save_rul_html_report` | Laudo HTML no padrão `report_html.py`: bloco 1 = `make_audit_header(...).to_html()`, `citation()` por valor, penúltimo bloco = `format_limitations_html` | `audit_trail`, `prognosis`; **não** estender `generate_html_report` (`report_html.py:602`), que é tipado a `BusPipelineReport` |
| `app/postprocessor/report_rul_pdf.py` | [N] | `save_rul_pdf_report` | Laudo PDF espelhando `report_pdf.py:1054-1173`; reutilizar `_build_audit_cover_page` (`:127`) exige `report_kind` por *kwarg* opcional (hoje derivado de `report.bus_id`, `:171`) | `matplotlib` (já em `requirements.txt:3`) |
| `app/i18n/translations/en.json` e `es.json` | [A] | pares PT→EN e PT→ES | Toda string de UI nova (rótulo de menu, título do diálogo, rótulos de campo, botões, faixas do semáforo); paridade exata obrigatória | Hoje 133 chaves em cada arquivo [CÁLCULO PRÓPRIO: `json.load`] |
| `app/core/version.py` | [A] | `VERSION_TUPLE` (`:1959`), `PRE_RELEASE` (`:1960`), docstring de histórico | Bump `4.0.0-beta → 4.1.0-beta` com entrada de histórico; **manter** o sufixo `beta` (o teste de *readiness* exige prefixo `4.` e sufixo `alpha`/`beta`) | Testes de *readiness*/*milestone* |
| `CHANGELOG.md` | [A] | seção `## [4.1.0-beta]` (`:7-25` é o padrão) e "Standards cobertos (cumulativo)" (`:181-193`) | `### Added`/`### Changed` com contagem de testes; acrescentar as normas novas à lista cumulativa | `version.py` |
| `tests/test_pp_v4_1_0_rul_prognosis.py` | [N] | `TestGating`, `TestAuditIntegration`, `TestDialog`, `test_main_window_wires_rul_action` | Gate bloqueado em `educational` e liberado em `enterprise`; header e limitações presentes no HTML/PDF; diálogo sem `dlg.exec()`; *wiring* de menu por `inspect.getsource` | `tests/test_pp_prognosis_core.py` (já cobre o núcleo) |
| `.github/workflows/test.yml` | [A] | lista explícita do *job* `test` (`:66-78`) | Acrescentar `tests/test_pp_prognosis_core.py` e `tests/test_pp_v4_1_0_rul_prognosis.py` + `--cov=app.postprocessor.prognosis` | Nenhuma |
| `app/preprocessor/atp_templates/vcb_reignition.mod` | [A] | bloco `DATA` (`:47-56`), recuperação dielétrica (`:115`) | Acrescentar `rrds_a`, `rrds_b` e um seletor de lei; manter `k_dielec = 17,0 V/µs` linear como **default atual** e a lei parabólica como **opção** | `vcb_model_emitter` |
| `app/preprocessor/vcb_model_emitter.py` | [A] | `VCB_REIGNITION_PROPS` (`:74-83`), `VCB3_REIGNITION_PROPS` (`:86-95`), `VCB_REIGNITION_DEFAULTS` (`:103-112`) | Acrescentar as propriedades **ao final** dos índices (10+ e 14+) para não deslocar o *layout* existente; nenhum default atual muda | Teste de integridade de mapeamento de propriedades |
| `app/analysis/transient_metrics.py` | [A] | `TrvMetrics` (`:29-38`), `compute_trv_metrics` (`:91-159`) | Acrescentar campos `Optional[...] = None`: `max_dvdt_kv_per_us` (derivada instantânea, distinta do `rrrv_kv_per_us` médio de `:131`) e `n_excursions_above` | Nenhuma; campos opcionais preservam chamadores |
| `app/postprocessor/trt_analyzer.py` | [A] | `TrtAnalysisReport` (`:168-204`), `analyze_trt` (`:372`) | Expor a contagem de excursões acima de um limiar configurável, ao lado de `rrrv_max_kV_per_us` (`:183`) — insumo direto de `n_reignitions` | `_compute_max_rrrv` (`:299`) já percorre a janela |
| `app/postprocessor/motor_starting.py` | [A] | `MotorStartingReport` (`:260-329`) | Expor `i2t_A2s` e `t_acc_s` como campos opcionais: `starting_time_s` já existe (`:294`, tempo até 95 % da rotação nominal, calculado em `:410`), mas **I²t não é calculado** — hoje o módulo apenas menciona a curva I²t em texto de *rationale* (`:540`) | `estimate_starting_time_s` (`:410`) |

### 2.3 Ressalva sobre a alteração do modelo de VCB

O `.mod` do repositório implementa recuperação dielétrica **linear**: `U_dielec_t := U0_dielec + k_dielec*(t - t_contact)*1e6`, com `k_dielec` default 17,0 V/µs [REPO: `app/preprocessor/atp_templates/vcb_reignition.mod:115,52`]. O Documento A usa lei **parabólica** de RRDS, $V_{wth}(t) = A\,t + B\,t^2$, com $A = 0{,}801$ kV·ms⁻¹ e $B = 1{,}226$ kV·ms⁻² [FATO: doc A, Tabela II, p. 3]. As duas físicas são incompatíveis entre si, e o repositório já contém, em outro artefato, a mesma forma quadrática usada por A: o validador exige parâmetro `RRDS*` e o arquivo de referência implementa `VWITHSTANDKV = RRDS_A·t_ms + RRDS_B·t_ms²` com `RRDS_A = 0,801` e `RRDS_B = 1,226` [REPO: `anexos/repo/vcb_reignicao_snubber.md:38,92,124,126`].

A recomendação arquitetural é **parametrizar a lei, não substituí-la**: acrescentar `rrds_a`/`rrds_b` e um seletor `dielectric_law ∈ {linear, quadratic}` cujo valor default permaneça `linear`, preservando bit a bit o comportamento atual dos casos existentes [INFERÊNCIA]. Sem isso, qualquer *fixture* de reprodução do Documento A produziria um perfil de estresse inconsistente com o artigo, e o risco R2 do mapa de convenções (duas físicas de disjuntor sem documento que as reconcilie) permaneceria aberto [REPO: `anexos/repo/vcb_reignicao_snubber.md:271`].

---

## 3. Contratos de dados entre camadas

### 3.1 Princípios

1. **Versionamento explícito.** Todo documento persistido carrega `schema_version` (SemVer). Mudança compatível (campo novo opcional) incrementa o *minor*; mudança que remove ou reinterpreta campo incrementa o *major*.
2. **Unidades no nome do campo.** O `AtpResults` do repositório não carrega metadado de unidade — volts × kV, A × kA são indistinguíveis [REPO: `anexos/repo/trt_transitorios_simulacao.md:40`]. O contrato do módulo de RUL corrige isso: todo campo numérico traz o sufixo de unidade, exatamente como já ocorre nos *dataclasses* (`V_pk_kV`, `T1_us`, `dvdt_kV_per_us`, `energy_J`, `theta_C`) [REPO: `stress_profile.py:146-155`].
3. **Rótulo de proveniência.** `StressEvent.source` e `StressProfile.label` já existem para isso [REPO: `stress_profile.py:156,248`].
4. **Auditoria antes da compressão.** O *hash* de proveniência é calculado sobre um **resumo determinístico** (parâmetros do caso + estatísticas por evento + SHA-256 do arquivo `.pl4`), nunca sobre a série temporal bruta — `_to_jsonable` faz `repr` de objetos desconhecidos, o que tornaria o *hash* não determinístico entre versões do numpy [REPO: `audit_trail.py:164-191`; risco R6 em `anexos/repo/convencoes_auditoria_gui_docs.md`].

### 3.2 Contrato C1 — perfil de estresse (`rul_stress_profile.v1.json`)

Fronteira **DM → SD/HA**. Serialização direta de `StressProfile` [REPO: `stress_profile.py:228-382`].

```json
{
  "schema_version": "1.0.0",
  "kind": "rul_stress_profile",
  "label": "M-4160-01 / manobra de abertura sob partida",
  "provenance": {
    "source": "ATP/EMTP",
    "atp_file_sha256": "<64 hex>",
    "pl4_file_sha256": "<64 hex>",
    "variable_name": "v(MOT_A)",
    "measurement_point": "terminal_do_motor | disjuntor",
    "generated_at_iso": "2026-09-03T00:00:00"
  },
  "sampling": { "step_s": 1.0e-6, "n_samples": 45000 },
  "detection": {
    "threshold_kV": 10.0,
    "group_window_s": 1.0e-3,
    "min_samples_per_front": 5,
    "surge_impedance_ohm": 40.0
  },
  "events": [
    { "V_pk_kV": 41.44, "T1_us": 2.759, "dvdt_kV_per_us": 15.05,
      "energy_J": 0.0, "n_reignitions": 3, "theta_C": 120.0,
      "timestamp_s": 0.0248, "source": "ATP/EMTP" }
  ],
  "statistics": {
    "n_events": 1, "n_operations": 1, "peak_max_kV": 41.44,
    "peak_mean_kV": 41.44, "dvdt_max_kV_per_us": 15.05,
    "T1_min_us": 2.759, "energy_total_J": 0.0, "theta_max_C": 120.0
  },
  "warnings": [
    "Passo de amostragem Δt = 1 µs ≥ 1 µs: … dv/dt são LIMITES INFERIORES …"
  ]
}
```

Regras do contrato: `statistics` é **derivável** de `events` e existe para auditoria (o laudo cita o valor sem recomputar); `warnings` é **obrigatório** e nunca omitido quando não vazio — é o registro de que a frente pode não ter sido resolvida [REPO: `stress_profile.py:245-263,519-527,626-640`]. `measurement_point` é obrigatório porque TRV no disjuntor não é a tensão nos terminais do motor [REPO: limitação `rul_measurement_point`, `prognosis/__init__.py:200-206`].

### 3.3 Contrato C2 — caso de prognóstico (`rul_case.v1.json`)

Fronteira **usuário/GUI → HA/PA**. Reúne o que **não** é extraível da forma de onda.

| Campo | Unidade | Origem obrigatória | Evidência |
|---|---|---|---|
| `asset_id` | — | usuário | — |
| `U_n_kV`, `U_s_kV`, `U_w0_kV` | kV | placa / coordenação de isolamento | γ = U_w/U_s [REPO: `damage_models.py:741,864-881`] |
| `params.{n_voltage, m_front, V_th_kV, V_ref_kV, N0_events, t_f0_us, HIC_C, theta0_C, a_first_coil, L0_thermal_h, B_thermal_K}` | ver `DamageModelParams` | **NÃO CALIBRADOS** — todos os defaults declaram origem em comentário | [REPO: `damage_models.py:374-432`] |
| `normalization` | `threshold_shift` \| `residual_withstand` | decisão do analista | [REPO: `damage_models.py:528`] |
| `thermal_profile[]` | `(theta_C, duration_h, label)` | RTD/fibra ou estimativa térmica | [REPO: `damage_models.py:680-697`] |
| `lambda_m_per_year` | manobras severas/ano | **entrada do usuário**; é o elo com o Documento B | [FATO: Etapa 2, §2 — B governa λ, A governa a severidade] |
| `measured_indicators.{ir_Mohm, pi, tan_delta, pd_qm_mV}` | MΩ, —, —, mV | ensaios; todos opcionais | [REPO: `health_index.py:295-298`] |
| `psi_min`, `state_dependent_threshold`, `synergy_fn_id` | — | decisão do analista | [REPO: `damage_models.py:742-746`] |

O caso **deve** carregar `calibration_warnings` materializadas no momento da execução, produzidas por `DamageModelParams.calibration_warnings()` [REPO: `damage_models.py:484-526`], para que o laudo não possa ser emitido sem elas.

### 3.4 Contrato C3 — resultado (`rul_result.v1.json`) e C4 — série de indicador (`rul_indicator_series.v1.csv`)

C3, fronteira **PA → AG**, é a serialização de `CombinedDamageAccumulator.summary()` mais `RulPrediction.summary()` mais `AssetHealthIndex.explain()`:

```json
{
  "schema_version": "1.0.0", "kind": "rul_result",
  "damage": { "D_el": 0.0, "D_th": 0.0, "D_sin": 0.0, "D_total": 0.0,
              "remaining_fraction": 1.0, "is_lower_bound": true,
              "n_events": 0, "n_operations": 0, "n_events_below_threshold": 0,
              "thermal_hours": 0.0, "normalization": "threshold_shift" },
  "coordination": { "psi": 1.0, "U_w_kV": null, "gamma": null },
  "rul": { "operations": null, "years": null,
           "ekf": { "rul": null, "rul_lower": null, "rul_upper": null,
                    "sigma": null, "confidence": 0.95, "alpha": null,
                    "beta": null, "n_updates": 0 } },
  "health_index": { "index": 100.0, "classification": "BOM",
                    "traffic_light": "verde",
                    "contributions": [ { "name": "damage_electrical",
                                         "available": true, "score": 1.0,
                                         "normalized_weight": 0.375,
                                         "contribution_pct": 37.5,
                                         "basis": "D7 / eq. (5.2) — Etapa 1 §5.4; Etapa 2 §5.2" } ] },
  "audit": { "limitations_applied": ["rul_params_not_calibrated", "rul_synergy_lower_bound"],
             "calibration_warnings": ["…"], "input_checksum_sha256": "<64 hex>" }
}
```

O campo `is_lower_bound` é **estrutural**: quando `synergy_fn` é `None`, `D` é cota inferior de dano e cota superior de RUL, e o resumo textual já o declara [REPO: `damage_models.py:819-822,1053-1057`]. `contribution_pct` soma 100 % sobre os componentes disponíveis, e componentes indisponíveis aparecem com `available=false` em vez de serem omitidos — a ausência de dado é visível, não silenciosa [REPO: `health_index.py:501-547`; teste `tests/test_pp_prognosis_core.py:990`].

C4 é a série que alimenta o EKF, em CSV com cabeçalho versionado (`# schema_version=1.0.0; kind=rul_indicator_series`) e colunas `t_h,indicator,unit,source`. O estimador exige tempo **não decrescente** e ergue `ValueError` caso contrário [REPO: `rul_estimator.py:314-317`; teste `:882`].

### 3.5 Como o vetor de estresse é auditado

Três garantias, todas já suportadas pelo código:

1. **Validação de entrada na fronteira.** `StressEvent.__post_init__` rejeita pico nulo, $T_1 \le 0$, dv/dt negativo, energia negativa, $n_r < 1$ e temperatura $\le -273{,}15$ °C [REPO: `stress_profile.py:158-191`; testes `:113-140`]. Nenhum evento fisicamente impossível entra no acumulador.
2. **Rastro de qualidade de amostragem.** Os três avisos (passo grosseiro, frente subamostrada, violação de Nyquist com $f \approx 0{,}35/t_r$) viajam com o perfil e devem ser renderizados no laudo [REPO: `stress_profile.py:102,519-527,585-590,626-640`].
3. **Limitações no laudo.** As 11 chaves `rul_*` são carregadas por `format_limitations_html` uma vez copiadas para o catálogo global, sem risco de colisão graças ao prefixo de *namespace* [REPO: `prognosis/__init__.py:164-167`; `audit_trail.py:408-420`; teste `tests/test_pp_prognosis_core.py:1137`].

---

## 4. Realização das equações D1–D7 e (5.1)–(5.2) no código

### 4.1 Tabela de rastreabilidade equação → função → `arquivo:linha` → teste

| Eq. | Forma | Função | `arquivo:linha` | Teste (`tests/test_pp_prognosis_core.py`) |
|---|---|---|---|---|
| **D1** | $L(V) = k\,V^{-n}$ | `inverse_power_law_life(V, k, n)` | `damage_models.py:122` | `:360` valor de mão; `:364` monotonicidade; `:370,374` validação |
| **D2** | $L = C\,(V - V_{th})^{-m}$, vida infinita abaixo do limiar | `ipl_with_threshold(V, V_th, C, m)` | `damage_models.py:158` | `:380` abaixo do limiar → `inf`; `:384` no limiar → `inf`; `:387` acima |
| **D3** | $(t_f/t_{f0})^{m}$ | `front_time_correction(t_f, t_f0, m)` | `damage_models.py:188` | `:397` valor de mão; `:401` neutro com $m=0$ |
| **D4** | $D = \sum_i n_i/N_i$, falha em $D=1$ | `miner_damage(events)` | `damage_models.py:216` | `:410` soma de razões; `:414` $N_i=\infty$ contribui zero; `:417` vazio → 0 |
| **D5** | $L(V,\theta)=t_0(V/V_0)^{-n}\exp(-B\,c_T)$, $c_T = 1/T_0 - 1/T$ | `simoni_life(...)` | `damage_models.py:324` | `:470` vida cai com tensão e com temperatura; `:489` validação |
| **D6a** | $L(\theta)=L_0\exp[-B(1/T_0 - 1/T)]$ | `arrhenius_life(...)` | `damage_models.py:261` | `:452` **convenção de sinal**: vida decresce com o calor; `:459` valor de mão |
| **D6b** | $L(\theta)=L_0\,2^{(\theta_0-\theta)/\mathrm{HIC}}$ | `montsinger_life(...)` | `damage_models.py:294` | `:434` $\theta = \theta_0 + \mathrm{HIC} \Rightarrow L_0/2$; `:439` neutro na referência |
| **D7 (N_j)** | $N_j = N_0\left[\frac{a V_{pk}-V_{th}}{V_{ref}-V_{th}}\right]^{-n}\left(\frac{t_f}{t_{f0}}\right)^{m} 2^{(\theta_0-\theta_j)/\mathrm{HIC}}$ | `supportable_events(...)` | `damage_models.py:531` | `:518` valor-ouro do exemplo da Etapa 1; `:585,591` modos e validação |
| **D7 (1/N_j)** | $1/N_j$, exatamente 0 se $aV_{pk}\le V_{th}$ | `event_damage(...)` | `damage_models.py:616` | `:538` dano exatamente zero; `:545` acima do limiar ainda danifica; `:531` monotonicidade em tensão |
| **D7 (térmico)** | fator térmico multiplica o **dano**, não a capacidade | `supportable_events` (`thermal_expo`) | `damage_models.py:609-614` | `:550` fator multiplica o dano; `:563` $+20$ K com HIC = 10 K → dano $\times\,4{,}0$ |
| **(5.1)** | $D = D^{th} + D^{el} + D_{sin}$ | `CombinedDamageAccumulator.D_total` | `damage_models.py:808-812` | `:622` total é a soma das parcelas; `:651` `synergy_fn` é usada |
| **(5.1) — $D^{th}$** | $\int \mathrm{d}\tau/L(\theta(\tau))$ | `add_thermal_interval` / `add_thermal_profile` | `damage_models.py:953,970` | `:632` valor de mão da integral; `:639` acumulação por trajetória |
| **(5.1) — $D^{el}$** | $\sum_m \sum_j 1/N_j$ | `add_event` / `add_events` / `add_profile` | `damage_models.py:890,917,921` | `:622`, `:721` RUL em manobras e anos |
| **(5.2)** | $N_j$ dependente do estado $U_w(\theta,D)$; travessia de limiar | `_effective_threshold_kV` + `normalization="residual_withstand"` | `damage_models.py:883-888,593-607` | `:683` monotonicidade em `residual_withstand`; `:699` limiar dependente do estado reabre o dano |
| **ψ(D)** | $\psi(D) = 1 - (1-\psi_{min})D$, $\psi(0)=1$, $\psi' < 0$ | `psi_linear` | `damage_models.py:647` | `:782` $\psi(0)=1$; `:785` decrescente |
| **γ(t)** | $\gamma = U_w(t)/U_s$, $U_w = U_{w0}\psi(D)$ | `U_w_kV()` / `gamma()` | `damage_models.py:849,864` | `:659` γ e suportabilidade residual; `:669,674` erros por dado ausente |
| **RUL (det.)** | $\widehat{\mathrm{RUL}} = (1-D)/(\mathrm{d}D/\mathrm{d}t)$ | `rul_from_damage` | `rul_estimator.py:470` | `:919` valor de mão; `:923` taxa nula → `inf`; `:926` $D\ge1$ → 0 |
| **RUL_N, RUL_t** | $\widehat{\mathrm{RUL}}_N = (1-D)/\mathbb{E}[\Delta D_m]$; $\widehat{\mathrm{RUL}}_t = \widehat{\mathrm{RUL}}_N/\lambda_m$ | `rul_operations()` / `rul_years(λ_m)` | `damage_models.py:998,1019` | `:721` valores; `:713` exige `add_profile`; `:749` `inf` se tudo abaixo do limiar |
| **EKF** | $I(t)=\alpha e^{\beta(t-t_0)}$, estado $[I,\alpha,\beta]$, eqs. (3)–(6) | `EkfRulEstimator.update` | `rul_estimator.py:297-359` | `:808` converge em série sintética; `:855` determinismo; `:863` histórico |
| **RUL + IC** | $T=\ln(\text{lim}/\alpha)/\beta$; método delta sobre $(\alpha,\beta)$ | `predict_rul` | `rul_estimator.py:383-467` | `:824` ponto = analítico; `:834` intervalo contém o ponto; `:844` confiança maior → intervalo maior |
| **AHI** | média ponderada renormalizada sobre componentes disponíveis | `AssetHealthIndex.index` | `health_index.py:464-479` | `:944` ativo íntegro = 100; `:950` exaurido = 0; `:998` renormalização |
| **$T_1$** | $T_1 = 1{,}67\,(t_{90\%}-t_{30\%})$ | `extract_stress_events` | `stress_profile.py:553-584` | `:185` casa com a definição normativa; `:171` Tabela III de A |
| **Eventos equivalentes** | $\sum_j (V_j/V_{max})^{n}$ | `StressProfile.equivalent_events` | `stress_profile.py:338-356` | `:314` casa com cálculo manual |

### 4.2 Duas decisões de modelagem materializadas no código

**(a) Convenção de sinal térmico.** A forma impressa por Feilat, $\exp[-B(1/T - 1/T_0)]$, faria a vida **crescer** com a temperatura, o que é fisicamente incorreto [FATO: Etapa 1, §5.4, D5, "Nota de sinal"]. O código adota $c_T = 1/T_0 - 1/T$ e o teste `test_arrhenius_sign_convention_life_decreases_with_heat` trava essa escolha [REPO: `damage_models.py:261-293`; teste `:452`]. Em D7, o fator $2^{(\theta_0-\theta_j)/\mathrm{HIC}}$ multiplica $N_j$, logo $1/N_j \propto 2^{(\theta_j-\theta_0)/\mathrm{HIC}}$ — **o fator térmico multiplica o dano** [REPO: `damage_models.py:582-584,609-614`; Etapa 2, §3.1]. Com HIC = 10 K, $+20$ K multiplicam a taxa de dano por 4,0 [REPO: teste `:563`; limitação `rul_thermal_state_not_derived`, `prognosis/__init__.py:214-219`].

**(b) Os dois modos de normalização de D7.** `threshold_shift` reproduz D7 como impressa; `residual_withstand` normaliza o estresse pela suportabilidade residual, $\big(aV_{pk}/U_w\big)\big/\big(V_{ref}/U_{w0}\big)$, de modo que $(V = V_{ref}, U_w = U_{w0}) \Rightarrow \text{razão} = 1$ [REPO: `damage_models.py:593-607`]. A razão de existir os dois modos é a **monotonicidade perversa** demonstrada na Etapa 2: em `threshold_shift`, para eventos mais severos que a referência ($aV_{pk} > V_{ref}$) — exatamente o regime dos 30 a 41 kV do Documento A —, reduzir $V_{th}$ pelo envelhecimento **reduz** o dano calculado, dando $\partial F/\partial D < 0$ [FATO: Etapa 2, §5.2, cálculo próprio sobre D7]. O modo `residual_withstand` torna $\partial F/\partial D > 0$ **estrutural**, e o teste `test_residual_withstand_is_monotonic_in_damage` verifica isso [REPO: teste `:683`]. A limitação `rul_synergy_lower_bound` declara textualmente esse condicionamento [REPO: `prognosis/__init__.py:178-185`].

---

## 5. Plano de validação

### 5.1 *Fixtures* sintéticas derivadas do Documento A

O Documento A publica, na Tabela III (p. 3), pico de TRV e RRRV por fase, com e sem *snubber* [FATO: doc A, Tabela III, p. 3]:

| Fase | Sem *snubber* — pico (kV) | Sem — RRRV (kV/µs) | Com *snubber* — pico (kV) | Com — RRRV (kV/µs) | Redução do pico [CÁLCULO PRÓPRIO] |
|---|---|---|---|---|---|
| A | −30,24 | 13,90 | 6,35 | 3,28 | 79,0 % |
| B | 41,44 | 15,05 | 13,65 | 13,11 | 67,1 % |
| C | −38,30 | 19,00 | −9,98 | 9,43 | 73,9 % |

**F1 — reprodução de pico e RRRV.** *Fixture* `_ramp_waveform(peak_kV, slope_kV_per_us, dt_s)`: rampa linear até o pico da fase B (41,44 kV) com inclinação 15,05 kV/µs, seguida de cauda exponencial de 20 µs [REPO: `tests/test_pp_prognosis_core.py:63-88`]. A rampa linear é escolhida porque nela o dv/dt máximo é **exatamente** a inclinação, o que permite comparar a extração com um valor fechado [REPO: `tests/test_pp_prognosis_core.py:73-76`]. Com passo fino de 10 ns, `test_doc_a_table_iii_phase_b_peak_and_rrrv` recupera pico e dv/dt com `rel=1e-3` e `warnings == []` [REPO: testes `:171-183,195-201`]; `test_t1_matches_iec_60034_15_definition` confirma $T_1 = 1{,}67 \times 0{,}60 \times t_{rampa} = 2{,}759$ µs [REPO: teste `:185-193`]. **F1b — passo grosseiro**: repetir a mesma *fixture* com o passo de 1 µs efetivamente usado em A [FATO: doc A, Tabela II, p. 3]; o critério passa a ser a **presença** dos avisos de passo grosseiro e de frente subamostrada, e o dv/dt reportado deve ser tratado como limite inferior [REPO: testes `:202-226`].

**F2 — mitigação atravessa o limiar de dano.** Com $V_{th}$ posicionado entre 13,65 e 41,44 kV, o evento "com *snubber*" da fase B deve produzir dano **exatamente** zero e o "sem *snubber*" dano positivo. O teste `test_mitigation_moves_event_below_threshold` já cobre a lógica [REPO: teste `:1120-1135`]. **Ressalva obrigatória**: isso valida a *mecânica* do limiar, **não** o valor de $V_{th}$, que é não calibrado.

**F3 — cadeia completa forma de onda → AHI.** `test_waveform_to_health_index` percorre `extract_stress_events` → `CombinedDamageAccumulator` → `AssetHealthIndex` [REPO: teste `:1099-1119`].

### 5.2 *Fixtures* sintéticas derivadas do Documento B

O Documento B publica, na Tabela III, três pontos de operação [FATO: doc B, Tabela III, linhas 343-354 do texto extraído; discussão p. 5-6]:

| Solução | $f_5$ (kW) | $V$ (pu) | Margem sobre $g_1 = 0{,}85$ pu [CÁLCULO PRÓPRIO] |
|---|---|---|---|
| Preserva 1 510 kW de produção | 7 417 | 0,850 | 0,00 % |
| Solução do "joelho" (mantém M_800) | 8 127 | 0,858 | 0,94 % |
| Corta as 19 máquinas | 8 927 | 0,866 | 1,88 % |

Sem corte, a tensão de *inrush* cai a 0,755 pu, bem abaixo do limite de 0,85 pu [FATO: doc B, p. 3, linha 140 do texto extraído].

**F4 — monotonicidade perversa de $f_5 \to \lambda$.** *Fixture* com três cenários de λ (manobras severas/ano) associados às três soluções, alimentando `rul_years(λ_m)` [REPO: `damage_models.py:1019-1037`]. **Critério**: a solução que preserva mais carga (menor $f_5$) deve produzir RUL **menor** se e somente se ela implicar λ maior — a arquitetura precisa tornar essa dependência visível no laudo, porque a margem de *ride-through* de 0,00 % da solução de 7 417 kW é menor que qualquer uma das três fontes de erro identificadas na Etapa 2 [FATO: Etapa 2, §2.4].

**F5 — trajetória térmica de partida.** `thermal_profile` derivado do tempo de aceleração sob tensão reduzida, alimentando `add_thermal_profile` [REPO: `damage_models.py:970-983`; teste `:639`]. **Bloqueio conhecido**: `motor_starting.py` não calcula I²t (§2.2), então a *fixture* precisa de entrada externa até que esse campo exista.

### 5.3 Métricas de prognóstico

| Métrica | Definição | Aplicável a | Estado |
|---|---|---|---|
| $\alpha$-$\lambda$ | fração de instantes em que $\widehat{\mathrm{RUL}}(t)$ cai na faixa $(1\pm\alpha)\mathrm{RUL}^*(t)$, avaliada em $t = \lambda\,t_{EoL}$ | EKF (`predict_rul`) | **A implementar** — exige verdade-terreno $\mathrm{RUL}^*$ |
| Horizonte de prognóstico | primeiro $t$ a partir do qual a métrica $\alpha$-$\lambda$ passa a ser satisfeita continuamente | EKF | **A implementar** |
| RMSE do indicador | $\sqrt{\frac{1}{N}\sum (\hat I_k - I_k)^2}$ sobre `predict_indicator` | EKF | **A implementar** — `history` já expõe a série [REPO: `rul_estimator.py:281-286`] |
| Cobertura do intervalo | fração de casos em que $\mathrm{RUL}^* \in [\mathrm{rul\_lower}, \mathrm{rul\_upper}]$ na confiança nominal | `RulPrediction` | **A implementar**; hoje só há teste de *bracketing* e de largura monotônica [REPO: testes `:834,844`] |
| Determinismo | mesma entrada → mesma saída, bit a bit | EKF | **Implementado** [REPO: teste `:855`] |

Todas as quatro primeiras exigem verdade-terreno. Como não há trajetória de degradação medida disponível, elas devem ser calculadas primeiro sobre **degradação sintética com fim de vida conhecido por construção** (série $\alpha e^{\beta t}$ com ruído gaussiano de variância conhecida), e o laudo deve declarar que a validação é sintética [INFERÊNCIA].

### 5.4 O que só pode ser validado com ensaio acelerado ou bancada de MT

| Item | Por que a simulação não basta | Evidência |
|---|---|---|
| Expoente $n$ da curva de vida para mica-epóxi de MT sob impulsos de VCB | Nenhum valor foi localizado; os expoentes de 3,8 a 11,7 vêm de fio esmaltado e epóxi puro. Mover $n$ de 4 para 9 altera a vida em manobras por fator 6,6 | [REPO: `prognosis/__init__.py:169-177`; Etapa 1, §5.4, D1] |
| Limiar de dano $V_{th}$ | A única evidência empírica de existência de limiar é indireta: 1 000 a 8 000 surtos de 3,0 a 7,8 pu não produziram degradação mensurável em dois de três estatores | [LITERATURA: Gupta, Lloyd e Sharma, IEEE TEC 5(2):320–326, 1990, via Etapa 1, §5.4, D2] |
| Fração $a(t_f)$ sobre a primeira bobina | Depende de reflexões no cabo e da geometria do enrolamento; deve ser **medida**, não presumida | [REPO: `damage_models.py:423-427`; limitação `rul_measurement_point`] |
| Forma de $\psi(D)$ e de $V_{th}(\theta)$ | Nenhuma fonte primária acessada fornece parâmetros medidos para mica-epóxi de MT | [FATO: Etapa 2, §5.2, "Ausência de parâmetros"] |
| Termo de sinergia $D_{sin}$ | (5.3) é definida como diferença entre solução acoplada e desacoplada; sua magnitude só é observável em ensaio multiestresse | [FATO: Etapa 2, §5.2] |
| Transferência do EKF de envelhecimento térmico em BT para dano espira-a-espira em MT | A arquitetura foi validada em estatores de 5 kW de baixa tensão ($n=3$), monitorando fase-terra | [REPO: `prognosis/__init__.py:220-226`] |
| Frentes sub-microssegundo | A IEC 60034-15:2009 §A.1 admite frentes de serviço até 0,1 µs; o passo de 1 µs do Documento A não as resolve | [NORMA: IEC 60034-15:2009, §A.1, citada em `stress_profile.py:26-28`; FATO: doc A, Tabela II, p. 3] |

---

## 6. Roadmap por versão

### 6.1 Situação atual

Versão corrente `4.0.0-beta` [REPO: `app/core/version.py:1959-1968`]; o `CHANGELOG.md` registra a `[4.0.0-beta]` de 2026-05-01 com i18n EN/ES em paridade 133/133 e "Master Protocol 8/8 garantias mantidas" [REPO: `CHANGELOG.md:7-23`]. O `ROADMAP.md` cobre o ciclo v0.94 → v1.0 e **não** contém linha de prognóstico/RUL [REPO: `ROADMAP.md:1-40`] — o módulo é, portanto, feature nova sem paridade PTW correspondente, a ser declarada como superação [REPO: `anexos/repo/convencoes_auditoria_gui_docs.md:L14`].

### 6.2 MVP atual (entregue nesta sessão, **não** liberável)

| Entregue | Evidência |
|---|---|
| Pacote `app/postprocessor/prognosis/` — 4 módulos mais a fachada, 3 052 linhas (`__init__` 248, `stress_profile` 672, `damage_models` 1 060, `rul_estimator` 494, `health_index` 578) | [CÁLCULO PRÓPRIO: `wc -l`] |
| 142 testes verdes em 0,34 s | [CÁLCULO PRÓPRIO: `pytest -q`] |
| Zero dependência nova (stdlib + `numpy`, já em `requirements.txt:4`) | [REPO: `rul_estimator.py` importa `numpy`; os demais módulos, apenas stdlib] |
| *Guards* de arquitetura: núcleo não importa GUI/plot nem faz I/O | [REPO: testes `:1157,1174`] |

### 6.3 v4.1.0-beta — "RUL Sprint 1: integração mínima liberável"

Escopo: E1 (`Feature.RUL_PROGNOSIS`), E2/E3 (`KNOWN_LIMITATIONS` + `STANDARDS_CATALOG`), E6/E8 (menu + `RulPrognosisDialog`), E12 (i18n EN/ES), E13/E14 (`version.py` + `CHANGELOG.md`), E17 (`tests/test_pp_v4_1_0_rul_prognosis.py`), E18 (subset CI).

Confronto com os **oito critérios de aceite de release** [REPO: `docs/PTW_TOTAL_PARITY_DIRECTIVE.md:128-142`]:

| # | Critério | Estado após v4.1.0 |
|---|---|---|
| 1 | TodoWrite completo das features endereçadas | A fazer no sprint |
| 2 | Cada feature cita seção+página em docstring | **Já atendido** no núcleo [REPO: `prognosis/__init__.py:39-65`; `stress_profile.py:20-31`] |
| 3 | Entrada na `PTW_SURPASSING_MATRIX.md` com ≥ 1 dimensão de superação | A fazer — declarar como superação (não há feature PTW de RUL) |
| 4 | Testes cobrem ≥ 80 % do módulo, ≥ 5 testes | **Já atendido** (142 testes) |
| 5 | *Sweep* *targeted* verde | A fazer |
| 6 | *Restore point* criado | A fazer (local, *gitignored*) |
| 7 | *Handoff doc* + `SESSION_HANDOFF` atualizados | A fazer |
| 8 | *Smoke test* reproduzindo exemplo do tutorial | A fazer — "Para usar RUL, o usuário clica em Análise → Prognóstico de isolamento / RUL" |

**Bloqueadores para fechar a release**: critérios 1, 3, 5, 6, 7 e 8 — todos de processo/integração, nenhum de núcleo computacional. O critério 8 é o que materializa a 7ª garantia.

### 6.4 v4.2.0 — "RUL Sprint 2: laudo, cadeia ATP e métricas de prognóstico"

| Item | Entrega |
|---|---|
| `report_rul_html.py` / `report_rul_pdf.py` | Laudo com header auditável, `citation()` por valor e bloco de limitações |
| Adaptador `AtpResults` → `extract_stress_events` | Fecha a lacuna DM: leitura do PL4 a partir de `RunResult.run_dir` |
| `transient_metrics` / `trt_analyzer` | `max_dvdt_kv_per_us` e contagem de excursões (campos opcionais) |
| `motor_starting` | `i2t_A2s` e `t_acc_s` explícitos |
| Métricas $\alpha$-$\lambda$, horizonte, RMSE e cobertura | Sobre degradação sintética; declaradas como validação sintética |
| Coleta de CREA/ART no diálogo de exportação | Fecha a lacuna L3 do mapa de convenções |

### 6.5 v4.3.0 — "RUL Sprint 3: incerteza completa e alinhamento com o Documento A"

| Item | Entrega |
|---|---|
| Saída distribucional (B10/B50 de Weibull por Monte Carlo sobre $n_r$, $V_{pk}$, $t_f$ e parâmetros de VCB), com `seed` no *payload* do *checksum* | Requisito de ISO 13381-1:2015, 3.3 e 3.9, hoje atendido apenas por método delta [REPO: limitação `rul_interval_delta_method`] |
| Lei de RRDS parabólica como **opção** no `.mod` e no *emitter* | Alinhamento com $A = 0{,}801$ kV·ms⁻¹ e $B = 1{,}226$ kV·ms⁻² do Documento A, sem quebrar defaults |
| *Dock* de curva de degradação com IC | E11 do mapa de convenções |
| *Health-aware load shedding* ($f_6$/$g_4$) | Etapa 2, §6.2 — depende de motor de otimização, fora do repositório hoje |

---

## 7. Riscos técnicos e impacto

### 7.1 Risco dominante: ausência de curva de vida calibrada

O risco de maior magnitude não é de engenharia de software: é que **nenhum valor de $n$ para mica-epóxi pré-formada de MT sob impulsos de VCB foi localizado na literatura acessada**, e que a vida em manobras varia por fator 6,6 ao mover $n$ de 4 para 9 [REPO: `prognosis/__init__.py:169-177`; Etapa 1, §5.4, D1]. Consequência arquitetural já implementada: `DamageModelParams.calibration_warnings()` **sempre** devolve ao menos uma advertência, independentemente da parametrização, e o `summary()` do acumulador a anexa [REPO: `damage_models.py:484-526,1058`; teste `:605`]. Consequência de produto: nenhum número absoluto de RUL pode ser publicado; o uso defensável do MVP é **comparativo** (com *snubber* × sem *snubber*, solução A de corte × solução B), no qual os parâmetros não calibrados se cancelam parcialmente na razão [INFERÊNCIA].

### 7.2 Desempenho

| Aspecto | Medida / estimativa | Evidência |
|---|---|---|
| Suíte do núcleo | 142 testes em 0,34 s | [CÁLCULO PRÓPRIO] |
| `extract_stress_events` | uma passada sobre a série para detectar excursões, mais uma busca retroativa por excursão; complexidade $O(N)$ no número de amostras, com constante pequena | [REPO: `stress_profile.py:529-540,556-575`] |
| Janela do Documento A | 45 ms a passo de 1 µs = 45 000 amostras por variável [FATO: doc A, Tabela II, p. 3] — irrelevante para o custo | [CÁLCULO PRÓPRIO] |
| EKF | matrizes 3×3 em numpy; custo por atualização constante | [REPO: `rul_estimator.py:325-355`] |
| Ponto de atenção | listas Python nativas em `results_reader` (`float32` → `list[float]`), o que multiplica o custo de memória para varreduras longas | [REPO: `anexos/repo/trt_transitorios_simulacao.md:38`] |

### 7.3 Dependências novas

**Nenhuma.** `stress_profile.py`, `damage_models.py` e `health_index.py` usam apenas a biblioteca padrão; `rul_estimator.py` usa `numpy`, já declarado [REPO: `requirements.txt:4`]. Isso evita o risco R4 do mapa de convenções (dependência nova quebra o *job* `imports`, que instala apenas `numpy`, `pydantic` e `PyYAML`, incha o PyInstaller e o Docker e exige `THIRD_PARTY_NOTICES`/`LICENSING` e o `Dockerfile`, que está na lista travada) [REPO: `anexos/repo/convencoes_auditoria_gui_docs.md:R4`]. O intervalo de confiança usa `statistics.NormalDist` da *stdlib* em vez de `scipy` [REPO: `rul_estimator.py:449`].

### 7.4 *Subset* de CI

O *job* de teste do CI público roda uma **lista fixa de 12 arquivos**, porque o *sweep* completo inclui testes legados que abrem `QDialog` modal e travam em ambiente *headless* [REPO: `.github/workflows/test.yml:50-78`]. Consequência direta: **`tests/test_pp_prognosis_core.py` não roda no CI hoje** e sua cobertura não é medida. Mitigação obrigatória no Sprint 1: acrescentar o arquivo à lista e `--cov=app.postprocessor.prognosis` ao comando. Como o núcleo não importa PySide6 nem matplotlib, ele roda sem *display* [REPO: teste `:1157`].

### 7.5 Demais riscos

| # | Risco | Impacto | Mitigação |
|---|---|---|---|
| RA | *Backend* órfão — módulo sem ação de menu viola a 7ª garantia; release reaberta como *draft* e item P0 | Alto, processual | Sprint 1 entrega backend + diálogo + menu + teste de *wiring* na mesma release [REPO: `anexos/repo/convencoes_auditoria_gui_docs.md:R1`] |
| RB | *Hash* de auditoria sobre série temporal longa: `_to_jsonable` faz `repr` de objetos desconhecidos, tornando o *checksum* dependente da versão do numpy | Alto, de reprodutibilidade | Hashear resumo determinístico (§3.1, item 4) e declarar em `KNOWN_LIMITATIONS` |
| RC | Colisão de chaves nos dicionários globais `KNOWN_LIMITATIONS`/`STANDARDS_CATALOG`, sem *namespace* por módulo | Médio | **Já mitigado**: as 11 chaves usam prefixo `rul_` e há teste que o verifica [REPO: `prognosis/__init__.py:164-167`; teste `:1137`] |
| RD | Bump de versão quebra os testes de *readiness*/*milestone*, que exigem prefixo `4.` e sufixo `alpha`/`beta` | Médio | Bump para `4.1.0-beta`, mantendo `PRE_RELEASE` [REPO: `app/core/version.py:1960`] |
| RE | Paridade i18n: chave só em `en.json`, ou valor vazio, quebra os testes de paridade | Médio | Adicionar pares completos EN e ES simultaneamente (133 chaves hoje em cada) |
| RF | Duas físicas de VCB incompatíveis (linear no *template*, quadrática no artefato de referência e no Documento A) | Médio, de reprodutibilidade | Parametrizar a lei mantendo `linear` como default (§2.3) |
| RG | Sobre-interpretação do AHI: IR/PI, tan δ e DP têm sensibilidade nula ou indireta ao dano espira-a-espira, e as próprias normas declaram que suas tendências não predizem tempo até a falha | Alto, de comunicação | **Já declarado** na limitação `rul_ahi_bands_not_normative` e no `summary()` [REPO: `prognosis/__init__.py:234-241`; teste `:1086`] |

---

## 8. Limitações e o que **não** foi implementado

### 8.1 Limitações do núcleo — as 11 chaves declaradas

Todas em `app/postprocessor/prognosis/__init__.py:168-248`, verificadas por teste (`:1137-1155`):

| Chave | Núcleo da limitação |
|---|---|
| `rul_params_not_calibrated` | Todos os parâmetros de dano são não calibrados; a incerteza de $n$ **domina** a estimativa de RUL |
| `rul_synergy_lower_bound` | Com $D_{sin}=0$, $D$ é cota inferior de dano e cota superior de RUL; $\partial F/\partial D > 0$ só é estrutural em `residual_withstand` |
| `rul_miner_linear_order_independent` | Miner usa valores esperados, linearidade vida-estresse e independência da ordem — o que não se verifica em dielétricos com histórico de *treeing* |
| `rul_front_time_sampling` | Com passo da ordem do tempo de frente, os dv/dt reportados são limites inferiores |
| `rul_measurement_point` | TRV no disjuntor não é a tensão nos terminais do motor; reflexões no cabo e $a(t_f)$ não são modeladas |
| `rul_reignition_count_user_premise` | $n_r$ é entrada do usuário ou resultado da detecção; sob IPL com $n \ge 4$ o dano é dominado pela maior reignição |
| `rul_thermal_state_not_derived` | $\theta_j$ é entrada; com HIC = 10 K, erro de $+20$ K multiplica a taxa de dano por 4,0 |
| `rul_ekf_thermal_aging_only` | Arquitetura validada em envelhecimento térmico de estator de 5 kW em BT; transferência para MT é hipótese |
| `rul_interval_delta_method` | Intervalo por método delta, não distribuição B10/B50 de Weibull por Monte Carlo |
| `rul_ahi_bands_not_normative` | Faixas 85/70/50 e pesos são convenção do módulo, não normativos |
| `rul_energy_surge_impedance_proxy` | $E = \int v^2/Z\,\mathrm{d}t$ com $Z$ informado pelo usuário; não é energia absorvida medida |

### 8.2 O que **não** foi implementado

| Item | Estado |
|---|---|
| `Feature.RUL_PROGNOSIS` e gate `@requires_feature` | Não existe [REPO: `app/commercial/feature_gates.py:67-96`] |
| Ação no menu Análise e `RulPrognosisDialog` | Não existem — **7ª garantia em aberto** |
| Chaves `rul_*` no `KNOWN_LIMITATIONS` global e normas no `STANDARDS_CATALOG` | Não copiadas; hoje 7 chaves e 13 normas [REPO: `audit_trail.py:73-87,338-382`] |
| Laudo HTML/PDF de RUL | Não existe |
| Strings i18n EN/ES do módulo | Não existem |
| Entrada em `CHANGELOG.md` e bump de `version.py` | Não feitos |
| Adaptador PL4 → perfil de estresse | Não existe |
| `max_dvdt`, contagem de excursões, I²t, $t_{acc}$ | Não expostos pelos módulos herdados |
| Lei parabólica de RRDS como opção | Não implementada |
| Saída distribucional B10/B50 por Monte Carlo | Não implementada |
| Termo de sinergia $D_{sin}$ com parametrização física | Não implementado — apenas o gancho `synergy_fn` [REPO: `damage_models.py:745,799-807`] |
| Métricas $\alpha$-$\lambda$, horizonte, RMSE, cobertura | Não implementadas |
| *Health-aware load shedding* ($f_6$/$g_4$) | Não implementado |

### 8.3 Lacunas normativas desta etapa

| # | Lacuna | Consequência |
|---|---|---|
| L-N1 | Texto normativo da **ISO 13374-1** não acessado nesta sessão | As camadas DA/DM/SD/HA/PA/AG são vocabulário de organização; nenhuma conformidade é alegada — [INSERIR CITAÇÃO: ISO 13374-1, título, ano e cláusula dos blocos funcionais] |
| L-N2 | `psi_min = 0,5` ancorado em fonte **secundária** que cita IEEE 522 | Marcado como hipótese a verificar no texto primário [REPO: `damage_models.py:655-665`] |
| L-N3 | `tan_delta_max = 20×10⁻³` proveniente de citação secundária da IEC 60034-27-3, Tab. 1 | Rastreável mas não verificado na fonte primária [REPO: `health_index.py:165-167`] |
| L-N4 | Parâmetros primários de Simoni (1981/1984) e de Montanari, Mazzanti e Simoni (2002) não acessados | Mantidos como [INSERIR CITAÇÃO] na Etapa 1, §5.4, D5 |

---

## 9. Referências

**Documentos primários da sessão**

SILVA, L. F. *et al.* **Documento A — Active thyristor snubber for VCB switching transients** (texto extraído). Tabelas II e III, p. 3. [Texto de trabalho; INSERIR CITAÇÃO completa: autores, evento SEPOC, ano, DOI].

SILVA, L. F. *et al.* **Documento B — Load shedding under N-1 with OpenDSS and NSGA-II/III** (texto extraído). Tabela III e p. 3, 5-6. [Texto de trabalho; INSERIR CITAÇÃO completa: autores, evento SEPOC, ano, DOI].

**Normas**

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **ABNT NBR 17094-3:2018** — Máquinas elétricas girantes: ensaios. Cláusulas 6.8.2 (Tabela 2, resistência de isolamento mínima) e 6.8.3 (índice de polarização). Rio de Janeiro: ABNT, 2018.

INTERNATIONAL ELECTROTECHNICAL COMMISSION. **IEC 60034-15:2009** — Rotating electrical machines — Part 15: Impulse voltage withstand levels of form-wound stator coils for rotating a.c. machines. Cláusulas 2.4, 4.2, 5.1 e Anexo A.1. Genebra: IEC, 2009.

INTERNATIONAL ELECTROTECHNICAL COMMISSION. **IEC 60034-18-41:2014** — Partial discharge free electrical insulation systems (Type I) used in rotating electrical machines fed from voltage converters. Cláusulas 3.2, 3.9 e 3.13. Genebra: IEC, 2014.

INTERNATIONAL ELECTROTECHNICAL COMMISSION. **IEC 60034-27-2:2023; IEC 60034-27-3:2015; IEC 60034-27-4:2018** — Off-line/on-line partial discharge measurements, dielectric dissipation factor and insulation resistance of the stator winding insulation. Introdução (as tendências não predizem tempo até a falha). Genebra: IEC.

INTERNATIONAL ELECTROTECHNICAL COMMISSION. **IEC 60071-1:2019** — Insulation co-ordination — Part 1: Definitions, principles and rules. Cláusulas 3.31 e 3.34. Genebra: IEC, 2019.

INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. **ISO 13381-1:2015** — Condition monitoring and diagnostics of machines — Prognostics — Part 1: General guidelines. Cláusulas 3.3 e 3.9. Genebra: ISO, 2015.

INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. **ISO 13374-1** — Condition monitoring and diagnostics of machines — Data processing, communication and presentation — Part 1: General guidelines. [INSERIR CITAÇÃO: ano e cláusula dos blocos funcionais DA/DM/SD/HA/PA/AG — texto não acessado nesta sessão].

NATIONAL ELECTRICAL MANUFACTURERS ASSOCIATION. **NEMA MG 1**, Parte 31, cláusula 31.4.1.2 — *k* = 10 °C para vida térmica relativa. Rosslyn: NEMA.

**Literatura**

CIGRE WORKING GROUP D1.43. **Technical Brochure 703** — Dielectric performance of insulation systems fed by fast pulses. p. 29 (Fig. 31), Figs. 24 e 33, p. 35-36. Paris: CIGRE.

FEILAT, E. A. Lifetime estimation of insulation systems. *IntechOpen*, 2018. Equações (21), (26), (27) e (29). DOI 10.5772/intechopen.72423. Disponível em: https://doi.org/10.5772/intechopen.72423.

GUPTA, B. K.; LLOYD, B. A.; SHARMA, D. K. Degradation of turn insulation in motor coils under repetitive surges. *IEEE Transactions on Energy Conversion*, v. 5, n. 2, p. 320-326, 1990. DOI 10.1109/60.107228. Disponível em: https://doi.org/10.1109/60.107228.

JENSEN, W. R.; STRANGAS, E. G.; FOSTER, S. N. Prognostics of stator insulation using an extended Kalman filter. 2018. Equações (1)-(8). [Fichamento interno: artigo 02; INSERIR CITAÇÃO completa: veículo, volume, páginas, DOI].

MA, K. *et al.* Mission-profile-based lifetime prediction of power devices. *IEEE Transactions on Power Electronics*, v. 30, n. 2, 2015. Equações (1)-(3), p. 5, 7. [Fichamento interno: artigo 12].

THEOFANOUS, N. *et al.* Thermal ageing of insulation systems. *Energies*, v. 18, art. 6087, 2025. Equações (5), (9)-(10), (17)-(19), (25); Tabela 1; p. 11 (HIC 8-15 °C). Disponível em: https://doi.org/10.3390/en18226087.

WARREN, V. Partial discharge statistics for medium-voltage machines. *IRMC*, 2022. Tabela 1 (percentis de $Q_m$ para 2 a < 6 kV, VHF, acopladores de 80 pF, 10 pps). [Fichamento interno; INSERIR CITAÇÃO completa].

**Artefatos do repositório (fonte de todo `arquivo:linha` citado)**

Olivas Power System Studio, v4.0.0-beta. `/home/user/olivas-power-system-studio`. Módulos citados: `app/postprocessor/prognosis/{__init__,stress_profile,damage_models,rul_estimator,health_index}.py`; `tests/test_pp_prognosis_core.py`; `app/postprocessor/{audit_trail,report_html,report_pdf,trt_analyzer,motor_starting}.py`; `app/commercial/feature_gates.py`; `app/gui/{main_window,analysis_dialogs}.py`; `app/core/version.py`; `app/simulation/{runner,results_reader}.py`; `app/analysis/transient_metrics.py`; `app/preprocessor/vcb_model_emitter.py`; `app/preprocessor/atp_templates/vcb_reignition.mod`; `requirements.txt`; `.github/workflows/test.yml`; `CHANGELOG.md`; `ROADMAP.md`; `ARCHITECTURE_ATP_STUDIO.txt`.

**Documentos anteriores desta série**

`docs/research/rul_isolamento/00_INDICE.md` — nota metodológica e rótulos de evidência.
`docs/research/rul_isolamento/01_ETAPA1_monitoramento_degradacao_isolamento.md` — §3.3 ($T_1$ e RRRV), §5.4 (D1-D7), §5.5, §6 (γ(t) e correção conceitual do BIL).
`docs/research/rul_isolamento/02_ETAPA2_cruzamento_A_x_B.md` — §2.4 (margens de *ride-through*), §3.1 (fator térmico), §5.2 (eqs. 5.1-5.3 e monotonicidade perversa), §6 (*health-aware load shedding*).
`docs/research/rul_isolamento/anexos/repo/convencoes_auditoria_gui_docs.md` — pontos de extensão E1-E20, checklist 4.1-4.7, lacunas L1-L15, riscos R1-R15.
`docs/research/rul_isolamento/anexos/repo/trt_transitorios_simulacao.md` — cadeia ATP → PL4 → métricas.
`docs/research/rul_isolamento/anexos/repo/vcb_reignicao_snubber.md` — divergência entre lei linear e parabólica de RRDS.
