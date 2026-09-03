# Fichamento 09 — Strangas, Aviyente, Neely e Zaidi (2013): efeito do prognóstico de falha e da mitigação sobre a confiabilidade de acionamentos PMAC

Convenções deste fichamento: "fato do artigo" = conteúdo verificável no texto, com página indicada segundo os marcadores "===== PAGE N =====" do arquivo extraído (p. 1 corresponde à página impressa 3519; p. 10, à página impressa 3528); "inferência minha" = conclusão derivada por mim a partir do texto ou do repositório; "hipótese" = proposição ainda não verificada. As Tabelas I–IV do artigo não tiveram seus valores numéricos extraídos no arquivo de texto (apenas os títulos); onde necessário, indico [INSERIR VALORES DA TABELA N]. As Figs. 1–5 tampouco estão disponíveis, apenas suas legendas. Os únicos valores numéricos das tabelas recuperáveis são os que o corpo do texto repete (Seção 7).

---

## 1. Referência completa

STRANGAS, Elias G.; AVIYENTE, Selin; NEELY, John D.; ZAIDI, Syed Sajjad H. The Effect of Failure Prognosis and Mitigation on the Reliability of Permanent-Magnet AC Motor Drives. **IEEE Transactions on Industrial Electronics**, v. 60, n. 8, p. 3519–3528, ago. 2013. DOI: 10.1109/TIE.2012.2227913.

Dados complementares (fato do artigo, p. 1):
- Manuscrito recebido em 22 abr. 2012; revisado em 11 ago. 2012 e 4 out. 2012; aceito em 17 out. 2012; publicado em 16 nov. 2012; versão corrente de 11 abr. 2013.
- Financiamento parcial: National Science Foundation (NSF), Grant Opportunities for Academic Liaison with Industry (GOALI), Grant 1102316.
- Afiliações: E. G. Strangas e S. Aviyente — Department of Electrical and Computer Engineering, Michigan State University, East Lansing, MI, EUA; J. D. Neely — Eaton Aerospace Actuation Systems, Grand Rapids, MI, EUA; S. S. H. Zaidi — Department of Electrical and Power Engineering, Pakistan Navy Engineering College, Karachi, Paquistão.
- Palavras-chave dos autores (Index Terms): fault detection, fault diagnosis, fault tolerance, hidden Markov models, linear discriminant analysis, permanent-magnet machines, prognostics and health management (PHM).
- Trabalhos anteriores dos mesmos autores sobre os quais este se apoia (referências do artigo, p. 9–10): [3] ZAIDI, S.; AVIYENTE, S.; SALMAN, M.; SHIN, K.; STRANGAS, E. Prognosis of gear failures in dc starter motors using hidden Markov models. IEEE Trans. Ind. Electron., v. 58, n. 5, p. 1695–1706, maio 2010 (ano transcrito conforme impresso; inferência minha: o v. 58 da IEEE TIE corresponde a 2011); [28] STRANGAS, E.; AVIYENTE, S.; NEELY, J.; ZAIDI, S. Improving the reliability of electrical drives through failure prognosis. Proc. IEEE Int. SDEMPED, set. 2011, p. 172–178; [36] STRANGAS, E.; AVIYENTE, S.; ZAIDI, S. Time frequency analysis for efficient fault diagnosis and failure prognosis for interior permanent-magnet ac motors. IEEE Trans. Ind. Electron., v. 55, n. 12, p. 4191–4199, dez. 2008; [48] ZAIDI, S.; ZANARDELLI, W.; AVIYENTE, S.; STRANGAS, E. Prognosis of electrical faults in permanent magnet ac machines using the hidden Markov model. Proc. 36th IEEE IECON, nov. 2010, p. 2634–2640.

## 2. Objetivo do artigo

Fato do artigo (p. 1, resumo): apresentar "a new approach to the mitigation of permanent-magnet ac motors that uses a failure prognosis method to predict failures and the remaining useful life and uses the output of the prognosis algorithm to decide when to modify the system and mitigate the fault", acompanhada de "a methodology to calculate the mean time between failures with and without mitigation". A abordagem é ilustrada com "a simple example of how the prognosis of failure due to a developing intermittent open circuit in one of the phases increases the drive reliability".

Fato do artigo (p. 2): a lacuna declarada é que "it has been assumed, but not substantiated, that prognosis and mitigation based on it may enhance reliability; still, the contributions of fault prognosis on the reliability have not been discussed. It is not clear yet how to determine the effect of mitigation and how false positives and negatives can affect the overall reliability." O artigo se propõe a "go beyond scheduling of maintenance and analyze the effect of the failure prognosis and subsequent reconfiguration on the reliability of an electrical drive" (p. 2).

Fato do artigo (p. 2): estrutura da contribuição — (i) revisão de um método de prognóstico previamente introduzido em [3] (Choi–Williams + LDC + HMM) demonstrado em uma máquina PMAC com circuito aberto em desenvolvimento; (ii) desenvolvimento de "a methodology to determine the changes in reliability with the use of prognosis and of imperfect diagnosis of faults that develop slowly".

