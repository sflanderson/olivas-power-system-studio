# Proposta de Trabalho de Conclusão de Curso

## Modelo aberto de conversor HVDC-VSC (MMC meia-ponte) para ATP-EMTP: benchmark reprodutível do bipolo ±600 kV Angicos–Itaporanga 2 e integração ao Olivas Power System Studio

| | |
|---|---|
| **Documento** | Proposta de tema de TCC + parecer de viabilidade de produto |
| **Documento-base** | EPE-DEE-RE-071/2025-rev0 — *Estudo de Expansão das Interligações Regionais, Parte III* (nov/2025, 509 p.) |
| **Empresa parceira** | Olivas — produto Olivas Power System Studio (Olivas EPS) |
| **Período previsto** | set/2026 – jun/2027 (TCC 1 + TCC 2) |
| **Data** | 27 de agosto de 2026 |

---

## 1. Sumário executivo

O relatório R1 da EPE recomenda o **bipolo Nordeste II**: HVDC-VSC, ±600 kV, 3.000 MW, ~2.500 km de
linha aérea entre Angicos (RN) e Itaporanga 2 (SP), operação em 2033, dentro de um pacote de
**R$ 26,5 bilhões**, dos quais **R$ 17,1 bilhões (65%) em instalações de corrente contínua**. Será o
primeiro elo VSC do SIN — os seis bipolos em operação e o sétimo em implantação são todos LCC.

No mesmo documento, a EPE registra por escrito a lacuna que dá origem a este TCC (p. 21, §1.5.5):

> "A ausência de modelos oficiais validados para conversores VSC constituiu um desafio relevante à
> realização das análises dinâmicas deste estudo. Tal fato dificultou, inclusive, o desenvolvimento de
> **modelos genéricos**⁸, em virtude da **ausência de um benchmark** a ser utilizado como referência para
> comparação de resultados."
>
> ⁸ *"Modelo concebido com os elementos contidos nas concepções atualizadas de VSC dos principais
> fabricantes, de forma a não privilegiar concepções específicas."*

A nota de rodapé 8 é, literalmente, a especificação do produto proposto aqui.

**Tema recomendado.** Desenvolver, validar e publicar sob licença permissiva um modelo genérico de
estação conversora HVDC-VSC com submódulos 100% meia-ponte, executável em **ATP-EMTP**, acompanhado
de um **benchmark aberto e reprodutível** do bipolo Nordeste II, e integrá-lo ao Olivas EPS como
componente de catálogo, emissor de cartões, estudo automatizado e laudo auditável.

**Resposta curta aos dois pontos levantados:**

1. **Modelo público integrável ao Olivas EPS — sim, com três ressalvas.** O termo correto é *aberto sob
   licença permissiva* (Apache-2.0 + CC-BY-4.0), não "domínio público" — a Lei 9.610/98 não admite
   renúncia a direitos morais e instrumentos tipo CC0 são de tradição estrangeira. O entregável é um
   **par**: um artefato que roda em ATP puro (independente do produto) e uma camada de integração no
   Olivas EPS. E o gargalo real **não é o MMC**: é o *wiring* automático MODELS↔rede, que hoje **não
   existe** no produto (§7.3) — ele é a primeira tarefa técnica e o gate de viabilidade.
2. **Viabilidade de mercado — sim, mas por um caminho diferente do imaginado.** A premissa "só o PSCAD
   tem modelo VSC" é **falsa** como afirmação geral (EMTP-RV, PowerFactory, Simulink/Simscape, PLECS,
   RTDS, OPAL-RT e Typhoon HIL têm MMC nativo) e **verdadeira** em três recortes, dos quais um é
   decisivo e foi verificado na fonte primária: **o ONS obriga a entrega de modelo detalhado do elo CC
   em ATP, mesmo quando o estudo foi feito em PSCAD**, e determina que os estudos de manobra do pátio
   CA das conversoras sejam feitos **na ferramenta ATP** (Submódulo 2.5, §7.15.1.10 e §7.15.3.4). Existe
   obrigação regulatória de produzir modelo HVDC em ATP e não existe modelo VSC público em ATP. Esse é
   o vão. O dimensionamento honesto do mercado está em §8.

---

## 2. Contexto: o que a EPE decidiu

### 2.1 A solução de referência

| Item | Valor | Pág. |
|---|---|---|
| Denominação | Bipolo Nordeste II — LT 600 kV CC Angicos (RN) – Itaporanga 2 (SP) | 25 |
| Tecnologia | HVDC-VSC, MMC **100% Half-Bridge** | 20, 251 |
| Tensão / potência | ±600 kV, 3.000 MW (inversora 2.880 MW; reversa 2.800 MW) | 84, 251-252 |
| Extensão | ~2.500 km em linha aérea | 25, 252 |
| Condutor | 6 × CAA 2167 MCM (Kiwi) por polo; 17 m entre polos; 14 m ao solo; faixa 55 m | 250, 252 |
| Resistência do polo | 0,00425 Ω/km @20 °C; 0,00476 Ω/km @50 °C | 252 |
| Corrente / perdas na LT | 2,5 kA (direta), 2,34 kA (reversa); 132,7 MW | 252 |
| Controle simulado | **Grid-Following**; requisito de **Grid-Forming** na especificação | 118, 42 |
| Suporte reativo | ±30% da potência nominal | 118, 42 |
| Modos | bipolar; monopolar com retorno por eletrodo; monopolar com retorno metálico | 42 |
| SCR de projeto | operação exigida entre **1,5 e 6,5** | 43 |
| SCR calculado | Angicos 4,08–6,07 (**1,92** na N-2 Açu III–Angicos C1+C2); Itaporanga 2 5,47–5,64 | 263-265 |
| SCR do modelo EMT | equivalente de Thévenin com SCR = 2,5 | 205 |
| Investimento | R$ 26,5 bi (R$ 17,1 bi em CC: R$ 9,7 bi LT + R$ 3,7 bi por conversora) | 23 |
| Entrada em operação | 2033 | 25 |

