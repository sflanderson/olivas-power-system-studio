# Fichamento A — Snubber tiristorizado ativo para mitigação seletiva de sobretensões de manobra de VCB em motores de indução de MT

## Convenções deste fichamento

- Fonte primária: `/tmp/claude-0/-home-user-olivas-power-system-studio/9d851478-5457-5818-8269-a836133b8dbc/scratchpad/papers_AB/txt/A_sepoc_snubber.txt` (5 páginas, marcadores `===== PAGE N =====`), complementada pela inspeção visual das Figs. 2, 3 e 4 extraídas do PDF `papers_AB/pdf/A_sepoc_snubber.pdf` (p. 4). Leituras de figura são sempre rotuladas como tal. As leituras da Fig. 2 usadas nas Seções 3.2 e 9.2 (rótulos "0.5 km", "185mm²", "240mm²" e ponto de conexão do snubber) foram reconferidas na imagem nativa embutida no PDF (2373 × 974 px, p. 4), com recortes ampliados; o texto do artigo não contém nenhum desses valores (verificado por busca no texto integral).
- Rótulos de evidência: **[FATO: doc A, p. N]** = afirmação textual do artigo; **[FATO: doc A, Fig. N, p. 4 — leitura de figura]** = dado legível apenas na figura; **[NORMA: id, cláusula]** = conteúdo normativo verificado; **[LITERATURA: ref., URL]** = fonte externa verificada nesta sessão; **[CÁLCULO PRÓPRIO]** = aritmética feita neste fichamento a partir de dados rotulados; **[INFERÊNCIA FÍSICA]** = derivação explícita a partir de fatos rotulados; **[HIPÓTESE]** = proposição não verificada; **[INSERIR CITAÇÃO]** = referência faltante.
- Mapa de páginas do texto-fonte: p. 1 = título, resumo, Seção I (Introdução) até a lista de contribuições; p. 2 = fim das contribuições, Seções II, III e início da IV; p. 3 = Tabelas I, II e III, Seções IV-A/B/C e V-A/B/C; p. 4 = legendas das Figs. 2–4, fim da Seção V-C, Seção VI (Conclusão) e ref. [1]; p. 5 = refs. [2]–[24].
- A premissa do usuário de "múltiplas reignições (5 a 7 eventos por ciclo)" **não consta do texto do Documento A**; ver Seção 6.7 para o estado dessa premissa frente ao artigo e à literatura verificada.

---

## 1. Referência

AUTORES ANÔNIMOS. *Selective Mitigation of Vacuum Circuit Breaker Switching Overvoltages in Medium Voltage Induction Motors Using an Active Thyristor Snubber*. Artigo submetido ao SEPOC 2026 (Seminar on Power Electronics and Control), revisão duplo-cega, informação de autoria omitida. 5 p., 4 figuras, 3 tabelas, 24 referências. [FATO: doc A, p. 1]

Palavras-chave (Index Terms) do artigo: circuit breakers, EMTP, induction motors, insulation life, power system transients, snubbers, surge protection, thyristors, transient analysis. [FATO: doc A, p. 1]

Vínculos declarados pelo próprio artigo: (i) estende o modelo fenomenológico de VCB e o estudo de caso de MT desenvolvidos na dissertação [1] (Silva, CEFET-MG, 2026, em português); (ii) constitui a "camada reflexiva (hardware)" de um método de duas camadas objeto de pedido de patente brasileiro [23]; (iii) aponta como próximo passo a validação em bancada de MT descrita em [24] (SBAI/SBSE 2025). [FATO: doc A, p. 1, 2 e 4]

---

## 2. Objetivo

- Objetivo declarado: apresentar "um estudo ATP/EMTP de um snubber tiristorizado ativo que é inserido na rede apenas durante o transitório", comparando quantitativamente, num motor de 1250 kW/4,16 kV, a TRV (tensão de restabelecimento transitória) com e sem o snubber, sob o cenário de pior caso (interrupção intempestiva da partida). [FATO: doc A, p. 1, resumo; p. 2, contribuições]
- Contribuições enumeradas pelo artigo [FATO: doc A, p. 1–2]:
  1. modelo dinâmico trifásico de VCB em ATP/EMTP (ATPDraw) que reproduz chopping de corrente, recuperação dielétrica (a frio) parabólica e reignição em alta frequência via controle TACS/MODELS [1];
  2. modelo de snubber ativo com disparo autônomo (SCRs em antiparalelo + resistor de amortecimento dimensionado próximo à impedância de surto, disparo tipo DIAC, bloqueio na passagem por zero da corrente);
  3. comparação quantitativa da TRV com e sem snubber, "enquadrada" (framed) na filosofia de suportabilidade a impulsos de frente íngreme (SFI) da IEC 60034-15 e nas regras de coordenação de isolamento da IEC 60071-1.
- Escopo explicitamente restrito: "O presente artigo valida apenas a camada reflexiva; a camada de proteção digital está fora do escopo deste trabalho." [FATO: doc A, p. 2, Seção III-B]
- Natureza da validação: "computacional" ("validate at the computational level"); validação experimental em bancada de 4,16 kV declarada como "próximo passo" e "em estudo". [FATO: doc A, p. 1 resumo; p. 4 conclusão]

---

## 3. Sistema estudado e parâmetros

### 3.1 Motor de indução (Tabela I do artigo)

| Parâmetro | Valor | Evidência |
|---|---|---|
| Potência nominal | 1250 kW | [FATO: doc A, Tabela I, p. 3] |
| Tensão de linha | 4,16 kV | [FATO: doc A, Tabela I, p. 3] |
| Frequência | 60 Hz | [FATO: doc A, Tabela I, p. 3] |
| Rendimento η | 0,95 | [FATO: doc A, Tabela I, p. 3] |
| Fator de potência | 0,88 | [FATO: doc A, Tabela I, p. 3] |
| Relação corrente de partida / nominal Ip/In | 6,5 | [FATO: doc A, Tabela I, p. 3] |
| Corrente nominal In = P/(√3·V·η·fp) = 1 250 000/(√3·4160·0,95·0,88) | ≈ 207,5 A | [CÁLCULO PRÓPRIO a partir da Tabela I] — coincide com "Line current (rms): 207.52 A" legível no relatório do modelo na Fig. 2 [FATO: doc A, Fig. 2, p. 4 — leitura de figura] |
| Corrente de partida Ip = 6,5·In | ≈ 1 349 A (≈ 1,35 kA) | [CÁLCULO PRÓPRIO] |
| Tensão de fase eficaz 4160/√3 | 2 401,8 V | [CÁLCULO PRÓPRIO]; coincide com "Phase voltage (rms): 2401.78 V" na Fig. 2 [leitura de figura] |
| Tensão de fase de pico 4160·√2/√3 | 3 396,6 V (≈ 3,40 kV) | [CÁLCULO PRÓPRIO] — usada adiante como base 1 pu |

Dados adicionais do motor legíveis apenas no quadro "MOTOR R-L MODEL REPORT FOR ATP (TRV)" da Fig. 2, não transcritos no texto [FATO: doc A, Fig. 2, p. 4 — leitura de figura]: TAG do motor 0101-MP-0001A; P_in = 1315,79 kW; S_in = 1495,22 kVA; impedância equivalente por fase (Y): |Z_eq| = 3,4550 Ω, R_eq = 0,691 Ω, X_eq = 3,3851 Ω, L_eq = 8,9795 mH; o motor é representado por um ramo R–L série concentrado rotulado "TRANSIENT ENERGIZATION STATE".

Observação crítica [INFERÊNCIA — leitura da Fig. 2, a verificar em [1]]: com V_fase = 2401,8 V e |Z_eq| = 3,455 Ω, a corrente do equivalente seria 695 A ≈ 3,35·In, e não 6,5·In = 1349 A (que exigiria |Z_eq| ≈ 1,78 Ω). O fator de potência do equivalente (0,691/3,455 = 0,20) é compatível com rotor bloqueado, mas o módulo da corrente não reproduz o Ip/In = 6,5 da Tabela I. O artigo não explica a relação entre os dois conjuntos de dados. Além disso, X_eq = 2π·60·8,9795 mH = 3,385 Ω confere [CÁLCULO PRÓPRIO].

### 3.2 Rede, cabos e fonte