Inferência minha: a contribuição original está na Seção III (caminhos para a falha com e sem mitigação, eqs. (7)–(11)) e na Seção VI (ajuste de limiares de decisão). O algoritmo de diagnóstico/prognóstico é reaproveitado de trabalhos anteriores do grupo, e o exemplo numérico é essencialmente ilustrativo, com sequência de observações sintética.

## 3. Sistema/componente e mecanismo(s) de degradação tratados

Sistema (fato do artigo):
- Acionamento PMAC completo: "a controller, power electronics, an electric motor, and a decision system" (p. 2). Falhas mais comuns em máquinas PMAC listadas: "bearing faults, stator opens and shorts, and rotor demagnetization, as well as failures in the power electronic switches, their drivers and sensors, and, most notably, the rotor position sensor" (p. 4).
- Tipos de falha considerados como primários ou secundários (p. 5): 1) mancais (fragilidade inerente, condições de operação ou correntes de mancal); 2) circuito aberto em uma fase por "a slowly developing fault (an intermittent fault of a contact with increased resistance) or a precipitous open in a winding connection of the switch"; 3) curto entre espiras ou para a terra, "intermittent and through a resistance, or ... the equivalent of a bolted fault"; 4) desmagnetização por "high temperature and high current in the negative d-axis"; 5) excentricidade estática ou dinâmica.

Falha primária analisada (fato do artigo, p. 6): circuito aberto "caused by a bad contact of a connector, an imperfect welding, or an electronic switch"; "In practice, this fault often starts as intermittent, and its severity can be described by its duration and the value of the resistance". A física do contato é remetida a [45] (Abbott, 1989) e [46] (Mroczkowski, 1998), e a prognose de eletrônica a [47] (Lall et al., 2011).

Mecanismos de degradação secundários induzidos pela mitigação (fato do artigo, p. 1 e p. 7): a reconfiguração para operação em duas fases eleva a corrente nos semicondutores e nos enrolamentos, "producing higher localized and average temperatures. These stresses decrease the life of the insulation and may demagnetize the magnets" (p. 1). Faltas subsequentes possíveis, citando [49] (p. 7): "1) increased temperature in the windings and/or in the inverter switches, leading to insulation and connector faults; 2) demagnetization, reversible or irreversible; 3) deterioration of the bearings."

Modelos de vida por componente (fato do artigo, p. 4 e p. 6): semicondutores — vida em função da temperatura de junção (Arrhenius, eq. (12)); isolamento do enrolamento — vida em função da temperatura, com ênfase no ponto quente: "It is important to estimate the hot spot, rather than the average winding temperature, and to include the effects of the operating mode while doing so" (p. 4); ímãs — "reversible change" e "irreversible change" térmica, com espiral de degradação: "decreased magnet performance leads to further increases in the stator currents and temperature and, eventually, to failure" (p. 6).

Inferência minha: o isolamento de estator aparece no artigo apenas como falta secundária (envelhecimento térmico acelerado pela operação reconfigurada) e como componente cuja taxa de falha entra na soma de (6); não é objeto de medição nem de prognóstico direto. O mecanismo primário estudado (contato intermitente) é de natureza elétrica-mecânica de conector, distinto do envelhecimento dielétrico.

## 4. Indicadores/precursores de degradação usados

| Indicador | Grandeza / unidade | Como é obtido | Amostragem | Página |
|---|---|---|---|---|
| Corrente de eixo direto do estator, i_d | A (unidade é inferência minha; o artigo só nomeia "stator d-axis current") | Única variável medida ("we use a single measurement to detect a fault and determine its type and severity", p. 2); analisa-se "the effect of the fault on the stator d-axis current" no transitório de "inception of clearing of the fault" | Não declarada | p. 2, 6 |
| Coeficientes tempo–frequência (distribuição de Choi–Williams) | Adimensionais / energia tempo–frequência (inferência minha) | "time–frequency analysis of portions of the signal at regular time intervals" (p. 2); Choi–Williams escolhida "due to its high resolution and shift invariance" (p. 3) | "regular time intervals" (p. 2); não quantificado | p. 2, 3 |
| Projeções D_c(x) sobre os hiperplanos LDC | Escores discriminantes adimensionais | Eq. (1); médias e variâncias das projeções de cada classe sobre cada plano (Tabelas I e II, C × C matrizes) | — | p. 3, 6–7 |
| Estado de severidade da falta S_1 … S_6 | Categórico (1 = saudável … 6 = falha) | Classe de maior discriminante; probabilidades condicionais b_j(O) (matriz B, Tabela III) | — | p. 3, 6–7 |
| Probabilidade do próximo estado ser falha, P[q_{t+1} = S_6] | Adimensional [0,1] | Eq. (4), recursão forward do HMM | Uma avaliação por t_sample; exemplo: 1 h | p. 3, 7–8 |
| Parâmetros de severidade do defeito imposto | Duração da intermitência (s) e resistência paralela do contato (Ω) — unidades são inferência minha | Impostos em bancada por "an externally controlled contact of varying parallel resistance" | — | p. 6 |
| Temperatura de junção T_J e temperatura de ponto quente do enrolamento | K | Não medidas no exemplo; estimadas de T_A, perdas e resistência térmica (semicondutor) ou de "current, voltage, speed, and power" via modelos numéricos ou de parâmetros concentrados (enrolamento) | — | p. 4, 6 |

