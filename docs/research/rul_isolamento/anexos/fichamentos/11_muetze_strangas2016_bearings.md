# Fichamento 11 — Muetze e Strangas (2016): vida útil de mancais de acionamentos inversorizados — métodos e direções de pesquisa, da manutenção localizada ao prognóstico

Convenções deste fichamento: "fato do artigo" = conteúdo verificável no texto extraído, com página indicada segundo os marcadores "===== PAGE N =====" (p. 1 corresponde à página impressa 63 da revista; p. 11, à página impressa 73); "fato do repositório" = conteúdo verificado no código do Olivas Power System Studio; "inferência minha" = conclusão derivada por mim a partir do texto ou do repositório; "hipótese" = proposição ainda não verificada. As Figs. 1–4 não estão disponíveis no texto extraído, apenas suas legendas e rótulos; a única equação numerada é a (1), p. 8. A equação da função de transferência mecânica (p. 5) veio ilegível na extração e é tratada na Seção 5.

---

## 1. Referência completa

MUETZE, Annette; STRANGAS, Elias G. The Useful Life of Inverter-Based Drive Bearings: Methods and research directions from localized maintenance to prognosis. **IEEE Industry Applications Magazine**, [INSERIR CITAÇÃO: volume e número não constam no texto extraído], p. 63–73, jul./ago. 2016. DOI: 10.1109/MIAS.2015.2459117.

Dados complementares (fato do artigo):
- Data de publicação: 2 maio 2016 (p. 1). Rodapé de licença: "1077-2618/16©2016IEEE" (p. 1).
- Afiliações (p. 11): A. Muetze — Graz University of Technology, Áustria, Fellow IEEE; E. G. Strangas — Michigan State University, East Lansing, Senior Member IEEE.
- Origem (p. 11): "This article first appeared as 'Methods and Research Directions for the Estimation of the Remaining Useful Life of Bearings of Inverter-Based Drives' at the 2014 IEEE IAS Annual Meeting."
- Hipótese (a verificar no IEEE Xplore): a edição jul./ago. 2016 da IEEE IAS Magazine corresponde ao v. 22, n. 4. Não confirmar sem consulta à fonte.
- Observação editorial (fato do artigo, p. 10–11): a lista de referências contém duplicatas — [30] e [39] são o mesmo trabalho (Tischmacher e Gattermann, ICEM 2012, p. 1764–1770) e [29] e [66] são o mesmo trabalho (Kriese et al., ICEM 2012, p. 1735–1739; em [66] o primeiro autor aparece grafado "K. Kriese").
- Ligação interna ao conjunto de fichamentos: a referência [4] deste artigo é o trabalho fichado em 09 (Strangas, Aviyente, Neely e Zaidi, IEEE TIE 2013), citado aqui como fundamento de que "prognosis ... promises to be more accurate and useful than diagnosis alone" (p. 2). A referência [7] (Nectoux et al., PRONOSTIA, PHM 2012) e a [44] (repositório NASA PCoE) são as bases públicas de mancais discutidas no artigo (p. 5).

## 2. Objetivo do artigo

Fato do artigo (p. 1, resumo): "we try to bridge the gap between the knowledge of the effects of bearing currents as they may occur with modern power electronics-based variable-speed drives and the prediction of a bearing's remaining useful life (RUL). We discuss the measurements used and the procedures and methods that have been developed. We identify what we consider to be the necessary next steps and the open questions that exist as well as what we consider to be necessary actions to establish tools and methods for the reliable estimation of the RUL of bearings using measurements of different characteristics and costs."

Fato do artigo (p. 3): o artigo "aims to comprehensively investigate possibilities to bridge the gap between the many works on bearing failure, mainly due to mechanical reasons (radial and axial forces), and the prediction of the bearing RUL and the fragmented knowledge available on bearing damage due to electric stress", descrevendo "the state of the art in predicting failures in bearings of electrical drives based on measurements" e discutindo "the issues that have to be addressed for timely maintenance based on estimating fault development".

Fato do artigo (p. 2): distinção conceitual central — "Prognosis, as opposed to diagnosis, is a process, a tool for CBM, and a means to foretell the evolution of an undesirable condition (here, a fault) and to predict when the device will no longer operate as designed or desired (Figure 1). The usefulness of this metric closely depends on the accuracy of the prediction and the confidence in it during the decision making."

Inferência minha: trata-se de um artigo de revisão e posicionamento (position paper), sem contribuição algorítmica nem experimental própria. Seu valor está (i) no arcabouço conceitual de prognóstico (Figs. 1 e 4), (ii) na taxonomia de causas/indicadores/métodos e (iii) na identificação explícita das lacunas — em particular, a inexistência de modelo quantitativo de progressão de dano por estresse elétrico e de base de dados run-to-failure com causa elétrica.