Requisitos funcionais inéditos para o SIN (§3.4[8], p. 42-43): modo **STATCOM**, injeção de corrente
reativa sob defeito, **grid-forming**, **black-start bidirecional**, potência reversa, operação a 85%
da tensão nominal e sobrecarga de 400 MW pela capacidade inerente dos submódulos.

### 2.2 Requisitos de desempenho que ainda não existem em norma

O item §3.4[9] (p. 43) exige reenergização do bipolo em **≤ 2,5 s** após a detecção da falta CC e
recuperação de 90% da potência em **≤ 5 s**, e reconhece:

> "será necessária a flexibilização dos tempos atualmente previstos em procedimentos de rede para elos
> de corrente contínua (que abarcam apenas a tecnologia LCC) — que são da ordem de 350 ms — ou a criação
> de procedimentos específicos para instalações VSC."

Um requisito normativo novo terá de ser escrito, e sua verificação é, por natureza, uma simulação EMT.

---

## 3. O problema

### 3.1 O encadeamento de contorno adotado pela EPE

| Etapa | Representação usada | Limitação declarada |
|---|---|---|
| Fluxo de potência | Barras PV com limites de reativo ~30% da Pn | Simplificação (p. 118-119) |
| Estabilidade (RMS) | **Carga ZIP: 60% P constante + 40% I constante** no ANATEM® | "não se mostrou suficiente para a realização de análises elétricas conclusivas nem para a recomendação de reforços sistêmicos" (p. 119) |
| Estabilidade (RMS), 2ª geração | Modelo de fasores dinâmicos do MMC **contratado ao CEPEL**, calibrado contra o benchmark do PSCAD | "ainda não estivesse totalmente apto" a faltas CC (p. 119) |
| **Transitórios (EMT)** | **PSCAD/EMTDC**, a partir do benchmark *VSC-MMC Half Bridge* (320 kV / 1.200 MW) da Knowledge Base, reescalado para 600 kV / 3.000 MW com apoio dos fabricantes | Rede CA representada apenas por equivalentes de Thévenin (p. 206) |

E o desfecho, na conclusão do capítulo 12 (p. 203 e 206):

> "Atualmente, o modelo desenvolvido em ANATEM® para representação do bipolo não representa de forma
> adequada este tipo de dinâmica, portanto não foi possível avaliar este fenômeno nas análises de
> estabilidade eletromecânica."

> "Os ajustes realizados no modelo EMT [...] deverão servir de subsídio para o aprimoramento do modelo
> em desenvolvimento no ANATEM®, pelo CEPEL, de forma que este também possa representar adequadamente
> os fenômenos associados a faltas na linha CC, **atualmente não contemplados**."

Vale registrar que o primeiro escalonamento do benchmark **falhou**: o modelo "mostrou desempenho
insuficiente para resposta a faltas na linha CC, apresentando sobretensões inadequadas e irrealistas"
(p. 199), e só se tornou funcional após a inserção de para-raios CC, lógica de NBS e uma sequência
coordenada de eventos. Essa é a parte difícil do problema, e ela está documentada.

### 3.2 Enunciado

O país vai construir o maior elo HVDC-VSC em linha aérea já contratado e, hoje:

- **não existe modelo VSC-MMC aberto, auditável e neutro em relação a fabricante** para EMT no Brasil;
- **não existe benchmark público** que permita a um terceiro reproduzir ou contestar os resultados
  publicados — o usado pela EPE está dentro de um software proprietário;
- os modelos "realistas" recomendados são, por construção, **caixas-pretas de fabricante**, com restrição
  de compartilhamento "por questão de confidencialidade e proteção ao segredo industrial" (p. 22, nota 10);
- o avanço do CEPEL é no flanco **RMS/fasorial** (ANATEM), não no flanco EMT.

### 3.3 Pergunta de pesquisa

> É possível construir um modelo genérico de conversor HVDC-VSC (MMC meia-ponte), **implementado em
> ATP-EMTP e acoplado à rede por fonte controlada por MODELS**, publicado sob licença permissiva e
> integrado ao Olivas EPS, capaz de (i) reproduzir um modelo chaveado detalhado construído no próprio
> ATP com NRMSE ≤ 2%; (ii) reproduzir o balanço de regime permanente publicado pela EPE com erro ≤ 1%;
> e (iii) reproduzir, **em envelope paramétrico**, os marcos transitórios de falta polo-terra na LT CC
> do Capítulo 12 — tudo sem qualquer dado confidencial de fabricante e com rastreabilidade auditável?