Fato do artigo (p. 2): os autores enfatizam que "In electrical drives, it is often necessary to minimize the number of inputs used for predicting a fault as well as use sensors with limited bandwidth and resolution", e que a determinação é sujeita a variáveis "either unknown (e.g., external electromagnetic noise or vibrations, variable supply voltage, and variations in manufacturing) or difficult to account for (e.g., load characteristics and speed)".

Inferência minha: não há precursor de degradação de isolamento (capacitância, tan δ, descargas parciais, resistência de isolamento) no artigo; o único "precursor" físico é a assinatura transitória do contato defeituoso em i_d.

## 5. Modelo/algoritmo

Classe: híbrida (inferência minha). O diagnóstico é orientado a dados (LDC treinado com ensaios), a densidade de observação B do HMM é empírica, mas a matriz de transição A "can be estimated from empirical data or from a physics-based fault evolution analysis" (p. 3) e, no exemplo, "was generally based on the expected degradation of contacts, using a heuristic approach described in [48]" (p. 7); os modelos de vida dos componentes (12)–(14) são físico-empíricos (Arrhenius). Rótulo alternativo cabível: "framework", pois a contribuição central é um arcabouço de análise de confiabilidade com mitigação, e não um novo estimador.

### 5.1 Pipeline geral (fato do artigo, p. 2–3)

1) Coleta de dados "(that may include currents, vibration, and acoustic noise)" e extração de características (tempo–frequência); 2) categorização da falta com treinamento a priori (LDC, vizinho mais próximo, redes neurais/fuzzy, algoritmos genéticos); 3) prognóstico: "estimation of the RUL, estimation of the most probable next state, or estimation of the probability of failure in the next time period", por filtro de Kalman estendido, HMM ou filtro de partículas; "The prognosis of failure is generally based on the statistics of the diagnosis and on a physics-based model of fault progression" (p. 3).

### 5.2 Diagnóstico: classificador discriminante linear (LDC)

Eq. (1), p. 3: D_c(x) = x_1 α_{1c} + x_2 α_{2c} + ··· + α_{k+1,c}, c = 1, 2, …, C.

Os coeficientes α_{ic} são obtidos do treinamento "so that the discriminant function D_c(x) computed for each training coefficient vector is maximum for the corresponding category of fault severity"; definem "the hyperplane that describes each fault class that will be referred to as the LDC plane" (p. 3). Classificação: a amostra é atribuída "to the class corresponding to the largest value" (p. 3). Além da classificação, calculam-se "the average and the variances of the discriminants resulting from this observation for all categories", de modo que "A fault therefore is categorized with a specific probability, and significant probability exists, and can be determined, that the fault is categorized as belonging to any other state" (p. 3).

### 5.3 Prognóstico: modelo oculto de Markov (HMM)

Parâmetros iniciais (fato do artigo, p. 3): distribuição inicial π ("can be determined from the manufacturer's data. In our work, we assume reasonable state probabilities to illustrate the method"); matriz de transição A com elemento (i, j) = p(S_{k+1} = j | S_k = i); densidade de observação B.

Eq. (2), p. 3: b_j(O_k) = p(O_k | S_k = j).

Eq. (3), p. 3 (transcrita conforme extraída; a extração de texto perdeu o sinal e o fator do expoente, de modo que a forma exata não é recuperável do arquivo — presumivelmente gaussiana padrão):
P(O | S_i) = [1 / (√(2π) σ_{O|S_i})] · exp[ ((O − μ_{O|S_i}) / σ_{O|S_i})² ],
"where the statistics, μ_{O|S_i} and σ_{O|S_i}, are obtained from the experimental data". Cada amostra de treinamento x^j é projetada em todos os C planos, gerando "a set of C × C means and C × C variance matrices" (p. 3).

Eq. (4), p. 3 (limite superior do somatório transcrito como impresso, "j"; inferência minha: o limite deveria ser C, o número de estados):
P[q_{t+1} = S_j | λ] = Σ_{i=1}^{j} P[q_t = S_i | λ] a_{ij} = Σ_{i=1}^{j} δ_t(i) a_{ij},
"where λ is the set of model parameters" e δ_t(i) é "the normalized forward probability at time t for each state S_i". Estimação via "Baum–Welch algorithm" (p. 3). "The state which corresponds to the highest probability, p_i, is deemed to be the next state, but it must be noted that none of these probabilities is zero" (p. 3).

Estrutura no exemplo (fato do artigo, p. 6–7): C = 6 classes de severidade "ranging from healthy to failure"; B gaussiana a partir das Tabelas I–II; A heurística de [48]; π assumida.

### 5.4 Confiabilidade sem e com mitigação (contribuição central)

Hipóteses (fato do artigo, p. 4): "we assume that a single fault will lead to failure"; "the only dependence of a fault on another is through the model that we develop and use, and the probabilities of faults are otherwise independent"; "the sum of the failure rates of all components represents the combined failure rate of the motor and controller"; confiabilidade inicial "based on the manufacturers' values at the rated power and temperature".