## 3. Sistema/componente e mecanismo(s) de degradação tratados

Componente (fato do artigo): mancais de rolamento de máquinas elétricas de baixa tensão alimentadas por inversor (acionamentos de velocidade variável baseados em eletrônica de potência). O artigo afirma que "Bearing failures are the primary cause of downtime in electrical drives (e.g., [1])" (p. 2) e que "Bearing faults, which are the dominant causes in low-voltage machines (e.g., [6]), are addressed here" (p. 2).

Origens de falha (fato do artigo, p. 3), em três classes:
1) "mechanical origin (mechanical bearing load as given by radial and axial forces, including eccentricity but also contamination)";
2) "electric origin (electric bearing load as given by bearing currents)";
3) "chemical and environmental causes (have significant effects, but very little systematic study is available) and temperature as both a cause and an effect (plays an important role)".

Mecanismo elétrico (fato do artigo, p. 3): desde meados dos anos 1990, "HF bearing currents that were caused by the interaction between the HF components of the common-mode (CM) voltage of an inverter (i.e., the HF components composed in the steeply rising voltage edges with high dv/dt) and an electric machine were found to put the bearings of modern power electronics-based variable-speed drive systems at risk [13]–[20]". Distinguem-se "discharge currents, which are ideally understood as voltage building first across and then discharging within a bearing, and currents that are directly related to the HF CM current and that are flowing through the bearing" (p. 3).

Progressão do dano elétrico (fato do artigo, p. 3–4): correntes de descarga produzem "localized pits that may translate into a gray trace, frosting, or fluting [24]–[29]"; "Depending on the energy released, the discharge may lead to melting or vaporization of the bearing raceway surface [28]". Segundo [29], "the small craters that are caused by melting are flattened by the rolling bearing balls, resulting only in a frosted raceway, and have been found to have no effect on the lifetime of the bearing. (Only an appropriate regreasing interval is said to be necessary.) The large craters resulting from vaporization will affect the lubricating grease, lead to corrugated patterns, and shorten the lifetime of the bearing" (p. 4). "Similar damage patterns also have been observed for the differential-mode currents [25]" (p. 4). A falha "is developed further by the localized currents and by the breakdown of the grease that results when current flows where these factors are iteratively affecting each other" (p. 4). Acoplamento vibração–descarga: "The impact of the vibrational excitation on the number of bearing voltage breakdowns has been reported [30], and the breakdown occurs in groups of the vibrational excitation frequency at low vibration frequencies" (p. 4).

Mecanismo mecânico (fato do artigo, p. 3): iniciação de fadiga exige "the stress to exceed a threshold value [22]"; cargas sem rotação (true brinelling), vibrações fora de operação (false brinelling) [21]; "Healing [23], the smoothing of sharp edges of a crack or damage zone by the rolling contact, initially reduces vibrations until the damage spreads". Realimentação: deterioração do mancal → excentricidade → "unbalanced magnetic pull" → mais carga no mancal [9] (p. 3).

Contaminação (fato do artigo, p. 3): "water directly degrades the lubricant and surfaces through oxidation, and particles disrupt the lubricant films"; "there has been no study that the authors are aware of that has considered the effect of such conditions on the RUL estimation".

Inferência minha: o artigo NÃO trata do isolamento de estator como objeto de prognóstico. O isolamento aparece apenas indiretamente: (i) a referência [36] (Ferreira, Trovão e de Almeida, ICEM 2008) diagnostica "motor bearings and insulation system condition" via correntes de modo comum e tensão eixo-terra (p. 10–11), e (ii) "stator winding shorts" são listados como falta cujas assinaturas se confundem com as de mancal (p. 9).

## 4. Indicadores/precursores de degradação usados

O artigo não mede nada; cataloga os indicadores da literatura. Taxa de amostragem não é citada para nenhum indicador (fato do artigo: ausência em todo o texto).

