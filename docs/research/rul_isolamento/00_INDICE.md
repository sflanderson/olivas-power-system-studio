# Monitoramento de degradação de isolamento e RUL de motores de indução MT — índice e nota metodológica

**Objetivo.** Registrar, em um único ponto de entrada, (i) o objetivo e o desenho em três etapas do estudo que fundamenta o módulo MVP de RUL (*remaining useful life*) de isolamento de estator para motores de indução de média tensão (MT, 2,3–13,8 kV) manobrados por disjuntores a vácuo (VCB) em plantas críticas; (ii) o método de produção e de verificação do material, incluindo o sistema de rótulos de evidência que governa todo o corpus; (iii) o mapa navegável dos documentos, dos anexos e dos **dois pacotes de código** que são o produto executável da série; (iv) as premissas do usuário — inclusive as decisões de arquitetura do autor sobre motor de física próprio e sobre modelos de linha — e as limitações globais que restringem o uso acadêmico do material; e (v) o próximo passo recomendado. Este arquivo é índice e contrato metodológico: ele **não** repete conteúdo técnico dos anexos nem do código, apenas os endereça.

**Diagnóstico.** As três etapas estão entregues e verificadas, em cinco documentos que somam 4 461 linhas — `01_…md` (873 l.), `02_…md` (960 l.), `03_…md` (701 l.), `04_…md` (733 l.) e `05_…md` (818 l.) —, sustentadas por 31 anexos (8 949 linhas) organizados em seis subdiretórios [REPO: `docs/research/rul_isolamento/`, contagem por `wc -l` nesta sessão]. A esse acervo textual juntou-se uma camada nova, de natureza distinta: **código executável e testado**, nos pacotes `app/simulation/emt/` (11 arquivos, 9 915 l., 273 testes) e `app/postprocessor/prognosis/` (5 arquivos, 3 240 l., 176 testes), com 449 testes passando em 62,66 s [CÁLCULO PRÓPRIO: `python3 -m pytest tests/test_emt_kernel.py tests/test_emt_vcb_snubber.py tests/test_emt_steady_state.py tests/test_emt_jmarti.py tests/test_emt_referencia_eee873.py tests/test_pp_prognosis_core.py -q` → `449 passed`, nesta sessão]. O acervo cobre com solidez três dos quatro elos da cadeia manobra → estresse → estado → vida: o **gerador de estresse** — que deixou de depender de binário de terceiro, porque o motor EMT próprio produz o vetor $s_{m,j}$ diretamente da sonda, sem arquivo intermediário [REPO: `docs/research/rul_isolamento/05_MOTOR_EMT_DEDICADO.md`, §11.1] —, o **envelope normativo de suportabilidade** (IEC 60034-15, IEEE 522, IEC 60034-18-41/-42, IEC 60071-1, IEC 62271-110) e o **estado da arte de monitoramento e de prognóstico** (13 fichamentos + IEC 60034-27-x, IEEE 43/1434, ISO 13374-1/13381-1). O elo ausente continua sendo o quarto e decisivo: **nenhuma fonte primária acessada fornece parâmetros de curva de vida (expoente $n$, limiar $V_{th}$, fração espira-a-espira $a(t_f)$) medidos em mica-epóxi pré-formada de MT sob impulsos de VCB** [FATO: `01_ETAPA1...md`, bloco inicial, "Limitações" (b) e §5.4, D1–D2]. Por isso o acumulador implementado é, por construção, **arquitetura com parâmetros declaradamente livres**, cuja incerteza é propagada, e não escondida. Duas lacunas estruturais permanecem abertas e estão registradas como tais: o motor **não lê `.atp`** (§4.1, P6) e é hoje um ***backend* órfão**, não importado por nenhum módulo fora do próprio pacote [FATO: `05_…md`, §11.3 e §11.4].

**Arquivos consultados.**

| Arquivo | Papel na composição deste índice |
|---|---|
| `01_ETAPA1_monitoramento_degradacao_isolamento.md` (873 l.) | Documento indexado; dele provêm o escopo da Etapa 1, as equações-âncora (§5.4), as limitações declaradas e a lista de referências sem fonte primária |
| `02_ETAPA2_cruzamento_A_x_B.md` (960 l.) | Documento indexado; acoplamento causal B → $\lambda$ / A → severidade, cadeia térmica derivada, acumulador multiestresse, *health-aware load shedding* |
| `03_ETAPA3_contexto_c_level.md` (701 l.) | Documento indexado (Etapa 3, parte 1); tabela-mestra fenômeno → KPI, custo de indisponibilidade verificado, modelo $E[C]$, painel executivo |
| `04_ARQUITETURA_MVP_RUL_OLIVAS.md` (733 l.) | Documento indexado (Etapa 3, parte 2); arquitetura do MVP, contratos de dados, realização de D1–D7 em código, *roadmap* e critérios de aceite |
| `05_MOTOR_EMT_DEDICADO.md` (818 l.) | Documento indexado; fundamentação, implementação, validação e critério de migração para C++ do motor EMT próprio; §11 (ponte com o prognóstico e papel do `.atp`) e §12 (41 limitações catalogadas) |
| `app/simulation/emt/` (11 arq., 9 915 l.) | Pacote de código indexado; motor EMT dedicado (MNA, modelos companheiros, CDA, Bergeron, JMarti, VCB, *snubber*) |
| `app/postprocessor/prognosis/` (5 arq., 3 240 l.) | Pacote de código indexado; perfil de estresse, modelos de dano D1–D7, estimador de RUL e *Asset Health Index* |
| `tests/test_emt_*.py` (5 arq., 4 154 l. com o de prognóstico) + `tests/test_pp_prognosis_core.py` | Contagem real de testes e estado de regressão declarados na §3.8 |
| `anexos/fichamentos_AB/A_snubber_tiristor_vcb.md` (423 l.) | Estado verificado do Documento A: Tabelas I–III, parâmetros do VCB, seção 8 ("o que A não afirma") |
| `anexos/fichamentos_AB/B_load_shedding_n1_nsga.md` (473 l.) | Estado verificado do Documento B: restrições g1–g3, NSGA-II/III, ausências declaradas |
| `anexos/fichamentos/01…13_*.md` (13 arq., 2 961 l.) | Corpus de apoio; convenções de rotulagem de cada fichamento |
| `anexos/pesquisa/*.md` (9 arq.) | Pesquisas dirigidas (3) e pesquisas web multi-fonte (6), com registro de bloqueios HTTP |
| `anexos/repo/*.md` (5 arq., 1 820 l.) | Mapas do código do Olivas Power System Studio (VCB/snubber, TRT, motor/partida, confiabilidade, convenções) |
| `anexos/cruzamento/*.md` (2 arq., 812 l.) | Cruzamentos A × literatura × repositório e B × consumo de vida |
| `anexos/verdicts/{A,B}_*.json` | Veredictos da verificação adversarial dos fichamentos A e B |
| Fontes primárias de EMT (5 arq., texto integral) | Dommel 1969 e 1971; Ho, Ruehli e Brennan 1975; Lin e Martí 1990; Mahseredjian et al. 2007 — base das deduções do documento 05 (§2.1, camada nova) |
| Listas 01 e 02 de EEE873 (2 arq., texto integral) | Trabalhos do próprio autor; fixam a notação e são o caso de referência já validado contra o ATP (§2.1) |

**Estratégia.** O índice adota três eixos de organização, nesta ordem de precedência: **(1) estado epistêmico** — cada item do acervo é classificado por origem (fonte primária lida / metadado / fonte secundária / inferência) por meio do sistema de rótulos da §2.7, que é o mesmo em todos os arquivos; **(2) função na cadeia causal** — cada anexo é posicionado como gerador de estresse, envelope normativo, indicador de estado, modelo de vida ou infraestrutura computacional; **(3) rastreabilidade** — todo caminho é relativo à raiz `docs/research/rul_isolamento/`, de modo que o diretório seja portável para anexo de tese, apêndice de artigo ou pacote de entrega, sem reescrita de referências.

**Limitações.** (a) As três etapas têm produto verificável em disco, mas os produtos **não têm o mesmo estatuto**: os documentos 01 a 03 são estudo com evidência rotulada; o 04 e o 05 descrevem **código que existe e é testado**, e por isso envelhecem com o código — toda contagem de linha, de teste e de limitação neles vale para o estado da árvore declarado, e deve ser reconferida por execução antes de citação acadêmica [CÁLCULO PRÓPRIO]. (b) O índice herda integralmente as limitações da Etapa 1 (§4.2), inclusive a ausência de parâmetros de vida para mica-epóxi e a não leitura do texto integral da IEEE Std 522 e da Tabela 1 da IEC 60034-15:2025. (c) Documentos A e B estão em revisão duplo-cega, sem autoria divulgada, o que impede citação nominal e obriga a marca [INSERIR CITAÇÃO] em toda referência bibliográfica a eles. (d) A contagem de linhas e de arquivos reflete o estado da árvore no momento da redação; qualquer inclusão posterior de anexo exige atualização da §3.

**Próximo passo recomendado.** A extração declarada como próximo passo da Etapa 1 — tensão no nó do motor, contagem de reignições por polo e tempo de frente $T_1$ por reignição — deixou de depender do binário do ATP: as três grandezas são hoje **saídas do motor próprio**, componentes nomeados do vetor de estresse $s_{m,j}$ [FATO: `05_…md`, §11.2]. O que resta, e é o que a §5 detalha, é (i) **fechar a lacuna do leitor de `.atp` → `Circuit`**, sem o qual a decisão de "fonte única da verdade" é intenção de arquitetura e não propriedade do código, e (ii) **retirar o motor da condição de *backend* órfão**, proibida pelas convenções do repositório [FATO: `05_…md`, §11.3–§11.4, §12.4]. O confronto numérico contra a Tabela III do Documento A permanece **aberto e assim reportado**, por falta dos dados de rede que A não publica [FATO: `05_…md`, §9].

