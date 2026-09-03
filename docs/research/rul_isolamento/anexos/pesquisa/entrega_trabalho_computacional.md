# Entrega de um trabalho computacional de RUL/PHM com qualidade acadêmica e industrial — pesquisa web multi-fonte

Tema: `entrega_trabalho_computacional`. Data da coleta: 2026-09-02. Escopo: arquiteturas de referência (ISO 13374 / OSA-CBM / MIMOSA), bibliotecas de código aberto, bancos de dados públicos de prognóstico, métricas de prognóstico, quantificação de incerteza, XAI, gêmeo digital (definições normativas), MLOps e deriva, reprodutibilidade (Zenodo, Software Heritage, JOSS, FAIR4RS), estrutura de artefato computacional de tese e conteúdo de um painel executivo de RUL (Asset Health Index, semáforo, RUL com intervalo, custo evitado, recomendação). Finalidade: subsidiar o módulo MVP de RUL de isolamento de motores de indução de média tensão (MT, 2,3–13,8 kV) do Olivas Power System Studio e o discurso para C-Level.

Convenções de rótulo (regra "zero suposição"): [FATO: doc A/B, p. N]; [FATO: artigo NN, p. N]; [NORMA: id, cláusula/tabela]; [LITERATURA: ref verificada + URL]; [REPO: caminho:linha]; [CÁLCULO PRÓPRIO: fórmula/comando]; [INFERÊNCIA FÍSICA: derivação]; [HIPÓTESE]. Escala de confiança da Tabela 2: **A** = fonte primária acessada, conteúdo lido e verificável (norma, artigo, documentação oficial, arquivo de esquema); **M** = fonte primária acessada, porém de fornecedor (material promocional) ou metadado sem texto integral (registro Crossref/Semantic Scholar/Zenodo) ou reprodução secundária de fonte primária identificada; **B** = fonte secundária, conteúdo parcial ou números conflitantes. Somente URLs efetivamente acessadas (conteúdo lido nesta coleta) constam das tabelas e referências; tentativas bloqueadas constam no Anexo A. A busca web por motor de pesquisa não esteve disponível nesta sessão; a coleta foi feita por acesso direto a URLs de fontes primárias conhecidas, APIs abertas (Crossref, Semantic Scholar, Zenodo, arXiv, NTRS) e busca de código no GitHub.

Página no formato "p. N" refere-se à numeração impressa quando existente; "PDF p. N" refere-se ao índice de página do arquivo quando a numeração impressa não pôde ser recuperada. Cópias dos PDFs lidos: `<scratchpad da sessão>/out/web/pdf/entrega/` (fair4rs.pdf, saxena2010_ijphm.pdf, cnaim_v2.1.pdf, nist_ams_400-2.pdf, chaoub2104.05049.pdf, osacbm_schema1.xsd).

---

## 1. Síntese executiva

1. A arquitetura de referência de sistemas de monitoramento/prognóstico continua sendo a cadeia funcional de seis blocos da ISO 13374, implementada pelo OSA-CBM da MIMOSA (versão 3.3.1, 2010). A existência dos seis blocos e das siglas DA/DM/SD/HA/PA/AG foi verificada em fonte primária (página da MIMOSA e esquema XSD do namespace `OSACBMV3.3.1`) [LITERATURA: MIMOSA; XSD OSA-CBM 3.3.1]; a expansão nominal dos blocos consta do enunciado da tarefa e não pôde ser lida no texto da norma (iso.org bloqueado) — ver §4.
2. A norma de prognóstico ISO 13381-1 foi **reeditada em 2025** (ISO 13381-1:2025 "General guidelines and requirements", válida desde 02.09.2025; a edição de 2015 foi retirada) [NORMA: ISO 13381-1:2025, página de catálogo EVS]. Qualquer tese que cite a ISO 13381-1 deve referenciar a edição 2025 e verificar o novo texto ("requirements").
3. Há uma pilha madura de código aberto para RUL: NASA ProgPy v1.8 (maio 2025; UKF/PF/KF, preditores Monte Carlo e Unscented Transform, métricas α-λ, PH, CRA, PoS), FilterPy (KF/EKF/UKF, partículas), pymoo 0.6.2 (NSGA-II/III), lifelines (sobrevivência, DOI Zenodo), scikit-learn (BSD), tsai (PyTorch/fastai), SHAP (MIT) e PyPHM (carregadores de dados, alfa) [LITERATURA: documentações oficiais].
4. Bancos públicos de prognóstico existem para IGBT (NASA, 6 dispositivos, sobrecarga térmica), turbofans (C-MAPSS FD001–FD004; PHM08), rolamentos (FEMTO/PRONOSTIA; XJTU-SY: 15 rolamentos, 25,6 kHz), baterias e capacitores; **não foi encontrado banco público de envelhecimento de isolamento de estator MT** no repositório NASA PCoE nem em buscas na API do Zenodo [LITERATURA: NASA PCoE; Zenodo API]. Isso condiciona a validação do módulo Olivas a dados sintéticos/físicos e a validação de método em bancos de outros domínios.
5. As métricas canônicas de prognóstico (Prognostic Horizon, α-λ, Relative Accuracy/CRA, Convergence) estão definidas em Saxena et al. (2010, IJPHM 1(1)), com a hierarquia PH → α-λ → RA/CRA → convergência e a incorporação de massa de probabilidade dentro dos limites α [LITERATURA: Saxena 2010, PDF p. 8, 11, 13–16]. A função de pontuação assimétrica do PHM08 (exp(−d/13)−1 para atraso negativo; exp(d/10)−1 para d ≥ 0) foi verificada em fonte secundária que a atribui ao desafio original [LITERATURA: Chaoub et al. 2021, p. 5].
6. Incerteza: Sankararaman e Goebel (2015) sustentam que "somente a abordagem bayesiana é aplicável no contexto de gestão de saúde baseada em condição" [LITERATURA: IJPHM 6(4)]; alternativas práticas verificadas: deep ensembles (Lakshminarayanan 2017), dropout bayesiano (Gal & Ghahramani 2016) e predição conforme com garantia de cobertura (Angelopoulos & Bates 2021).
7. XAI em PHM: revisão PRISMA 2015–2021 (Sensors 21(23):8020) reporta adoção crescente, perdas de desempenho mínimas e lacunas em envolvimento humano, métricas de avaliação e gestão de incerteza [LITERATURA: Crossref + resumo].
8. Gêmeo digital: a ISO 23247-1:2021 (manufatura) define gêmeo digital como "representação digital adequada ao propósito de um Elemento Observável de Manufatura (OME) com sincronização entre o OME e sua representação digital" (transcrição do NIST AMS 400-2 a partir do ISO/DIS 23247-1) [LITERATURA: NIST AMS 400-2, PDF p. 8]; a ISO/IEC 30173:2023 traz conceitos e terminologia genéricos [NORMA: ISO/IEC 30173:2023, catálogo EVS]. A sincronização é o requisito que separa "modelo de simulação" de "gêmeo digital".
9. MLOps: níveis 0/1/2 de maturidade e gatilhos de retreinamento (sob demanda, agenda, novos dados, degradação de desempenho, mudança de distribuição) [LITERATURA: Google Cloud Architecture]; deriva de dados/conceito/predição e testes KS, qui-quadrado, Wasserstein, Jensen-Shannon e PSI [LITERATURA: Evidently AI].
10. Reprodutibilidade e artefato de tese: FAIR4RS v1.0 (DOI 10.15497/RDA00068, 2022) com 17 princípios/subprincípios; DOI por release via integração GitHub–Zenodo; SWHID intrínsecos do Software Heritage; JOSS exige licença OSI, seis meses de histórico público, testes e documentação; "Ten Simple Rules" (Sandve 2013) e definições reproduzível/replicável/robusto/generalizável (The Turing Way).
11. Painel executivo: os índices de saúde de ativos têm base normativa/regulatória em T&D (CIGRE TB 858, 2021, metodologia em oito passos; Ofgem CNAIM v2.1, 2021: Health Score 0,5–15 → bandas HI1–HI5 → PoF; Criticality C1–C4; risco monetizado) e base comercial em APM (GE Vernova APM Health/SmartSignal; AVEVA Predictive Analytics com "time-to-failure forecasts" e ações prescritivas; AVEVA PI; ABB Digital Powertrain Insights com "real-time asset health dashboards"; Siemens Senseye com "visão unificada de condição e risco"). O conteúdo mínimo consolidado em §5.9 é: banda de saúde, PoF, criticidade/consequência, risco (monetizado), RUL com P05/P50/P95 e horizonte, ação recomendada com custo evitado, prioridade de atenção, estado de dados/deriva, versão e hash do modelo, explicação dos fatores dominantes e limitações declaradas.
12. Para o Olivas: o repositório já possui os padrões de Monte Carlo com semente, gating comercial, trilha de auditoria SHA256 e painel HTML de avaliação de equipamentos [REPO], o que permite implementar a cadeia DA→AG sem reescrita; faltam `pyproject.toml`, `CITATION.cff`, DOI e um protocolo de métricas de prognóstico (§5).

---

## 2. Tabela de fatos verificados