| Indicador | Grandeza / unidade | Como é obtido | Página | Observação |
|---|---|---|---|---|
| Aceleração na carcaça (vibração) | aceleração; m/s² (unidade é inferência minha) | acelerômetro no housing; "may be caused by the load rather than the bearings" | p. 4 | 1º em frequência de uso (fato do artigo) |
| Som na vizinhança do mancal | pressão acústica (unidade não declarada) | microfone | p. 4 | 2º em frequência de uso |
| Temperatura das pistas e da carcaça | temperatura; °C (inferência minha) | sensor de temperatura; "can be measured relatively easily" (p. 9) | p. 4, 9 | 3º; também "cause and effect" (p. 3) |
| Correntes de estator e suas componentes HF | corrente; A | sensores já existentes nos terminais do estator ("sensors that are there for other purposes", p. 2) | p. 2, 4 | 4º; preferido por custo |
| Características químicas da graxa | não declarada | análise da graxa; "number and size of spalls in bearing grease" só em grandes instalações, não online (p. 9) | p. 4, 9 | 5º |
| Corrente de modo comum (CM) | corrente; A | medição na alimentação; [34]–[37] | p. 4 | específico do estresse elétrico |
| Tensão de mancal (bearing voltage) | tensão; V | medição direta, "recently proposed [39], [40]"; "even closer to the source ... arguably more accurate" | p. 4 | requer sensor dedicado (custo, p. 9) |
| Pulsações de torque | torque; N·m (inferência minha) | estimadas do acionamento; "closer to the source of the disturbance and lead to a better indication of the fault [3]" | p. 4, 5 | melhor que corrente, segundo [3] |
| Função de transferência mecânica G_mech(jω) | adimensional / resposta em frequência | identificação do sistema de duas inércias + mola (Pacas et al. 2009 [41]); detecção pelo "departure of the transfer function from the ideal function" | p. 5 | ver Seção 5 |
| Potência instantânea / fator de potência instantâneo | W / adimensional | [70], [71]; "a single variable can be extracted to give a more sensitive and accurate indication" | p. 9 | fusão de medições |
| Eficiência do motor | adimensional | Frosini e Bassi [42] | p. 5 | — |
| Causas estimadas: correntes de mancal | corrente; A | NÃO mensuráveis via corrente de estator; "can only be estimated from operating conditions (inverter status, speed, and temperature)" [18], [19], [29], [37], [66] | p. 9 | entrada de "History of Causes" (Fig. 4) |
| Variáveis secundárias | ciclos (contagem), tempo ocioso (h), cargas axiais/radiais (N) | ciclos "can be monitored"; cargas axiais "cannot even be estimated because they depend on alignment" | p. 8, 9 | — |

Features derivadas (fato do artigo, p. 5–6): domínio do tempo — momentos "(mean, variance, skewness, and kurtosis) [50], [51] as well as peaks and crest factor"; em [52], "17 features, and the number was reduced to three using principal component analysis", e "the health indicator evolution is much better than kurtosis in estimating the RUL"; domínio da frequência — Fourier com frequências características "uniquely related to the speed of the rotor, the number of rolling elements, and the fault location", subtração espectral [49], root-MUSIC [53]; tempo–frequência — wavelets [43], [48], distribuição de Wigner e classe de Cohen [46], [54]; em Qiu et al. [48], seleção da wavelet-mãe por similaridade de forma, entropia de Shannon para esparsidade e SVD para escala.

Fato do artigo (p. 4): "Especially in the early stages of a fault, where its manifestation is primarily in certain vibration frequencies, the envelope of the signal may be preferable to work with, as is the use of a weighted frequency window."

## 5. Modelo/algoritmo

Classe: **revisão** (review/position paper). Não há algoritmo próprio, hiperparâmetro ou estrutura de rede. O artigo organiza a literatura em três famílias e defende explicitamente a família híbrida.

Pipeline de diagnóstico (fato do artigo, p. 4): "1) data collection and preprocessing; 2) features and feature selection; 3) categorization."

Pipeline de prognóstico (fato do artigo, Fig. 4, p. 7 — rótulos da figura): "History of Observations", "History of Causes", "Since the Beginning of Operation", "Historic Data", "Model Development" (antes da operação), "Feature Extraction", "Categorization—Statistics", "Prognosis: Probability of Every State", "Next Probable State", "RUL", "Decision on Mitigation/Maintenance", "Possible Update of Model Parameters" (quase tempo real). Legenda: "The flow and timing of information for diagnosis and prognosis."

Requisitos do modelo de evolução (fato do artigo, p. 7): além do modelo, é preciso "calculate the model parameters, either ahead of time or as the fault develops [62]; use measurements to determine the state of the bearing at every sample point; measure or predict the causes of the fault development".

