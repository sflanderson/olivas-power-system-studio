# Fichamento 03 — Revisão sobre prognóstico e estimação de RUL de acionamentos e máquinas elétricas

Arquivo-fonte: `/tmp/claude-0/-home-user-olivas-power-system-studio/9d851478-5457-5818-8269-a836133b8dbc/scratchpad/papers/txt/A_Review_on_Prognosis_and_Remaining_Useful_Life_Estimation_of_Electrical_Drives_amp_Machines.txt` (7 páginas extraídas; figuras não recuperadas pela extração de texto).

Convenção de rotulagem usada neste fichamento: **[fato]** = afirmação presente no texto do artigo, com página; **[inferência]** = conclusão minha a partir do texto ou do contexto do projeto; **[hipótese]** = conjectura ainda não verificável.

---

## 1. Referência completa

SHARMA, Vivek Kumar; SESHADRINATH, Jeevanand. A Review on Prognosis and Remaining Useful Life Estimation of Electrical Drives & Machines. In: **2024 Second International Conference on Smart Technologies for Power and Renewable Energy (SPECon)**. IEEE, 2024. DOI: 10.1109/SPECon61254.2024.10537428. ISBN 979-8-3503-8304-1. Páginas nos anais: [INSERIR CITAÇÃO] (não constam no texto extraído).

- Afiliação **[fato, p. 1]**: Department of Electrical Engineering, Indian Institute of Technology Roorkee, Uttarakhand, Índia. Primeiro autor Student Member IEEE; segundo autor Senior Member IEEE.
- Tipo **[fato, p. 1–2]**: artigo de revisão (conferência), 7 páginas, 40 referências, uma tabela comparativa (Tabela I, p. 5–6) e três figuras (Fig. 1 procedimento geral, Fig. 2 classificação, Fig. 3 abordagem híbrida), cujas imagens não estão disponíveis no texto extraído.
- Palavras-chave **[fato, p. 1]**: Condition Monitoring, Diagnosis, Prognosis, Remaining Useful Life.

## 2. Objetivo do artigo

**[fato, p. 1]** "Antologizar" o trabalho em monitoramento de condição, prognóstico e estimação de RUL de acionamentos/máquinas elétricas dos últimos anos; apresentar o procedimento geral de prognóstico, os tipos de técnica e um estudo comparativo; organizar a literatura **por técnica** (e não por componente ou aplicação) e fornecer uma tabela conclusiva com características, méritos e deméritos de cada técnica.

**[fato, p. 1]** Distinção conceitual adotada: diagnóstico = identificação da falta por uma ou várias assinaturas; prognóstico = predição da saúde do sistema por um conjunto de assinaturas ao longo de um período, estendível à estimação de RUL. Dois regimes de prognóstico: (i) "prognóstico geral", sob estresses diversos sem falta declarada; (ii) "prognóstico de falta", após diagnóstico, focado na propagação da falta.

**[fato, p. 2]** Justificativa: a pesquisa em diagnóstico é muito mais difundida que em prognóstico, que "não atraiu o interesse dos pesquisadores devido à complexidade matemática, à complexidade de implementação e à incerteza da degradação ou falha", mas vem ganhando atenção por segurança, gestão de custo, confiabilidade e operação ininterrupta.

**[inferência]** O artigo é um mapa de literatura de baixa profundidade: não deriva modelos, não reproduz resultados numéricos dos trabalhos revisados e não propõe método próprio. Seu valor está na taxonomia, na Tabela I e no conjunto de referências primárias sobre isolamento de estator.

## 3. Sistema/componente e mecanismo(s) de degradação tratados

