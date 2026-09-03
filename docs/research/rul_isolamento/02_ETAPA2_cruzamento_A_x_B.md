# Etapa 2 — Cruzamento de domínios: mitigação seletiva de sobretensões de manobra (Documento A) e load shedding seletivo sob contingência N-1 (Documento B)

**Objetivo.** Estabelecer, com rastreabilidade de evidência elo a elo, a relação causal entre os dois trabalhos que compõem a base do módulo MVP de RUL de isolamento de estator: (i) demonstrar, por leitura integral dos dois textos primários, que o cenário de pior caso simulado pelo Documento A é o desfecho operacional que a decisão otimizada pelo Documento B existe para evitar, de modo que **B determina a taxa de ocorrência $\lambda$ do evento cuja severidade A reduz**; (ii) derivar a cadeia térmica que B não modela e mostrar por que ela realimenta a probabilidade do evento de A; (iii) formalizar o acumulador multiestresse e a formulação *health-aware* de corte de carga, marcando o que é proposta e o que é resultado; (iv) mapear os artigos de apoio por elo da cadeia; (v) inventariar o que o Olivas Power System Studio já entrega e o que falta, com verificação direta de código; e (vi) especificar o experimento computacional mínimo que une os dois domínios.

**Diagnóstico.** O acoplamento central **é verificável nos dois textos primários e não é afirmado por nenhum deles**. O Documento A declara: "The studied scenario is the most critical one: an intempestive interruption of a motor start commanded by the protection. The maneuver is aborted while the machine is drawing its full starting current ($I_p/I_n = 6.5$)" [FATO: doc A, p. 3, V]. O Documento B declara, no resumo: "Starting a large induction motor in an industrial plant that operates under N-1 contingency often requires shedding part of the connected load in advance; **otherwise, the voltage sag trips undervoltage protection across the bus**" [FATO: doc B, p. 1], e quantifica o desfecho evitado: $V^{(\mathrm{INRUSH})}_{\min} = 0{,}755$ pu contra o limite de *ride-through* de 0,85 pu, "well below" [FATO: doc B, p. 2]. Os dois textos descrevem, portanto, os dois lados do mesmo evento — B a montante (por que a proteção atua), A a jusante (o que a atuação produz no dielétrico) — e **nenhum deles cita o outro** [FATO por omissão, verificado por leitura integral: doc A, p. 1–5, refs. [1]–[24]; doc B, p. 1–6, refs. [1]–[19]]. A consequência quantitativa é severa e não trivial: as três soluções da frente de Pareto de B operam a 0,850 / 0,858 / 0,866 pu, isto é, com margem de **0,0 % a 1,9 %** sobre o ajuste que separa a operação normal do cenário de A [CÁLCULO PRÓPRIO sobre doc B, p. 3, Tabela III], enquanto a discrepância **típica** documentada entre estudo quase-estático e estudo dinâmico é de $\pm$ 0,5 % — já **metade da margem do joelho** — e o máximo reportado é de 4,31 %, com as ressalvas de base de normalização e de atribuição dos autores registradas na §2.4(a) [LITERATURA: Nivelo et al., IPST 2021, p. 6–8]. O risco dominante desta etapa não é de modelagem: é de **precisão sem exatidão**, isto é, um *surrogate* com MAE de $8{,}5\times10^{-5}$ pu emulando um modelo físico cuja incerteza é **1,7 a 2,6 ordens de grandeza maior** (§2.4(c)).

**Arquivos consultados.**

| Arquivo | Papel nesta etapa |
|---|---|
| `(texto integral, fora do repositório) A_sepoc_snubber.txt` (p. 1–5) | Fonte primária do Documento A: Tabelas I–III, Seções II–VI, refs. [1]–[24] |
| `(texto integral, fora do repositório) B_sepoc_load_shedding.txt` (p. 1–6) | Fonte primária do Documento B: eqs. (1)–(4), Algoritmos 1–2, Tabelas I–VI, refs. [1]–[19] |
| `01_ETAPA1_monitoramento_degradacao_isolamento.md` (873 l.) | Notação, equações D1–D7, vetor $\mathbf{s}_{m,j}$, ressalvas e limitações herdadas |
| `anexos/fichamentos_AB/A_snubber_tiristor_vcb.md` (423 l.) | Fichamento verificado de A, incluindo §8 ("o que A não afirma") |
| `anexos/fichamentos_AB/B_load_shedding_n1_nsga.md` (473 l.) | Fichamento verificado de B, incluindo §8 (28 itens de ausência) e §9.2 (limitações inferidas) |
| `anexos/cruzamento/cruzamento_A_snubber_vcb.md` (379 l.) | Rascunho **não verificado**: perfil de estresse por evento, D1–D9, divergências L1/L2/A |
| `anexos/cruzamento/cruzamento_B_load_shedding_n1.md` (433 l.) | Rascunho **não verificado**: (E1)–(E9), tabelas 2.1–2.5, inventário do repositório |
| `anexos/pesquisa/termico_partidas_n1_otimizacao.md` (268 l.) | F1–F48: classes térmicas, IEEE 620, IEEE 3002.7, Montsinger/Arrhenius, decisão pós-prognóstico, *surrogates* |
| `anexos/fichamentos/{02,06,07,09,10,12}_*.md` | Jensen (EKF), Yu (modo), Vichare & Pecht (LCM), Strangas (mitigação → MTBF), Siami-Namini (LSTM/BiLSTM), Ma (perfil de missão) |
| `anexos/repo/*.md` (5 arq.) | Mapas do código; todos os símbolos citados na §9 foram **reconferidos por leitura direta** em HEAD `d6a1160` |

**Estratégia.** O documento trata os dois trabalhos como **duas metades de um único problema de decisão sob incerteza**, e não como dois estudos independentes a serem justapostos. A ordem é: (§1) delimitar rigorosamente o que cada um modela e não modela; (§2) testar nos textos primários a hipótese de acoplamento causal e quantificá-la; (§3) testar o acoplamento inverso, do estado elétrico/térmico da partida para a severidade do transitório; (§4) derivar a cadeia térmica ausente em B com âncora normativa; (§5) formalizar a sinergia; (§6–§7) levar o resultado à formulação de otimização e ao *trade-off* de projeto; (§8–§10) mapear literatura, código e experimento. Os rascunhos de `anexos/cruzamento/` foram tratados como **hipóteses a confirmar**: toda afirmação deles que sobrevive aqui foi reconferida no texto primário correspondente, e as que não sobreviveram estão registradas como correção explícita (§11, itens 3 e 7).

**Limitações.** (a) Nenhum dos dois documentos fornece inércia $J$, curva $T_L(\omega)$, classe térmica, $t_{LR}$ a quente ou constante de tempo térmica do motor de 1250 kW; toda a §4 é **derivação com parâmetros hipotéticos declarados**, e seus números são faixas, não valores. (b) A lista das 19 máquinas de B está nos CSV do repositório retido para revisão cega [FATO: doc B, p. 3], de modo que a decomposição do afundamento por carga — necessária para a análise de sensibilidade da §2.4 — é feita por limite superior, não exatamente. (c) O termo de sinergia da §5 **não tem nenhum parâmetro medido disponível** nas fontes acessadas [INSERIR CITAÇÃO]. (d) A associação entre "commanded by the protection" (A) e a função ANSI 27 (B) é **inferência**: A não nomeia a função de proteção que comanda a interrupção [FATO por omissão: doc A, p. 3]. (e) Todas as limitações da Etapa 1 (§9, itens 1–12) permanecem integralmente válidas, em especial a ausência de $n$, $V_{th}$ e $a(t_f)$ para mica-epóxi pré-formada de MT. (f) Este documento foi submetido a duas rodadas de verificação adversarial — fidelidade aos textos primários e correção física/dimensional/normativa —, cujas correções estão aplicadas no corpo e registradas na §11.1, itens 10–17; as fontes de literatura externa **não reverificadas** nessa rodada estão listadas na nota de verificação que abre a §12.

**Próximo passo recomendado.** Executar o **elo E-2** do experimento da §10 antes de qualquer outro: a estimativa da probabilidade condicional $P[\text{atuação da 27} \mid V_{\min}, t_{acc}]$ exige apenas dois dados que hoje não existem em nenhum dos documentos — o **ajuste temporizado** da ANSI 27 (B declara só o nível, 0,85 pu, "adopted in this study as a typical ANSI 27 undervoltage setting" [FATO: doc B, p. 2], sem temporização [FATO: ausência; fichamento B §8, item 14]) e o **tempo de aceleração** a 0,850 pu. Sem o primeiro, o elo B → A é qualitativo; sem o segundo, é não quantificável. Ambos são obteníveis: o ajuste, por consulta ao ajuste real de uma planta; o tempo, pela integração de (4.2) com a curva conjugado–velocidade do fabricante.

---

## 1. Os dois domínios lado a lado

### 1.1 Tabela comparativa

| Dimensão | Documento A | Documento B |
|---|---|---|
| Pergunta respondida | Quanto uma manobra severa solicita o dielétrico, e quanto um snubber ativo reduz essa solicitação | Quais máquinas desligar antes da partida, para que a partida seja factível sob N-1 |
| Escala de tempo | µs–ms (passo 1 µs, janela 45 ms) [FATO: doc A, Tabela II, p. 3] | s–min (INRUSH "about 10 s"; snapshots quase-estáticos) [FATO: doc B, p. 2] |
| Ferramenta | ATP/EMTP (ATPDraw), TACS/MODELS [FATO: doc A, p. 2–3, IV] | OpenDSS via `py-dss-interface`, Python 3, pymoo [FATO: doc B, p. 3] |
| Representação do motor alvo | Ramo R–L série concentrado ($R_{eq}=0{,}691\ \Omega$, $L_{eq}=8{,}9795$ mH) [FATO: doc A, Fig. 2, p. 4 — leitura de figura; REPO: `git show ad308d5:trt_all_motors_dt_ea.atp:736-738`] | Carga de **impedância constante de rotor bloqueado**, $K_{ir}=6{,}5$, $\cos\varphi_{lr}=0{,}20$ [FATO: doc B, p. 2] |
| Grandeza de saída | TRV de pico e RRRV **no disjuntor**, por fase (Tabela III) [FATO: doc A, p. 3] | $V^{(k)}_{\min}$, $V^{(k)}_{\max}$, $N^{(k)}_{viol}$, perdas, $S^{(k)}_{TR}$ por *snapshot* [FATO: doc B, p. 3, Alg. 1] |
| Estressor dominante | Impulso de frente íngreme repetitivo (SFI) sobre a isolação espira-a-espira [FATO: doc A, p. 2, II-B] | Afundamento de tensão sustentado (~10 s) e carregamento do transformador [FATO: doc B, p. 2–3] |
| Função de proteção modelada | **Nenhuma explícita.** O texto diz apenas "commanded by the protection" [FATO: doc A, p. 3, V]; nenhuma função ANSI, ajuste ou temporização é citada [FATO por omissão, p. 1–5] | ANSI 27 (sag, $g_1$ e $f_3$), 59 (swell, $g_2$ e $f_3$), 49 (réplica térmica do **transformador**, $g_3$), 51 (retaguarda, "enveloped by $g_3$ in steady state") [FATO: doc B, p. 2, Tabela I] |
| Objeto protegido | Isolação de estator do motor alvo (declarado; não modelado) | Barramento: cargas vizinhas (27), transformador remanescente (49) |
| Grandeza otimizada | Nenhuma. É estudo de caso único, sem varredura, sem estatística [FATO por omissão: doc A, p. 3–4] | $\min (f_3, f_4, f_5)$ sob $g_1$–$g_3$, com NSGA-II/III/U-NSGA-III/aleatório, 10 sementes [FATO: doc B, eqs. (1)–(4), p. 2–3] |
| Validação | "at the computational level"; bancada de 4,16 kV e HIL declarados como próximo passo [FATO: doc A, p. 1, 4, VI] | Reprodutibilidade por `python -m src.sepoc_study`; validação dinâmica declarada trabalho futuro [FATO: doc B, p. 3, 6] |

### 1.2 O que cada documento NÃO modela

| Ausência | Documento A | Documento B |
|---|---|---|
| Isolamento e sua degradação | Não há enrolamento a parâmetros distribuídos, capacitância espira-espira/espira-terra, distribuição de impulso, DP, *treeing*, curva de vida, BIL, classe térmica ou idade [FATO por omissão, verificado em p. 1–5 e Figs. 1–4] | As palavras "aging", "insulation", "lifetime", "remaining useful life" e "degradation" **não ocorrem** no texto [FATO: ausência, verificado por leitura integral, p. 1–6] |
| Contagem de reignições | Não reportada; apenas "successive arc reignitions", "multiple reignitions", "burst of steep front voltage escalations" [FATO: doc A, p. 1–3] | Não aplicável: não há VCB, chopping, reignição, TRV ou dv/dt em B [FATO: ausência] |
| Tensão no terminal do motor | Sonda `01AT` existe na Fig. 2, mas os resultados não são reportados [FATO: doc A, Fig. 2, p. 4; FATO por omissão] | Reporta $V_{\min}$ da barra de 4,16 kV, não o terminal da máquina; sem cabo modelado [FATO: ausência; fichamento B §8, item 12] |
| Térmica do motor | Temperatura do enrolamento não é variável do modelo; $R_{eq}$ é constante [FATO por omissão; FATO: doc A, Fig. 2] | Nenhuma réplica térmica de motor, constante de tempo, temperatura ou classe térmica; a ANSI 49 de B é do **transformador** [FATO: doc B, p. 2, Tabela I; FATO: ausência] |
| Tempo de aceleração / $I^2t$ | Não calculado; o motor não gira no modelo (ramo passivo) [FATO por omissão] | Sem curva conjugado–velocidade, conjugado de carga, inércia ou integração dinâmica; a duração de 10 s é **declarada, não derivada** [FATO: doc B, p. 2; FATO: ausência] |
| RUL | A sigla não aparece; "remaining useful life" ocorre **uma vez**, na p. 2, como finalidade da camada digital [FATO: doc A, p. 2, III-B] | Não ocorre [FATO: ausência] |
| Dinâmica | Estritamente EMT; nenhuma dinâmica eletromecânica | Quatro fluxos quase-estáticos; "validate selected scenarios in dynamic simulation" é trabalho futuro [FATO: doc B, p. 6] |
| Estatística / incerteza | Uma abertura, um conjunto de instantes de separação; nenhuma análise Monte Carlo [FATO por omissão] | Nenhuma análise de sensibilidade a $K_{ir}$, $\cos\varphi_{lr}$, $X_{HL}$ ou X/R [FATO: ausência; fichamento B §9.2] |
| Citação mútua | Nenhuma das 24 referências de A é o Documento B nem trata de corte de carga ou N-1 [FATO por omissão: doc A, p. 4–5] | Nenhuma das 19 referências de B trata de isolamento, envelhecimento, térmica de motores, transitórios de manobra ou RUL [FATO: doc B, p. 6; fichamento B §11] |

**Registro obrigatório** [FATO por omissão]: os dois documentos **não se citam mutuamente** e não compartilham nenhuma referência bibliográfica. A união proposta neste documento é, portanto, contribuição desta etapa, não leitura de nenhum dos dois.

### 1.3 O que os dois compartilham — e por que isso não é coincidência

Três parâmetros coincidem literalmente:

| Parâmetro | Documento A | Documento B | Evidência |
|---|---|---|---|
| Máquina alvo | 1250 kW, 4,16 kV, 60 Hz | 1250 kW, $\cos\varphi = 0{,}89$, barra 4,16 kV | [FATO: doc A, Tabela I, p. 3; doc B, p. 2] |
| Múltiplo de corrente de partida | $I_p/I_n = 6{,}5$ | $K_{ir} = 6{,}5$ | [FATO: doc A, Tabela I; doc B, p. 2] |
| Estado da máquina no evento | "drawing its full starting current" | *snapshot* INRUSH, rotor bloqueado | [FATO: doc A, p. 3, V; doc B, p. 2] |

Acresce uma coincidência **não declarada por nenhum dos dois**, obtida por cálculo: o ramo R–L concentrado com que A representa o motor tem
$$
X = \omega L_{eq} = 377 \times 8{,}9795\times10^{-3} = 3{,}3853\ \Omega,\qquad
|Z| = \sqrt{R_{eq}^2 + X^2} = 3{,}4551\ \Omega,\qquad
\cos\varphi = \frac{R_{eq}}{|Z|} = \frac{0{,}691}{3{,}4551} = \mathbf{0{,}2000}
$$
[CÁLCULO PRÓPRIO sobre $R_{eq}=0{,}691\ \Omega$ e $L_{eq}=8{,}9795$ mH]. O fator de potência do ramo de A é **exatamente** o $\cos\varphi_{lr} = 0{,}20$ que B declara para o *snapshot* INRUSH [FATO: doc B, p. 2].

**Enunciado exato da coincidência, e apenas dele** [INFERÊNCIA FÍSICA a partir de dois FATOs independentes]: o ramo de A tem o **mesmo ângulo de impedância** de rotor bloqueado que B declara ($\cos\varphi = 0{,}2000$ contra 0,20), **mas não o mesmo módulo** — o de A corresponde a $3{,}35\,I_n$ e o de B a $6{,}5\,I_n$ (cálculo abaixo). A coincidência de ângulo é evidência forte de que A parametrizou o ramo para o estado de rotor bloqueado, e de que os dois documentos descrevem a mesma máquina nesse estado por dois formalismos distintos — **mas a discrepância de módulo permanece não explicada**, e a afirmação de identidade de estado elétrico só é sustentável se e quando a pergunta Q3 (§11.3) for resolvida. Nenhum dos dois documentos afirma nem a coincidência nem a discrepância [FATO por omissão].

Ressalva quantitativa obrigatória, que é a pergunta aberta Q3 (§11.3): aplicado fase-terra a $U_N/\sqrt3 = 2{,}402$ kV, esse ramo drena $2402/3{,}4551 = 695{,}2$ A $= 3{,}35\,I_n$, e **não** os $6{,}5\,I_n = 1349$ A declarados na Tabela I de A [CÁLCULO PRÓPRIO; $I_n = 207{,}52$ A por $P/(\sqrt3 U_N \eta \,\mathrm{fp})$ com $P = 1250$ kW, $U_N = 4{,}16$ kV, $\eta = 0{,}95$ e fp $= 0{,}88$, todos FATO: doc A, Tabela I, p. 3]. O mesmo valor é legível como "Line current (rms): 207.52 A" na Fig. 2 [FATO: doc A, Fig. 2, p. 4 — leitura de figura]; essa igualdade é **consistência interna de A** (a figura é saída do modelo alimentado pela mesma Tabela I) e **não** corroboração independente do ramo R–L. A impedância que reproduziria $6{,}5\,I_n$ a $\cos\varphi=0{,}20$ seria $|Z| = 1{,}781\ \Omega$ — exatamente $1{,}94\times$ menor que a adotada. Ou a conexão do ramo não é fase-terra, ou a impedância não está escalada para $I_p/I_n = 6{,}5$. **A consequência é material**: se o ramo drena 3,35 $I_n$ e não 6,5 $I_n$, o cenário de A é menos severo do que o rótulo "$I_p/I_n = 6{,}5$" sugere, e a energia magnética do reservatório (§3.2) é $(6{,}5/3{,}35)^2 = 3{,}77\times$ menor que a calculada a partir da placa.

---

## 2. O acoplamento causal principal: B fixa $\lambda$, A fixa a severidade

### 2.1 Verificação da hipótese nos dois textos primários

A hipótese a testar era: *o cenário de pior caso de A é exatamente o desfecho que a decisão de B existe para evitar*. A verificação, transcrição por transcrição:

| # | Proposição | Transcrição literal | Veredicto |
|---|---|---|---|
| P1 | O evento de A é a interrupção de uma partida, comandada pela proteção | "an intempestive interruption of a motor start commanded by the protection. The maneuver is aborted while the machine is drawing its full starting current ($I_p/I_n = 6.5$)" | **Confirmado** [FATO: doc A, p. 3, V] |
| P2 | O evento que B existe para evitar é a atuação da proteção de subtensão durante a partida | "Starting a large induction motor … often requires shedding part of the connected load in advance; otherwise, **the voltage sag trips undervoltage protection across the bus**" | **Confirmado** [FATO: doc B, p. 1, resumo] |
| P3 | O mecanismo é o afundamento causado pela corrente de rotor bloqueado | "The locked-rotor current, typically 5 to 7 times the rated value at a power factor near 0.2, depresses the bus voltage for several seconds and **may trip the ANSI 27 undervoltage protection of every neighboring load**" | **Confirmado** [FATO: doc B, p. 1, I] |
| P4 | Sem corte, a operação é infactível pelo critério de tensão | "the direct start of the target with all machines connected drives the inrush voltage to 0.755 pu, well below the 0.85 pu ride-through limit … The operation is therefore infeasible without prior load shedding, on two independent grounds: voltage and transformer overload" | **Confirmado** [FATO: doc B, p. 2, II-A] |
| P5 | O objeto da atuação da 27 inclui o disjuntor do próprio alvo | — | **Não confirmado.** B nomeia explicitamente "every neighboring load" (p. 1) e, no resumo, "across the bus" (p. 1). Que o elemento 27 associado ao **próprio alvo** também opere é [INFERÊNCIA]: um afundamento de barra a 0,755 pu está abaixo de qualquer ajuste de 0,85 pu daquela barra, inclusive o do alvo. B não modela a proteção do alvo [FATO: ausência] |
| P6 | A função que comanda a interrupção em A é a ANSI 27 | — | **Não confirmado.** A escreve apenas "commanded by the protection" e **não nomeia função, ajuste ou temporização** [FATO por omissão: doc A, p. 3, V]. Candidatas igualmente compatíveis: 27 (subtensão), 51/51LR (sobrecorrente temporizada durante partida prolongada), 48 (sequência incompleta / *stall*), 49 (réplica térmica do motor) — todas plausíveis pelo prolongamento de $t_{acc}$ derivado na §4 [INFERÊNCIA] |

**Conclusão da verificação.** A hipótese central sobrevive na sua forma forte quanto ao *cenário* (P1–P4 confirmados literalmente) e deve ser enunciada na forma fraca quanto ao *mecanismo de disparo* (P5–P6 são inferência). O enunciado correto e defensável é:

> Um plano de corte insuficiente sob N-1 produz um afundamento abaixo do ajuste de *ride-through* adotado como típico para a ANSI 27 [FATO: doc B, p. 1–2]; a atuação de proteção durante a corrente de partida abre o VCB sobre corrente indutiva elevada [INFERÊNCIA a partir de P4 e P1]; a interrupção dessa corrente produz *chopping* e reignições sucessivas [FATO: doc A, p. 2, II-A]; a escalada por reignições gera o transitório de 41,44 kV / 15,05 kV·µs⁻¹ que o snubber ativo reduz a 13,65 kV / 13,11 kV·µs⁻¹ [FATO: doc A, Tabela III, p. 3]. **B determina a taxa de ocorrência $\lambda$ do evento cuja severidade A reduz; nenhum dos dois documentos afirma essa relação** [FATO por omissão].

### 2.2 A cadeia, elo a elo, com rótulo por elo

| Elo | Enunciado | Rótulo |
|---|---|---|
| L1 | Contingência N-1 remove um dos dois transformadores 7,5/9 MVA; a demanda plena de 18,2 MVA "doubles the 9 MVA AF capacity" | [FATO: doc B, p. 2] |
| L2 | A partida direta do alvo sob a topologia N-1 e com todas as máquinas conectadas leva $V^{(\mathrm{INRUSH})}_{\min}$ a 0,755 pu | [FATO: doc B, p. 2–3] |
| L3 | 0,755 pu está abaixo do ajuste de *ride-through* de 0,85 pu adotado como típico para a ANSI 27 | [FATO: doc B, p. 2] |
| L4 | Um elemento 27 desse barramento opera durante o transitório de partida | [INFERÊNCIA]; B modela a violação como contagem $N_{viol}$ e restrição $g_1$, sem temporização [FATO: doc B, p. 2–3; FATO: ausência] |
| L5 | A atuação abre o VCB **enquanto o motor drena corrente de partida** | [INFERÊNCIA]; é literalmente o cenário de A, "the maneuver is aborted while the machine is drawing its full starting current" [FATO: doc A, p. 3] |
| L6 | O VCB interrompe corrente indutiva elevada; o arco extingue-se antes do zero natural em $I_{ch} = 1$–2 A | [FATO: doc A, p. 2, II-A; Tabela II, p. 3] |
| L7 | A recuperação dielétrica parabólica $V_{wth} = 0{,}801\,t + 1{,}226\,t^2$ [kV, t em ms] é vencida pela TRV, e sucedem-se reignições que escalam a tensão | [FATO: doc A, p. 3, IV-B e V-A] |
| L8 | Cada reignição impõe um SFI nos terminais da máquina, concentrado nas primeiras espiras | [FATO: doc A, p. 2, II-B]; a fração não é quantificada por A [FATO por omissão]; a norma nega lei fechada [NORMA: IEC 60034-15:2009, A.3] |
| L9 | O dano dielétrico incremental acumula por manobra segundo D7 da Etapa 1 | [PROPOSTA — Etapa 1, §5.4, D7; todos os parâmetros livres] |
| L10 | A norma reconhece o cenário como especial: os níveis padrão "may not be adequate for special operating conditions (e.g. **interrupted start** …)" | [NORMA: IEC 60034-15:2009, Tabela 1, Nota 5]; a edição 2025 prevê níveis reforçados para "aborted starts" [NORMA: IEC CDV 60034-15, 4.3 — rascunho] |
| L11 | A norma de manobra confirma a severidade: "the switching of the current of a starting or stalled motor is usually the more severe operation" | [NORMA: IEC 62271-110:2023, 4.3.2] |

Os elos L1–L3 e L6–L8 são **fato**; L4–L5 e L9 são **inferência/proposta**. É exatamente nos elos L4 e L5 que o experimento da §10 deve ser instrumentado, porque são os únicos elos da cadeia que ninguém mediu nem simulou.

### 2.3 A margem de *ride-through* das três soluções de B

| Solução (doc B, Tabela III) | Mantidas | $f_5$ [kW] | $f_4$ [kW] | $V^{(\mathrm{INR})}_{\min}$ [pu] | Margem absoluta [pu] | Margem relativa |
|---|---|---|---|---|---|---|
| Mínimo corte | M_710, M_800 | 7417 | 43,2 | 0,850 | **0,000** | **0,00 %** |
| Joelho | M_800 | 8127 | 34,6 | 0,858 | 0,008 | 0,94 % |
| Mínimas perdas | (nenhuma) | 8927 | 26,5 | 0,866 | 0,016 | 1,88 % |
| *(infactível)* Sem corte | todas | 0 | — | 0,755 | −0,095 | −11,2 % |

Valores de $f_4$, $f_5$ e $V_{\min}$: [FATO: doc B, p. 3, Tabela III]. Margens: [CÁLCULO PRÓPRIO: $V_{\min} - 0{,}85$ e $(V_{\min}-0{,}85)/0{,}85$].

O próprio B declara a margem nula da solução recomendada: "at this point the sag constraint is active, with $V^{(\mathrm{INRUSH})}_{\min} = 0.850$ pu, **at the ride-through limit**" [FATO: doc B, p. 3], e a conclusão repete: "starts the 1250 kW target with the sag constraint active at 0.85 pu" [FATO: doc B, p. 5]. Em linguagem de otimização, isso é ótimo; em linguagem de engenharia de proteção, é **operar exatamente sobre o ajuste**.

### 2.4 O que a margem nula significa: três fontes de erro maiores que ela

**(a) Erro do modelo quase-estático contra a partida real (dinâmica).** O estudo comparativo mais próximo acessado — plataforma *offshore* isolada, motores de 11 MW, PTW (snapshot) contra RTDS (domínio do tempo) — reporta que "the vast majority of the absolute differences obtained were less than ± 0.5 %", com um caso extremo em que "another specific case presents the greatest difference between methodologies of **4.31 %**" [LITERATURA: Nivelo et al., IPST 2021, p. 6–8, texto e Tabela VII].

**Duas ressalvas materiais sobre o valor de 4,31 %, exigidas pelo próprio artigo** [LITERATURA: idem]:

- **A base de normalização não é declarada.** A Tabela VII intitula-se "absolute difference in % — PTW vs. RTDS" sobre **quedas de tensão**, e a frase seguinte dos autores ("However, the voltage drop in this case is less than 10 %, relatively far from the recommended limit of 15 %") sugere leitura em **pontos percentuais de queda**. A conversão para pu admite, portanto, duas leituras: 4,31 % **da magnitude** de 0,85 pu $\Rightarrow$ 0,0366 pu; ou 4,31 % **da própria queda** $\Rightarrow$ $\approx$ 0,0043 pu — uma ordem de grandeza de diferença [CÁLCULO PRÓPRIO].
- **Os autores atribuem o *outlier* a artefato de modelagem**, não à diferença entre metodologias: "this error may have occurred due to the equivalent loads created in the respective buses", e o caso ocorre na barra PN-2A (4,16 kV, coluna M4-740 kVA da Tabela VII), que **não hospeda o motor partindo**.

Aplicado à base de 0,85 pu, com as duas leituras explicitadas [CÁLCULO PRÓPRIO]:

| Discrepância documentada | Em pu sobre 0,85 | Compara-se a … |
|---|---|---|
| 0,5 % (caso típico, robusto às duas leituras) | 0,0043 pu | **53 % da margem do joelho**; 27 % da margem de mínimas perdas |
| 4,31 % (máximo), leitura benigna (% da queda) | 0,0043 pu | **27 % a 54 % das margens do joelho e de mínimas perdas** |
| 4,31 % (máximo), leitura severa (% da magnitude) | 0,0366 pu | **2,3× a maior das três margens**; consome as três soluções |

Isto é: a discrepância **típica** já consome metade da margem do joelho — e este é o enunciado robusto, que sobrevive às duas leituras e ao caráter de *outlier* do caso extremo. A leitura severa do máximo documentado invalidaria as três soluções da frente, mas **é a leitura menos favorável de um número cuja base o artigo não declara e cuja causa os próprios autores atribuem a cargas equivalentes agregadas**; não deve ser usada como resultado. B reconhece implicitamente o ponto ao listar "validate selected scenarios in dynamic simulation" como trabalho futuro [FATO: doc B, p. 6], mas não o converte em margem de projeto.

**(b) Erro dos parâmetros nominais do modelo de inrush.** $K_{ir} = 6{,}5$ e $\cos\varphi_{lr} = 0{,}20$ são **parâmetros declarados, não derivados de placa nem de ensaio** [FATO: doc B, p. 2; FATO: ausência, fichamento B §8, item 6]; o próprio B admite a faixa ao escrever "typically 5 to 7 times the rated value at a power factor near 0.2" [FATO: doc B, p. 1]. Sensibilidade de primeira ordem, com hipóteses declaradas [CÁLCULO PRÓPRIO]:

Seja $\Delta V = 1 - V^{(\mathrm{INRUSH})}_{\min}$ o afundamento. Na solução de mínimas perdas (todas as 19 cortadas), $\Delta V = 0{,}134$ pu, produzido pelo alvo em inrush mais 3,6 MW de carga estática mais o transformador. Atribuindo **todo** esse afundamento ao alvo — limite superior, pois a carga estática e a impedância do transformador respondem por parte dele —, e linearizando,
$$
\frac{\partial V_{\min}}{\partial K_{ir}} \;\approx\; -\frac{\Delta V}{K_{ir}} \;=\; -\frac{0{,}134}{6{,}5} \;=\; -0{,}0206\ \mathrm{pu\ por\ unidade\ de\ }K_{ir}.
$$

| $K_{ir}$ | $\Delta V_{\min}$ estimado [pu] | Efeito sobre a solução do joelho (margem 0,008 pu) |
|---|---|---|
| 6,5 → 6,9 (+6,2 %) | −0,0082 | **Consome integralmente a margem** |
| 6,5 → 7,0 (+7,7 %) | −0,0103 | Consome a margem e 64 % da margem de mínimas perdas |
| 6,5 → 6,0 (−7,7 %) | +0,0103 | Folga; a solução mínimo-corte deixaria de ser ativa |

Ou seja: **mover $K_{ir}$ de 6,5 para 7,0 — dentro da faixa "5 to 7" que o próprio B enuncia — anula a margem do joelho e quase a de mínimas perdas** [CÁLCULO PRÓPRIO, com hipóteses de linearidade e de atribuição integral declaradas]. Para referência normativa, a especificação de O&G aceita corrente de rotor bloqueado declarada "between 4,0 and 6,5 times the rated current" [NORMA: IOGP S-704 v2.0, 11.3.1.1; $\equiv$ v1.0, 9.12.1.1, numeração riscada no redline], colocando 6,5 no **teto** da faixa admissível, o que torna a hipótese conservadora — mas apenas se o valor de placa for de fato o declarado.

Já $\cos\varphi_{lr}$ é efeito de **segunda ordem**: com X/R = 12 na fonte e $X_{HL}=8\%$, o afundamento é dominado pela componente reativa, e $\sin\varphi$ varia de 0,9798 ($\cos\varphi=0{,}20$) para 0,9887 ($\cos\varphi=0{,}15$, +0,91 %) ou 0,9682 ($\cos\varphi=0{,}25$, −1,18 %) [CÁLCULO PRÓPRIO], o que desloca $V_{\min}$ em $\mp\,0{,}0012$–$0{,}0016$ pu — cerca de 15–20 % da margem do joelho, não mais.

**(c) Precisão do *surrogate* contra exatidão do modelo.** O *surrogate* de B reproduz $V^{(\mathrm{INRUSH})}_{\min}$ com $R^2 > 0{,}999$ e MAE $= 8{,}5\times10^{-5}$ pu [FATO: doc B, p. 5, Tabela VI, linha "Ridge (quadratic)"], "about 0.01 % of nominal, **tighter than any practical protection setting tolerance**" [FATO: doc B, p. 5, Seção V, texto — a frase está no corpo, não na Tabela VI, que traz apenas as quatro linhas de acurácia]. A afirmação é correta e é, ao mesmo tempo, o ponto crítico. Comparando as três escalas [CÁLCULO PRÓPRIO]:

| Grandeza | Valor [pu] | Razão para o MAE do *surrogate* |
|---|---|---|
| MAE do *surrogate* | $8{,}5\times10^{-5}$ | 1 |
| Margem do joelho | $8{,}0\times10^{-3}$ | 94 |
| Discrepância snapshot × dinâmico, caso típico (0,5 %) | $4{,}3\times10^{-3}$ | 50 |
| Sensibilidade a $K_{ir}$ (6,5 → 7,0) | $1{,}0\times10^{-2}$ | 121 |
| Discrepância snapshot × dinâmico, máximo (4,31 %), **leitura severa** (ver ressalvas em (a)) | $3{,}7\times10^{-2}$ | 431 |

**Enunciado defensável** [INFERÊNCIA a partir dos números acima]: o *surrogate* de B emula o motor de fluxo de potência com erro **1,7 a 2,6 ordens de grandeza menor** que a incerteza do próprio modelo físico que esse motor implementa. A garantia declarada por B — "Prediction errors may degrade search efficiency, but they never produce an unverified shedding recommendation, because final feasibility is always confirmed by the full power flow" [FATO: doc B, p. 5] — é rigorosa e permanece válida, **mas protege contra o erro do *surrogate*, não contra o erro do modelo**. O que falta é a margem de projeto: um $V^{ir}$ efetivo maior que 0,85 pu, ou uma restrição probabilística $P[V_{\min} < V^{ir}] \le \varepsilon$, nenhuma das quais existe em B [FATO: ausência de análise de sensibilidade; fichamento B §9.2].

### 2.5 A consequência para $\lambda$: a monotonicidade perversa

Reunindo §2.3, §2.4 e a §4 (adiante), obtém-se uma cadeia **monótona no mesmo sentido**, que é o resultado central desta etapa [INFERÊNCIA a partir de FATOs de A e B mais as derivações da §4]:

$$
f_5 \downarrow \;\Longrightarrow\; V^{(\mathrm{INRUSH})}_{\min} \downarrow \;\Longrightarrow\;
\underbrace{t_{acc} \uparrow}_{\S4.2} \;\text{e}\; \underbrace{\text{margem} \downarrow}_{\S2.3}
\;\Longrightarrow\; P[\text{atuação durante a partida}] \uparrow \;\Longrightarrow\; \lambda_A \uparrow
$$

(Nesta seção $\lambda_A$ denota a **probabilidade por partida**, $\lambda_A^{(\mathrm{part})}$; a taxa anual correspondente é $\lambda_A^{(\mathrm{part})}\cdot N_{N\text{-}1}$ — convenção fixada na §6.2.)

isto é: **quanto menos produção o plano sacrifica, maior a taxa de ocorrência do evento que o Documento A trata como pior caso**. As três soluções de B ordenam-se, nesse eixo, exatamente ao contrário da ordem em que B as apresenta:

| Solução | $f_5$ (menor é melhor para produção) | $V_{\min}$ | Margem | $t_{acc}$ relativo (§4.2) | Exposição a L4–L5 |
|---|---|---|---|---|---|
| Mínimo corte | **7417 kW (melhor)** | 0,850 | 0,00 % | **maior** | **maior** |
| Joelho | 8127 kW | 0,858 | 0,94 % | intermediário | intermediário |
| Mínimas perdas | 8927 kW (pior) | 0,866 | 1,88 % | **menor** | **menor** |

A solução que B recomenda na conclusão — "The recommended shedding plan keeps two large secondary machines connected and starts the 1250 kW target with the sag constraint active at 0.85 pu, preserving 490 kW of production **relative to the earlier formulation**" [FATO: doc B, p. 5] — é, sob esta leitura, **a de maior $\lambda_A$ da frente**. **Precisão obrigatória sobre o número**: os 490 kW são o **ganho** da formulação restrita sobre a preliminar de cinco objetivos, que cortava 7907 kW ($7907 - 7417 = 490$ kW) [FATO: doc B, p. 3–4; CÁLCULO PRÓPRIO]; a produção **absoluta** preservada pelo plano recomendado é de **1510 kW** — "machines M_710 and M_800 remain connected, preserving 1510 kW of production ($f_5 = 7417$ kW, $f_4 = 43{,}2$ kW)" [FATO: doc B, p. 3] —, coerente com $8927 - 7417 = 1510$ kW da Tabela III [CÁLCULO PRÓPRIO]. Citar os 490 kW sem a cláusula final induz o leitor a lê-los como produção absoluta, o que erra por fator 3,08.

A leitura por $\lambda_A$ **não contradiz B**: B otimiza o que declara otimizar. Mostra que **a frente de Pareto de B está incompleta em um eixo que B não mede**, e é essa a lacuna que a §6 preenche com $f_6$ e $g_4$.

---

## 3. O acoplamento inverso: o estado elétrico, magnético e térmico no instante da manobra

### 3.1 A manobra de A ocorre no ponto de maior densidade de corrente do ciclo térmico

A partida é, por construção, o regime de maior densidade de corrente do motor: "During acceleration to full speed, the motor generates heating of the rotor and stator at a rate substantially higher than during full load running conditions … can cause damage to either the stator insulation or the rotor bars and end rings" [LITERATURA: L&B Electric, *Medium voltage motor starting*, 1998, p. 1]. A interrupção de A ocorre **dentro dessa janela** [FATO: doc A, p. 3, V]. Logo, o enrolamento que recebe o SFI está, no instante do impulso, na sua temperatura transitória mais alta do ciclo — e é justamente a temperatura do enrolamento que **não é variável do modelo de A** [FATO por omissão: doc A, p. 1–5; o ramo R–L tem $R_{eq}$ fixo].

Isto tem consequência direta sobre D7 da Etapa 1, cujo fator térmico é avaliado em $\theta_j$ = temperatura do enrolamento **no evento $j$** [Etapa 1, §5.4, D7].

**Correção de sinal a D7, aplicada em todo este documento** [CÁLCULO PRÓPRIO; registrada na §11.1, item 10]. Tal como impresso na Etapa 1, o fator $2^{(\theta_j-\theta_0)/\mathrm{HIC}}$ **multiplica** $N_j$; como $N_j$ está no **denominador** do dano ($\Delta D_m = \sum 1/N_j$), a forma impressa faria a taxa de dano **cair** por $2^{(\theta_j-\theta_0)/\mathrm{HIC}}$ com o aquecimento — o oposto de Montsinger e inconsistente com a própria D6 do mesmo texto, $L(\theta) = L_0\,2^{(\theta_0-\theta)/\mathrm{HIC}}$, em que o expoente é $(\theta_0-\theta)$. A forma harmonizada, adotada daqui em diante, é
$$
N_j \;=\; N_0\left(\frac{a(t_{f,j})V_{pk,j}-V_{th}}{V_{ref}-V_{th}}\right)^{-n}\left(\frac{t_{f,j}}{t_{f,0}}\right)^{m}\,2^{(\theta_0-\theta_j)/\mathrm{HIC}},
\qquad\text{equivalentemente}\qquad
\frac{1}{N_j} \;\propto\; 2^{(\theta_j-\theta_0)/\mathrm{HIC}} .
$$
Trata-se de correção **de sinal, não de mérito**: a Etapa 1 já rotula D7 como [HIPÓTESE de modelagem — todos os parâmetros a calibrar], e o fator de aceleração AF e todos os valores numéricos da tabela de sensibilidade da §4.3 permanecem inalterados; o que muda é o expoente com que AF entra em $N_j$.

Com a forma corrigida e HIC = 10 K, uma sobretemperatura de partida de +20 K sobre a referência multiplica a taxa de dano por $2^{20/10} = 4{,}0$; com HIC = 8 K, por $2^{20/8} = 5{,}66$ [CÁLCULO PRÓPRIO; faixa de HIC 8–15 °C conforme LITERATURA: Theofanous et al., *Energies* 18:6087, 2025, p. 11]. **Nem A nem B fornecem $\theta_j$**; A porque não modela térmica, B porque só modela a réplica térmica do transformador [FATO: ausência nos dois].

### 3.2 O reservatório magnético escala com $L I^2$ — e $I$ é a corrente de partida

A energia magnética disponível no ramo de carga no instante da abertura é $\tfrac12 L_{eq} i^2$. Avaliando nos dois estados possíveis da máquina, com $L_{eq} = 8{,}9795$ mH [FATO: doc A, Fig. 2 — leitura de figura; REPO: `git show ad308d5:trt_all_motors_dt_ea.atp:736-738`] e com as correntes de placa de A [CÁLCULO PRÓPRIO]:

| Estado | $I$ rms [A] | $\hat I$ pico [A] | $\tfrac12 L_{eq}\hat I^2$ [J] |
|---|---|---|---|
| Regime nominal, $L_{eq}$ do ramo de A | 207,52 | 293,5 | **386,7** |
| Partida plena, $I_p = 6{,}5 I_n$, $L_{eq}$ do ramo de A | 1348,9 | 1907,6 | **16 338** |
| *(o que o ramo de A efetivamente drena a 2,402 kV fase-terra)* | 695,2 | 983,2 | **4 340** |

Razão entre as duas primeiras linhas: $16\,338/386{,}7 = 42{,}25 = 6{,}5^2$ [CÁLCULO PRÓPRIO]. **Duas ressalvas obrigatórias, sem as quais o número é enganoso**:

1. **A razão $6{,}5^2$ é propriedade do ramo fixo de A, não da máquina.** Ela só se obtém mantendo $L_{eq} = 8{,}9795$ mH **invariante** entre os dois estados, o que é verdade para o ramo R–L de A (que é fixo por construção) e **falso** para uma máquina de indução real, cuja indutância equivalente em regime nominal é dominada pela magnetização e é bem maior que a de rotor bloqueado. Contraste [CÁLCULO PRÓPRIO]: em regime, $|Z| = 2402/207{,}52 = 11{,}58\ \Omega$ a $\cos\varphi = 0{,}88$, donde $X = 11{,}58\,\mathrm{sen}(28{,}36^\circ) = 5{,}50\ \Omega$ e $L = 14{,}6$ mH, o que dá $\tfrac12 L\hat I^2 = 628$ J e reduz a razão física entre regime nominal e rotor bloqueado a $\approx 26$, não 42. Portanto: **dentro do modelo de ramo fixo de A o reservatório escala com $\hat I^2$, isto é, 42,25× entre 1,0 e 6,5 $I_n$; a razão física é menor ($\approx 26$), porque $L$ não é invariante ao escorregamento** [INFERÊNCIA FÍSICA].
2. **Os 16,3 kJ são condicionais a $\hat I = 6{,}5\,I_n$.** Como registrado na §1.3 e retomado na §11.1, item 8, o ramo **tal como parametrizado** drena 3,35 $I_n$ e não 6,5 $I_n$, de modo que a energia efetivamente armazenada nele a 2,402 kV é **4,34 kJ**, e não 16,3 kJ — fator 3,77 [CÁLCULO PRÓPRIO]. Todo número de energia desta subseção deve ser lido como faixa 4,3–16,3 kJ enquanto Q3 (§11.3) não for respondida.