---

## 1. Objetivo do estudo e desenho em três etapas

### 1.1 Objeto e recorte

O estudo constrói a **base técnica e de negócios** de um módulo MVP de estimação de RUL do isolamento de estator de motores de indução de MT (2,3–13,8 kV) instalados em plantas críticas, integrável ao Olivas Power System Studio [REPO: `app/core/version.py:1959-1968`, `VERSION_TUPLE = (4, 0, 0)` + `PRE_RELEASE = "beta"`, conforme `anexos/repo/convencoes_auditoria_gui_docs.md`]. O recorte de modo de falha é o **dano espira-a-espira por surtos de frente rápida** originados em manobra de VCB, e não a falha de massa (*groundwall*) nem os mancais.

Três razões sustentam o recorte, todas verificadas na Etapa 1: a física concentra a solicitação nas primeiras espiras sob frente curta [NORMA: IEC 60034-15:2009, Anexo A.1]; a norma reconhece não existir lei fechada para pré-calcular essa tensão longitudinal [NORMA: IEC 60034-15:2009, A.3]; e o curto entre espiras é tratado na literatura como estágio inicial da maioria das falhas de enrolamento [LITERATURA: Kohler, Sottile e Trutt, IEEE TIA, 2002, DOI 10.1109/tia.2002.802935 — resumo verificado].

O contexto de aplicação — refinarias e plataformas de óleo e gás (O&G) — é tratado como **hipótese de mercado e de severidade operacional**, não como fato do corpus: nenhum documento do acervo contém dados de campo de uma planta específica [HIPÓTESE; ver §4.1, item P3].

### 1.2 Perguntas-guia do estudo

| # | Pergunta | Etapa que responde |
|---|---|---|
| Q1 | Por que o dano espira-a-espira é o modo de falha crítico e o mais difícil de detectar? | 1 (entregue) |
| Q2 | Quanto estresse dielétrico uma manobra severa impõe, em números verificáveis, e como ele se compara aos envelopes normativos? | 1 (entregue) |
| Q3 | Por que nenhum método normalizado converte uma manobra em consumo de vida, e o que faltaria para que convertesse? | 1 (entregue) |
| Q4 | Que arquitetura computacional converte oscilograma de manobra em RUL com incerteza declarada, e como ela se acopla ao repositório existente? | 2 (entregue) + 4 |
| Q5 | Que valor econômico e que indicadores (Asset Health Index, custo evitado) tornam o módulo defensável perante C-Level, e como o resultado é entregue como trabalho acadêmico reprodutível? | 3 (entregue, em duas partes: 03 e 04) |
| Q6 | Quem resolve o transitório que gera o vetor de estresse, com que fundamentação e com que validação — e sob que critério objetivo o laço interno migra para C++? | 05 (entregue) |

### 1.3 As três etapas

| Etapa | Escopo | Produto | Estado |
|---|---|---|---|
| **1 — Monitoramento de degradação de isolamento** | Estresse dielétrico espira-a-espira; TRVs de VCB; efeito cumulativo de reignições; envelope normativo de suportabilidade; métodos atuais de monitoramento; lacuna metodológica | `01_ETAPA1_monitoramento_degradacao_isolamento.md` (10 seções, 873 l.) + 31 anexos | **Entregue e verificado** [REPO: `docs/research/rul_isolamento/01_ETAPA1_monitoramento_degradacao_isolamento.md`] |
| **2 — Cruzamento dos domínios A × B** | Acoplamento causal (B fixa $\lambda$, A fixa a severidade); acoplamento inverso pelo estado elétrico, magnético e térmico; cadeia térmica que B não modela; acumulador multiestresse; *health-aware load shedding*; snubber como variável de decisão; experimento mínimo de cruzamento | `02_ETAPA2_cruzamento_A_x_B.md` (12 seções, 960 l.) | **Entregue** [REPO: `docs/research/rul_isolamento/02_ETAPA2_cruzamento_A_x_B.md`] |
| **3 — Caso de negócio e arquitetura de entrega** | Parte 1: tradução fenômeno → KPI, custo de indisponibilidade verificado, modelo $E[C]$, objeções, painel executivo, roteiro de entrega. Parte 2: arquitetura do MVP, inventário de arquivos, contratos de dados entre camadas, realização de D1–D7 em código, plano de validação, *roadmap* e riscos | `03_ETAPA3_contexto_c_level.md` (9 seções, 701 l.) + `04_ARQUITETURA_MVP_RUL_OLIVAS.md` (9 seções, 733 l.) | **Entregue em duas partes** [REPO: idem] |
| **Anexo de motor** (fora da numeração de etapas) | Justificativa da decisão por motor EMT dedicado e próprio; MNA e modelos companheiros; CDA; partida em regime permanente; Bergeron e JMarti; VCB dinâmico; *snubber*; validação contra fontes primárias e contra as Listas EEE873; *benchmark* aberto contra A; desempenho e critério de migração para C++ | `05_MOTOR_EMT_DEDICADO.md` (13 seções, 818 l.) + os dois pacotes de código da §3.8 | **Entregue; duas lacunas declaradas** (leitor de `.atp`; *backend* órfão) |

Os insumos das Etapas 2 e 3 residem em `anexos/pesquisa/` (`entrega_trabalho_computacional.md`, `termico_partidas_n1_otimizacao.md` para a Etapa 2; `c_level_demanda_rul.md`, `contexto_industrial_brasil_og.md` para a Etapa 3) e em `anexos/repo/` (pontos de integração). A separação entre etapas é de **redação**, não de coleta. O documento 05 é de natureza distinta dos demais: enquanto 01 a 04 argumentam a partir de texto e de código lido, o 05 documenta **código escrito nesta série**, e por isso traz `arquivo:linha` em cada afirmação e um teste por equação deduzida.

### 1.4 O que a Etapa 1 efetivamente fixou

Quatro resultados estruturais, que as etapas seguintes tomam como dados de entrada e não devem reabrir sem nova evidência:

1. **O estressor é medível em microssegundos; o estado é medível em meses; não existe função de transferência normalizada entre os dois.** Essa assimetria é a lacuna que o módulo endereça [FATO: `01_ETAPA1...md`, §1.3].
2. **A norma de manobra indutiva não impõe teto de sobretensão** — "No limits to the overvoltages are given as the overvoltages are only relevant to the specific application" —, transferindo a coordenação para o projeto da instalação [NORMA: IEC 62271-110:2023, 4.3.1].
3. **O cenário do Documento A é justamente aquele que a IEC 60034-15 ressalva.** A Nota 5 da Tabela 1 adverte que os níveis-padrão "may not be adequate for special operating conditions (e.g. interrupted start …)"; trata-se de ressalva, não de exclusão formal [NORMA: IEC 60034-15:2009, Tabela 1, Nota 5 — transcrição literal reconferida em preview oficial]. A equivalência entre "interrupted start" e a "intempestive interruption of a motor start" de A é interpretação do estudo [INFERÊNCIA].
4. **As três normas de diagnóstico negam explicitamente predizer tempo até falha** a partir de seus indicadores [NORMA: IEC 60034-27-2:2023, Introdução; IEC 60034-27-3:2015, Introdução; IEC 60034-27-4:2018, Introdução]. Logo, o módulo não compete com norma: ocupa espaço que a norma declara vago.

---

## 2. Método

### 2.1 Corpus

O corpus tem quatro camadas, com estatutos epistêmicos distintos e **não intercambiáveis**. A distinção que mais importa é a das duas últimas: uma é literatura **publicada e revisada por pares**, que pode fundamentar um modelo; a outra é **trabalho do próprio autor**, que fixa notação e serve de caso de referência, mas não é fonte de autoridade sobre si mesma.

| Camada | Itens | Estatuto | Onde está o produto |
|---|---|---|---|
| **Documentos do autor (em revisão)** | A (snubber ativo a tiristor, ATP/EMTP, VCB dinâmico) e B (load shedding seletivo sob N-1, OpenDSS, NSGA-II/III) | Submissões em revisão duplo-cega, **sem autoria divulgada**; texto integral lido | `anexos/fichamentos_AB/` (2 arq.) |
| **Literatura de apoio** | 13 artigos de RUL/PHM, prognóstico de isolamento, IGBT, mancais, séries temporais e revisões | Publicados; texto integral lido para todos; tabelas/figuras nem sempre recuperadas pela extração | `anexos/fichamentos/` (13 arq.) |
| **Fontes primárias de EMT** | 5 artigos clássicos de formulação numérica (tabela abaixo) | **Publicados e canônicos**; texto integral acessado; sustentam dedução de modelo, com número de equação e página | `05_MOTOR_EMT_DEDICADO.md`, §§2–5 e docstrings de `app/simulation/emt/` |
| **Trabalhos do autor em EEE873** | Listas 01 e 02 da disciplina EEE873 — Análise de Redes Elétricas no Domínio do Tempo (PPGEE/UFMG, prof. Alberto de Conti) | **Não publicados**; texto integral disponível. Fixam a **notação** do projeto e são **caso de referência já validado contra o ATP** — nunca fonte de autoridade sobre a física | `05_MOTOR_EMT_DEDICADO.md`, §8; `tests/test_emt_referencia_eee873.py` (35 testes) |

Composição da camada de fontes primárias de EMT, toda ela com texto integral acessado e citada no formato `[FONTE: autor ano, p. N, eq. (N)]`:

| Fonte | O que sustenta no código |
|---|---|
| DOMMEL, 1969 (PAS-88, n. 4) | Modelos companheiros de $L$ e $C$ pela regra trapezoidal; equivalente de Bergeron e perdas $R/4$, $R/2$, $R/4$; condições iniciais de linha (Apêndice I) |
| DOMMEL, 1971 (PAS-90, n. 6) | Elementos não lineares e variantes no tempo — hoje **fora** do kernel; base do item 6 do trabalho futuro |
| HO; RUEHLI; BRENNAN, 1975 (CAS-22, n. 6) | Formulação nodal aumentada (MNA): estampa de fonte de tensão e de chave por variável de corrente adicional |
| LIN; MARTÍ, 1990 (PWRS-5, n. 2) | Procedimento de amortecimento crítico (CDA): dois meios-passos de Euler regressivo na descontinuidade |
| MAHSEREDJIAN et al., 2007 (EPSR 77) | Enquadramento de arquitetura de solver moderno; motivação da separação entre montagem, fatoração e controle |

Camada complementar, não bibliográfica: **normas e guias** (IEC, IEEE, ISO, NEMA, ABNT, CIGRE), acessados por preview oficial, amostra de norma ou página do organismo, sempre com a cláusula/tabela identificada; e o **próprio repositório**, lido como fonte de fato verificável.

**Regra de uso das Listas EEE873**, que decorre do estatuto declarado: as convenções que elas fixam — $G_L = \Delta t/(2L)$, $G_C = 2C/\Delta t$, $I_L(t) = 2G_L v_L(t) + I_L(t-\Delta t)$, semeadura em regime permanente com $I_L(0) = i_L(0) + G_L v_L(0)$ e $I_C(0) = -[G_C v_C(0) + i_C(0)]$, fasor de amplitude com cosseno como referência, critério de abertura por margem $I_{mar}$ — são adotadas **por serem as do autor**, e as tolerâncias que elas publicam (§8) são **alvo de regressão**, não evidência independente. A evidência independente, nesses casos, é o ATP, contra o qual as listas já foram confrontadas: regime permanente × solução fasorial 1,39 × 10⁻¹⁰ V; rotina própria × ATP 4,27 × 10⁻⁴ V em tensão (8,5 × 10⁻⁵ %) e 4,83 × 10⁻⁷ A em corrente; pico da TRV de 504,292 V coincidente entre a rotina própria e o ATP [LISTA: 02, Tabela 3, $\Delta t = 1$ µs, $t_{max} = 100$ ms].

Composição da camada de apoio:

| # | Fichamento | Eixo temático |
|---|---|---|
| 01 | `01_liu2025_rul_overview.md` | Panorama e cienciometria de RUL |
| 02 | `02_jensen2018_stator_insulation_ekf.md` | **Prognóstico online de isolamento de estator com EKF** (âncora principal) |
| 03 | `03_review_rul_electrical_drives.md` | Revisão de prognóstico em acionamentos e máquinas |
| 04 | `04_sonnenfeld_nasa_aging_platform.md` | Plataforma de envelhecimento acelerado (NASA Ames) |
| 05 | `05_ahsan_igbt_nn_anfis.md` | RUL de IGBT por NN/ANFIS |
| 06 | `06_yu2014_hybrid_mode_dependent.md` | Prognóstico baseado em modelo com degradação dependente do modo |
| 07 | `07_vichare_pecht2006_phm_electronics.md` | **PHM de eletrônicos; monitoramento do ciclo de vida (LCM)** |
| 08 | `08_yin_igbt_cnn_bilstm_attention.md` | RUL de IGBT com CNN-BiLSTM-Attention |
| 09 | `09_strangas2013_prognosis_mitigation.md` | **Efeito de prognóstico + mitigação sobre confiabilidade** |
| 10 | `10_siaminamini_lstm_bilstm.md` | LSTM/BiLSTM em séries temporais (método, não degradação) |
| 11 | `11_muetze_strangas2016_bearings.md` | Vida de mancais em acionamentos inversorizados |
| 12 | `12_ma2015_mission_profile_igbt.md` | **Perfil de missão → carga → Miner** (esqueleto arquitetural) |
| 13 | `13_wu2024_dl_rul_survey.md` | Survey de RUL por aprendizado profundo |

Advertência de corpus, registrada nos próprios fichamentos: os artigos 05, 08 e 12 tratam de **mecanismo termomecânico em semicondutores**, não de degradação dielétrica; o artigo 10 **não trata de degradação, confiabilidade, PHM ou RUL** [FATO: `anexos/fichamentos/10_siaminamini_lstm_bilstm.md`, advertência inicial]. Eles entram como **catálogo de método**, jamais como evidência física sobre isolamento.

### 2.2 Fichamento estruturado

Cada fichamento segue protocolo fixo, o que torna os 15 documentos comparáveis entre si:

1. referência completa em ABNT, com DOI/ISBN e marcação explícita de campo ausente como `[INSERIR CITAÇÃO]`;
2. paginação declarada — "p. N" refere-se aos marcadores `===== PAGE N =====` do texto extraído, com a correspondência à paginação impressa dita quando diferem (p. ex., artigo 09: p. 1 = p. 3519);
3. objeto, método, dados e resultados numéricos transcritos com página;
4. equações numeradas do artigo, transcritas com variáveis e unidades;
5. **seção de ausências** ("o que o artigo não afirma"), rotulada `[FATO por omissão]` e obtida por busca no texto integral — é o item que sustenta as afirmações negativas do estudo;
6. ganchos para o módulo de RUL e variáveis reutilizáveis;
7. limitações e riscos de sobre-interpretação.

Nos fichamentos A e B, acrescenta-se a **leitura de figura** como categoria própria: valores lidos em imagem nativa ampliada (p. ex., rótulos "0,5 km", "185 mm²", "240 mm²" da Fig. 2 de A) são sempre marcados como leitura de figura e distinguidos do texto, porque o artigo não os enuncia [FATO: `anexos/fichamentos_AB/A_snubber_tiristor_vcb.md`, §3.2 e convenções].

### 2.3 Pesquisa normativa e web com fontes primárias

Regras aplicadas em `anexos/pesquisa/` (9 arquivos), verificáveis nos cabeçalhos de cada um:

- **Somente URLs efetivamente acessadas** são listadas; buscas que não resultaram em leitura não viram referência.
- **Bloqueios são registrados**, não silenciados: páginas de editoras (IEEE Xplore, IET, Wiley, Elsevier, Springer) retornaram HTTP 403 e, nesses casos, apenas metadados e resumos via OpenAlex/Crossref/Semantic Scholar foram usados, com o grau de confiança explicitado [FATO: `anexos/pesquisa/espira_a_espira_reignicoes_cumulativas.md`, cabeçalho].
- **Normas por fonte primária ou amostra oficial**: preview iTeh, IEC Webstore, IEEE SA, PDFs de organismos; cada afirmação normativa cita cláusula, tabela ou anexo, nunca a norma como um todo.
- **Marca de verificação por fato**: nas pesquisas normativas, cada item recebe "confirmado por fonte" (texto lido) ou "não verificado" (fonte secundária ou página bloqueada) [FATO: `anexos/pesquisa/normas_monitoramento_isolamento.md`, cabeçalho].
- **Orçamento de busca declarado**: uma das pesquisas registra esgotamento do orçamento de consultas e lista, em anexo próprio, as URLs tentadas e bloqueadas, que **não** são usadas como evidência [FATO: `anexos/pesquisa/termico_partidas_n1_otimizacao.md`, cabeçalho].

### 2.4 Mapeamento do repositório

Cinco áreas do Olivas Power System Studio foram lidas e mapeadas em `anexos/repo/`, com a regra de que toda afirmação sobre o código traz `[REPO: caminho:linha]` e de que **nada foi modificado** (árvore de trabalho limpa declarada em cada mapa). O objetivo é identificar onde um módulo de prognóstico se encaixa **sem reescrever o existente**: a cadeia VCB/VCB3 → MODEL de reignição → snubber (extração de $V_{pk}$, dv/dt, contagem de reignições, energia), a cadeia de simulação e análise de transitórios, o fluxo de partida/reaceleração de motores, a infraestrutura de confiabilidade e Monte Carlo (onde a saída distribucional de RUL se aloja) e as convenções de auditoria, GUI e documentação (onde o módulo precisa se conformar).

### 2.5 Cruzamento A × B × literatura × repositório

Dois documentos de cruzamento consolidam o acervo em uma matriz **estressor × indicador × modelo**: `anexos/cruzamento/cruzamento_A_snubber_vcb.md` transforma os números de A em perfil de estresse por evento e enumera acumuladores candidatos (D1–D9); `anexos/cruzamento/cruzamento_B_load_shedding_n1.md` conecta B ao consumo de vida, tratando a decisão de load shedding como variável que altera a **frequência e a severidade** das manobras — isto é, a taxa $\lambda_m$ do acumulador. A complementaridade entre A e B é a tese operacional do módulo: **A dá a dose por evento; B dá a taxa de eventos**; nenhum dos dois, isoladamente, fecha o cálculo de vida.

### 2.6 Verificação adversarial por lentes independentes e reparo

Os fichamentos A e B foram submetidos a verificação adversarial: um segundo passe, com lentes independentes do passe de redação, releu o texto-fonte e classificou cada afirmação numerada em **confirmada**, **refutada** (contradiz o texto-fonte) ou **não sustentada** (não localizável no texto-fonte, ainda que plausível). O veredicto foi persistido em JSON.

| Documento | Afirmações refutadas | Afirmações não sustentadas | Estado do reparo |
|---|---|---|---|
| A (snubber/VCB) | 1 — a alegação de que "a sigla RUL aparece uma vez (p. 2)" | 3 — seção do cabo fonte→VCB (185 mm²); leitura da Nota 5 como "exclusão"; posição do snubber a montante do cabo | Passe automático de reparo **não concluiu**; correções aplicadas e presentes na versão final |
| B (load shedding N-1) | 0 | 2 — ausência de discussão do afundamento de 0,85 pu sobre motores em operação; afirmação de que g3 nunca fica ativa | Passe automático de reparo **não concluiu**; itens reescritos como interpretação, não como fato |