- Escopo declarado **[fato, p. 1]**: máquinas e acionamentos elétricos em geral (motores de indução, PMAC, drives inversorizados, mancais), com excursões para turbinas (creep), disjuntores (bobina de disparo), baterias Li-ion e cabos subterrâneos (p. 3–4).
- Mecanismos de degradação de motores elencados **[fato, p. 1]**: estresse térmico (decomposição de material), estresse elétrico (desbalanço de tensões de alimentação), estresse mecânico (força de Lorentz oposta e vibração) e estresse ambiental — "estas são as principais facetas que contribuem para a degradação do isolamento". Critério de comprometimento: redução de rigidez dielétrica e de propriedades mecânicas em relação ao estado saudável, elevando a probabilidade de falta entre espiras.
- Afirmação central **[fato, p. 1]**: "Uma das complicações mais prevalentes durante a operação prolongada da máquina é a degradação do isolamento."
- Faltas cobertas nos trabalhos revisados **[fato, p. 3–5]**: degradação de isolamento de estator [10]–[12], [28]; falta entre espiras [16]; quebra de barra de rotor [14]; sub/sobretensão e desbalanço [17]; mancais [7], [22]–[24], [31], [35], [39], [40]; faltas elétricas em PMAC [30]; caixa de engrenagens de aerogerador [38].

**[inferência]** Nenhum trabalho revisado trata de sobretensões de manobra, transitórios de frente íngreme, descargas parciais ou máquinas de média tensão; o foco em isolamento é dominado por máquinas de baixa tensão alimentadas por inversor (grupo Strangas/MSU e Tsyokhla/Griffo/Wang).

## 4. Indicadores/precursores de degradação usados

O artigo não fornece unidades nem taxas de amostragem; a tabela abaixo transcreve o que o texto diz e marca como inferência minha as unidades usuais.

| Indicador (grandeza) | Trabalho revisado | Como é obtido (segundo o artigo) | Unidade [inferência] | Taxa de amostragem |
|---|---|---|---|---|
| Magnitude da tensão aplicada e temperatura de operação | [10] Jensen, Strangas, Foster 2018 | "os dois parâmetros mais impactantes para a estimação de RUL" em ensaio acelerado térmico de estator **[fato, p. 3]** | V; °C | não citada |
| Corrente de fuga do isolamento (tendência) | [11] Babel & Strangas 2014 | Ajuste das medições de corrente de fuga a um modelo de decaimento exponencial, com R e C equivalentes do isolamento obtidos por FEM de máquina PMAC BT de bobina de barras; predição de tendência por EKF **[fato, p. 3]** | A (ou mA/µA) | não citada |
| Picos de sobressinal da resposta transitória da corrente de fuga | [12] Jensen, Strangas, Foster 2017 | Detector de pico analógico, "usando amostragem de baixa frequência"; EKF prediz vida do isolamento; "pode ser confiável quando há dispositivos de banda larga (wide bandgap) no sistema" **[fato, p. 3]** | A | "baixa frequência", valor não citado |
| Capacitância equivalente de parede de isolamento à terra e fator de dissipação em várias frequências | [28] Tsyokhla, Griffo, Wang 2019 | Medidas em conjunto de máquinas sob envelhecimento acelerado até a falha; ajuste de curva relacionando medições à vida final **[fato, p. 4]** | F (nF/pF); adimensional (tan δ) | não citada |
| Parâmetros de falta entre espiras (parâmetros de modelo) | [16] Nguyen, Seshadrinath et al. 2017 | Estimados por filtro de partículas e usados como parâmetros prognósticos; progressão da falta modelada como degraus nos parâmetros **[fato, p. 3]** | adimensional / Ω | não citada |
| Indicadores estacionários e transitórios de corrente (Fourier, Hilbert) | [14] Climente-Alarcon et al. 2015 | Transformadas sobre assinaturas medidas; PF para evolução de quebra de barra **[fato, p. 3]** | — | não citada |
| Características tempo-frequência da corrente da máquina | [30] Strangas et al. 2008 | Extraídas experimentalmente para treinar HMM; probabilidade de estado de falha por observação **[fato, p. 4]** | — | não citada |
| Health Index (HI) | [27] Yang et al. 2016 | Mapeamento sinais→HI→RUL em dois estágios; HI assumido decrescente linearmente do máximo ao mínimo **[fato, p. 4]** | adimensional | não citada |
| Vibração/aceleração | [20], [21], [39], [40] | Aquisição periódica; análise de envelope; distância de Mahalanobis até limiar de degradação, depois KF **[fato, p. 3, 5]** | m/s² | não citada |
| Corrente do gerador | [38] Cheng, Qu, Qiao 2018 | Assinatura de saúde de caixa de engrenagens; ANFIS + PF **[fato, p. 5]** | A | não citada |
| Tensão e corrente de campo (cabos) | [34] Liu, Wang, Tian 2015 | Análise probabilística contínua de dados de campo **[fato, p. 4]** | V; A | não citada |

