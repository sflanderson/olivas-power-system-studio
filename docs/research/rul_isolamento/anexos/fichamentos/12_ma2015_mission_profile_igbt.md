# Fichamento 12 — Ma, Liserre, Blaabjerg e Kerekes (2015): carga térmica e estimativa de vida de dispositivos de potência considerando perfis de missão em conversores eólicos

Convenções deste fichamento: "fato do artigo" = conteúdo verificável no texto extraído, com página indicada segundo os marcadores "===== PAGE N =====" (p. 1 corresponde à página 590 do periódico; p. 13, à página 602); "fato do repositório" = conteúdo verificado por leitura direta do código do Olivas Power System Studio; "inferência minha" = conclusão derivada por mim a partir do texto, de aritmética sobre dados do artigo ou do repositório; "hipótese" = proposição ainda não verificada, a ser testada. As Tabelas I (parâmetros do conversor de 2 MW) e II (parâmetros da bancada experimental) não tiveram seus valores extraídos no arquivo de texto; onde necessário, indico [INSERIR VALORES DA TABELA N]. As figuras (Figs. 1 a 27) não tiveram conteúdo gráfico extraído; os valores numéricos citados abaixo provêm exclusivamente do corpo do texto e das legendas.

---

## 1. Referência completa

MA, Ke; LISERRE, Marco; BLAABJERG, Frede; KEREKES, Tamas. Thermal Loading and Lifetime Estimation for Power Device Considering Mission Profiles in Wind Power Converter. **IEEE Transactions on Power Electronics**, v. 30, n. 2, p. 590–602, fev. 2015. DOI: 10.1109/TPEL.2014.2312335.

Dados complementares (fato do artigo, p. 1):
- Manuscrito recebido em 21 ago. 2013; revisado em 3 dez. 2013 e 20 fev. 2014; aceito em 10 mar. 2014; publicado em 18 mar. 2014; versão corrente de 7 out. 2014. Editor associado responsável: Y.-M. Chen.
- Afiliação dos quatro autores: Department of Energy Technology, Aalborg University, Aalborg 9220, Dinamarca (e-mails kema@et.aau.dk, mli@et.aau.dk, fbl@et.aau.dk, tak@et.aau.dk).
- Versão de conferência anterior do mesmo trabalho (ref. [39] do artigo, p. 12): MA, K.; BLAABJERG, F. Lifetime estimation for the power semiconductors considering mission profiles in wind power converter. In: Proc. IEEE Energy Convers. Congr. Expo. (ECCE), set. 2013, p. 2962–2971.
- Termos de indexação: IGBT, lifetime prediction, mission profiles, power semiconductor device, thermal cycling, wind power (p. 1).

## 2. Objetivo do artigo

Fato do artigo (p. 1, resumo): os conversores eletrônicos de potência de turbinas eólicas e seus semicondutores "suffer from complicated power loadings related to environment, and are proven to have high failure rates"; por isso "correct lifetime estimation of wind power converter is crucial for the reliability improvement and also for cost reduction of wind power technology". Os métodos existentes "are not yet suitable in the wind power application, because the comprehensive mission profiles are not well specified and included". O artigo propõe "a relative more advanced approach [...] based on the loading and strength analysis of devices and takes into account different time constants of the thermal behaviors in power converter", com "some experimental results [...] to validate the thermal behavior of power device under different mission profiles".

Fato do artigo (p. 2): a contribuição declarada é dupla: (i) um método de mapeamento do perfil de missão (velocidade do vento e temperatura ambiente por um ano) para o perfil de carga térmica dos IGBTs, separado em três constantes de tempo (longo, médio e curto prazo); (ii) a obtenção não apenas de um número global de vida, mas da "lifetime distribution—which indicates the failure contribution by different loading conditions as well as failure mechanisms".

Inferência minha: o artigo é um trabalho de estimativa de vida consumida (damage accumulation) por física da falha, e não de prognóstico online. Não há sensor em campo, não há estimação de estado nem atualização bayesiana; a saída é a vida B10 consumida por ano, decomposta por mecanismo, por escala de tempo e por condição operativa (velocidade do vento). O termo RUL não aparece no texto.

## 3. Sistema/componente e mecanismo(s) de degradação tratados

Sistema (fato do artigo):
- Turbina eólica de 2,0 MW Vestas V80 [25], classe de vento IEC I (velocidade média 8,5–10 m/s), operando com perfil de missão de 1 ano (velocidade do vento e temperatura ambiente, médias de 3 h, altura de cubo de 80 m) coletado em parque eólico próximo a Thyborøn, Dinamarca (latitude 56,71°, longitude 8,20°) (p. 2, Fig. 3).
- Conversor back-to-back de dois níveis (2L-VSC); apenas o conversor do lado da rede é analisado, com parâmetros da Tabela I [INSERIR VALORES DA TABELA I] (p. 2–3, Fig. 4). "The generator side converter can share the similar approach for the analysis" (p. 3).
- Módulo IGBT ABB 5SNA 2400E170305 (2,4 kA / 1,1 kV / 150 °C), com temperatura máxima de junção fixada em 115 °C quando o líquido do dissipador refrigerado a água está a 40 °C (p. 3).