Verificação do reparo, feita nesta sessão por leitura da versão publicada: o item refutado foi reescrito para "a expressão *remaining useful life* ocorre uma única vez, por extenso, na p. 2 (Seção III-B) …; a sigla 'RUL' não aparece em nenhuma parte do texto" [REPO: `anexos/fichamentos_AB/A_snubber_tiristor_vcb.md:324`]; a Nota 5 passou a ser descrita como "ressalva ('may not be adequate'), não uma exclusão formal" [REPO: `anexos/fichamentos_AB/A_snubber_tiristor_vcb.md:271`]; e a seção do cabo passou a constar como leitura de figura reconferida em recorte ampliado, com registro explícito de que "o texto do artigo não contém nenhum desses valores" [REPO: `anexos/fichamentos_AB/A_snubber_tiristor_vcb.md:62`]. **Consequência prática**: afirmações originárias de leitura de figura ou de interpretação normativa não podem migrar para texto acadêmico sem a ressalva de origem que as acompanha no anexo.

### 2.7 Sistema de rótulos de evidência

Regra "zero suposição": **toda** afirmação factual do estudo carrega um rótulo. O rótulo não é ornamento — ele define o teste de falseabilidade aplicável e o uso permitido da afirmação.

| Rótulo | Significado | Como se verifica / falseia | Uso permitido |
|---|---|---|---|
| `[FATO: doc A/B, p. N]` | Enunciado presente no texto do Documento A ou B, na página indicada | Reler a página no `.txt` de origem | Livre no estudo; em publicação, sem citação nominal enquanto durar a revisão cega |
| `[FATO: artigo NN, p. N]` | Enunciado presente no artigo de apoio NN do corpus | Reler a página no fichamento e no texto extraído | Livre, com citação ABNT |
| `[FATO por omissão]` | **Ausência** verificada por busca no texto integral | Repetir a busca no texto integral | Sustenta afirmações negativas ("A não quantifica X"); nunca sustenta afirmação positiva |
| `[FONTE: autor ano, p. N, eq. (N)]` | Enunciado, equação ou dedução de **fonte primária publicada** de EMT (as cinco da §2.1) | Reler a equação na página indicada do texto integral | Livre, com citação completa; é o único rótulo que fundamenta a dedução de um modelo numérico |
| `[LISTA: 01/02, seção]` | Convenção, resultado ou tolerância dos **trabalhos do próprio autor** em EEE873 | Reler a seção da lista; e, quando for número, reconferir contra o ATP nela reportado | Fixa notação e serve de **alvo de regressão**; **não** é evidência independente sobre a física, porque é do próprio autor |
| `[NORMA: id, tabela/cláusula]` | Texto ou requisito de norma, com cláusula/tabela identificada | Conferir a cláusula na amostra ou no exemplar | Livre, desde que a edição seja citada; ver §4.2 sobre edições não lidas |
| `[LITERATURA: ref + URL]` | Fonte externa acessada; distingue-se texto integral lido de resumo/metadado | Abrir a URL registrada | Livre; resumo/metadado **não** sustenta valor numérico |
| `[REPO: caminho:linha]` | Conteúdo do repositório lido diretamente | `sed -n 'N,Mp' caminho` no commit indicado | Livre; depende do commit, que deve ser citado quando relevante |
| `[CÁLCULO PRÓPRIO: fórmula]` | Aritmética explícita sobre dados rotulados | Refazer a conta com a fórmula transcrita | Livre, desde que as entradas sejam rotuladas |
| `[INFERÊNCIA FÍSICA: derivação]` | Dedução declarada a partir de física ou de fatos rotulados | Auditar a derivação passo a passo | Permitida em discussão; **não** é resultado |
| `[INFERÊNCIA]` | Juízo interpretativo do redator (p. ex. equivalência de termos normativos) | Confrontar com o texto-fonte | Permitida se explicitada como interpretação |
| `[HIPÓTESE]` | Conjectura ainda não verificada, a testar | Definir o experimento ou a medição que a decide | Só como premissa declarada; nunca como fundamento de conclusão |
| `[INSERIR CITAÇÃO]` | Lacuna bibliográfica assumida: referência ou valor não verificado em fonte primária | Obter a fonte primária | Bloqueia o uso do valor em texto acadêmico até resolução |

**Precedência**: quando a mesma afirmação admite dois rótulos, prevalece o **mais fraco** (por exemplo, valor lido em figura e não enunciado no texto é `[FATO: doc A, Fig. N — leitura de figura]`, e não `[FATO: doc A, p. N]`). Nenhuma referência é inventada: quando a fonte falta, o marcador `[INSERIR CITAÇÃO]` permanece no texto.

### 2.8 Equações-âncora e convenção de unidades

O estudo é organizado em torno de quatro equações, desenvolvidas na Etapa 1 (§5.4) e retomadas na Etapa 2. Reproduzem-se aqui apenas como âncoras de navegação, com definição de variáveis e unidades.

**(E1) Recuperação dielétrica do VCB (RRDS parabólica)** — o gerador de reignições no modelo de A:

$$
V_{wth}(t) \;=\; A\,t \;+\; B\,t^{2},
$$

com $V_{wth}$ [kV] a suportabilidade do *gap* após a extinção do arco, $t$ [ms] o tempo decorrido desde a extinção, $A = 0{,}801$ kV·ms⁻¹ e $B = 1{,}226$ kV·ms⁻² [FATO: doc A, p. 3, IV-B e Tabela II]. Parâmetros associados do mesmo modelo: nível de chopping $I_{ch} = 1$ a $2$ A; di/dt crítico de 5 a 15 A/µs; *stagger* de 14 a 25 ms entre polos; passo de integração de 1 µs; janela de 45 ms [FATO: doc A, Tabela II, p. 3].

**(E2) Lei de potência inversa com limiar** — a curva de vida elétrica:

$$
N(V) \;=\; N_0\left(\frac{V}{V_{ref}}\right)^{-n},
\qquad
L \;=\; C\,(E-E_0)^{-m},
$$

com $N$ [impulsos] o número de eventos até ruptura, $V$ [V] a tensão do impulso, $V_{ref}$ [V] e $N_0$ [impulsos] o par de referência, $n$ [adimensional] o coeficiente de resistência à tensão (VEC), $E$ [kV/mm] o campo, $E_0$ [kV/mm] o campo-limiar e $C$, $m$ constantes do material [LITERATURA: Feilat, IntechOpen 2018, eq. (21), DOI 10.5772/intechopen.72423; CIGRE WG D1.43, TB 703, p. 29]. **Nenhum valor de $n$ para mica-epóxi pré-formada de MT sob impulsos de VCB foi localizado** — [INSERIR CITAÇÃO].

**(E3) Dano linear cumulativo (regra de Miner)**:

$$
D \;=\; \sum_i \frac{n_i}{N_i}, \qquad \text{falha em } D = 1,
\qquad\text{forma contínua: } \mathrm{LF} \;=\; \int_{t_1}^{t_2}\frac{\mathrm{d}t}{L(\theta(t))},
$$

com $n_i$ [eventos] o número de eventos aplicados no nível de estresse $i$, $N_i$ [eventos] o número suportável nesse nível, $D$ [adimensional] o dano acumulado, $\mathrm{LF}$ [adimensional] a fração de vida térmica e $\theta$ [°C] a temperatura do enrolamento [LITERATURA: ReliaSoft HotWire 116; Theofanous et al., *Energies* 18:6087, 2025].

**(E4) RUL como saída distribucional** — a forma-alvo do módulo:

$$
\widehat{\mathrm{RUL}}_N \;=\; \frac{1 - D(t)}{\mathbb{E}[\Delta D_m]},
\qquad
\widehat{\mathrm{RUL}}_t \;=\; \frac{\widehat{\mathrm{RUL}}_N}{\lambda_m},
$$

com $\Delta D_m$ [adimensional] o dano de uma manobra $m$, $\widehat{\mathrm{RUL}}_N$ [manobras] a vida remanescente em número de eventos, $\lambda_m$ [manobras/ano] a taxa de manobras severas e $\widehat{\mathrm{RUL}}_t$ [anos] a vida remanescente em tempo. A saída deve ser **distribuição** (percentis B10/B50) por Monte Carlo, com nível de confiança explícito [NORMA: ISO 13381-1:2015, 3.3, 3.9]. É por $\lambda_m$ que o Documento B entra no cálculo.

**Convenção de unidades do estudo**: tensões em kV (picos de TRV) ou V (formulações genéricas); taxas de crescimento em kV/µs; tempos de frente em µs; campo em kV/mm; temperatura em °C nas expressões de engenharia e em K nas expressões de Arrhenius; energia em J. Toda grandeza normalizada declara a base (p. u. de $\sqrt{2}\,U_n/\sqrt{3}$ quando fase-terra).

---

## 3. Mapa dos documentos e dos anexos

### 3.1 Árvore

