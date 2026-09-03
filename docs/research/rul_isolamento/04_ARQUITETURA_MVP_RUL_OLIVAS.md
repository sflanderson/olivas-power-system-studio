# Etapa 3 (parte 2) — Arquitetura do MVP de RUL e *Asset Health Index* no Olivas Power System Studio

**Objetivo.** Documentar a arquitetura do MVP de prognóstico de vida útil remanescente (RUL) do isolamento estatórico de motores de indução de média tensão (2,3 a 13,8 kV) no Olivas Power System Studio, registrando **o que já foi implementado nesta sessão** — o pacote de prognóstico `app/postprocessor/prognosis/` (4 módulos mais a fachada, 3 052 linhas, 176 testes) e o **motor de transitórios eletromagnéticos dedicado** `app/simulation/emt/` (9 módulos mais o pacote de casos, 9 915 linhas, 273 testes) — com rastreabilidade `arquivo:linha`, e **o que falta** para fechar uma release conforme os oito critérios de aceite do projeto.

**Remissão.** A fundamentação do motor dedicado (dedução dos modelos companheiros contra Dommel 1969/1971, Ho *et al.* 1975, Lin & Martí 1990 e Mahseredjian *et al.* 2007; regressão dígito a dígito contra as Listas 01 e 02 de EEE873, elas próprias validadas contra o ATP; e o catálogo de 27 limitações do kernel) é objeto do **documento 05 desta série**, ao qual este documento remete em vez de repetir [REMISSÃO: `docs/research/rul_isolamento/05_MOTOR_EMT_DEDICADO.md` — §1 justificativa, §2 MNA e modelos companheiros, §3 CDA, §4 partida em regime permanente, §5 Bergeron e JMarti].

**Diagnóstico.** O núcleo computacional existe e é puro (sem I/O, sem GUI, sem estado global) [REPO: `app/postprocessor/prognosis/__init__.py:8-11`]. Ele **não** está integrado a nenhuma das seis convenções obrigatórias do repositório: não há `Feature` comercial, não há ação de menu (violação em aberto da 7ª garantia), não há chaves em `STANDARDS_CATALOG`/`KNOWN_LIMITATIONS` globais, não há laudo HTML/PDF, não há strings i18n, não há entrada em `CHANGELOG.md`/`version.py`. Quanto à camada de simulação, o quadro **mudou** nesta sessão: o repositório continua **sem** cadeia automática ATP → PL4 → perfil de estresse — o `AtpRunner` posiciona arquivos mas nenhum consumidor lê o PL4 a partir de `RunResult.run_dir` [REPO: `docs/research/rul_isolamento/anexos/repo/trt_transitorios_simulacao.md:28`, verificado contra `app/simulation/runner.py:285,338-372`] —, mas passou a dispor de um **motor de transitórios eletromagnéticos próprio, em Python**, cujas sondas entregam o vetor de estresse diretamente a `extract_stress_events`, sem passar por arquivo intermediário [REPO: `app/simulation/emt/probes.py:248-288`]. Duas premissas do enunciado da tarefa são **corrigidas** aqui: (i) não existe motor de física em C++ neste projeto — a árvore não contém um único arquivo `.cpp`/`.cc`/`.hpp` [CÁLCULO PRÓPRIO: `find . -name "*.cpp" -o -name "*.cc" -o -name "*.hpp"` → vazio]; o motor dedicado é **Python puro**, e a migração do laço interno para C++ atrás da mesma API é decisão futura, condicionada ao critério objetivo da §6.6, não estado atual; (ii) o `RRRV` do repositório é uma taxa **média** até o pico, não a derivada instantânea que o vetor de estresse exige [REPO: `app/analysis/transient_metrics.py:131`] — o motor dedicado já expõe a derivada máxima entre amostras consecutivas em `MotorSwitchingModel.trv_summary()` [REPO: `app/simulation/emt/cases/motor_switching.py:702-723`].

**Arquivos consultados.**