Feitas as duas ressalvas, o conteúdo físico da escolha de A por $I_p/I_n = 6{,}5$ como pior caso é este: **o reservatório magnético disponível na partida é de 26 a 42 vezes maior que em regime**, conforme se adote a indutância física da máquina ou a do ramo fixo de A [INFERÊNCIA FÍSICA].

**Porém — e este é o ponto que A não explora nem discute** [FATO por omissão] — a energia efetivamente **capturada no instante do chopping** não escala com $I_p$: escala com $I_{ch}$, que A fixa em 1–2 A [FATO: doc A, Tabela II, p. 3]:
$$
\tfrac12 L_{eq} I_{ch}^2 = \tfrac12 \times 8{,}9795\times10^{-3} \times 2^2 = 1{,}80\times10^{-2}\ \mathrm{J} = 18\ \mathrm{mJ},
$$
isto é, $1{,}1\times10^{-6}$ do reservatório de 16,3 kJ — ou $4{,}1\times10^{-6}$ do reservatório de 4,3 kJ efetivamente presente no ramo tal como parametrizado (ressalva 2 acima) [CÁLCULO PRÓPRIO]. **A conclusão é a mesma nas duas leituras**: a energia de chopping é cinco a seis ordens de grandeza menor que o reservatório. A Etapa 1 já registrara que "o chopping isolado não explica picos de 30–41 kV" [Etapa 1, §5.1, item 1]. A conclusão desta etapa é mais forte e mais útil:

> **A corrente de partida não age sobre o transitório de A pela via da energia de chopping; age por três outras vias, das quais A explora apenas a primeira implicitamente** [INFERÊNCIA FÍSICA]:
>
> 1. **Fase da tensão de recuperação.** Com $\cos\varphi = 0{,}200$ do ramo (§1.3), o zero de corrente ocorre a $\arccos(0{,}20) = 78{,}5^\circ$ da tensão, isto é, praticamente no pico — condição de TRV máxima [INFERÊNCIA FÍSICA; a mesma que a IEC 62271-110:2023, 4.3.2, invoca ao declarar a manobra de motor em partida como "usually the more severe operation"].
> 2. **Estreitamento da janela de chopping.** O di/dt da corrente de frequência industrial no zero é $\mathrm{d}i/\mathrm{d}t = \omega \hat I$: $377 \times 1907{,}6 = 0{,}719$ A/µs na partida contra $377 \times 293{,}5 = 0{,}111$ A/µs em regime [CÁLCULO PRÓPRIO]. O tempo que a corrente permanece dentro da janela $|i| < I_{ch} = 2$ A é $4/(\mathrm{d}i/\mathrm{d}t)$: **5,6 µs na partida contra 36 µs em regime**. A janela em que o critério de chopping pode disparar é 6,5× mais estreita e 6,5× mais determinada. (Esta via é **independente de $L_{eq}$** e, portanto, imune à ressalva 2 acima.)
> 3. **Corrente disponível para as reignições.** A escalada de A ("the successive reignitions escalate the TRV to severe levels", [FATO: doc A, p. 3, V-A]) consiste em drenar sucessivamente frações do reservatório — 4,3 kJ pelo ramo tal como parametrizado, 16,3 kJ se escalado a $6{,}5\,I_n$ (ressalva 2); é o tamanho do reservatório, e não a energia do primeiro chopping, que fixa o teto da escalada [INFERÊNCIA FÍSICA].

**Verificação de coerência interna do modelo de A** [CÁLCULO PRÓPRIO]: o critério de extinção de alta frequência de A é di/dt crítico de 5–15 A/µs [FATO: doc A, Tabela II]. A corrente de frequência industrial atinge, no zero, 0,111 A/µs (regime) e 0,719 A/µs (partida) — **7 a 135 vezes abaixo do limiar**. Uma corrente de reignição de alta frequência a 100 kHz atinge 5 A/µs com amplitude de apenas $5\times10^6/(2\pi\times10^5) = 8$ A de pico [CÁLCULO PRÓPRIO]. Logo, o critério de di/dt de A **discrimina exclusivamente entre correntes de alta frequência**, nunca atua sobre a corrente de 60 Hz, e a magnitude de $I_p$ não entra nesse critério. O escopo qualitativo é **enunciado pelo próprio texto de A**, que escreve "the **subsequent high frequency current** is interrupted when its di/dt at the zero crossing exceeds a critical value (5 A µs⁻¹ to 15 A µs⁻¹)" [FATO: doc A, p. 3, IV-B]; o que A **não** faz é **quantificar a separação** — 0,111 e 0,719 A/µs contra 5–15 A/µs, e 8 A de pico a 100 kHz —, e é essa quantificação que é necessária para reproduzir o modelo. As larguras de janela derivadas acima (5,6 µs e 36 µs) são independentes de $L_{eq}$ e, portanto, não herdam a incerteza da ressalva 2.

### 3.3 O que NÃO está modelado nesse acoplamento

| Item | Situação | Rótulo |
|---|---|---|
| Temperatura do enrolamento no instante da manobra | Não é variável do modelo de A; $R_{eq}$ constante | [FATO por omissão: doc A] |
| Dependência de $R_{eq}$, $L_{eq}$ com o escorregamento | O ramo é fixo; o motor não desacelera nem acelera no modelo de A | [FATO por omissão: doc A, Fig. 2] |
| Dependência da suportabilidade $U_w$ com a temperatura | Ausente em A e em B | [FATO: ausência nos dois] |
| Instante da manobra dentro da partida (0 s? 5 s? 12 s?) | A fixa os instantes de separação em 14,55/24,75/24,81 ms de simulação [REPO: `git show ad308d5:trt_all_motors_dt_ea.atp:589,616,643`], o que é o instante **na onda de 60 Hz**, não o instante **na partida** | [FATO por omissão: doc A] |
| Efeito do afundamento (0,850 pu) sobre a corrente interrompida | **A não declara o módulo da tensão de fonte** — diz apenas "A three phase 60 Hz source represents the upstream MV feeder" [FATO: doc A, p. 3, IV-A], e nem a Tabela I (dados de placa) nem a Tabela II trazem valor de fonte; não há ocorrência de "pu" em A [FATO por omissão: doc A, p. 1–5, verificado por leitura integral]. **Assume-se 1,0 pu** [HIPÓTESE — plausível por ser o padrão de um estudo de caso, mas não declarada]. Sob essa hipótese, a interrupção real sob N-1 ocorreria a $\approx$ 0,85 pu, com $I = 0{,}85 \times 6{,}5\,I_n = 5{,}5\,I_n$ | [HIPÓTESE + INFERÊNCIA]; reduz o reservatório em $0{,}85^2 = 0{,}72$, isto é, −28 % [CÁLCULO PRÓPRIO] |

O último item é uma **correção necessária ao cruzamento**, condicionada à hipótese de fonte a 1,0 pu: se a manobra de A ocorre porque a proteção atuou por subtensão, então ela ocorre a $\approx 0{,}85$ pu, e o reservatório magnético é 28 % menor que o simulado por A. O cenário de A é, nesse aspecto, **conservador em relação ao cenário que B descreve** [INFERÊNCIA FÍSICA] — o que reforça a leitura da Etapa 1 (§9, item 4) de que os números de A são envelope, não estatística.

---

## 4. A cadeia térmica implícita em B, derivada — e que B não modela

**Advertência de escopo, aplicável a toda esta seção.** Nada aqui é resultado de B. B **não** modela térmica de motor, **não** calcula tempo de aceleração, **não** calcula $I^2t$ do motor, **não** compara com curvas de limite térmico e **não** trata partidas por hora [FATO: ausência, verificado por leitura integral de p. 1–6; fichamento B §8, itens 1–4]. A réplica térmica ANSI 49 de B é do **transformador**, referida ao estágio AF [FATO: doc B, p. 2, Tabela I]. Os parâmetros $J$, $T_L(\omega)$, $t_{LR}$ a quente, classe térmica e constante de tempo do motor de 1250 kW **não constam de nenhum dos dois documentos** [FATO: ausência em A e em B].

### 4.1 Torque e corrente sob tensão reduzida

Para carga de impedância constante em rotor bloqueado — o modelo declarado por B [FATO: doc B, p. 2] — a corrente é proporcional à tensão terminal:
$$
I_{start}(V_t) = K_{ir}\,I_n\,\frac{V_t}{V_n},
$$
com $I_{start}$ [A] a corrente drenada, $K_{ir}$ [pu] o múltiplo de rotor bloqueado, $I_n$ [A] a corrente nominal, $V_t$ e $V_n$ [V] a tensão terminal e a nominal [INFERÊNCIA FÍSICA: definição de carga de impedância constante]. A âncora normativa é explícita: "during starting time, a motor draws an inrush current **directly proportional to terminal voltage**" [NORMA: IEEE Std 399-1997, 9.3.1, p. 235].

O conjugado, ao contrário, é quadrático. A âncora normativa **verificável no texto acessado** é a cláusula 12.44.2: "Since the torque developed by the motor at any speed is **approximately** proportional to the **square** of the voltage and inversely proportional to the square of the frequency …" [NORMA: ANSI/NEMA MG 1-2016 (R2018), Parte 12, 12.44.2 — note-se o qualificador "approximately", que não deve ser suprimido]. A formulação "The locked-rotor and breakdown torque will be proportional to the square of the voltage applied", atribuída à cláusula 14.30 por fonte secundária [LITERATURA: Bonnett & Boteler, ACEEE 2001, p. 2], **não foi localizada com essa numeração** no texto acessado da MG 1-2016 (R2018) — possivelmente numeração de edição anterior [INSERIR CITAÇÃO — cláusula não localizada]. A física é, de todo modo, independentemente ancorada: "Only 25 % torque is available … with 50 % of rated voltage" [NORMA: IEEE Std 399-1997, 9.3.1, p. 235], que é $0{,}5^2$ [CÁLCULO PRÓPRIO].

$$
T_m(\omega, V_t) = T_m(\omega, V_n)\left(\frac{V_t}{V_n}\right)^{2}.
$$

Tabela derivada para as tensões de B [CÁLCULO PRÓPRIO: $V^2$ e $K_{ir}V$; tensões de FATO: doc B, p. 2–3]:

| Condição (doc B) | $V_t$ [pu] | $T_m/T_m(1)$ | queda de conjugado | $I/I_n$ | queda de corrente |
|---|---|---|---|---|---|
| Sem corte (infactível) | 0,755 | 0,570 | **−43,0 %** | 4,91 | −24,5 % |
| Mínimo corte | 0,850 | 0,7225 | **−27,8 %** | 5,52 | −15,0 % |
| Joelho | 0,858 | 0,736 | −26,4 % | 5,58 | −14,2 % |
| Mínimas perdas | 0,866 | 0,750 | −25,0 % | 5,63 | −13,4 % |

**Precisão obrigatória sobre "torque acelerante".** A 0,850 pu, o que cai 27,75 % é o **conjugado motor**, não o conjugado acelerante. O conjugado acelerante é $T_a = T_m - T_L$, e $T_L$ **não** escala com a tensão (a carga mecânica ignora a tensão de alimentação). Logo, para todo $T_L > 0$,
$$
\frac{T_a(V)}{T_a(1)} = \frac{T_m(1)V^2 - T_L}{T_m(1) - T_L} \;<\; V^2 ,
$$
isto é, **o conjugado acelerante cai mais que 27,8 %** [INFERÊNCIA FÍSICA]. Exemplo com parâmetros hipotéticos declarados ($k_T = 0{,}7$ pu de conjugado médio de partida, carga quadrática com $k_L = 1$ e fator médio $f_L = 1/3$, isto é, $T_L$ médio $= 0{,}333$ pu) [HIPÓTESE; parâmetros ausentes em A e B]:
$$
\frac{T_a(0{,}85)}{T_a(1)} = \frac{0{,}7\times0{,}7225 - 0{,}3333}{0{,}7 - 0{,}3333} = \frac{0{,}1725}{0{,}3667} = 0{,}470
\quad\Rightarrow\quad \textbf{queda de 53 \%}
$$
[CÁLCULO PRÓPRIO]. A assimetria decisiva é esta: **a corrente cai 15 % e o conjugado acelerante cai 53 %**, o que alonga a aceleração e aumenta $\int i^2\,\mathrm{d}t$.

### 4.2 Tempo de aceleração e a divergência da integral

A equação do movimento e sua integral:
$$
J\,\frac{\mathrm{d}\omega}{\mathrm{d}t} = T_m(\omega)\left(\frac{V_t}{V_n}\right)^{2} - T_L(\omega)
\qquad\Longrightarrow\qquad
\boxed{\;t_{acc}(V_t) = \int_{0}^{\omega_f} \frac{J\,\mathrm{d}\omega}{\,T_m(\omega)\,(V_t/V_n)^2 - T_L(\omega)\,}\;}
\tag{4.2}
$$
com $t_{acc}$ [s] o tempo de aceleração, $J$ [kg·m²] a inércia total (motor + carga refletida), $\omega$ [rad/s] a velocidade angular do rotor, $\omega_f$ [rad/s] a velocidade final (usualmente 0,95 $\omega_s$), $T_m(\omega)$ [N·m] o conjugado motor à tensão nominal, $T_L(\omega)$ [N·m] o conjugado resistente da carga, $V_t$ e $V_n$ [V] as tensões terminal e nominal [INFERÊNCIA FÍSICA: segunda lei de Newton para rotação]. A IEEE 399 exige, para o estudo de aceleração, exatamente os dois dados que faltam: $Wk^2$ do motor e da carga e as curvas conjugado–velocidade [NORMA: IEEE Std 399-1997, cap. 9, p. 239].

**Por que a integral diverge.** O integrando é $J/[T_m(\omega)V^2 - T_L(\omega)]$. Se em algum $\omega^\ast \in [0,\omega_f]$ o denominador se anula — isto é, se o conjugado motor reduzido pela tensão encontra o conjugado de carga —, o integrando tem polo **não integrável de primeira ordem** e $t_{acc} \to \infty$: fisicamente, o rotor estaciona em $\omega^\ast$ e não completa a partida. Esse é o fenômeno de *stall*.

A partida completa-se **se e somente se** $V^2 T_m(\omega) > T_L(\omega)$ para **todo** $\omega$ do percurso, isto é, $V > g(\omega) := \sqrt{T_L(\omega)/T_m(\omega)}$ para todo $\omega$, o que exige $V$ acima do **supremo** de $g$. Logo a tensão mínima de partida é
$$
V_{stall} \;=\; \max_{\omega\in[0,\omega_f]} \sqrt{\frac{T_L(\omega)}{T_m(\omega)}} \;,
\qquad\text{e, na aproximação de conjugado médio,}\qquad
V_{stall} = \sqrt{\frac{f_L\,k_L}{k_T}} ,
\tag{4.3}
$$
com $k_T$ [pu] o conjugado médio de partida, $k_L$ [pu] o conjugado nominal de carga e $f_L$ o fator de conjugado médio ($1$ constante, $1/2$ linear, $1/3$ quadrática, $1/4$ cúbica) [INFERÊNCIA FÍSICA; a forma de conjugado médio é a implementada no repositório, REPO: `app/postprocessor/motor_starting.py:410-453`, que retorna `float('inf')` em `if T_motor_avg <= T_load_avg` e usa exatamente os fatores CONSTANT 1,0 / LINEAR 0,5 / QUADRATIC 1/3 / CUBIC 1/4].

**Nota obrigatória sobre o operador** [INFERÊNCIA FÍSICA]: o binding point é o $\omega$ de **maior** razão $T_L/T_m$ — tipicamente o **vale de conjugado** (*pull-up torque*), que é onde motores de MT efetivamente estacionam. Usar o mínimo selecionaria o ponto **menos** restritivo da curva e seria erro **não conservador**, declarando factíveis partidas que estagnam. Na aproximação de conjugado médio adotada nesta subseção — em que a curva $T_m(\omega)$ é substituída por um único valor e $g(\omega)$ é constante — **máximo e mínimo colapsam no mesmo escalar** $\sqrt{f_L k_L/k_T}$, de modo que todos os valores numéricos tabulados adiante (0,690 / 0,577 / 0,845 / 0,707) permanecem válidos e inalterados; e é justamente o vale de conjugado que essa aproximação apaga.

Na mesma aproximação de conjugado médio,
$$
\frac{t_{acc}(V)}{t_{acc}(1)} = \frac{k_T - f_L k_L}{k_T V^2 - f_L k_L},
\qquad
\frac{I^2t(V)}{I^2t(1)} = V^2\,\frac{t_{acc}(V)}{t_{acc}(1)} .
\tag{4.4}
$$

Valores derivados para as tensões de B, **com todos os parâmetros declarados como hipótese** [CÁLCULO PRÓPRIO sobre (4.3)–(4.4); $k_T$, $k_L$, $f_L$ são [HIPÓTESE] — nem A nem B informam conjugado de partida ou tipo de carga]:

| Caso [HIPÓTESE] | $V_{stall}$ | 0,755 pu | 0,850 pu | 0,858 pu | 0,866 pu |
|---|---|---|---|---|---|
| $k_T=0{,}7$; carga quadrática ($f_Lk_L=1/3$) | 0,690 | $t$: 5,58× / $I^2t$: 3,18× | 2,13× / 1,54× | 2,01× / 1,48× | 1,91× / 1,43× |
| $k_T=1{,}0$; carga quadrática | 0,577 | 2,82× / 1,61× | 1,71× / 1,24× | 1,65× / 1,22× | 1,60× / 1,20× |
| $k_T=0{,}7$; carga constante ($f_Lk_L=0{,}5$) | **0,845** | **não acelera** | 34,8× / 25,1× | 13,1× / 9,6× | 8,0× / 6,0× |
| $k_T=1{,}0$; carga constante | 0,707 | 7,14× / 4,07× | 2,25× / 1,62× | 2,12× / 1,56× | 2,00× / 1,50× |

Três leituras [INFERÊNCIA a partir da tabela]:

1. **Na condição que B declara infactível (0,755 pu), a partida pode simplesmente não completar** para carga de conjugado constante com $k_T$ modesto — resultado qualitativamente diferente de "a proteção atua", e que B não pode produzir porque não integra (4.2).
2. **A diferença entre as três soluções factíveis de B é pequena em $V$ e grande em $t_{acc}$.** Entre 0,850 e 0,866 pu há 1,9 % de tensão; no caso de carga constante com $k_T = 0{,}7$, há **4,4× de diferença em tempo de aceleração** (34,8× contra 8,0×) e **4,2× em $I^2t$**. A restrição $g_1$ trata as três como equivalentes (todas factíveis); um critério térmico as separa por fator de várias unidades.
3. **0,850 pu é escolha de risco justamente porque $V_{stall}$ pode estar imediatamente abaixo.** No terceiro caso da tabela, $V_{stall} = 0{,}845$ pu — a **0,6 % abaixo** do ponto de operação recomendado por B. Com o modelo quase-estático não há como saber: (4.2) não é avaliada, e $V_{\min}$ é o valor instantâneo de rotor bloqueado, não a trajetória.

**Ressalva de honestidade sobre a aproximação de conjugado médio** [INFERÊNCIA]: (4.4) superestima a sensibilidade nas vizinhanças de $V_{stall}$, porque substitui a curva $T_m(\omega)$ real (com vale de conjugado e conjugado máximo) por um valor médio. É exatamente esse o regime em que a distinção entre máximo e mínimo em (4.3) deixa de ser vácua: **com $T_m(\omega)$ real, o ponto ativo é o vale de conjugado**, e a aproximação de conjugado médio o apaga — de modo que o $V_{stall}$ escalar da tabela acima é, ele próprio, uma **subestimativa** da tensão mínima real de partida. O mesmo vale para o repositório, que implementa a mesma aproximação de média e por isso também não distingue os dois operadores [REPO: `app/postprocessor/motor_starting.py:410-453`].

A especificação de O&G impõe capacidade de acelerar a carga a 80 % da tensão nominal e margem de conjugado acelerante $\ge$ 10 % nessa condição [NORMA: IOGP S-704 v1.0, 9.12.1.2–9.12.1.3, numeração riscada no redline v2.0 × v1.0; equivalentes na v2.0: 11.3.1.4 e 11.3.1.6 — "Inclusive of the negative tolerance, the accelerating torque of the motor at the rated frequency with 80 % of the rated voltage applied at the motor terminals shall be at least 10 % of the full load torque **at any point**"], o que, **se atendido pelo alvo**, exclui os casos "não acelera" acima de 0,80 pu. Registre-se que o "at any point" da cláusula v2.0 **corrobora o operador de (4.3)**: a norma exige a margem em todo ponto da curva, não em média [INFERÊNCIA]. Nem A nem B declaram conformidade com essa especificação [FATO: ausência].

### 4.3 De $I^2t$ à temperatura de ponto quente e à vida

Com corrente aproximadamente constante durante a aceleração (limite superior conservador),
$$
I^2t(V) \approx \bigl(K_{ir}I_n\bigr)^2 V^2\, t_{acc}(V),
\qquad
U(V) = \frac{I^2t(V)}{I_{LR}^2\,t_{LR,\mathrm{hot}}} = \frac{V^2\,t_{acc}(V)}{t_{LR,\mathrm{hot}}},
\tag{4.5}
$$
com $U$ [pu] a fração da capacidade térmica a quente consumida pela partida, $I_{LR}$ [A] a corrente de rotor bloqueado à tensão nominal e $t_{LR,\mathrm{hot}}$ [s] o tempo admissível de rotor bloqueado a quente [INFERÊNCIA FÍSICA: efeito Joule com resistência constante; normalização pela curva de limite térmico].