Mecanismos de degradação (fato do artigo):
- Ciclagem térmica como uma das causas de falha mais críticas em eletrônica de potência [11]–[14]: "The temperature fluctuation on different materials with mismatched coefficients of thermal expansion may cause disconnection in the contacting areas after certain cycles, thus leading to the failures of the devices" (p. 1).
- Três mecanismos de fadiga de interconexão discriminados nos resultados (p. 5, Fig. 11): trinca da solda da placa-base ("B solder", causada pela ciclagem da temperatura de encapsulamento Tc); trinca da solda do chip ("C solder", causada pela ciclagem da temperatura de junção Tj); e descolamento de fios de ligação ("bond wire lift-off", causado pela ciclagem de Tj).
- Escopo declarado: "the fatigue on the interconnections inside IGBT modules based on soldering and aluminium bond wires is mainly focused" (p. 9). Outras causas — "electrical degradation, humidity, vibration, cosmic radiation, etc." — exigem "quite different scenarios and approaches" e "cannot be evaluated in this paper" (p. 9).

Inferência minha: o mecanismo é termo-mecânico (fadiga por dilatação diferencial), e a variável de estresse é uma temperatura interna ao componente, obtida por simulação eletro-térmica e não por medição em operação. Não há degradação elétrica do dielétrico em nenhuma parte do modelo.

## 4. Indicadores/precursores de degradação usados

Observação preliminar (inferência minha): o artigo não usa "precursores" no sentido de PHM (sinais medidos que antecedem a falha). As grandezas abaixo são variáveis de estresse calculadas e, no caso da validação, medidas em bancada.

| Indicador | Grandeza / unidade | Como é obtido | Passo de tempo / taxa de amostragem | Página |
|---|---|---|---|---|
| Temperatura de junção Tj do chip IGBT | °C | Simulação eletro-térmica: perda (tabela 3-D) × rede térmica (Figs. 7, 8, 14) | Longo prazo: passo de 3 h por 1 ano; médio prazo: passo de 1 s por 3 h; curto prazo: passo de 0,5 ms por 0,2 s | p. 3–4, 6, 8 |
| Temperatura de encapsulamento (placa-base) Tc | °C | Idem; no médio prazo por caminho térmico separado (Cauer de camada única + graxa + dissipador) | Idem | p. 4, 6 |
| Amplitude de ciclo térmico ΔTj | K | Contagem rainflow [29], [30] sobre Tj (longo e médio prazos); analiticamente pela eq. (4) no curto prazo | — | p. 4, 8 |
| Temperatura média do ciclo Tjm | °C | Rainflow (longo/médio); perfil de médio prazo (Fig. 16) no curto prazo | — | p. 4, 8 |
| Período do ciclo tcycle (tperiod) | s | Rainflow "which extracts ΔTj, Tjm, and also tcycle", "Different from the traditional approach" | — | p. 4 |
| Perda no dispositivo Ploss | W (unidade implícita) | Tabela de consulta 3-D em função da potência de entrada do conversor e de Tj; cada ponto simulado em modelo de circuito detalhado com comutação, perdas de condução, comutação e recuperação reversa do diodo [26] | — | p. 3–4, Fig. 7 |
| Número de ciclos até falha Nlife (a B10) | ciclos | Tabelas do fabricante [16] (longo/médio prazo) ou eq. (5) [35] (curto prazo) | — | p. 5, 8 |
| Vida B10 consumida CL | % | Eqs. (1)–(3), regra de Miner | Anual | p. 5, 7 |
| Tj e Tc medidas (validação) | °C | Câmera termográfica infravermelha de alta frequência sobre módulo aberto e pintado de preto; pontos tp1 (Tj) e tp2 (Tc) | 10 Hz (médio prazo, 10 min); 350 Hz (curto prazo, 0,2 s) | p. 10–11, Figs. 25–27 |

Detalhes (fato do artigo):
- "not only the amplitude ΔTj and the mean value Tjm of thermal cycles, but also the cycling period tcycle all have strong impacts to the lifetime of power devices [15]–[18]" (p. 4).
- No longo prazo, "460 thermal cycles are identified" no perfil de Tj de 1 ano (p. 4, Fig. 10).
- Tfluid é mantida em 40 °C sempre que o IGBT gera perdas e assume a temperatura da nacele se a velocidade do vento ficar abaixo do cut-in por mais de 12 h (p. 4).
- No curto prazo, "the junction temperature Tj oscillates at 50 Hz with constant swinging amplitude, while the case temperature Tc remains almost unchanged", de modo que os modelos de vida são aplicados diretamente "without rain flow counting" e Tc não é considerada (p. 8).

Inferência minha: a extração de tcycle pelo rainflow é anunciada como diferencial, mas o algoritmo de atribuição do período a cada ciclo contado não é descrito; o leitor não consegue reproduzir a Fig. 10 a partir do texto.

## 5. Modelo/algoritmo

Classe: física (physics-of-failure), com modelos de resistência (strength) obtidos por ajuste empírico de ensaios acelerados do fabricante. Inferência minha: no vocabulário da literatura de RUL, é um método "model-based" de acúmulo de dano; não há componente orientado a dados no sentido de aprendizado a partir de histórico operacional.

