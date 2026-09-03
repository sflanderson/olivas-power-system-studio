# Monitoramento de degradação de isolamento e RUL de motores de indução MT — índice e nota metodológica

**Objetivo.** Registrar, em um único ponto de entrada, (i) o objetivo e o desenho em três etapas do estudo que fundamenta o módulo MVP de RUL (*remaining useful life*) de isolamento de estator para motores de indução de média tensão (MT, 2,3–13,8 kV) manobrados por disjuntores a vácuo (VCB) em plantas críticas; (ii) o método de produção e de verificação do material, incluindo o sistema de rótulos de evidência que governa todo o corpus; (iii) o mapa navegável dos documentos e dos anexos; (iv) as premissas do usuário e as limitações globais que restringem o uso acadêmico do material; e (v) o próximo passo recomendado. Este arquivo é índice e contrato metodológico: ele **não** repete conteúdo técnico dos anexos, apenas os endereça.

**Diagnóstico.** A Etapa 1 está entregue e verificada, em `01_ETAPA1_monitoramento_degradacao_isolamento.md` (873 linhas), sustentada por 31 anexos (8 949 linhas) organizados em cinco subdiretórios [REPO: `docs/research/rul_isolamento/`, contagem por `wc -l` nesta sessão]. O acervo cobre com solidez três dos quatro elos da cadeia manobra → estresse → estado → vida: o **gerador de estresse** (Documento A, ATP/EMTP, com números de TRV e RRRV verificados), o **envelope normativo de suportabilidade** (IEC 60034-15, IEEE 522, IEC 60034-18-41/-42, IEC 60071-1, IEC 62271-110) e o **estado da arte de monitoramento e de prognóstico** (13 fichamentos + IEC 60034-27-x, IEEE 43/1434, ISO 13374-1/13381-1). O elo ausente é o quarto e decisivo: **nenhuma fonte primária acessada fornece parâmetros de curva de vida (expoente $n$, limiar $V_{th}$, fração espira-a-espira $a(t_f)$) medidos em mica-epóxi pré-formada de MT sob impulsos de VCB** [FATO: `01_ETAPA1...md`, bloco inicial, "Limitações" (b) e §5.4, D1–D2]. Consequentemente, a Etapa 2 não pode ser um exercício de calibração a partir da literatura: precisa ser desenhada como **arquitetura de acumulador de dano com parâmetros declaradamente livres**, cuja incerteza é propagada, e não escondida.

**Arquivos consultados.**

| Arquivo | Papel na composição deste índice |
|---|---|
| `01_ETAPA1_monitoramento_degradacao_isolamento.md` (873 l.) | Documento indexado; dele provêm o escopo da Etapa 1, as equações-âncora (§5.4), as limitações declaradas e a lista de referências sem fonte primária |
| `anexos/fichamentos_AB/A_snubber_tiristor_vcb.md` (423 l.) | Estado verificado do Documento A: Tabelas I–III, parâmetros do VCB, seção 8 ("o que A não afirma") |
| `anexos/fichamentos_AB/B_load_shedding_n1_nsga.md` (473 l.) | Estado verificado do Documento B: restrições g1–g3, NSGA-II/III, ausências declaradas |
| `anexos/fichamentos/01…13_*.md` (13 arq., 2 961 l.) | Corpus de apoio; convenções de rotulagem de cada fichamento |
| `anexos/pesquisa/*.md` (9 arq.) | Pesquisas dirigidas (3) e pesquisas web multi-fonte (6), com registro de bloqueios HTTP |
| `anexos/repo/*.md` (5 arq., 1 820 l.) | Mapas do código do Olivas Power System Studio (VCB/snubber, TRT, motor/partida, confiabilidade, convenções) |
| `anexos/cruzamento/*.md` (2 arq., 812 l.) | Cruzamentos A × literatura × repositório e B × consumo de vida |
| `anexos/verdicts/{A,B}_*.json` | Veredictos da verificação adversarial dos fichamentos A e B |

**Estratégia.** O índice adota três eixos de organização, nesta ordem de precedência: **(1) estado epistêmico** — cada item do acervo é classificado por origem (fonte primária lida / metadado / fonte secundária / inferência) por meio do sistema de rótulos da §2.7, que é o mesmo em todos os arquivos; **(2) função na cadeia causal** — cada anexo é posicionado como gerador de estresse, envelope normativo, indicador de estado, modelo de vida ou infraestrutura computacional; **(3) rastreabilidade** — todo caminho é relativo à raiz `docs/research/rul_isolamento/`, de modo que o diretório seja portável para anexo de tese, apêndice de artigo ou pacote de entrega, sem reescrita de referências.