A âncora normativa é a IEEE 620: "The thermal limitations of induction motors are specified by thermal limit curves that are **plots of the limiting temperature of the rotor and stator in units of $I^2t$**", com duas condições iniciais, "cold" (ambiente) e "hot" (temperatura de operação) [NORMA: IEEE Std 620, escopo; LITERATURA: Zocholl & Benmouyal, WPRC 2001, p. 2 (PDF 3)]. A IEEE 620 **padroniza a apresentação e declara não informar como as curvas são construídas** — "Otherwise, the guide gives no information as to how the curves are constructed" [LITERATURA: Zocholl & Benmouyal, WPRC 2001, p. 2–4] —, de modo que qualquer $I^2t$ "de catálogo" sem a curva do fabricante é [HIPÓTESE].

**Advertência obrigatória sobre (4.5)**: com resistência rotórica fixa, "the relay … **overestimates the temperature during valid start**. This is the cause of premature tripping when starting a high-inertia motor"; num exemplo documentado, "The rotor reaches only 72 % of the limiting temperature while the $I^2t$ relay trips" [LITERATURA: Zocholl, SEL 2007/2012, p. 4–5 (PDF)]. Portanto (4.5) é **limite superior**, e deve ser reportada como tal.

Referências numéricas verificadas para ordem de grandeza [LITERATURA: Zocholl, SEL 2007/2012, p. 6 (PDF 7)]: motor de 7000 hp / 900 rpm com $I_{LR} = 6{,}3$ pu, $t_{LR}$ frio 14 s, quente 12 s, $\tau_{estator} = 950$ s. Para outro caso, 400 hp / 3600 rpm: a 2 pu, $t_{hot} = 223$ s contra $t_{cold} = 279$ s, isto é, **−20 % de capacidade a quente** [LITERATURA: Zocholl & Benmouyal, WPRC 2001, p. 2–4].

**O confronto decisivo com B** [INFERÊNCIA a partir de FATO: doc B, p. 2 e das fontes acima]: B exclui o *snapshot* INRUSH da restrição $g_3$ com o argumento — correto para o transformador — de que "it lasts about 10 s, far shorter than the thermal time constant of an oil immersed unit, and falls within the short duration loading capability defined in the IEEE loading guide [19]" [FATO: doc B, p. 2]. Mas **10 s é da mesma ordem do $t_{LR,\mathrm{hot}}$ de um motor de MT**: no único caso documentado acessado, 12 s a quente e 14 s a frio, para 7000 hp / 900 rpm [LITERATURA: Zocholl, SEL 2007/2012, p. 6 (PDF 7)]. A faixa 10–20 s usada adiante como *default* é **generalização a partir desse único ponto** — de máquina de porte muito superior ao alvo de 1250 kW e de baixa rotação (900 rpm, portanto inércia e $t_{LR}$ maiores que os de uma máquina de 2 ou 4 polos) —, e é [HIPÓTESE] até obtenção da curva do fabricante, coerentemente com o que a §10.3 já declara. O que é desprezível para o transformador (constante térmica de horas) é **crítico** para o motor (constante térmica de rotor de segundos). B não comete erro: B não fala do motor. Mas a exclusão do INRUSH de $g_3$ deixa **sem nenhum guardião térmico** exatamente o componente que o módulo de RUL protege.

Da temperatura à vida, com a equação D6 da Etapa 1:
$$
L(\theta) = L_0\,2^{(\theta_0-\theta)/\mathrm{HIC}},
\qquad
\mathrm{AF}(\theta) = 2^{(\theta-\theta_0)/\mathrm{HIC}},
\qquad
\Delta L_{start}(V) = \frac{1}{L_0}\int_0^{t_{cool}} \mathrm{AF}\bigl(\theta_{hs}(t;V)\bigr)\,\mathrm{d}t,
\tag{4.6}
$$
com $L$ [h] a vida térmica, $\theta$ [°C] a temperatura de ponto quente, $\theta_0$ [°C] a temperatura de referência, HIC [°C] o intervalo de bissecção de vida e AF o fator de aceleração [Etapa 1, §5.4, D6; LITERATURA: Theofanous et al., *Energies* 18:6087, 2025, eqs. (9)–(10)]. Faixa de HIC: 8–15 °C conforme o material; a "regra dos 10 °C" é caso particular; a observação original de Montsinger (1930) foi $\approx$ 8 °C em cambraia envernizada [LITERATURA: idem, p. 7–8, 11]. Sensibilidade [CÁLCULO PRÓPRIO: $2^{\Delta\theta/\mathrm{HIC}}$]:

| $\Delta\theta$ | HIC = 8 K | HIC = 10 K | HIC = 15 K |
|---|---|---|---|
| +10 K | 2,38× | 2,00× | 1,59× |
| +20 K | 5,66× | 4,00× | 2,52× |
| +30 K | 13,45× | 8,00× | 4,00× |

A dispersão a +20 K é de $5{,}66/2{,}52 = 2{,}25\times$ [CÁLCULO PRÓPRIO]: HIC deve ser tratado como **parâmetro incerto propagado**, jamais fixado em 10 K sem ensaio IEC 60034-18-31 do fabricante [INSERIR CITAÇÃO — norma não acessada].

Limites por classe, para fixar $\theta_0$ [NORMA: IEC 60034-1, Tabela 7, via Leroy-Somer TN11; NEMA MG 1 via PSRC C37.96, p. 17–18 (PDF); LITERATURA: WEG, Guia de especificação, Tab. 7.1]: ambiente 40 °C + elevação (método da resistência: B 80 K, F 105 K, H 125 K) + margem de ponto quente (B/F 10 K, H 15 K) = 130 / 155 / 180 °C. Prática de O&G: "The motor insulation system shall be thermal class 155 (F) in accordance with IEC 60085 **without exceeding thermal class 130 (B) temperature rise** for the motor rated output at the maximum reference coolant temperature" [NORMA: IOGP S-704 v2.0, 8.1, transcrição literal]. A comparação deve ser feita em **uma única convenção**, sob pena de misturar limite com ponto quente e valor médio por resistência: a margem é $155 - 130 = 25$ K em base de ponto quente, equivalentemente $145 - 120 = 25$ K em base de valor médio por resistência, ou $105 - 80 = 25$ K em base de **elevação** — que é a base em que a cláusula 8.1 está escrita [CÁLCULO PRÓPRIO]. **A margem térmica de projeto é, portanto, de 25 K**, e não os 35 K que resultariam de subtrair o limite de F com ponto quente (155 °C) do valor de B sem ponto quente (120 °C). **A classe térmica do motor de 1250 kW não consta de nenhum dos dois documentos** [FATO: ausência].

### 4.4 Orçamento de partidas: o limite que nenhum dos dois documentos verifica

| Critério | Enunciado | Fonte | Escopo de aplicação |
|---|---|---|---|
| Mínimo NEMA | "Two starts in succession (coasting to rest between starts) with the motor initially at the ambient temperature **or** one start with the motor initially at a temperature not exceeding its rated load operating temperature" | [NORMA: ANSI/NEMA MG 1, 12.54.1, via FAQ NEMA 1.41] | **Não aplicável ao caso.** 12.54.1 vale para "Design A and B squirrel-cage induction motors having horsepower ratings given in 10.32.4", e a cláusula de escopo 12.1 limita a Parte 12 a motores CA até 500 hp a 3600/1800 rpm, 350 hp a 1200 rpm e 250 hp a 900 rpm. O alvo de 1250 kW ($\approx$ 1676 hp) e as cortadas de 710 e 800 kW ($\approx$ 952 e 1073 hp) são **máquinas grandes** (Seção III da MG 1), fora do escopo da Parte 12 [NORMA: ANSI/NEMA MG 1-2016 (R2018), 12.1 e 12.54.1] |
| **"per hour" não consta na NEMA — mas consta na IOGP** | A FAQ do próprio comitê registra que a expressão "per hour" não está em 12.54.1 | [NORMA: idem]; "Large motors are generally not rated for starts per hour" [LITERATURA: L&B Electric, 1998, p. 1] | Por máquina. **Ressalva**: o contraste é menos forte do que parece, porque a Tabela 25 da IOGP S-704 v2.0 — que é a âncora aplicável a máquinas de MT — traz explicitamente "minimum number of consecutive starts **per hour**" |
| Mínimo IEC/ABNT | Duas partidas sucessivas a frio; uma a quente | [LITERATURA: WEG, Guia de especificação, p. 29, reproduzindo ABNT NBR 17094 / IEC 60034-1] | Por máquina, em sequência consecutiva |
| Prática O&G — religamento | "Minimum number of consecutive starts **per hour**": 3 a frio ("initial temperature at or below the maximum ambient"), 2 a quente; nota: "The motor should coast to rest between consecutive starts" | [NORMA: IOGP S-704 v2.0, Tabela 25 — "Add new Table 25", transcrição literal; substitui 9.12.2.1–9.12.2.5 da v1.0] | **Por máquina e por hora** |
| Prática O&G — vida e frequência anual | Vida mínima de 5000 partidas a plena tensão; mínimo de 1000 partidas/ano | [NORMA: IOGP S-704 v2.0, 11.3.1.3; v1.0, 9.12.2.5 (numeração riscada no redline)] | Por máquina |
| Prática O&G — corrente de rotor bloqueado | "For motors without specific starting requirements, the locked rotor current shall be between 4,0 and 6,5 times the rated current" | [NORMA: IOGP S-704 v2.0, 11.3.1.1; v1.0, 9.12.1.1] | Por máquina |
| Critério de coordenação partida × rotor bloqueado | v1.0: "At 80 % of rated voltage at the motor terminals, the minimum **hot** locked-rotor time shall be at least **5 seconds more** than the time required to accelerate the specified driven load"; v2.0: "The locked rotor withstand time under hot condition shall be greater than the time required to accelerate the specified driven load at 80 % of rated voltage at the motor terminals plus 5 s" | [NORMA: IOGP S-704 v1.0, 9.12.1.5, numeração riscada no redline; v2.0, 11.3.1.5] | Por máquina |

**Advertência sobre a numeração das cláusulas IOGP** [NORMA]: no documento acessado — o redline v2.0 × v1.0, nov. 2024 — a numeração **9.12.x é a da v1.0, riscada**; os requisitos vigentes na v2.0 estão em **11.3.1.x** e na **Tabela 25**. As transcrições literais desta etapa conferem palavra por palavra com o texto correspondente; o que foi corrigido aqui é a **versão atribuída à numeração**.

Consequência direta para o cruzamento [INFERÊNCIA]: o plano de corte de B implica, além da partida do alvo, o **religamento de cada máquina cortada** — 17 no plano de mínimo corte (M_710 e M_800 mantidas), 18 no joelho (M_800 mantida) e 19 no de mínimas perdas [FATO: doc B, p. 3, Tabela III]. B não modela nenhum religamento [FATO: ausência; fichamento B §8, item 7]. Duas precisões, ambas necessárias:

- **A ordem do erro de contagem é 18 a 20, não 17 a 19.** A contabilidade de B registra **uma** partida (a do alvo) contra **18 a 20** manobras efetivas (1 do alvo + 17 a 19 religamentos), isto é, um fator de 18 a 20; os números 17 a 19 são os **religamentos adicionais não modelados**, não o fator multiplicativo [CÁLCULO PRÓPRIO].
- **Não existe "orçamento de partidas da planta" agregável.** Os limites de NEMA 12.54.1, da IEC 60034-1/ABNT NBR 17094 e da Tabela 25 da IOGP são todos **por máquina** e por sequência consecutiva; 17 religamentos são 17 máquinas **distintas** consumindo uma partida cada do próprio orçamento, e não 17 partidas de um orçamento único. O enunciado defensável é, portanto: **B não modela a sequência de religamentos nem o intervalo entre eles**, e é a sequência — contra os mínimos por máquina, com o qualificador "por hora" da Tabela 25 da IOGP — que precisa ser verificada, não um múltiplo de um orçamento agregado. Para o alvo de 1250 kW, a âncora aplicável é a Tabela 25 da IOGP e o dado do fabricante, **não** a NEMA 12.54.1, que está fora de escopo [NORMA: ANSI/NEMA MG 1, 12.1].

Feita a correção, a conclusão de mérito permanece e fica melhor fundamentada: contra mínimos de 2 a 3 partidas consecutivas **por máquina e por hora**, um plano que exige 18 a 20 manobras numa mesma janela operacional não é detalhe — é a diferença entre uma manobra e um **regime** de manobras, e nenhum dos dois documentos o contabiliza.

---

## 5. Sinergia multiestresse: por que a combinação consome RUL mais que a soma

### 5.1 O mecanismo, nas duas direções

**Direção térmica → elétrica.** O envelhecimento térmico reduz a suportabilidade dielétrica residual. A Etapa 1 já formalizou a suportabilidade como variável de estado (§6):
$$
U_w(t) = U_{w,0}\,\psi\bigl(D(t)\bigr),\qquad \psi(0)=1,\ \psi'<0,
\qquad
\gamma(t) = \frac{U_w(t)}{U_s},
$$
com $U_w$ [kV] a suportabilidade real, $U_{w,0}$ [kV] a inicial verificada em ensaio de tipo, $D$ o dano acumulado, $\gamma$ a **margem de coordenação** e $U_s$ [kV] a solicitação de projeto [Etapa 1, §6]. A evidência de que $U_w$ decai sob envelhecimento é indireta mas convergente: bobinas envelhecidas por *voltage endurance* e por ciclagem térmica foram ensaiadas a surto até a falha "para avaliar o efeito adverso do envelhecimento" [LITERATURA: Haq, Omranipour e Teran, IEEE EIC 2014, resumo — **valores numéricos não acessados**]; os motores cuja suportabilidade estava abaixo dos surtos de serviço eram os "severamente envelhecidos" [LITERATURA: Gupta et al., IEEE TEC EC-2(4), 1987, Parte 3, resumo]; ruptura $\ge$ 5 pu na maioria de 17 motores ensaiados contra $\ge$ 10 pu em máquinas **novas** [LITERATURA: idem, Parte 2, resumo]; e a prática normativa de reduzir o nível de ensaio a 75 % em máquinas em serviço [LITERATURA secundária: Electrical Trader / Electrom, citando IEEE 522-2023 — **HIPÓTESE a verificar no texto primário**].

O efeito sobre o acumulador é direto e não é aditivo: em D7 da Etapa 1, o número de eventos suportáveis é
$$
N_j = N_0\left(\frac{a(t_{f,j})\,V_{pk,j} - V_{th}}{V_{ref}-V_{th}}\right)^{-n}\left(\frac{t_{f,j}}{t_{f,0}}\right)^{m} 2^{(\theta_0-\theta_j)/\mathrm{HIC}}
$$
[Etapa 1, §5.4, D7, **com a correção de sinal do fator térmico introduzida na §3.1** — a forma impressa na Etapa 1 traz $2^{(\theta_j-\theta_0)/\mathrm{HIC}}$, que é inconsistente com D6 e faria o dano decrescer com a temperatura]. Se o envelhecimento térmico **reduz $V_{th}$** (o limiar de dano acompanha a suportabilidade residual), então um evento antes inócuo ($a V_{pk} \le V_{th}$, $1/N_j = 0$) passa a ser danoso, e a transição é **descontínua**, não proporcional [INFERÊNCIA FÍSICA a partir da forma de D7]. A Etapa 1 mostrou que essa descontinuidade domina o resultado: "com $V_{th}$ entre 4,0 e 12,2 pu, … a mitigação move o evento para **abaixo do limiar de dano**, o que é uma conclusão muito mais forte do que a redução percentual do pico" [Etapa 1, §5.5]. O corolário simétrico é que **o envelhecimento térmico move o evento de volta para cima do limiar**.

**Direção elétrica → térmica.** O surto aquece localmente o dielétrico. Evidência experimental verificada: queda de vida da isolação de massa de $\approx$ 58 % (sem refrigeração) contra $\approx$ 31 % (com refrigeração) sob envelhecimento por pulsos, **evidenciando aquecimento dielétrico** [LITERATURA: CIGRE WG D1.43, TB 703, p. 35–36, Tab. 4]. Isto é: o mesmo estresse elétrico produz quase o dobro de perda de vida quando o calor não é removido — prova direta de que as duas parcelas não são independentes. Adicionalmente, a própria revisão de envelhecimento térmico adverte que "Mechanical fatigue, vibration-induced stress, or **electric field effects** … are not explicitly accounted for … but **can become significant in applications involving strong electro-mechanical coupling or repetitive start-stop cycles**" [LITERATURA: Theofanous et al., *Energies* 2025, p. 31] — descrição literal do regime deste módulo.

### 5.2 O acumulador combinado proposto

$$
\boxed{\;
D(t)\;=\;\underbrace{\int_0^{t} \frac{\mathrm{d}\tau}{L\bigl(\theta(\tau)\bigr)}}_{D^{th}(t)\ \text{— térmico}}
\;+\;\underbrace{\sum_{m\,\le\,t} \Delta D_m^{el}}_{D^{el}(t)\ \text{— elétrico por manobra}}
\;+\;\underbrace{D_{sin}(t)}_{\text{sinergia}}
\;}
\tag{5.1}
$$

$$
\Delta D_m^{el} = \sum_{j=1}^{n_{r,m}} \frac{1}{N_j\bigl(U_w(\theta,D)\bigr)},
\qquad
\frac{1}{N_j} = 0 \ \ \text{sempre que}\ \ a(t_{f,j})\,V_{pk,j} \le V_{th}\bigl(U_w(\theta,D)\bigr) ,
\tag{5.2}
$$

com: $D$ [adimensional] o dano acumulado, falha convencionada em $D=1$; $\theta(\tau)$ [°C] a trajetória de temperatura de ponto quente, que inclui os transitórios de partida de (4.6); $L(\theta)$ [h] a vida térmica de D6; $m$ o índice de manobra; $j$ o índice de reignição dentro da manobra; $n_{r,m}$ o número de reignições por polo na manobra $m$; $N_j$ [eventos] o número de eventos suportáveis no nível de estresse $j$, agora **dependente do estado** $U_w(\theta,D)$; $V_{pk,j}$ [V] o pico da $j$-ésima frente **no terminal do motor**; $a(t_f)$ [adimensional] a fração que recai sobre a primeira bobina; $V_{th}$ [V] o limiar de dano [Etapa 1, §5.4, D2 e D7].

**Ancoragem de cada parcela:**

| Parcela | Ancoragem | Rótulo |
|---|---|---|
| $D^{th}$ | Forma contínua da regra de Miner para envelhecimento térmico, $\mathrm{LF} = \int \mathrm{d}t/L(\theta(t))$ | [LITERATURA: Theofanous et al., *Energies* 2025, eqs. (17)–(19); Etapa 1, D4 e D6] |
| $D^{el}$ | Miner discreta sobre eventos, com $N_j$ por lei de potência inversa com limiar e correção de frente | [Etapa 1, D1–D3, D7; LITERATURA: Feilat, IntechOpen 2018, eq. (21); CIGRE TB 703, p. 29, Fig. 31] |
| Acoplamento $V$–$T$ dentro de $N_j$ | Modelo multiestresse de Simoni, $L(V,T)=t_0(V/V_0)^{-n}\exp(-B c_T)$, $c_T = 1/T_0 - 1/T$; Ramu com $K(T)$ e $n(T)$; Montanari probabilístico com $\beta(T)$ | [Etapa 1, D5; LITERATURA: Feilat 2018, eqs. (26), (27), (29); INSERIR CITAÇÃO primária: Simoni 1981/1984; Montanari, Mazzanti e Simoni, IEEE TDEI 9:730–745, 2002] |
| Contabilidade anual por perfil de missão | $CL_n = 100/N_{n,\mathrm{life}}$, $CL_{1\,\mathrm{ano}} = \sum_n CL_n$, e extrapolação ponderada pela distribuição de condições | [FATO: artigo 12, Ma et al., eqs. (1)–(3), p. 5, 7] |

**Definição operacional do termo de sinergia** [PROPOSTA]. A forma (5.1) é **aditiva por conveniência de auditoria**; a física é implícita, porque (5.2) depende de $D$, o que torna o sistema autoacoplado:
$$
\dot D = F\bigl(D,\theta,\{\mathbf{s}_{m,j}\}\bigr),\qquad \frac{\partial F}{\partial D} > 0 \ \ \text{[HIPÓTESE de monotonicidade — ver ressalva adiante]} .
$$
Define-se então, sem introduzir parâmetro novo:
$$
D_{sin}(t) \;:=\; D_{\text{exato}}(t) \;-\; \bigl[D^{th}(t) + D^{el}(t)\bigr],
\tag{5.3}
$$
em que $D_{\text{exato}}$ é a solução do sistema autoacoplado e $D^{th}$, $D^{el}$ são as soluções **desacopladas** (cada mecanismo avaliado com $U_w$ congelado no valor inicial) [PROPOSTA; formalização própria].

**Sinal do termo — enunciado condicional** [INFERÊNCIA FÍSICA]: **sob a hipótese $\partial F/\partial D > 0$**, o teorema de comparação para EDO escalar dá $D_{\text{exato}} \ge D^{th} + D^{el}$, isto é, $D_{sin}(t) \ge 0$ para todo $t$ — pois a solução desacoplada equivale a $F$ avaliada com $D$ congelado no valor inicial. A implicação é correta; a **premissa não é automática** e deve ser declarada como tal, porque **D7 pode violá-la**:

> Em D7, $1/N_j \propto \bigl[(a V_{pk} - V_{th})/(V_{ref}-V_{th})\bigr]^{n}$. Derivando essa razão $r$ em relação a $V_{th}$: $\partial r/\partial V_{th} = (a V_{pk} - V_{ref})/(V_{ref}-V_{th})^2$. Logo, para eventos **mais severos que a referência** ($a V_{pk} > V_{ref}$) — que é exatamente o regime dos 30–41 kV de A —, reduzir $V_{th}$ pelo envelhecimento **reduz** $r$, **aumenta** $N_j$ e **diminui** o dano calculado por evento, dando $\partial F/\partial D < 0$ [CÁLCULO PRÓPRIO sobre D7]. O sinal é o afirmado apenas para eventos **abaixo de $V_{ref}$**, e — caso particular decisivo — para a **travessia do limiar** descrita na §5.1 ($1/N_j = 0 \to 1/N_j > 0$), que é o argumento efetivamente usado ali.