**[fato, p. 1]** Procedimento geral (Fig. 1): (1) obter assinaturas de saúde por medição ou por estimação no mecanismo de controle; (2) extrair características; (3) algoritmo para estimar RUL, o estado mais provável seguinte ou a probabilidade de falha no próximo período. "Em algumas aplicações a RUL também é conhecida como distância prognóstica disponível ou lead time, usada como métrica prognóstica importante."

## 5. Modelo/algoritmo

**Classe: revisão** (não propõe modelo próprio). Taxonomia em quatro classes (Fig. 2) **[fato, p. 2]**: (A) baseadas em modelo; (B) orientadas a dados; (C) baseadas em conhecimento (também chamadas estatísticas); (D) híbridas.

### 5.1 Equações-chave transcritas

Únicas equações do artigo: modelo geral em espaço de estados usado para explicar KF/EKF/UKF **[fato, p. 3]**. Os símbolos das Eqs. (1) e (2) foram perdidos na extração do texto (aparecem como " =   +  + (1)" e " =   +  (2)"). A reconstrução abaixo é **[inferência]** a partir da lista de definições que o próprio artigo fornece logo após as equações (p. 3):

- Eq. (1), p. 3: x_k = A_k x_{k-1} + B_k u_k + W_k
- Eq. (2), p. 3: y_k = C_k x_k + V_k

onde **[fato, p. 3]**: A_k = modelo de transição de estado aplicado ao estado passado x_{k-1}; B_k = modelo de entrada de controle aplicado à entrada u_k; W_k = ruído de processo; C_k = modelo de observação/medição que "fornece o mapeamento do valor estimado ao valor verdadeiro"; V_k = ruído de medição.

**[fato, p. 3]** Restrições do KF: A_k e C_k lineares; W_k e V_k gaussianos não correlacionados, o que garante PDFs gaussianas de estado e saída. EKF: lineariza via Jacobianos de A_k e C_k nos estados estimados. UKF: em vez de linearizar, propaga pontos sigma pela transformação não linear original, usando **2K+1 pontos sigma para K estados**; "preferível em estimações altamente não lineares".

### 5.2 Estrutura das classes (síntese do artigo)

- **Baseadas em modelo [fato, p. 2–3]**: exigem modelo físico/numérico preciso e parâmetros bem determinados; permitem limiar de predição preciso, capturam interação entre assinaturas e faltas simultâneas em nível de componente; "é a abordagem mais precisa", mas inviável quando falta conhecimento de domínio. Ferramentas: KF/EKF/UKF [10]–[13], PF [14]–[16], observadores [17]–[18].
- **Orientadas a dados [fato, p. 4]**: interpolam comportamento futuro a partir de histórico; "caixa-preta"; problemas declarados: definição do limiar, tempo de início da predição (TSP) e anomalias aleatórias nos dados. Famílias: regressão linear/polinomial [27]–[29], Markov/HMM [30]–[31], inteligentes (NN) [33]–[34], probabilísticas; comparação RVM vs. GPR vs. NN em [25]. Subdivisão por uso de HI: RUL direta (um estágio) vs. baseada em HI (dois ou mais estágios) [27].
- **Baseadas em conhecimento [fato, p. 4]**: processamento de sinais e lógica fuzzy; "não há muito trabalho extenso neste campo"; usadas em combinação com as outras para formar híbridos.
- **Híbridas [fato, p. 5]**: combinam PF + NN [37], ANFIS + PF [38], clustering por formigas + HMM + ANFIS [39], Mahalanobis + KF com EM e atualização bayesiana [40], NN distribuídas + Bayes recursivo [36].