Famílias (fato do artigo):
- Baseadas em dados (p. 6–7): "If a data-based model is to be used alone, a large number of samples or a clear trend that will lead to reliable extrapolation is needed" (p. 6). HMM e filtro de partículas "have received the most attention"; em [63] (caixas de engrenagens) "the particle filter method performed more accurately at the expense of computation time" (p. 7). HMM básico: "three matrices have to be prepared ahead of time: one that relates observations to states (i.e., the state probability matrix), one that relates the probabilities of transitions from one state to another, and the initial-state probability vector"; extrair RUL "is complex"; Soualhi et al. [64] usam "adaptive neuro-fuzzy inference to extrapolate and predict the evolution of features" (p. 7). Kalman: "only useful for linear degradation models with additive white noise"; EKF "approximating the state using a local linearization" (p. 6).
- Baseadas em física (p. 6–7): analogia com propagação de trinca (modelo de Paris) [60], [61]; modelos de correntes de mancal [13]–[20] que, "Except for the distinction between melting and vaporization as a function of the energy released ... are limited to describing the amplitudes and/or likeliness that bearing currents will occur as functions of certain machine operating parameters. Models that describe the fault development in a quantitative way over time and related to observations or measurable quantities have not been developed yet because of a lack of understanding of the underlying mechanisms" (p. 7). "Analytical physics-based predictive models suffer from the fact that the model parameters are not known, only their general forms, and that these parameters change with time and environment" (p. 7); atualização por dados de diagnóstico: Bolander et al. [67].
- Híbridas (p. 6, 9, 10): Zhang et al. [38] "combining statistical prediction and the use of particle filters" (p. 6); "Combining data- and model-based techniques appears to be the appropriate direction for monitoring fault evolution. Using physical models limits the need for extensive training" (p. 9); conclusão: "We expect the problem of the failure prognosis of bearings to require hybrid approaches: data based, enhanced by physical model understanding and interpretation, and, at the same time, combined features arriving from more than one source" (p. 10).

Categorização (fato do artigo, p. 6): LDA [41], clustering, SVM, filtros de partículas, redes neurais, enxames; operadores morfológicos + inferência fuzzy [55]; em [56] (faltas de estator em motores) compararam-se STFT, wavelet não decimada, Wigner e Choi–Williams com classificadores LDC e k-means, avaliados pelo coeficiente de Fisher, concluindo que "the extracted time-frequency feature vectors comprise redundant information"; Cococcioni et al. [57] compararam discriminantes linear/quadrático e redes MLP/RBF.

Equações:
- Eq. (1), p. 8 (fato do artigo, única equação numerada), métrica de validação de prognóstico de Tang et al. [69]:
  V = (E_ref − E_prog) / (E_ref − E_perf)  (1)
  "where E_ref is the cost of performing maintenance as originally scheduled and E_perf corresponds to V = 1, the cost of a perfect prediction when that maintenance is planned immediately before the system failure while giving the user (through prognosis) the right time to plan maintenance." E_prog é o custo associado aos cenários do prognóstico, "which is constant and minimal when the failure occurs during a maintenance window and has different and high values when it occurs before or after this window" (p. 8). Os conceitos de "accuracy and skill" foram tomados "from the experience and literature on climate forecasts" (p. 8). Aplicada originalmente a baterias de íon-lítio, "but the results can be extended to bearings" (p. 8).
- Função de transferência mecânica sem falta, p. 5 (não numerada; fato do artigo): G_mech(jω) de um sistema "consisting of two inertias connected by a spring", "where T_L and T_M are run-up times of the load and motor, T_C is the spring constant, and d is the damping of the spring". A extração de texto embaralhou os termos (aparecem fatores em T_M, T_L, T_C, d, jω e (jω)² sem estrutura recuperável); [INSERIR EQUAÇÃO — transcrever do PDF original, p. 67 impressa]. Uso declarado: "Reconstructing the plant and/or determining its characteristics from this function or observation, in general, is not possible ... Detection is then based on the departure of the transfer function from the ideal function in the case of faults" (p. 5).

Inferência minha: o artigo é agnóstico quanto a arquitetura; sua "estrutura" é o fluxo de informação da Fig. 4, cujo elemento distintivo é o canal paralelo "History of Causes" (causas previstas, não medidas) alimentando o modelo junto com "History of Observations".

## 6. Dados e experimento

Fato do artigo: nenhum experimento próprio é apresentado. Os autores declaram apenas que "We are working on one set of experiments and data sets combining two effects, and we hope they will contribute to further progress in this area" (p. 9).

Bases de dados públicas discutidas (fato do artigo, p. 5): "one from a test bench designed by Rexnord Corporation with data available at the Prognostics Center of Excellence [44] and another from the Franche-Comté Electronique Mécanique Thermique et Optique–Sciences et Technologies Institute [45]–[47]" (PRONOSTIA, [7]). Limitações dessas bases (fato do artigo, p. 7–8): "limited to radial forces as causes and vibrations as measurements"; não incluem "the presence of resonant frequencies in the system because these are minimized in the experiment", "the effect of current and voltage of the motor (these are even more decoupled from the faulted bearing when it is driven through a belt)" e "the effects of the time-varying operation with possible long idle times".

Lacuna experimental declarada (fato do artigo, p. 7): para estresse elétrico, "there is still no database from which the fault development over time and the moment a bearing failure occurs can be estimated". Geração artificial de faltas por corrente de eixo: Stack, Habetler e Harley [68] (p. 8, 11).

Número de amostras/ciclos: não aplicável (fato do artigo: nenhum dado numérico de ensaio é reportado).

