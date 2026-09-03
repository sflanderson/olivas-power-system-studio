# Fichamento 13 — Wu, Wu, Tan e Xu (2024): predição de vida útil remanescente baseada em aprendizado profundo — uma revisão

Arquivo-fonte: `papers/txt/sensors-24-03454-v3.txt` (30 páginas; a paginação "p. N" abaixo segue os marcadores `===== PAGE N =====` do txt, que coincidem com a paginação interna "N of 30" do artigo).

Convenção de rotulagem: **[FATO]** = afirmação do artigo, com página; **[INFERÊNCIA]** = leitura/juízo meu a partir do texto ou do repositório; **[HIPÓTESE]** = suposição não verificável no texto.

Advertência inicial: trata-se de **artigo de revisão** (categoria "Review" da MDPI, p. 1). Não há experimento próprio, dataset próprio, indicador medido nem resultado numérico de desempenho do(s) autor(es). Os números que aparecem são citados de trabalhos terceiros. As seções 4, 6 e 7 registram, portanto, ausências explícitas e o que pode ser aproveitado como catálogo metodológico.

---

## 1. Referência completa

WU, Fuhui; WU, Qingbo; TAN, Yusong; XU, Xinghua. Remaining Useful Life Prediction Based on Deep Learning: A Survey. **Sensors**, Basel, v. 24, n. 11, art. 3454, p. 1–30, 2024. DOI: 10.3390/s24113454. [FATO, p. 1]

- Tipo: "Review"; editor acadêmico: Yi Qin; recebido em 21 abr. 2024, revisado em 22 maio 2024, aceito em 24 maio 2024, publicado em 27 maio 2024; licença CC BY 4.0 (p. 1). [FATO]
- Afiliações (p. 1) [FATO]: F. Wu — School of Information Engineering, Wuhan College, Wuhan; Q. Wu e Y. Tan — College of Computer, National University of Defense Technology, Changsha; X. Xu — National Key Laboratory of Science and Technology on Vessel Integrated Power System, Naval University of Engineering, Wuhan. Autor correspondente: fuhui.wu@whxy.edu.cn.
- Financiamento: Guangdong Major Project of Basic and Applied Basic Research, Grant 2019B030302002 (p. 25). [FATO]
- Contribuições: conceituação, metodologia, validação, análise formal e redação original de F.W.; investigação e supervisão de Q.W. e Y.T.; recursos e revisão de X.X. (p. 25). [FATO]
- Extensão: 162 referências (p. 25–30); 3 figuras; 8 tabelas. [FATO]
- O número "11" do volume 24 é inferido do padrão MDPI para o DOI `s24113454` (24 = volume, 11 = número, 3454 = artigo); o texto extraído traz apenas "Sensors 2024, 24, 3454". [INFERÊNCIA]

---

## 2. Objetivo do artigo

Realizar uma revisão abrangente da predição de RUL baseada em aprendizado profundo (DL) segundo três dimensões: (i) propor um **framework unificado** e revisar modelos/abordagens sob ele; (ii) comparar os processos de estimação **por modelo de rede profunda**; (iii) examinar a literatura **por problema específico** (p. ex., dados rotulados limitados); e, ao final, sintetizar desafios e direções futuras (Resumo, p. 1). [FATO]

Quatro princípios orientadores declarados (p. 5) [FATO]:
1. revisar a literatura sob uma formulação e um framework unificados;
2. revisar "principalmente da perspectiva do problema de predição de RUL", e não da perspectiva das redes;
3. **não** introduzir detalhes das técnicas de DL ("assume-se que os leitores já possuem esse conhecimento");
4. **não** detalhar campos de aplicação específicos nem datasets de teste, para estudar "a metodologia geral".

Justificativa para uma nova revisão: as revisões anteriores focadas em DL para RUL "revisaram um número limitado de trabalhos [20]" ou "consideraram apenas baterias de íon-lítio [21]" (p. 5); a Tabela 2 (p. 5) compara nove revisões anteriores nas dimensões objetivo (PHM vs. RUL) e método (TDD = tradicional orientado a dados; SNN = rede rasa; DNN = rede profunda). [FATO]

[INFERÊNCIA] Os princípios 3 e 4 delimitam o alcance: o artigo é um mapa de arquiteturas e etapas de processamento, não um manual de aplicação. Para o problema-alvo, isso significa que ele fornece o "esqueleto" do pipeline, mas nenhuma orientação sobre grandezas físicas, sensores ou regimes de estresse.

---

## 3. Sistema/componente e mecanismo(s) de degradação tratados

