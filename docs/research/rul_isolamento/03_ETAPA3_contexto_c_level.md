# Etapa 3 (parte 1) — Contexto industrial e tradução executiva: do TRV ao risco financeiro

**Objetivo.** Construir a ponte auditável entre as grandezas físicas fixadas nas Etapas 1 e 2 — pico de sobretensão, $\mathrm{d}v/\mathrm{d}t$, reignições, afundamento de partida, contingência N-1, margem de coordenação $\gamma(t)$ — e as grandezas com que uma diretoria de planta decide: OPEX, CAPEX, lucro cessante, risco de segurança/ESG, prêmio de seguro e os KPIs que ela já acompanha. Especificamente: (i) uma tabela-mestra de tradução fenômeno → consequência física → consequência operacional → consequência de negócio → KPI, com rótulo de evidência por linha; (ii) o repertório **verificado** de custo de indisponibilidade, separando custo por hora, custo anual por instalação e custo de troca de motor de média tensão (MT), com as ressalvas metodológicas de cada levantamento; (iii) o modelo de decisão econômica $E[C]$ e sua extensão a valor de opção, ancorado na única formalização do corpus que liga prognóstico imperfeito a MTBF (Strangas et al., 2013); (iv) os quatro argumentos de venda e as seis objeções típicas, com resposta técnica a cada uma; (v) a especificação do painel executivo — e, sobretudo, do que ele **não** deve exibir; (vi) a narrativa de valor específica dos Documentos A e B com os números reais das Etapas 1 e 2; e (vii) o roteiro de entrega do trabalho computacional (tese + artefato). Este documento é a **parte 1** da Etapa 3 prevista no índice [REPO: `docs/research/rul_isolamento/00_INDICE.md`, §1.3, linha "Etapa 3"].

**Diagnóstico.** O acervo permite sustentar, com fonte primária acessada, **a demanda executiva e as barreiras**, mas **não** o número que a própria venda mais exige: o custo por evento de falha de motor MT em refinaria ou plataforma. Três assimetrias estruturam esta etapa. **Primeira**: os números de custo de parada mais citados provêm de relatórios patrocinados por fornecedores — o mais usado, Siemens/Senseye, é extrapolado de 181 entrevistas em quatro anos para a Fortune Global 500, e seus próprios autores declaram que a amostra "pode inflar levemente" a prevalência de manutenção preditiva e que os **resultados combinados entre setores** "não são diretamente comparáveis ano a ano" e devem ser vistos "as indicative only" [LITERATURA: Siemens/Senseye, *TCOD 2022*, p. 15, 21; *TCOD 2024*, p. 6, 15]. **Segunda**: a barreira dominante declarada é econômica **ou de escopo**, não de instrumentação técnica — 63 % das empresas sem planos de PdM 4.0 (isto é, 63 % dos 40 % sem planos, ≈ 25 % da amostra de 268) declararam que "um bom *business case* para PdM 4.0 não pôde ser feito **ou** que a técnica não é relevante para o seu negócio", categoria composta que a fonte não desdobra e sobre a qual ela própria adverte que "for certain companies there may indeed not be a viable business case"; contra 23 % que alegam falta de dados e 8 % falta de capacidade analítica [LITERATURA: PwC/Mainnovation 2018, p. 8]; e apenas 23 a 25 % das organizações conseguem vincular iniciativas de IA a receita ou custo [LITERATURA: Bain 2025; BCG 2025]. **Terceira**: a única análise custo-benefício de PHM com erro prognóstico acessada demonstra que **taxas altas de falso alarme podem tornar o sistema economicamente pior que a referência** [LITERATURA: Hölzel e Gollnick 2015, p. 14], enquanto nenhum dos surveys executivos acessados reporta taxa de falso alarme como KPI — lacuna entre a literatura de PHM e a prática de gestão [INFERÊNCIA]. A consequência de projeto é direta e não negociável: **o valor do módulo é dominado pela criticidade do ativo (existência de reserva instalada e de redundância de processo), não pela acurácia do estimador** [CÁLCULO PRÓPRIO, §3.4], de modo que a classificação de criticidade precede a estimação de RUL na ordem de execução.

**Arquivos consultados.**

| Arquivo | Papel nesta etapa |
|---|---|
| `anexos/pesquisa/c_level_demanda_rul.md` (354 l.) | Fonte única dos números de custo, adoção, barreiras, KPIs e seguro; escala de confiança A/M/B e Anexo A de bloqueios HTTP |
| `anexos/pesquisa/contexto_industrial_brasil_og.md` (219 l.) | Contexto Brasil/O&G: Petrobras PN 2026-30, EPRI EL-2678, ANP/SGSO/RASO, NR-10/NR-12, ISO 55001, ABRAMAN |
| `anexos/pesquisa/entrega_trabalho_computacional.md` (345 l.) | ISO 13374/13381-1, métricas de prognóstico (Saxena 2010), incerteza, FAIR4RS/Zenodo/JOSS, conteúdo mínimo do painel |
| `01_ETAPA1_monitoramento_degradacao_isolamento.md` (873 l.) | Tabela III de A com colunas derivadas (§3.2), margem $\gamma(t)$ e correção do BIL (§6), tabela de 11 métodos (§7.1), vetor $\mathbf{s}_{m,j}$ (§8.2) |
| `02_ETAPA2_cruzamento_A_x_B.md` (960 l.) | Acoplamento causal B → A, margens de *ride-through* (§2.3), monotonicidade perversa (§2.5), acumulador $D(t)$ (§5.2), $f_6$/$g_4$ (§6.2), ancoragem em Strangas (§7.2), Q1–Q12 (§11.3) |
| `anexos/fichamentos/09_strangas2013_prognosis_mitigation.md` (242 l.) | Eqs. (5)–(11), (15)–(16); resultados numéricos p. 7–9; oito limitações declaradas e onze inferidas |
| `anexos/fichamentos/07_vichare_pecht2006_phm_electronics.md` (209 l.) | Quatro metas do PHM (p. 1), custo de falso alarme de BIT (p. 2), condição de recuperação do investimento (p. 3), rota LCM (p. 5–6) |
| `anexos/repo/convencoes_auditoria_gui_docs.md` (451 l.) | Checklist obrigatório de módulo novo (§4.1–4.6): cabeçalho de auditoria, `KNOWN_LIMITATIONS`, `STANDARDS_CATALOG`, gating comercial, 7ª garantia de GUI |
| `(texto integral, fora do repositório) A_sepoc_snubber.txt` (p. 1–5) | Tabela III; alegação de preservação da assinatura de alta frequência (p. 1–2); camada digital prevista e não apresentada (p. 2) |
| `(texto integral, fora do repositório) B_sepoc_load_shedding.txt` (p. 1–6) | $V_{\min}$ 0,755 pu sem corte; $g_1$ 0,85 pu; soluções 0,850/0,858/0,866 pu; $f_5$ 7417/8127/8927 kW |

**Arquivos afetados.** `docs/research/rul_isolamento/03_ETAPA3_contexto_c_level.md` (este arquivo, novo). Nenhum arquivo de código é tocado nesta etapa; os pontos de acoplamento no repositório são **indicados**, não implementados (§7.4).

**Estratégia.** Três princípios governam a redação. **(1) Nenhum número de mercado é estimado.** Todo valor monetário provém de fonte primária acessada e registrada em `c_level_demanda_rul.md` ou em `contexto_industrial_brasil_og.md`, com ano, amostra e patrocínio declarados na própria linha; onde a fonte não existe, escreve-se `[INSERIR CITAÇÃO]` e a lacuna entra na §8. **(2) A tradução é unidirecional e rastreável.** Cada linha da tabela-mestra parte de um fenômeno cuja física foi fixada na Etapa 1 ou na Etapa 2 e termina em um KPI cuja existência foi documentada em survey executivo ou em norma de KPI de manutenção; nenhum elo é criado por analogia. **(3) O adversário do argumento é o falso alarme, não o ceticismo.** A estrutura econômica adotada (§3) contabiliza explicitamente o custo do falso positivo, porque é o único termo que a literatura acessada demonstra capaz de inverter o sinal do valor [LITERATURA: Hölzel e Gollnick 2015, p. 14]; um discurso de venda que o omita é tecnicamente frágil, não apenas incompleto.

**Limitações.** (a) **Não existe fonte acessada que forneça o custo de um evento de falha de motor MT em refinaria ou plataforma**, com ou sem reserva instalada; todo exemplo numérico desta etapa é ilustrativo e assim rotulado [INSERIR CITAÇÃO]. (b) **Não existe fonte acessada que forneça o custo de rebobinagem ou de reposição de motor MT** — o valor de US$ 300 mil usado no exemplo é hipótese herdada de `c_level_demanda_rul.md` §5.3 [INSERIR CITAÇÃO]. (c) As faixas de benefício atribuídas à McKinsey ("−30 a −50 % de parada, +20 a +40 % de vida") **não foram verificadas na fonte primária** (HTTP 503) e não são usadas [INSERIR CITAÇÃO]. (d) Nenhuma fonte primária acessada quantifica redução de prêmio de seguro condicionada a prognóstico de máquinas elétricas; o canal existe como produto, não como preço [LITERATURA: Munich Re *IoT Cover*; HSB 2022]. (e) Os indicadores do Documento Nacional ABRAMAN 2024 são restritos a associados; os números brasileiros de manutenção usados são de 2013 e 2017, via fonte secundária acadêmica [LITERATURA: Favarão da Silva, tese USP 2022, p. 21–22]. (f) O texto integral da ISO 55000/55001:2024, da EN 15341:2019 e da ISO 13381-1:2025 **não foi lido**; as citações são de página de catálogo ou de escopo [NORMA: textos não acessados]. (g) Todas as limitações das Etapas 1 e 2 permanecem — em especial a ausência de $n$, $V_{th}$ e $a(t_f)$ para mica-epóxi pré-formada de MT, que impede que qualquer RUL desta etapa seja apresentado como resultado.

**Próximo passo recomendado.** Antes de qualquer apresentação a diretoria, executar a **classificação de criticidade da população de motores** da planta-alvo — existência de reserva instalada, redundância de processo, tempo de mobilização de sobressalente —, porque o cálculo da §3.4 mostra que o mesmo motor, com os mesmos parâmetros de degradação, produz valor de +US$ 877 mil/ano ou −US$ 83 mil/ano conforme haja ou não redundância [CÁLCULO PRÓPRIO]. Sem essa classificação, o *business case* é indefensável em qualquer direção. Em paralelo, obter da planta os dois números que a Etapa 2 já apontava como bloqueantes (Q2 e Q10): o ajuste temporizado da ANSI 27 e a taxa anual de contingências N-1 [FATO: `02_ETAPA2...md`, §11.3, Q2 e Q10].

---

## 1. Tabela-mestra de tradução: do fenômeno físico ao KPI executivo

### 1.1 Convenção de leitura

A tabela lê-se da esquerda para a direita como uma cadeia causal com **um rótulo por elo**, não como uma associação de ideias. Onde a passagem de uma coluna à seguinte é inferência desta etapa, o rótulo é `[INFERÊNCIA]`; onde é fato de documento, norma ou literatura, o rótulo nomeia a fonte e a página. A coluna "KPI que o executivo já acompanha" só admite indicadores cuja existência foi documentada em survey executivo acessado, em norma de KPI de manutenção ou em documento público da própria operadora — nunca KPIs inventados para a ocasião.

### 1.2 A tabela