### 5.1 Arquitetura (fato do artigo)

Fig. 1 (p. 1): estimativa de vida baseada em física = análise de estresse (mapeamento do perfil de carga que dispara falhas) + modelo de resistência (quanto de carga o componente suporta).

Fig. 2 e Seção II (p. 2): separação dos comportamentos térmicos em três constantes de tempo, por analogia com "lenses with different focal length" na fotografia:
- Longo prazo (Seção III): perturbações ambientais (vento e temperatura ambiente) em dias a meses; passo de 3 h, horizonte de 1 ano; inércias mecânicas e capacitâncias térmicas desprezadas (só resistências térmicas, Fig. 8); potência da turbina obtida da curva de potência do fabricante (p. 3–4).
- Médio prazo (Seção IV): comportamentos mecânicos da turbina (controle de pitch e de velocidade); passo de 1 s, horizonte de 3 h, extrapolado para 1 ano por ponderação pela distribuição de velocidades do vento (Fig. 13, classes de 2 m/s); vento reconstruído por modelo do RISØ National Laboratory baseado no espectro de Kaimal [31], com sombra da torre, turbulência rotacional e intensidade de turbulência de 18 % (classe A); função de transferência de inércia com constante de 20 s "to roughly emulate the power inertia of the wind turbine, drive train, and generator" (p. 5–6).
- Curto prazo (Seção V): perturbações elétricas rápidas (alternância da corrente de carga, comutação, faltas na rede); constantes de tempo de milissegundos; ΔTj resolvida analiticamente pela eq. (4) (p. 7–8).
- Combinação das três escalas pela regra de Miner [22] (p. 2).

Comportamento de partida/parada da turbina (fato do artigo, p. 6): velocidade nominal de vento 12 m/s; cut-in 3 m/s (média de 5 min); cut-out 25 m/s (média de 5 min) ou 32 m/s (média de 5 s); re-cut-in 24 m/s com atraso de 30 min "to emulate the startup process of the whole wind power generation system". "the turn ON and turn OFF of power converter will introduce significant power changes and thus have strong effects on the thermal cycling of power devices".

Modelo térmico de médio prazo (fato do artigo, p. 6, Fig. 14, ref. [32]): dois caminhos térmicos com fluxos de calor não acoplados. Caminho 1: rede Foster multicamada do datasheet para Tj, alimentada por um potencial de temperatura igual a Tc vindo do caminho 2. Caminho 2: rede Foster interna transformada matematicamente em uma célula Cauer RC de camada única (usada apenas como filtro de perdas), mais graxa térmica e dissipador, para Tc e temperatura do dissipador. Os autores admitem que a transformação "will lose some accuracy for the thermal dynamics of junction temperature".

### 5.2 Equações-chave (transcritas, com numeração original)

Acúmulo de vida no longo prazo (p. 5):

    CL_n = 100 / N_{n,life}   (%)                                   (1)  p. 5
    CL_{1year,long} = Σ_{n=1}^{460} CL_n                             (2)  p. 5

onde N_{n,life} é o número de ciclos que leva o IGBT a 10 % de taxa de falha (B10) para o n-ésimo ciclo contado (ΔTj, Tjm, tcycle), obtido das tabelas do fabricante [16]; a soma segue a regra de Miner [22].

Extrapolação do médio prazo de 3 h para 1 ano (p. 7):

    CL_{1year,medium} = (365·24/3) · ( W_{1 m/s} · CL_{1 m/s,3h} + W_{3 m/s} · CL_{3 m/s,3h} + ··· + W_{29 m/s} · CL_{29 m/s,3h} )   (3)  p. 7

onde W_{1 m/s} a W_{29 m/s} são os fatores de ponderação da densidade da distribuição de velocidades do vento (Fig. 13); a simulação de 3 h é repetida 15 vezes com Vave de 1 a 29 m/s em passos de 2 m/s. Inferência minha: 365·24/3 = 2920 segmentos de 3 h por ano.

Amplitude do ciclo térmico de curto prazo (p. 8, ref. [34]):

    ΔTj = Ploss · Zth( 3/(8·fo) ) + 2·Ploss · Zth( 1/(4·fo) )         (4)  p. 8

onde Ploss é a perda do dispositivo (tabela da Fig. 7), Zth é a impedância térmica em função do tempo (datasheet) e fo é a frequência fundamental de saída do conversor (50 Hz).

Modelo de vida de curto prazo tipo Coffin–Manson (p. 8, ref. [35], ensaiado com período de ciclagem de 2 s):

    Nlife = 1.017^{ (125 − Tjm − ΔTj/2)^{1.16} } × 8.2·10^{14} × (ΔTj)^{−5.28}      (5)  p. 8

Observação sobre a transcrição (inferência minha): no texto extraído a expressão aparece como "1.017(125−Tjm−ΔTj/2)1.16 × 8.2·1014 × (ΔTj)−5.28", com os expoentes perdidos na conversão; a leitura acima (base 1,017 elevada a (125 − Tjm − ΔTj/2)^1,16, multiplicada por 8,2·10^14 e por ΔTj^−5,28) é a interpretação mais consistente com a forma usual dos modelos ABB para HiPak, mas deve ser conferida no PDF original antes de qualquer uso numérico [INSERIR CITAÇÃO]. Fato do artigo: "this lifetime model only reflects the general failures of IGBT module and cannot separate the three failure mechanisms shown in Fig. 11" (p. 8).