| # | Fato | Fonte (URL acessada) | Ano | Conf. |
|---|---|---|---|---|
| 1 | "OSA-CBM is an implementation of the ISO-13374 functional specification. OSA-CBM adds data structures and defines interface methods." A ISO 13374 "defines the six functional blocks of condition monitoring systems and their general inputs/outputs". | https://www.mimosa.org/mimosa-osa-cbm/ | 2010 (v3.3.1, 29 jun 2010; desenvolvimento desde 2001) | A |
| 2 | O esquema XML do OSA-CBM 3.3.1 (namespace `http://www.mimosa.org/OSACBMV3.3.1`) define os elementos `DADataEvent`, `DMDataEvent`, `SDDataEvent`, `HADataEvent`, `PADataEvent`, `AGDataEvent` e as portas `DAPort … AGPort`, confirmando as seis camadas DA/DM/SD/HA/PA/AG. | https://raw.githubusercontent.com/PredixDev/ext-interface/master/ext-model/src/main/resources/META-INF/schemas/osa/schema1.xsd (cópia do esquema MIMOSA em repositório público; localizado via busca de código GitHub `HADataEvent PADataEvent SDDataEvent`) | 2010 (esquema) | A |
| 3 | A página de especificações da MIMOSA lista "OSA-CBM 3.2.1", enquanto a página do OSA-CBM declara "latest version 3.3.1" — discrepância de versão entre páginas oficiais. | https://www.mimosa.org/specifications/ e https://www.mimosa.org/mimosa-osa-cbm/ | — | M |
| 4 | ISO 13374-1:2003 "Condition monitoring and diagnostics of machines — Data processing, communication and presentation — Part 1: General guidelines" "establishes general guidelines for software specifications related to data processing, communication, and presentation of machine condition monitoring and diagnostic information". Válida desde 13.03.2003. | https://www.evs.ee/en/iso-13374-1-2003 | 2003 | A |
| 5 | ISO 13374-2:2007 (Part 2: Data processing) especifica "a reference information model and a reference processing model to which an open condition monitoring and diagnostics (CM&D) architecture needs to conform". | https://www.evs.ee/en/iso-13374-2-2007 | 2007 | A |
| 6 | ISO 13381-1:2015 (Prognostics — Part 1: General guidelines) foi **retirada em 02.09.2025 e substituída pela ISO 13381-1:2025** "Condition monitoring and diagnostics of machine systems — Prognostics — Part 1: General guidelines and requirements". Partes companheiras (2015): performance trending (Parte 2), cycle-based life techniques (Parte 3), remaining useful life modelling (Parte 4). | https://www.evs.ee/en/iso-13381-1-2015 ; https://www.evs.ee/en/iso-13381-1-2025 | 2015 / 2025 | A |
| 7 | ISO 17359:2018 "Condition monitoring and diagnostics of machines — General guidelines" dá diretrizes gerais para estabelecer um programa de monitoramento de condição e referencia as normas associadas. | https://www.evs.ee/en/iso-17359-2018 | 2018 | A |
| 8 | ISO 55000:2024 "Asset management — Vocabulary, overview and principles" (substitui ISO 55000:2014), aplicável a todos os tipos de ativos e organizações. | https://www.evs.ee/en/iso-55000-2024 | 2024 | A |
| 9 | ISO 23247-1:2021 "Automation systems and integration — Digital twin framework for manufacturing — Part 1: Overview and general principles", válida desde 22.10.2021. | https://www.evs.ee/en/iso-23247-1-2021 | 2021 | A |
| 10 | Definição (transcrita pelo NIST do ISO/DIS 23247-1): gêmeo digital em manufatura é "a fit for purpose digital representation of an Observable Manufacturing Element (OME) with synchronization between the OME and its digital representation"; OME pode ser pessoal, equipamento, material, processo, instalação, ambiente, produto ou documento. Entidades da arquitetura de referência (ISO/DIS 23247-2): OMEs; Data Collection and Device Control Entity (DCDCE); Core Entity; User Entity; Cross-System Entity. O documento traz um caso de uso "Machine Health Digital Twin". | https://nvlpubs.nist.gov/nistpubs/ams/NIST.AMS.400-2.pdf (PDF p. 8, 12–13; seção 4.1) | 2021 | A |
| 11 | ISO/IEC 30173:2023 "Digital twin — Concepts and terminology" cobre "the terms and definitions of digital twin, concepts of digital twin (e.g. digital twin system context, life cycle process for digital twin, types of digital twin), functional view of digital twin, and digital twin stakeholders". | https://www.evs.ee/en/iso-iec-30173-2023 | 2023 | A |
| 12 | IEEE 1856-2017 "IEEE Standard Framework for Prognostics and Health Management of Electronic Systems", IEEE Reliability Society, aprovada em 28 set 2017, DOI 10.1109/IEEESTD.2017.8227036. | https://api.crossref.org/works/10.1109/IEEESTD.2017.8227036 | 2017 | M (metadado) |
| 13 | ProgPy: "an open-sourced python package supporting research and development of prognostics and health management and predictive maintenance tools"; NASA PCoE com DLR, Northrop Grumman, RISE e Vanderbilt; v1.8 (maio 2025), DOI 10.5281/ZENODO.8097013; `pip install progpy`; contém modelos, estimadores de estado, preditores, `UncertainData`, modelos compostos/ensemble/mixture-of-experts, `prog_server`/`prog_client`; licença NASA "AS IS" com cláusula de indenização ao governo dos EUA. | https://nasa.github.io/progpy/ | 2025 | A |
| 14 | ProgPy — estimadores: UKF ("sigma points", assume normalidade), PF (amostras não ponderadas, mais preciso e mais custoso), KF (apenas `LinearModel`); preditores: Unscented Transform (retorna `MultivariateNormalDist`) e Monte Carlo (`UnweightedSamples`); métricas: α-λ ("whether the prediction falls within specified limits at particular times with respect to a performance measure"), Prognostic Horizon ("the difference between a time when the predictions meet specified performance criteria, and the time corresponding to the true Time of Event"), Cumulative Relative Accuracy, Monotonicity, Probability of Success. | https://nasa.github.io/progpy/prog_algs_guide.html | 2025 | A |
| 15 | FilterPy: "a Python library that implements a number of Bayesian filters, most notably Kalman filters" (KF, EKF, UKF, Ensemble KF, g-h, Bayes discreto, reamostragem para filtro de partículas, suavizadores RTS); autor Roger R. Labbe; livro "Kalman and Bayesian Filters in Python". | https://filterpy.readthedocs.io/en/latest/ | 2014–2016 (docs) | A |
| 16 | pymoo 0.6.2: NSGA-II, R-NSGA-II, NSGA-III, U-NSGA-III, MOEA/D, RVEA, SMS-EMOA etc.; citação Blank & Deb, IEEE Access 8:89497–89509, 2020, DOI 10.1109/ACCESS.2020.2990567. | https://pymoo.org/ ; https://api.crossref.org/works/10.1109/ACCESS.2020.2990567 | 2020 | A |
| 17 | NSGA-II: Deb, Pratap, Agarwal, Meyarivan, IEEE Trans. Evol. Comput. 6(2):182–197, 2002, DOI 10.1109/4235.996017. | https://api.crossref.org/works/10.1109/4235.996017 | 2002 | M (metadado) |
| 18 | lifelines: "a complete survival analysis library, written in pure Python", dados censurados à direita/esquerda/intervalo; modelos paramétricos, semiparamétricos e não paramétricos; citação via Zenodo DOI 10.5281/zenodo.805993. | https://lifelines.readthedocs.io/en/latest/ | — | A |
| 19 | scikit-learn: licença BSD; citação Pedregosa et al., JMLR 12:2825–2830, 2011. | https://scikit-learn.org/stable/about.html | 2011 | A |
| 20 | tsai: "State-of-the-art Deep Learning library for Time Series and Sequences" sobre PyTorch e fastai; classificação, regressão, previsão e imputação; modelos LSTM/GRU, InceptionTime, ResNet, TCN, TST, PatchTST, ROCKET/MiniRocket; requer Python ≥ 3.10 (v1.0.0). | https://timeseriesai.github.io/tsai/ | 2023 (citação) | A |
| 21 | SHAP: "a game theoretic approach to explain the output of any machine learning model"; licença MIT; TreeExplainer, DeepExplainer, GradientExplainer, LinearExplainer, KernelExplainer; referências Lundberg & Lee (NeurIPS 2017) e Lundberg et al. (Nature Machine Intelligence 2020). | https://github.com/shap/shap ; https://shap.readthedocs.io/en/latest/ | 2017/2020 | A |
| 22 | PyPHM: "Machinery data, made easy"; carregadores para UC-Berkeley Milling, IMS Bearing e Airbus Helicopter Accelerometer; MIT; estado alfa; arXiv:2205.15489. | https://github.com/tvhahn/PyPHM | 2022 | A |
| 23 | Repositório NASA PCoE: 21 bancos; Turbofan (C-MAPSS, Saxena & Goebel 2008) — quatro conjuntos com combinações de condições operacionais e modos de falha; PHM08 Challenge (RUL verdadeira não revelada; "currently unavailable"); IGBT Accelerated Aging (Celaya, Wysocki, Goebel 2009) — "6 devices", sobrecarga térmica, um com polarização CC de gate e demais com sinal quadrado; FEMTO Bearing (Nectoux et al., IEEE PHM 2012); baterias Li-ion (múltiplos); capacitores sob estresse elétrico (Renwick, Kulkarni, Celaya). "No transformer or motor-specific datasets are listed." | https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ | 2008–2012 (bancos) | A |
| 24 | C-MAPSS: FD001 100/100 trajetórias, 1 condição, 1 modo (HPC); FD002 260/259, 6 condições, 1 modo; FD003 100/100, 1 condição, 2 modos (HPC e ventilador); FD004 248/249, 6 condições, 2 modos; 26 colunas (unidade, ciclo, 3 ajustes operacionais, 21 sensores); objetivo: RUL em ciclos; citação Saxena et al., PHM08, Denver, out. 2008. | https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data | 2008 | A |
| 25 | Saxena, Goebel, Simon, Eklund, "Damage propagation modeling for aircraft engine run-to-failure simulation", Int. Conf. PHM 2008, DOI 10.1109/PHM.2008.4711414; 1776 citações (Semantic Scholar). | https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/PHM.2008.4711414 | 2008 | M (metadado) |
| 26 | Função de pontuação do desafio C-MAPSS/PHM08 (transcrita): s = exp(−d/13) − 1 se d < 0; s = exp(d/10) − 1 se d ≥ 0; d = RUL prevista − RUL verdadeira; "penalizes more the errors that predict a RUL too late than too early", "as proposed in the original C-MAPSS evaluation campaign"; RMSE usada em conjunto; RUL máxima truncada em 125 ou 130 ciclos na literatura. | https://arxiv.org/abs/2104.05049 ; PDF https://arxiv.org/pdf/2104.05049 (p. 5) | 2021 | M (secundária fiel) |
| 27 | XJTU-SY: 15 rolamentos, 5 por condição: 2100 rpm/12 kN, 2250 rpm/11 kN, 2400 rpm/10 kN; vibração a 25,6 kHz, 32768 pontos (1,28 s) por amostragem, período 1 min; run-to-failure; "publicly available"; citar Wang, Lei, Li, Li, IEEE Trans. Reliability 69(1):401–412, 2020. | https://biaowang.tech/xjtu-sy-bearing-datasets/ ; https://api.crossref.org/works/10.1109/TR.2018.2882682 | 2020 | A |
| 28 | Busca na API do Zenodo por "stator insulation" aging dataset, por "partial discharge" datasets e por "twisted pair"/"magnet wire"/"turn insulation" aging: nenhum banco de envelhecimento acelerado de isolamento de enrolamento; resultados são artigos, dados de antenas para DP em GIS e formas de onda acústicas de DP (2026). | https://zenodo.org/api/records?q=%22stator%20insulation%22%20aging%20dataset&size=10 ; https://zenodo.org/api/records?q=%22partial%20discharge%22%20AND%20(dataset%20OR%20measurements)&size=10&type=dataset ; https://zenodo.org/api/records?q=(%22twisted%20pair%22%20OR%20%22magnet%20wire%22%20OR%20%22turn%20insulation%22)%20AND%20aging&size=10 | 2026 (consulta) | A (ausência verificada apenas no Zenodo) |
| 29 | Saxena, Celaya, Saha, Saha, Goebel, "Metrics for Offline Evaluation of Prognostic Performance", IJPHM 1(1), 2010, ISSN 2153-2648, DOI 10.36001/ijphm.2010.v1i1.1336, CC BY; 269 citações (Semantic Scholar). Crossref/Semantic Scholar registram ano 2021 (redigitalização), mas o cabeçalho do PDF traz "2010 001". | https://papers.phmsociety.org/index.php/ijphm/article/view/1336 ; https://api.crossref.org/works/10.36001/ijphm.2010.v1i1.1336 ; https://api.semanticscholar.org/graph/v1/paper/DOI:10.36001/ijphm.2010.v1i1.1336 ; PDF https://papers.phmsociety.org/index.php/ijphm/article/download/1336/324 | 2010 | A |
| 30 | Definições (Saxena 2010): PH "is defined as the difference between the time index i when the predictions first meet the specified performance criteria (based on data accumulated until time index i) and the time index for EoL"; "The choice of α depends on the estimate of time required to take a corrective action"; α-λ "is defined as a binary metric that evaluates whether the prediction accuracy at specific time instance tλ falls within specified α-bounds", com α expresso como percentagem da RUL real; RA "is defined as a measure of error in RUL prediction relative to the actual RUL r*(iλ) at a specific time index iλ"; Convergence "is a meta-metric defined to quantify the rate at which any metric (M) like accuracy or precision improves with time", medida pela distância ao centroide da área sob a curva; hierarquia PH → α-λ → RA/CRA → convergência; incorporação da massa de probabilidade dentro dos limites α (β = limiar mínimo de probabilidade). | PDF acima (PDF p. 8, 11, 13–16) | 2010 | A |
| 31 | Sankararaman & Goebel, "Uncertainty in Prognostics and Systems Health Management", IJPHM 6(4), 2015, DOI 10.36001/ijphm.2015.v6i4.2319: "it is almost practically impossible to precisely predict future events"; distinção frequentista × bayesiana; "only the Bayesian approach is applicable in the context of condition-based health management". | https://papers.phmsociety.org/index.php/ijphm/article/view/2319 | 2015 | A |
| 32 | Deep ensembles (Lakshminarayanan, Pritzel, Blundell, NIPS 2017): método "simple to implement, readily parallelizable, requires very little hyperparameter tuning, and yields high quality predictive uncertainty estimates"; incertezas "as good or better than approximate Bayesian NNs"; testado em dados fora da distribuição. | https://arxiv.org/abs/1612.01474 | 2017 | A |
| 33 | Dropout como aproximação bayesiana (Gal & Ghahramani, ICML 2016): conexão entre dropout e inferência bayesiana em processos gaussianos; melhora log-verossimilhança preditiva e RMSE. | https://arxiv.org/abs/1506.02142 | 2016 | A |
| 34 | Predição conforme (Angelopoulos & Bates, 2021): "explicit, non-asymptotic guarantees even without distributional assumptions or model assumptions"; conjuntos "guaranteed to contain the ground truth with a user-specified probability, such as 90%". | https://arxiv.org/abs/2107.07511 | 2021 | A |
| 35 | Khosravi, Nahavandi, Creighton, Atiya, "Comprehensive Review of Neural Network-Based Prediction Intervals and New Advances", IEEE Trans. Neural Networks 22(9):1341–1356, 2011, DOI 10.1109/TNN.2011.2162110 (referência para métricas de cobertura/largura de intervalos; texto integral não acessado). | https://api.crossref.org/works/10.1109/TNN.2011.2162110 | 2011 | M (metadado) |
| 36 | Nor, Pedapati, Muhammad, Leiva, "Overview of Explainable Artificial Intelligence for Prognostic and Health Management of Industrial Assets Based on PRISMA", Sensors 21(23):8020, 2021, DOI 10.3390/s21238020: revisão 2015–2021; "XAI offers dual advantages, where it is assimilated as a tool to execute PHM tasks and explain diagnostic and anomaly detection activities"; lacunas: envolvimento humano, métricas de avaliação, gestão de incerteza. | https://api.crossref.org/works/10.3390/s21238020 | 2021 | M (metadado + resumo) |
| 37 | MLOps (Google): nível 0 "every step is manual…", "lack of active performance monitoring"; nível 1 automação do pipeline de treinamento com "CT of the model in production"; nível 2 CI/CD; componentes: extração, análise, preparação, treino, avaliação, validação, serving, monitoramento; gatilhos de retreinamento: "On demand", "On a schedule", "On availability of new training data", "On model performance degradation", "On significant changes in the data distributions". | https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning | — | A (doc. de fornecedor) |
| 38 | Deriva (Evidently): data drift = "a change in the statistical properties and characteristics of the input data"; concept drift = mudança na relação entrada–alvo; prediction drift = mudança na distribuição das saídas; testes: Kolmogorov-Smirnov, qui-quadrado, Wasserstein, Jensen-Shannon, PSI; "statistically significant difference may not always be practically significant". | https://www.evidentlyai.com/ml-in-production/data-drift | — | A (doc. de fornecedor) |
| 39 | FAIR4RS v1.0 (Chue Hong, Katz, Barker et al.; RDA/FORCE11/ReSA), DOI 10.15497/RDA00068, publicado 24 mai 2022 (versão 1.0 de 16 mar 2022 na RDA), CC-BY-4.0; princípios: F1 (F1.1, F1.2), F2, F3, F4, A1 (A1.1, A1.2), A2, I1, I2, R1 (R1.1, R1.2), R2, R3 — p. ex. F1 "Software is assigned a globally unique and persistent identifier"; R1.1 "Software is given a clear and accessible license"; R1.2 "Software is associated with detailed provenance"; R3 "Software meets domain-relevant community standards". | https://zenodo.org/records/6623556 ; https://zenodo.org/api/records/6623556 ; PDF https://zenodo.org/api/records/6623556/files/FAIR4RS%20Principles%20Final%20Recommendation%20Zenodo.pdf/content (PDF p. 7) ; https://www.rd-alliance.org/group_output/fair-principles-for-research-software-fair4rs-principles/ | 2022 | A |
| 40 | GitHub–Zenodo: "Zenodo archives your repository and issues a new DOI each time you create a new GitHub release"; repositório deve ser público e ter licença. | https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content | — | A |
| 41 | SWHID (Software Heritage): sintaxe `swh:1:<type>:<hash>[;qualifiers]`, tipos `cnt`, `dir`, `rev`, `rel`, `snp`, hash SHA1 de 40 hex; identificadores intrínsecos "computed from the object itself, without having to rely on any third party"; qualificadores origin, visit, anchor, path, lines. | https://docs.softwareheritage.org/devel/swh-model/persistent-identifiers.html | — | A |
| 42 | JOSS: "a developer friendly, open access journal for research software packages", ISSN 2475-9066; exige licença OSI, "at least six months of public history", "evidence of releases, public issues/pull requests", "comprehensive testing", "clear documentation", software "feature-complete"; revisão pública em issues do GitHub; DOI Crossref; arquivamento em Portico. | https://joss.theoj.org/about | — | A |
| 43 | Sandve, Nekrutenko, Taylor, Hovig, "Ten Simple Rules for Reproducible Computational Research", PLOS Comput. Biol. 2013, DOI 10.1371/journal.pcbi.1003285: regras 1–10 (rastrear como cada resultado foi produzido; evitar manipulação manual; arquivar versões exatas de programas externos; versionar scripts; registrar resultados intermediários; anotar sementes aleatórias; guardar dados brutos das figuras; saída hierárquica; ligar afirmações textuais a resultados; acesso público a scripts, execuções e resultados). | https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003285 | 2013 | A |
| 44 | The Turing Way: "reproducible when the same analysis steps performed on the same dataset consistently produces the same answer"; "replicable when the same analysis performed on different datasets produces qualitatively similar answers"; "robust when the same dataset is subjected to different analysis workflows…"; generalizável = replicável + robusto. | https://book.the-turing-way.org/reproducible-research/overview/overview-definitions | — | A |
| 45 | CIGRE TB 858 "Asset health indices for equipment in existing substations", WG B3.48, 2021: metodologia genérica em oito passos (identificar ativos e níveis de revisão; FMEA; desempenho individual; indicadores de condição; coleta de dados de inspeção; avaliação da condição frente aos modos de falha; agregação em AHI; ações de mitigação); trata "potential methods for aggregation of health scores" e verificação de sanidade; usos: manutenção, reforma e substituição; "The need is then to have the capability to identify the time frames for these transition stages." | https://www.e-cigre.org/publications/detail/858-asset-health-indices-for-equipment-in-existing-substations.html | 2021 | A (resumo oficial; corpo da brochura não acessado) |
| 46 | Ofgem/DNOs, CNAIM v2.1 (01 abr 2021): três componentes regulatórios — Health Index (bandas HI1–HI5), Criticality Index (C1–C4) e Risk Index; Tabela 5: HI1 ≥0,5 <3; HI2 ≥3 <5,5; HI3 ≥5,5 <6,5; HI4 ≥6,5 <8; HI5 ≥8 ≤15; bandas traduzidas em PoF; Current Health Score em dois passos (Initial Health Score por idade/vida esperada com modelo exponencial; modificação por condição observada/medida e Reliability Modifier); Future Health Score = Current Health Score × e^((β2/r)·t), limitado a 15; risco monetizado por banda HI×C em £ (2020/21). | https://www.ofgem.gov.uk/sites/default/files/docs/2021/04/dno_common_network_asset_indices_methodology_v2.1_final_01-04-2021.pdf (p. 21–23, 29, Tabela 5; §6.1.10 p. 40; Tabela 238 p. 202–203) | 2021 | A |
| 47 | GE Vernova APM: "APM Health" (monitoramento de condição), "SmartSignal" (analítica preditiva) para "remotely monitor assets, dispatch maintenance in advance, plan for spare parts, and even avoid catastrophic failures"; benefícios declarados: "2-6% increased availability", "3-40% EH&S incident reduction", "10-40% reduction in reactive maintenance", "5-10% inventory cost reduction". | https://www.gevernova.com/software/products/asset-performance-management | 2026 (acesso) | M (marketing) |
| 48 | AVEVA Predictive Analytics: "Identify asset anomalies weeks or months before failure occurs"; "time-to-failure forecasts that provide an estimated time until a failure is likely to occur"; "recommended actions from the AVEVA Asset Library… more than 22,000 hours of experience"; casos: "99% plant reliability obtained", "Up to $37 Million CAD efficiency savings… within the first 24 months", "3,000 annual maintenance hours eliminated", "10% reduction in recurring maintenance costs"; "no-code environment". | https://www.aveva.com/en/products/predictive-analytics/ | 2026 (acesso) | M (marketing) |
| 49 | AVEVA PI System (ex-OSIsoft): "collect, store, normalize, enrich, and visualize real-time operations data" com "sub-second granularity"; Asset Framework ("configure reusable asset models, events and analytics"); PI Vision; "75% of the world's crude oil, natural gas, and liquids are produced with AVEVA PI System"; caso TotalEnergies "direct savings around 1.5 million Euros". | https://www.aveva.com/en/products/aveva-pi-system/ | 2026 (acesso) | M (marketing) |
| 50 | ABB Ability Digital Powertrain Insights ("formerly called Condition Monitoring"): "predictive maintenance software platform for industrial powertrains"; "Real-time asset health dashboards", "Analytics-driven anomaly detection", "Condition and trend analysis", "Centralized visibility across sites and fleets"; ABB Ability Digital Powertrain: "detect emerging risks early, assess failure probability, and act before downtime impacts production". (A URL do Smart Sensor entregou esta página; sinalização em semáforo e vida remanescente não constam do texto lido.) | https://new.abb.com/motors-generators/service/advanced-services/smart-sensor (conteúdo servido: Digital Powertrain Insights) | 2026 (acesso) | M (marketing) |
| 51 | Siemens Senseye Predictive Maintenance: "Holistic asset health visibility" — "a unified view of asset condition and risk across your operation"; "Detect early signs of failure across assets and sites to prevent unexpected stoppages"; ajuda a "decide where to act first"; sem números de ROI nem RUL na página. | https://siemens.com/global/en/products/services/digital-enterprise-services/analytics-artificial-intelligence-services/predictive-services/senseye-predictive-maintenance.html | 2026 (acesso) | M (marketing) |
| 52 | Olivas: versão declarada 4.0.0-beta; licença Apache-2.0; `Feature.RELIABILITY_MC` com tier "commercial"; `run_monte_carlo(..., seed=42)` em confiabilidade e `run_monte_carlo(..., random_seed=None)` em arc flash; `generate_html_dashboard` e `export_csv` no painel de avaliação; base IEEE 493-2007; dependências declaradas em `requirements.txt` (8 linhas: PySide6, matplotlib, numpy, pytest, pydantic, PyYAML, openpyxl e um SDK de API externa); CI com matriz Python 3.11–3.13; 247 arquivos em `tests/`; inexistem `pyproject.toml`, `CITATION.cff` e `docs/research/`. | [REPO: app/core/version.py:1959-1960; LICENSE.txt:1-5; app/commercial/feature_gates.py:67,73,88; app/postprocessor/reliability_monte_carlo.py:243,251,290; app/postprocessor/arc_flash_monte_carlo.py:288,293,319; app/postprocessor/equipment_eval_dashboard.py:141,302; app/postprocessor/reliability.py:17,75; requirements.txt:1-8; .github/workflows/test.yml:19] [CÁLCULO PRÓPRIO: `ls tests | wc -l` = 247; `ls pyproject.toml CITATION*` sem resultado] | 2026 | A |

