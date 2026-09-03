# Fichamento exaustivo e crítico — Documento B

**Arquivo-fonte:** `/tmp/claude-0/-home-user-olivas-power-system-studio/9d851478-5457-5818-8269-a836133b8dbc/scratchpad/papers_AB/txt/B_sepoc_load_shedding.txt` (6 páginas, marcadores `===== PAGE N =====`).

**Convenção de rótulos (regra "zero suposição"):** [FATO: doc B, p. N] transcrição ou paráfrase direta do texto; [FATO: doc A, p. N] idem para o Documento A (verificado no arquivo `A_sepoc_snubber.txt`); [NORMA: id, cláusula] norma citada, cláusula quando conhecida; [LITERATURA: ref verificada, URL] fonte externa verificada nesta sessão; [INFERÊNCIA FÍSICA / ARITMÉTICA: derivação explícita] conclusão derivada do texto por raciocínio explícito; [HIPÓTESE] conjectura sem suporte textual; [FATO: ausência] afirmação de que o texto NÃO contém determinado conteúdo (verificada por leitura integral).

**Notas de transcrição:** o extrator de texto achatou sobrescritos e subscritos. "219 scenarios" (p. 1, resumo) corresponde a 2^19 = 524 288, número que o próprio texto explicita no corpo (p. 1, "524 288 candidate scenarios"). Símbolos como `V (INRUSH) min` correspondem a $V_{\min}^{(\text{INRUSH})}$; `S(sust) T R` a $S_{TR}^{(\text{sust})}$; `Kir` a $K_{ir}$; `R2` a $R^2$. A sentença "against the sparse fronts of the five-objective model. trade off between losses and shed production (Fig. 1)" (p. 3) é um fragmento editorial do original (frase truncada), transcrito como está.

---

## 1 Referência

Autores anônimos, "Selective Load Shedding for the Switching of Large Motors Under N-1 Contingency: Constrained Multiobjective Optimization with NSGA-II, NSGA-III and Regression Surrogates", submetido ao SEPOC 2026 (versão de primeira submissão, revisão duplo-cega; "Authors omitted for double blind review"). [FATO: doc B, p. 1]

Palavras-chave declaradas: evolutionary computation, genetic algorithms, induction motors, industrial power systems, load shedding, Pareto optimization, power system security, power system simulation, regression analysis. [FATO: doc B, p. 1]

Ferramentas declaradas: OpenDSS [13] via `py-dss-interface`, Python 3, pymoo [12]; reprodução integral com `python -m src.sepoc_study`; link do repositório retido para revisão cega. [FATO: doc B, p. 3]

---

## 2 Objetivo

1. Construir uma ferramenta prática de análise para a decisão preventiva de corte seletivo de carga (load shedding) antes da partida direta (direct-on-line) de um motor de indução de grande porte em planta industrial operando sob contingência N-1, com base em estudos de fluxo de potência. [FATO: doc B, p. 1]
2. Responder a uma questão metodológica: por que o NSGA-III, esperado como superior ao NSGA-II para problemas com mais de três objetivos, ficou estatisticamente abaixo da busca aleatória numa formulação preliminar de cinco objetivos, e como corrigir a formulação. [FATO: doc B, p. 1]
3. Quatro contribuições declaradas: (i) reformular a decisão com limites de tensão como restrições de desigualdade, restando três objetivos conflitantes em toda a região factível; (ii) comparar NSGA-II, NSGA-III com direções de referência por energia dimensionadas à população, e busca aleatória sob orçamento igual; (iii) destilar uma diretriz de uso (NSGA-II para plantas pequenas com dois ou três objetivos; NSGA-III para sistemas grandes com muitos objetivos e tratamento correto de restrições); (iv) avaliar um surrogate de regressão para sistemas muito grandes, verificando sua exatidão contra o motor de cálculo exato. [FATO: doc B, p. 1–2]
4. Distinção declarada: os esquemas clássicos de undervoltage load shedding [3] agem após o distúrbio para deter o colapso de tensão; a decisão aqui é preventiva, tomada antes de uma manobra planejada. [FATO: doc B, p. 1]

---

## 3 Sistema estudado e parâmetros

| Item | Valor / descrição | Rótulo |
|---|---|---|
| Tipo de planta | Indústria de processo (process industry) | [FATO: doc B, p. 2] |
| Fonte equivalente | 13,8 kV; corrente de curto-circuito trifásica 15 kA; X/R = 12 | [FATO: doc B, p. 2] |
| Transformadores | Dois, em paralelo, dupla capacidade nominal (dual rated): 7,5 MVA em resfriamento a ar natural (AN) e 9 MVA em ar forçado (AF) | [FATO: doc B, p. 2] |
| Impedância | $X_{HL}$ = 8 % na base 7,5 MVA | [FATO: doc B, p. 2] |
| Conexão | ΔYn (primário em delta, secundário em estrela aterrada) | [FATO: doc B, p. 2] |
| Barra secundária | Barra única de 4,16 kV | [FATO: doc B, p. 2] |
| Motores | $n_m$ = 20 motores de indução, todos na barra de 4,16 kV: um alvo (target) de 1250 kW (cos φ = 0,89) mais 19 máquinas de 75 a 1100 kW | [FATO: doc B, p. 2] |
| Carga estática | 3,6 MW | [FATO: doc B, p. 2] |
| Demanda plena | 18,2 MVA ("full plant demand"), que "dobra" a capacidade AF de 9 MVA | [FATO: doc B, p. 2] |
| Proteção do transformador | Réplica térmica (função ANSI 49 da tabela de dispositivos [18]) referida ao estágio AF, com retaguarda de sobrecorrente temporizada (função 51) | [FATO: doc B, p. 2] |
| Proteções de tensão | ANSI 27 (subtensão) e ANSI 59 (sobretensão) | [FATO: doc B, p. 2, Tabela I] |
| Condição operativa | N-1: um transformador fora de serviço, o remanescente no estágio AF | [FATO: doc B, p. 2] |
| Limite de afundamento (ride-through) | $V^{ir}$ = 0,85 pu, "adotado neste estudo como ajuste típico de subtensão ANSI 27" | [FATO: doc B, p. 2] |
| Limite de sobretensão (swell) | $V^{sw}$ = 1,08 pu | [FATO: doc B, p. 2] |
| Limite térmico | $S_{AF}$ = 9 MVA (define o pickup da função 49) | [FATO: doc B, p. 2] |
| Tensão de inrush sem corte | 0,755 pu com todas as máquinas conectadas | [FATO: doc B, p. 2 e p. 3] |
| Espaço de decisão | $2^{N-1}$ = 2^19 = 524 288 cenários; cada um exige quatro fluxos de potência | [FATO: doc B, p. 1] |
| Custo por avaliação | ≈ 25 ms (quatro fluxos OpenDSS) para a planta de 20 motores | [FATO: doc B, p. 5] |
| Nomes de máquinas citados | M_710, M_800 (Tabela III) | [FATO: doc B, p. 3] |

Observações críticas sobre a planta:

- A lista individual das 19 máquinas (potência, fator de potência, rendimento, corrente de rotor bloqueado) NÃO consta do texto; o artigo remete aos arquivos CSV do repositório, cujo link foi retido. [FATO: ausência; doc B, p. 3]
- A soma das potências nominais das 19 máquinas pode ser derivada de $f_5$ = 8927 kW no ponto em que nenhuma máquina é mantida (Tabela III): $\sum_i P_{n,i}$ = 8927 kW. Com o alvo (1250 kW) e a carga estática (3,6 MW), a potência ativa nominal instalada seria 13 777 kW. Confrontada com a demanda declarada de 18,2 MVA, isso implicaria fator de potência global ≈ 0,76 caso os kW fossem potência elétrica de entrada em regime nominal; o artigo não informa fatores de potência nem rendimentos das 19 máquinas nem da carga estática, logo a coerência não pode ser fechada com o texto. [INFERÊNCIA ARITMÉTICA: derivação explícita; dados faltantes marcados como FATO: ausência]
- Os nomes M_710 e M_800 aparentam codificar a potência em kW: 8927 − 7417 = 1510 kW = 710 + 800, exatamente o valor "preserving 1510 kW of production" (p. 3), e 8927 − 8127 = 800 kW. [INFERÊNCIA ARITMÉTICA a partir de doc B, p. 3, Tabela III]
- O cenário com todas as máquinas conectadas carrega o transformador a 2,03 × AF = 18,3 MVA, coerente com a demanda plena de 18,2 MVA. [INFERÊNCIA ARITMÉTICA: 2,03 × 9 MVA; doc B, p. 2–3]