### 5.3 Hiperparâmetros e escolhas estruturais (fato do artigo)

- Longo prazo: passo 3 h, horizonte 1 ano; sem capacitâncias térmicas; 460 ciclos rainflow (p. 3–4).
- Médio prazo: passo 1 s, horizonte 3 h; inércia 20 s; turbulência 18 %; 15 velocidades médias (1–29 m/s, passo 2 m/s); modelo de vida [16] para ciclos de 1 s a 3 h (p. 5–7).
- Curto prazo: passo 0,5 ms, janela 0,2 s, Tref = 40 °C, fo = 50 Hz; modelo (5); Tjm tomada do perfil de médio prazo; 15 simulações de 3 h reutilizadas (p. 8).
- Cobertura declarada dos modelos de resistência: [16] cobre períodos de ciclo de 10 s a 1 dia; [15], [17] cobrem 2 a 30 s; [35] ensaiado a 2 s (p. 8–9).

## 6. Dados e experimento

Dados de simulação (fato do artigo):
- Perfil de missão: 1 ano de velocidade do vento e temperatura ambiente, médias de 3 h, 80 m de altura, parque próximo a Thyborøn, Dinamarca (p. 2, Fig. 3). Não há indicação de ano civil da coleta nem de fonte pública dos dados (fato: ausência).
- Turbina V80 2,0 MW; conversor 2L back-to-back (Tabela I) [INSERIR VALORES DA TABELA I] (p. 2–3).
- Ferramenta de simulação de perdas: PLECS blockset 3.1 [26] (p. 4, 12). Modelo de vento: RISØ/Kaimal [31] (p. 5).

Ensaio experimental de validação (fato do artigo, p. 10–11):
- Objeto: "downscale dc–ac converter"; topologia 3L-NPC trifásica, escolhida porque "has only half of the voltage stress on the devices compared to the 2 L converter", vantajoso "because the used power module is opened with degraded voltage insulation capability" (p. 10). Módulo de potência da fase A aberto e pintado de preto (Fig. 23).
- Alimentação por duas fontes CC; carga RL trifásica passiva; corrente ajustada pelo índice de modulação (p. 10–11). Parâmetros na Tabela II [INSERIR VALORES DA TABELA II].
- Condição nominal (Fig. 24, p. 11): M = 1 p.u., Vdc = 600 V, fs = 20 kHz, FP = 1; escalas 1 kV/div (tensão de linha), 500 V/div (tensão de fase), 20 A/div (corrente), 4 ms/div. Potência nominal de saída: 10 kW (p. 11).
- Instrumentação: câmera termográfica infravermelha de alta frequência; pontos tp1 (Tj, chip do interruptor externo Tout) e tp2 (Tc, placa-base) (Fig. 25). A legenda da Fig. 25 registra "MOSEFET is imaged" (p. 11).
- Ensaio de médio prazo: 10 min correspondentes ao segmento 5100–5700 s da Fig. 16(b)/Fig. 15(b), com corrente variada conforme a potência em p.u. do conversor; amostragem térmica a 10 Hz (Fig. 26, p. 11).
- Ensaio de curto prazo: 0,2 s com corrente constante à potência nominal de 10 kW; amostragem a 350 Hz (Fig. 27, p. 11).
- Número de amostras/dispositivos/ciclos até falha: não se aplica; nenhum dispositivo foi levado à falha (fato: ausência de ensaio de vida).

Inferência minha: o dispositivo validado (MOSFET em módulo NPC de 10 kW, Vdc = 600 V) difere em tecnologia, potência (três ordens de grandeza), topologia (3L versus 2L) e frequência de comutação do IGBT de 2,4 kA/1,1 kV do estudo de caso; a validação é, portanto, de comportamento qualitativo (forma dos perfis térmicos), não de valores absolutos de Tj, Tc ou ΔTj do caso de 2 MW.

## 7. Métricas e resultados numéricos

Não há métrica de erro (RMSE, MAPE, intervalo de confiança) reportada em nenhuma parte do texto (fato: ausência). Os resultados são:

Longo prazo (p. 4–5):
- 460 ciclos térmicos identificados pelo rainflow no perfil de Tj de 1 ano, passo de 3 h (p. 4).
- Vida B10 consumida por ciclos > 3 h (Fig. 11): a ciclagem sobre a solda do chip (C solder) "consume more lifetime (i.e., more quick to failure) than the other two failure mechanisms" (p. 5). Valores percentuais não constam no texto [INSERIR VALORES DA FIG. 11].

Médio prazo (p. 6–7):
- Abaixo de 11 m/s, a amplitude de flutuação de Tj e Tc cresce com a velocidade do vento; acima de 11 m/s a flutuação é menor, mas cut-out e re-cut-in "will introduce significant thermal cycles" (p. 6).
- Vida B10 consumida por ciclos de 1 s a 3 h (Fig. 17): "the temperature cycling on the based plate of IGBT consumes more lifetime than the other two failure mechanisms" (p. 7).
- Distribuição por velocidade (Fig. 18): "the lifetime of the power devices is consumed intensively at wind speeds of 10–12 m/s", faixa próxima à velocidade nominal, quando o pitch é ativado e a potência varia significativamente (p. 7).