---

## 3. Números-chave

- **Seis** blocos funcionais ISO 13374/OSA-CBM; siglas DA, DM, SD, HA, PA, AG verificadas no esquema OSA-CBM 3.3.1 (2010) [LITERATURA: MIMOSA; XSD].
- ISO 13381-1: edição 2015 retirada em **02.09.2025**; edição **2025** vigente [NORMA: catálogo EVS].
- ProgPy **v1.8** (maio 2025), DOI 10.5281/ZENODO.8097013 [LITERATURA].
- pymoo **0.6.2**; NSGA-II (2002) e NSGA-III disponíveis [LITERATURA].
- NASA PCoE: **21** bancos; IGBT: **6** dispositivos; C-MAPSS: FD001 100/100, FD002 260/259, FD003 100/100, FD004 248/249 trajetórias; **21** sensores + 3 ajustes; **0** bancos de motor/transformador [LITERATURA].
- XJTU-SY: **15** rolamentos, **3** condições, **25,6 kHz**, 32768 pontos/1,28 s a cada 1 min [LITERATURA].
- Pontuação PHM08: constantes **13** (previsão antecipada) e **10** (previsão atrasada) na exponencial assimétrica; truncamento de RUL em **125–130** ciclos [LITERATURA: Chaoub 2021, p. 5 — secundária].
- Saxena 2010: **4** métricas hierárquicas (PH, α-λ, RA/CRA, convergência); parâmetros α (erro admissível), λ (fração da vida entre tP e EoL), β (probabilidade mínima) [LITERATURA: PDF p. 8, 13–16].
- Predição conforme: cobertura especificada pelo usuário, p. ex. **90%**, sem hipóteses distribucionais [LITERATURA: arXiv 2107.07511].
- MLOps: **3** níveis (0, 1, 2); **5** gatilhos de retreinamento [LITERATURA: Google]; **5** testes de deriva citados (KS, qui-quadrado, Wasserstein, JS, PSI) [LITERATURA: Evidently].
- FAIR4RS: **17** enunciados (11 princípios + 6 subprincípios), v1.0 de 2022 [LITERATURA: PDF p. 7].
- JOSS: **≥ 6 meses** de histórico público; licença OSI; DOI Crossref [LITERATURA].
- CNAIM: Health Score **0,5–15**; **5** bandas HI; **4** bandas de criticidade; Future Health Score limitado a **15** [LITERATURA: CNAIM v2.1, Tabela 5 p. 29; §6.1.10].
- CIGRE TB 858: **8** passos metodológicos [LITERATURA: resumo oficial].
- Fornecedores (declarações não auditadas): GE Vernova "2-6%" disponibilidade, "10-40%" menos manutenção reativa; AVEVA "$37 Million CAD" em 24 meses, "3,000" horas/ano; PI System "75%" do petróleo/gás/líquidos mundiais; TotalEnergies "1.5 million Euros" [LITERATURA: páginas de produto; confiança M].
- Olivas: versão **4.0.0-beta**; **247** arquivos de teste; CI em Python **3.11–3.13**; semente **42** padrão no MC de confiabilidade [REPO; CÁLCULO PRÓPRIO].

