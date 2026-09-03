# Fichamento 06 — Yu, Wang e Luo (2014): prognóstico baseado em modelo para sistemas híbridos com degradação dependente do modo de operação

Convenções deste fichamento: "fato do artigo" = conteúdo verificável no texto, com página indicada segundo os marcadores "===== PAGE N =====" do arquivo extraído (p. 1 corresponde à página impressa 546; p. 9, à página 554); "inferência minha" = conclusão derivada por mim a partir do texto ou do repositório; "hipótese" = proposição ainda não verificada. As Tabelas I–X do artigo não tiveram seus valores numéricos extraídos no arquivo de texto (apenas os títulos); onde necessário, indico [INSERIR VALORES DA TABELA N]. As Figs. 1–11 tampouco estão disponíveis, apenas suas legendas.

---

## 1. Referência completa

YU, Ming; WANG, Danwei; LUO, Ming. Model-Based Prognosis for Hybrid Systems With Mode-Dependent Degradation Behaviors. **IEEE Transactions on Industrial Electronics**, v. 61, n. 1, p. 546–554, jan. 2014. DOI: 10.1109/TIE.2013.2244538.

Dados complementares (fato do artigo, p. 1):
- Manuscrito recebido em 5 jul. 2012; revisado em 18 dez. 2012; aceito em 10 jan. 2013; publicado em 1 fev. 2013; versão corrente de 18 jul. 2013.
- Financiamento parcial: National Natural Science Foundation of China, Grants 91120308 e 61074185.
- Afiliações: M. Yu e D. Wang — School of Electrical and Electronic Engineering, Nanyang Technological University (NTU), Singapura; M. Luo — Singapore Institute of Manufacturing Technology (SIMTech), A*STAR, Singapura.
- Palavras-chave dos autores: degradation model, differential evolution (DE), dynamic fault isolation (DFI), failure threshold, hybrid systems, model-based prognosis, remaining useful life (RUL).
- Trabalho anterior dos mesmos autores sobre o qual este se apoia (ref. [14] do artigo, p. 9): YU, M.; WANG, D.; LUO, M.; HUANG, L. Prognosis of hybrid systems with multiple incipient faults: Augmented global analytical redundancy relations approach. IEEE Trans. Syst., Man, Cybern. A, v. 41, n. 3, p. 540–551, maio 2011.

## 2. Objetivo do artigo

Fato do artigo (p. 1, resumo): desenvolver um arcabouço de prognóstico baseado em modelo para sistemas híbridos (dinâmica contínua interagindo com mudanças discretas de configuração, denominadas "mode changes") no qual (i) múltiplas falhas incipientes podem ocorrer simultaneamente em um modo em que têm detectabilidades diferentes; (ii) um esquema de isolamento dinâmico de falhas (DFI) com "tempo de espera" (WT) permite que todas as falhas manifestem seus sintomas nos resíduos; (iii) o comportamento de degradação de cada componente faltoso é dependente do modo e é estimado por um algoritmo híbrido de evolução diferencial (HDE); (iv) a vida útil remanescente dependente do modo (MD-RUL) é calculada a partir do modelo de degradação estimado e de um limiar de falha "selecionado pelo usuário".

Fato do artigo (p. 1): os autores reivindicam ineditismo — "To the best of our knowledge, it is the first time in the literature that the multiple incipient faults with different detectabilities at the fault-initiating mode are considered for the prognosis of hybrid systems."

Fato do artigo (p. 2): a contribuição algorítmica é o "sequential prognosis method for multiple failures", composto por um módulo de prognóstico padrão (ativado a cada nova inconsistência detectada) e um módulo de prognóstico auxiliar (ativado a cada nova mudança de modo), ambos realizados via HDE.

Inferência minha: o artigo é primariamente um trabalho de metodologia de diagnóstico/prognóstico (FDI + RUL) para sistemas chaveados, e não um estudo de degradação física de um componente. O "sistema híbrido" é um circuito RC chaveado de bancada, e a degradação é sintética (ver Seção 3).

## 3. Sistema/componente e mecanismo(s) de degradação tratados

Sistema (fato do artigo):
- Exemplo didático (p. 2, Fig. 1): circuito chaveado com fonte V1, resistores R1 e R2, capacitor C1, chave sw1 e dois sensores (De, tensão; Df, corrente); dois modos, a ∈ {0, 1}, conforme o estado da chave.
- Sistema experimental (p. 5, Fig. 4): circuito com cinco resistores R1–R5, duas fontes V1 e V2, dois capacitores C1 e C2, um sensor de corrente Df, três sensores de tensão De1–De3 e duas chaves sw1 e sw2; quatro modos [a1, a2] ∈ {0,1}². Modelado por Diagnostic Hybrid Bond Graph (DHBG), "an HBG with a causality assignment that all its controlled junctions and storage components are assigned with preferred causalities [13]" (p. 2).
- Os autores justificam a relevância de sistemas híbridos citando "automobiles and converters" (p. 1) e o motor de alimentação de uma impressora com modos "ramp-up, rotating with constant speed, ramp-down, and idle" (p. 3, citando [11]).