| # | Fenômeno técnico | Consequência física | Consequência operacional | Consequência de negócio | KPI que o executivo já acompanha |
|---|---|---|---|---|---|
| **T1** | **TRV de VCB** — pico de 41,44 kV na fase B sem mitigação, contra 13,65 kV com snubber [FATO: doc A, Tabela III, p. 3] | 12,20 pu na base $\sqrt{2}\,U_{LL}/\sqrt3 = 3{,}397$ kV, contra 4,02 pu mitigado; **295 %** da suportabilidade entre espiras de bobina nova ($U'_P = 14{,}07$ kV) [NORMA: IEC 60034-15:2009, Tabela 1] e **465 %** do critério de 75 % para máquina em serviço ($8{,}92$ kV $= 0{,}75\times3{,}5$ pu, **base IEEE**, não IEC) [NORMA: IEEE Std 522-2023; CÁLCULO PRÓPRIO: `01_ETAPA1...md`, §6] | Solicitação acima do envelope normativo em cada manobra abortada; erosão da margem de coordenação $\gamma(t)=U_w(t)/U_s$ até $\gamma \to 1$ [INFERÊNCIA FÍSICA: `01_ETAPA1...md`, §6] | Falha não programada de motor crítico → lucro cessante dominado por $C_h\cdot T_{ind}$; OPEX de rebobinagem; CAPEX antecipado de reposição [CÁLCULO PRÓPRIO, §3.4] | Horas de parada não programada por mês; custo de manutenção [LITERATURA: TCOD 2024, p. 10–11; PwC 2018, p. 10] |
| **T2** | **$\mathrm{d}v/\mathrm{d}t$ (RRRV)** — 19,00 kV/µs na fase C sem mitigação; 13,11 kV/µs na fase B com mitigação [FATO: doc A, Tabela III, p. 3] | Frente íngreme concentra a tensão longitudinal nas primeiras espiras; a norma reconhece **não existir lei fechada** para pré-calcular essa distribuição [NORMA: IEC 60034-15:2009, A.1 e A.3] | Dano espira-a-espira invisível a IR/PI, tan δ e DP — apenas o ensaio de surto solicita diretamente a isolação entre espiras, e é offline e potencialmente destrutivo [NORMA: IEEE 522-2023, escopo; `01_ETAPA1...md`, §7.1] | Modo de falha que a inspeção de rotina não detecta; risco de falha entre paradas programadas, isto é, exatamente no intervalo em que a planta não tem janela [INFERÊNCIA] | Disponibilidade/*uptime* — objetivo primário para 51 % dos respondentes [LITERATURA: PwC 2018, p. 9] |
| **T3** | **Reignições múltiplas por manobra** ($n_{r,m}$ por polo) | Cada reignição é um evento de dano independente no acumulador $\Delta D_m^{el}=\sum_j 1/N_j$ [`02_ETAPA2...md`, eq. (5.2)] | $n_{r,m}$ **não é reportado pelo Documento A** [FATO por omissão: doc A, p. 1–5]; a premissa "5 a 7 reignições por ciclo" é do usuário, não do artigo [HIPÓTESE do usuário] | Incerteza de primeira ordem no dano por evento; impede comprometer-se com número de RUL sem intervalo [INFERÊNCIA] | Nenhum KPI atual captura isto — é a lacuna que o módulo cria valor ao preencher [INFERÊNCIA] |
| **T4** | **Afundamento de partida** — $V^{(\mathrm{INRUSH})}_{\min}=0{,}755$ pu sem corte de carga [FATO: doc B, p. 2] | Abaixo do limite de *ride-through* de 0,85 pu ($g_1$), "well below" [FATO: doc B, p. 2]; conjugado cai com $V^2$ [NORMA: ANSI/NEMA MG 1, 12.44.2] | Atuação da proteção de subtensão em todo o barramento; partida abortada; o cenário de pior caso do Documento A [FATO: doc B, p. 1; doc A, p. 3, V] | Perda de batelada/produção do trem afetado; risco de trip em cascata; custo de religamento de 17 a 19 máquinas [FATO: doc B; `02_ETAPA2...md`, §4.4] | Incidentes de parada por mês (25/mês por planta em 2024, contra 42 em 2019) [LITERATURA: TCOD 2024, p. 3] |
| **T5** | **Contingência N-1** com corte seletivo | Três soluções de Pareto a 0,850 / 0,858 / 0,866 pu, com margem de **0,00 % / 0,94 % / 1,88 %** sobre $g_1$ [FATO: doc B, p. 3, Tabela III; CÁLCULO PRÓPRIO: `02_ETAPA2...md`, §2.3] | A discrepância **típica** documentada entre estudo quase-estático e dinâmico ($\pm$0,5 %) já consome **53 %** da margem do joelho [LITERATURA: Nivelo et al., IPST 2021, p. 6–8; CÁLCULO PRÓPRIO] | Decisão de operar sob N-1 tomada com margem menor que a incerteza do modelo que a produz — risco de projeto não contabilizado no plano [INFERÊNCIA] | Confiabilidade/disponibilidade operacional; na Petrobras, **DO ≥ 97 %** por *benchmark* Solomon [FATO: Petrobras, PN 2026-30, p. 73] |
| **T6** | **Margem de coordenação** $\gamma(t)=U_w(t)/U_s$, com $U_w(t)=U_{w,0}\,\psi(D(t))$, $\psi(0)=1$, $\psi'<0$ [`01_ETAPA1...md`, §6] | O BIL é nível **declarado e verificado por ensaio de tipo**, não propriedade que decaia; o que decai é a suportabilidade real $U_w(t)$ [NORMA: IEC 60071-1:2019, 3.34] | Com snubber, o evento fica **dentro** da suportabilidade de bobina nova (97 % de $U'_P$) mas **acima** da de bobina em serviço (153 % do critério de 75 %) [CÁLCULO PRÓPRIO: `01_ETAPA1...md`, §6] | A margem já foi consumida mesmo com mitigação: a decisão deixa de ser "instalar ou não o snubber" e passa a ser "quando intervir no ativo" [INFERÊNCIA] | Extensão de vida do ativo — objetivo primário para 7 % e benefício obtido por 46 %, com média de +20 % [LITERATURA: PwC 2018, p. 9–10] |
| **T7** | **Sinergia térmico-dielétrica**: a manobra de A incide no instante de maior temperatura transitória do enrolamento [`02_ETAPA2...md`, §5.3] | Fator térmico $1/N_j \propto 2^{(\theta_j-\theta_0)/\mathrm{HIC}}$ multiplica a taxa de dano por **2× a 5,7×** para +10 a +20 K [CÁLCULO PRÓPRIO: `02_ETAPA2...md`, §4.3] | Nenhum dos dois documentos permite avaliar essa multiplicação: A não tem $\theta$; B não tem $\theta$ do motor [FATO por omissão nos dois] | Uma estimativa que ignore a sinergia é **cota inferior de dano**, isto é, cota superior de RUL: otimista por construção [INFERÊNCIA: `02_ETAPA2...md`, §5.2] | Risco SHEQ — 52 % obtêm redução, média −14 % [LITERATURA: PwC 2018, p. 10] |
| **T8** | **Falha de enrolamento como modo dominante** | Levantamento EPRI (4.797 motores, 1.227 falhas, 56 concessionárias): rolamentos 41 %, estator 37 %, rotor 10 %, outros 12 %; do estator, enrolamento 94 %; do enrolamento, à terra 65 % e entre espiras 12 % [LITERATURA: EPRI EL-2678, 1982, p. S-7 e 8-2] | $0{,}37\times0{,}94\approx 35$ % de todas as falhas são de enrolamento estatórico; $\approx 4$ % são entre espiras; taxa anual de falha de enrolamento $\approx 0{,}35\times3{,}5\,\% \approx 1{,}2\,\%$/ano [CÁLCULO PRÓPRIO sobre EPRI] | Prior de taxa de falha para a camada econômica, **explicitamente editável**; população de 1982 de concessionárias, não de refino [LITERATURA + ressalva de transferibilidade] | MTBF/MTTR; taxa de falha por ativo [NORMA: EN 15341:2019, escopo] |
| **T9** | **Integridade elétrica como item auditado pelo regulador** | Fiscalização ANP 2024: 35 ações, 236 não conformidades (37 críticas, 15,7 %), 33 interdições totais ou parciais; achado literal "painel elétrico com baixo isolamento" [FATO: ANP, RASO 2024, p. 6, 65] | O SGSO exige, na prática nº 13, "planos e procedimentos para inspeção, teste e manutenção" alinhados a normas e boas práticas [NORMA: ANP Res. 43/2007, RT do SGSO, 13.2.1] | Não conformidade regulatória tem custo direto (interdição) e custo de reputação; a evidência de prognóstico é insumo de auditoria [INFERÊNCIA] | Não conformidades e interdições; incidentes SHEQ [FATO: ANP RASO 2024] |
| **T10** | **Manutenção preditiva de item de segurança** | A NR-12 exige, para preditivas, "descrição das técnicas de análise e meios de supervisão centralizados ou de amostragem" [NORMA: NR-12, 12.11.2.2] | O módulo pode **gerar automaticamente** esse texto a partir do cabeçalho de auditoria e do catálogo de normas [INFERÊNCIA; REPO: `app/postprocessor/audit_trail.py`, `STANDARDS_CATALOG`] | Conformidade documental sem esforço adicional de engenharia; reduz custo de auditoria [INFERÊNCIA] | Aderência a NR; itens de prontuário NR-10 (obrigatório acima de 75 kW instalados) [NORMA: NR-10, 10.2.4] |

### 1.3 O que a tabela deliberadamente não faz

Ela **não** converte fenômeno em dinheiro. A conversão exige três parâmetros de planta que nenhum documento do acervo fornece — custo horário de indisponibilidade da unidade, tempo de indisponibilidade por evento e existência de reserva — e é objeto da §3. Apresentar a tabela como se já produzisse valor monetário é precisamente o erro que os críticos de *benchmark* apontam: "confundir parada de TI com parada de produção, misturar perdas anuais com horárias" [LITERATURA: ReliaMag 2026 — confiança B].

---

## 2. Custo de indisponibilidade: o que está verificado, com ressalva por levantamento

### 2.1 Distinção obrigatória entre as três grandezas

Os três números são frequentemente citados como se fossem intercambiáveis, e não são [INFERÊNCIA a partir da comparação das metodologias declaradas]:

$$
\underbrace{C_h\ [\mathrm{US\$/h}]}_{\text{custo por hora de parada}}
\quad\ne\quad
\underbrace{C_{ano}\ [\mathrm{US\$/ano\cdot instalação}]}_{\text{custo anual por instalação}}
\quad\ne\quad
\underbrace{C_{rep}\ [\mathrm{US\$/evento}]}_{\text{custo de troca do ativo}}
$$

com $C_{ano} \approx C_h \cdot H_{ind}$, sendo $H_{ind}$ [h/ano] as horas anuais de indisponibilidade não programada — relação que só é válida se as duas grandezas vierem do mesmo levantamento e da mesma amostra [CÁLCULO PRÓPRIO; ressalva metodológica].

### 2.2 Custo por hora de parada não programada

| Setor / escopo | Valor | Ano de referência | Amostra e método | Ressalva metodológica | Confiança |
|---|---|---|---|---|---|
| **Óleo e gás** | **≈ US$ 500 mil/h**; "mais que dobrou em dois anos" | 2021–22 | 56 entrevistas (jan/2021–ago/2022), extrapolação por número de plantas/empregados | Relatório de fornecedor; "the higher the oil price … the higher the losses" [LITERATURA: TCOD 2024, p. 6]. O TCOD 2024 registra que em 2023 o custo **horário** em O&G caiu acentuadamente frente ao pico de 2022, retornando a patamar "broadly similar to that in 2019", com o barril de volta a US$ 60–80 [LITERATURA: TCOD 2024, p. 6]; e, em grandeza distinta, que o custo **anual por planta** em O&G em 2023 foi metade do de 2019, tendo sido o triplo em 2022 [LITERATURA: TCOD 2024, p. 8]. As duas grandezas não se confundem: **não** escrever "o custo horário caiu pela metade" | M |
| Automotivo | US$ 2,3 mi/h | 2023 | 181 entrevistas (abr/2019–mar/2023) | Idem; a ressalva da fonte é restrita aos **resultados combinados entre setores**, que "are not directly comparable year-on-year and should be seen as indicative only" [TCOD 2024, p. 6] | M |
| Bens de consumo (FMCG) | US$ 36 mil/h | 2023 | Idem | Idem | M |
| **Média multissetorial** | **US$ 125 mil/h** | 2023 | 3.215 decisores de manutenção (Sapio Research, jul/2023), setores incluindo O&G e químico | Encomenda de fornecedor de serviços de confiabilidade; amostra grande, metodologia declarada | M |
| Multissetorial (citação secundária) | US$ 260 mil/h | 2016 | Atribuído à Aberdeen por reprodução de 2017 | **Fonte primária não localizada** — não usar sem verificação | [INSERIR CITAÇÃO] |

**Fontes**: [LITERATURA: Siemens/Senseye, *TCOD 2022*, p. 4; *TCOD 2024*, p. 2–3, 6, 8, 15]; [LITERATURA: ABB/Sapio 2023, via Reliabilityweb]; [LITERATURA: The Manufacturer 2017 — reprodução].

**Regra de uso** [INFERÊNCIA a partir de TCOD 2024, p. 6 e ReliaMag 2026]: o valor de O&G é **função do preço do barril** e não é transferível entre anos nem entre unidades. Em qualquer apresentação, ele entra como *default* rotulado, e a primeira ação da conversa é substituí-lo pelo número da própria planta — prática recomendada tanto pelo guia de CFO quanto pelos críticos de *benchmark* [LITERATURA: Tractian 2026 — B; ReliaMag 2026 — B].

### 2.3 Custo anual por instalação e por planta

| Escopo | Valor | Ano | Ressalva | Confiança |
|---|---|---|---|---|
| **Instalação de O&G** | **US$ 149 mi/ano** (alta de 76 % em dois anos) | 2021–22 | Extrapolação Siemens/Senseye; vinculada ao pico de preço do petróleo (US$ 115/bbl em jun/2022 contra US$ 30 em mar/2020) [LITERATURA: TCOD 2022, p. 4, 9, 11–12]. A âncora de O&G de 2019–20 **não é publicada** pela fonte; por retroação da própria alta declarada, ≈ US$ 85 mi/ano [CÁLCULO PRÓPRIO: 149/1,76 — valor não publicado pela fonte] | M |
| Planta grande média (multissetorial / instalação FG500) | US$ 129 mi/ano | 2021–22 | Extrapolação Siemens/Senseye; alta de 65 % sobre 2019–20. Valor **multissetorial**, não de O&G, e do biênio 2021–22, não de 2019–20 [LITERATURA: TCOD 2022, p. 2, 4, 12] | M |
| Planta grande média (multissetorial) — **mesma série** da linha anterior | US$ 253 mi/ano; 326 h/ano perdidas; 25 incidentes/mês; tempo de retomada de 49 → 81 min | 2023 | Idem; a progressão 129 → 253 é a **mesma série** (planta grande média, TCOD 2022 → TCOD 2024), não duas séries distintas; o aumento do tempo de retomada é atribuído a perda de mão de obra qualificada [LITERATURA: TCOD 2024, p. 3, 10–11] | M |
| Fortune Global 500 (agregado) | US$ 1,4 tri/ano ≈ 11 % da receita | 2023 | Extrapolação a partir de 181 entrevistas [LITERATURA: TCOD 2024, p. 2–3, 8, 15] | M |
| **O&G *offshore*** | US$ 38 mi/ano (média) a US$ 88 mi (piores); 27 dias/ano; 1 % de parada (3,65 dias) > US$ 5 mi | 2016 (est.) | Estudo Kimberlite/GE; **whitepaper original não acessado**, e as reproduções divergem: US$ 38 mi, US$ 49 mi e US$ 58–59 mi para o mesmo estudo [LITERATURA: MaxGrip; Dispel; Moir et al. 2018, p. 3] | B |
| O&G *offshore* por estratégia | Reativa 8,43 % de parada não programada (US$ 58–59 mi); planejada 7,97 %; **preditiva 5,42 %** (US$ 24 mi); < 24 % dos operadores usavam abordagem preditiva | 2016 | Reprodução acadêmica de estudo patrocinado [LITERATURA: Moir, Niculita e Milligan, PHME 2018, p. 2–3] | M |
| Indústria de processo (agregado) | ≈ 5 % da produção, US$ 20 bi/ano | 2006–07 | Citação indireta de ARC via ABB Review; dado antigo [LITERATURA: ABB Review 3/2007, p. 15] | B |

### 2.4 Refino e o contexto brasileiro

| Evento / grandeza | Valor | Fonte e ressalva |
|---|---|---|
| **Um dia de refinaria de 250 mil b/d parada** | **US$ 19,64 mi ≈ R$ 106 mi**; três dias ≈ US$ 58,9 mi ≈ R$ 318 mi | Cálculo jornalístico com premissas explícitas (Brent US$ 78,55) [LITERATURA: Times Brasil/CNBC, 14 ago. 2026] — **é cálculo de veículo, não de operadora**; confiança M |
| Fator de utilização do parque Petrobras | 95 % (1T/2026); 97,4 % (mar/2026, maior desde dez/2014); **> 100 %** (abr–mai/2026) | [LITERATURA: Times Brasil 2026] — sem folga, toda falha de motor crítico vira perda de produção [INFERÊNCIA] |
| Parada **programada** da RPBC (178 mil b/d) | R$ 500 mi, ≈ 70 dias, sem impacto no abastecimento por planejamento de estoques | [FATO: Agência Petrobras, 28 jun. 2024] — mostra o **contraste**: o custo do programado é orçado; o do não programado, não |
| Paradas programadas 2026 (Petrobras) | RPBC, REPLAN, REGAP e REPAR, mobilizando 3.300 a 4.520 pessoas cada; **US$ 0,5 bi em 2026**; US$ 2,4 bi no PN 2026-30 | [FATO: Petrobras, PN 2026-30, p. 74] |
| Investimentos correntes (manutenção e operação de ativos existentes) | ≈ **US$ 5 bi/ano** | [FATO: Petrobras, PN 2026-30, p. 27] |
| Meta de confiabilidade do refino (RefTOP) | **DO ≥ 97 %** por *benchmark* Solomon; ganho acumulado de US$ 1 bi; US$ 1 bi previstos no quinquênio para mais de 150 projetos | [FATO: Petrobras, PN 2026-30, p. 73] |
| TIR real média por segmento | E&P 30 %; **RTC 23 %**; G&EBC 15 % | [FATO: Petrobras, PN 2026-30, p. 30 — leitura de gráfico] |
| Parada **não programada** por falha de energia externa — Reduc (≈ 240 mil b/d) | ≈ 13 dias parada a partir de 31 ago. 2016 | [LITERATURA: Reuters/Investing 2016] |
| Parada por falta de energia — BP Whiting (435 mil b/d) | Gasolina do Meio-Oeste +13 c/gal e diesel +30 c/gal em uma semana | [LITERATURA: EIA, *Today in Energy*, 13 fev. 2024] |

**Leitura executiva defensável** [INFERÊNCIA]: o par "R$ 500 mi orçados para 70 dias de parada programada" contra "R$ 106 mi por dia de parada não programada" é o argumento mais forte disponível em contexto brasileiro, porque compara duas grandezas da mesma ordem e do mesmo setor, ambas de fonte acessada, e explicita que a diferença entre elas é **planejamento**, não tecnologia.

### 2.5 Custo de troca de motor MT — a lacuna que não pode ser preenchida por estimativa

**Nenhuma fonte primária acessada nesta pesquisa fornece**: (i) custo de rebobinagem de motor de indução MT de 1250 kW / 4,16 kV; (ii) custo de reposição do mesmo motor; (iii) prazo de entrega de sobressalente; (iv) custo por evento de falha de motor MT em refinaria ou plataforma, com ou sem reserva instalada [INSERIR CITAÇÃO]. As evidências parciais disponíveis, todas insuficientes para substituir os itens acima:

- Em geração de energia, quebras mecânicas e elétricas respondem por **mais de 70 % dos eventos e mais de 80 % do impacto financeiro** de 427 sinistros entre 2021 e 2025 (US$ 3,7 bi), com prazos de reposição "de anos" para grandes ativos [LITERATURA: FM via IT Brief 2026 — confiança B, secundária; a fonte primária não foi acessada].
- No setor de petróleo e carvão dos EUA (SIC 29, dados de 1994), estimavam-se 834 mil motores de potência integral em 1.971 estabelecimentos, com 54,6 % da energia em motores acima de 200 HP e 59 % em bombas [LITERATURA: DOE/EERE 1998 (reimpr. 2002), p. 116–118] — indica concentração de energia, **não** custo de falha.
- O barramento estudado no Documento B tem 20 motores de indução [FATO: doc B, p. 2]; o número de motores MT por refinaria ou plataforma brasileira não consta de nenhuma fonte pública acessada [INSERIR CITAÇÃO].

**Consequência de projeto** [INFERÊNCIA]: $C_{rep}$ e $T_{ind}$ são **entradas obrigatórias do usuário**, com valor-padrão explicitamente rotulado como hipótese e bloqueio de relatório enquanto não substituídos. Não há alternativa metodologicamente honesta: o módulo não pode inventar o número que a fonte não fornece.

### 2.6 Adoção e barreiras — o que sustenta o discurso e o que o limita

| Indicador | Valor | Fonte | Confiança |
|---|---|---|---|
| Empresas no nível "PdM 4.0" (analítica preditiva) | **11 %**, estável entre 2017 e 2018 (n = 268, BE/DE/NL) | PwC/Mainnovation 2018, p. 3, 8 | A |
| Empresas sem planos de PdM 4.0 cujo motivo declarado é "**no good business case / not relevant**" | **63 %** dos 40 % sem planos (≈ 25 % dos 268) — categoria **composta e não desdobrada pela fonte**: "a good business case for PdM 4.0 could not be made **or that it is not relevant to their business**"; contra 23 % sem dados e 8 % sem capacidade analítica | PwC 2018, p. 8 | A |
| Fatores críticos de sucesso | Disponibilidade de dados **67 %**; orçamento **60 %** | PwC 2018, p. 9 | A |
| Objetivo primário declarado | *Uptime* 51 %; satisfação do cliente 12 %; custo 11 %; SHEQ 8 %; extensão de vida 7 % | PwC 2018, p. 9 | A |
| Resultados entre 67 implantadores | 95 % reportam resultado; *uptime* +9 % (até +25–30 %); custo −12 %; SHEQ −14 %; vida do ativo +20 % — **provavelmente em equipamentos isolados, pilotos, *low hanging fruit*** (ressalva dos próprios autores) | PwC 2018, p. 10 | A |
| Adoção de PdM (EUA/Canadá, n = 1.320) | **27 % em 2025**, contra 30 % em 2024; 71 % têm preventiva como estratégia principal, mas **58 % gastam mais da metade do tempo reagindo**; idade média dos equipamentos 24 anos | MaintainX 2025 | M (fornecedor de CMMS) |
| Confiança / explicabilidade como barreira | **43 %** citam *trust*/explicabilidade/transparência; qualidade de dados 54 %; integração de legado e silos 48 %; só 34 % têm *streaming* em tempo real; **7 %** têm IA embutida nos processos centrais | IIoT World 2026 | M (amostra autosselecionada) |
| C-suite e IA | 94 % de 1.600 executivos (12 mercados, incl. Brasil) planejam expandir IA industrial; **17 %** implementaram plenamente o plano inicial; **37 % dizem que o próprio C-suite não entende como a IA funciona**; 48 % precisam justificar recursos continuamente | Honeywell/Wakefield 2024 | M |
| Vínculo com resultado financeiro | Só **25 %** geram valor significativo com IA; "a maioria das empresas não acompanha KPIs financeiros de suas iniciativas de IA" | BCG, *AI Radar* 2025 | A |
| Papel do CFO | Onde o CFO tem autoridade plena sobre investimento digital, **42 %** das organizações atingem lucratividade acima da média, contra **18 %** sem essa autoridade | Deloitte 2025 | A |
| Brasil — barreiras | Custo **66 %**; falta de conhecimento 25 %; **dificuldade de perceber retorno 25 %**; 69 % usam ≥ 1 tecnologia digital (48 % em 2016) | CNI 2022 | A |
| Brasil — cultura executiva | "Diversas empresas encontram dificuldades junto aos altos executivos para aprovação de projetos"; executivos julgam Indústria 4.0 "apenas modismo" ou priorizam projetos "cuja avaliação dos benefícios é mais simples" (24 entrevistas com gerentes/diretores, 2019) | CNI 2020, p. 10–11 | A (qualitativo) |
| Gestão de ativos certificada | 322 organizações certificadas ISO 55001 no mundo (2022); **16 na América do Sul, 6 no Brasil**; Petrobras declara "primeiro e único parque termelétrico certificado" (13 usinas, 4,9 GW) | Favarão da Silva 2022, p. 78; Petrobras PN 2026-30, p. 89 | M / A |

---

## 3. Modelo de decisão econômica

### 3.1 Forma mínima, na notação pedida

A forma que o diretor de planta reconhece de imediato é o custo esperado do evento:

$$
E[C] \;=\; P(\text{falha}\mid\text{saúde}) \times \bigl(C_{reparo} + C_{lucro\ cessante}\times \mathrm{MTTR}\bigr)
\tag{3.1}
$$

com $E[C]$ [US$/horizonte] o custo esperado no horizonte considerado; $P(\text{falha}\mid\text{saúde})\in[0,1]$ a probabilidade de falha **condicionada ao estado de saúde estimado**, adimensional; $C_{reparo}$ [US$] o custo direto de reparo ou substituição; $C_{lucro\ cessante}$ [US$/h] a margem de contribuição perdida por hora de indisponibilidade; e $\mathrm{MTTR}$ [h] o tempo médio de reparo — na acepção operacional de tempo de indisponibilidade do **processo**, não apenas do ativo [INFERÊNCIA: distinção necessária porque, com reserva instalada, o MTTR do processo é muito menor que o do motor].

**Por que (3.1) é insuficiente sozinha** [INFERÊNCIA a partir de Hölzel e Gollnick 2015]: ela precifica apenas o evento evitado. Não precifica o custo de agir, o custo de agir sem necessidade, nem o custo do próprio sistema de prognóstico — os três termos que decidem o sinal do resultado.

### 3.2 Forma completa: política sem e com prognóstico

Sem prognóstico, no horizonte $H$ [meses ou anos]:

$$
E[L_0] \;=\; P_f(H)\cdot\bigl(C_h\,T_{ind} + C_{rep} + C_{pen}\bigr)
\tag{3.2}
$$

Com prognóstico, com intervenção planejada disparada quando $\mathrm{RUL}_{p10} < H$:

$$
E[L_1] \;=\; P_f'(H)\cdot\bigl(C_h\,T_{ind} + C_{rep} + C_{pen}\bigr)
\;+\; P_{int}\,C_{plan}
\;+\; E[N_{FA}]\,C_{FA}
\;+\; C_{PHM}
\tag{3.3}
$$

$$
V \;=\; E[L_0] - E[L_1]
\tag{3.4}
$$

com $C_h$ [US$/h] o custo horário de indisponibilidade da unidade; $T_{ind}$ [h] o tempo de indisponibilidade por evento (função da existência de reserva); $C_{rep}$ [US$] o reparo; $C_{pen}$ [US$] penalidades contratuais ou regulatórias; $P_f(H)$ e $P_f'(H)$ [–] as probabilidades de falha no horizonte sem e com a política prognóstica; $P_{int}$ [–] a probabilidade de a política disparar uma intervenção planejada; $C_{plan}$ [US$] o custo da intervenção planejada; $E[N_{FA}]$ [eventos/horizonte] o número esperado de falsos alarmes; $C_{FA}$ [US$] o custo unitário do falso alarme; $C_{PHM}$ [US$/horizonte] o custo do próprio sistema. A condição de adoção é $V>0$, e **$V$ é o teto do custo aceitável do sistema** — resultado que Hölzel e Gollnick estabelecem explicitamente ao apontar que o ganho máximo de VPL de US$ 5,6 mi por aeronave "é ao mesmo tempo o limite superior do custo de aquisição" do sistema PHM [LITERATURA: Hölzel e Gollnick 2015, p. 13; formulação transposta em `c_level_demanda_rul.md` §5.3].

### 3.3 Base metodológica publicada de cada termo

| Termo | Método publicado que o sustenta | Rótulo |
|---|---|---|
| Incerteza em $P_f$, $C_h$, $T_{ind}$ | ROI de PHM por simulação estocástica de custo de ciclo de vida; "acomodar as incertezas no cálculo de ROI de PHM está no cerne do desenvolvimento de *business cases* realistas"; *point estimates* não representam *business cases* | [LITERATURA: Feldman, Jazouli e Sandborn 2009; Sandborn e Wilkinson 2007; página CALCE] |
| $E[N_{FA}]\,C_{FA}$ | Análise custo-benefício por simulação de eventos discretos com erros prognósticos ($r=8\,\%$): eventos não programados caem de 5.400 para 4.250 com PHM perfeito, até −420 atrasos; **"taxas altas de falso alarme podem causar deterioração econômica"** frente à referência | [LITERATURA: Hölzel e Gollnick 2015, p. 10–14] |
| $P_{int}$, $C_{plan}$ e o instante ótimo | RUL de ML integrada a Weibull e a política de substituição por blocos com reparo mínimo | [LITERATURA: Choo e Shin, IJPHM 16(1), 2025] |
| Uso do **intervalo** de RUL, não do ponto | Programação estocástica (MILP) com intervalos de confiança de RUL reduz custo de disrupção e cancelamentos "à custa de aumentos moderados no custo de planejamento" | [LITERATURA: Käslin et al., arXiv:2608.22569, 2026 — preprint] |
| Valor da informação do monitoramento | Ignorar a dependência temporal das observações leva a custos "muito maiores que o esperado"; a modelagem correta reduz custos "até um quarto" | [LITERATURA: Nielsen, *Structural Health Monitoring*, 2021] |
| Condição de recuperação do investimento | "A empresa tem de assegurar que o custo adicional de implementar PHM possa ser recuperado por meio de maior eficiência operacional e de manutenção" | [FATO: artigo 07, p. 3] |

### 3.4 Exemplo numérico — **integralmente ilustrativo**

**Advertência que deve acompanhar o exemplo em qualquer apresentação** [rotulação obrigatória]: os valores abaixo servem para exibir a **estrutura** do cálculo e a **sensibilidade** do resultado, não para afirmar o valor do módulo em qualquer planta real. **Dez das onze entradas são hipóteses declaradas** — apenas $C_h$ tem fonte acessada, e ainda assim é média setorial de O&G no biênio 2021–22, não valor de refinaria [LITERATURA: TCOD 2022, p. 4]; duas das dez ($C_{rep}$ e $T_{ind}$) não têm sequer fonte parcial em nenhum documento do acervo [INSERIR CITAÇÃO].

Ativo: o motor de **1250 kW / 4,16 kV** do Documento A [FATO: doc A, p. 3]. Horizonte $H=12$ meses.

| Parâmetro | Valor | Rótulo |
|---|---|---|
| $C_h$ | US$ 500 mil/h | [LITERATURA: TCOD 2022, p. 4 — média setorial de O&G em 2021–22, **não** específica de refinaria; segue o preço do barril] |
| $T_{ind}$ | 48 h | [HIPÓTESE: reserva de motor disponível, troca mecânica e ensaios] |
| $C_{rep}$ | US$ 300 mil | [HIPÓTESE: rebobinagem/reposição de motor MT — INSERIR CITAÇÃO] |
| $C_{pen}$ | 0 | [HIPÓTESE] |
| $P_f(H)$ | 0,05 | [HIPÓTESE; ordem de grandeza compatível com a taxa de falha de enrolamento de ≈ 1,2 %/ano derivada do EPRI, majorada por criticidade — CÁLCULO PRÓPRIO, §1.2, T8] |
| $P_f'(H)$ | 0,01 | [HIPÓTESE] |
| $P_{int}$ | 0,20 | [HIPÓTESE] |
| $C_{plan}$ | US$ 150 mil | [HIPÓTESE] |
| $E[N_{FA}]$ | 0,5/ano | [HIPÓTESE] |
| $C_{FA}$ | US$ 50 mil | [HIPÓTESE] |
| $C_{PHM}$ | US$ 40 mil/ano | [HIPÓTESE] |

**Cenário 1 — motor crítico sem redundância de processo** [CÁLCULO PRÓPRIO]:

$$
E[L_0] = 0{,}05\times(500{.}000\times48 + 300{.}000) = 0{,}05\times 24{.}300{.}000 = \mathrm{US\$}\ 1{.}215{.}000
$$
$$
E[L_1] = 0{,}01\times 24{.}300{.}000 + 0{,}20\times150{.}000 + 0{,}5\times50{.}000 + 40{.}000 = \mathrm{US\$}\ 338{.}000
$$
$$
V = 1{.}215{.}000 - 338{.}000 \approx \mathrm{US\$}\ 877\ \text{mil/ano por motor}
$$

**Cenário 2 — o mesmo motor, com reserva instalada e redundância de processo** ($T_{ind}^{\text{efetivo}}\to 0$) [CÁLCULO PRÓPRIO]:

$$
V = (0{,}05-0{,}01)\times 300{.}000 - \bigl(0{,}20\times150{.}000 + 0{,}5\times50{.}000 + 40{.}000\bigr) = 12{.}000 - 95{.}000 \approx -\mathrm{US\$}\ 83\ \text{mil/ano}
$$

**Conclusão do cálculo, que é o resultado mais importante desta seção** [INFERÊNCIA a partir dos dois cenários]: o valor do RUL para a diretoria é **função primária da criticidade** — existência de reserva e redundância de processo —, e não da acurácia do modelo. A variação de $T_{ind}$ de 48 h para 0 h inverte o sinal de $V$ sem alterar nenhum parâmetro de degradação. Duas consequências obrigatórias: (i) o módulo deve **classificar motores por criticidade antes de estimar RUL**; (ii) o resultado deve ser reportado como **faixa** com sensibilidade explícita a $P_f$, $T_{ind}$ e $C_h$, jamais como número único.

### 3.5 Extensão a valor de opção: adiar ou antecipar a intervenção

O modelo (3.2)–(3.4) compara duas políticas fixas. A decisão real é **sequencial**: a cada atualização do prognóstico, o gestor escolhe entre intervir agora, adiar até a próxima janela e reavaliar, ou antecipar. Formalizando a escolha de adiamento por $\Delta t$ [meses] [PROPOSTA; formalização própria ancorada em Choo e Shin 2025, Käslin et al. 2026 e Nielsen 2021]:

$$
V_{op}(t) \;=\; \max\Bigl\{\,0,\;\; E\bigl[C_{\text{intervir em }t}\bigr] \;-\; \mathbb{E}_{\mathcal{I}_{t+\Delta t}}\bigl[C_{\text{intervir em }t+\Delta t}\bigr]\,\Bigr\}
\tag{3.5}
$$

sujeito à **restrição de exercibilidade**, que é a única parte da expressão que a física impõe:

$$
\mathrm{RUL}_{p10}(t) \;>\; \Delta t \;+\; T_{mob}
\tag{3.6}
$$

com $\mathcal{I}_{t+\Delta t}$ o conjunto de informação disponível após a próxima atualização do prognóstico; $\mathrm{RUL}_{p10}$ [meses] o percentil 10 da distribuição de vida remanescente; e $T_{mob}$ [meses] o tempo de mobilização de sobressalente, equipe e janela de parada.

Três leituras, cada uma com o seu rótulo:

1. **O valor de adiar é o valor da informação futura.** É exatamente a grandeza que Nielsen (2021) formaliza como valor da informação de monitoramento, com a advertência de que ignorar a dependência temporal das observações produz custos "muito maiores que o esperado" [LITERATURA: Nielsen 2021]. Um prognóstico cujo intervalo **não estreita** com o tempo não gera valor de opção — daí a métrica de convergência de Saxena et al. ser requisito, e não refinamento [LITERATURA: Saxena et al., IJPHM 1(1), 2010, PDF p. 16].
2. **O valor de antecipar é o valor de evitar a janela cara.** Antecipar a intervenção para uma parada programada já orçada converte o custo do evento de "não programado a R$ 106 mi/dia" para "incremento marginal de uma parada de R$ 500 mi já planejada" [LITERATURA: Times Brasil 2026; Agência Petrobras 2024; INFERÊNCIA quanto à conversão].
3. **A restrição (3.6) é o que impede a opção de virar procrastinação.** Ela usa o **percentil 10**, não a mediana, porque a decisão é de cauda: o custo do erro é assimétrico. A norma de prognóstico exige exatamente essa declaração conjunta de horizonte preditivo e nível de confiança [NORMA: ISO 13381-1:2015, 3.3, 3.9, 3.10 — edição substituída pela ISO 13381-1:2025, cujo texto não foi lido].

### 3.6 Ancoragem em Strangas et al. (2013): o que aquele artigo demonstra e o que não demonstra

É o único trabalho do corpus que formaliza **quanto a mitigação decidida por prognóstico imperfeito altera o MTBF**, e por isso é a ponte entre o modelo econômico e a engenharia de confiabilidade.

**O que demonstra** [FATO: artigo 09, p. 4–5, eqs. (5)–(11)]. Para uma falta primária de taxa $\lambda_1$ [h⁻¹], quatro caminhos até a falha:

$$
\mathrm{MTBF}_1=\frac{1}{p_1\lambda_1}\ \text{(não detectada)};\qquad
\mathrm{MTBF}_2=\frac{1}{p_{12}\lambda_1}+\frac{1}{\lambda_2}\ \text{(detectada tarde $\to$ falta secundária)};
$$
$$
\mathrm{MTBF}_3=\frac{1}{p_{13}\lambda_1}+\frac{1}{\lambda_3}\ \text{(detectada cedo e mitigada, }\lambda_3\ll\lambda_2);\qquad
\mathrm{MTBF}_4=\frac{1}{\lambda_{10}}+\frac{1}{\lambda_3},\ \ \lambda_{10}=\frac{p_{10}}{t_{sample}}\ \text{(falso positivo)};
$$
$$
\lambda_{sys}=\sum_{i=1}^{4}\frac{1}{\mathrm{MTBF}_i}
$$

com $p_1$, $p_{12}$, $p_{13}$, $p_{10}$ [–] as probabilidades de cada caminho e $t_{sample}$ [h] o intervalo de amostragem da decisão. Resultados numéricos do exemplo: com decisão por diagnóstico direto, $p_{10}=0{,}719$, $\lambda_{10}=0{,}719$ h⁻¹, $\mathrm{MTBF}_4=2{,}326\times10^4$ h, $p_1=0{,}8021$, $\mathrm{MTBF}_1=3{,}895\times10^4$ h e $\lambda_{sys}=1{,}68\times10^{-4}$ h⁻¹; com decisão por prognóstico e limiar de 0,4 sobre $P[q_{t+1}=S_6]$, "both $\mathrm{MTBF}_1$ and $\mathrm{MTBF}_4$ are infinite since no such path is probable" [FATO: artigo 09, p. 8–9]. O artigo declara a lacuna que preenche: "it has been assumed, but not substantiated, that prognosis and mitigation based on it may enhance reliability … It is not clear yet how to determine the effect of mitigation and how false positives and negatives can affect the overall reliability" [FATO: artigo 09, p. 2], e registra o custo da própria mitigação: "A drive, then, once it is modified to alleviate the effects of a fault, has **decreased life expectancy**" [FATO: artigo 09, p. 1].

**O que NÃO demonstra** [FATO: artigo 09 + INFERÊNCIA do fichamento 09, §8; reproduzido de `02_ETAPA2...md`, §7.2]:

1. **Nenhum RUL em unidades de tempo é calculado.** O exemplo entrega a probabilidade de o próximo estado ser falha; a ligação entre a saída do HMM e as taxas $\lambda$ da Tabela IV não é formalizada.
2. **Taxa de falha constante e aditiva**, inadequada a mecanismo de desgaste com risco crescente — que é exatamente o regime do isolamento.
3. **A sequência de observações é sintética e monotônica** (30 observações horárias construídas a partir das estatísticas das projeções LDC), e o limiar de 0,4 é escolhido *a posteriori* sobre a mesma sequência (ajuste *in-sample*); não há validação independente.
4. **Não há modelo de custo.** Falsos positivos entram apenas como redução de MTBF (via $\lambda_3$), sem custo de indisponibilidade; falsos negativos, sem custo de falha catastrófica. A otimização de limiar é, portanto, **unidimensional** — e é precisamente esta a lacuna que (3.2)–(3.4) preenchem.
5. **Inconsistências editoriais**: a desigualdade impressa $\mathrm{MTBF}_3<\mathrm{MTBF}_2<\mathrm{MTBF}_1$ conflita com o texto que a acompanha; e a eq. (13) do artigo, para vida de isolamento, é dimensionalmente ambígua e não deve ser usada sem reparametrização.
6. **O isolamento aparece apenas como falta secundária** (envelhecimento térmico acelerado pela reconfiguração); o mecanismo primário estudado é contato intermitente em motor PMAC. **Nenhum valor numérico do artigo é reutilizável.**

**Uso correto na narrativa executiva** [INFERÊNCIA]: cite-se Strangas como **estrutura de raciocínio** — "existe literatura revisada por pares que formaliza como o prognóstico imperfeito muda o MTBF, incluindo o custo do falso positivo" — e **nunca** como evidência de ganho quantitativo para motores MT. A frase defensável é: *"a mitigação decidida por prognóstico melhora o MTBF apenas se a taxa de falso positivo estiver abaixo do limiar que a própria formulação determina; abaixo dele o ganho existe, acima dele o sistema piora a confiabilidade"* [FATO: artigo 09, eqs. (10)–(11) e p. 8–9].

---

## 4. Como sustentar o argumento de RUL diante de diretores de planta

### 4.1 Os quatro argumentos que funcionam

**A1 — Evitar a parada não programada.**
*Enunciado*: "Uma hora de parada em óleo e gás custou, em média, cerca de US$ 500 mil no biênio 2021–22, e o custo acompanha o preço do barril; no Brasil, um dia de refinaria de 250 mil b/d parada equivale a cerca de R$ 106 milhões" [LITERATURA: TCOD 2022, p. 4; TCOD 2024, p. 6; Times Brasil 2026].
*Por que funciona*: o custo de parada é o número de abertura que os próprios guias de CFO recomendam, e "zero parada não programada" é prioridade máxima declarada por 72 % dos decisores em um levantamento de 450 respondentes [LITERATURA: Tractian 2026 — B; The Manufacturer 2017 — B].
*Como não errar*: substituir imediatamente pelo número da própria planta; apresentar como faixa vinculada ao barril; **não** somar nem transferir perdas anuais para grandezas horárias [LITERATURA: ReliaMag 2026 — B]. Em particular, a única "metade" publicada pela fonte é o **custo anual por planta** de O&G em 2023 frente a 2019 [LITERATURA: TCOD 2024, p. 8]; quanto ao custo **horário**, a fonte diz que em 2023 ele caiu acentuadamente frente ao pico de 2022 e voltou a patamar "broadly similar to that in 2019" [LITERATURA: TCOD 2024, p. 6] — enunciar "o custo horário caiu pela metade" é exatamente o erro que este item proíbe.

**A2 — Converter CAPEX de troca preventiva em OPEX planejado.**
*Enunciado*: a decisão deixa de ser "trocar por calendário" e passa a ser "intervir na próxima janela de parada quando $\mathrm{RUL}_{p10}$ cair abaixo do horizonte de mobilização", conforme (3.5)–(3.6).
*Por que funciona*: a extensão de vida do ativo é benefício reportado por 46 % dos implantadores, com média de +20 % [LITERATURA: PwC 2018, p. 10]; e o dinheiro da manutenção já existe — a Petrobras declara ≈ US$ 5 bi/ano de investimentos correntes voltados a manutenção e operação de ativos existentes [FATO: PN 2026-30, p. 27], de modo que o pleito é de **realocação**, não de orçamento novo.
*Como não errar*: a literatura de política de substituição exige a integração explícita da RUL a um modelo de substituição, não a substituição do calendário por intuição [LITERATURA: Choo e Shin 2025].

**A3 — Sustentar a decisão de operar sob N-1 com risco quantificado.**
*Enunciado*: as três soluções da frente de Pareto do Documento B operam com margem de **0,00 %, 0,94 % e 1,88 %** sobre o ajuste de *ride-through* de 0,85 pu, enquanto a discrepância típica documentada entre estudo quase-estático e dinâmico ($\pm$ 0,5 %) já consome 53 % da margem intermediária [FATO: doc B, p. 3, Tabela III; LITERATURA: Nivelo et al., IPST 2021, p. 6–8; CÁLCULO PRÓPRIO: `02_ETAPA2...md`, §2.3–2.4].
*Por que funciona*: transforma uma decisão hoje tomada por regra fixa em decisão com risco explícito, e a exigência de "classificar os riscos identificados" e considerar "a análise histórica de incidentes" é textual no regulamento do SGSO [NORMA: ANP Res. 43/2007, RT do SGSO, prática nº 12, item 12.3].
*Como não errar*: **não** dizer que "a margem de 0,85 pu de B é insuficiente" — é julgamento sobre um ajuste que B declara como típico; dizer que as soluções operam com 0 a 1,9 % de margem e que a incerteza documentada é dessa ordem [`02_ETAPA2...md`, §11.2].

**A4 — Atender gestão de ativos ISO 55001 e requisitos de seguradora.**
*Enunciado ISO*: a ISO 55000:2024 organiza a decisão na linguagem de "valor e risco para partes interessadas"; a certificação ainda é rara no país (6 organizações brasileiras entre 322 no mundo em 2022) e a Petrobras a declara como diferencial do seu parque termelétrico [LITERATURA: Favarão da Silva 2022, p. 78; FATO: PN 2026-30, p. 89; NORMA: ISO 55000:2024 — texto não lido].
*Enunciado seguro*: existe produto de garantia de desempenho lastreada em seguro para soluções de manutenção preditiva e monitoramento de condição, e a HSB reporta ROI médio de 506 % entre seus dez maiores clientes de IoT em 2021 [LITERATURA: Munich Re *IoT Cover*; HSB 2022 — ambas M].
*Como não errar*: **nenhuma fonte primária acessada quantifica redução de prêmio condicionada a RUL de motores elétricos**. O argumento correto é de **elegibilidade e de evidência** ("o módulo produz o registro que a seguradora pede"), nunca de desconto prometido [INSERIR CITAÇÃO].

### 4.2 As seis objeções típicas e a resposta técnica a cada uma

| # | Objeção | Base documental da objeção | Resposta técnica |
|---|---|---|---|
| **O1** | **"É uma caixa-preta; não vou parar um motor por causa de um número que ninguém explica."** | 43 % citam confiança/explicabilidade/transparência como barreira [LITERATURA: IIoT World 2026]; 37 % dos executivos dizem que o próprio C-suite não entende IA [Honeywell 2024]; engenheiros de processo "contornam ou reverificam IA que não mostra o trabalho" [Seeq/Control Global 2026 — B] | A cadeia é **física e auditável elo a elo**: manobra → vetor de estresse $\mathbf{s}_{m,j}=(V_{pk}^{\phi\text{-}g},V_{pk}^{\phi\text{-}n},T_1,t_r,(\mathrm{d}v/\mathrm{d}t)_{\max},E_s,f_{\mathrm{dom}},t_j)$ → severidade normalizada $S_{m,j}=V_{pk,j}/U_{\mathrm{env}}(T_{1,j})$ → dano $\Delta D^{el}_m$ → RUL → custo [`01_ETAPA1...md`, §8.2]. Cada elo cita norma e página; o relatório abre com cabeçalho de auditoria e hash SHA256 dos insumos [REPO: `app/postprocessor/audit_trail.py`; convenção obrigatória 4.1.2]. A explicabilidade aqui **não é XAI pós-hoc sobre um modelo opaco**: é decomposição do dano por mecanismo |
| **O2** | **"Não temos os dados."** | Dados são fator crítico para 67 % e ausência de dados é a razão de 23 % dos que não planejam PdM [PwC 2018, p. 8–9]; qualidade de dados é barreira para 54 % e só 34 % têm *streaming* em tempo real [IIoT World 2026]; ≈ 3/4 ainda dependem de historiadores [TCOD 2024, p. 13] | O MVP é **baseado em simulação**, não em telemetria: os estressores vêm do modelo ATP/EMTP de manobra e do fluxo de potência de partida que a planta já produz em estudos de projeto [FATO: doc A; doc B]. Isso inverte a ordem usual: o *business case* é montado **antes** do investimento em sensores, e o sensor entra depois, priorizado pelo mecanismo que o próprio modelo apontou como dominante — que é o passo FMMEA de Vichare e Pecht [FATO: artigo 07, p. 6–7]. Ressalva honesta: sem dado de campo, o resultado é **prognóstico baseado em simulação**, não gêmeo digital [INFERÊNCIA: a sincronização com o ativo é o que separa os dois — NIST AMS 400-2, transcrevendo ISO/DIS 23247-1] |
| **O3** | **"Não vai integrar com nosso OT/TI; e tem risco cibernético."** | Integração de legado e silos é barreira para 48 % [IIoT World 2026]; cibersegurança para 22 % [MaintainX 2025]; "em vários casos foi o departamento de TI, não o conselho, que freou o projeto" [PwC 2018, p. 9] | O módulo é *offline* e roda no ambiente de engenharia, consumindo arquivos de estudo (ATP, OpenDSS) e devolvendo relatório HTML/PDF: **não requer conexão a rede OT nem escrita em sistema de controle** [INFERÊNCIA a partir da arquitetura do repositório]. A integração com CMMS/historiador é fase posterior e opcional. Onde houver dado de campo, a arquitetura de referência é a cadeia de seis blocos DA→DM→SD→HA→PA→AG da ISO 13374, implementada pelo OSA-CBM/MIMOSA — padrão aberto, não protocolo proprietário [LITERATURA: MIMOSA; esquema XSD OSA-CBM 3.3.1] |
| **O4** | **"Se o modelo errar, de quem é a responsabilidade?"** | O artigo que formaliza mitigação por prognóstico declara que "modificar o sistema com base em detecção ou prognóstico acarreta perigos decorrentes de falsos positivos e negativos" [FATO: artigo 09, p. 9]; e que "operadores humanos precisam confiar no sistema preditivo" em aplicações críticas [LITERATURA: Cummins et al. 2024] | Três respostas concretas. **(i) O módulo não comanda**: ele emite recomendação (bloco AG), e a decisão permanece com o responsável técnico, cujo nome consta do cabeçalho de auditoria [REPO: convenção 4.1.2]. **(ii) A incerteza é declarada**: RUL é distribuição com $p05/p50/p95$ e horizonte, exigência normativa de prognóstico [NORMA: ISO 13381-1, 3.3, 3.9, 3.10]. **(iii) As limitações são renderizadas em todo laudo**, por construção do repositório (`KNOWN_LIMITATIONS` + `format_limitations_html`) [REPO: convenção 4.1.4] — inclusive a de que os parâmetros de curva de vida para mica-epóxi de MT não têm fonte primária [`01_ETAPA1...md`, limitação (b)] |
| **O5** | **"O sensor é caro."** | Custo é a principal barreira para 66 % das indústrias brasileiras [CNI 2022]; orçamento é fator crítico para 60 % [PwC 2018, p. 9]; Vichare e Pecht alertam que a caracterização e o desenvolvimento de modelo "pode ser demorada, custosa e pode não funcionar" [FATO: artigo 07, p. 5] | Duas respostas. **(i) A Fase 1 não compra sensor**: usa simulação e ensaios offline que a planta já faz (IR/PI, tan δ, DP, ensaio de surto) [`01_ETAPA1...md`, §7.1]. **(ii) Quando o sensor entrar, a exigência é conhecida e há rota de baixo custo**: reconstruir $T_1=1{,}67(t_{90}-t_{30})$ de uma frente de 0,1 µs exige 50–100 MS/s e banda ≥ 3,5 MHz [CÁLCULO PRÓPRIO: `01_ETAPA1...md`, §8.3], mas o detector de pico analógico de Jensen et al. reduz a exigência a **10 MSa/s** — preservando o pico, embora **não** o tempo de frente [FATO: artigo 02, p. 7–8; INFERÊNCIA quanto à limitação]. E, por (3.4), o valor $V$ é o **teto** do orçamento aceitável: a pergunta "quanto posso gastar?" tem resposta calculável antes da compra [LITERATURA: Hölzel e Gollnick 2015, p. 13] |
| **O6** | **"Já temos manutenção preventiva."** | 71 % declaram a preventiva como estratégia principal, mas **58 % gastam mais da metade do tempo reagindo**; idade média dos equipamentos de 24 anos [MaintainX 2025]; no Brasil, a corretiva representava ≈ 37 % das horas totais e a indisponibilidade média era de 12,6 % (2017) [LITERATURA: Favarão da Silva 2022, p. 21, citando ABRAMAN 2017] | A preventiva por calendário **não vê o mecanismo em questão**. As três normas de diagnóstico de isolamento negam predizer tempo até falha a partir dos **seus respectivos** indicadores, cada uma com enunciado próprio: **DP** — "there is **no evidence that the time to failure** of the stator winding insulation can be estimated using any PD quantity, even in combination with other electrical tests" [NORMA: IEC TS 60034-27-2:2012, Introdução, *Limitations* — amostra lida; **a permanência da sentença na ed. 2023 não foi verificada**: da Introdução acessada da IEC 60034-27-2:2023 consta apenas "comparative, rather than absolute measurements … acceptance criteria with simple limits … cannot be established"]; **tan δ** — "the trend evaluations cannot be used to predict the time to failure" [NORMA: IEC 60034-27-3:2015, Introdução]; **IR/PI** — idem, incidindo sobre avaliações de tendência de IR/PI, não sobre DP [NORMA: IEC 60034-27-4:2018, Introdução]. E o único ensaio normalizado que solicita diretamente a isolação entre espiras é o de surto, que é offline e potencialmente destrutivo [NORMA: IEEE 522-2023, escopo]. O módulo, portanto, **não compete com a preventiva**: ocupa o espaço que a própria norma declara vago [`00_INDICE.md`, §1.4, item 4] |

### 4.3 Regra transversal de honestidade do discurso

Toda afirmação sobre adoção ou mercado usada em apresentação deve carregar, na mesma frase ou em nota, **três atributos**: amostra, ano e patrocínio. Exemplo de formulação correta: *"entre 268 empresas de Bélgica, Alemanha e Países Baixos pesquisadas por PwC e Mainnovation em 2018, 11 % estavam no nível de analítica preditiva"*. Exemplo de formulação incorreta, ainda que factualmente derivada da mesma fonte: *"apenas 11 % das indústrias fazem manutenção preditiva"*. A dispersão entre 11 % (PwC, nível 4), 27–30 % (MaintainX) e "quase metade com equipe dedicada" (Siemens) explica-se pelo denominador (empresa, planta, ativo), pelo nível de maturidade e pela autosseleção da amostra [INFERÊNCIA a partir da comparação das metodologias declaradas].

---

## 5. O painel executivo: o que deve mostrar e o que não deve

### 5.1 Conteúdo mínimo obrigatório

| Elemento | Forma exigida | Lastro |
|---|---|---|
| **Asset Health Index (AHI) por motor, em bandas** | Escore contínuo mapeado em cinco bandas, com critérios publicados e regra de agregação **declarada** | [LITERATURA: Ofgem CNAIM v2.1, 2021 — *Health Score* 0,5–15 → bandas HI1–HI5 → probabilidade de falha; CIGRE TB 858, 2021 — metodologia em oito passos]. Transferência de T&D para motores MT é [HIPÓTESE] a calibrar |
| **Probabilidade de falha no horizonte** | $\mathrm{PoF}(H)$ derivada do escore ou do modelo, com $H$ = próximo ciclo de parada programada | [LITERATURA: CNAIM §4.3–4.4]; ancoragem de prior no EPRI (§1.2, T8) |
| **Criticidade / consequência** | Bandas de consequência (produção, segurança, ambiente), **separadas** da saúde | [LITERATURA: CNAIM — *Criticality Index*]; exigida pelo resultado da §3.4 |
| **Risco monetizado** | $\text{Risco} = \mathrm{PoF}\times\text{consequência}$, em moeda; semáforo aplicado ao **risco**, não à saúde isolada | [LITERATURA: CNAIM — risco monetizado]; [INFERÊNCIA quanto ao semáforo] |
| **RUL com intervalo** | $p05/p50/p95$ **e** horizonte de prognóstico $\mathrm{PH}(\alpha)$, em unidades de negócio (meses, manobras, partidas) | [NORMA: ISO 13381-1, 3.3, 3.9, 3.10]; [LITERATURA: Saxena et al. 2010; ProgPy `UncertainData`] |
| **Tendência e convergência** | Trajetória do AHI e **estreitamento** do intervalo ao longo do tempo | [LITERATURA: Saxena et al. 2010, PDF p. 16 — convergência] |
| **Ação recomendada com custo evitado** | Ação, janela e $V=E[L_0]-E[L_1]$ com faixa de sensibilidade | (3.2)–(3.4); [LITERATURA: Hölzel e Gollnick 2015] |
| **Rastreabilidade até a norma** | Versão do software, hash SHA256 dos insumos, normas aplicadas com cláusula, responsável técnico | [REPO: `app/postprocessor/audit_trail.py`, `make_audit_header`, `STANDARDS_CATALOG`; convenções 4.1.2 e 4.1.5] |
| **Explicação por fatores dominantes** | Decomposição do dano por mecanismo (térmico $D^{th}$, elétrico $D^{el}$, sinergia $D_{sin}$) | [`02_ETAPA2...md`, eq. (5.1)]; [LITERATURA: revisão PRISMA de XAI em PHM, *Sensors* 21(23):8020, 2021] |
| **Estado de dados e deriva** | Cobertura de simulações/sensores, última atualização, alerta de deriva de distribuição dos insumos | [LITERATURA: Evidently AI — deriva de dados/conceito/predição; Google Cloud — gatilhos de retreinamento] |
| **Limitações declaradas** | Bloco renderizado em todo laudo | [REPO: `KNOWN_LIMITATIONS`; convenção 4.1.4] |

### 5.2 Por que RUL sem intervalo é inaceitável — três razões independentes

1. **Razão normativa.** A norma de prognóstico exige a declaração conjunta de horizonte preditivo, limiar de falha e **nível de confiança**; um número isolado não satisfaz nenhum dos três [NORMA: ISO 13381-1:2015, 3.3, 3.9, 3.10 — substituída pela edição 2025, cujo título passou a "General guidelines **and requirements**", texto não lido].
2. **Razão epistêmica.** "É praticamente impossível prever eventos futuros com precisão"; a literatura de referência sustenta que, no contexto de gestão de saúde baseada em condição, "somente a abordagem bayesiana é aplicável" — isto é, a saída natural do problema **é uma distribuição**, e reportar o ponto é descartar informação, não simplificá-la [LITERATURA: Sankararaman e Goebel, IJPHM 6(4), 2015].
3. **Razão de decisão.** A decisão de (3.5)–(3.6) usa o **percentil 10**, não a mediana, porque o custo do erro é assimétrico; e a otimização de manutenção com intervalos de confiança de RUL reduz custo de disrupção "à custa de aumentos moderados no custo de planejamento" — ganho que **desaparece** se apenas o ponto for entregue [LITERATURA: Käslin et al. 2026]. Complementarmente, no caso concreto deste estudo, o próprio termo de sinergia torna a soma desacoplada uma **cota inferior de dano**, isto é, cota superior de RUL: um valor único seria sistematicamente otimista [INFERÊNCIA: `02_ETAPA2...md`, §5.2].

### 5.3 Por que a explicabilidade da decomposição é requisito, e não enfeite

1. **Porque é a barreira declarada.** Confiança/explicabilidade é barreira para 43 % dos profissionais industriais, e a opacidade e a rastreabilidade das decisões figuram entre os obstáculos centrais à IA na manufatura [LITERATURA: IIoT World 2026; Ahangar, Farhat e Sivanathan, *Sensors* 25(14):4357, 2025].
2. **Porque a decomposição é a própria evidência física.** No caso deste módulo, explicar não é anexar valores SHAP a um regressor: é exibir $D(t)=D^{th}+D^{el}+D_{sin}$ com cada parcela remetida à sua equação e à sua norma [`02_ETAPA2...md`, eq. (5.1)]. A explicação **é** o modelo.
3. **Porque sem ela o falso alarme não é diagnosticável.** Se o painel apenas emitir "RUL = 8 meses", a equipe não tem como saber se o alerta veio de um evento térmico, de uma manobra severa ou de uma mudança de premissa; e o falso alarme é o termo que a literatura mostra capaz de inverter o sinal do valor [LITERATURA: Hölzel e Gollnick 2015, p. 14].
4. **Porque a norma de trabalho exige a descrição do método.** Para itens de segurança, a NR-12 exige, no caso de preditivas, "descrição das técnicas de análise e meios de supervisão centralizados ou de amostragem" [NORMA: NR-12, 12.11.2.2] — uma exigência que só uma decomposição documentada satisfaz.

### 5.4 O que o painel **não** deve mostrar

| Não exibir | Razão |
|---|---|
| **RUL como número único** ou como data de falha | §5.2, três razões independentes |
| **Matriz de risco 5×5 como saída primária** | A crítica de Cox (2008) registra "resolução pobre" e capacidade de comparar corretamente "menos de 10 %" de pares de riscos escolhidos ao acaso; manter a saída quantitativa (probabilidade × custo) e a matriz apenas como camada de apresentação [LITERATURA: Cox 2008, via revisão terciária; recomendação em `contexto_industrial_brasil_og.md` §4, item 9] |
| **"BIL remanescente"** ou "queda de BIL" | O BIL é nível declarado e verificado por ensaio de tipo, não variável de estado; a grandeza correta é a margem $\gamma(t)=U_w(t)/U_s$ [NORMA: IEC 60071-1:2019, 3.31 e 3.34; `01_ETAPA1...md`, §6] |
| **Percentuais de benefício de fornecedores** apresentados como resultado do módulo | Todos os números de −50 % de parada, −40 % de custo, +85 % de acurácia são de implantações de fornecedor, sem metodologia publicada [LITERATURA: TCOD 2024, p. 14 — confiança B] |
| **Semáforo sobre a saúde isolada** | O semáforo deve refletir **risco** (saúde × consequência); um motor degradado com reserva instalada não é uma emergência, e um motor saudável sem redundância pode ser [INFERÊNCIA a partir de §3.4 e CNAIM] |
| **Alerta sem custo de agir** | Sem $C_{plan}$, $C_{FA}$ e $P_{int}$ ao lado, o painel externaliza para o operador a única decisão que a literatura mostra ser economicamente perigosa [LITERATURA: Hölzel e Gollnick 2015, p. 14; FATO: artigo 07, p. 2 — falso alarme de BIT causa "substituição desnecessária e custosa, requalificação, atraso de expedição e perda de disponibilidade"] |
| **A palavra "gêmeo digital"** enquanto não houver sincronização com o ativo | A definição normativa exige "sincronização entre o elemento observável e sua representação digital"; sem dado de campo, o correto é "modelo de prognóstico baseado em simulação" [LITERATURA: NIST AMS 400-2, PDF p. 8, transcrevendo ISO/DIS 23247-1] |

---

## 6. Narrativa de valor específica dos Documentos A e B

### 6.1 Documento A — o snubber compra severidade reduzida **e** preserva a observabilidade

**Os números reais** [FATO: doc A, Tabela III, p. 3; colunas derivadas em CÁLCULO PRÓPRIO, `01_ETAPA1...md`, §3.2]:

| Fase | Pico sem (kV) | RRRV sem (kV/µs) | Pico com (kV) | RRRV com (kV/µs) | Redução de pico | Redução de RRRV |
|---|---|---|---|---|---|---|
| A | −30,24 | 13,90 | 6,35 | 3,28 | **79,0 %** | **76,4 %** |
| B | 41,44 | 15,05 | 13,65 | 13,11 | **67,1 %** | **12,9 %** |
| C | −38,30 | 19,00 | −9,98 | 9,43 | **73,9 %** | **50,4 %** |

**Três precisões obrigatórias em qualquer apresentação** [CÁLCULO PRÓPRIO + INFERÊNCIA, `01_ETAPA1...md`, §3.2]:
1. O "cerca de 67 %" do resumo de A refere-se **apenas à fase B** (67,06 %); as fases A e C têm reduções de pico **maiores** (79,0 % e 73,9 %).
2. A redução de $\mathrm{d}v/\mathrm{d}t$ é fortemente assimétrica (76,4 % / 12,9 % / 50,4 %), e o artigo sustenta a afirmação de que o snubber "também reduz a taxa de crescimento (de 15,05 para 13,11 kV/µs)" **justamente na fase de menor redução**.
3. Estes são valores de TRV **no disjuntor**, não nos terminais do motor; a diferença é ressalva estrutural declarada [`01_ETAPA1...md`, §3.4].

**A alegação de preservação da assinatura diagnóstica.** O Documento A afirma que os métodos passivos convencionais — arrestadores ZnO e filtros RC/RLC fixos — são "permanentemente conectados", alteram a impedância da rede em regime e "mascaram o conteúdo de alta frequência que é valioso para diagnóstico" [FATO: doc A, p. 1, resumo]; e que o disparo por evento com bloqueio natural no zero de corrente "é o que torna a mitigação seletiva: elementos dissipativos estão presentes apenas enquanto a anomalia dura, preservando as características elétricas de regime e **a assinatura de alta frequência exigida para diagnóstico**" [FATO: doc A, p. 2, III-A].

**Estatuto desta alegação** [HIPÓTESE NÃO QUANTIFICADA — rotulação obrigatória]: o Documento A **não apresenta** nenhuma medida da assinatura preservada — não há espectro comparado com e sem snubber, não há métrica de conteúdo espectral, não há contagem de reignições [FATO por omissão: doc A, p. 1–5]. E a camada digital que extrairia "peak voltage, dv/dt, absorbed energy, spectral content" para alimentar "an incremental insulation degradation model to estimate the remaining useful life" é explicitamente declarada fora do escopo: "The present paper validates only the reflexive layer; the digital protection layer is beyond the scope of this work" [FATO: doc A, p. 2, III-B]. Além disso, a aquisição "only during SCR conduction" implica que, sem *pre-trigger*, a parte inicial do $\mathrm{d}v/\mathrm{d}t$ — a mais relevante para a isolação entre espiras — pode ficar fora do registro [INFERÊNCIA: `01_ETAPA1...md`, §8.3(b)].

**Narrativa de valor defensável, em linguagem de negócio** [INFERÊNCIA]: *"o snubber ativo faz duas coisas ao mesmo tempo: reduz a severidade do evento em 67 a 79 % de pico, e — diferentemente de um filtro fixo — não permanece na rede em regime, de modo que a planta continua a poder observar o transitório. Reduzir o estresse sem perder a observabilidade é o que permite que o mesmo dispositivo seja mitigação e sensor. A parte de mitigação está simulada e quantificada; a parte de observabilidade é hipótese do artigo, não medida nele, e é justamente o que este trabalho se propõe a fechar."* A última oração é obrigatória: sem ela, a apresentação atribui a A um resultado que A não tem.

**O que não dizer** [`02_ETAPA2...md`, §11.2]: "o snubber multiplica a vida do isolamento por 100". Razão de dano **por evento** não é razão de vida, e a razão de $10^2$ (para $n=4$) é ilustração da Etapa 1, com expoentes de fio esmaltado e epóxi puro, não de mica-epóxi [`01_ETAPA1...md`, §5.5].

### 6.2 Documento B — o corte de carga consciente da saúde troca produção por vida do ativo

**Os números reais** [FATO: doc B, p. 2–3, Tabela III; margens em CÁLCULO PRÓPRIO, `02_ETAPA2...md`, §2.3]:

| Solução | Máquinas mantidas | $f_5$ [kW cortados] | $V^{(\mathrm{INRUSH})}_{\min}$ [pu] | Margem sobre $g_1=0{,}85$ pu |
|---|---|---|---|---|
| Mínimo corte (recomendada por B) | M_710, M_800 | **7417** | 0,850 | **0,00 %** |
| Joelho | M_800 | 8127 | 0,858 | 0,94 % |
| Mínimas perdas | nenhuma | 8927 | 0,866 | 1,88 % |
| *(infactível)* Sem corte | todas | 0 | **0,755** | −11,2 % |

**A monotonicidade perversa, em linguagem de negócio** [INFERÊNCIA: `02_ETAPA2...md`, §2.5]. A cadeia derivada na Etapa 2 é monótona no mesmo sentido:

$$
f_5 \downarrow \;\Longrightarrow\; V^{(\mathrm{INRUSH})}_{\min} \downarrow \;\Longrightarrow\; t_{acc}\uparrow \ \text{e}\ \text{margem}\downarrow \;\Longrightarrow\; P[\text{atuação durante a partida}]\uparrow \;\Longrightarrow\; \lambda_A\uparrow
$$

**Tradução para diretoria**: *"quanto menos produção o plano sacrifica hoje, mais frequente se torna, amanhã, o evento que degrada o motor. As três soluções ordenam-se, no eixo de vida do ativo, exatamente ao contrário da ordem em que aparecem no eixo de produção. A solução que preserva mais produção — 1510 kW mantidos — é a que opera com margem zero e a que mais expõe o isolamento."* [FATO: doc B, p. 3 — "machines M_710 and M_800 remain connected, preserving 1510 kW of production"; INFERÊNCIA quanto ao ordenamento].

**Precisão numérica obrigatória** [FATO: doc B, p. 3–4; CÁLCULO PRÓPRIO: `02_ETAPA2...md`, §2.5]: os **490 kW** que B cita na conclusão são o *ganho* da formulação restrita sobre a formulação preliminar de cinco objetivos ($7907-7417=490$ kW), **não** a produção absoluta preservada, que é de **1510 kW** ($8927-7417$). Citar 490 kW como produção preservada erra por fator 3,08.

**Ressalva de fidelidade** [`02_ETAPA2...md`, §2.5]: a leitura por $\lambda_A$ **não contradiz B**. B otimiza o que declara otimizar, e o faz corretamente; o que se mostra é que a frente de Pareto está incompleta em um eixo que B não mede. É essa lacuna que o objetivo adicional $f_6$ (consumo esperado de vida do isolamento) e a restrição $g_4$ (margem de coordenação) preenchem [PROPOSTA: `02_ETAPA2...md`, §6.2, eqs. (6.1)–(6.3)].

### 6.3 A síntese: os dois documentos como duas metades de uma decisão

$$
\underbrace{\text{Documento B fixa }\lambda}_{\text{com que frequência o evento ocorre}}
\qquad\times\qquad
\underbrace{\text{Documento A fixa a severidade}}_{\text{quanto cada evento custa em vida}}
\;=\;
\underbrace{\text{consumo esperado de vida por ano}}_{\text{o que entra em }E[C]}
$$

[INFERÊNCIA verificada elo a elo em `02_ETAPA2...md`, §2.2; nenhum dos dois documentos cita o outro — FATO por omissão em ambos]. Em linguagem de negócio: *"um dos trabalhos decide quantas vezes por ano o motor é submetido ao pior evento; o outro decide quanto cada um desses eventos custa em vida útil. Nenhum dos dois, sozinho, responde à pergunta do diretor — 'quanto tempo esse motor ainda tem?' — e é a combinação dos dois, com o custo por hora de parada da própria planta, que responde."*

E o resultado de decisão que emerge da combinação, formalizado na Etapa 2 [PROPOSTA: `02_ETAPA2...md`, §7.1]: se o snubber reduzir o dano por evento em cerca de duas ordens de grandeza, então **um plano de corte com $\lambda_A$ até duas ordens de grandeza maior produz o mesmo custo dielétrico esperado** — isto é, **o snubber compra tolerância a planos mais agressivos em produção**. Duas ressalvas obrigatórias: $u$ (instalar o snubber) é decisão de projeto, não operacional, o que torna o problema de dois níveis; e o próprio snubber envelhece — o TOR da CIGRE WG C4.76 registra que, sob sobretensões de alta amplitude e alta inclinação, "o nível de isolamento desses dispositivos de supressão pode deteriorar-se gradualmente por efeitos cumulativos" [CIGRE: TOR WG C4.76, 2023-07-31, p. 1–4].

---

## 7. Roteiro de entrega do trabalho computacional (tese + artefato)

### 7.1 Arquitetura de referência e nomenclatura

Mapear os módulos sobre a cadeia funcional de seis blocos da ISO 13374, implementada pelo OSA-CBM da MIMOSA (v3.3.1, 2010; siglas DA/DM/SD/HA/PA/AG verificadas no esquema XSD do namespace `OSACBMV3.3.1`) [LITERATURA: MIMOSA; XSD OSA-CBM 3.3.1]. Nomear as estruturas de dados com as siglas (`InsulationStressInputs` = DA/DM; `HealthAssessment` = HA; `RulPrognosisResult` = PA; `Advisory` = AG) torna a arquitetura auditável contra a norma **sem** exigir conformidade formal ao OSA-CBM, que impõe estruturas e interfaces próprias [INFERÊNCIA: `entrega_trabalho_computacional.md` §5.1]. Advertência: o texto integral da ISO 13374-1/-2 não foi lido; a expansão nominal dos blocos permanece sem citação de cláusula [INSERIR CITAÇÃO].

### 7.2 Métricas de prognóstico obrigatórias no relatório

| Métrica | Definição e parâmetro a declarar | Fonte |
|---|---|---|
| **Prognostic Horizon**, $\mathrm{PH}(\alpha)$ | Diferença entre o instante em que as previsões passam a cumprir o critério de desempenho e o instante de fim de vida; **"a escolha de $\alpha$ depende da estimativa do tempo necessário para a ação corretiva"** — aqui, o tempo de mobilização até a próxima parada programada | [LITERATURA: Saxena et al., IJPHM 1(1), 2010, PDF p. 8, 14] |
| **α-λ** | Métrica binária: a acurácia no instante $t_\lambda$ cai dentro das bandas $\alpha$, expressas como percentagem da RUL real; declarar também $\beta$, a massa de probabilidade mínima dentro das bandas | [idem, PDF p. 11, 15] |
| **RA / CRA** | Erro de previsão relativo à RUL real em $i_\lambda$; forma cumulativa ao longo da trajetória | [idem, PDF p. 13] |
| **Convergência** | Taxa com que acurácia ou precisão melhoram com o tempo, medida pela distância ao centroide da área sob a curva | [idem, PDF p. 16] |
| **RMSE** e **pontuação assimétrica** | RMSE em unidades de RUL; a função assimétrica do desafio PHM08 ($s=e^{-d/13}-1$ para $d<0$; $s=e^{d/10}-1$ para $d\ge0$) penaliza mais a previsão atrasada — mas as constantes **13/10 são escolha de política de risco daquele desafio**, e para isolamento MT devem ser **derivadas do custo de parada** de (3.2)–(3.3), não copiadas | [LITERATURA: Chaoub et al. 2021, p. 5 — secundária fiel; Saxena et al. 2008 — apenas metadados; INFERÊNCIA quanto à derivação] |
| **Cobertura empírica dos intervalos** (PICP) e largura média (MPIW) | Fração de casos em que o valor real cai em $[p05,p95]$ e largura média do intervalo | [LITERATURA: Khosravi et al., IEEE TNN 22(9), 2011 — metadado; página específica INSERIR CITAÇÃO] |

**Hierarquia de aplicação**: PH → α-λ → RA/CRA → convergência [LITERATURA: Saxena et al. 2010].

### 7.3 Quantificação de incerteza e validação sem banco de dados do domínio

1. **Declarar a abordagem.** Bayesiana/filtro (EKF/UKF/PF), *deep ensembles*, *dropout* bayesiano ou predição conforme — e reportar a cobertura empírica obtida. Sankararaman e Goebel sustentam que "somente a abordagem bayesiana é aplicável no contexto de gestão de saúde baseada em condição"; *ensembles* e *dropout* são aproximações práticas sem garantia formal; a predição conforme oferece garantia de cobertura marginal sob intercambiabilidade, hipótese que séries de degradação de um único ativo em geral violam [LITERATURA: Sankararaman e Goebel 2015; Lakshminarayanan et al. 2017; Gal e Ghahramani 2016; Angelopoulos e Bates 2021; INFERÊNCIA quanto à violação].
2. **Aceitar a ausência de banco público do domínio.** Não foi localizado banco público de envelhecimento de isolamento de estator MT no repositório NASA PCoE nem em três consultas à API do Zenodo; a conclusão robusta é "não localizado nas fontes consultadas" [LITERATURA: NASA PCoE; API Zenodo]. Isso condiciona a validação a: **validação de método** em bancos de outros domínios (NASA IGBT, 6 dispositivos sob envelhecimento térmico acelerado — fisicamente o mais próximo; C-MAPSS FD001–FD004 para comparabilidade com a literatura) e **validação física** por trajetórias sintéticas geradas a partir das grandezas de estresse dos Documentos A e B, com o modelo de dano declarado como hipótese [LITERATURA: NASA PCoE; data.nasa.gov; FATO: doc A e doc B].
3. **Escala de qualidade de evidência.** Reproduzível (mesmos dados, mesma análise, semente fixa) → replicável (outros motores/plantas) → robusto (outro estimador) → generalizável [LITERATURA: The Turing Way].

### 7.4 Reprodutibilidade, publicação e DOI

| Item | Ação | Lastro |
|---|---|---|
| Identificador persistente | *Release* no GitHub integrado ao Zenodo, gerando **DOI por versão**; depósito no Software Heritage com SWHID citado na tese | [LITERATURA: FAIR4RS v1.0, princípios F1, F1.2, A1; GitHub Docs; SWHID] |
| Empacotamento | Pacote separado `olivas-rul` com `pyproject.toml`, `CITATION.cff`, `LICENSE` (Apache-2.0 já existente) e versão semântica | [LITERATURA: FAIR4RS R1.1]; [REPO: `LICENSE.txt`, `CHANGELOG.md`] |
| Determinismo | Sementes fixas em todo Monte Carlo — já é padrão do repositório; ambiente travado por lockfile (hoje há apenas limites inferiores em `requirements.txt`) | [LITERATURA: Sandve et al. 2013, regras 3 e 6]; [REPO: `reliability_monte_carlo.py`, `arc_flash_monte_carlo.py`] |
| Proveniência | Cabeçalho de auditoria com SHA256 dos insumos e versão do software já existe; corrigir *timestamp* para UTC com fuso | [LITERATURA: FAIR4RS R1.2]; [REPO: `app/postprocessor/audit_trail.py`] |
| Dados por trás de cada figura | Publicar as séries que geram cada gráfico do painel | [LITERATURA: Sandve et al. 2013, regra 7] |
| Cartões de dados | Um por banco usado, com citação obrigatória (XJTU-SY exige citar Wang et al. 2020; NASA indica citação por banco) | [LITERATURA: XJTU-SY; NASA PCoE] |
| Publicação de software | Candidatura ao JOSS **somente após** ≥ 6 meses de histórico público, testes e documentação; o *gating* comercial por tier do Olivas cria tensão com o requisito de software "feature-complete", que se evita publicando o módulo de RUL como pacote separado | [LITERATURA: JOSS]; [REPO: `app/commercial/feature_gates.py`]; [INFERÊNCIA] |
| Conformidade com o repositório | Cumprir integralmente o checklist de módulo novo: docstring com norma §seção p. NN; `make_audit_header` como primeiro bloco do laudo; `citation(...)` ao lado de cada valor; entrada em `KNOWN_LIMITATIONS` e em `STANDARDS_CATALOG`; `Feature` + `FEATURE_TIER_MAP`; ação de menu na GUI antes do *release* (7ª garantia); testes com cobertura mínima de 80 % | [REPO: `anexos/repo/convencoes_auditoria_gui_docs.md`, §4.1–4.6] |
| Posicionamento honesto | Chamar o MVP de "modelo de prognóstico baseado em simulação"; reservar "gêmeo digital" para a fase com sincronização de dados do ativo | [LITERATURA: NIST AMS 400-2]; [INFERÊNCIA] |

### 7.5 Sequência recomendada de entrega

1. Classificação de criticidade da população de motores (pré-requisito de §3.4).
2. Extração, do modelo ATP existente, de tensão no nó do motor, contagem de reignições por polo e $T_1$ por reignição — entradas obrigatórias de qualquer acumulador de dano, hoje inexistentes no acervo [FATO: `01_ETAPA1...md`, próximo passo; `00_INDICE.md`].
3. Camada econômica (3.2)–(3.4) com parâmetros de planta editáveis e bloqueio de laudo enquanto $C_h$, $T_{ind}$ e $C_{rep}$ forem os *defaults* rotulados.
4. Painel executivo da §5.1 sobre o motor de estudo, com faixa em vez de valor.
5. Experimento de $f_6$/$g_4$ e verificação de não degenerescência da frente (correlação de postos e PCA) [PROPOSTA: `02_ETAPA2...md`, §6.3].
6. Empacotamento, DOI e cartões de dados (§7.4).

---

## 8. Riscos e limitações

### 8.1 Dado ausente

| Lacuna | Consequência | Encaminhamento |
|---|---|---|
| Custo por evento de falha de motor MT em refinaria/plataforma, com e sem reserva | $E[C]$ não é calculável sem entrada do usuário | [INSERIR CITAÇÃO]; parâmetro obrigatório de planta |
| Custo de rebobinagem/reposição de motor MT e prazo de sobressalente | $C_{rep}$ e $T_{mob}$ hipotéticos | [INSERIR CITAÇÃO] |
| Parâmetros de curva de vida ($n$, $V_{th}$, $a(t_f)$) para mica-epóxi pré-formada de MT | Nenhum RUL pode ser apresentado como resultado; apenas arquitetura com parâmetros livres e incerteza propagada | [INSERIR CITAÇÃO]; herdado de `01_ETAPA1...md`, limitação (b) |
| Número de reignições por manobra, $n_{r,m}$ | Incerteza de primeira ordem no dano por evento; A não o reporta | [FATO por omissão: doc A]; Q9 de `02_ETAPA2...md` |
| Ajuste temporizado da ANSI 27 e taxa anual de contingências N-1 | O elo B → A permanece qualitativo; dano por evento não converte em RUL em tempo | Q2 e Q10 de `02_ETAPA2...md` |
| Indicadores do Documento Nacional ABRAMAN 2024 | Números brasileiros de manutenção são de 2013/2017 via secundária | [INSERIR CITAÇÃO]; acesso restrito a associados |
| Fonte primária das faixas atribuídas à McKinsey | Não usar as faixas "−30 a −50 % de parada, +20 a +40 % de vida" | [INSERIR CITAÇÃO]; HTTP 503 na coleta |
| Prêmio de seguro condicionado a prognóstico de máquinas elétricas | O argumento de seguro é de elegibilidade e evidência, nunca de desconto | [INSERIR CITAÇÃO] |
| Whitepaper GE/Kimberlite 2016 (US$ 38 / 49 / 58 mi divergem entre reproduções) | Usar apenas com a ressalva de divergência | [INSERIR CITAÇÃO] |

### 8.2 Responsabilidade

O módulo emite recomendação, não comando; a decisão permanece com o responsável técnico identificado no cabeçalho de auditoria [REPO: convenção 4.1.2]. Dois riscos específicos: **(i)** um alerta correto ignorado gera responsabilidade documentada — o registro é bidirecional; **(ii)** um falso positivo que motive parada desnecessária tem custo direto, e a literatura de PHM registra que falsos alarmes de sistemas embarcados de teste levam a "substituição desnecessária e custosa, requalificação, atraso de expedição e perda de disponibilidade" [FATO: artigo 07, p. 2]. A mitigação é contratual e documental, não algorítmica: declarar limiares, reportar $P_{FA}$ e $C_{FA}$, e renderizar as limitações em todo laudo.

### 8.3 Regulatório

**(a) Transição da NR-10.** Há dois textos vigentes em janela sobreposta: o atual (AT > 1.000 V CA; prontuário obrigatório acima de 75 kW instalados) e o novo (Portaria MTE nº 737, de 29 mai. 2026, vigência a partir de 1º jun. 2027), que institui a classe **Média Tensão (> 1.000 V)** e redefine AT como > 36.200 V [NORMA: NR-10, texto vigente, 10.2.4 e glossário; NR-10, texto de 2026, Anexo I]. Documentos do módulo devem citar a versão aplicável e evitar o termo "AT" para 2,3–13,8 kV a partir de 2027. **(b) NR-12.** Preditivas de itens de segurança exigem "descrição das técnicas de análise e meios de supervisão centralizados ou de amostragem" [NORMA: NR-12, 12.11.2.2]. **(c) SGSO/ANP.** Para instalações marítimas, as práticas nº 12 (identificação e análise de riscos, com classificação e análise histórica de incidentes) e nº 13 (integridade mecânica: planos de inspeção, teste e manutenção) são o ponto de acoplamento natural das saídas do módulo [NORMA: ANP Res. 43/2007, RT do SGSO, 12.3 e 13.2.1]. **(d)** Nenhuma das normas de gestão de ativos ou de prognóstico citadas teve texto integral lido nesta pesquisa; as citações são de escopo ou de catálogo [NORMA: ISO 55000/55001:2024, EN 15341:2019, ISO 13381-1:2025 — textos não acessados].

### 8.4 Maturidade

| Risco | Evidência | Mitigação |
|---|---|---|
| **Purgatório de piloto** | 33 % dos executivos insatisfeitos relatam que a IA funcionou no piloto e não escalou [LITERATURA: Bain 2025]; a PwC adverte que os ganhos de PdM 4.0 foram "provavelmente obtidos em peças isoladas de equipamento" [PwC 2018, p. 10] | Desenhar desde o início para frota (classificação de criticidade + priorização por risco), não para um motor de demonstração |
| **Ausência de KPI financeiro** | "A maioria das empresas não acompanha KPIs financeiros de suas iniciativas de IA"; só 23 % conseguem vincular IA a receita ou custo [LITERATURA: BCG 2025; Bain 2025] | A camada econômica (3.2)–(3.4) é entregável de primeira classe, não relatório anexo |
| **Falso alarme destruindo o valor** | "Taxas altas de falso alarme podem causar deterioração econômica" [LITERATURA: Hölzel e Gollnick 2015, p. 14]; nenhum survey executivo acessado reporta falso alarme como KPI [INFERÊNCIA] | Reportar $P_{FA}$ e $C_{FA}$ ao lado do RUL; derivar as constantes da pontuação assimétrica do custo de parada, não do desafio PHM08 |
| **Transferência de AHI de T&D para motores** | CIGRE TB 858 e CNAIM fornecem a estrutura, mas curvas, modificadores e pesos são específicos de ativos de rede | [HIPÓTESE] declarada; calibrar antes de publicar bandas |
| **Deriva do modelo** | Não há norma que fixe limiares de deriva; a própria documentação de referência alerta que significância estatística não implica relevância prática [LITERATURA: Evidently AI] | Monitorar deriva dos **insumos** (distribuição de sobretensões e de partidas por período) com KS/PSI e registrar "estado de dados" no painel |
| **Sobrevida atribuída a fonte errada** | O levantamento EPRI de 1982 é de auxiliares de usinas, com tecnologia de isolamento da época; a subpesquisa de 122 motores manobrados a vácuo não atribuiu nenhuma das 7 falhas ao dispositivo a vácuo [LITERATURA: EPRI EL-2678, p. S-7] | Usar o EPRI como **prior editável**, jamais como evidência de causalidade entre VCB e falha; a amostra é pequena, de 1982, e não mede degradação acumulada [INFERÊNCIA] |

---

## 9. Referências

**Documentos primários (revisão duplo-cega; autoria não divulgada — [INSERIR CITAÇÃO] até publicação)**

AUTORES OMITIDOS. *Selective mitigation of vacuum circuit breaker switching overvoltages in medium voltage induction motors using an active thyristor snubber*. Submissão ao SEPOC 2026, 5 p. — **Documento A**.

AUTORES OMITIDOS. *Selective load shedding for the switching of large motors under N-1 contingency: constrained multiobjective optimization with NSGA-II, NSGA-III and regression surrogates*. Submissão ao SEPOC 2026, 6 p. — **Documento B**.

**Documentos internos do estudo**

ETAPA 1. *Aprofundamento no monitoramento de degradação de isolamentos de estator*. `docs/research/rul_isolamento/01_ETAPA1_monitoramento_degradacao_isolamento.md`, 873 l.

ETAPA 2. *Cruzamento de domínios: mitigação seletiva de sobretensões de manobra e load shedding seletivo sob contingência N-1*. `docs/research/rul_isolamento/02_ETAPA2_cruzamento_A_x_B.md`, 960 l.

ÍNDICE. *Monitoramento de degradação de isolamento e RUL de motores de indução MT — índice e nota metodológica*. `docs/research/rul_isolamento/00_INDICE.md`, 376 l.

**Normas e regulamentos**

AGÊNCIA NACIONAL DO PETRÓLEO, GÁS NATURAL E BIOCOMBUSTÍVEIS. *Regulamento Técnico do Sistema de Gerenciamento da Segurança Operacional das Instalações Marítimas de Perfuração e Produção de Petróleo e Gás Natural* (anexo à Resolução ANP nº 43/2007). Rio de Janeiro: ANP, 2007. Disponível em: https://www.gov.br/anp/pt-br/assuntos/exploracao-e-producao-de-oleo-e-gas/seguranca-operacional/arq/regulamento_sgso.pdf. Acesso em: 2 set. 2026.

AGÊNCIA NACIONAL DO PETRÓLEO, GÁS NATURAL E BIOCOMBUSTÍVEIS. Superintendência de Segurança Operacional. *Relatório Anual de Segurança Operacional das Atividades de Exploração e Produção de Petróleo e Gás Natural 2024*. Rio de Janeiro: ANP, 2025. Disponível em: https://www.gov.br/anp/pt-br/assuntos/exploracao-e-producao-de-oleo-e-gas/seguranca-operacional/arq/raso/2024-relatorio-anual-seguranca-operacioanl.pdf. Acesso em: 2 set. 2026.

BRASIL. Ministério do Trabalho e Emprego. *NR-10 — Segurança em Instalações e Serviços em Eletricidade* (texto da Portaria MTE nº 598/2004, alterado pelas Portarias MTPS nº 508/2016 e SEPRT nº 915/2019). Disponível em: https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/arquivos/normas-regulamentadoras/nr-10-atualizada-2019-1.pdf. Acesso em: 2 set. 2026.

BRASIL. Ministério do Trabalho e Emprego. *NR-10 — Segurança em Instalações Elétricas e Serviços em Eletricidade* (Portaria MTE nº 737, de 29 mai. 2026; vigência a partir de 1º jun. 2027). Disponível em: https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/arquivos/normas-regulamentadoras/nr-10.pdf. Acesso em: 2 set. 2026.

BRASIL. Ministério do Trabalho e Emprego. *NR-12 — Segurança no Trabalho em Máquinas e Equipamentos* (consolidação 2025). Disponível em: https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/normas-regulamentadora/normas-regulamentadoras-vigentes/nr-12-atualizada-2025.pdf. Acesso em: 2 set. 2026.

BSI. *BS EN 15341:2019 — Maintenance. Maintenance key performance indicators*. 2019. Disponível em: https://knowledge.bsigroup.com/products/maintenance-maintenance-key-performance-indicators. Acesso em: 2 set. 2026. [Texto integral não lido.]

CIGRE. *Terms of Reference WG C4.76 — Overvoltage protection in switching inductive devices with vacuum circuit breaker*. 31 jul. 2023. Disponível em: https://www.cigre.org/userfiles/files/News/2023/TOR-WG%20C4_76_Overvoltage%20protection%20in%20switching%20inductive%20devices%20with%20vacuum%20circuit%20breaker-rev1.pdf. Acesso em: 2 set. 2026.

INTERNATIONAL ELECTROTECHNICAL COMMISSION. *IEC 60034-15:2009 — Impulse voltage withstand levels of form-wound stator coils*. 3. ed. Genebra: IEC, 2009. Amostra: https://cdn.standards.iteh.ai/samples/15848/1b914cc7cb9b4c4582e502f946666007/IEC-60034-15-2009.pdf. Acesso em: 2 set. 2026.

INTERNATIONAL ELECTROTECHNICAL COMMISSION. *IEC 60034-27-2:2023*; *IEC 60034-27-3:2015*; *IEC 60034-27-4:2018* — Condition monitoring of rotating electrical machines. Genebra: IEC. (Introduções consultadas.)

INTERNATIONAL ELECTROTECHNICAL COMMISSION. *IEC 60071-1:2019 — Insulation co-ordination — Part 1: Definitions, principles and rules*. 9. ed. Genebra: IEC, 2019. Amostra: https://cdn.standards.iteh.ai/samples/100144/6c649e0574b44164805acdb3a39941f0/IEC-60071-1-2019.pdf. Acesso em: 2 set. 2026. (3.31 — fator de segurança $K_s$; 3.34 — tensão suportável nominal.)

INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. *ISO 13374-1:2003*; *ISO 13374-2:2007* — Condition monitoring and diagnostics of machines — Data processing, communication and presentation. Escopos via catálogo EVS: https://www.evs.ee/en/iso-13374-1-2003; https://www.evs.ee/en/iso-13374-2-2007. Acesso em: 2 set. 2026. [Textos integrais não lidos.]

INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. *ISO 13381-1:2025 — Condition monitoring and diagnostics of machine systems — Prognostics — Part 1: General guidelines and requirements* (substitui a ed. 2015, retirada em 02.09.2025). Catálogo EVS: https://www.evs.ee/en/iso-13381-1-2025. Acesso em: 2 set. 2026. [Texto integral não lido; a edição 2015 foi consultada em amostra, cláusulas 3.3, 3.9 e 3.10.]

INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. *ISO 55000:2024 — Asset management — Vocabulary, overview and principles*. Catálogo EVS: https://www.evs.ee/en/iso-55000-2024. Acesso em: 2 set. 2026. [Texto integral não lido.]

INSTITUTE OF ELECTRICAL AND ELECTRONICS ENGINEERS. *IEEE Std 522-2023 — Guide for testing turn insulation of form-wound stator coils for alternating-current electric machines*. Nova York: IEEE, 2023. (Escopo consultado; Figura 1 não acessada — INSERIR CITAÇÃO.)

**Levantamentos de mercado, relatórios e imprensa**

ABB. *ABB survey reveals unplanned downtime costs $125,000 per hour* (reproduzido por Reliabilityweb). 2023. Disponível em: https://reliabilityweb.com/en/press-release/abb-survey-reveals-unplanned-downtime-costs-125000-per-hour. Acesso em: 2 set. 2026.

AGÊNCIA PETROBRAS. *Petrobras investe R$ 500 milhões na parada programada de manutenção da Refinaria Presidente Bernardes de Cubatão (RPBC)*. 28 jun. 2024. Disponível em: https://agencia.petrobras.com.br/w/negocio/petrobras-investe-r-500-milhoes-na-parada-programada-de-manutencao-da-refinaria-presidente-bernardes-de-cubatao-rpbc-. Acesso em: 2 set. 2026.

BAIN & COMPANY. *Executive survey: AI moves from pilots to production*. 24 nov. 2025. Disponível em: https://www.bain.com/insights/executive-survey-ai-moves-from-pilots-to-production/. Acesso em: 2 set. 2026.

BCG. *From potential to profit: closing the AI impact gap* (AI Radar 2025). 15 jan. 2025. Disponível em: https://www.bcg.com/publications/2025/closing-the-ai-impact-gap. Acesso em: 2 set. 2026.

CNI — CONFEDERAÇÃO NACIONAL DA INDÚSTRIA. *A difusão das tecnologias da Indústria 4.0 em empresas brasileiras*. Brasília: CNI, 2020. Disponível em: https://static.portaldaindustria.com.br/media/filer_public/c4/26/c42635b7-c3c0-4763-8ed2-69aa33b8a07e/a_difusao_das_tecnologias_da_industria_40_vf.pdf. Acesso em: 2 set. 2026.

CNI — CONFEDERAÇÃO NACIONAL DA INDÚSTRIA. *Indústria 4.0: 69 % das indústrias brasileiras fazem uso de tecnologia digital*. Agência de Notícias da Indústria, 26 abr. 2022. Disponível em: https://noticias.portaldaindustria.com.br/noticias/inovacao-e-tecnologia/industria-40-69-das-industrias-brasileiras-fazem-uso-de-tecnologia-digital-no-brasil/. Acesso em: 2 set. 2026.

DELOITTE INSIGHTS. *Industry 4.0 and predictive technologies for asset maintenance*. 9 maio 2017. Disponível em: https://www.deloitte.com/us/en/insights/industry/manufacturing-industrial-products/industry-4-0/using-predictive-technologies-for-asset-maintenance.html. Acesso em: 2 set. 2026.

DELOITTE INSIGHTS. *How the right mix of C-suite leadership can drive outsized AI returns*. 18 dez. 2025. Disponível em: https://www.deloitte.com/us/en/insights/topics/digital-transformation/c-suite-leadership-ai-returns.html. Acesso em: 2 set. 2026.

EIA — U.S. ENERGY INFORMATION ADMINISTRATION. *Midwest refinery outage is affecting petroleum product markets*. Today in Energy, 13 fev. 2024. Disponível em: https://www.eia.gov/todayinenergy/detail.php?id=61403. Acesso em: 2 set. 2026.

HONEYWELL. *Industrial AI uptake is just getting started but majority of sector is uncovering new use cases*. 23 jul. 2024. Disponível em: https://www.honeywell.com/us/en/news/press-releases/2024/07/industrial-ai-uptake-is-just-getting-started-but-majority-of-sector-is-uncovering-new-use-cases-finds-honeywell-research. Acesso em: 2 set. 2026.

HSB. *HSB IoT clients gain 500 percent return on investment*. 29 mar. 2022. Disponível em: https://www.munichre.com/hsb/en/press-and-publications/press-releases/2022/2022-03-29-hsb-iot-clients-gain-500-percent-roi.html. Acesso em: 2 set. 2026.

IIoT WORLD. *Industrial AI Readiness Report 2026: data comes first*. 27 jan. 2026. Disponível em: https://www.iiot-world.com/industrial-iot/connected-industry/industrial-ai-readiness-report-2026/. Acesso em: 2 set. 2026.

INVESTING.COM; REUTERS. *Refinaria da Petrobras Reduc opera normalmente após parada não programada*. 13 set. 2016. Disponível em: https://br.investing.com/news/stock-market-news/refinaria-da-petrobras-reduc-opera-normalmente-apos-parada-nao-programada-202801. Acesso em: 2 set. 2026.

IT BRIEF AUSTRALIA. *FM warns of rising risks to power generation assets*. 21 jul. 2026. Disponível em: https://itbrief.com.au/story/fm-warns-of-rising-risks-to-power-generation-assets. Acesso em: 2 set. 2026.

MAINTAINX. *2025 State of Industrial Maintenance*. 2025. Disponível em: https://www.getmaintainx.com/newsroom/state-of-industrial-maintenance-report-2025. Acesso em: 2 set. 2026.

MAXGRIP. *The cost of unplanned downtime*. 31 ago. 2026. Disponível em: https://www.maxgrip.com/resource/article-the-cost-of-unplanned-downtime/. Acesso em: 2 set. 2026.

MUNICH RE. *IoT Cover — gaining trust and building confidence*. s.d. Disponível em: https://www.munichre.com/en/solutions/for-industry-clients/iot-cover.html. Acesso em: 2 set. 2026.

PETROBRAS. *Plano de Negócios 2026-2030* (Plano Estratégico 2050). Rio de Janeiro: Petrobras, 27 nov. 2025. Disponível em: https://petrobras.com.br/documents/2677942/12513210/PN+2026-30_27nov_final_port.pdf. Acesso em: 2 set. 2026.

PwC; MAINNOVATION. *Predictive Maintenance 4.0: beyond the hype — PdM 4.0 delivers results*. set. 2018. Disponível em: https://www.mainnovation.com/wp-content/uploads/tmp/6397245268d8d3711c88cda0b4585ab02e612f2e.pdf. Acesso em: 2 set. 2026.

RAVAGNANI, A. *Refinarias brasileiras operam acima da capacidade e custo de paradas supera R$ 100 milhões por dia*. Times Brasil/CNBC, 14 ago. 2026. Disponível em: https://timesbrasil.com.br/empresas-e-negocios/combustiveis/refinarias-acima-da-capacidade-custo-paradas-manutencao/. Acesso em: 2 set. 2026.

RELIAMAG. *Industrial downtime cost benchmarks: what published studies actually show*. 2026. Disponível em: https://reliamag.com/guides/industrial-downtime-cost-benchmarks/. Acesso em: 2 set. 2026.

ROCKWELL AUTOMATION. *Ninety-five percent of manufacturers are investing in AI* (10th State of Smart Manufacturing Report). 3 jun. 2025. Disponível em: https://www.rockwellautomation.com/en-us/company/news/press-releases/Ninety-Five-Percent-of-Manufacturers-Are-Investing-in-AI-to-Navigate-Uncertainty-and-Accelerate-Smart-Manufacturing.html. Acesso em: 2 set. 2026.

SIEMENS; SENSEYE. *The True Cost of Downtime 2022*. Erlangen: Siemens AG, 2023. Disponível em: https://assets.new.siemens.com/siemens/assets/api/uuid:3d606495-dbe0-43e4-80b1-d04e27ada920/dics-b10153-00-7600truecostofdowntime2022-144.pdf. Acesso em: 2 set. 2026.

SIEMENS; SENSEYE. *The True Cost of Downtime 2024*. Erlangen: Siemens AG, 2024. Disponível em: https://assets.new.siemens.com/siemens/assets/api/uuid:1b43afb5-2d07-47f7-9eb7-893fe7d0bc59/TCOD-2024_original.pdf. Acesso em: 2 set. 2026.

THE MANUFACTURER. *Unplanned downtime affecting 82 % of businesses*. 2017. Disponível em: https://www.themanufacturer.com/articles/unplanned-downtime-affecting-82-businesses/. Acesso em: 2 set. 2026.

TRACTIAN. *The CFO's guide to funding a predictive maintenance program*. 19 ago. 2026. Disponível em: https://tractian.com/en/blog/the-cfos-guide-to-funding-a-predictive-maintenance-program. Acesso em: 2 set. 2026.

**Literatura técnica e acadêmica**

AHANGAR, M. N.; FARHAT, Z. A.; SIVANATHAN, A. AI trustworthiness in manufacturing: challenges, toolkits, and the path to Industry 5.0. *Sensors*, v. 25, n. 14, art. 4357, 2025. DOI 10.3390/s25144357. Disponível em: https://pmc.ncbi.nlm.nih.gov/articles/PMC12298069/. Acesso em: 2 set. 2026.

ANGELOPOULOS, A. N.; BATES, S. A gentle introduction to conformal prediction and distribution-free uncertainty quantification. *arXiv*:2107.07511, 2021. Disponível em: https://arxiv.org/abs/2107.07511. Acesso em: 2 set. 2026.

CHAOUB, A. et al. Learning representations with end-to-end models for improved remaining useful life prognostic. *arXiv*:2104.05049, 2021. Disponível em: https://arxiv.org/abs/2104.05049. Acesso em: 2 set. 2026. (Fonte secundária para a função de pontuação do desafio PHM08.)

CHOO, Y.; SHIN, S.-J. Integrating machine learning-based remaining useful life predictions with cost-optimal block replacement for industrial maintenance. *International Journal of Prognostics and Health Management*, v. 16, n. 1, 2025. DOI 10.36001/ijphm.2025.v16i1.4242.

COX, L. A. What's wrong with risk matrices? *Risk Analysis*, v. 28, n. 2, 2008. DOI 10.1111/j.1539-6924.2008.01030.x. [Citado via revisão terciária; texto não lido.]

CUMMINS, L. et al. Explainable predictive maintenance: a survey of current methods, challenges and opportunities. *arXiv*:2401.07871, 2024. Disponível em: https://arxiv.org/abs/2401.07871. Acesso em: 2 set. 2026.

FAVARÃO DA SILVA, R. *Estrutura de gerenciamento de manutenção para a gestão de ativos físicos*. Tese (Doutorado) — Escola Politécnica, Universidade de São Paulo, 2022. DOI 10.11606/t.3.2022.tde-12082022-101810. Disponível em: http://www.teses.usp.br/teses/disponiveis/3/3151/tde-12082022-101810/publico/RenanFavaraodaSilvaCorr22.pdf. Acesso em: 2 set. 2026.

FELDMAN, K.; JAZOULI, T.; SANDBORN, P. A methodology for determining the return on investment associated with prognostics and health management. *IEEE Transactions on Reliability*, v. 58, n. 2, p. 305–316, 2009. DOI 10.1109/TR.2009.2020133.

GAL, Y.; GHAHRAMANI, Z. Dropout as a Bayesian approximation. *arXiv*:1506.02142, 2016 (ICML).

GENERAL ELECTRIC COMPANY; CORNELL, E. P.; OWEN, E. L.; APPIARIUS, J. C.; McCOY, R. M.; ALBRECHT, P. F.; HOUGHTALING, D. W. *Improved Motors for Utility Applications, Volume 1*. EPRI EL-2678, RP 1763-1, Final Report. Palo Alto: EPRI, out. 1982. Disponível em: https://www.osti.gov/servlets/purl/6759687. Acesso em: 2 set. 2026.

HÖLZEL, N. B.; GOLLNICK, V. Cost-benefit analysis of prognostics and condition-based maintenance concepts for commercial aircraft considering prognostic errors. In: ANNUAL CONFERENCE OF THE PHM SOCIETY, 2015. Disponível em: https://elib.dlr.de/100435/1/phmc_15_050.pdf. Acesso em: 2 set. 2026.

JENSEN, W. R.; STRANGAS, E. G.; FOSTER, S. N. A method for online stator insulation prognosis for inverter-driven machines. *IEEE Transactions on Industry Applications*, v. 54, n. 6, p. 5897–5906, 2018. DOI 10.1109/TIA.2018.2854408.

KÄSLIN, B. et al. Integrating prognostics, maintenance, and tail assignment under remaining useful life uncertainty. *arXiv*:2608.22569, 2026. Disponível em: https://arxiv.org/abs/2608.22569. Acesso em: 2 set. 2026.

KHOSRAVI, A.; NAHAVANDI, S.; CREIGHTON, D.; ATIYA, A. F. Comprehensive review of neural network-based prediction intervals and new advances. *IEEE Transactions on Neural Networks*, v. 22, n. 9, p. 1341–1356, 2011. DOI 10.1109/TNN.2011.2162110. [Metadados; texto integral não acessado.]

LAKSHMINARAYANAN, B.; PRITZEL, A.; BLUNDELL, C. Simple and scalable predictive uncertainty estimation using deep ensembles. *arXiv*:1612.01474, 2017 (NIPS).

MOIR, K.; NICULITA, O.; MILLIGAN, W. Prognostics and health management in the oil & gas industry — a step change. In: EUROPEAN CONFERENCE OF THE PHM SOCIETY, 2018. Disponível em: http://www.papers.phmsociety.org/index.php/phme/article/download/396/phmec_18_396. Acesso em: 2 set. 2026.

NIELSEN, J. S. Value of information of structural health monitoring with temporally dependent observations. *Structural Health Monitoring*, 2021. DOI 10.1177/14759217211030605.

NIST. *Digital Twin Framework for Manufacturing* (AMS 400-2). Gaithersburg: NIST, 2021. Disponível em: https://nvlpubs.nist.gov/nistpubs/ams/NIST.AMS.400-2.pdf. Acesso em: 2 set. 2026.

NIVELO, J. J. O. et al. Evaluating voltage drop snapshot and time motor starting study methodologies — an offshore platform case study. In: IPST 2021, Belo Horizonte, paper 21IPST112. Disponível em: https://www.ipstconf.org/papers/Proc_IPST2021/21IPST112.pdf. Acesso em: 3 set. 2026.

NOR, A. K. M.; PEDAPATI, S. R.; MUHAMMAD, M.; LEIVA, V. Overview of explainable artificial intelligence for prognostic and health management of industrial assets based on PRISMA. *Sensors*, v. 21, n. 23, art. 8020, 2021. DOI 10.3390/s21238020. [Metadados e resumo.]

SANDBORN, P.; WILKINSON, C. A maintenance planning and business case development model for the application of PHM to electronic systems. *Microelectronics Reliability*, v. 47, n. 12, p. 1889–1901, 2007. DOI 10.1016/j.microrel.2007.02.016.

SANKARARAMAN, S.; GOEBEL, K. Uncertainty in prognostics and systems health management. *International Journal of Prognostics and Health Management*, v. 6, n. 4, 2015. DOI 10.36001/ijphm.2015.v6i4.2319.

SANDVE, G. K. et al. Ten simple rules for reproducible computational research. *PLoS Computational Biology*, 2013.

SAXENA, A.; CELAYA, J.; SAHA, B.; SAHA, S.; GOEBEL, K. Metrics for offline evaluation of prognostic performance. *International Journal of Prognostics and Health Management*, v. 1, n. 1, 2010. DOI 10.36001/ijphm.2010.v1i1.1336. Disponível em: https://papers.phmsociety.org/index.php/ijphm/article/download/1336/324. Acesso em: 2 set. 2026.

STRANGAS, E. G.; AVIYENTE, S.; NEELY, J. D.; ZAIDI, S. S. H. The effect of failure prognosis and mitigation on the reliability of permanent-magnet AC motor drives. *IEEE Transactions on Industrial Electronics*, v. 60, n. 8, p. 3519–3528, 2013. DOI 10.1109/TIE.2012.2227913.

U.S. DEPARTMENT OF ENERGY. Office of Energy Efficiency and Renewable Energy. *United States Industrial Electric Motor Systems Market Opportunities Assessment*. Washington: DOE, dez. 1998 (reimpr. dez. 2002). Disponível em: https://www.energy.gov/sites/prod/files/2014/04/f15/mtrmkt.pdf. Acesso em: 2 set. 2026.

VICHARE, N. M.; PECHT, M. G. Prognostics and health management of electronics. *IEEE Transactions on Components and Packaging Technologies*, v. 29, n. 1, p. 222–229, 2006. (DOI completo — [INSERIR CITAÇÃO].)

**Recursos de reprodutibilidade e dados**

CHUE HONG, N. P. et al. *FAIR Principles for Research Software (FAIR4RS Principles)*, v1.0. RDA/FORCE11/ReSA, 2022. DOI 10.15497/RDA00068. Disponível em: https://zenodo.org/records/6623556. Acesso em: 2 set. 2026.

MIMOSA. *OSA-CBM*. Disponível em: https://www.mimosa.org/mimosa-osa-cbm/. Acesso em: 2 set. 2026.

NASA. *Prognostics Center of Excellence Data Set Repository*. Disponível em: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/. Acesso em: 2 set. 2026.

NASA. *ProgPy — Prognostics Python Packages*, v1.8. 2025. DOI 10.5281/zenodo.8097013. Disponível em: https://nasa.github.io/progpy/. Acesso em: 2 set. 2026.

**Referências citadas por fontes acessadas, mas não acessadas diretamente — não usar como fonte primária**

McKinsey & Company (2014; 2018) [INSERIR CITAÇÃO]; GE Oil & Gas/Kimberlite, *The impact of digital on unplanned downtime* (2016) [INSERIR CITAÇÃO]; Aberdeen, *The rising cost of downtime* (2016) [INSERIR CITAÇÃO]; ARC Advisory Group (2006) [INSERIR CITAÇÃO]; ABRAMAN, *Documento Nacional 2024* (restrito a associados) [INSERIR CITAÇÃO]; CIGRE TB 858 (2021), corpo do texto [INSERIR CITAÇÃO]; Ofgem CNAIM v2.1 (2021), tabelas [INSERIR CITAÇÃO]; texto integral de ISO 55001:2024, EN 15341:2019 e ISO 13381-1:2025 [NORMA: textos não lidos]; custo por evento de falha de motor MT e custo de rebobinagem/reposição de motor MT [INSERIR CITAÇÃO]; prêmio de seguro condicionado a prognóstico de máquinas elétricas [INSERIR CITAÇÃO].