---

## 4. Controvérsias e limites de evidência

1. **Nomes dos blocos ISO 13374.** O texto integral da ISO 13374-1/-2 não pôde ser lido (iso.org bloqueado; catálogo EVS só traz o escopo). As siglas DA/DM/SD/HA/PA/AG são verificadas no XSD do OSA-CBM 3.3.1; a expansão nominal ("Data Acquisition… Advisory Generation") é a do enunciado da tarefa e da prática corrente, mas fica sem citação de cláusula: [NORMA: ISO 13374-1:2003, cláusula — [INSERIR CITAÇÃO]]. Há também discrepância de versão (3.2.1 × 3.3.1) entre páginas oficiais da MIMOSA.
2. **ISO 13381-1:2025.** A troca de "General guidelines" (2015) por "General guidelines and requirements" (2025) sugere requisitos verificáveis, mas o texto não foi acessado; o estado das Partes 2–4 após 2025 não foi verificado [HIPÓTESE: permanecem vigentes até revisão].
3. **Ausência de banco público de envelhecimento de isolamento MT.** A ausência foi verificada apenas no repositório NASA PCoE e em três consultas ao Zenodo; IEEE DataPort, Mendeley Data e repositórios institucionais não foram consultados com sucesso (Anexo A). Conclusão robusta apenas como "não localizado nas fontes consultadas". O artigo 02 (Jensen 2018) usa três estatores próprios sem dispersão estatística [FATO: artigo 02, fichamento §"n = 3"], reforçando a escassez.
4. **Pontuação PHM08.** As constantes 13/10 e a forma exponencial provêm de fonte secundária (Chaoub et al. 2021) que as atribui ao desafio original; o artigo de Saxena et al. (2008) teve apenas metadados acessados. Além disso, a assimetria (penalizar mais previsões atrasadas) é uma escolha de política de risco do desafio, não uma propriedade universal — para isolamento de motores MT, o custo relativo de "atrasar" vs "antecipar" deve ser derivado do custo de parada (ver `c_level_demanda_rul.md`, §5.3) [INFERÊNCIA].
5. **Ano de Saxena et al. (IJPHM).** Crossref e Semantic Scholar registram 2021 (redigitalização do periódico), o PDF traz 2010; citar 2010 com o DOI atual.
6. **Bayesiano × frequentista × conforme.** Sankararaman & Goebel (2015) defendem que só a abordagem bayesiana se aplica a CBM; deep ensembles e dropout são aproximações práticas sem garantia formal; a predição conforme oferece garantia de cobertura marginal sob hipótese de intercambiabilidade, que séries temporais de degradação de um único ativo violam em geral [INFERÊNCIA a partir das definições lidas]. A escolha deve ser declarada e as coberturas empíricas reportadas.
7. **XAI.** A revisão de 2021 indica "perdas de desempenho mínimas" e "implementação industrial substancial", mas reconhece que métricas de avaliação de explicações e a integração com incerteza são lacunas — ou seja, não há padrão de avaliação de explicabilidade em PHM [LITERATURA: Sensors 2021, resumo].
8. **Gêmeo digital.** O NIST registra que "there exist a variety of definitions of digital twins, inconsistent terminologies, and no standardized procedures" [LITERATURA: NIST AMS 400-2, PDF p. 7–8]. A ISO 23247 é de manufatura; a ISO/IEC 30173 é genérica; a Digital Twin Consortium não pôde ser acessada. Chamar o módulo de RUL de "gêmeo digital" exige sincronização com o ativo (dados de campo), inexistente num MVP baseado só em simulação [INFERÊNCIA].
9. **Benefícios de fornecedores.** Todos os números de GE Vernova, AVEVA, ABB e Siemens são declarações de marketing sem metodologia; devem ser citados como tal (confiança M) e nunca como evidência de eficácia do módulo Olivas.
10. **Transferência de AHI de T&D para motores MT em O&G.** CIGRE TB 858 (subestações) e CNAIM (redes de distribuição do Reino Unido) fornecem a estrutura (score → banda → PoF → criticidade → risco monetizado), mas as curvas, os modificadores e os pesos são específicos de ativos de rede; a aplicação a motores é [HIPÓTESE] a calibrar.
11. **Publicação em JOSS × modelo comercial.** O Olivas é Apache-2.0 (licença OSI), mas possui gating comercial por tier [REPO: app/commercial/feature_gates.py:67-96]; JOSS exige software "feature-complete" com histórico público — publicar apenas o módulo de RUL como pacote separado evita a tensão [INFERÊNCIA].
12. **Licença do ProgPy.** A documentação descreve software NASA "AS IS" com cláusula de indenização; a compatibilidade com Apache-2.0 e com distribuição comercial não foi verificada [HIPÓTESE: usar ProgPy como referência metodológica e dependência opcional, não como base do núcleo].
13. **MLOps e deriva.** As fontes são documentação de fornecedores (Google, Evidently); não há norma que fixe limiares de deriva; a própria fonte alerta que significância estatística não implica relevância prática.
14. **Fontes bloqueadas.** ACM (badging de artefatos), Nature (FAIR4RS versão de periódico), MDPI (texto integral da revisão XAI), Software Heritage (site institucional), Bentley (AssetWise), Siemens SIDRIVE IQ e Digital Twin Consortium não puderam ser lidos (Anexo A); as afirmações correspondentes ficam sem citação primária ou apoiadas em fontes alternativas.

