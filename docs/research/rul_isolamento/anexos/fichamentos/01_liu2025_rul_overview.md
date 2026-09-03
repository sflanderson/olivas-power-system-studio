# Fichamento 01 — liu2025_rul_overview

Arquivo-fonte: `papers/txt/1-s2.0-S2666827025000878-main.txt` (20 páginas; marcadores "===== PAGE N =====").
Convenção de rótulos: **[fato]** = afirmação extraída do artigo, com página; **[inferência]** = conclusão minha a partir do texto; **[hipótese]** = conjectura a verificar.

---

## 1. Referência completa

LIU, Yitong; WEN, Jiarui; WANG, Guoqiang. A comprehensive overview of remaining useful life prediction: From traditional literature review to scientometric analysis. **Machine Learning with Applications**, v. 21, art. 100704, 2025. DOI: 10.1016/j.mlwa.2025.100704. (p. 1)

- Afiliação: School of Mathematics, Physics and Statistics, Shanghai University of Engineering Science, Xangai, China (p. 1). Autor correspondente: G. Wang (p. 1).
- Histórico editorial: recebido em 11 maio 2025; revisado em 27 jun. 2025; aceito em 1 jul. 2025; disponível on-line em 18 jul. 2025 (p. 1).
- Licença: CC BY-NC 4.0; ISSN 2666-8270 (p. 1).
- Paginação: artigo numerado (100704), sem intervalo de páginas impresso; o PDF tem 20 páginas (pp. 1–16 de texto, pp. 17–20 de referências).
- Financiamento: National Natural Science Foundation of China, n. 12171307 e 11971302 (p. 17).
- Palavras-chave declaradas: Remaining useful life; Prognostics and health management; Model-based methods; Data-driven methods; Hybrid methods; CiteSpace; Scientometric analysis (p. 1).

## 2. Objetivo do artigo

**[fato]** Oferecer uma visão geral ("overview") da predição de RUL em duas frentes: (i) revisão metodológica tradicional — taxonomia em métodos baseados em modelo, orientados a dados e híbridos; processo de predição; conjuntos de dados de referência; ferramentas de implementação — e (ii) análise cientométrica de 3442 artigos da Web of Science (WoS) com o CiteSpace, cobrindo áreas de pesquisa, grupos, periódicos, evolução de palavras-chave e tendências (p. 1–2).

**[fato]** Justificativa apresentada: revisões anteriores "often focus narrowly on algorithmic taxonomies or application-specific evaluations"; Lei et al. (2018) não cobriram arquiteturas híbridas de aprendizado profundo; Pei et al. (2019) omitiram perspectiva bibliométrica; Wang et al. (2023) e Li et al. (2024b) careciam de "an integrated view of technical evolution and research dynamics" (p. 1–2).

**[fato]** Estrutura: Seção 2 (paradigmas), 3 (processo), 4 (datasets), 5 (ferramentas), 6 (cientometria), 7 (tendências e conclusão) (p. 2, Fig. 1).

## 3. Sistema/componente e mecanismo(s) de degradação tratados

**[fato]** Trata-se de revisão genérica, sem sistema-alvo único. Os domínios de aplicação enumerados para métodos baseados em modelo são (p. 2–3):

| Domínio | Mecanismos / leis físicas citadas | Estimadores citados |
|---|---|---|
| Engenharia aeroespacial | Propagação de trinca por fadiga (lei de Paris, fator de intensidade de tensão); curvas S-N; equações de fluência | EKF |
| Máquinas rotativas | Desgaste (lei de Archard) em engrenagens e mancais; modelos dinâmicos sob carga variável; modelos térmicos (sobreaquecimento, falha de lubrificação); vibração | PF, HMM |
| Baterias | Modelo Doyle–Fuller–Newman; crescimento de SEI; perda de capacidade; flutuação térmica | Filtro de Kalman (SOC/SOH) |
| Turbinas eólicas | Regra de Miner (dano acumulado); fluência; ressonância vibratória | PF, HMM |

**[fato]** Os objetos típicos identificados na cientometria são "rolling bearing", "lithium-ion batteries", "electric vehicles" e "state of charge" (p. 14), além de motores turbofan (C-MAPSS), células a combustível e ferramentas de corte (citações dispersas, p. 4–7).

**[fato]** Menções a equipamentos elétricos são marginais: (a) na Tabela 1, o cenário típico do modelo ARMA inclui "Vibration data for motors, electrical equipment [...] single-sensor temperature monitoring" (p. 4); (b) na aquisição de dados, "temperature sensors monitor thermal stresses in engines and electrical systems" (p. 8); (c) a referência Chen et al. (2024) trata de RUL de IGBT por fusão de características multi-fonte (p. 15; lista de referências p. 17); (d) o periódico *Microelectronics Reliability* aparece com 53 artigos (1,47%) entre as 20 principais fontes (p. 14, Tabela 6).

