# Etapa 1 — Aprofundamento no monitoramento de degradação de isolamentos de estator: estresse dielétrico espira-a-espira, TRVs de VCB e efeito cumulativo de reignições

**Objetivo.** Estabelecer a base física, normativa e metodológica do módulo MVP de RUL (*remaining useful life*) de isolamento de estator para motores de indução de média tensão (2,3–13,8 kV) manobrados por disjuntores a vácuo (VCB) em plantas críticas, respondendo a três perguntas: (i) por que o dano espira-a-espira por frente rápida é o modo de falha crítico e por que é o mais difícil de detectar; (ii) quanto estresse dielétrico uma manobra severa impõe, em números verificáveis, e como esse estresse se compara aos envelopes normativos de suportabilidade; (iii) por que nenhum método de monitoramento atualmente normalizado converte uma manobra em consumo de vida, e o que precisaria existir para que convertesse.

**Diagnóstico.** O Documento A fornece o gerador de estresse (modelo dinâmico de VCB com chopping, recuperação dielétrica parabólica e reignição de alta frequência em ATP/EMTP) e a evidência quantitativa de que a mitigação ativa reduz o pico de TRV em 67 % [FATO: doc A, p. 1, 3], mas **não** modela o isolamento (motor representado por ramo R–L concentrado), **não** conta reignições, **não** reporta tensão nos terminais do motor, **não** define BIL e **não** calcula RUL [FATO: doc A, p. 3–4; FATO por omissão verificado por leitura integral do texto, p. 1–5]. Do lado normativo, IEC 60034-15, IEEE 522, IEC 60034-27-x e IEEE 43 fornecem **níveis de suportabilidade e limiares de aceitação**, e três delas negam explicitamente a possibilidade de predizer tempo até falha a partir dos respectivos indicadores [NORMA: IEC 60034-27-2:2023, Introdução; IEC 60034-27-3:2015, Introdução; IEC 60034-27-4:2018, Introdução]. Portanto, existe uma lacuna metodológica real, e ela é precisamente a interface entre o oscilograma de manobra e um acumulador de dano dielétrico. O risco dominante do projeto não é técnico-computacional: é a **ausência de parâmetros de curva de vida (expoente $n$, limiar $V_{th}$, fração espira-a-espira $a(t_f)$) medidos em mica-epóxi pré-formada de MT sob impulsos de VCB**, que não foram localizados em nenhuma fonte primária acessada.

**Arquivos consultados.**

| Arquivo | Papel nesta etapa |
|---|---|
| `(PDF do autor, fora do repositório) A_sepoc_snubber.txt` (p. 1–5) | Fonte primária do Documento A: Tabelas I–III, Seções II–VI, referências [1]–[24] |
| `anexos/fichamentos_AB/A_snubber_tiristor_vcb.md` | Fichamento verificado de A, incluindo leituras das Figs. 1–4 e a lista explícita do que A não afirma (§8) |
| `anexos/pesquisa/espira_a_espira_reignicoes_cumulativas.md` | Distribuição espira-a-espira, contagem de reignições, modelos de dano (F1–F37, C1–C9) |
| `anexos/pesquisa/iec60034_15_bil_suportabilidade.md` | IEC 60034-15 (2009/2025), IEEE 522, IEC 60071-1, IEC 60034-18-41/-42 (F1–F27) |
| `anexos/pesquisa/metodos_monitoramento_estator_atual.md` | Tabela comparativa de métodos, ISO 13374-1/13381-1, percentis de DP (F1–F50, C1–C6) |
| `anexos/cruzamento/cruzamento_A_snubber_vcb.md` | Perfil de estresse por evento, acumuladores D1–D9, matriz estressor × indicador × modelo, inventário do repositório |
| `anexos/pesquisa/fisica_surtos_vcb_isolamento.md` | Física de chopping/reignição, modelos de vida (F1–F48) |
| `anexos/pesquisa/normas_monitoramento_isolamento.md` | Estado das edições normativas, ISO 55000/55001, CIGRE C4.76 e JWG A3.53 (F1–F59) |
| `anexos/fichamentos/02, 07, 09, 12, 13` | Jensen (EKF), Vichare & Pecht (LCM), Strangas (prognóstico + mitigação), Ma (perfil de missão), Wu (survey DL) |

**Estratégia.** O documento segue a cadeia causal completa **manobra → transitório no disjuntor → tensão no terminal do motor → tensão longitudinal na primeira bobina → descarga parcial e *treeing* → perda de suportabilidade → falha**, marcando em cada elo o que é fato verificado, o que é inferência física e o que é hipótese a calibrar. Os números do Documento A são tratados como *dados de entrada* de um acumulador de dano, não como resultado de conformidade normativa. Toda comparação com norma é apresentada com a ressalva de que a grandeza reportada por A é TRV **no disjuntor**, não tensão nos terminais do motor.

**Limitações.** (a) Nenhuma fonte primária acessada quantifica a fração da tensão terminal que recai sobre a primeira bobina em função do tempo de frente para bobinas pré-formadas de MT; os números clássicos "70–90 % a 0,1 µs" **não** foram confirmados. (b) O expoente de vida $n$ da lei de potência inversa disponível provém de fio esmaltado e de epóxi puro, não de mica-epóxi. (c) O texto integral da IEEE Std 522 (1992/2004/2023) e a Tabela 1 da IEC 60034-15:2025 não foram lidos; os valores usados vêm de amostra do CDV e de fontes secundárias, sempre rotuladas. (d) O Documento A integra com passo de 1 µs, o que impede resolver frentes de 0,1–0,2 µs e torna as RRRV reportadas limites inferiores do dv/dt real.

**Próximo passo recomendado.** Extrair do modelo ATP do Documento A, sem alterar o circuito, as três grandezas que faltam para fechar a cadeia: (1) tensão fase-terra e fase-neutro no nó do motor (sonda `01AT`, já presente no `/OUTPUT` do arquivo de referência [REPO: `git show ad308d5:trt_all_motors_dt_ea.atp:857-859`]); (2) contagem de reignições por polo por manobra; (3) tempo de frente $T_1$ por reignição segundo a definição normativa. Em paralelo, reduzir o passo de integração para 10–50 ns num caso de verificação, para checar se as frentes de sub-microssegundo alteram materialmente a RRRV.

---

## 1. Enquadramento: por que o dano espira-a-espira é o modo crítico e o mais difícil de detectar

### 1.1 O problema

Redes isoladas e fracamente malhadas de plantas críticas — plataformas *offshore*, refinarias, petroquímicas — operam grandes motores de indução de MT manobrados por VCB [FATO: doc A, p. 1]. O VCB é preferido por compacidade, baixa manutenção e alta confiabilidade, mas sua recuperação dielétrica muito rápida tem um contraponto documentado: ao interromper correntes indutivas, o arco pode extinguir-se antes do zero natural (*current chopping*) e a recuperação rápida do *gap* favorece reignições múltiplas [FATO: doc A, p. 1]. A energia magnética armazenada nas indutâncias transfere-se às capacitâncias parasitas, produzindo TRVs com picos elevados e frentes íngremes [FATO: doc A, p. 1].

A norma de manobra de cargas indutivas é explícita quanto ao pior caso: "the switching of the current of a starting or stalled motor is usually the more severe operation" [NORMA: IEC 62271-110:2023, 4.3.2], e a mesma norma declara que "No limits to the overvoltages are given as the overvoltages are only relevant to the specific application" [NORMA: IEC 62271-110:2023, 4.3.1]. Ou seja: o evento mais severo é reconhecido, mas nenhum teto normativo é imposto ao fabricante do disjuntor — a responsabilidade de coordenação recai sobre o projeto da instalação.

Do lado da máquina, a IEC 60034-15 adverte que seus níveis padrão "foram considerados apropriados para solicitações relacionadas à operação de disjuntores que podem ocorrer em serviço. Podem não ser adequados para condições operacionais especiais (p. ex. **partida interrompida** ou conexão direta a linhas aéreas)" [NORMA: IEC 60034-15:2009, Tabela 1, Nota 5, transcrição literal: "They may not be adequate for special operating conditions (e.g. interrupted start or direct connection to overhead lines)"]. O cenário simulado pelo Documento A é exatamente "an intempestive interruption of a motor start commanded by the protection", com a máquina drenando corrente plena de partida ($I_p/I_n = 6{,}5$) [FATO: doc A, p. 3, V]. A equivalência entre "interrupted start" da norma e o cenário de A é interpretação deste documento [INFERÊNCIA], mas a coincidência é literal.

A edição de 2025 da norma reforça o ponto: prevê **níveis reforçados** (*enhanced*) para "very frequent switching or aborted starts" [NORMA: IEC CDV 60034-15 (2/2199/CDV), 4.3 — rascunho "subject to change"; a Tabela 1 da edição publicada não foi acessada, INSERIR CITAÇÃO].

### 1.2 Por que o modo crítico é o espira-a-espira

Três razões, cada uma com fonte:

1. **A física concentra o estresse.** Sob surto de frente curta, a fase não pode assumir instantaneamente o mesmo potencial em todos os pontos; surgem uma componente **transversal** (condutor–terra) e uma **longitudinal** (ao longo do condutor), esta última solicitando a isolação entre espiras, e "as componentes mais altas de ambas normalmente aparecem na primeira ou na última bobina do enrolamento" [NORMA: IEC 60034-15:2009, Anexo A.1]. O Documento A invoca o mesmo mecanismo: "Because of travelling wave effects along the windings, a large fraction of this voltage appears across the first few turns" [FATO: doc A, p. 2, II-B].
2. **A norma reconhece que não há lei fechada.** "no simple law has been found for pre-calculating this peak value" para a tensão longitudinal na bobina de entrada, que depende do tempo de subida $t_s$, do comprimento de condutor e do arranjo de espiras [NORMA: IEC 60034-15:2009, A.3]. Isto é decisivo: se não há lei simples, não há como converter tensão terminal em tensão entre espiras sem modelo específico da máquina.
3. **A falha é o precursor da falha de massa.** O detector de impedância efetiva de sequência negativa foi proposto para "turn-to-turn insulation deterioration", que os autores consideram "the beginning stage of most motor winding failures" [LITERATURA: Kohler, Sottile e Trutt, IEEE TIA, 2002, resumo via OpenAlex, DOI 10.1109/tia.2002.802935]. O curto entre espiras evolui para curto fase-terra e queima do estator.