Componentes "degradáveis" e mecanismo (fato do artigo):
- As falhas são de dois tipos: paramétricas (resistores R_i) e não paramétricas (atuador e sensores), estas últimas quantificadas por "efficiency factors" β_V1, β_Df, β_De (p. 2): "three additional parameters (βV1, βDf, and βDe) called efficiency factors are used to quantify the faults in sensors and actuator, which facilitate the fault identification and prognosis of these nonparametric components."
- No experimento, "Two incipient faults are considered: one is an actuator fault in V1, and the other is a sensor fault in De3" (p. 6).
- A "degradação" não é física: os fatores de eficiência β_V1 e β_De3 seguem equações diferenciais determinísticas (16) e (17) "run in the backgrounds, and the FDI process does not assume the knowledge of (16) and (17)" (p. 7). Os coeficientes "are selected to ensure monotonic decrease of two efficiency factors" (p. 6).
- Conceito central: "For a hybrid system, the same component will exhibit different degradation behaviors at different operating modes" (p. 3) — o mesmo componente segue leis distintas (linear ou não linear) conforme o modo; daí "mode-dependent degradation models (MD-DM)" e "mode-dependent RUL (MD-RUL)" (p. 3).

Inferência minha: não há mecanismo de envelhecimento físico (térmico, elétrico, mecânico) no artigo. A degradação é uma trajetória injetada por software em parâmetros multiplicativos do modelo (ganho de atuador, ganho de sensor). Isso limita a validação ao aspecto algorítmico (identificação de estrutura e coeficientes de uma EDO conhecida a priori pelo experimentador, mas oculta do estimador), não ao aspecto prognóstico de um processo real de desgaste.

## 4. Indicadores/precursores de degradação usados

| Indicador | Grandeza / unidade | Como é obtido | Amostragem | Página |
|---|---|---|---|---|
| Resíduos G_l das AGARRs (augmented global analytical redundancy relations) | G1: unidade de tensão (V); G2–G4: unidade de corrente (A) — unidades são inferência minha a partir da estrutura das eqs. (12)–(15); o artigo não as declara | Avaliação numérica das relações de redundância analítica derivadas do DHBG com as medições dos sensores (Df, De1–De3) e os estados das chaves a1, a2 | t_s = 0,05 s (p. 6); N = 100 amostras coletadas por fase de prognóstico, isto é, 5 s (p. 7–8) | p. 2, 5 |
| Vetor binário de coerência C = [c1, …, cm] | Adimensional, c_l ∈ {0,1} | c_l = 1 quando |G_l| excede seu limiar ε_l; "When the system is fault free, the binary coherence vector C will be zero" | Mesma da anterior | p. 2 |
| Limiares de resíduo | ε1 = 5e−4, ε2 = 8e−4, ε3 = 5e−4, ε4 = 3e−4 (unidades não declaradas; por inferência, V para ε1 e A para ε2–ε4) | "set by observing residual responses under normal condition, and they should be defined carefully to avoid false alarm" | — | p. 7 |
| Fatores de eficiência β_V1, β_De3 (variável de estado de saúde) | Adimensional; valor nominal 1 (inferência minha); limiares de falha β^F_V1 = 0,5 e β^F_De3 = 0,3 | Não medidos diretamente; estimados pelo HDE a partir dos resíduos | — | p. 6 |
| Parâmetro físico degradável (ex.: R2) | Ω | Idem, estimado por HDE; exemplo com limiar R2^F | — | p. 3, 5 |

Fato do artigo (p. 2): a matriz de assinatura de falhas dependente do modo (MD-FSM, Tabelas I–II para o exemplo, III–VI para o experimento) define, para cada modo, quais componentes são detectáveis por quais resíduos; um componente pode ser "nondetectable" em um modo e "detectable" em outro [INSERIR VALORES DAS TABELAS I–VI].

Inferência minha: o "precursor" no sentido de PHM não é uma grandeza física medida do componente (como capacitância, tan δ ou descargas parciais), mas um estado latente (β) inferido por consistência de modelo. Isso é típico da escola de diagnóstico baseado em bond graph e difere dos indicadores diretos usados nos artigos de isolamento de estator desta revisão.