## 7. Métricas e resultados numéricos

Fato do artigo: o texto não reporta resultados numéricos próprios (nenhum erro de RUL, acurácia, RMSE ou intervalo de confiança). Os únicos elementos quantificáveis são:

| Item | Valor | Página |
|---|---|---|
| Métrica de valor do prognóstico (Tang et al. [69]) | V = (E_ref − E_prog)/(E_ref − E_perf); V = 1 para predição perfeita | p. 8 |
| Redução de features em [52] | 17 features → 3 componentes principais (PCA) | p. 5 |
| Métodos comparados em [56] | 4 transformadas (STFT, UWT, Wigner, Choi–Williams) × 2 classificadores (LDC, k-means); critério: coeficiente de Fisher | p. 6 |
| Comparação HMM × filtro de partículas [63] | filtro de partículas "more accurately at the expense of computation time" (sem números) | p. 7 |
| Bases públicas run-to-failure | 2 (NASA PCoE/Rexnord; FEMTO-ST/PRONOSTIA) | p. 5 |
| Localizações de falta consideradas | 3 (pista externa, pista interna, esfera) | p. 4 |
| Classes de origem de falta | 3 (mecânica, elétrica, química/ambiental + temperatura) | p. 3 |
| Etapas do diagnóstico | 3 | p. 4 |
| Matrizes do HMM básico | 3 (emissão, transição, estado inicial) | p. 7 |
| Efeito de crateras pequenas (fusão) sobre a vida do mancal, segundo [29] | nenhum (apenas reengraxe); crateras grandes (vaporização) encurtam a vida | p. 3–4 |
| Resultados de modelos puramente de dados [72], [73] | "encouraging results but occasionally unacceptable erroneous RULs" | p. 10 |

Inferência minha: a ausência de métricas é coerente com o gênero (revisão em revista de aplicação). Para fins de comparação quantitativa com os demais artigos do conjunto, este item deve constar como "não reportado".

## 8. Limitações

Declaradas pelos autores (fato do artigo):
1. (declarada, p. 7) Inexistência de modelo físico quantitativo de progressão do dano elétrico: "Models that describe the fault development in a quantitative way over time ... have not been developed yet because of a lack of understanding of the underlying mechanisms."
2. (declarada, p. 7) Inexistência de base de dados run-to-failure sob estresse elétrico.
3. (declarada, p. 6) Eventos abruptos imprevisíveis: "Unexpected abrupt changes in the state of the bearing often occur because of unpredicted events, e.g., spalls, contamination, grease breakdown, and bearing currents ... The randomness of these events makes very early prediction of the RUL nearly impossible."
4. (declarada, p. 9) Correntes de mancal não são observáveis pela corrente de estator; só estimáveis de condições operacionais.
5. (declarada, p. 9) Variáveis de causa não estimáveis (cargas axiais dependem de alinhamento) e dificuldade de coletar histórico: "collecting a large amount of historic data is difficult and often impossible, especially in the case of limited samples or unique operating conditions".
6. (declarada, p. 9) Isolamento de faltas: assinaturas semelhantes para "rotor bar breakage, bearing degradation, eccentricity, or stator winding shorts"; "the categorization has been limited to determining the states of the fault rather than the isolation of different types of faults".
7. (declarada, p. 8) Bases públicas minimizam ressonâncias, desacoplam tensão/corrente do motor e ignoram operação variável com longos tempos ociosos.
8. (declarada, p. 8) "A large number of approaches have led to a confusing number of techniques, but few criteria have been established or applied for their selection and application."
9. (declarada, p. 9) Atualização de parâmetros do modelo de evolução durante a operação "are open problems".
10. (declarada, p. 3) Nenhum estudo conhecido sobre efeito de contaminação na estimativa de RUL.
11. (declarada, p. 9) Confiança no prognóstico "remains to be explored" para mancais; só verificável "through the design and utilization of specific tests in which more than one factor is involved".

Identificadas por mim (inferência minha):
12. Escopo restrito a máquinas de baixa tensão e a mancais; nada sobre média tensão, nem sobre isolamento de estator, nem sobre manobra por disjuntor (VCB). O dv/dt discutido é o de bordas PWM de inversor, com regime de repetição (kHz) e amplitude (barramento CC) muito distintos de surtos de manobra de VCB (eventos raros, frentes de dezenas a centenas de kV/µs, amplitudes de múltiplos p.u.).
13. Nenhuma metodologia de validação é proposta além da menção à métrica V de [69]; o artigo não a aplica.
14. A função de transferência mecânica de [41] (p. 5) é apresentada sem indicação de como se identifica em planta industrial com controlador de banda limitada — o próprio artigo admite que "the controller does not allow any HF signals and changes to be noticed" (p. 5).
15. A afirmação de que crateras de fusão "have no effect on the lifetime" (p. 4) é atribuída a uma única fonte [29]; o artigo não a confronta com [24]–[27].
16. Datação: o conteúdo reflete a literatura até 2014 (origem no IAS Annual Meeting 2014); técnicas de aprendizado profundo para RUL, presentes em outros artigos do conjunto (fichamentos 08 e 10), não são cobertas.
17. Duplicação de referências ([29]/[66] e [30]/[39]) indica revisão editorial incompleta, o que recomenda cautela ao citar numerações internas.