Isto é **artefato da normalização** $(V_{ref}-V_{th})$ no denominador de D7, não física [INFERÊNCIA]. Duas saídas, ambas registradas como pendência (§11.1, item 11): (i) manter D7 e enunciar $D_{sin} \ge 0$ **condicionado** ao regime $a V_{pk} \le V_{ref}$ e à travessia de limiar; ou (ii) reparametrizar D7 normalizando o estresse pela **suportabilidade residual**, $a V_{pk}/U_w(\theta,D)$, em vez de deslocá-lo por $V_{th}$ — o que torna $\partial F/\partial D > 0$ **estrutural** e é a forma preferível para o módulo. Feita essa ressalva, a consequência de decisão é a única afirmação forte que esta seção autoriza:

> **Sob $\partial F/\partial D > 0$, a soma desacoplada é um limite inferior do dano; portanto, uma estimativa de RUL que ignore a sinergia é sistematicamente otimista.** Um módulo que reporte apenas $D^{th}+D^{el}$ deve declará-lo como cota inferior de dano (cota superior de RUL), nunca como estimativa central — e deve declarar junto a premissa de monotonicidade, verificando-a na parametrização efetivamente adotada para $N_j$.

**Ausência de parâmetros — declaração obrigatória** [INSERIR CITAÇÃO]: nenhuma fonte primária acessada nesta sessão fornece parâmetros medidos para $\psi(\cdot)$, para a dependência $V_{th}(\theta)$ ou para $D_{sin}$ em mica-epóxi pré-formada de MT. O que existe é: (i) a evidência qualitativa de aquecimento dielétrico da CIGRE TB 703 (p. 35–36); (ii) os modelos multiestresse de Simoni/Ramu/Montanari, cujos parâmetros $B$, $n(T)$, $\beta(T)$ **não** foram localizados para esse material; (iii) a advertência da Etapa 1 (§9, item 9) de que a soma independente das parcelas é aproximação. **(5.1)–(5.3) são formulação proposta, não resultado.**

### 5.3 Onde a sinergia se manifesta neste caso concreto

Encadeando §2, §3 e §4, a partida sob N-1 é o **único evento do ciclo de vida da máquina em que os dois estresses coincidem no tempo e no lugar**:

| Instante | Estresse térmico | Estresse elétrico | Coincidência |
|---|---|---|---|
| $t \in [0, t_{acc}]$, partida a 0,850 pu | $I^2t$ elevado, $\theta_{hs}$ crescente (§4.3) | Nenhum (regime de 60 Hz) | — |
| $t = t_{trip} \le t_{acc}$, atuação da proteção | $\theta_{hs}$ no máximo do transitório | Chopping + reignições, SFI repetitivo (§2.2, L6–L8) | **Máxima** |
| $t > t_{trip}$, resfriamento | $\theta_{hs}$ decai com $\tau \sim 10^3$ s | Nenhum | — |

A leitura operacional [INFERÊNCIA]: o SFI de A incide sobre um enrolamento na sua temperatura transitória mais alta, o que — pelo fator térmico de D7 na forma corrigida, $1/N_j \propto 2^{(\theta_j-\theta_0)/\mathrm{HIC}}$ (§3.1) — multiplica a taxa de dano por 2× a 5,7× para +10 a +20 K [CÁLCULO PRÓPRIO, §4.3]. **Nenhum dos dois documentos permite avaliar essa multiplicação**, porque A não tem $\theta$ e B não tem $\theta$ do motor [FATO: ausência nos dois].

---

## 6. *Health-aware load shedding*: como o RUL entra na formulação de B

### 6.1 Transcrição das equações (1)–(4) de B

Com limites de *ride-through* $V^{ir} = 0{,}85$ pu e $V^{sw} = 1{,}08$ pu, e vetor de decisão binário $s \in \{0,1\}^{n_m-1}$ com $s_i = 1$ mantendo a máquina $i$ conectada [FATO: doc B, p. 2]:

$$
\min_{s}\ F(s) = \bigl(f_3,\ f_4,\ f_5\bigr)
\tag{1}
$$
$$
f_3 = \sum_k N^{(k)}_{viol}(s),\qquad
f_4 = P^{(\mathrm{PRE\text{-}DISC})}_{losses}(s)\ [\mathrm{kW}],\qquad
f_5 = \sum_{i:\,s_i=0} P_{n,i}\ [\mathrm{kW}]
$$
sujeito a
$$
g_1 = V^{ir} - V^{(\mathrm{INRUSH})}_{\min} \le 0
\tag{2}
$$
$$
g_2 = V^{(\mathrm{POST\text{-}DISC})}_{\max} - V^{sw} \le 0
\tag{3}
$$
$$
g_3 = S^{(\mathrm{sust})}_{TR}/S_{AF} - 1 \le 0
\tag{4}
$$

com $N^{(k)}_{viol}$ a contagem de violações de envelope de proteção no *snapshot* $k \in \{$PRE-ENERG, INRUSH, PRE-DISC, POST-DISC$\}$; $S^{(\mathrm{sust})}_{TR}$ a maior potência aparente através do transformador remanescente nos *snapshots* sustentados; e $S_{AF} = 9$ MVA a capacidade em ar forçado que define o *pickup* da função 49 [FATO: doc B, p. 2, transcrição literal das eqs. (1)–(4)]. O INRUSH é excluído de $g_3$ por durar $\approx$ 10 s [FATO: doc B, p. 2]. Fluxos não convergentes são declarados fortemente infactíveis, $g_1=g_2=g_3=1$ [FATO: doc B, p. 2–3, Alg. 1, l. 6–8].

### 6.2 Extensão proposta

**(a) Objetivo adicional $f_6$ — consumo esperado de vida do isolamento no cenário** [PROPOSTA; nenhum elemento consta de B]:

$$
f_6(s) \;=\;
\underbrace{\Delta L_T\!\bigl(V^{(\mathrm{INRUSH})}_{\min}(s)\bigr)}_{\text{alvo: térmico de partida, (4.6)}}
\;+\;\underbrace{\lambda_A^{(\mathrm{part})}(s)\cdot \mathbb{E}\bigl[\Delta D^{el}_m\bigr]}_{\text{alvo: dielétrico, via }\S2.5\text{ e D7}}
\;+\;\underbrace{\sum_{i:\,s_i=0}\Delta L_i\!\bigl(V^{(\mathrm{RESTART})}_i(s)\bigr)}_{\text{religamento das cortadas}}
\;+\;\underbrace{\sum_{i:\,s_i=1}\Delta L^{sag}_i}_{\text{mantidas sob afundamento}}
\tag{6.1}
$$

**Convenção dimensional de (6.1) — obrigatória, e fixada aqui** [PROPOSTA]. Todos os quatro termos são **fração de vida adimensional por evento de partida**, coerentemente com (4.6), que define $\Delta L_{start}(V) = (1/L_0)\int \mathrm{AF}\,\mathrm{d}t$ como fração (e não como horas-equivalentes), e com a convenção $D(t)=1$ na falha da §5.2. Em consequência:

- $\lambda_A$ é escrito em (6.1) como $\lambda_A^{(\mathrm{part})}(s) = P[\text{atuação durante a partida}\mid V_{\min}(s), t_{acc}(s)] \in [0,1]$, **probabilidade adimensional por partida**;
- a **taxa anual** correspondente é $\lambda_A^{(\mathrm{ano})} = \lambda_A^{(\mathrm{part})}\cdot N_{N\text{-}1}$ [eventos/ano], e é essa — **não** a de (6.1) — que aparece no custo anual da §7.1, item 2, e no elo E-3 da §10.1;
- $\mathbb{E}[\Delta D^{el}_m]$ é o dano dielétrico esperado **por evento**, de D7 [Etapa 1, §5.4].

A leitura em **horas-equivalentes à temperatura de classe** é secundária e obtém-se por $f_6\cdot L_0$ [h]; não deve ser usada como unidade de (6.1), sob pena de somar $\int\mathrm{AF}\,\mathrm{d}t$ com $(1/L_0)\int\mathrm{AF}\,\mathrm{d}t$. Em qualquer das duas leituras, reportar **faixa** por HIC $\in \{8,10,15\}$ K e por $n \in [4;\,11{,}7]$ [PROPOSTA].

O segundo termo de (6.1) é a contribuição específica desta etapa: **é ele que injeta o Documento A dentro da formulação do Documento B**. Os termos três e quatro estão em `anexos/cruzamento/cruzamento_B_load_shedding_n1.md` (E7) e foram aqui confirmados como necessários, mas dependem de um quinto *snapshot* por máquina religada, que B não tem [FATO: ausência].

**(b) Restrição adicional $g_4$ — margem de coordenação** [PROPOSTA]. Duas formas, ambas normativamente ancoradas:

$$
g_4(s) = t_{acc}\bigl(V^{(\mathrm{INRUSH})}_{\min}(s)\bigr) - \bigl(t_{LR,\mathrm{hot}} - \Delta t_{marg}\bigr) \le 0,
\qquad \Delta t_{marg} = 5\ \mathrm{s}
\tag{6.2}
$$

reproduzindo literalmente o critério "At 80 % of rated voltage at the motor terminals, the minimum hot locked-rotor time shall be at least 5 seconds more than the time required to accelerate the specified driven load" [NORMA: IOGP S-704 v1.0, 9.12.1.5, numeração riscada no redline v2.0 × v1.0; texto vigente equivalente em 11.3.1.5 da v2.0 — ver §4.4]; e

$$
g_4'(s) = \gamma_{\min} - \gamma(s) \le 0,
\qquad
\gamma(s) = \frac{U_w\bigl(\theta,D\bigr)}{U_s(s)},
\tag{6.3}
$$

com $\gamma$ a margem de coordenação da Etapa 1 (§6) e $U_s(s)$ o percentil alto da distribuição de sobretensões de manobra sob o plano $s$ — que depende de $s$ **porque $\lambda_A$ depende de $s$** (§2.5). A âncora normativa de (6.3) é o fator de segurança $K_s$ da IEC 60071-1, definido como "overall factor … accounting for all other differences in dielectric strength between the conditions **in service during life time** and those in the standard withstand voltage test" [NORMA: IEC 60071-1:2019, 3.31]: (6.3) é esse $K_s$ tornado dependente do dano acumulado [Etapa 1, §6].

### 6.3 $f_6$ é objetivo ou restrição? A lição metodológica de B aplicada

B documenta, com dados próprios, a patologia a evitar: na formulação preliminar de cinco objetivos, "two of which measured sag and swell severities that **vanish identically on the feasible region**", "the Pareto front became degenerate", e o NSGA-III ficou 23 % **abaixo** da busca aleatória (HV mediano 286 289 contra 370 604; Wilcoxon $p = 0{,}0020$) [FATO: doc B, p. 1–2, Tabela II]. A correção foi tratar limites operacionais como restrições e dimensionar as direções de referência à população, o que reverteu o resultado para +49 % sobre a aleatória e 96,5 % do NSGA-II [FATO: doc B, p. 3–4, Tabelas IV–V]. O princípio declarado por B é o critério de decisão: "The voltage limits are **operational requirements, not preferences**, so the corrected model treats them as inequality constraints" [FATO: doc B, p. 2].

Aplicando o critério, item a item:

| Teste | $f_6$ | $g_4$ |
|---|---|---|
| Anula-se identicamente na região factível? | **Não.** Toda partida consome vida: $\Delta L > 0$ para todo $V$ finito, e $\lambda_A > 0$ para toda margem finita [INFERÊNCIA a partir de (4.6) e §2.5] | Não se aplica (é limite) |
| É requisito operacional ou preferência? | **Preferência**: quanto de vida a planta aceita gastar numa partida é decisão de negócio, não limite de norma | **Requisito**: (6.2) transcreve cláusula normativa; (6.3) transcreve o $K_s$ da IEC 60071-1 |
| Conflita com os demais na região factível? | **Sim**, e com mínimo interior (ver abaixo) | — |
| Risco de degenerescência | **Sim, quase-degenerescência por colinearidade** — ver adiante | Nenhum |

**Recomendação, com justificativa** [PROPOSTA]: **$f_6$ como quarto objetivo e $g_4$ como quarta restrição**, mas $f_6$ **obrigatoriamente com o termo de religamento**. A razão é precisa e é a lição de B levada ao caso: se $f_6$ dependesse **apenas** de $V^{(\mathrm{INRUSH})}_{\min}$ — isto é, apenas dos dois primeiros termos de (6.1) —, então, como (i) $V_{\min}$ é quase linear nos bits ("bus voltage responds almost linearly to the switching of individual loads at this scale" [FATO: doc B, p. 5]) e (ii) $V_{\min}$ cresce monotonicamente com a potência cortada, $f_6$ seria função **quase monótona de $f_5$**. A frente $(f_5,f_6)$ degeneraria em curva: quatro objetivos nominais, três dimensões efetivas — exatamente a condição em que Ishibuchi et al. documentam a queda dos algoritmos por decomposição, que B cita como causa da sua própria patologia [FATO: doc B, p. 2, citando [10]]. O terceiro termo de (6.1) — os 17 a 19 religamentos (§4.4) — **cresce** com o corte e quebra a colinearidade, dando a $f_6$ um **mínimo interior** em $f_5$ [INFERÊNCIA]:

| Objetivo | Tendência com mais corte | Origem |
|---|---|---|
| $f_5$ (kW cortados) | cresce | definição [FATO: doc B, p. 2] |
| $f_4$ (perdas) | decresce | "keeping more machines connected … raises losses" [FATO: doc B, p. 3] |
| $f_3$ (violações) | decresce | idem |
| $f_6$, termos do alvo (térmico + dielétrico) | decresce ($V\uparrow$, $t_{acc}\downarrow$, $\lambda_A\downarrow$) | (4.4), (4.6), §2.5 |
| $f_6$, termo de religamento | cresce (mais partidas) | §4.4 |
| **$f_6$ total** | **mínimo interior** | soma das duas tendências |

**Verificação obrigatória no experimento** [PROPOSTA metodológica]: reportar (i) o coeficiente de correlação de postos entre $f_5$ e $f_6$ sobre a frente e (ii) a razão de autovalores de uma PCA da frente, como medida de dimensão efetiva. Se a correlação exceder, digamos, 0,95, $f_6$ deve ser rebaixado a restrição ou fundido a $f_5$, sob pena de reproduzir a degenerescência que B corrigiu. Este é um teste que B não teve de fazer (três objetivos conflitantes por construção) e que a extensão a quatro torna obrigatório.

**Benefício metodológico colateral.** B declara que a metade da sua diretriz relativa a "muitos objetivos" **não foi testada**: "That half of the guideline rests on the literature" [FATO: doc B, p. 4]. Acrescentar $f_6$ leva o problema a quatro objetivos e oferece **a primeira oportunidade de testar empiricamente essa metade**, com o mesmo protocolo de B (10 sementes, HV com referência a 10 % de margem, Wilcoxon pareado $\alpha = 0{,}05$) [FATO: doc B, p. 3].

### 6.4 Custo computacional e viabilidade do *surrogate* para $f_6$

O orçamento exato de B é de $\approx$ 25 ms por avaliação (quatro fluxos OpenDSS) para a planta de 20 motores [FATO: doc B, p. 5]. Acrescentar $f_6$ acrescenta, por avaliação: (i) a integração de (4.2) — ou sua aproximação (4.4); (ii) o transitório térmico (4.6); (iii) o cálculo de $\lambda_A$; (iv) os *snapshots* de religamento. Os itens (i)–(iii) são baratos em forma fechada e caros em forma íntegra; o item (iv) multiplica o custo por $\approx$ 18.

B demonstra que um *surrogate* de regressão ridge quadrática sobre os 19 bits e suas interações par a par reproduz $V^{(\mathrm{INRUSH})}_{\min}$ com $R^2 = 0{,}9999$ e MAE $= 8{,}5\times10^{-5}$ pu, sobre 14 343 cenários únicos, validação cruzada de 5 dobras [FATO: doc B, p. 5, Tabela VI, e p. 5, Seção V, texto, para a contagem de cenários e o protocolo de validação], com a justificativa física de que "bus voltage responds almost linearly to the switching of individual loads at this scale, and the pairwise terms capture the interaction effects" [FATO: doc B, p. 5]. Com bits binários, $x_i^2 = x_i$, de modo que o modelo tem $19 + \binom{19}{2} = 190$ regressores [CÁLCULO PRÓPRIO; o artigo não declara a contagem].

**A mesma exatidão se transfere a $t_{acc}$ e ao consumo de vida?** [HIPÓTESE — resposta provável: não, e a razão é estrutural.] Três argumentos:

1. **$t_{acc}$ tem polo.** Por (4.4), $t_{acc}(V) \propto 1/(k_T V^2 - f_Lk_L)$, com polo em $V_{stall}$. Uma superfície com polo não é aproximável com $R^2 > 0{,}999$ por polinômio de grau 2 numa vizinhança que contenha o polo [INFERÊNCIA].
2. **$\Delta L$ é exponencial em $\theta$.** Por (4.6), $\mathrm{AF} = 2^{\Delta\theta/\mathrm{HIC}}$; a composição bits $\to V \to t_{acc} \to \theta \to \mathrm{AF}$ é exponencial de uma função com polo [INFERÊNCIA].
3. **Não há evidência acessada** de *surrogate* de tempo de aceleração ou de $I^2t$ com essa exatidão; o que a literatura acessada reporta para redes é MLP com 97–98 % de acurácia e 0,0–0,64 % de falsos negativos em triagem de contingências [LITERATURA: Schaefer, Menke e Braun, arXiv:2008.09384, 2020], e GP que **falha** sem termo residual de incerteza porque "simulators violate the GP's underlying Gaussian assumption" [LITERATURA: Houdouin e Saludjian, arXiv:2503.00094, 2025].

**Proposta: *surrogate* composto** [PROPOSTA metodológica] — regressão na parte quase linear, física na parte não linear:
$$
\hat f_6(s) \;=\; f_6^{\text{físico}}\!\bigl(\hat V_{\min}(s)\bigr),
\qquad \hat V_{\min} = \text{ridge quadrático de B} .
\tag{6.4}
$$
Assim o erro do *surrogate* ($8{,}5\times10^{-5}$ pu) propaga-se por (4.4) e (4.6) com sensibilidade conhecida — pequena a 0,866 pu, grande na vizinhança de $V_{stall}$ —, em vez de ser absorvido por um regressor cego. A garantia de B permanece intacta desde que a verificação final calcule $f_6$ e $g_4$ com o fluxo exato **e** com a integração íntegra de (4.2), não com (4.4) [INFERÊNCIA]; o Algoritmo 2 de B, aliás, **é proposto e não executado** no próprio artigo [FATO: ausência; doc B, p. 5], de modo que sua primeira execução seria contribuição.

---

## 7. O snubber como variável de decisão

### 7.1 O deslocamento do ótimo

A Etapa 1 (§5.5, Passo 2 e advertências) estabeleceu, com todas as ressalvas, que a razão de dano por evento entre a manobra não mitigada e a mitigada é **da ordem de $10^2$ para $n=4$ (faixa 100–170, conforme a regra de contagem aplicada aos dois ramos)**, subindo a $1{,}95\times10^3$ ($n=6{,}4$) e $3{,}06\times10^4$ ($n=9$), e que, na presença de limiar $V_{th}$ entre 4,0 e 12,2 pu, a razão torna-se formalmente **infinita** porque a mitigação move o evento para abaixo do limiar [Etapa 1, §5.5]. As ressalvas são integralmente herdadas: expoentes de fio esmaltado e epóxi puro, não mica-epóxi; contagem de excursões por leitura de figura; TRV no disjuntor, não no motor; e o único mecanismo identificado que **reduz** o benefício aparente — o encurtamento da frente com $m>0$ — que levaria a razão de 168 para $\approx$ 64 sob $m=1$ [Etapa 1, §5.5, Passo 3].

Aceita essa ordem de grandeza como hipótese de trabalho, o snubber deixa de ser um dispositivo e passa a ser uma **variável de decisão que desloca a fronteira de Pareto de B** [PROPOSTA]. O argumento, em três linhas:

1. Pelo §2.5, o plano que preserva mais produção (menor $f_5$) é o de maior $\lambda_A$.
2. O custo esperado dielétrico **por ano** é $\lambda_A^{(\mathrm{ano})}(s)\cdot \mathbb{E}[\Delta D^{el}_m \mid u] = \lambda_A^{(\mathrm{part})}(s)\,N_{N\text{-}1}\,\mathbb{E}[\Delta D^{el}_m \mid u]$, com $u \in \{0,1\}$ indicando ausência/presença do snubber e $N_{N\text{-}1}$ [partidas/ano] a frequência de partidas sob N-1 (convenção da §6.2).
3. Se $\mathbb{E}[\Delta D^{el}_m \mid u=1] \approx 10^{-2}\,\mathbb{E}[\Delta D^{el}_m \mid u=0]$, então **um plano com $\lambda_A$ até duas ordens de grandeza maior produz o mesmo custo dielétrico esperado** [CÁLCULO PRÓPRIO sobre a hipótese do item 2].

Ou seja: **o snubber compra tolerância a planos de corte mais agressivos em produção**. Formalizando como problema conjunto [PROPOSTA]:

$$
\min_{s\,\in\,\{0,1\}^{n_m-1},\ u\,\in\,\{0,1\}}\ \Bigl(f_3,\ f_4,\ f_5,\ f_6(s,u),\ C_{capex}(u)\Bigr)
\quad\text{s.a.}\quad g_1,\dots,g_3 \ \text{(B)},\ g_4 \ \text{(6.2)–(6.3)},
\tag{7.1}
$$
$$
f_6(s,u) \;=\; \Delta L_T\bigl(V_{\min}(s)\bigr) \;+\; \lambda_A^{(\mathrm{part})}(s)\,\mathbb{E}\bigl[\Delta D^{el}_m \mid u\bigr] \;+\; \sum_{i:\,s_i=0}\Delta L_i \;+\; \sum_{i:\,s_i=1}\Delta L^{sag}_i ,
$$