## 5. Modelo/algoritmo

Classe: híbrida (inferência minha). Os autores denominam o método "model-based" (p. 1), e a geração de resíduos é fisicamente fundamentada (DHBG → AGARRs). Entretanto, a lei de degradação (4) é uma família paramétrica empírica cuja estrutura (vetor binário) e coeficientes (reais) são identificados a partir de dados por um algoritmo evolutivo; não há lei física de envelhecimento. Rótulo alternativo cabível: "framework" (o artigo propõe um arcabouço: DFI + prognóstico sequencial + HDE).

### 5.1 Geração de resíduos (exemplo de dois modos, p. 2)

Eq. (1), p. 2: G1 = β_V1·V1 − R1·(Df/β_Df) − De/β_De

Eq. (2), p. 2: G2 = Df/β_Df − a·(1/R2)·(De/β_De) − C1·d/dt(De/β_De), com a ∈ {0,1} o estado da chave.

### 5.2 Tempo de espera do DFI (p. 3)

Eq. (3), p. 3: T_wt = T_rmct + Σ_{k=0}^{n} T^k_mct, com T^0_mct = 0,

em que T_wt é o tempo de espera; T_rmct "denotes the remaining mode change time, which means the time difference between the first observed inconsistency and the following mode change"; T^k_mct "represents the successive mode change time interval".

Fato do artigo (p. 3): "according to (3), the system is at least required to continuously monitor the process until the next mode change instance from the first observed fault condition." Hipótese de trabalho assumida: "Assume that all faults could be detected within the predefined WT."

Regra de isolamento sequencial (p. 3): a falha verdadeira já identificada deve estar contida em todos os elementos do novo conjunto de suspeitas, δ = {θ1&θi, θ1&βj, θ1&θi&βj, …}; se a nova inconsistência coincide com a mudança de modo, "the added fault signature is only caused by components that are nondetectable at previous mode and are detectable at current mode".

### 5.3 Modelo de degradação dependente do modo (p. 3)

Eq. (4), p. 3: ω1·P̈ + (1 − ω1)·Ṗ = b·P^{2ω2} + c·P^{ω3},

com P o valor do parâmetro ou do fator de eficiência; b, c os coeficientes; ω_i ∈ {0,1}, i = 1,2,3; Ω = [ω1, ω2, ω3] denominado "degradation model structure vector (DMSV)". Exemplos dados pelos autores: Ω = [0,1,1] ⇒ Ṙ2 = b·R2² + c·R2 (não linear); Ω = [0,0,1] ⇒ Ṙ2 = b + c·R2 (linear).

Inferência minha: a família (4) contém 8 estruturas possíveis (2³), incluindo modelos de 2ª ordem (ω1 = 1) que os autores não exercitam no experimento; a solução de Ω = [0,0,1] é exponencial no tempo, P(t) = (P0 + b/c)·e^{ct} − b/c, o que a torna equivalente ao modelo de tendência exponencial usado em outros trabalhos de prognóstico de isolamento (ver Seção 11).

### 5.4 HDE: evolução diferencial híbrida real–binária (p. 4–5)

Motivação (p. 3): "the traditional gradient-based method cannot directly solve this identification problem because the objective function to be minimized is not directly related to the binary vector DMSV; thus, no gradient information can be obtained."

RDE (real), estratégia DE/best/1/bin:

Eq. (5), p. 4: V^{G+1}_{ij} = X^G_best + F_r × (X^G_{r1 j} − X^G_{r2 j}), F_r ∈ [0, 2], r1 ≠ r2 ∈ [1, N].

Eq. (6), p. 4 (cruzamento): H^{G+1}_{ij} = V^{G+1}_{ij} se rand_j ≤ CR ou j = rnbr(i); H^{G+1}_{ij} = X^G_{ij} se rand_j > CR ou j ≠ rnbr(i); CR ∈ [0,1].

Eq. (7), p. 4 (seleção): X^{G+1}_i = H^{G+1}_i se f(H^{G+1}_i) > f(X^G_i); X^G_i caso contrário.

BDE (binária), com mutação booleana:

Eq. (8), p. 4: V^{G+1}_{ij} = X^G_best + F_b • (X^G_{r1 j} ⊕ X^G_{r2 j}), em que (•), (+), (⊕) denotam AND, OR e XOR; "F_b is a random D-bit binary vector, and it is not a control parameter."

Acoplamento e função de aptidão:

Eq. (9), p. 4: F_fitness = 1 / ( Σ_{l=1}^{m} Σ_{n=1}^{N} |G^n_l| + ϵ ),