---

## 4. Objetivos

### 4.1 Objetivo geral

Desenvolver, validar quantitativamente e publicar sob licença permissiva um modelo eletromagnético
transitório genérico de estação conversora HVDC-VSC com submódulos 100% meia-ponte — braço com estados
de capacitor observáveis, bloqueio por diodos de braço, controle *grid-following* e sequência de
proteção e religamento de falta CC — executável em ATP-EMTP e integrado ao Olivas EPS, acompanhado de
um benchmark aberto e reprodutível do bipolo ±600 kV / 3.000 MW / 2.500 km Angicos–Itaporanga 2.

### 4.2 Objetivos específicos (partição MoSCoW)

**MUST — núcleo mínimo defensável**

1. **OE1** Consolidar em arquivo versionado (`data/hvdc_ne2_params.yaml`), com **campo de fonte e faixa
   de incerteza por parâmetro**, todas as premissas públicas do bipolo, registrando as divergências
   internas reais do relatório.
2. **OE2** Executar, como **primeira tarefa técnica e com decisão GO/NO-GO formal**, a prova de conceito
   do acoplamento MODELS→rede no ATP e implementar `app/preprocessor/models_wiring.py`.
3. **OE3** Formular e verificar o braço MMC meia-ponte com estados de capacitor por submódulo, com
   oráculo numérico independente em Python/NumPy.
4. **OE4** Implementar o estado bloqueado (condução pelos diodos de braço) — o mecanismo em que o
   modelo escalado da EPE falhou.
5. **OE5** Derivar os parâmetros internos não publicados a partir de regras de projeto de literatura
   aberta, com **faixa declarada** (V_SM, número de submódulos, constante de energia, indutância de
   braço, impedância do transformador conversor).
6. **OE6** Gerar a LT CC de 2.500 km por **JMarti**, usando o caso de dados LINE CONSTANTS do próprio ATP.
7. **OE7** Implementar em MODELS o controle *grid-following* (SRF-PLL, laços dq, limitador com base
   declarada, *capability* P-Q, operação a 85%, modo STATCOM).
8. **OE8** Implementar a sequência de proteção e religamento com **todas as temporizações parametrizadas**.
9. **OE9** Publicar repositório aberto com DOI e manifesto SHA256.

**SHOULD** — estudo de agregação N→N_eq com fronteira de Pareto exatidão × CPU; varredura de
sensibilidade das temporizações de proteção; decomposição do erro de representação do conversor
(MMC completo × aproximação ZIP 60/40 que a EPE foi obrigada a adotar).

**COULD** — integração aditiva ao Olivas EPS (§7), métricas de conversor e codificação executável dos
requisitos EPE.

---

## 5. Escopo

### 5.1 Incluído

- MMC 100% meia-ponte; braço acoplado à rede por **fonte controlada por MODELS** com atraso de um passo
  declarado e verificado quanto a estabilidade.
- **Modelo chaveado detalhado de referência construído no próprio ATP** (N_SM ∈ {8, 12}, com snubbers),
  usado como verdade-terreno interna — reexecutável pela banca sem licença de terceiros.
- Topologia CC completa: dois polos independentes, reator de alisamento, reator de braço, resistor de
  pré-inserção, **NBS**, para-raios CC, ramo de aterramento, eletrodo de terra e retorno metálico, com
  os três modos de operação comutáveis.
- LT CC de 2.500 km em JMarti, com verificação de velocidade de modo aéreo e tempo de trânsito (~8,5 ms).
- Transformador conversor via BCTRAN; redes CA por equivalentes de Thévenin com **SCR paramétrico**
  (2,50 / 4,08 / 5,47 / 6,07, com 1,92 reportado).
- Varreduras de SCR e de nível de tensão CC (525 / 600 / 640 kV, os três cenários do §1.5.4 da EPE).

### 5.2 Excluído (e por quê)

| Item | Motivo |
|---|---|
| Componente **Type-94** e qualquer elemento por compensação | o modo THEV admite um elemento por sub-rede eletricamente conectada; o bipolo tem 24 braços em, no máximo, duas sub-redes |
| Controle **grid-forming** | a própria EPE registra que "não há uma definição consensada" de requisitos (§15.2.15, p. 256); validar contra requisito instável é indefensável — vira tema-satélite |
| Full-bridge, arranjos mistos, híbridos LCC+VSC, >640 kV, >3,6 GW, multiterminal | descartados pelo grupo de trabalho EPE-ONS (§6.4, p. 79) |
| Disjuntores CC | não fazem parte da solução meia-ponte de referência |
| Espectro harmônico de comutação / **IEEE 519** | um modelo com submódulos agregados **não** reproduz o espectro de comutação — prometer isso destrói credibilidade técnica |
| *Converter-driven stability*, varredura de impedância e passividade | tema-satélite (§10) |
| Coordenação de isolamento e dimensionamento de para-raios/chopper | tema-satélite; o modelo entrega as formas de onda, não o dimensionamento |
| Modelos *replica* de fabricante e padrão IEEE/CIGRÉ DLL | tema-satélite e item de roadmap comercial |
| Refatoração do núcleo do Olivas EPS | integração é **estritamente aditiva** |
| Redistribuição do solver ATP | publica-se **dados e modelos**, nunca o executável |