### 5.3 Tabela I — características, méritos e deméritos **[fato, p. 5–6]**

| Método | Característica | Mérito | Demérito |
|---|---|---|---|
| KF/EKF/UKF | modelo em espaço de estados | fácil de implementar e preciso, "por isso a técnica mais famosa" | exige modelo preciso e estados iniciais; inclusão de ruído gaussiano aumenta complexidade |
| Filtro de partículas | modelo em espaço de estados | preciso sem hipótese gaussiana | computação complexa; implementação real "onerosa" |
| Observadores (Luenberger, modos deslizantes) | modelo em espaço de estados | resultados precisos | exige estado inicial e modelo preciso |
| Regressão linear/polinomial | dados passados, atualizados ao longo da estimação | fácil; recomendada para falhas pouco complexas | inadequada para falhas complexas |
| NN / NFIS | idem | aplicável a falhas complexas | grande volume de dados |
| Probabilísticas | idem | predição precisa se há domínio de probabilidade | "enorme" volume de dados de falha |
| Markov | idem | "uma das ferramentas mais apropriadas" com bom histórico | "enorme" volume de dados de falha |
| Processamento de sinais | análise no tempo/frequência | basta o sinal atual de falta | requer informação de todas as falhas possíveis |
| Lógica fuzzy | regras se-então | menor variabilidade do processo | exige expertise do sistema |

Hiperparâmetros: nenhum é reportado **[fato]**.

## 6. Dados e experimento

**[fato]** O artigo não apresenta dados próprios, ensaios ou datasets. Menções indiretas, sem números:
- [10]: "ensaio de degradação acelerada efetuado aplicando estresse térmico no estator em alta temperatura e por longa duração" (p. 3) — temperatura, duração e número de amostras não informados.
- [28]: "conjunto de máquinas submetido a envelhecimento acelerado até a falha completa", medidas "em diferentes frequências" (p. 4) — quantidade de máquinas e frequências não informadas.
- [11]: FEM de "máquina PMAC de baixa tensão de bobina de barras" (p. 3).
- [25]: comparação RVM/GPR/NN (p. 4), sem resultados transcritos.

**[inferência]** Para qualquer reuso quantitativo é obrigatório recorrer aos artigos primários; este texto não serve como fonte de números de ensaio.

## 7. Métricas e resultados numéricos

**[fato]** Não há métricas de desempenho (erro de RUL, horizonte, cobertura, RMSE etc.) nem resultados numéricos no artigo. Os únicos valores quantitativos do texto são estruturais:
- 4 classes de abordagem (p. 2); 40 referências (p. 6–7); Tabela I com 9 linhas de método em 3 grupos (p. 5–6).
- Regra do UKF: 2K+1 pontos sigma para K estados (p. 3).
- Subdivisão orientada a dados: 1 estágio (RUL direta) vs. ≥2 estágios (via HI) (p. 4).

## 8. Limitações

**Declaradas pelos autores:**
- (declarada, p. 2) Prognóstico é área com menos pesquisa que diagnóstico, por complexidade matemática, de implementação e incerteza de degradação/falha.
- (declarada, p. 2–3) Abordagens baseadas em modelo exigem modelo preciso e parâmetros físicos exatos; podem ser tediosas ou impossíveis de obter.
- (declarada, p. 4) Abordagens orientadas a dados: dificuldade de fixar limiar, tempo de início de predição e anomalias; exigem grande volume de dados de falha (Tabela I, p. 6).
- (declarada, p. 5) Dados históricos de longo prazo "às vezes são impraticáveis" para sistemas de longa vida.
- (declarada, p. 4) Métodos baseados em conhecimento pouco desenvolvidos.