em que G_l é a l-ésima AGARR, ϵ "is a small positive constant that is used to avoid zero division", n é o índice discreto de amostragem (p. 5). "The RDE and BDE simultaneously evolve and are coupled through the common fitness function" (p. 4).

Inferência minha sobre o mecanismo: cada indivíduo (Ω, b, c) gera uma trajetória candidata do parâmetro/fator ao longo das N amostras; substituída nas AGARRs, a trajetória correta anula os resíduos, maximizando (9). O artigo não explicita como a trajetória candidata é integrada nem a condição inicial P(t_f) usada.

Estrutura multiestimador (p. 5): com um único suspeito, um HDE; com vários suspeitos, "several HDE estimators run in parallel, and each estimator serves to identify one element in the set", comparando-se as aptidões finais. O módulo auxiliar "only employs a single HDE estimator" porque a falha verdadeira já é conhecida.

Hiperparâmetros usados (fato do artigo, p. 7): tamanho da população = 100; iterações máximas = 400; F_r = 0,4; CR = 0,8.

### 5.5 EOL e RUL (p. 5)

Eq. (10), p. 5: EOL(t_f) = inf{ t ∈ ℝ : t ≥ (t_f + N·t_s) ∧ T_EOL = 1 }

Eq. (11), p. 5: RUL(t_f) = EOL(t_f) − (t_f + N·t_s),

com T_EOL = 1 quando o limiar de falha é excedido; N o número de dados coletados; t_s o tempo de amostragem.

Forma fechada para lei linear (p. 5, texto corrido, sem numeração): para Ṙ2 = b + c·R2 e limiar R2^F, EOL = log((b̄ + c̄·R2^F)/(b̄ + R2(0)·c̄))/c̄ e RUL = log((b̄ + c̄·R2^F)/(b̄ + R2(0)·c̄))/c̄ − t_f − N·t_s, "where b̄ and c̄ are estimated values of b and c, and R2(0) is the value of R2 at time point t_f".

Inferência minha (observação crítica): a expressão de RUL subtrai t_f e N·t_s de um tempo cuja origem é R2(0) = R2(t_f); há aparente mistura de origem absoluta e relativa de tempo, a menos que R2(0) se refira ao valor em t = 0. [VERIFICAR NA VERSÃO PUBLICADA].

Propriedade declarada (p. 5): "the estimated MD-RUL of each prognosis module is independent of the MD-RUL for the same fault component of the previous prognosis module, which means the estimated error of the previous prognosis module will not be propagated to the next prognosis module."

### 5.6 AGARRs do circuito experimental (p. 5)

Eq. (12): G1 = β_V1·V1 − R1·(Df/β_Df) − De1/β_De1

Eq. (13): G2 = Df/β_Df + (a1/R2)·(β_V2·V2 − De1/β_De1) − C1·d/dt(De1/β_De1) − (1/R3)·(De1/β_De1 − De2/β_De2)

Eq. (14): G3 = (1/R3)·(De1/β_De1 − De2/β_De2) − C2·d/dt(De2/β_De2) − (a2/R4)·(De2/β_De2 − De3/β_De3)

Eq. (15): G4 = a2·[ (1/R4)·(De2/β_De2 − De3/β_De3) − (1/R5)·(De3/β_De3) ],

com a1, a2 ∈ {0,1} os estados de sw1 e sw2. "only junctions with the attached sensor are considered. Four structurally independent AGARRs are obtained" (p. 5).

## 6. Dados e experimento

Fato do artigo (p. 6):
- Parâmetros nominais: V1 = 9 V; V2 = 0,5 V; R1 = 670 Ω; R2 = 215,6 Ω; R3 = 67,5 Ω; R4 = 215,4 Ω; R5 = 509 Ω; C1 = 1000 µF; C2 = 4700 µF.
- Tempo de amostragem 0,05 s; estados das chaves na Fig. 6 (não disponível).
- Bancada (Fig. 7): PC interfaceado ao circuito por duas placas DAQ NI PCI-6025E e NI PCI-6713; "The PC RTWT controls the states of sw1 and sw2 through the analog outputs of these DAQ cards" (RTWT = Real-Time Windows Target, inferência minha).
- Leis de degradação injetadas (Eq. 16, p. 6), para β_V1:
  - modo [1,0]: β̇_V1 = −0,03·β_V1² + 0,01·β_V1, Ω = [0,1,1];
  - modo [0,0]: β̇_V1 = −0,02·β_V1 + 0,005, Ω = [0,0,1];
  - modo [0,1]: β̇_V1 = −0,05·β_V1² + 0,0035·β_V1, Ω = [0,1,1].