**[fato + alerta de leitura]** Na Seção 2.3.2 lê-se: "Recent advances in signal decomposition-enhanced deep learning have addressed partial discharge data challenges. For instance, Liu et al. (2024a) developed a [...] VMD-optimized CNN-BiGRU framework, which eliminates the need for complete charge–discharge cycles" (p. 7). **[inferência]** O termo "partial discharge" refere-se a *descarga parcial (incompleta) de bateria* — a referência Liu et al. (2024a) intitula-se "A hybrid deep learning approach for remaining useful life prediction of lithium-ion batteries based on discharging fragments" (p. 18) — e **não** a descargas parciais dielétricas (PD) em isolamento. Esse falso cognato deve ser evitado ao citar o artigo no contexto de isolamento de estator.

**[inferência]** Não há qualquer tratamento de isolamento elétrico, envelhecimento dielétrico, sobretensões de manobra, estresse térmico de partida ou motores de indução de média tensão.

## 4. Indicadores/precursores de degradação usados

Por ser revisão, o artigo não mede grandezas; ele cataloga as usadas na literatura. Registro abaixo o que é explicitado, com unidade quando o texto a fornece.

**Sensores e características (Seção 3.1–3.2, p. 8):**
- **[fato]** Sensores comuns: vibração, temperatura, tensão elétrica, pressão, "selected based on equipment failure modes" (p. 8). Unidades não declaradas.
- **[fato]** Características no domínio do tempo: RMS, curtose; no domínio da frequência: "spectral characteristics"; transformada wavelet para realce de características (p. 8).
- **[fato]** Propriedades desejáveis de um Health Indicator (HI): monotonicidade, robustez e "trendability" (p. 8, citando Lei et al., 2018).
- **[fato]** Taxonomia de HI: *Physics-based HI* (PHI: RMS, variância, derivados de mecanismo físico) vs. *Virtual HI* (VHI: fusão de vários PHIs/sinais via PCA, mapas auto-organizáveis, autoencoders, GAN "skip-convolution" de Qi et al., 2024) (p. 8).
- **[fato]** Bibliotecas de extração: *tsfresh* (média, variância, taxa de cruzamento por zero, energia FFT, autocorrelação); *PyWavelets* (DWT multirresolução para sinais não estacionários, vibração); *lifelines* (Kaplan–Meier, Cox, dados censurados) (p. 11, Tabela 3).

**Conjuntos de dados de referência (Seção 4, p. 9–10):**
- **[fato]** C-MAPSS (NASA): quatro subconjuntos FD001–FD004; séries "run-to-failure" com temperatura, pressão e velocidade de rotação; condições operacionais e modos de falha distintos (p. 9). Taxa de amostragem não citada.
- **[fato]** FEMTO/PRONOSTIA (IEEE PHM 2012): ensaio acelerado de rolamentos com força radial "exceeding the maximum dynamic load", velocidade constante; dois acelerômetros e um termopar; **falha definida por amplitude de vibração > 20 g** (p. 9). Taxa de amostragem não citada.
- **[fato]** IMS (Univ. Cincinnati/NASA): três subconjuntos; quatro rolamentos Rexnord ZA-2115 de dupla carreira; acelerômetros nas carcaças; tampão magnético coleta detritos no retorno de óleo; parada quando o acúmulo de detritos excede um limiar; **amostragem 20,48 kHz** (p. 10).
- **[fato]** NASA Battery Prognostics: tensão, temperatura e corrente "in high resolution" sob regimes variados de carga/descarga (p. 10).
- **[fato]** CALCE: capacidade de longo prazo, resistência interna e perfis de queda de tensão sob taxas de descarga e temperaturas ambientes variáveis (p. 10).

**[inferência]** Nenhum indicador dielétrico (descargas parciais, tan δ, capacitância, resistência de isolamento/índice de polarização, tensão de ruptura residual) é mencionado.

## 5. Modelo/algoritmo

**Classe:** revisão (survey metodológico + análise cientométrica). Não propõe modelo novo nem reporta hiperparâmetros de modelos de RUL.

### 5.1 Equações transcritas (numeração original)

Convenção de transcrição: notação simplificada em texto; índices e sobrescritos conforme o original.