---

## 4 Modelagem

### 4.1 Vetor de decisão e snapshots de fluxo de potência

- Vetor binário $s \in \{0,1\}^{n_m - 1}$, com $s_i = 1$ mantendo a máquina $i$ conectada. [FATO: doc B, p. 2]
- Cada candidato é avaliado com quatro fluxos de potência quase-estáticos no OpenDSS: [FATO: doc B, p. 2]
  1. PRE-ENERG — alvo desligado;
  2. INRUSH — alvo representado como carga de impedância constante de rotor bloqueado, $K_{ir}$ = 6,5, $\cos\varphi_{lr}$ = 0,20;
  3. PRE-DISC — alvo em operação nominal;
  4. POST-DISC — alvo desconectado.
- Em cada snapshot $k$ registram-se $V_{\min}^{(k)}$, $V_{\max}^{(k)}$, $N_{viol}^{(k)}$, perdas e $S_{TR}^{(k)}$ (Algoritmo 1, linha 4). [FATO: doc B, p. 3]

### 4.2 Modelo do motor alvo no snapshot INRUSH

- Carga de impedância constante em condição de rotor bloqueado, $K_{ir}$ = 6,5 e $\cos\varphi_{lr}$ = 0,20. [FATO: doc B, p. 2]
- Contexto geral declarado na introdução: "the locked-rotor current, typically 5 to 7 times the rated value at a power factor near 0.2, depresses the bus voltage for several seconds and may trip the ANSI 27 undervoltage protection of every neighboring load [1], [2]". [FATO: doc B, p. 1] — ATENÇÃO: a expressão "5 to 7 times" no Documento B refere-se ao múltiplo da corrente de rotor bloqueado, não a número de reignições; a premissa do usuário de "5 a 7 reignições por ciclo" NÃO tem correspondência no Documento B. [FATO: ausência]
- Consequências do modelo de impedância constante, derivadas do texto: com $Z_{lr}$ fixa, $I \propto V$ e $S \propto V^2$; a 0,85 pu, a corrente absorvida pelo alvo seria 0,85 × 6,5 ≈ 5,5 vezes a corrente nominal referida à tensão nominal. O artigo não explicita essa relação; ela decorre da definição de carga de impedância constante. [INFERÊNCIA FÍSICA: derivação explícita a partir de doc B, p. 2]
- Coerência com o Documento A: o mesmo alvo (1250 kW, 4,16 kV) e o mesmo múltiplo $I_p/I_n$ = 6,5 aparecem no Documento A. [FATO: doc A, p. 1]

### 4.3 Formulação preliminar (cinco objetivos, degenerada)

Minimização de cinco objetivos: [FATO: doc B, p. 2]

$$f_1 = \max\left(0,\; 0{,}85 - V_{\min}^{(\text{INRUSH})}\right) \quad \text{(severidade do afundamento)}$$

$$f_2 = \max\left(0,\; V_{\max}^{(\text{POST-DISC})} - 1{,}08\right) \quad \text{(severidade do swell)}$$

$f_3$ = violações de proteção; $f_4$ = perdas; $f_5$ = potência produtiva cortada; penalidades multiplicativas para candidatos infactíveis. [FATO: doc B, p. 2]

Diagnóstico do artigo: todo cenário factível tem afundamento e swell nulos, logo a frente colapsa em subespaço de dimensão efetiva três ou menor; algoritmos por direções de referência distribuem o esforço sobre um simplex de dimensão plena e, com frente degenerada, a maioria das direções nunca encontra solução e a pressão seletiva cai [10]. [FATO: doc B, p. 2]

### 4.4 Formulação corrigida (três objetivos + três restrições) — equações (1)–(4)

Com limites de ride-through $V^{ir}$ = 0,85 pu e $V^{sw}$ = 1,08 pu, o modelo lê-se: [FATO: doc B, p. 2]

$$\min_{s} \; F(s) = \left(f_3,\; f_4,\; f_5\right) \qquad (1)$$

$$f_3 = \sum_{k} N_{viol}^{(k)}(s)$$

$$f_4 = P_{losses}^{(\text{PRE-DISC})}(s) \quad [\text{kW}]$$

$$f_5 = \sum_{i:\, s_i = 0} P_{n,i} \quad [\text{kW}]$$

sujeito a

$$g_1 = V^{ir} - V_{\min}^{(\text{INRUSH})} \le 0 \qquad (2)$$

$$g_2 = V_{\max}^{(\text{POST-DISC})} - V^{sw} \le 0 \qquad (3)$$

$$g_3 = S_{TR}^{(\text{sust})} / S_{AF} - 1 \le 0 \qquad (4)$$

Definições declaradas: $N_{viol}^{(k)}$ conta violações de envelope de proteção no snapshot $k$; $f_4$ penaliza pontos de operação ineficientes; $f_5$ é a potência produtiva perdida pelo corte; $S_{TR}^{(\text{sust})}$ é a maior potência aparente através do transformador remanescente nos snapshots sustentados (PRE-ENERG, PRE-DISC, POST-DISC); $S_{AF}$ = 9 MVA é a capacidade em ar forçado que define o pickup da função 49. [FATO: doc B, p. 2]

Tratamento de restrições: constraint domination introduzido pelos autores do NSGA-III [6]. [FATO: doc B, p. 2]

Conflito declarado: manter mais máquinas conectadas reduz $f_5$ mas eleva perdas e pressão de violação; $f_3$ não se anula por construção no conjunto factível, pois (2)–(4) limitam apenas o afundamento de inrush, o swell pós-desconexão e a carga sustentada do transformador, enquanto $f_3$ conta violações nos quatro snapshots. [FATO: doc B, p. 2–3]

Numeração preservada: $f_3$ a $f_5$ mantêm os símbolos da formulação preliminar. [FATO: doc B, p. 2]

### 4.5 Exclusão do INRUSH de $g_3$ e não convergência

- O snapshot INRUSH é excluído de $g_3$ porque "dura cerca de 10 s, muito menos que a constante de tempo térmica de uma unidade imersa em óleo, e cai dentro da capacidade de carregamento de curta duração definida no guia de carregamento IEEE [19]; sua carga é, contudo, calculada e reportada". [FATO: doc B, p. 2]
- Fluxos que não convergem são declarados fortemente infactíveis: $g_1 = g_2 = g_3 = 1$ (Algoritmo 1, linhas 6–8: retorna F de pior caso e G = [1, 1, 1]). [FATO: doc B, p. 2–3]

### 4.6 Algoritmo 1 — avaliação exata de um plano $s$ (transcrição)