- Leis de degradação injetadas (Eq. 17, p. 6), para β_De3:
  - modo [1,0]: β̇_De3 = −0,025·β_De3 + 0,01, Ω = [0,0,1];
  - modo [0,0]: β̇_De3 = −0,03·β_De3² + 0,003·β_De3, Ω = [0,1,1];
  - modo [0,1]: β̇_De3 = −0,06·β_De3 + 0,015, Ω = [0,0,1].
- Limiares de falha: β^F_V1 = 0,5 e β^F_De3 = 0,3.

Cronologia do ensaio (fato do artigo, p. 7–8):
1. t = 5 s, modo [1,0]: introduzidas as falhas em β_V1 e β_De3; β_De3 é não detectável nesse modo (Tabela IV); vetor de coerência [1 0 0 0]; conjunto de suspeitas δ = [β_V1, R1, β_V1&R1]; 100 amostras coletadas; módulo padrão identifica β_V1 como falha verdadeira (Fig. 10); MD-RUL na Tabela VII [INSERIR VALORES].
2. Tempo de espera definido pela Eq. (18), p. 7: T_wt = T_rmct + T¹_mct = 5 + 5 = 10 s, com k = 1.
3. t = 10 s: mudança para modo [0,0]; 100 amostras em 5 s; módulo auxiliar recalcula MD-RUL de β_V1 no novo modo (Tabela VIII) [INSERIR VALORES].
4. t = 15 s: novo vetor de coerência [1 0 1 1] no modo [0,1]; conjunto de suspeitas δ = [β_V1&R4, β_V1&R4&R5, β_V1&β_De3, β_V1&β_De3&R4, β_V1&β_De3&R5, β_V1&β_De3&R4&R5]; "six HDE estimators run in parallel to find the true faults along with their DMSVs" (Fig. 11; Tabela IX) [INSERIR VALORES].

Comparação algorítmica (fato do artigo, p. 8): HDE vs. GA vs. AGA [19], sobre os mesmos dados da fase 3; população = 100 e iterações máximas = 400 para todos; 30 execuções independentes por algoritmo; Tabela X reporta F^min, F^max, F^mean e desvio-padrão σ da aptidão [INSERIR VALORES DA TABELA X].

Inferência minha: o ensaio tem 20 s de duração total (5 s de operação sã + 3 fases de 5 s), com N = 100 amostras por fase; é um experimento de bancada em escala de laboratório, com "degradação" ocorrendo em segundos por construção das Eqs. (16)–(17). Não há conjunto de dados público, réplicas ou ruído caracterizado.

## 7. Métricas e resultados numéricos

- Métrica de detecção: |G_l| > ε_l, com ε1 = 5e−4, ε2 = 8e−4, ε3 = 5e−4, ε4 = 3e−4 (p. 7). Resultado: "a deviation in residual of G1 is expected upon the fault occurrence in βV1. The experimental result confirms this behavior" (p. 7).
- Métrica de identificação: aptidão (9) — "results reveal that the true fault is in βV1" (p. 7, Fig. 10) e, na fase 3, os seis estimadores paralelos encontram "the true faults along with their DMSVs" (p. 8, Fig. 11; Tabela IX).
- Métrica de prognóstico: MD-RUL por modo (Tabelas VII, VIII, IX) — valores numéricos não extraídos [INSERIR VALORES]. O artigo não reporta erro de RUL em relação ao valor verdadeiro (que seria calculável a partir de (16)–(17)), nem métricas padronizadas de PHM (α-λ, horizonte de prognóstico, RA, etc.) — inferência minha, por ausência no texto.
- Comparação de otimizadores (p. 8, Tabela X): "It is clear that HDE outperforms the other algorithms considered in this paper in terms of final solution and standard deviation." Valores não extraídos [INSERIR VALORES DA TABELA X].
- Hiperparâmetros: população 100; 400 iterações; F_r = 0,4; CR = 0,8 (p. 7).

## 8. Limitações

Declaradas pelos autores:
1. (declarada, p. 1) "Model-based prognostic methods can offer accurate predictions provided that the physical degradation processes are fully understood."
2. (declarada, p. 3) Hipótese de que todas as falhas são detectáveis dentro do WT predefinido; e o WT exige monitoração contínua "at least […] until the next mode change instance".
3. (declarada, p. 7) Limiares de resíduo ajustados por observação em condição normal e que "should be defined carefully to avoid false alarm".
4. (declarada, p. 6–7) As Eqs. (16)–(17) são determinísticas e servem apenas para simular a degradação; a MD-RUL "should not be considered as deterministic, which can be updated based on online collected data".
5. (declarada, p. 1) O limiar de falha é "user-selected" (resumo), isto é, exógeno ao método.