Curto prazo (p. 8):
- Tj oscila a 50 Hz com amplitude constante; Tc praticamente constante (Fig. 19, 0,2 s, passo 0,5 ms, Tref = 40 °C).
- Distribuição por velocidade (Fig. 20): consumo intenso em 14–15 m/s, onde a perda absoluta é máxima porque a turbina gera potência máxima; os valores "is much higher than the one shown in Fig. 18, this is because different lifetime models are used and the number of thermal cycling is significantly larger" (p. 8).

Total (p. 9):
- Fig. 21 (modelo [16], sem o curto prazo): "the critical thermal stresses which cause the reliability problem of the given converter can be addressed—the base plate and chip solder fatigues caused by medium-term thermal cycles".
- Fig. 22 (modelo [15], [17], só médio e curto prazos, sem longo prazo): resultados "may vary in a large range even with the same loading of power device" conforme o modelo de vida adotado.

Validação experimental (p. 11):
- Médio prazo (Fig. 26, 10 Hz): Tj > Tc, maior amplitude de ciclagem, ambas seguem a corrente — "consistent with the estimated thermal profiles shown in Fig. 16(b)".
- Curto prazo (Fig. 27, 350 Hz): "Tj oscillates at the fundamental frequency of 50 Hz with constant fluctuating amplitude of 1.5 °C, while Tc is almost constant" — "consistent with the estimated thermal profiles shown in Fig. 19".

Concordância com a literatura (p. 10): consumo mais intenso em torno da velocidade nominal concorda com [41], [45]; predomínio da fadiga de solda sobre o descolamento de fios concorda com [16], [18]; importância dos ciclos térmicos pequenos concorda com Weiss e Eckel [40].

Inferência minha: o artigo não reporta o número total de anos até B10 nem o percentual anual total consumido; a conclusão "quantitativa" fica restrita a rankings (qual mecanismo, qual escala, qual faixa de vento consome mais).

## 8. Limitações

Declaradas pelos autores:
1. (declarada, p. 8) Falta de dados de ensaio para ciclos com ΔTj < 10 K e frequência > 1 Hz; o modelo [35], ensaiado a período de 2 s, é usado a 50 Hz "for a rough approximation" e não separa mecanismos.
2. (declarada, p. 9) Os modelos de vida do fabricante cobrem faixas limitadas de ΔTj, Tjm e tperiod; ciclos "não identificados" foram tratados por interpolação/extrapolação linear em escala logarítmica e com tperiod fora da especificação, "this could lead to in-confidence of the acquired lifetime results".
3. (declarada, p. 9) Modelos de vida distintos, com tecnologias, ratings, condições de ensaio e critérios de falha diversos, produzem vidas "in a large range" para a mesma carga; sua avaliação está fora do escopo.
4. (declarada, p. 9) Os três intervalos de tempo e passos são "qualitative definitions", ajustáveis caso a caso.
5. (declarada, p. 9) Só fadiga de solda e fios de alumínio; degradação elétrica, umidade, vibração e radiação cósmica não avaliadas.
6. (declarada, p. 9) A Fig. 21 (total) exclui o curto prazo porque o modelo [16] só cobre 10 s a 1 dia; a Fig. 22 exclui o longo prazo porque [15], [17] só cobrem 2 a 30 s.
7. (declarada, p. 10) A vida estimada não pode ser validada por estatísticas de falha de campo, que não refletem a tecnologia atual, agregam o conversor inteiro e raramente discriminam causas; só o comportamento térmico é validado.
8. (declarada, p. 6) A inércia mecânica é emulada "roughly" por uma constante de 20 s; a transformação Foster→Cauer de camada única perde acurácia na dinâmica de Tj.
9. (declarada, p. 10) A bancada usa 3L-NPC e módulo aberto com isolamento degradado, por conveniência de operação prolongada.

Identificadas por mim:
10. (minha inferência) Tabelas I e II não extraídas; sem elas não é possível reproduzir as perdas nem a bancada.
11. (minha inferência) O dispositivo validado é um MOSFET de 10 kW (legenda da Fig. 25), não o IGBT de 2,4 kA do caso; a validação é qualitativa ("features are consistent"), sem métrica de erro nem comparação ponto a ponto simulação × medição.
12. (minha inferência) A regra de Miner assume dano linear, independente da ordem dos ciclos e sem interação entre mecanismos e escalas; o artigo não discute essa hipótese nem propõe alternativa.
13. (minha inferência) Não há quantificação de incerteza: a vida B10 é um quantil do modelo do fabricante, mas nenhuma incerteza de perfil de missão, de parâmetros térmicos ou de interpolação é propagada; a saída é determinística.
14. (minha inferência) O perfil de missão é um único ano de um único sítio; não há variabilidade interanual nem análise de sensibilidade ao sítio ou à classe de vento.
15. (minha inferência) A extrapolação da eq. (3) trata cada segmento de 3 h como estacionário na média; transições entre classes de velocidade (que geram ciclos de médio prazo) não são capturadas nem pelo médio prazo (segmentos independentes) nem pelo longo prazo (passo de 3 h), o que pode subestimar ciclos com período entre minutos e horas.
16. (minha inferência) A temperatura ambiente entra apenas por Tfluid = temperatura da nacele quando a turbina fica parada > 12 h; nos demais instantes Tfluid = 40 °C fixo, o que elimina a sazonalidade do dissipador.
17. (minha inferência) O algoritmo de extração de tcycle pelo rainflow não é descrito; a Fig. 10 não é reproduzível a partir do texto.
18. (minha inferência) Não há saída de RUL propriamente dita (tempo restante a partir de um estado atual), apenas consumo anual em condição nova; o método não incorpora observações do estado real do componente.

