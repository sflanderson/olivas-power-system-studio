# Motor de transitórios eletromagnéticos dedicado do Olivas PSS: fundamentação, implementação, validação e caminho para C++

**Objetivo.** Documentar, com rastreabilidade `arquivo:linha`, o motor de transitórios eletromagnéticos (EMT) próprio do Olivas Power System Studio — pacote `app/simulation/emt/` (11 arquivos, 9 915 linhas) com 273 testes dedicados —, desde a justificativa da decisão de construí-lo até o critério objetivo de migração do laço interno para C++. O documento registra **o que existe no código**, a **dedução de cada modelo contra a fonte primária** (número de equação e página), a **regressão dígito a dígito** contra os dois trabalhos do próprio autor em EEE873 (que já são validados contra o ATP), e o **estado honesto** do confronto contra a Tabela III do Documento A, que permanece **aberto**.

**Diagnóstico.** O kernel está completo e verificado nas suas fundações: modelos companheiros de Dommel, formulação nodal aumentada (MNA) de Ho, Ruehli e Brennan, amortecimento crítico (CDA) de Lin e Martí, partida em regime permanente por solução fasorial, linha de Bergeron e linha dependente da frequência pelo método de Martí, disjuntor a vácuo dinâmico e *snubber* a tiristor. A suíte inteira — 449 testes, sendo 273 do motor e 176 do núcleo de prognóstico — passa em 63,6 s [CÁLCULO PRÓPRIO: `python3 -m pytest tests/test_emt_kernel.py tests/test_emt_vcb_snubber.py tests/test_pp_prognosis_core.py tests/test_emt_steady_state.py tests/test_emt_jmarti.py tests/test_emt_referencia_eee873.py -q` → `449 passed in 63.56s`, nesta sessão]. A **regressão contra as Listas 01 e 02 de EEE873 fecha dígito a dígito** em 28 dos 30 casos confrontados, com duas divergências menores registradas e explicadas (§8.6). O confronto contra o Documento A **não fecha**: com os parâmetros publicados de A, nenhum polo alcança a primeira interrupção bem-sucedida e o pico de TRV registrado é da ordem de 0,1 kV contra 41,44 kV da Tabela III [CÁLCULO PRÓPRIO, medido nesta sessão; REPO: `app/simulation/emt/cases/motor_switching.py`, `KNOWN_LIMITATIONS["emt_case_doc_a_rrds_prevents_clearing"]`]. O motor continua **órfão** no sentido das convenções do repositório: nenhum módulo fora de `app/simulation/emt/` o importa [CÁLCULO PRÓPRIO: `grep -rn "simulation.emt" app/ --include=*.py` fora do próprio pacote → vazio].

**Arquivos consultados.**