Identificadas por mim (minha inferência):
6. Degradação sintética: não há envelhecimento físico; o experimento valida apenas a recuperação de uma EDO conhecida, com estrutura pertencente à mesma família (4) usada pelo estimador (viés de "modelo dentro do modelo").
7. Ausência de quantificação de incerteza: a MD-RUL é um escalar; não há intervalos de confiança, distribuição de RUL nem propagação da incerteza de b̄, c̄ ou da variabilidade estocástica do HDE (embora a Tabela X mostre σ da aptidão, isso não é traduzido em σ da RUL).
8. A RUL calculada em um modo pressupõe permanência indefinida naquele modo; o método não integra a sequência futura de modos (ciclo de trabalho) para uma RUL "efetiva". Contraste com a abordagem de ref. [8] do artigo (Luo et al.), que "is performed by mixing mode-based life predictions via time-averaged mode probabilities" (p. 1) — arquitetura mais adequada a cargas com ciclo de serviço conhecido.
9. Função de aptidão (9) soma valores absolutos de resíduos de unidades físicas distintas (tensão e corrente) sem normalização, o que pode enviesar a identificação para o resíduo de maior escala.
10. Custo computacional: fase 3 exige 6 estimadores × 100 indivíduos × 400 gerações, cada avaliação envolvendo a integração da trajetória candidata sobre N = 100 amostras; o tempo de execução não é reportado, o que impede julgar a aplicabilidade "online" reivindicada.
11. Latência de decisão estrutural: pelo DFI, o diagnóstico completo só se conclui após a próxima mudança de modo. Em ativos com mudanças de modo raras (ex.: partidas de grandes motores algumas vezes por ano), o WT pode ser de meses.
12. Escala e ruído: circuito RC de bancada com sensores de baixa tensão; não há caracterização de ruído de medição nem de erro de modelo (incerteza paramétrica de R e C), fatores que dominam o desempenho de esquemas baseados em resíduos em sistemas industriais.
13. Requisito de modelo estrutural completo (DHBG com causalidade preferida e sensores em junções específicas) — inviável de obter para o estado dielétrico de um enrolamento sem instrumentação dedicada.
14. Possível inconsistência de origem temporal na fórmula de RUL da p. 5 (ver Seção 5.5).

## 9. Transferibilidade para o problema-alvo

Problema-alvo: isolamento de estator de motor de indução MT (2,3–13,8 kV) submetido a (a) sobretensões de manobra de VCB (corte de corrente, reignições múltiplas, frentes íngremes, dV/dt), com ou sem snubber tiristorizado (trabalho A), e (b) estresse térmico de partidas de grandes motores sob contingência N-1 com load shedding (trabalho B).

### 9.1 O que se transfere

1. Conceito de degradação dependente do modo (transfere-se integralmente como arquitetura conceitual). O artigo formaliza que "the same component will exhibit different degradation behaviors at different operating modes" e exemplifica exatamente com um motor: "the motor wear in the ramp-up mode is more severe than the wear in the idle mode" (p. 3). Mapeamento (inferência minha):
   - Modo "regime permanente": envelhecimento térmico/elétrico lento a 60 Hz.
   - Modo "partida normal": aquecimento adiabático do enrolamento, dilatação diferencial, esforço eletrodinâmico nas cabeças de bobina — taxa de degradação elevada durante segundos.
   - Modo "partida sob N-1 com load shedding" (trabalho B): tensão de barra reduzida, partida mais longa, I²t maior — lei de degradação com coeficientes ainda mais severos.
   - Modo "manobra de VCB sem snubber" (trabalho A): dano por evento (reignições, dV/dt), concentrado nas primeiras espiras.
   - Modo "manobra de VCB com snubber tiristorizado ativo": lei atenuada.
   O snubber seletivo do trabalho A é, na linguagem do artigo, um comutador de modo que altera o DMSV/coeficientes da degradação do isolamento; o load shedding do trabalho B altera a sequência de modos. Isso justifica, na tese, um índice de saúde único com leis de degradação comutadas.

2. Conceito de detectabilidade dependente do modo e DFI (transfere-se com adaptação). A ideia de que uma falha pode ser "nondetectable at previous mode and are detectable at current mode" (p. 3) tem análogo físico direto: uma fragilidade de isolamento entre espiras é praticamente invisível em regime a 60 Hz (distribuição linear de tensão ao longo da bobina) e torna-se detectável sob frente íngreme de manobra do VCB, quando a tensão se concentra nas primeiras espiras (hipótese física a ser confirmada com [INSERIR CITAÇÃO] sobre distribuição de tensão de surto em enrolamentos). O "tempo de espera" do artigo corresponde a aguardar a próxima manobra ou partida — evento que, no problema-alvo, pode ser programado (manobra de teste) em vez de esperado.