---

## 5. Implicações para o módulo RUL de isolamento de motores MT (Olivas) e para o discurso C-Level

### 5.1 Arquitetura de referência: mapear DA→AG sobre o que existe

| Bloco OSA-CBM (sigla verificada) | Conteúdo no MVP Olivas | Lastro |
|---|---|---|
| DA — aquisição | Fase 1: saídas de simulação ATP/EMTP de manobras de VCB (pico, dv/dt, energia, espectro) e de partidas/afundamentos (OpenDSS); Fase 2: séries de campo (medições do programa de monitoramento). | [FATO: doc A — camada digital extrai pico, dv/dt, energia e espectro; fichamento A]; [FATO: doc B — V_inrush 0,755 pu sem shedding]; [NORMA: ISO 17359:2018 para o programa de monitoramento] |
| DM — manipulação | Extração de características por evento (contadores por classe de severidade, I²t por partida, estatísticas de sobretensão). | [FATO: artigo 05, fichamento §4 — contagem de eventos por classe]; [REPO: app/postprocessor/motor_starting.py:481 `analyze_motor_starting`, conforme mapa] |
| SD — detecção de estado | Regras PASS/WARN/FAIL já existentes (`RuleEngine`, `RuleSeverity`). | [REPO: app/postprocessor/coord_rules.py:120-124, conforme mapa `confiabilidade_eval_montecarlo.md`] |
| HA — avaliação de saúde | Índice de saúde (HI) com propriedades de monotonicidade, tendenciabilidade e prognosticabilidade; FMMEA primeiro para escolher mecanismos (erosão por DP, térmico, mecânico). | [FATO: artigo 13, p. 6 — três propriedades do HI]; [FATO: artigo 07, p. 6–7 — FMMEA] |
| PA — prognóstico | RUL com distribuição (P05/P50/P95) por Monte Carlo ou filtro (EKF/UKF/PF), no padrão dos MCs existentes (semente, `n_samples`, percentis). | [REPO: app/postprocessor/arc_flash_monte_carlo.py:288-319]; [FATO: artigo 02 — EKF sobre indicador de isolamento]; [LITERATURA: ProgPy — UKF/PF/MC] |
| AG — recomendação | Ação recomendada, custo evitado, janela de intervenção; bloco de limitações e cabeçalho de auditoria SHA256. | [REPO: app/postprocessor/audit_trail.py:135-161, 338-424, conforme mapa]; [LITERATURA: AVEVA — "recommended actions"; CNAIM — risco monetizado] |

[INFERÊNCIA] Nomear os módulos e as estruturas de dados com as siglas DA…AG (p. ex., `InsulationStressInputs` = DA/DM; `HealthAssessment` = HA; `RulPrognosisResult` = PA; `Advisory` = AG) torna a arquitetura auditável contra a ISO 13374 sem exigir conformidade formal ao OSA-CBM (que exige as estruturas de dados e interfaces da especificação [LITERATURA: MIMOSA]).

### 5.2 Pilha de bibliotecas (compatível com Apache-2.0 do repositório)

- Núcleo determinístico e MC: `numpy` (já declarado) [REPO: requirements.txt]; filtros EKF/UKF/PF: FilterPy (KF/EKF/UKF, reamostragem de partículas) [LITERATURA]; ProgPy como referência de API (estimador → preditor → `UncertainData`) e para replicar métricas α-λ/PH/CRA/PoS [LITERATURA] — dependência opcional dada a licença NASA (§4, item 12).
- Sobrevivência com censura (frotas de motores com poucos eventos): lifelines [LITERATURA]; otimização multiobjetivo (trade-off acurácia × custo de intervenção, coerente com o doc B): pymoo NSGA-II/III [LITERATURA; FATO: doc B — NSGA-II vs NSGA-III].
- Aprendizado de máquina: scikit-learn (BSD) para modelos de referência (regressão, GBM), tsai/PyTorch apenas se houver séries de campo suficientes [LITERATURA]; SHAP (MIT) para explicações [LITERATURA].
- Todas as licenças listadas (BSD, MIT) são compatíveis com Apache-2.0 [INFERÊNCIA a partir das licenças declaradas nas páginas acessadas; verificação jurídica pendente].