```
docs/research/rul_isolamento/
├── 00_INDICE.md                                       (este arquivo)
├── 01_ETAPA1_monitoramento_degradacao_isolamento.md   (Etapa 1 — entregue,  873 l.)
├── 02_ETAPA2_cruzamento_A_x_B.md                      (Etapa 2 — entregue,  960 l.)
├── 03_ETAPA3_contexto_c_level.md                      (Etapa 3, parte 1,    701 l.)
├── 04_ARQUITETURA_MVP_RUL_OLIVAS.md                   (Etapa 3, parte 2,    733 l.)
├── 05_MOTOR_EMT_DEDICADO.md                           (motor EMT próprio,   818 l.)
├── 06_CASO_BASE_ATP_ESPECIFICACAO.md                  (caso base extraído do .atp)
├── 07_AUDITORIA_DO_CASO_ATP.md                        (auditoria do caso e do MODEL)
├── 08_VARREDURA_ESTATISTICA_VCB.md                    (varredura Monte Carlo do VCB)
├── 09_PARA_RAIOS_E_CRITERIO_DE_ACEITACAO.md           (compensação, MOA e aceitação)
└── anexos/
    ├── fichamentos/        13 arquivos — literatura de apoio
    ├── fichamentos_AB/      2 arquivos — Documentos A e B do autor
    ├── pesquisa/            9 arquivos — 3 pesquisas dirigidas + 6 pesquisas web
    ├── repo/                5 arquivos — mapas do código
    ├── cruzamento/          2 arquivos — A × B × literatura × repositório
    ├── dados/               4 arquivos — resultados brutos das varreduras (JSON)
    └── verdicts/            2 arquivos — veredictos da verificação adversarial (JSON)
```

Fora deste diretório, e parte integrante da entrega, os dois pacotes de código detalhados na §3.8:

```
app/simulation/emt/          11 arquivos,  9 915 l. — motor de transitórios dedicado
app/postprocessor/prognosis/  5 arquivos,  3 240 l. — perfil de estresse, dano, RUL, AHI
tests/test_emt_*.py           5 arquivos            — 273 testes do motor
tests/test_pp_prognosis_core.py                     — 176 testes do prognóstico
```

Todos os caminhos de documento citados adiante são **relativos a `docs/research/rul_isolamento/`**; os caminhos de código são **relativos à raiz do repositório**. Os anexos são referenciados, nunca transcritos: o conteúdo técnico vive neles.

### 3.2 Documentos principais

| Caminho relativo | Conteúdo | Extensão |
|---|---|---|
| `01_ETAPA1_monitoramento_degradacao_isolamento.md` | 10 seções: enquadramento do modo de falha; física do estresse espira-a-espira; perfil de estresse do Documento A (Tabela III, normalizações, tempo de frente equivalente); referencial normativo de suportabilidade; efeito cumulativo de reignições (D1–D7 + exemplo numérico); correção conceitual sobre "redução do BIL"; métodos atuais de monitoramento; lacuna metodológica e proposta de contagem de estresse; limitações; referências | 873 linhas |
| `02_ETAPA2_cruzamento_A_x_B.md` | 12 seções: os dois domínios lado a lado; acoplamento causal (B fixa $\lambda$, A fixa a severidade); acoplamento inverso pelo estado no instante da manobra; cadeia térmica derivada que B não modela; sinergia multiestresse; *health-aware load shedding*; snubber como variável de decisão; mapeamento dos artigos por elo; o que o Olivas já entrega; experimento mínimo de cruzamento; limitações; referências | 960 linhas |
| `03_ETAPA3_contexto_c_level.md` | 9 seções (Etapa 3, parte 1): tabela-mestra fenômeno → KPI; custo de indisponibilidade com ressalva por levantamento; modelo de decisão econômica $E[C]$ e valor de opção; argumentos e objeções; painel executivo e o que ele **não** deve exibir; narrativa de valor de A e B; roteiro de entrega do trabalho computacional; riscos; referências | 701 linhas |
| `04_ARQUITETURA_MVP_RUL_OLIVAS.md` | 9 seções (Etapa 3, parte 2): fluxo de dados do gêmeo digital em camadas; inventário de arquivos (criado, a criar, a alterar); contratos de dados entre camadas; realização de D1–D7 e (5.1)–(5.2) no código; plano de validação; *roadmap* por versão; riscos técnicos; limitações e o que **não** foi implementado; referências | 733 linhas |
| `05_MOTOR_EMT_DEDICADO.md` | 13 seções: por que um motor dedicado e próprio (F1–F3) e o `.atp` como fonte da verdade; MNA e modelos companheiros; CDA; partida em regime permanente; Bergeron e JMarti lado a lado, com o viés de $T_1$ medido; VCB dinâmico; *snubber* e a lacuna do nível de *breakover*; validação (fontes primárias + regressão dígito a dígito contra as Listas EEE873); *benchmark* aberto contra o Documento A; desempenho medido e critério objetivo de migração para C++; integração com o prognóstico e papel do `.atp`; 41 limitações catalogadas e trabalho futuro; referências | 818 linhas |


Os quatro documentos acrescentados depois do fechamento das etapas — `06` a `09` — formam a
linha de **confrontação com a literatura**, e não com os Documentos A e B: eles substituem a
validação contra a Tabela III de A, que seria circular, pela confrontação com as faixas
publicadas e com os critérios de validade internos do motor.

| Caminho relativo | Conteúdo | Extensão |
|---|---|---|
| `06_CASO_BASE_ATP_ESPECIFICACAO.md` | Especificação do caso base extraída do `.atp`: topologia, cartões, parâmetros do disjuntor e do amortecedor, com a listagem do ATP como fonte da solução de regime | 94 linhas |
| `07_AUDITORIA_DO_CASO_ATP.md` | Ancoragem do regime permanente por equivalente de Thévenin; decodificação da matriz do transformador; defeito corrigido no motor dedicado; **dois defeitos no `MODEL` do arquivo** que tornam a escalada impossível; confronto com a Tabela III; achados da listagem; cinco correções recomendadas | 193 linhas |
| `08_VARREDURA_ESTATISTICA_VCB.md` | Varredura Monte Carlo com o **tempo de arco** como variável de controle e o disjuntor tratado como **tripolar**; três cenários (literatura, medido, caso de referência) com e sem amortecedor, 900 realizações; supressão da escalada pelo amortecedor e seu custo em regime; **delimitação do domínio de validade da cauda de escalada**, com o mecanismo diagnosticado e o caminho de correção | 262 linhas |
| `09_PARA_RAIOS_E_CRITERIO_DE_ACEITACAO.md` | Método de **compensação** de Dommel 1971 verificado contra soluções analíticas; **para-raios ZnO** com a curva publicada por Vollet, escalada para 4,16 kV e confrontada com o envelope da IEC 60034-15; a cauda de escalada volta à faixa publicada (77,5 → 3,45 pu; 128 → 6 reignições); **critério de aceitação de Wong** atendido quanto à forma — dependência com a RRDS passa a ter máximo interior —, com a localização discutida; reconciliação de unidades da lei de extinção; **disrupção da isolação** no envelope da IEC 60034-15 como evento terminal, com as duas ressalvas de convergência medidas | 291 linhas |

### 3.3 `anexos/fichamentos/` — literatura de apoio (13)

`01_liu2025_rul_overview.md` · `02_jensen2018_stator_insulation_ekf.md` · `03_review_rul_electrical_drives.md` · `04_sonnenfeld_nasa_aging_platform.md` · `05_ahsan_igbt_nn_anfis.md` · `06_yu2014_hybrid_mode_dependent.md` · `07_vichare_pecht2006_phm_electronics.md` · `08_yin_igbt_cnn_bilstm_attention.md` · `09_strangas2013_prognosis_mitigation.md` · `10_siaminamini_lstm_bilstm.md` · `11_muetze_strangas2016_bearings.md` · `12_ma2015_mission_profile_igbt.md` · `13_wu2024_dl_rul_survey.md`

Eixos temáticos e advertências de aplicabilidade na tabela da §2.1. Âncoras diretas do módulo: 02 (prognóstico de isolamento), 07 (LCM/PHM), 09 (prognóstico + mitigação), 12 (perfil de missão → Miner), 13 (catálogo de arquiteturas).

### 3.4 `anexos/fichamentos_AB/` — Documentos do autor (2)

| Caminho relativo | Conteúdo | Extensão |
|---|---|---|
| `fichamentos_AB/A_snubber_tiristor_vcb.md` | Documento A: sistema e cenário (motor 1250 kW / 4,16 kV; interrupção intempestiva de partida com $I_p/I_n = 6{,}5$); parâmetros do VCB (Tabela II); Tabela III completa (com e sem snubber); leituras das Figs. 2–4 marcadas como tal; §8 com a lista de ausências; §10 com ganchos para RUL | 423 linhas |
| `fichamentos_AB/B_load_shedding_n1_nsga.md` | Documento B: load shedding seletivo sob N-1; OpenDSS; $V_{inrush} = 0{,}755$ p.u. sem shedding; restrições $g_1 \ge 0{,}85$ p.u., $g_2 \le 1{,}08$ p.u., $g_3 = S/S_{AF}$; NSGA-II/III; surrogate ridge com $R^2 > 0{,}999$; ausências declaradas | 473 linhas |

### 3.5 `anexos/pesquisa/` — pesquisas dirigidas e web (9)

| Caminho relativo | Foco |
|---|---|
| `pesquisa/iec60034_15_bil_suportabilidade.md` | IEC 60034-15 (2009/2025), IEEE 522, IEC 60071-1, IEC 60034-18-41/-42; confronto com os números de A |
| `pesquisa/espira_a_espira_reignicoes_cumulativas.md` | Distribuição espira-a-espira, contagem de reignições, modelos de dano |
| `pesquisa/metodos_monitoramento_estator_atual.md` | Métodos online/offline, ISO 13374-1/13381-1, percentis de DP |
| `pesquisa/fisica_surtos_vcb_isolamento.md` | Chopping, escalonamento de tensão, reignição; modelos de vida |
| `pesquisa/normas_monitoramento_isolamento.md` | Edições normativas, ISO 55000/55001, CIGRE C4.76 e JWG A3.53 |
| `pesquisa/termico_partidas_n1_otimizacao.md` | Estresse térmico de partidas e afundamentos sob N-1; envelhecimento térmico; otimização com prognóstico |
| `pesquisa/c_level_demanda_rul.md` | Demanda executiva por RUL/PdM; KPIs; barreiras; custo de parada em O&G |
| `pesquisa/contexto_industrial_brasil_og.md` | Programas de confiabilidade no Brasil; população de motores MT; ISO 55001; Manutenção 4.0 |
| `pesquisa/entrega_trabalho_computacional.md` | ISO 13374/OSA-CBM/MIMOSA; métricas de prognóstico; incerteza; XAI; MLOps; reprodutibilidade; painel executivo e Asset Health Index |