**Identificadas por mim (minha inferência):**
- Ausência total de resultados numéricos, métricas prognósticas (p. ex., α-λ, PH, RA) ou comparação quantitativa entre técnicas; a Tabela I é qualitativa e opinativa (ex.: "técnica mais famosa").
- Inconsistência bibliográfica verificável: no texto, [31] é descrito como análise tempo-frequência com quatro métodos em drive PMAC estendida a HMM (p. 4) e [35] como híbrido para RUL de mancais com modelos preditivos adaptativos (p. 5); na lista de referências (p. 7), [31] é Ahmad, Khan e Kim (mancais, modelos adaptativos) e [35] é Zaidi et al. (PMAC, HMM). As entradas [31] e [35] parecem trocadas; ao citar, verificar o primário.
- Numeração de seções salta de "III. CONCLUSIONS" para "VI. REFERENCES" (p. 6); indício de revisão editorial fraca.
- Equações (1)–(2) genéricas, sem qualquer modelo de degradação de isolamento transcrito (Arrhenius, Eyring, lei de potência inversa, modelo de decaimento exponencial), embora citados nominalmente ([17] Arrhenius, p. 3; [11] decaimento exponencial, p. 3).
- Recorte temporal: referências até 2021; não cobre deep learning para RUL (LSTM, TCN, transformers) nem prognóstico de descargas parciais em máquinas MT.
- Escopo tendencioso para máquinas BT alimentadas por inversor e para mancais; máquinas de média tensão, isolamento formado (VPI/resin-rich), sobretensões de manobra e DP não aparecem.
- Termos como "hybrid systems" (p. 2, sistemas híbridos contínuo-discretos de [8]–[9]) e "hybrid approaches" (p. 5, combinação de técnicas) são usados com sentidos distintos sem alerta, o que pode confundir o leitor.

## 9. Transferibilidade para o problema-alvo

Problema-alvo: isolamento de estator de motor de indução MT (2,3–13,8 kV) sob (a) sobretensões de manobra de VCB (chopping, reignições múltiplas, frentes íngremes, dV/dt), com/sem snubber tiristorizado; (b) estresse térmico de partidas de grandes motores sob contingência N-1 com load shedding.