**Limitações.** (a) O escopo detalhado das Etapas 2 e 3 é **previsto**, não contratado: apenas a Etapa 1 tem produto verificável em disco; o desdobramento apresentado na §1.3 é proposta deste índice [HIPÓTESE de escopo]. (b) O índice herda integralmente as limitações da Etapa 1 (§4.2), inclusive a ausência de parâmetros de vida para mica-epóxi e a não leitura do texto integral da IEEE Std 522 e da Tabela 1 da IEC 60034-15:2025. (c) Documentos A e B estão em revisão duplo-cega, sem autoria divulgada, o que impede citação nominal e obriga a marca [INSERIR CITAÇÃO] em toda referência bibliográfica a eles. (d) A contagem de linhas e de arquivos reflete o estado da árvore no momento da redação; qualquer inclusão posterior de anexo exige atualização da §3.

**Próximo passo recomendado.** Antes de abrir a Etapa 2, executar a extração declarada como próximo passo da Etapa 1 — tensão no nó do motor, contagem de reignições por polo e tempo de frente $T_1$ por reignição, a partir do modelo ATP existente, sem alterar o circuito —, porque esses três números são as **entradas obrigatórias** de qualquer acumulador de dano e hoje não existem em nenhum documento do acervo [FATO: `01_ETAPA1...md`, bloco inicial, "Próximo passo recomendado"; FATO por omissão: doc A, p. 1–5]. Sem eles, a Etapa 2 produziria arquitetura sem dado de entrada.

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
| Q4 | Que arquitetura computacional converte oscilograma de manobra em RUL com incerteza declarada, e como ela se acopla ao repositório existente? | 2 (prevista) |
| Q5 | Que valor econômico e que indicadores (Asset Health Index, custo evitado) tornam o módulo defensável perante C-Level, e como o resultado é entregue como trabalho acadêmico reprodutível? | 3 (prevista) |

### 1.3 As três etapas

| Etapa | Escopo | Produto | Estado |
|---|---|---|---|
| **1 — Monitoramento de degradação de isolamento** | Estresse dielétrico espira-a-espira; TRVs de VCB; efeito cumulativo de reignições; envelope normativo de suportabilidade; métodos atuais de monitoramento; lacuna metodológica | `01_ETAPA1_monitoramento_degradacao_isolamento.md` (10 seções, 873 l.) + 31 anexos | **Entregue e verificado** [REPO: `docs/research/rul_isolamento/01_ETAPA1_monitoramento_degradacao_isolamento.md`] |
| **2 — Especificação do módulo MVP de RUL** | Arquitetura do acumulador de dano; extração de descritores do transitório (ATP/EMTP); acoplamento aos Documentos A (estresse por manobra) e B (frequência de manobras sob N-1); propagação de incerteza; pontos de integração no repositório; plano de calibração dos parâmetros livres | Documento `02_*` + protótipo de código | **Prevista** [HIPÓTESE de escopo — a confirmar com o autor] |
| **3 — Caso de negócio e entrega acadêmica** | Tradução de RUL em decisão (Asset Health Index, semáforo, custo evitado); demanda de C-Level; contexto industrial brasileiro e de O&G; reprodutibilidade (FAIR4RS, DOI de software); empacotamento dos entregáveis | Documento `03_*` + pacote de entrega | **Prevista** [HIPÓTESE de escopo — a confirmar com o autor] |

Os insumos das Etapas 2 e 3 **já estão parcialmente coletados** e residem em `anexos/pesquisa/` (`entrega_trabalho_computacional.md`, `termico_partidas_n1_otimizacao.md` para a Etapa 2; `c_level_demanda_rul.md`, `contexto_industrial_brasil_og.md` para a Etapa 3) e em `anexos/repo/` (pontos de integração). A separação entre etapas é de **redação**, não de coleta.

### 1.4 O que a Etapa 1 efetivamente fixou

Quatro resultados estruturais, que as etapas seguintes tomam como dados de entrada e não devem reabrir sem nova evidência:

1. **O estressor é medível em microssegundos; o estado é medível em meses; não existe função de transferência normalizada entre os dois.** Essa assimetria é a lacuna que o módulo endereça [FATO: `01_ETAPA1...md`, §1.3].
2. **A norma de manobra indutiva não impõe teto de sobretensão** — "No limits to the overvoltages are given as the overvoltages are only relevant to the specific application" —, transferindo a coordenação para o projeto da instalação [NORMA: IEC 62271-110:2023, 4.3.1].
3. **O cenário do Documento A é justamente aquele que a IEC 60034-15 ressalva.** A Nota 5 da Tabela 1 adverte que os níveis-padrão "may not be adequate for special operating conditions (e.g. interrupted start …)"; trata-se de ressalva, não de exclusão formal [NORMA: IEC 60034-15:2009, Tabela 1, Nota 5 — transcrição literal reconferida em preview oficial]. A equivalência entre "interrupted start" e a "intempestive interruption of a motor start" de A é interpretação do estudo [INFERÊNCIA].
4. **As três normas de diagnóstico negam explicitamente predizer tempo até falha** a partir de seus indicadores [NORMA: IEC 60034-27-2:2023, Introdução; IEC 60034-27-3:2015, Introdução; IEC 60034-27-4:2018, Introdução]. Logo, o módulo não compete com norma: ocupa espaço que a norma declara vago.

---

## 2. Método

### 2.1 Corpus

O corpus tem duas camadas, com estatutos epistêmicos distintos e não intercambiáveis.

| Camada | Itens | Estatuto | Onde está o produto |
|---|---|---|---|
| **Documentos do autor** | A (snubber ativo a tiristor, ATP/EMTP, VCB dinâmico) e B (load shedding seletivo sob N-1, OpenDSS, NSGA-II/III) | Submissões em revisão duplo-cega, **sem autoria divulgada**; texto integral lido | `anexos/fichamentos_AB/` (2 arq.) |
| **Literatura de apoio** | 13 artigos de RUL/PHM, prognóstico de isolamento, IGBT, mancais, séries temporais e revisões | Publicados; texto integral lido para todos; tabelas/figuras nem sempre recuperadas pela extração | `anexos/fichamentos/` (13 arq.) |

Camada complementar, não bibliográfica: **normas e guias** (IEC, IEEE, ISO, NEMA, ABNT, CIGRE), acessados por preview oficial, amostra de norma ou página do organismo, sempre com a cláusula/tabela identificada; e o **próprio repositório**, lido como fonte de fato verificável.

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
├── 01_ETAPA1_monitoramento_degradacao_isolamento.md   (Etapa 1 — entregue)
└── anexos/
    ├── fichamentos/        13 arquivos — literatura de apoio
    ├── fichamentos_AB/      2 arquivos — Documentos A e B do autor
    ├── pesquisa/            9 arquivos — 3 pesquisas dirigidas + 6 pesquisas web
    ├── repo/                5 arquivos — mapas do código
    └── cruzamento/          2 arquivos — A × B × literatura × repositório