Os três primeiros são as **pesquisas dirigidas da Etapa 1**; os seis restantes são pesquisas web multi-fonte, das quais quatro alimentam prioritariamente as Etapas 2 e 3.

### 3.6 `anexos/repo/` — mapas do código (5)

| Caminho relativo | Área mapeada | Papel para o módulo |
|---|---|---|
| `repo/vcb_reignicao_snubber.md` | VCB/VCB3 → MODEL de reignição → snubber | Onde extrair $V_{pk}$, dv/dt, contagem de reignições e energia |
| `repo/trt_transitorios_simulacao.md` | Cadeia de simulação e análise de transitórios | Onde o descritor de surto é calculado e persistido |
| `repo/motor_partida_reaccel_fluxo.md` | Partida, reaceleração e fluxo | Onde a manobra severa é definida e contada |
| `repo/confiabilidade_eval_montecarlo.md` | Confiabilidade e Monte Carlo | Onde a saída distribucional de RUL se aloja |
| `repo/convencoes_auditoria_gui_docs.md` | Convenções de auditoria, GUI e documentação | A que o módulo deve se conformar para ser aceito no produto |

### 3.7 `anexos/cruzamento/` — cruzamentos (2)

| Caminho relativo | Conteúdo |
|---|---|
| `cruzamento/cruzamento_A_snubber_vcb.md` | Perfil de estresse por evento a partir de A; acumuladores D1–D9; matriz estressor × indicador × modelo; inventário de pontos de integração |
| `cruzamento/cruzamento_B_load_shedding_n1.md` | Documento B como fonte da taxa $\lambda_m$ e da severidade das manobras; consumo de vida sob decisões de shedding; ausências de B |

### 3.8 Pacotes de código — o produto executável da série

Diferentemente dos anexos, que são texto, esta é a parte da entrega que **executa e é testada**. Caminhos relativos à raiz do repositório; contagens medidas nesta sessão [CÁLCULO PRÓPRIO: `wc -l` e `pytest --collect-only`].

**`app/simulation/emt/` — motor de transitórios eletromagnéticos dedicado (11 arquivos, 9 915 linhas)**

| Arquivo | Linhas | Papel |
|---|---|---|
| `__init__.py` | 457 | Fachada (77 nomes em `__all__`), decisão do autor gravada no cabeçalho, `KNOWN_LIMITATIONS` (19 chaves alcançáveis) |
| `components.py` | 1 259 | `Resistor`, `Inductor`, `Capacitor`, `VoltageSource`, `Switch`, `CoupledRL` — modelos companheiros e estampas MNA |
| `circuit.py` | 1 207 | Montagem, fatoração LU com cache por topologia, CDA, `Solver`, base de tempo indexada |
| `jmarti.py` | 2 349 | Linha dependente da frequência: ajuste racional por *vector fitting*, fase mínima, atraso, convolução recursiva |
| `vcb.py` | 1 115 | Disjuntor a vácuo dinâmico: corte por margem, recuperação parabólica, reignição, extinção de alta frequência, contagem |
| `steady_state.py` | 810 | Partida em regime permanente senoidal por solução fasorial |
| `snubber.py` | 684 | SCR antiparalelos com $R_s$: disparo por sobretensão, bloqueio no zero |
| `line.py` | 601 | Linha de Bergeron a parâmetros constantes, com perdas $R/4$, $R/2$, $R/4$ e semeadura de regime |
| `probes.py` | 310 | Sondas e a ponte `to_stress_profile` para o prognóstico |
| `cases/motor_switching.py` + `cases/__init__.py` | 1 068 + 55 | Caso de manobra do motor de 1 250 kW / 4,16 kV do Documento A |

**`app/postprocessor/prognosis/` — núcleo de prognóstico (5 arquivos, 3 240 linhas)**

| Arquivo | Linhas | Papel |
|---|---|---|
| `damage_models.py` | 1 112 | Acumuladores D1–D7 com parâmetros declaradamente livres |
| `stress_profile.py` | 682 | `extract_stress_events` → `StressProfile`: consumidor do vetor de estresse $s_{m,j}$ |
| `health_index.py` | 631 | *Asset Health Index* e semáforo |
| `rul_estimator.py` | 554 | Estimativa de RUL como distribuição (E4) |
| `__init__.py` | 261 | Fachada (33 nomes em `__all__`) |

**Suíte de testes — contagem real**

| Arquivo | Testes | Escopo |
|---|---|---|
| `tests/test_emt_kernel.py` | 94 | Montagem de matriz, soluções analíticas, Bergeron, CDA, cache de fatoração, convergência, sondas, fontes primárias |
| `tests/test_emt_vcb_snubber.py` | 52 | VCB, *snubber*, balanço de energia no corte |
| `tests/test_emt_jmarti.py` | 49 | Ajuste racional, fase mínima, atraso, ondas viajantes, viés de frente |
| `tests/test_emt_steady_state.py` | 43 | Partida fasorial, idempotência, ordem do resíduo, linha semeada |
| `tests/test_emt_referencia_eee873.py` | 35 | **Regressão dígito a dígito contra as Listas 01 e 02**, que já são validadas contra o ATP |
| `tests/test_pp_prognosis_core.py` | 176 | Perfil de estresse, acumuladores, RUL, AHI |
| **Total** | **449** | `449 passed in 62,66 s` nesta sessão |

Dois números merecem registro, porque contradizem contagens ainda presentes em documentos anteriores desta série e prevalece o medido: o pacote de prognóstico tem **3 240** linhas (o documento 04 registra 3 052) e o catálogo de limitações do motor soma **41** chaves, das quais apenas **19** são alcançáveis pela fachada — as de `vcb.py`, `snubber.py` e do caso de manobra **não são agregadas**, defeito de laudo já identificado e priorizado [FATO: `05_…md`, §12.1 e §12.4, item 2].

### 3.9 Corpus externo ao repositório

As cinco fontes primárias de EMT e as duas Listas de EEE873 (§2.1) **não estão versionadas neste diretório**: foram acessadas em texto integral durante a redação do documento 05 e são citadas por identidade bibliográfica, não por caminho. A rastreabilidade delas é feita pelo par rótulo + localização interna — `[FONTE: Dommel 1969, p. 389, eq. (4)-(6)]`, `[LISTA: 02, §3.6]` —, verificável por quem tenha o mesmo texto em mãos. As Listas permanecem com **[INSERIR CITAÇÃO]** na forma nominal ABNT, porque dados de autoria e de data não devem ser presumidos [FATO: `05_…md`, §13].

---

## 4. Premissas do usuário e limitações globais

### 4.1 Premissas do usuário