Eq. (5), p. 4: λ = 1 / MTBF.

Eq. (6), p. 4: λ_system = Σ_{i=1}^{n} λ_i.

Caminhos para a falha (Fig. 2; fato do artigo, p. 5), para uma falta primária "fault 1" de taxa λ_1:

- Caminho 1 — falta não detectada nem mitigada (probabilidade p_1), levando à falha. Eq. (7), p. 5: MTBF_1 = 1 / (p_1 λ_1).
- Caminho 2 — falta detectada a tempo de evitar a falha direta, "but not soon enough to avoid a secondary fault 2 (probability p_12)", com taxa λ_2. Eq. (8), p. 5: MTBF_2 = 1/(p_12 λ_1) + 1/λ_2.
- Caminho 3 — falta detectada cedo por prognóstico (probabilidade p_13), levando a "a reduced or modified system, with failure rate λ_3, expected to be significantly lower than λ_2". Eq. (9), p. 5: MTBF_3 = 1/(p_13 λ_1) + 1/λ_3.
- Desigualdade impressa (p. 5): MTBF_3 < MTBF_2 < MTBF_1, acompanhada do texto "a fault detected late will result in higher failure rate than one detected and mitigated on time and that a healthy unmodified drive would have the lowest failure rate". Inferência minha: há aparente inconsistência entre a desigualdade impressa e o texto (se λ_3 < λ_2 e p_13 ≈ p_12, decorre MTBF_3 > MTBF_2); pode tratar-se de erro tipográfico ou de a desigualdade referir-se a outra ordenação; não é possível decidir pelo texto.
- Caminho 4 — falso positivo: "fault 1 may be diagnosed, although no such fault may be present, with probability p_10", que "depends on the external conditions (e.g., noise, sensors, etc.) and the threshold that leads to a determination of a fault". A "taxa de falha" associada "is not a characteristic of the drive or of the fault but depends on the diagnosis method, the instrumentation, and the sampling interval t_sample". MTBF da má diagnose: 1/λ_10 = t_sample / p_10. Eq. (10), p. 5: MTBF_4 = 1/λ_10 + 1/λ_3.

Eq. (11), p. 5: λ_system = Σ_{i=1}^{4} 1 / MTBF_i.

### 5.5 Taxas de falha de componentes

Eq. (12), p. 6 (semicondutores): L(T_J) = L_0 · exp(−B · Δ), "where L is the quantifiable life measurement as a function of T_J, the junction temperature in degrees kelvin, L_0 is a quantitative life measurement in hours, B = E_A/K, E_A is the activation energy in electronvolts, K is Boltzmann's constant, and Δ = 1/T_A − 1/T_J".

Eq. (13), p. 6 (isolamento, denominada pelos autores "The Arrhenius model for insulation"): L_insulation = L_o · exp(−B · T/C), "where B and C are constants".

Eq. (14), p. 6: λ_insulation = 1 / L_insulation.

Inferência minha: a forma (13), com T no numerador do expoente, não corresponde à lei de Arrhenius clássica (exp(E_A/(kT))), nem à sua linearização usual; sem definição de C nem de unidades de T, a expressão é dimensionalmente ambígua. Trata-se de uma formulação simplificada, não utilizável diretamente sem reparametrização (ver Seção 8).

### 5.6 Taxa de falso positivo

Eq. (15), p. 7: λ(t) = lim_{dt→0} p(fail in (t, t + dt) | no failure up to time t) / dt.

Eq. (16), p. 7: λ_10 = p(false positive in the interval) / t_sample, assumindo taxa constante no intervalo e "during this interval, only one such calculation is made". "It is clear that this false positive determination is affected primarily by the prognosis process, i.e., the method of determination of the next state, the threshold of a decision of failure, and the sampling interval" (p. 7).

Definição de falso positivo no contexto de prognóstico (p. 7): "the probability of failure, p_10, in the next step, as calculated through the prediction method, exceeds a threshold, and this will initiate a remediation. False positive then means that the state of the drive is below that corresponding to the threshold."

### 5.7 Mitigação empregada e limiares

Mitigação (fato do artigo, p. 7): "reconfiguration of the controller to operate the motor with two phases through the use of a center-tapped dc bus. To maintain power to the motor, the current through the power electronics and windings will have to be increased, and the control algorithm has to be modified", com "increased power losses, torque pulsations, and flux fluctuations".

Limiares (fato do artigo, p. 8): decisão por prognóstico "based on whether the probability that the next state is a failure state exceeds a threshold or the RUL is below a threshold"; no exemplo, limiar 0,4 sobre P[q_{t+1} = S_6]; para diagnóstico direto, limiar 0,28 para detecção do estado 5.

Hiperparâmetros declarados: C = 6 estados; t_sample = 1 h no exemplo (p. 7–8); nenhum hiperparâmetro do Choi–Williams (parâmetro σ do núcleo), do LDC ou do Baum–Welch (iterações, critério de parada) é informado.

## 6. Dados e experimento