## 9. Transferibilidade para o problema-alvo

Problema-alvo: isolamento de estator de motor de indução MT (2,3–13,8 kV) submetido a (a) sobretensões de manobra de disjuntor a vácuo (VCB) — chopping, reignições múltiplas, frentes íngremes, dV/dt — com/sem snubber tiristorizado (trabalho A) e (b) estresse térmico de partidas de grandes motores sob contingência N-1 com load shedding (trabalho B).

Contexto do repositório (fato do repositório):
- `app/preprocessor/atp_templates/vcb_reignition.mod`: MODEL ATP de reignição estatística por polo (I_chop ~ N(I_chop_mean, σ²) amostrado no cruzamento de zero; reignição se |di/dt| > di/dt_crit(t) = didt_crit_0 + didt_sigma·(t − t_open); recuperação dielétrica U_dielec(t) = U0_dielec + k_dielec·(t − t_corte); saída reign_count), com valores padrão I_chop_mean = 5 A, σ = 1 A, didt_crit_0 = 16 A/µs, k_dielec = 17 V/µs, U0_dielec = 690 V, T_bounce = 0,5 ms e semente de RNG. `app/validation/validator_vcb.py` verifica faixas (I_CHOP típico 1–15 A, RRDS_A/B > 0) e alerta quando há VCB sem controlador de snubber (código VCB-0xx).
- `app/postprocessor/tcc_damage.py::MotorThermalCurve`: curva térmica de motor de constante de tempo única, t(I) = K_motor/(I/FLA)², com K_motor = tE·(I_LR/FLA)² (padrões: I_LR/FLA = 6, tE = 10 s), com limitação documentada de que rotor e estator têm constantes térmicas distintas em motores grandes de alta tensão.
- `app/postprocessor/motor_starting.py`: critérios V > 0,85 pu (IEEE 399 §10), V > 0,80 pu (NEMA MG 1), t_start < 0,7 × t_locked_rotor_thermal, N_starts/hora (NEMA MG 1 §20.43). `app/postprocessor/motor_reaccel.py`: cenários de reaceleração, black-start e transferência de barra.

### 9.1 O que se transfere

(T1) Arquitetura "perfil de missão → perfil de carga (estresse) → modelo de resistência → acúmulo de dano → distribuição de vida por mecanismo e por condição operativa" (Fig. 1 e Seção II, p. 1–2). Transfere-se integralmente como esqueleto do módulo computacional. Hipótese de mapeamento para o motor MT:
- Perfil de missão do motor: histórico anual de (i) manobras do VCB (número, instante de abertura relativo ao zero de corrente, condição do motor no instante — partida, plena carga, vazio), (ii) partidas/paradas/reacelerações, incluindo as impostas por contingência N-1 e pelas decisões de load shedding do trabalho B, (iii) carga e temperatura ambiente. Análogo direto do perfil vento + ambiente da Fig. 3.
- Perfil de carga: para (a), forma de onda de tensão nos terminais e entre espiras (pico, dV/dt, número de reignições, energia) por manobra, obtida do ATP com `vcb_reignition.mod`, com e sem snubber; para (b), temperatura do enrolamento (hot-spot) por partida, obtida de rede térmica alimentada pelo perfil de corrente de partida sob tensão reduzida.
- Modelos de resistência: para (a), curvas de suportabilidade repetitiva a impulsos do sistema isolante (número de impulsos até falha em função da amplitude e do tempo de frente) [INSERIR CITAÇÃO]; para (b), lei de Arrhenius/classe térmica para envelhecimento térmico e curva de ciclagem térmica para delaminação/afrouxamento [INSERIR CITAÇÃO].
- Acúmulo: regra de Miner, com as ressalvas do item 9.2.

(T2) Separação por constantes de tempo (Fig. 2, p. 2) e a advertência de que "if too rough models and longer time step are used, the generated loading profile may not contain enough thermal dynamics and the lifetime information may significantly deviate from the reality" (p. 2). Hipótese de tradução: curto prazo (µs–ms) = surtos de VCB, resolvidos no ATP com passo sub-microssegundo; médio prazo (s–min) = transitório térmico de partida e reaceleração (o `MotorThermalCurve` de constante de tempo única é o análogo grosseiro de uma célula RC térmica única, intermediário entre a rede puramente resistiva da Fig. 8 e a rede de dois caminhos da Fig. 14; uma rede de duas constantes estator/rotor seria o análogo da Fig. 14); longo prazo (h–meses) = carga e ambiente, com envelhecimento térmico de Arrhenius. A observação de que partidas/paradas ("turn ON and turn OFF of power converter", cut-out/re-cut-in com atraso de 30 min, p. 6) dominam os ciclos de médio prazo transfere-se diretamente: as partidas do trabalho B são o evento de médio prazo dominante para o motor.