| Elemento | Descrição | Evidência |
|---|---|---|
| Fonte a montante | Fonte trifásica 60 Hz representando o alimentador de MT | [FATO: doc A, p. 3, IV-A] |
| Transformador abaixador | Presente na visão geral do circuito ("step down transformer"); sem dados no texto | [FATO: doc A, Fig. 2 legenda, p. 4] |
| Idem, leitura de figura | Transformador Δ–Y (rótulo "BCT"); medidores de tensão rotulados "11718∠0" (primário, lado fonte) e "3386∠30" (secundário Y do transformador, a montante do bloco LCC de 0,5 km); o valor 3386 V ≈ pico da tensão de fase da barra de 4,16 kV (3397 V) e o defasamento de 30° é compatível com Δ–Y | [FATO: doc A, Fig. 2, p. 4 — leitura de figura]; interpretação como pico de fase: [INFERÊNCIA]; nível de tensão a montante: não determinável com segurança [HIPÓTESE: ~13,8–14,4 kV] |
| Cabo secundário do transformador→VCB | Bloco "LCC" rotulado "0.5 km" e "185mm²", inserido entre o nó do secundário (Y) do transformador BCT (onde está o medidor "3386∠30") e o divisor trifásico que alimenta os três polos do VCB. O texto do artigo não informa comprimento nem seção de nenhum cabo; a atribuição do modelo JMARTI aos cabos vem apenas da Seção IV-A e da legenda da Fig. 2, não do rótulo do bloco | Comprimento e seção: [FATO: doc A, Fig. 2, p. 4 — leitura de figura, reconferida em recorte ampliado da imagem nativa]; tipo JMARTI/LCC: [FATO: doc A, p. 3, IV-A; Fig. 2 legenda, p. 4]; ausência desses valores no texto: [FATO por omissão] |
| Elemento entre a fonte EPSrst e o primário do transformador | Elemento concentrado rotulado "185mm²" (símbolo com resistor em série e dois elementos capacitivos laterais); tipo exato do componente não legível | [FATO: doc A, Fig. 2, p. 4 — leitura de figura]; natureza do componente (p. ex. equivalente π concentrado): [HIPÓTESE] |
| Cabo VCB→motor | Bloco "LCC" rotulado "240mm²", entre o nó do lado de carga do VCB e o motor equivalente; o bloco não exibe rótulo de comprimento e o texto não o informa | Seção: [FATO: doc A, Fig. 2, p. 4 — leitura de figura, reconferida]; tipo JMARTI/LCC: [FATO: doc A, p. 3, IV-A; Fig. 2 legenda, p. 4]; comprimento: [FATO por omissão] |
| Modelo dos cabos | "Frequency dependent line and cable model (JMARTI, Line and Cable Constants, LCC)", reproduzindo o comportamento a parâmetros distribuídos em alta frequência "que governa as frentes íngremes" | [FATO: doc A, p. 3, IV-A] |
| Localização do snubber — o que o texto diz | "The branch is connected in parallel with the machine terminals" (Seção III, repetido em III-A, p. 2); legenda da Fig. 1: "connected between the bus and the neutral", com o nó de entrada rotulado "from VCB / motor bus" (p. 2). O texto não define se "machine terminals" designa os bornes físicos do motor ou o barramento do motor no painel | [FATO: doc A, p. 2]; ambiguidade terminológica: [FATO por omissão] |
| Localização do snubber — o que a Fig. 2 mostra | Os três ramos SCR–SCR–R_s e o bloco `snub_ctrl` (desenhados em traço cinza-claro) partem de um nó do barramento do lado de carga do VCB, situado entre a sonda de tensão "V" e o bloco LCC de 240 mm² que leva ao motor equivalente; não há ligação do snubber ao nó do motor (sonda 01AT) | [FATO: doc A, Fig. 2, p. 4 — leitura de figura, reconferida em recorte ampliado da imagem nativa]; significado do traço cinza-claro (componente desabilitado/oculto no caso "sem snubber"?): [HIPÓTESE] |
| Localização do snubber — conclusão | Se a leitura da Fig. 2 estiver correta, o snubber está no lado do painel (barramento do VCB), a montante do cabo de 240 mm², e não nos bornes físicos do motor; a afirmação textual "machine terminals" só se concilia com a figura se designar o barramento do motor no painel. O artigo não esclarece a discrepância nem apresenta sensibilidade ao ponto de conexão | [INFERÊNCIA a partir da leitura de figura e do texto da p. 2] |
| Ponto de medição da "TRV at the VCB" | Sonda de tensão "V" no nó de carga do VCB (Fig. 2); existe também sonda "01AT" no terminal do motor, cujos resultados não são reportados | [FATO: doc A, Fig. 2, p. 4 — leitura de figura]; se a grandeza é tensão nó-terra ou tensão através do gap: não esclarecido no texto [INFERÊNCIA] |

### 3.3 VCB dinâmico e snubber (Tabela II do artigo, transcrita integralmente)

| Parâmetro | Valor | Evidência |
|---|---|---|
| Nível de chopping I_ch | 1 A a 2 A | [FATO: doc A, Tabela II, p. 3; texto IV-B cita [1], [5]] |
| Constante A da RRDS | 0,801 kV·ms⁻¹ | [FATO: doc A, Tabela II, p. 3] |
| Constante B da RRDS | 1,226 kV·ms⁻² | [FATO: doc A, Tabela II, p. 3] |
| di/dt crítico de reignição (interrupção da corrente de AF) | 5 A·µs⁻¹ a 15 A·µs⁻¹ | [FATO: doc A, Tabela II, p. 3; texto IV-B cita [1], [2]] |
| Dispersão (stagger) da separação dos contatos | 14 ms a 25 ms | [FATO: doc A, Tabela II, p. 3] |
| Resistor de amortecimento do snubber R_s (por fase) | 30 Ω | [FATO: doc A, Tabela II, p. 3; p. 2 III-A] |
| Passo de integração | 1 µs | [FATO: doc A, Tabela II, p. 3; p. 3 IV] |
| Janela simulada | 45 ms | [FATO: doc A, Tabela II, p. 3; p. 3 IV] |

Elementos do modelo de VCB visíveis na Fig. 2 [FATO: doc A, Fig. 2 legenda, p. 4]: blocos MODELS `vcb_rr`, `vcb_rs`, `vcb_rt` (um por fase), cada um comutando um ramo de arco RARC, LARC, CARC conforme o estado do disjuntor; sinais `SW_STATEr/s/t`. Valores de RARC, LARC e CARC: não informados.

Ambiguidade do "stagger" [INFERÊNCIA — a esclarecer em [1]]: o texto diz que os instantes de separação são "slightly offset between phases (of the order of 14 ms to 25 ms)". Um desvio mútuo de 14–25 ms não seria "leve" (é maior que um semiciclo de 8,33 ms); a leitura mais plausível é que os instantes absolutos de separação estão entre 14 ms e 25 ms da janela de 45 ms. Essa leitura é compatível com a Fig. 3, em que o primeiro evento visível ocorre em ≈ 19,7 ms e o surto principal em ≈ 24,7 ms [FATO: doc A, Fig. 3, p. 4 — leitura de figura]. Para referência: a não simultaneidade de polos admissível em disjuntores de AT é limitada por norma [NORMA: IEC 62271-100, cláusula sobre não simultaneidade de polos — número de cláusula e valor a verificar; não citada pelo artigo].

### 3.4 Cenário simulado

- "Interrupção intempestiva de uma partida de motor comandada pela proteção": a manobra é abortada enquanto a máquina drena a corrente de partida plena (Ip/In = 6,5), "isto é, o chopping de uma grande corrente indutiva nas piores condições possíveis". [FATO: doc A, p. 3, Seção V]
- Janela de 45 ms; figuras 3 e 4 exibem o intervalo 0,015–0,030 s com eixo de −40/−50 a +50 kV. [FATO: doc A, Tabela II, p. 3; Figs. 3–4, p. 4 — leitura de figura]

---

## 4. Modelagem (equações transcritas, com página)

### 4.1 Energia de chopping (Seção II-A)

(E1) A interrupção de i_L antes do zero natural "força a energia indutiva ½·L·I_ch² para a capacitância C do lado da carga, excitando oscilações de alta frequência cujo primeiro pico pode atingir várias vezes a tensão de pico do sistema [5], [10]". [FATO: doc A, p. 2, II-A]