## 9. Transferibilidade para o problema-alvo

Problema-alvo: isolamento de estator de motor de indução MT (2,3–13,8 kV) sob (a) sobretensões de manobra de VCB (chopping, reignições múltiplas, frentes íngremes, dV/dt) com/sem snubber tiristorizado (trabalho A) e (b) estresse térmico de partidas de grandes motores sob contingência N-1 com load shedding (trabalho B).

Contexto do repositório (fato do repositório): `app/validation/validator_vcb.py` valida modelos ATP `VCB_*` com parâmetros `T_OPEN`, `I_CHOP` (faixa típica 1–15 A, aviso acima de 20 A), `RRDS_A`/`RRDS_B` (rigidez dielétrica para suportabilidade de TRT), `DIDT_CRIT`, `RCLOSED`/`ROPEN`, e exige controlador de snubber (`SNUB_*`) conectado às saídas `CB_STATE` (códigos VCB-030/031). `app/postprocessor/motor_starting.py` implementa afundamento de tensão e tempo de aceleração por IEEE 399 §10, com critérios V > 0,85 pu, t_start < 0,7 × t_locked_rotor_thermal e N_starts/hora (NEMA MG 1). `app/postprocessor/tcc_damage.py` implementa `MotorThermalCurve` com t(I) = K_motor/(I/FLA)², K_motor = locked_rotor_time_s × locked_rotor_factor².

### O que se transfere

1. **Arquitetura de prognóstico com canal de causas previstas (Fig. 4, p. 7)** — transfere-se integralmente. O artigo estabelece que correntes de mancal "cannot be monitored through the measurement of stator currents, they can only be estimated from operating conditions" (p. 9) e que "Because bearing currents can be predicted to some degree, they can be used to enhance the model and the prediction" (p. 6). Inferência minha: o análogo direto para o alvo (a) é a sobretensão de manobra no terminal do motor, que não é medida rotineiramente em planta, mas é calculável por simulação ATP a partir do estado de manobra (chopping, reignições, comprimento de cabo, presença/estado do snubber) — exatamente o que o repositório já parametriza. O "History of Causes" torna-se o registro cumulativo de eventos de manobra com amplitude, dV/dt e número de reignições por evento; para o alvo (b), o registro de partidas com tensão de partida, t_start e I²t acumulado sob N-1.
2. **Modelo de eventos abruptos que mudam a trajetória de degradação (p. 6, p. 10)** — "it has become possible to determine events that precipitously change the state of health and lead to new deterioration trajectories. Bearing currents cause such sudden events, and the presence of bearing currents can be utilized for their prediction" (p. 10). Inferência minha: cada surto de reignição múltipla é candidato a "evento de salto" do estado do isolamento (hipótese: iniciação de descargas parciais ou microfissura na isolação de espira), a ser tratado como transição não linear no modelo de estado, e não como envelhecimento contínuo. Isso sugere um modelo híbrido de dois regimes: envelhecimento térmico contínuo (Arrhenius/I²t, alvo b) e saltos por surto (alvo a).
3. **Separação de causas concorrentes com assinaturas semelhantes (p. 8–9)** — o requisito de "determine how similar features ... can be due to different causes ... and to develop more accurate methods to separate them" (p. 8) transfere-se ao problema de atribuir a degradação do isolamento ao estresse elétrico de manobra versus ao térmico de partidas; inferência minha: é o núcleo do fator TEAM (térmico, elétrico, ambiental, mecânico) e justifica manter os dois canais de causa separados no modelo.
4. **Métrica de valor do prognóstico, eq. (1), p. 8** — transfere-se diretamente como critério de validação orientado a custo (janela de manutenção, custo de parada antecipada versus falha), aplicável a qualquer ativo. É a ponte mais objetiva com a demanda de C-Level (Seção 11).
5. **Requisito de usar sensores existentes (p. 2, p. 8)** — "it is preferable to use sensors that are there for other purposes. Of these, the most common are current and voltage sensors at the stator terminals" (p. 2). Transfere-se: em MT, TCs e TPs de proteção e o próprio relé (o repositório tem `app/standards/relay_models.py` e integração IEC 61850-9-2 em `app/integration/iec61850_sv.py` — fato do repositório) já existem; a lógica de "custo de sensor justificável em grandes instalações" (p. 8) aplica-se a plataformas/refinarias (hipótese de contexto).
6. **Hibridização física + dados como direção (p. 9–10)** — transfere-se como tese metodológica: física fornece amplitude/probabilidade do estresse (surto simulado, temperatura estimada), dados fornecem a relação estresse → estado observável.
7. **Alerta sobre modelos puramente de dados (p. 10)** — "require narrow but extensive training" e produzem "occasionally unacceptable erroneous RULs": transfere-se como argumento contra aplicar diretamente LSTM/BiLSTM (fichamento 10) sem canal físico, dada a raridade de eventos de manobra e a impossibilidade de run-to-failure em motores MT de planta.
8. **Fig. 1, p. 2 (intervalo de confiança versus janela de manutenção)** — transfere-se como linguagem de decisão para o trabalho computacional: RUL com intervalo de confiança e limiar de acionamento de manutenção.
9. **Necessidade de base experimental multi-causa (p. 9)** — transfere-se como requisito de validação: ensaio acelerado combinando surtos repetitivos e ciclos térmicos em corpos de prova de isolação (hipótese: bobinas-modelo conforme IEC 60034-18-41/42, [INSERIR CITAÇÃO]).