(T3) Contagem rainflow com extração de (ΔT, Tm, tcycle) (p. 4) sobre o perfil de temperatura do enrolamento. Transfere-se como técnica, pois o mecanismo termo-mecânico (dilatação diferencial cobre/isolante/núcleo) é análogo ao de CTE mismatch do módulo IGBT (p. 1). Hipótese: em motores MT de grande porte, a ciclagem térmica de partidas sucessivas é candidata a mecanismo dominante de delaminação do groundwall [INSERIR CITAÇÃO].

(T4) Extrapolação por ponderação pela distribuição das condições operativas, eq. (3) (p. 7). Transfere-se como método de composição: para (b), simular a partida para um conjunto discreto de condições (tensão na barra durante a partida, carga acoplada, temperatura inicial do enrolamento, configuração de load shedding) e ponderar pela frequência anual de cada condição sob N-1; para (a), simular Monte Carlo de manobras (o `vcb_reignition.mod` já amostra I_chop e admite semente) e ponderar pela distribuição de instantes de abertura e pela fração de manobras com snubber ativo.

(T5) Saída como distribuição de vida consumida por mecanismo, por escala de tempo e por condição (Figs. 11, 17, 18, 20, 21). Transfere-se como o entregável de decisão: "qual fração da vida do isolamento é consumida por manobras de VCB sem snubber versus com snubber" (trabalho A) e "qual fração é consumida por partidas sob N-1 versus partidas normais" (trabalho B). É o argumento de p. 2 ("lifetime distribution [...] would be more useful for the design and improvement") aplicado ao nível C.

(T6) Estratégia de validação (Seção VII, p. 10–11): reconhecer que a vida não é validável por estatística de campo e validar o estresse, não a vida. Transfere-se como protocolo: validar as formas de onda de surto (osciloscopia nos terminais do motor, com e sem snubber) e as temperaturas de partida (RTD/PT100 embutidos), e declarar explicitamente a vida como extrapolação de modelo.

(T7) Tratamento honesto das "unidentified cycles" fora da faixa ensaiada (p. 9). Transfere-se como exigência de documentar, para cada modelo de resistência do isolamento, a faixa de amplitude/frente/temperatura ensaiada e sinalizar toda extrapolação.

### 9.2 O que não se transfere e por quê

(N1) Os modelos de resistência específicos — tabelas B10 da ABB [16] e a eq. (5) de Coffin–Manson [35] — não se transferem: descrevem fadiga de solda e de fios de alumínio, com expoentes ajustados a módulos HiPak; o isolamento de estator degrada por mecanismos elétricos (descargas parciais, erosão, treeing), térmicos (oxidação, cisão de cadeias) e mecânicos, com leis distintas (potência inversa em tensão, Arrhenius em temperatura). Inferência minha.

(N2) Os indicadores Tj e Tc e a eq. (4) (ripple de Tj a 50 Hz) não se transferem: a constante térmica do enrolamento é de minutos a horas, e a oscilação de temperatura a frequência fundamental é desprezível no motor; o "curto prazo" do motor é dielétrico (surto), não térmico. Inferência minha.

(N3) A regra de Miner linear é questionável para o estresse dielétrico por surtos: a degradação por descargas parciais tem comportamento de limiar (tensão de incepção) e forte não linearidade com a amplitude; um surto acima do limiar de reignição múltipla pode causar dano desproporcional, e a sequência importa. O artigo não oferece ferramenta para isso. Inferência minha; hipótese a testar com modelo de dano não linear.

(N4) O perfil de missão determinístico de um ano não se transfere para o estresse (a): as manobras de VCB são eventos estocásticos (chopping, sequência de reignições) cuja severidade depende do instante de abertura e do estado do motor; exige-se caracterização estatística por Monte Carlo no ATP, e não um único perfil temporal. Inferência minha.

(N5) A bancada de validação (câmera IR sobre módulo aberto) não se transfere: o isolamento está embutido nas ranhuras; a observação direta exige indicadores elétricos (corrente de fuga transitória, capacitância, tanδ, descargas parciais — ver fichamento 02, Jensen et al. 2018) ou térmicos indiretos (RTD). Inferência minha.

(N6) A tabela 3-D de perdas em função de potência e Tj (Fig. 7) não se transfere em conteúdo, mas se transfere em forma (tabela de perdas Joule do enrolamento em função de corrente e temperatura, com resistência corrigida). Inferência minha.

(N7) O artigo não trata de mitigação (o snubber tiristorizado do trabalho A) nem de otimização de decisões operativas (o load shedding do trabalho B); não há função de custo, nem comparação de cenários. O módulo-alvo terá de acrescentar a camada de comparação de cenários por conta própria. Fato do artigo (ausência) e inferência minha.

### 9.3 Nota de transferibilidade