Requer: modelo de rede compilado; limites $V^{ir}$, $V^{sw}$, $S_{AF}$. [FATO: doc B, p. 3]
1. Aplicar os estados liga/desliga de $s$ às $n_m - 1$ máquinas.
2. Para cada $k \in$ {PRE-ENERG, INRUSH, PRE-DISC, POST-DISC}:
3. definir o estado do alvo no snapshot $k$; resolver o fluxo de potência;
4. registrar $V_{\min}^{(k)}$, $V_{\max}^{(k)}$, $N_{viol}^{(k)}$, perdas e $S_{TR}^{(k)}$.
5. Fim do laço.
6. Se algum snapshot não convergiu: retornar F de pior caso; G = [1, 1, 1].
9. $f_3 \leftarrow \sum_k N_{viol}^{(k)}$; $f_4 \leftarrow P_{losses}^{(\text{PRE-DISC})}$; $f_5 \leftarrow \sum_{i: s_i=0} P_{n,i}$.
10. $g_1 \leftarrow V^{ir} - V_{\min}^{(\text{INRUSH})}$; $g_2 \leftarrow V_{\max}^{(\text{POST-DISC})} - V^{sw}$.
11. $g_3 \leftarrow S_{TR}^{(\text{sust})}/S_{AF} - 1$ sobre os snapshots sustentados.
12. Retornar F = [$f_3$, $f_4$, $f_5$]; G = [$g_1$, $g_2$, $g_3$].

### 4.7 Algoritmos e protocolo experimental

| Parâmetro | Valor | Rótulo |
|---|---|---|
| Codificação | Binária, amostragem uniforme aleatória | [FATO: doc B, p. 3] |
| Cruzamento | Uniforme, $p_c$ = 0,9 | [FATO: doc B, p. 3] |
| Mutação | Bit-flip, $p_m$ = 0,15 | [FATO: doc B, p. 3] |
| Seleção | Constraint domination | [FATO: doc B, p. 3] |
| População / gerações | µ = 40; G = 20 (800 avaliações) | [FATO: doc B, p. 3] |
| Sementes | {42, …, 51} (10 sementes) | [FATO: doc B, p. 3] |
| NSGA-II [4] | Crowding distance | [FATO: doc B, p. 3] |
| NSGA-III [5] | Direções de referência por energia de Riesz (s-energy) [9], dimensionadas à população: \|W\| = µ = 40 em três dimensões | [FATO: doc B, p. 3] |
| U-NSGA-III [7] | Variante unificada, conforme implementada no pymoo [12] | [FATO: doc B, p. 3] |
| Busca aleatória | Vetores binários uniformes, mesmo orçamento; arquiva o conjunto factível não dominado | [FATO: doc B, p. 3] |
| Métrica | Hipervolume (HV) [11] do conjunto factível não dominado, ponto de referência comum com margem de 10 % sobre a união de todas as execuções | [FATO: doc B, p. 3] |
| Teste estatístico | Wilcoxon pareado de postos sinalizados, α = 0,05 | [FATO: doc B, p. 3] |
| Estudo preliminar (5 objetivos) | Direções Das–Dennis [8], 35 para 5 objetivos; 800 avaliações; variante memética = NSGA-II binário + busca local | [FATO: doc B, p. 2] |

### 4.8 Surrogate de regressão e Algoritmo 2

- Dados de treino: cenários avaliados em todas as execuções dos estudos de otimização, deduplicados, apenas casos convergidos: 14 343 cenários únicos. [FATO: doc B, p. 5]
- Modelos: regressão ridge quadrática sobre as interações par a par dos 19 bits, e random forest; validação cruzada de 5 dobras; alvos: $V_{\min}^{(\text{INRUSH})}$ (que governa $g_1$) e perdas $f_4$. [FATO: doc B, p. 5]
- Para variáveis binárias, $x_i^2 = x_i$, de modo que o modelo quadrático reduz-se a 19 termos lineares + C(19,2) = 171 termos par a par = 190 regressores (mais intercepto). O artigo não declara a contagem de regressores. [INFERÊNCIA ARITMÉTICA a partir de doc B, p. 5]
- Justificativa física dada pelo artigo: "a tensão de barra responde de forma quase linear ao chaveamento de cargas individuais nesta escala, e os termos par a par capturam os efeitos de interação (Fig. 4)". [FATO: doc B, p. 5]
- Fig. 4: gráfico de paridade para $V_{\min}^{(\text{INRUSH})}$ (ridge quadrático, 30 % de teste retido; linha pontilhada marca 0,85 pu). Observação: a Tabela VI usa validação cruzada de 5 dobras; a Fig. 4 usa hold-out de 30 %; são protocolos distintos. [FATO: doc B, p. 5]
- Orçamento de avaliações exatas com razão de triagem ρ: ρµG + µ, redução por fator ≈ 1/ρ, "da mesma ordem da aceleração reportada para triagem aprendida de contingências [16]". [FATO: doc B, p. 5]

Algoritmo 2 — laço com triagem por surrogate para sistemas muito grandes (transcrição): [FATO: doc B, p. 5]

Requer: tamanho da população µ, gerações G, razão de triagem ρ.
1. Avaliar a população inicial com o Algoritmo 1; armazenar os resultados no arquivo A.
2. Ajustar o regressor $\hat{h}$ (bits do plano → $\hat{g}_1$ e objetivos) sobre A.
3. Para t = 1 até G:
4. gerar µ descendentes por seleção, cruzamento e mutação;
5. ordenar os descendentes por margem de factibilidade e objetivos preditos por $\hat{h}$;
6. avaliar a melhor fração ρ com o Algoritmo 1; adicionar os resultados a A;
7. aplicar seleção ambiental apenas sobre soluções avaliadas exatamente;
8. reajustar $\hat{h}$ sobre A em intervalos fixos.
9. Fim do laço.
10. Retornar o conjunto factível não dominado de A, cada membro verificado pelo fluxo de potência exato.

Garantia declarada: "Erros de predição podem degradar a eficiência da busca, mas nunca produzem uma recomendação de corte não verificada, porque a factibilidade final é sempre confirmada pelo fluxo de potência completo". [FATO: doc B, p. 5]

Estado do Algoritmo 2 no artigo: é PROPOSTO ("we therefore propose"); o artigo reporta apenas a exatidão do surrogate (Tabela VI, Fig. 4). Não há resultado de execução do Algoritmo 2 (HV, tempo, número de avaliações exatas economizadas) no texto. [FATO: ausência; doc B, p. 5]

---

## 5 Resultados numéricos

### 5.1 Tabela I — funções ANSI representadas no modelo [18] (p. 2)

| ANSI | Função | Papel no modelo |
|---|---|---|
| 27 | Subtensão | Limite de afundamento, restrição $g_1$ e contagem $f_3$ |
| 59 | Sobretensão | Limite de swell, restrição $g_2$ e contagem $f_3$ |
| 49 | Sobrecarga térmica | Carregamento do transformador, restrição $g_3$ na capacidade AF |
| 51 | Sobrecorrente temporizada | Retaguarda da 49; envelopada por $g_3$ em regime permanente |

[FATO: doc B, p. 2]

### 5.2 Tabela II — estudo de dez sementes, formulação de cinco objetivos (p. 2)

Direções Das–Dennis [8], 35 para 5 objetivos; 800 avaliações. HV: hipervolume; IGD: inverted generational distance (menor é melhor).

| Algoritmo | HV (mediana) | IGD | vs. aleatória (Wilcoxon) |
|---|---|---|---|
| NSGA-II (memético) | 384 984 | 84,8 | p = 0,0195 |
| NSGA-II (binário) | 369 313 | 102,1 | p = 0,7695 |
| Busca aleatória | 370 604 | 566,0 | — |
| NSGA-III | 286 289 | 1287,9 | p = 0,0020 |

[FATO: doc B, p. 2]

Texto associado: NSGA-III atingiu HV mediano 23 % abaixo da busca aleatória, com alta variância e mediana de apenas três soluções não dominadas por execução; apenas a variante binária pura do NSGA-II é levada ao estudo corrigido. [FATO: doc B, p. 2] Verificação: 286 289 / 370 604 = 0,772 → 22,8 % abaixo. [INFERÊNCIA ARITMÉTICA]

### 5.3 Tabela III — soluções factíveis representativas (NSGA-II, semente 42) (p. 3)

| Solução | Mantidas ligadas | $f_4$ [kW] | $f_5$ [kW] | $V_{\min}^{(\text{INR})}$ [pu] |
|---|---|---|---|---|
| Mínimo corte de potência | M_710, M_800 | 43,2 | 7417 | 0,850 |
| Joelho (knee) | M_800 | 34,6 | 8127 | 0,858 |
| Mínimas perdas | (nenhuma) | 26,5 | 8927 | 0,866 |