todos os termos em **fração de vida por evento de partida**, conforme a convenção dimensional fixada na §6.2.

Duas ressalvas obrigatórias sobre (7.1) [INFERÊNCIA]:

- **$u$ não é decisão operacional, é decisão de projeto.** Diferentemente de $s$, que se decide antes de cada partida, $u$ se decide uma vez na vida da instalação. A formulação correta é, portanto, **de dois níveis**: no nível superior escolhe-se $u$ (CAPEX); no inferior, a frente de Pareto em $s$ condicionada a $u$. A comparação de interesse é entre **duas frentes**, não entre pontos.
- **O snubber tem confiabilidade própria e envelhece.** O TOR da CIGRE WG C4.76 registra que, sob sobretensões de alta amplitude e alta inclinação, "the insulation level of these suppression devices may gradually deteriorate due to **cumulative effects**", e que os snubbers RC têm níveis de suportabilidade "relatively low" [CIGRE: TOR WG C4.76, 2023-07-31, p. 1–4]. O RUL do próprio snubber é lacuna aberta [Etapa 1, §6].

### 7.2 Ancoragem em Strangas et al. (artigo 09): o que aquele artigo demonstra e o que não demonstra

**O que demonstra** [FATO: artigo 09]. É o único do corpus que formaliza quanto a mitigação decidida por prognóstico **imperfeito** altera o MTBF. Para uma falta primária de taxa $\lambda_1$, quatro caminhos [FATO: artigo 09, Fig. 2 e eqs. (7)–(11), p. 5]:

$$
\mathrm{MTBF}_1 = \frac{1}{p_1\lambda_1}
\quad\text{(não detectada)};\qquad
\mathrm{MTBF}_2 = \frac{1}{p_{12}\lambda_1} + \frac{1}{\lambda_2}
\quad\text{(detectada tarde, falta secundária)};
$$
$$
\mathrm{MTBF}_3 = \frac{1}{p_{13}\lambda_1} + \frac{1}{\lambda_3}
\quad\text{(detectada cedo e mitigada, }\lambda_3 \ll \lambda_2\text{)};\qquad
\mathrm{MTBF}_4 = \frac{1}{\lambda_{10}} + \frac{1}{\lambda_3},\ \ \lambda_{10} = \frac{p_{10}}{t_{sample}}
\quad\text{(falso positivo)};
$$
$$
\lambda_{sys} = \sum_{i=1}^{4}\frac{1}{\mathrm{MTBF}_i}.
$$

O artigo declara a lacuna que preenche: "it has been assumed, but not substantiated, that prognosis and mitigation based on it may enhance reliability; still, the contributions of fault prognosis on the reliability have not been discussed. It is not clear yet how to determine the effect of mitigation and how false positives and negatives can affect the overall reliability" [FATO: artigo 09, p. 2]. E registra o custo da mitigação: "A drive, then, once it is modified to alleviate the effects of a fault, has **decreased life expectancy**" [FATO: artigo 09, p. 1]; "the estimation of the time to failure through prognosis can lead to the timely mitigation of the fault and, in turn, can extend the lifetime and reliability of the drive" [FATO: artigo 09, p. 1]. No exemplo, o limiar de decisão de 0,4 sobre $P[q_{t+1}=S_6]$ elimina falsos positivos e negativos, tornando $\mathrm{MTBF}_1$ e $\mathrm{MTBF}_4$ infinitos [FATO: artigo 09, p. 8–9].

**O que NÃO demonstra** [FATO: artigo 09 + INFERÊNCIA do fichamento 09, §8]:

1. **Nenhum RUL em unidades de tempo é calculado.** O exemplo entrega a probabilidade de o próximo estado ser falha, não uma distribuição de tempo até falha; a ligação entre a saída do HMM e as taxas $\lambda$ da Tabela IV não é formalizada.
2. **Taxa de falha constante e aditiva**, inadequada a desgaste com risco crescente — que é exatamente o regime do isolamento [INFERÊNCIA].
3. **A sequência de observações é sintética e monotônica**, e o limiar de 0,4 é escolhido *a posteriori* sobre a mesma sequência (ajuste *in-sample*); não há validação independente.
4. **Inconsistências editoriais**: a desigualdade impressa $\mathrm{MTBF}_3 < \mathrm{MTBF}_2 < \mathrm{MTBF}_1$ conflita com o texto que a acompanha (se $\lambda_3 \ll \lambda_2$ e $p_{13}\approx p_{12}$, decorre $\mathrm{MTBF}_3 > \mathrm{MTBF}_2$); e a eq. (13), de isolamento, é dimensionalmente ambígua e não deve ser usada sem reparametrização [FATO: artigo 09, p. 5–6; INFERÊNCIA].
5. **O isolamento aparece apenas como falta secundária** (envelhecimento térmico acelerado); o mecanismo primário estudado é contato intermitente em motor PMAC. **Nenhum valor numérico do artigo é reutilizável.**
6. **Não há modelo de custo**: falsos positivos entram apenas como redução de MTBF, sem custo de indisponibilidade [INFERÊNCIA].

**Mapeamento para (7.1)** [INFERÊNCIA]: "fault 1" = degradação incipiente da isolação de espira por surtos; caminho 3 = mitigação (snubber ativo $u=1$ **e/ou** plano de corte $s$ que evita a atuação), com $\lambda_3$ incluindo a taxa de falha do próprio snubber; caminho 4 = falso positivo, que aqui tem **duas naturezas distintas**: disparo espúrio do DIAC (custo de confiabilidade) e **corte de carga desnecessário** (custo de produção $f_5$, que B já mede e que Strangas não modela). É precisamente nesse ponto que os dois trabalhos se completam: **B otimiza a decisão sem prognóstico; Strangas prognostica sem otimizar a decisão; (6.1)–(7.1) unem os dois** [INFERÊNCIA].

---

## 8. Mapeamento dos artigos de apoio por elo da cadeia

| Elo da cadeia | Artigo(s) | O que exatamente se transfere | O que **não** se transfere |
|---|---|---|---|
| **L1–L3** — topologia N-1 como modo de operação que altera a lei de degradação | **Yu, Wang e Luo (2014)**, artigo 06 | O conceito e o formalismo: "For a hybrid system, the same component will exhibit **different degradation behaviors at different operating modes**", com exemplo de motor — "the motor wear in the ramp-up mode is more severe than the wear in the idle mode" [FATO: artigo 06, p. 3]. Modelo comutado por modo, eq. (4): $\omega_1\ddot P + (1-\omega_1)\dot P = bP^{2\omega_2} + cP^{\omega_3}$, com vetor de estrutura DMSV $\Omega=[\omega_1,\omega_2,\omega_3]$ e coeficientes por modo [FATO: artigo 06, p. 3]. Mapeamento: modos = {regime N, regime N-1, partida a plena tensão, partida sob N-1 sem corte (0,755 pu), partida sob N-1 com plano $s$ (0,850–0,866 pu), religamento}. **O vetor $s$ de B é o que escolhe a sequência de modos** | Degradação **sintética** (fatores de eficiência $\beta$ injetados por EDO em circuito RC de bancada); nenhum mecanismo físico de envelhecimento [FATO: artigo 06, p. 6–7]. RUL escalar sem incerteza. O "tempo de espera" do DFI exige que o diagnóstico só se complete após a próxima mudança de modo [FATO: artigo 06, p. 3] — em planta com partidas raras, meses |
| **L4–L5** — decisão de mitigar e efeito no MTBF | **Strangas et al. (2013)**, artigo 09 | Eqs. (7)–(11): caminhos com e sem mitigação, tratamento explícito de falsos positivos e negativos, e o limiar de decisão como variável de projeto [FATO: artigo 09, p. 5, 8]. É o esqueleto formal de (7.1) | Ver §7.2, itens 1–6. Em particular: taxa constante, sequência sintética, nenhum RUL em tempo, nenhum valor numérico reaproveitável |
| **L6–L8** — estresse por evento e sua conversão em vetor | **Jensen, Strangas e Foster (2018)**, artigo 02 | Arquitetura completa de prognóstico online com poucos recursos: indicador $I_{leak} = \alpha e^{\beta t}$, estado $x = [I_{leak},\alpha,\beta]^T$, EKF, limiar de falha, e o **detector de pico analógico** (diodo de 4 ns, op-amp de 900 V/µs, capacitor de 47 nF) que reduz a exigência de 1 GSa/s para **10 MSa/s** [FATO: artigo 02, p. 5–8]. A cadeia EKF → tendência → limiar → RUL é agnóstica ao indicador e pode receber $D(t)$ de (5.1) | Indicador validado com **envelhecimento térmico** em estatores BT de 5 kW ($n=3$), monitorando fase-terra; os pulsos de excitação "were not designed to contribute to the degradation" [FATO: artigo 02, p. 2–4]. **Alerta crítico**: "the actual dV/dt of the switching device is **assumed to be constant** for this method to detect changes in the insulation properties" [FATO: artigo 02, p. 3] — hipótese violada por um VCB com chopping e reignições estocásticas e, adicionalmente, **pela própria mitigação**, que conforma a frente. O detector de pico preserva o pico, **não o tempo de frente**, insuficiente para o envelope tempo–tensão [INFERÊNCIA] |
| **L9** — acúmulo de dano e contabilidade anual | **Ma, Liserre, Blaabjerg e Kerekes (2015)**, artigo 12 | Esqueleto "perfil de missão → perfil de carga → modelo de resistência → Miner → **distribuição** de vida consumida por mecanismo e por condição", com separação em três constantes de tempo (longo: passo de 3 h por 1 ano; médio: 1 s por 3 h; curto: 0,5 ms por 0,2 s); *rainflow* extraindo $\Delta T_j$, $T_{jm}$ **e** $t_{cycle}$; $CL_n = 100/N_{n,\mathrm{life}}$, $CL_{1\,\mathrm{ano}} = \sum CL_n$ e a extrapolação ponderada pela distribuição de condições [FATO: artigo 12, eqs. (1)–(3), p. 4–7]. Mapeamento das três escalas: **curto** = reignições (µs); **médio** = partida (s); **longo** = térmica de regime (h–meses). A eq. (3) vira $\Delta L_{ano} = N_N\,\Delta L(V=1) + N_{N-1}\sum_s p(s)\,f_6(s)$ | Mecanismo termomecânico (fadiga de solda e fios de ligação); modelos B10 do fabricante e Coffin–Manson. A variável de estresse é temperatura **simulada**, não medida. Declaração explícita: "electrical degradation … **cannot be evaluated in this paper**" [FATO: artigo 12, p. 9]. O termo RUL não aparece. Miner **linear** é questionável para dano dielétrico **com limiar** [INFERÊNCIA; §5.2] |
| **L9** — arquitetura de aquisição de carga | **Vichare e Pecht (2006)**, artigo 07 | A rota LCM: "If one can measure these loads **in-situ**, the load profiles can be used in conjunction with damage models to assess the degradation due to cumulative load exposures" [FATO: artigo 07, p. 5]; pré-processamento por remoção de *outliers* + *rainflow* de três parâmetros (faixa, média, rampa) e binagem em histogramas; MSET/SPRT sobre resíduos; FMMEA como passo inicial. Mapeamento: **os quatro *snapshots* de B são o registro de carga do evento de partida**; o histograma de $U$ por classe de severidade é o histograma binado do LCM; e o *load shedding* é um **modificador da distribuição de cargas** | **Nenhuma equação, nenhum modelo de dano, nenhuma métrica de desempenho prognóstico** [FATO: ausência]. Recorte em eletrônica de baixa tensão. A recomendação de perfil de uso previsível é **violada** por contingências N-1 — o que favorece a abordagem por dano acumulado sobre a de precursor com perfil fixo [INFERÊNCIA] |
| **Camada de previsão** (não de decisão) | **Siami-Namini et al. (2019)**, artigo 10; Yin et al. (2024), artigo 08 | Papel legítimo: previsão da trajetória do indicador de saúde com **covariáveis de estresse vindas do otimizador** (contagem de partidas sob N-1 ponderadas por $U$, $f_6$ acumulado) [INFERÊNCIA]. BiLSTM reduziu RMSE em média 37,78 % [FATO: artigo 10, p. 5–7] | **Não servem como *surrogate* do otimizador** (§6.4): o mapeamento bits → $f_6$ não é série temporal. BiLSTM **não é causal** e é incompatível com predição online; piorou em um dos casos (+45,03 % em IXIC.weekly) e converge mais devagar; "needs fetching more training data" [FATO: artigo 10, p. 5–7] — o que pesa contra arquiteturas profundas num regime de $10^1$–$10^3$ eventos/ano |

**Observação transversal, reafirmada** [INFERÊNCIA]: nenhum dos 13 artigos do corpus contém simultaneamente (i) um estressor dielétrico impulsivo, (ii) um indicador de isolação de MT e (iii) um modelo estresse → dano para surtos esparsos [Etapa 1, §7.3]. E nenhum deles trata de *load shedding*, N-1, partida de motor de MT ou otimização evolutiva de decisão operacional [FATO: ausência, verificada nos 13 fichamentos]. A revisão de decisão pós-prognóstico de 2020 encontrou **três** trabalhos de controle automático com RUL e **nenhum** sobre corte de carga preventivo [LITERATURA: Wesendrup e Hellingrath, PHME 2020, p. 5–6, 9], e declara o campo "still in its infancy". A combinação "vida consumida por partida sob N-1 como objetivo/restrição de *load shedding*" é, portanto, **lacuna documentada** — o que é oportunidade de contribuição, não evidência de viabilidade.

---

## 9. O que o Olivas já entrega e o que falta

**Base de verificação.** Todos os símbolos abaixo foram **reconferidos por leitura direta do código** nesta sessão, em HEAD `d6a1160` (a Etapa 1 fora escrita em `961d66a` e os mapas de `anexos/repo/` em `26d9248`; as linhas citadas foram revalidadas, e as divergências de numeração corrigidas).

### 9.1 Inventário por elo da cadeia

| Elo | Módulo existente | Estado verificado | Lacuna |
|---|---|---|---|
| L1–L3 — fluxo de potência e afundamento | `app/postprocessor/power_flow.py`; `app/postprocessor/motor_starting.py:367-407` (`calculate_voltage_dip_pu`) | Newton–Raphson, sequência positiva; divisor de impedância para o afundamento | **Sem N-1, sem corte de carga, sem otimização**: `app/postprocessor/power_flow.py:87` declara literalmente "Sem otimização (load shedding, FACTS)." [REPO, verificado]. É a **única** ocorrência de "load shedding" em `app/**/*.py` |
| L1–L3 — corrente de partida sob afundamento | `app/postprocessor/motor_starting.py:505` | `I_during_A = I_LR_A * V_during_pu / case.bus_pre_fault_voltage_pu` — implementa $I \propto V$, coerente com IEEE 399 9.3.1 e com o modelo de impedância constante de B | Nenhuma; este elo está correto |
| L4 — probabilidade de atuação da 27 | — | Inexistente | **Não existe** nenhum modelo de atuação temporizada de 27 acoplado ao transitório de partida |
| §4.2 — tempo de aceleração dependente da tensão | `app/postprocessor/motor_starting.py:410` (`estimate_starting_time_s`) | Conjugado médio: $t = J\cdot0{,}95\,\omega_s/(T_{m,avg}-T_{L,avg})$, com fatores de carga CONSTANT/LINEAR/QUADRATIC/CUBIC; retorna `inf` quando $T_{m,avg}\le T_{L,avg}$ (é o *stall* de (4.3)) | **Não usa a tensão**: nenhuma referência a `V_during_pu` no corpo da função [REPO, verificado por leitura das l. 410-453]. É o item de maior alavancagem: sem $V^2$ no conjugado, o $I^2t$ sob N-1 é subestimado exatamente nos casos críticos |
| §4.3 — capacidade térmica do motor | `app/postprocessor/tcc_damage.py:450` (`MotorThermalCurve`), `:471` | $K_{motor} = t_{LR}\times(\text{fator de rotor bloqueado})^2$; $t(I) = K_{motor}/(I/\mathrm{FLA})^2$; `locked_rotor_time_s` default 10,0 s (`:532`) | **Curva única, sem HOT/COLD**, contra a IEEE 620 que exige as duas condições iniciais; sem constante de tempo de resfriamento; sem $R_r(s)$, de modo que a curva é o limite superior adiabático que Zocholl documenta superestimar |
| §4.4 — orçamento de partidas | `app/postprocessor/motor_starting.py:99` | `DEFAULT_START_TIME_FRACTION_LIMIT = 0.70` — constante **declarada e inerte** (nenhum uso no fluxo de decisão) | Sem contador de partidas frias/quentes, sem confronto com os mínimos NEMA/IEC/IOGP |
| §4.3 — aviso térmico de partida | `app/postprocessor/motor_starting.py:540` | Só emite aviso "verificar curva I²t do motor" quando $t_{start} > 30$ s | Limiar arbitrário e alto: $t_{LR,\mathrm{hot}}$ de referência é 12 s no único caso documentado acessado, e a faixa 10–20 s é [HIPÓTESE] (§4.3, §10.3) |
| ANSI 49 | `app/postprocessor/tcc_devices.py:399` (`relay_51_50_49`) | O próprio *docstring* declara: "49 thermal é modelado como `TCCSegmentDefiniteTime` (fix delay quando I > pickup_49). Modelagem fiel ao thermal replica curve do datasheet exigiria `TCCSegmentTimeCurrentPoints` — fica para v1.4" [REPO, verificado] | Réplica térmica real ausente; é tempo definido |
| Classe térmica | `app/preprocessor/equipment_catalog.py:124` | `insulation_class: str = "F"` — existe **só no catálogo** | Não é propagada para `MotorParameters` nem usada em nenhum cálculo |
| L6–L7 — modelo de VCB | `app/preprocessor/atp_templates/vcb_reignition.mod` | `DATA`: `I_chop_mean {dflt: 5.0}` (l. 48), `didt_crit_0 {dflt: 16.0}` (l. 50), `k_dielec {dflt: 17.0}` (l. 52), `U0_dielec {dflt: 690.0}` (l. 53); recuperação **linear** `U_dielec_t := U0_dielec + k_dielec * (t - t_contact) * 1e6` (l. 115); `reign_count` incrementado em l. 101 e l. 120 | **Diverge do Documento A** — ver §9.2 |
| L8–L9 — métricas de transitório | `app/analysis/transient_metrics.py:41` (`compute_transient_metrics`) | **Integrada à aplicação**: chamada pela GUI (`app/gui/main_window.py:2298`), pela exportação CSV (`app/analysis/csv_export.py:48`) e pelo relatório (`app/analysis/report_export.py:93`) [REPO, verificado] | Produz apenas pico, mínimo, RMS, frequência por zeros e amortecimento — **nenhuma métrica de frente** ($T_1$, $t_r$) e nenhuma métrica de dano |
| L8 — métricas de TRV | `app/analysis/transient_metrics.py:91` (`compute_trv_metrics`) | **Sem chamador na aplicação**: as únicas ocorrências fora da definição estão em `tests/` [REPO, verificado por grep em `app/` e `tests/`] | Código morto do ponto de vista do produto |
| L8 — analisador de TRT | `app/postprocessor/trt_analyzer.py:372` (`analyze_trt`), `:299` (`_compute_max_rrrv`) | `analyze_trt` só é referenciada no *docstring* do próprio módulo (l. 11, 32) e em `tests/test_pp_trt_analyzer.py`; **não há ponte PL4 → `TrtWaveform`** | Sem chamador de produção |
| L9 — camada de dano | — | `grep -rniE "rainflow\|weibull\|arrhenius\|montsinger\|remaining useful\|prognos\|nsga\|pareto\|pymoo" app/ --include=*.py` retorna **vazio** [REPO, reconfirmado em HEAD `d6a1160`] | **Toda a camada de dano e toda a camada de otimização multiobjetivo são inexistentes** |

**Síntese** [INFERÊNCIA]: o repositório já mede o transitório, já o exporta, já conta reignições no modelo ATP e já calcula afundamento e corrente de partida. O que não existe é (i) a **métrica de frente** na cadeia de aplicação, (ii) a **dependência do tempo de aceleração com a tensão**, (iii) as **curvas térmicas quente/frio**, (iv) a **camada de dano** e (v) **qualquer** suporte a N-1, corte de carga ou otimização multiobjetivo.

### 9.2 A divergência de modelo de VCB — e o que ela implica para reprodutibilidade

| Aspecto | Repositório (`vcb_reignition.mod`) | Documento A |
|---|---|---|
| Lei de recuperação dielétrica | **Linear**: $U_0 + k\,\Delta t$, com $U_0 = 690$ V e $k = 17$ V/µs $=$ 17 kV/ms [REPO: `.mod:52-53, 115`] | **Parabólica**: $V_{wth}(t) = A t + B t^2$, $A = 0{,}801$ kV/ms, $B = 1{,}226$ kV/ms² [FATO: doc A, Tabela II, p. 3] |
| Suportabilidade em $t = 1$ ms | 17,7 kV | **2,03 kV** |
| *Chopping* | $\mathcal N(5;\,1^2)$ A, uma amostra por realização [REPO: `.mod:48-49, 83`] | 1 A a 2 A, determinístico [FATO: doc A, Tabela II] |
| Energia $\tfrac12 L I_{ch}^2$ | 112 mJ (5 A) | 4,5–18 mJ (1–2 A) |
| di/dt crítico | 16 A/µs + 0,034 A/µs²·$\Delta t$; **reignição** se $|di/dt|$ > crítico no corte [REPO: `.mod:50-51, 98-101`] | 5–15 A/µs; **extinção** de AF quando o di/dt "exceeds a critical value" [FATO: doc A, p. 3, IV-B] |
| Origem de $t$ | Desde o corte (`t_contact`) [REPO: `.mod:106, 115`] | "after arc extinction" [FATO: doc A, p. 3] |
| Snubber | **Inexistente** no preprocessor: nenhum componente, nenhum emissor | SCR antiparalelo + $R_s = 30\ \Omega$/fase, disparo por DIAC [FATO: doc A, p. 2, III-A] |