Fato do artigo:
- Bancada: motor PMAC não especificado ("the particular motor used in this example", p. 6); falta imposta por "an externally controlled contact of varying parallel resistance" (p. 6). Potência, tensão, número de polos, inversor, taxa de amostragem e número de ensaios não são informados.
- Treinamento: "tests were conducted for different fault severities, data were collected, and Choi–Williams features were extracted" (p. 6); "extensive training of the algorithm has led to statistics corresponding to each severity, the mean, and the standard deviation of the projection of the time–frequency features onto the LDC planes for the six classes" (p. 6). Número de amostras por classe não declarado.
- Resultados do treinamento: Tabela I (médias das projeções sobre cada plano LDC), Tabela II (variâncias), Tabela III (probabilidades de estado, matriz B) [INSERIR VALORES DAS TABELAS I–III].
- Taxas de falha: Tabela IV, "Rates of failure in hr⁻¹", com "typical values used for this example and were calculated based on the typical temperature of the windings, etc., using the methodology outlined in [10]" (p. 7) [INSERIR VALORES DA TABELA IV].
- Sequência de validação do prognóstico: "an artificial series of actual observations was constructed to emulate the progression of a fault from stage 1 (healthy) to stage 6 (failure). These were based on the statistics of the projections on the LDC planes" (p. 8). Sequência: [1 1 2 2 2 2 2 2 2 2 2 2 2 3 3 3 3 3 3 3 3 3 3 3 4 4 5 5 6 6] (30 observações, contagem minha), "repeated every hour, starting from a healthy motor and drive" (p. 8).

Inferência minha: não há ensaio acelerado de degradação nem dado run-to-failure. A matriz B é a única quantidade estimada de dados experimentais; A, π, Tabela IV e a trajetória de observações são assumidas ou construídas. O experimento demonstra o algoritmo, não valida sua capacidade preditiva.

## 7. Métricas e resultados numéricos

| Resultado | Valor | Condição | Página |
|---|---|---|---|
| Probabilidade de um estado saudável (S_1) ser classificado como falha ou quase falha (C_5 ou C_6) | 0,3052 | Matriz B (Tabela III) | p. 7 |
| Probabilidade de severidade 5 ser classificada como saudável (C_1) | 0,1617 | idem | p. 7 |
| Probabilidade de severidade 6 (falha) ser classificada como saudável (C_1) | 0,1304 | idem | p. 7 |
| Probabilidade de severidade 6 ser classificada como severidade 2–4 | 0,4149 | idem | p. 7 |
| Taxa total de falha do sistema com decisão por diagnóstico direto, eq. (11) | λ_system = 1,68·10⁻⁴ (h⁻¹, unidade da Tabela IV) | "for sampling every hour" | p. 8 |
| Limiar de prognóstico que elimina FP e FN na sequência sintética | 0,4 sobre P[próximo estado = S_6] | 30 observações horárias | p. 8 |
| Limiar de diagnóstico para o estado 5 | 0,28 → "at least two observations, 11 and 14, will result in incorrect detection" | idem | p. 8 |
| Probabilidade de falso positivo por diagnóstico | p_10 = 0,719; λ_10 = 0,719 h⁻¹ | t_sample = 1 h | p. 8 |
| MTBF do caminho 4 (falso positivo) por diagnóstico | MTBF_4 = 1/λ_10 + 1/λ_3 = 2,326·10⁴ (h, inferência minha quanto à unidade) | idem | p. 8 |
| Probabilidade de falta não detectada por diagnóstico | p_1 = 1 − 0,1979 = 0,8021 | idem | p. 8 |
| MTBF do caminho 1 por diagnóstico | MTBF_1 = 1/(p_1 λ_1) = 3,895·10⁴ (h) | idem | p. 9 |
| MTBF_1 e MTBF_4 com prognóstico | "both MTBF_1 and MTBF_4 are infinite since no such path is probable" | sequência sintética, limiar 0,4 | p. 9 |

Observações sobre a Fig. 5 (fato do artigo, p. 8): "1) The probabilities of failure while in states 1 and 2 are too high if estimated using either diagnosis and prognosis; if mitigation is based on these numbers alone, it will result in an unacceptable failure rate. 2) Fault prognosis gives drastically higher probability for accurate determination of a fault near or at the failure stage. 3) This large difference between the probabilities of failure allows the decision threshold to be much higher when fault prognosis is used, thus effectively eliminating false negatives."

Retrocálculo (inferência minha, a partir de MTBF_4 = 2,326·10⁴ h com 1/λ_10 = 1,391 h): 1/λ_3 ≈ 2,326·10⁴ h ⇒ λ_3 ≈ 4,3·10⁻⁵ h⁻¹; a partir de MTBF_1 = 3,895·10⁴ h e p_1 = 0,8021: λ_1 ≈ 3,2·10⁻⁵ h⁻¹. Esses seriam dois dos três valores da Tabela IV; λ_2 não é recuperável. As contribuições dos caminhos 1 e 4 somam ≈ 6,9·10⁻⁵ h⁻¹, de modo que, se λ_system = 1,68·10⁻⁴ h⁻¹ for a soma dos quatro caminhos, os caminhos 2 e 3 responderiam por ≈ 9,9·10⁻⁵ h⁻¹ (hipótese, dependente da coerência interna do exemplo).