[FATO: doc B, p. 3]

### 5.4 Resultados textuais da Seção IV-A (p. 3)

- Com todas as máquinas conectadas o alvo não pode ser partido: $V_{\min}^{(\text{INRUSH})}$ = 0,755 pu. [FATO: doc B, p. 3]
- Uma única execução do NSGA-II (µ = 40, G = 20, semente 42) produz 467 avaliações factíveis de 800, cobrindo 316 cenários únicos, e retorna, sobre o arquivo de todos os cenários avaliados na execução, uma frente factível não dominada com 97 soluções. [FATO: doc B, p. 3]
- Extremo 1: todas as 19 máquinas cortadas ($f_4$ = 26,5 kW; $f_5$ = 8927 kW). Extremo 2: M_710 e M_800 permanecem conectadas, preservando 1510 kW de produção ($f_5$ = 7417 kW; $f_4$ = 43,2 kW); a restrição de afundamento está ativa, com $V_{\min}^{(\text{INRUSH})}$ = 0,850 pu, no limite de ride-through. Solução joelho: mantém M_800 ($f_5$ = 8127 kW; $V_{\min}^{(\text{INRUSH})}$ = 0,858 pu). [FATO: doc B, p. 3]
- O modelo restrito supera o melhor cenário do estudo de cinco objetivos, que cortava 7907 kW: pressionar a busca contra uma fronteira explícita de restrição recupera 490 kW de produção. [FATO: doc B, p. 3] Verificação: 7907 − 7417 = 490 kW. [INFERÊNCIA ARITMÉTICA]
- Transformador no plano recomendado: carga sustentada de 7,31 MVA = 81 % da capacidade AF, mas 97 % da capacidade AN; sem ar forçado o plano operaria a menos de 3 % do pickup da função 49, sem margem prática. [FATO: doc B, p. 3] Verificação: 7,31/9 = 0,812; 7,31/7,5 = 0,975. [INFERÊNCIA ARITMÉTICA]
- Durante o inrush de 10 s a potência aparente atinge 1,38 vezes a capacidade AF, "dentro da capacidade de curta duração do guia de carregamento [19] e invisível ao elemento térmico". [FATO: doc B, p. 3] Equivalente: 1,38 × 9 = 12,4 MVA. [INFERÊNCIA ARITMÉTICA]
- $g_3$ permanece inativa ao longo de toda a frente factível, pois $g_1$ (tensão) satura primeiro nesta planta; o cenário com todas as máquinas viola ambas, com o transformador a 2,03 vezes a capacidade AF, de modo que a proteção de sobrecarga por si só o proibiria. [FATO: doc B, p. 3]

### 5.5 Tabela IV — hipervolume final e factibilidade, 10 sementes, formulação corrigida (p. 4)

µ = 40, G = 20, 800 avaliações. |P|: tamanho do conjunto factível não dominado final; |P| e avaliações factíveis são médias sobre as 10 sementes.

| Algoritmo | HV (mediana) | HV (desvio-padrão) | \|P\| | Avaliações factíveis |
|---|---|---|---|---|
| NSGA-II | 220 533 | 713 | 40 | 435/800 |
| NSGA-III | 212 884 | 508 | 8 | 480/800 |
| U-NSGA-III | 213 210 | 256 | 8 | 467/800 |
| Aleatória | 142 840 | 25 821 | 4,5 | 4,7/800 |

[FATO: doc B, p. 4]

### 5.6 Tabela V — teste de Wilcoxon pareado sobre HV (10 sementes, α = 0,05) (p. 4)

| Comparação | valor-p | Significativo |
|---|---|---|
| NSGA-II vs. NSGA-III | 0,0020 | sim |
| NSGA-II vs. aleatória | 0,0020 | sim |
| NSGA-III vs. aleatória | 0,0020 | sim |
| NSGA-III vs. U-NSGA-III | 0,0137 | sim |

[FATO: doc B, p. 4]

### 5.7 Resultados textuais da Seção IV-B (p. 3–4)

- Reversão do resultado do NSGA-III: 23 % abaixo da aleatória na formulação degenerada; 49 % acima da aleatória em HV mediano (p = 0,002) e 96,5 % do valor do NSGA-II na formulação corrigida; "do último lugar a um segundo lugar próximo" com o mesmo algoritmo, orçamento e planta. [FATO: doc B, p. 3–4] Verificações: 212 884/142 840 = 1,490; 212 884/220 533 = 0,965. [INFERÊNCIA ARITMÉTICA]
- As duas correções (constraint handling de [6]; dimensionamento de direções de [5], [9]) foram aplicadas conjuntamente; os hipervolumes das duas formulações são calculados em espaços de objetivos diferentes, logo apenas a ordenação dentro de cada estudo é comparável; isolar a contribuição de cada correção fica para trabalho futuro. [FATO: doc B, p. 4]
- A busca aleatória colapsa quando a factibilidade importa: apenas 0,6 % dos cenários aleatórios uniformes satisfazem (2)–(4), contra 54 % a 60 % de avaliações factíveis alcançadas por constraint domination. [FATO: doc B, p. 4] Verificação: 4,7/800 = 0,59 %; 435/800 = 54,4 %; 480/800 = 60,0 %. [INFERÊNCIA ARITMÉTICA]
- NSGA-II mantém vantagem pequena e significativa sobre NSGA-III a três objetivos (+3,6 %, p = 0,002); U-NSGA-III tem vantagem leve mas significativa sobre NSGA-III (p = 0,0137). [FATO: doc B, p. 4] Verificação: 220 533/212 884 = 1,036. [INFERÊNCIA ARITMÉTICA]
- Figs. 1–3 (não transcritas no texto extraído): Fig. 1 — soluções factíveis não dominadas (união de 10 sementes), $f_4$ contra $f_5$, frente densa e bem espalhada para todos os algoritmos; Fig. 2 — HV final sobre 10 sementes; Fig. 3 — HV mediano por geração com bandas interquartis. [FATO: doc B, p. 4, legendas]

### 5.8 Tabela VI — exatidão do surrogate, validação cruzada de 5 dobras, 14 343 cenários únicos (p. 5)

| Alvo | Modelo | $R^2$ | MAE |
|---|---|---|---|
| $V_{\min}^{(\text{INR})}$ [pu] | Ridge (quadrático) | 0,9999 | 8,5 × 10⁻⁵ |
| $V_{\min}^{(\text{INR})}$ [pu] | Random forest | 0,977 | 2,1 × 10⁻³ |
| $f_4$ [kW] | Ridge (quadrático) | 0,9999 | 0,24 |
| $f_4$ [kW] | Random forest | 0,974 | 3,7 |

[FATO: doc B, p. 5]

Texto associado: o modelo ridge reproduz a tensão de inrush do OpenDSS com $R^2$ > 0,999 e erro absoluto médio abaixo de 10⁻⁴ pu, "cerca de 0,01 % da nominal, mais apertado que qualquer tolerância prática de ajuste de proteção". [FATO: doc B, p. 5] Verificação: 8,5 × 10⁻⁵ pu = 0,0085 % ≈ 0,01 %. [INFERÊNCIA ARITMÉTICA]

### 5.9 Custo computacional (p. 5)

- ≈ 25 ms por avaliação (quatro fluxos OpenDSS) para a planta de 20 motores. [FATO: doc B, p. 5]
- Nota crítica: a esse custo, a enumeração exaustiva dos 524 288 cenários exigiria ≈ 524 288 × 0,025 s ≈ 3,6 h de processamento sequencial; a afirmação de que a enumeração é "impraticável" (p. 1) deve ser lida como relativa, e o próprio artigo situa a motivação do surrogate em sistemas "com centenas de barras, modelos detalhados de alimentadores ou verificação dinâmica" (p. 5). [INFERÊNCIA ARITMÉTICA a partir de doc B, p. 1 e p. 5]
- Uma execução (800 avaliações) custa ≈ 20 s. [INFERÊNCIA ARITMÉTICA: 800 × 25 ms]