- **Sistema:** nenhum sistema específico. Por construção (princípio 4, p. 5), o artigo abstrai o ativo. [FATO]
- **Campos de aplicação que aparecem nas tabelas de síntese** (todos de trabalhos terceiros) [FATO]: rolamentos (Tab. 3–8); motores turbofan/aeronáuticos e datasets C-MAPSS, PHM 08 Challenge, PHM 2012 Challenge e Milling (Tab. 5–8; p. 13, 16, 18, 19); baterias de íon-lítio (Tab. 5, 7; p. 13, 18); célula a combustível PEMFC (Tab. 5, p. 13); caixa de engrenagens (p. 13); desgaste de ferramenta e fresamento (p. 13, 18); discos rígidos (p. 13); turbina a gás (p. 13, 18); aviônica modular integrada (IMA) (p. 18); taxa de remoção de material em polimento (p. 12); propagação de trinca (p. 19); facas de corte (p. 19); "transformador de potência" e "ventilador de resfriamento elétrico" (apenas como casos do ensemble de Hu et al. [142], p. 19); "sistema de equipamento" genérico (patente [92], p. 13).
- **Mecanismos de degradação:** não são descritos. O texto trata a degradação de forma fenomenológica — "trajetórias históricas" de sensores das quais se "descobre a lei de degradação de desempenho" (p. 2). [FATO]
- **Ausências verificadas no texto integral** [FATO — ausência]: nenhuma ocorrência dos termos *insulation*, *stator*, *motor* (no sentido de máquina elétrica), *partial discharge*, *Arrhenius*, *Weibull* (exceto no título da ref. [4]), *censoring*. A única máquina elétrica citada é indireta (referência [45], ICEMS, sobre rolamentos).
- [INFERÊNCIA] O corpus revisado é dominado por degradação mecânica progressiva (rolamentos, turbinas) e eletroquímica (baterias, PEMFC), regimes em que o indicador de saúde evolui de forma aproximadamente contínua e monotônica. Degradação dielétrica sob estresse impulsivo (surtos de manobra) não é contemplada nem tangencialmente.

---

## 4. Indicadores/precursores de degradação usados

Não há grandeza medida pelos autores. O artigo trata **indicador de saúde (HI)** como construto abstrato e cita exemplos de terceiros sem unidade nem taxa de amostragem. Registra-se o que consta:

| Grandeza / construto | Unidade | Como é obtido | Taxa de amostragem | Página |
|---|---|---|---|---|
| **Health indicator (HI)** — "métrica de indexação de saúde" gerada antes do cálculo de RUL; deve satisfazer **monotonicidade, tendenciabilidade (trendability) e prognosticabilidade (prognosability)** | adimensional (não declarado) [INFERÊNCIA] | por aprendizado não supervisionado, pois "datasets para redes profundas não possuem rótulos de treinamento de HI" | não citada | p. 8, 9 |
| **PHI (physical HI)** vs. **FHI (fused/synthesized/virtual HI)** — PHI extraído por estatística ou processamento de sinal; FHI construído por fusão de múltiplos PHIs ou sensores | não declarada | fusão por AAKR, média ponderada (pesos por GWO), perceptron, CNN, RNN/LSTM (Tab. 3) | não citada | p. 9–11 |
| Sinal de **vibração de rolamento** — características no domínio do tempo (insensíveis a pequenas mudanças, sensíveis a ruído; representam o estágio intermediário) e no domínio da frequência (sensíveis aos estágios inicial e final) [23] | não declarada | FT, WVD, WT, CWT, STFT; imagens tempo-frequência para CNN | não citada | p. 7, 10, 16 |
| **Dados diferenciais dinâmicos** [24] — diferença avante entre o valor atual do sensor e o anterior "sob o mesmo modo de operação" | mesma do sensor | cálculo direto antes do treinamento | não citada | p. 7 |
| **Curtose** — usada para determinar o *first prediction time* (FPT) [29,30] | adimensional [INFERÊNCIA] | estatística de 4ª ordem do sinal | não citada | p. 7 |
| **Série de capacidade de bateria** — reconstruída por EMD; captura degradação de longo prazo e "recuperação de capacidade em certos ciclos" [138] | não declarada (Ah implícito) [INFERÊNCIA] | ensaio de ciclagem | por ciclo | p. 19 |
| **Vetor spectrum-principal-energy** [111] — característica projetada para suprir "falta de características no domínio do tempo" | não declarada | extração espectral, entrada de CNN de 8 camadas | não citada | p. 16 |
| **Características tridomínio** (tempo, frequência, tempo–frequência) por janela local [99] | não declarada | segmentação em janelas de comprimento fixo | não citada | p. 16 |

Critérios de seleção de sinais (p. 7) [FATO]: os dados selecionados devem ter "capacidade diagnóstica, sensibilidade e consistência"; a capacidade diagnóstica "determina a acurácia", a sensibilidade "é altamente correlacionada com o desempenho de predição" e a consistência "relaciona-se à confiança do resultado".

Três inconvenientes dos HIs sintetizados (p. 9) [FATO]: (1) características estatísticas têm faixas distintas e contribuições desiguais; (2) "é difícil determinar um limiar de falha definido porque os valores de HI apresentam grande variação entre ativos no instante da falha"; (3) características variam em sensibilidade a falhas.

[INFERÊNCIA] Os três critérios de HI (monotonicidade, tendenciabilidade, prognosticabilidade) são o item mais reaproveitável desta seção: servem como **critério de aceitação** de qualquer indicador candidato de isolamento (p. ex., magnitude/fase de descargas parciais, tan δ, capacitância, resistência de isolamento, índice de polarização), independentemente do modelo. O inconveniente (2) — limiar de falha disperso entre ativos — é justamente o caso do isolamento de estator, cuja ruptura depende de defeitos locais e do estresse aplicado.

---

## 5. Modelo/algoritmo