---

## 6. Metodologia e cronograma

| Fase | Conteúdo | Marco |
|---|---|---|
| **E0** set/26 | Extração rastreável das premissas; especificação do benchmark com 5 casos de ensaio; pré-registro dos critérios | **M0** — premissas e requisitos aprovados pelo orientador |
| **E1** out/26 | **GATE TÉCNICO**: PoC do wiring MODELS→fonte controlada no ATP; `models_wiring.py`; oráculo em Python | **M1 (GO/NO-GO, 31/10/2026)** — PoC executa e o laço realimentado é estável |
| **E2–E3** nov/26 | Braço em MODELS com estados de submódulo; LT CC em JMarti; verificação de R a 20 °C e 50 °C, velocidade de modo e tempo de trânsito | **M2** — erro ≤ 1% nos parâmetros de linha |
| **E4** dez/26 | Verdade-terreno interna (modelo chaveado no próprio ATP); conservação de energia de braço; **preprint com DOI** | **M3 — TCC 1 aprovado**; NRMSE ≤ 2% |
| **E5** jan/27 | Controle *grid-following*; sintonia por largura de banda; *capability*; STATCOM | **M4** — degrau 0,1→1,0 pu com sobressinal ≤ 10% e acomodação ≤ 100 ms |
| **E6** fev/27 | Bipolo completo; inicialização determinística e soft-start; regime permanente | **M5 (GATE MUST, 28/02/2027)** — núcleo mínimo defensável atingido |
| **E7** mar/27 | Máquina de estados de proteção; ensaio de falta polo-terra na LT CC | **M6 (data de corte, 31/03/2027)** — temporizações reproduzidas com erro ≤ 2 ms |
| **E8–E9** abr/27 | Agregação N→N_eq; varredura de Δt e de temporizações; decomposição do erro de representação | **M7** — par (N_eq, Δt) recomendado; **artigo submetido** |
| **E10** mai–jun/27 | Integração aditiva ao Olivas EPS; varreduras de SCR e tensão; redação e defesa | **M8/M9** — PR com CI verde; **TCC defendido**; release v1.0 com DOI |

O **M5 (28/02/2027) é o gate de segurança**: validação contra verdade-terreno interna + regime
permanente contra a EPE já constitui, sozinho, um TCC aprovável e um artigo submetível. Tudo o que vem
depois é incremento.

---

## 7. Plano de validação

Todos os critérios são **pré-registrados** antes da execução, com métrica única declarada
(NRMSE normalizado pela faixa do sinal de referência) e **todos os desvios publicados**, inclusive os
reprovados. Duas classes de tolerância são mantidas rigorosamente separadas: **verificação de
implementação** (testa o código; tolerância apertada) e **validação física** (testa o modelo contra
grandezas que dependem de parâmetros internos não publicados; tolerância larga, demonstração em envelope).

| Nível | O que testa | Critério | Depende de terceiros? |
|---|---|---|---|
| **V0** | Conservação de energia de braço | desvio < 0,5% da energia nominal em 1 s | **Não** — analítico |
| **V1** | Parâmetros da LT CC | R a 20 °C e 50 °C com erro ≤ 1%; τ ≈ 8,5 ms; v entre 0,90c e 0,99c | Não |
| **V2** | Verdade-terreno interna (modelo chaveado no próprio ATP) | NRMSE ≤ 2% em tensão CA, corrente de braço e circulante; erro de tensão de capacitor ≤ 1% | **Não** |
| **V3** | Regime permanente (Tabelas 15-6 e 15-7 da EPE) | erro ≤ 1% nas grandezas CC; 2,5 kA / 2,34 kA | Não |
| **V4** | Desempenho de controle | sobressinal ≤ 10%; acomodação ≤ 100 ms; erro ≤ 0,5%; margem de fase ≥ 45° | Não |
| **V5** | Falta CC (Capítulo 12) | temporizações programadas com erro ≤ 2 ms; sobretensão ≤ 1,5 pu; picos e tempos **em envelope** | Não |
| **V6** | Referência externa (Simulink/Simscape ou PSCAD acadêmico) | complementar, declarado como tal | **Sim — opcional** |

**A validação não depende de licença de terceiros.** V0 é analítica; V2 usa como referência um modelo
construído no próprio ATP; V1, V3 e V5 usam números publicados pela EPE. V6 é bônus.

Uma correção metodológica relevante: **os parâmetros internos do MMC não são públicos** (número de
submódulos, capacitância, indutância de braço, transformador). A resposta não é chutar valores e
comparar ponto a ponto — é **varrer as faixas de projeto declaradas e demonstrar que o resultado da
EPE cai dentro do envelope produzido**, separando erro de método de erro de premissa.

---

## 8. Integração ao Olivas EPS

### 8.1 O que já existe (verificado no repositório)

O Olivas EPS já é um front-end e pré/pós-processador completo de ATP-EMTP:

- `app/preprocessor/atp_format.py` — emissão em **formato colunar estrito** (≤ 80 colunas, nó de 6
  caracteres), conforme ATP Rule Book Vol. 2