### 5.10 Conclusão (p. 5–6)

- Plano recomendado: mantém duas grandes máquinas secundárias conectadas e parte o alvo de 1250 kW com a restrição de afundamento ativa em 0,85 pu, preservando 490 kW de produção em relação à formulação anterior; o plano só é sustentável no estágio AF do transformador, cuja carga atinge 97 % da capacidade AN. [FATO: doc B, p. 5]
- Trabalho futuro: aplicar o pipeline a alimentadores públicos de grande escala (EPRI ckt24 e IEEE 8500-node test feeder) com triagem por surrogate ativa, e validar cenários selecionados em simulação dinâmica. [FATO: doc B, p. 5–6]

---

## 6 Mecanismos físicos invocados e referências de suporte

| Mecanismo | O que o artigo afirma | Rótulo / suporte |
|---|---|---|
| Afundamento de tensão na partida direta | Corrente de rotor bloqueado tipicamente 5–7 × $I_n$ a FP ≈ 0,2 deprime a tensão de barra por vários segundos e pode atuar a ANSI 27 das cargas vizinhas [1], [2] | [FATO: doc B, p. 1]; suporte externo: IEEE Std 3002.7-2018 (estudos de partida de motores: corrente de partida e queda de tensão) [LITERATURA: verificada, https://ieeexplore.ieee.org/document/8700700/; cláusula não identificada] |
| Modelo do motor no inrush | Carga de impedância constante, $K_{ir}$ = 6,5, $\cos\varphi_{lr}$ = 0,20 | [FATO: doc B, p. 2]; consequência $I \propto V$, $S \propto V^2$ [INFERÊNCIA FÍSICA: definição de impedância constante] |
| Térmica do transformador | Réplica térmica ANSI 49 referida ao estágio AF; inrush de ≈ 10 s "muito menor que a constante de tempo térmica de uma unidade imersa em óleo"; carga de curta duração admissível pelo guia IEEE C57.91 [19]; 1,38 × AF por 10 s "invisível ao elemento térmico" | [FATO: doc B, p. 2–3]; [NORMA: IEEE Std C57.91-2011, cláusula não citada pelo artigo] [LITERATURA: verificada, https://ieeexplore.ieee.org/document/6166928]. O artigo NÃO informa o valor da constante de tempo térmica nem calcula temperatura de ponto quente ou perda de vida do transformador. [FATO: ausência] |
| Dupla capacidade AN/AF | Carga sustentada de 7,31 MVA = 81 % AF / 97 % AN; sem ar forçado, margem < 3 % até o pickup da 49 | [FATO: doc B, p. 3] |
| Swell pós-desconexão | Limite $V^{sw}$ = 1,08 pu sobre $V_{\max}^{(\text{POST-DISC})}$ | [FATO: doc B, p. 2]. O mecanismo físico do swell não é explicado no texto; fisicamente, a remoção da carga do alvo reduz a queda de tensão em $X_{HL}$ e eleva a tensão da barra com carga reduzida. [INFERÊNCIA FÍSICA: queda de tensão em reatância série] |
| Linearidade tensão-carga | "A tensão de barra responde quase linearmente ao chaveamento de cargas individuais nesta escala"; termos par a par capturam interações | [FATO: doc B, p. 5] |
| Conflito perdas × produção | Manter mais máquinas reduz $f_5$ e eleva $f_4$ e pressão de violação | [FATO: doc B, p. 2–3] |
| Degeneração da frente de Pareto | Objetivos que se anulam no conjunto factível colapsam a frente; algoritmos por decomposição dependem da forma da frente [10]; direções não dimensionadas à população ficam vazias [9] | [FATO: doc B, p. 2, p. 4] |

Mecanismos térmicos do MOTOR relevantes ao contexto do usuário, mas AUSENTES no Documento B:

- Aquecimento Joule de estator e rotor durante a partida, proporcional a $\int I^2 dt$; para corrente de rotor bloqueado aproximadamente constante durante a aceleração, o aquecimento cresce com $I_{lr}^2 \cdot t_{acc}$. [INFERÊNCIA FÍSICA: efeito Joule; NÃO consta do doc B — FATO: ausência]
- Dependência do tempo de aceleração com a tensão: para motor de indução o conjugado varia com $V^2$; a 0,85 pu, o conjugado de partida é ≈ 72 % do valor à tensão nominal, prolongando a aceleração. [INFERÊNCIA FÍSICA: $T \propto V^2$ para o modelo de circuito equivalente do motor de indução; NÃO consta do doc B — FATO: ausência]
- Curvas de limite térmico de máquinas de indução com rotor em gaiola (rotor bloqueado a quente/frio, aceleração): IEEE Std 620-1996 (reafirmada 2008; substituída por IEEE 620-2022). [LITERATURA: verificada, https://ieeexplore.ieee.org/document/511267/; cláusula não identificada]
- Níveis de suportabilidade a impulso de bobinas pré-formadas de estator (3–15 kV): IEC 60034-15:2009 (Ed. 3.0) e IEC 60034-15:2025 (Ed. 4.0). [NORMA: IEC 60034-15; cláusula não identificada] [LITERATURA: verificada, https://webstore.ansi.org/standards/iec/IEC6003415Ed2009 e https://knowledge.bsigroup.com/products/rotating-electrical-machines-part-15-impulse-voltage-withstand-levels-of-form-wound-stator-coils-for-rotating-a-c-machines]. O Documento B NÃO cita a IEC 60034-15. [FATO: ausência]

---

## 7 Normas citadas e como são usadas

| Norma | Ref. no artigo | Uso no texto | Rótulo |
|---|---|---|---|
| IEEE Std 399-1997 (Brown Book) | [1] | Citada na introdução como suporte à afirmação de que a corrente de rotor bloqueado (5–7 × $I_n$, FP ≈ 0,2) deprime a tensão por vários segundos e pode atuar a ANSI 27 | [FATO: doc B, p. 1, p. 6] |
| IEEE Std 3002.7-2018 (estudos de partida de motores) | [2] | Idem [1]; citada em par com [1] na introdução | [FATO: doc B, p. 1, p. 6] |
| IEEE Std C37.2-2008 (números de função de dispositivos) | [18] | Fonte da nomenclatura ANSI 27, 59, 49, 51 (Tabela I) e da "tabela de dispositivos ANSI" | [FATO: doc B, p. 2, p. 6] |
| IEEE Std C57.91-2011 (guia de carregamento de transformadores imersos em óleo mineral) | [19] | Justifica excluir o INRUSH (≈ 10 s) de $g_3$ pela "capacidade de carga de curta duração"; justifica que 1,38 × AF por 10 s é admissível e invisível ao elemento térmico | [FATO: doc B, p. 2, p. 3, p. 6] |
| Ajuste ANSI 27 = 0,85 pu | — | "Adotado neste estudo como ajuste típico"; não atribuído a cláusula de norma | [FATO: doc B, p. 2] |
| Ajuste ANSI 59 = 1,08 pu | — | Declarado como limite de swell; origem não informada | [FATO: doc B, p. 2]; [FATO: ausência de justificativa] |
| Pickup ANSI 49 = $S_{AF}$ = 9 MVA | — | Réplica térmica referida ao estágio AF; ANSI 51 como retaguarda "envelopada por $g_3$ em regime permanente" | [FATO: doc B, p. 2] |
| IEC 60034-15, IEC 60034-1, NEMA MG-1, IEEE 620, IEEE C37.96 (proteção de motores) | — | NÃO citadas | [FATO: ausência] |

---

## 8 O que o artigo NÃO afirma/modela (lista explícita)

Todos os itens abaixo foram verificados por leitura integral do texto (p. 1–6) e recebem o rótulo [FATO: ausência].

Modelagem do motor:
1. NÃO modela a térmica do MOTOR (nem estator nem rotor): não há réplica térmica ANSI 49 de motor, constante de tempo térmica de motor, temperatura de enrolamento ou classe térmica de isolamento.
2. NÃO calcula tempo de aceleração: não há curva conjugado-velocidade, conjugado de carga, inércia (H ou J), nem integração dinâmica da partida.
3. NÃO calcula $I^2 t$ do motor nem compara com curvas de limite térmico (rotor bloqueado a quente/frio, aceleração).
4. NÃO trata envelhecimento de isolamento, degradação acumulada, número admissível de partidas por hora/dia, nem vida útil restante (RUL); as palavras "aging", "insulation", "lifetime", "remaining useful life", "degradation" não ocorrem no texto.
5. NÃO informa o valor absoluto da corrente de rotor bloqueado (A), a tensão-dependência de $K_{ir}$, nem se 6,5 é referido à tensão nominal ou à tensão da barra.
6. NÃO deriva $K_{ir}$ = 6,5 nem $\cos\varphi_{lr}$ = 0,20 de dados de placa ou ensaio; são parâmetros declarados.
7. NÃO modela partida com tensão reduzida, soft-starter, inversor ou partida sequencial das máquinas cortadas (religamento pós-partida).
8. NÃO modela as 19 máquinas individualmente no texto (lista, FP, rendimento, prioridade de processo); remete aos CSV do repositório retido.

Fenômenos elétricos:
9. NÃO modela transitórios eletromagnéticos: sem disjuntor a vácuo, chopping, reignição, sobretensão de manobra, TRV, dv/dt, energia de surto, espectro — esse é o domínio do Documento A. A expressão "5 to 7" no Documento B refere-se ao múltiplo da corrente de rotor bloqueado (p. 1), não a reignições.
10. NÃO faz simulação dinâmica (RMS ou EMT); os quatro snapshots são fluxos de potência quase-estáticos; a validação dinâmica é declarada como trabalho futuro (p. 6).
11. NÃO modela harmônicos, desequilíbrio, afundamentos por faltas, nem estabilidade de tensão pós-distúrbio (o artigo distingue-se explicitamente do UVLS clássico [3]).
12. NÃO modela cabos, capacitores de correção de FP, geração local, comutação de tap ou regulação de tensão da fonte.
13. NÃO informa o método de solução do fluxo de potência no OpenDSS, tolerâncias, nem modelos ZIP das demais cargas (apenas o alvo em INRUSH é declarado como impedância constante).

Proteção e transformador:
14. NÃO informa temporizações da ANSI 27/59 (só os níveis 0,85 e 1,08 pu), nem curva da ANSI 51.
15. NÃO calcula temperatura de topo de óleo, ponto quente, perda de vida ou constante de tempo térmica do transformador; a IEEE C57.91 é invocada qualitativamente ("short duration loading capability"), sem cláusula ou tabela.
16. NÃO trata a dinâmica de acionamento dos ventiladores (transição AN → AF) nem a hipótese de falha do ar forçado além da observação de margem < 3 %.
17. NÃO modela os efeitos eletromecânicos do afundamento de tensão sobre as máquinas mantidas em operação (aumento de escorregamento, reaceleração, queda de contatores, redução de conjugado): as palavras "slip", "reacceleration" e "contactor" não ocorrem no texto. O único efeito do afundamento sobre as cargas vizinhas que o artigo considera é a atuação da proteção de subtensão ANSI 27 — "may trip the ANSI 27 undervoltage protection of every neighboring load" (p. 1) —, representada pelo limite de ride-through de 0,85 pu (p. 2), pela restrição $g_1$ e pela contagem $N_{viol}$ em $f_3$ (p. 2–3). [FATO: doc B, p. 1–3 para o que consta; FATO: ausência para escorregamento, reaceleração e contatores]

Duração do inrush:
18. NÃO calcula a duração do inrush: o valor "cerca de 10 s" (p. 2) e "o inrush de 10 s" (p. 3) é declarado, não derivado; na introdução fala-se em "vários segundos" (p. 1). Não há base numérica (inércia, conjugado) para os 10 s.

Otimização e surrogate:
19. NÃO isola o efeito de cada correção (restrições vs. dimensionamento de direções): aplicadas em conjunto (p. 4).
20. NÃO compara hipervolumes entre as duas formulações (espaços de objetivos distintos; p. 4).
21. NÃO testa a metade da diretriz relativa a "muitos objetivos" (> 3): "that half of the guideline rests on the literature" (p. 4).
22. NÃO executa o Algoritmo 2; apenas o propõe e mede a exatidão dos regressores (p. 5).
23. NÃO reporta hiperparâmetros do ridge (λ) nem do random forest; NÃO reporta o erro máximo (apenas $R^2$ e MAE); NÃO avalia o surrogate fora da distribuição visitada pelo otimizador.
24. NÃO reporta tempos de execução totais nem hardware (apenas ≈ 25 ms por avaliação).
25. NÃO apresenta custo econômico do corte, prioridade de processo, nem restrições operacionais de religamento; "shed load per priority class" e "switching counts" são mencionados apenas como objetivos possíveis em plantas maiores (p. 4).
26. NÃO fornece o link do repositório (retido para revisão cega; p. 3).

Contexto industrial:
27. NÃO menciona refinarias, plataformas, tensões 2,3–13,8 kV como classe, nem monitoramento on-line; a planta é descrita genericamente como "process industry" a 13,8/4,16 kV.
28. NÃO cita a IEC 60034-15 nem qualquer norma de isolamento de máquinas.

---

## 9 Limitações declaradas e limitações inferidas

### 9.1 Declaradas pelos autores

- As duas correções foram aplicadas conjuntamente; os HV das duas formulações estão em espaços diferentes; a contribuição de cada correção fica para trabalho futuro. [FATO: doc B, p. 4]
- A metade da diretriz relativa a muitos objetivos apoia-se na literatura, não nos dados do artigo. [FATO: doc B, p. 4]
- Erros de predição do surrogate podem degradar a eficiência da busca (embora nunca produzam recomendação não verificada). [FATO: doc B, p. 5]
- Validação dinâmica e aplicação a alimentadores grandes (EPRI ckt24, IEEE 8500) são trabalho futuro. [FATO: doc B, p. 5–6]
- Link do repositório retido (reprodutibilidade prometida, não verificável nesta versão). [FATO: doc B, p. 3]

### 9.2 Inferidas (rotuladas)

- $g_3$ permanece inativa ao longo de toda a frente factível porque $g_1$ (tensão) satura primeiro nesta planta; o cenário com todas as máquinas conectadas viola $g_1$ e $g_3$, com o transformador a 2,03 × AF. [FATO: doc B, p. 3] O artigo apresenta essa observação como resultado, NÃO como limitação. Decorre dela que a restrição térmica do transformador nunca foi a restrição ativa (binding) em solução factível alguma: o mecanismo "réplica térmica → restrição $g_3$" só foi exercitado no lado infactível (cenário com todas as máquinas), e a sua capacidade de moldar a frente de Pareto não foi demonstrada nesta planta. [INFERÊNCIA a partir de doc B, p. 3; FATO: ausência de solução factível com $g_3$ ativa]
- Modelo quase-estático de impedância constante para o inrush ignora a variação da corrente e do FP com o escorregamento durante a aceleração; a tensão mínima de 0,850 pu no instante de rotor bloqueado é o pior caso instantâneo, mas o artigo não avalia se a tensão se mantém abaixo de ajustes temporizados da 27 por tempo suficiente para atuação. [INFERÊNCIA FÍSICA: a corrente de partida de motor de indução decresce com o aumento da velocidade; ausência declarada em §8, itens 2 e 14]
- A restrição $g_1$ ativa em exatamente 0,850 pu (Tabela III) significa margem zero em relação ao ajuste da 27; qualquer erro de modelo (X/R da fonte, $X_{HL}$, FP das cargas) pode tornar o plano "mínimo corte" infactível na prática; o artigo não faz análise de sensibilidade. [INFERÊNCIA: doc B, p. 3; FATO: ausência de análise de sensibilidade]
- O ajuste 0,85 pu é "típico", não específico da planta; em plantas reais os ajustes da 27 e suas temporizações variam por carga. [INFERÊNCIA a partir de doc B, p. 2]
- O conjunto de treino do surrogate (14 343 cenários) provém do histórico do otimizador, portanto é enviesado para a vizinhança da região factível; a exatidão reportada não garante desempenho para cenários muito distantes (p. ex., com todas as máquinas ligadas). [INFERÊNCIA: doc B, p. 5]
- A "linearidade" da resposta de tensão é afirmada "nesta escala" (barra única, 19 cargas); para redes com centenas de barras, sobre as quais o Algoritmo 2 é proposto, a validade dos 190 regressores par a par não foi testada. [INFERÊNCIA: doc B, p. 5]
- |P| = 40 para o NSGA-II (Tabela IV) coincide com µ = 40, sugerindo que a população final é inteiramente não dominada, ou seja, o tamanho da frente reportada é limitado pelo tamanho da população; a frente de 97 soluções (p. 3) foi obtida sobre o arquivo de todas as avaliações, não sobre a população final. [INFERÊNCIA: doc B, p. 3–4]
- Orçamento de 800 avaliações (≈ 20 s) é pequeno; a comparação com busca aleatória a esse orçamento favorece qualquer método com pressão de factibilidade. [INFERÊNCIA ARITMÉTICA: doc B, p. 3, p. 5]
- Enumeração exaustiva a 25 ms/avaliação levaria ≈ 3,6 h — viável off-line para esta planta; o argumento de impraticabilidade só se sustenta para sistemas maiores ou uso on-line. [INFERÊNCIA ARITMÉTICA: doc B, p. 1, p. 5]
- O tratamento do inrush no transformador (1,38 × AF por 10 s) sem cálculo de ponto quente é aceitável para uma única partida, mas partidas repetidas ou falha da partida com religamento não são avaliadas. [HIPÓTESE]
- Fragmento editorial na p. 3 (frase truncada antes de "trade off between losses…") indica versão de submissão não revisada. [FATO: doc B, p. 3]

---

## 10 Ganchos para RUL / monitoramento de isolamento

### 10.1 O que o artigo já sugere textualmente

| Gancho | Texto do artigo | Rótulo |
|---|---|---|
| Evento de partida quantificado | Alvo de 1250 kW, $K_{ir}$ = 6,5, $\cos\varphi_{lr}$ = 0,20, $V_{\min}^{(\text{INRUSH})}$ entre 0,755 pu (sem corte) e 0,866 pu (corte total); inrush ≈ 10 s | [FATO: doc B, p. 2–3] — fornece as condições elétricas de contorno de cada partida (tensão de barra, múltiplo de corrente, duração assumida) |
| "Switching counts" como objetivo futuro | Em sistemas maiores a decisão acumula objetivos: "violations per protection zone, losses per feeder, shed load per priority class, reserve margins, switching counts" | [FATO: doc B, p. 4] — único ponto do texto em que a contagem de manobras aparece como grandeza de decisão; não é ligada a desgaste ou RUL pelo artigo |
| Réplica térmica como restrição | ANSI 49 do transformador referida ao estágio AF, com IEEE C57.91 para carga de curta duração | [FATO: doc B, p. 2–3] — o padrão "réplica térmica → restrição $g_3$" é um modelo de integração de um limite térmico num otimizador; aplica-se ao transformador, NÃO ao motor |
| Verificação exata obrigatória | Toda recomendação final é verificada pelo fluxo de potência completo (Algoritmo 2, linha 10) | [FATO: doc B, p. 5] — padrão de projeto reutilizável: surrogate para triagem, motor físico para decisão |
| Surrogate de $V_{\min}^{(\text{INRUSH})}$ | Ridge quadrático, $R^2$ = 0,9999, MAE 8,5 × 10⁻⁵ pu, 25 ms por avaliação exata | [FATO: doc B, p. 5] — permite estimar quase instantaneamente a tensão de partida para qualquer configuração de carga |
| Validação dinâmica futura | "validate selected scenarios in dynamic simulation" | [FATO: doc B, p. 6] — abre espaço para modelo dinâmico do motor (tempo de aceleração) |
| Reprodutibilidade | Planta em CSV, modelos OpenDSS, sementes e scripts; "every number in the paper can be regenerated with one command" | [FATO: doc B, p. 2–3] — a planta modelada é candidata a caso-base do MVP, condicionada à liberação do repositório |

### 10.2 Encadeamentos possíveis (rotulados, não afirmados pelo artigo)

- Tensão de partida → tempo de aceleração → $I^2 t$: com $T \propto V^2$ e corrente de partida ≈ constante durante a aceleração, uma partida a 0,850 pu (plano "mínimo corte") impõe aceleração mais longa e maior $\int I^2 dt$ do que a 0,866 pu (corte total); o artigo fornece as tensões, mas não o tempo de aceleração nem o $I^2 t$. [INFERÊNCIA FÍSICA: derivação a partir do modelo de circuito equivalente; dados de B, p. 3] Suporte normativo para curvas de limite térmico: IEEE Std 620-1996 [LITERATURA: verificada, https://ieeexplore.ieee.org/document/511267/]; para o cálculo de tempo de aceleração em estudos de partida: IEEE Std 3002.7-2018 [LITERATURA: verificada, https://ieeexplore.ieee.org/document/8700700/; cláusula não identificada].
- Acoplamento com o Documento A: o Documento A modela, para a mesma máquina (1250 kW, 4,16 kV, $I_p/I_n$ = 6,5), a interrupção intempestiva da partida por disjuntor a vácuo como pior caso de sobretensão [FATO: doc A, p. 1]. O snapshot INRUSH do Documento B define o estado elétrico da barra no instante em que tal interrupção ocorreria. Um pipeline combinado usaria B para o contexto de partida (tensão, corrente, plano de corte) e A para o estresse dielétrico caso a partida seja abortada. [INFERÊNCIA: junção de FATO doc A, p. 1 e FATO doc B, p. 2; nenhum dos dois artigos propõe essa junção — FATO: ausência]
- Premissa do usuário "5 a 7 reignições por ciclo": não consta do Documento B; no Documento A ocorre "multiple reignitions" sem contagem [FATO: doc A, p. 1–2]; permanece [HIPÓTESE do usuário] a ser suportada por literatura independente [INSERIR CITAÇÃO].
- Contagem de eventos como variável de degradação: "switching counts" (p. 4) poderia alimentar um modelo incremental de degradação por evento (partidas, manobras), mas o artigo não estabelece qualquer relação entre contagem de manobras e vida do isolamento. [HIPÓTESE]
- Réplica térmica do motor como restrição do otimizador: por analogia com $g_3$ (transformador), uma restrição $g_4$ baseada em réplica térmica ANSI 49 do motor ou em curva de limite térmico (IEEE 620) poderia limitar planos que impliquem partidas próximas do limite térmico; o artigo não a propõe. [HIPÓTESE]
- IEC 60034-15: define níveis de suportabilidade a impulso das bobinas pré-formadas (3–15 kV); a ligação com B só existe via A (sobretensões de manobra), pois B não produz nenhuma grandeza de impulso. [NORMA: IEC 60034-15, cláusula não identificada] [FATO: ausência em B]

---

## 11 Referências do artigo (19) com função

Todas transcritas da p. 6; a função é inferida do ponto de citação no texto (páginas indicadas). [FATO: doc B, p. 6 e páginas de citação]

| # | Referência (como no artigo) | Função no artigo | Onde citada |
|---|---|---|---|
| [1] | IEEE Std 399-1997, IEEE Recommended Practice for Industrial and Commercial Power Systems Analysis (Brown Book), IEEE, 1997. | Suporte à caracterização da partida direta (5–7 × $I_n$, FP ≈ 0,2, afundamento por segundos, atuação da 27) | p. 1 |
| [2] | IEEE Std 3002.7-2018, IEEE Recommended Practice for Conducting Motor-Starting Studies and Analysis of Industrial and Commercial Power Systems, IEEE, 2018. | Idem [1]; referência normativa para estudos de partida de motores | p. 1 |
| [3] | C. W. Taylor, "Concepts of undervoltage load shedding for voltage stability," IEEE Trans. Power Del., vol. 7, no. 2, pp. 480–488, Apr. 1992. | Distinguir o UVLS clássico (corretivo, pós-distúrbio) da decisão preventiva do artigo | p. 1 |
| [4] | K. Deb, A. Pratap, S. Agarwal and T. Meyarivan, "A fast and elitist multiobjective genetic algorithm: NSGA-II," IEEE Trans. Evol. Comput., vol. 6, no. 2, pp. 182–197, Apr. 2002. | Algoritmo NSGA-II (crowding distance) | p. 1, p. 3 |
| [5] | K. Deb and H. Jain, "An evolutionary many-objective optimization algorithm using reference-point-based nondominated sorting approach, part I: Solving problems with box constraints," IEEE Trans. Evol. Comput., vol. 18, no. 4, pp. 577–601, Aug. 2014. | Algoritmo NSGA-III; justificativa de que foi projetado para > 3 objetivos; dimensionamento de direções | p. 1, p. 3, p. 4 |
| [6] | H. Jain and K. Deb, "…part II: Handling constraints and extending to an adaptive approach," IEEE Trans. Evol. Comput., vol. 18, no. 4, pp. 602–622, Aug. 2014. | Mecanismo de constraint domination adotado na formulação corrigida | p. 1, p. 2, p. 4 |
| [7] | H. Seada and K. Deb, "A unified evolutionary optimization procedure for single, multiple, and many objectives," IEEE Trans. Evol. Comput., vol. 20, no. 3, pp. 358–369, Jun. 2016. | Variante U-NSGA-III reportada | p. 3 |
| [8] | I. Das and J. E. Dennis, "Normal-boundary intersection: A new method for generating the Pareto surface in nonlinear multicriteria optimization problems," SIAM J. Optim., vol. 8, no. 3, pp. 631–657, 1998. | Direções de referência Das–Dennis (35 para 5 objetivos) usadas no estudo degenerado; criticadas por impor descasamento entre número de direções e população | p. 2, p. 3 |
| [9] | J. Blank, K. Deb and P. C. Roy, "Generating well-spaced points on a unit simplex for evolutionary many-objective optimization," IEEE Trans. Evol. Comput., vol. 25, no. 1, pp. 48–60, Feb. 2021. | Direções por energia de Riesz dimensionadas à população (\|W\| = 40) | p. 3, p. 4 |
| [10] | H. Ishibuchi, Y. Setoguchi, H. Masuda and Y. Nojima, "Performance of decomposition-based many-objective algorithms strongly depends on Pareto front shapes," IEEE Trans. Evol. Comput., vol. 21, no. 2, pp. 169–190, Apr. 2017. | Explicação teórica da queda de desempenho do NSGA-III em frentes degeneradas | p. 1, p. 2, p. 4 |
| [11] | E. Zitzler and L. Thiele, "Multiobjective evolutionary algorithms: a comparative case study and the strength Pareto approach," IEEE Trans. Evol. Comput., vol. 3, no. 4, pp. 257–271, 1999. | Métrica de hipervolume | p. 3 |
| [12] | J. Blank and K. Deb, "pymoo: Multi-objective optimization in Python," IEEE Access, vol. 8, pp. 89497–89509, 2020. | Biblioteca de otimização usada (implementação de NSGA-II/III, U-NSGA-III) | p. 3 |
| [13] | EPRI, OpenDSS – Distribution System Simulator, EPRI, Palo Alto, CA, 2023. [Online]. https://www.epri.com/pages/sa/opendss | Motor de fluxo de potência | p. 1 |
| [14] | Y. Jin, "Surrogate-assisted evolutionary computation: Recent advances and future challenges," Swarm and Evolutionary Computation, vol. 1, no. 2, pp. 61–70, Jun. 2011. | Fundamento da computação evolutiva assistida por surrogate | p. 5 |
| [15] | A. I. J. Forrester and A. J. Keane, "Recent advances in surrogate-based optimization," Progress in Aerospace Sciences, vol. 45, no. 1–3, pp. 50–79, 2009. | Idem [14] | p. 5 |
| [16] | Y. Du, F. Li, J. Li and T. Zheng, "Achieving 100x acceleration for N-1 contingency screening with uncertain scenarios using deep convolutional neural network," IEEE Trans. Power Syst., vol. 34, no. 4, pp. 3303–3305, Jul. 2019. | Precedente de aceleração de triagem N-1 por modelos aprendidos (duas ordens de grandeza); comparação com o fator 1/ρ | p. 5 |
| [17] | X. Hu, H. Hu, S. Verma and Z.-L. Zhang, "Physics-guided deep neural networks for power flow analysis," IEEE Trans. Power Syst., vol. 36, no. 3, pp. 2082–2092, May 2021. | Precedente de aproximação de fluxo de potência por modelos aprendidos | p. 5 |
| [18] | IEEE Std C37.2-2008, IEEE Standard for Electrical Power System Device Function Numbers, Acronyms, and Contact Designations, IEEE, 2008. | Nomenclatura das funções ANSI 27/59/49/51 (Tabela I) | p. 2 |
| [19] | IEEE Std C57.91-2011, IEEE Guide for Loading Mineral-Oil-Immersed Transformers and Step-Voltage Regulators, IEEE, 2012. | Capacidade de carga de curta duração do transformador; justifica excluir o INRUSH de $g_3$ e admitir 1,38 × AF por 10 s | p. 2, p. 3 |

Observação: nenhuma das 19 referências trata de isolamento, envelhecimento, térmica de motores, transitórios de manobra ou RUL. [FATO: doc B, p. 6]

---

## Apêndice — Verificações aritméticas consolidadas

| Afirmação do artigo | Cálculo | Resultado | Rótulo |
|---|---|---|---|
| NSGA-III 23 % abaixo da aleatória (5 obj.) | 286 289 / 370 604 | 0,772 (−22,8 %) | [INFERÊNCIA ARITMÉTICA; coerente] |
| NSGA-III +49 % sobre aleatória (3 obj.) | 212 884 / 142 840 | 1,490 | [coerente] |
| NSGA-III = 96,5 % do NSGA-II | 212 884 / 220 533 | 0,9653 | [coerente] |
| NSGA-II +3,6 % sobre NSGA-III | 220 533 / 212 884 | 1,0359 | [coerente] |
| 7,31 MVA = 81 % AF / 97 % AN | 7,31/9; 7,31/7,5 | 0,812; 0,975 | [coerente] |
| 1,38 × AF; 2,03 × AF | × 9 MVA | 12,4 MVA; 18,3 MVA (≈ 18,2 MVA de demanda plena) | [coerente] |
| 0,6 % aleatórios factíveis; 54–60 % por constraint domination | 4,7/800; 435/800; 480/800 | 0,59 %; 54,4 %; 60,0 % | [coerente] |
| 490 kW recuperados | 7907 − 7417 | 490 | [coerente] |
| 1510 kW preservados | 8927 − 7417 = 710 + 800 | 1510 | [coerente; nomes M_710/M_800 codificam kW — inferência] |
| MAE ≈ 0,01 % da nominal | 8,5 × 10⁻⁵ pu | 0,0085 % | [coerente] |
| Espaço de busca | 2^19 | 524 288 | [coerente] |
| Tempo de enumeração exaustiva | 524 288 × 25 ms | ≈ 3,6 h | [não afirmado pelo artigo; crítica] |