**Classe:** **revisão** (survey) de métodos **orientados a dados** (deep learning). O artigo classifica os métodos de RUL em *model-based* (físicos) e *data-driven*, e dentro destes em TDD, SNN e DNN; só os DNN são revisados (p. 2, 5). [FATO]

### 5.1 Formulação do problema e equação-chave (p. 5–6) [FATO]

- "Atualmente, não há uma definição clara de vida útil remanescente (RUL). É até difícil definir o instante de falha de um sistema" (p. 5).
- Definição 1: T = instante de falha do sistema. Definição 2: t = instante até o qual o sistema sobreviveu (p. 6).
- Única equação numerada do artigo, com atribuição a Banjevic [22]:

  **rul = T − t   (1)**   — p. 6

- O método baseado em DL "constrói uma rede neural profunda que calcula o valor de RUL a partir dos dados brutos de entrada de forma fim-a-fim" (p. 6).

[INFERÊNCIA] A eq. (1) é determinística e pressupõe T único e observável. O próprio artigo reconhece que, em aplicações reais, "a manutenção baseia-se usualmente na função densidade de probabilidade (PDF) da RUL" (p. 15) e que a falta de representação de incerteza é "uma desvantagem comum dos métodos de DL" (p. 21). Não há formulação probabilística explícita (p. ex., RUL como variável aleatória condicionada a covariáveis) no corpo do texto.

### 5.2 Framework unificado em três estágios (Fig. 2, p. 6) [FATO]

1. **Pré-processamento de dados** (p. 6–8): filtragem (critérios de diagnóstico, sensibilidade, consistência; dados diferenciais dinâmicos), normalização (z-score [25]; normalização multirregime por componente [26]) e particionamento em três níveis: (a) treino/teste, rotulado/não rotulado; (b) **estágio saudável vs. estágio de deterioração** — a maioria da literatura assume RUL *piecewise linear* (constante no início, decrescente linear depois), assunção que "frequentemente torna esses modelos impraticáveis para tarefas reais" (p. 7); alternativas: classificador MLP treinado por EKF [27,28] e FPT por curtose [29,30]; (c) modos de mapeamento **P2P** (ponto a ponto), **S2P** (sequência a ponto) e **S2S** (sequência a sequência); "para o cenário de predição de RUL, P2P e S2P são usualmente adotados" (p. 7–8). Preparação de entradas: *point-wise*, *segment-wise* (janela deslizante) e *temporal-wise* (p. 8).
2. **Geração de indicador de saúde** (p. 8, 9–11): transformação/seleção de características (AE, EAE, SDA, SAE, CNN, RNN-ED com vetores de máscara e delta para valores faltantes, PCA, KPCA, SOM; seleção como problema multiobjetivo [39]) e fusão/regressão (AAKR, média ponderada por GWO, perceptron, CNN, RNN, LSTM; suavização por MA/EWMA; remoção de *trend burrs* pela regra 3σ; regressão por GRU hierárquica ou GPR; agrupamento K-means por padrão de degradação; modelos distintos por estágio). Tabela 3 (p. 10) sintetiza 10 trabalhos.
3. **Predição de RUL** (p. 8–9): escolha do modelo (RNN e CNN são "os dois mais usados"), treinamento (sobreajuste, subajuste, explosão/desaparecimento de gradiente; validação cruzada; transferência) e otimização de hiperparâmetros "tratada como problema de otimização multiobjetivo" (p. 9).

### 5.3 Modelos revisados (Seção 4.2, p. 11–17) [FATO]

| Família | Variantes e exemplos citados | Detalhes estruturais mencionados | Página |
|---|---|---|---|
| Auto-encoder | AE empilhado treinado por HELM [55]; IDDA com dois DDAs + regressão linear (registros distantes = tendência de dano; recentes = suavização) [57]; conceito de "eletrocardiograma de dispositivo (DECG)" | — | p. 11–12 |
| RBM / DBN | RBM aprimorado com **regularização de inclinação** (trendability) + SOM para HI 1-D + RUL por similaridade [59]; DDBN-ACO [61]; RBMs empilhados + MLP de 3 camadas com PSO [62]; CDBN (unidades contínuas) com LLE e GA [63] | Tab. 4 (4 trabalhos) | p. 12–13 |
| RNN padrão | realimentação saída→entrada [69,70]; RNN estendida Elman+Jordan [71]; RNN adaptativa [72]; treinamento em lote vs. incremental [70]; BPTT truncado [27]; EKF [28]; evolução diferencial [102] | Tab. 5 (~31 trabalhos) | p. 13–14 |
| ESN | reservatório esparso aleatório, treino por regressão linear; PEMFC [74,103]; DE multiobjetivo para parâmetros [104]; biblioteca de ESNs por grupo de condição + filtro de Kalman [73] | — | p. 14 |
| LSTM | C-MAPSS/PHM08 [76]; duas camadas [89]; LSTM profunda [91,92,93]; **BiLSTM com duas camadas ocultas bidirecionais** e perceptron de uma camada para HI [94]; convolução nas transições entrada-estado e estado-estado [106,87]; atenção sobre características manuais + aprendidas [88]; dropout [100]; RMSprop [83]; Monte Carlo para incerteza [83]; atualização online de parâmetros [82] | — | p. 14–15 |
| GRU | MDGRU: RBM nas duas primeiras camadas + camada multiescala + skip-GRU com dropout/ReLU/Adam + três camadas densas [96]; KPCA + GRU sequence-to-one [97]; LFGRU bidirecional com média ponderada das características locais [99]; BiGRU com autoatenção temporal [101] | — | p. 15–16 |
| CNN | primeira aplicação: **dois pares conv+pooling + MLP**, com normalização customizada [108]; CNN de **8 camadas** (3 conv, 3 pooling, 1 flatten, 1 saída) + regressão linear de suavização [111]; MSCNN com WT + interpolação bilinear [109]; DCNN com min–max e janela temporal [110]; MSCNN com STFT, dropout, leaky ReLU [29]; núcleos paralelos de tamanhos distintos [114]; MSCAN com autoatenção [115]; **ECNN com dois canais** (dados anteriores/posteriores), **ponto de degradação = metade do maior ciclo**, seguido de decaimento linear, otimizador Adam [112] | Tab. 6 (6 trabalhos) | p. 16–17 |