- `app/preprocessor/bridge_to_atp.py` (2.461 linhas) — tradutor unifilar → cartões, com despacho por
  tipo (`_convert_diode:452`, `_convert_igbt:1201`, `_convert_transformer:1221`, `_convert_line:1515`)
- `app/preprocessor/spec/` + **59 arquivos `.ocomp`** em `catalog_specs/` — registro declarativo de componentes
- `tacs.py`, `tacs_blocks.py`, `tacs_tf.py`, `tacs_interface.py` — blocos TACS e ponte EMTP↔TACS
- `vcb_model_emitter.py` + `atp_templates/vcb_reignition.mod` — **precedente direto**: um algoritmo
  complexo (CIGRE WG A3.26) já é entregue como template em linguagem **ATP MODELS**
- `lcc.py`, `jmarti_pch.py`, `vector_fitting.py` — LINE CONSTANTS, JMarti e ajuste racional
- `bctran.py` — transformador (único emissor já em colunas fixas Type-51/52)
- `simulation/runner.py` (`AtpRunner`) e `results_reader.py` (leitura de PL4)
- `postprocessor/audit_trail.py` — laudo com SHA256 dos inputs e bloco de limitações automático
- `app/plugins/` — ecossistema de plugins

### 8.2 O que não existe — o delta do TCC

**Nenhum dos 59 componentes do catálogo é de corrente contínua.** Não há conversor, não há polo CC, e
`PinPhase` admite apenas A/B/C/N/NONE. Além disso, três achados de auditoria mudam a ordem das tarefas:

1. **Não existe wiring MODELS↔rede automatizado.** O próprio `vcb_reignition.mod` declara na sua
   limitação v0.22.1 que "o wiring TACS ... é manual". Esse é o **gargalo estrutural** e a primeira
   tarefa técnica — e, isoladamente, vale mais para o produto do que o módulo HVDC, porque destrava
   qualquer modelo futuro que precise de lógica (proteção, FACTS, religador, gerador com conversor).
2. **`app/preprocessor/tacs_interface.py:141,148` documenta a fonte comandada por TACS como
   "SOURCE TYPE-13 (V) ou TYPE-14 (I)".** No ATP, Type-13 é fonte rampa de dupla inclinação e Type-14 é
   fonte cossenoidal; a fonte comandada por TACS/MODELS é o **Type-60**. Item a corrigir — e exatamente
   o tipo de erro que faz uma prova de conceito falhar pelo motivo errado.
3. **`tests/test_pp_registry_guard.py:69,275,279` espera 49 arquivos `.ocomp`, e existem 59.** Drift
   pré-existente do teste de guarda, a corrigir em PR separado (não como carona do PR de HVDC).

### 8.3 Entregáveis de integração (aditivos)

`VSCMMC.ocomp`, `LTCC.ocomp`, `NBS.ocomp` e `ELTR.ocomp`; renderizadores em `symbols.py`; ramos de
despacho em `bridge_to_atp.py`; extensão de `PinPhase` com DC_POS/DC_NEG/DC_RET; emissão estrita do
para-raios CC; `app/analysis/mmc_metrics.py`; `app/standards/epe_hvdc_vsc.py` (requisitos §3.4[8] e
§3.4[9] como critérios executáveis com citação de página); `app/postprocessor/studies/hvdc_dc_fault.py`
com veredito PASS/FAIL encadeado ao laudo auditável.

---

## 9. Viabilidade de mercado

### 9.1 A premissa precisa ser corrigida antes de virar argumento

**"Hoje só o PSCAD tem modelo voltado para HVDC-VSC" é falso como afirmação geral.** Têm modelo MMC
nativo, no mínimo: **EMTP-RV** (documentação pública de 2014 com quatro níveis de modelo — *Full
Detailed*, *Detailed Equivalent*, *Switching Function of Arm*, AVM), **DIgSILENT PowerFactory** (MMC
meia-ponte e ponte completa, cobrindo os tipos 3 a 7 da CIGRÉ TB 604), **MATLAB/Simulink + Simscape
Electrical**, **PLECS**, **RTDS/RSCAD**, **OPAL-RT/HYPERSIM** e **Typhoon HIL**. Sustentar a premissa
original em banca ou em material de venda é entregar o flanco ao primeiro interlocutor que abrir o
site da DIgSILENT.

**A premissa é verdadeira em três recortes** — e é deles que o trabalho vive:

1. **Ecossistema ATP-EMTP/ATPDraw:** não foi localizado nenhum modelo MMC/VSC público, distribuído ou de
   biblioteca. Há artigos de conferência (grupo do Prof. M. Kizilcay, Univ. Siegen, European EMTP-ATP
   Conference 2016 e 2017) **sem entrega de arquivos**. *Exigência metodológica: essa afirmação só entra
   no texto como "não foi localizado até <data>", com script de busca versionado, e somente após obter e
   ler os trabalhos de Siegen — isso é tarefa do mês 1.*
2. **Ecossistema aberto:** Dynawo, DPsim, ANDES, OpenIPSL, PowerSimulationsDynamics.jl, GridPACK e
   pandapower param em modelos fasoriais/médios. Nenhum MMC EMT chaveado.