Nota: 3/5.

Justificativa (inferência minha): a arquitetura multi-escala com acúmulo de dano e saída decomposta por mecanismo/condição (T1–T5) e o protocolo de validação do estresse (T6) são diretamente reaproveitáveis como espinha dorsal do módulo computacional e respondem à demanda de nível C por "onde a vida está sendo gasta". Contudo, nenhum indicador, nenhum modelo de resistência e nenhum arranjo experimental se aplica ao isolamento de estator; o estresse dominante do trabalho A (dielétrico, estocástico, com limiar) é qualitativamente diferente do estresse térmico determinístico do artigo; e o artigo não produz RUL condicionada ao estado, apenas consumo em condição nova.

## 10. Citações literais relevantes

1. (p. 1) "the reliability engineering in power electronics is now moving from a solely statistical approach that has been proven to be unsatisfactory in the automotive industry, to a more physics-based approach which involves not only the statistics but also the root cause behind the failures [8]–[14]."
2. (p. 2) "these existing lifetime estimations can just acquire very general lifetime information of devices (e.g., number of years to failure), while the lifetime distribution—which indicates the failure contribution by different loading conditions as well as failure mechanisms, would be more useful for the design and improvement of converter reliability."
3. (p. 2) "if too rough models and longer time step are used, the generated loading profile may not contain enough thermal dynamics and the lifetime information may significantly deviate from the reality. Therefore, it is important first to develop a way to properly extract and sort the thermal loading in wind power converter for the sake of lifetime estimation."
4. (p. 4) "Different from the traditional approach, a rain flow counting method which extracts ΔTj, Tjm, and also tcycle is used in this paper. [...] 460 thermal cycles are identified and each counted cycle with its corresponding ΔTj, Tjm, and tcycle are shown."
5. (p. 8) "due to the lack of the testing data, most manufacturer cannot provide enough lifetime information by thermal cycles with small ΔTj (<10 K) and high cycling frequency (>1 Hz)."
6. (p. 9) "ΔTj and Tjm are interpolated/extrapolated linearly with log scale, and some cycling period tperiod are not consistent with the specification in the lifetime models—-this could lead to in-confidence of the acquired lifetime results. Therefore, even more advanced lifetime models which can cover more loading conditions of power devices are required."
7. (p. 10) "the general failure statistics, which include many other unknown causes of failure, cannot be used to validate the thermal-related lifetime modeled in this paper."
8. (p. 11) "Tj oscillates at the fundamental frequency of 50 Hz with constant fluctuating amplitude of 1.5 °C, while Tc is almost constant without significant fluctuations—these features are consistent with the estimated thermal profiles shown in Fig. 19."

## 11. Ligações com RUL, PHM e nível C

RUL (inferência minha): o artigo não define nem calcula RUL; calcula vida B10 consumida por ano em condição nova (eqs. (1)–(3)). A conversão para "anos até B10" seria 100/CL_anual (aritmética minha, não feita pelo artigo). Para um método de monitoramento, o artigo fornece o "modelo de dano a priori"; falta a camada de atualização por observação (como o EKF do fichamento 02) que transformaria o consumo estimado em RUL condicionada ao estado. A combinação "modelo físico de acúmulo de dano (este artigo) + estimador de estado alimentado por indicador medido (fichamento 02)" é a hipótese de arquitetura híbrida para o módulo-alvo.

PHM (inferência minha): o artigo é um exemplo canônico de physics-of-failure na fase de projeto (design for reliability, refs. [19], [36]). Contribui ao PHM com: separação por escalas de tempo, rainflow com período de ciclo, ponderação por distribuição de condições e decomposição da vida consumida por mecanismo. Não contribui com detecção, diagnóstico ou prognóstico online.

Argumentos de custo/decisão/manutenção transcritos (fato do artigo):
- (p. 1, resumo) "correct lifetime estimation of wind power converter is crucial for the reliability improvement and also for cost reduction of wind power technology."
- (p. 1) "The fast growth in the total installation and individual capacity makes the failures of wind turbines more critical for the power system stability and also more costly to repair [1]–[3]. Former field feedbacks have shown that the power electronics tend to have higher failure rate than the other parts in the wind turbine system [4], [5]. As a result, correctly estimating the reliability performance of the wind power converter is crucial, not only for lifetime extension, but also for the cost reduction of the wind power technology [6], [7]."
- (p. 12, conclusão) "more possibilities and details of the lifetime information for wind power converter can be obtained like the lifetime consumption by different thermal behaviors, wind speeds, and failure mechanisms. This is very useful to indicate and improve the weakness of the system in respect to the reliability performance."

Leitura para o nível C (inferência minha): o valor de decisão do método está em responder "qual condição operativa e qual mecanismo consomem mais vida", e não em um número único de anos. Aplicado ao problema-alvo, isso se traduz em dois quocientes auditáveis: vida consumida por manobra de VCB com snubber / sem snubber (justificativa econômica do trabalho A) e vida consumida por partida sob N-1 / partida normal (custo oculto de cada política de load shedding do trabalho B). O artigo não traz custo monetário, política de manutenção nem intervalo de inspeção; esses elementos terão de vir de outras fontes [INSERIR CITAÇÃO].