Nota (inferência minha): a frase "The high probabilities of false positives and false negatives give a significantly low total failure rate from (11), λ_system = 1.68·10⁻⁴" (p. 8) parece conter um lapso ("low" onde o sentido lógico é "high"), pois altas probabilidades de erro só podem piorar a confiabilidade. Transcrevo como impresso.

Métricas ausentes: não há acurácia de classificação por classe, matriz de confusão em amostras de teste, erro de RUL, intervalos de confiança nem análise de sensibilidade a t_sample ou aos limiares.

## 8. Limitações

Declaradas pelos autores:
- (declarada, p. 3) π assumida: "we assume reasonable state probabilities to illustrate the method".
- (declarada, p. 6) A simplificada: "Deriving a detailed model for the evolution of open circuit faults is highly dependent on the operating conditions of the drive. In this paper, a simple model is used to develop matrix A, in order to demonstrate the methodology proposed."
- (declarada, p. 7) Taxas da Tabela IV são "typical values used for this example".
- (declarada, p. 7) Incerteza alta do classificador: "the probability of inaccurate categorization can be very high"; (p. 8) "the statistics resulting from the classification method and the resultant fault diagnosis give high levels of uncertainty".
- (declarada, p. 8) Sequência de observações artificial; "More accurate estimations of the probabilities of false negatives and positives can be made by extensive numerical examples."
- (declarada, p. 4) Hipóteses de falha única, independência entre faltas e soma de taxas (sistema em série).
- (declarada, p. 6) "Determining the temperature of the windings can be complex and inaccurate".
- (declarada, p. 9) Dependência de modelo físico de progressão: "The proposed method relies on the failure prognosis methodology, which, in turn, requires a method to model the fault progression. With few exceptions, this is based on a physical model of the fault, and this is what is required in practical cases."
- (declarada, p. 9) Cobertura de uma única falta primária; "It can be expanded to cover all primary faults".

Identificadas por mim:
- (minha inferência) O artigo promete estimativa de RUL, mas o exemplo entrega apenas a probabilidade de o próximo estado ser falha; nenhum RUL em unidades de tempo é calculado, e a ligação entre a saída do HMM e as taxas λ da Tabela IV não é formalizada (p_1, p_10 são lidos da matriz B ou da sequência sintética, não derivados de uma distribuição de RUL).
- (minha inferência) Modelo de taxa de falha constante (exponencial) e aditiva. Para mecanismos de desgaste como o envelhecimento de isolamento, a taxa de risco é crescente; a álgebra (5)–(11) ignora a memória do dano acumulado e a idade do componente, o que tende a subestimar o efeito de mitigações tardias.
- (minha inferência) A eq. (13) não é a lei de Arrhenius e carece de definição de C e das unidades de T, exigindo reparametrização antes de uso. A eq. (12), ao contrário, é a forma de aceleração de Arrhenius usual (L_0 = vida à temperatura de referência T_A; L decresce com T_J, pois Δ cresce com T_J), mas o artigo não fornece E_A nem L_0 para o exemplo.
- (minha inferência) Inconsistências editoriais: desigualdade MTBF_3 < MTBF_2 < MTBF_1 em conflito com o texto (p. 5); limite superior "j" no somatório de (4); frase "significantly low total failure rate" (p. 8).
- (minha inferência) O resultado "MTBF_1 e MTBF_4 infinitos com prognóstico" é artefato da sequência sintética monotônica e do limiar escolhido a posteriori sobre a mesma sequência (ajuste in-sample); não há validação em sequências independentes, ruidosas ou não monotônicas.
- (minha inferência) O modelo de falso positivo λ_10 = p_10/t_sample assume que cada avaliação é independente da anterior; com HMM, as decisões são correlacionadas no tempo, e a taxa efetiva de falsos positivos não escala linearmente com a frequência de amostragem.
- (minha inferência) Não há modelo de custo: falsos positivos são tratados apenas como redução de MTBF (via λ_3), sem custo de indisponibilidade, e falsos negativos, sem custo de falha catastrófica; a otimização de limiar é, portanto, unidimensional.
- (minha inferência) A única variável observada, i_d, pressupõe controle vetorial com transformação dq disponível no controlador; o método não é aplicável tal qual a motores alimentados diretamente da rede.
- (minha inferência) O motor, o inversor e a instrumentação não são caracterizados, impedindo reprodução.

## 9. Transferibilidade para o problema-alvo

Problema-alvo: isolamento de estator de motor de indução de MT (2,3–13,8 kV) submetido a (a) sobretensões de manobra de disjuntor a vácuo (VCB) — corte de corrente (chopping), reignições múltiplas, frentes íngremes, dV/dt — com ou sem snubber tiristorizado ativo (trabalho A do autor) e (b) estresse térmico de partidas de grandes motores sob contingência N-1 com load shedding seletivo (trabalho B do autor).

### 9.1 O que se transfere