### 5.3 Validação sem banco de isolamento MT

1. **Validação de método** em bancos públicos com protocolo padronizado: NASA IGBT (6 dispositivos, envelhecimento térmico acelerado — fisicamente próximo de degradação térmica de isolamento) e C-MAPSS FD001–FD004 (métricas de referência e comparabilidade com a literatura) [LITERATURA: NASA PCoE; data.nasa.gov]; rolamentos (XJTU-SY/FEMTO) só para o pipeline de HI [LITERATURA].
2. **Validação física** no domínio: geração de trajetórias sintéticas de degradação a partir das grandezas de estresse simuladas no doc A (pico e dv/dt por manobra; energia absorvida) e das partidas do doc B, com modelo incremental de dano declarado como hipótese — o doc A não apresenta o modelo incremental nem quantifica reignições [FATO: doc A, fichamento — ausências]; a premissa do usuário "5 a 7 reignições por ciclo" não consta do doc A e deve ser tratada como [HIPÓTESE do usuário] (ver `fisica_surtos_vcb_isolamento.md`).
3. **Métricas obrigatórias no relatório** (cada uma com parâmetro declarado): RMSE e pontuação assimétrica (com constantes derivadas do custo de parada, não necessariamente 13/10) [LITERATURA: Chaoub 2021 — secundária; Saxena 2008 — metadado]; PH(α) com α escolhido pelo tempo de ação corretiva (parada programada do motor) [LITERATURA: Saxena 2010, PDF p. 14]; α-λ com β (massa de probabilidade) [PDF p. 11, 15]; RA/CRA; convergência [PDF p. 16]; cobertura empírica dos intervalos P05–P95 (PICP) e largura média [LITERATURA: Khosravi 2011 — metadado; [INSERIR CITAÇÃO de página]].
4. **Incerteza**: declarar explicitamente a abordagem (bayesiana/filtro; ensemble; conforme) e reportar cobertura empírica [LITERATURA: Sankararaman 2015; Lakshminarayanan 2017; Angelopoulos & Bates 2021].
5. **Escala de qualidade de evidência**: reproduzível (mesmos dados, mesma análise, semente fixa) → replicável (outros motores/plantas) → robusta (outro estimador) [LITERATURA: The Turing Way].

### 5.4 Reprodutibilidade e artefato computacional de tese

Estrutura mínima [INFERÊNCIA a partir de FAIR4RS, Sandve 2013, JOSS e GitHub–Zenodo]:
- Pacote separado `olivas-rul` (ou submódulo) com `pyproject.toml`, `CITATION.cff`, `LICENSE` (Apache-2.0 já existente [REPO: LICENSE.txt]), `CHANGELOG` (já existe [REPO: CHANGELOG.md]) e versão semântica — atende F1/F1.2, R1.1 [LITERATURA: FAIR4RS].
- Release no GitHub → DOI Zenodo por versão (F1, A1) [LITERATURA: GitHub Docs]; depósito no Software Heritage com SWHID do snapshot/release citado na tese (identificador intrínseco, independente de terceiros) [LITERATURA: SWHID].
- Sementes fixas em todo MC (já é padrão: `seed=42`, `random_seed`) [REPO: reliability_monte_carlo.py:251; arc_flash_monte_carlo.py:293] — regra 6 de Sandve; dados brutos atrás de cada figura (regra 7); ambiente travado (`requirements` com versões exatas ou lockfile — hoje apenas limites inferiores [REPO: requirements.txt:1-8]) — regra 3.
- Cabeçalho de auditoria com SHA256 dos insumos e versão do software já existe [REPO: app/postprocessor/audit_trail.py:135-161, conforme mapa]; corrigir timestamp para UTC com fuso (mapa aponta `datetime.now()` sem fuso, l. 320) — provenance R1.2.
- Testes e CI já existem (247 arquivos; matriz 3.11–3.13) [REPO; CÁLCULO PRÓPRIO]; documentar cobertura e adicionar testes de regressão numérica para as métricas de prognóstico (valores de referência em C-MAPSS).
- Cartões de dados (data cards) para cada banco usado, com DOI/citação obrigatória (XJTU-SY exige citar Wang et al. 2020; NASA indica citação por banco) [LITERATURA].
- Candidatura a JOSS somente após ≥ 6 meses de histórico público e documentação/testes completos [LITERATURA: JOSS].

### 5.5 XAI e MLOps no MVP

- Explicação por fatores dominantes (SHAP para modelos de dados; sensibilidade/Sobol ou decomposição de dano por mecanismo para modelos físicos) apresentada junto ao RUL, nunca isolada [LITERATURA: SHAP; Sensors 2021 — lacunas de avaliação].
- Deriva: no MVP baseado em simulação, monitorar deriva dos insumos (distribuição de sobretensões e partidas por período) com KS/PSI e registrar "estado de dados" no painel; definir gatilhos de recalibração (novos dados de campo; degradação de PH/α-λ em back-testing) [LITERATURA: Google; Evidently] — nível 0→1 de maturidade é suficiente para tese; nível 2 é roadmap comercial [INFERÊNCIA].

### 5.6 Gêmeo digital: posicionamento honesto

Chamar o MVP de "modelo de prognóstico baseado em simulação" e reservar "gêmeo digital" para a fase com sincronização de dados do ativo (DCDCE → Core Entity → User Entity, ISO 23247-2) [LITERATURA: NIST AMS 400-2]. Citar ISO 23247-1:2021 e ISO/IEC 30173:2023 pelas páginas de catálogo acessadas; a definição integral só via NIST (transcrição do DIS) — [NORMA: ISO 23247-1:2021, cláusula 3 — [INSERIR CITAÇÃO] após acesso ao texto].

### 5.7 O que o painel executivo de RUL deve mostrar (conteúdo mínimo consolidado)

| Elemento | Definição/forma | Lastro |
|---|---|---|
| Banda de saúde (AHI) por motor | Score contínuo → 5 bandas (analogia HI1–HI5) com critérios publicados; agregação declarada | [LITERATURA: CNAIM Tabela 5; CIGRE TB 858 — agregação e sanidade] |
| Probabilidade de falha no horizonte | PoF(t) derivada da banda/score ou do modelo de RUL; horizonte = próximo ciclo de parada | [LITERATURA: CNAIM §4.3–4.4]; [REPO: padrão `prob_failure_before_horizon` proposto no mapa] |
| Criticidade/consequência | Bandas C1–C4 pela consequência (produção, segurança, ambiente) | [LITERATURA: CNAIM — Criticality Index] |
| Risco (semáforo) | Risco = PoF × consequência, monetizado por banda; cor por faixa de risco, não por saúde isolada | [LITERATURA: CNAIM — risco monetizado, Tabela 238] [INFERÊNCIA: semáforo sobre risco] |
| RUL com intervalo | P05/P50/P95 em unidades de negócio (meses, manobras, partidas) e horizonte de prognóstico PH(α) | [LITERATURA: Saxena 2010; ProgPy `UncertainData`]; [FATO: artigo 08 — exemplo do que falta quando só há HI] |
| Tendência e convergência | Trajetória do HI e estreitamento do intervalo ao longo do tempo | [LITERATURA: Saxena 2010 — convergência; FATO: artigo 02 — RUL é trajetória] |
| Ação recomendada e custo evitado | Ação (reapertar programa de monitoramento, aplicar snubber, reprogramar partidas, reparar) com custo evitado estimado e janela | [LITERATURA: AVEVA — "recommended actions"; GE — "dispatch maintenance in advance"]; [FATO: doc A — snubber reduz pico de −30,24 kV para 6,35 kV na fase A, Tabela III]; `c_level_demanda_rul.md` §5.3 |
| Prioridade de atenção | Ordenação de frota por risco para "decidir onde agir primeiro" | [LITERATURA: Senseye] |
| Estado de dados e deriva | Cobertura de sensores/simulações, última atualização, alertas de deriva | [LITERATURA: Evidently; Google] |
| Identidade do cálculo | Versão, hash SHA256 dos insumos, normas aplicadas, responsável técnico | [REPO: audit_trail.py — `AuditHeader`, conforme mapa] |
| Explicação | Fatores dominantes do RUL (mecanismo/variável) | [LITERATURA: SHAP; Sensors 2021] |
| Limitações declaradas | Bloco de limitações por chave | [REPO: audit_trail.py `KNOWN_LIMITATIONS`, conforme mapa] |

### 5.8 Mensagens para o discurso C-Level (cada uma com lastro)

1. "O módulo segue a cadeia funcional da ISO 13374 usada pelos sistemas de CBM industriais (OSA-CBM/MIMOSA) e reporta RUL com intervalo, não um número único" [LITERATURA: MIMOSA; Saxena 2010; Sankararaman 2015].
2. "As métricas de acerto são as do NASA/PHM Society (horizonte de prognóstico, α-λ, acurácia relativa), com parâmetros ligados ao tempo de parada programada" [LITERATURA: Saxena 2010, PDF p. 14].
3. "A saúde do ativo é apresentada como índice em bandas e risco monetizado, no mesmo formato que reguladores e CIGRE usam para ativos elétricos" [LITERATURA: CNAIM; CIGRE TB 858].
4. "Não existe banco público de envelhecimento de isolamento de motores MT; a validação inicial é física (simulação) e metodológica (bancos NASA), e a validação de campo é a etapa comercial" [LITERATURA: NASA PCoE; Zenodo].
5. "Código, dados sintéticos e resultados terão DOI e identificador permanente; qualquer número do painel é reproduzível com semente e hash" [LITERATURA: FAIR4RS; GitHub–Zenodo; SWHID]; [REPO: audit_trail; MCs com semente].
6. "Fornecedores de APM prometem 2–6% de disponibilidade e 10–40% menos manutenção reativa; são declarações de marketing, e o módulo Olivas se diferencia por auditabilidade e física explícita da manobra (VCB, snubber) e da partida (N-1)" [LITERATURA: GE Vernova — confiança M]; [FATO: doc A; doc B].