```

Todos os caminhos citados adiante são **relativos a `docs/research/rul_isolamento/`**. Os anexos são referenciados, nunca transcritos: o conteúdo técnico vive neles.

### 3.2 Documentos principais

| Caminho relativo | Conteúdo | Extensão |
|---|---|---|
| `01_ETAPA1_monitoramento_degradacao_isolamento.md` | 10 seções: enquadramento do modo de falha; física do estresse espira-a-espira; perfil de estresse do Documento A (Tabela III, normalizações, tempo de frente equivalente); referencial normativo de suportabilidade; efeito cumulativo de reignições (D1–D7 + exemplo numérico); correção conceitual sobre "redução do BIL"; métodos atuais de monitoramento; lacuna metodológica e proposta de contagem de estresse; limitações; referências | 873 linhas |
| `02_*` (previsto) | Especificação do módulo MVP de RUL | — |
| `03_*` (previsto) | Caso de negócio e entrega acadêmica | — |

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

### 4.3 Regras de uso do acervo em texto acadêmico

1. Afirmação com `[INSERIR CITAÇÃO]` **não** entra em artigo ou tese antes de a fonte primária ser lida.
2. Valor obtido por **leitura de figura** só é citado com a ressalva de origem que o acompanha no anexo.
3. Afirmação negativa sobre A ou B exige rótulo `[FATO por omissão]` e a indicação de que foi verificada por busca no texto integral.
4. Rótulo `[HIPÓTESE]` jamais fundamenta conclusão; aparece somente como premissa declarada, com o teste que a decidiria.
5. Comparação entre TRV do disjuntor e envelope de suportabilidade de máquina traz sempre a ressalva de grandeza (L3).

---

## 5. Próximo passo recomendado

**Passo imediato (pré-Etapa 2), por ordem de dependência:**

1. **Extrair do modelo ATP do Documento A, sem alterar o circuito**, as três grandezas ausentes: (i) tensão fase-terra e fase-neutro no nó do motor; (ii) número de reignições por polo por manobra, $n_{r,m}$; (iii) tempo de frente $T_1$ por reignição, na definição normativa. Sonda já existente no `/OUTPUT` do arquivo de referência [REPO: `git show ad308d5:trt_all_motors_dt_ea.atp:857-859`, conforme `01_ETAPA1...md`]. Sem essas três séries, (E4) não tem entrada.
2. **Verificar sensibilidade ao passo de integração** (L5): repetir um caso com passo de 10–50 ns e medir se as frentes de sub-microssegundo alteram materialmente a RRRV. O resultado decide se as RRRV da Tabela III podem ser usadas diretamente como dose ou apenas como limite inferior.
3. **Fechar as lacunas normativas de maior impacto** (L8): obter o texto integral da IEEE Std 522 (Fig. 1, envelope tensão × tempo de frente) e a Tabela 1 da IEC 60034-15:2025, que definem o denominador do confronto de suportabilidade.
4. **Só então abrir a Etapa 2**, com a arquitetura de (E1)–(E4) instanciada sobre dados reais do modelo e com plano explícito de calibração e de propagação de incerteza dos parâmetros livres de (E2).

**Decisão a submeter ao autor antes da Etapa 2**: confirmar o escopo previsto nas linhas 2 e 3 da tabela da §1.3, que hoje é proposta deste índice e não contrato [HIPÓTESE de escopo].

---

## Referências

ABNT. **ABNT NBR 17094-1:2018** — Máquinas elétricas girantes — Parte 1: Motores de indução trifásicos — Requisitos. 3. ed. Rio de Janeiro: ABNT, 2018.

AUTORES OMITIDOS (revisão duplo-cega). **Selective mitigation of vacuum circuit breaker switching overvoltages in medium voltage induction motors using an active thyristor snubber**. Submissão ao SEPOC 2026. 5 p. — **Documento A**. Autoria a confirmar após publicação — [INSERIR CITAÇÃO].

AUTORES OMITIDOS (revisão duplo-cega). **Selective load shedding for the switching of large motors under N-1 contingency: constrained multiobjective optimization with NSGA-II, NSGA-III and regression surrogates**. Submissão ao SEPOC 2026. 6 p. — **Documento B**. Autoria a confirmar após publicação — [INSERIR CITAÇÃO].

CIGRE. **Technical Brochure 703 — Insulation degradation under fast, repetitive voltage pulses**. WG D1.43. Paris: CIGRE, 2017. Cópia consultada: https://cigre.cz/dokumenty_komise/d1/WG%20D1.43_TB_Final.pdf. Acesso em: 2 set. 2026.

FEILAT, E. A. Lifetime assessment of electrical insulation. In: **Electric Field**. Londres: IntechOpen, 2018. DOI 10.5772/intechopen.72423. Disponível em: https://cdn.intechopen.com/pdfs/58128.pdf. Acesso em: 2 set. 2026.

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

MA, K.; LISERRE, M.; BLAABJERG, F.; KEREKES, T. Thermal loading and lifetime estimation for power device considering mission profiles in wind power converter. **IEEE Transactions on Power Electronics**, v. 30, n. 2, p. 590–602, fev. 2015. DOI 10.1109/TPEL.2014.2312335.

RELIASOFT. **Miner's rule and cumulative damage models**. HotWire, n. 116. Disponível em: https://help.reliasoft.com/articles/content/hotwire/issue116/hottopics116.htm. Acesso em: 2 set. 2026.

THEOFANOUS, A. et al. Modelling of insulation thermal ageing: historical evolution from fundamental chemistry towards becoming an electrical machine design tool. **Energies**, v. 18, art. 6087, 2025. DOI 10.3390/en18236087. Disponível em: https://aisberg.unibg.it/retrieve/43c96487-a8ad-4947-a8c8-3b350e9892a2/J65.pdf. Acesso em: 2 set. 2026.

VOLLET, C.; DE METZ-NOBLAT, B. Vacuum circuit breaker model: application case to motors switching. In: **INTERNATIONAL CONFERENCE ON POWER SYSTEMS TRANSIENTS (IPST 2007)**, Lyon, 2007, paper 07IPST106. Disponível em: https://www.ipstconf.org/papers/Proc_IPST2007/07IPST106.pdf. Acesso em: 2 set. 2026.

**Nota sobre a lista de referências.** Este índice cita apenas as fontes invocadas em seu próprio texto. A lista bibliográfica completa do estudo, com 60+ entradas e a seção "Referências ainda sem fonte primária acessada", está em `01_ETAPA1_monitoramento_degradacao_isolamento.md`, §10. Nenhuma referência foi criada sem verificação: onde a fonte falta, o marcador `[INSERIR CITAÇÃO]` permanece no texto.