| Caminho | Uso nesta etapa |
|---|---|
| `/home/user/olivas-power-system-studio/app/postprocessor/prognosis/__init__.py` | API pública, `KNOWN_LIMITATIONS` (11 chaves) |
| `/home/user/olivas-power-system-studio/app/postprocessor/prognosis/stress_profile.py` | `StressEvent`, `StressProfile`, `extract_stress_events` |
| `/home/user/olivas-power-system-studio/app/postprocessor/prognosis/damage_models.py` | D1–D7, `CombinedDamageAccumulator`, ψ(D) |
| `/home/user/olivas-power-system-studio/app/postprocessor/prognosis/rul_estimator.py` | EKF, `RulPrediction`, `rul_from_damage` |
| `/home/user/olivas-power-system-studio/app/postprocessor/prognosis/health_index.py` | AHI 0–100, pesos, limiares, `explain()` |
| `/home/user/olivas-power-system-studio/tests/test_pp_prognosis_core.py` | 176 testes; mapeamento equação→teste |
| `/home/user/olivas-power-system-studio/app/simulation/emt/__init__.py` | Fachada do motor dedicado, `__all__` (`:216`), `KNOWN_LIMITATIONS` (`:311`, 19 chaves após agregar as do JMarti) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/components.py` | Modelos companheiros R, L, C, fonte, chave e RL acoplado; estampas MNA |
| `/home/user/olivas-power-system-studio/app/simulation/emt/circuit.py` | Montagem, LU com cache por topologia, CDA, `TimedSwitchController` (`:498`), `Solver` (`:659`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/steady_state.py` | Partida em regime permanente por solução fasorial (`initialize_steady_state`, `:761`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/line.py` | Linha/cabo a parâmetros constantes (Bergeron), `BergeronLine` (`:283`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/jmarti.py` | Linha/cabo dependente da frequência (Martí), `JMARTI_LIMITATIONS` (`:2252-2313`, 7 chaves) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/vcb.py` | VCB dinâmico: corte por margem, recuperação parabólica, reignição, extinção de AF |
| `/home/user/olivas-power-system-studio/app/simulation/emt/snubber.py` | SCR antiparalelos com `Rs`, disparo por sobretensão, bloqueio no zero |
| `/home/user/olivas-power-system-studio/app/simulation/emt/probes.py` | **Ponte simulação → prognóstico**: `to_stress_profile` (`:248-288`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/cases/motor_switching.py` | Caso do Documento A; `DOC_A_TABLE_III` (`:149`), `KNOWN_LIMITATIONS` (`:956`, 8 chaves) |
| `/home/user/olivas-power-system-studio/tests/test_emt_kernel.py`, `test_emt_steady_state.py`, `test_emt_jmarti.py`, `test_emt_vcb_snubber.py`, `test_emt_referencia_eee873.py` | 273 testes do motor (94 / 43 / 49 / 52 / 35) |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/01_ETAPA1_monitoramento_degradacao_isolamento.md` | D1–D7 (§5.4), γ(t) (§6), T1 (§3.3) |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/02_ETAPA2_cruzamento_A_x_B.md` | eq. (5.1)–(5.3), monotonicidade perversa (§5.2) |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/anexos/repo/convencoes_auditoria_gui_docs.md` | pontos de extensão E1–E20, checklist 4.1–4.7, riscos R1–R15 |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/anexos/repo/trt_transitorios_simulacao.md` | cadeia ATP→PL4→métricas |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/anexos/repo/vcb_reignicao_snubber.md` | divergência linear × parabólica de RRDS |
| `/home/user/olivas-power-system-studio/docs/research/rul_isolamento/anexos/pesquisa/entrega_trabalho_computacional.md` | forma de entrega do trabalho computacional |
| `app/commercial/feature_gates.py`, `app/postprocessor/audit_trail.py`, `report_html.py`, `report_pdf.py`, `app/gui/main_window.py`, `app/gui/analysis_dialogs.py`, `app/core/version.py`, `app/simulation/runner.py`, `app/simulation/results_reader.py`, `app/analysis/transient_metrics.py`, `app/postprocessor/trt_analyzer.py`, `app/postprocessor/motor_starting.py`, `app/preprocessor/vcb_model_emitter.py`, `app/preprocessor/atp_templates/vcb_reignition.mod`, `requirements.txt`, `.github/workflows/test.yml`, `CHANGELOG.md`, `ROADMAP.md`, `ARCHITECTURE_ATP_STUDIO.txt` | pontos de integração, verificados por leitura direta |
| `.../scratchpad/papers_AB/txt/A_sepoc_snubber.txt`, `.../B_sepoc_load_shedding.txt` | Tabelas II e III de A; Tabela III de B |

**Arquivos afetados.** Criado nesta etapa: apenas este documento. Criados **antes** nesta sessão: os 5 arquivos do pacote `prognosis/` e `tests/test_pp_prognosis_core.py`; e, depois, os 11 arquivos do pacote `app/simulation/emt/` mais os 5 arquivos de teste do motor. **Nenhum arquivo pré-existente do repositório foi modificado** — o motor dedicado é pacote novo e não toca `app/simulation/runner.py`, que continua sendo o caminho do ATP. A §2 lista as alterações pendentes.

**Estratégia.** (1) Mapear a cadeia em camadas funcionais ISO 13374 e ancorar cada camada em um componente real, distinguindo o que roda em Python no repositório — inclusive, agora, o motor EMT dedicado —, o que é binário externo e o que ainda não existe. (2) Enumerar arquivo por arquivo o que foi criado, o que criar e o que alterar, com dependência explícita. (3) Fixar contratos de dados versionados entre camadas. (4) Provar, por `arquivo:linha` e por teste, que D1–D7 e (5.1)–(5.2) estão implementadas. (5) Definir o plano de validação com *fixtures* derivadas das Tabelas III de A e de B e métricas de prognóstico. (6) Roadmap por versão contra os 8 critérios de aceite. (7)–(8) Riscos e limitações declarados.

**Limitações.** Este documento descreve arquitetura e código verificado; **não** entrega integração GUI, laudo, i18n nem gate comercial — todos permanecem pendentes, **também para o motor dedicado**, que hoje não é importado por nenhum módulo fora de `app/simulation/emt/` [CÁLCULO PRÓPRIO: `grep -rn "simulation.emt" app/` fora do próprio pacote → vazio] e é, portanto, um segundo *backend* órfão (risco RH da §7.5). O confronto do caso de manobra com a Tabela III do Documento A permanece **aberto** e é declarado como tal (§5.1 e §7.6). Os parâmetros dos modelos de dano continuam **não calibrados** para mica-epóxi pré-formada de MT; nenhum número de RUL produzido pelo módulo é citável como valor fechado [REPO: `app/postprocessor/prognosis/damage_models.py:377-380`]. O texto normativo da ISO 13374-1 **não foi acessado** nesta sessão: as seis camadas são usadas como vocabulário de organização, não como declaração de conformidade.

**Próximo passo recomendado.** Abrir `docs/v4.1.0_BACKLOG_AUDIT.md` e executar o Sprint 1 da §6 (`Feature.RUL_PROGNOSIS` + `RulPrognosisDialog` + ação de menu + teste de *wiring*), que é o único caminho para retirar o módulo da condição de *backend* órfão proibida desde a v3.1.0 [REPO: `docs/research/rul_isolamento/anexos/repo/convencoes_auditoria_gui_docs.md:171`, citando `docs/SESSION_HANDOFF.md:37-43`]. **O mesmo sprint deve tratar o motor EMT dedicado**, que hoje é o segundo *backend* órfão do repositório (risco RH, §7.5); e, no plano técnico, o próximo passo do motor é o carregador `.atp → Circuit` (§2.4), sem o qual a afirmação "o `.atp` é a fonte única da verdade" continua verdadeira como arquitetura e não exercitada como execução.

---

## 1. Fluxo de dados do gêmeo digital em camadas funcionais

### 1.1 Vocabulário de camadas e ressalva de conformidade

As seis camadas funcionais **DA → DM → SD → HA → PA → AG** (aquisição de dados, manipulação de dados, detecção de estado, avaliação de saúde, avaliação prognóstica, geração de recomendação) são a decomposição canônica de sistemas de monitoramento de condição [NORMA: ISO 13374-1:2003, blocos funcionais — **texto normativo NÃO acessado nesta sessão**; ver §8, item L-N1]. Elas são usadas aqui como **vocabulário de organização da arquitetura**, e nenhuma alegação de conformidade formal é feita. A exigência de nível de confiança explícito na saída prognóstica, essa sim, foi verificada e está citada no código [NORMA: ISO 13381-1:2015, 3.3 e 3.9, citada em `app/postprocessor/prognosis/__init__.py:55-56` e em `rul_estimator.py:401`].

### 1.2 Onde entra o Python e onde entram os motores de física

**Correção de premissa — não há C++ neste projeto, e o motor de transitórios não é mais só externo.** A árvore do repositório não contém nenhum arquivo `.cpp`, `.cc` ou `.hpp` [CÁLCULO PRÓPRIO: varredura `find`, resultado vazio]. Todo o código do produto é Python, e as dependências declaradas são `PySide6`, `anthropic`, `matplotlib`, `numpy`, `pytest`, `pydantic`, `PyYAML`, `openpyxl` [REPO: `requirements.txt:1-8`] — `scipy` **não** é dependência e não foi acrescentada pelo motor dedicado. Portanto **nenhum motor de física em C++ existe hoje neste projeto**, e a arquitetura do MVP não pressupõe compilação nativa. A decisão do autor é diferente de "nunca haverá C++": o motor dedicado nasce em Python com o **laço interno isolável**, e a migração desse laço para C++ atrás da mesma API é item de *roadmap* sujeito ao critério objetivo da §6.6 [DECISÃO DO AUTOR, registrada aqui como premissa de arquitetura].

Os motores de física passam a ser **três**, com naturezas distintas:

| Regime | Motor | Natureza | Papel do Olivas |
|---|---|---|---|
| Transitório eletromagnético (µs–ms) — **caminho principal** | Motor EMT **dedicado**, `app/simulation/emt/` | **Python puro dentro do repositório**, sem dependência nova (`numpy` já declarado); solver nodal de Dommel com integração trapezoidal, passo fixo, MNA, CDA, Bergeron e JMarti [REPO: `app/simulation/emt/__init__.py:22-53`] | Monta o circuito, resolve, e entrega o vetor de estresse $s_{m,j}$ **em memória**, por `probes.to_stress_profile` [REPO: `app/simulation/emt/probes.py:248-288`] |
| Transitório eletromagnético (µs–ms) — **via alternativa** | ATP/EMTP (executável externo, invocado por *subprocess*) | **Binário externo de terceiro**, caminho configurado pelo usuário; o repositório não o compila nem o distribui [REPO: `app/simulation/runner.py:27-36,167-179`] | Emite o `.atp`, invoca o executável, coleta `.pl4/.lis/.pch/.dbg` e grava `execution.log` [REPO: `app/simulation/runner.py:127-318,338-372,374-394`]. Continua íntegro e **não foi tocado** pelo pacote novo |
| Regime permanente e quase-estático (s–h) | Fluxo de potência, curto-circuito, partida de motor, TCC, arc-flash, confiabilidade | **Python puro dentro do repositório** [REPO: `app/postprocessor/power_flow.py`, `short_circuit.py`, `motor_starting.py`, `reliability.py` — inventário em `app/postprocessor/`] | Executa integralmente; não há motor externo |

**Por que um motor dedicado, e o que ele *não* substitui.** A justificativa registrada no próprio pacote é de volume, reprodutibilidade e distribuição: o executável ATP é binário licenciado, não redistribuível e orientado a **um caso por execução**, ao passo que o estudo de RUL exige da ordem de 10³ a 10⁴ execuções — o produto cartesiano da frente de Pareto de planos de corte (Documento B) pelo Monte Carlo do instante de abertura e da corrente de *chopping* (Documento A) [REPO: `app/simulation/emt/__init__.py:5-20`]. O que o motor dedicado **não** faz é substituir o `.atp` como registro: o arquivo permanece a **fonte única da verdade do caso técnico** (parágrafo seguinte), e o motor é apenas quem o **resolve**. Como a via do ATP continua disponível e intocada, o `.atp` permanece confrontável contra terceiro — é o que torna o motor auditável em vez de autorreferente.

O `.atp` é o **artefato canônico** da camada de transitórios: a arquitetura declarada do produto é `.atp → parser → modelo semântico → GUI/LLM/validação → serializer → .atp` [REPO: `ARCHITECTURE_ATP_STUDIO.txt:12-14`]. Ou seja, o modelo semântico é reconstruível a partir do arquivo e o arquivo é reconstruível a partir do modelo — o `.atp` é a fonte única da verdade do caso de transitório, e o `hash` desse arquivo é o candidato natural a identificador de proveniência do perfil de estresse (§3.4). **A entrada do motor dedicado não altera esse papel**: o motor consome o caso e produz a série, mas o registro do caso continua sendo o `.atp`. Enquanto não existir o carregador `.atp → circuito do motor` (lacuna declarada na §2.4), o caso do Documento A está codificado como *dataclasses* Python em `cases/motor_switching.py`, e é essa codificação — e não o `.atp` — que responde pelos números aqui citados; o `hash` de proveniência do perfil deve, nesse regime, apontar para a versão do módulo do caso, não para um `.atp` [CÁLCULO PRÓPRIO].

**Ressalva de método sobre o Documento B.** O Documento B resolve fluxo de potência em OpenDSS com otimização NSGA-II/III e *surrogate* de regressão *ridge* [FATO: doc B, p. 1-3]. O OpenDSS **não** é integrado ao repositório: nenhum módulo de `app/` o invoca [CÁLCULO PRÓPRIO: varredura do inventário de `app/postprocessor/`, `app/simulation/`, `app/analysis/`]. O que o Olivas executa hoje em regime permanente é o seu **próprio** fluxo de potência em Python. Nenhuma integração com OpenDSS é assumida nesta arquitetura; a ligação com B entra pela taxa λ de manobras severas, que é **entrada** do módulo (§3.2), não resultado de uma simulação acoplada.

### 1.3 A cadeia, camada por camada

```
┌─ DA — Data Acquisition ────────────────────────────────────────────────────┐
│ (a) SIMULAÇÃO — CAMINHO PRINCIPAL: motor EMT dedicado, em processo         │
│     caso (.atp = fonte da verdade; hoje dataclasses) ──▶ Circuit/Solver    │
│     [REPO: app/simulation/emt/circuit.py:317,659]  ──▶ Probe (em memória)  │
│ (a') SIMULAÇÃO — VIA ALTERNATIVA: .atp ──▶ ATP/EMTP externo                │
│     [REPO: app/simulation/runner.py:127-318]  ──▶ .pl4 / .lis / .pch       │
│ (b) CAMPO (não implementado): oscilografia de manobra, sensor de DP,       │
│     RTD/fibra de ponto quente, ensaios IR/PI e tan δ  ──▶ CSV/COMTRADE     │
└────────────────────────────────────────────────────────────────────────────┘
                              │ (a) em memória      │ (a') e (b) por arquivo
┌─ DM — Data Manipulation ────┴─────────────────────┴────────────────────────┐
│ (a) Ponte direta (IMPLEMENTADA):                                           │
│   probes.to_stress_profile(probe, threshold_kV, Z, θ) → StressProfile      │
│   [REPO: app/simulation/emt/probes.py:248-288]                             │
│ (a') Leitura PL4 → AtpResults(variables, time, data, delta_t, n_steps)     │
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
| DA (transitório, principal) | Motor EMT dedicado: `Circuit` + `Solver` + `VacuumCircuitBreakerModel` + `ThyristorSnubber` | **Implementado**, 273 testes verdes; Python puro, sem dependência nova | [REPO: `app/simulation/emt/circuit.py:317,659`; `vcb.py:356`; `snubber.py:184`; `cases/motor_switching.py:644`] |
| DA (transitório, alternativo) | ATP/EMTP externo via `AtpRunner.run` | **Externo, existente e intocado**; sucesso = `returncode == 0` e ausência de `/ERROR/` no *stdout* | [REPO: `app/simulation/runner.py:127-318`, critério em `:263-265` conforme `anexos/repo/trt_transitorios_simulacao.md:22`] |
| DA (campo) | Oscilografia, DP, RTD, IR/PI, tan δ | **Não implementado**; entradas do usuário | [REPO: `prognosis/__init__.py:200-219` — `rul_measurement_point`, `rul_thermal_state_not_derived`] |
| DM (leitura) | `read_pl4` → `AtpResults` | **Existente**; sem metadado de unidade (V × kV) e com exceções silenciadas | [REPO: `app/simulation/results_reader.py:46-96`; `anexos/repo/trt_transitorios_simulacao.md:35,46`] |
| DM (ponte motor dedicado → perfil) | `probes.to_stress_profile` → `extract_stress_events` | **Implementado**; converte V→kV e repassa `group_window_s`, `min_samples_per_front`, `coarse_step_s` sem alteração; sem arquivo intermediário | [REPO: `app/simulation/emt/probes.py:248-288`; teste `tests/test_emt_vcb_snubber.py:916-947`] |
| DM (ponte PL4 → perfil) | adaptador `AtpResults` → `extract_stress_events` | **Falta**; nenhum consumidor lê PL4 a partir de `RunResult.run_dir`. Continua necessária para conferir o motor dedicado contra o ATP fora do banco de regressão de EEE873 | [REPO: `anexos/repo/trt_transitorios_simulacao.md:28`] |
| DA/DM (carga do caso) | carregador `.atp` → `Circuit` do motor dedicado | **Falta**; o caso de A está codificado em Python, não lido do `.atp` | [REPO: `app/simulation/emt/cases/motor_switching.py:728-826`; §2.4] |
| DM (extração) | `extract_stress_events` | **Implementado**, 176 testes verdes | [REPO: `stress_profile.py:405`; teste `tests/test_pp_prognosis_core.py:170-311`] |
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
| `tests/test_pp_prognosis_core.py` | [C] | 16 classes de teste, 176 casos | Cobertura do núcleo, incluindo *guards* de arquitetura (`:1157` não importa GUI/plot; `:1174` não faz I/O) | `pytest` |

**Verificação de execução** [CÁLCULO PRÓPRIO]: `python3 -m pytest tests/test_pp_prognosis_core.py -q` → `176 passed` em ~0,2-0,3 s. A contagem de 176 é propriedade do repositório e reproduzível; o **tempo** é grandeza dependente de máquina e carga, citado apenas como ordem de grandeza [CÁLCULO PRÓPRIO, dependente de máquina].

### 2.2 Integrações pendentes com as convenções do repositório

| Arquivo | Ação | Símbolo | Responsabilidade | Dependência |
|---|---|---|---|---|
| `app/commercial/feature_gates.py` | [A] | `class Feature` (`:67-80`) e `FEATURE_TIER_MAP` (`:84-96`) | Acrescentar `RUL_PROGNOSIS = "rul_prognosis"` mapeado a `"commercial"` (alinhado aos três Monte Carlos, `:88-90`); decorar o ponto de entrada com `@requires_feature` | Nenhuma; tier ≥ `demo` é obrigatório sob o teste de hierarquia [REPO: `anexos/repo/convencoes_auditoria_gui_docs.md:E1`] |
| `app/gui/rul_prognosis_dialog.py` | [N] | `RulPrognosisDialog(QDialog)` | Diálogo modal com `QFormLayout`, *spin boxes* com `setRange/setValue/setSuffix`, rótulos citando norma, `QPlainTextEdit` de resultado, captura separada de `LicenseRequiredError` | `PySide6`; padrão de `app/gui/analysis_dialogs.py:78-284,661-797` |
| `app/gui/main_window.py` | [A] | bloco `analysis_menu` (`:442`), padrão `act_reliability` (`:529-533`), handler `_on_show_reliability` (`:3070`) | Ação `act_rul = analysis_menu.addAction("<emoji> Prognóstico de isolamento / RUL …", self._on_show_rul_prognosis)` + `setStatusTip` + handler `_on_show_rul_prognosis(self, *_qt_args)` com import *lazy* — **7ª garantia** | `rul_prognosis_dialog` |
| `app/gui/analysis_dialogs.py` | [A] (opcional) | `run_pipeline_report_export` (`:997`) | Segunda porta de entrada para exportação do laudo de RUL, coletando engenheiro/CREA/ART/notas (lacuna L3 do mapa de convenções) | `report_rul_html`, `report_rul_pdf` |
| `app/postprocessor/audit_trail.py` | [A] | `STANDARDS_CATALOG` (`:73-87`, hoje 13 normas), `KNOWN_LIMITATIONS` (`:338-382`, hoje 7 chaves) | Acrescentar as normas efetivamente citadas no código (IEC 60034-15:2009, IEC 60034-18-41:2014, IEC 60034-27-2/-3/-4, IEC 60071-1:2019, ABNT NBR 17094-3:2018, NEMA MG 1 Parte 31, ISO 13381-1:2015) e as 11 chaves `rul_*` já escritas em `prognosis/__init__.py:168-248`, **mais as 27 chaves `emt_*`** do motor dedicado (19 em `app/simulation/emt/__init__.py:311-446`, já incluídas as 7 `emt_jmarti_*` agregadas de `jmarti.py:2252-2313`, e 8 `emt_case_*` em `cases/motor_switching.py:956-1048`) | Nenhuma; `format_limitations_html` ignora chaves desconhecidas [REPO: `audit_trail.py:408-420`]. O prefixo `emt_` isola o *namespace*, e a agregação já verifica colisão e estoura em caso de choque [REPO: `app/simulation/emt/__init__.py:450-456`] |
| `app/postprocessor/report_rul_html.py` | [N] | `generate_rul_html_report`, `save_rul_html_report` | Laudo HTML no padrão `report_html.py`: bloco 1 = `make_audit_header(...).to_html()`, `citation()` por valor, penúltimo bloco = `format_limitations_html` | `audit_trail`, `prognosis`; **não** estender `generate_html_report` (`report_html.py:602`), que é tipado a `BusPipelineReport` |
| `app/postprocessor/report_rul_pdf.py` | [N] | `save_rul_pdf_report` | Laudo PDF espelhando `report_pdf.py:1054-1173`; reutilizar `_build_audit_cover_page` (`:127`) exige `report_kind` por *kwarg* opcional (hoje derivado de `report.bus_id`, `:171`) | `matplotlib` (já em `requirements.txt:3`) |
| `app/i18n/translations/en.json` e `es.json` | [A] | pares PT→EN e PT→ES | Toda string de UI nova (rótulo de menu, título do diálogo, rótulos de campo, botões, faixas do semáforo); paridade exata obrigatória | Hoje 133 chaves em cada arquivo [CÁLCULO PRÓPRIO: `json.load`] |
| `app/core/version.py` | [A] | `VERSION_TUPLE` (`:1959`), `PRE_RELEASE` (`:1960`), docstring de histórico | Bump `4.0.0-beta → 4.1.0-beta` com entrada de histórico; **manter** o sufixo `beta` (o teste de *readiness* exige prefixo `4.` e sufixo `alpha`/`beta`) | Testes de *readiness*/*milestone* |
| `CHANGELOG.md` | [A] | seção `## [4.1.0-beta]` (`:7-25` é o padrão) e "Standards cobertos (cumulativo)" (`:181-193`) | `### Added`/`### Changed` com contagem de testes; acrescentar as normas novas à lista cumulativa | `version.py` |
| `tests/test_pp_v4_1_0_rul_prognosis.py` | [N] | `TestGating`, `TestAuditIntegration`, `TestDialog`, `test_main_window_wires_rul_action` | Gate bloqueado em `educational` e liberado em `enterprise`; header e limitações presentes no HTML/PDF; diálogo sem `dlg.exec()`; *wiring* de menu por `inspect.getsource` | `tests/test_pp_prognosis_core.py` (já cobre o núcleo) |
| `.github/workflows/test.yml` | [A] | lista explícita do *job* `test` (`:66-78`) | Acrescentar `tests/test_pp_prognosis_core.py` e `tests/test_pp_v4_1_0_rul_prognosis.py` + `--cov=app.postprocessor.prognosis`; acrescentar também os **5 arquivos de teste do motor EMT** + `--cov=app.simulation.emt`. Atenção ao `--timeout=60` por teste já configurado (`:87`): a suíte do motor roda em ~63 s no total, mas nenhum teste isolado se aproxima do limite [CÁLCULO PRÓPRIO] | Nenhuma; o motor não importa PySide6 nem matplotlib e roda sem *display* |
| `app/preprocessor/atp_templates/vcb_reignition.mod` | [A] | bloco `DATA` (`:47-56`), recuperação dielétrica (`:115`) | Acrescentar `rrds_a`, `rrds_b` e um seletor de lei; manter `k_dielec = 17,0 V/µs` linear como **default atual** e a lei parabólica como **opção** | `vcb_model_emitter` |
| `app/preprocessor/vcb_model_emitter.py` | [A] | `VCB_REIGNITION_PROPS` (`:74-83`), `VCB3_REIGNITION_PROPS` (`:86-95`), `VCB_REIGNITION_DEFAULTS` (`:103-112`) | Acrescentar as propriedades **ao final** dos índices (10+ e 14+) para não deslocar o *layout* existente; nenhum default atual muda | Teste de integridade de mapeamento de propriedades |
| `app/analysis/transient_metrics.py` | [A] | `TrvMetrics` (`:29-38`), `compute_trv_metrics` (`:91-159`) | Acrescentar campos `Optional[...] = None`: `max_dvdt_kv_per_us` (derivada instantânea, distinta do `rrrv_kv_per_us` médio de `:131`) e `n_excursions_above` | Nenhuma; campos opcionais preservam chamadores |
| `app/postprocessor/trt_analyzer.py` | [A] | `TrtAnalysisReport` (`:168-204`), `analyze_trt` (`:372`) | Expor a contagem de excursões acima de um limiar configurável, ao lado de `rrrv_max_kV_per_us` (`:183`) — insumo direto de `n_reignitions` | `_compute_max_rrrv` (`:299`) já percorre a janela |
| `app/postprocessor/motor_starting.py` | [A] | `MotorStartingReport` (`:260-329`) | Expor `i2t_A2s` e `t_acc_s` como campos opcionais: `starting_time_s` já existe (`:295`, tempo até 95 % da rotação nominal, calculado em `:410`), mas **I²t não é calculado** — hoje o módulo apenas menciona a curva I²t em texto de *rationale* (`:540`) | `estimate_starting_time_s` (`:410`) |

### 2.3 Ressalva sobre a alteração do modelo de VCB

O `.mod` do repositório implementa recuperação dielétrica **linear**: `U_dielec_t := U0_dielec + k_dielec*(t - t_contact)*1e6`, com `k_dielec` default 17,0 V/µs [REPO: `app/preprocessor/atp_templates/vcb_reignition.mod:115,52`]. O Documento A usa lei **parabólica** de RRDS, $V_{wth}(t) = A\,t + B\,t^2$, com $A = 0{,}801$ kV·ms⁻¹ e $B = 1{,}226$ kV·ms⁻² [FATO: doc A, Tabela II, p. 3]. As duas físicas são incompatíveis entre si, e o repositório já contém, em outro artefato, a mesma forma quadrática usada por A: o validador exige parâmetro `RRDS*` e o arquivo de referência implementa `VWITHSTANDKV = RRDS_A·t_ms + RRDS_B·t_ms²` com `RRDS_A = 0,801` e `RRDS_B = 1,226` [REPO: `anexos/repo/vcb_reignicao_snubber.md:38,92,124,126`].

A recomendação arquitetural é **parametrizar a lei, não substituí-la**: acrescentar `rrds_a`/`rrds_b` e um seletor `dielectric_law ∈ {linear, quadratic}` cujo valor default permaneça `linear`, preservando bit a bit o comportamento atual dos casos existentes [INFERÊNCIA]. Sem isso, qualquer *fixture* de reprodução do Documento A produziria um perfil de estresse inconsistente com o artigo, e o risco R2 do mapa de convenções (duas físicas de disjuntor sem documento que as reconcilie) permaneceria aberto [REPO: `anexos/repo/vcb_reignicao_snubber.md:271`].

**Nota de estado.** No **motor dedicado** essa ressalva já está resolvida na direção recomendada: a lei de recuperação dielétrica é um `Protocol` com duas realizações, `ParabolicRecovery` (a de A) e `LinearRecovery` (a do `.mod`), escolhidas por parâmetro [REPO: `app/simulation/emt/vcb.py:200-292`]. A pendência remanescente é apenas no `.mod`/*emitter* do caminho ATP, que continua exclusivamente linear.

### 2.4 Pacote do motor EMT dedicado — o que já existe e o que falta

| Arquivo | Ação | Símbolo | Responsabilidade | Dependência |
|---|---|---|---|---|
| `app/simulation/emt/__init__.py` | [C] | `__all__` (`:216`), `KNOWN_LIMITATIONS` (`:311`, 19 chaves `emt_*`), agregação de `JMARTI_LIMITATIONS` com verificação de colisão (`:450-456`) | Fachada da API pública e catálogo local de limitações no padrão de `prognosis/__init__.py` | módulos do próprio pacote |
| `app/simulation/emt/components.py` | [C] | `Resistor`, `Inductor`, `Capacitor`, `VoltageSource`, `Switch`, `CoupledRL` | Modelos companheiros trapezoidais e de Euler regressivo, condições iniciais $i(0)$ **e** $v(0)$, estampas MNA, referência de fasor `sin`/`cos` | `numpy` (já em `requirements.txt:4`) |
| `app/simulation/emt/circuit.py` | [C] | `Circuit` (`:317`), `TimedSwitchController` (`:498`), `SolverResult` (`:622`), `Solver` (`:659`), `lu_factor`/`lu_solve` (`:223,261`) | Montagem MNA, fatoração por topologia com cache indexado por assinatura (LU própria com pivotamento parcial, aplicada pela inversa quando o condicionamento estimado permite), marcha no tempo, CDA por par de meios-passos, critério de comutação por margem `Imar` | `numpy` |
| `app/simulation/emt/steady_state.py` | [C] | `initialize_steady_state` (`:761`), `solve_phasor` (`:558`), `seed_from_phasor` (`:669`), `MultipleFrequenciesError` (`:187`), `UnsupportedComponentError` (`:196`) | Partida em regime permanente senoidal por solução fasorial — equivalente do `TSTART` negativo do cartão de fonte do ATP | `numpy` |
| `app/simulation/emt/line.py` | [C] | `BergeronLine` (`:283`), `_TravelHistory` (`:187`), `surge_impedance` (`:580`), `travel_time` (`:587`) | Linha/cabo a parâmetros constantes, perdas concentradas `R/4, R/2, R/4`, interpolação linear de histórico | `numpy` |
| `app/simulation/emt/jmarti.py` | [C] | `JMartiLine`, `ModalJMartiLine`, `JMARTI_LIMITATIONS` (`:2252`) | Linha/cabo dependente da frequência: ajuste racional por *vector fitting*, fase mínima de Bode para extrair $\tau$, convolução recursiva por polo, decomposição modal com matriz real e constante | `numpy` — **`scipy` não é usado** |
| `app/simulation/emt/vcb.py` | [C] | `VacuumCircuitBreakerModel` (`:356`), `ParabolicRecovery` (`:209`), `LinearRecovery` (`:257`), `VCBPoleResult` (`:293`), `three_phase_vcb` (`:941`) | VCB dinâmico: corte por margem de corrente, recuperação dielétrica parabólica ou linear, reignição, extinção de alta frequência, contagem de reignições — origem de $n_r$ no vetor $s_{m,j}$ | `components`, `circuit` |
| `app/simulation/emt/snubber.py` | [C] | `ThyristorSnubber` (`:184`), `SnubberBranch` (`:489`), `three_phase_snubber` (`:572`) | SCR antiparalelos com $R_s$, disparo por sobretensão, bloqueio no zero de corrente, energia por ramo | `components`, `circuit` |
| `app/simulation/emt/probes.py` | [C] | `Probe` (`:57`), `NodeVoltageProbe` (`:126`), `DifferentialVoltageProbe` (`:193`), **`to_stress_profile` (`:248`)** | Aquisição das séries e **ponte oficial** para o núcleo de prognóstico; converte V→kV e delega a `extract_stress_events` | `numpy`; importa `prognosis` **em função**, não em módulo (evita acoplamento de importação) |
| `app/simulation/emt/cases/motor_switching.py` | [C] | `MotorSwitchingCase` (`:728`), `MotorSwitchingModel` (`:644`), `DOC_A_TABLE_III` (`:149`), `CABLE_MODELS` (`:278`), `KNOWN_LIMITATIONS` (`:956`, 8 chaves `emt_case_*`) | Caso de manobra 1250 kW / 4,16 kV do Documento A montado em *dataclasses*; `trv_summary()` (`:702`) devolve pico com sinal e RRRV máxima por fase | pacote `emt` |
| `tests/test_emt_kernel.py`, `test_emt_steady_state.py`, `test_emt_jmarti.py`, `test_emt_vcb_snubber.py`, `test_emt_referencia_eee873.py` | [C] | 94 / 43 / 49 / 52 / 35 = **273 testes**, 6 007 linhas | Kernel contra fontes primárias; regime permanente; JMarti; VCB e *snubber*; **regressão dígito a dígito contra as Listas 01 e 02 de EEE873**, que são o banco validado contra o ATP | `pytest`, `numpy` |
| `app/simulation/emt/atp_loader.py` | **[N]** | `circuit_from_atp(path) -> Circuit` | Carregar o caso a partir do `.atp`, fechando a única lacuna que hoje separa "o `.atp` é a fonte da verdade" (declaração) de "o motor resolve o `.atp`" (execução) | *parser* `.atp` já existente na arquitetura declarada [REPO: `ARCHITECTURE_ATP_STUDIO.txt:12-14`] |
| `app/gui/emt_*` e `Feature.EMT_ENGINE` | **[N]** | — | O motor é hoje o **segundo** *backend* órfão do repositório: nenhum módulo fora de `app/simulation/emt/` o importa [CÁLCULO PRÓPRIO: `grep -rn "simulation.emt" app/` fora do pacote → vazio]. A 7ª garantia vale para ele tanto quanto para o pacote de prognóstico | GUI |

**Verificação de execução** [CÁLCULO PRÓPRIO, nesta sessão]: `python3 -m pytest tests/test_emt_kernel.py tests/test_emt_vcb_snubber.py tests/test_emt_steady_state.py tests/test_emt_jmarti.py tests/test_emt_referencia_eee873.py tests/test_pp_prognosis_core.py -q` → **449 testes verdes** em ~63 s (273 do motor + 176 do prognóstico). A contagem é propriedade do repositório e reproduzível; o tempo é dependente de máquina.

---

## 3. Contratos de dados entre camadas

### 3.1 Princípios

1. **Versionamento explícito.** Todo documento persistido carrega `schema_version` (SemVer). Mudança compatível (campo novo opcional) incrementa o *minor*; mudança que remove ou reinterpreta campo incrementa o *major*.
2. **Unidades no nome do campo.** O `AtpResults` do repositório não carrega metadado de unidade — volts × kV, A × kA são indistinguíveis [REPO: `anexos/repo/trt_transitorios_simulacao.md:46`]. O contrato do módulo de RUL corrige isso: todo campo numérico traz o sufixo de unidade, exatamente como já ocorre nos *dataclasses* (`V_pk_kV`, `T1_us`, `dvdt_kV_per_us`, `energy_J`, `theta_C`) [REPO: `stress_profile.py:146-155`].
3. **Rótulo de proveniência.** `StressEvent.source` e `StressProfile.label` já existem para isso [REPO: `stress_profile.py:156,248`].
4. **Auditoria antes da compressão.** O *hash* de proveniência é calculado sobre um **resumo determinístico** — parâmetros do caso, estatísticas por evento e, conforme a via de solução, o SHA-256 do arquivo `.pl4` (via ATP) ou a identificação de versão do módulo do caso mais os campos de configuração do solver do bloco `provenance` da §3.2 (motor dedicado) —, nunca sobre a série temporal bruta — `_to_jsonable` faz `repr` de objetos desconhecidos, o que tornaria o *hash* não determinístico entre versões do numpy [REPO: `audit_trail.py:164-191`; risco R6 em `anexos/repo/convencoes_auditoria_gui_docs.md`].

### 3.2 Contrato C1 — perfil de estresse (`rul_stress_profile.v1.json`)

Fronteira **DM → SD/HA**. Serialização direta de `StressProfile` [REPO: `stress_profile.py:228-382`].

```json
{
  "schema_version": "1.0.0",
  "kind": "rul_stress_profile",
  "label": "M-4160-01 / manobra de abertura sob partida",
  "provenance": {
    "solver": "olivas-emt | ATP/EMTP | campo",
    "source": "emt:v_motor_b",
    "atp_file_sha256": "<64 hex>",
    "pl4_file_sha256": "<64 hex ou null quando o solver é o motor dedicado>",
    "case_module_version": "app.simulation.emt.cases.motor_switching@<git sha>",
    "line_model": "bergeron | jmarti",
    "dielectric_law": "parabolic(A=0.801, B=1.226) | linear(k=17.0)",
    "cda": { "enabled": true, "full_steps": 2 },
    "init": "zero | steady_state",
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

**Campos acrescentados pela existência de duas vias de solução.** `solver` é obrigatório e distingue o motor dedicado do ATP externo — sem ele, dois perfis numericamente diferentes do mesmo caso ficariam indistinguíveis no laudo (risco RI, §7.5). `source` já é preenchido pelo adaptador com `"emt:<nome da sonda>"` [REPO: `app/simulation/emt/probes.py:283`]. Quando `solver == "olivas-emt"`, `pl4_file_sha256` é `null` — não existe arquivo intermediário — e o par (`case_module_version`, `atp_file_sha256`) responde pela identidade do caso; enquanto o carregador `.atp` não existir (§2.4), apenas `case_module_version` é preenchido, e isso deve aparecer no laudo, não ser omitido. `line_model`, `dielectric_law`, `cda` e `init` são registrados porque **cada um deles muda o número reportado**: a lei dielétrica decide se há interrupção (§5.1); o CDA desloca o pico de TRV (na Questão 2 da Lista 02, de 504,292 V sem CDA para 505,148 V com CDA, ambos entre o valor do ATP e o analítico de 506,170 V) [LISTA: 02, §3.7-3.8; CÁLCULO PRÓPRIO]; e `init` decide se a série começa em regime ou em repouso.

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

O caso **deve** carregar `calibration_warnings` materializadas no momento da execução, produzidas por `DamageModelParams.calibration_warnings()` [REPO: `damage_models.py:484-515`], para que o laudo não possa ser emitido sem elas.

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

O campo `is_lower_bound` é **estrutural**: quando `synergy_fn` é `None`, `D` é cota inferior de dano e cota superior de RUL, e o resumo textual já o declara [REPO: `damage_models.py:819-822,1054-1058`]. `contribution_pct` soma 100 % sobre os componentes disponíveis, e componentes indisponíveis aparecem com `available=false` em vez de serem omitidos — a ausência de dado é visível, não silenciosa [REPO: `health_index.py:501-547`; teste `tests/test_pp_prognosis_core.py:990`].

C4 é a série que alimenta o EKF, em CSV com cabeçalho versionado (`# schema_version=1.0.0; kind=rul_indicator_series`) e colunas `t_h,indicator,unit,source`. O estimador exige tempo **não decrescente** e ergue `ValueError` caso contrário [REPO: `rul_estimator.py:317-320`; teste `:882`].

### 3.5 Como o vetor de estresse é auditado

Três garantias, todas já suportadas pelo código:

1. **Validação de entrada na fronteira.** `StressEvent.__post_init__` rejeita pico nulo, $T_1 \le 0$, dv/dt negativo, energia negativa, $n_r < 1$ e temperatura $\le -273{,}15$ °C [REPO: `stress_profile.py:158-191`; testes `:113-140`]. Nenhum evento fisicamente impossível entra no acumulador.
2. **Rastro de qualidade de amostragem.** Os três avisos (passo grosseiro, frente subamostrada, violação de Nyquist com $f \approx 0{,}35/t_r$) viajam com o perfil e devem ser renderizados no laudo [REPO: `stress_profile.py:102,519-527,585-590,626-640`].
3. **Limitações no laudo.** As 11 chaves `rul_*` são carregadas por `format_limitations_html` uma vez copiadas para o catálogo global, sem risco de colisão graças ao prefixo de *namespace* [REPO: `prognosis/__init__.py:164-167`; `audit_trail.py:408-420`; teste `tests/test_pp_prognosis_core.py:1137`].

---

## 4. Realização das equações D1–D7 e (5.1)–(5.2) no código

### 4.1 Tabela de rastreabilidade equação → função → `arquivo:linha` → teste

A tabela abaixo mapeia **23 relações** — D1 a D5, D6 nas duas formas (a/b), D7 em três recortes ($N_j$, $1/N_j$ e fator térmico), (5.1) e suas duas parcelas, (5.2), ψ(D), γ(t), RUL determinística, RUL_N/RUL_t, EKF, RUL com intervalo, AHI, $T_1$ e eventos equivalentes — a **24 âncoras de teste distintas** em `tests/test_pp_prognosis_core.py`. Cada linha aponta função, `arquivo:linha` e ao menos um `def test_...` que trava o comportamento; nenhuma relação fica sem âncora [CÁLCULO PRÓPRIO: contagem das linhas da tabela e das âncoras `:NNN` citadas].

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
| **D7 (térmico)** | fator térmico multiplica o **dano**, não a capacidade | `supportable_events` (`thermal_expo`) | `damage_models.py:609-613` | `:550` fator multiplica o dano; `:563` $+20$ K com HIC = 10 K → dano $\times\,4{,}0$ |
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

**(a) Convenção de sinal térmico.** A forma impressa por Feilat, $\exp[-B(1/T - 1/T_0)]$, faria a vida **crescer** com a temperatura, o que é fisicamente incorreto [FATO: Etapa 1, §5.4, D5, "Nota de sinal"]. O código adota $c_T = 1/T_0 - 1/T$ e o teste `test_arrhenius_sign_convention_life_decreases_with_heat` trava essa escolha [REPO: `damage_models.py:261-293`; teste `:452`]. Em D7, o fator $2^{(\theta_0-\theta_j)/\mathrm{HIC}}$ multiplica $N_j$, logo $1/N_j \propto 2^{(\theta_j-\theta_0)/\mathrm{HIC}}$ — **o fator térmico multiplica o dano** [REPO: convenção declarada na docstring de `supportable_events`, `damage_models.py:546-547`, implementada em `:609-613`; Etapa 2, §3.1]. Com HIC = 10 K, $+20$ K multiplicam a taxa de dano por 4,0 [REPO: teste `:563`; limitação `rul_thermal_state_not_derived`, `prognosis/__init__.py:214-219`].

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

**F1 — reprodução de pico e RRRV.** *Fixture* `_ramp_waveform(peak_kV, slope_kV_per_us, dt_s)`: rampa linear até o pico da fase B (41,44 kV) com inclinação 15,05 kV/µs, seguida de cauda exponencial de 20 µs [REPO: `tests/test_pp_prognosis_core.py:63-88`]. A rampa linear é escolhida porque nela o dv/dt máximo é **exatamente** a inclinação, o que permite comparar a extração com um valor fechado [REPO: `tests/test_pp_prognosis_core.py:73-76`]. Com passo fino de 10 ns, `test_doc_a_table_iii_phase_b_peak_and_rrrv` recupera pico e dv/dt com `rel=1e-3` e `warnings == []` [REPO: testes `:171-183,195-201`]; `test_t1_matches_iec_60034_15_definition` confirma $T_1 = 1{,}67 \times 0{,}60 \times t_{rampa} = 2{,}759$ µs [REPO: teste `:185-193`]. **F1b — passo grosseiro (*fixture* A CRIAR)**: repetir a mesma *fixture* com o passo de **1 µs** efetivamente usado em A [FATO: doc A, Tabela II, p. 3]. Esse caso **ainda não está coberto**: os dois testes de passo grosseiro existentes usam 2 µs, não 1 µs [REPO: `tests/test_pp_prognosis_core.py:202-213` e `:215-225`, docstring em `:203` — "Passo de 2 µs > 1 µs ⇒ aviso"]. Eles são citados aqui apenas como evidência de que o **mecanismo** de aviso funciona. O limiar do código é `if dt >= coarse_step_s` com `DEFAULT_COARSE_STEP_S = 1,0e-6` [REPO: `stress_profile.py:87,520`], de modo que o passo de 1 µs de A dispararia o aviso. **Essa inferência deixou de ser inferência**: com o motor dedicado, o caso de A a $\Delta t = 1$ µs foi executado e o perfil da fase B veio com os **três** avisos simultâneos — passo grosseiro (Δt = 1 µs ≥ 1 µs, dv/dt como limite inferior), 23 excursões com $(t_{90}-t_{30}) < 5\Delta t$, e 1 excursão violando o critério de Nyquist da banda equivalente da frente —, sobre 124 eventos detectados acima de 2,5 kV [CÁLCULO PRÓPRIO, nesta sessão, sobre `MotorSwitchingCase` + `to_stress_profile`]. Falta apenas fixar isso como teste; o critério de aceite passa a ser a **presença** dos três avisos, e o dv/dt reportado deve ser tratado como limite inferior. Consequência para o vetor de estresse: **no passo de A, dv/dt e $T_1$ são cotas, não medidas** — o que atinge diretamente D3 e o fator $(t_f/t_{f0})^m$ de D7.

**F2 — mitigação atravessa o limiar de dano.** Com $V_{th}$ posicionado entre 13,65 e 41,44 kV, o evento "com *snubber*" da fase B deve produzir dano **exatamente** zero e o "sem *snubber*" dano positivo. O teste `test_mitigation_moves_event_below_threshold` já cobre a lógica [REPO: teste `:1120-1135`]. **Ressalva obrigatória**: isso valida a *mecânica* do limiar, **não** o valor de $V_{th}$, que é não calibrado.

**F3 — cadeia completa forma de onda → AHI.** `test_waveform_to_health_index` percorre `extract_stress_events` → `CombinedDamageAccumulator` → `AssetHealthIndex` [REPO: teste `:1099-1119`].

**F6 — cadeia completa *circuito* → AHI, sem forma de onda sintética.** Com o motor dedicado, F1–F3 deixam de ser o único caminho: `test_caso_alimenta_o_nucleo_de_prognostico_com_o_vetor_de_estresse` monta o caso de A, resolve, e entrega a sonda do terminal do motor a `to_stress_profile`, verificando que cada evento traz $V_{pk} \ge$ limiar, $T_1 \ge 0$, dv/dt $\ge 0$, energia $\ge 0$, $\theta$ propagado e $n_r \ge 1$, com passo de amostragem igual ao $\Delta t$ do solver [REPO: `tests/test_emt_vcb_snubber.py:916-947`]. É a primeira *fixture* da série em que a forma de onda é **resolvida**, e não construída para ter a resposta desejada.

**Benchmark contra a Tabela III — ABERTO.** É preciso separar duas coisas que o motor faz e uma que ele ainda não faz. (i) O **kernel** está validado contra referência externa: a suíte `tests/test_emt_referencia_eee873.py` reproduz, dígito a dígito, o banco das Listas 01 e 02 de EEE873, que o próprio autor já havia confrontado com o ATP — inclusive o pico de TRV de 504,292 V, valor que coincide entre a rotina do autor e o ATP, e os instantes de corte da Tabela 4 para $\Delta t$ = 4, 2, 1 e 0,5 µs [LISTA: 02, Questão 2, Tabelas 3 e 4; detalhamento em `05_MOTOR_EMT_DEDICADO.md`]. (ii) O **caso de A** executa, corta por polo, conta reignições e alimenta o prognóstico (F6). (iii) O que **não** ocorre é a reprodução dos números da Tabela III: com os parâmetros publicados de A (RRDS $A = 0{,}801$ kV/ms, $B = 1{,}226$ kV/ms², $\Delta t = 1$ µs) e a convenção física de $\mathrm{d}i/\mathrm{d}t$, nenhum polo alcança a primeira interrupção bem-sucedida — um passo após o corte a suportabilidade vale 0,801 V, a TRV já vale dezenas de volts, o *gap* reignita, e o pico registrado fica na casa de 0,1 kV contra os 41,44 kV da Tabela III [REPO: limitação `emt_case_doc_a_rrds_prevents_clearing`, `app/simulation/emt/cases/motor_switching.py:1016-1032`; CÁLCULO PRÓPRIO nesta sessão: caso padrão, 45 000 passos, picos de 0,0796 / 0,1010 / 0,1010 kV nas fases A/B/C]. Elevando $A$ a 200 kV/ms — uma ordem de grandeza acima da faixa publicada — há interrupção limpa e TRV de 6,6 a 7,1 kV, isto é, cerca de 2 pu, o valor clássico [REPO: teste `tests/test_emt_vcb_snubber.py:892-914`].

**Conclusão defensável, e apenas ela.** Daqui **não** se conclui que os 41,44 kV de A estão errados, nem que este motor os reproduz. Conclui-se que **a Tabela III não é reprodutível a partir do artigo isolado**, porque A omite dados de rede necessários [REPO: limitação `emt_case_undisclosed_network_data`, `cases/motor_switching.py:966-974`]. Soma-se a isso o fato de o caso partir deliberadamente do REPOUSO, e não do regime permanente: com $L/R = 13{,}0$ ms na variante da Fig. 2, os instantes de separação padrão (14 a 25 ms) deixam ainda 34 % de componente contínua em $t = 14$ ms, de modo que o valor absoluto do pico não é comparável ao de A sem antes fixar o estado de regime [REPO: limitação `emt_case_no_steady_state_start`, `cases/motor_switching.py:1033-1048`]. O caminho para fechar o *benchmark* é obter do autor o `.atp` do caso de A e o resultado de `CABLE CONSTANTS`/`LINE CONSTANTS` correspondente, e então (a) resolver o mesmo `.atp` pelas duas vias — motor dedicado e ATP externo — e (b) comparar pico e RRRV por fase, com e sem *snubber*, no mesmo critério de leitura de `trv_summary()`. Enquanto isso não ocorre, **nenhum número do caso de A produzido por este motor pode ser citado como reprodução do artigo**; ele vale como caso de exercício da cadeia, não como validação.

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

Versão corrente `4.0.0-beta` [REPO: `app/core/version.py:1959-1968`]; o `CHANGELOG.md` registra a `[4.0.0-beta]` de 2026-05-01 com i18n EN/ES em paridade 133/133 e "Master Protocol 8/8 garantias mantidas" [REPO: `CHANGELOG.md:7-23`]. O `ROADMAP.md` cobre o ciclo v0.94 → v1.0 e **não** contém linha de prognóstico/RUL [REPO: `ROADMAP.md:1-40`] — o módulo é, portanto, feature nova sem paridade PTW correspondente, a ser declarada como superação [REPO: `anexos/repo/convencoes_auditoria_gui_docs.md:L14`] O mesmo vale, com mais força, para o **motor EMT dedicado**: nenhuma ferramenta da linha PTW resolve transitórios eletromagnéticos, de modo que ele é superação por definição, e não paridade — o que também significa que não há referência de concorrente contra a qual conferi-lo, e a validação tem de vir da literatura primária e do ATP (§7.6).

### 6.2 MVP atual (entregue nesta sessão, **não** liberável)

| Entregue | Evidência |
|---|---|
| Pacote `app/postprocessor/prognosis/` — 4 módulos mais a fachada, 3 052 linhas (`__init__` 248, `stress_profile` 672, `damage_models` 1 060, `rul_estimator` 494, `health_index` 578) | [CÁLCULO PRÓPRIO: `wc -l`] |
| 176 testes verdes do prognóstico (tempo de suíte ~0,2-0,3 s, dependente de máquina) | [CÁLCULO PRÓPRIO: `pytest -q`] |
| Zero dependência nova (stdlib + `numpy`, já em `requirements.txt:4`) | [REPO: `rul_estimator.py` importa `numpy`; os demais módulos, apenas stdlib] |
| *Guards* de arquitetura: núcleo não importa GUI/plot nem faz I/O | [REPO: testes `:1157,1174`] |
| Pacote `app/simulation/emt/` — motor EMT dedicado, 9 módulos mais o pacote de casos, 9 915 linhas (`__init__` 457, `components` 1 259, `circuit` 1 207, `steady_state` 810, `line` 601, `jmarti` 2 349, `vcb` 1 115, `snubber` 684, `probes` 310, `cases/` 1 123) | [CÁLCULO PRÓPRIO: `wc -l`] |
| 273 testes verdes do motor, 6 007 linhas de teste; total da sessão **449 testes** em ~63 s | [CÁLCULO PRÓPRIO: `pytest -q` sobre os 6 arquivos, nesta sessão] |
| Regressão contra referência externa: Listas 01 e 02 de EEE873 reproduzidas dígito a dígito, incluindo o pico de TRV de 504,292 V que coincide entre a rotina do autor e o ATP | [LISTA: 02, Tabelas 3 e 4; REPO: `tests/test_emt_referencia_eee873.py`; `05_MOTOR_EMT_DEDICADO.md`] |
| Ponte simulação → prognóstico fechada **em memória**, sem arquivo intermediário | [REPO: `app/simulation/emt/probes.py:248-288`; teste `tests/test_emt_vcb_snubber.py:916-947`] |
| Zero dependência nova também no motor: apenas `numpy`; **`scipy` não foi adicionado** | [CÁLCULO PRÓPRIO: `requirements.txt` inalterado; nenhum `import scipy` no pacote] |
| Caminho do ATP preservado: `app/simulation/runner.py` **não foi tocado** | [CÁLCULO PRÓPRIO: `git status` — o arquivo não consta entre os modificados] |

### 6.3 v4.1.0-beta — "RUL Sprint 1: integração mínima liberável"

Escopo: E1 (`Feature.RUL_PROGNOSIS`), E2/E3 (`KNOWN_LIMITATIONS` + `STANDARDS_CATALOG`), E6/E8 (menu + `RulPrognosisDialog`), E12 (i18n EN/ES), E13/E14 (`version.py` + `CHANGELOG.md`), E17 (`tests/test_pp_v4_1_0_rul_prognosis.py`), E18 (subset CI).

Confronto com os **oito critérios de aceite de release** [REPO: `docs/PTW_TOTAL_PARITY_DIRECTIVE.md:128-142`]:

| # | Critério | Estado após v4.1.0 |
|---|---|---|
| 1 | TodoWrite completo das features endereçadas | A fazer no sprint |
| 2 | Cada feature cita seção+página **do manual** em docstring [REPO: `docs/PTW_TOTAL_PARITY_DIRECTIVE.md:133`] | **Reinterpretado, não atendido na letra**: não há feature PTW correspondente (ver critério 3), logo não há seção+página de manual a citar. As docstrings do núcleo citam **norma + cláusula** e seção das Etapas 1/2 [REPO: `prognosis/__init__.py:39-65`; `stress_profile.py:20-31`]. Exige **aceite explícito do revisor de release** para valer como equivalente |
| 3 | Entrada na `PTW_SURPASSING_MATRIX.md` com ≥ 1 dimensão de superação | A fazer — declarar como superação (não há feature PTW de RUL) |
| 4 | Testes próprios cobrem ≥ 80 % do módulo novo (≥ 5 testes) [REPO: `docs/PTW_TOTAL_PARITY_DIRECTIVE.md:135`] | **Parcialmente atendido**: 449 testes entre prognóstico e motor (≫ 5), mas a cobertura ≥ 80 % **NÃO É MEDIDA** — `pytest-cov`/`coverage` ausentes no ambiente e `app.postprocessor.prognosis` fora da lista `--cov` do CI [REPO: `.github/workflows/test.yml:79-84`; §7.4 deste documento] |
| 5 | *Sweep* *targeted* verde | A fazer |
| 6 | *Restore point* criado | A fazer (local, *gitignored*) |
| 7 | *Handoff doc* + `SESSION_HANDOFF` atualizados | A fazer |
| 8 | *Smoke test* reproduzindo exemplo do tutorial | A fazer — "Para usar RUL, o usuário clica em Análise → Prognóstico de isolamento / RUL" |

**Situação verificável hoje: 1/8** — apenas a metade "≥ 5 testes" do critério 4 é demonstrável por execução, e nenhum dos oito critérios está integralmente satisfeito. **Bloqueadores para fechar a release**: critérios 1, 3, 5, 6, 7 e 8 (processo/integração, nenhum de núcleo computacional), mais a metade não medida do critério 4 (instalar `pytest-cov` e acrescentar `--cov=app.postprocessor.prognosis` ao *job* de CI, §7.4) e o aceite explícito do revisor quanto à reinterpretação do critério 2. O critério 8 é o que materializa a 7ª garantia.

### 6.4 v4.2.0 — "RUL Sprint 2: laudo, cadeia ATP e métricas de prognóstico"

| Item | Entrega |
|---|---|
| `report_rul_html.py` / `report_rul_pdf.py` | Laudo com header auditável, `citation()` por valor e bloco de limitações |
| Adaptador `AtpResults` → `extract_stress_events` | Fecha a lacuna DM da **via alternativa**: leitura do PL4 a partir de `RunResult.run_dir`. Segue necessário mesmo com o motor dedicado, porque é ele que permite confrontar as duas vias sobre o mesmo `.atp` |
| `app/simulation/emt/atp_loader.py` — `circuit_from_atp` | Fecha a lacuna DA do **caminho principal**: hoje o caso de A é *dataclass* Python, não leitura do `.atp`. Sem isso, "o `.atp` é a fonte da verdade" permanece declaração de arquitetura, não prática executada |
| Gate, diálogo e ação de menu do motor EMT | Retira o motor da condição de *backend* órfão (7ª garantia), do mesmo modo que o Sprint 1 faz pelo pacote de prognóstico |
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
| Fechamento do *benchmark* contra a Tabela III de A | Obter o `.atp` do caso e o `CABLE CONSTANTS` correspondente; resolver pelas duas vias e comparar pico e RRRV por fase (§5.1). Enquanto não fechado, o caso vale como exercício da cadeia, não como validação |

**Nota.** No motor dedicado, a lei parabólica de RRDS **já é uma das duas realizações do `Protocol` de recuperação dielétrica** [REPO: `app/simulation/emt/vcb.py:209-292`]; o item acima diz respeito ao `.mod` e ao *emitter* do caminho ATP, que continuam exclusivamente lineares.

### 6.6 Roadmap do motor dedicado e o critério objetivo de migração do laço para C++

**Ordem de dependência.** (1) `atp_loader` (§2.4), sem o qual o `.atp` não é resolvido pelo motor; (2) gate + diálogo + ação de menu, que retiram o motor da condição de *backend* órfão; (3) fechamento do *benchmark* contra A (§5.1); (4) tabelas de `CABLE CONSTANTS` reais alimentando o modelo JMarti, hoje geradas de um $R'L'C'$ com $R'$ constante; (5) **só então** a questão do C++.

**Por que a migração não é decidida agora.** A API do motor é a fronteira estável: `Circuit`/`Solver` recebem componentes e devolvem `SolverResult`, e o laço de marcha no tempo — montagem do vetor de correntes históricas, resolução do sistema já fatorado e `commit()` dos ramos — está isolado em `Solver.run` [REPO: `app/simulation/emt/circuit.py:659`]. Reescrever esse laço em C++ atrás da mesma assinatura é mudança de implementação, não de arquitetura, e por isso pode ser **adiada sem custo de retrabalho** — o que não pode ser adiado é a validação, que é o que confere significado a qualquer ganho de velocidade.

**Medida de referência** [CÁLCULO PRÓPRIO, nesta sessão, máquina única, sem paralelismo]: o caso do Documento A, com $\Delta t = 1$ µs e janela de 45 ms, executa **45 000 passos em 2,37 s** sobre um sistema MNA de **dimensão 27**, isto é, **≈ 53 µs por passo**. Extrapolando para o volume que justifica o motor próprio — 10³ a 10⁴ execuções —, obtêm-se **40 min a 6,6 h** de núcleo único; com 8 processos, **5 min a 50 min**. Ordens de grandeza dependentes de máquina, citadas como base de decisão, não como especificação.

**Critério objetivo de migração.** A reescrita do laço em C++ só é aberta quando **todas** as quatro condições abaixo forem verdadeiras ao mesmo tempo:

| # | Condição | Verificação |
|---|---|---|
| C1 | O *benchmark* contra referência externa está **fechado**, e existe um conjunto de casos-ouro com tolerância numérica declarada que a implementação em C++ terá de reproduzir dígito a dígito | Hoje: **parcialmente satisfeito** — o banco de EEE873 existe e é reproduzido; o de A está aberto (§5.1) |
| C2 | O estudo em escala está **especificado** — número de execuções, dimensão do sistema e janela — e o tempo total projetado em Python, já com paralelismo por processo, excede o orçamento aceito para uma rodada de estudo | Hoje: **não satisfeito** — nem o número de execuções nem o orçamento estão fixados |
| C3 | O laço interno é comprovadamente o gargalo, medido por perfilagem, e não a montagem, a fatoração ou a extração de eventos | Hoje: **indiciado, não perfilado**. Confronto de duas medições independentes: a resolução do sistema já fatorado custa 1,24 µs em dimensão 32 [CÁLCULO PRÓPRIO registrado em `05_MOTOR_EMT_DEDICADO.md`, §2.6], contra os ≈ 53 µs por passo do caso completo em dimensão 27 — a álgebra linear responde por algo da ordem de 2 % do passo, e os outros 98 % estão na montagem do vetor de históricos, no `commit()` dos ramos e nos controladores. É indício forte de que o alvo do C++ seria o laço, mas ainda **falta a perfilagem que o comprove** |
| C4 | As alternativas em Python foram esgotadas — vetorização de sondas, redução da dimensão, paralelismo por processo sobre o Monte Carlo, e passo adaptativo por trecho — e o ganho residual projetado do C++ é de pelo menos uma ordem de grandeza | Hoje: **não satisfeito**; o paralelismo por processo é trivial neste problema, porque as execuções são independentes |

**Contrato da migração, se e quando ocorrer.** (i) A API pública do pacote não muda; o C++ entra como implementação alternativa do laço, selecionável, com a implementação em Python **mantida** como referência executável. (ii) A suíte de 273 testes roda contra as duas implementações, e a divergência admitida é a da tolerância declarada em C1, não "resultados parecidos". (iii) A dependência de compilação nativa entra no `Dockerfile` e no empacotamento — arquivos da lista travada —, o que por si só exige decisão de projeto separada e não pode ser tratado como detalhe de otimização.

---

## 7. Riscos técnicos e impacto

### 7.1 Risco dominante: ausência de curva de vida calibrada

O risco de maior magnitude não é de engenharia de software: é que **nenhum valor de $n$ para mica-epóxi pré-formada de MT sob impulsos de VCB foi localizado na literatura acessada**, e que a vida em manobras varia por fator 6,6 ao mover $n$ de 4 para 9 [REPO: `prognosis/__init__.py:169-177`; Etapa 1, §5.4, D1]. Consequência arquitetural já implementada: `DamageModelParams.calibration_warnings()` **sempre** devolve ao menos uma advertência, independentemente da parametrização, e o `summary()` do acumulador a anexa [REPO: `damage_models.py:484-515,1059`; teste `:605`]. Consequência de produto: nenhum número absoluto de RUL pode ser publicado; o uso defensável do MVP é **comparativo** (com *snubber* × sem *snubber*, solução A de corte × solução B), no qual os parâmetros não calibrados se cancelam parcialmente na razão [INFERÊNCIA].

### 7.2 Desempenho

| Aspecto | Medida / estimativa | Evidência |
|---|---|---|
| Suíte do núcleo de prognóstico | 176 testes em ~0,2-0,3 s | [CÁLCULO PRÓPRIO, dependente de máquina e carga] |
| `extract_stress_events` | uma passada sobre a série para detectar excursões, mais uma busca retroativa por excursão; complexidade $O(N)$ no número de amostras, com constante pequena | [REPO: `stress_profile.py:529-540,556-575`] |
| Janela do Documento A | 45 ms a passo de 1 µs = 45 000 amostras por variável [FATO: doc A, Tabela II, p. 3] — irrelevante para o custo | [CÁLCULO PRÓPRIO] |
| EKF | matrizes 3×3 em numpy; custo por atualização constante | [REPO: `rul_estimator.py:325-355`] |
| Ponto de atenção | listas Python nativas em `results_reader` (`float32` → `list[float]`), o que multiplica o custo de memória para varreduras longas | [REPO: `anexos/repo/trt_transitorios_simulacao.md:45`] |
| **Motor EMT dedicado — caso de A** | 45 000 passos ($\Delta t = 1$ µs, janela de 45 ms) sobre sistema MNA de dimensão 27 em **2,37 s**, isto é, **≈ 53 µs por passo** | [CÁLCULO PRÓPRIO, nesta sessão; dependente de máquina] |
| **Motor EMT — projeção do estudo em escala** | 10³ a 10⁴ execuções ⇒ 40 min a 6,6 h em núcleo único; 5 min a 50 min com 8 processos. É esta a base do critério C2 de migração para C++ (§6.6), e não uma medida de gargalo | [CÁLCULO PRÓPRIO, extrapolação linear da linha anterior] |
| **Motor EMT — fatoração LU** | Reaproveitada por cache indexado por assinatura de topologia, e não refeita a cada passo — é o que torna o laço interno, e não a álgebra, o candidato a gargalo (condição C3 da §6.6) | [REPO: `app/simulation/emt/circuit.py:278-316`; limitação `emt_dense_lu_no_sparsity`] |
| **Suíte do motor** | 273 testes em ~63 s, dominados pelos casos de 45 000 passos e pela regressão de EEE873 em quatro passos de integração | [CÁLCULO PRÓPRIO, dependente de máquina] |

### 7.3 Dependências novas

**Nenhuma, nos dois pacotes.** `stress_profile.py`, `damage_models.py` e `health_index.py` usam apenas a biblioteca padrão; `rul_estimator.py` usa `numpy`, já declarado [REPO: `requirements.txt:4`]. O motor EMT dedicado usa **exclusivamente `numpy`**: `requirements.txt` não foi alterado, e **`scipy` não foi adicionado** — decisão que teve consequência de projeto concreta, pois obrigou a escrever em `numpy.linalg` a fatoração LU com pivotamento (`circuit.py:223-276`) e o ajuste racional por *vector fitting* do modelo JMarti, em vez de recorrer a `scipy.linalg`/`scipy.signal` [CÁLCULO PRÓPRIO: nenhum `import scipy` no pacote]. Isso evita o risco R4 do mapa de convenções (dependência nova quebra o *job* `imports`, que instala apenas `numpy`, `pydantic` e `PyYAML`, incha o PyInstaller e o Docker e exige `THIRD_PARTY_NOTICES`/`LICENSING` e o `Dockerfile`, que está na lista travada) [REPO: `anexos/repo/convencoes_auditoria_gui_docs.md:R4`]. O intervalo de confiança usa `statistics.NormalDist` da *stdlib* em vez de `scipy` [REPO: `rul_estimator.py:75` (import), `:447` (`NormalDist().inv_cdf(0.5 + confidence / 2.0)`)].

### 7.4 *Subset* de CI

O *job* de teste do CI público roda uma **lista fixa de 12 arquivos**, porque o *sweep* completo inclui testes legados que abrem `QDialog` modal e travam em ambiente *headless* [REPO: `.github/workflows/test.yml:50-78`]. Consequência direta: **nem `tests/test_pp_prognosis_core.py` nem os 5 arquivos de teste do motor EMT rodam no CI hoje** — 449 testes verdes nesta sessão que o CI público não exercita — e sua cobertura não é medida. O módulo também **não** consta da lista `--cov` do *job* [REPO: `.github/workflows/test.yml:79-84`], e no ambiente desta sessão `pytest-cov`/`coverage` não estão instalados (`python -m pytest --cov …` → *unrecognized arguments*; `import coverage` → `ModuleNotFoundError`) [CÁLCULO PRÓPRIO]. Por isso o critério 4 de release é declarado **parcialmente atendido** na §6.3: a metade "≥ 5 testes" é demonstrada, a metade "≥ 80 % de cobertura" **não é medida em lugar nenhum**. Mitigação obrigatória no Sprint 1: instalar `pytest-cov` no ambiente de CI, acrescentar os **6 arquivos** à lista de testes e `--cov=app.postprocessor.prognosis --cov=app.simulation.emt` ao comando. Nem o núcleo de prognóstico nem o motor EMT importam PySide6 ou matplotlib, de modo que ambos rodam sem *display* [REPO: teste `tests/test_pp_prognosis_core.py:1157`; CÁLCULO PRÓPRIO: nenhuma ocorrência de `PySide6`/`matplotlib` em `app/simulation/emt/`]. Atenção ao `--timeout=60` por teste (`:87`): a suíte do motor leva ~63 s no agregado, mas nenhum teste isolado se aproxima do limite.

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
| RH | **Segundo *backend* órfão**: o motor EMT não é importado por nenhum módulo fora de `app/simulation/emt/`, o que reproduz para ele a mesma violação da 7ª garantia que motiva o Sprint 1 | Alto, processual | Tratar motor e prognóstico no mesmo sprint de integração, com uma ação de menu cada, ou uma única ação que encadeie os dois (§6.4) [CÁLCULO PRÓPRIO: `grep -rn "simulation.emt" app/` fora do pacote → vazio] |
| RI | **Motor próprio percebido como substituto do ATP**: um revisor pode ler "motor dedicado" como abandono do `.atp` e da conferência contra terceiro | Alto, de comunicação e de aceitação acadêmica | O `.atp` permanece a fonte da verdade do caso e o `AtpRunner` permanece íntegro e não tocado (§1.2); o laudo deve nomear a via de solução usada em cada perfil, campo `provenance.source` do contrato C1 (§3.2), com `"emt:<sonda>"` para o motor próprio [REPO: `app/simulation/emt/probes.py:283`] |
| RJ | **Validação circular**: usar o próprio motor para gerar a verdade-terreno que o valida | Alto, metodológico | A regressão é contra referência **externa** — as Listas 01 e 02 de EEE873, previamente confrontadas com o ATP pelo autor —, não contra saídas do próprio motor (§7.6) |
| RK | O motor não roda no CI: os 5 arquivos de teste não constam da lista fixa do *job* `test`, tal como `tests/test_pp_prognosis_core.py` | Médio | Acrescentar os 6 arquivos e `--cov=app.simulation.emt`, observando o `--timeout=60` por teste (§2.2, §7.4) |
| RL | **Duas físicas de VCB agora em três lugares**: parabólica e linear no motor dedicado (`vcb.py`), apenas linear no `.mod`, e parabólica no artefato de referência. Divergência silenciosa entre a via do motor e a via do ATP para o *mesmo* caso | Médio, de reprodutibilidade | Parametrizar o `.mod` (§2.3) e exigir que o laudo registre a lei e os coeficientes efetivamente usados, qualquer que seja a via |

### 7.6 Estado da validação do motor próprio: o que está fechado e o que está aberto

Um motor de física próprio só reduz risco se a sua validação for **externa**. O quadro, sem arredondar para cima:

| Frente | Estado | Referência externa | Evidência |
|---|---|---|---|
| Modelos companheiros de $R$, $L$, $C$, fonte, chave e ramo RL acoplado | **Fechado**, conferido equação a equação | Dommel 1969, eqs. (9a)/(9b), (10a)/(10b), (11), (17a)/(17b) e Apêndice I; Ho *et al.* 1975, eq. (2) e Tabela I | [REPO: `app/simulation/emt/components.py`; `05_MOTOR_EMT_DEDICADO.md`, §2] |
| Procedimento CDA (par de meios-passos de Euler regressivo) | **Fechado** | Lin & Martí 1990, §2, p. 394, itens 1-6 | [REPO: `app/simulation/emt/circuit.py`; `05_MOTOR_EMT_DEDICADO.md`, §3] |
| Linha a parâmetros constantes (Bergeron) | **Fechado** no limite sem perdas | Dommel 1969, eqs. (4)-(6), (7a)/(7b), p. 389 | [REPO: `app/simulation/emt/line.py`] |
| Solução numérica ponta a ponta, contra o **ATP** | **Fechado sobre o banco de EEE873**: regime permanente fasorial, instantes de corte por margem $I_{mar}$, pico de TRV e oscilação numérica de período $2\Delta t$ reproduzidos dígito a dígito, inclusive o pico de 504,292 V comum à rotina do autor e ao ATP | Listas 01 e 02 de EEE873, previamente confrontadas com o ATP pelo autor | [LISTA: 01, Tabelas 2 e 3; LISTA: 02, Tabelas 1 a 4; REPO: `tests/test_emt_referencia_eee873.py`, 35 testes] |
| Caso de manobra do **Documento A** (Tabela III) | **ABERTO** — o caso executa e alimenta a cadeia, mas os picos publicados não são reproduzidos com os parâmetros do artigo; A omite dados de rede necessários | Documento A, Tabela III, p. 3 | [REPO: limitações `emt_case_doc_a_rrds_prevents_clearing` e `emt_case_undisclosed_network_data`; §5.1] |
| Modelo dependente da frequência (JMarti) | **ABERTO quanto à fonte primária**: o texto integral de Martí 1982 não foi acessado; a formulação foi montada de fontes secundárias registradas, e o limite sem perdas foi conferido contra Dommel 1969 | Martí 1982 — [INSERIR CITAÇÃO: equações e páginas] | [REPO: `app/simulation/emt/jmarti.py`; limitação `emt_jmarti_hybrid_recursion`, que declara a recursão adotada como escolha própria **não publicada**] |
| Tabelas de $Z_c(\omega)$ e $A(\omega)$ do cabo do caso | **ABERTO** — hoje geradas de um $R'L'C'$ com $R'$ constante, sem efeito pelicular nem retorno pela terra; devem vir do `CABLE CONSTANTS` do caso ATP | — | [REPO: limitação `emt_jmarti_fit_is_the_model`] |

**Leitura correta deste quadro.** O que está fechado é o **método numérico**: dadas as equações de rede, o motor as integra como o ATP integra, dentro das tolerâncias medidas pelo autor (4,27·10⁻⁴ V em tensão e 4,83·10⁻⁷ A em corrente na comparação rotina × ATP da Lista 02). O que está aberto é o **modelo do caso industrial**: quais são os parâmetros de rede do Documento A e quais tabelas de cabo descrevem a instalação. São problemas de natureza distinta, e confundi-los nos dois sentidos é erro — nem o banco de EEE873 valida o caso de A, nem o *benchmark* aberto de A invalida o kernel.

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

**As 27 chaves do motor dedicado.** O motor mantém catálogo próprio, no mesmo padrão e com prefixo `emt_` para isolar o *namespace* no laudo: 19 chaves em `app/simulation/emt/__init__.py:311-446` — já incluídas as 7 `emt_jmarti_*` agregadas de `jmarti.py:2252-2313` com verificação de colisão que estoura em caso de choque [REPO: `__init__.py:450-456`] — e mais 8 chaves `emt_case_*` do caso do Documento A em `cases/motor_switching.py:956-1048`. As de maior consequência para o vetor de estresse são quatro: `emt_switching_quantized_to_step` (o instante de comutação é quantizado em $\Delta t$, o que desloca o pico de TRV — a Lista 02 mede o efeito, de 501,37 V em 4 µs a 505,84 V em 0,25 µs contra 506,170 V analítico); `emt_jmarti_fit_is_the_model` (o que se simula é o **ajuste** de $Z_c(\omega)$ e $A(\omega)$, e o erro de ajuste é erro de modelo, não reduzível por refino de $\Delta t$); `emt_jmarti_hybrid_recursion` (a recursão por polo adotada é escolha própria, **não publicada**, feita para compatibilidade com o CDA, e deve ser declarada no laudo); e `emt_case_doc_a_rrds_prevents_clearing` (o *benchmark* aberto da §5.1). O catálogo completo, chave a chave, é objeto de `05_MOTOR_EMT_DEDICADO.md`. Somadas às 11 chaves `rul_*`, são **38 limitações declaradas** a copiar para o `KNOWN_LIMITATIONS` global do laudo (§2.2).

### 8.2 O que **não** foi implementado

| Item | Estado |
|---|---|
| `Feature.RUL_PROGNOSIS` e gate `@requires_feature` | Não existe [REPO: `app/commercial/feature_gates.py:67-96`] |
| Ação no menu Análise e `RulPrognosisDialog` | Não existem — **7ª garantia em aberto** |
| Chaves `rul_*` no `KNOWN_LIMITATIONS` global e normas no `STANDARDS_CATALOG` | Não copiadas; hoje 7 chaves e 13 normas [REPO: `audit_trail.py:73-87,338-382`] |
| Laudo HTML/PDF de RUL | Não existe |
| Strings i18n EN/ES do módulo | Não existem |
| Entrada em `CHANGELOG.md` e bump de `version.py` | Não feitos |
| Adaptador PL4 → perfil de estresse (via ATP) | Não existe. **A ponte equivalente do motor dedicado existe**: `probes.to_stress_profile` [REPO: `app/simulation/emt/probes.py:248-288`] |
| Carregador `.atp` → circuito do motor dedicado | Não existe; o caso de A é *dataclass* Python (§2.4) |
| Gate, diálogo e ação de menu do motor EMT | Não existem — **7ª garantia em aberto também para o motor** (risco RH) |
| Reprodução da Tabela III do Documento A pelo motor | Não obtida com os parâmetros publicados; *benchmark* declarado **aberto** (§5.1, §7.6) |
| Tabelas de cabo vindas do `CABLE CONSTANTS` do caso ATP | Não existem; o JMarti é alimentado por $R'L'C'$ com $R'$ constante |
| Laço interno do motor em C++ | Não existe e não está autorizado — a migração depende das quatro condições C1-C4 da §6.6, nenhuma delas integralmente satisfeita hoje |
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
| L-N5 | Texto integral de **Martí 1982** não acessado; o modelo de linha dependente da frequência foi montado a partir de fontes secundárias registradas e conferido, no limite sem perdas, contra Dommel 1969 | Quatro pontos do módulo `jmarti.py` mantêm [INSERIR CITAÇÃO] para equação e página (formulação $F = 2v - B$, relação de Bode para o atraso, matriz modal constante, sequência do ajuste). Nada foi atribuído ao artigo sem lastro em fonte efetivamente acessada |

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

**Fontes primárias do motor de transitórios dedicado**

Conferidas equação a equação contra a implementação; a correspondência item a item está nas docstrings dos módulos e é detalhada em `docs/research/rul_isolamento/05_MOTOR_EMT_DEDICADO.md`.

DOMMEL, H. W. Digital computer solution of electromagnetic transients in single- and multiphase networks. **IEEE Transactions on Power Apparatus and Systems**, v. PAS-88, n. 4, p. 388-399, abr. 1969. DOI 10.1109/TPAS.1969.292459. — Eqs. (4)-(6), (7a)/(7b), (9a)/(9b), (10a)/(10b), (11), (17a)/(17b); "Approximation of Series Resistance of Lines", p. 390; "Accuracy", p. 391; Apêndice I, p. 395.

DOMMEL, H. W. Nonlinear and time-varying elements in digital simulation of electromagnetic transients. **IEEE Transactions on Power Apparatus and Systems**, v. PAS-90, p. 2561-2567, 1971. — §III e §V (elementos variantes no tempo e chaves).

HO, C.-W.; RUEHLI, A. E.; BRENNAN, P. A. The modified nodal approach to network analysis. **IEEE Transactions on Circuits and Systems**, v. CAS-22, n. 6, p. 504-509, jun. 1975. — Eq. (2) e Tabela I (estampas).

LIN, J.; MARTÍ, J. R. Implementation of the CDA procedure in the EMTP. **IEEE Transactions on Power Systems**, v. 5, n. 2, p. 394-402, maio 1990. — §2, p. 394, procedimento em seis itens; eqs. (2)-(4) e Apêndice (A.3), (A.5), (A.6).

MAHSEREDJIAN, J.; DENNETIÈRE, S.; DUBÉ, L.; KHODABAKHCHIAN, B.; GÉRIN-LAJOIE, L. On a new approach for the simulation of transients in power systems. **Electric Power Systems Research**, v. 77, p. 1514-1520, 2007. — §2, eq. (2) (sistema de posto fixo).

MARTÍ, J. R. Accurate modelling of frequency-dependent transmission lines in electromagnetic transient simulations. 1982. — **Texto integral NÃO acessado nesta sessão** (lacuna L-N5); [INSERIR CITAÇÃO: veículo, volume, páginas, DOI, equações e páginas].

**Trabalhos do próprio autor — caso de referência validado contra o ATP**

AUTOR DESTE ESTUDO. **Lista 01 — EEE873 Análise de Redes Elétricas no Domínio do Tempo** (prof. Alberto de Conti, PPGEE/UFMG). Modelos numéricos de indutor e capacitor (trapezoidal e Euler regressiva), solução por Laplace do Exemplo A, ordem de convergência; código MATLAB e arquivo `.atp`. §1.1, §1.2, §2.1, §2.2, §4.3, §6.2, Tabelas 1 a 3. [Trabalho de disciplina; INSERIR CITAÇÃO: autoria por extenso e data de entrega].

AUTOR DESTE ESTUDO. **Lista 02 — EEE873 Análise de Redes Elétricas no Domínio do Tempo** (prof. Alberto de Conti, PPGEE/UFMG). MNA e modelagem de chaves; Questão 1 (curto-circuito em carga RL) e Questão 2 (abertura de disjuntor a vácuo alimentando reator, corte por margem $I_{mar}$). §1.2, §1.3, §1.4, §2.7, §3.3, §3.6, §3.7, §3.8; Tabelas 1 a 4. [Trabalho de disciplina; INSERIR CITAÇÃO: autoria por extenso e data de entrega].

**Literatura**

CIGRE WORKING GROUP D1.43. **Technical Brochure 703** — Dielectric performance of insulation systems fed by fast pulses. p. 29 (Fig. 31), Figs. 24 e 33, p. 35-36. Paris: CIGRE.

FEILAT, E. A. Lifetime estimation of insulation systems. *IntechOpen*, 2018. Equações (21), (26), (27) e (29). DOI 10.5772/intechopen.72423. Disponível em: https://doi.org/10.5772/intechopen.72423.

GUPTA, B. K.; LLOYD, B. A.; SHARMA, D. K. Degradation of turn insulation in motor coils under repetitive surges. *IEEE Transactions on Energy Conversion*, v. 5, n. 2, p. 320-326, 1990. DOI 10.1109/60.107228. Disponível em: https://doi.org/10.1109/60.107228.

JENSEN, W. R.; STRANGAS, E. G.; FOSTER, S. N. Prognostics of stator insulation using an extended Kalman filter. 2018. Equações (1)-(8). [Fichamento interno: artigo 02; INSERIR CITAÇÃO completa: veículo, volume, páginas, DOI].

MA, K. *et al.* Mission-profile-based lifetime prediction of power devices. *IEEE Transactions on Power Electronics*, v. 30, n. 2, 2015. Equações (1)-(3), p. 5, 7. [Fichamento interno: artigo 12].

THEOFANOUS, N. *et al.* Thermal ageing of insulation systems. *Energies*, v. 18, art. 6087, 2025. Equações (5), (9)-(10), (17)-(19), (25); Tabela 1; p. 11 (HIC 8-15 °C). Disponível em: https://doi.org/10.3390/en18226087.

WARREN, V. Partial discharge statistics for medium-voltage machines. *IRMC*, 2022. Tabela 1 (percentis de $Q_m$ para 2 a < 6 kV, VHF, acopladores de 80 pF, 10 pps). [Fichamento interno; INSERIR CITAÇÃO completa].

**Artefatos do repositório (fonte de todo `arquivo:linha` citado)**

Olivas Power System Studio, v4.0.0-beta. `/home/user/olivas-power-system-studio`. Módulos citados: `app/postprocessor/prognosis/{__init__,stress_profile,damage_models,rul_estimator,health_index}.py`; `app/simulation/emt/{__init__,components,circuit,steady_state,line,jmarti,vcb,snubber,probes}.py` e `app/simulation/emt/cases/motor_switching.py`; `tests/test_pp_prognosis_core.py`; `tests/test_emt_{kernel,steady_state,jmarti,vcb_snubber,referencia_eee873}.py`; `app/postprocessor/{audit_trail,report_html,report_pdf,trt_analyzer,motor_starting}.py`; `app/commercial/feature_gates.py`; `app/gui/{main_window,analysis_dialogs}.py`; `app/core/version.py`; `app/simulation/{runner,results_reader}.py`; `app/analysis/transient_metrics.py`; `app/preprocessor/vcb_model_emitter.py`; `app/preprocessor/atp_templates/vcb_reignition.mod`; `requirements.txt`; `.github/workflows/test.yml`; `CHANGELOG.md`; `ROADMAP.md`; `ARCHITECTURE_ATP_STUDIO.txt`.

**Documentos anteriores desta série**

`docs/research/rul_isolamento/00_INDICE.md` — nota metodológica e rótulos de evidência.
`docs/research/rul_isolamento/01_ETAPA1_monitoramento_degradacao_isolamento.md` — §3.3 ($T_1$ e RRRV), §5.4 (D1-D7), §5.5, §6 (γ(t) e correção conceitual do BIL).
`docs/research/rul_isolamento/02_ETAPA2_cruzamento_A_x_B.md` — §2.4 (margens de *ride-through*), §3.1 (fator térmico), §5.2 (eqs. 5.1-5.3 e monotonicidade perversa), §6 (*health-aware load shedding*).
`docs/research/rul_isolamento/anexos/repo/convencoes_auditoria_gui_docs.md` — pontos de extensão E1-E20, checklist 4.1-4.7, lacunas L1-L15, riscos R1-R15.
`docs/research/rul_isolamento/anexos/repo/trt_transitorios_simulacao.md` — cadeia ATP → PL4 → métricas.
`docs/research/rul_isolamento/anexos/repo/vcb_reignicao_snubber.md` — divergência entre lei linear e parabólica de RRDS.

**Documento posterior desta série**

`docs/research/rul_isolamento/05_MOTOR_EMT_DEDICADO.md` — **Motor de transitórios eletromagnéticos dedicado do Olivas PSS: fundamentação, implementação, validação e caminho para C++**: fundamentação dos modelos companheiros contra as fontes primárias acima, procedimento CDA, partida em regime permanente, modelo dependente da frequência, regressão dígito a dígito contra as Listas 01 e 02 de EEE873 e catálogo completo das 27 limitações `emt_*`. Este documento (04) trata da **arquitetura** e remete a 05 sempre que a questão é a **física ou a validação numérica** do motor. Seções: §1 por que um motor dedicado; §2 MNA e modelos companheiros; §3 CDA; §4 partida em regime permanente; §5 Bergeron e JMarti. [REMISSÃO: numeração das seções posteriores a conferir na versão final de 05.]