### 5.9 Lacunas a preencher (ordem sugerida)

1. Acesso ao texto da ISO 13374-1 (cláusulas dos seis blocos) e da ISO 13381-1:2025 (requisitos) — [INSERIR CITAÇÃO].
2. Texto integral de Saxena et al. (2008) para a pontuação PHM08 (constantes 13/10) — [INSERIR CITAÇÃO].
3. Texto integral de Khosravi et al. (2011) para PICP/MPIW — [INSERIR CITAÇÃO].
4. Definição de gêmeo digital na cláusula 3 da ISO 23247-1:2021 e na ISO/IEC 30173:2023 — [INSERIR CITAÇÃO].
5. Corpo da CIGRE TB 858 (métodos de agregação) — [INSERIR CITAÇÃO].
6. Verificação de licença do ProgPy para redistribuição — [INSERIR CITAÇÃO].
7. Consulta a IEEE DataPort/Mendeley Data para bancos de envelhecimento de isolamento — pendente (Anexo A).

---

## 6. Referências (ABNT)

ANGELOPOULOS, A. N.; BATES, S. **A gentle introduction to conformal prediction and distribution-free uncertainty quantification**. arXiv:2107.07511, 2021 (rev. 2022). Disponível em: https://arxiv.org/abs/2107.07511. Acesso em: 2 set. 2026.

AVEVA. **AVEVA PI System**. Disponível em: https://www.aveva.com/en/products/aveva-pi-system/. Acesso em: 2 set. 2026.

AVEVA. **AVEVA Predictive Analytics**. Disponível em: https://www.aveva.com/en/products/predictive-analytics/. Acesso em: 2 set. 2026.

ABB. **ABB Ability Digital Powertrain Insights**. Disponível em: https://new.abb.com/motors-generators/service/advanced-services/smart-sensor. Acesso em: 2 set. 2026.

BLANK, J.; DEB, K. pymoo: multi-objective optimization in Python. **IEEE Access**, v. 8, p. 89497–89509, 2020. DOI: 10.1109/ACCESS.2020.2990567. Metadados: https://api.crossref.org/works/10.1109/ACCESS.2020.2990567; documentação: https://pymoo.org/. Acesso em: 2 set. 2026.

CHAOUB, A.; VOISIN, A.; CERISARA, C.; IUNG, B. **Learning representations with end-to-end models for improved remaining useful life prognostics**. arXiv:2104.05049, 2021. Disponível em: https://arxiv.org/abs/2104.05049; PDF: https://arxiv.org/pdf/2104.05049. Acesso em: 2 set. 2026.

CHUE HONG, N. P.; KATZ, D. S.; BARKER, M. et al. **FAIR Principles for Research Software (FAIR4RS Principles)**. Version 1.0. Research Data Alliance, 2022. DOI: 10.15497/RDA00068. Disponível em: https://zenodo.org/records/6623556; https://www.rd-alliance.org/group_output/fair-principles-for-research-software-fair4rs-principles/. Acesso em: 2 set. 2026.

CIGRE. **Asset health indices for equipment in existing substations**. Technical Brochure 858, WG B3.48. Paris: CIGRE, 2021. Disponível em: https://www.e-cigre.org/publications/detail/858-asset-health-indices-for-equipment-in-existing-substations.html. Acesso em: 2 set. 2026.

DEB, K.; PRATAP, A.; AGARWAL, S.; MEYARIVAN, T. A fast and elitist multiobjective genetic algorithm: NSGA-II. **IEEE Transactions on Evolutionary Computation**, v. 6, n. 2, p. 182–197, 2002. DOI: 10.1109/4235.996017. Metadados: https://api.crossref.org/works/10.1109/4235.996017. Acesso em: 2 set. 2026.

EVIDENTLY AI. **What is data drift in ML, and how to detect and handle it**. Disponível em: https://www.evidentlyai.com/ml-in-production/data-drift. Acesso em: 2 set. 2026.

GAL, Y.; GHAHRAMANI, Z. **Dropout as a Bayesian approximation: representing model uncertainty in deep learning**. arXiv:1506.02142, 2015 (ICML 2016). Disponível em: https://arxiv.org/abs/1506.02142. Acesso em: 2 set. 2026.

GE VERNOVA. **Asset Performance Management (APM)**. Disponível em: https://www.gevernova.com/software/products/asset-performance-management. Acesso em: 2 set. 2026.

GITHUB. **Referencing and citing content**. GitHub Docs. Disponível em: https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content. Acesso em: 2 set. 2026.

GOOGLE CLOUD. **MLOps: continuous delivery and automation pipelines in machine learning**. Cloud Architecture Center. Disponível em: https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning. Acesso em: 2 set. 2026.

IEEE. **IEEE Std 1856-2017 — IEEE Standard Framework for Prognostics and Health Management of Electronic Systems**. New York: IEEE, 2017. DOI: 10.1109/IEEESTD.2017.8227036. Metadados: https://api.crossref.org/works/10.1109/IEEESTD.2017.8227036. Acesso em: 2 set. 2026.

ISO. **ISO 13374-1:2003 — Condition monitoring and diagnostics of machines — Data processing, communication and presentation — Part 1: General guidelines**. Catálogo EVS: https://www.evs.ee/en/iso-13374-1-2003. Acesso em: 2 set. 2026.

ISO. **ISO 13374-2:2007 — … Part 2: Data processing**. Catálogo EVS: https://www.evs.ee/en/iso-13374-2-2007. Acesso em: 2 set. 2026.

ISO. **ISO 13381-1:2015 — Condition monitoring and diagnostics of machines — Prognostics — Part 1: General guidelines** (retirada em 02.09.2025). Catálogo EVS: https://www.evs.ee/en/iso-13381-1-2015. Acesso em: 2 set. 2026.

ISO. **ISO 13381-1:2025 — Condition monitoring and diagnostics of machine systems — Prognostics — Part 1: General guidelines and requirements**. Catálogo EVS: https://www.evs.ee/en/iso-13381-1-2025. Acesso em: 2 set. 2026.

ISO. **ISO 17359:2018 — Condition monitoring and diagnostics of machines — General guidelines**. Catálogo EVS: https://www.evs.ee/en/iso-17359-2018. Acesso em: 2 set. 2026.

ISO. **ISO 23247-1:2021 — Automation systems and integration — Digital twin framework for manufacturing — Part 1: Overview and general principles**. Catálogo EVS: https://www.evs.ee/en/iso-23247-1-2021. Acesso em: 2 set. 2026.

ISO. **ISO 55000:2024 — Asset management — Vocabulary, overview and principles**. Catálogo EVS: https://www.evs.ee/en/iso-55000-2024. Acesso em: 2 set. 2026.

ISO/IEC. **ISO/IEC 30173:2023 — Digital twin — Concepts and terminology**. Catálogo EVS: https://www.evs.ee/en/iso-iec-30173-2023. Acesso em: 2 set. 2026.

JOURNAL OF OPEN SOURCE SOFTWARE. **About JOSS**. Disponível em: https://joss.theoj.org/about. Acesso em: 2 set. 2026.

KHOSRAVI, A.; NAHAVANDI, S.; CREIGHTON, D.; ATIYA, A. F. Comprehensive review of neural network-based prediction intervals and new advances. **IEEE Transactions on Neural Networks**, v. 22, n. 9, p. 1341–1356, 2011. DOI: 10.1109/TNN.2011.2162110. Metadados: https://api.crossref.org/works/10.1109/TNN.2011.2162110. Acesso em: 2 set. 2026.

LABBE, R. R. **FilterPy documentation**. Disponível em: https://filterpy.readthedocs.io/en/latest/. Acesso em: 2 set. 2026.

LAKSHMINARAYANAN, B.; PRITZEL, A.; BLUNDELL, C. **Simple and scalable predictive uncertainty estimation using deep ensembles**. arXiv:1612.01474, 2016 (NIPS 2017). Disponível em: https://arxiv.org/abs/1612.01474. Acesso em: 2 set. 2026.

LIFELINES. **lifelines: survival analysis in Python**. Documentação. DOI: 10.5281/zenodo.805993. Disponível em: https://lifelines.readthedocs.io/en/latest/. Acesso em: 2 set. 2026.

LUNDBERG, S. M. et al. **SHAP (SHapley Additive exPlanations)**. Repositório e documentação. Disponível em: https://github.com/shap/shap; https://shap.readthedocs.io/en/latest/. Acesso em: 2 set. 2026.

MIMOSA. **MIMOSA OSA-CBM**. Disponível em: https://www.mimosa.org/mimosa-osa-cbm/. Acesso em: 2 set. 2026.

MIMOSA. **Specifications**. Disponível em: https://www.mimosa.org/specifications/. Acesso em: 2 set. 2026.

MIMOSA. **OSA-CBM V3.3.1 XML Schema** (cópia pública em repositório GitHub PredixDev/ext-interface). Disponível em: https://raw.githubusercontent.com/PredixDev/ext-interface/master/ext-model/src/main/resources/META-INF/schemas/osa/schema1.xsd. Acesso em: 2 set. 2026.