**O que se transfere:**
- *Arquitetura de prognóstico* **[fato, p. 1]** — pipeline assinaturas → extração de características → algoritmo de RUL/próximo estado/probabilidade de falha, com a RUL expressa como "lead time". **[inferência]** Serve como espinha dorsal do método de monitoramento: as assinaturas podem vir (a) das formas de onda de manobra simuladas no Olivas Power System Studio (modelo VCB com I_CHOP, RRDS_A/RRDS_B, DIDT_CRIT e controlador SNUB_CTRL, conforme `app/validation/validator_vcb.py`) e (b) do perfil térmico de partida sob N-1.
- *Classe de estimador* **[fato, p. 3]** — EKF para tendência de indicador de isolamento com modelo de decaimento exponencial [11] e EKF alimentado por picos de sobressinal de corrente de fuga [12], explicitamente indicado como confiável "quando há dispositivos de banda larga no sistema". **[inferência]** O argumento de [12] (transitórios de frente íngreme de inversores SiC/GaN excitam a resposta transitória do isolamento) é analogamente aplicável a reignições de VCB: ambos são eventos de alto dV/dt cuja resposta transitória da corrente pode ser capturada por detector de pico e amostragem lenta. Isso é a ligação mais direta com o tema A.
- *Variáveis de estresse dominantes* **[fato, p. 3]** — em [10], magnitude da tensão aplicada e temperatura de operação são "os dois parâmetros mais impactantes" para RUL. **[inferência]** Corresponde exatamente ao par (a) tensão de surto / (b) temperatura de partida do problema-alvo; sugere um modelo de vida multi-estresse com a contagem de eventos de manobra e de partidas como covariáveis.
- *Modelo térmico + Arrhenius* **[fato, p. 3]** — [17] combina modelo elétrico e térmico com equações de Arrhenius para perda de vida sob sub/sobretensão e desbalanço. **[inferência]** Transfere-se ao tema B: cada partida sob N-1 (tensão reduzida, corrente de rotor bloqueado prolongada) produz um incremento de temperatura de enrolamento e uma perda de vida calculável por Arrhenius; o load shedding ótimo (NSGA-II/III) pode incluir a perda de vida acumulada como objetivo ou restrição.
- *Indicadores de isolamento off-line/on-line* **[fato, p. 4]** — capacitância de parede à terra e fator de dissipação em múltiplas frequências [28], com ajuste de curva para vida final. **[inferência]** Estas grandezas são medidas rotineiramente em motores MT (ensaios de tan δ/capacitância) e são candidatas naturais a Health Index.
- *Esquema HI em dois estágios* **[fato, p. 4]** — sinais → HI → RUL [27]. **[inferência]** Adequado quando os dados de falha são escassos (caso industrial típico), pois separa a fusão de indicadores da extrapolação.
- *Método de validação* **[fato, p. 3–4]** — envelhecimento acelerado térmico até a falha [10], [28]. **[inferência]** Transfere-se como estratégia, não como dado; para o problema-alvo seria necessário envelhecimento combinado térmico + impulsos repetitivos, que o artigo não discute.
- *Trade-offs da Tabela I* **[fato, p. 5–6]** — orientam a escolha: KF/EKF quando há modelo de degradação simples e poucos dados; PF quando a distribuição não é gaussiana (típico de eventos discretos de manobra); HMM/probabilístico só com histórico farto.

**O que não se transfere e por quê:**
- Nenhum indicador ou modelo é específico para sobretensões de manobra, chopping, reignições, dV/dt ou descargas parciais em isolamento MT; a palavra "surge"/"partial discharge" não ocorre. A física da degradação por impulsos repetitivos (erosão por DP, envelhecimento por espaçamento de espiras) fica fora do artigo.
- Não há modelo de degradação explícito (só a forma genérica de espaço de estados); as funções f(·) e h(·) para o isolamento MT terão de vir dos primários ([10]–[12], [17], [28]) ou de normas (IEC 60034-18-41/42, IEEE 1776) [INSERIR CITAÇÃO].
- Não há dados, unidades, taxas de amostragem ou métricas; impossível calibrar ou comparar desempenho a partir deste texto.
- O efeito do snubber tiristorizado (mitigação seletiva) sobre a taxa de degradação não tem análogo no artigo; o mais próximo é [6] (prognóstico usado para mitigação e agendamento de manutenção em PMAC, p. 2), que sugere apenas a ideia de fechar a malha prognóstico → mitigação.
- Contexto de manobra de disjuntor aparece só como monitoramento da bobina de disparo do próprio disjuntor [32] (p. 4), não do efeito do disjuntor sobre o motor.

**Nota de transferibilidade: 3/5.** Justificativa **[inferência]**: transfere-se a arquitetura, a taxonomia, o par tensão/temperatura como estressores dominantes, o uso de EKF/PF sobre indicadores de isolamento e um conjunto curto e pertinente de referências primárias; não se transfere nenhum indicador, equação, dado ou métrica diretamente aplicável ao isolamento MT sob manobra de VCB. Útil como texto de posicionamento na revisão bibliográfica da tese e como ponte para os primários; insuficiente como base metodológica.

## 10. Citações literais relevantes