3. **Prática regulatória brasileira:** nas 509 páginas do EPE-DEE-RE-071/2025 há **15 ocorrências de
   "PSCAD"** e **zero** de ATP, EMTP, ATPDraw, PowerFactory, Simulink, RTDS ou HYPERSIM.

### 9.2 O argumento comercial forte (verificado na fonte primária)

O gargalo brasileiro **não é o PSCAD — é o ATP**. Nos Procedimentos de Rede do ONS, Submódulo 2.5
(*Requisitos mínimos para elos de corrente contínua*, rev. 2016.12, aprovada pela ReN ANEEL 756/16):

> **§7.15.1.9** (p. 36) — "Estes estudos devem ser realizados com os programas usualmente utilizados no
> SIN: ANAREDE (fluxo de potência), ANATEM (estabilidade eletromecânica), **PSCAD e/ou ATP**
> (transitórios eletromagnéticos)."

> **§7.15.1.10** (p. 36) — "**Mesmo que os estudos tenham sido realizados por meio do PSCAD, a
> transmissora deve entregar ao ONS**, até o início dos estudos pré-operacionais, **um modelo detalhado
> do elo CC incluindo todos os controles também para o programa ATP**. Este modelo deve ser acompanhado
> pelo manual correspondente e pelos testes de validação executados confrontados com os resultados
> obtidos pelo Simulador CC."

> **§7.15.3.4** (p. 37) — sobre os estudos de manobra do pátio CA das conversoras (energização de
> transformadores conversores, TRT de disjuntores, energização de linhas, religamentos):
> "**As simulações devem ser realizadas na ferramenta ATP.**"

> **§7.15.2.2 e §7.15.2.3** (p. 37) — oscilações subsíncronas em "ATP ou PSCAD", e "os modelos
> utilizados, devidamente aferidos e documentados, devem ser disponibilizados ao ONS".

E no Submódulo 18.2 (*Modelos computacionais*, rev. 2020.01), item **4.2.4**: "ATP — Denominação de
referência: Modelo para análise de transitórios eletromagnéticos. **Propriedade: uso livre**",
referenciado em 15 submódulos (2.3, 2.4, 2.5, 2.8, 4.3, 6.3 a 6.6, 7.5, 21.2, 21.4, 21.6, 21.9, 23.3).
**O PSCAD não consta da lista oficial de ferramentas do ONS.**

Conclusão: existe **obrigação regulatória** de produzir modelo detalhado de elo CC em ATP — e, para o
primeiro bipolo VSC do SIN, alguém terá de construir um MMC em ATP. Hoje esse trabalho é feito
artesanalmente, sem ferramental de autoria, e não há modelo público de partida.

> *Nota de diligência: os Procedimentos de Rede passaram por reorganização e revisões recentes. A
> numeração e a redação acima foram verificadas nas versões citadas; antes de qualquer uso externo
> (proposta comercial, artigo), reconfirmar na revisão vigente na data.*

### 9.3 Dimensionamento honesto

**O que não é mercado:** os R$ 26,5 bilhões (R$ 17,1 bi em CC) são **CAPEX de obra**. Usá-los como
mercado endereçável de software é o erro de dimensionamento mais fácil de desmontar numa reunião.

**O que é mercado:** o gasto brasileiro realmente endereçável em ferramenta de estudo EMT de HVDC é da
ordem de **poucos milhões de reais por ano, entre menos de dez organizações**, a maioria já com PSCAD
instalado e, a partir do R2, obrigada a usar modelo *replica* de fabricante.

**Onde está o retorno, em ordem de concretude:**

1. **A linha de montagem normativa.** `app/standards/epe_hvdc_vsc.py` transforma os requisitos §3.4[8] e
   §3.4[9] em critérios executáveis com veredito PASS/FAIL e laudo auditável em SHA256. O modelo físico
   qualquer engenheiro competente reproduz da literatura; a **codificação normativa versionada e
   rastreável, não**. E há janela: os Procedimentos de Rede cobrem apenas LCC e vão precisar de
   procedimento específico para VSC.
2. **Infraestrutura que vale mais que o módulo.** O wiring MODELS↔rede destrava qualquer modelo futuro
   com lógica e habilita um marketplace de módulos de terceiros.
3. **Alavanca sobre módulos que já vendem:** TRT/IEC 62271-100 nos disjuntores CA das conversoras — que
   são precisamente o meio de eliminação de falta CC na solução meia-ponte —, sobretensões e para-raios
   agora também do lado CC. *Sem prometer IEEE 519* (§5.2).
4. **Funil acadêmico:** universidades sem licença PSCAD passam a poder ensinar HVDC-VSC com ATP +
   Olivas EPS. É aquisição barata, não receita.

**Teto declarado, por escrito e por código:** nenhum modelo genérico aberto substitui o *replica* do
fabricante em R2, detalhamento ou comissionamento. O nicho é **planejamento, anteprojeto, verificação
independente e ensino** — exatamente onde a EPE ficou sem ferramenta. O laudo emite esse bloco de
limitações automaticamente.