### 5.4 Métodos transversais (Seção 4.3–4.4, p. 17–21) [FATO]

- **Transferência de aprendizado** (p. 17–18): motivação — "(1) não é permitido operar até a falha ativos críticos; (2) muitas falhas ocorrem lentamente ... podendo levar meses ou anos"; três categorias (indutiva, transdutiva, não supervisionada [117]) e quatro níveis (instância, representação de características, parâmetros, conhecimento relacional); BiLSTM com transferência de parâmetros em C-MAPSS [118] — eficaz "exceto ao transferir de múltiplas condições operacionais para uma única condição", abrindo o problema de **transferência negativa**; DTL com SAE e três estratégias [120]; adaptação de domínio com LSTM [121]; transferência transdutiva para rolamentos [122–125]; uso de "dados simulados" [116].
- **Híbridos** (p. 18–19): paradigma de dois estágios (AE/RBM → RNN/CNN); SDAE+SVM [128]; AE+BLSTM [129]; CNN+RNN [130–134]; deep AE + DNN de nove camadas com "normalização experience–max" [135]; DBN+FNN com *grid search* [136]; **filtro de partículas + rede neural (MLP, RNN, WNN)** — "desempenho não dependente do tipo de rede" [137]; LSTM+Elman com EMD [138]. Tabela 7 (11 trabalhos).
- **Ensemble** (p. 19–20): dois aspectos — projeto dos membros e fusão das saídas; filtro de Kalman [139]; **switching Kalman filter** para superar a assunção de degradação linear [140,141]; cinco modelos com ponderação por acurácia, diversidade e otimização [142]; PF com ANNs [143]; ESNs com DE multiobjetivo (objetivos CRA e α-λ) e agregação local dinâmica + incerteza por MVE [144]; pesos dependentes do estágio de degradação [145]; CNN-BLSTM com média ponderada [146]; **MODBNE** — DBNs otimizadas por MOEA/D [148] com objetivos conflitantes acurácia × diversidade e pesos por DE [147]. Tabela 8 (8 trabalhos).
- **Ad hoc** (p. 20–21): múltiplas condições operacionais (normalização multirregime [26]; BLSTM que recebe condições operacionais como entrada, com dropout e *early stopping* [25]); dados rotulados insuficientes (SSL: VAE + RNN [152]; rede de cinco camadas RBM→2 LSTM→FNN→saída, treinada por TBPTT [153]; dados de simulação [116]); incerteza (DBN+RVM [154]; bootstrap em LSTM–FNN [155]; inferência variacional + MC dropout [156]; dropout com densidade kernel [157]; GPR para regeneração de capacidade [158]; camada de saída gaussiana [159]).

### 5.5 Hiperparâmetros e estruturas numericamente especificadas (todos de terceiros) [FATO]

- Peel [139]: ensemble vencedor da categoria IEEE GOLD do PHM'08 — RBF com **15** nós ocultos e dois MLPs com **75** e **100** nós ocultos; seleção por heurística de torneio; fusão por filtro de Kalman (p. 19–20).
- Ren et al. [111]: CNN de **8** camadas (p. 16).
- Babu et al. [108]: **dois** pares conv+pooling + MLP (p. 16).
- Zhang et al. [94]: **duas** camadas LSTM bidirecionais + perceptron de uma camada (p. 15).
- Jiang e Kuo [112]: ponto de degradação = **1/2** do maior ciclo (p. 17).
- Ellefsen et al. [153]: rede de **cinco** camadas (p. 21).
- Hu et al. [142]: **cinco** modelos-membro, validação cruzada K-fold (p. 19).
- Nenhum valor de taxa de aprendizado, tamanho de janela, número de épocas ou dimensão de embedding é reportado. [FATO — ausência]

---

## 6. Dados e experimento

- **Experimento próprio:** nenhum. [FATO]
- **Datasets nomeados** (sempre por trabalhos terceiros) [FATO]: C-MAPSS (NASA; referência de benchmarking [119]), PHM 08 Challenge, PHM 2012 Challenge, Milling dataset (p. 13, 16, 18, 19). Nenhum é descrito (número de unidades, ciclos, sensores).
- **Ensaios acelerados:** não são discutidos. [FATO — ausência]
- **Metodologia da revisão:** não são declarados base de busca, período, critérios de inclusão/exclusão nem número de artigos triados. A cobertura temporal das referências vai de 1986 (ref. [12]) a 2023 (ref. [125], [160]). [FATO + INFERÊNCIA]
- **Fonte de contexto quantitativo:** "desde os anos 1980, a capacidade mundial de armazenar informação per capita dobrou a cada 40 meses [9]"; curva de volume de dados atribuída a relatório da IDC (Fig. 1, p. 3); eras tera/peta/exaescala do Top500 (p. 3). [FATO]