1. (p. 1) "The life of electric motor depends on thermal stress leads to material decomposition, electrical stresses such as unbalancing in supply voltages, mechanical stresses due to opposing Lorentz force and vibration, and environmental stresses. These are the main facets contributing to insulation degradation."
2. (p. 1) "One of the most prevalent complication during long run of the machine is the insulation degradation."
3. (p. 1) "In some applications remaining useful life is also known as available prognostic distance or lead time, which is used as an important prognostic metrics."
4. (p. 2) "The failure prognosis has not attracted the interests of researchers due to mathematical complexity, implementation complexity and uncertainty of degradation or failure. However, now a days it's getting attention ensuring the safety requirements, cost management, reliability and uninterrupted operation."
5. (p. 3) "The two most impactful parameters for remaining useful life estimation is the magnitude of applied voltage and the operating temperature."
6. (p. 3) "in [12], an analog peak detector is used to get the magnitudes of peak overshoots of the transient response of the leakage current using low frequency sampling. And EKF is exerted to predict the insulation life. This strategy may be reliable when wide bandgap devices are there in the system."
7. (p. 4) "However, in data-driven methods there are some worthwhile issues viz. make out of threshold value, time to start prediction (TSP) and working out with random anomalies in the data."
8. (p. 5) "The model-based approaches work with system specific model, and it will not be feasible to develop such models for every system. The data-driven methods need past or historical data of concerned system, sometimes it becomes impractical to have such data for long run systems."

## 11. Ligações com os outros temas: RUL, PHM e C-Level

**RUL/PHM (fatos do artigo):**
- Definição operacional de RUL como extensão do prognóstico e sua equivalência a "lead time" (p. 1) — vocabulário útil para alinhar a tese com a literatura PHM.
- Diferença entre "prognóstico geral" (estresses, sem falta) e "prognóstico de falta" (propagação) (p. 1). **[inferência]** O tema A (surtos de VCB) e o tema B (partidas N-1) situam-se no primeiro regime: são estressores que consomem vida sem falta declarada; a transição para o segundo regime ocorre quando surge uma falta entre espiras incipiente [16].
- Fechamento da malha prognóstico → mitigação → agendamento de manutenção [6] (p. 2). **[inferência]** É o análogo conceitual da "mitigação seletiva" do tema A: o snubber tiristorizado pode ser acionado seletivamente com base no estado de saúde estimado, e o load shedding do tema B pode ponderar a perda de vida.

**C-Level / custo / decisão (transcrições com página):**
- (p. 1) "Thus, by employing CBM the cost associated with inessential maintenances and the down time can be reduced."
- (p. 1) "It is important in continuous health monitoring, timely maintenance scheduling, risk of failure analysis and remaining life prediction."
- (p. 2) "However, now a days it's getting attention ensuring the safety requirements, cost management, reliability and uninterrupted operation."
- (p. 6) "Prognosis is helpful in condition-based maintenance that reduces the cost of unnecessary maintenance and degradation monitoring that can avoid the severe failure and it also reduces down time of the machine."

**[inferência]** Os argumentos econômicos são qualitativos (sem valores de custo, disponibilidade ou retorno). Para um público C-Level, este artigo fornece a narrativa (CBM reduz manutenção desnecessária e downtime; prognóstico complementa diagnóstico), mas não o caso de negócio quantificado; este deverá vir de outras fontes [INSERIR CITAÇÃO] ou do próprio estudo computacional, que pode traduzir a perda de vida por manobra/partida em custo esperado de falha e em decisões (instalar snubber, ajustar política de load shedding, antecipar rebobinagem).

**[hipótese]** Dado o contexto industrial sugerido pela marca d'água (óleo e gás), a Tabela I aponta para uma estratégia pragmática: começar com EKF/regressão sobre poucos indicadores (tan δ, capacitância, temperatura, contagem de manobras e partidas) e evoluir para PF/híbrido conforme se acumulem dados de campo, já que métodos de Markov e probabilísticos exigem "enorme volume de dados de falha" (p. 6), raramente disponível para motores MT críticos.