- Arcabouço de confiabilidade com mitigação imperfeita (eqs. (5)–(11), Fig. 2) — transfere-se integralmente como estrutura de raciocínio (inferência minha). Mapeamento proposto (hipótese): "fault 1" = degradação incipiente do isolamento (p. ex., surgimento de descargas parciais em espiras de entrada após surtos de VCB); "fault 2" (detecção tardia) = curto entre espiras evoluindo para falta à terra; caminho 3 = mitigação seletiva a tempo (inserção do snubber tiristorizado ou alteração de sequência de manobra), com λ_3 incluindo a taxa de falha própria do snubber; caminho 4 = falso positivo = atuação desnecessária do snubber (custo baixo em confiabilidade, mas não nulo: o dispositivo ativo tem λ própria conforme (12) e entra na soma (6)). Para o problema (b), "mitigação" = load shedding seletivo que reduz a duração e a temperatura da partida; falso positivo = corte de carga desnecessário (custo de produção, não de confiabilidade — o que o artigo não modela).
- Conceito de "taxa de falha" de falso positivo dependente do algoritmo, da instrumentação e de t_sample (eqs. (15)–(16), p. 5 e 7) — transfere-se como métrica de projeto para o esquema de decisão seletiva do trabalho A: a seletividade da mitigação é, no vocabulário do artigo, a escolha do limiar que equilibra p_10 e p_1 (inferência minha).
- Decisão baseada em sequência de estados (HMM) em vez de observação isolada (p. 2, p. 8) — transfere-se como arquitetura: extração de características → classificador com estatísticas de projeção → HMM → limiar sobre P[próximo estado = falha]. Hipótese para o problema-alvo: as observações O_k poderiam ser vetores por manobra (sobretensão de pico, dV/dt máximo, número de reignições, energia do transitório) gerados pela plataforma do repositório, que já implementa o MODEL ATP `vcb_reignition` (parâmetros RRDS de recuperação dielétrica, corrente de corte com valor padrão de 5 A e σ = 1 A, e acoplamento de um controlador de snubber às saídas CB_STATE); os estados S_1…S_C seriam classes de severidade do isolamento (p. ex., por magnitude de DP ou por queda de capacitância).
- Modelos de vida térmica por componente e ênfase no ponto quente (p. 4; eqs. (12)–(14)) — transferem-se em espírito para (b): cada partida sob N-1 impõe elevação de temperatura do enrolamento que pode ser convertida em consumo de vida por Arrhenius; a recomendação de estimar "the hot spot, rather than the average winding temperature, and to include the effects of the operating mode" (p. 4) é diretamente aplicável ao dimensionamento de partidas consecutivas e à decisão de load shedding. É necessário, porém, substituir (13) por uma lei de Arrhenius corretamente parametrizada (p. ex., IEEE 1 ou IEC 60034-18) [INSERIR CITAÇÃO].
- Argumento de que a mitigação altera o modo de falha e a taxa de falha do sistema modificado (p. 1, p. 4) — transfere-se: um motor cuja partida é realizada sob tensão reduzida pela contingência (sem shedding) opera em "sistema modificado" com λ_2 maior; com shedding, em λ_3 menor. A formalização (8)–(9) fornece o vínculo entre a decisão operacional e o MTBF.

### 9.2 O que não se transfere

- Indicador (i_d, Choi–Williams) e classificador treinado: específicos de acionamento com controle vetorial e de falta de contato; motores de MT partidos diretamente da rede por VCB não dispõem de i_d nem apresentam a assinatura transitória em questão (inferência minha).
- Mecanismo de degradação e matriz A: a heurística de degradação de contato [48] não descreve envelhecimento dielétrico; para surtos de VCB, a degradação é acionada por eventos discretos (cada manobra é um choque de dV/dt sobre o isolamento entre espiras), e não por evolução lenta amostrada a t_sample fixo. A matriz A precisaria ser reconstruída como modelo de dano acumulado por manobra (hipótese: Miner ou lei de potência inversa em tensão, combinada com Arrhenius para (b)) [INSERIR CITAÇÃO].
- Escalas temporais: reignições ocorrem em microssegundos e o dano se acumula ao longo de anos; o artigo trabalha em escala única (horas). A estrutura HMM comporta amostragem por evento de manobra, mas isso não é discutido no artigo.
- Taxa de falha constante e aditiva: inadequada ao desgaste do isolamento (risco crescente). Para o problema-alvo, é preferível Weibull ou modelo de dano acumulado com limiar (inferência minha).
- Mitigação por reconfiguração de fases com barramento CC com derivação central: sem análogo em motores de MT alimentados pela rede.
- Resultados numéricos: nenhum valor (Tabela III, Tabela IV, MTBF) é reutilizável, pois pertencem a um motor PMAC não caracterizado e a uma sequência sintética.
- Validação: o artigo não fornece um método de validação transferível (não há dados run-to-failure, validação cruzada nem métricas de RUL).

### 9.3 Nota

Nota atribuída: 3/5. Justificativa (inferência minha): alta transferibilidade conceitual e arquitetural — o artigo é, entre os fichados, o que mais diretamente formaliza a pergunta "quanto a mitigação seletiva, decidida por prognóstico imperfeito, melhora o MTBF?", que é o núcleo de valor dos trabalhos A e B; baixa transferibilidade de indicador, física de degradação, dados e resultados. A nota não é maior porque o artigo não entrega RUL em tempo, não valida em dados reais e apresenta imprecisões nos modelos de vida que exigem reconstrução.