Razões calculadas [CÁLCULO PRÓPRIO]: em $t=1$ ms, o modelo do repositório é $17{,}7/2{,}03 = 8{,}7\times$ mais rígido que o de A; a inclinação instantânea de A, $A + 2Bt$, só alcança os 17 kV/ms do repositório em $t = (17-0{,}801)/(2\times1{,}226) = 6{,}6$ ms. Quanto ao *chopping*, a energia capturada difere por $(5/2)^2 = 6{,}25\times$.

**O que isso implica para reprodutibilidade** [INFERÊNCIA, e é a conclusão desta subseção]:

1. **O repositório, como está, não reproduz a Tabela III de A e não deve ser usado para tentá-lo.** Uma recuperação 8,7× mais rígida no primeiro milissegundo suprime a maior parte das reignições, e é a escalada por reignições — não o *chopping* — que produz os 41,44 kV [FATO: doc A, p. 3, V-A].
2. **A divergência não é erro de um dos dois**: os parâmetros do repositório (5 A de *chopping*, 17 kV/ms) estão mais próximos da faixa central publicada (20–50 kV/ms; *chopping* de Cu/Cr de 2–10 A), enquanto os de A estão no **extremo inferior** dessa faixa [Etapa 1, §3.1 e §9, item 4]. São dois pontos legítimos de um espaço de parâmetros incertos.
3. **Consequência de método**: os parâmetros do VCB devem ser expostos como **entradas incertas com faixas declaradas** — RRDS 2–50 kV/ms, capacidade de extinção de AF 100–700 A/µs, *chopping* 1–10 A —, e não fixados nos valores de nenhum dos dois [Etapa 1, §8.3(h)]. Qualquer número de dano que dependa do pico de TRV herda **inteiramente** essa incerteza, e a Etapa 1 mostrou que errar o pico por fator 2 altera $\Delta D$ por $2^n$ = 16 a 512 vezes [Etapa 1, §5.5, Passo 3].
4. **A convenção de di/dt está invertida entre o repositório e o *texto* de A, e ambas divergem da literatura consolidada** (Wong; Xue e Popov; Abdulahovic adotam extinção quando $|di/dt|$ é **menor** que a capacidade) [Etapa 1, §3.1]. Precisão obrigatória: **A é internamente ambíguo**. O texto da Seção IV-B descreve **interrupção** acima do valor crítico — "the subsequent high frequency current **is interrupted** when its di/dt at the zero crossing exceeds a critical value (5 A µs⁻¹ to 15 A µs⁻¹)" —, ao passo que a Tabela II do mesmo artigo nomeia o parâmetro "**Critical reignition di/dt**", que é precisamente a convenção adotada pelo repositório [FATO: doc A, p. 3, IV-B e Tabela II]. A divergência não é, portanto, limpa entre repositório e A: é, em parte, uma contradição interna de A entre texto e tabela. **A pergunta a dirigir aos autores de A é qual das duas o modelo TACS efetivamente implementa** (Q1/Q9). Enquanto isso não for resolvido, **o sinal do efeito do parâmetro sobre $n_r$ é indeterminado** — e $n_r$ é entrada de (5.2).

---

## 10. Experimento computacional mínimo de cruzamento

**Objetivo.** Produzir, de forma reprodutível, a primeira frente de Pareto de planos de corte anotada com consumo esperado de vida do isolamento, unindo o domínio de B (s–min, OpenDSS) ao de A (µs–ms, ATP/EMTP). Todos os itens são [PROPOSTA] salvo indicação.

### 10.1 Cadeia de elos

| Elo | Entrada | Processo | Saída | Ferramenta |
|---|---|---|---|---|
| **E-0** | Descrição da planta | Reconstruir a planta de B como sistema explícito: fonte 13,8 kV ($I_{cc3\varphi}=15$ kA, X/R = 12), um transformador 7,5/9 MVA com $X_{HL}=8\%$ base 7,5 MVA, ΔYn, barra 4,16 kV, 19 máquinas somando 8927 kW mais 3,6 MW estáticos, alvo de 1250 kW | Modelo de rede | OpenDSS ou `power_flow.py` |
| **E-1** | Frente de Pareto de B | Varrer os planos $s$ da frente (e, para referência, os $2^{19}$ = 524 288 planos por enumeração exaustiva, viável em $\approx$ 3,6 h a 25 ms/avaliação) | $V^{(\mathrm{INRUSH})}_{\min}(s)$, $f_3$, $f_4$, $f_5$, $S_{TR}$ | Alg. 1 de B |
| **E-2** | $V_{\min}(s)$, curva $T_m(\omega)$, $T_L(\omega)$, $J$ | Integrar (4.2); calcular $I^2t$ e $U$ por (4.5); calcular $\theta_{hs}(t)$ | $t_{acc}(s)$, $U(s)$, $\theta_{hs}(s)$ | Novo módulo |
| **E-3** | $V_{\min}(s)$, $t_{acc}(s)$, ajuste e temporização da 27 (e da 51/48/49) | Estimar $P[\text{atuação} \mid V_{\min}, t_{acc}]$ como fração do tempo em que $V < V_{27}$ excede a temporização | $\lambda_A^{(\mathrm{part})}(s)$ [adimensional, por partida] e $\lambda_A^{(\mathrm{ano})} = \lambda_A^{(\mathrm{part})}\times N_{N-1}$ [eventos/ano] — convenção da §6.2 | Novo módulo |
| **E-4** | Planos com $\lambda_A > 0$ | Simulação ATP do evento de A, com e sem snubber, a partir do estado elétrico do plano (tensão de fonte reduzida a $V_{\min}$, corrente $0{,}85\times6{,}5\,I_n$) | Formas de onda em `X0002A-C` (barramento) **e** `01ATA-C` (terminal do motor) | ATP/EMTP, arquivo de referência |
| **E-5** | Formas de onda | Extrair o vetor $\mathbf{s}_{m,j} = (V^{\phi\text{-}g}_{pk}, V^{\phi\text{-}n}_{pk}, T_1, t_r, (dv/dt)_{\max}, E_s, f_{dom}, t_j)$ por evento e contar $n_r$ por polo | Vetor de estresse por evento | Novo módulo, Etapa 1 §8.2 |
| **E-6** | Vetores + $\theta_{hs}$ | Aplicar (5.1)–(5.2) com priors largos ($n\in[4,12]$, $V_{th}\in\{0;\,3{,}5;\,7{,}8\}$ pu, $m\in\{0,1\}$, HIC $\in\{8,10,15\}$ K); Monte Carlo | $\Delta D^{el}$, $\Delta D^{th}$, e a cota inferior $D^{th}+D^{el}$ | Novo módulo |
| **E-7** | Por plano | $f_6(s,u)$ de (6.1); $\widehat{\mathrm{RUL}} = (1-D)/\mathbb{E}[\Delta D]$ como **distribuição** (percentis B10/B50), com nível de confiança declarado [NORMA: ISO 13381-1, 3.3, 3.9] | RUL esperado por plano, com e sem snubber | — |
| **E-8** | $f_6$ e $g_4$ | Re-otimizar com quatro objetivos e quatro restrições; protocolo de B (µ=40, G=20, sementes 42–51, HV, Wilcoxon $\alpha=0{,}05$); comparar NSGA-II × NSGA-III × U-NSGA-III × aleatório | Nova frente de Pareto; correlação de postos $f_5$–$f_6$; PCA da frente | pymoo ou implementação própria |

### 10.2 Critérios de aceite

1. **E-0/E-1**: $V^{(\mathrm{INRUSH})}_{\min}$ com todas as máquinas em $0{,}755 \pm 0{,}03$ pu, e os planos {M_710, M_800} / {M_800} / {} em $0{,}850$ / $0{,}858$ / $0{,}866 \pm 0{,}01$ pu [FATO: doc B, p. 2–3]. **Reprodução exata é impossível sem os CSV retidos**; a diferença deve ser reportada como limitação, não absorvida.
2. **E-4**: picos e RRRV no barramento dentro de $\pm5\%$ da Tabela III de A (41,44/15,05; −38,30/19,00; −30,24/13,90 sem snubber; 13,65/13,11; −9,98/9,43; 6,35/3,28 com snubber) [FATO: doc A, Tabela III — a Tabela III sustenta apenas os pares pico/RRRV], **na condição de fonte a 1,0 pu, que é [HIPÓTESE]: A não declara o módulo da tensão de fonte** [FATO por omissão: doc A, p. 1–5; ver §3.3]; a corrida a $V_{\min}$ é o caso novo e não tem referência.
3. **E-5**: entregar as três grandezas que a Etapa 1 declarou faltantes — tensão no terminal do motor, contagem $n_r$ por polo e $T_1 = 1{,}67(t_{90}-t_{30})$ por reignição —, com passo de integração reduzido a 10–50 ns em pelo menos um caso de verificação.
4. **E-8**: (i) reproduzir o resultado de B a três objetivos (NSGA-II supera aleatório com $p \le 0{,}05$); (ii) reportar, a quatro objetivos, se NSGA-III supera NSGA-II — **teste empírico da metade não testada da diretriz de B**; (iii) $f_6$ com termo de religamento deve apresentar mínimo interior em $f_5$; se a correlação de postos $f_5$–$f_6$ exceder 0,95, rebaixar $f_6$ a restrição.

### 10.3 Entradas que faltam e como obtê-las

| Entrada faltante | Onde falta | Como obter | Se não obtida |
|---|---|---|---|
| Lista das 19 máquinas (P, fp, η, $I_{LR}$) | CSV de B, retidos para revisão cega [FATO: doc B, p. 3] | Solicitar ao autor; a planta é o caso-base natural do MVP | Lista sintética somando 8927 kW e contendo 710 e 800 kW; resultado **qualitativo** |
| $J$ e curva $T_L(\omega)$ do alvo | Ausente em A e em B [FATO: ausência] | Folha de dados do fabricante; ou envelope pela IOGP S-704 (aceleração garantida a 80 % V, margem $\ge$ 10 %) | Faixas por $k_T$ e tipo de carga (§4.2), reportadas como faixa |
| $t_{LR,\mathrm{hot}}$ e curvas quente/frio (IEEE 620) | Ausente em A e em B | Fabricante; a IEEE 620 **não** diz como construí-las [LITERATURA: Zocholl & Benmouyal 2001] | Faixa 10–20 s; declarar como hipótese |
| Ajuste **temporizado** da ANSI 27 | B declara só o nível (0,85 pu, "típico") [FATO: doc B, p. 2; FATO: ausência de temporização] | Ajuste real de uma planta; ou varredura paramétrica | $\lambda_A$ fica qualitativo; **é o elo mais crítico** (§ "próximo passo") |
| Classe térmica e HIC do sistema isolante | Ausente em A e em B | Ensaio IEC 60034-18-31 do fabricante [INSERIR CITAÇÃO — norma não acessada] | HIC $\in\{8,10,15\}$ K propagado por Monte Carlo |
| Expoente $n$, limiar $V_{th}$, fração $a(t_f)$ | **Nenhuma fonte primária acessada** [Etapa 1, §9, itens 1–2] | Ensaio de *endurance* a impulsos (IEC 60034-18-42; IEEE 522 até a falha); modelo MTL/FEM do motor específico para $a(t_f)$ | Priors largos; a saída é **razão** entre planos, não valor absoluto de RUL |
| $N_{N-1}$ (partidas sob N-1 por ano) | Ausente em A e em B | Taxa de falha do transformador × regime de manutenção; IEEE 493 | Entrada de planta declarada como hipótese |

**Regra de ouro do experimento** [PROPOSTA]: enquanto $n$, $V_{th}$ e $a(t_f)$ não forem medidos, **o entregável não é RUL em anos, e sim a razão de RUL entre planos e entre configurações de snubber** — grandeza que é invariante a $N_0$ e muito menos sensível aos parâmetros livres do que o valor absoluto.

---

## 11. Limitações, riscos de sobre-interpretação e perguntas abertas

### 11.1 Limitações desta etapa

1. **O elo L4–L5 é inferência, não fato.** A associação entre "commanded by the protection" (A) e a ANSI 27 (B) não é afirmada por nenhum dos dois [FATO por omissão: doc A, p. 3]. Enquanto o ajuste temporizado não for conhecido, a cadeia B → A é **qualitativa**.
2. **Toda a §4 é derivação com parâmetros hipotéticos.** As razões de $t_{acc}$ e $I^2t$ variam por fator superior a 10 conforme $k_T$ e o tipo de carga; nenhum número dessa seção deve ser citado como valor.
3. **Correção a um rascunho de insumo.** O rascunho `cruzamento_B_load_shedding_n1.md` (Tabela 2.5) conclui que "nenhuma das soluções de B satisfaz o critério IOGP $t_{acc} \le t_{LR,\mathrm{hot}} - 5$ s". Esta etapa **não sustenta** essa conclusão como resultado: ela depende inteiramente de $t_{acc}(1)=6$ s e $t_{LR,\mathrm{hot}}=12$ s, ambos hipotéticos, e inverte-se com $t_{LR,\mathrm{hot}}=20$ s. O enunciado correto é condicional: *se* os parâmetros forem os hipotetizados, *então* $g_4$ tornaria o problema infactível — e essa infactibilidade seria, ela própria, informação de decisão que B não pode produzir [INFERÊNCIA].
4. **A margem nula não é erro de B.** B otimiza contra a restrição declarada e o faz corretamente; o que falta é margem de projeto contra a incerteza do modelo. Atribuir a B um erro seria sobre-interpretação.
5. **O termo de sinergia não tem parâmetros.** (5.3) é definição por resíduo; nenhuma medição a sustenta [INSERIR CITAÇÃO].
6. **A razão de dano do snubber herda todas as ressalvas da Etapa 1** (§5.5): leitura de figura, contagem assimétrica entre ramos, expoentes emprestados de fio esmaltado, TRV no disjuntor. A faixa 100–170 ($n=4$) é ilustração, não medida.
7. **Correção a um rascunho de insumo, II.** O rascunho `cruzamento_A_snubber_vcb.md` (§2.2, leitura 1) escreve "faixa de ruptura de 5–10 pu reportada para isolação de espira nova". A Etapa 1 (§4.5, item 1 e §9, item 10) já vetou essa formulação: as fontes dão **limites inferiores** ($\ge$ 5 pu na maioria de 17 motores; $\ge$ 10 pu em máquinas novas), não um teto. Não usar.
8. **Discrepância não resolvida no modelo de A.** O ramo R–L de A drena 3,35 $I_n$ a $\cos\varphi = 0{,}200$, e não os 6,5 $I_n$ da Tabela I (§1.3). Enquanto isso não for esclarecido, todos os números de energia da §3.2 têm incerteza de fator até 3,8, e a afirmação de que A e B representam a máquina no **mesmo estado elétrico** só se sustenta quanto ao **ângulo** de impedância, não quanto ao módulo.
9. **Herdadas da Etapa 1**: ausência de $a(t_f)$ primário; expoentes emprestados; cenário único em A; parametrização de VCB no extremo inferior; TRV no disjuntor $\ne$ tensão no motor; passo de 1 µs insuficiente; convenção de di/dt não esclarecida; nenhuma norma certifica RUL [Etapa 1, §9, itens 1–12].
10. **Correção de sinal a D7 da Etapa 1** (§3.1). O fator térmico impresso na Etapa 1, $2^{(\theta_j-\theta_0)/\mathrm{HIC}}$ multiplicando $N_j$, faria o dano **decrescer** com a temperatura e é inconsistente com D6 do mesmo texto. Este documento adota $N_j \propto 2^{(\theta_0-\theta_j)/\mathrm{HIC}}$, equivalentemente $1/N_j \propto 2^{(\theta_j-\theta_0)/\mathrm{HIC}}$. Não é contradição de mérito — a Etapa 1 já rotula D7 como [HIPÓTESE de modelagem] —, e nenhum valor numérico muda; mas a Etapa 1 deve ser corrigida na próxima revisão.
11. **A monotonicidade $\partial F/\partial D > 0$ não decorre de D7** (§5.2). Para eventos mais severos que $V_{ref}$ — o regime dos 30–41 kV de A —, a normalização $(V_{ref}-V_{th})$ de D7 faz o dano por evento **cair** quando $V_{th}$ decresce por envelhecimento, invertendo o sinal. O enunciado $D_{sin}\ge 0$ é, portanto, **condicional**, e a reparametrização por suportabilidade residual ($a V_{pk}/U_w$) é a saída estrutural recomendada.
12. **Convenção dimensional de $f_6$ e de $\lambda_A$ fixada nesta revisão** (§6.2). Todos os termos de (6.1) e (7.1) são fração de vida **por evento de partida**; $\lambda_A^{(\mathrm{part})}$ é adimensional e $\lambda_A^{(\mathrm{ano})} = \lambda_A^{(\mathrm{part})}N_{N\text{-}1}$. A leitura em horas-equivalentes é secundária ($f_6\cdot L_0$). Antes desta revisão, as duas convenções coexistiam em §6.2, §7.1 e §10.1.
13. **Numeração das cláusulas IOGP corrigida** (§4.2, §4.4, §6.2). As cláusulas 9.12.x citadas nas versões anteriores são da **v1.0**, riscadas no redline v2.0 × v1.0; a numeração vigente é 11.3.1.x mais a Tabela 25. As transcrições literais estavam corretas; a versão atribuída, não. A Tabela 25 da v2.0 qualifica os mínimos de religamento como **"per hour"**, o que enfraquece o contraste que a versão anterior fazia com a ausência de "per hour" na NEMA.
14. **Escopo da NEMA MG 1, Parte 12, não é aplicável ao caso** (§4.4). A cláusula 12.54.1 vale para motores Design A/B dentro do escopo da Parte 12 (até 500 hp a 3600/1800 rpm); o alvo de 1250 kW e as cortadas de 710/800 kW são máquinas grandes, cobertas pela Seção III. O "mínimo NEMA" permanece no documento como **referência de ordem de grandeza**, não como âncora normativa do caso.
15. **Não existe orçamento de partidas agregável por planta** (§4.4). Os mínimos normativos são por máquina; o que B não modela é a **sequência** de 17 a 19 religamentos e seus intervalos, e o erro de contagem da partida do alvo é de fator 18 a 20, não 17 a 19.
16. **A hipótese de fonte a 1,0 pu em A é hipótese, não fato** (§3.3, §10.2). A não declara o módulo da tensão de fonte em nenhuma passagem [FATO por omissão: doc A, p. 1–5].
17. **O operador de (4.3) foi corrigido de mínimo para máximo** (§4.2). O erro anterior era **não conservador**; nenhum valor numérico da §4.2 muda, porque a aproximação de conjugado médio colapsa os dois operadores.

### 11.2 Riscos de sobre-interpretação — o que **não** dizer

| Não dizer | Por quê | O que dizer |
|---|---|---|
| "O Documento B previne o evento do Documento A" | Nenhum dos dois afirma isso; a ligação é inferência desta etapa e depende de L4–L5 | "O plano de corte de B determina a probabilidade da condição em que a interrupção de A ocorre [INFERÊNCIA]" |
| "A margem de 0,85 pu de B é insuficiente" | É julgamento sobre um ajuste que B declara como típico, não como resultado | "As três soluções operam com 0 a 1,9 % de margem; a discrepância **típica** documentada entre estudo quase-estático e dinâmico ($\pm$ 0,5 %) já consome metade da margem do joelho [CÁLCULO PRÓPRIO + LITERATURA, §2.4(a)]" |
| "O snubber multiplica a vida do isolamento por 100" | Razão de dano por evento $\ne$ razão de vida; e a razão é ilustração da Etapa 1 | "Sob as hipóteses declaradas, a razão de dano **por evento** é da ordem de $10^2$ para $n=4$, e a mitigação pode mover o evento para abaixo do limiar de dano [Etapa 1, §5.5]" |
| "A partida a 0,850 pu excede o limite térmico do motor" | Depende de $J$, $T_L$, $t_{LR,\mathrm{hot}}$, nenhum dos quais existe | "Sob parâmetros hipotéticos, o tempo de aceleração é 1,7 a 35 vezes o de tensão plena; o resultado é uma faixa, não um valor" |
| "$f_6$ melhora a decisão" | Nenhuma execução foi feita; a própria degenerescência é risco documentado | "$f_6$ é proposta cuja não degenerescência deve ser verificada por correlação de postos e PCA antes de qualquer conclusão" |
| "5 a 7 reignições por manobra, conforme A" | Não consta de A nem de B [FATO por omissão nos dois] | "Reignições por polo por manobra, $n_r$, variável aleatória com prior discreto em [0, 10] [Etapa 1, §5.3]" |

### 11.3 Perguntas abertas

| # | Pergunta | Por que importa | A quem/como perguntar |
|---|---|---|---|
| Q1 | Qual função de proteção comanda a interrupção no cenário de A? | Determina se o elo B → A se fecha pela 27 ou pela 51/48/49 (§4 sugere as três últimas como igualmente plausíveis sob $t_{acc}$ prolongado) | Autores de A |
| Q2 | Qual o ajuste **temporizado** da ANSI 27 e ele é o mesmo para o alvo e para as cargas vizinhas? | Sem temporização, $P[\text{atuação}]$ não é calculável; um afundamento de 10 s a 0,84 pu pode ou não atuar | Autores de B / dado de planta |
| Q3 | Por que o ramo R–L de A drena 3,35 $I_n$ e não 6,5 $I_n$ (§1.3)? | Escala toda a energia magnética por até 3,8× | Autores de A |
| Q4 | $J$, $T_L(\omega)$, $t_{LR,\mathrm{hot}}$ e classe térmica do motor de 1250 kW | Fecha a §4 e converte faixas em números | Folha de dados do fabricante |
| Q5 | O plano de corte contempla o **religamento** das 17–19 máquinas? Em que sequência e com que intervalo? | Domina $f_6$ (§6.2) e o orçamento de partidas (§4.4) | Autores de B / prática de planta |
| Q6 | $g_3$ nunca é ativa em B, pois $g_1$ satura primeiro [FATO: doc B, p. 3]. Isso se mantém com o transformador em AN (97 % da capacidade)? | Se o ar forçado falhar, a margem cai a 3 % e $g_3$ pode passar a ser a restrição ativa | Análise de sensibilidade |
| Q7 | $f_6$ degenera a frente por colinearidade com $f_5$? | Determina se $f_6$ é objetivo ou restrição (§6.3) | Experimento E-8 |
| Q8 | Um *surrogate* mantém $R^2 > 0{,}999$ para $t_{acc}$ e $f_6$? | Determina a viabilidade computacional (§6.4) | Experimento E-8 |
| Q9 | O snubber reduz o **número** de reignições ou apenas a amplitude? | Muda (5.2) pelo termo $n_{r,m}$; A não afirma [FATO por omissão] | Simulação E-4 com contagem |
| Q10 | Qual a taxa anual de contingências N-1 ($N_{N-1}$) e de partidas abortadas ($\lambda_m$)? | Converte dano por evento em RUL em tempo | Dado de planta / IEEE 493 |
| Q11 | Como conciliar Miner linear com dano dielétrico com limiar e com $D_{sin} \ge 0$? | A linearidade de Miner é hipótese incompatível com a autoaceleração de (5.3) | Processo de saltos / gama marcado [HIPÓTESE] |
| Q12 | Qual o RUL do próprio snubber sob $10^1$–$10^3$ eventos/ano? | $\lambda_3$ de Strangas exige a taxa de falha do SCR e do resistor | [CIGRE: TOR WG C4.76]; ensaio |