### O que NÃO se transfere e por quê

1. **Indicadores** (vibração, som, tensão de mancal, corrente CM, graxa, frequências características de rolamento, G_mech) — todos são específicos da mecânica do rolamento; nenhum é precursor de degradação dielétrica. Precursores para o alvo (descargas parciais, tan δ, capacitância, resistência de isolamento, corrente de fuga, temperatura de ponto quente) não aparecem no artigo. [INSERIR CITAÇÃO para precursores de isolamento; ver fichamento 02 (Jensen 2018) no conjunto.]
2. **Física do dano** (pitting, frosting, fluting, fusão/vaporização, brinelling, healing) — não tem análogo no isolamento; a fenomenologia de erosão por descarga parcial e de degradação térmica do sistema mica/epóxi é distinta.
3. **Natureza do estresse elétrico** — dv/dt de PWM (repetitivo, kHz, amplitude do barramento CC) versus surto de manobra de VCB (raro, amplitude de múltiplos p.u., frentes íngremes, reignições em cascata). O artigo não fornece nenhum modelo de dano por evento elétrico transferível; apenas o conceito de "energia liberada" como discriminador de severidade (p. 3–4, [28]), que, por analogia (hipótese), sugere usar energia ou integral de dV/dt do surto como variável de severidade por evento.
4. **Bases de dados** (NASA PCoE, PRONOSTIA) — inúteis para o alvo.
5. **Escopo de tensão e de acionamento** — máquinas de baixa tensão inversorizadas; motores MT do alvo são, em geral, partida direta via VCB (hipótese de contexto).
6. **Estresse térmico de partida (alvo b)** — o artigo trata temperatura apenas como "cause and effect" (p. 3), variável secundária (p. 8) e fator de degradação (p. 9), sem qualquer modelo térmico ou de ciclos de partida. Não há nada a transferir além da recomendação de incluir "cycles" e "idle time" como covariáveis (p. 8–9).
7. **Métodos de validação** — o artigo não valida nada; só aponta a métrica de [69].

### Nota de transferibilidade: **2/5**

Justificativa (inferência minha): transferência forte no nível conceitual e arquitetural (Fig. 4, eventos abruptos, canal de causas previstas por simulação, eq. (1), hibridização) e nula no nível de indicador, física do dano, dados e algoritmo. O artigo é mais útil como fundamentação metodológica e como argumento de decisão do que como fonte técnica para o isolamento MT.

## 10. Citações literais relevantes