**Gate comercial obrigatório antes de maio/2027:** lista nominal de dez organizações-alvo, hipótese de
preço (por assento ou por estudo) e duas cartas de interesse assinadas. Sem isso, o módulo deve ser
orçado como **marketing técnico e funil acadêmico** — o que continua sendo bom investimento, com a
expectativa correta.

### 9.4 Um risco jurídico que precede este TCC

A licença de uso do ATP-EMTP é concedida individualmente por grupos regionais de usuários e exige
declaração de **não participação no "comércio do EMTP"**, além de vedar a redistribuição do material.
Isso é **exposição pré-existente e de nível de empresa** — a Olivas já comercializa hoje um front-end de
ATP, sem qualquer módulo HVDC. O parecer jurídico e a consulta ao grupo de usuários devem ser
conduzidos **agora, por causa do produto existente**, e nenhuma peça deste trabalho deve alegar que o
módulo HVDC agrava a exposição. O que o TCC publica são **dados e modelos** (`.atp`, `.mod`, `.csv`),
nunca o solver.

---

## 10. Licenciamento: open-core em três camadas

- **Camada 1 — aberta e permissiva** (repositório independente, DOI Zenodo, manifesto SHA256):
  **Apache-2.0** para código, templates `.mod` e cartões `.atp`; **CC-BY-4.0** para dados, premissas,
  dataset de validação, figuras e documentação. Efeito prático: EPE, ONS, ANEEL, transmissoras,
  fabricantes e universidades usam, modificam e redistribuem sem pedir permissão, inclusive
  comercialmente.
- **Camada 2 — produto** (`Feature.HVDC_VSC_STUDY` em `app/commercial/feature_gates.py`): estudo
  automatizado em lote com veredito PASS/FAIL, codificação normativa, motor de varredura paramétrica,
  laudo profissional com auditoria e SHA256, biblioteca curada e mantida de casos, suporte.
- **Camada 3 — infraestrutura**, contribuída ao núcleo sob Apache-2.0 e de forma estritamente aditiva.

Racional: a barreira de entrada de um concorrente **não é o modelo** — é a cadeia
*unifilar → cartão ATP → execução → laudo assinável*. Abrir o modelo maximiza adoção, citação e
confiança; o produto captura valor no fluxo de trabalho.

---

## 11. Riscos

| # | Risco | P | I | Mitigação |
|---|---|---|---|---|
| R1 | Acoplamento MODELS→fonte controlada não funcionar, ou laço com atraso de um passo ser instável | Média | **Alto** | PoC como primeira tarefa, com GO/NO-GO em 31/10/2026, antes de qualquer investimento em controle |
| R2 | Custo computacional inviabilizar as varreduras (MODELS é interpretado) | Média | Médio-alto | Envelope declarado: submódulos agregados, Δt = 20 µs, reordenação apenas nas transições de nível |
| R3 | Nenhum parâmetro interno do MMC é publicado | **Certa** | Médio | Dimensionamento por regras públicas com faixa declarada + **validação em envelope** |
| R4 | Modelo não reproduzir a falta CC — falha que o próprio benchmark do PSCAD apresentou (p. 199) | Média | Alto | Estado bloqueado validado isoladamente em circuito reduzido antes do caso completo |
| R5 | Escopo excessivo para autor único em 10 meses | **Alta** | Alto | Partição MoSCoW assinada + gate M5 (28/02/2027) que sozinho já é TCC aprovável |
| R6 | Perda de ineditismo (Siegen publicou arquivos? terceiro publica antes?) | Média | Médio | Ler Siegen no mês 1; preprint com DOI em dez/2026 para fixar prioridade |
| R7 | Indisponibilidade de ferramenta de referência externa | Média | **Baixo** | Validação principal é autossuficiente (V0–V5) |
| R8 | Cláusula de "comércio do EMTP" na licença do ATP | Média | Alto p/ negócio; **nulo** p/ validade acadêmica | Parecer jurídico conduzido pela empresa **agora**, por causa do produto existente |
| R9 | Modelo aberto ser percebido como substituto do *replica* de fabricante | Média | Médio | Teto declarado por escrito **e por código** (bloco de limitações automático no laudo) |
| R10 | Quebra do CI na integração (guard test espera 49 `.ocomp`, existem 59) | Alta | Baixo | Correção do drift em PR separado; código novo importa sem PySide6 |

---

## 12. Questões técnicas em aberto (a fechar no gate M1)

Levantadas na revisão crítica desta proposta e **deliberadamente não resolvidas aqui** — são o conteúdo
das primeiras seis semanas:

1. **Taxonomia do modelo.** Um braço com vetor de tensões de capacitor, modulação por nível mais próximo
   e ordenação é mais próximo do *Detailed Equivalent Model* (Gnanarathna–Gole–Jayasinghe, 2011) com
   submódulos agregados do que do *Switching Function of Arm*. A rotulagem correta precisa ser fechada
   antes da redação — ela muda a alegação de contribuição.
2. **Topologia do estado bloqueado.** Um diodo de *bypass* em paralelo com uma **fonte de tensão ideal**
   controlada curto-circuita a fonte ao conduzir (matriz singular). A implementação viável provavelmente
   é chavear o **valor** da fonte dentro do MODELS em função do sinal da corrente de braço, com
   resistência série explícita. É onde o trabalho pode queimar semanas — e é onde o modelo da EPE falhou.