| Caminho | Uso neste documento |
|---|---|
| `/home/user/olivas-power-system-studio/app/simulation/emt/__init__.py` (457 l.) | Fachada, `__all__`, `KNOWN_LIMITATIONS` (`:311`, 19 chaves) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/components.py` (1 259 l.) | `Component` (`:279`), `Resistor` (`:413`), `Inductor` (`:462`), `Capacitor` (`:567`), `VoltageSource` (`:667`), `Switch` (`:832`), `CoupledRL` (`:1012`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/circuit.py` (1 207 l.) | `lu_factor` (`:223`), `_Factorization` (`:278`), `Circuit` (`:317`), `TimedSwitchController` (`:498`), `Solver` (`:659`), laço de marcha (`:1022-1195`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/steady_state.py` (810 l.) | `PhasorSolution` (`:211`), `_line_admittance` (`:410`), `solve_phasor` (`:558`), `seed_from_phasor` (`:669`), `initialize_steady_state` (`:761`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/line.py` (601 l.) | `_TravelHistory` (`:187`), `BergeronLine` (`:283`), `seed_steady_state` (`:428`), `_history_sources` (`:505`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/jmarti.py` (2 349 l.) | `vector_fit` (`:656`), `minimum_phase_angle` (`:860`), `estimate_time_delay` (`:955`), `LineFrequencyData` (`:1052`), `ModalLineModel` (`:1315`), `_PoleRecursion` (`:1478`), `JMartiLine` (`:1747`), `JMARTI_LIMITATIONS` (`:2251`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/vcb.py` (1 115 l.) | `ParabolicRecovery` (`:209`), `LinearRecovery` (`:257`), `VacuumCircuitBreakerModel` (`:356`), máquina de estados (`:690-829`), `three_phase_vcb` (`:941`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/snubber.py` (684 l.) | `ThyristorSnubber` (`:184`), `_evaluate_breakover` (`:429`), `build_snubber_branch` (`:517`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/probes.py` (310 l.) | `Probe` (`:57`), `DifferentialVoltageProbe` (`:193`), `to_stress_profile` (`:248`) |
| `/home/user/olivas-power-system-studio/app/simulation/emt/cases/motor_switching.py` (1 068 l.) | `DOC_A_TABLE_III` (`:149`), `CableParameters` (`:282`), `MotorSwitchingModel` (`:644`), `build()` (`:823`), `KNOWN_LIMITATIONS` (8 chaves) |
| `/home/user/olivas-power-system-studio/tests/test_emt_kernel.py` (1 511 l., 94 testes) | 12 classes, de `TestMontagemMatriz` (`:76`) a `TestCasoReferenciaLista02` (`:1303`) |
| `/home/user/olivas-power-system-studio/tests/test_emt_referencia_eee873.py` (1 389 l., 35 testes) | Regressão contra as Listas 01 e 02 |
| `/home/user/olivas-power-system-studio/tests/test_emt_steady_state.py` (1 017 l., 43 testes) | Partida fasorial |
| `/home/user/olivas-power-system-studio/tests/test_emt_jmarti.py` (1 037 l., 49 testes) | Ajuste racional, fase mínima, viés de frente (`:632`) |
| `/home/user/olivas-power-system-studio/tests/test_emt_vcb_snubber.py` (1 053 l., 52 testes) | VCB e *snubber*, balanço de energia (`:342`, `:362`, `:739`) |
| `/home/user/olivas-power-system-studio/app/preprocessor/atp_templates/vcb_reignition.mod` | MODEL legado (recuperação **linear**) para a tabela comparativa da §6.6 |
| `/home/user/olivas-power-system-studio/app/postprocessor/prognosis/stress_profile.py` | `extract_stress_events` (`:415`), destino do vetor de estresse |
| `.../scratchpad/emt_refs/txt/{1969_Dommel_EMTP, 1971_Dommel_nonlinear, 1975_Ho_MNA, 1990_Lin_Marti_CDA, 2007_Mahseredjian_EMTP_RV}.txt` | Fontes primárias, texto integral |
| `.../scratchpad/eee873/{Lista01_EEE873, Lista02_EEE873}.txt` | Casos de referência do autor, validados contra o ATP |
| `.../scratchpad/papers_AB/txt/A_sepoc_snubber.txt` | Documento A: Tabelas II e III |

**Arquivos afetados.** Criado nesta etapa: **apenas este documento**, `docs/research/rul_isolamento/05_MOTOR_EMT_DEDICADO.md`. O código descrito foi produzido nas fases anteriores desta mesma sessão; este documento **não altera código**. Estado da árvore no momento da redação: `app/simulation/emt/{__init__,circuit,components,line,vcb}.py` e `app/simulation/emt/cases/motor_switching.py`, `tests/test_emt_kernel.py` e `tests/test_emt_vcb_snubber.py` **modificados e não commitados**; `app/simulation/emt/{jmarti,steady_state}.py`, `tests/test_emt_{jmarti,steady_state,referencia_eee873}.py` **não rastreados** [CÁLCULO PRÓPRIO: `git status --porcelain`]. Último *commit* do motor: `74c81b4 feat(emt): modelo dinamico de disjuntor a vacuo e snubber a tiristor`.

**Estratégia.** (1) Justificar a decisão de motor dedicado por fatos verificáveis, sem afirmar nada sobre termos de licença que não se possa sustentar (§1). (2) Deduzir a formulação MNA e cada modelo companheiro a partir da fonte primária, com número de equação e página, e apontar a linha do código que realiza cada equação (§2). (3) Demonstrar por que a regra trapezoidal oscila na interrupção de corrente indutiva, reproduzir o procedimento de Lin e Martí como publicado e medir o efeito (§3). (4) Mostrar que a partida em regime permanente é requisito, não conveniência (§4). (5) Colocar Bergeron e JMarti lado a lado e medir o viés entre eles sobre a **mesma** frente (§5). (6)–(7) Documentar VCB e *snubber* e as lacunas do Documento A (§6, §7). (8) Apresentar a validação completa em tabela referência × obtido × veredito (§8). (9) Reportar o *benchmark* contra A com honestidade, incluindo o que falta (§9). (10) Medir desempenho e fixar critério objetivo de migração para C++ (§10). (11)–(13) Integração, limitações e referências.

**Limitações.** Este documento descreve **código verificado e medições desta sessão**; não introduz nem calibra parâmetro físico algum. O texto integral de Martí (1982) **não esteve disponível**: os números de equação e de página desse artigo aparecem como `[INSERIR CITAÇÃO]` em quatro pontos de `jmarti.py`, e a formulação foi montada a partir de fontes secundárias efetivamente acessadas, com o limite sem perdas conferido contra Dommel (§5.4). O confronto com a Tabela III do Documento A **não fecha** (§9). O motor **não** tem integração com a GUI, com o laudo, com i18n nem com o gate comercial, e **não** lê nem escreve `.atp` (§11.3). Nenhuma medida de desempenho aqui é determinística: `SolverResult.wall_time_s` é explicitamente marcado como impróprio para asserção de teste [REPO: `app/simulation/emt/circuit.py:653-655`].

**Próximo passo recomendado.** Fechar a lacuna da §11.3 — um leitor de cartões `.atp` que instancie o circuito do kernel a partir do arquivo, preservando o `.atp` como fonte única da verdade —, porque é ele que transforma o motor de um segundo *backend* órfão em um solucionador do caso técnico já existente. Enquanto isso não existir, todo caso do kernel é construído em Python e diverge do registro `.atp` por construção.

---

## 1. Por que um motor dedicado, e por que próprio

### 1.1 A demanda que o binário externo não atende

As Etapas 1 e 2 desta série fixaram um requisito que não é de exatidão, e sim de **volume**: o acumulador de dano consome um vetor de estresse $s_{m,j}$ por evento de manobra, e a estimativa de RUL com incerteza declarada exige varrer o espaço de instante de abertura, corrente de corte e plano de corte de carga [REPO: `docs/research/rul_isolamento/02_ETAPA2_cruzamento_A_x_B.md`]. A ordem de grandeza declarada pelo próprio pacote é de $10^3$ a $10^4$ execuções [REPO: `app/simulation/emt/__init__.py:8-15`].

Três fatos, e apenas três, sustentam a decisão — todos verificáveis, nenhum sobre termos de licença:

| # | Fato | Consequência |
|---|---|---|
| F1 | O executável ATP-EMTP (TPBIG) é **binário de terceiro**, obtido por credenciamento individual, e o repositório não o distribui: o `AtpRunner` apenas posiciona arquivos e invoca um executável do ambiente [REPO: `app/simulation/runner.py:285,338-372`] | Um produto comercial não pode depender de o usuário final possuir o binário para produzir o número de RUL |
| F2 | O executável é orientado a **um caso por execução**, com entrada e saída por arquivo (`.atp` → `.pl4`) | $10^4$ execuções implicam $10^4$ ciclos de escrita, processo e leitura de arquivo |
| F3 | **Nenhum consumidor do repositório lê o `.pl4`** a partir de `RunResult.run_dir` [REPO: `docs/research/rul_isolamento/anexos/repo/trt_transitorios_simulacao.md:28`, verificado contra `app/simulation/runner.py`] | A cadeia ATP → perfil de estresse **não existe hoje**; construí-la custaria um leitor de `.pl4` mais o *harness* de execução em massa |

**O que este documento NÃO afirma.** Nada sobre o que a licença do ATP permite ou proíbe em termos de redistribuição, uso comercial ou automação — o texto de licença não foi acessado nesta sessão e qualquer afirmação a respeito seria inventada [FATO por omissão]. A decisão registrada é do autor e se apoia em F1–F3, que são propriedades observáveis do repositório e do modo de operação do binário.

### 1.2 Reprodutibilidade auditável

O segundo motivo é epistêmico e é o que dá a este projeto o direito de publicar números. Com motor próprio:

* cada equação tem **fonte, número e página** na docstring do módulo que a realiza, e um teste que a exercita — por exemplo, a recursão do Apêndice I de Dommel para o indutor está provada em `tests/test_emt_kernel.py`, classe `TestFontesPrimarias` (`:1168`);
* o **catálogo de limitações é código**, não prosa: 19 chaves em `app.simulation.emt.KNOWN_LIMITATIONS` mais 8 do caso de manobra, verificáveis por `import` [CÁLCULO PRÓPRIO: contagem nesta sessão];
* o resultado é **determinístico** e reexecutável sem binário externo, o que torna a suíte de 273 testes do motor uma linha de base de regressão real.

### 1.3 O `.atp` continua sendo a fonte da verdade

A decisão do autor é explícita e está gravada no cabeçalho do pacote: *"O arquivo `.atp` permanece **fonte única da verdade** do caso técnico; o que muda é quem o resolve. O runner do ATP continua funcionando e não é tocado por este pacote"* [REPO: `app/simulation/emt/__init__.py:17-21`]. Verificado: o pacote `emt` **não importa** `app.simulation.runner` e não é importado por ele [CÁLCULO PRÓPRIO: `grep`]. A consequência prática — hoje o kernel não lê `.atp`, de modo que o caso resolvido é construído em Python e pode divergir do registro — é a lacuna da §11.3.

---

## 2. Formulação: análise nodal modificada e modelos companheiros

### 2.1 O sistema resolvido a cada passo

A cada instante de simulação resolve-se um sistema algébrico linear

$$\mathbf{A}\,\mathbf{x}(t) = \mathbf{b}(t), \qquad \mathbf{x} = \begin{bmatrix}\mathbf{v}_n \\ \mathbf{i}_x\end{bmatrix} \tag{2.1}$$

com $\mathbf{v}_n$ o vetor de tensões nodais em relação à terra [V] e $\mathbf{i}_x$ o vetor de correntes de ramo das fontes de tensão e das chaves ideais [A]. A partição é a da análise nodal modificada:

$$\begin{bmatrix}\mathbf{G} & \mathbf{A}_c \\ \mathbf{A}_l & \mathbf{A}_d\end{bmatrix}\begin{bmatrix}\mathbf{v}_n \\ \mathbf{i}_x\end{bmatrix} = \begin{bmatrix}\mathbf{i}_n \\ \mathbf{v}_x\end{bmatrix} \tag{2.2}$$

em que $\mathbf{G}$ é a matriz de condutâncias nodais [S], $\mathbf{i}_n$ reúne as fontes de corrente conhecidas e os termos históricos [A] e $\mathbf{v}_x$ as tensões conhecidas [V]. Esta é exatamente a eq. (2) de Ho, Ruehli e Brennan, com os carimbos da Tabela I do mesmo artigo [FONTE: Ho, Ruehli & Brennan 1975, p. 504, eq. (2) e Tabela I, p. 505], na notação e partição fixadas pelo autor [LISTA: 02, §1.2, eqs. (4)-(5)]. Realizada em `Circuit.assemble_matrix` [REPO: `app/simulation/emt/circuit.py:462`] e `Circuit.assemble_rhs` [REPO: `app/simulation/emt/circuit.py:471`].

**Por que MNA e não eliminação de nós de tensão conhecida.** Três razões, todas registradas no código [REPO: `app/simulation/emt/components.py:700-704`]: (i) a chave ideal **não tem tensão conhecida** quando aberta, de modo que a eliminação não a representa sem impedância fictícia; (ii) a eliminação **renumera o sistema** a cada manobra, inviabilizando o cache de fatoração; (iii) mantendo a incógnita de corrente da chave **também no estado aberto**, com a equação $i=0$, a **dimensão e o posto do sistema são invariantes** à topologia e só os coeficientes mudam — é o *fixed rank system* de [FONTE: Mahseredjian et al. 2007, §2, p. 1516] e o "ponto essencial" de [LISTA: 02, §1.2]. A ausência de impedância fictícia elimina a constante de tempo espúria $R_{\text{open}}C$ e as *"superfluous natural frequencies and matrix conditioning problems"* [FONTE: Mahseredjian et al. 2007, §1, p. 1515].

**Convenção de sinal da corrente de fonte.** A LKC é escrita somando as correntes que **saem** do nó, e $i_{\text{src}}$ é a que **entra** pelo terminal positivo — daí o $+1$ na linha do nó $p$ [LISTA: 02, §1.2, eqs. (7) e (10)]. Consequência que **deve** ser observada ao comparar com o ATP: a corrente **fornecida ao circuito** é $-i_{\text{src}}$ [REPO: `app/simulation/emt/components.py:692-697`].

### 2.2 Modelo companheiro do indutor

Integrando $v = L\,\mathrm{d}i/\mathrm{d}t$ de $t-\Delta t$ a $t$ pela regra trapezoidal:

$$i(t) - i(t-\Delta t) = \frac{1}{L}\int_{t-\Delta t}^{t} v\,\mathrm{d}t \approx \frac{\Delta t}{2L}\left[v(t) + v(t-\Delta t)\right] \tag{2.3}$$

$$\boxed{\;i(t) = G_L\,v(t) + I_{\text{hist}}(t), \quad G_L = \frac{\Delta t}{2L}\;[\mathrm{S}], \quad I_{\text{hist}}(t) = i(t-\Delta t) + G_L\,v(t-\Delta t)\;[\mathrm{A}]\;} \tag{2.4}$$

Termo a termo as eqs. (9a) e (9b) de [FONTE: Dommel 1969, p. 389], na notação do autor [LISTA: 02, eq. (1); LISTA: 01, §1.1 e Tabela 1]. Realizadas em `Inductor.prepare` (`_g = dt/(2L)`) e `Inductor.history_current_A` [REPO: `app/simulation/emt/components.py:518-540`].

**Forma recursiva e a prova de equivalência.** Dommel escreve, no Apêndice I, a recursão de valor único, com sinal **+** para indutância:

$$I_L(t) = 2\,G_L\,v_L(t) + I_L(t-\Delta t) \tag{2.5}$$

[FONTE: Dommel 1969, Apêndice I, p. 395; LISTA: 02, eq. (3)]. O código guarda o **par** $(i, v)$ em vez do valor recursivo único. [CÁLCULO PRÓPRIO] As duas formas são algebricamente idênticas: `commit()` calcula $i \leftarrow G v + I_{\text{hist}}$ e a chamada seguinte de `history_current_A()` devolve $i + G v = 2 G v + I_{\text{hist},\text{anterior}}$, que é (2.5). Provado por teste dedicado, `test_recursao_do_indutor_dommel_apendice_I` [REPO: `tests/test_emt_kernel.py`, classe `TestFontesPrimarias`, `:1168`].

**Correção de citação executada nesta sessão.** A docstring dizia "Dommel 1969, eq. 5" — número que **não corresponde** ao indutor no artigo. Substituída por (9a)/(9b), p. 389 [AUDITORIA desta sessão].

### 2.3 Modelo companheiro do capacitor — o sinal é o ponto crítico

$$v(t) - v(t-\Delta t) \approx \frac{\Delta t}{2C}\left[i(t) + i(t-\Delta t)\right] \tag{2.6}$$

$$\boxed{\;i(t) = G_C\,v(t) + I_{\text{hist}}(t), \quad G_C = \frac{2C}{\Delta t}\;[\mathrm{S}], \quad I_{\text{hist}}(t) = -\,i(t-\Delta t) - G_C\,v(t-\Delta t)\;[\mathrm{A}]\;} \tag{2.7}$$

**As duas parcelas do histórico são negativas** — é aqui que a álgebra do capacitor difere estruturalmente da do indutor, e é o erro de sinal mais comum na implementação de um kernel EMT. Eqs. (10a) e (10b) de [FONTE: Dommel 1969, p. 390]; [LISTA: 02, eq. (2); LISTA: 01, §2.1]. A recursão correspondente **alterna de sinal a cada passo**:

$$I_C(t) = -\,2\,G_C\,v_C(t) - I_C(t-\Delta t) \tag{2.8}$$

[FONTE: Dommel 1969, Apêndice I, p. 395, sinal **−** para capacitância]. Realizada em `Capacitor.history_current_A` [REPO: `app/simulation/emt/components.py:633-640`], verificada por teste.

**Observação de auditoria, registrada por dever de transparência.** O OCR do texto integral de Dommel disponível nesta sessão **omite o sinal menos** sobre $i_{km}$ em (10b). A forma correta foi confirmada por dedução independente a partir de (2.6) e pelas eqs. (3) e (6) da Lista 02 [AUDITORIA desta sessão]. A citação anterior, vaga ("eq. 8"), foi substituída pelas equações corretas.

### 2.4 Ramo RL acoplado de $n$ enrolamentos

Com $\mathbf{R}$ e $\mathbf{L}$ matrizes $n\times n$ e $[\mathbf{S}] = \mathbf{R} + 2\mathbf{L}/\Delta t$:

$$\mathbf{G} = [\mathbf{S}]^{-1}, \qquad \mathbf{I}_{\text{hist}}(t) = [\mathbf{S}]^{-1}\left[\mathbf{v}(t-\Delta t) + \left(\tfrac{2\mathbf{L}}{\Delta t} - \mathbf{R}\right)\mathbf{i}(t-\Delta t)\right] \tag{2.9}$$

Eqs. (17a) e (17b) de [FONTE: Dommel 1969, p. 392]. Dommel imprime a forma recursiva $[\mathbf{I}(t-\Delta t)] = [\mathbf{H}]([\mathbf{v}] + [\mathbf{S}][\mathbf{I}(t-2\Delta t)]) - [\mathbf{I}(t-2\Delta t)]$ com $[\mathbf{H}] = 2([\mathbf{S}]^{-1} - [\mathbf{S}]^{-1}[\mathbf{R}][\mathbf{S}]^{-1})$. [CÁLCULO PRÓPRIO] As duas coincidem, pois $[\mathbf{H}][\mathbf{S}] - \mathbf{1} = \mathbf{1} - 2[\mathbf{S}]^{-1}[\mathbf{R}]$; substituindo $\mathbf{i}(t-\Delta t) = [\mathbf{S}]^{-1}\mathbf{v}(t-\Delta t) + \mathbf{I}(t-2\Delta t)$ recupera-se termo a termo a recursão publicada. Prova acrescentada à docstring [REPO: `app/simulation/emt/components.py:106-115`]; implementação em `CoupledRL` [REPO: `app/simulation/emt/components.py:1012`].

### 2.5 Resistor, fonte de tensão e chave ideal

| Ramo | Estampa | Fonte |
|---|---|---|
| `Resistor` | $G = 1/R$, $I_{\text{hist}} = 0$ | [FONTE: Dommel 1969, eq. (11), p. 390] |
| `VoltageSource` | incidência $\pm 1$ e linha de restrição $v_p - v_n = e(t)$ | [FONTE: Ho et al. 1975, Tabela I, entrada `E`, p. 505]; [LISTA: 02, eqs. (4)-(5)] |
| `Switch` fechada | linha de restrição $v_k - v_m = 0$ | [LISTA: 02, eq. (5)]; [FONTE: Dommel 1969, p. 391] |
| `Switch` aberta | linha de restrição $i_{km} = 0$ (célula diagonal $= 1$) | [LISTA: 02, eq. (18)]; $S_d$ de [FONTE: Mahseredjian et al. 2007, eq. (2), p. 1516] |

A chave ideal é o caso particular de resistência variante no tempo de [FONTE: Dommel 1971, §III, p. 2561]. O RHS da linha de restrição é **nulo nos dois estados**, razão pela qual `Switch` não sobrescreve `stamp_rhs` [REPO: `app/simulation/emt/components.py:976-995`]. Teste verifica que a comutação altera **exatamente uma linha** da matriz, com dimensão e posto invariantes [REPO: `tests/test_emt_kernel.py`, `TestFontesPrimarias`].

**Convenção de fase — divergência corrigida nesta sessão.** `VoltageSource` gerava **apenas seno**, incompatível com o fasor de amplitude com o cosseno como referência fixado pelo autor, $x(t) = \mathrm{Re}\{\hat{X}e^{j\omega t}\}$ [LISTA: 02, §1.4], e com os circuitos de referência $v_s = 100\cos(377t)$ V. Acrescentado `phase_reference ∈ {"sin","cos"}` (padrão `"sin"` por compatibilidade), propagado a `three_phase_voltage_sources` [REPO: `app/simulation/emt/components.py:715,743-751,776-820`]. Com `"cos"` o kernel reproduz **todos** os fasores publicados em [LISTA: 02, §3.3] nos dígitos impressos (§8.3).

### 2.6 Fatoração: por que inversa cacheada e não LU a cada passo

`scipy` não é dependência do projeto, logo não há `scipy.linalg.lu_factor` [REPO: `requirements.txt`]. Restam três caminhos sobre `numpy`, e a decisão foi por **medição** [CÁLCULO PRÓPRIO, registrado em `app/simulation/emt/circuit.py:134-146`]:

| Caminho | $n=7$ | $n=32$ | $n=128$ |
|---|---|---|---|
| `np.linalg.solve` a cada passo | 5,48 µs | 16,2 µs | 199,0 µs |
| Substituição LU própria (laço em Python) | 23,25 µs | 112,2 µs | 481,3 µs |
| $\mathbf{A}^{-1}\mathbf{b}$ com inversa cacheada | **1,08 µs** | **1,24 µs** | **2,95 µs** |

Erro relativo contra `np.linalg.solve`: $7{,}2\times10^{-19}$ (LU) e $9{,}2\times10^{-17}$ (inversa) — dez ordens de grandeza abaixo de qualquer significância física, e a matriz MNA é bem condicionada **porque** não há impedância fictícia de chave. Decisão implementada: fatora-se por LU própria (que dá detecção explícita de singularidade com pivotamento parcial e estimativa de condicionamento) e aplica-se pela inversa; acima de `INVERSE_CONDITION_LIMIT = 1e10` o solver registra `WARNING` e volta à substituição LU [REPO: `app/simulation/emt/circuit.py:205-211,940-977`].

**Divergência deliberada em relação a Dommel.** [FONTE: Dommel 1969, p. 391] reordena os nós com chave para o fim da matriz e refaz **apenas a parte inferior** da fatoração. Aqui a matriz é remontada inteira e a fatoração é recuperada de um cache indexado pela assinatura de topologia. O ganho de Dommel vem da esparsidade em redes grandes; o ganho do cache vem da **recorrência das mesmas poucas topologias** em sequências de reignição — o regime de uso deste kernel. Medido no caso de manobra: 4 fatorações contra 22 mudanças de topologia, com 19 acertos de cache [CÁLCULO PRÓPRIO desta sessão]. Divergência declarada em `Switch` [REPO: `app/simulation/emt/components.py:1000-1010`].

---

## 3. Amortecimento crítico (CDA)

### 3.1 Por que a regra trapezoidal oscila na interrupção de corrente indutiva

Aplicada ao ramo $L$ que, após a manobra, passa a ver uma resistência elevada $R$, a recursão trapezoidal tem polo discreto

$$z = \frac{1 - R\Delta t/2L}{1 + R\Delta t/2L} \;\longrightarrow\; -1 \quad\text{quando}\quad \frac{R\,\Delta t}{2L} \gg 1 \tag{3.1}$$

isto é, oscilação de período $2\Delta t$ com amortecimento desprezível [FONTE: Lin & Martí 1990, §2, p. 394]. É **artefato numérico**, e contamina exatamente as duas grandezas que alimentam o modelo de dano: $V_{pk}$ e $\mathrm{d}v/\mathrm{d}t$ [REPO: `app/simulation/emt/circuit.py:106-125`].

O caso é reproduzido **dígito a dígito** contra o ATP em [LISTA: 02, §3.8]: sequência $-4\,887{,}8$; $+5\,074{,}5$; $-4\,887{,}8$; $+5\,074{,}6$ V no nó da fonte, com amplitude prevista $(2L_1/\Delta t)\,|i_{\text{cortada}}| \approx 4\,990$ V. O kernel reproduz a mesma sequência e a mesma amplitude, $4\,989{,}9$ V, e mostra a oscilação **sustentada** (alternância de sinal em 200 passos, ainda acima de 4 800 V a 68 ms do corte) [CÁLCULO PRÓPRIO; REPO: `tests/test_emt_referencia_eee873.py:1169`, `test_q2_oscilacao_numerica_sem_cda`].

Com Euler regressivo de meio-passo o polo é $z = 1/(1 + Rh/L) \to 0^+$ e o artefato desaparece em dois meios-passos.

### 3.2 O procedimento de Lin e Martí, como publicado

O cabeçalho de `circuit.py` reproduz o procedimento em **seis passos**, substituindo a paráfrase anterior [REPO: `app/simulation/emt/circuit.py:46-104`]:

1. marcha trapezoidal normal até que uma descontinuidade esteja prevista para $t_1^+$ — manobras, saltos de fonte (**inclusive em $t=0$**) e transições de segmento de indutância linear por partes;
2. resolve-se normalmente em $t_1$, supondo que a descontinuidade ainda não ocorreu (solução para $t_1^-$);
3. aplica-se a descontinuidade;
4. obtém-se $t_1 + \Delta t/2$ por Euler regressivo com passo $\Delta t/2$ — *"a matriz [G] da eq. (1) não muda; só as fórmulas do vetor de históricos [h(t)] precisam mudar"*;
5. resolve-se **uma segunda vez** por Euler regressivo, em $t_2 = t_1 + \Delta t$, de modo que a marcha recai sobre a malha uniforme;
6. prossegue-se com a regra trapezoidal em $t_2 + \Delta t$, …

[FONTE: Lin & Martí 1990, §2, p. 394, itens 1-6]. São **exatamente dois meios-passos por descontinuidade**. Implementado em `Solver.run` [REPO: `app/simulation/emt/circuit.py:1160-1176`], com `cda_events` incrementado uma vez por descontinuidade e base de tempo uniforme verificada por teste.

**A propriedade que dispensa refatoração.** Com $h = \Delta t/2$:

$$G_L = \frac{h}{L} = \frac{\Delta t}{2L}, \qquad G_C = \frac{C}{h} = \frac{2C}{\Delta t}, \qquad \mathbf{G} = \left(\mathbf{R} + \frac{\mathbf{L}}{h}\right)^{-1} = \left(\mathbf{R} + \frac{2\mathbf{L}}{\Delta t}\right)^{-1} \tag{3.2}$$

**as condutâncias companheiras do Euler regressivo de meio-passo são idênticas às trapezoidais** [FONTE: Lin & Martí 1990, §2, p. 394 e Conclusões, p. 401]. Só o histórico muda:

$$I_{\text{hist}}^{L} = i(t-h), \qquad I_{\text{hist}}^{C} = -G_C\,v(t-h), \qquad \mathbf{I}_{\text{hist}}^{RL} = \mathbf{G}\,\frac{2\mathbf{L}}{\Delta t}\,\mathbf{i}(t-h) \tag{3.3}$$

eqs. (2)-(4) e Apêndice, eqs. (A.3), (A.5), (A.6) de [FONTE: Lin & Martí 1990]; [LISTA: 01, §1.2, §2.2 e Tabela 1]. É precisamente a **supressão do termo de tensão** no histórico do indutor que mata a oscilação de $2\Delta t$ [FONTE: Lin & Martí 1990, p. 395].

**Correção de citação executada nesta sessão.** A referência anterior, "Martí & Lin 1989", é o artigo do **conceito**; para a **implementação** a fonte correta é Lin & Martí 1990, com equação e página [AUDITORIA desta sessão].

### 3.3 Três regras da fonte que o código respeita — e que agora estão escritas

| Regra da fonte | Estado no código | Onde |
|---|---|---|
| *"Os resultados em $t_1+\Delta t/2$ são apenas quantidades matemáticas […] **nenhuma decisão sobre abrir ou fechar chaves** é tomada com base nesses resultados"* [FONTE: Lin & Martí 1990, §2, p. 394] | **Confere por construção**: os controladores só são chamados no início de cada passo **completo**; a razão, antes não registrada, agora está com a citação literal | `circuit.py:1145-1147,1160-1167` |
| *"Não exige o reajuste de condições iniciais nem outras complicações"* — nenhuma reconstrução de histórico ao voltar ao trapezoidal | **Confere**: o segundo meio-passo termina sobre $t_2 = t_1+\Delta t$ e deixa $i(t_2)$ e $v(t_2)$ em cada ramo; o passo trapezoidal seguinte lê esse par por (9b)/(10b). Era o ponto mais crítico da auditoria e estava correto, sem justificativa escrita | `circuit.py:96-104` |
| Exatamente **um par** de meios-passos por descontinuidade | **Confere** no padrão `cda_full_steps=1` | `circuit.py:1173` |

### 3.4 Três divergências corrigidas nesta sessão

**(a) `record_half_steps` recomendava o oposto da fonte.** A docstring recomendava ativá-lo *"quando o pico da grandeza de interesse puder cair dentro do par de meios-passos"* — contrariando a fonte, que declara esse ponto **sem significado físico**. Ativá-lo injeta um ponto de amortecimento deliberado na série e, portanto, no vetor de estresse $s_{m,j}$. Corrigido: docstring e `KNOWN_LIMITATIONS` reescritas, `WARNING` emitido na ativação, e apontado o caminho legítimo — **reduzir $\Delta t$**, cujo efeito está medido em [LISTA: 02, Tabela 4]: pico de 501,37 V em 4 µs → 505,84 V em 0,25 µs → 506,170 V analítico [REPO: `app/simulation/emt/circuit.py:694-712,829-836`].

**(b) `cda_full_steps > 1` era apresentado como recomendação.** A fonte prescreve **exatamente um par**; o único caso em que admite meios-passos adicionais (§4, p. 395) é a mudança de segmento de indutância linear por partes, e são **três** adicionais — número ímpar, justamente para recair sobre a malha uniforme —, elemento **inexistente** neste kernel. Marcado como `[HIPÓTESE]`/extensão não publicada, com `WARNING` em log quando $n>1$ [REPO: `app/simulation/emt/circuit.py:822-831`].

**(c) CDA em $t=0$ era incondicional.** Correto na partida do repouso (há descontinuidade), **errado** na partida em regime permanente, em que não há descontinuidade e os dois meios-passos introduzem amortecimento espúrio. Acrescentado `Solver(cda_at_start=…)`, com resolução automática pelo modo de partida (`True` com `init="zero"`, `False` com `init="steady_state"`) e `WARNING` quando forçado `True` em regime [REPO: `app/simulation/emt/circuit.py:855-880`].

### 3.5 Evidência quantitativa do CDA

| Grandeza | Sem CDA (trapezoidal pura) | Com CDA (padrão do motor) | Fonte/veredito |
|---|---|---|---|
| $v_3$ no passo do corte, Questão 2 | $-4\,887{,}8$ V, alternando com $+5\,074{,}5$ V, **sustentado** | $93{,}4$ V já no passo do corte, seguindo $v_s(t)$ com erro $<10^{-6}$ V; **nenhuma** alternância de sinal | [LISTA: 02, §3.8] reproduzido dígito a dígito; CDA verificado em `tests/test_emt_referencia_eee873.py:1207` |
| Fator de propagação da eq. (30) da Lista 02 | $-1{,}0$ (exato) | — | [LISTA: 02, §3.8] |
| Pico da TRV, $\Delta t = 1$ µs | 504,2923 V (= 504,292 V do autor **e** do ATP) | 505,1484 V | O CDA **aproxima** o pico do analítico 506,170 V (§8.5) |
| Paliativo $R_p = 2L_1/\Delta t = 10$ kΩ do autor | fator $0{,}0$ exato; preço medido 0,0760 V (0,015 % do pico) | não necessário | O CDA suprime a oscilação **sem alterar o circuito**, ao contrário de $R_p$ |
| Questão 1, desvio contra a analítica | $2{,}055\times10^{-3}$ A | $4{,}14\times10^{-3}$ A (0,022 % do pico) | Mesma ordem; o CDA amortece deliberadamente o passo da manobra |

Leitura correta destes números: o CDA **não é gratuito** — ele discretiza de outra forma exatamente o passo da descontinuidade, e por isso o desvio contra uma referência trapezoidal pura cresce. O que ele compra é a eliminação de um artefato de **milhares de volts** em $v_3$, que entraria direto no vetor de estresse. A troca é obviamente favorável para estudo de isolamento.

---

## 4. Partida em regime permanente: requisito, não conveniência

### 4.1 Por que é requisito

Partir do repouso significa partir de um estado que **não é solução do circuito energizado**: a resposta natural daí decorrente é um transitório de energização espúrio que se superpõe ao fenômeno de interesse e contamina $V_{pk}$ e $\mathrm{d}v/\mathrm{d}t$ [REPO: `app/simulation/emt/steady_state.py:6-15`]. Em um estudo cujo produto é um vetor de estresse por evento, isso não é imprecisão: é **contaminação da variável de saída**.

A prescrição é da fonte primária e é a que o ATP adota pelo `TSTART` negativo do cartão de fonte:

$$I_L(0) = i_L(0) + G_L\,v_L(0)\;[\mathrm{A}], \qquad I_C(0) = -\left[G_C\,v_C(0) + i_C(0)\right]\;[\mathrm{A}] \tag{4.1}$$

[LISTA: 02, §1.4 e eq. (6)]; [FONTE: Dommel 1969, Apêndice I, p. 395: *"if the initial conditions are not zero, the history terms must be preloaded"*].

### 4.2 A lacuna real que existia — e a medição da diferença

`Inductor` aceitava **apenas** `initial_current_A` (forçando $v_L(0)=0$) e `Capacitor` **apenas** `initial_voltage_V` (forçando $i_C(0)=0$), o que tornava **impossível** realizar (4.1) e, portanto, impossível a partida em regime permanente da Lista 02. Corrigido: `Inductor` ganhou `initial_voltage_V` e `Capacitor` ganhou `initial_current_A`, com `reset()` pré-carregando o par [REPO: `app/simulation/emt/components.py:498-528,598-628`].

| Configuração | Desvio contra a solução fasorial, Questão 2, $\Delta t = 1$ µs |
|---|---|
| Semeadura completa por (4.1) + `cda_at_start=False` | $1{,}3938\times10^{-10}$ V |
| **Referência do autor** [LISTA: 02, Tabela 3] | $1{,}39\times10^{-10}$ V |
| Sem a semeadura completa | $9{,}72\times10^{-5}$ V — **sete ordens de grandeza pior** |

[CÁLCULO PRÓPRIO desta sessão; teste em `tests/test_emt_referencia_eee873.py:1026`, `test_q2_a_partida_em_regime_permanente_e_exata`, tolerância $5\times10^{-13}$ V = meia unidade no último dígito publicado.]

### 4.3 Como a semeadura foi implementada — quatro decisões

**(a) Fasores contínuos, não o ponto fixo da recursão.** Usa-se $j\omega L$ e $1/(j\omega C)$, como manda o enunciado e como faz a rotina MATLAB do autor [LISTA: 02, Apêndice A, `1i*par.w*L`]. A alternativa consistente com a recursão, $Z_L = j(2L/\Delta t)\tan(\omega\Delta t/2)$, **não** foi adotada: divergiria da referência validada contra o ATP [DECISÃO desta sessão, verificada por script independente antes de codificar: $1{,}3905\times10^{-10}$ isolado, $1{,}392\times10^{-10}$ no kernel].

**(b) Semeadura pela via dos parâmetros de condição inicial dos ramos**, não por escrita direta nos termos históricos. Impondo $i(0)$ e $v(0)$ em `Inductor`/`Capacitor`/`CoupledRL`, o próprio `history_current_A()` já produz (4.1). Benefício: `reset()` reproduz a semente, de modo que reexecutar o solver **reinicia sempre do mesmo regime** — há teste de idempotência [REPO: `app/simulation/emt/steady_state.py:669`, `seed_from_phasor`].

**(c) Admitância da linha de Bergeron tirada das equações do próprio modelo discreto**, não da linha ideal: resolve-se em fasor o sistema $2\times2$ com o operador de atraso $d = e^{-j\omega\tau}$, o fator $\zeta$ e a repartição $a,b$ das perdas concentradas. Só assim a semeadura é coerente com a recursão que a marcha vai executar. Verificado que sem perdas recai em $Y_{11} = 1/(jZ_c\tan\omega\tau)$ e $Y_{12} = -1/(jZ_c\sin\omega\tau)$ [REPO: `app/simulation/emt/steady_state.py:410`, `_line_admittance`; teste `test_linha_sem_perdas_reduz_a_admitancia_classica`]. Medido: desvio de $10^{-12}$ V com linha casada e $\tau$ múltiplo de $\Delta t$, contra **997 V** (a própria tensão de regime) na partida do repouso.

**(d) Erro explícito em vez de semeadura parcial.** Ramo sem equivalente fasorial levanta `UnsupportedComponentError`, com ponteiro para o gancho de extensão `stamp_phasor(A, b, omega)`; linha em meia onda sem perdas ($\omega\tau$ múltiplo de $\pi$) levanta `SteadyStateError` em vez de dividir por determinante nulo [REPO: `app/simulation/emt/steady_state.py:187-208`].

### 4.4 O resíduo permanente, medido e explicado

A rede discreta responde como a contínua em $\omega_{\text{ef}} = (2/\Delta t)\tan(\omega\Delta t/2)$, de modo que resta um desvio **permanente de amplitude constante** — não um transitório que decaia — de ordem relativa

$$\frac{\Delta\omega}{\omega} \approx \frac{(\omega\Delta t)^2}{12} \tag{4.2}$$

| Circuito | $\Delta t$ | Resíduo medido | Referência |
|---|---|---|---|
| RL série (0,5 Ω, 25 mH, 60 Hz) | 1 µs | $1{,}36\times10^{-7}$ A sobre 4,43 A | [CÁLCULO PRÓPRIO], cai por 4 a cada divisão de $\Delta t$ por 2 (teste de ordem) |
| Questão 2 (tensão do reator) | 1 µs | $1{,}392\times10^{-10}$ V | [LISTA: 02, Tabela 3]: $1{,}39\times10^{-10}$ V |
| `CoupledRL` | 2 µs | $1{,}5\times10^{-6}$ V sobre 72 V | Maior porque a resistência entra **dentro** da recursão |

**Advertência necessária:** o $1{,}39\times10^{-10}$ V é um patamar **excepcionalmente baixo por cancelamento** — a tensão do reator, $90{,}912\,\mathrm{V}\angle-0{,}0005°$, é quase estacionária em $\omega$ — e **não** deve ser tomado como resíduo típico [REPO: `KNOWN_LIMITATIONS["emt_steady_state_residual_deviation"]`].

### 4.5 Contrato da base de tempo

Em **nenhum** dos dois modos se registra amostra em $t=0$: a primeira amostra da série é a de $t=\Delta t$, para que o comprimento das séries não dependa do modo de partida. Em compensação, com `init="steady_state"` o vetor de estado em $t=0$ **já é o do regime**, de modo que os controladores — inclusive o critério $I_{mar}$ — leem correntes de regime **antes** do primeiro passo; há teste que verifica exatamente isso [REPO: `app/simulation/emt/circuit.py:1178-1186`].

---

## 5. Modelos de linha: Bergeron e JMarti lado a lado

### 5.1 Bergeron — dedução e estampa

Para a linha sem perdas, a solução de d'Alembert torna $e + Z i$ constante ao longo da característica, o que dá o par de equivalentes de Norton **desacoplados**:

$$i_{km}(t) = \frac{1}{Z_c}e_k(t) + I_k(t-\tau), \qquad I_k(t-\tau) = -\frac{1}{Z_c}e_m(t-\tau) - i_{mk}(t-\tau) \tag{5.1}$$

$$Z_c = \sqrt{L'/C'}\;[\Omega], \qquad \tau = \ell\sqrt{L'C'}\;[\mathrm{s}] \tag{5.2}$$

Eqs. (4)-(6) e (7a)/(7b) de [FONTE: Dommel 1969, p. 389; Fig. 1(b)]. A estampa é **só diagonal** — *"linhas sem perdas contribuem apenas para os elementos diagonais da matriz"* [FONTE: Dommel 1969, §I, p. 389] —, o que é a propriedade que faz a linha "partir" a matriz do sistema em blocos. Verificado por teste que a implementação com $\zeta=1$ se reduz termo a termo a (5.1) [REPO: `app/simulation/emt/line.py:505-526`; `tests/test_emt_kernel.py`, `TestFontesPrimarias`]. Citação anterior vaga ("§III", que na verdade trata de acoplamento mútuo) substituída pelas equações e página corretas [AUDITORIA desta sessão].

**Perdas concentradas $R/4$, $R/2$, $R/4$.** [FONTE: Dommel 1969, "Approximation of Series Resistance of Lines", p. 390]. O código usa a **forma refinada** (com $\zeta$ multiplicando as correntes de histórico), do *Theory Book*, e **não** a combinação linear impressa em 1969. O critério que decidiu foi a consistência em corrente contínua [CÁLCULO PRÓPRIO]:

| Forma | Resistência total vista em CC |
|---|---|
| Refinada (implementada) | $R$ **exatamente**, sem erro de truncamento — o que Dommel promete |
| Impressa em 1969 | $R\,(Z_c + R/4)/(2Z_c) \approx R/2$, isto é, **metade** |

A escolha era portanto a correta; a divergência com o texto de 1969 estava **indocumentada** e agora é declarada, com a verificação em CC explicitada e implementada como teste de aceitação [REPO: `app/simulation/emt/line.py:44-79`].

### 5.2 Tratamento de $\tau$ não múltiplo de $\Delta t$ — divergência declarada

A fonte prevê **duas** opções e diz que **ambas** elevam $\tau < \Delta t$ para $\Delta t$, para que o equivalente da Fig. 1 continue válido: *"uma opção usa interpolação linear […]; para casos com descontinuidades esperadas, outra opção arredonda o tempo de trânsito $\tau$ para o múltiplo inteiro de $\Delta t$ mais próximo"* [FONTE: Dommel 1969, "Accuracy", p. 391].

O kernel implementa **só a interpolação linear** e, para $\tau < \Delta t$, faz **retenção de ordem zero** em vez de elevar $\tau$. O comportamento **não foi alterado** — elevá-lo mudaria silenciosamente o caso do usuário —; a divergência foi **declarada** na docstring e no texto do `WARNING` emitido em `BergeronLine.prepare` [REPO: `app/simulation/emt/line.py:399-413`].

### 5.3 Condições iniciais da linha — lacuna fechada pela §4

[FONTE: Dommel 1969, Apêndice I, p. 395] exige $I_k$ e $I_m$ dados em $t = 0, -\Delta t, \ldots, -\tau$. O padrão do módulo é histórico nulo antes de $t=0$ (linha desenergizada). Para a partida em regime a exigência é atendida por `BergeronLine.seed_steady_state`, que preenche o buffer com a onda de regime em $0, -\Delta t, \ldots, -(\tau + 2\Delta t)$ — duas amostras de folga, para que a consulta mais antiga (em $\Delta t/2 - \tau$, com CDA na partida) caia **dentro** do buffer e não no ramo de retenção de ordem zero [REPO: `app/simulation/emt/line.py:428-503`].

### 5.4 JMarti — formulação, ajuste racional e convolução recursiva

**Ressalva de citação, declarada de saída.** O texto integral de Martí (1982) **não esteve disponível nesta sessão**. A formulação foi montada a partir de quatro fontes secundárias efetivamente acessadas em 3 set. 2026, todas registradas com URL na docstring do módulo, e o **limite sem perdas foi conferido contra Dommel 1969**, esse sim disponível integralmente. Os números de equação e de página de 1982 aparecem como `[INSERIR CITAÇÃO]` em quatro pontos [REPO: `app/simulation/emt/jmarti.py:17-46`].

Para uma linha uniforme:

$$\gamma(\omega) = \sqrt{z y}, \qquad Z_c(\omega) = \sqrt{z/y}\;[\Omega], \qquad A(\omega) = e^{-\gamma(\omega)\ell} \tag{5.3}$$

Definem-se as funções de onda em cada terminal, com $i_k$ **entrando** na linha:

$$F_k = v_k + z_c * i_k \quad(\text{parte}), \qquad B_k = v_k - z_c * i_k \quad(\text{chega}), \qquad B_k(\omega) = A(\omega)F_m(\omega) \tag{5.4}$$

A identidade $F = 2v - B$ elimina a convolução com $z_c$ no lado do histórico, deixando apenas a convolução com $y_c = 1/Z_c$ (que vira condutância mais histórico) e a convolução com $A$, cuja entrada é conhecida por ser atrasada de $\tau$. Resulta

$$i_k(t) = G\,v_k(t) + I_{\text{hist},k}(t), \qquad G = d + \sum_i w_i\,\mathrm{Re}(c_{1,i})\;[\mathrm{S}] \tag{5.5}$$

isto é, **exatamente a mesma estampa do Bergeron** — condutância só na diagonal do próprio terminal e uma fonte de corrente de histórico. Verificado por teste que a condutância estampada é a mesma do Bergeron no limite correspondente [REPO: `tests/test_emt_jmarti.py:492`].

O atraso é extraído e tratado à parte, $A(\omega) = A_{\min}(\omega)\,e^{-j\omega\tau}$, com $A_{\min}$ de fase mínima ajustada em função racional e $e^{-j\omega\tau}$ realizado como deslocamento no buffer de trânsito.

**Ajuste por *vector fitting*, e por quê.** Adotou-se *vector fitting* [LITERATURA: Gustavsen & Semlyen 1999] como rotina padrão, com quatro justificativas declaradas: ajusta módulo **e** fase simultaneamente, sem a etapa heurística de traçado de assíntotas; admite pares complexos conjugados, necessários para $A_{\min}$ de cabos, que o traçado clássico não produz; o erro de ajuste é saída natural do método e pode ser confrontado com tolerância declarada — requisito de auditoria deste repositório; e depende só de `numpy.linalg`, com `scipy` fora das dependências [REPO: `app/simulation/emt/jmarti.py:99-125`]. **A fase mínima não foi abandonada**: é ela que extrai $\tau$ (`minimum_phase_angle` `:860` + `estimate_time_delay` `:955`), exatamente como em Martí.

**Relação de Bode em escala logarítmica.** A primeira implementação (cepstro real sobre malha uniforme em $\omega$) errava até 1,55 rad, porque malha linear não resolve simultaneamente 1 Hz e 10 MHz. Substituída pela forma integral logarítmica

$$\varphi(\omega_0) = \frac{1}{\pi}\int \frac{\mathrm{d}A}{\mathrm{d}u}\,\ln\left|\coth\frac{u}{2}\right|\mathrm{d}u, \qquad u = \ln(\omega/\omega_0) \tag{5.6}$$

com erro medido caindo para $< 0{,}01$ rad. A singularidade do núcleo em $u=0$ é integrada analiticamente na própria célula, $\int \ln(2/|u|)\,\mathrm{d}u = \Delta[1 + \ln(4/\Delta)]$ [CÁLCULO PRÓPRIO].

**Verificação de *aliasing* de fase na extração de $\tau$ — guarda indispensável.** Descobriu-se em bancada que malha logarítmica rala falseia $\tau$ **silenciosamente**: com $\ell = 500$ m, $f_{\max} = 10$ MHz e 43 pontos por década mediu-se $\tau = 1{,}10$ µs contra 1,67 µs corretos, porque o giro de fase entre amostras vizinhas excede $\pi$ e `numpy.unwrap` não recupera a volta. `estimate_time_delay` agora **recusa** a tabela com mensagem que diz quantos pontos por década são necessários, e `frequency_grid_for_delay` (`:323`) dimensiona a malha automaticamente [CÁLCULO PRÓPRIO].

**Recursão exponencial "híbrida" — escolha própria, declarada como não publicada.** A recursão trapezoidal por polo, $\alpha = (2+p\Delta t)/(2-p\Delta t)$, tem $\alpha \to -1$ para polos rápidos: com $|p|\sim10^7$ rad/s e $\Delta t = 1$ µs dá $\alpha \approx -0{,}67$ — exatamente a oscilação de $2\Delta t$ que o CDA existe para matar. Mas a recursão exponencial pura tem coeficiente instantâneo dependente de $h$, e o solver **não** reavalia topologia entre os dois meios-passos do CDA (`_sync_topology` é chamado uma vez por passo completo, `circuit.py:1145`), de modo que uma condutância dependente de $h$ estamparia matriz errada e envenenaria o cache de fatoração. Adotou-se então:

$$\alpha_i(h) = e^{p_i h}, \qquad c_{1,i} = \frac{k_i\,\Delta t}{2 - p_i\,\Delta t}, \qquad c_{2,i}(h) = k_i\,h\,\phi(p_i h) - c_{1,i} \tag{5.7}$$

com $c_1$ **fixo no passo de referência**. Três propriedades, todas verificadas: estabilidade incondicional ($|\alpha|<1$ para todo $\mathrm{Re}(p)<0$ e todo $h$); ganho de regime exato; e **invariância da matriz ao CDA** — $k\Delta t/(2-p\Delta t)$ é ao mesmo tempo o coeficiente instantâneo do trapézio com $\Delta t$ e o do Euler regressivo com $\Delta t/2$, a mesma coincidência de (3.2). Coincide com o trapezoidal até $O(\Delta t^2)$ e degenera em ganho estático sem oscilação para $|p\Delta t|\gg1$ [CÁLCULO PRÓPRIO; REPO: `app/simulation/emt/jmarti.py:127-172`, `_PoleRecursion` `:1478`]. Verificado no teste que conta fatorações: **2** (uma por topologia de chave), **nenhuma** causada pelos meios-passos.

**Tolerância como contrato, não como aviso.** O erro é sempre registrado em log (ordens, $d$, RMS e máximo relativos, iterações, polos refletidos), emite `WARNING` acima de metade da tolerância e levanta `RationalFitError` acima dela, com mensagem acionável. Padrão: 2 % de erro RMS relativo [REPO: `app/simulation/emt/jmarti.py:236-240,821`]. Medido no caso de manobra: $Y_c$ com 6 polos e erro RMS $1{,}8\times10^{-5}$; $A_{\min}$ com 10 polos e erro RMS $6{,}8\times10^{-9}$ [CÁLCULO PRÓPRIO desta sessão].

### 5.5 A medição que importa para a Etapa 1: o viés entre os dois modelos

Sobre a **mesma frente íngreme** (cabo de 500 m, $R' = 20$ mΩ/m, $\Delta t = 5$ ns, fonte casada, terminação aberta) [CÁLCULO PRÓPRIO; REPO: `tests/test_emt_jmarti.py:632`, `test_frente_ingreme_diferenca_de_dvdt_e_de_t1`]:

| Modelo | Pico [V] | $T_1$ [µs] | $\mathrm{d}v/\mathrm{d}t$ [V/s] |
|---|---|---|---|
| Bergeron **sem perdas** | 100,000 | **0,00** (sobe em um único passo, qualquer que seja o comprimento) | $2{,}000\times10^{10}$ |
| Bergeron **com perdas** $R/4,R/2,R/4$ | 97,58 | — | — |
| JMarti (ajustado) | 99,194 | **1,29** | $1{,}750\times10^{10}$ ($-12{,}5$ %) |

**Implicação direta sobre o acumulador de dano da Etapa 1.** O viés dominante **não é de amplitude, é de tempo de frente**. Como o modelo de dano da Etapa 1 pondera a fração da frente que aparece nas primeiras espiras em função de $T_1$ [REPO: `docs/research/rul_isolamento/01_ETAPA1_monitoramento_degradacao_isolamento.md`, §3.3], um $T_1$ nulo por construção **superestima** sistematicamente a solicitação espira-a-espira — e o faz de modo **independente do refino de $\Delta t$**, porque a frente do Bergeron sobe em um passo qualquer que seja $\Delta t$. Portanto:

1. os $V_{pk}$ e $\mathrm{d}v/\mathrm{d}t$ do Bergeron **sem perdas** devem ser lidos como **cota superior** de estresse, não como estimativa central [REPO: `app/simulation/emt/line.py:150-160`];
2. **a alegação de cota superior não vale para o Bergeron COM perdas concentradas**: medido, ele dá pico **menor** que o JMarti (97,58 V contra 99,19 V), porque a aproximação concentrada atenua também a componente de baixa frequência. O texto de `KNOWN_LIMITATIONS` e o teste foram corrigidos para dizer isso [CÁLCULO PRÓPRIO desta sessão];
3. o erro de **ajuste** do JMarti é erro de **modelo**: propaga-se para $V_{pk}$ e $\mathrm{d}v/\mathrm{d}t$ e **não** é reduzido por refinamento de $\Delta t$ [REPO: `KNOWN_LIMITATIONS["emt_jmarti_fit_is_the_model"]`].

**Seleção por um único parâmetro.** `CableParameters.model='jmarti'` ou `MotorSwitchingCase.with_cable_model('jmarti')` é tudo o que muda: como a interface de componente é a mesma, nem o circuito, nem as sondas, nem os controladores, nem o VCB, nem o *snubber* foram tocados. O padrão continua `'bergeron'`, para não alterar silenciosamente resultados já publicados [REPO: `app/simulation/emt/cases/motor_switching.py:804`].


---

## 6. Modelo dinâmico de disjuntor a vácuo

### 6.1 Escopo: o VCB não é um ramo, é um controlador

`vcb.py` **não** é um ramo de circuito: é a camada de controle que comanda uma `Switch` ideal do kernel, reproduzindo os três fenômenos que a chave ideal, por declaração, não contém (limitação `emt_ideal_switch_no_arc`) [REPO: `app/simulation/emt/vcb.py:8-14`]. A separação é deliberada e é o que permite que a matriz MNA permaneça de posto fixo (§2.1) enquanto a física do arco vive fora dela.

### 6.2 Máquina de estados

Cinco estados, na ordem canônica do ciclo de manobra [REPO: `app/simulation/emt/vcb.py:166-190`]:

| Estado | Significado | Transição de saída |
|---|---|---|
| `closed` | contatos fechados, nenhuma separação comandada | $t \ge t_{\text{sep}}$ → `arcing` |
| `arcing` | contatos separados, arco de frequência industrial | $|i| \le I_{ch}$ (e, se exigido, corrente rumo a zero) → `open` |
| `arcing_hf` | arco de alta frequência, pós-reignição | zero de corrente com $\mathrm{d}i/\mathrm{d}t$ dentro da capacidade → `open` |
| `open` | corrente interrompida, *gap* em recuperação | $|v_{\text{gap}}| > V_{wth}(t - t_{\text{ext}})$ → `arcing_hf` (reignição) |
| `cleared` | interrupção definitiva | teto de reignições (salvaguarda **numérica**, não física) |

Implementada em `VacuumCircuitBreakerModel.__call__` [REPO: `app/simulation/emt/vcb.py:690-715`]. Uma guarda de **arco estabelecido** impede decisão espúria no passo da ignição, em que $i(t-\Delta t)$ ainda é a amostra do estado anterior [REPO: `app/simulation/emt/vcb.py:735-737,760-763`].

### 6.3 Corte de corrente: é o campo `Imar` do ATP

O critério é $|i| \le I_{ch}$, que é **exatamente** o campo *current margin* (colunas 35-44) do cartão de chave do ATP: *"a abertura comandada em $t_0$ só se efetiva a partir do primeiro instante $t \ge t_0$ em que a corrente na chave se anula ou cai abaixo de um limiar $|I_{mar}|$"* [LISTA: 02, §1.3 e §3.6]. Aqui $I_{mar}$ é a **corrente de *chopping* amostrada** da faixa do Documento A (1 a 2 A) em vez de valor fixo de cartão [FATO: doc A, p. 2, II-A e Tabela II, p. 3].

**Validação do critério contra o ATP**: os dois programas cortam a corrente no **mesmo passo**, $t_c = 32{,}361$ ms [LISTA: 02, §3.7 e Tabela 4]. Citação e dado de validação acrescentados a `_evaluate_power_frequency_arc` nesta sessão [REPO: `app/simulation/emt/vcb.py:717-736`].

**Correção executada nesta sessão em `TimedSwitchController`.** O controlador abria a chave **incondicionalmente** em $t \ge$ `open_time_s`, ignorando o critério publicado. Corrigido com o parâmetro `current_margin_A` (`None` = abertura forçada, comportamento anterior preservado), com precedência do controlador sobre o campo homônimo da própria `Switch` [REPO: `app/simulation/emt/circuit.py:541-616`]. O critério também foi tornado explícito no próprio `Switch`, com `may_interrupt()`/`open_within_margin()`, e o VCB publica a propriedade `current_margin_A` espelhando o $I_{ch}$ amostrado no cartão da chave a cada `reset` [REPO: `app/simulation/emt/components.py:910-953`; `app/simulation/emt/vcb.py:646`]. Acrescentado `effective_open_time_s` para tornar o instante de corte **auditável e testável**.

**Efeito medido** (§8.5): com $I_{mar} = 0{,}5$ A o kernel reproduz **dígito a dígito** a Tabela 4 da Lista 02. Baixando a margem para 2 mA — o que o passo de 1 µs resolve em torno do zero natural — a interrupção ocorre com 1,005 mA e o pico cai a 90,912 V, isto é, **exatamente a tensão de pico de regime, sem sobretensão alguma** [CÁLCULO PRÓPRIO]. Isso confirma o mecanismo do Documento A: **é a corrente cortada que gera a solicitação sobre o isolamento**, e é o campo $I_{mar}$ — e só ele — que a representa [LISTA: 02, §3.6].

### 6.4 Recuperação dielétrica parabólica

$$V_{wth}(t) = A\,t + B\,t^2, \qquad A = 0{,}801\ \mathrm{kV/ms}, \qquad B = 1{,}226\ \mathrm{kV/ms^2} \tag{6.1}$$

com $t$ o tempo decorrido desde a extinção [ms] e $V_{wth}$ a suportabilidade instantânea do *gap* [kV] [FATO: doc A, p. 3, IV-B e Tabela II]. Implementada em `ParabolicRecovery` [REPO: `app/simulation/emt/vcb.py:209-255`], que também expõe a inclinação instantânea `slope_kV_per_ms`.

### 6.5 Reignição, extinção de alta frequência e a ambiguidade do Documento A

Reignição é declarada quando $|v_{\text{gap}}| > V_{wth}$, e a partir daí o arco de alta frequência é interrompido no **zero de corrente** conforme o $\mathrm{d}i/\mathrm{d}t$ naquele instante, com faixa crítica de 5 a 15 A/µs [FATO: doc A, p. 3, IV-B e Tabela II].

**O Documento A é internamente ambíguo** quanto ao sentido do critério, e a divergência está registrada item a item na Etapa 2 [REPO: `docs/research/rul_isolamento/02_ETAPA2_cruzamento_A_x_B.md:738`]:

* o **texto** da Seção IV-B afirma que a corrente é interrompida quando o $\mathrm{d}i/\mathrm{d}t$ no zero **excede** um valor crítico [FATO: doc A, p. 3, IV-B];
* a **Tabela II** do mesmo artigo nomeia o parâmetro *"Critical **reignition** di/dt"*, isto é, o valor **acima** do qual há reignição — convenção **oposta**, e é a adotada pelo MODEL legado [REPO: `app/preprocessor/atp_templates/vcb_reignition.mod:98-101`].

O padrão do módulo é a convenção **física** (`DIDT_INTERRUPT_WITHIN`: interrompe quando $|\mathrm{d}i/\mathrm{d}t| \le$ capacidade), sustentada pela literatura consolidada de interruptores a vácuo [LITERATURA: Wong, Snider & Lo 2003; Abdulahovic et al. 2017]. A convenção invertida permanece disponível em `DIDT_INTERRUPT_ABOVE` **apenas** para reproduzir a leitura literal de A e o `.mod` legado, com advertência explícita de que **o sinal do efeito do parâmetro sobre $n_r$ — entrada do vetor de estresse — se inverte com ela** [REPO: `app/simulation/emt/vcb.py:37-83`].

### 6.6 Tabela comparativa: kernel dedicado × `vcb_reignition.mod` legado

| Aspecto | `app/simulation/emt/vcb.py` (dedicado) | `atp_templates/vcb_reignition.mod` (legado) |
|---|---|---|
| Lei de recuperação dielétrica | **Parabólica** $At + Bt^2$, $A = 0{,}801$ kV/ms, $B = 1{,}226$ kV/ms² [FATO: doc A, Tabela II] | **Linear** $U_0 + k(t-t_c)$, $U_0 = 690$ V, $k = 17$ V/µs [REPO: `.mod`:52-53,115] |
| Origem dos parâmetros | Documento A, Tabela II | CIGRE TB 570 / EPRI 1989 / Helmer & Lindmayer 1996 [REPO: `.mod`:6-12] |
| Corrente de corte | $I_{ch}$ amostrado da faixa 1–2 A de A; distribuições `uniform`/`normal`/`deterministic`, **semente sempre explícita** | $I_{chop} \sim N(5{,}0;\,1{,}0)$ A [REPO: `.mod`:47-48] |
| Entropia | Proibida entropia implícita: `uniform` e `normal` **exigem** `seed` | `normal(Seed)` do MODELS |
| Convenção de $\mathrm{d}i/\mathrm{d}t$ | **Física** por padrão, invertida disponível e declarada | **Invertida** (reignita acima do crítico) [REPO: `.mod`:98-101] |
| Endurecimento $\mathrm{d}i/\mathrm{d}t_{\text{crit}}(t)$ | **Não reproduzido**: capacidade constante (`emt_vcb_constant_didt_capability`) | $\mathrm{d}i/\mathrm{d}t_0 + \sigma\,(t - T_{open})$ [REPO: `.mod`:50,96] |
| Rebote mecânico `T_bounce` | **Não reproduzido**, e a razão é registrada: o bloco correspondente do MODEL é **inerte** (corpo vazio) [REPO: `.mod`:124-128] | declarado em `DATA`, sem efeito |
| Máquina de estados | 5 estados, incluindo `arcing_hf` distinto de `arcing` | 3 estados (`1` fechada, `0` aberta, `2` reignindo — este último nunca atribuído) |
| Estado dielétrico inicial | $V_{wth}(0) = 0$ pela lei parabólica (`emt_vcb_zero_initial_withstand`) | $U_0 = 690$ V residual imediato |
| Acoplamento ao solver | Controlador Python chamado antes de cada passo; corte com **critério $I_{mar}$ do ATP** | TACS, com ***wiring* manual** até a v0.22.2 [REPO: `.mod`:34-37] |
| Contagem de reignições | `reignition_count` mais tempos, tensões e suportabilidades de cada evento (`VCBPoleResult`) | `reign_count` escalar |
| Teto de reignições | 200, declarado como salvaguarda **numérica**, com `WARNING` ao travar | inexistente |

O adaptador `vcb_from_mod_parameters` [REPO: `app/simulation/emt/vcb.py:830-905`] reproduz a parametrização legada sobre o kernel dedicado, com as quatro diferenças assumidas e declaradas na própria docstring.

### 6.7 Escalonamento de polos

`stagger_times` distribui os instantes de separação igualmente dentro da faixa de 14 a 25 ms [FATO: doc A, p. 3, IV-B e Tabela II]. **[FATO por omissão]** A não declara se 14–25 ms é a faixa dos instantes **absolutos** ou a **diferença** entre polos. A interpretação adotada — instantes absolutos — é declarada e justificada: é a única compatível com a janela simulada de 45 ms, e 11 ms de diferença entre polos seria mecanicamente implausível, já que o intervalo entre zeros de corrente consecutivos de fases distintas é $1/(6f) = 2{,}78$ ms a 60 Hz [INFERÊNCIA FÍSICA; REPO: `app/simulation/emt/vcb.py:128-140`].

---

## 7. *Snubber* a tiristor e a lacuna do nível de *breakover*

### 7.1 O que o Documento A descreve

Ramo em paralelo com os terminais da máquina, composto de **dois SCR em antiparalelo** formando chave CA bidirecional, mais **resistor de amortecimento $R_s$ em série**, dimensionado próximo da impedância de surto do circuito associado, com $R_s = 30\ \Omega$ por fase [FATO: doc A, p. 2, III-A e Tabela II, p. 3]. Ciclo de operação em quatro itens: regime transparente com SCR bloqueados; disparo por *breakover* do DIAC, dependendo **apenas** das condições elétricas locais, sem comando digital; amortecimento pela circulação em $R_s$; bloqueio natural no zero de corrente [FATO: doc A, p. 2, III-A, itens 1 a 4].

### 7.2 A lacuna, e a decisão de projeto que ela impõe

**[FATO por omissão]** O Documento A **não informa o nível de *breakover* do DIAC** em nenhuma das cinco páginas: nem no texto da Seção III-A, nem na Tabela II (que lista apenas $R_s = 30\ \Omega$), nem na legenda da Fig. 1. Sem ele, o instante de disparo — e portanto **todo o resultado da Tabela III** — **não é reprodutível a partir do artigo**.

Consequência de projeto, implementada: `ThyristorSnubber` torna `breakover_voltage_V` **parâmetro obrigatório, sem valor padrão**, e a mensagem de erro diz por quê. Um padrão silencioso disfarçaria uma escolha do implementador como dado do artigo [REPO: `app/simulation/emt/snubber.py:37-52,291-299`]. Faixa de referência a declarar como hipótese no laudo: acima da tensão de fase de pico em regime (3,40 kV para a barra de 4,16 kV) e abaixo do nível de proteção pretendido [INFERÊNCIA FÍSICA].

### 7.3 Representação e o que se perde

Os dois SCR são representados por **uma** `Switch` ideal bidirecional: do ponto de vista dos terminais, um par antiparalelo ideal disparado conduz nas duas polaridades sem queda, e qual dos dois conduz é interno ao par. O que se perde está declarado em `emt_snubber_ideal_valve_pair`: queda direta de condução (1 a 2 V por válvula), corrente de manutenção, $\mathrm{d}i/\mathrm{d}t$ e $\mathrm{d}v/\mathrm{d}t$ críticos de comutação e tempo de recuperação reversa [REPO: `app/simulation/emt/snubber.py:191-200`].

**Lógica implementada.** `blocked` → (`|v_ramo| ≥ V_bo`) → `conducting`, emulando o DIAC por nível, **apenas com a grandeza local**; uma vez disparado o SCR **trava** e não desliga por queda de tensão. `conducting` → (zero de corrente, por troca de sinal ou $|i| \le I_h$) → `blocked` [REPO: `app/simulation/emt/snubber.py:429-487`].

**O que se registra**, espelhando o que a camada digital de A adquire — *"o registro oscilográfico de alta resolução do transitório apenas durante a condução do SCR"* [FATO: doc A, p. 2, III-B]: a **janela de condução** (lista de pares $t_{on}, t_{off}$) e a **energia dissipada**

$$E_s = \int R_s\,i^2\,\mathrm{d}t \quad [\mathrm{J}] \tag{7.1}$$

com testes que a confrontam contra integral independente e verificam a escala com $R_s$ [REPO: `tests/test_emt_vcb_snubber.py:739,758`].

---

## 8. Validação

### 8.1 Estrutura da suíte

| Arquivo | Testes | Escopo |
|---|---|---|
| `tests/test_emt_kernel.py` | 94 | Montagem de matriz, regime contínuo, soluções analíticas, Bergeron, CDA, fatoração e cache, convergência, `CoupledRL` e trifásico, validação de entrada, sondas, **fontes primárias**, **caso de referência da Lista 02** |
| `tests/test_emt_referencia_eee873.py` | 35 | Regressão dígito a dígito contra as Listas 01 e 02 |
| `tests/test_emt_steady_state.py` | 43 | Partida fasorial, idempotência, ordem do resíduo, linha semeada |
| `tests/test_emt_jmarti.py` | 49 | Ajuste racional, fase mínima, atraso, modelo modal, ondas viajantes, viés de frente, integração com o solver |
| `tests/test_emt_vcb_snubber.py` | 52 | VCB, *snubber*, balanço de energia no corte |
| **Total do motor** | **273** | |
| `tests/test_pp_prognosis_core.py` | 176 | Núcleo de prognóstico (consumidor do vetor de estresse) |
| **Total executado** | **449** | `449 passed in 63.56s` [CÁLCULO PRÓPRIO desta sessão] |

### 8.2 Regressão contra a Lista 01 — modelos numéricos e ordem de convergência

| Caso | Referência do autor | Obtido | Veredito |
|---|---|---|---|
| §4.3 primeiro passo × ATP: $v_3(0{,}1\ \mu s)$ | 0,024814 V (ATP `tpbigg32`) | 0,024814 V | **BATE** (exato nas 6 casas publicadas) |
| §4.3 primeiro passo × ATP: $i(0{,}1\ \mu s)$ | 0,496278 mA | 0,496278 mA | **BATE** |
| Tabela 2 — trapezoidal × Laplace | 0,4749 V (2,56 %) / 0,4971 mA (5,37 %) | 0,474880 V (2,562 %) / 0,497081 mA (5,365 %) | **BATE** |
| Tabela 2 — Euler regressivo × Laplace | 2,4881 V (13,42 %) / 2,4998 mA (26,98 %) | 2,488118 V / 2,499850 mA | **BATE** |
| Tabela 2 — trapezoidal com partida corrigida | 0,0613 V (0,33 %) / 0,0612 mA (0,66 %) | 0,061300 V / 0,061205 mA | **BATE** |
| Tabela 3 — picos sucessivos, trapezoidal | 9,2534 / 6,7589 / 4,9368 / 3,6058 / 2,6337 mA; desvios $-0{,}12$ a $+0{,}02$ % | idênticos | **BATE** — erro de **fase**: amplitude preservada, $|$desvio$| < 0{,}15$ %, **não acumula** |
| Tabela 3 — picos sucessivos, Euler regressivo | 8,5995 / 4,5875 / 2,4480 / 1,3067 / 0,6968 mA; desvios $-7{,}18$ a $-73{,}54$ % | idênticos | **BATE** — erro de **amplitude**: amortecimento numérico monotonicamente crescente |
| §6.2 verificação 1 — analítica em $t - \Delta t/2$ | erro cai de 0,4749 V para 0,0613 V (redução de 7,8×) | 0,061248 V; redução de 7,75× | **BATE** com tolerância afrouxada de $5\times10^{-5}$ para $10^{-4}$ V, **justificada**: o autor cita o mesmo 0,0613 V para as duas verificações do §6.2, mas elas dão 0,06125 (deslocamento) e 0,06130 (partida corrigida), esta reproduzida com tolerância estrita |
| §6.2 Fig. 9 — ordem de convergência $p$ (6 passos, 0,4 a 0,0125 µs) | trapezoidal 1,02; corrigida 1,998; Euler 0,73 | **1,0244 / 1,9977 / 0,7270** | **BATE** — conclusão reproduzida: o atraso de meio passo na partida **mascara** a ordem 2; corrigida a partida, ela é recuperada |

### 8.3 Regressão contra a Lista 02, Questão 1 — curto-circuito na carga

| Caso | Referência | Obtido | Veredito |
|---|---|---|---|
| §2.3 fasor de regime, chave aberta (listagem do ATP) | $\hat{I} = 4{,}4320710624\angle{-24{,}6908953°}$ A; $Z_1 = 22{,}562815\angle{24{,}6909°}$ Ω | 4,432071068 ∠−24,690895171°; 22,562815 ∠24,690895° | **BATE**; tolerância $10^{-8}$ no módulo e $5\times10^{-7}$ no ângulo, **justificada**: o ATP resolve o fasor em precisão simples e imprime mais dígitos do que carrega (desvio $5{,}9\times10^{-9}$ A e $1{,}3\times10^{-7}$°, **do ATP**) |
| eq. (14) condições iniciais em $t=0$ | $i_L(0) = 4{,}026867$ A; $v_2(0)=97{,}986566$; $v_3(0)=80{,}537341$; $v_L(0)=17{,}449225$ V | idênticos | **BATE** |
| §2.4 resposta forçada e natural pós-curto | $Z_2 = 9{,}438253\angle86{,}9633°$ Ω; $|\hat{I}_2| = 10{,}595181$ A; $i(t_0^-) = -0{,}513266$ A; $i_f(t_0^+) = -9{,}886313$ A; $A_{nat} = 9{,}373048$ A; $\tau = 50$ ms | idênticos em todas as casas publicadas | **BATE** |
| §2.6 primeiro pico de corrente | 18,69 A ($\approx 1{,}76\times$ a amplitude de regime final) | 18,6926 A; razão 1,7643 | **BATE** |
| Tabela 1, linha 1 — rotina × analítica | $2{,}055\times10^{-3}$ A (0,0110 % do pico) | $2{,}054738\times10^{-3}$ A (0,0110 %) | **BATE** |
| Tabela 1, linha 2 — convenção do instante de comutação | $4{,}106\times10^{-3}$ A | $4{,}105320\times10^{-3}$ A entre as duas convenções do próprio motor; diferença é resposta natural pura, decaindo com $\tau = 50$ ms (verificado em 6 múltiplos de $\tau$) | **BATE** (o `.pl4` do ATP não está disponível; a grandeza que explica o desvio é interna e reprodutível) |
| Tabela 2 — erro **antes** do curto, 6 passos (100 a 2 µs) | 2,201e−4 / 5,503e−5 / 8,805e−6 / 2,201e−6 / 5,503e−7 / 8,805e−8 A; $p = 2{,}00$ | 2,2013e−4 / 5,5031e−5 / 8,8050e−6 / 2,2012e−6 / 5,5031e−7 / 8,8050e−8; $p = 2{,}0000$ | **BATE termo a termo** |
| Tabela 2 — erro **depois** do curto e previsão fechada $\Delta I = (\Delta t/2L)R_2|i(t_0^-)|$ | $R_2|i(t_0^-)| = 10{,}265314$ V; razões 0,9894 → 1,0002; $p = 1{,}00$ | 10,265314 V; razões **1,0085 → 1,0002** ($p = 1{,}0020$); absolutos 2,0547e−3 / 1,0269e−3 / 4,1068e−4 A contra 2,051e−3 / 1,026e−3 / 4,107e−4 ($\le 0{,}2$ %) | **BATE com divergência menor registrada** — ver §8.6(a) |

**Convenção do instante de comutação.** O controlador é chamado com o instante **já resolvido**, de modo que a mudança de estado só se reflete no passo seguinte — é a convenção do ATP, que avalia o estado das chaves **antes** de resolver cada passo, usando o instante anterior, e que reduz o desvio contra o ATP de $4{,}11\times10^{-3}$ A para $1{,}21\times10^{-5}$ A [LISTA: 02, §2.7 e Tabela 1]. A escolha estava correta mas **não documentada**; agora está [REPO: `app/simulation/emt/circuit.py:527-534`].

### 8.4 Regressão contra a Lista 02, Questão 2 — abertura de disjuntor a vácuo

| Caso | Referência | Obtido | Veredito |
|---|---|---|---|
| §3.3 regime fasorial | $Z_{reat} = 19{,}508791\angle75{,}1389°$ Ω; $Z_{tot} = 21{,}458977\angle75{,}1394°$ Ω; $\hat{i}_s = 4{,}660054\angle{-75{,}1394°}$ A; $\hat{v} = 90{,}912028\angle{-0{,}0005°}$ V; $\hat{i} = 4{,}661711\angle{-75{,}1448°}$ A; $i_C = 1{,}71$ mA | idênticos em **todas** as casas publicadas | **BATE** |
| eqs. (24)/(25) instante de corte exato e condições no corte | $i_s(t_0) = -3{,}9137$ A; $t_c = 32{,}359422$ ms; $v_0 = 84{,}862016$ V; $i_0 = -0{,}500615$ A; $\alpha = 50$; $\omega_0 = 20\,000$; $\omega_d = 19\,999{,}9375$; $f_d = 3\,183{,}09$ Hz; $T_d = 314{,}16\ \mu$s; $A_0 = 507{,}967$ V; $i_0/(\omega_d C) = 500{,}6$ V; $Z_0 = 1\,000\ \Omega$ | idênticos | **BATE** |
| (a) Tabela 3 — partida em regime × solução fasorial | $1{,}39\times10^{-10}$ V | $1{,}391953\times10^{-10}$ V | **BATE** (tolerância $5\times10^{-13}$ V = meia unidade no último dígito publicado) |
| **(b) Tabela 3 — PICO DA TRV (critério de aceite principal)** | **504,292 V — mesmo valor na rotina própria do autor E no ATP** | **504,29235 V** | **BATE.** Tolerância adotada $5\times10^{-4}$ V (relativa $10^{-6}$), **mais exigente que a própria concordância rotina × ATP publicada** (4,27e−4 V), e ainda assim passa |
| §3.7 pico analítico com corte exato | 506,170 V; diferença de 1,9 V (0,37 %) por quantização do corte | 506,1703 V; diferença 1,878 V (0,371 %). **Observação nova**: o supremo **contínuo** da mesma expressão é 506,190 V — os 0,02 V são resolução de amostragem, não do método | **BATE** |
| (c) §3.6 instante de corte × listagem do ATP | `*** Open switch "N3" to "N4" after 3.23600000E-02 sec.`; $t_{c,\text{num}}$ tabelado 32,361 ms | decisão de abrir em **32,360000 ms** (= impressão do ATP); primeira solução com a chave aberta em **32,361000 ms** (= Tabela 4) | **BATE nas duas convenções** (a conversão $t_{c,\text{num}} = $ `effective_open_time_s` $+\ \Delta t$ está isolada em função e documentada) |
| (d) §3.8 oscilação de período $2\Delta t$ no nó 3, **sem** CDA | $-4\,887{,}8$; $+5\,074{,}5$; $-4\,887{,}8$; $+5\,074{,}6$ V (rotina **e** ATP, dígito a dígito); amplitude prevista $\approx 4\,990$ V | idênticos; amplitude 4 989,9 V; oscilação **sustentada**; $v(t) = v_4$ **não** afetada, pico permanece 504,292 V | **BATE dígito a dígito** |

**Convergência da Tabela 4, linha a linha** [LISTA: 02, §3.7]:

| $\Delta t$ [µs] | $t_c$ ref. [ms] | $t_c$ obtido [ms] | atraso ref. [µs] | pico ref. [V] | pico obtido [V] |
|---|---|---|---|---|---|
| 4,00 | 32,364000 | **32,364000** | +4,578 | 501,37 | **501,3725** |
| 2,00 | 32,362000 | **32,362000** | +2,578 | 503,29 | **503,2873** |
| 1,00 | 32,361000 | **32,361000** | +1,578 | 504,29 | **504,2923** |
| 0,50 | 32,360000 | **32,360000** | +0,578 | 505,62 | **505,6153** |
| 0,25 | 32,359750 | **32,359750** | +0,328 | 505,84 | **505,8387** |

Monotonicidade das duas convergências e aproximação ao pico analítico (506,170 V) verificadas [REPO: `tests/test_emt_referencia_eee873.py:1118`].

### 8.5 Verificações independentes de física

| Verificação | Critério | Resultado | Onde |
|---|---|---|---|
| **Balanço de energia** em tanque LC sem perdas | $E = \tfrac12 Li^2 + \tfrac12 Cv^2$ constante (o trapézio é conservativo) | desvio relativo $< 10^{-4}$ com $\Delta t = 10$ ns em 1 ms | `tests/test_emt_kernel.py:335` |
| Frequência do tanque LC | $f_0 = 1/(2\pi\sqrt{LC}) = 5\,032{,}92$ Hz | `rel=1e-4` sobre 20 cruzamentos | `tests/test_emt_kernel.py:349` |
| Balanço de energia no **corte do VCB** | energia do indutor no instante do corte transferida à capacitância | confere | `tests/test_emt_vcb_snubber.py:342,362` |
| Conservação de energia em **linha sem perdas** (JMarti) | — | confere | `tests/test_emt_jmarti.py:574` |
| **Ordem 2** com excitação senoidal | razão de erro $\to 0{,}25$ ao halvar $\Delta t$ | `approx(0.25, rel=0.05)` em três passos | `tests/test_emt_kernel.py:826` |
| **Ordem 2 no degrau contínuo** (o CDA de partida a preserva) | idem | `approx(0.25, rel=0.05)` | `tests/test_emt_kernel.py:835` |
| Convergência do pico do RLC ao analítico | erro decrescente com o refino | confere | `tests/test_emt_kernel.py:858` |
| **Estabilidade** do ajuste racional | todos os polos no semiplano esquerdo; polos instáveis **refletidos** | confere | `tests/test_emt_jmarti.py:243` |
| Linha de Bergeron em CC | $I = (v_k - v_m)/R$ **exato** (§5.1) | confere | `tests/test_emt_kernel.py`, `TestLinhaBergeron` |
| Comutação altera **uma** linha, posto invariante | dimensão e posto constantes | confere | `tests/test_emt_kernel.py`, `TestFontesPrimarias` |
| Cache: 2 topologias ⇒ 2 fatorações | independentemente do número de comutações | confere | `tests/test_emt_kernel.py:660` |

**Papel do campo $I_{mar}$, verificado experimentalmente.** Referência: *"sem o campo Imar o ATP esperaria um zero natural de corrente e a sobretensão praticamente desapareceria"* [LISTA: 02, §3.6]. Obtido: com $I_{mar} = 0{,}5$ A o pico é 504,29 V; baixando a margem para 2 mA, a interrupção ocorre com 1,005 mA e o pico cai a **90,912 V — exatamente a tensão de pico de regime, sem sobretensão alguma**. **BATE**: o mecanismo do Documento A é confirmado — é a **corrente cortada** que gera a solicitação [REPO: `tests/test_emt_referencia_eee873.py:1352`].

### 8.6 Divergências registradas, e por que não são falhas

**(a) Razões da Tabela 2 da Questão 1 convergem por cima, não por baixo.** As razões do autor vêm por **baixo** (0,9894 → 1,0002) e as nossas por **cima** (1,0085 → 1,0002). Causa identificada: nas rotinas do autor, `Δt = 100*1e-6` vale $9{,}999999999999999\times10^{-5}$ em precisão dupla, de modo que $t(801)$ cai **logo abaixo** de 0,08 s e a chave fecha um passo depois; aqui usam-se literais exatos e o fechamento cai em $t_0$. **As duas famílias convergem para a MESMA previsão fechada da eq. (16), sem nenhum ajuste** — o que valida a previsão, não a implementação de uma delas [CÁLCULO PRÓPRIO].

**(b) Paliativo $R_p = 2L_1/\Delta t = 10$ kΩ: preço 3× menor que o publicado.** Referência: desvio de 0,249 V em $v(t)$, 0,049 % do pico. Obtido: 0,0760 V, 0,015 %. Hipótese documentada no teste: `simula_q2(...,Rp)` do autor reaproveita condições iniciais calculadas **sem** $R_p$, enquanto `Solver(init='steady_state')` resolve o fasor do circuito **efetivamente montado**, $R_p$ incluído — o que elimina um pequeno transitório de partida. O teste verifica o **limite publicado** ($< 0{,}05$ % do pico), satisfeito com folga, e **não** o número [REPO: `tests/test_emt_referencia_eee873.py:1234`]. O fator de propagação da eq. (30) é reproduzido **exatamente**: $-1{,}0$ sem $R_p$ e $0{,}0$ com $R_p$.

**(c) Pico da TRV na configuração padrão do motor (CDA ligado): 505,148 V.** Não há valor publicado; as balizas são 504,292 V (trapezoidal pura) e 506,170 V (analítico com corte exato). O valor obtido fica **entre as duas** — isto é, o CDA **não degrada** a estimativa de sobretensão, **aproxima-a do analítico**. Aceito com tolerância declarada de 1,0 V (0,2 %). A partida em regime permanece exata ($1{,}39\times10^{-10}$ V) e o instante de corte é o mesmo (32,361 ms), **porque o critério é de corrente e não de relógio** [REPO: `tests/test_emt_referencia_eee873.py:1282`].

### 8.7 Defeito encontrado e corrigido pela própria regressão

**Base de tempo do solver.** A marcha acumulava $\Delta t$ no relógio, e o erro de arredondamento crescia com o número de passos: em 1 600 passos de 50 µs chegava-se a $t = 0{,}07999999999999935$ s (deriva de $1{,}4\times10^{-14}$ s por acumulação), **abaixo** do 0,08 s exato, o que deslocava de um passo a classificação pré/pós-comutação contra a malha exata do ATP ($n\Delta t$) e das rotinas do autor ($t = (0{:}N-1)\Delta t$). Corrigido para base **indexada**, $t_n = t_{\text{origem}} + n\Delta t$, com erro de uma única operação, independente da duração [REPO: `app/simulation/emt/circuit.py:1188-1199`]. **449 testes passam depois da correção.** Este é o argumento mais forte a favor da regressão contra as listas: o defeito era invisível aos testes sintéticos e só apareceu no confronto dígito a dígito com o ATP.

---

## 9. *Benchmark* contra o Documento A: reportado honestamente

### 9.1 O que se compara

Tabela III de A, pico de TRV [kV] e RRRV [kV/µs] por fase [FATO: doc A, Tabela III, p. 3], codificada em `DOC_A_TABLE_III` [REPO: `app/simulation/emt/cases/motor_switching.py:149`] **como referência de confronto, não de aceite** — a advertência está no próprio módulo.

### 9.2 Resultado medido nesta sessão

Caso padrão (`MotorSwitchingCase()`, $\Delta t = 1$ µs, janela 45 ms, cabos Bergeron, `init='zero'`), tensão no nó do motor:

| Fase | Doc A sem *snubber* [kV; kV/µs] | Obtido sem *snubber* | Doc A com *snubber* | Obtido com *snubber* ($V_{bo} = 6$ kV) |
|---|---|---|---|---|
| A | $-30{,}24$; 13,90 | $-3{,}15$; **0,04** | 6,35; 3,28 | $-3{,}15$; 0,04 |
| B | $+41{,}44$; 15,05 | $-5{,}76$; **0,41** | 13,65; 13,11 | $-5{,}76$; 0,41 |
| C | $-38{,}30$; 19,00 | $+5{,}66$; **0,41** | $-9{,}98$; 9,43 | $+5{,}66$; 0,41 |

Reignições por polo: 4 / 4 / 3. Energia no *snubber*: **$E_s = 0$ J nas três fases** — o ramo **nunca dispara**, porque o pico jamais alcança os 6 kV do *breakover* hipotético. Pico de TRV **através do disjuntor**: 79,6 / 101,0 / 101,0 V. Estado final dos três polos: `arcing_hf` — **nenhum polo alcança a interrupção definitiva dentro da janela** [CÁLCULO PRÓPRIO desta sessão].

**Veredito: o *benchmark* NÃO fecha.** A discrepância é de fator $\approx 7$ em $V_{pk}$ e de **duas ordens de grandeza** em $\mathrm{d}v/\mathrm{d}t$.

### 9.3 Causa dominante, identificada e quantificada

Com os parâmetros publicados de A e a convenção física de $\mathrm{d}i/\mathrm{d}t$, **nenhum polo alcança a primeira interrupção bem-sucedida**: um passo depois do corte a suportabilidade parabólica vale $V_{wth}(1\ \mu s) = 0{,}801$ V, a TRV já vale dezenas de volts e o *gap* reignita; a sequência se repete a cada zero de corrente de 60 Hz [CÁLCULO PRÓPRIO; REPO: `KNOWN_LIMITATIONS["emt_case_doc_a_rrds_prevents_clearing"]`].

Verificado nesta sessão que **a ambiguidade do $\mathrm{d}i/\mathrm{d}t$ não é a causa**: com a convenção invertida (leitura literal do texto de A e do `.mod` legado) os picos são **os mesmos** ($-3{,}15$ / $-5{,}76$ / $+5{,}66$ kV), mudando apenas a contagem de reignições de 4/4/3 para 1/1/1, e os três polos terminam igualmente em `arcing_hf` [CÁLCULO PRÓPRIO desta sessão].

Ensaio de sensibilidade registrado: elevar $A$ para 200 kV/ms — apenas uma ordem de grandeza acima da faixa publicada de 2 a 50 kV/ms — produz **interrupção limpa e TRV de 6,6 a 7,1 kV**, isto é, cerca de 2 pu, que é o valor clássico [CÁLCULO PRÓPRIO].

### 9.4 O que falta para fechar, em ordem de impacto

1. **Dados de rede omitidos por A** (`emt_case_undisclosed_network_data`): A não publica impedância de curto da fonte, dados do transformador, comprimentos e parâmetros dos cabos nem a capacitância parasita do motor com precisão suficiente. Enquanto isso não for obtido, **a conclusão defensável é que a Tabela III não é reprodutível a partir do artigo isolado** — não que os 41,44 kV estejam errados, nem que este modelo os reproduza.
2. **Nível de *breakover* do DIAC** (§7.2): sem ele o resultado "com *snubber*" da Tabela III é indeterminado por construção.
3. **Partida do repouso** (`emt_case_no_steady_state_start`): o caso mantém `init='zero'` **deliberadamente**, porque A não informa o estado de regime da rede a montante e uma semeadura fasorial sobre dados presumidos daria falsa precisão. Consequência medida: com $L/R = 13{,}0$ ms na variante da Fig. 2, a componente contínua ainda vale **34 %** em $t = 14$ ms, e os instantes de separação de 14 a 25 ms dão apenas 0,8 a 1,5 ciclo de acomodação [CÁLCULO PRÓPRIO].
4. **Cabos LCC/JMARTI de A**: o caso comutado para `'jmarti'` gera hoje tabelas do modelo $R'L'C'$ com $R'$ **constante** [HIPÓTESE] — sem efeito pelicular nem retorno pela terra —, de modo que a dependência de frequência representada é menos acentuada que a real, e com o $R'$ padrão a diferença ante o Bergeron é praticamente nula (TRV 101,18 V contra 101,00 V). **Para o estudo definitivo as tabelas devem vir do `CABLE CONSTANTS` do caso ATP.**
5. **Motor concentrado** (`emt_case_motor_lumped_rl`): ramo $R$–$L$ série com capacitância em paralelo, a mesma representação da Fig. 2 de A. **Não há distribuição da tensão entre espiras**, de modo que o $V_{pk}$ no nó do motor **não** é a tensão entre as primeiras espiras — a fração da frente que ali aparece é entrada externa do modelo de dano, não saída deste caso.
6. **Ambiguidade do ramo RL** (`emt_case_rl_branch_ambiguous`) e **ausência de acoplamento entre fases** (`emt_case_no_phase_coupling`).

### 9.5 O que o *benchmark* aberto **não** invalida

A validação do §8 é contra as Listas 01 e 02, que são **casos do próprio autor validados contra o ATP com valores publicados**, e ela fecha dígito a dígito. O *benchmark* de A é um confronto contra um artigo cujos dados de entrada estão incompletos, e a lacuna está **do lado do artigo**, não do kernel. Misturar as duas coisas seria erro epistêmico: o kernel está validado como **solucionador**; o caso de A está **não reproduzível** como caso.

---

## 10. Desempenho medido e o caminho para C++

### 10.1 Medições desta sessão

| Caso | $n$ (dimensão MNA) | Passos | Tempo de parede | µs/passo | Fatorações / acertos de cache |
|---|---|---|---|---|---|
| Lista 02 Q2, $\Delta t = 4$ µs, 100 ms | 7 | 25 000 | 0,297 s | 11,88 | 2 / 0 |
| Lista 02 Q2, $\Delta t = 1$ µs, 100 ms | 7 | 100 000 | 1,151 s | 11,51 | 2 / 0 |
| Lista 02 Q2, $\Delta t = 0{,}25$ µs, 100 ms | 7 | 400 000 | 4,690 s | 11,72 | 2 / 0 |
| Caso de manobra (Bergeron), 45 ms a 1 µs | 27 | 45 000 | 2,21 s | 49,2 | 4 / 19 |
| Caso de manobra **com *snubber*** | 33 | 45 000 | 2,51 s | 55,8 | 4 / 19 |
| Caso de manobra **com JMarti** | 27 | 45 000 | 12,85 s | 285,6 | 4 / 19 |

Observação relevante: o custo por passo é **praticamente independente de $\Delta t$** e cresce com o **número de componentes**, não com o condicionamento — o que já antecipa o resultado do perfil.

### 10.2 Onde o tempo é gasto — e por que isso decide a arquitetura da migração

Perfil do caso de manobra sob `cProfile` (13 558 858 chamadas, 8,15 s sob o perfilador contra 2,21 s sem ele) [CÁLCULO PRÓPRIO desta sessão]:

| Item | `tottime` | Chamadas | Comentário |
|---|---|---|---|
| `components.node_voltage` | 0,816 s | 2 971 890 | Leitura de tensão nodal com sentinela de terra |
| `line._TravelHistory.value_at` | 0,652 s | 270 210 | Interpolação de histórico de trânsito |
| `circuit.Solver._advance` | 0,466 s | 45 035 | Laço do passo |
| `probes.Probe.record` | 0,460 s | 540 000 | Registro de sondas |
| `circuit.Circuit.assemble_rhs` | 0,431 s | 45 035 | Montagem do lado direito |
| **`_Factorization.apply` + `Solver._solve` (a álgebra linear)** | **0,160 s** | 45 035 | **1,96 % do total** |

**Conclusão objetiva: o gargalo não é a álgebra linear — é o *overhead* do interpretador nas estampas, no `commit` e nas sondas.** Trocar por LAPACK, esparsidade ou fatoração mais esperta **não compra praticamente nada**. Um laço interno em C++ compra o resto.

### 10.3 Extrapolação para $10^3$–$10^4$ execuções

| Cenário | $10^3$ execuções | $10^4$ execuções |
|---|---|---|
| Caso de manobra, Bergeron, 1 processo | 37 min | **6,3 h** |
| Caso de manobra, Bergeron, 8 processos | 4,7 min | 47 min |
| Caso de manobra, JMarti, 1 processo | 3,6 h | **35,7 h** |
| Caso de manobra, JMarti, 8 processos | 27 min | 4,5 h |

[CÁLCULO PRÓPRIO: extrapolação linear das medições da §10.1, com escalonamento ideal por processo. O escalonamento por processo é **plausível e não medido**: o kernel é puro e determinístico, sem estado global, o que torna a paralelização pela dimensão de Monte Carlo trivialmente correta — mas nenhum *harness* de execução em massa existe hoje, e o custo de partida do processo Python não está contabilizado.]

### 10.4 Critério objetivo de migração

A migração do laço interno para C++ atrás da mesma API deve ser aberta quando as **três** condições forem simultaneamente verdadeiras — e não antes:

1. **Orçamento excedido com paralelismo já explorado**: o estudo alvo exigir tempo de parede superior ao seu orçamento **depois** de aplicado o paralelismo por processo sobre a dimensão de Monte Carlo. Pelo quadro da §10.3, isso ocorre primeiro no caminho **JMarti**, não no Bergeron.
2. **Perfil ainda dominado pelo interpretador**: mais de 90 % do `tottime` em estampas, `commit` e sondas, e não em álgebra linear. Hoje: **98 %** [CÁLCULO PRÓPRIO, §10.2]. Se um dia a álgebra linear passar a dominar (redes com $n$ na casa dos milhares), a resposta correta deixa de ser C++ e passa a ser **esparsidade**, o que é outra decisão.
3. **API congelada por regressão**: os 273 testes do motor — em particular os 35 da regressão EEE873, que comparam dígito a dígito contra o ATP — devem servir de contrato para validar a substituição. Sem eles a migração é indefensável, porque não haveria como distinguir uma diferença de implementação de um erro.

**Escopo mínimo da migração, quando ocorrer**: `Component.stamp_rhs`, `Component.commit`, `Circuit.assemble_rhs`, `_Factorization.apply` e `_TravelHistory.value_at` — que somam, hoje, cerca de 60 % do `tottime` medido, mais o `overhead` de despacho que desaparece por construção. **Fora do escopo**: a lógica de controle (VCB, *snubber*, controladores), que roda uma vez por passo e cujo custo é desprezível, e o ajuste racional do JMarti, que roda uma vez por construção do modelo.

### 10.5 A restrição do `Dockerfile` travado

`Dockerfile` e `docker-compose.yml` estão na **lista travada** de arquivos que não podem ser tocados. Isso tem consequência direta e não negociável sobre o desenho da migração:

* **não** se pode acrescentar cadeia de compilação (compilador, `build-essential`, cabeçalhos de Python) à imagem para compilar a extensão no destino;
* portanto a extensão nativa, quando existir, deve chegar **pré-compilada** (rodas binárias por plataforma) e ser instalada como dependência comum, **ou** o projeto deve manter um **caminho puro-Python selecionado em tempo de importação**, com a extensão como aceleração opcional;
* a segunda alternativa é a defensável para este projeto, porque preserva a propriedade que hoje sustenta a auditabilidade: **a suíte de 449 testes precisa passar sem a extensão**, e a extensão precisa ser validada contra ela.

Registre-se ainda que `requirements.txt` declara `numpy, pydantic, PyYAML, matplotlib, PySide6, pytest, openpyxl`, e que **`scipy` não é dependência e não foi acrescentada** por nenhum módulo do motor — inclusive o ajuste racional do JMarti usa apenas `numpy.linalg` [REPO: `app/simulation/emt/jmarti.py:120-124`].

---

## 11. Integração com o prognóstico e o papel do `.atp`

### 11.1 A ponte simulação → prognóstico

`probes.to_stress_profile` converte a série de uma sonda de tensão em perfil de estresse, delegando a `app.postprocessor.prognosis.stress_profile.extract_stress_events` e convertendo volts para quilovolts [REPO: `app/simulation/emt/probes.py:248-288`]. O `source` padrão identifica o motor dedicado (`emt:<nome da sonda>`), **para que o laudo distinga séries simuladas de oscilografias reais** — requisito de auditoria, não conveniência.

A cadeia é direta, **sem arquivo intermediário**: sonda → série $(t, v)$ → `extract_stress_events` → `StressProfile` → acumulador de dano D1–D7 → RUL. É a diferença estrutural em relação ao caminho do ATP, que exigiria escrever `.atp`, executar o binário, ler `.pl4` e converter.

### 11.2 O vetor de estresse $s_{m,j}$ e quem produz cada componente

| Componente de $s_{m,j}$ | Produzido por | Ressalva |
|---|---|---|
| $V_{pk}$ [kV] | `MotorSwitchingModel.trv_summary()`, pico **com sinal** da amostra de maior módulo, como na Tabela III de A | Cota superior com Bergeron sem perdas; **não** vale para Bergeron com perdas (§5.5) |
| $\mathrm{d}v/\mathrm{d}t$ (RRRV) [kV/µs] | maior derivada de primeira ordem entre amostras consecutivas | **Cota inferior** do valor real quando o passo for da ordem do tempo de frente [REPO: `app/simulation/emt/cases/motor_switching.py:703-712`] |
| $n_r$ (reignições por polo) | `MotorSwitchingModel.reignition_counts` | Sensível à convenção de $\mathrm{d}i/\mathrm{d}t$, cujo sinal do efeito se inverte (§6.5) |
| $T_1$ (tempo de frente) | derivado da série da sonda | **Nulo por construção** no Bergeron; 1,29 µs no JMarti sobre a mesma frente (§5.5) |
| $E_s$ [J] | `MotorSwitchingModel.snubber_energy_J` | Só o resistor: `emt_snubber_energy_from_resistor_only` |

**Correção de premissa registrada na Etapa 3, confirmada aqui:** o `RRRV` do repositório legado é taxa **média** até o pico, não a derivada instantânea que o vetor de estresse exige [REPO: `app/analysis/transient_metrics.py:131`]; o motor dedicado expõe a derivada máxima entre amostras consecutivas.

### 11.3 O `.atp` como fonte da verdade — e a lacuna que resta

A decisão do autor é que o `.atp` permanece **fonte única da verdade do caso técnico**, e o motor o **resolve**, não o substitui como registro [REPO: `app/simulation/emt/__init__.py:17-21`]. Verificado que o pacote não toca `app/simulation/runner.py`, que continua sendo o caminho do ATP.

**A lacuna é esta, e é a mais importante deste documento:** o kernel **não lê `.atp`**. Todo caso é construído em Python — `MotorSwitchingCase.build()` monta o circuito a partir de `dataclasses` de parâmetros [REPO: `app/simulation/emt/cases/motor_switching.py:823-936`]. Consequência: **o caso resolvido e o caso registrado no `.atp` são dois objetos distintos, mantidos em sincronia manualmente**, o que contraria a própria decisão que os declara como um só. Enquanto um leitor de cartões `.atp` → `Circuit` não existir, a afirmação "o `.atp` é a fonte da verdade" é uma **intenção de arquitetura**, não uma propriedade do código.

### 11.4 Estado de integração no repositório

Nenhum módulo fora de `app/simulation/emt/` importa o pacote [CÁLCULO PRÓPRIO: `grep -rn "simulation.emt" app/ --include=*.py` fora do pacote → vazio]. Não há `Feature` comercial, ação de menu, chave em `STANDARDS_CATALOG` global, laudo, string i18n nem entrada em `CHANGELOG.md`/`version.py`. O motor é, hoje, um ***backend* órfão** — condição proibida pelas convenções do repositório desde a v3.1.0 [REPO: `docs/research/rul_isolamento/anexos/repo/convencoes_auditoria_gui_docs.md:171`]. A remediação está desenhada no Sprint 1 da Etapa 3 [REPO: `docs/research/rul_isolamento/04_ARQUITETURA_MVP_RUL_OLIVAS.md`, §6].

---

## 12. Limitações declaradas e trabalho futuro

### 12.1 Catálogo de limitações: onde está e um defeito de agregação

| Dicionário | Chaves | Agregado à fachada `app.simulation.emt.KNOWN_LIMITATIONS`? |
|---|---|---|
| `app/simulation/emt/__init__.py:311` (kernel) | 12 próprias | — (é a fachada) |
| `jmarti.JMARTI_LIMITATIONS` (`:2251`) | 7 | **Sim**, com verificação de colisão [REPO: `app/simulation/emt/__init__.py:452-456`] |
| `vcb.KNOWN_LIMITATIONS` (`:1003`) | 8 | **NÃO** |
| `snubber.KNOWN_LIMITATIONS` (`:621`) | 6 | **NÃO** |
| `cases/motor_switching.KNOWN_LIMITATIONS` | 8 | **NÃO** |
| **Total real** | **41** | **Alcançáveis pela fachada: 19** |

**Item em aberto, encontrado nesta sessão:** as 14 chaves de `vcb.py` e `snubber.py` e as 8 do caso **não são agregadas** à fachada, embora `jmarti.py` o seja. Consequência prática: um laudo que enumere `app.simulation.emt.KNOWN_LIMITATIONS` **omitirá silenciosamente** todas as limitações do disjuntor a vácuo, do *snubber* e do caso de manobra — inclusive `emt_vcb_didt_convention_ambiguous` e `emt_snubber_breakover_not_published`, que são exatamente as que **precisam** aparecer em qualquer laudo do estudo de A [CÁLCULO PRÓPRIO: verificado por `import` nesta sessão]. Registre-se ainda que a contagem de "27 limitações do kernel" citada no documento 04 corresponde a 19 + 8 e também está desatualizada em relação às 41 existentes.

### 12.2 Limitações estruturais do kernel

| Chave | Conteúdo essencial |
|---|---|
| `emt_linear_components_only` | Os ramos ESTAMPADOS são lineares: não há saturação, histerese nem resistência de arco dependente da corrente. **Superada em parte**: elementos não lineares entram por compensação (`nonlinear.py`) e o para-raios está implementado (`arrester.py`) — ver `09_PARA_RAIOS_E_CRITERIO_DE_ACEITACAO.md` |
| `emt_dense_lu_no_sparsity` | Matriz densa; sem esparsidade — decisão justificada por medição (§2.6), a rever se $n$ crescer |
| `emt_switching_quantized_to_step` | Instante efetivo de manobra quantizado em $\Delta t$; efeito medido em [LISTA: 02, Tabela 4] |
| `emt_cda_only_on_topology_change` | CDA disparado por mudança de topologia (e por $t=0$, conforme o modo de partida) |
| `emt_cda_residual_in_stiff_networks` | Um par de meios-passos reduz o artefato por $\approx(1+R\Delta t/2L)^2$, não o anula; `cda_full_steps=2` mitiga **mas é extensão não publicada** |
| `emt_cda_half_step_not_recorded` | A amostra de $t+\Delta t/2$ é descartada por padrão, o que é o correto; o pico registrado pode ficar abaixo do calculado pelo solver — resolver reduzindo $\Delta t$ |
| `emt_steady_state_single_frequency` | Uma única frequência; harmônicos, componente contínua e fontes de frequências distintas levantam erro em vez de semear errado |
| `emt_steady_state_residual_deviation` | Resíduo permanente de ordem $(\omega\Delta t)^2/12$ (§4.4) |
| `emt_steady_state_line_interpolation` | Erro de interpolação do histórico quando $\tau$ não é múltiplo de $\Delta t$; linha em meia onda sem perdas é singular |
| `emt_constant_parameter_line`, `emt_single_mode_line` | Bergeron: sem dependência de frequência nem acoplamento entre condutores |
| `emt_ideal_switch_no_arc` | A chave é ideal; arco, rigidez de recuperação e corte pertencem ao controlador |

### 12.3 Limitações do modelo dependente da frequência

`emt_jmarti_constant_real_modal_matrix` (matriz modal real e constante — a aproximação característica do método; a de autovetores de $[Y][Z]$ é função da frequência e complexa, e é o que os modelos de domínio de fases vieram corrigir); `emt_jmarti_single_conductor_default` (o componente padrão é monomodal; `ModalJMartiLine` existe, mas **a matriz de transformação e os parâmetros por modo são entrada do usuário**, não calculados a partir da geometria de um cabo real); `emt_jmarti_no_steady_state_init` (`init='steady_state'` **não** suporta a linha JMarti e levanta `UnsupportedComponentError` — contrato fixado por teste, deliberadamente preferível a uma semeadura errada); `emt_jmarti_fit_is_the_model` (o que se simula é o **ajuste**, não a tabela; medido: $Y_c(0)$ do ajuste dá $2{,}2\times10^{-4}$ S contra $5{,}4\times10^{-4}$ S da tabela na primeira amostra, porque $Y_c(0)$ verdadeiro tende a zero e a faixa começa em 1 Hz); `emt_jmarti_hybrid_recursion` (o par $c_1, c_2$ é **escolha própria não publicada**, feita para compatibilidade com o CDA — **deve ser declarado no laudo**); `emt_jmarti_delay_interpolation`; `emt_jmarti_no_passivity_enforcement` (impõe-se **estabilidade**, não **passividade** no sentido forte: ajuste estável porém não passivo pode gerar crescimento de energia em rede com realimentação).

### 12.4 Trabalho futuro, em ordem de prioridade

1. **Leitor de cartões `.atp` → `Circuit`** (§11.3) — sem ele a decisão de fonte única da verdade não se realiza no código.
2. **Agregar `vcb`, `snubber` e o caso à fachada de `KNOWN_LIMITATIONS`** (§12.1) — defeito de laudo, correção de baixo custo e alto impacto.
3. **Obter os dados de rede omitidos por A** e as tabelas de `CABLE CONSTANTS` do caso ATP, únicos caminhos para fechar §9.
4. **Retirar o motor da condição de *backend* órfão** (§11.4): `Feature`, ação de menu, laudo, i18n, `CHANGELOG`.
5. **Condições iniciais da linha em modo `zero` com histórico pré-carregado**, para casos em que a janela de acomodação de $\tau$ seja inviável.
6. ~~**Não linearidades** (saturação de transformador, para-raios) por compensação, na linha de [FONTE: Dommel 1971].~~ **Feito para o para-raios** (`app/simulation/emt/nonlinear.py`, `arrester.py`), com a álgebra verificada contra solução analítica; a saturação de transformador continua pendente e usa o mesmo mecanismo.
7. **Traçado de assíntotas de Bode** como rotina de ajuste alternativa, caso se queira reproduzir literalmente o procedimento de 1982.
8. **Migração do laço interno para C++**, apenas quando as três condições da §10.4 forem satisfeitas.

---

## 13. Referências

### Fontes primárias (texto integral acessado nesta sessão)

DOMMEL, H. W. Digital computer solution of electromagnetic transients in single- and multiphase networks. **IEEE Transactions on Power Apparatus and Systems**, v. PAS-88, n. 4, p. 388-399, abr. 1969.

DOMMEL, H. W. Nonlinear and time-varying elements in digital simulation of electromagnetic transients. **IEEE Transactions on Power Apparatus and Systems**, v. PAS-90, n. 6, p. 2561-2567, nov./dez. 1971.

HO, C.-W.; RUEHLI, A. E.; BRENNAN, P. A. The modified nodal approach to network analysis. **IEEE Transactions on Circuits and Systems**, v. CAS-22, n. 6, p. 504-509, jun. 1975.

LIN, J.; MARTÍ, J. R. Implementation of the CDA procedure in the EMTP. **IEEE Transactions on Power Systems**, v. 5, n. 2, p. 394-402, maio 1990.

MAHSEREDJIAN, J. et al. On a new approach for the simulation of transients in power systems. **Electric Power Systems Research**, v. 77, n. 11, p. 1514-1520, 2007.

### Trabalhos do autor (casos de referência validados contra o ATP)

[AUTOR DESTE REPOSITÓRIO]. **Lista de exercícios 01 — EEE873: Análise de Redes Elétricas no Domínio do Tempo** (prof. Alberto De Conti). Programa de Pós-Graduação em Engenharia Elétrica, Universidade Federal de Minas Gerais. Modelos numéricos de indutor e capacitor (trapezoidal e Euler regressiva), solução analítica por Laplace do Exemplo A, solução nodal, ordem de convergência, código MATLAB e arquivo `.atp`. Citado como [LISTA: 01, seção]. — **[INSERIR CITAÇÃO]**: a forma nominal ABNT depende de dados de autoria e de data que não devem ser presumidos aqui.

[AUTOR DESTE REPOSITÓRIO]. **Lista de exercícios 02 — EEE873: Análise de Redes Elétricas no Domínio do Tempo** (prof. Alberto De Conti). Programa de Pós-Graduação em Engenharia Elétrica, Universidade Federal de Minas Gerais. Análise nodal modificada e modelagem de chaves; Questão 1, curto-circuito na carga de circuito RL; Questão 2, abertura de disjuntor a vácuo alimentando reator, com Tabelas 1 a 4 e comparação contra o ATP. Citado como [LISTA: 02, seção]. — **[INSERIR CITAÇÃO]**: idem.

### Fontes secundárias efetivamente consultadas

GUSTAVSEN, B.; SEMLYEN, A. Rational approximation of frequency domain responses by vector fitting. **IEEE Transactions on Power Delivery**, v. 14, n. 3, p. 1052-1061, jul. 1999.

SEMLYEN, A.; DABULEANU, A. Fast and accurate switching transient calculations on transmission lines with ground return using recursive convolutions. **IEEE Transactions on Power Apparatus and Systems**, v. PAS-94, n. 2, p. 561-571, mar./abr. 1975.

DERI, A.; TEVAN, G.; SEMLYEN, A.; CASTANHEIRA, A. The complex ground return plane: a simplified model for homogeneous and multi-layer earth return. **IEEE Transactions on Power Apparatus and Systems**, v. PAS-100, n. 8, p. 3686-3693, ago. 1981.

MARTÍ, J. R. Accurate modelling of frequency-dependent transmission lines in electromagnetic transient simulations. **IEEE Transactions on Power Apparatus and Systems**, v. PAS-101, n. 1, p. 147-157, jan. 1982. — **Texto integral NÃO acessado nesta sessão**; números de equação e de página aparecem como [INSERIR CITAÇÃO] em `app/simulation/emt/jmarti.py`.

MARTÍ, J. R.; LIN, J. Suppression of numerical oscillations in the EMTP. **IEEE Transactions on Power Systems**, v. 4, n. 2, p. 739-747, 1989. — Artigo do **conceito**; a implementação segue Lin & Martí (1990).

DOMMEL, H. W. **Electromagnetic Transients Program Reference Manual (EMTP Theory Book)**. Portland: Bonneville Power Administration, 1986. §4.2.1.4 (forma refinada da aproximação $R/4$, $R/2$, $R/4$).

MARTINEZ-VELASCO, J. A. (ed.). **Transient Analysis of Power Systems: Solution Techniques, Tools and Applications**. Chichester: Wiley/IEEE Press, 2015. cap. 2.

GREENWOOD, A. **Electrical Transients in Power Systems**. 2. ed. New York: Wiley, 1991. cap. 5 e 10.

VAN DER SLUIS, L. **Transients in Power Systems**. Chichester: Wiley, 2001. cap. 4-6.

WONG, S. M.; SNIDER, L. A.; LO, E. W. C. Overvoltages and reignition behavior of vacuum circuit breaker. In: **6th International Conference on Advances in Power System Control, Operation and Management (APSCOM)**, 2003, p. 653-658. DOI: 10.1049/cp:20030663.

ABDULAHOVIC, T.; THIRINGER, T.; REZA, M.; BREDER, H. Vacuum circuit-breaker parameter calculation and modelling for power system transient studies. **IEEE Transactions on Power Delivery**, v. 32, n. 3, p. 1165-1172, 2017. DOI: 10.1109/TPWRD.2014.2357993.

FARIA DA SILVA, F. et al. **An advanced transmission line and cable model in Matlab for the simulation of power-system transients**. IntechOpen, 2012. Disponível em: https://www.intechopen.com/chapters/39330. Acesso em: 3 set. 2026.

COLIB. **FDLine — frequency dependent line model**. Disponível em: https://colib.net/models/6-NetworkComponents/Line/FDLine/. Acesso em: 3 set. 2026.

MANITOBA HYDRO INTERNATIONAL. **PSCAD/EMTDC Help — Frequency Dependent Models**. Disponível em: https://www.pscad.com/webhelp/EMTDC/Transmission_Lines/Frequency_Dependent_Models.htm. Acesso em: 3 set. 2026.

SINTEF. **The Vector Fitting Web Site**. Disponível em: https://www.sintef.no/en/software/vector-fitting/. Acesso em: 3 set. 2026.

CIGRE WORKING GROUP A3.26. **Tools for the simulation of the effects of the internal arc in HV gas-insulated switchgear**. Technical Brochure 570, 2014. — Citada pelo MODEL legado do repositório.

HELMER, J.; LINDMAYER, M. Mathematical modeling of the high frequency behavior of vacuum interrupters. In: **XVIIth International Symposium on Discharges and Electrical Insulation in Vacuum (ISDEIV)**, 1996. — Citada pelo MODEL legado do repositório.

### Documentos em revisão duplo-cega

DOCUMENTO A. Manobra de motor de 1 250 kW / 4,16 kV com disjuntor a vácuo e *snubber* a tiristor. **[INSERIR CITAÇÃO]** — autoria não divulgada; Tabelas II e III citadas por página.

### Documentos internos desta série

`docs/research/rul_isolamento/00_INDICE.md`; `01_ETAPA1_monitoramento_degradacao_isolamento.md`; `02_ETAPA2_cruzamento_A_x_B.md`; `03_ETAPA3_contexto_c_level.md`; `04_ARQUITETURA_MVP_RUL_OLIVAS.md`; `anexos/repo/convencoes_auditoria_gui_docs.md`.