3. Prognóstico sequencial com gatilho por mudança de modo (transfere-se como arquitetura de software). O módulo auxiliar "is triggered when a new mode change occurs" (p. 2) e a MD-RUL de cada módulo é independente da anterior (p. 5). Para o problema-alvo: cada partida ou manobra dispara reestimação do modelo e da RUL; erros de estimativas anteriores não se propagam. Isso é compatível com um pipeline de pós-processamento por evento, semelhante ao que o repositório já faz para métricas de transitório (app/analysis/transient_metrics.py) e para o modelo estatístico de reignição do VCB (app/preprocessor/vcb_model_emitter.py, parâmetros I_chop, di/dt crítico, k_dielec, U0) — inferência minha a partir do repositório.

4. Família de modelos (4) e identificação conjunta de estrutura + coeficientes (transfere-se parcialmente). A ideia de escolher entre leis linear/exponencial/quadrática por modo é útil para indicadores de tendência (capacitância, tan δ, PDIV, corrente de fuga transitória). A solução exponencial de Ω = [0,0,1] coincide com o modelo de tendência empregado em prognóstico de isolamento por EKF (ver Seção 11). O HDE pode ser substituído por seleção bayesiana de modelo ou por filtro de partículas com hipótese de estrutura, ganhando-se incerteza de RUL.

5. Definições formais de EOL/RUL (10)–(11) com limiar de falha explícito e janela de coleta N·t_s (transfere-se integralmente como formalismo de tese).

### 9.2 O que não se transfere e por quê

1. Indicador: os resíduos de AGARR derivados de DHBG de um circuito RC de baixa tensão não têm correspondente para o estado dielétrico do enrolamento; não existe sensor "De" para a saúde do isolamento nem modelo bond graph fechado do enrolamento com causalidade preferida. O problema-alvo exigirá indicadores diretos (PD, tan δ, capacitância, corrente de fuga sob frente rápida, temperatura de ponto quente) — inferência minha.
2. Natureza temporal versus por evento: a Eq. (4) é uma EDO em tempo contínuo; o dano por sobretensão de manobra é discreto e cumulativo por evento (número de reignições × amplitude × dV/dt). Seria necessário reformular (4) em domínio de ciclos/eventos (P_{k+1} = P_k + g(estresse_k)), o que muda o estimador — hipótese de reformulação minha.
3. Validação: degradação sintética injetada em fatores de eficiência não substitui ensaio acelerado de envelhecimento dielétrico (térmico, ou por impulsos repetitivos). O método de validação do artigo não é reproduzível para o isolamento sem bancada de envelhecimento — inferência minha.
4. Ausência de incerteza: para a demanda de RUL em nível gerencial (C-Level), uma RUL escalar sem intervalo de confiança é insuficiente; o método precisa ser embutido em estimador probabilístico — inferência minha.
5. RUL por modo sem integração de ciclo de serviço: para motores com dezenas de partidas por ano e centenas de manobras, a RUL relevante é a integrada sobre a sequência esperada de modos (o que o artigo não faz), abordagem mais próxima de ref. [8] do artigo — inferência minha.
6. Escalabilidade do HDE (6 estimadores paralelos × 100 × 400) não é demonstrada em tempo real; para monitoração online de ativos MT, seria preciso avaliar custo — inferência minha.

### 9.3 Nota atribuída

Nota: 3/5.

Justificativa (inferência minha): alta transferibilidade conceitual e arquitetural (degradação dependente do modo; detectabilidade dependente do modo; prognóstico sequencial por evento; formalismo EOL/RUL com limiar explícito), com baixa transferibilidade de indicador, de modelo físico, de método de validação e de tratamento de incerteza. O artigo é mais útil como fundamento para a formulação do método de monitoramento (capítulo de modelagem da tese) do que como base experimental.