Quanto à relevância estatística do isolamento de estator em O&G: o Documento A apoia-se em Thorsen e Dalva [FATO: doc A, p. 1, refs. [12], [13]], mas **não transcreve nenhum percentual** [FATO por omissão]. A verificação desta sessão registra: os percentuais por componente **não foram confirmados no texto primário** (páginas IEEE Xplore não renderizaram); fonte secundária técnica atribui a Thorsen e Dalva (1999) que "for motors rated above 2000 kW stator windings accounted for around 60 % of total failures" e que "bearings and stator windings account for 75 %-80 % of all high voltage motor failures" [LITERATURA: Pinto, Strickler e Anand, IEEE PCIC 2022, paper 0567, https://ieeepcic.com/2022conference/wp-content/uploads/sites/7/2022/09/2022-PCIC-0567.pdf]. Comparadores verificados: EPRI 1983 — estator 37 %, mancais 41 %; IEEE-IAS 1985 — enrolamento ≈ 26 %, mancais ≈ 45 % [LITERATURA: https://reliamag.com/articles/large-motor-reliability-studies/]. **Não usar percentuais de Thorsen e Dalva em texto acadêmico antes de transcrevê-los do PDF IEEE** — [INSERIR CITAÇÃO].

### 1.3 Por que é o mais difícil de detectar

| Obstáculo | Evidência |
|---|---|
| Nenhum ensaio **online** normalizado interroga a isolação entre espiras | A DP online cobre ≥ 3 kV sem conversor e mede o *groundwall*; a norma nega estimativa de tempo até falha por qualquer grandeza de DP [NORMA: IEC 60034-27-2:2023, Introdução, "Limitations"] |
| O único ensaio normalizado que solicita diretamente a isolação entre espiras é **offline** e potencialmente destrutivo | Ensaio de surto: IEEE Std 522-2023 (200 kW–100 MW); IEC 60034-15 em bobinas-amostra [NORMA: IEEE 522-2023, escopo; IEC 60034-15:2009, 4.2] |
| A própria IEC desaconselha ensaio de impulso entre espiras em enrolamento completo | "not recommended" pela dificuldade de detectar a falha entre espiras [NORMA: IEC 60034-15:2009, 5.2] |
| Os guias de ensaio de surto declaram não avaliar surtos anormais | "Test voltage levels described herein do not evaluate the ability of the turn insulation to withstand abnormal voltage surges" [NORMA: IEEE 522-2023, escopo, citação verbatim da página IEEE SA] |
| Os métodos online sensíveis a espira (MCSA, sequência negativa) detectam o **curto já formado**, não a fadiga que o precede | [LITERATURA: Tallam et al., IEEE TIA 43(4):920–933, 2007; Ruzimov et al., *Sensors*, 2025, https://pmc.ncbi.nlm.nih.gov/articles/PMC12349302/] |
| A degradação é episódica, não contínua | O estresse ocorre em janelas de ~0,1–3 ms por manobra [LITERATURA: Wong, Snider e Lo, IPST 2003, p. 2, 5], enquanto os métodos de tendência amostram em escala de meses |

O resultado é uma assimetria: **o estressor é medível em microssegundos; o estado é medível em meses; e não existe função de transferência normalizada entre os dois.** É essa função de transferência que o módulo de RUL precisa construir.

---

## 2. Física do estresse espira-a-espira

### 2.1 Distribuição não linear e dependência do tempo de frente

Quando um surto de tempo de subida $t_s$ incide no terminal, a bobina de entrada comporta-se como uma linha de transmissão multicondutora (MTL), não como uma indutância concentrada. A tensão que aparece entre espiras adjacentes é, em primeira ordem, a **diferença temporal** da onda incidente ao longo do percurso de uma espira:

$$
\Delta v_{\text{esp}}(t) \;\approx\; v(t) - v\!\left(t - \tau_{\text{esp}}\right),
\qquad
\tau_{\text{esp}} = \frac{\ell_{\text{esp}}}{u},
$$

em que $\Delta v_{\text{esp}}$ [V] é a tensão longitudinal sobre uma espira, $v(t)$ [V] a tensão incidente no terminal, $\tau_{\text{esp}}$ [s] o tempo de trânsito de uma espira, $\ell_{\text{esp}}$ [m] o comprimento do condutor de uma espira e $u$ [m/s] a velocidade de propagação no enrolamento [INFERÊNCIA FÍSICA a partir do modelo MTL]. Para $t_s \gg \tau_{\text{esp}}$, $\Delta v_{\text{esp}} \to \tau_{\text{esp}}\,\mathrm{d}v/\mathrm{d}t$, isto é, **a tensão entre espiras é proporcional ao dv/dt e não ao pico**. Para $t_s \lesssim \tau_{\text{esp}}$, quase toda a frente cai sobre as primeiras espiras.

Suporte de literatura para a ordem de grandeza de $\tau$: "tempo de trânsito na primeira bobina ~100 ns" [LITERATURA secundária: Baker/SKF, *The State of Surge Testing on Induction Motors*, p. 7, http://www.cmcbaker.com/manuals/surge%20test%20whitepaper.pdf], da mesma ordem das frentes de serviço que a norma admite ("voltage surges … may have rise times down to 0,1 µs" [NORMA: IEC 60034-15:2009, A.1]). Ou seja, em serviço o regime é justamente o de transição, em que o comportamento é fortemente não uniforme.

**Advertência de honestidade documental.** Os percentuais frequentemente citados — ≈ 70–90 % do surto na primeira bobina a 0,1 µs e ≈ 20–30 % a 1 µs — **não foram confirmados em nenhuma fonte primária acessada nesta sessão**. Os textos integrais de Cornick & Thompson (1982), Wright, Yang & McLeay (1983), Gupta et al. (1987), Narang et al. (1989) e do capítulo de Stone et al. (2014) retornaram HTTP 403 [registro de acesso em `out/etapa1/espira_a_espira_reignicoes_cumulativas.md`, §5.1]. O que foi confirmado:

| Grandeza | Valor | Condição | Fonte |
|---|---|---|---|
| Tendência qualitativa | "quanto menor o tempo de subida, mais desigual a distribuição entre espiras"; *jump voltage* e tempo de subida são os fatores mais significativos para a isolação espira-a-espira | pares torcidos e bobinas pré-formadas | [LITERATURA: CIGRE WG D1.43, TB 703, Tabela 2 e Fig. 13, p. 15–18, 34, https://cigre.cz/dokumenty_komise/d1/WG%20D1.43_TB_Final.pdf] |
| Máxima tensão espira-a-espira | **16,1 % da tensão aplicada**, na 13.ª espira da **primeira** bobina | FEM + circuito, motor 13,8 kV / 10 MW, 13 espiras/bobina, isolação de espira 0,3 mm, rampa de 0,2 µs | [LITERATURA: Ferreira e Ferreira, IPST 2021, Tab. VI–VII, https://www.ipstconf.org/papers/Proc_IPST2021/21IPST056.pdf] |
| Máxima tensão espira-terra | **121,7 %** da tensão aplicada (101,7 % quando o rotor é incluído) | idem | [idem, Tab. VI–VII] |
| Persistência da não uniformidade | mantém-se para degraus de 0,1 µs **a mais de 10 µs** | medições em máquina protótipo | [LITERATURA: Krings et al., ICEM 2016, resumo via OpenAlex, DOI 10.1109/ICELMACH.2016.7732753] |

Ressalva sobre Ferreira & Ferreira: os 16,1 % e 121,7 % são **resultado de simulação da máquina completa**; a validação experimental restringiu-se a medições de capacitância e a um ensaio de surto em **uma bobina isolada**; a distribuição entre espiras da máquina montada não foi confrontada com medição [LITERATURA: Ferreira e Ferreira, IPST 2021, Seção III].

### 2.2 Modelo de onda viajante / linha de transmissão

O modelo consagrado é a MTL da bobina de linha, com propagação simultânea em **modo série** (ao longo do condutor) e **modo paralelo** (entre espiras e para a terra através das capacitâncias) [LITERATURA: Wright, Yang e McLeay, IEE Proc. B 130(4):245–256, 1983, resumo verificado; Oyegoke, 2000; Zhang et al., IEEE Trans. Magn. 49(5):1905–1908, 2013; Hussain e Gómez, IEEE TDEI 24(2):837–846, 2017]. O equivalente por espira é uma cascata de células com indutância própria e mútua, resistência série, capacitância espira-espira $C_s$ e capacitância espira-terra $C_g$; sob frente rápida "a maior parte da tensão de linha é aplicada às primeiras espiras" [LITERATURA: CIGRE WG D1.43, TB 703, p. 15, Fig. 11].

A grandeza que a norma de conversores usa para parametrizar essa concentração é a fração de pior caso da *jump voltage*:

$$
V_{\text{esp,máx}} = a(t_r)\,U_j ,
$$

com $V_{\text{esp,máx}}$ [V] a máxima tensão sobre a isolação entre espiras, $U_j$ [V] o *jump voltage* (degrau de tensão no terminal) e $a(t_r)$ [adimensional] a fração de pior caso, função do tempo de subida $t_r = t_{90\%}-t_{10\%}$ [NORMA: IEC 60034-18-41:2014, 3.13, 3.22; a curva de pior caso é a Fig. 7 da norma, reproduzida como Fig. 13 do CIGRE — **valores numéricos não acessados**, INSERIR CITAÇÃO]. O CIGRE registra ainda os fatores $K = 0{,}7$ (espira/espira) e $EF = 1{,}63$ [LITERATURA: CIGRE WG D1.43, TB 703, p. 43].

**Duas ressalvas obrigatórias sobre essa parametrização** [NORMA: IEC 60034-18-41:2014, amostra iTeh lida nesta sessão]:

1. **Classe de sistema isolante e topologia de enrolamento.** A legenda da Fig. 7 é, literalmente, "Worst case voltage stressing the turn/turn insulation in a variety of **random wound** stators as a function of the rise time of the impulse", e a Introdução da mesma norma delimita: "The Type I systems are dealt with in this standard. They are generally used in rotating machines rated at **700 V r.m.s. or less** and tend to have random wound windings". O alvo deste documento é bobina **pré-formada** de mica-epóxi de 4,16 kV, isto é, sistema **Tipo II**. Transpor a curva da Fig. 7 para essa classe é troca simultânea de classe de sistema isolante e de topologia de enrolamento, e portanto **[HIPÓTESE]** — não é rota válida para obter $a(t_f)$ do motor de 4,16 kV. A Fig. 7 pode servir apenas como **referência de forma** da dependência com $t_r$, jamais de valores.
2. **Convenção pico versus pico a pico.** A norma expressa a solicitação entre espiras como **$2a\,U_j$ pico a pico** (Fig. B.4, legenda: "peak/peak voltage of 2aUj on the turn/turn insulation"). A forma $V_{\text{esp,máx}} = a(t_r)U_j$ escrita acima é a convenção **de pico** adotada neste documento; qualquer valor numérico extraído da norma exige declarar em qual das duas convenções está, sob pena de erro de fator 2.

### 2.3 Papel do cabo e das reflexões

O cabo entre painel e motor não é neutro. Três efeitos verificados:

1. **Reflexão na descontinuidade de impedância.** A impedância de surto de cabos de potência é de dezenas de ohms (≈ 30–80 Ω), contra 300–500 Ω de linhas aéreas [LITERATURA secundária: ScienceDirect Topics, "Surge impedance"]; a impedância de surto do enrolamento do motor é muito maior, o que produz coeficiente de reflexão positivo e **dobra** a tensão incidente no terminal do motor no limite ideal [INFERÊNCIA FÍSICA]. Vollet e de Metz-Noblat mostram exatamente isso: com para-raios apenas no cubículo, "devido às reflexões de onda no cabo", a sobretensão no terminal do motor não fica limitada [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, §V-B, p. 5, https://www.ipstconf.org/papers/Proc_IPST2007/07IPST106.pdf].
2. **Amortecimento e alongamento da frente.** Capacitores nos terminais alongam a frente [LITERATURA: Cornick e Thompson, 1982, Partes 1 e 2, resumo via OpenAlex]. Um resistor casado ($R = Z_c$) anula a reflexão, pois $\alpha = (R-Z_c)/(R+Z_c) = 0$ [LITERATURA: Abdulahovic, tese Chalmers 2011, p. 120, https://publications.lib.chalmers.se/records/fulltext/148759/148759.pdf].
3. **Ponto de instalação.** O Documento A afirma que o snubber está "connected in parallel with the machine terminals" [FATO: doc A, p. 2, III-A], mas a leitura da Fig. 2 mostra os ramos SCR–SCR–$R_s$ partindo do nó do lado de carga do VCB, **a montante** do bloco LCC de 240 mm² que leva ao motor [FATO: doc A, Fig. 2, p. 4 — leitura de figura, reconferida em recorte ampliado da imagem nativa]. A confirmação independente está no arquivo de referência: válvulas TYPE-11 entre `X0002C` e `XX0034` e resistor de 30 Ω de `XX0034` para a terra, com as cargas do motor em `01ATA/B/C` separadas por segmento de cabo [REPO: `git show ad308d5:trt_all_motors_dt_ea.atp:739, 837, 846-847, 736`]. Consequência: **a proteção está no painel, não nos bornes do motor** [INFERÊNCIA], e a literatura correlata mostra que isso pode não limitar a tensão no terminal do motor.

### 2.4 O que o Documento A afirma sobre isso — e o que ele não modela

| Afirmação de A | Página | Status |
|---|---|---|
| "Because of travelling wave effects along the windings, a large fraction of this voltage appears across the first few turns [1], [6]" | p. 2, II-B | [FATO: doc A]. A fração não é quantificada; as refs. [1] (dissertação) e [6] (Bak et al., modelagem de VCB para TRV em redes) não são fontes de distribuição de tensão em enrolamentos [INFERÊNCIA] |
| "the nonlinear voltage distribution concentrates stress on the line end turns and, under repetitive excitation, initiates and propagates electrical treeing" | p. 1 | [FATO: doc A]. Nenhuma referência de física de dielétricos é citada [FATO por omissão] |
| "Repetitive SFI stress is the driving mechanism of electrical treeing and of the slow, 'silent' fatigue of the interturn insulation" | p. 2, II-B | [FATO: doc A]. "Fadiga silenciosa" é expressão do artigo, sem definição operacional nem indicador mensurável associado [FATO por omissão] |
| "The strong attenuation of the peak directly relieves the dielectric 'bombardment' of the first stator turns" | p. 4, V-C | [FATO: doc A]. A redução de pico (67 %) não se transfere integralmente à isolação de espira porque a RRRV da fase B cai apenas 12,9 % e a tensão longitudinal depende do tempo de subida [NORMA: IEC 60034-15:2009, A.3; INFERÊNCIA FÍSICA] |

**O que A não modela** [FATO por omissão, verificado por leitura integral de p. 1–5 e das Figs. 1–4]:

- **O isolamento.** Não há modelo de enrolamento a parâmetros distribuídos, capacitâncias espira-espira ou espira-terra, nem distribuição de tensão de impulso ao longo da bobina. O motor é um ramo R–L série concentrado com $R_{eq} = 0{,}691\ \Omega$ e $L_{eq} = 8{,}9795$ mH [FATO: doc A, Fig. 2, p. 4 — leitura de figura; confirmado em REPO: `git show ad308d5:trt_all_motors_dt_ea.atp:736-738`]. Logo, o efeito de onda viajante **no enrolamento** não é simulado: é argumento, não resultado [INFERÊNCIA].
- **A tensão nos terminais do motor.** Existe sonda `01AT` na Fig. 2, mas seus resultados não são reportados [FATO: doc A, Fig. 2, p. 4; FATO por omissão].
- **Descargas parciais, treeing, curva de vida, limiar de iniciação e qualquer relação quantitativa entre pico/dv/dt/energia e dano** [FATO por omissão].
- **O número de reignições**, o BIL, a classe térmica, o sistema isolante (mica/epóxi, VPI, *resin-rich*), a idade e o histórico de manobras da máquina [FATO por omissão].
- **A camada digital.** Nenhuma equação, variável de estado, taxa de amostragem ou algoritmo do "incremental insulation degradation model" é apresentado; o próprio artigo declara que "the digital protection layer is beyond the scope of this work" [FATO: doc A, p. 2, III-B].

Observação adicional de coerência interna [INFERÊNCIA]: a sigla RUL não aparece em nenhuma parte do texto de A; a expressão "remaining useful life" ocorre **uma única vez**, na p. 2 (Seção III-B), como finalidade da camada digital.

---

## 3. Perfil de estresse do Documento A

### 3.1 Sistema, disjuntor e cenário

| Grandeza | Valor | Evidência |
|---|---|---|
| Motor | 1250 kW; 4,16 kV; 60 Hz; $\eta = 0{,}95$; $\mathrm{fp} = 0{,}88$; $I_p/I_n = 6{,}5$ | [FATO: doc A, Tabela I, p. 3] |
| Corrente nominal | $I_n = P/(\sqrt{3}\,V\,\eta\,\mathrm{fp}) = 1{,}25\times10^6/(\sqrt3 \cdot 4160 \cdot 0{,}95 \cdot 0{,}88) \approx 207{,}5$ A | [CÁLCULO PRÓPRIO]; coincide com "Line current (rms): 207.52 A" legível na Fig. 2 [FATO: doc A, Fig. 2, p. 4 — leitura de figura] |
| Corrente de partida | $I_p = 6{,}5\,I_n \approx 1349$ A | [CÁLCULO PRÓPRIO] |
| Base 1 pu (pico fase-terra) | $1\ \mathrm{pu} = \sqrt{2/3}\,U_N = 4160\cdot 0{,}8165 = 3{,}397$ kV, **base de tensão nominal da máquina** | [CÁLCULO PRÓPRIO]; convenção de máquina, usada pela IEEE Std 522 (nível de bobina nova $= 2{,}86\,U_{LL} = 3{,}5$ pu) e pela IEC 60034-15:2025 [LITERATURA secundária; NORMA: IEC CDV 60034-15]. **Não confundir** com a base pu da IEC 60071-1:2019, 3.17, Nota 1 — "overvoltage values expressed in p.u. refer to $U_s\sqrt{2/3}$", com $U_s$ a **tensão máxima do sistema**: com $U_s = 7{,}2$ kV (Seção 4.3), 1 pu = 5,88 kV e os 41,44 kV valeriam 7,05 pu [NORMA: IEC 60071-1:2019, 3.17, Nota 1, amostra iTeh lida; CÁLCULO PRÓPRIO]. **Toda tabela em pu deste documento usa a base de máquina, 3,397 kV** |
| Chopping $I_{ch}$ | 1 A a 2 A | [FATO: doc A, Tabela II, p. 3] |
| RRDS (recuperação dielétrica a frio) | $V_{wth}(t) = A\,t + B\,t^2$; $A = 0{,}801$ kV/ms; $B = 1{,}226$ kV/ms²; $t$ contado "after arc extinction" | [FATO: doc A, p. 3, IV-B; Tabela II] |
| di/dt crítico de reignição | 5 A/µs a 15 A/µs | [FATO: doc A, Tabela II, p. 3] |
| Dispersão de polos (*stagger*) | 14 ms a 25 ms | [FATO: doc A, Tabela II, p. 3] |
| Resistor do snubber | $R_s = 30\ \Omega$/fase, "sized close to the surge impedance" | [FATO: doc A, p. 2, III-A; Tabela II] |
| Passo de integração / janela | 1 µs / 45 ms | [FATO: doc A, Tabela II, p. 3] |
| Cenário | Interrupção intempestiva de partida comandada pela proteção, com $I_p/I_n = 6{,}5$ | [FATO: doc A, p. 3, V] |

Duas leituras da RRDS [CÁLCULO PRÓPRIO a partir da Tabela II]:

$$
V_{wth}(t) = 0{,}801\,t + 1{,}226\,t^2 \ [\mathrm{kV}],\quad t\ \mathrm{em\ ms};
\qquad
\frac{\mathrm{d}V_{wth}}{\mathrm{d}t} = 0{,}801 + 2{,}452\,t \ [\mathrm{kV/ms}].
$$

| $t$ (ms) | 0,1 | 0,5 | 1,0 | 2,0 | 3,0 | 4,0 | 5,0 | 6,0 |
|---|---|---|---|---|---|---|---|---|
| $V_{wth}$ (kV) | 0,092 | 0,707 | 2,03 | 6,51 | 13,44 | 22,82 | 34,66 | 48,94 |
| $\mathrm{d}V_{wth}/\mathrm{d}t$ (kV/ms) | 1,05 | 2,03 | 3,25 | 5,71 | 8,16 | 10,6 | 13,1 | 15,5 |

Tempos para o *gap* suportar os picos reportados [CÁLCULO PRÓPRIO, raiz positiva de $Bt^2 + At - V = 0$]: $V = 41{,}44$ kV → $t \approx 5{,}50$ ms; $V = 13{,}65$ kV → $t \approx 3{,}03$ ms; $V = 14{,}07$ kV ($U'_P$ de 4,16 kV, Seção 4) → $t \approx 3{,}08$ ms.

**Comparação com a literatura** [INFERÊNCIA]. Todas as comparações abaixo são de **inclinações médias no intervalo 0–1 ms**; comparar $V_{wth}(1\ \mathrm{ms}) = 2{,}03$ kV com taxas em kV/ms só é lícito porque $t = 1$ ms.

- **RRDS.** A RRDS de A fornece 2,03 kV em 1 ms (inclinação média de 2,03 kV/ms), contra recuperação linear de "20 or 40 kV/ms" usada por Vollet [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, §III-D, p. 3 — texto primário lido], 2/20/30/50 V/µs por Wong [LITERATURA: IPST 2003, Tab. 1], 20–30 kV/ms por Xue e Popov [LITERATURA: IPST 2013, Tab. I] e 5,5 kV/ms iniciais **medidos** [LITERATURA: Abdulahovic, 2011, p. 112]. A inclinação instantânea de A só atinge 20 kV/ms em $t \approx 7{,}8$ ms [CÁLCULO PRÓPRIO]. Qualificação correta: **a RRDS de A é o extremo inferior da faixa publicada, não um valor fora dela** — coincide praticamente com o caso mínimo de Wong (2 V/µs = 2 kV/ms), está 10–25× abaixo dos casos centrais (20–50 V/µs) e ≈ 2,7× abaixo dos 5,5 kV/ms iniciais de Abdulahovic [CÁLCULO PRÓPRIO: $20/2{,}03 = 9{,}9$; $50/2{,}03 = 24{,}6$; $5{,}5/2{,}03 = 2{,}71$]. Uma recuperação inicial lenta favorece sequências longas de reignição e escalada mais severa [LITERATURA: Wong, Snider e Lo, IPST 2003, p. 4–5].
- **di/dt crítico.** O di/dt crítico de 5–15 A/µs de A é ≈ **7 a 140× inferior à capacidade de extinção de alta frequência** publicada, 100–700 A/µs [LITERATURA: Wong 2003, Tab. 2 ($D = 100$ e 600 A/µs); Abdulahovic 2011, p. 29 (100–600 A/µs); Xue e Popov, IPST 2013, Tab. I (500–700 A/µs)] [CÁLCULO PRÓPRIO: $100/15 = 6{,}7$; $700/5 = 140$]. **Não confundir** essa grandeza com o di/dt da corrente de frequência industrial que o VCB é capaz de interromper, 150–1000 A/µs [LITERATURA: Wong 2003, p. 1] — são parâmetros distintos, e a mistura dos dois é a origem de razões espúrias.

Consequência prática: com ambos os parâmetros no **extremo inferior** da faixa publicada, **os resultados de A devem ser lidos como envelope conservador extremo, não como estatística de campo** — extremo quanto ao *resultado*, ainda que os *parâmetros de entrada* permaneçam dentro (na borda) do que a literatura reporta.

Há ainda uma **ambiguidade de convenção não resolvida** [INFERÊNCIA]: A escreve que a corrente de AF "is interrupted when its di/dt at the zero crossing **exceeds** a critical value" [FATO: doc A, p. 3, IV-B], ao passo que Wong, Xue & Popov e Abdulahovic adotam a convenção oposta — a extinção ocorre quando $|\mathrm{d}i/\mathrm{d}t|$ é **menor** que a capacidade de extinção [LITERATURA: Wong 2003, p. 2: "when the absolute value of the rate-of-change of the current at a current zero above this di/dt limit, arc extinction will not occur"; Xue e Popov, IPST 2013, p. 2; Abdulahovic 2011, p. 28]. Sem esclarecer a convenção no MODELS/TACS, **não é possível inferir o sentido do efeito sobre o número de reignições**.

### 3.2 Tabela III completa, reduções percentuais e normalizações

**Tabela III do Documento A** — "TRV peak and rate of rise (RRRV) at the VCB" [FATO: doc A, Tabela III, p. 3], acrescida das colunas derivadas [CÁLCULO PRÓPRIO]:

| Fase | Pico sem (kV) | RRRV sem (kV/µs) | Pico com (kV) | RRRV com (kV/µs) | Pico sem (pu) | Pico com (pu) | Redução pico (%) | Redução RRRV (%) | $t_f$ sem (µs) | $t_f$ com (µs) |
|---|---|---|---|---|---|---|---|---|---|---|
| A | −30,24 | 13,90 | 6,35 | 3,28 | 8,90 | 1,87 | **79,0** | **76,4** | 2,18 | 1,94 |
| B | 41,44 | 15,05 | 13,65 | 13,11 | 12,20 | 4,02 | **67,1** | **12,9** | 2,75 | 1,04 |
| C | −38,30 | 19,00 | −9,98 | 9,43 | 11,28 | 2,94 | **73,9** | **50,4** | 2,02 | 1,06 |

Fórmulas [CÁLCULO PRÓPRIO]: redução $= (|V_{\text{sem}}| - |V_{\text{com}}|)/|V_{\text{sem}}|$; pu $= V/3{,}397$; $t_f \approx V_{pk}/\mathrm{RRRV}$.

Nota de rodapé da Tabela III, transcrita: "Phase B has the highest peak; the highest RRRV without mitigation is phase C (19.00 kV µs⁻¹). Only the worst phase (B) is annotated in Fig. 4." [FATO: doc A, p. 3]. A quarta linha da tabela original é duplicata da linha B, provável artefato de editoração [INFERÊNCIA].

**Três leituras que o artigo não faz** [CÁLCULO PRÓPRIO + INFERÊNCIA]:

1. O "about 67 %" citado no resumo corresponde a 67,06 % e refere-se **apenas** à fase B. As fases A e C têm reduções de pico maiores (79,0 % e 73,9 %).
2. A redução de RRRV é **fortemente assimétrica entre fases**: 76,4 % (A), 12,9 % (B), 50,4 % (C). Registre-se, para precisão: A **divulga** que a maior RRRV sem mitigação é a da fase C — "the steepest front, 19.00 kV µs⁻¹, occurs on phase C (peak −38.30 kV)" (V-A) e a nota da Tabela III repete "the highest RRRV without mitigation is phase C (19.00 kV µs⁻¹)" [FATO: doc A, p. 3]. O que A **não** comenta é (i) a assimetria das **reduções** percentuais de dv/dt entre fases (76,4 % / 12,9 % / 50,4 %) [CÁLCULO PRÓPRIO] e (ii) as RRRV com snubber das fases A e C no texto corrido [FATO por omissão]. A crítica central permanece integralmente: o artigo sustenta a afirmação de que o snubber "also lowers the rate of rise (from 15.05 to 13.11 kV µs⁻¹)" [FATO: doc A, p. 3, V-C] **na fase de menor redução**.
3. A fase A **inverte a polaridade** do pico (−30,24 kV → +6,35 kV), o que não é comentado [FATO: doc A, Tabela III; FATO por omissão].

### 3.3 Tempo de frente equivalente: por que $t_f = V_{pk}/\mathrm{RRRV}$ é apenas indicativo

A coluna $t_f$ acima usa a hipótese de frente linear:

$$
t_f \;\approx\; \frac{V_{pk}}{\mathrm{RRRV}} \qquad [\text{HIPÓTESE: frente linear e RRRV = inclinação média até o pico}].
$$

Quatro ressalvas, todas necessárias:

1. **A não define RRRV** — máxima derivada? média até o pico? outra? [FATO por omissão: doc A, p. 3]. A norma de máquinas define $T_1 = 1{,}67\,(t_{90\%} - t_{30\%})$ [NORMA: IEC 60034-15:2009, 2.4] e a de conversores define $t_r = t_{90\%} - t_{10\%}$ [NORMA: IEC 60034-18-41:2014, 3.13] — grandezas distintas entre si e distintas de $V_{pk}/\mathrm{RRRV}$.
2. **Pico e RRRV podem pertencer a impulsos distintos da sequência.** O pico de 41,44 kV é o valor máximo alcançado **após a escalada** por reignições sucessivas ("the successive reignitions escalate the TRV" [FATO: doc A, p. 3, V-A]); a nota da Tabela III mostra que o maior pico (fase B) e a maior RRRV (fase C) nem sequer estão na mesma fase [FATO: doc A, p. 3]. A razão $V_{pk}/\mathrm{RRRV}$ **não é**, portanto, um tempo de frente.
3. **O passo de integração é de 1 µs** [FATO: doc A, Tabela II]. Com snubber, $t_f \approx 1$ µs nas fases B e C — **igual ao passo**. As RRRV "com snubber" dessas fases são derivadas numéricas sobre 1–3 amostras; frentes de sub-microssegundo não estão resolvidas, e as RRRV reportadas devem ser lidas como **limites inferiores** do dv/dt real [INFERÊNCIA].
4. **A norma admite frentes de serviço de até 0,1 µs** [NORMA: IEC 60034-15:2009, A.1], uma década abaixo do passo do estudo. O próprio A afirma disparar os SCR "within a microsecond of the anomaly" [FATO: doc A, p. 3, V-B], valor igual ao passo, isto é, no limite da resolução do modelo [INFERÊNCIA].

Há ainda uma tensão interna do argumento de A [INFERÊNCIA]: a objeção central aos supressores RC fixos é que eles "mask the MHz range spectrum needed for condition monitoring" [FATO: doc A, p. 1], mas um modelo com passo de 1 µs tem frequência de Nyquist de 500 kHz e é incapaz de representar o espectro de MHz que se afirma preservar. Além disso, em primeira ordem a alegação não se sustenta. Para um supressor R–C real, a função de transferência é $H = Z_{RC}/(Z_c + Z_{RC}) = (1 + \mathrm{j}\omega RC)/[1 + \mathrm{j}\omega C(Z_c + R)]$, com polo em $1/[2\pi C(Z_c+R)]$, zero em $1/(2\pi RC)$ e **patamar de alta frequência $R/(Z_c+R)$** [CÁLCULO PRÓPRIO, detalhado em `out/etapa1/metodos_monitoramento_estator_atual.md`, C4]. Os valores de componente vêm da fonte primária: "The value of the capacitor is taken to 0,2 or 0,3 µF and the resistor must be **at least** equal to 30 Ω" [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, §III-F, p. 3 — texto primário lido]. Com $C = 0{,}25$ µF e $R = 30\ \Omega$: polo em 10,6 kHz e zero em 21,2 kHz para $Z_c = 30\ \Omega$. O patamar depende da impedância de surto do cabo, que esta própria etapa registra como ≈ 30–80 Ω (Seção 2.3):

| $Z_c$ | Patamar $R/(Z_c+R)$ | Atenuação |
|---|---|---|
| 30 Ω | 0,500 | **−6,0 dB** |
| 80 Ω | 0,273 | **−11,3 dB** |

Como Vollet especifica $R \ge 30\ \Omega$, valores maiores de $R$ **elevam** o patamar e reduzem ainda mais a atenuação, reforçando a conclusão. Em nenhuma combinação da faixa se obtêm os **33 dB a 1 MHz** e **65 dB a 40 MHz** de um **capacitor puro** [CÁLCULO PRÓPRIO: $1/(2\pi Z_c C) \to$ razão de 47,1 a 1 MHz e 1885 a 40 MHz]. A atenuação de um R–C é, portanto, plana e modesta — uma a duas ordens de grandeza aquém do que "mascarar o espectro de MHz" exigiria. A alegação permanece [HIPÓTESE], a ser demonstrada por medição da função de transferência de um supressor R–C comercial na faixa 100 kHz–100 MHz — [INSERIR CITAÇÃO: não há medição publicada localizada].

### 3.4 Ressalva estrutural: TRV no VCB ≠ tensão nos terminais do motor — e ressalva de grandeza

Esta ressalva é o limite de validade de tudo o que se segue na Seção 4.

- A Tabela III é explicitamente "at the VCB" [FATO: doc A, p. 3, título da Tabela III].
- O ensaio normativo entre espiras aplica a tensão "between the two terminals of the sample coils" e o ensaio de isolação principal "between the coil terminals and earth" [NORMA: IEC 60034-15:2009, 4.2–4.3].
- Vollet e de Metz-Noblat comparam o nível SFI com a tensão **fase-neutro no motor** e o nível LI com a tensão **fase-terra no motor**, não com a TRV no disjuntor [LITERATURA: IPST 2007, p. 4].
- O snubber de A está no barramento do painel, a montante do cabo de 240 mm² (Seção 2.3).

**Ressalva adicional, de grandeza — não apenas de ponto de medição.** TRV é, por definição, tensão **através do *gap* aberto**, ao passo que $U_P$, $U'_P$ e o BIL de rede são níveis **fase-terra**: são categorias distintas, e não apenas nós distintos do circuito. **A não declara qual das duas a Tabela III reporta** [FATO por omissão: doc A, p. 3]. A leitura das Figs. 3–4 indica tensão **fase-terra do lado da carga**: (i) as três traces decaem exatamente a 0 kV após o desligamento completo (≈ 28 ms), o que uma tensão de *gap* não faria — ela recuperaria a senóide de 60 Hz do lado fonte; (ii) antes da separação dos contatos as amplitudes são ≈ ±3 kV, compatíveis com 1 pu = 3,397 kV fase-terra. Se essa leitura estiver correta, a comparação com $U_P$ e com o BIL de rede é **legítima em natureza**; mas isso é **[INFERÊNCIA] desta verificação, não afirmação de A**, e deve ser confirmado junto aos autores ou no arquivo ATP antes de qualquer uso.

Portanto, qualquer razão TRV/nível calculada adiante é **indicativa de ordem de grandeza**, não critério de conformidade.

---

## 4. Referencial normativo de suportabilidade

### 4.1 IEC 60034-15 — o que foi efetivamente verificado

**Edição 3.0 (2009-03)** — texto lido na amostra oficial iTeh [NORMA: https://cdn.standards.iteh.ai/samples/15848/1b914cc7cb9b4c4582e502f946666007/IEC-60034-15-2009.pdf]:

$$
U_P = 4\,U_N + 5\ [\mathrm{kV}]\quad\text{(pico, isolação principal)};
\qquad
U'_P = 0{,}65\,U_P = 0{,}65\,(4\,U_N + 5)\ [\mathrm{kV}]\quad\text{(pico, entre espiras)},
$$

com $U_N$ [kV] a tensão nominal de linha da máquina, $U_P$ o nível de impulso atmosférico normalizado (1,2 µs ± 30 % / 50 µs ± 20 %, ± 3 %, ≥ 5 impulsos de mesma polaridade) e $U'_P$ o nível de impulso de frente íngreme (SFI), aplicado por descarga oscilatória amortecida de capacitor, com **tempo de frente 0,2 ± 0,1 µs** até 35 kV (acima: 0,2 µs, +0,3/−0,1 µs) e ≥ 5 operações de chaveamento [NORMA: IEC 60034-15:2009, Tabela 1, Notas 1–4; 4.2–4.3; A.2].

Cláusulas adicionais **efetivamente verificadas**:

| Cláusula | Conteúdo verificado |
|---|---|
| 2.4 | $T_1 = 1{,}67\,(t_{90\%} - t_{30\%})$ (tempo de frente) |
| 3 | Fator de sobretensão para conversores "may be as high as 1,7 for a 3-level converter" |
| 4.4 | Ensaio alternativo à frequência industrial: $(2U_N + 1)$ kV por 1 min, rampa a 1 kV/s até $2(2U_N+1)$ kV |
| 5.1 | Ensaio de rotina em bobinas inseridas no núcleo antes do processamento: **40 % a 80 %** de $U'_P$ |
| 5.2 | Ensaio de impulso entre espiras em enrolamento completo **"not recommended"** |
| Tabela 1, Nota 5 | Níveis "may not be adequate for special operating conditions (e.g. **interrupted start** or direct connection to overhead lines)" |
| A.1 | Tensão transversal e longitudinal; maiores componentes na primeira ou última bobina; frentes de serviço "down to 0,1 µs" |
| A.3 | "no simple law has been found" para pré-calcular o pico longitudinal |

**Edição 4.0 (2025-06-06)** — mudanças declaradas no prefácio da edição publicada: harmonizar os níveis com IEEE Std 522; introduzir nível reforçado (*enhanced*); permitir ensaio até a ruptura; melhorar a avaliação de impulsos com oscilação/*overshoot*; **excluir máquinas alimentadas por conversores** do escopo; orientar a execução dos ensaios [NORMA: IEC 60034-15:2025, prefácio/escopo, via amostra NSAI e IEC Webstore]. **A Tabela 1 da edição publicada não foi acessada** [INSERIR CITAÇÃO]. Os valores usados adiante provêm do CDV 2/2199/CDV (2024), marcado "subject to change": Tabela 1 do CDV dá $U_P = 16{,}3$ kV e $U'_P = 11{,}4$ kV para $U_N = 4$ kV, com mínimos de 8 kV e 5,6 kV; níveis reforçados = padrão + 15 kV (SLI) e + 11 kV (SFI), limitados a 2× o padrão, para "very frequent switching or **aborted starts**" [NORMA: IEC CDV 60034-15, 4.2–4.3 e Tabela 1].

Verificação de consistência da inferência de forma [CÁLCULO PRÓPRIO]: $5\sqrt{2/3}\,U_N$ para $U_N =$ 4; 6,6; 13,8 kV dá 16,33; 26,94; 56,34 kV (Tabela CDV: 16,3; 26,9; 56,3), e $3{,}5\sqrt{2/3}\,U_N$ dá 11,43; 18,86; 39,44 kV (Tabela CDV: 11,4; 18,9; 39,4). A razão SFI/SLI = 0,70 coincide com a afirmação do CDV ("around 70 % of the standard lightning withstand voltage"). Ponto de cruzamento entre edições: $0{,}65(4U_N+5) = 2{,}858\,U_N$ em $U_N \approx 12{,}6$ kV — **abaixo disso, a edição 2025 fixa SFI menor que a de 2009**.

### 4.2 IEEE Std 522 — o que foi verificado e o que não foi

**Verificado em fonte primária (página IEEE SA)** [NORMA: https://standards.ieee.org/ieee/522/6940/]: IEEE Std 522-2023 ativa (aprovada 2023-09-21, publicada 2023-10-30), aplicável a máquinas de 200 kW a 100 MW; "Test voltage levels described herein **do not evaluate the ability of the turn insulation to withstand abnormal voltage surges**"; "The repetitive voltage surges (spikes) associated with Variable Frequency Drives (VFDs) are not addressed here."

Registre-se que o título e o escopo verificados restringem a norma à **isolação entre espiras** ("Guide for Testing **Turn** Insulation of Form-Wound Stator Coils for Alternating-Current Electric Machines"; "the dielectric strength of the insulation separating various turns from each other within multi-turn form-wound coils"): **a IEEE 522 não especifica nível de isolação principal (*groundwall*)**, e os valores de 3,5 pu e 5 pu abaixo são dois pontos de um **único** envelope de suportabilidade entre espiras em função do tempo de frente — não dois níveis de isolações distintas.

**Não verificado em texto primário** [LITERATURA secundária — o texto integral da norma não foi acessado]: o envelope tensão × tempo de frente (**entre espiras**), descrito como **patamares** — 0 a 100 ns: 1 pu; 100 ns a 1,2 µs: **3,5 pu**; ≥ 1,2 µs: **5 pu** — com $1\ \mathrm{pu} = \sqrt{2/3}\,U_L$ [LITERATURA secundária: Baker/SKF, p. 4–5, citando IEEE 522-1992, Fig. 1, p. 8]; e o fator de **75 % para máquinas em serviço** [LITERATURA secundária: Electrical Trader; Electrom]. Corroboração indireta do vértice de 3,5 pu: $2{,}86\,V_{LL} = 3{,}5\sqrt{2/3}$ [CÁLCULO PRÓPRIO: $3{,}5 \times 0{,}8165 = 2{,}858$] e a NOTA do CDV 2024 ("in line with the level as defined in IEEE Std 522"). **A forma exata do envelope entre 0,1 e 1,2 µs (patamar ou rampa) não foi verificada** — qualquer interpolação é [HIPÓTESE].

### 4.3 IEC 60071-1 — coordenação de isolamento

[NORMA: IEC 60071-1:2019, 3.17.2.2–3.17.2.3, amostra iTeh]: sobretensão de **frente rápida** (FFO) tem $0{,}1\ \mu\mathrm{s} < T_1 \le 20\ \mu\mathrm{s}$, $T_2 < 300\ \mu\mathrm{s}$; sobretensão de **frente muito rápida** (VFFO) tem $T_f \le 0{,}1\ \mu\mathrm{s}$, $30\ \mathrm{kHz} < f < 100\ \mathrm{MHz}$. Sobretensões em pu referem-se a $U_s\sqrt2/\sqrt3$ [NORMA: 3.17, Nota]. A norma delega a cada comitê de aparelhos a fixação dos níveis; para máquinas rotativas, o comitê é o TC 2, via IEC 60034-15 [NORMA: IEC 60034-15:2009 e :2025, Introdução].

BIL de **rede**: a Tabela 2 da IEC 60071-1 não lista $U_m = 4{,}4$ kV; a linha imediatamente superior é $U_m = 7{,}2$ kV → **40 ou 60 kV** de pico (1,2/50 µs) e 20 kV eficazes por 1 min [NORMA: IEC 60071-1:2006, Tabela 2, p. 18; a identidade dos valores na edição 2019 não foi conferida]. Este BIL aplica-se ao **equipamento de rede** (cubículo, cabo, transformador), **não** à máquina.

### 4.4 IEC 60034-18-41 e -42 — impulsos repetitivos

Aplicam-se a máquinas alimentadas por conversores, **não** ao motor DOL do Documento A, mas fornecem a base metodológica do módulo de RUL:

| Conceito | Definição verificada | Fonte |
|---|---|---|
| Tipo I | Sistema isolante "not expected to experience partial discharge activity"; geralmente ≤ 700 V, enrolamento aleatório | [NORMA: IEC 60034-18-41:2014, Introdução] |
| Tipo II | Sistema "expected to experience and withstand partial discharge activity"; pré-formadas, > 700 V | [NORMA: IEC 60034-18-42:2017+AMD1:2020, escopo] |
| PDIV | Tensão de início de DP (para impulso: valor pico a pico) | [NORMA: IEC 60034-18-41:2014, 3.2] |
| RPDIV | Mínimo valor pico a pico com **mais de 5 pulsos de DP em 10 impulsos de tensão de mesma polaridade** ("more than five PD pulses occur on ten voltage impulses of the same polarity") | [NORMA: idem, 3.9, amostra iTeh lida] |
| $t_r$ | Tempo de subida 10–90 % | [NORMA: idem, 3.13] |
| $U_j$ | *Jump voltage* | [NORMA: idem, 3.22] |
| Categorias de estresse | A (benigna, $OF \le 1{,}1$); B (moderada, 1,1–1,5); C (severa, 1,5–2,0); D (extrema, 2,0–2,5), com $t_r = 0{,}2 \pm 0{,}1$ µs | [LITERATURA: CIGRE WG D1.43, TB 703, p. 11, 33, 43, reproduzindo a Tabela 4/B.1 da norma — **tabela original não acessada**] |
| Extrapolação de vida (Tipo II) | Regra de aceleração em frequência **combinada com a lei de potência inversa** | [LITERATURA: CIGRE WG D1.43, TB 703, p. 35; NORMA: IEC 60034-18-42] |

Registre-se também a IEC TS 60034-18-42 na sua forma de qualificação e a IEC TS 60034-27-5:2021, que trata da medição off-line de PDIV/PDEV sob impulsos repetitivos [NORMA: https://webstore.iec.ch/en/publication/31870].

### 4.5 Níveis calculados para 4,16 kV e confronto com a Tabela III

Todos os valores desta subseção são [CÁLCULO PRÓPRIO] sobre $U_N = 4{,}16$ kV, com $1\ \mathrm{pu} = 3{,}397$ kV.

| Referência | Isolação principal (fase-terra) | Entre espiras / SFI | Observação |
|---|---|---|---|
| IEC 60034-15:2009 | $U_P = 4(4{,}16)+5 = \mathbf{21{,}64}$ kV (Tabela 1, 4 kV: 21 kV) | $U'_P = 0{,}65 \times 21{,}64 = \mathbf{14{,}07}$ kV (Tabela 1, 4 kV: 14 kV) | 1,2/50 µs e 0,2 ± 0,1 µs |
| IEC 60034-15:2025 (via CDV) | $\approx 5\ \mathrm{pu} = \mathbf{16{,}98}$ kV (CDV, 4 kV: 16,3) | $\approx 3{,}5\ \mathrm{pu} = \mathbf{11{,}89}$ kV (CDV, 4 kV: 11,4) | mínimos 8 / 5,6 kV não governam |
| IEC 60034-15:2025 reforçado | $\approx 31{,}98$ kV (teto 33,97 kV) | $\approx 22{,}89$ kV (teto 23,78 kV) | mediante acordo, para *aborted starts* |
| IEEE 522 (bobinas novas) — **isolação ENTRE ESPIRAS apenas** | **não especificado** pela norma | Dois pontos de **um único** envelope tensão × tempo de frente: **5 pu = 16,98 kV** para $T_1 \ge 1{,}2$ µs e **3,5 pu = 11,89 kV** $= 2{,}86\times4{,}16$ para frentes curtas | O título e o escopo da norma são "Guide for Testing **TURN** Insulation of Form-Wound Stator Coils…", cobrindo "the dielectric strength of the insulation separating various turns from each other" — **a IEEE 522 não fixa nível de isolação principal (*groundwall*)** [NORMA: IEEE 522-2023, título e escopo, página IEEE SA; LITERATURA secundária para os valores do envelope] |
| IEEE 522-2023 (máquinas em serviço, 75 % — **entre espiras**) | — | $0{,}75\times3{,}5\ \mathrm{pu} = 0{,}75\times11{,}89 = \mathbf{8{,}92}$ kV | A fonte secundária diz "testing used machines at 75 % of **the standard surge voltage**", sendo esta o nível de bobina nova ($2{,}86\,V_{LL} = 3{,}5$ pu) [LITERATURA secundária: Electrical Trader — HIPÓTESE a verificar no texto primário] |
| Ensaio 50/60 Hz (2009, 4.4) | 9,32 kV eficazes (1 min); rampa a 18,64 kV | — | Pico do **patamar de 1 min** = $9{,}32\sqrt2 = 13{,}18$ kV. A comparação que a **norma** faz é outra: NOTA 1 de 4.4 — "The rated impulse levels in Table 1, Columns 2 and 3, are lower than the peak value $2\sqrt2(2U_N + 1\ \mathrm{kV})$ derived from this test", que para 4,16 kV vale **26,36 kV**, superior a 21,64 e 14,07 kV [NORMA: IEC 60034-15:2009, 4.4, NOTA 1, amostra iTeh lida; CÁLCULO PRÓPRIO] |
| Rotina em bobinas inseridas (5.1) | — | 5,63 a 11,26 kV (40–80 % de $U'_P$) | [CÁLCULO PRÓPRIO] |
| IEC 60071-1, rede $U_m = 7{,}2$ kV | BIL 40 ou 60 kV | — | **não se aplica à máquina** |

**Confronto com a Tabela III** [CÁLCULO PRÓPRIO; ver ressalva da Seção 3.4]:

| Caso | kV | pu | / $U_P$ 2009 (21,64) | / $U'_P$ 2009 (14,07) | / 5 pu (16,98) | / 3,5 pu (11,89) | / BIL de rede 60 kV |
|---|---|---|---|---|---|---|---|
| B sem snubber | 41,44 | 12,20 | **1,91** | **2,95** | **2,44** | **3,49** | 0,69 |
| C sem snubber | 38,30 | 11,28 | 1,77 | 2,72 | 2,26 | 3,22 | 0,64 |
| A sem snubber | 30,24 | 8,90 | 1,40 | 2,15 | 1,78 | 2,54 | 0,50 |
| B com snubber | 13,65 | 4,02 | 0,63 | **0,97** | 0,80 | **1,15** | 0,23 |
| C com snubber | 9,98 | 2,94 | 0,46 | 0,71 | 0,59 | 0,84 | 0,17 |
| A com snubber | 6,35 | 1,87 | 0,29 | 0,45 | 0,37 | 0,53 | 0,11 |

Cinco leituras [INFERÊNCIA FÍSICA a partir dos números acima]:

1. **Sem mitigação, o evento está fora de qualquer envelope de qualificação.** Os 12,20 pu excedem **todos** os envelopes normativos calculados — $1{,}91\times U_P$(2009), $2{,}95\times U'_P$(2009), $2{,}44\times5$ pu e $3{,}49\times3{,}5$ pu — e superam inclusive o nível **reforçado** de 2025 (≈ 32 kV). A comparação com dados de ruptura **sugere** ruptura provável, mas **não é conclusiva**, por duas razões que precisam ser ditas: (i) os 7,8 pu de Gupta, Lloyd e Sharma (1990) são o **maior nível de um ensaio de *endurance* que não produziu degradação mensurável** em 2 de 3 estatores — excedê-los é sair da faixa ensaiada, não evidência de ruptura (é como **limiar** que esse dado é corretamente usado em 5.4/D2 e 5.6); (ii) os enunciados de Gupta et al. 1987, Parte 2 são **limites inferiores** ("ruptura ≥ 5 pu na maioria dos 17 motores, ≥ 10 pu em máquinas novas"), obtidos com impulsos de frente **0,1 µs**, ao passo que a frente equivalente do evento de A é ≈ 2,75 µs — uma década mais longa, região em que o envelope admissível é **maior** (5 pu contra 3,5 pu), conforme a própria lição de Vollet registrada no item 4 abaixo. Não escrever, portanto, "faixa de ruptura típica de 5–10 pu": não há teto de 10 pu nas fontes [LITERATURA: Gupta et al. 1987, Parte 2 e Gupta, Lloyd e Sharma 1990, resumos via OpenAlex].
2. **A máquina é o elo mais fraco da coordenação — mas a rede não está necessariamente coberta.** A Tabela 2 da IEC 60071-1 oferece **dois** níveis alternativos para $U_m = 7{,}2$ kV, 40 **ou** 60 kV, e a escolha cabe ao projetista/comitê de aparelhos conforme a exposição, não é automática. Assim: 41,44 kV são **69 % do alternativo superior (60 kV)** e **104 % do alternativo inferior (40 kV)**, contra **191 % do nível de isolação principal da máquina** (21,64 kV) [NORMA: IEC 60071-1:2006, Tabela 2; CÁLCULO PRÓPRIO: $41{,}44/60 = 0{,}691$; $41{,}44/40 = 1{,}036$; $41{,}44/21{,}64 = 1{,}915$]. A máquina permanece o elo mais fraco por margem de **1,8× a 2,8×**, o que justifica proteção **nos terminais do motor** e não apenas no painel [INFERÊNCIA; concordante com Vollet 2007, p. 5]; mas, com o nível de 40 kV, o evento **também excede o BIL do cubículo**. O critério de escolha do nível de rede deve ser declarado **antes** de qualquer conclusão de coordenação. Vale ainda a ressalva de grandeza da Seção 3.4: A não declara se a Tabela III é tensão de *gap* ou fase-terra.
3. **Com snubber, o evento cai para a vizinhança da suportabilidade — não para o desprezível.** 4,02 pu equivale a **97 % de $U'_P$(2009)**, **115 % de 3,5 pu (2025/IEEE)** e **153 % do critério de 75 % para máquinas em serviço** ($13{,}65/8{,}92 = 1{,}530$) [CÁLCULO PRÓPRIO]. **O critério de 75 % é único e tem base IEEE**: $0{,}75\times3{,}5$ pu = 8,92 kV. É exatamente a faixa que **justifica um modelo de dano incremental em vez de um critério passa/não passa**.
4. **A comparação apenas por magnitude é insuficiente.** Vollet e de Metz-Noblat aprovaram um motor de 11 kV pelo critério de amplitude (24 kV < 32 kV) e o reprovaram pelo tempo de subida: "the time rise was shorter than the wave defined in the IEC 60 034-15" [LITERATURA: IPST 2007, p. 5–6]. A Tabela III de A não permite essa comparação porque não fornece $T_1$.
5. **Comparativo de dv/dt de ensaio** [CÁLCULO PRÓPRIO]: um SLI de 21,64 kV em 1,2 µs equivale a ≈ 18 kV/µs; um SFI de 14,07 kV em 0,2 µs equivale a ≈ 70 kV/µs (≈ 141 kV/µs a 0,1 µs). As RRRV de A (13–19 kV/µs) são da ordem do SLI e **uma década abaixo** do dv/dt do ensaio SFI — porém medidas no disjuntor e com passo de 1 µs.

**Sobre a alegação de conformidade de A.** O artigo afirma que os resultados apoiam "compliance with the SFI withstand philosophy of IEC 60034-15 and the insulation coordination limits of IEC 60071-1" [FATO: doc A, p. 4, V-C], mas **nenhum nível normativo é transcrito, nenhuma forma de onda normalizada é usada e nenhuma comparação numérica resultado × envelope é apresentada** [FATO por omissão; verificado em p. 2 e p. 4]. Além disso, a fórmula $4U_N + 5$ / 0,65 pertence à edição 2009, enquanto a referência [21] de A é a edição 2025, que adota ≈ 5 pu / 3,5 pu — o que **reduz** o SFI para 4,16 kV de 14,1 para ≈ 11,9 kV. Qualquer alegação de conformidade deve dizer **com qual edição**.

---

## 5. Efeito cumulativo de múltiplas reignições

### 5.1 O mecanismo, elo por elo

A cadeia causal, com a fonte de cada elo:

1. **Chopping e reignição.** O arco a vácuo colapsa em $I_{ch}$ de poucos ampères; a energia $\tfrac12 L I_{ch}^2$ é forçada na capacitância do lado da carga [FATO: doc A, p. 2, II-A]. A forma fechada da sobretensão de chopping, por balanço de energia, é
$$
\hat U_m = \sqrt{U_{pf}^2 + I_0^2\,\frac{L_b}{C_b}},
$$
com $\hat U_m$ [V] o pico, $U_{pf}$ [V] a tensão de fase no instante do corte, $I_0$ [A] a corrente cortada, $L_b$ [H] e $C_b$ [F] a indutância e a capacitância do lado da carga [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, §II-A]. Ordem de grandeza para A: com $L_{eq} = 8{,}98$ mH e $I_{ch} = 2$ A, a energia presa é 18 mJ [CÁLCULO PRÓPRIO]; com $C = 10$ nF [HIPÓTESE], $\Delta V \approx I_{ch}\sqrt{L/C} \approx 1{,}9$ kV. **O chopping isolado não explica picos de 30–41 kV** — a escalada decorre das reignições, como o próprio A afirma [FATO: doc A, p. 3, V-A].
2. **Escalada.** Se a TRV excede a suportabilidade em recuperação, o *gap* rompe e o ciclo se repete, gerando "a burst of steep front voltage escalations" [FATO: doc A, p. 2]. A literatura confirma: "This sequence of events may be repeated several times (up to 10) with increasing amplitude. The process will stop only when the breaker gap strength reaches a value higher than the TRV" [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, §II-B].
3. **Impulso íngreme nos terminais.** Cada reignição impõe um SFI [FATO: doc A, p. 2, II-B].
4. **Concentração nas primeiras espiras.** Seção 2 deste documento [NORMA: IEC 60034-15:2009, A.1, A.3; LITERATURA: Ferreira e Ferreira 2021].
5. **PDIV excedido → descargas parciais.** Acima do PDIV a degradação é "almost continuous"; a DP tem atraso estatístico de iniciação, de modo que a sobretensão efetiva é maior quanto maior o *slew rate*, e a magnitude das DP cresce quando o tempo de subida diminui [LITERATURA: CIGRE WG D1.43, TB 703, p. 21, 25–27, Figs. 26–27]. Evidência experimental direta em bobina pré-formada de 2 kV: o PDIV caiu de 3,95 para 3,71 kV ao reduzir o tempo de subida de 800 ns para 100 ns [LITERATURA: Hu et al., IEEE OJPEL 2, 2021, Fig. 14, https://pmc.ncbi.nlm.nih.gov/articles/PMC8152218/] — **ressalva importante: essa medição é da isolação FASE-TERRA, não da isolação entre espiras**, conforme a própria conclusão dos autores; a queda declarada de −6,5 % difere do cálculo direto $(3{,}95-3{,}71)/3{,}95 = -6{,}1\%$ [CÁLCULO PRÓPRIO — inconsistência interna da fonte].
6. **Treeing elétrico.** Iniciação por injeção/extração de elétrons quentes em protrusões, com campo de iniciação ≈ 400–600 kV/mm em PE sob CA; carga espacial desprezível acima de 50 Hz; surtos de polaridade positiva mais severos; o número de surtos para iniciar uma árvore cresce com a taxa de repetição [LITERATURA: CIGRE WG D1.43, TB 703, p. 29–30].
7. **Perda de suportabilidade.** Seção 6.

### 5.2 Quantas reignições por manobra? O que a literatura efetivamente reporta

| Fonte | O que reporta | Grandeza reportada |
|---|---|---|
| Vollet e de Metz-Noblat, IPST 2007, p. 2 | "may be repeated several times (**up to 10**) with increasing amplitude"; corrente de AF 100–200 kHz | teto por sequência |
| Wong, Snider e Lo, IPST 2003, p. 4–6 | O número de reignições **aumenta** quando a RRDS cai (50 → 30 V/µs) e quando a capacidade de extinção de AF é **maior**; escalada mais severa para RRDS de 20–30 V/µs e tempo de arco de 0–100 µs; 48 modelos × 100 casos de Monte Carlo | dependências, sem tabela de contagem |
| Xue e Popov, IPST 2013, Tab. V | Em 50 aberturas simuladas, **12 / 18 / 17** apresentaram reignição (motores de 10,2 / 5,5 / 1,25 MW, 11 kV); pico até **10,4 pu** (motor de 1,25 MW em partida) | fração de aberturas com reignição (24–36 %), **não** o número por abertura |
| Abdulahovic, tese Chalmers 2011, p. 101–120 | Carga indutiva com chopping de 2,5–5 A: "very large number of reignitions"; abertura em vazio: poucas, < 1 pu; simulação e medição **divergem na contagem**, mas coincidem em repetitividade e no pico/frente do maior *strike* | qualitativo |
| Glinkowski, Gutierrez e Braun, IEEE TPWRD 12(1), 1997 | Probabilidade de reignições múltiplas "proportional to the arc angle and is very small"; capacitores de proteção reduzem a TRV mas **aumentam** a corrente de reignição | probabilidade |
| Gupta et al. 1987, Parte 1 (EPRI) | Dispositivos a vácuo produzem "numerosos transitórios de frente íngreme por operação de **fechamento**"; até 4,6 pu na partida; **sem surtos significativos na abertura de motores em regime** | medição de campo, 33 motores |
| IEC 62271-110:2023, 3.6 | O evento de AF é "single or multiple" | definição |

**Síntese** [INFERÊNCIA]: não existe, nas fontes acessadas, distribuição estatística publicada do número de reignições por manobra de motor de MT. Há um teto ("até 10"), dependências qualitativas (RRDS, capacidade de extinção de AF, tempo de arco, capacitância de carga) e frações de aberturas com reignição.

### 5.3 A premissa do usuário "5 a 7 reignições por ciclo"

Três afirmações, nesta ordem:

1. **A premissa NÃO consta do Documento A.** Verificado por leitura integral de p. 1–5: o artigo usa apenas "successive arc reignitions" (p. 1), "multiple reignitions" (p. 1), "burst of steep front voltage escalations" (p. 2) e "the successive reignitions escalate the TRV" (p. 3) [FATO: doc A, p. 1–3]. **Não deve ser atribuída ao artigo** [PREMISSA DO USUÁRIO].
2. **Está dentro do envelope publicado, mas não é um valor típico documentado.** O único número verificado é "várias vezes (até 10)" [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, p. 2]; Wong reporta variação com RRDS e di/dt sem tabular; Xue & Popov tabulam a frequência de aberturas com reignição, não a contagem por abertura; Abdulahovic reporta divergência entre simulação e medição na contagem [HIPÓTESE do usuário, parcialmente suportada].
3. **A unidade "por ciclo" é ambígua e provavelmente inadequada.** A sequência de reignições ocorre nos primeiros ~0,1–3 ms após a separação dos contatos (modo A de Wong) ou até o próximo zero de 50/60 Hz (modo B) [LITERATURA: Wong, Snider e Lo, IPST 2003, p. 2, 5 — estudo de rede de 50 Hz]; **não é um fenômeno que se repita a cada ciclo da frequência industrial** [INFERÊNCIA]. Definição recomendada para o módulo: **reignições por polo por manobra**, $n_r$, tratada como variável aleatória com prior discreto em $[0, 10]$ [HIPÓTESE de modelagem].

**Ressalva sobre a janela de 0,1–3 ms** [CÁLCULO PRÓPRIO]: essa janela decorre de RRDS **típicas** (20–50 kV/ms). Com a RRDS parametrizada no Documento A, a suportabilidade do *gap* só alcança 41,44 kV em $t \approx 5{,}50$ ms após a extinção do arco (Seção 3.1), de modo que a sequência simulada por A é **necessariamente mais longa** que a janela típica. Isso é consequência direta da parametrização adotada, **não** da física do VCB comercial, e deve ser dito explicitamente sob pena de o leitor confrontar a janela com a Fig. 3 e ver contradição.

Contagem visual na Fig. 3 de A (sem snubber): sequência crescente de excursões na fase B em ≈ 0,6 ms, com **6 a 10 excursões distinguíveis**; a contagem e a atribuição de cada degrau intermediário a uma fase específica **não são determináveis com confiabilidade** a partir da figura [FATO: doc A, Fig. 3, p. 4 — leitura de figura; INFERÊNCIA visual]. Em ampliação 6× do recorte 0,0245–0,0255 s da imagem nativa, as excursões positivas nítidas da fase B (laranja) leem-se em ≈ 19 kV e ≈ 22–23 kV abaixo do pico; os patamares de ≈ 28 e ≈ 37 kV da escalada são traçados **predominantemente pela fase C** (amarelo), com o laranja aparecendo apenas no topo do maior pico. **Qualquer sequência numérica atribuída à fase B é, portanto, [HIPÓTESE de leitura de figura], não dado** — ver H4 na Seção 5.5.

### 5.4 Equações de acúmulo de dano, com origem de cada uma

**(D1) Lei de potência inversa (IPL) — envelhecimento elétrico.**

$$
L(V) = k\,V^{-n}
\qquad\Longleftrightarrow\qquad
\log L = \log k - n\,\log V,
$$

com $L$ [h ou n.º de impulsos] a vida, $V$ [V] a tensão (ou $E$ [kV/mm] o campo), $k$ constante do material e $n$ [adimensional] o coeficiente de resistência à tensão (VEC) [LITERATURA: Feilat, IntechOpen 2018, eq. (21), DOI 10.5772/intechopen.72423]. Para impulsos, a forma equivalente é $N(V) \propto V^{-n}$ (número de impulsos até ruptura), verificada em epóxi ponta-plano com frente de 500 ns: "As the applied surge voltage increases, the life decreases following an inverse power law" [LITERATURA: CIGRE WG D1.43, TB 703, p. 29, Fig. 31].

**Expoentes medidos** [LITERATURA: CIGRE WG D1.43, TB 703, Figs. 24 e 33]:

| Condição (pares torcidos, fio esmaltado) | $n$ |
|---|---|
| 50 Hz senoidal, ar | 6,4 |
| 10 kHz senoidal | 5,3 |
| 10 kHz unipolar | 7,1 |
| 10 kHz bipolar | 3,8 |
| 50 Hz, com / sem DP | 11,7 / 8,7 |
| 10 kHz, com / sem DP | 6,4 / 4,5 |

**Advertência**: todos esses expoentes provêm de fio esmaltado e epóxi puro. **Nenhum valor de $n$ para mica-epóxi pré-formada de MT sob impulsos de VCB foi localizado** — [INSERIR CITAÇÃO].

**(D2) IPL com limiar.**

$$
L = C\,(E - E_0)^{-m}
\qquad\text{ou}\qquad
t_f = t_0\left(\frac{E}{E_0}\right)^{-b},
$$

com $E_0$ [kV/mm] o campo-limiar de envelhecimento ("electrical fatigue") [LITERATURA: Tommasini, CERN, arXiv:1104.0802; Choudhary et al., *Energies* 15:3408, 2022, eqs. (1), (4)]. **Evidência empírica de existência de limiar**: 1 000 a 8 000 surtos de 3,0 a 7,8 pu com frente de 0,1 µs **não produziram degradação mensurável em dois de três estatores** [LITERATURA: Gupta, Lloyd e Sharma, IEEE TEC 5(2):320–326, 1990, resumo via OpenAlex, DOI 10.1109/60.107228]. Os limiares físicos normativos correspondentes são PDIV e RPDIV [NORMA: IEC 60034-18-41:2014, 3.2, 3.9].

**(D3) Dependência do tempo de frente / dv/dt.**

$$
L \propto \left(\frac{\mathrm{d}v}{\mathrm{d}t}\right)^{-n'}
$$

[LITERATURA: Yang et al., *High Voltage*, 2023, resumo, DOI 10.1049/hve2.12375: "vida da isolação espira-a-espira proporcional à n-ésima potência de dv/dt (até 20 V/ns)"]. Suporte qualitativo independente: "the shorter the rise time, the larger the PD magnitudes; thus, the shorter lifetime" [LITERATURA: Ghassemi, IEEE TDEI 2019 / arXiv:2007.03194, p. 2].

**(D4) Regra de Miner (dano linear cumulativo).**

$$
D = \sum_i \frac{n_i}{N_i},\qquad \text{falha em } D = 1;
\qquad\text{forma contínua (térmica): } \mathrm{LF} = \int_{t_1}^{t_2}\frac{\mathrm{d}t}{L(\theta(t))},
$$

com $n_i$ o número de ciclos/eventos aplicados no nível de estresse $i$ e $N_i$ o número suportável nesse nível [LITERATURA: ReliaSoft HotWire 116; Theofanous et al., *Energies* 18:6087, 2025, eqs. (17)–(19), (25)]. **Limitações declaradas**: usa apenas valores esperados, assume relação linear vida–estresse e independência da ordem de aplicação [LITERATURA: ReliaSoft]. Aplicação de referência em prognóstico por perfil de missão: $CL_n = 100/N_{n,\text{life}}$ [%], $CL_{1\,\text{ano}} = \sum_{n=1}^{460} CL_n$ [FATO: artigo 12, Ma et al., IEEE TPEL 30(2), eqs. (1)–(2), p. 5].

**(D5) Modelos multi-estresse.** Simoni:

$$
L(V,T) = t_0\left(\frac{V}{V_0}\right)^{-n}\exp\!\left(-B\,c_T\right),\qquad c_T = \frac{1}{T_0}-\frac{1}{T},
$$

com $T$ [K] a temperatura e $B$ [K] o parâmetro térmico [LITERATURA: Feilat 2018, eq. (26); INSERIR CITAÇÃO primária: Simoni 1981/1984; Montanari, Mazzanti e Simoni, IEEE TDEI 9:730–745, 2002]. **Nota de sinal** [INFERÊNCIA FÍSICA]: Feilat imprime $\Delta(1/T) = 1/T - 1/T_0$, o que, com $B>0$, faria a vida **crescer** com a temperatura — fisicamente incorreto; adotar $c_T = 1/T_0 - 1/T$. Ramu: $L(V,T) = K(T)\,V^{-n(T)}\exp(-B\,c_T)$ com $K(T) = \exp(K_1 - K_2 c_T)$ e $n(T) = \exp(n_1 - n_2 c_T)$ [LITERATURA: Feilat 2018, eq. (27)]. Montanari (probabilístico):

$$
L_p(V,T) = L_S\left(\frac{V}{V_S}\right)^{-n}\big[-\ln(1-p)\big]^{1/\beta(T)},
$$

com $p$ a probabilidade de falha e $\beta$ o parâmetro de forma de Weibull [LITERATURA: Feilat 2018, eq. (29)]. Crine (termodinâmico): $t = (h/2fkT)\exp(\Delta G/kT)\,\mathrm{csch}\!\left(\tfrac12\varepsilon_0\varepsilon'\Delta V F^2/kT\right)$, com $\Delta G \approx 1{,}28$ eV e limiar de 9–12 kV/mm em XLPE [LITERATURA: Crine, Jicable 2007, eqs. (1)–(2)]. DMM (Dissado–Mazzanti–Montanari), seis parâmetros [LITERATURA: Cooper, Dissado e Fothergill, IEEE TDEI 12(1):1–10, 2005, eq. (19)].

**(D6) Parcela térmica.** Arrhenius–Dakin e Montsinger:

$$
L(\theta) = L_0\exp\!\left[-B\left(\frac{1}{\theta_0}-\frac{1}{\theta}\right)\right];
\qquad
L(\theta) = L_0\,2^{(\theta_0-\theta)/\mathrm{HIC}},\quad \mathrm{HIC} = 8\text{–}15\ ^\circ\mathrm{C},
$$

com $B = E_a/k_B$ [K] e HIC (*halving interval of the temperature*) [°C] [LITERATURA: Theofanous et al., *Energies* 18:6087, 2025, eqs. (5), (9)–(10)]. Energias de ativação típicas: epóxi 110–170 kJ/mol; poliimida 180–240 kJ/mol [idem, Tabela 1]. A NEMA adota $k = 10\ ^\circ$C para expectativa de vida térmica relativa [NORMA: NEMA MG 1 Parte 31, 31.4.1.2].

**(D7) Acumulador por evento proposto para o módulo de RUL** [HIPÓTESE de modelagem — **todos** os parâmetros a calibrar]:

$$
\Delta D_m = \sum_{j=1}^{n_{r,m}} \frac{1}{N_j},
\qquad
N_j = N_0\left(\frac{a(t_{f,j})\,V_{pk,j} - V_{th}}{V_{ref} - V_{th}}\right)^{-n}\left(\frac{t_{f,j}}{t_{f,0}}\right)^{m} 2^{(\theta_j-\theta_0)/\mathrm{HIC}},
$$

com $1/N_j = 0$ sempre que $a(t_{f,j})V_{pk,j} \le V_{th}$; e

$$
D(t) = \sum_{m\,\le\, t}\Delta D_m + \int_0^t \frac{\mathrm{d}t'}{L(\theta(t'))},
\qquad
\widehat{\mathrm{RUL}}_N = \frac{1 - D(t)}{\mathbb{E}[\Delta D_m]},
\qquad
\widehat{\mathrm{RUL}}_t = \frac{\widehat{\mathrm{RUL}}_N}{\lambda_m},
$$

em que $m$ indexa manobras, $j$ indexa reignições dentro de uma manobra, $n_{r,m}$ é o número de reignições da manobra $m$, $V_{pk,j}$ [V] o pico da $j$-ésima frente **no terminal do motor**, $a(t_f)$ [adimensional] a fração que recai sobre a primeira bobina, $t_{f,j}$ [s] o tempo de frente, $V_{th}$ [V] o limiar de dano, $V_{ref}$ [V] e $N_0$ [eventos] o par de referência da curva de vida, $m > 0$ o expoente que penaliza frentes curtas, $\theta_j$ [°C] a temperatura do enrolamento no evento e $\lambda_m$ [manobras/ano] a taxa de manobras severas. A saída deve ser **distribuição** (percentis B10/B50 de Weibull) obtida por Monte Carlo sobre $n_r$, $V_{pk}$, $t_f$ e os parâmetros do VCB, com nível de confiança explícito [NORMA: ISO 13381-1:2015, 3.3, 3.9].

### 5.5 Exemplo numérico: fração de vida consumida por manobra

**Hipóteses declaradas** (todas [HIPÓTESE], nenhuma verificada):

- H1: $a(t_f) \equiv$ constante e a tensão no terminal do motor $\equiv$ TRV no VCB. Isso faz $a$ cancelar-se na razão $V/V_{ref}$ e é **conservador quanto ao ponto de medição** (ignora reflexões no cabo, que tendem a aumentar $V$ no motor).
- H2: par de referência $N_0 = 10^4$ eventos a $V_{ref} = 7{,}8$ pu, ancorado na ordem de grandeza de Gupta, Lloyd e Sharma (1 000–8 000 surtos a 3,0–7,8 pu **sem degradação mensurável** em 2 de 3 estatores) — portanto uma referência **otimista**, já que a fonte não observou falha.
- H3: sem limiar ($V_{th}=0$) e sem correção de frente ($m=0$) e térmica, para isolar o efeito do expoente $n$.
- H4 **[HIPÓTESE de leitura de figura — não determinável]**: sequência de reignições sem snubber lida na Fig. 3 como 18 → 23 → 28 → 37 → 41,44 kV (5 excursões) e, com snubber, evento único de 13,65 kV na Fig. 4. **Esta hipótese é frágil nos dois ramos e a assimetria entre eles enviesa o resultado a favor da mitigação**; ela é mantida apenas para fixar um caso de referência, e os números dela derivados **não devem ser citados como valores fechados**. Especificamente:
  - *Ramo sem snubber.* A Seção 5.3 registra 6 a 10 excursões distinguíveis, não 5, e os degraus intermediários de ≈ 28 e ≈ 37 kV parecem pertencer à fase C, não à B. Se a escada da fase B for apenas {19; 23; 41,44}, $n_{eq}(n=4) = 1{,}14$ em vez de 1,97, isto é, $\Delta D$ cai 42 % [CÁLCULO PRÓPRIO].
  - *Ramo com snubber.* Em ampliação 8× do recorte de ≈ 24,8 ms da Fig. 4, a fase B apresenta o pulso de 13,65 kV seguido de **3 a 4 excursões secundárias em ≈ 9–9,5 kV** sobre a cauda amortecida, antes do decaimento suave. Tratar o evento mitigado como excursão única zera a contribuição dessas excursões e **maximiza** a razão de dano relatada: com três excursões a $9{,}4/13{,}65 = 0{,}689$, $n_{eq}(n=4) = 1 + 3(0{,}689)^4 = 1{,}68$, o que eleva $\Delta D_{\text{com}}$ em 68 % e **reduz a razão de dano de 168 para ≈ 100** [CÁLCULO PRÓPRIO].
  - *Regra de contagem.* A regra correta é aplicar o **mesmo** critério aos dois ramos; enquanto isso não for feito, a assimetria fica aqui declarada como **hipótese conservadora invertida** (favorável ao snubber), e os resultados são reportados como faixa.
- H5: $\lambda_m = 10$ partidas abortadas/ano.

**Passo 1 — eventos equivalentes ao pico máximo** [CÁLCULO PRÓPRIO]:

$$
n_{eq} = \sum_{j}\left(\frac{V_j}{V_{\max}}\right)^{n}
$$

| $n$ | 4 | 6,4 | 9 |
|---|---|---|---|
| $n_{eq}$ sem snubber — caso de referência H4 (5 excursões) | 1,97 | 1,59 | 1,40 |
| $n_{eq}$ sem snubber — **faixa admissível** (ver nota) | **1,14–3,67** | **1,03–2,68** | **1,01–2,14** |
| $n_{eq}$ com snubber — caso de referência H4 (1 excursão) | 1,00 | 1,00 | 1,00 |
| $n_{eq}$ com snubber — **com as 3 excursões secundárias de ≈ 9,4 kV da Fig. 4** | **1,68** | **1,28** | **1,10** |

Nota sobre a faixa [CÁLCULO PRÓPRIO sobre HIPÓTESE de leitura de figura]: o limite **inferior** adota a escada mínima defensável da fase B, {19; 23; 41,44} kV (3 excursões); o limite **superior** adota 10 excursões igualmente espaçadas de 18 a 41,44 kV, teto compatível com o "até 10" de Vollet. Todos os $n_{eq}$ desta tabela repousam sobre H4 e **não devem ser citados como números fechados** — em particular 1,97 / 1,59 / 1,40.

Leitura decisiva [INFERÊNCIA], e esta **é robusta a toda a faixa**: **sob IPL com $n \ge 4$, o dano da manobra é dominado pela última (maior) reignição**; a contagem $n_r$ é secundária frente à amplitude do maior *strike*. Isso é coerente com Abdulahovic, para quem simulação e medição divergem na contagem mas coincidem no maior *strike* [LITERATURA: Abdulahovic 2011, p. 118].

**Passo 2 — fração de vida por manobra** [CÁLCULO PRÓPRIO]: $\Delta D_m = n_{eq}\,(V_{\max}/V_{ref})^{n}/N_0$, com $V_{\max} = 12{,}20$ pu (sem) e 4,018 pu (com), $V_{ref} = 7{,}8$ pu.

| $n$ | $\Delta D_m$ sem snubber | Manobras até $D=1$ | Anos ($\lambda_m=10$/ano) | $\Delta D_m$ com snubber | Manobras até $D=1$ | Razão de dano sem/com |
|---|---|---|---|---|---|---|
| 4,0 | $1{,}18\times10^{-3}$ | 846 | 85 | $7{,}04\times10^{-6}$ | $1{,}4\times10^{5}$ | **168** |
| 6,4 | $2{,}79\times10^{-3}$ | 358 | 36 | $1{,}43\times10^{-6}$ | $7{,}0\times10^{5}$ | **1,95 × 10³** |
| 9,0 | $7{,}82\times10^{-3}$ | 128 | 12,8 | $2{,}56\times10^{-7}$ | $3{,}9\times10^{6}$ | **3,06 × 10⁴** |

**Advertência sobre a razão de dano** [CÁLCULO PRÓPRIO]: os valores da última coluna decorrem do caso de referência H4 e herdam sua assimetria de contagem (5 excursões sem snubber contra 1 com snubber). Aplicando aos dois ramos a **mesma** regra — em particular contabilizando as excursões secundárias de ≈ 9,4 kV visíveis na Fig. 4 —, a razão para $n = 4$ cai de 168 para ≈ 100. **Reportar a razão como faixa: ≈ 100–170 para $n = 4$**, e proporcionalmente para os demais expoentes.

**Passo 3 — sensibilidade ao expoente** [CÁLCULO PRÓPRIO]:

- A vida em manobras varia por um **fator de 6,6** (846 → 128) ao mover $n$ de 4 para 9. Como a faixa plausível de $n$ na literatura de dielétricos é 3,8–11,7, a incerteza do expoente **domina** a estimativa de RUL.
- A razão de dano entre evento não mitigado e mitigado — que é o argumento de valor do snubber — varia de $1{,}7\times10^2$ a $3{,}1\times10^4$ **no caso de referência H4**; com regra de contagem simétrica entre os dois ramos, o limite inferior cai para ≈ $1{,}0\times10^2$ ($n=4$), conforme a advertência do Passo 2. Considerando apenas os picos, $(41{,}44/13{,}65)^n = 3{,}036^n$ dá 68 ($n$=3,8), 148 (4,5), $1{,}2\times10^3$ (6,4), $2{,}2\times10^4$ (9) e $4{,}4\times10^5$ (11,7) [CÁLCULO PRÓPRIO].
- **A contagem $n_r$ é praticamente irrelevante para $\Delta D_m$, desde que o maior *strike* seja capturado** [CÁLCULO PRÓPRIO]. Omitir as **duas menores** excursões da sequência de referência altera $\Delta D_m$ em apenas **−6,6 % ($n=4$), −1,8 % ($n=6{,}4$) e −0,4 % ($n=9$)**; errar o **pico máximo** por um fator 2 altera-o por $2^n$ = **16 a 512** vezes. Isso é coerente com — e não contraria — a conclusão do Passo 1 de que o dano é dominado pela maior reignição. **Condição de validade do enunciado**: a decomposição $\Delta D = n_{eq}(V_{\max}/V_{ref})^n$ só torna o erro de contagem desprezível se as excursões omitidas ou acrescentadas estiverem **abaixo** do máximo; se tiverem amplitude comparável a $V_{\max}$, o efeito é de ordem $\pm 2/n_{eq}$ (≈ 100 %), mas nesse caso $V_{\max}$ também muda e o erro dominante volta a ser o de amplitude. Consequência prática direta, reforçada: a prioridade de instrumentação é **medir bem o pico e a frente**, não contar reignições com precisão.
- Introduzindo o limiar (H3 relaxada): com $V_{th} = 7{,}8$ pu, o evento mitigado (4,02 pu) tem $\Delta D_m = 0$ **exatamente**, e a razão de dano torna-se infinita [INFERÊNCIA]. Com $V_{th}$ entre 4,0 e 12,2 pu, o resultado é qualitativamente o mesmo: a mitigação move o evento para **abaixo do limiar de dano**, o que é uma conclusão muito mais forte do que a redução percentual do pico.
- Introduzindo a correção de frente ($m>0$, H3 relaxada): **se a mitigação encurtar a frente real**, a razão de dano **cai**, porque no acumulador (D7) $N_j \propto (t_f/t_{f,0})^{m}$ e a RRRV da fase B reduz apenas 12,9 %, ao passo que a frente encurta — deslocando o evento para uma região de menor suportabilidade admitida [FATO: doc A, Tabela III; INFERÊNCIA]. **A magnitude não é quantificável com a Tabela III**, e por duas razões que a própria Seção 3.3 estabelece: (i) $V_{pk}/\mathrm{RRRV}$ **não é** um tempo de frente (o pico é atingido após a escalada e a maior RRRV está em outra fase); (ii) o valor "com snubber" (1,04 µs) **coincide com o passo de integração de 1 µs**, sendo derivada numérica sobre 1–3 amostras. Ordem de grandeza apenas ilustrativa, sob a hipótese $m = 1$ e $t_f$ de 2,75 → 1,04 µs: a razão de dano cairia de 168 para ≈ 64 ($n = 4$) [CÁLCULO PRÓPRIO, HIPÓTESE]. Este é o único mecanismo identificado que pode **reduzir** o benefício aparente do snubber, e é exatamente a razão técnica para exigir, no próximo passo, $T_1 = 1{,}67(t_{90}-t_{30})$ **medido por reignição** e re-simulação com passo de 10–50 ns.

**Contagem anual ilustrativa** [HIPÓTESE]: com 5–7 reignições/polo/manobra (premissa do usuário) e 10 partidas abortadas/ano, tem-se 50–70 eventos severos/ano/polo, contra $10^3$–$10^4$ surtos sem dano mensurável a 3–7,8 pu em Gupta 1990. **A fadiga só é relevante se $a(t_f)V_{pk}$ exceder $V_{th}$** — o que reforça a necessidade de **medir**, e não presumir, a fração espira-a-espira.

### 5.6 Advertência de conciliação de evidências

Há uma tensão aparente entre duas famílias de resultados:

- **CIGRE / Ghassemi / Hu**: DP e degradação aceleram fortemente quando o tempo de subida diminui; a vida decresce por IPL [LITERATURA: CIGRE WG D1.43, TB 703, Figs. 26–27; Ghassemi 2019/2020; Hu et al. 2021].
- **Gupta, Lloyd e Sharma 1990**: 1 000–8 000 surtos de 3,0–7,8 pu (0,1 µs) **não** produziram degradação mensurável em dois de três estatores.

A conciliação provável [INFERÊNCIA]: **existe limiar** (PDIV/RPDIV e campo de iniciação de treeing), e o dano cumulativo só ocorre acima dele. Um modelo de RUL que **não** incorpore limiar produzirá sistematicamente RUL pessimista para manobras rotineiras. Corrobora essa leitura o fato de que Gupta et al. 1987 (Parte 1) **não observaram surtos significativos na abertura de motores em regime**; a severidade concentra-se na interrupção de corrente de partida/rotor bloqueado [LITERATURA: resumos via OpenAlex, DOI 10.1109/TEC.1987.4765906 e .4765908; NORMA: IEC 62271-110:2023, 4.3.2]. **Os resultados de A não devem ser extrapolados a aberturas rotineiras em carga.**

---

## 6. "Redução do BIL": correção conceitual

**A correção, em duas frases.** O BIL é um **nível de suportabilidade declarado e verificado por ensaio de tipo** — um número de projeto e de coordenação, não uma propriedade que decaia com o serviço; um enrolamento envelhecido não "perde BIL", ele deixa de cumprir o BIL que lhe foi atribuído. O que decai com o envelhecimento é a **suportabilidade real** do enrolamento, e o efeito operacional correto de descrever é a **erosão da margem de coordenação**: a distância entre a solicitação máxima esperada e a suportabilidade remanescente encolhe pelos dois lados — o estresse pode crescer (degradação do VCB, cabos mais curtos, mais partidas abortadas) e a suportabilidade decresce.

**Ancoragem normativa da correção.** A própria IEC 60071-1:2019 já institui as duas peças do argumento, e convém citá-las em vez de deixar a crítica como inferência isolada: (i) a **tensão suportável nominal** é definida como "value of the test voltage, applied in a standard withstand voltage test that proves that the insulation complies with one or more required withstand voltages" — logo, um nível de **ensaio e declaração**, não uma propriedade que decaia [NORMA: IEC 60071-1:2019, 3.34, amostra iTeh lida]; (ii) o **fator de segurança** $K_s$ é o "overall factor to be applied to the co-ordination withstand voltage … accounting for all other differences in dielectric strength between the conditions **in service during life time** and those in the standard withstand voltage test" [NORMA: IEC 60071-1:2019, 3.31, amostra iTeh lida]. Ou seja, o mecanismo de margem para envelhecimento em serviço **já existe na norma**; o que se propõe abaixo é torná-lo **dependente do dano acumulado**.

**Formalização** [refinamento normativo de $K_s$; INFERÊNCIA FÍSICA, formalização própria]. Defina a margem de coordenação como razão:

$$
\gamma(t) = \frac{U_w(t)}{U_s},
\qquad
U_w(t) = U_{w,0}\,\psi\big(D(t)\big),\quad \psi(0)=1,\ \psi'<0,
$$

com $U_w(t)$ [kV] a suportabilidade real do enrolamento no instante $t$, $U_{w,0}$ [kV] a suportabilidade inicial (verificada em ensaio de tipo, igual ou superior ao BIL/nível declarado), $\psi$ a função de degradação monotonicamente decrescente do dano acumulado $D$ (Seção 5.4), e $U_s$ [kV] a solicitação de projeto (percentil alto da distribuição de sobretensões de manobra). O critério de fim de vida por coordenação é $\gamma(t) \to 1$. **O BIL entra em $U_{w,0}$, como condição inicial; ele não é a variável de estado.**

**Evidência de que $U_w$ decai:**

| Evidência | Natureza | Fonte |
|---|---|---|
| Bobinas de 4,0 / 10 / 13,8 kV envelhecidas por *voltage endurance* (IEEE 1553) e de 3,3 kV por ciclagem térmica (IEEE 1310) foram ensaiadas a surto até a falha (IEEE 522) "para avaliar o efeito adverso do envelhecimento" | ensaio dedicado; **valores numéricos não acessados** | [LITERATURA: Haq, Omranipour e Teran, IEEE EIC 2014, resumo via OpenAlex, DOI 10.1109/EIC.2014.6869351] |
| Os motores cuja suportabilidade estava abaixo dos surtos de serviço eram os **severamente envelhecidos** ou com isolação de espira mal fabricada | levantamento de campo | [LITERATURA: Gupta et al., IEEE TEC EC-2(4):674–679, 1987, Parte 3, resumo via OpenAlex] |
| Ruptura da isolação de espira ≥ 5 pu na maioria de 17 motores ensaiados (impulsos de 0,1 µs); máquinas **novas** ≥ 10 pu | ensaio; contraste novo × usado | [LITERATURA: Gupta et al., IEEE TEC EC-2(4):666–673, 1987, Parte 2, resumo via OpenAlex] |
| Redução do nível de ensaio para **75 %** em máquinas em serviço | prática normativa | [LITERATURA secundária: Electrical Trader / Electrom, citando IEEE 522-2023 — **HIPÓTESE a verificar no texto da norma**] |
| Queda de vida da isolação de massa de ≈ 58 % (sem refrigeração) e ≈ 31 % (com) sob envelhecimento por pulsos, evidenciando aquecimento dielétrico | ensaio em bobinas pré-formadas | [LITERATURA: CIGRE WG D1.43, TB 703, p. 35–36, Tab. 4] |
| Fator "novo × usado": 40–80 % de $U'_P$ já é o nível de rotina para bobinas inseridas **antes** do processamento | prática normativa | [NORMA: IEC 60034-15:2009, 5.1] |

**Como isso se aplica ao caso do Documento A** [CÁLCULO PRÓPRIO + INFERÊNCIA]:

| Camada | Nível (4,16 kV) | TRV sem snubber (41,44 kV) | TRV com snubber (13,65 kV) |
|---|---|---|---|
| BIL de **rede** ($U_m$ = 7,2 kV), alternativo **superior** | 60 kV | 69 % | 23 % |
| BIL de **rede** ($U_m$ = 7,2 kV), alternativo **inferior** | 40 kV | **104 %** | 34 % |
| Isolação principal da **máquina** (2009) | 21,64 kV | **191 %** | 63 % |
| Entre espiras da **máquina**, nova (2009) | 14,07 kV | **295 %** | 97 % |
| Entre espiras da **máquina**, em serviço — **critério de 75 %, base IEEE** ($0{,}75\times3{,}5$ pu) | **8,92 kV** | **465 %** | **153 %** |
| *(leitura auxiliar)* Entre espiras, em serviço — transposição do fator de 75 % para a base IEC ($0{,}75\,U'_P$ 2009) | 10,55 kV | 393 % | 129 % — **[HIPÓTESE: transposição do fator IEEE para a base IEC, sem respaldo em texto de norma]** |

**Uma única base para o critério de 75 %.** O fator de 75 % é atribuído à IEEE Std 522-2023 e incide sobre "the standard surge voltage" **da própria IEEE**, isto é, o nível de bobina nova de $2{,}86\,V_{LL} = 3{,}5$ pu = 11,89 kV; logo o critério é **8,92 kV** e a razão do evento mitigado é **153 %** [CÁLCULO PRÓPRIO: $13{,}65/8{,}92 = 1{,}530$], em consonância com a Seção 4.5. A linha de 10,55 kV é mantida apenas como leitura auxiliar, **explicitamente rotulada como extrapolação sem amparo normativo**; 10,55 kV e 8,92 kV **não** devem coexistir como "o" critério de 75 %.

A leitura correta [INFERÊNCIA]: com o snubber, o evento está **dentro** da suportabilidade de uma bobina nova (97 % de $U'_P$ 2009), mas **acima** da suportabilidade presumida de uma bobina em serviço (153 % do critério de 75 % na base IEEE). Isto é: **a margem de coordenação da máquina envelhecida já foi consumida, mesmo com mitigação** — não porque "o BIL caiu", mas porque $U_w(t)$ desceu e $U_s$ permaneceu alto. É exatamente essa situação que torna o RUL uma pergunta operacional e não acadêmica.

Registre-se ainda que os próprios dispositivos de supressão envelhecem: o TOR da CIGRE WG C4.76 afirma que, sob sobretensões de alta amplitude e alta inclinação, "the insulation level of these suppression devices may gradually deteriorate due to cumulative effects" e que os snubbers RC têm níveis de suportabilidade "relatively low" [CIGRE: TOR WG C4.76, 2023-07-31, p. 1–4]. O **RUL do próprio snubber** é lacuna aberta [INFERÊNCIA].

---

## 7. Métodos atuais de monitoramento

### 7.1 Tabela comparativa

Legenda de sensibilidade ao dano espira-a-espira por surto: **Direta** (o método solicita ou mede a isolação entre espiras); **Indireta** (detecta consequências: DP, curto já formado, aquecimento); **Nula/baixa** (sensível ao *groundwall* ou ao estado global). Maturidade: Ind. (prática industrial consolidada), Emerg. (produto recente/nicho), Pesq. (pesquisa).

| Método | Norma(s) | Grandeza medida | Sensibilidade ao dano espira-a-espira | On/Off | Maturidade | Limitação declarada |
|---|---|---|---|---|---|---|
| **IR / PI** | IEEE 43-2013 (*Inactive-Reserved* desde 2024-03-21); IEC 60034-27-4:2018; ABNT NBR 17094-3:2018 | $R_i$(1 min) [MΩ]; $\mathrm{PI} = R_{i,10}/R_{i,1}$ | **Nula/baixa** | Off | Ind. | "give no indication of local weak points … and the trend evaluations **cannot be used to predict the time to failure**"; "may not indicate internal voids caused by improper impregnation or thermal deterioration" [NORMA: IEC 60034-27-4:2018, Introdução] |
| **tan δ / tip-up** | IEC 60034-27-3:2015 (≥ 6 kV, com revestimento condutor de ranhura); IEEE 286 [INSERIR CITAÇÃO — não acessada] | tan δ; $\Delta\tan\delta$ por degrau de $0{,}2U_N$; tip-up $= \tan\delta(0{,}6U_N)-\tan\delta(0{,}2U_N)$ | **Nula/baixa** (integra todo o enrolamento) | Off | Ind. | Tendência "cannot be used to predict the time to failure" [NORMA: IEC 60034-27-3:2015, Introdução]. Não formalmente aplicável a 4,16 kV |
| **DP offline** | IEC 60034-27-1:2017; IEEE 1434-2014 (*Inactive-Reserved* desde 2025-03-27) | Magnitude e padrão PRPD | **Indireta** | Off | Ind. | Não detecta todos os problemas de isolação; requer parada e fonte AT |
| **DP online** | IEC 60034-27-2:2023 (≥ 3 kV, sem conversor); acopladores de 80 pF; VHF 30–350 MHz | $Q_m$ (magnitude a 10 pulsos/s); NQN | **Indireta** (quantifica *groundwall*) | On | Ind. | "there is **no evidence that the time to failure** of the stator winding insulation can be estimated using any PD quantity, even in combination with other electrical tests" [NORMA: IEC TS 60034-27-2:2012, Introdução, *Limitations* — amostra lida; **a permanência da sentença na ed. 2023 não foi verificada**]; medições comparativas, não absolutas, e "acceptance criteria with simple limits … cannot be established" [NORMA: IEC 60034-27-2:2023, Introdução — amostra lida] |
| **Ensaio de surto / comparação de surto (EAR)** | IEEE 522-2023 (200 kW–100 MW); IEC 60034-15 (bobinas-amostra) | Deslocamento da forma de onda oscilatória; $\mathrm{EAR} = 100\,A_3/A_2$ | **DIRETA** — único método normalizado que solicita a isolação entre espiras | Off | Ind. | "do not evaluate the ability of the turn insulation to withstand **abnormal** voltage surges"; ensaio em enrolamento completo "not recommended" [NORMA: IEEE 522-2023, escopo; IEC 60034-15:2009, 5.2]. Potencialmente destrutivo |
| **Hipot CC / CA** | IEEE 95-2002 (*Inactive-Reserved*); IEEE 56-2016 | Corrente de fuga × tensão; prova de suportabilidade | **Nula** (*groundwall*) | Off | Ind. | Prova de aptidão, não de tendência |
| **MCSA / sequência negativa** | Sem norma | Impedância efetiva de sequência negativa; assimetria de corrente | **Indireta** — detecta o **curto já existente**, não a fadiga | On | Emerg. | Sensibilidade reportada a 1 % das espiras em curto (laboratório, com inversor); robustez limitada com VFD e desequilíbrio de alimentação [LITERATURA: Ruzimov et al., *Sensors*, 2025] |
| **Corrente de fuga + EKF** | Sem norma | *Overshoot* pico a pico da corrente de fuga transitória a degrau de tensão | **Indireta/baixa** | On | Pesq. | Validado com **envelhecimento térmico** em estatores BT de 5 kW (n = 3), pulsos de 160 V que "were not designed to contribute to the degradation of the insulation"; monitora fase-terra [FATO: artigo 02, p. 2–4] |
| **Oscilografia de manobra (MHz)** — proposta implícita de A | Sem norma específica; IEC 60034-15 como referência de envelope | Pico, dv/dt, tempo de frente, n.º de reignições, energia, espectro **por evento** | **Direta para o ESTRESSE**, não para o estado | On (por evento) | Pesq./Emerg. | Requer ≥ 50–100 MS/s e banda ≥ 3,5 MHz para frentes de 0,1 µs [CÁLCULO PRÓPRIO]; A adquire "only during SCR conduction" [FATO: doc A, p. 2] |
| **Monitoramento de carga de ciclo de vida (LCM)** | ISO 13374-1:2003 (arquitetura); ISO 13381-1 (prognóstico) | Cargas medidas *in situ* → modelo de dano → vida consumida | **Indireta (arquitetural)** | On | Pesq. (para MT) | "If one can measure these loads in-situ, the load profiles can be used in conjunction with damage models to assess the degradation due to cumulative load exposures" [FATO: artigo 07, p. 5]; o artigo **não fornece nenhum modelo de dano** [FATO por omissão] |
| **Perfil de missão → Miner** | Sem norma | Histograma de eventos por classe de severidade; rainflow | **Indireta (arquitetural)** | Off/On | Pesq. | Ma et al. aplicam $CL_n = 100/N_{n,\text{life}}$ e $CL_{1\,\text{ano}} = \sum CL_n$ a IGBTs; mecanismo termomecânico, **sem degradação dielétrica em nenhuma parte do modelo** [FATO: artigo 12, eqs. (1)–(2), p. 5, 9] |

### 7.2 Limiares numéricos públicos disponíveis

| Grandeza | Valor | Fonte |
|---|---|---|
| IR mínimo (pré-formadas pós-1970), 40 °C, 1 min | 100 MΩ; isolação boa típica 10–100 × o mínimo | [NORMA: ABNT NBR 17094-3:2018, 6.8.2, Tab. 2] |
| IR mínimo (bobinados ≤ 1970 / campo) | $kV + 1$ MΩ → 5,16 MΩ para 4,16 kV | [NORMA: idem]; [CÁLCULO PRÓPRIO] |
| PI mínimo | 1,5 (classe A); 2,0 (B, F, H); não significativo se $R_{i,1} > 5\,000$ MΩ | [NORMA: ABNT NBR 17094-3:2018, 6.8.3] |
| Critério de aptidão | ≤ 10 000 kW: IR **ou** PI; > 10 000 kW: **ambos** | [NORMA: idem, 6.8.4–6.8.5] |
| tan δ (bobinas novas, $0{,}2U_N$) | ≤ 20 × 10⁻³ | [LITERATURA: Iris Power, citando IEC 60034-27-3, Tab. 1] |
| $\Delta\tan\delta$ por degrau; tip-up | ≤ 5 × 10⁻³; ≤ 5 × 10⁻³ | [idem] |
| $Q_m$, percentis 25/50/75/90 %, 2–< 6 kV (ar, 80 pF, 10 pps) | 7 / 24 / 71 / **208** mV | [LITERATURA: Warren, IRMC 2022, Tab. 1] |
| $Q_m$, percentis, 13–< 16 kV | 45 / 111 / 239 / **488** mV | [idem] |
| Alarme sugerido de monitor contínuo | percentil 75 (≤ 4 kV); percentil 90 (> 4 kV) | [idem, p. 2–3] |
| Regra de deterioração rápida | duplicação de $Q_m$ em ≈ 12 meses | [idem] |
| EAR (ensaio de surto) | 0–2 % idêntico; 2–4 % atenção; 4–8 % investigar; 8–15 % problema provável; > 15 % falha confirmada | [LITERATURA: Vivid Metrawatt — **fonte de fabricante, confiança baixa**] |

Observação obrigatória [LITERATURA: Warren, IRMC 2022, p. 1]: "Calibration of on-line PD test results is theoretically not possible"; os percentis valem **apenas** para instrumentação VHF com acopladores de 80 pF e a mesma separação de ruído. Transferi-los a outra instrumentação é [HIPÓTESE].

### 7.3 O que os cinco artigos-âncora efetivamente entregam

| Artigo | Contribuição transferível | O que **não** transfere |
|---|---|---|
| **Jensen, Strangas e Foster (2018)** — artigo 02 | Arquitetura completa de prognóstico online com poucos recursos: indicador $I_{leak} = \alpha e^{\beta t}$ [eq. (7)], vetor de estados $x = [I_{leak}, \alpha, \beta]^T$ [eq. (8)], EKF [eqs. (1)–(6)], limiar de falha = valor inicial do *overshoot* (falha quando o decaimento atinge 96 % do limiar), e **instrumentação de baixo custo**: detector de pico analógico (diodo de 4 ns, op-amp de 900 V/µs, capacitor de 47 nF) que reduz a exigência de 1 GSa/s para **10 MSa/s** [FATO: artigo 02, p. 5–8] | O indicador foi validado com **envelhecimento térmico** em estatores BT de 5 kW, monitorando fase-terra; os pulsos de excitação "were not designed to contribute to the degradation"; $n=3$ máquinas sem repetições e sem métrica agregada de erro. **Alerta crítico para o Documento A**: o pico do *overshoot* depende do dV/dt aplicado, e "the actual dV/dt of the switching device is **assumed to be constant** for this method to detect changes in the insulation properties" [FATO: artigo 02, p. 3] — num esquema com snubber, a variação de dv/dt **introduzida pela própria mitigação** deve ser registrada e compensada antes de usar a resposta ao impulso como precursor [INFERÊNCIA] |
| **Vichare e Pecht (2006)** — artigo 07 | Taxonomia de PHM em quatro abordagens e, sobretudo, a rota LCM: "If one can measure these loads in-situ, the load profiles can be used in conjunction with damage models to assess the degradation due to cumulative load exposures" (p. 5). Pré-processamento por **OOR + rainflow de três parâmetros** (faixa, média, rampa) e binagem em histogramas; MSET/SPRT sobre resíduos para anomalia; FMMEA como passo inicial de priorização de mecanismos | **Nenhuma equação, nenhum modelo de dano, nenhuma métrica de desempenho prognóstico** [FATO — ausência]. Recorte em eletrônica de baixa tensão; nada sobre dielétricos de MT, DP ou envelhecimento termoelétrico de isolação sólida |
| **Strangas, Aviyente, Neely e Zaidi (2013)** — artigo 09 | Único do corpus que formaliza **quanto a mitigação decidida por prognóstico imperfeito melhora o MTBF**, com caminhos de falha com e sem mitigação [eqs. (7)–(11)] e ajuste de limiares de decisão considerando falsos positivos e negativos. Reconhece que a reconfiguração "decrease the life of the insulation" — isto é, mitigar um modo pode acelerar outro | O isolamento de estator aparece apenas como falta **secundária** (envelhecimento térmico acelerado); o mecanismo primário estudado é contato intermitente. Taxa de falha constante é inadequada a desgaste [INFERÊNCIA] |
| **Ma, Liserre, Blaabjerg e Kerekes (2015)** — artigo 12 | Esqueleto "perfil de missão → carga → resistência → Miner" com **separação em três constantes de tempo** (longo: passo de 3 h por 1 ano; médio: 1 s por 3 h; curto: 0,5 ms por 0,2 s), rainflow que extrai $\Delta T_j$, $T_{jm}$ **e** $t_{cycle}$, e saída como **distribuição de vida consumida por mecanismo e por condição operativa**, não como número único | Mecanismo termomecânico (fadiga de solda e de fios de ligação); a variável de estresse é temperatura **simulada**, não medida em operação. "electrical degradation … cannot be evaluated in this paper" (p. 9). O termo RUL não aparece |
| **Wu, Wu, Tan e Xu (2024)** — artigo 13 | Vocabulário e critérios de qualidade de indicador de saúde: **monotonicidade, *trendability* e *prognosability***; distinção PHI (indicador físico) × FHI (fundido/virtual); catálogo de arquiteturas DL e do pipeline de RUL | Revisão sem experimento próprio. **Ausência verificada no texto integral** dos termos *insulation*, *stator*, *partial discharge*, *Arrhenius*, *censoring* [FATO — ausência]. O corpus revisado é dominado por degradação mecânica progressiva e eletroquímica; degradação dielétrica sob estresse impulsivo **não é contemplada nem tangencialmente** |

**Observação transversal** [INFERÊNCIA]: nenhum dos treze artigos do corpus contém simultaneamente (i) um estressor dielétrico impulsivo, (ii) um indicador de isolação de MT e (iii) um modelo estresse → dano para surtos esparsos. A lacuna que o "incremental insulation degradation model" de A pretende ocupar **não é preenchida por nenhum deles**.

---

## 8. Lacuna metodológica e proposta de contagem de estresse

### 8.1 Por que nenhum método atual converte a manobra em consumo de vida

Quatro razões estruturais, cada uma documentada:

1. **As normas de ensaio negam explicitamente a predição.** IEC 60034-27-2 (DP online), IEC 60034-27-3 (tan δ) e IEC 60034-27-4 (IR/PI) declaram, cada uma, que suas grandezas **não** permitem estimar o tempo até falha [NORMA: Introduções das três]. A literatura industrial chega à mesma conclusão: "at best a probabilistic approach would be achievable" [LITERATURA: Stone et al., Iris Power].
2. **Os envelopes de impulso são critérios de qualificação, não curvas de vida.** A IEC 60034-15 é ensaio de suportabilidade em **bobinas-amostra**, com pelo menos **cinco operações de chaveamento** no ensaio entre espiras — "The number of switching operations shall be at least five" [NORMA: IEC 60034-15:2009, 4.2] — e pelo menos **cinco impulsos de mesma polaridade** no ensaio de isolação principal — "The number of impulses shall be at least five and of the same polarity" [NORMA: idem, 4.3]. O número de solicitações que uma máquina recebe em serviço (manobras × reignições) é **ordens de grandeza maior** [INFERÊNCIA]. A norma não define dano cumulativo.
3. **Os métodos de estado são lentos e integradores; o estressor é rápido e local.** DP online, tan δ e IR integram o enrolamento inteiro e amostram em escala de meses; a solicitação espira-a-espira dura microssegundos e concentra-se em poucas espiras.
4. **Falta a função de transferência.** Converter TRV no disjuntor em tensão entre espiras exige (i) propagação no cabo e (ii) modelo de enrolamento a parâmetros distribuídos — e a própria norma declara que "no simple law has been found" para o segundo [NORMA: IEC 60034-15:2009, A.3].

**Estado do repositório** [REPO, verificado nesta sessão em HEAD `961d66a`]:

- `compute_transient_metrics` (pico, mínimo, RMS, frequência por zeros, amortecimento) **já está integrada à aplicação** — é chamada pela GUI no laço sobre `pl4.variables` do painel de resultados, pela exportação CSV e pelo relatório HTML/PDF [REPO: `app/gui/main_window.py:63, 2298`; `app/analysis/csv_export.py:13, 48`; `app/analysis/report_export.py:17, 93`], e `csv_export`/`report_export` são por sua vez importados pela GUI e pela API de projeto [REPO: `app/gui/main_window.py:60-61`; `app/llm/project_api.py:15-16`]. **O problema não é falta de chamador: é que ela produz apenas pico/mín./RMS/frequência/amortecimento — nenhuma métrica de frente e nenhuma métrica de dano** [REPO: `app/analysis/transient_metrics.py:41-88`].
- `compute_trv_metrics` (RRRV = pico/tempo ao pico e envelope IEC simplificado) é que **não tem chamador na aplicação**, sendo exercida apenas em teste [REPO: `app/analysis/transient_metrics.py:91-159`; `tests/test_analysis.py:15, 72, 79`].
- `analyze_trt` é chamada **apenas por testes**, sem ponte PL4 e sem chamador na GUI — no módulo, a única ocorrência é texto de *docstring* [REPO: `app/postprocessor/trt_analyzer.py:11, 32`; `tests/test_pp_trt_analyzer.py:24`]. `_compute_max_rrrv` **não** está órfã: é chamada internamente por `analyze_trt` [REPO: `app/postprocessor/trt_analyzer.py:299-360, 442`]. E não existe ponte PL4 → `TrtWaveform`: a classe só ocorre dentro de `trt_analyzer.py` e dos testes [REPO: `app/postprocessor/trt_analyzer.py:92`].
- O template MODELS de reignição expõe `reign_count` como saída, incrementado em dois pontos [REPO: `app/preprocessor/atp_templates/vcb_reignition.mod:64, 101, 120`].
- E, decisivamente: `grep -rniE "rainflow|weibull|arrhenius|remaining useful|prognos" app --include=*.py` retorna **vazio** [REPO: reconfirmado em HEAD `961d66a`].

Ou seja: **o repositório já mede o transitório, já o exporta e já conta reignições no modelo; o que não existe é (i) a métrica de frente na cadeia de aplicação e (ii) a camada de dano.**

### 8.2 O que a camada digital de A precisaria conter

O Documento A afirma que a camada digital extrai "peak voltage, dv/dt, absorbed energy, spectral content" e atualiza "an incremental insulation degradation model to estimate the remaining useful life" [FATO: doc A, p. 2, III-B], **sem definir nenhuma das quatro grandezas** [FATO por omissão]. Proposta de definição operacional [HIPÓTESE de projeto, ancorada nas normas indicadas]. Para cada evento $j$ (reignição, pré-ignição ou chopping) de uma manobra $m$:

$$
\mathbf{s}_{m,j} = \Big(V_{pk,j}^{\phi\text{-}g},\; V_{pk,j}^{\phi\text{-}n},\; T_{1,j},\; t_{r,j},\; (\mathrm{d}v/\mathrm{d}t)_{\max,j},\; E_{s,j},\; f_{\mathrm{dom},j},\; t_j\Big),
$$

com:

| Componente | Definição | Unidade | Origem |
|---|---|---|---|
| $V_{pk}^{\phi\text{-}g}$, $V_{pk}^{\phi\text{-}n}$ | Picos fase-terra e fase-neutro **no terminal do motor** | kV | Comparáveis a $U_P$ e $U'_P$, respectivamente [NORMA: IEC 60034-15:2009, 4.2–4.3; LITERATURA: Vollet 2007, p. 4] |
| $T_1$ | $1{,}67\,(t_{90\%} - t_{30\%})$ | µs | [NORMA: IEC 60034-15:2009, 2.4] |
| $t_r$ | $t_{90\%} - t_{10\%}$ | µs | [NORMA: IEC 60034-18-41:2014, 3.13] |
| $(\mathrm{d}v/\mathrm{d}t)_{\max}$ | Máxima derivada da frente | kV/µs | [INFERÊNCIA] |
| $E_s$ | $\displaystyle\int R_s\,i_s^2(t)\,\mathrm{d}t$ durante a condução dos SCR | J | [INFERÊNCIA FÍSICA: definição de energia em resistor; A cita "absorbed energy" sem definir] |
| $f_{\mathrm{dom}}$ | Frequência dominante do transitório | kHz–MHz | Referências: 100–200 kHz típicos [LITERATURA: Vollet 2007, p. 2]; 0,25–1,8 MHz no circuito de Helmer [LITERATURA: Wong 2003, p. 3–4] |
| $t_j$ | Instante do evento na manobra | ms | [INFERÊNCIA] |

O vetor da manobra é $\{\mathbf{s}_{m,j}\}_{j=1}^{n_{r,m}}$, com $n_{r,m}$ o número de reignições — grandeza que A não reporta. **Das oito componentes, o Documento A fornece numericamente apenas duas (pico e RRRV), e somente no disjuntor** [FATO: doc A, Tabela III; FATO por omissão para as demais].

A severidade normalizada de cada evento deve ser expressa como fração do envelope normativo:

$$
S_{m,j} = \frac{V_{pk,j}}{U_{\mathrm{env}}(T_{1,j})},
$$

com $U_{\mathrm{env}}$ definido por vértices — (1 pu, $\to 0$ µs), (3,5 pu, 0,1–0,2 µs), (5 pu, ≥ 1,2 µs) — e parametrizável para as edições 2009 e 2025 e para os níveis reforçados [NORMA: IEC 60034-15:2009 e :2025; LITERATURA secundária: envelope IEEE 522]. A lição de Vollet é operacional: **um evento com pico abaixo do nível mas frente mais curta que a de ensaio deve ser classificado como "fora do envelope"** [LITERATURA: IPST 2007, p. 5–6].

O dano incremental é então o acumulador (D7) da Seção 5.4, com a arquitetura de blocos da ISO 13374-1: DA (oscilografia + DP + RTD + ensaios offline) → DM (extração de $\mathbf{s}$) → SD (linha de base por motor) → HA (fusão com EAR, PI, tip-up, percentis de $Q_m$) → PA (RUL com intervalo de confiança) → AG (recomendações de manobra e manutenção) [NORMA: ISO 13374-1:2003, 2.2.1]. A saída deve declarar horizonte preditivo, limiar de falha e nível de confiança [NORMA: ISO 13381-1:2015, 3.3, 3.9, 3.10].

### 8.3 Decisões de projeto em aberto

**(a) Taxa de amostragem e largura de banda.** Para reconstruir $T_1 = 1{,}67(t_{90}-t_{30})$ de uma frente de 0,1 µs são necessárias 5–10 amostras na frente, isto é, **50 a 100 MS/s**; para 0,2 µs, 25–50 MS/s. A banda analógica mínima é $B \approx 0{,}35/t_r$ = 3,5 MHz (0,1 µs) e 1,75 MHz (0,2 µs) [CÁLCULO PRÓPRIO]. Se o mesmo canal servir também a DP, a banda relevante é VHF 30–350 MHz [LITERATURA: Sedding, Stone e Warren, IRMC 2017]. **Alternativa de baixo custo**: o detector de pico analógico de Jensen et al. reduz a exigência a 10 MSa/s preservando a informação de pico [FATO: artigo 02, p. 7–8] — mas **preserva apenas o pico, não o tempo de frente**, o que é insuficiente para o envelope tempo–tensão [INFERÊNCIA]. Decisão em aberto: canal duplo (pico analógico rápido + oscilografia em janela curta) versus canal único de alta taxa.

**(b) Gatilho e pré-trigger.** A: "the record is acquired only during SCR conduction" [FATO: doc A, p. 2]. Como o registro começa após o disparo do DIAC, **a parte inicial do dv/dt — a mais relevante para a isolação entre espiras — pode ficar fora do registro** sem *pre-trigger* [INFERÊNCIA]. A evidência de figura é precisa quanto a isso: no evento de ≈ 19,6 ms, o snubber **atua** — a oscilação de alta frequência de ≈ 1 ms presente nas três fases da Fig. 3 (±5–7 kV) praticamente desaparece na Fig. 4, restando um único pulso estreito com o degrau residual —, mas **o pico da primeira excursão permanece inalterado** (≈ −6 kV em ambas as figuras), porque o ramo só conduz **após o *breakover* do DIAC** [FATO: doc A, Figs. 3–4 — leitura de figura em ampliação do mesmo recorte ≈ 19,6–20,6 ms das imagens nativas; INFERÊNCIA]. É exatamente essa parte do dv/dt que um registro iniciado na condução dos SCR perderia. **Não se trata, portanto, de exemplo de "snubber que não dispara"**: se o documento quiser sustentar a hipótese de eventos sem disparo, ela exige outra evidência que não as Figs. 3–4. Decisão em aberto, e agora melhor ancorada: gatilho por dv/dt no barramento, **independente do estado dos SCR**, com buffer circular de pré-trigger.

**(c) Limiar de dano $V_{th}$ e normalização.** Três candidatos, todos hipotéticos: (i) PDIV/RPDIV medidos *in situ* na própria máquina [NORMA: IEC 60034-18-41:2014, 3.2, 3.9]; (ii) percentil da distribuição histórica de surtos do próprio barramento (limiar relativo, imune a erro de $a(t_f)$); (iii) fração do envelope normativo (p. ex., $S > 0{,}75$, ecoando o critério de 75 % para máquinas em serviço). A escolha muda qualitativamente o resultado (Seção 5.5) e deve ser declarada como [HIPÓTESE] até calibração em bancada.

**(d) Fração espira-a-espira $a(t_f)$.** Três rotas: (i) modelo MTL/FEM do motor específico [LITERATURA: Zhang et al. 2013; Hussain e Gómez 2017; Ferreira e Ferreira 2021]; (ii) medição em bobina de linha instrumentada; (iii) **apenas como referência de forma da curva, jamais de valores**, a curva de pior caso da IEC 60034-18-41 (Fig. 7) — que é derivada para estatores de enrolamento **aleatório** (Tipo I, geralmente ≤ 700 V) e cuja transposição para bobina pré-formada de MT (Tipo II) é **[HIPÓTESE]**, não rota válida (Seção 2.2) [NORMA: IEC 60034-18-41:2014, legenda da Fig. 7 e Introdução, amostra iTeh lida — **valores não acessados**]. Restam, portanto, apenas (i) e (ii) como rotas legítimas; sem uma delas, o módulo estima estresse no terminal, não na espira.

**(e) Efeito do próprio snubber sobre a assinatura.** Com $R_s = 30\ \Omega$ em condução, o snubber altera a impedância terminal durante o transitório; a assinatura registrada é a do **evento amortecido**. A: apresenta isso como vantagem (mitigar e registrar o mesmo evento) [FATO: doc A, p. 4], mas para rastreabilidade a inferência do estresse **não mitigado** exige modelo inverso [INFERÊNCIA]. Some-se o alerta de Jensen: se o indicador for uma resposta a impulso, a variação de dv/dt causada pela mitigação precisa ser compensada [FATO: artigo 02, p. 3].

**(f) Contagem $n_r$.** Deve ser **medida** (contagem de cruzamentos de AF na corrente do polo, ou incrementos de `reign_count` [REPO: `app/preprocessor/atp_templates/vcb_reignition.mod:115-120`]), não presumida. Prior recomendado: discreto em $[0, 10]$, com dependência de RRDS, capacidade de extinção e tempo de arco [LITERATURA: Vollet 2007; Wong 2003].

**(g) Segmentação de cenários.** Atribuir dano ≈ 0 a aberturas em carga nominal e a vazio, salvo evidência de DP, e concentrar a contabilidade em interrupção de partida/rotor bloqueado [NORMA: IEC 62271-110:2023, 4.3.2; LITERATURA: Gupta et al. 1987, Parte 1; Xue e Popov 2013]. Isso evita inflar $D$ com eventos benignos.

**(h) Calibração dos parâmetros do gêmeo ATP.** Os parâmetros do VCB devem ser expostos como **entradas incertas com faixas da literatura** (RRDS 2–50 kV/ms; capacidade de extinção de AF 100–700 A/µs; chopping 2–10 A), e não fixados nos valores de A (0,801 kV/ms inicial, 2,03 kV/ms de inclinação média em 0–1 ms; 5–15 A/µs), que representam o **extremo inferior** da faixa publicada [LITERATURA: Wong 2003, Tab. 1–2; Vollet 2007, §III-D; Xue e Popov 2013, Tab. I; Abdulahovic 2011, p. 29; INFERÊNCIA]. As faixas aqui são as mesmas da Seção 3.1 e da Seção 9.4 — **não usar tetos discrepantes (600, 1000 A/µs) em seções diferentes**.

---

## 9. Limitações e riscos de sobre-interpretação

1. **A cadeia física está incompleta em seu elo mais importante.** Não há, nas fontes acessadas, quantificação primária da fração da tensão terminal que recai sobre a primeira bobina de uma bobina pré-formada de MT em função do tempo de frente. Os números "70–90 % a 0,1 µs / 20–30 % a 1 µs" **não foram confirmados** e não devem ser usados. O único valor primário disponível (16,1 % espira-a-espira a 0,2 µs, em bobina de 13 espiras) é resultado de **simulação** de máquina completa validada experimentalmente apenas em bobina isolada, e refere-se a grandeza diferente de "fração na primeira bobina" [LITERATURA: Ferreira e Ferreira 2021, Seção III, Tab. VI–VII].
2. **Os expoentes de vida são emprestados.** $n \in [3{,}8;\,11{,}7]$ provém de pares torcidos de fio esmaltado e de epóxi puro [LITERATURA: CIGRE WG D1.43, TB 703, Figs. 24, 33]; a transposição para mica-epóxi pré-formada é [HIPÓTESE]. Como mostrado em 5.5, a incerteza do expoente domina a estimativa de RUL.
3. **Os números do Documento A são de um cenário único.** Uma abertura, um conjunto de instantes de separação, sem análise estatística [FATO por omissão: doc A]. Não se pode afirmar que 41,44 kV seja o máximo, nem que 13,65 kV seja o máximo residual.
4. **A parametrização do VCB de A é o extremo inferior da faixa publicada.** RRDS 10–25× mais lenta que os casos centrais de 20–50 kV/ms (e coincidente com o caso mínimo de 2 V/µs de Wong), e di/dt crítico ≈ 7–140× menor que a **capacidade de extinção de AF** de 100–700 A/µs (Seção 3.1) — grandeza que não deve ser confundida com o di/dt da corrente de frequência industrial interrompida, de 150–1000 A/µs. Os 12,2 pu resultantes são **2–3× superiores** ao teto de 4,3–4,6 pu medido/simulado na literatura de campo [LITERATURA: Gupta et al. 1987 via Baker/SKF; Abdulahovic 2011, p. 8; Xemard et al., IPST 2019]. **Não citar 41 kV / 12 pu como valor típico.**
5. **TRV no disjuntor não é tensão no motor.** Toda comparação normativa desta etapa carrega essa ressalva (Seção 3.4). O snubber está no barramento do painel, a montante do cabo de 240 mm² (Seção 2.3), e a literatura correlata mostra que proteção no painel pode não limitar a tensão no terminal do motor por reflexões [LITERATURA: Vollet 2007, §V-B].
6. **A resolução temporal do estudo é insuficiente para o fenômeno alegado.** Passo de 1 µs contra frentes normativas de 0,2 µs e frentes de serviço de 0,1 µs; e contra o "espectro de MHz" que o próprio argumento comercial invoca [FATO: doc A, Tabela II e p. 1; INFERÊNCIA].
7. **Convenção de extinção de AF não esclarecida.** A redação de A é oposta à da literatura consolidada; sem resolver isso, o sentido do efeito do parâmetro sobre o número de reignições é indeterminado (Seção 3.1).
8. **A premissa "5 a 7 reignições por ciclo" é do usuário, não do Documento A nem da literatura.** Está dentro do teto "até 10", mas não é constante documentada; a unidade "por ciclo" é fisicamente inadequada (Seção 5.3).
9. **Risco de dupla contagem de mecanismos.** O modelo (D7) soma parcela elétrica por evento e parcela térmica contínua. Como a regra de Miner é linear e ignora interação e ordem [LITERATURA: ReliaSoft], e como os modelos multi-estresse (Simoni, Ramu) mostram acoplamento entre $V$ e $T$, a soma independente é aproximação [HIPÓTESE].
10. **Nenhuma norma certifica RUL.** Evitar, em qualquer discurso: "certificado por norma", "RUL exato", "redução do BIL", "5–7 reignições por ciclo" atribuídas a fonte, e "IEEE 43-2024" (edição não verificada em fonte primária). Acrescentem-se, por força das correções desta revisão: **"faixa de ruptura típica de 5–10 pu"** (as fontes dão limites inferiores, não teto — Seção 4.5); **"nível de isolação principal da IEEE 522"** (a norma cobre apenas isolação entre espiras — Seção 4.2); **razões de di/dt calculadas contra "100–1000 A/µs"** (misturam capacidade de extinção de AF com di/dt de corrente industrial interrompida — Seção 3.1); e o par **"10,55 kV / 129 %"** como critério de 75 % (a base do fator é IEEE: 8,92 kV / 153 % — Seção 6).
11. **Edições em transição.** IEEE 43-2013 e IEEE 1434-2014 estão *Inactive-Reserved*; IEEE 95-2002 e IEEE 1310-2012 idem; ISO 13381-1:2025 substituiu a de 2015 e introduz "requirements" cujo conteúdo não foi lido; a Tabela 1 da IEC 60034-15:2025 não foi acessada. **Citar sempre edição e data.**
12. **Fontes secundárias em posições estruturais.** O envelope IEEE 522 e o fator de 75 % para máquinas em serviço sustentam parte da argumentação das Seções 4 e 6 e provêm de fontes secundárias (Baker/SKF; Electrical Trader; Electrom). Devem ser ancorados no texto primário antes de qualquer uso acadêmico ou comercial — [INSERIR CITAÇÃO].

---

## 10. Referências

ABDULAHOVIC, T. **Analysis of high-frequency electrical transients in offshore wind parks**. 2011. Tese (Doutorado) — Chalmers University of Technology, Göteborg, 2011. ISBN 978-91-7385-598-3. Disponível em: https://publications.lib.chalmers.se/records/fulltext/148759/148759.pdf. Acesso em: 2 set. 2026.

ABNT. **ABNT NBR 17094-1:2018** — Máquinas elétricas girantes — Parte 1: Motores de indução trifásicos — Requisitos. 3. ed. Rio de Janeiro: ABNT, 2018.

ABNT. **ABNT NBR 17094-3:2018** — Máquinas elétricas girantes — Parte 3: Motores de indução trifásicos — Métodos de ensaio. Rio de Janeiro: ABNT, 2018. Disponível em: https://www2.uesb.br/biblioteca/wp-content/uploads/2022/03/NBR-17094-M%C3%81QUINAS-EL%C3%89TRICAS-GIRANTES-PARTE-3-MOTORES-DE-INDU%C3%87%C3%83O-TRIF%C3%81SICOS-METODOS-DE-ENSAIO.pdf. Acesso em: 2 set. 2026.

AUTORES OMITIDOS (revisão duplo-cega). **Selective mitigation of vacuum circuit breaker switching overvoltages in medium voltage induction motors using an active thyristor snubber**. Submissão ao SEPOC 2026. 5 p. — **Documento A** [FATO: doc A, p. 1: "Anonymous Authors — Paper submitted to SEPOC 2026 for double blind review (author information omitted)"]. Autoria a confirmar após publicação — [INSERIR CITAÇÃO].

BAKER INSTRUMENT / SKF. **The state of surge testing on induction motors**. White paper, s.d. Disponível em: http://www.cmcbaker.com/manuals/surge%20test%20whitepaper.pdf. Acesso em: 2 set. 2026. (Fonte secundária; citada aqui pelo envelope da IEEE 522-1992, Fig. 1, e pelos dados de Gupta et al. 1987.)

CHOUDHARY, M.; SHAFIQ, M.; KIITAM, I.; HUSSAIN, A.; PALU, I.; TAKLAJA, P. A review of aging models for electrical insulation in power cables. **Energies**, v. 15, n. 9, 3408, 2022. DOI 10.3390/en15093408. Disponível em: https://psecommunity.org/wp-content/plugins/wpor/includes/file/2303/LAPSE-2023.13751-1v1.pdf. Acesso em: 2 set. 2026.

CIGRE. **Technical Brochure 703 — Insulation degradation under fast, repetitive voltage pulses**. WG D1.43 (Convenor: A. Cavallini; Secretário: D. Fabiani). Paris: CIGRE, 2017. Cópia consultada: https://cigre.cz/dokumenty_komise/d1/WG%20D1.43_TB_Final.pdf. Acesso em: 2 set. 2026. Nota: o "© 2011" impresso na p. 1 do arquivo é do *template*, não a data de publicação.

CIGRE. **Terms of Reference WG C4.76 — Overvoltage protection in switching inductive devices with vacuum circuit breaker**. 31 jul. 2023. Disponível em: https://www.cigre.org/userfiles/files/News/2023/TOR-WG%20C4_76_Overvoltage%20protection%20in%20switching%20inductive%20devices%20with%20vacuum%20circuit%20breaker-rev1.pdf. Acesso em: 2 set. 2026.

CIGRE. **Terms of Reference JWG A3/A2/B3/B4/C4.53 — Inductive load switching in transmission and distribution systems**. 13 out. 2025. Disponível em: https://www.cigre.org/userfiles/files/News/2025/TOR%20JWG%20A3_A2_B3_B4_C4_53_Inductive%20load%20switching%20in%20transmission%20and%20distribution%20systems.pdf. Acesso em: 2 set. 2026.

COOPER, E. S.; DISSADO, L. A.; FOTHERGILL, J. C. Application of thermoelectric ageing models to polymeric insulation in cable geometry. **IEEE Transactions on Dielectrics and Electrical Insulation**, v. 12, n. 1, p. 1–10, 2005. DOI 10.1109/TDEI.2005.1394009. Disponível em: https://openaccess.city.ac.uk/id/eprint/1356/. Acesso em: 2 set. 2026.

CORNICK, K. J.; THOMPSON, T. R. Steep-fronted switching voltage transients and their distribution in motor windings. Part 1 / Part 2. **IEE Proceedings B**, v. 129, n. 2, p. 45–55 / 56–63, 1982. DOI 10.1049/ip-b.1982.0007 e 10.1049/ip-b.1982.0008. (Metadados verificados; **textos integrais não acessados** — INSERIR CITAÇÃO para valores percentuais.)

CRINE, J.-P. A molecular approach to the electrical aging of XLPE cables. In: **JICABLE 2007**, Session C7.1, paper C7.1.5. Disponível em: http://www.jicable.org/2007/Actes/Session_C71/JIC07_C7115.pdf. Acesso em: 2 set. 2026.

ELECTRICAL TRADER. **IEC vs. IEEE standards for impulse testing**. s.d. Disponível em: https://electricaltrader.com/blogs/news/iec-vs-ieee-standards-impulse-testing. Acesso em: 2 set. 2026. (Fonte secundária.)

FEILAT, E. A. Lifetime assessment of electrical insulation. In: **Electric Field**. Londres: IntechOpen, 2018. DOI 10.5772/intechopen.72423. Disponível em: https://cdn.intechopen.com/pdfs/58128.pdf. Acesso em: 2 set. 2026.

FERREIRA, R. S.; FERREIRA, A. C. Transient model to study voltage distribution in electrical machine windings considering the rotor. In: **INTERNATIONAL CONFERENCE ON POWER SYSTEMS TRANSIENTS (IPST 2021)**, Belo Horizonte, 2021, paper 21IPST056. Disponível em: https://www.ipstconf.org/papers/Proc_IPST2021/21IPST056.pdf. Acesso em: 2 set. 2026.

GHASSEMI, M. Accelerated insulation aging due to fast, repetitive voltages: a review identifying challenges and future research needs. **IEEE Transactions on Dielectrics and Electrical Insulation**, 2019 (volume/páginas — [INSERIR CITAÇÃO]); pré-print arXiv:2007.03194, 2020. Disponível em: https://arxiv.org/pdf/2007.03194. Acesso em: 2 set. 2026.

GLINKOWSKI, M. T.; GUTIERREZ, M. R.; BRAUN, D. Voltage escalation and reignition behavior of vacuum generator circuit breakers during load shedding. **IEEE Transactions on Power Delivery**, v. 12, n. 1, p. 219–226, 1997. DOI 10.1109/61.568244. Resumo: https://www.osti.gov/biblio/477204. Acesso em: 2 set. 2026.

GUPTA, B. K.; LLOYD, B. A.; STONE, G. C.; CAMPBELL, S. R.; SHARMA, D. K.; NILSSON, N. E. Turn insulation capability of large AC motors. Part 1 — Surge monitoring. **IEEE Transactions on Energy Conversion**, v. EC-2, n. 4, p. 658–665, dez. 1987. DOI 10.1109/TEC.1987.4765906. (Resumo verificado; texto integral não acessado.)

GUPTA, B. K.; LLOYD, B. A.; STONE, G. C.; SHARMA, D. K.; FITZGERALD, J. P. Turn insulation capability of large AC motors. Part 2 — Impulse strength. **IEEE Transactions on Energy Conversion**, v. EC-2, n. 4, p. 666–673, dez. 1987. DOI 10.1109/TEC.1987.4765907. (Resumo verificado.)

GUPTA, B. K. et al. Turn insulation capability of large AC motors. Part 3 — Insulation coordination. **IEEE Transactions on Energy Conversion**, v. EC-2, n. 4, p. 674–679, dez. 1987. DOI 10.1109/TEC.1987.4765908. (Resumo verificado.)

GUPTA, B. K.; LLOYD, B. A.; SHARMA, D. K. Degradation of turn insulation in motor coils under repetitive surges. **IEEE Transactions on Energy Conversion**, v. 5, n. 2, p. 320–326, 1990. DOI 10.1109/60.107228. (Resumo verificado; texto integral não acessado — INSERIR CITAÇÃO para os valores 1 000–8 000 surtos / 3,0–7,8 pu.)

HAQ, S. U.; OMRANIPOUR, R.; TERAN, L. Surge withstand capability of electrically and thermo-mechanically aged turn insulation of medium voltage form-wound AC stator coils. In: **IEEE ELECTRICAL INSULATION CONFERENCE (EIC)**, 2014. DOI 10.1109/EIC.2014.6869351. (Resumo verificado; **valores numéricos não acessados**.)

HU, B. et al. A partial discharge study of medium-voltage motor winding insulation under two-level voltage pulses with high dv/dt. **IEEE Open Journal of Power Electronics**, v. 2, 2021. DOI 10.1109/OJPEL.2021.3069780. Disponível em: https://pmc.ncbi.nlm.nih.gov/articles/PMC8152218/. Acesso em: 2 set. 2026.

HUSSAIN, M. K.; GÓMEZ, P. Optimized dielectric design of stator windings from medium voltage induction machines fed by fast front pulses. **IEEE Transactions on Dielectrics and Electrical Insulation**, v. 24, n. 2, p. 837–846, 2017. DOI 10.1109/TDEI.2017.006249.

IEC. **IEC 60034-15:2009** — Rotating electrical machines — Part 15: Impulse voltage withstand levels of form-wound stator coils for rotating a.c. machines. 3. ed. Genebra: IEC, 2009. Amostra oficial: https://cdn.standards.iteh.ai/samples/15848/1b914cc7cb9b4c4582e502f946666007/IEC-60034-15-2009.pdf. Acesso em: 2 set. 2026.

IEC. **IEC 60034-15:2025** — idem. 4. ed., 2025-06-06. Genebra: IEC, 2025. Disponível em: https://webstore.iec.ch/en/publication/69045. Amostra (I.S. EN IEC 60034-15:2025): https://www.intertekinform.com/preview/1948903295308.pdf?sku=1408890_saig_nsai_nsai_3650192. Acesso em: 2 set. 2026. (**Tabela 1 da edição publicada não acessada** — INSERIR CITAÇÃO.)

IEC. **IEC CDV 60034-15 (2/2199/CDV)** — Committee Draft for Vote, future edition 4. Genebra: IEC, 2024 (oSIST prEN IEC 60034-15:2024). Amostra: https://cdn.standards.iteh.ai/samples/76379/70c15953e53f480988b6605f0730692c/oSIST-prEN-IEC-60034-15-2024.pdf. Acesso em: 2 set. 2026. (Rascunho, "subject to change".)

IEC. **IEC 60034-18-41:2014 (+AMD1:2019)** — Partial discharge free electrical insulation systems (Type I) used in rotating electrical machines fed from voltage converters. Genebra: IEC, 2014. Amostra: https://cdn.standards.iteh.ai/samples/18905/b95c2f0bc77e4b658894b3e6629e3aa2/IEC-60034-18-41-2014.pdf. Acesso em: 2 set. 2026. (**Tabela 4 e Fig. 7 não acessadas** — INSERIR CITAÇÃO.)

IEC. **IEC 60034-18-42:2017 (+AMD1:2020)** — Partial discharge resistant electrical insulation systems (Type II). Genebra: IEC, 2017. Disponível em: https://webstore.iec.ch/en/publication/28040. Acesso em: 2 set. 2026.

IEC. **IEC 60034-27-1:2017** — Off-line partial discharge measurements on the winding insulation. Genebra: IEC, 2017. Disponível em: https://webstore.iec.ch/en/publication/29254. Acesso em: 2 set. 2026.

IEC. **IEC 60034-27-2:2023** — On-line partial discharge measurements on the stator winding insulation. Genebra: IEC, 2023. Disponível em: https://webstore.iec.ch/en/publication/64620. Amostra: https://cdn.standards.iteh.ai/samples/103004/5eca519428624e729a23cd1282b66962/IEC-60034-27-2-2023.pdf. Acesso em: 2 set. 2026.

IEC. **IEC 60034-27-3:2015** — Dielectric dissipation factor measurement on stator winding insulation. Genebra: IEC, 2015. Amostra: https://cdn.standards.iteh.ai/samples/19866/c3993cedb23c47f9831620d7be90fef3/IEC-60034-27-3-2015.pdf. Acesso em: 2 set. 2026.

IEC. **IEC 60034-27-4:2018** — Measurement of insulation resistance and polarization index of winding insulation. Genebra: IEC, 2018. Amostra: https://cdn.standards.iteh.ai/samples/21978/2d3f0846afc7499190a2d8bcfa239328/IEC-60034-27-4-2018.pdf. Acesso em: 2 set. 2026.

IEC. **IEC TS 60034-27-5:2021** — Off-line measurement of PDIV/PDEV under repetitive impulses. Genebra: IEC, 2021. Disponível em: https://webstore.iec.ch/en/publication/31870. Acesso em: 2 set. 2026.

IEC. **IEC 60071-1:2019** — Insulation co-ordination — Part 1: Definitions, principles and rules. 9. ed. Genebra: IEC, 2019. Amostra: https://cdn.standards.iteh.ai/samples/100144/6c649e0574b44164805acdb3a39941f0/IEC-60071-1-2019.pdf. Acesso em: 2 set. 2026.

IEC. **IEC 60071-1:2006 (IS/IEC)** — idem, 8. ed. Nova Délhi: BIS, 2006. Disponível em: https://law.resource.org/pub/in/bis/S05/is.iec.60071.1.2006.pdf. Acesso em: 2 set. 2026. (Tabela 2 lida nesta edição.)

IEC. **IEC 62271-110:2023** — High-voltage switchgear and controlgear — Part 110: Inductive load switching. 5. ed. Genebra: IEC, 2023. Amostra: https://cdn.standards.iteh.ai/samples/110032/6134d1d703624b01af650b4c93dc550f/IEC-62271-110-2023.pdf. Acesso em: 2 set. 2026.

IEEE. **IEEE Std 43-2013** — Recommended practice for testing insulation resistance of electric machinery. Nova York: IEEE, 2013 (*Inactive-Reserved* desde 2024-03-21). Disponível em: https://standards.ieee.org/ieee/43/4791/. Acesso em: 2 set. 2026.

IEEE. **IEEE Std 522-2023** — Guide for testing turn insulation of form-wound stator coils for alternating-current electric machines. Nova York: IEEE, 2023. Disponível em: https://standards.ieee.org/ieee/522/6940/. Acesso em: 2 set. 2026. (**Texto integral não acessado**; o envelope tensão × tempo de frente citado neste documento provém de fonte secundária — INSERIR CITAÇÃO: IEEE Std 522, Fig. 1.)

IEEE. **IEEE Std 1434-2014** — Guide for the measurement of partial discharges in AC electric machinery. Nova York: IEEE, 2014 (*Inactive-Reserved* desde 2025-03-27; projeto sucessor P1434). Disponível em: https://standards.ieee.org/standard/1434-2014.html. Acesso em: 2 set. 2026.

ISO. **ISO 13374-1:2003** — Condition monitoring and diagnostics of machines — Data processing, communication and presentation — Part 1: General guidelines. Amostra: https://cdn.standards.iteh.ai/samples/21832/4f282cf6f5594b73be0bbca7590719f1/ISO-13374-1-2003.pdf. Acesso em: 2 set. 2026.

ISO. **ISO 13381-1:2015** — Condition monitoring and diagnostics of machines — Prognostics — Part 1: General guidelines. Amostra: https://cdn.standards.iteh.ai/samples/51436/8246d96c8ff54347ae65f3aba73f2e88/ISO-13381-1-2015.pdf. Acesso em: 2 set. 2026. (Substituída pela ISO 13381-1:2025, publicada em 2025-09-02 — conteúdo não lido.)

JENSEN, W. R.; STRANGAS, E. G.; FOSTER, S. N. A method for online stator insulation prognosis for inverter-driven machines. **IEEE Transactions on Industry Applications**, v. 54, n. 6, p. 5897–5906, nov./dez. 2018. DOI 10.1109/TIA.2018.2854408. (Texto integral lido — fichamento 02.)

KOHLER, J. L.; SOTTILE, J.; TRUTT, F. C. Condition monitoring of stator windings in induction motors. Part I — Experimental investigation of the effective negative-sequence impedance detector. **IEEE Transactions on Industry Applications**, 2002. DOI 10.1109/TIA.2002.802935. (Resumo verificado.)

KRINGS, A.; PAULSSON, G.; SAHLÉN, F.; HOLMGREN, B. Experimental investigation of the voltage distribution in form wound windings of large AC machines due to fast transients. In: **ICEM**, 22., 2016, p. 1700–1706. DOI 10.1109/ICELMACH.2016.7732753. (Resumo verificado.)

MA, K.; LISERRE, M.; BLAABJERG, F.; KEREKES, T. Thermal loading and lifetime estimation for power device considering mission profiles in wind power converter. **IEEE Transactions on Power Electronics**, v. 30, n. 2, p. 590–602, fev. 2015. DOI 10.1109/TPEL.2014.2312335. (Texto integral lido — fichamento 12.)

NEMA. **ANSI/NEMA MG 1-2016 (Rev. 2018)**, Partes 30 e 31. Disponível em: https://www.nema.org/docs/default-source/standards-document-library/mg-1-part-31-watermark.pdf?sfvrsn=649fb42f_1. Acesso em: 2 set. 2026.

PINTO, C.; STRICKLER, R. N.; ANAND, V. A case study on lifetime assessment of stator windings in large machines. In: **IEEE PCIC 2022**, paper 0567. Disponível em: https://ieeepcic.com/2022conference/wp-content/uploads/sites/7/2022/09/2022-PCIC-0567.pdf. Acesso em: 2 set. 2026.

RELIASOFT. **Miner's rule and cumulative damage models**. HotWire, n. 116. Disponível em: https://help.reliasoft.com/articles/content/hotwire/issue116/hottopics116.htm. Acesso em: 2 set. 2026.

RUZIMOV, S. et al. Detection of inter-turn short-circuit faults for inverter-fed induction motors based on negative-sequence current analysis. **Sensors**, 2025. Disponível em: https://pmc.ncbi.nlm.nih.gov/articles/PMC12349302/. Acesso em: 2 set. 2026.

SEDDING, H.; STONE, G.; WARREN, V. **Partial discharge testing: a progress report — PD: a comparison test**. Iris Rotating Machine Conference (IRMC), 2017. Disponível em: https://irispower.com/wp-content/uploads/2017/06/14-Sedding-Comparison-Test-IRMC-2017.pdf. Acesso em: 2 set. 2026.

STONE, G. C.; CULBERT, I.; BOULTER, E. A.; DHIRANI, H. **Electrical insulation for rotating machines: design, evaluation, aging, testing, and repair**. 2. ed. Hoboken: Wiley-IEEE Press, 2014. ISBN 978-1-118-05706-3. (Capítulos sobre distribuição de surto e isolação de espira **não lidos** — INSERIR CITAÇÃO com página.)

STRANGAS, E. G.; AVIYENTE, S.; NEELY, J. D.; ZAIDI, S. S. H. The effect of failure prognosis and mitigation on the reliability of permanent-magnet AC motor drives. **IEEE Transactions on Industrial Electronics**, v. 60, n. 8, p. 3519–3528, ago. 2013. DOI 10.1109/TIE.2012.2227913. (Texto integral lido — fichamento 09.)

TALLAM, R. M. et al. A survey of methods for detection of stator-related faults in induction machines. **IEEE Transactions on Industry Applications**, v. 43, n. 4, p. 920–933, 2007. DOI 10.1109/TIA.2007.900448. (Resumo verificado.)

THEOFANOUS, A. et al. Modelling of insulation thermal ageing: historical evolution from fundamental chemistry towards becoming an electrical machine design tool. **Energies**, v. 18, 6087, 2025. DOI 10.3390/en18236087. Disponível em: https://aisberg.unibg.it/retrieve/43c96487-a8ad-4947-a8c8-3b350e9892a2/J65.pdf. Acesso em: 2 set. 2026.

THORSEN, O. V.; DALVA, M. A survey of faults on induction motors in offshore oil industry, petrochemical industry, gas terminals and oil refineries. In: **IEEE PCIC**, 1994, p. 1–9. DOI 10.1109/PCICON.1994.347637; versão em **IEEE Transactions on Industry Applications**, v. 31, n. 5, p. 1186–1196, 1995. DOI 10.1109/28.464536. (Metadados verificados; **percentuais por componente não confirmados no texto primário** — INSERIR CITAÇÃO.)

THORSEN, O. V.; DALVA, M. Failure identification and analysis for high-voltage induction motors in the petrochemical industry. **IEEE Transactions on Industry Applications**, v. 35, n. 4, p. 810–818, 1999. DOI 10.1109/28.777188. (Metadados verificados: 483 motores, 6 135 unidade-anos, 100–1 300 kW.)

TOMMASINI, D. **Dielectric insulation and high-voltage issues**. CERN, 2011. arXiv:1104.0802. Disponível em: https://arxiv.org/pdf/1104.0802. Acesso em: 2 set. 2026.

VICHARE, N. M.; PECHT, M. G. Prognostics and health management of electronics. **IEEE Transactions on Components and Packaging Technologies**, v. 29, n. 1, p. 222–229, mar. 2006. (DOI completo — [INSERIR CITAÇÃO].) (Texto integral lido — fichamento 07.)

VOLLET, C.; DE METZ-NOBLAT, B. Vacuum circuit breaker model: application case to motors switching. In: **INTERNATIONAL CONFERENCE ON POWER SYSTEMS TRANSIENTS (IPST 2007)**, Lyon, 2007, paper 07IPST106. Disponível em: https://www.ipstconf.org/papers/Proc_IPST2007/07IPST106.pdf. Acesso em: 2 set. 2026.

VOLLET, C.; DE METZ NOBLAT, B. Protecting high-voltage motors against switching overvoltages. In: **4th EUROPEAN CONFERENCE ON ELECTRICAL AND INSTRUMENTATION APPLICATIONS IN THE PETROLEUM & CHEMICAL INDUSTRY (PCIC EUROPE)**, 2007, p. 1–7. DOI 10.1109/PCICEUROPE.2007.4354001. Referência [14] do Documento A; publicação distinta do trabalho IPST 2007; **não acessada** — [INSERIR CITAÇÃO].

WARREN, V. **Partial discharge testing: a progress report — trend of Qm percentile rankings 1997-2021**. IRMC 2022. Disponível em: https://irispower.com/wp-content/uploads/2023/07/Trend-of-Qm-Percentile-Rankings-1997-2021-Warren-IRMC-2022-paper.pdf. Acesso em: 2 set. 2026.

WONG, S. M.; SNIDER, L. A.; LO, E. W. C. Overvoltages and reignition behavior of vacuum circuit breaker. In: **INTERNATIONAL CONFERENCE ON POWER SYSTEMS TRANSIENTS (IPST 2003)**, New Orleans, 2003, paper 03IPST14a-03. Disponível em: https://www.ipstconf.org/papers/Proc_IPST2003/03IPST14a-03.pdf. Acesso em: 2 set. 2026. (Versão APSCOM 2003: DOI 10.1049/cp:20030663 — referência [4] do Documento A.)

WRIGHT, M. T.; YANG, S. J.; McLEAY, K. General theory of fast-fronted interturn voltage distribution in electrical machine windings. **IEE Proceedings B**, v. 130, n. 4, p. 245–256, 1983. DOI 10.1049/ip-b.1983.0040. (Metadados verificados; **texto integral não acessado**.)

WU, F.; WU, Q.; TAN, Y.; XU, X. Remaining useful life prediction based on deep learning: a survey. **Sensors**, v. 24, n. 11, art. 3454, p. 1–30, 2024. DOI 10.3390/s24113454. (Texto integral lido — fichamento 13.)

XEMARD, A.; JURISIC, B.; RIOUAL, M.; OLIVIER, A.; SELIN, E. Interruption of small, medium-voltage transformer current with a vacuum circuit breaker. In: **IPST 2019**, paper 19IPST095. Disponível em: https://www.ipstconf.org/papers/Proc_IPST2019/19IPST095.pdf. Acesso em: 2 set. 2026.

XUE, H.; POPOV, M. Analysis of switching transient overvoltages in the power system of floating production storage and offloading vessel. In: **IPST 2013**, Vancouver, paper 13IPST007. Disponível em: https://www.ipstconf.org/papers/Proc_IPST2013/13IPST007.pdf. Acesso em: 2 set. 2026.

YANG, Y.; BAI, X.; LEI, Y.; LIU, K.; WU, G. Voltage rise rate-related generalised probabilistic lifetime model of turn-to-turn insulation in inverter-fed motors. **High Voltage**, 2023. DOI 10.1049/hve2.12375. (Resumo verificado.)

ZHANG, J. et al. Analysis of inter-turn insulation of high voltage electrical machine by using multi-conductor transmission line model. **IEEE Transactions on Magnetics**, v. 49, n. 5, p. 1905–1908, 2013. DOI 10.1109/TMAG.2013.2245873.

---

### Referências ainda sem fonte primária acessada (manter como [INSERIR CITAÇÃO] até verificação)

IEEE Std 522, Fig. 1 (envelope tensão × tempo de frente, edições 1992/2004/2023); IEC 60034-15:2025, Tabela 1 (p. 13); IEC 60034-18-41:2014, Tabela 4 e Fig. 7; Thorsen e Dalva (1995, 1999), tabelas de percentuais por componente; Gupta et al. (1987, Partes 1–3) e Gupta, Lloyd e Sharma (1990), textos integrais; Haq, Omranipour e Teran (2014), valores numéricos; Stone et al. (2014), capítulos sobre distribuição de surto; Simoni (1981, 1984) e Montanari, Mazzanti e Simoni (2002), originais; IEEE Std 286; NEMA MG 1 Parte 20; IEC 62271-100:2021 (definição de RRRV e parâmetros de TRV); ANSI/IEEE C37.20.2 (BIL de painéis de 4,76 kV); IEC 60038:2009, Tabela 3 (série 60 Hz); Narang et al. (1989); Oyegoke (1999/2000); medição publicada da função de transferência de supressor R–C comercial na faixa 100 kHz–100 MHz.