1. "Bearing failures are the primary cause of downtime in electrical drives (e.g., [1]). Even when the cause of the bearing degradation and the bearing condition are accurately known, possible actions of management are limited beyond localized maintenance." (p. 2)
2. "Predicting the time of failure, or RUL, is generally preferable to estimating the state of health in terms of maintenance scheduling, use of redundant equipment, and accuracy." (p. 2)
3. "In most cases, installation and use of separate dedicated sensors to determine the state of health of a bearing cannot be justified; it is preferable to use sensors that are there for other purposes. Of these, the most common are current and voltage sensors at the stator terminals." (p. 2)
4. "Unexpected abrupt changes in the state of the bearing often occur because of unpredicted events, e.g., spalls, contamination, grease breakdown, and bearing currents. These events change the bearing state and rate of degradation [62]. The randomness of these events makes very early prediction of the RUL nearly impossible. Because bearing currents can be predicted to some degree, they can be used to enhance the model and the prediction." (p. 6)
5. "Models that describe the fault development in a quantitative way over time and related to observations or measurable quantities have not been developed yet because of a lack of understanding of the underlying mechanisms." (p. 7)
6. "A false-positive prognosis will lead not only to early maintenance and increased cost due to loss of operation, but also to loss of confidence and, with this, a shutdown of the monitoring system and a step-by-step prognosis. On the other hand, late failure estimation or false-negative prognosis may lead to catastrophic failure or, at least, emergency maintenance. The preferred time for maintenance is during a maintenance window, which would necessitate confidence in this measurement as shown in Figure 1." (p. 8)
7. "Since bearing currents cannot be monitored through the measurement of stator currents, they can only be estimated from operating conditions (inverter status, speed, and temperature), and, from these, the effects on the bearing can be estimated in turn [18], [19], [29], [37], [66]." (p. 9)
8. "We expect the problem of the failure prognosis of bearings to require hybrid approaches: data based, enhanced by physical model understanding and interpretation, and, at the same time, combined features arriving from more than one source (stator current to detect transient eccentricities and general roughness related to vibration measurements)." (p. 10)

## 11. Ligações com RUL, PHM e C-Level

RUL e PHM (fato do artigo):
- Definição operacional de prognóstico e de RUL, com a decisão de manutenção dependendo "not only on RUL but also on the confidence in the prognosis prediction, expected service requirements, and redundancies" (p. 2).
- Pré-requisitos de um sistema PHM (p. 2): sistema de medição das manifestações da falta; método de redução das medições a um conjunto tratável; software de extração da condição e de sua evolução "over time or operations"; modelos "(physical, statistical, or both)" obtidos a priori; limiares "established ahead of time" para determinação do RUL.
- Menção à comunidade PHM: "a conference (Prognostics and Health Management) has resulted in a large number of relevant publications" (p. 2) e ao livro de Vachtsevanos et al. [5] (p. 2, 9).
- Ligação com o fichamento 09: a tese de que o prognóstico "promises to be more accurate and useful than diagnosis alone [4]" (p. 2) é a do artigo de Strangas et al. (2013).

Argumentos de custo/decisão/manutenção transcritos (fato do artigo):
- Fig. 1, p. 2: "(a) The maintenance scheduled based on condition. Errors may lead to failure before maintenance A or premature and costly shutdown B. (b) The maintenance based on prognosis. For short confidence intervals, maintenance can be performed close to the anticipated failure."
- Custo da mitigação (p. 2): "Although techniques are available to eliminate these problems, they not only add cost to the system but also may pose additional maintenance and reliability issues."
- Custo de medição (p. 8): "The cost of measuring variables that will lead to the extraction of features and eventually to diagnosis and prognosis is, of course, of paramount importance, too. In the case of large wind generators or sensitive applications, the cost of specialized sensors is more easily justified than for the bearings of a traction motor of a passenger vehicle."
- Falsos positivos/negativos e perda de confiança (p. 8): ver citação 6 da Seção 10.
- Métrica de valor econômico do prognóstico, eq. (1), p. 8: V = (E_ref − E_prog)/(E_ref − E_perf), com E_prog "constant and minimal when the failure occurs during a maintenance window and has different and high values when it occurs before or after this window".
- Critério de adoção (p. 9): "The application of a failure prognosis technique should be based on the expectation that the probability of the failure of a system or unnecessary maintenance and the cost associated with them will be lower than the case in which prognosis is not used. This raises the issue of confidence in the prognosis."
- Implementabilidade (p. 8): "A method to predict bearing faults in high-performance and/or high-reliability drives has to be easily implementable, even in cases in which limited information on the bearing and operational characteristics are available, without burdening the system with inconvenient sensors or other hardware."

Inferência minha para o trabalho computacional e a narrativa C-Level:
- O par (Fig. 1, eq. (1)) fornece a forma mais compacta de explicar a um executivo por que RUL com intervalo de confiança vale mais que um alarme de condição: a manutenção migra para a janela planejada e o valor V mede o ganho relativo ao cronograma vigente.
- A observação de que a mitigação "add[s] cost ... and may pose additional maintenance and reliability issues" (p. 2) é o análogo direto do snubber tiristorizado (trabalho A) e do load shedding (trabalho B): ambos são mitigação com custo, e o prognóstico é o que permite decidir seletivamente quando acioná-los — o que conecta os três trabalhos do autor sob a rubrica "mitigação seletiva orientada por prognóstico", tal como o bloco "Decision on Mitigation/Maintenance" da Fig. 4 (p. 7).
- A advertência sobre perda de confiança por falsos positivos (p. 8) deve orientar a escolha de limiares do módulo computacional e a apresentação de resultados (probabilidade e intervalo, não ponto único).