## 10. Citações literais relevantes

1. (p. 1) "A drive, then, once it is modified to alleviate the effects of a fault, has decreased life expectancy."
2. (p. 2) "Since the decision to mitigate is based on a sequence of states and on the rate with which this sequence is progressing, the decision can be more accurate and timely. Such decisions should be based not only on the most probable fault state of the drive but also on the expected time to failure".
3. (p. 2) "it has been assumed, but not substantiated, that prognosis and mitigation based on it may enhance reliability; still, the contributions of fault prognosis on the reliability have not been discussed. It is not clear yet how to determine the effect of mitigation and how false positives and negatives can affect the overall reliability."
4. (p. 4) "It is important to estimate the hot spot, rather than the average winding temperature, and to include the effects of the operating mode while doing so."
5. (p. 5) "The probability of an incorrect diagnosis is constant, regardless of how often the condition of the drive is evaluated, but a more frequent evaluation will increase the corresponding false failure rate for this path".
6. (p. 8) "This large difference between the probabilities of failure allows the decision threshold to be much higher when fault prognosis is used, thus effectively eliminating false negatives."
7. (p. 9) "When this mitigation is performed after a fault has been established, the RUL of a drive system may have already been severely reduced since secondary wear and faults may have developed. Modifying the system based on the results of either fault detection or failure prognosis entails dangers stemming from false positives and negatives."
8. (p. 9) "The proposed analysis method allows the operator to set thresholds for the RUL of the drive to maximize its reliability."

## 11. Ligações com os outros temas: RUL, PHM, C-Level

RUL e PHM (fato do artigo):
- Definição operacional de prognóstico: "prognosis relies on the continuous monitoring of variables of operation and parameters of the drive and uses this information to predict the time until a failure will occur" (p. 2); saídas admissíveis: "estimation of the RUL, estimation of the most probable next state, or estimation of the probability of failure in the next time period" (p. 3).
- Etapas necessárias para ligar prognóstico a confiabilidade: "identification of failure, extraction of features and categorization of the type of fault and its severity, and calculation of the expected evolution of the fault, so that a decision can be taken before a fault becomes a failure or causes other faults that decrease dramatically the remaining useful life (RUL)" (p. 2).
- Revisão de métodos de prognóstico (p. 2–3): HMM e variantes [27], [28]; Kalman e extrapolação [30]; filtros de partículas [25]; referência de base: Vachtsevanos et al. [23]. Trabalhos sobre motores de indução citados: Ondel et al. [29], [30]; Climente-Alarcon et al. [31]; Bazzi, Dominguez-Garcia e Krein [33] (modelo de Markov de confiabilidade para acionamento de indução com controle vetorial).
- Ligação com CBM/PHM e decisão: "Using fault diagnosis and prognosis to determine the need for mitigation and maintenance in order to improve the reliability of systems through decision making has been a field of study in condition-based maintenance and prognostics and health management" (p. 2); "Necessary for the implementation of such techniques is a thorough understanding and modeling of the physics of the failure mechanism" (p. 2).

C-Level / decisão / manutenção (fato do artigo):
- A decisão do operador é enunciada em três opções: "continue operating the drive system, seek immediate interruption of operation and/or maintenance, or employ systems to mitigate the fault. This decision is based on the accuracy of the estimate of the fault state, the operating conditions and demands, and the methods of mitigation available that have been included in the original design" (p. 4).
- Diferença entre diagnóstico e prognóstico para a gestão: "Although the diagnosis of a fault can lead to appropriate maintenance, the estimation of the time to failure through prognosis can lead to the timely mitigation of the fault and, in turn, can extend the lifetime and reliability of the drive" (p. 1).
- Métrica gerencial adotada: MTBF do sistema com e sem mitigação (eqs. (5)–(11)); o artigo não apresenta valores monetários, custos de parada, custos de manutenção ou análise de retorno. A referência [32] (Siyambalapitiya e McLaren, 1988, "Reliability improvement and economic benefits of on-line monitoring systems for large induction machines", IEEE IAS Annual Meeting) é indicada pelos autores como trabalho pioneiro em benefícios econômicos de monitoramento on-line de grandes máquinas de indução (p. 2 e p. 10) — pista bibliográfica relevante para o argumento econômico ao C-Level, a verificar [INSERIR CITAÇÃO após consulta].

Inferência minha sobre a entrega computacional: o artigo sugere um produto mínimo de software para a tese — um "calculador de MTBF com mitigação" que receba (i) a matriz de confusão/probabilidades de estado do classificador, (ii) as taxas de falha dos modos de operação normal, degradado e mitigado, (iii) t_sample e o limiar de decisão, e devolva λ_system, MTBF por caminho e a curva de troca entre falsos positivos e falsos negativos. Para o C-Level, isso traduz "seletividade do snubber" e "load shedding sob N-1" em horas de MTBF e em probabilidade de falha no próximo intervalo, que são as grandezas que o artigo mostra serem decidíveis por limiar (p. 8–9).