---

## 7. Métricas e resultados numéricos

- **Resultados próprios:** nenhum. [FATO]
- **Métricas mencionadas** [FATO]: *cumulative relative accuracy* (CRA) — "estimativa média do erro relativo da predição de RUL ... tende a ampliar erros cometidos no fim da vida do sistema"; **α-λ accuracy** — "quantas vezes, em média, a predição de RUL cai dentro de dois limites de confiança relativos" (p. 20); validação cruzada K-fold como estimador de acurácia de membros de ensemble (p. 19); acurácia e diversidade como objetivos conflitantes de seleção de ensemble (p. 20, 24).
- **Afirmações qualitativas de desempenho reportadas de terceiros** [FATO]: FNN/RNN superam modelos autorregressivos [69] (p. 14); RNN estendida supera Elman e Jordan isoladamente [71] (p. 14); treinamento em lote evita sobreajuste do incremental [70] (p. 14); HELM "mais eficiente que retropropagação" [55] (p. 12); sequence-to-one "mais adequado" que sequence-to-sequence no cenário de [97] (p. 15); ponderação por otimização de Hu et al. "provou desempenhar melhor em três casos" (PHM'08, transformador de potência, ventilador) (p. 19); transferência eficaz "na maioria dos casos" [118] (p. 17).
- **Únicos números no corpo do texto:** os de estrutura listados em §5.5 e o "40 meses" de p. 3. Não há RMSE, MAE, *scoring function* do PHM'08 nem intervalos de confiança. [FATO — ausência]

[INFERÊNCIA] A ausência de qualquer tabela comparativa de desempenho é a maior fragilidade do artigo como fonte para justificar escolhas de arquitetura: ele informa **o que** foi feito, não **quão bem**.

---

## 8. Limitações

### 8.1 Declaradas pelos autores
1. **[declarada]** "Não há definição clara de RUL. É até difícil definir o instante de falha de um sistema" (p. 5).
2. **[declarada]** A assunção de RUL *piecewise linear* "frequentemente torna esses modelos impraticáveis para tarefas do mundo real"; escolher o ponto de início da degradação "é um problema comum na literatura" (p. 7).
3. **[declarada]** Limiar de falha de HI indefinido, pois os valores de HI "têm grande faixa de variação entre ativos no instante da falha" (p. 9).
4. **[declarada]** Transferência negativa ao passar de múltiplas para uma única condição operacional (p. 17).
5. **[declarada]** O ensemble de Peel assume "que a saúde do sistema degrada linearmente com o uso" (p. 20).
6. **[declarada]** "A falta de representação de incerteza é atualmente uma desvantagem comum dos métodos de DL"; "valores determinísticos podem não ser suficientes para decisões operacionais baseadas em RUL, como manutenção" (p. 21); LSTM "é incapaz de obter incertezas. Este problema não é pesquisado a fundo na literatura" (p. 15).
7. **[declarada]** "A predição de RUL ainda não é amplamente usada em sistemas reais" e a área "ainda está em estágio preliminar comparada a outras, como reconhecimento de fala e LLM" (p. 21–22).
8. **[declarada]** Falta de framework geral e de *benchmarking*; "pouco se sabe sobre por que e como essas arquiteturas ... foram projetadas" (p. 22); falta de datasets abertos de grande escala (p. 22–23).
9. **[declarada]** Redes profundas "ainda são consideradas modelos caixa-preta. Seus mecanismos internos são inexplicáveis" (p. 23).
10. **[declarada]** Hiperparâmetros "majoritariamente projetados manualmente" (p. 24).
11. **[declarada]** Datasets desbalanceados — "a quantidade de dados de falha é muito menor que a de dados saudáveis" (p. 24); a maioria dos trabalhos "assume que os ativos operam em condição operacional constante, o que não é verdade em ambientes de produção reais" (p. 24).
12. **[declarada]** "Poucos trabalhos se preocupam com os custos, especialmente computacionais"; a predição "deve ser realizada de maneira crítica no tempo" (p. 24).
13. **[declarada]** Escopo: sem detalhes de DL e sem detalhes de aplicação/datasets (princípios 3 e 4, p. 5).

### 8.2 Identificadas por mim
1. **[minha inferência]** Ausência total de comparação quantitativa de desempenho (ver §7); o leitor não consegue ordenar as abordagens.
2. **[minha inferência]** Metodologia de revisão não declarada (base, período, critérios), o que compromete a reprodutibilidade da própria revisão.
3. **[minha inferência]** Cobertura enviesada para rolamentos/turbofan/baterias; nenhuma menção a isolamento elétrico, máquinas elétricas de MT, descargas parciais ou envelhecimento dielétrico.
4. **[minha inferência]** O framework assume degradação **contínua e observada por séries temporais regulares**. Não há categoria para degradação **acionada por eventos** (contagem/severidade de surtos, partidas), nem para dados de estresse esparsos ou censurados; a palavra *censoring* não aparece.
5. **[minha inferência]** Modelos híbridos física–dados são tratados apenas via filtro de partículas com "modelos analíticos" (p. 19) e via "dados simulados" (p. 17, 21); não há discussão de *physics-informed neural networks* ou de regularização por leis de envelhecimento, embora p. 23 (5.2.2) recomende integrar conhecimento de domínio como termo de regularização.
6. **[minha inferência]** Arquiteturas baseadas em atenção/Transformers são mencionadas apenas de passagem (atenção em [88], [101], [115]; "cross-domain transformer" em [116]); para uma revisão de 2024, a cobertura de modelos pós-2020 é rala.
7. **[minha inferência]** Inconsistências editoriais: na Tabela 3 (p. 10) o trabalho de "Yoo et al." é numerado [42], mesmo número de "Zhao et al."; pelo texto de p. 11 e pela lista de referências (ref. [52] = Yoo e Baek, CWT+CNN, Appl. Sci. 2018), o correto seria [52]. Grafia "C-MASS" (p. 14) para C-MAPSS. A referência [92] é uma patente norte-americana, sem revisão por pares.
8. **[minha inferência]** A eq. (1) e o restante do texto não distinguem RUL populacional de RUL individual condicionada ao histórico de estresse — distinção central para ativos únicos de MT com histórico de manobras conhecido.
9. **[minha inferência]** A afirmação de que DL "é capaz de lidar com esses problemas automaticamente sem conhecimento de domínio" (p. 2) é parcialmente contradita pela Seção 5.2.2 (p. 23), que reconhece a necessidade de conhecimento de domínio para gerar características discriminativas e reduzir a escala do modelo.

---

## 9. Transferibilidade para o problema-alvo

**Problema-alvo:** isolamento de estator de motor de indução de MT (2,3–13,8 kV) sujeito a (a) sobretensões de manobra de VCB — corte de corrente (*chopping*), reignições múltiplas, frentes íngremes, dV/dt — com ou sem snubber tiristorizado (trabalho A), e (b) estresse térmico de partidas de grandes motores sob contingência N-1 com *load shedding* (trabalho B).

**Fatos do repositório usados como contexto** [FATO — repositório]: o modelo `app/preprocessor/atp_templates/vcb_reignition.mod` implementa reignição estatística por polo (CIGRE WG A3.26) com corrente de *chopping* I_chop ~ N(5 A, 1 A²) por padrão, di/dt crítico inicial de 16 A/µs com endurecimento de 0,034 A/µs², recuperação dielétrica U_dielec(t) = 690 V + 17 V/µs·(t − t_corte), rebote mecânico de 0,5 ms e contador `reign_count`; `app/validation/validator_vcb.py` valida faixa típica de I_chop (1–15 A), parâmetros RRDS de suportabilidade a TRV e a presença/conexão de um controlador de snubber. [HIPÓTESE] O snubber tiristorizado do trabalho A atua seletivamente sobre esse mecanismo, reduzindo o número de reignições e o dV/dt visto pelo enrolamento.

### 9.1 O que se transfere

| Elemento do artigo | Como se aplica ao problema-alvo | Rótulo |
|---|---|---|
| **Framework em três estágios** (pré-processamento → HI → RUL), p. 6 | Estrutura diretamente reutilizável como espinha dorsal do módulo computacional: (1) ingestão de séries de monitoramento (DP, tan δ, temperatura de enrolamento) **e** de registros de eventos (manobras de VCB com `reign_count`, partidas N-1); (2) construção de HI de isolamento; (3) regressão de RUL. | [INFERÊNCIA] |
| **Critérios de HI** — monotonicidade, tendenciabilidade, prognosticabilidade, p. 8–9 | Critérios de aceitação para indicadores de isolamento; permitem descartar precursores não monotônicos (p. ex., DP com "auto-cura" aparente por variação de umidade/temperatura). | [INFERÊNCIA] |
| **Particionamento saudável/deterioração** e FPT, p. 7 | Necessário porque o isolamento de MT passa longo período em patamar; o FPT poderia ser disparado por um evento (primeira manobra com reignições acima de limiar) em vez de por curtose. | [INFERÊNCIA] |
| **Múltiplas condições operacionais** — normalização multirregime [26] e BLSTM que recebe as condições como entrada [25], p. 20–21 | O "regime" do motor (partida normal, partida N-1 com *load shedding*, manobra com/sem snubber) entra como covariável de entrada do modelo; a normalização por regime evita que a variação de regime seja confundida com degradação. Ligação direta com o trabalho B. | [INFERÊNCIA] |
| **Escassez de falhas e uso de dados simulados** [116], p. 17, 21 | Motores de MT raramente operam até a falha (o artigo cita exatamente essa razão, p. 17). O repositório já gera, via ATP, formas de onda e contagens de reignição; essas simulações podem alimentar o estágio de pré-treinamento (transferência simulação→campo), como o artigo sugere. | [INFERÊNCIA] |
| **Transferência de aprendizado** com alerta de transferência negativa, p. 17 | Transferir de uma frota/ensaio acelerado para um motor único exige verificar o sentido "múltiplas condições → condição única", que o artigo aponta como problemático. | [INFERÊNCIA] |
| **Quantificação de incerteza** — bootstrap, MC dropout, GPR, camada gaussiana, p. 21 | Indispensável para decisão de manutenção (o artigo o afirma em p. 15 e 21); é o que permite entregar ao C-Level uma RUL com intervalo, não um número. | [INFERÊNCIA] |
| **Ensemble multiobjetivo** (acurácia × diversidade; MOEA/D; DE; menção a NSGA-II na ref. [148]), p. 20, 24 | Ponte metodológica com o trabalho B (NSGA-II/NSGA-III e surrogates): a mesma maquinaria de otimização multiobjetivo pode selecionar/ponderar membros do ensemble de RUL. | [INFERÊNCIA] |
| **Híbrido filtro de partículas + rede neural** [137], p. 18–19 | Modelo de referência para um híbrido física–dados em que a evolução do HI segue lei de envelhecimento (térmico/elétrico) e a rede corrige o resíduo. | [INFERÊNCIA] |
| **Custo computacional e criticidade temporal** (5.4.3), p. 24 | Argumento para dimensionar o módulo como *offline batch* + inferência leve, e para justificar surrogates. | [INFERÊNCIA] |

### 9.2 O que não se transfere e por quê

1. **Indicadores:** nenhum indicador do artigo é de isolamento; os exemplos (vibração, capacidade de bateria, ciclos de turbofan) não têm análogo direto. As grandezas relevantes (DP, tan δ, capacitância, resistência de isolamento, temperatura de ponto quente) terão de vir de outras fontes [INSERIR CITAÇÃO]. [INFERÊNCIA]
2. **Natureza do estresse:** o framework pressupõe séries temporais regulares de sensores com degradação gradual. O estresse de manobra de VCB é **impulsivo e esparso** (dezenas de eventos por ano, cada um com duração de µs e dV/dt elevado), e o estresse térmico de partida N-1 é **episódico**. Nenhum dos modos P2P/S2P/S2S (p. 7–8) contempla entradas do tipo "sequência de eventos com marcas temporais irregulares"; seria preciso um estágio adicional de agregação de eventos (contagem, severidade acumulada) antes do framework. [INFERÊNCIA]
3. **Escala temporal de aquisição:** os modelos revisados operam sobre ciclos/janelas de segundos a horas; a caracterização de frentes íngremes exige aquisição em ns–µs, que só faz sentido como pré-processamento físico (extração de dV/dt máximo, número de reignições, energia do surto), não como entrada bruta de CNN/LSTM. [INFERÊNCIA]
4. **Definição de falha:** a eq. (1) assume T observável. Para isolamento de MT, a "falha" pode ser ruptura súbita sob um surto específico, dependente do estresse aplicado naquele instante, o que torna T uma variável aleatória condicionada ao estresse futuro — formulação ausente no artigo. [INFERÊNCIA]
5. **Validação:** o artigo não oferece protocolo de validação (métricas, particionamento por unidade, *leakage*) além de menções a CRA, α-λ e K-fold. Um protocolo para ativos únicos com histórico censurado terá de ser construído a partir de outras fontes [INSERIR CITAÇÃO]. [INFERÊNCIA]
6. **Mitigação:** o artigo não trata de ações que alteram a trajetória de degradação (como o snubber do trabalho A ou o *load shedding* do trabalho B). O framework é passivo (observa e prediz); o problema-alvo exige acoplar a RUL a decisões que modificam o estresse — o que está mais próximo do escopo de PHM com mitigação (cf. fichamento 09, Strangas et al.). [INFERÊNCIA]

### 9.3 Nota

**Nota: 2/5.** Justificativa: transfere-se a arquitetura conceitual (framework, critérios de HI, tratamento de regimes múltiplos, escassez de dados, incerteza, ensembles multiobjetivo) e um catálogo de arquiteturas com referências; não se transfere nenhum indicador, dado, equação de degradação, protocolo de ensaio ou resultado. O artigo é útil como **mapa e vocabulário** para a seção de revisão de literatura da tese e para justificar o desenho de um pipeline em três estágios, mas não sustenta sozinho nenhuma escolha específica de modelo para isolamento de estator sob surtos de VCB ou partidas N-1. [INFERÊNCIA]

---

## 10. Citações literais relevantes

1. "Remaining useful life (RUL) is the useful life left in an asset at a particular time of operation. It is a crucial technology in health management. Accurate RUL prediction provides instructions for system design, production, and maintenance. For device maintenance, its costs constitute a large portion of the operating and overhead expenses in industries." (p. 1)
2. "Currently, there is no clear definition of remaining useful life (RUL). It is even difficult to define the failure time of a system. Generally, the remaining useful life is defined as the time length from current time point to the failure time point intuitively." (p. 5)
3. "Three key properties of HI are monotonicity, trendability, and prognosability. Monotonicity requires that the equipment does not undergo self-healing, which would result in non-monotonic trends. Trendability indicates the degree to which the evolution of the health indicator has the same shape and can be described by the same functional form. Prognosability measures the variance of the HI values at failure time." (p. 8)
4. "Most research in the literature assumes that the degradation is not noticeable, and the RUL will be piecewise continuous, such that the RUL is constant at the beginning and then decreases linearly. However, this assumption often makes these models impractical for real-world tasks." (p. 7)
5. "A major challenge in data-driven prognostics is that it is often difficult to obtain a large number of failure samples. This situation arises for several reasons: (1) running until failure is not permitted for critical assets; (2) many failures occur slowly and follow a degradation path, which might take months or even years." (p. 17)
6. "Maintenance in real-world applications is usually based on the RUL probability distribution function (PDF). However, the LSTM model is unable to obtain uncertainties. This problem is not thoroughly researched in the literature." (p. 15)
7. "Deterministic prediction values may not sufficient for RUL based operation decisions like maintenance. If the RUL prediction interval can be estimated, it would provide more information for operation decision. Lacking uncertainty representation is currently a common disadvantage of deep learning methods." (p. 21)
8. "Within this survey, few works concern the costs, especially for the computations, of various deep learning models. [...] However, accurate RUL prediction should be carried out in a time-critical manner in order to finally realize the benefit from deep-learning-based RUL prediction." (p. 24)

---

## 11. Ligações com os outros temas

### 11.1 RUL
- Definição formal mínima (eq. (1), p. 6) e reconhecimento de que a definição operacional de falha é aberta (p. 5). [FATO]
- Taxonomia dos métodos: *model-based* vs. *data-driven*; dentro de *data-driven*, TDD (regressão, movimento browniano, processos gama, markovianos; filtragem estocástica, modelos de risco com covariáveis, HMM/HSMM [8]), SNN e DNN (p. 2, 5). [FATO] — útil para posicionar o método proposto na tese.
- Quatro deficiências dos métodos tradicionais: dependência de modelos físicos, fusão de dados multidimensionais, modelagem de variáveis ambientais externas, múltiplos modos de falha (p. 2). [FATO] — [INFERÊNCIA] as três últimas são exatamente as dificuldades do problema-alvo (múltiplos sensores, regimes N-1 e manobras como variáveis externas, modos térmico e elétrico de envelhecimento).

### 11.2 PHM
- Distinção diagnóstico (detecção, isolamento, identificação após a anomalia) vs. prognóstico (predição de falha e degradação antes de ocorrerem); "o diagnóstico já foi amplamente estudado e aplicado na indústria. O prognóstico, que não fez progresso significativo, é o foco desta revisão" (p. 2). [FATO]
- PHM tem objetivo "mais amplo" que RUL: monitora parâmetros, detecta anomalia, diagnostica e então prognostica (p. 5). [FATO]
- Áreas ativas: aeroespacial, automotiva, nuclear, controle de processos e defesa [3] (p. 2). [FATO]
- Ativos de missão crítica: "no caso de ativos de missão crítica como uma usina nuclear, uma única falha significa um desastre" (p. 21). [FATO] — [INFERÊNCIA] argumento análogo para motores de MT de processo contínuo em refinarias/plataformas, se a hipótese de contexto industrial se confirmar.

### 11.3 C-Level (custo, decisão, manutenção) — transcrições com página
- Custo de manutenção: "For device maintenance, its costs constitute a large portion of the operating and overhead expenses in industries. Hence, both academia and industry are committed to promoting RUL prediction technology for better maintenance strategies." (p. 1) [FATO]
- Três estratégias de manutenção: corretiva (menor número de eventos, mas "frequentemente encurta a vida útil dos ativos devido a danos irreversíveis causados pela falha"); TBM (assume MTBF conhecido "estatística ou experiencialmente"); CBM ("visa realizar a manutenção no ponto ótimo de tempo com base na informação de condição coletada") (p. 1–2). [FATO]
- Limitação da CBM sem prognóstico: "the deviations may not necessarily equate to failure in case of operating condition changes or acceptable degradation levels" (p. 1). [FATO] — [INFERÊNCIA] este é o argumento executivo para ir além de alarmes de DP/tan δ e entregar RUL: desvio não é falha.
- Indústria 4.0 e "necessidade urgente" de RUL acurada (p. 2); "RUL prediction is promoted by industry needs, and deep learning is considered a revolutionary technology" (p. 5). [FATO]
- Decisão sob incerteza: citações 6 e 7 de §10 (p. 15, 21). [FATO]
- Custo computacional e criticidade temporal: citação 8 de §10 (p. 24). [FATO]
- Estado de adoção: "RUL prediction has still not been widely used in real systems" (p. 21). [FATO] — [INFERÊNCIA] ao apresentar um módulo computacional a executivos, este trecho apoia a narrativa de que a entrega é um protótipo de pesquisa com validação progressiva, não um produto maduro.

### 11.4 Ligação com os trabalhos A e B
- **A (snubber tiristorizado):** nenhuma ligação direta no texto. Ligação indireta pela recomendação de usar dados simulados quando não há falhas registradas (p. 17, 21) — o modelo de reignição do repositório é a fonte natural desses dados — e pela necessidade de tratar o regime "com/sem snubber" como condição operacional (p. 20–21). [INFERÊNCIA]
- **B (load shedding N-1, NSGA-II/III, surrogates):** ligação metodológica pela formulação multiobjetivo (acurácia × diversidade) de ensembles e de hiperparâmetros (p. 9, 20, 24) e pela citação de MOEA/D e NSGA-II [148] (p. 20, 30); ligação de dados pela modelagem de múltiplas condições operacionais (p. 20–21, 24). [INFERÊNCIA]