Hipótese de contexto: se o cenário industrial for de refinarias/plataformas com motores MT manobrados por VCB (hipótese sugerida apenas pela marca d'água de licença dos PDFs, não por dado do autor), o mapeamento modo = {regime, partida, partida N-1, manobra sem snubber, manobra com snubber} é diretamente operacionalizável a partir do registro de eventos do sistema de proteção e do SCADA.

## 10. Citações literais relevantes

1. "Model-based prognostic methods can offer accurate predictions provided that the physical degradation processes are fully understood." (p. 1)
2. "To the best of our knowledge, it is the first time in the literature that the multiple incipient faults with different detectabilities at the fault-initiating mode are considered for the prognosis of hybrid systems." (p. 1)
3. "For a hybrid system, the same component will exhibit different degradation behaviors at different operating modes. For instance, the feed motor in a printer may be in the ramp-up, rotating with constant speed, ramp-down, and idle modes [11]. It is evident that the motor wear in the ramp-up mode is more severe than the wear in the idle mode." (p. 3)
4. "Since the degradation model is mode dependent, the RUL for each faulty component is also mode dependent, referred to as mode-dependent RUL (MD-RUL)." (p. 3)
5. "It is worth to note that according to (3), the system is at least required to continuously monitor the process until the next mode change instance from the first observed fault condition." (p. 3)
6. "In addition, the estimated MD-RUL of each prognosis module is independent of the MD-RUL for the same fault component of the previous prognosis module, which means the estimated error of the previous prognosis module will not be propagated to the next prognosis module." (p. 5)
7. "These thresholds are set by observing residual responses under normal condition, and they should be defined carefully to avoid false alarm." (p. 7)
8. "The obtained model is used to compute the MD-RUL and the MD-RUL should not be considered as deterministic, which can be updated based on online collected data." (p. 7)

## 11. Ligações com os outros temas: RUL, PHM, C-Level

RUL/PHM (fato do artigo):
- Definição operacional de prognóstico (p. 1): "Prognosis usually determines whether a failure is impending and estimates how soon and how likely a failure will occur. The main task of prognosis is to predict the end of life (EOL) or remaining useful life (RUL) of a faulty component or subsystem."
- Dificuldade central do prognóstico (p. 1): "Prognosis is a key element of CBM and presents major challenges to CBM primarily because it projects the current faulty condition in the absence of future observations."
- Formalização EOL/RUL nas Eqs. (10)–(11), p. 5, com limiar de falha e janela de dados N·t_s.
- Posicionamento frente à literatura (p. 1): crítica a [5] por assumir degradação linear; menção a IMM [7], [8] para rastrear dano oculto e misturar previsões de vida por modo.

Manutenção e decisão (fato do artigo, p. 1): "Unlike traditional scheduled or breakdown maintenance, condition-based maintenance (CBM) performs required repair and maintenance based on the assessment of the system condition." O artigo não apresenta argumentos de custo, análise econômica, matriz de risco ou estudo de caso de decisão gerencial; a única alavanca de decisão explicitada é o limiar de falha "user-selected" (p. 1, 8).

Inferências minhas para o eixo C-Level:
- O limiar de falha exógeno (β^F) é, na prática, a interface entre engenharia e gestão: define o apetite de risco e converte um índice de saúde em data de intervenção. Na tese, esse limiar deve ser derivado de critério normativo ou de risco (custo de parada versus custo de rebobinamento), e não escolhido arbitrariamente como no artigo.
- A independência entre estimativas sucessivas de MD-RUL (p. 5) é um argumento de robustez apresentável à gestão: cada evento (partida, manobra) "reinicia" a estimativa com dados novos, evitando acumulação de erro.
- A latência estrutural do DFI (esperar a próxima mudança de modo) é um custo de informação: para ativos críticos, a gestão pode optar por "provocar" uma mudança de modo controlada (manobra de teste com snubber ativo, partida em vazio) para encurtar o WT — hipótese a ser avaliada com custos operacionais.

Ligações internas à revisão (inferência minha):
- Com o fichamento 02 (Jensen, Strangas e Foster, 2018): o modelo de tendência exponencial estimado por EKF equivale à estrutura Ω = [0,0,1] da Eq. (4); o presente artigo generaliza para múltiplas estruturas comutadas por modo, enquanto Jensen et al. fornecem o indicador físico (overshoot da corrente de fuga sob frente rápida) que este artigo não possui. A combinação "indicador de Jensen + comutação de modo de Yu" é uma linha de síntese candidata para a tese.
- Com o repositório: os parâmetros do modelo de reignição do VCB (I_chop, σ, di/dt crítico, k_dielec, U0) e as métricas de transitório já implementadas permitem rotular cada manobra simulada com um vetor de estresse; esse rótulo é o "modo" na acepção deste artigo, com ou sem snubber tiristorizado (trabalho A).
- Com o trabalho B: a decisão de load shedding sob N-1 escolhe a sequência de modos de partida dos grandes motores; a MD-RUL fornece um critério adicional (degradação do isolamento por partida) para a função objetivo multiobjetivo — hipótese de integração.