| # | Premissa | Estado | Tratamento adotado |
|---|---|---|---|
| **P1** | "5 a 7 reignições por ciclo" em manobra de VCB | **Não consta do Documento A** [FATO por omissão: doc A, p. 1–5 — verificado por leitura integral]; é premissa do usuário | Tratada como hipótese de dose a medir, nunca como fato de A. Confronto com a literatura: reignições "may be repeated several times (up to 10)" [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, paper 07IPST106, https://www.ipstconf.org/papers/Proc_IPST2007/07IPST106.pdf]. A faixa do usuário é compatível com esse relato, porém **a contagem é dependente do caso** (topologia, momento da abertura, *stagger*, di/dt): o módulo deve **extrair** $n_{r,m}$ do oscilograma, não assumi-lo [HIPÓTESE de projeto: `anexos/fichamentos_AB/A_snubber_tiristor_vcb.md:378`] |
| **P2** | O dano relevante é **espira-a-espira**, por frente rápida | Sustentada por norma e literatura (§1.1) | Adotada como recorte do estudo; a falha de massa e os mancais ficam fora do MVP |
| **P3** | O contexto de aplicação é **O&G** (refinarias, plataformas) | **Hipótese**: nenhum dado de campo de planta específica está no corpus | Usada como cenário de severidade e de valor econômico; toda cifra de custo de parada é rotulada `[LITERATURA]` e nunca atribuída a uma planta |
| **P4** | O módulo deve entregar **RUL com incerteza**, integrável a um Asset Health Index | Compatível com a norma de prognóstico [NORMA: ISO 13381-1:2015, 3.3, 3.9] | Fixada como requisito de saída (E4): distribuição e nível de confiança, não número único |
| **P5** | O snubber ativo de A é **mitigação**, e mitigação altera vida | Sustentada por A quanto à redução do estresse [FATO: doc A, Tabela III, p. 3] e por literatura quanto ao efeito de mitigação sobre confiabilidade [FATO: artigo 09] | O efeito sobre RUL é **conclusão a demonstrar** pelo módulo, não premissa: A não calcula RUL |
| **P6** | **Decisão do autor**: o motor de física é **dedicado e próprio**, em Python, com o laço interno migrável para C++ depois **atrás da mesma API**; o `.atp` permanece **fonte única da verdade** do caso técnico, e o motor o **resolve**, não o substitui como registro | **Decisão, não hipótese**; apoiada em três fatos observáveis do repositório — binário de terceiro obtido por credenciamento e não distribuído, orientação a um caso por execução com E/S por arquivo, e inexistência de qualquer consumidor de `.pl4` —, sendo que a demanda de $10^3$ a $10^4$ execuções é o que a torna necessária [FATO: `05_…md`, §1.1, F1–F3] | Adotada como requisito de arquitetura. **Duas ressalvas de execução, ambas declaradas**: (i) o kernel **não lê `.atp`**, de modo que o caso resolvido e o caso registrado são hoje dois objetos mantidos em sincronia manual — enquanto o leitor `.atp` → `Circuit` não existir, "fonte única da verdade" é intenção de arquitetura, não propriedade do código [FATO: `05_…md`, §11.3]; (ii) o pacote é ***backend* órfão**, condição proibida pelas convenções desde a v3.1.0 [FATO: `05_…md`, §11.4]. Nada se afirma sobre termos de licença do ATP — o texto não foi acessado [FATO por omissão] |
| **P7** | **Decisão do autor sobre modelos de linha**: Bergeron a parâmetros constantes é o **padrão**, e JMarti (dependente da frequência) é **opcional**, selecionado por um único parâmetro, sem tocar circuito, sondas, VCB ou *snubber* | Implementada e medida. O padrão continua `'bergeron'` **para não alterar silenciosamente resultados já publicados** [FATO: `05_…md`, §5.5; REPO: `app/simulation/emt/cases/motor_switching.py:804`] | Consequência **direta sobre o vetor de estresse**, e por isso premissa e não detalhe: o viés dominante entre os dois modelos não é de amplitude, é de **tempo de frente** — o Bergeron sem perdas sobe em um único passo ($T_1 = 0$) qualquer que seja $\Delta t$, contra $T_1 = 1{,}29$ µs do JMarti sobre a mesma frente, com d$v$/d$t$ 12,5 % menor. Logo: $V_{pk}$ e d$v$/d$t$ do Bergeron **sem perdas** são **cota superior** de estresse, nunca estimativa central; a cota superior **não vale** para o Bergeron **com perdas** concentradas, que mede pico menor que o JMarti (97,58 V contra 99,19 V); e o erro de ajuste do JMarti é erro de **modelo**, não reduzido por refino de $\Delta t$ [FATO: `05_…md`, §5.5] |

### 4.2 Limitações globais

| # | Limitação | Origem | Consequência operacional |
|---|---|---|---|
| **L1** | **A não quantifica reignições**: não reporta número de reignições por polo por manobra | [FATO por omissão: doc A, p. 1–5] | A dose por evento não pode ser fechada sem a extração descrita na §5 |
| **L2** | **A não modela o isolamento**: o motor é ramo R–L concentrado | [FATO: doc A, p. 3–4] | A tensão longitudinal entre espiras **não** é resultado de A; qualquer $a(t_f)$ é inferência ou hipótese |
| **L3** | **A não reporta tensão nos terminais do motor**: a Tabela III é TRV **no disjuntor** | [FATO: doc A, p. 3] | Toda comparação com envelope normativo de máquina carrega essa ressalva de grandeza |
| **L4** | **A não define BIL, não calcula RUL e não valida experimentalmente** | [FATO por omissão: doc A, p. 1–5] | "Redução do BIL" é conceito a corrigir (Etapa 1, §6); RUL é contribuição nova, não replicação |
| **L5** | **Passo de integração de 1 µs em A** | [FATO: doc A, Tabela II, p. 3] | Frentes de 0,1–0,2 µs não são resolvidas; as RRRV reportadas são **limites inferiores** do dv/dt real |
| **L6** | **B não modela térmica do motor** | [FATO por omissão: doc B] | O acoplamento térmico do acumulador (E3) precisa de modelo próprio; B fornece apenas tensão e potência |
| **L7** | **Ausência de parâmetros de vida para mica-epóxi de MT** sob impulsos de VCB ($n$, $V_{th}$, $a(t_f)$) | [INSERIR CITAÇÃO] | Os parâmetros de (E2) permanecem livres; a Etapa 2 deve propagar essa incerteza, não arbitrá-la |
| **L8** | **Normas não verificadas estão marcadas**: texto integral da IEEE Std 522 (1992/2004/2023) e Tabela 1 da IEC 60034-15:2025 não lidos; IEC 60034-18-41 Tabela 4 e Fig. 7 não acessadas | Declarado em `01_ETAPA1...md`, §10, lista final | Nenhum desses valores pode ir a texto acadêmico antes de leitura da fonte; permanecem `[INSERIR CITAÇÃO]` |
| **L9** | **Percentuais de falha por componente de Thorsen e Dalva não confirmados em fonte primária** | Páginas IEEE Xplore não renderizaram | Usar apenas números de fontes efetivamente acessadas, com o rótulo da fonte |
| **L10** | **Documentos A e B em revisão duplo-cega, sem autoria** | [FATO: doc A, p. 1; doc B, p. 1] | Citação nominal impossível; referência ABNT permanece com `[INSERIR CITAÇÃO]` até publicação |
| **L11** | **Contexto O&G é hipótese** (P3) | §4.1 | Nenhuma conclusão do estudo pode depender de dado de planta não disponível |
| **L12** | **Bloqueios de acesso a editoras** (HTTP 403) durante a coleta | Cabeçalhos das pesquisas | Resumos e metadados sustentam existência e escopo, **nunca** valores numéricos |
| **L13** | **O motor EMT não lê `.atp` e é *backend* órfão** | [FATO: `05_…md`, §11.3–§11.4] | A premissa P6 só se realiza no código quando o leitor de cartões existir; até lá, toda divergência entre o `.atp` e o caso em Python é possível e não é detectada automaticamente |
| **L14** | **O confronto contra a Tabela III do Documento A não fecha** | [FATO: `05_…md`, §9] | Com os parâmetros publicados de A, nenhum polo alcança a primeira interrupção bem-sucedida; faltam dados de rede que A não publica. Nenhum número de A pode ser apresentado como reproduzido |
| **L15** | **Martí (1982) não acessado**: a formulação do modelo dependente da frequência foi montada a partir de fontes secundárias, com o limite sem perdas conferido contra Dommel 1969 | [FATO: `05_…md`, §5.4] | Números de equação e de página de 1982 permanecem `[INSERIR CITAÇÃO]` no código; a recursão exponencial híbrida é **escolha própria não publicada** e deve ser declarada em laudo |

### 4.3 Regras de uso do acervo em texto acadêmico

1. Afirmação com `[INSERIR CITAÇÃO]` **não** entra em artigo ou tese antes de a fonte primária ser lida.
2. Valor obtido por **leitura de figura** só é citado com a ressalva de origem que o acompanha no anexo.
3. Afirmação negativa sobre A ou B exige rótulo `[FATO por omissão]` e a indicação de que foi verificada por busca no texto integral.
4. Rótulo `[HIPÓTESE]` jamais fundamenta conclusão; aparece somente como premissa declarada, com o teste que a decidiria.
5. Comparação entre TRV do disjuntor e envelope de suportabilidade de máquina traz sempre a ressalva de grandeza (L3).
6. Afirmação rotulada `[LISTA: 01/02]` **não** se apresenta como validação independente: é trabalho do próprio autor. O que valida é o ATP contra o qual a lista já foi confrontada, e é esse confronto que se cita (§2.1).
7. Todo número de $V_{pk}$, d$v$/d$t$ ou $T_1$ produzido pelo motor declara o **modelo de linha** que o gerou, porque o viés entre Bergeron e JMarti é de tempo de frente e altera o dano (P7).

---

## 5. Próximo passo recomendado

O passo que este índice recomendava na sua versão anterior — extrair do modelo ATP a tensão no nó do motor, a contagem de reignições e o tempo de frente — **está cumprido por outro caminho**: as três grandezas são saídas nomeadas do motor próprio, entregues ao acumulador sem arquivo intermediário [FATO: `05_…md`, §11.1–§11.2]. A fila passa a ser esta, por ordem de dependência:

1. **Leitor de cartões `.atp` → `Circuit`.** É o item que converte a premissa P6 de intenção em propriedade do código. Enquanto não existir, o caso resolvido e o caso registrado são dois objetos em sincronia manual (L13) [FATO: `05_…md`, §12.4, item 1].
2. **Agregar `vcb`, `snubber` e o caso de manobra à fachada de `KNOWN_LIMITATIONS`.** Correção de baixo custo e alto impacto: hoje um laudo que enumere as limitações do motor **omite silenciosamente** as do disjuntor a vácuo e as do *snubber* — inclusive as duas que precisam obrigatoriamente aparecer em qualquer laudo do estudo de A [FATO: `05_…md`, §12.1].
3. **Retirar o motor da condição de *backend* órfão** (L13): `Feature`, ação de menu, laudo, i18n e `CHANGELOG`, conforme o Sprint 1 do documento 04 [FATO: `05_…md`, §11.4].
4. **Obter os dados de rede omitidos pelo Documento A** e as tabelas de `CABLE CONSTANTS` do caso ATP — únicos caminhos para fechar o *benchmark* que hoje se reporta como aberto (L14).
5. **Fechar as lacunas normativas de maior impacto** (L8): texto integral da IEEE Std 522 (Fig. 1, envelope tensão × tempo de frente) e Tabela 1 da IEC 60034-15:2025, que definem o denominador do confronto de suportabilidade.
6. **Calibrar os parâmetros livres de (E2)** — que permanecem livres por ausência de fonte (L7) —, com propagação de incerteza declarada, e **não** por arbitramento.

**Sobre a migração para C++**: não é próximo passo. Ela deve ser aberta apenas quando as três condições objetivas do documento 05 forem simultaneamente verdadeiras — orçamento de tempo excedido **depois** de explorado o paralelismo por processo, perfil ainda dominado pelo interpretador, e API congelada pelos 273 testes do motor como contrato de regressão [FATO: `05_…md`, §10.4].

---

## Referências

ABNT. **ABNT NBR 17094-1:2018** — Máquinas elétricas girantes — Parte 1: Motores de indução trifásicos — Requisitos. 3. ed. Rio de Janeiro: ABNT, 2018.

AUTORES OMITIDOS (revisão duplo-cega). **Selective mitigation of vacuum circuit breaker switching overvoltages in medium voltage induction motors using an active thyristor snubber**. Submissão ao SEPOC 2026. 5 p. — **Documento A**. Autoria a confirmar após publicação — [INSERIR CITAÇÃO].

AUTORES OMITIDOS (revisão duplo-cega). **Selective load shedding for the switching of large motors under N-1 contingency: constrained multiobjective optimization with NSGA-II, NSGA-III and regression surrogates**. Submissão ao SEPOC 2026. 6 p. — **Documento B**. Autoria a confirmar após publicação — [INSERIR CITAÇÃO].

AUTOR DESTE REPOSITÓRIO. **Lista de exercícios 01 — EEE873: Análise de Redes Elétricas no Domínio do Tempo** (prof. Alberto de Conti). Programa de Pós-Graduação em Engenharia Elétrica, Universidade Federal de Minas Gerais. Modelos numéricos de indutor e capacitor (trapezoidal e Euler regressiva), solução analítica por Laplace do Exemplo A, solução nodal, ordem de convergência, código MATLAB e arquivo `.atp`. Citada como [LISTA: 01, seção]. Forma nominal ABNT — [INSERIR CITAÇÃO]: dados de autoria e de data não devem ser presumidos.

AUTOR DESTE REPOSITÓRIO. **Lista de exercícios 02 — EEE873: Análise de Redes Elétricas no Domínio do Tempo** (prof. Alberto de Conti). Programa de Pós-Graduação em Engenharia Elétrica, Universidade Federal de Minas Gerais. Análise nodal modificada e modelagem de chaves; Questão 1 (curto-circuito na carga de circuito RL); Questão 2 (abertura de disjuntor a vácuo alimentando reator), com as Tabelas 1 a 4 e a comparação contra o ATP. Citada como [LISTA: 02, seção]. Forma nominal ABNT — [INSERIR CITAÇÃO]: idem.

CIGRE. **Technical Brochure 703 — Insulation degradation under fast, repetitive voltage pulses**. WG D1.43. Paris: CIGRE, 2017. Cópia consultada: https://cigre.cz/dokumenty_komise/d1/WG%20D1.43_TB_Final.pdf. Acesso em: 2 set. 2026.

DOMMEL, H. W. Digital computer solution of electromagnetic transients in single- and multiphase networks. **IEEE Transactions on Power Apparatus and Systems**, v. PAS-88, n. 4, p. 388–399, abr. 1969. — Fonte primária; texto integral acessado.

DOMMEL, H. W. Nonlinear and time-varying elements in digital simulation of electromagnetic transients. **IEEE Transactions on Power Apparatus and Systems**, v. PAS-90, n. 6, p. 2561–2567, nov./dez. 1971. — Fonte primária; texto integral acessado.

FEILAT, E. A. Lifetime assessment of electrical insulation. In: **Electric Field**. Londres: IntechOpen, 2018. DOI 10.5772/intechopen.72423. Disponível em: https://cdn.intechopen.com/pdfs/58128.pdf. Acesso em: 2 set. 2026.

HO, C.-W.; RUEHLI, A. E.; BRENNAN, P. A. The modified nodal approach to network analysis. **IEEE Transactions on Circuits and Systems**, v. CAS-22, n. 6, p. 504–509, jun. 1975. — Fonte primária; texto integral acessado.

IEC. **IEC 60034-15:2009** — Rotating electrical machines — Part 15: Impulse voltage withstand levels of form-wound stator coils for rotating a.c. machines. 3. ed. Genebra: IEC, 2009. Amostra oficial: https://cdn.standards.iteh.ai/samples/15848/1b914cc7cb9b4c4582e502f946666007/IEC-60034-15-2009.pdf. Acesso em: 2 set. 2026.

IEC. **IEC 60034-15:2025** — idem. 4. ed. Genebra: IEC, 2025. Disponível em: https://webstore.iec.ch/en/publication/69045. Acesso em: 2 set. 2026. (Tabela 1 da edição publicada **não acessada** — [INSERIR CITAÇÃO].)

IEC. **IEC 60034-18-41:2014 (+AMD1:2019)** — Partial discharge free electrical insulation systems (Type I) used in rotating electrical machines fed from voltage converters. Genebra: IEC, 2014. Amostra: https://cdn.standards.iteh.ai/samples/18905/b95c2f0bc77e4b658894b3e6629e3aa2/IEC-60034-18-41-2014.pdf. Acesso em: 2 set. 2026. (Tabela 4 e Fig. 7 **não acessadas** — [INSERIR CITAÇÃO].)

IEC. **IEC 60034-27-2:2023** — On-line partial discharge measurements on the stator winding insulation of rotating electrical machines. Genebra: IEC, 2023. Amostra: https://cdn.standards.iteh.ai/samples/103004/5eca519428624e729a23cd1282b66962/IEC-60034-27-2-2023.pdf. Acesso em: 2 set. 2026.

IEC. **IEC 60034-27-3:2015** — Dielectric dissipation factor measurement on stator winding insulation of rotating electrical machines. Genebra: IEC, 2015. Amostra: https://cdn.standards.iteh.ai/samples/19866/c3993cedb23c47f9831620d7be90fef3/IEC-60034-27-3-2015.pdf. Acesso em: 2 set. 2026.

IEC. **IEC 60034-27-4:2018** — Measurement of insulation resistance and polarization index of winding insulation of rotating electrical machines. Genebra: IEC, 2018. Amostra: https://cdn.standards.iteh.ai/samples/21978/2d3f0846afc7499190a2d8bcfa239328/IEC-60034-27-4-2018.pdf. Acesso em: 2 set. 2026.

IEC. **IEC 62271-110:2023** — High-voltage switchgear and controlgear — Part 110: Inductive load switching. 5. ed. Genebra: IEC, 2023. Amostra: https://cdn.standards.iteh.ai/samples/110032/6134d1d703624b01af650b4c93dc550f/IEC-62271-110-2023.pdf. Acesso em: 2 set. 2026.

IEEE. **IEEE Std 522-2023** — Guide for testing turn insulation of form-wound stator coils for alternating-current electric machines. Nova York: IEEE, 2023. Disponível em: https://standards.ieee.org/ieee/522/6940/. Acesso em: 2 set. 2026. (Texto integral **não acessado** — [INSERIR CITAÇÃO] para a Fig. 1.)

ISO. **ISO 13381-1:2015** — Condition monitoring and diagnostics of machines — Prognostics — Part 1: General guidelines. Amostra: https://cdn.standards.iteh.ai/samples/51436/8246d96c8ff54347ae65f3aba73f2e88/ISO-13381-1-2015.pdf. Acesso em: 2 set. 2026. (Substituída pela ISO 13381-1:2025 — conteúdo não lido.)

KOHLER, J. L.; SOTTILE, J.; TRUTT, F. C. Condition monitoring of stator windings in induction motors. Part I — Experimental investigation of the effective negative-sequence impedance detector. **IEEE Transactions on Industry Applications**, 2002. DOI 10.1109/TIA.2002.802935. (Resumo verificado; texto integral não acessado.)

LIN, J.; MARTÍ, J. R. Implementation of the CDA procedure in the EMTP. **IEEE Transactions on Power Systems**, v. 5, n. 2, p. 394–402, maio 1990. — Fonte primária; texto integral acessado.

MA, K.; LISERRE, M.; BLAABJERG, F.; KEREKES, T. Thermal loading and lifetime estimation for power device considering mission profiles in wind power converter. **IEEE Transactions on Power Electronics**, v. 30, n. 2, p. 590–602, fev. 2015. DOI 10.1109/TPEL.2014.2312335.

MAHSEREDJIAN, J. et al. On a new approach for the simulation of transients in power systems. **Electric Power Systems Research**, v. 77, n. 11, p. 1514–1520, 2007. — Fonte primária; texto integral acessado.

RELIASOFT. **Miner's rule and cumulative damage models**. HotWire, n. 116. Disponível em: https://help.reliasoft.com/articles/content/hotwire/issue116/hottopics116.htm. Acesso em: 2 set. 2026.

THEOFANOUS, A. et al. Modelling of insulation thermal ageing: historical evolution from fundamental chemistry towards becoming an electrical machine design tool. **Energies**, v. 18, art. 6087, 2025. DOI 10.3390/en18236087. Disponível em: https://aisberg.unibg.it/retrieve/43c96487-a8ad-4947-a8c8-3b350e9892a2/J65.pdf. Acesso em: 2 set. 2026.

VOLLET, C.; DE METZ-NOBLAT, B. Vacuum circuit breaker model: application case to motors switching. In: **INTERNATIONAL CONFERENCE ON POWER SYSTEMS TRANSIENTS (IPST 2007)**, Lyon, 2007, paper 07IPST106. Disponível em: https://www.ipstconf.org/papers/Proc_IPST2007/07IPST106.pdf. Acesso em: 2 set. 2026.

**Nota sobre a lista de referências.** Este índice cita apenas as fontes invocadas em seu próprio texto. A lista bibliográfica completa do estudo, com 60+ entradas e a seção "Referências ainda sem fonte primária acessada", está em `01_ETAPA1_monitoramento_degradacao_isolamento.md`, §10. Nenhuma referência foi criada sem verificação: onde a fonte falta, o marcador `[INSERIR CITAÇÃO]` permanece no texto.