3. **Tipo de cartão da fonte comandada** — Type-60, e não Type-13/14 como o repositório documenta (§8.2).
4. **Requisito de reenergização.** A leitura de que "a EPE não atenderia ao próprio requisito" **não se
   sustenta**: o §15.2.13 (p. 256) mostra que os 2,5 s e os 5 s foram *derivados* dos ~2 s de
   reenergização e ~4 s de recuperação observados no PSCAD. O que resta é uma **ambiguidade de definição**
   de "reenergização" — nota de rodapé, não pilar de originalidade.
5. **Divergências internas do relatório** a registrar (não a "explicar"): 3 kA (p. 254) × ~2,85 kA
   (p. 123) de corrente máxima de IGBT; §3.4[8].b ("corrente total ≤ 1 pu") × §15.2.9 (limite de 1 pu
   de corrente **CC**); Kiwi 72/7 × 45/7 entre tabelas; "R$ 199,96/MWh" (p. 242) × "/MW" (p. 246 e 259).

---

## 13. Temas-satélite (próximos TCCs sobre a mesma base)

1. **Grid-forming sobre o modelo aberto** — droop, VSM e dVOC em MODELS, atacando o regime em que o
   *grid-following* falha por construção: SCR < 2, exatamente a contingência N-2 Açu III–Angicos.
2. **Estabilidade dirigida por conversores em Angicos** — varredura de impedância, passividade e
   interações harmônicas com os IBRs vizinhos. Ataca diretamente a recomendação §3.4[11] e o §15.2.14
   ("*deve ser investigada a possibilidade da ocorrência de interações de controle e interações
   harmônicas*"). **Maior valor comercial**, porque a EPE tornou o estudo obrigatório.
3. **Contribuição de curto-circuito de unidade com conversor pleno (IEC 60909-0:2016 §6.7)** — fecha o
   ciclo com o módulo de curto-circuito que o Olivas EPS **já vende** e que hoje não implementa §6.7.
   **Maior conversão comercial imediata.**
4. **Coordenação de isolamento do pátio CC ±600 kV** — dimensionamento de para-raios, resistor de
   amortecimento e chopper, atacando a recomendação §3.4[10].
5. **Hospedagem de modelos de fabricante no padrão IEEE/CIGRÉ DLL (CIGRÉ TB 958, 2025)** em fluxo
   ATP-EMTP — o único caminho que **resolve**, em vez de tentar substituir, o problema do modelo
   certificado. Roadmap de produto, não pesquisa de graduação.

---

## 14. Decisões pendentes

1. **Orientador e instituição** — o trabalho exige alguém confortável com EMT e ATP.
2. **Ferramenta de referência externa (V6)** — verificar se a universidade tem PSCAD educacional ou
   MATLAB/Simscape. Não é bloqueante, mas fortalece a validação.
3. **Declaração de vínculo** — o autor é ligado à Olivas; isso deve constar da folha de rosto e de seção
   própria da monografia.
4. **Parecer jurídico sobre a licença do ATP** (§9.4) — tarefa da empresa, imediata e independente do TCC.
5. **Onde publicar o repositório aberto** — organização própria ou institucional, com DOI Zenodo.

---

## 15. Referências principais

1. **EPE**. *EPE-DEE-RE-071/2025-rev0 — Estudo de Expansão das Interligações Regionais, Parte III*. Nov. 2025, 509 p.
2. **ONS**. *Procedimentos de Rede, Submódulo 2.5 — Requisitos mínimos para elos de corrente contínua*, rev. 2016.12.
3. **ONS**. *Procedimentos de Rede, Submódulo 18.2 — Modelos computacionais*, rev. 2020.01.
4. **EPE**. *EPE-DEE-DEA-NT-004/2020 — Diretrizes para a elaboração dos relatórios técnicos R1 a R5*.
5. **GNANARATHNA, U. N.; GOLE, A. M.; JAYASINGHE, R. P.** *Efficient Modeling of Modular Multilevel HVDC
   Converters (MMC) on Electromagnetic Transient Simulation Programs*. IEEE Trans. Power Delivery, 2011.
   DOI 10.1109/TPWRD.2010.2060737.
6. **CIGRÉ WG B4.57**. *TB 604 — Guide for the Development of Models for HVDC Converters in a HVDC Grid*, 2014.
7. **CIGRÉ JWG B4.82**. *TB 958 — Guidelines for Use of Real-Code in EMT Models for HVDC, FACTS and
   Inverter-Based Generators*, 2025.
8. **SAAD, H.; MAHSEREDJIAN, J.; DENNETIÈRE, S. et al.** *MMC Documentation* (EMTP-RV), 2014 — quatro
   níveis de modelo de MMC.
9. **HATZIARGYRIOU, N. et al.** *Definition and Classification of Power System Stability — Revisited &
   Extended*. IEEE Trans. Power Systems, v. 36, n. 4, 2021.
10. **DOMMEL, H. W.** *EMTP Theory Book*. BPA.
11. **ATP Rule Book**, vols. 1 e 2 (MODELS, TACS, LINE CONSTANTS, JMarti).