NASA. **PCoE Data Set Repository**. Intelligent Systems Division. Disponível em: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/. Acesso em: 2 set. 2026.

NASA. **CMAPSS Jet Engine Simulated Data**. data.nasa.gov. Disponível em: https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data. Acesso em: 2 set. 2026.

NASA. **ProgPy — Prognostics Python Packages**, v1.8, 2025. DOI: 10.5281/ZENODO.8097013. Disponível em: https://nasa.github.io/progpy/; https://nasa.github.io/progpy/prog_algs_guide.html. Acesso em: 2 set. 2026.

NOR, A. K. M.; PEDAPATI, S. R.; MUHAMMAD, M.; LEIVA, V. Overview of explainable artificial intelligence for prognostic and health management of industrial assets based on PRISMA. **Sensors**, v. 21, n. 23, art. 8020, 2021. DOI: 10.3390/s21238020. Metadados: https://api.crossref.org/works/10.3390/s21238020. Acesso em: 2 set. 2026.

OFGEM; DISTRIBUTION NETWORK OPERATORS. **DNO Common Network Asset Indices Methodology**, v. 2.1, 1 abr. 2021. Disponível em: https://www.ofgem.gov.uk/sites/default/files/docs/2021/04/dno_common_network_asset_indices_methodology_v2.1_final_01-04-2021.pdf. Acesso em: 2 set. 2026.

PEDREGOSA, F. et al. Scikit-learn: machine learning in Python. **Journal of Machine Learning Research**, v. 12, p. 2825–2830, 2011. Citação e licença: https://scikit-learn.org/stable/about.html. Acesso em: 2 set. 2026.

SANDVE, G. K.; NEKRUTENKO, A.; TAYLOR, J.; HOVIG, E. Ten simple rules for reproducible computational research. **PLOS Computational Biology**, v. 9, n. 10, e1003285, 2013. DOI: 10.1371/journal.pcbi.1003285. Disponível em: https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003285. Acesso em: 2 set. 2026.

SANKARARAMAN, S.; GOEBEL, K. Uncertainty in prognostics and systems health management. **International Journal of Prognostics and Health Management**, v. 6, n. 4, 2015. DOI: 10.36001/ijphm.2015.v6i4.2319. Disponível em: https://papers.phmsociety.org/index.php/ijphm/article/view/2319. Acesso em: 2 set. 2026.

SAXENA, A.; CELAYA, J.; SAHA, B.; SAHA, S.; GOEBEL, K. Metrics for offline evaluation of prognostic performance. **International Journal of Prognostics and Health Management**, v. 1, n. 1, 2010. DOI: 10.36001/ijphm.2010.v1i1.1336. Disponível em: https://papers.phmsociety.org/index.php/ijphm/article/view/1336; PDF: https://papers.phmsociety.org/index.php/ijphm/article/download/1336/324. Acesso em: 2 set. 2026.

SAXENA, A.; GOEBEL, K.; SIMON, D.; EKLUND, N. Damage propagation modeling for aircraft engine run-to-failure simulation. In: **International Conference on Prognostics and Health Management (PHM08)**. Denver, 2008. DOI: 10.1109/PHM.2008.4711414. Metadados: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/PHM.2008.4711414. Acesso em: 2 set. 2026. Texto integral não acessado — [INSERIR CITAÇÃO de página para a função de pontuação].

SHAO, G. **Use case scenarios for digital twin implementation based on ISO 23247**. NIST Advanced Manufacturing Series 400-2. Gaithersburg: NIST, 2021. DOI: 10.6028/NIST.AMS.400-2. Disponível em: https://nvlpubs.nist.gov/nistpubs/ams/NIST.AMS.400-2.pdf. Acesso em: 2 set. 2026.

SIEMENS. **Senseye Predictive Maintenance**. Disponível em: https://siemens.com/global/en/products/services/digital-enterprise-services/analytics-artificial-intelligence-services/predictive-services/senseye-predictive-maintenance.html. Acesso em: 2 set. 2026.

SOFTWARE HERITAGE. **SoftWare Heritage persistent IDentifiers (SWHIDs)**. Documentação swh-model. Disponível em: https://docs.softwareheritage.org/devel/swh-model/persistent-identifiers.html. Acesso em: 2 set. 2026.

THE TURING WAY COMMUNITY. **Definitions of reproducibility**. In: The Turing Way. Disponível em: https://book.the-turing-way.org/reproducible-research/overview/overview-definitions. Acesso em: 2 set. 2026.

TIMESERIESAI. **tsai — state-of-the-art deep learning library for time series and sequences**. Disponível em: https://timeseriesai.github.io/tsai/. Acesso em: 2 set. 2026.

TVHAHN. **PyPHM — machinery data, made easy**. Repositório GitHub. Disponível em: https://github.com/tvhahn/PyPHM. Acesso em: 2 set. 2026.

WANG, B.; LEI, Y.; LI, N.; LI, N. A hybrid prognostics approach for estimating remaining useful life of rolling element bearings. **IEEE Transactions on Reliability**, v. 69, n. 1, p. 401–412, 2020. DOI: 10.1109/TR.2018.2882682. Metadados: https://api.crossref.org/works/10.1109/TR.2018.2882682; banco XJTU-SY: https://biaowang.tech/xjtu-sy-bearing-datasets/. Acesso em: 2 set. 2026.

ZENODO. **Consultas à API de registros** (stator insulation aging; partial discharge datasets; twisted pair/magnet wire/turn insulation aging). Disponível em: https://zenodo.org/api/records?q=%22stator%20insulation%22%20aging%20dataset&size=10; https://zenodo.org/api/records?q=%22partial%20discharge%22%20AND%20(dataset%20OR%20measurements)&size=10&type=dataset; https://zenodo.org/api/records?q=(%22twisted%20pair%22%20OR%20%22magnet%20wire%22%20OR%20%22turn%20insulation%22)%20AND%20aging&size=10. Acesso em: 2 set. 2026.

Fontes internas (não web): fichamentos dos artigos 02, 05, 07, 08, 13 e dos documentos A e B em `<scratchpad da sessão>/out/fichamentos/` e `.../out/fichamentos_AB/`; mapas do repositório em `.../out/repo/`; pesquisa `c_level_demanda_rul.md`, `fisica_surtos_vcb_isolamento.md` e `normas_monitoramento_isolamento.md` em `.../out/web/`.

---

## Anexo A — URLs tentadas e não acessadas (bloqueio, redirecionamento a autenticação ou conteúdo indisponível)

| URL | Resultado |
|---|---|
| https://www.iso.org/standard/21832.html (ISO 13374-1) | HTTP 403; via curl: página "Just a moment…" (desafio JavaScript) |
| https://www.iso.org/standard/75066.html (ISO 23247-1) | HTTP 403 |
| https://standards.iteh.ai/… (ISO 13374-1, URL inferida) | página genérica; URL do documento não localizada |
| https://www.nature.com/articles/s41597-022-01710-x (FAIR4RS, Sci. Data) | redirecionamento para idp.nature.com (não seguido) |
| https://www.softwareheritage.org/save-and-reference-research-software/ ; /mission/ ; /faq/ ; https://www.softwareheritage.org/ ; https://archive.softwareheritage.org/ | HTTP 503 / acesso negado / erro TLS via curl |
| https://www.acm.org/publications/policies/artifact-review-and-badging-current | HTTP 403 (Cloudflare) |
| https://www.mdpi.com/1424-8220/21/23/8020 | HTTP 403 (metadados obtidos via Crossref) |
| https://www.digitaltwinconsortium.org/glossary/glossary/ ; /initiatives/the-definition-of-a-digital-twin/ | HTTP 403 |
| https://www.bentley.com/software/assetwise/ ; /assetwise-asset-reliability/ | página de autenticação ("Signing in") |
| https://www.siemens.com/global/en/products/drives/sidrive-iq.html ; …/senseye-predictive-maintenance.html (caminho antigo) | HTTP 404 (Senseye acessado pelo caminho novo) |
| https://new.abb.com/motors-generators/digital-powertrain ; …/health-and-monitoring/abb-ability-digital-powertrain-insights | HTTP 503 (conteúdo obtido via curl da URL do Smart Sensor) |
| https://data.nasa.gov/dataset/igbt-accelerated-aging | HTTP 404 (descrição obtida na página do repositório PCoE) |
| https://www.femto-st.fr/…/IEEE-PHM-2012-Data-challenge ; https://hal.science/hal-00719503 (+ /document) | HTTP 404 / acesso negado |
| https://ieee-dataport.org/search/node?keys=stator+insulation+aging | HTTP 404 |
| https://ntrs.nasa.gov/api/citations/search?q=… (Saxena 2008 metrics) | 0 resultados |
| https://api.semanticscholar.org/graph/v1/paper/search?… (Sankararaman) | HTTP 429 (obtido depois diretamente no IJPHM) |
| https://nasa.github.io/progpy/api_ref/progpy/Metrics.html | HTTP 404 (métricas lidas em prog_algs_guide.html) |
| https://www.phmsociety.org/competition/phm/08 | HTTP 404 |
| https://en.wikipedia.org/wiki/MIMOSA_(organization) ; https://en.wikipedia.org/wiki/Condition-based_maintenance | 404 / sem menção a OSA-CBM |
| https://www.ofgem.gov.uk/publications/dno-common-network-asset-indices-methodology | apenas página de aviso (PDF v2.1 acessado diretamente) |
| https://api.crossref.org/works/10.15497/RDA00068 | HTTP 404 (DOI DataCite; registro lido no Zenodo) |