---

## 12. Referências

**Nota de verificação adversarial** [registro obrigatório]. Este documento passou por duas rodadas de verificação adversarial: (i) fidelidade aos textos primários A e B, com reconferência de cada transcrição, número e página, das afirmações de ausência em B, do texto integral do artigo 09 e de cada símbolo `[REPO:]` contra o repositório em HEAD `d6a1160`; e (ii) correção física, dimensional e normativa, com recálculo integral de todos os `[CÁLCULO PRÓPRIO]` e verificação do escopo das normas nos textos oficiais acessados (IOGP S-704 redline v2.0 × v1.0; ANSI/NEMA MG 1, Parte 12; Nivelo et al., IPST 2021). As correções resultantes estão aplicadas no corpo e registradas na §11.1, itens 10–17.

**Não reverificadas nessa rodada** — devem ser lidas com o mesmo estatuto que o documento já atribui a IEEE 620, IEEE 3002.7 e NEMA MG 1 ("texto integral não acessado"): NEMA MG 1 14.30 via Bonnett & Boteler; IEEE Std 399-1997, 9.3.1, p. 235; Zocholl (SEL, 7000 hp, $t_{LR}$ frio 14 s / quente 12 s; "the relay overestimates the temperature during valid start"; "the rotor reaches only 72 %"); CIGRE TB 703, p. 35–36, Tab. 4 (58 % contra 31 %); Houdouin e Saludjian, arXiv:2503.00094. Estas fontes **não foram refutadas**; foram apenas **não reconferidas** contra o texto primário nesta rodada. Toda a **aritmética** derivada delas, essa sim, foi reconferida e confere: $0{,}0431\times0{,}85 = 0{,}0366$ pu; $0{,}0366/0{,}016 = 2{,}29$; $0{,}005\times0{,}85 = 0{,}00425$ pu ($53\%$ de 0,008 pu); $4{,}3\times10^{-3}/8{,}5\times10^{-5} = 50{,}6$; $3{,}7\times10^{-2}/8{,}5\times10^{-5} = 431$ ($\log_{10}$: 1,70 a 2,63 ordens); $(0{,}7\times0{,}7225-0{,}3333)/(0{,}7-0{,}3333) = 0{,}470$ (queda de 53 %); $2^{20/8} = 5{,}66$ e $2^{20/15} = 2{,}52$ (dispersão 2,25×).

**Documentos primários (revisão duplo-cega; autoria não divulgada — [INSERIR CITAÇÃO] até publicação)**

AUTORES OMITIDOS. **Selective mitigation of vacuum circuit breaker switching overvoltages in medium voltage induction motors using an active thyristor snubber**. Submissão ao SEPOC 2026, 5 p. — **Documento A** [FATO: doc A, p. 1: "Anonymous Authors — Paper submitted to SEPOC 2026 for double blind review"].

AUTORES OMITIDOS. **Selective load shedding for the switching of large motors under N-1 contingency: constrained multiobjective optimization with NSGA-II, NSGA-III and regression surrogates**. Primeira submissão, SEPOC 2026, 6 p. — **Documento B** [FATO: doc B, p. 1: "Authors omitted for double blind review"].

**Documento interno do estudo**

ETAPA 1. **Aprofundamento no monitoramento de degradação de isolamentos de estator: estresse dielétrico espira-a-espira, TRVs de VCB e efeito cumulativo de reignições**. `docs/research/rul_isolamento/01_ETAPA1_monitoramento_degradacao_isolamento.md`, 873 l. (equações D1–D7 em §5.4; vetor $\mathbf{s}_{m,j}$ em §8.2; margem de coordenação $\gamma$ em §6).

**Normas**

ABNT. **ABNT NBR 17094-3:2018** — Máquinas elétricas girantes — Parte 3: Motores de indução trifásicos — Métodos de ensaio. Rio de Janeiro: ABNT, 2018.

IEC. **IEC 60034-1** — Rotating electrical machines — Part 1: Rating and performance. Genebra: IEC. (Tabela 7 consultada por reprodução literal em Leroy-Somer TN11 e WEG; **texto integral não acessado** — INSERIR CITAÇÃO.)

IEC. **IEC 60034-15:2009** — Impulse voltage withstand levels of form-wound stator coils. 3. ed. Genebra: IEC, 2009. Amostra: https://cdn.standards.iteh.ai/samples/15848/1b914cc7cb9b4c4582e502f946666007/IEC-60034-15-2009.pdf. Acesso em: 2 set. 2026. (Tabela 1, Nota 5 — "interrupted start"; A.1, A.3.)

IEC. **IEC CDV 60034-15 (2/2199/CDV)** — Committee Draft for Vote, future ed. 4. Genebra: IEC, 2024. Amostra: https://cdn.standards.iteh.ai/samples/76379/70c15953e53f480988b6605f0730692c/oSIST-prEN-IEC-60034-15-2024.pdf. Acesso em: 2 set. 2026. (Rascunho "subject to change"; 4.3 — níveis reforçados para "aborted starts".)

IEC. **IEC 60034-18-31** — Qualification and quality control tests for partial discharge free electrical insulation systems (Type I). Genebra: IEC. **Não acessada** — [INSERIR CITAÇÃO].

IEC. **IEC 60071-1:2019** — Insulation co-ordination — Part 1. 9. ed. Genebra: IEC, 2019. Amostra: https://cdn.standards.iteh.ai/samples/100144/6c649e0574b44164805acdb3a39941f0/IEC-60071-1-2019.pdf. Acesso em: 2 set. 2026. (3.31 — fator de segurança $K_s$; 3.34.)

IEC. **IEC 62271-110:2023** — Inductive load switching. 5. ed. Genebra: IEC, 2023. Amostra: https://cdn.standards.iteh.ai/samples/110032/6134d1d703624b01af650b4c93dc550f/IEC-62271-110-2023.pdf. Acesso em: 2 set. 2026. (4.3.2 — manobra de motor em partida como operação mais severa.)

IEEE. **IEEE Std 399-1997** — Recommended practice for industrial and commercial power systems analysis (Brown Book), cap. 9 — Motor-starting studies. Nova York: IEEE, 1998. Amostra: https://www.elecenghub.com/NewSamples/IEEE/181347463/IEEE-399-1997-2.pdf. Acesso em: 2 set. 2026. (9.3.1, p. 235; dados exigidos, p. 239.)

IEEE. **IEEE Std 620-2022** — Guide for the presentation of thermal limit curves for squirrel cage induction machines. Nova York: IEEE, 2022. Metadados: https://www.en-standard.eu/ieee-620-2022-ieee-guide-for-the-presentation-of-thermal-limit-curves-for-squirrel-cage-induction-machines/. Acesso em: 2 set. 2026. (**Texto integral não acessado** — INSERIR CITAÇÃO.)

IEEE. **IEEE Std 3002.7-2018** — Recommended practice for conducting motor-starting studies. Nova York: IEEE, 2019. Metadados: https://standards.ieee.org/content/ieee-standards/en/standard/3002_7-2018.html. Acesso em: 2 set. 2026. (Tabela de níveis críticos reproduzida literalmente por Nivelo et al., IPST 2021, p. 2; **texto integral não acessado**.)

IEEE. **IEEE Std C37.2-2008** — Standard for electrical power system device function numbers. Nova York: IEEE, 2008. (Referência [18] do Documento B.)

IEEE. **IEEE Std C57.91-2011** — Guide for loading mineral-oil-immersed transformers. Nova York: IEEE, 2012. (Referência [19] do Documento B; invocada qualitativamente, sem cláusula.)

IOGP. **IOGP S-704 v2.0 — Supplementary specification to IEC 60034-1 for high-voltage three-phase cage induction motors** (Redline v2.0 × v1.0). Londres: IOGP, nov. 2024. Disponível em: https://www.iogp.org/bookstore/wp-content/uploads/sites/2/2024/11/S-704v2024-11-TRS-REDLINE.pdf. Acesso em: 3 set. 2026. **Advertência de numeração**: o documento é um *redline*; as cláusulas **9.12.x são da v1.0 e aparecem riscadas**, enquanto a numeração **vigente da v2.0 é 11.3.1.x** mais a nova Tabela 25. Cláusulas efetivamente consultadas e transcritas nesta etapa: 8.1 (classe térmica 155 (F) sem exceder elevação da classe 130 (B)); v2.0 11.3.1.1 (corrente de rotor bloqueado entre 4,0 e 6,5 $I_N$) $\equiv$ v1.0 9.12.1.1; v2.0 11.3.1.3 (vida mínima de 5000 partidas a plena tensão); v2.0 11.3.1.4 e 11.3.1.6 (partida e aceleração a 80 % da tensão nominal; margem de conjugado $\ge$ 10 % do conjugado de plena carga "at any point") $\equiv$ v1.0 9.12.1.2–9.12.1.3; v2.0 11.3.1.5 (tempo de rotor bloqueado a quente $>$ tempo de aceleração a 80 % V mais 5 s) $\equiv$ v1.0 9.12.1.5; v2.0 Tabela 25 ("Number of re-starts of motors": mínimo de partidas consecutivas **por hora**, 3 a frio e 2 a quente, com "the motor should coast to rest between consecutive starts") $\equiv$ v1.0 9.12.2.1–9.12.2.4; v1.0 9.12.2.5 (mínimo de 1000 partidas/ano).

ISO. **ISO 13381-1:2015** — Condition monitoring and diagnostics of machines — Prognostics — Part 1. Amostra: https://cdn.standards.iteh.ai/samples/51436/8246d96c8ff54347ae65f3aba73f2e88/ISO-13381-1-2015.pdf. Acesso em: 2 set. 2026. (3.3, 3.9 — horizonte preditivo e nível de confiança. Substituída pela ed. 2025, não lida.)

NEMA. **ANSI/NEMA MG 1-2016 (R2018)** — Motors and generators. Parte 12 consultada em texto oficial: 12.1 (escopo — motores CA até 500 hp a 3600/1800 rpm, 350 hp a 1200 rpm, 250 hp a 900 rpm), 12.44.2 ("the torque developed by the motor at any speed is **approximately** proportional to the square of the voltage"), 12.54.1 (partidas em sucessão, para motores Design A/B com potências de 10.32.4). Partes 30–31 e cláusula 14.30 **não localizadas no texto acessado** — [INSERIR CITAÇÃO]. Reproduções literais secundárias: FAQ NEMA (https://www.nema.org/membership/products/mg-1-faq, FAQ 1.41) e Bonnett & Boteler (ACEEE 2001, p. 2). Acesso em: 3 set. 2026.

**Artigos do corpus de apoio**

JENSEN, W. R.; STRANGAS, E. G.; FOSTER, S. N. A method for online stator insulation prognosis for inverter-driven machines. **IEEE Transactions on Industry Applications**, v. 54, n. 6, p. 5897–5906, 2018. DOI 10.1109/TIA.2018.2854408. (Artigo 02 — texto integral lido.)

MA, K.; LISERRE, M.; BLAABJERG, F.; KEREKES, T. Thermal loading and lifetime estimation for power device considering mission profiles in wind power converter. **IEEE Transactions on Power Electronics**, v. 30, n. 2, p. 590–602, 2015. DOI 10.1109/TPEL.2014.2312335. (Artigo 12 — texto integral lido.)

SIAMI-NAMINI, S.; TAVAKOLI, N.; SIAMI NAMIN, A. The performance of LSTM and BiLSTM in forecasting time series. In: **IEEE Big Data**, 2019, p. 3285–3292. (Artigo 10.)

STRANGAS, E. G.; AVIYENTE, S.; NEELY, J. D.; ZAIDI, S. S. H. The effect of failure prognosis and mitigation on the reliability of permanent-magnet AC motor drives. **IEEE Transactions on Industrial Electronics**, v. 60, n. 8, p. 3519–3528, 2013. DOI 10.1109/TIE.2012.2227913. (Artigo 09 — texto integral lido.)

VICHARE, N. M.; PECHT, M. G. Prognostics and health management of electronics. **IEEE Transactions on Components and Packaging Technologies**, v. 29, n. 1, p. 222–229, 2006. (Artigo 07 — texto integral lido; DOI completo — [INSERIR CITAÇÃO].)

YIN, C.; HU, Y.; CAO, W. IGBT remaining useful life prediction based on CNN-BiLSTM-Attention. In: **ISEEIE**, 2024, p. 62–66. DOI 10.1109/ISEEIE62461.2024.00019. (Artigo 08.)

YU, M.; WANG, D.; LUO, M. Model-based prognosis for hybrid systems with mode-dependent degradation behaviors. **IEEE Transactions on Industrial Electronics**, v. 61, n. 1, p. 546–554, 2014. DOI 10.1109/TIE.2013.2244538. (Artigo 06 — texto integral lido.)

**Literatura verificada**

BONNETT, A. H.; BOTELER, R. The impact that voltage variations have on AC induction motor performance. In: **ACEEE Summer Study on Energy Efficiency in Industry**, 2001. Disponível em: https://www.aceee.org/files/proceedings/2001/data/papers/SS01_Panel2_Paper27.pdf. Acesso em: 2 set. 2026.

CIGRE. **Technical Brochure 703 — Insulation degradation under fast, repetitive voltage pulses**. WG D1.43. Paris: CIGRE, 2017. Disponível em: https://cigre.cz/dokumenty_komise/d1/WG%20D1.43_TB_Final.pdf. Acesso em: 2 set. 2026. (p. 29, Fig. 31; p. 35–36, Tab. 4 — aquecimento dielétrico.)

CIGRE. **Terms of Reference WG C4.76 — Overvoltage protection in switching inductive devices with vacuum circuit breaker**. 31 jul. 2023. Disponível em: https://www.cigre.org/userfiles/files/News/2023/TOR-WG%20C4_76_Overvoltage%20protection%20in%20switching%20inductive%20devices%20with%20vacuum%20circuit%20breaker-rev1.pdf. Acesso em: 2 set. 2026.

FEILAT, E. A. Lifetime assessment of electrical insulation. In: **Electric Field**. Londres: IntechOpen, 2018. DOI 10.5772/intechopen.72423. Disponível em: https://cdn.intechopen.com/pdfs/58128.pdf. Acesso em: 2 set. 2026. (eqs. (21), (26), (27), (29).)

GUPTA, B. K. et al. Turn insulation capability of large AC motors, Partes 1–3. **IEEE Transactions on Energy Conversion**, v. EC-2, n. 4, p. 658–679, 1987. DOI 10.1109/TEC.1987.4765906/.4765907/.4765908. (Resumos verificados; **textos integrais não acessados**.)

HAQ, S. U.; OMRANIPOUR, R.; TERAN, L. Surge withstand capability of electrically and thermo-mechanically aged turn insulation of medium voltage form-wound AC stator coils. In: **IEEE EIC**, 2014. DOI 10.1109/EIC.2014.6869351. (Resumo verificado; **valores numéricos não acessados**.)

HOUDOUIN, P.; SALUDJIAN, L. Gaussian process surrogate model to approximate power grid simulators. **arXiv**:2503.00094, 2025. Disponível em: https://arxiv.org/abs/2503.00094. Acesso em: 2 set. 2026.

L&B ELECTRIC. **Medium voltage motor starting** (N. Duplantis, 1998). Disponível em: https://www.landbelectric.com/download-document/81-medium-voltage-motor-starting.html. Acesso em: 2 set. 2026.

LEROY-SOMER. **Technical Note TN11 — Insulation class / temperature rise class** (5202en-2024.09/d). Disponível em: https://www.leroy-somer.com/documentation_pdf/5202_en.pdf. Acesso em: 2 set. 2026.

NIVELO, J. J. O. et al. Evaluating voltage drop snapshot and time motor starting study methodologies — an offshore platform case study. In: **IPST 2021**, Belo Horizonte, paper 21IPST112. Disponível em: https://www.ipstconf.org/papers/Proc_IPST2021/21IPST112.pdf. Acesso em: 3 set. 2026. (p. 2 — Tabela I da IEEE 3002.7; p. 6–8 — snapshot × domínio do tempo: "the vast majority of the absolute differences obtained were less than ± 0.5 %"; máximo de 4,31 % na Tabela VII, barra PN-2A / M4-740 kVA, que os autores atribuem a "the equivalent loads created in the respective buses" e cuja base de normalização não é declarada — ver ressalvas na §2.4(a).)

PES-PSRC. **C37.96-2012 — IEEE Guide for AC Motor Protection**: apresentação do WG J10, set. 2013. Disponível em: https://www.pes-psrc.org/kb/report/1015.pdf. Acesso em: 2 set. 2026. (p. 17–18, 21, 37, 44 (PDF).)

SCHAEFER, F.; MENKE, J.-H.; BRAUN, M. Evaluating machine learning models for the fast identification of contingency cases. **arXiv**:2008.09384, 2020. Disponível em: https://arxiv.org/abs/2008.09384. Acesso em: 2 set. 2026.

THEOFANOUS, A. et al. Modelling of insulation thermal ageing: historical evolution from fundamental chemistry towards becoming an electrical machine design tool. **Energies**, v. 18, art. 6087, 2025. DOI 10.3390/en18236087. Disponível em: https://aisberg.unibg.it/retrieve/43c96487-a8ad-4947-a8c8-3b350e9892a2/J65.pdf. Acesso em: 2 set. 2026. (p. 7–8, 11, 14, 31; eqs. (9)–(10), (17)–(19).)

WEG. **Guia de especificação — Motores elétricos** (50032749). Jaraguá do Sul: WEG, s.d. Disponível em: https://static.weg.net/medias/downloadcenter/h32/hc5/WEG-motores-eletricos-guia-de-especificacao-50032749-brochure-portuguese-web.pdf. Acesso em: 2 set. 2026. (p. 29, 36.)

WESENDRUP, K.; HELLINGRATH, B. A process-based review of post-prognostics decision-making. **PHM Society European Conference**, v. 5, n. 1, 2020. Disponível em: https://papers.phmsociety.org/index.php/phme/article/download/1203/phmec_20_1203. Acesso em: 2 set. 2026.

ZOCHOLL, S. E. Optimizing motor thermal models. **SEL Journal of Reliable Power**, v. 3, n. 1, 2012 (PCIC 2006, I&CPS 2007). Disponível em: https://cdn.selinc.com/assets/Literature/Publications/Technical%20Papers/6276_OptimizingThermalModels_SZ_20070226_Web.pdf. Acesso em: 2 set. 2026. (eqs. (19)–(21); exemplo de 7000 hp; rotor a 72 % do limite.)

ZOCHOLL, S. E.; BENMOUYAL, G. Using thermal limit curves to define thermal models of induction motors. In: **Western Protective Relay Conference**, 28., Spokane, 2001. Disponível em: https://wprcarchives.org/wp-content/uploads/2024/07/STANLEY-E.-ZOCHOLL_USING-THERMAL-LIMIT-CURVES-TO-DEFINE-THERMAL-MODELS-OF-INDUCTION-MOTORS_2001.pdf. Acesso em: 2 set. 2026.

**Repositório**

OLIVAS POWER SYSTEM STUDIO. Repositório local `/home/user/olivas-power-system-studio`, HEAD `d6a1160`. Símbolos citados na §9 verificados por leitura direta nesta sessão: `app/postprocessor/motor_starting.py:99,410,505,540`; `app/postprocessor/tcc_damage.py:450,471,532`; `app/postprocessor/tcc_devices.py:399`; `app/postprocessor/power_flow.py:87`; `app/preprocessor/equipment_catalog.py:124`; `app/preprocessor/atp_templates/vcb_reignition.mod:48,50,52,53,83,98-101,115,120`; `app/analysis/transient_metrics.py:41,91`; `app/analysis/csv_export.py:48`; `app/analysis/report_export.py:93`; `app/gui/main_window.py:2298`; `app/postprocessor/trt_analyzer.py:299,372`. Arquivo de referência ATP recuperado do histórico: `git show ad308d5:trt_all_motors_dt_ea.atp` (l. 589, 616, 643, 736-738).

**Referências ainda sem fonte primária acessada** — manter [INSERIR CITAÇÃO] até verificação

IEEE Std 522, Fig. 1 (envelope tensão × tempo de frente); IEC 60034-15:2025, Tabela 1; IEC 60034-18-41:2014, Tabela 4 e Fig. 7; IEC 60034-18-31 (constantes de envelhecimento térmico do sistema isolante); IEEE 620-2022 e IEEE 3002.7-2018 (textos integrais); NEMA MG 1 (texto integral); IEC 60034-1 (texto integral, Tabela 7); MONTSINGER (1930); DAKIN (1948); MONTANARI, MAZZANTI e SIMONI (2002); SIMONI (1981, 1984); GUPTA et al. (1987, Partes 1–3) e GUPTA, LLOYD e SHARMA (1990), textos integrais; HAQ, OMRANIPOUR e TERAN (2014), valores numéricos; ISHIBUCHI et al. (2017) e DEB e JAIN (2014), citados por B e não lidos nesta sessão; parâmetros medidos de $\psi(\cdot)$, $V_{th}(\theta)$ e $D_{sin}$ para mica-epóxi pré-formada de MT.