O artigo **não** escreve a forma fechada da sobretensão de chopping. A forma clássica por balanço de energia é ½·L_b·I_0² + ½·C_b·U_pf² = ½·C_b·Û_m², donde Û_m = √(U_pf² + I_0²·L_b/C_b) [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, Seção II-A, https://www.ipstconf.org/papers/Proc_IPST2007/07IPST106.pdf — versão IPST do trabalho cujo correlato PCIC Europe 2007 é a ref. [14] do artigo]. Para I_ch → 0 na tensão de pico, reduz-se a ΔV = I_ch·√(L/C) [INFERÊNCIA FÍSICA a partir da expressão anterior].

Ordem de grandeza [INFERÊNCIA FÍSICA com hipótese explícita]: com L_eq = 8,98 mH (Fig. 2) e I_ch = 2 A (Tabela II), a energia magnética presa é ½·8,98·10⁻³·2² ≈ 18 mJ [CÁLCULO PRÓPRIO]. A sobretensão de chopping exige C, que o artigo não fornece; supondo C = 10 nF [HIPÓTESE], √(L/C) ≈ 948 Ω e ΔV ≈ 1,9 kV; com C = 1 nF [HIPÓTESE], ΔV ≈ 6 kV. Em qualquer dos casos, o chopping isolado não explica picos de 30–41 kV; a escalada decorre das reignições sucessivas, como o próprio artigo afirma ("the successive reignitions escalate the TRV to severe levels") [FATO: doc A, p. 3, V-A]. Concordante com a literatura: "overvoltages at current chopping do not need surge protection" [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, Seção II-A, URL acima].

### 4.2 Recuperação dielétrica a frio — lei parabólica (Seção IV-B)

(E2) V_wth(t) = A·t + B·t², com t = tempo após a extinção do arco, A = 0,801 kV·ms⁻¹, B = 1,226 kV·ms⁻². Citada como "parabolic rate of rise of dielectric strength (RRDS) law" [1], [7]. [FATO: doc A, p. 3, IV-B e Tabela II]

Valores tabulados [CÁLCULO PRÓPRIO a partir de (E2)]:

| t após extinção (ms) | V_wth (kV) |
|---|---|
| 0,1 | 0,092 |
| 0,5 | 0,707 |
| 1,0 | 2,03 |
| 2,0 | 6,51 |
| 3,0 | 13,44 |
| 4,0 | 22,82 |
| 5,0 | 34,66 |
| 6,0 | 48,94 |

Tempos para o gap suportar os picos reportados [CÁLCULO PRÓPRIO, raiz positiva de B·t² + A·t − V = 0]: V = 41,44 kV → t ≈ 5,50 ms; V = 13,65 kV → t ≈ 3,03 ms; V = 14,07 kV (U'_P da IEC 60034-15:2009 para 4,16 kV, ver Seção 7) → t ≈ 3,08 ms.

Comparação com a literatura [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, Seção III-D, URL acima]: aquele modelo usa recuperação **linear** com inclinação de 20 ou 40 kV/ms. A lei (E2) do Documento A fornece apenas ≈ 2 kV em 1 ms, isto é, cerca de dez vezes menos que 20 kV/ms no primeiro milissegundo, e só ultrapassa 20 kV/ms de inclinação instantânea (dV/dt = A + 2Bt) para t > 7,8 ms [CÁLCULO PRÓPRIO]. [INFERÊNCIA]: a recuperação adotada no Documento A é comparativamente lenta, o que favorece reignições mais numerosas e escalada mais severa; o artigo não discute a origem experimental de A e B além de remeter a [1] e [7].

Consistência interna [INFERÊNCIA — leitura da Fig. 3]: se um polo separou em ≈ 19,7 ms (primeiro evento visível), em 24,7–25,3 ms a suportabilidade (E2) valeria 34,7–39 kV, da ordem dos picos máximos observados (38,3–41,4 kV); isso é coerente com a interrupção da escalada quando V_wth ultrapassa a TRV, mas o artigo não informa qual polo separa em que instante.

### 4.3 Critérios de reignição e de interrupção da corrente de alta frequência (Seção IV-B)

(E3) Reignição: "declarada quando a TRV excede a suportabilidade instantânea" — TRV(t) > V_wth(t). [FATO: doc A, p. 3, IV-B]

(E4) Interrupção da corrente de AF pós-reignição: "quando seu di/dt na passagem por zero excede um valor crítico (5 A·µs⁻¹ a 15 A·µs⁻¹) [1], [2]". [FATO: doc A, p. 3, IV-B]

Alerta de consistência [INFERÊNCIA — a verificar em [1] e [2]]: nos modelos fenomenológicos de VCB da literatura (Helmer–Lindmayer [7]; Kondala Rao–Gajjar [2]; Vollet 2007), o interruptor a vácuo **consegue** interromper a corrente de AF na passagem por zero quando |di/dt| é **inferior** à capacidade crítica de extinção, e **falha** quando é superior [LITERATURA: formulação usual; a verificação textual nas refs. [2] e [7] não foi feita nesta sessão — INSERIR CITAÇÃO com página]. A redação do Documento A ("interrupted when its di/dt ... exceeds a critical value") parece invertida em relação a essa convenção; pode ser deslize de redação ou convenção própria de [1]. Deve ser confirmada antes de reutilizar o modelo.

Adicionalmente, o artigo não informa quantas passagens por zero de AF são exigidas antes da extinção (Vollet 2007 fixa 3) nem a frequência típica da corrente de reignição (Vollet 2007: 100–200 kHz) [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, Seções II-B e III-D, URL acima].

### 4.4 Dimensionamento do resistor do snubber

(E5) R_s "dimensionado próximo à impedância de surto do circuito associado, de modo a amortecer reflexões e dissipar a energia transitória (R_s = 30 Ω por fase no presente modelo)". [FATO: doc A, p. 2, III-A]

O valor da impedância de surto do cabo não é informado; infere-se Z_surto ≈ 30 Ω [INFERÊNCIA]. Valores típicos de impedância de surto de cabos de potência situam-se em dezenas de ohms (≈ 30–80 Ω), contra 300–500 Ω para linhas aéreas [LITERATURA: página de referência ScienceDirect Topics "Surge impedance", https://www.sciencedirect.com/topics/engineering/surge-impedance — fonte secundária; confirmar em Greenwood [10] — INSERIR CITAÇÃO com página]. Cabo em questão: 240 mm² (Fig. 2, leitura de figura).

Perda de energia no snubber: E_s = ∫ R_s·i_s²(t) dt durante a condução [INFERÊNCIA FÍSICA: definição de energia dissipada em resistor]; o artigo cita "absorbed energy" como métrica extraível (p. 2, III-B), mas não apresenta nenhum valor de energia nem de corrente no snubber.

### 4.5 Lógica de operação do snubber (Seção III-A, ciclo de quatro estados)

1. Regime permanente: SCRs bloqueados, ramo aberto, sem corrente; "não altera a impedância equivalente nem o fluxo de potência, nem introduz perdas; é transparente à rede". [FATO: doc A, p. 2]
2. Disparo: a tensão sobre o DIAC (diodo bidirecional de ruptura) cresce com a sobretensão; ao atingir o nível de breakover, o DIAC conduz abruptamente e injeta pulso de gate no SCR da polaridade adequada; "o disparo depende apenas das condições elétricas locais, sem comando digital". [FATO: doc A, p. 2]
3. Amortecimento: a corrente flui por R_s, dissipando a energia transitória e reduzindo pico e dv/dt; o casamento com a impedância de surto limita reflexões. [FATO: doc A, p. 2]
4. Bloqueio natural: quando a corrente do ramo decai por zero, os SCRs desligam naturalmente; o ramo reabre sem comando externo. [FATO: doc A, p. 2]

Implementação em ATP/EMTP: chaves antiparalelas controladas por TACS por fase (par de SCR) em série com o resistor, disparadas por "master trigger logic" que emula o breakover do DIAC ("latching at the abrupt voltage rise") e desliga as válvulas na passagem por zero da corrente; controle reflexivo e dinâmica de arco governados por rotinas TACS. [FATO: doc A, p. 3, IV-C] Bloco `snub_ctrl` lê os estados dos disjuntores CBA–CBC e dispara os gates GA–GC. [FATO: doc A, Fig. 1 legenda, p. 2]

Lacuna [INFERÊNCIA]: a legenda da Fig. 1 diz que `snub_ctrl` "lê os estados do disjuntor", enquanto o texto diz que o disparo depende "apenas das condições elétricas locais" (nível de tensão no DIAC). O nível de breakover, a lógica exata de latching e a eventual dependência do estado do disjuntor não são especificados.

### 4.6 Camada digital (Seção III-B) — apenas descrita, não modelada

Após cada evento mitigado, "o registro oscilográfico de alta resolução do transitório é adquirido **apenas durante a condução dos SCR** e passado à camada de proteção digital, que extrai métricas de estresse dielétrico (tensão de pico, dv/dt, energia absorvida, conteúdo espectral) e atualiza um modelo incremental de degradação do isolamento para estimar a vida útil remanescente do ativo [18], [19], [20]." [FATO: doc A, p. 2, III-B] Nenhuma equação, arquitetura, taxa de amostragem ou algoritmo dessa camada é apresentado.

---

## 5. Resultados numéricos

### 5.1 Tabela III do artigo (transcrição integral) — "TRV peak and rate of rise (RRRV) at the VCB"

| Fase | Sem snubber: pico (kV) | Sem snubber: RRRV (kV/µs) | Com snubber: pico (kV) | Com snubber: RRRV (kV/µs) | Evidência |
|---|---|---|---|---|---|
| A | −30,24 | 13,90 | 6,35 | 3,28 | [FATO: doc A, Tabela III, p. 3] |
| B | 41,44 | 15,05 | 13,65 | 13,11 | [FATO: doc A, Tabela III, p. 3] |
| C | −38,30 | 19,00 | −9,98 | 9,43 | [FATO: doc A, Tabela III, p. 3] |
| "Phase B^a" (linha repetida) | 41,44 | 15,05 | 13,65 | 13,11 | [FATO: doc A, Tabela III, p. 3] |

Nota de rodapé "a" da tabela: "A fase B tem o pico mais alto; a RRRV mais alta sem mitigação é a da fase C (19,00 kV·µs⁻¹). Apenas a pior fase (B) é anotada na Fig. 4." [FATO: doc A, Tabela III, p. 3] A quarta linha é uma duplicata da linha B (provável artefato de editoração) [INFERÊNCIA].

Valores confirmados nas caixas de anotação das figuras: Fig. 3 anota A (−30,24 kV; 13,90 kV/µs), B (41,44 kV; 15,05 kV/µs) e C (−38,30 kV; 19,00 kV/µs); Fig. 4 anota apenas B (13,65 kV; 13,11 kV/µs). [FATO: doc A, Figs. 3–4, p. 4 — leitura de figura]

### 5.2 Reduções percentuais por fase — [CÁLCULO PRÓPRIO a partir da Tabela III]

Redução (%) = (|sem| − |com|)/|sem| × 100; razão = |com|/|sem|.

| Fase | Pico sem (kV) | Pico com (kV) | Δpico (kV) | Redução pico (%) | Razão pico | RRRV sem | RRRV com | ΔRRRV | Redução RRRV (%) | Razão RRRV |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 30,24 | 6,35 | 23,89 | **79,0** | 0,210 | 13,90 | 3,28 | 10,62 | **76,4** | 0,236 |
| B | 41,44 | 13,65 | 27,79 | **67,1** | 0,329 | 15,05 | 13,11 | 1,94 | **12,9** | 0,871 |
| C | 38,30 | 9,98 | 28,32 | **73,9** | 0,261 | 19,00 | 9,43 | 9,57 | **50,4** | 0,496 |

- O "about 67 %" do artigo [FATO: doc A, p. 1 e p. 3] corresponde a 67,06 % [CÁLCULO PRÓPRIO].
- A redução de RRRV na fase B (a única destacada pelo artigo) é modesta (12,9 %); as fases A e C, não discutidas no texto quanto a RRRV, têm reduções muito maiores (76,4 % e 50,4 %). O artigo afirma reduzir a taxa de subida "de 15,05 para 13,11 kV·µs⁻¹" sem comentar essa assimetria. [CÁLCULO PRÓPRIO + INFERÊNCIA]
- Mudança de polaridade do pico da fase A (−30,24 kV → +6,35 kV) não é comentada pelo artigo. [FATO: doc A, Tabela III, p. 3] + [INFERÊNCIA]

### 5.3 Normalização em pu e tempo de frente equivalente — [CÁLCULO PRÓPRIO]

Base: 1 pu = 3,397 kV (pico da tensão fase-terra de 4,16 kV). Atenção: a grandeza reportada é a "TRV at the VCB" (ver Seção 3.2, ambiguidade nó-terra × através do gap) e não a tensão nos terminais do motor; a normalização é apenas de referência.

| Fase | Pico sem (pu) | Pico com (pu) | t_f sem = pico/RRRV (µs) | t_f com (µs) |
|---|---|---|---|---|
| A | 8,90 | 1,87 | 2,18 | 1,94 |
| B | 12,20 | 4,02 | 2,75 | 1,04 |
| C | 11,28 | 2,94 | 2,02 | 1,06 |

- O tempo de frente equivalente t_f = pico/RRRV supõe frente linear e depende da definição de RRRV, que o artigo não explicita (máxima derivada? pico/tempo-ao-pico?). [INFERÊNCIA]
- Com o snubber, t_f das fases B e C cai para ≈ 1 µs, igual ao passo de integração (1 µs). Logo, as RRRV "com snubber" das fases B e C são derivadas numéricas sobre 1–3 amostras — a resolução temporal do estudo é insuficiente para caracterizar frentes de sub-microssegundo (a IEC 60034-15 define o impulso de frente íngreme com T₁ = 0,2 µs; ver Seção 7). [INFERÊNCIA a partir de Tabela II e Tabela III]

### 5.4 Leitura qualitativa das Figs. 3 e 4 [FATO: doc A, Figs. 3–4, p. 4 — leitura de figura; contagens são INFERÊNCIA visual]

- Fig. 3 (sem snubber): (i) evento menor em ≈ 19,7 ms, com excursões de ≈ ±6 kV nas fases B e C e oscilação amortecida de ≈ 0,5 ms; (ii) surto principal iniciando em ≈ 24,7 ms, com sequência de excursões de amplitude crescente na fase B (da ordem de 18 → 23 → 28 → 37 → 41 kV) num intervalo de ≈ 0,6 ms; (iii) "ringing" de alta frequência decaindo até ≈ 28,5 ms. A sequência crescente é a assinatura visual da escalada por reignições sucessivas. Contagem visual: da ordem de 6 a 10 excursões distinguíveis na fase B; **o número de reignições não é reportado no texto e não pode ser determinado com confiabilidade a partir da figura impressa**.
- Fig. 4 (com snubber): (i) o evento de ≈ 19,7 ms permanece com excursões de ≈ −6 kV (B) e +5 kV (C), semelhantes às da Fig. 3 — sugerindo que o snubber não atuou nesse primeiro evento (nível de breakover não informado) [INFERÊNCIA]; (ii) em ≈ 24,7 ms, pico único de 13,65 kV na fase B seguido de patamar de ≈ 8 kV decaindo em ≈ 2 ms, e excursão de −10 kV na fase C seguida de decaimento — forma compatível com dissipação em R_s [INFERÊNCIA]; (iii) ausência do "ringing" prolongado da Fig. 3; (iv) a excursão de 6,35 kV da fase A (Tabela III) não é discernível na figura reproduzida, possivelmente sobreposta [INFERÊNCIA].
- O artigo afirma que "a subida abrupta de tensão dispara os SCR dentro de um microssegundo da anomalia" [FATO: doc A, p. 3, V-B] — igual ao passo de integração; o atraso de disparo está no limite de resolução do modelo [INFERÊNCIA].

### 5.5 O que NÃO é reportado numericamente [FATO por omissão, verificado em todo o texto]

Corrente no snubber; energia dissipada em R_s; duração da condução dos SCR; número de reignições por polo; instantes de separação por polo; tensões nos terminais do motor (sonda 01AT); tensões entre espiras; espectro de frequência; sensibilidade a R_s, ao nível de breakover, ao comprimento do cabo, a I_ch, a A/B ou ao di/dt crítico; cenário de abertura em regime (corrente nominal) ou de fechamento (pre-strike); comparação numérica com ZnO ou RC.

---

## 6. Mecanismos físicos invocados e referências de suporte

### 6.1 Chopping de corrente e transferência de energia L → C
- Afirmação: o arco a vácuo instável colapsa abruptamente numa corrente de chopping de "poucos ampères"; a energia ½·L·I_ch² é transferida à capacitância do lado da carga, excitando oscilações de AF cujo primeiro pico "pode atingir várias vezes a tensão de pico do sistema". [FATO: doc A, p. 2, II-A] Suporte citado: [5] Abdulahovic et al. 2017; [10] Greenwood 1991; na Introdução, [1]–[4] para chopping e reignições múltiplas e [10], [11] para a transferência magnética→capacitiva. [FATO: doc A, p. 1]
- Faixa de chopping usada (1–2 A) é inferior à faixa "tipicamente 2 a 10 A" citada por Vollet 2007 e aos 5 ou 8 A ali simulados [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, Seções II-A e III-D, URL na Seção 4.1]. [INFERÊNCIA]: o Documento A não é conservador no chopping, mas o é na recuperação dielétrica (Seção 4.2).

### 6.2 Reignições sucessivas e escalada de tensão
- Afirmação: se a TRV excede a suportabilidade em recuperação, o gap rompe (reignição) "e o ciclo se repete, gerando uma rajada (burst) de escaladas de tensão de frente íngreme"; "acúmulo determinístico" investigado em [1], [4], [7]. [FATO: doc A, p. 2, II-A] Na Introdução: "a rápida recuperação do gap favorece múltiplas reignições [1]–[4]". [FATO: doc A, p. 1]
- Suporte externo verificado: "This sequence of events may be repeated several times (up to 10) with increasing amplitude. The process will stop only when the breaker gap strength reaches a value higher than the TRV." [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, Seção II-B, https://www.ipstconf.org/papers/Proc_IPST2007/07IPST106.pdf]. Também: reignições múltiplas e escalada de tensão em disjuntores a vácuo de gerador durante rejeição de carga [LITERATURA: Glinkowski, Gutierrez e Braun, IEEE Trans. Power Del., v. 12, n. 1, 1997, DOI 10.1109/61.568244, https://www.osti.gov/biblio/477204 — resumo verificado, sem contagem numérica].

### 6.3 Natureza determinística/caótica da reignição
- Afirmação: "modelos de arco tradicionais tratam a reignição como evento puramente probabilístico, ignorando sua natureza determinística e caótica [8], [9]". [FATO: doc A, p. 1] As refs. [8] (Tseng et al., Cassie–Mayr híbrido) e [9] (Bizjak et al., Mayr/Cassie) são modelos de arco por equações diferenciais; o artigo as usa como contraponto, não as implementa (o VCB é fenomenológico, com ramo RARC/LARC/CARC comutado). [INFERÊNCIA a partir de p. 1, p. 3 e Fig. 2]

### 6.4 Efeito de onda viajante e concentração nas primeiras espiras
- Afirmação: "por efeitos de onda viajante ao longo dos enrolamentos, uma grande fração dessa tensão aparece através das primeiras poucas espiras [1], [6]"; na Introdução, "a distribuição não linear de tensão concentra o estresse nas espiras de extremidade de linha ... [6], [14]". [FATO: doc A, p. 2, II-B; p. 1]
- Observação sobre o suporte [INFERÊNCIA]: a ref. [6] (Bak et al. 2018) é um artigo de modelagem de VCB para avaliação de TRV em redes; a ref. [14] (Vollet e de Metz Noblat 2007) trata da proteção de motores de AT contra sobretensões de manobra. O suporte específico para a distribuição de tensão entre espiras (modelos de enrolamento a parâmetros distribuídos) não é oferecido pelo artigo — [INSERIR CITAÇÃO: modelo de distribuição de tensão de impulso em enrolamentos de máquinas; p. ex., trabalhos clássicos sobre "turn-to-turn voltage distribution under steep-front surges"].
- Suporte normativo verificado para o princípio físico: "quando um surto de tensão de tempo de subida curto ocorre entre um terminal da máquina e a terra, a fase correspondente não pode adotar instantaneamente o mesmo potencial em todos os pontos ... surgem tensão transversal (condutor–terra) e longitudinal (ao longo do condutor) ... a longitudinal também solicita o isolamento entre espiras. As componentes mais altas de ambas normalmente aparecem na primeira ou na última bobina do enrolamento. Na prática, os surtos ... podem ter tempos de subida até 0,1 µs." [NORMA: IEC 60034-15:2009, Anexo A.1 (informativo); preview verificado em https://cdn.standards.iteh.ai/samples/15848/1b914cc7cb9b4c4582e502f946666007/IEC-60034-15-2009.pdf]
- Modelagem no artigo: o motor é um ramo R–L concentrado (Fig. 2); portanto, o efeito de onda viajante **no enrolamento** não é simulado — é invocado apenas como argumento. [FATO: doc A, Fig. 2, p. 4 — leitura de figura] + [INFERÊNCIA]

### 6.5 Treeing elétrico e "fadiga silenciosa"
- Afirmação: "o estresse SFI repetitivo é o mecanismo condutor do treeing elétrico e da fadiga lenta e 'silenciosa' do isolamento entre espiras, que a IEC 60034-15 aborda através de níveis de suportabilidade a impulso para bobinas pré-formadas". [FATO: doc A, p. 2, II-B] Na Introdução: "sob excitação repetitiva, inicia e propaga treeing elétrico, levando a falha prematura do isolamento [6], [14]". [FATO: doc A, p. 1] Na Discussão: a atenuação do pico "alivia diretamente o 'bombardeio' dielétrico das primeiras espiras do estator, mitigando o mecanismo de fadiga por treeing elétrico". [FATO: doc A, p. 4, V-C]
- Suporte [INFERÊNCIA]: nenhuma referência de física de dielétricos (iniciação/propagação de treeing, curvas de vida sob impulsos repetitivos, modelo de potência inversa) é citada; o vínculo entre número/amplitude de impulsos e dano é qualitativo. [INSERIR CITAÇÃO: literatura de envelhecimento de isolamento de máquinas sob impulsos repetitivos / treeing elétrico].
- Termo "fadiga silenciosa": expressão do artigo, sem definição operacional (não há indicador mensurável associado). [FATO: doc A, p. 2] + [INFERÊNCIA]

### 6.6 Evidência de campo (falhas de isolamento em motores de MT de óleo e gás)
- "Levantamentos de campo confirmam que falhas relacionadas ao isolamento são causa principal de paradas de motores de MT na indústria de óleo e gás [12], [13]." [FATO: doc A, p. 1] Refs. [12] e [13]: Thorsen e Dalva, PCIC 1994 e IEEE Trans. Ind. Appl. 1999. Nenhum número dos levantamentos é transcrito pelo artigo. [FATO por omissão]

### 6.7 Estado da premissa do usuário "5 a 7 reignições por ciclo"
- **Não consta do Documento A.** O artigo usa apenas "successive arc reignitions" (p. 1), "multiple reignitions" (p. 1), "burst of steep front voltage escalations" (p. 2) e "the successive reignitions escalate the TRV" (p. 3). [FATO: doc A, p. 1–3]
- Literatura verificada: "várias vezes (até 10)" por sequência de interrupção [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, URL na Seção 4.1]. A faixa 5–7 está contida em "até 10", mas não é afirmada por essa fonte.
- Leitura visual da Fig. 3: da ordem de 6–10 excursões crescentes na fase B no surto principal — compatível, porém não confiável (Seção 5.4). [INFERÊNCIA visual]
- A unidade "por ciclo" precisa de definição: por semiciclo de 60 Hz, por polo, por manobra? O Documento A não oferece base para fixar a unidade. [HIPÓTESE do usuário — manter rotulada; INSERIR CITAÇÃO com medições de campo/laboratório de contagem de reignições, p. ex. trabalhos de Popov e van der Sluis sobre modelos de VCB, não verificados nesta sessão]

### 6.8 Argumento contra ZnO e RC/RLC fixos (item (e) da tarefa)
- "Para-raios de óxido metálico (ZnO) grampeiam o pico de tensão, mas têm efeito limitado sobre dv/dt; supressores RC ou RLC fixos reduzem dv/dt, mas são permanentemente conectados, de modo que modificam a impedância da rede, introduzem perdas contínuas, podem agravar o chopping e, criticamente para plantas ciberfísicas modernas, mascaram o espectro na faixa de MHz necessário para monitoramento de condição e rastreabilidade de eventos [14], [15], [16]." [FATO: doc A, p. 1]
- Repetido na Discussão: o ramo aberto em regime "não altera a impedância da rede nem mascara o conteúdo de alta frequência do transitório, de modo que o mesmo evento que está sendo mitigado pode também ser registrado e usado para estimativa de saúde do ativo". [FATO: doc A, p. 3–4, V-C]
- Suporte externo verificado que corrobora parte do argumento sobre ZnO: com para-raios apenas no terminal de carga do VCB, "devido às reflexões de onda no cabo, a sobretensão no terminal do motor" não fica limitada; "os para-raios não limitam as reignições múltiplas"; supressores C–R corretamente dimensionados "eliminam reignições múltiplas e a escalada de tensão" [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, Seção V-B e Conclusões, URL na Seção 4.1]. Observação [INFERÊNCIA]: essa mesma fonte (correlata da ref. [14] do artigo) conclui **a favor** dos supressores RC fixos; o Documento A não confronta essa conclusão, apenas reposiciona a objeção para o plano das perdas, da impedância e do mascaramento espectral.
- O artigo **não** quantifica: perdas de um RC típico; alteração de impedância; "agravamento do chopping" por RC; atenuação espectral causada por RC/ZnO; nem simula ZnO/RC no mesmo circuito para comparação. [FATO por omissão]
- Tensão interna [INFERÊNCIA]: o argumento do "espectro em MHz" convive com um modelo de passo 1 µs (frequência de Nyquist 500 kHz), incapaz de representar o conteúdo em MHz que se afirma preservar.

---

## 7. Normas citadas e como são usadas

| Norma | Como o artigo a cita | Uso efetivo | Evidência |
|---|---|---|---|
| IEC 60034-15:2025, *Rotating Electrical Machines — Part 15: Impulse Voltage Withstand Levels of Form-Wound Stator Coils* (ref. [21]) | "framed against the steep front impulse (SFI) withstand philosophy of IEC 60034-15" (p. 2); "which the IEC 60034-15 standard addresses through impulse withstand levels for form wound stator coils" (p. 2); "supporting compliance with the SFI withstand philosophy of IEC 60034-15" (p. 4) | Apenas enquadramento retórico. Nenhum nível de suportabilidade (U_P, U'_P), nenhuma forma de onda normalizada (1,2/50 µs; 0,2 µs) e nenhuma comparação numérica resultado × envelope são apresentados. A palavra "compliance" é usada sem demonstração. | [FATO: doc A, p. 2 e p. 4] |
| IEC 60071-1:2019, *Insulation Co-ordination — Part 1: Definitions, Principles and Rules* (ref. [22]) | "the insulation coordination rules of IEC 60071-1" (p. 2); "the insulation coordination limits of IEC 60071-1" (p. 4) | Apenas enquadramento. Nenhum procedimento de coordenação (tensões representativas, fatores de coordenação/segurança, níveis de suportabilidade normalizados) é aplicado; nenhum BIL do motor ou do painel é definido. | [FATO: doc A, p. 2 e p. 4] |

Conteúdo normativo verificado nesta sessão, para uso do orquestrador (não usado pelo artigo):

- [NORMA: IEC 60034-15:2009 (Ed. 3.0), Cláusula 3 e Tabela 1, Notas 1–5; preview verificado em https://cdn.standards.iteh.ai/samples/15848/1b914cc7cb9b4c4582e502f946666007/IEC-60034-15-2009.pdf]:
  - U_P = 4·U_N + 5 kV (pico) para impulso atmosférico normalizado 1,2 µs ± 30 % / 50 µs ± 20 % (isolamento principal);
  - U'_P = 0,65·U_P para impulso de frente íngreme com tempo de frente 0,2 ± 0,1 µs até 35 kV (isolamento entre espiras);
  - Nota 5: os níveis da coluna 3 "foram considerados apropriados para solicitações relacionadas à operação de disjuntores que podem ocorrer em serviço. Podem não ser adequados para condições operacionais especiais (p. ex. **partida interrompida** ou conexão direta a linhas aéreas). Nesses casos, os enrolamentos devem ser projetados para suportar outros níveis de impulso ou protegidos de forma apropriada." Redação original reconferida nesta sessão no preview iTeh: "They may not be adequate for special operating conditions (e.g. interrupted start or direct connection to overhead lines). In such cases the windings should either be designed to withstand other impulse levels or be protected in an appropriate way." — a Nota é uma ressalva ("may not be adequate"), não uma exclusão formal do caso.
  - Cláusula 4.2: o ensaio entre espiras usa descarga oscilatória amortecida de capacitor, com **no mínimo cinco** operações de chaveamento; frente do primeiro pico 0,2 ± 0,1 µs.
  - Anexo A.2: U'_P = 0,65·(4·U_N + 5) kV.
  - Tabela 1 não lista 4,16 kV; valores vizinhos: U_N = 4 kV → U_P = 21 kV, U'_P = 14 kV.
- Existência da edição citada pelo artigo: IEC 60034-15 Ed. 4.0, 2025-06 [LITERATURA: catálogo iTeh, https://www.standards.iteh.ai/catalog/standards/clc/69d2f9f4-d3cd-43e7-9376-db4406810959/en-iec-60034-15-2025 — apenas a existência foi verificada; **não foi verificado se as fórmulas da Ed. 3.0 foram mantidas na Ed. 4.0**].
- [CÁLCULO PRÓPRIO com a Ed. 3.0, a confirmar na Ed. 4.0]: para U_N = 4,16 kV, U_P = 21,64 kV e U'_P = 14,07 kV. Confronto com a Tabela III do artigo (com a ressalva de que a grandeza reportada é a TRV no VCB, e não a tensão nos terminais do motor): sem snubber, os picos de 30,2–41,4 kV excedem U_P (21,64 kV) e U'_P (14,07 kV) em todas as fases; com snubber, o pico da fase B (13,65 kV) fica a 97 % de U'_P e a 63 % de U_P, com frente equivalente ≈ 1 µs (mais lenta que 0,2 µs), e as fases A e C ficam bem abaixo. Esse confronto **não é feito pelo artigo** e deve ser refeito com a tensão no terminal do motor (sonda 01AT da Fig. 2) e com a Ed. 4.0 da norma.
- Relevância direta da Nota 5 [INFERÊNCIA]: o cenário estudado pelo artigo ("intempestive interruption of a motor start", p. 3) corresponde, na interpretação deste fichamento, ao exemplo "interrupted start" da Nota 5 — equivalência de termos não afirmada pelo artigo nem definida pela norma no trecho consultado. Sob essa interpretação, o caso simulado é justamente aquele para o qual a norma admite que os níveis-padrão "podem não ser adequados", o que reforça a necessidade de proteção — mas também indica que "compliance with the SFI withstand philosophy" (p. 4) não pode ser reivindicada apenas pelo atendimento a U'_P. A permanência da Nota 5 na Ed. 4.0 (2025), citada pelo artigo, não foi verificada.
- IEC 60071-1:2019 [NORMA: escopo — definições, princípios e regras de coordenação de isolamento para redes > 1 kV; cláusulas não verificadas nesta sessão]: o artigo não a aplica.
- Norma mencionada em Vollet 2007 para motores: recomendação IEEE de suportabilidade a impulso de motores [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, ref. [5] daquele artigo, não identificada aqui — INSERIR CITAÇÃO]; o Documento A não cita nenhuma norma IEEE (p. ex., IEEE Std C37.011 para TRV, IEEE Std 522 para ensaios de impulso entre espiras) [FATO por omissão; existência dessas normas: conhecimento geral, não verificado nesta sessão].

---

## 8. O que o artigo NÃO afirma / NÃO modela (lista explícita — base da regra "zero suposição")

Cada item abaixo foi verificado por leitura integral do texto (p. 1–5) e das Figs. 1–4.

**Sobre o disjuntor e o fenômeno**
1. Não quantifica o número de reignições por manobra, por polo ou "por ciclo" — em nenhuma parte do texto. A expressão "5 a 7 eventos por ciclo" não aparece.
2. Não informa a frequência da corrente de reignição nem a frequência de oscilação da TRV.
3. Não informa os instantes de separação de cada polo nem qual polo interrompe primeiro.
4. Não apresenta a origem experimental das constantes A e B da RRDS (remete a [1] e [7]).
5. Não define a grandeza "RRRV" (máxima derivada, derivada média até o pico, ou outra).
6. Não esclarece se a "TRV at the VCB" é tensão através do gap ou tensão nó-terra no lado de carga (a Fig. 2 sugere sonda de nó).
7. Não modela o arco por equações de Cassie/Mayr (cita-as apenas como contraponto); os valores de RARC, LARC, CARC não são dados.
8. Não considera manobras de fechamento (pre-strike), abertura em carga nominal, abertura a vazio nem chopping virtual (acoplamento capacitivo entre fases).

**Sobre o motor e o isolamento**
9. Não modela o isolamento do motor: não há modelo de enrolamento a parâmetros distribuídos, capacitâncias entre espiras/para a terra, nem distribuição de tensão de impulso ao longo da bobina. O motor é um ramo R–L série concentrado (Fig. 2).
10. Não reporta a tensão nos terminais do motor (embora exista sonda 01AT na Fig. 2) nem a tensão entre espiras.
11. Não define o BIL do motor, nem U_P/U'_P da IEC 60034-15, nem compara os resultados a qualquer envelope normativo.
12. Não menciona a classe térmica, o sistema de isolamento (mica/epóxi, VPI, resin-rich), a idade, o histórico de manobras nem o estado do isolamento do motor.
13. Não modela nem menciona descargas parciais, fator de dissipação, resistência de isolamento, índice de polarização, corrente de fuga ou qualquer indicador dielétrico mensurável.
14. Não apresenta modelo de treeing, curva de vida (p. ex., lei de potência inversa), limiar de iniciação nem qualquer relação quantitativa entre pico/dv/dt/energia e dano.

**Sobre RUL e a camada digital**
15. Não calcula RUL, não define horizonte de prognóstico, não define critério de fim de vida nem incerteza.
16. Não apresenta o "modelo incremental de degradação" (nenhuma equação, variável de estado, taxa de amostragem, algoritmo, dado de treinamento ou validação).
17. Não especifica como as quatro métricas (pico, dv/dt, energia absorvida, conteúdo espectral) são calculadas, normalizadas ou combinadas.
18. Não explica como a aquisição "apenas durante a condução dos SCR" trata eventos em que o snubber não dispara (p. ex., o evento de ≈ 19,7 ms nas Figs. 3–4) nem como registra a parcela do transitório anterior ao disparo.
19. Não relaciona as refs. [18]–[20] (gêmeo digital) a nenhum método concreto para máquinas de MT.

**Sobre o snubber**
20. Não informa o nível de breakover do DIAC, o atraso de disparo real, a corrente de gate, as especificações dos SCR (tensão, corrente, di/dt, dv/dt suportáveis), a energia/potência do resistor nem a estratégia de proteção do próprio snubber.
21. Não apresenta sensibilidade a R_s, ao ponto de conexão (painel × terminais do motor), ao comprimento do cabo ou aos parâmetros do VCB.
22. Não simula ZnO nem RC/RLC no mesmo circuito; a superioridade sobre eles é argumentativa.
23. Não quantifica "perdas contínuas", "alteração de impedância" ou "mascaramento espectral" dos dispositivos passivos.
24. Não trata o comportamento do snubber em faltas, em regime com harmônicos, em sobretensões temporárias de 60 Hz, nem o risco de disparo espúrio.

**Sobre validação e escopo**
25. Não valida experimentalmente (declara bancada e HIL como próximos passos).
26. Não apresenta comparação com medições de campo nem com os resultados originais de [1] (apenas diz que os estende).
27. Não apresenta análise estatística (Monte Carlo de instantes de abertura, dispersão de I_ch, etc.).
28. Não menciona o número de motores, a topologia N-1 ou o load shedding do Documento B; os dois documentos são independentes no texto.
29. Não associa nenhum número à vida útil remanescente: a expressão "remaining useful life" ocorre uma única vez, por extenso, na p. 2 (Seção III-B), como finalidade da camada digital; a sigla "RUL" não aparece em nenhuma parte do texto (verificado por busca no texto integral, p. 1–5). Entre os termos de indexação consta apenas "insulation life" (p. 1). [FATO: doc A, p. 1–2; FATO por omissão]

---

## 9. Limitações

### 9.1 Declaradas pelo artigo
- Validação apenas computacional (ATP/EMTP); validação experimental em bancada de 4,16 kV "é o próximo passo e está atualmente em estudo". [FATO: doc A, p. 1 resumo; p. 4 conclusão]
- A camada de proteção digital "está além do escopo deste trabalho". [FATO: doc A, p. 2, III-B]
- Pendências de hardware listadas: resistor de alta energia, válvulas SCR, gate drivers com alta imunidade a ruído, integração com a camada digital, bancada de MT [24] e HIL na classe 4,16 kV. [FATO: doc A, p. 4, conclusão]

### 9.2 Inferidas neste fichamento (rotuladas)
- [INFERÊNCIA] Passo de 1 µs limita a representação de frentes de 0,2 µs (norma) e do "espectro em MHz" (argumento central); as RRRV com snubber nas fases B e C equivalem a 1 amostra de frente.
- [INFERÊNCIA] O motor R–L concentrado impede qualquer conclusão sobre a tensão nas "primeiras espiras", que é o mecanismo de dano alegado.
- [INFERÊNCIA a partir de leitura de figura] Na Fig. 2, os ramos do snubber partem do nó do lado de carga do VCB, antes do bloco LCC de 240 mm² que leva ao motor equivalente (Seção 3.2), enquanto o texto afirma que o ramo é "connected in parallel with the machine terminals" (p. 2). Se a leitura da figura estiver correta, a proteção está no lado do painel; a literatura correlata mostra que proteção no lado do painel pode não limitar a tensão no terminal do motor devido a reflexões no cabo [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, Seção V-B, URL na Seção 4.1]. O artigo não reporta a tensão no terminal do motor (sonda 01AT) nem esclarece a discrepância entre texto e figura.
- [INFERÊNCIA] Possível inversão de sentido no critério de di/dt crítico (Seção 4.3).
- [INFERÊNCIA] Aparente inconsistência entre Ip/In = 6,5 (Tabela I) e |Z_eq| = 3,455 Ω (Fig. 2), que corresponde a ≈ 3,35·In (Seção 3.1).
- [INFERÊNCIA] Assimetria de mitigação de RRRV entre fases (12,9 % em B contra 76,4 % em A) não discutida; a alegação de "reduz dv/dt" apoia-se na fase em que a redução é menor.
- [INFERÊNCIA] Cenário único (uma abertura, um conjunto de instantes); ausência de análise estatística impede afirmar que 41,44 kV seja o máximo ou que 13,65 kV seja o máximo residual.
- [INFERÊNCIA] Recuperação dielétrica (E2) muito mais lenta que os 20–40 kV/ms de Vollet 2007 no primeiro milissegundo; a severidade do caso-base depende fortemente dessa escolha.
- [INFERÊNCIA] "Compliance" com IEC 60034-15 e "limits" de IEC 60071-1 são reivindicados sem nenhum número normativo. Além disso, a Nota 5 da Tabela 1 da IEC 60034-15:2009 adverte que os níveis da coluna 3 (U'_P) "podem não ser adequados" ("may not be adequate") para condições operacionais especiais e cita nominalmente a "partida interrompida" ("interrupted start") como exemplo — ressalva, não exclusão formal [NORMA: IEC 60034-15:2009, Tabela 1, Nota 5 — preview iTeh reconferido nesta sessão, URL na Seção 7]. A equivalência entre "interrupted start" da norma e a "intempestive interruption of a motor start" do artigo é interpretação deste fichamento [INFERÊNCIA]; a permanência da Nota na Ed. 4.0 (2025) não foi verificada.
- [INFERÊNCIA] A lista de referências mistura suporte técnico direto ([1]–[7], [10], [11]) com referências genéricas de gêmeo digital ([18]–[20], uma delas sobre motores de veículos elétricos) que não sustentam um modelo de degradação de isolamento de MT.

---

## 10. Ganchos para RUL e monitoramento de isolamento

### 10.1 O que o artigo já sugere textualmente

| Gancho | Texto do artigo | Evidência |
|---|---|---|
| Dano cumulativo por manobras | TRVs "com frentes íngremes (alto dv/dt) que impulsionam a degradação cumulativa do isolamento do estator" | [FATO: doc A, p. 1, resumo] |
| Rastreamento de saúde a partir de transitórios registrados | camada digital = "agente de decisão que opera em frequência industrial para aconselhar decisões de manobra e rastrear a saúde do ativo a partir dos transitórios registrados" | [FATO: doc A, p. 1, Introdução] |
| Aquisição condicionada ao evento | "registro oscilográfico de alta resolução do transitório é adquirido apenas durante a condução dos SCR" | [FATO: doc A, p. 2, III-B] |
| Conjunto de features | "métricas de estresse dielétrico (tensão de pico, dv/dt, energia absorvida, conteúdo espectral)" | [FATO: doc A, p. 2, III-B] |
| Modelo de degradação incremental → RUL | "atualiza um modelo incremental de degradação do isolamento para estimar a vida útil remanescente do ativo [18], [19], [20]" | [FATO: doc A, p. 2, III-B] |
| Preservação da assinatura de AF como requisito de projeto | ramo aberto em regime "preserva ... a assinatura de alta frequência requerida para diagnóstico"; "o mesmo evento que está sendo mitigado pode também ser registrado e usado para estimativa de saúde do ativo" | [FATO: doc A, p. 2, III-A; p. 3–4, V-C] |
| Rastreabilidade de eventos | dispositivos passivos "mascaram o espectro na faixa de MHz necessário para monitoramento de condição e rastreabilidade de eventos" | [FATO: doc A, p. 1] |
| Mecanismo-alvo | "'bombardeio' dielétrico das primeiras espiras", "fadiga por treeing elétrico", "fadiga silenciosa do isolamento entre espiras" | [FATO: doc A, p. 2, II-B; p. 4, V-C] |
| Base experimental futura | bancada de MT para monitoramento preditivo de motor offshore [24]; HIL na classe 4,16 kV | [FATO: doc A, p. 4, conclusão] |
| Decisão de manobra assistida | a camada digital "aconselha decisões de manobra" (ponto de contato natural com o Documento B, não explicitado pelo artigo) | [FATO: doc A, p. 1] + [INFERÊNCIA quanto ao vínculo com B] |

### 10.2 Variáveis numéricas do artigo reutilizáveis como entrada de um módulo de RUL

- Por evento e por fase: pico (kV), RRRV (kV/µs), com e sem mitigação (Tabela III, p. 3) — apenas um evento simulado.
- Parâmetros do gerador de estresse (VCB): I_ch, A, B, di/dt crítico, stagger (Tabela II, p. 3).
- Parâmetros do "atenuador" (snubber): R_s = 30 Ω (Tabela II, p. 3).
- Motor: 1250 kW, 4,16 kV, Ip/In = 6,5 (Tabela I, p. 3); L_eq = 8,98 mH, R_eq = 0,691 Ω (Fig. 2, leitura de figura).
- Derivados neste fichamento [CÁLCULO PRÓPRIO]: In ≈ 207,5 A; Ip ≈ 1,35 kA; picos em pu (8,90/12,20/11,28 sem; 1,87/4,02/2,94 com); frentes equivalentes 2,0–2,8 µs sem, 1,0–1,9 µs com; reduções 67–79 % (pico) e 13–76 % (RRRV).

### 10.3 Lacunas que um módulo de RUL precisa fechar (não fornecidas pelo artigo)

- [HIPÓTESE de projeto] Função de transferência do estresse: TRV no VCB → tensão no terminal do motor → tensão entre espiras da primeira bobina. Exige modelo de cabo + enrolamento a parâmetros distribuídos; o artigo só fornece o primeiro elo e, segundo a leitura da Fig. 2 (Seção 3.2), medido no lado do painel (barramento do VCB), não no terminal do motor.
- [HIPÓTESE de projeto] Lei de dano: relação entre (pico, dv/dt, energia, número de eventos) e consumo de vida do isolamento entre espiras. O artigo não fornece; a IEC 60034-15 fornece apenas níveis de suportabilidade de projeto (U'_P para frente de 0,2 µs, ensaio com ≥ 5 impulsos) [NORMA: IEC 60034-15:2009, Tabela 1 e cl. 4.2], não uma curva de vida. [INSERIR CITAÇÃO: modelos de vida sob impulsos repetitivos].
- [HIPÓTESE de projeto] Contador de eventos: o número de reignições por manobra é a variável de dose mais elementar e não é reportado; um módulo de RUL deve extraí-lo do oscilograma (contagem de frentes acima de um limiar), não assumi-lo (a premissa "5–7" deve ser tratada como hipótese a medir).
- [HIPÓTESE de projeto] Ponto de medição e largura de banda: a aquisição "durante a condução dos SCR" precisa de taxa de amostragem ≥ dezenas de MS/s para frentes de 0,2 µs; o artigo não define.
- Cruzamento com o corpus de apoio [FATO: fichamento 02 do corpus, Jensen, Strangas e Foster 2018]: o pico da corrente de fuga transitória depende do dV/dt aplicado, e o dV/dt do dispositivo de comutação é assumido constante para que o indicador reflita o isolamento — o que implica que, num esquema com snubber, a variação de dv/dt introduzida pela própria mitigação deve ser registrada e compensada antes de usar indicadores de resposta ao impulso como precursor de degradação. [INFERÊNCIA a partir do corpus; ver `/tmp/claude-0/-home-user-olivas-power-system-studio/9d851478-5457-5818-8269-a836133b8dbc/scratchpad/out/fichamentos/02_jensen2018_stator_insulation_ekf.md`]

---

## 11. Referências do artigo (24) e sua função no argumento

| Nº | Referência (como listada, p. 4–5) | Função no argumento do Documento A | Onde é citada |
|---|---|---|---|
| [1] | L. F. Silva, "Investigation of the switching overvoltage caused by arc reignition in 4.16 kV vacuum circuit breakers" (em português), dissertação de mestrado, PPGEL, CEFET-MG, Belo Horizonte, 2026 | Base direta: modelo fenomenológico de VCB (chopping, RRDS parabólica, reignição AF via TACS/MODELS), estudo de caso de 4,16 kV, parâmetros de Tabela II; efeito de onda viajante nas primeiras espiras | p. 1 (Introdução, contribuições), p. 2 (II-A, II-B, IV), p. 3 (IV-B, três vezes) |
| [2] | B. Kondala Rao e G. Gajjar, "Development and application of vacuum circuit breaker model in electromagnetic transient simulation", IEEE Power India Conf., 2006, DOI 10.1109/POWERI.2006.1632503 | Modelo de VCB em EMTP; suporte ao critério de di/dt crítico (5–15 A/µs) | p. 1; p. 3 (IV-B) |
| [3] | R. B. Shores e V. E. Phillips, "High voltage vacuum circuit breakers", IEEE Trans. Power App. Syst., v. 94, n. 5, p. 1821–1830, 1975, DOI 10.1109/T-PAS.1975.32027 | Referência histórica sobre chopping e reignições em VCB | p. 1 |
| [4] | S. M. Wong, L. A. Snider e E. W. C. Lo, "Overvoltages and reignition behavior of vacuum circuit breaker", APSCOM 2003, p. 653–658, DOI 10.1049/cp:20030663 | Comportamento de reignição e sobretensões; acúmulo determinístico em disjuntores de 4,16 kV | p. 1; p. 2 (II-A) |
| [5] | T. Abdulahovic, T. Thiringer, M. Reza e H. Breder, "Vacuum circuit-breaker parameter calculation and modelling for power system transient studies", IEEE Trans. Power Del., v. 32, n. 3, p. 1165–1172, 2017, DOI 10.1109/TPWRD.2014.2357993 | Parâmetros de VCB; uso de VCB em redes industriais isoladas; nível de chopping 1–2 A; oscilação L→C | p. 1; p. 2 (II-A); p. 3 (IV-B) |
| [6] | C. L. Bak et al., "Vacuum circuit breaker modelling for the assessment of transient recovery voltages: Application to various network configurations", Electric Power Syst. Res., v. 156, p. 35–43, 2018, DOI 10.1016/j.epsr.2017.11.010 | Citado para concentração de estresse nas espiras de extremidade, treeing e onda viajante (embora seja artigo de modelagem de VCB/TRV) | p. 1; p. 2 (II-B) |
| [7] | J. Helmer e M. Lindmayer, "Mathematical modeling of the high frequency behavior of vacuum interrupters and comparison with measured transients in power systems", ISDEIV 1996, p. 323–331, DOI 10.1109/DEIV.1996.545375 | Modelo de AF de interruptores a vácuo; lei RRDS parabólica; acúmulo determinístico | p. 2 (II-A); p. 3 (IV-B) |
| [8] | K.-J. Tseng, Y. Wang e D. M. Vilathgamuwa, "An experimentally verified hybrid Cassie-Mayr electric arc model for power electronics simulations", IEEE Trans. Power Electron., v. 12, n. 3, p. 429–436, 1997, DOI 10.1109/63.575670 | Contraponto: modelos de arco "tradicionais" que tratam reignição como probabilística (segundo o artigo) | p. 1 |
| [9] | G. Bizjak, P. Zunko e D. Povh, "Circuit breaker model for digital simulation based on Mayr's and Cassie's differential arc equations", IEEE Trans. Power Del., v. 10, n. 3, p. 1310–1315, 1995, DOI 10.1109/61.400910 | Idem [8] | p. 1 |
| [10] | A. Greenwood, *Electrical Transients in Power Systems*, 2. ed., Wiley, 1991 | Teoria de transitórios: transferência de energia magnética→capacitiva, TRV com picos altos e frentes íngremes; chopping | p. 1; p. 2 (II-A) |
| [11] | L. van der Sluis, *Transients in Power Systems*, Wiley, 2001 | Idem [10] (TRV) | p. 1 |
| [12] | O. V. Thorsen e M. Dalva, "A survey of faults on induction motors in offshore oil industry, petrochemical industry, gas terminals and oil refineries", IEEE PCIC 1994, DOI 10.1109/PCICON.1994.347637 | Evidência de campo: falhas de isolamento como causa principal de paradas em óleo e gás; uso de VCB em plantas críticas | p. 1 (duas vezes) |
| [13] | O. V. Thorsen e M. Dalva, "Failure identification and analysis for high-voltage induction motors in the petrochemical industry", IEEE Trans. Ind. Appl., v. 35, n. 4, p. 810–818, 1999, DOI 10.1109/28.777188 | Idem [12] | p. 1 (duas vezes) |
| [14] | C. Vollet e B. de Metz Noblat, "Protecting high-voltage motors against switching overvoltages", 4th European Conf. Electrical and Instrumentation Applications in the Petroleum & Chemical Industry (PCIC Europe), 2007, DOI 10.1109/PCICEUROPE.2007.4354001 | Treeing/estresse nas espiras de extremidade; limitações de ZnO e RC. (A versão IPST 2007 dos mesmos autores, verificada nesta sessão, conclui a favor de supressores C–R e cita "até 10" reignições.) | p. 1 (duas vezes) |
| [15] | K. Samaras, C. Sandberg, C. J. Salmas e A. Koulaxouzidis, "Electrical surge protection devices for industrial facilities: a tutorial review", 52nd IEEE PCIC, 2005, p. 165–175, DOI 10.1109/PCICON.2005.1524552 | Revisão de dispositivos de proteção contra surtos: limitações de ZnO/RC | p. 1 |
| [16] | S. W. Nene et al., "Mitigation of transients in capacitor coupled substations using traditional RLC filter techniques", J. Power and Energy Eng., v. 12, 2024 | Filtros RLC tradicionais (permanentemente conectados) como contraponto | p. 1 |
| [17] | J. A. Martínez-Velasco, "Introduction to transients analysis of power systems with ATP", in *Transient Analysis of Power Systems: A Practical Approach*, Wiley, 2020, p. 1–9, DOI 10.1002/9781119480549.ch1 | Ferramenta: ATPDraw/EMTP | p. 2 (IV) |
| [18] | S. Venkatesan et al., "Health monitoring and prognosis of electric vehicle motor using intelligent-digital twin", IET Electr. Power Appl., v. 13, n. 9, p. 1328–1335, 2019 | Suporte genérico à ideia de gêmeo digital/prognóstico na camada digital (motor de veículo elétrico, não MT) | p. 2 (III-B) |
| [19] | Z. Liu et al., "The role of data fusion in predictive maintenance using digital twin", AIP Conf. Proc., v. 1949, art. 020023, 2018, DOI 10.1063/1.5031520 | Idem [18] (fusão de dados / manutenção preditiva) | p. 2 (III-B) |
| [20] | A. Fuller et al., "Digital twin: Enabling technologies, challenges and open research", IEEE Access, v. 8, p. 108952–108971, 2020 | Idem [18] (revisão de gêmeo digital) | p. 2 (III-B) |
| [21] | IEC 60034-15: *Rotating Electrical Machines, Part 15: Impulse Voltage Withstand Levels of Form-Wound Stator Coils*, Genebra, 2025 | Enquadramento: "filosofia de suportabilidade SFI"; nenhum valor usado | p. 2 (contribuições, II-B); p. 4 (V-C) |
| [22] | IEC 60071-1: *Insulation Co-ordination, Part 1: Definitions, Principles and Rules*, Genebra, 2019 | Enquadramento: "regras/limites de coordenação de isolamento"; nenhum procedimento aplicado | p. 2 (contribuições); p. 4 (V-C) |
| [23] | "Method for the mitigation of transient overvoltages and monitoring of dielectric degradation in electrical systems", pedido de patente brasileiro, 2026 (número, depositante e inventores omitidos) | Origem do método de duas camadas (snubber reflexivo + camada digital); confere prioridade/propriedade intelectual | p. 1 |
| [24] | L. F. Silva, M. Guimarães, C. A. Conceição, T. A. C. Maia e S. M. Silva, "Implementation of a medium voltage experimental test bench for predictive monitoring of offshore motor", XVII SBAI / XI SBSE, 2025, DOI 10.29327/1842969.1-325 | Bancada de MT para a validação experimental futura (próximo passo) | p. 4 (conclusão) |

Observação [INFERÊNCIA]: a ref. [24] lista autores nominalmente (Silva, Guimarães, Conceição, Maia, Silva), o que, num artigo em revisão duplo-cega, sugere o grupo de origem, sem confirmação no texto.

---

## Fontes externas verificadas nesta sessão (fora do artigo)

- Vollet, C.; de Metz-Noblat, B. "Vacuum Circuit Breaker Model: Application Case to Motors Switching", IPST 2007, Lyon. https://www.ipstconf.org/papers/Proc_IPST2007/07IPST106.pdf — texto integral obtido e lido (Seções II-A, II-B, III-D, V-B, VI).
- IEC 60034-15:2009 (Ed. 3.0), preview oficial iTeh: https://cdn.standards.iteh.ai/samples/15848/1b914cc7cb9b4c4582e502f946666007/IEC-60034-15-2009.pdf — Cláusulas 1–4.2, Tabela 1 (Notas 1–5) e Anexo A.1–A.3 lidos; arquivo (12 p.) baixado novamente nesta sessão e a Nota 5 transcrita literalmente na Seção 7.
- IEC 60034-15:2025 (Ed. 4.0, 2025-06), catálogo: https://www.standards.iteh.ai/catalog/standards/clc/69d2f9f4-d3cd-43e7-9376-db4406810959/en-iec-60034-15-2025 — apenas existência verificada.
- Glinkowski, M. T.; Gutierrez, M. R.; Braun, D. "Voltage escalation and reignition behavior of vacuum generator circuit breakers during load shedding", IEEE Trans. Power Del., v. 12, n. 1, 1997, DOI 10.1109/61.568244 — resumo verificado em https://www.osti.gov/biblio/477204.
- ScienceDirect Topics, "Surge impedance": https://www.sciencedirect.com/topics/engineering/surge-impedance — apenas ordem de grandeza (cabos ≈ dezenas de ohms; linhas aéreas 300–500 Ω); fonte secundária.