- **SVM (p. 3, eq. 1)**, atribuída a Tipping (1999):
  y(x) = Σ_{n=1}^{N} ω_n K(x, x_n) + ε, com ω_n pesos, K(·) kernel e ε ruído independente (p. 3–4).
  **[inferência]** A equação e a citação correspondem ao *Relevance Vector Machine* (Tipping, 1999, listado na p. 19), não ao SVM de Cortes & Vapnik (1995); a forma funcional é a mesma, mas a atribuição é imprecisa.

- **GPR (p. 4–5, eqs. 2–7):**
  (2) f(x) ~ N(μ(x), k(x, x'));
  (3) k_SE(x, x') = σ_f² exp[−(x − x')²/(2 l²)], com variância de sinal σ_f² e escala l;
  (4) y = f(x) + ϵ, ϵ ~ N(0, σ²);
  (5) y ~ N(0, K(X, X) + σ_n² I_n);
  (6) f̄* = K(x*, X) [K(X, X) + σ_n² I_n]^{-1} y;
  (7) cov(f*) = k(x*, x*) − K(x*, X) [K(X, X) + σ_n² I_n]^{-1} K(X, x*).
  Há ainda a prior conjunta [y; f*] ~ N(0, [[K(X,X)+σ_n² I_n, K(X,x*)],[K(x*,X), k(x*,x*)]]) e a posterior f*|X,y,x* ~ N(f̄*, cov(f*)), sem numeração (p. 5).
  **[inferência]** A variância do ruído aparece como σ² na eq. (4) e σ_n² nas eqs. (5)–(7): inconsistência notacional menor.

- **Neurônio artificial (p. 5, eq. 8):** y = f(Σ_{i=1}^{n} w_i x_i + b).

- **CNN (p. 5, eqs. 9–11):**
  (9) y^{l(i,j)} = K_i^l * x^{l(r_j)} = Σ_{j'=0}^{W−1} K_i^{l(j')} x^{l(j+j')}, W largura da janela de convolução;
  (10) a^{l(i,j)} = max{0, y^{l(i,j)}} (ReLU);
  (11) p^{l(i,j)} = max_{(j−1)V+1 ≤ t ≤ jV} {a^{l(i,t)}} (max pooling, V largura de pooling).

- **RNN (p. 6, eqs. 12–13):** h_t = tanh(W_h h_{t−1} + W_x x_t + b_h); y_t = W_y h_t + b_y.

- **LSTM (p. 6, eqs. 14–19):**
  (14) f_t = σ(W_f·[h_{t−1}, x_t] + b_f); (15) i_t = σ(W_i·[h_{t−1}, x_t] + b_i);
  (16) C̃_t = tanh(W_C·[h_{t−1}, x_t] + b_C); (17) o_t = σ(W_o·[h_{t−1}, x_t] + b_o);
  (18) C_t = f_t·C_{t−1} + i_t·C̃_t; (19) h_t = o_t·tanh(C_t).

### 5.2 Estruturas conceituais

- **[fato]** Modelos estatísticos (p. 3–4, Tabela 1): processo de Wiener (degradação contínua, ruído gaussiano, inferência bayesiana; sensível a ruído não gaussiano, fraco em estágio inicial, "inapplicable to strict monotonic degradation"); processo Gamma (monotônico não decrescente, interpretável, "cannot handle degradation reversal"); ARMA (linear, estacionário, curto prazo); cadeias de Markov (estados discretos de saúde); Weibull (requer dados abundantes de falha; fraco em estágio inicial/dados esparsos).
- **[fato]** Híbridos (p. 6–7, Fig. 4): modelo físico + dados (RRBF+AR; modelo exponencial duplo + RVM; GM + RVM; PF como "bridging technique" com GPR, RNA, LSTM; PINN com restrições físicas na função de perda, p. ex. Liao et al. 2023 em C-MAPSS; E et al. 2025); dados + dados (WMNN+GPR; Bi-LSTM + transfer learning; CNN-LSTM; VMD-CNN-BiGRU; GA+ELM).
- **[fato]** Tabela 2 (p. 8): comparação dos três paradigmas — baseados em modelo: alta interpretabilidade, exigem conhecimento especialista, pouca adaptabilidade; orientados a dados: flexíveis/escaláveis, exigem grandes conjuntos rotulados, sem interpretabilidade física; híbridos: robustos em condições incertas, maior complexidade e custo computacional.
- **[fato]** Processo em quatro etapas (p. 7, Fig. 5): (1) aquisição de dados; (2) construção de HI; (3) divisão em estágios de saúde; (4) predição de RUL contra limiar de falha predefinido.
  **[inferência]** O texto atribui o processo a "Lei et al., 2016a", mas a obra que sistematiza exatamente essas quatro etapas, pela lista de referências, é Lei et al. (2018), "Machinery health prognostics: A systematic review from data acquisition to RUL prediction" (p. 18); as duas entradas de 2016 tratam de diagnóstico não supervisionado (IEEE TIE) e de um método baseado em modelo (IEEE TR). Provável erro de chave de citação.
- **[fato]** Divisão de estágios (p. 8): dois estágios (degradação consistente no estágio não saudável; ex.: Wiener não linear de Lin et al., 2021; estratégia adversarial de Liu et al., 2024b; detecção de "first predicting time" + incerteza de Chen et al., 2023) vs. multiestágio (sub-estágios por modo de falha/condição operacional; PCA+HI; K-means; HMM).
- **[fato]** Predição (p. 8–9): seleção e treino do modelo; atualização contínua com dados em tempo real; quantificação de incerteza por Monte Carlo e inferência bayesiana; avaliação por MSE/RMSE; validação cruzada ou conjunto independente.
- **[fato]** Ferramentas (p. 10–11): Python como padrão; NumPy, Pandas, Scikit-learn; TensorFlow/Keras (tf.data com janela deslizante) e PyTorch; tsfresh, PyWavelets, lifelines.

### 5.3 Parâmetros da análise cientométrica (únicos "hiperparâmetros" declarados)

- **[fato]** Fonte: WoS Core Collection; consulta "Remaining useful life prediction" em título, resumo, palavras-chave de autor e Keywords Plus → 3796 registros; filtro: apenas artigos de periódico em inglês revisados por pares (excluídos anais, capítulos, preprints) + triagem manual de título/resumo (excluídos contextos biológicos/clínicos) → **3442 artigos** (p. 10).
- **[fato]** CiteSpace 6.3.R1; fatia temporal de 1 ano; nós "Countries", "Institutions" (redes) e "Keywords" (co-ocorrência, clusterização, burst) (p. 11).
- **[fato]** Clusterização de palavras-chave: janela 1997–2024; g-index (k = 5); poda Pathfinder; rotulagem LLR (p. 13).

## 6. Dados e experimento

**[fato]** Não há ensaio experimental nem treinamento de modelos. O único "experimento" é a análise bibliométrica descrita em 5.3. Os datasets da Seção 4 são descritos, não utilizados (p. 9–10).

**[fato]** Sobre limitações dos dados de campo: "Since it is hard to collect real data all the way until a machine fails, researchers often use simulated scenarios or lab experiments instead. While useful, these approaches may not fully capture real-world conditions. As a result, simulated datasets are widely used in RUL research" (p. 8).

**[fato]** Disponibilidade de dados: "Data will be made available on request" (p. 17).

## 7. Métricas e resultados numéricos

**Métricas de RUL mencionadas:** MSE e RMSE; validação cruzada ou conjuntos independentes (p. 9). **[fato]** Nenhum resultado numérico de desempenho de modelo de RUL (RMSE, score, etc.) é reportado no artigo — apenas qualificações ("outperformed", "high accuracy") de trabalhos citados (p. 4–7, 15–16).

**Resultados cientométricos (todos [fato]):**
- Volume: baixo de 1997 a 2011; crescimento rápido a partir de 2011; pico de **686 artigos em 2023**; 2024 parcial por corte em meados do ano (p. 10, Fig. 6).
- Áreas: Engineering 2477; Computer Science 766; Instruments & Instrumentation 592 artigos (p. 11, Fig. 7).
- Rede de países: N = 79, E = 263, densidade = 0,0854 (p. 11).
- Tabela 4 (p. 11) — país, centralidade, contagem: China 0,25 / 2361; EUA 0,27 / 479; França 0,17 / 192; Inglaterra 0,28 / 157; Canadá 0,03 / 149; Coreia do Sul 0,06 / 130; Itália 0,11 / 115; Índia 0,03 / 87; Singapura 0,00 / 79; Alemanha 0,07 / 61.
- Tabela 5 (p. 13) — instituições: Beihang 150; Xi'an Jiaotong 124; Chongqing 105; NUAA 95; Shanghai Jiao Tong 85; CAS 75; Harbin IT 75; UESTC 73; CNRS 70; Rocket Force Univ. of Eng. 65.
- Tabela 6 (p. 14) — periódicos (artigos, % do total): Reliability Engineering & System Safety 243 (6,76%); IEEE Access 154 (4,28%); Mechanical Systems and Signal Processing 125 (3,48%); IEEE Trans. Instrumentation and Measurement 123 (3,42%); Sensors 100 (2,78%); Measurement 94 (2,61%); IEEE Trans. Reliability 87 (2,42%); Measurement Science and Technology 87 (2,42%); Energies 83 (2,31%); Journal of Energy Storage 81 (2,25%); Applied Sciences 79 (2,20%); IEEE TII 60 (1,67%); IEEE TIE 59 (1,64%); Applied Energy 54 (1,50%); Energy 54 (1,50%); Microelectronics Reliability 53 (1,47%); QREI 46 (1,28%); J. Power Sources 44 (1,22%); IEEE Sensors J. 41 (1,14%); Applied Soft Computing 36 (1,00%); Eng. Appl. of AI 36 (1,00%).
- Rede de palavras-chave: 263 nós; **modularidade Q = 0,8692**; **silhueta média = 0,9603**; 13 agrupamentos em três temas (métodos, problemas, objetos) (p. 13, Fig. 10).
- Evolução de métodos: 1997–2010 "regression analysis"/condition monitoring; 2010–2019 particle filter, SVM, CBM, feature extraction; depois CNN/LSTM; desde 2019 attention e transfer learning (p. 13–14).
- Bursts (Tabela 7, p. 16; texto p. 15): 'condition monitoring' 2000–2018; 'particle filter' 2009–2019; 'support vector machines' e 'degradation modeling' 2013–2020; deep 'learning' 2016–2019; 'recurrent neural networks' e 'temporal convolutional networks' a partir de 2022; 'battery management systems' e 'wind turbines' em ascensão. **[fato]** A Tabela 7 é uma imagem; seus valores de intensidade de burst não constam do texto extraído.

## 8. Limitações

**Declaradas pelos autores:**
1. **[declarada]** Métodos orientados a dados dependem de "large-scale, high-quality labeled datasets" (p. 1) e "performance may degrade in sparse/noisy data; lacks physical interpretability" (p. 8, Tabela 2).
2. **[declarada]** Métodos baseados em modelo exigem "expert knowledge of system dynamics; limited adaptability to changing environments or complex systems" (p. 8).
3. **[declarada]** Híbridos: "Higher implementation complexity; computationally demanding; requires careful model fusion and tuning" (p. 8) e "increased complexity in implementation and maintenance" (p. 7).
4. **[declarada]** Dados simulados/laboratoriais "may not fully capture real-world conditions" (p. 8).
5. **[declarada]** Limitações por modelo estatístico (Tabela 1, p. 4): Wiener sensível a ruído não gaussiano e fraco no início; Gamma incapaz de reversão; ARMA falha em não estacionariedade; Markov requer estados predefinidos; Weibull requer dados abundantes de falha.
6. **[declarada]** SVM: "require careful parameter tuning and are limited in their ability to capture long-term temporal dependencies" (p. 4); GPR: "challenges in scalability, kernel engineering, and temporal sequence modeling" (p. 5); CNN: limitação em dependências temporais longas (p. 5); RNN: gradientes que desaparecem/explodem (p. 6).
7. **[declarada]** Corpus cientométrico restrito a artigos de periódico em inglês; 2024 incompleto (p. 10).
8. **[declarada]** LLMs/IA generativa para PHM: "further exploration is needed to align these tools with PHM applications" (p. 16).

**Identificadas por mim:**
9. **[minha inferência]** Ausência total de métricas numéricas comparativas: o leitor não consegue hierarquizar os métodos por desempenho; a revisão é enumerativa, não avaliativa.
10. **[minha inferência]** Corpus baseado em uma única string de busca ("Remaining useful life prediction"); trabalhos que usam "lifetime estimation", "life consumption", "ageing" ou "end-of-life" (comuns na literatura de isolamento elétrico, eletrônica de potência e transformadores) tendem a ficar fora, o que pode subestimar a presença de equipamentos elétricos nos clusters.
11. **[minha inferência]** Nenhum cluster ou palavra-chave de "insulation", "partial discharge" (sentido dielétrico), "stator", "motor" ou "transformer" é reportado (p. 13–15), indicando que o mapa de tendências pouco informa sobre prognóstico de isolamento.
12. **[minha inferência]** Explicações causais na cientometria ("Chinese dominance [...] is driven by substantial government funding, rapid industrial growth, and strong academic programs", p. 11; "culture of technological innovation" na América do Norte, p. 12) não são sustentadas por dados do próprio estudo.
13. **[minha inferência]** Inconsistências bibliográficas: eq. (1) atribuída a Tipping (1999) — RVM — como SVM (p. 3); processo em quatro etapas atribuído a Lei et al. (2016a) quando a referência coerente é Lei et al. (2018) (p. 7 vs. p. 18); a entrada "Zhu et al. (2014)" carrega DOI 10.1109/ITEC55900.2023.10187083, idêntico ao de Guo et al. (2023) (p. 17 e p. 20); Li et al. (2023a) STAIRnet listado com volume 24(3) de 2024 (p. 18).
14. **[minha inferência]** O uso de "partial discharge" no sentido de descarga parcial de bateria (p. 7) é ambíguo e pode induzir a erro em buscas bibliográficas por PD dielétrica.
15. **[minha inferência]** Não se discute o problema de dados censurados/sobreviventes (apenas menção ao *lifelines*, p. 11), nem métricas específicas de prognóstico (α-λ, PH, convergência) além de MSE/RMSE; a referência a Lei et al. (2018) substitui essa discussão (p. 9).
16. **[minha inferência]** Falta qualquer análise de custo, ROI ou decisão de manutenção com números; as menções a custo são qualitativas (ver Seção 11).

## 9. Transferibilidade para o problema-alvo

Problema-alvo: isolamento de estator de motor de indução de MT (2,3–13,8 kV) submetido a (a) sobretensões de manobra de VCB (chopping, reignições múltiplas, frentes íngremes/dV/dt) com/sem snubber tiristorizado ativo (trabalho A) e (b) estresse térmico de partidas de grandes motores sob contingência N-1 com load shedding seletivo (trabalho B).

### 9.1 O que se transfere

1. **Taxonomia e critério de escolha de paradigma** (p. 7–8, Tabela 2). **[inferência]** Para isolamento de estator há leis físicas de envelhecimento consolidadas — térmico (Arrhenius/Montsinger; classes térmicas IEC 60034-18 [INSERIR CITAÇÃO]) e elétrico (lei de potência inversa; IEC 60034-18-41/42 para repetitividade de impulsos [INSERIR CITAÇÃO]) — mas dados run-to-failure de campo são raros. Pela própria Tabela 2, isso aponta para o paradigma **híbrido** (modelo físico de dano acumulado + atualização bayesiana/PF com dados de monitoramento), e não para deep learning puro. A menção do artigo a kernels GPR com lei de Arrhenius embutida (Liu et al., 2019a, p. 5) e a PINN (p. 6) é diretamente reaproveitável como arquitetura.
2. **Processo em quatro etapas** (p. 7, Fig. 5) como espinha dorsal do método de monitoramento: aquisição → HI → divisão de estágios → RUL contra limiar. **[inferência]** A "divisão multiestágio por modo de falha/condição operacional" (p. 8) encaixa-se num isolamento sujeito a dois estressores distintos (surtos de VCB e térmico de partida): estágios podem ser delimitados por eventos discretos (manobras, partidas) e não apenas por tempo.
3. **Critérios de qualidade de HI** — monotonicidade, robustez, trendability (p. 8) — e a distinção PHI/VHI (p. 8). **[inferência]** Um HI físico candidato seria a fração de vida consumida por dano acumulado (análogo à regra de Miner citada na p. 2 para turbinas eólicas), somando parcelas térmicas (por partida, a partir de temperatura de enrolamento) e elétricas (por manobra, a partir de amplitude/dV/dt/número de reignições); um VHI poderia fundir PD, tan δ e capacitância quando disponíveis.
4. **Processos estocásticos monotônicos** (Gamma, p. 3–4) e **Weibull** (p. 3–4). **[hipótese]** A degradação dielétrica é essencialmente irreversível, o que favorece o processo Gamma sobre o de Wiener; a distribuição de Weibull é a base tradicional de análise de dados de ruptura de isolamento (IEEE Std 930 [INSERIR CITAÇÃO]).
5. **Quantificação de incerteza e validação** (p. 8–9, 15): Monte Carlo, inferência bayesiana, intervalos de confiança; validação cruzada ou conjuntos independentes. **[inferência]** Coerente com os módulos `reliability_monte_carlo.py` e `power_flow_monte_carlo.py` já existentes no repositório; o mesmo ferramental pode propagar a incerteza de I_chop (média 5 A, σ 1 A nos defaults de `vcb_model_emitter.py`) e di/dt crítico até a distribuição de RUL.
6. **Aprendizado por transferência/adaptação de domínio entre máquinas com incerteza** (Zeng et al., 2024, p. 15) e **aprendizado on-line com determinação automática do "first prediction time"** (Wang et al., 2025a, p. 16). **[inferência]** Frotas de motores MT são heterogêneas e cada unidade tem poucos ciclos; essas duas linhas respondem exatamente a esse cenário.
7. **Modelo de ensaio acelerado** do FEMTO/PRONOSTIA (carga acima do limite dinâmico, critério de falha explícito em 20 g, p. 9) e do IMS (critério por detritos, 20,48 kHz, p. 10). **[inferência]** Servem de modelo de protocolo para um ensaio acelerado de bobinas/formetes sob impulsos repetitivos com dV/dt controlado, com critério de falha declarado (p. ex., PDIV abaixo de limiar ou ruptura) — o artigo não fornece o protocolo, apenas o padrão de documentação.
8. **Ferramental** (p. 10–11): Python, tsfresh, PyWavelets (útil para transitórios de manobra, sinais não estacionários), *lifelines* para dados censurados (motores retirados de serviço sem falha).
9. **Posicionamento editorial** (Tabela 6, p. 14): RESS, MSSP, IEEE TIM, IEEE TR e Microelectronics Reliability como veículos de referência para o capítulo de RUL da tese.

### 9.2 O que não se transfere (e por quê)

1. **Indicadores**: nenhum indicador dielétrico é tratado; vibração, temperatura de óleo, detritos, capacidade de bateria não têm análogo direto. A cadeia sensor → HI precisa vir de outra literatura (PD on-line, tan δ, monitoramento de temperatura de enrolamento) [INSERIR CITAÇÃO].
2. **Natureza do estressor**: todos os modelos revistos pressupõem séries temporais contínuas de degradação gradual. Surtos de VCB são eventos impulsivos, raros, de amplitude estocástica (chopping, reignições múltiplas) — a variável natural é a **contagem/severidade de eventos**, não uma série amostrada regularmente. As arquiteturas CNN/LSTM (eqs. 9–19) não modelam "dano por evento" sem reformulação (p. ex., processo de choque composto — não abordado no artigo).
3. **Ausência de modelo estresse → dano**: o repositório já calcula o estresse (reignição em MODELS/ATP com I_chop, di/dt crítico, recuperação dielétrica 17 kV/ms; snubber; partida de motor com queda de tensão e tempo de aceleração), mas o artigo não oferece nenhuma função de transferência de sobretensão/dV/dt ou de temperatura de partida para consumo de vida.
4. **Datasets**: C-MAPSS, FEMTO, IMS, NASA Battery e CALCE não têm relação com isolamento de estator; não há dataset público análogo citado.
5. **Decisão e custo**: o artigo não traz modelo de decisão de manutenção, custo de parada ou ROI; a ligação com load shedding (trabalho B) — que é um problema de otimização multiobjetivo — não encontra apoio metodológico aqui.
6. **Métricas**: MSE/RMSE (p. 9) são insuficientes para RUL em regime de poucos eventos; métricas específicas de prognóstico não são discutidas.
7. **Cientometria**: os mapas de tendência não contêm o domínio elétrico de máquinas; servem apenas para justificar lacuna ("gap") na introdução da tese, não para orientar métodos.

### 9.3 Nota de transferibilidade: **2/5**

**[inferência]** Justificativa: transfere estrutura (taxonomia, pipeline de quatro etapas, critérios de HI, quantificação de incerteza, ferramental, cenário de dados escassos/censurados) e argumentos para escolha de paradigma híbrido; não transfere indicador, modelo de dano, dataset, métrica específica nem lógica de decisão. É leitura de enquadramento, não de método.

## 10. Citações literais relevantes

1. "Within PHM systems, Remaining Useful Life (RUL) prediction has emerged as a cornerstone for reducing unexpected downtimes and maintenance costs (Jardine et al., 2006; Lee et al., 2014)." (p. 1)
2. "Thus, the choice of method depends on application requirements, data availability, and system complexity." (p. 7)
3. "RUL prediction is a critical component of machinery health prognostics, involving a structured four-stage process (Lei et al., 2016a): data acquisition, health indicator construction, health stage division, and RUL prediction." (p. 7)
4. "Since it is hard to collect real data all the way until a machine fails, researchers often use simulated scenarios or lab experiments instead. While useful, these approaches may not fully capture real-world conditions." (p. 8)
5. "Effective HIs simplify the modeling and enhance prediction accuracy by reflecting the deterioration of machinery with properties such as monotonicity, robustness, and trendability (Lei et al., 2018)." (p. 8)
6. "RUL refers to the estimated time before a machine reaches a failure threshold, beyond which its performance becomes unacceptable." (p. 8)
7. "Incorporating uncertainty quantification and validation strategies not only improves prediction accuracy but also enhances the model's applicability in industrial settings, supporting informed maintenance planning and operational decision-making." (p. 9)
8. "Another key trend is the emergence of explainable AI as a critical research frontier, especially in regulated or safety-critical domains. Furthermore, by providing transparent and interpretable model outputs, explainable AI enhances trust and promotes broader adoption of RUL prediction systems." (p. 16)

## 11. Ligações com os outros temas

### 11.1 RUL e PHM
- **[fato]** Define RUL como tempo estimado até o limiar de falha (p. 8) e situa a predição de RUL como "cornerstone" do PHM na Indústria 4.0 (p. 1).
- **[fato]** Tendências: RNN/LSTM/TCN para dependências sequenciais; inferência bayesiana e GPR para incerteza "in safety-sensitive applications"; sistemas integrados de monitoramento + analítica + decisão on-line "gradually becoming the norm" (p. 15); fusão multi-fonte, quantificação de incerteza epistêmica/aleatória, aprendizado contínuo, transfer learning com poda por destilação (Zheng et al., 2024), modelagem on-line adaptativa, atenção, gêmeos digitais, XAI, LLMs para PHM (p. 15–16).
- **[inferência]** Para a tese, o artigo fornece o vocabulário canônico (HI, PHI/VHI, health stage, first prediction time, failure threshold) e as referências-âncora (Lei et al., 2018; Si et al., 2011; Liao & Köttig, 2014; Li et al., 2024c sobre physics-informed) que devem ser lidas na fonte antes de qualquer citação indireta.

### 11.2 Relação com os trabalhos A e B e com o repositório
- **[inferência]** Trabalho A (snubber tiristorizado): o modelo de reignição já implementado (`app/preprocessor/vcb_model_emitter.py`, `atp_templates/vcb_reignition.mod`, defaults I_chop 5 A, σ 1 A, di/dt crítico 16 A/µs, recuperação dielétrica 17 kV/ms; validação de conexão do snubber em `app/validation/validator_vcb.py`) produz o **estressor**; o artigo sugere que a etapa seguinte é converter esse estressor em HI físico de dano acumulado e, então, em RUL com incerteza. O snubber entra como variável de decisão que altera a taxa de consumo de vida — o artigo não trata de mitigação, apenas de predição.
- **[inferência]** Trabalho B (load shedding N-1): `app/postprocessor/motor_starting.py` e `motor_reaccel.py` já calculam queda de tensão e tempo de partida; o estresse térmico por partida pode alimentar a parcela térmica do mesmo HI. A revisão não aborda otimização multiobjetivo nem surrogates; o vínculo é apenas o HI compartilhado.
- **[inferência]** `app/postprocessor/reliability.py` (IEEE 1366: SAIFI, SAIDI, MTBF, MTTR) opera com taxas médias; um estimador de RUL condicionado ao histórico de manobras/partidas permitiria substituir MTBF constante por taxa de falha dependente do estado — ponte natural entre o módulo existente e um módulo de prognóstico.

### 11.3 Argumentos de custo, decisão e manutenção (C-Level)
Transcrições (todas qualitativas; o artigo não apresenta valores monetários):
- "Within PHM systems, Remaining Useful Life (RUL) prediction has emerged as a cornerstone for reducing unexpected downtimes and maintenance costs" (p. 1).
- "Both methods require a deep understanding of system dynamics and are particularly effective for accurate, interpretable predictions essential for maintenance planning." (p. 2)
- "This systematic process supports informed maintenance decisions and enhances operational efficiency, as shown in Fig. 5." (p. 7)
- "Bearings are vital components in industrial machinery, and their failure can cause significant downtime and costly repairs." (p. 9)
- "[...] supporting informed maintenance planning and operational decision-making." (p. 9)
- "Real-time health estimation and predictive maintenance are becoming more important as core industrial needs. What is more, integrated systems that combine condition monitoring, intelligent data analytics, and online decision-making are gradually becoming the norm in modern industrial settings." (p. 15)
- "The integration of machine learning and IoT infrastructure enables proactive maintenance strategies across production lines, improving equipment availability and operational efficiency." (p. 15)
- "[...] digital twin frameworks are being widely adopted to simulate physical asset behavior, allowing real-time monitoring, scenario testing, and predictive analysis in virtual environments." (p. 16)
- "[...] explainable AI enhances trust and promotes broader adoption of RUL prediction systems." (p. 16)

**[inferência]** Para um público executivo, o artigo sustenta três mensagens: (i) RUL é a métrica que converte monitoramento em decisão de manutenção; (ii) a escolha entre modelo físico, dados ou híbrido é uma decisão de risco/dados/interpretabilidade, não apenas técnica (Tabela 2, p. 8); (iii) explicabilidade e quantificação de incerteza são pré-requisitos de adoção em domínios regulados/críticos (p. 15–16). **[hipótese]** No contexto de óleo e gás (marca d'água "Petrobras" nos PDFs — hipótese de contexto), a mensagem (iii) é a mais relevante para justificar um módulo computacional auditável no Olivas Power System Studio, em vez de um modelo caixa-preta.
