# Fichamento 02 — Jensen, Strangas e Foster (2018): prognóstico online de isolamento de estator com EKF

Convenções deste fichamento: "fato do artigo" = conteúdo verificável no texto, com página indicada segundo os marcadores "===== PAGE N ====="; "inferência minha" = conclusão derivada por mim a partir do texto ou do repositório; "hipótese" = proposição ainda não verificada, a ser testada. Tabelas I, II e III do artigo não tiveram seus valores numéricos extraídos no arquivo de texto; onde necessário, indico [INSERIR VALORES DA TABELA N].

---

## 1. Referência completa

JENSEN, William R.; STRANGAS, Elias G.; FOSTER, Shanelle N. A Method for Online Stator Insulation Prognosis for Inverter-Driven Machines. **IEEE Transactions on Industry Applications**, v. 54, n. 6, p. 5897–5906, nov./dez. 2018. DOI: 10.1109/TIA.2018.2854408.

Dados complementares (fato do artigo, p. 1):
- Paper 2017-EMC-1394.R1; versão estendida do trabalho apresentado no 2017 IEEE 11th International Symposium on Diagnostics for Electrical Machines, Power Electronics and Drives (SDEMPED), Tinos, Grécia, 29 ago.–1 set. 2017; aprovado pelo Electric Machines Committee da IEEE Industry Applications Society.
- Manuscrito recebido em 8 jan. 2018; revisado em 29 mar. 2018; aceito em 15 jun. 2018; publicado em 8 jul. 2018.
- Afiliação: Department of Electrical and Computer Engineering, Michigan State University, East Lansing, MI, EUA. Apoio parcial: James Dyson Foundation Fellowship.
- Artigo-base da versão de conferência: JENSEN, W. R.; STRANGAS, E. G.; FOSTER, S. N. Online estimation of remaining useful life of stator insulation. In: Proc. IEEE 11th Int. Symp. SDEMPED, ago. 2017, p. 635–641 (ref. [23] do artigo, p. 10).

## 2. Objetivo do artigo

Fato do artigo (p. 1, resumo e introdução): propor um método online para calcular a vida útil remanescente (RUL) do isolamento de estator "with a simple equipment", usando a corrente de fuga transitória produzida por pulsos de tensão de frente rápida (como os de um inversor PWM), um algoritmo de filtro de Kalman estendido (EKF) para projetar a tendência do indicador até um limiar de falha, e um circuito analógico detector de pico que reduz a taxa de amostragem exigida para capturar a informação prognóstica.

Fato do artigo (p. 2): a contribuição incremental em relação à versão SDEMPED [23] é demonstrar experimentalmente que "a simple analog circuit, that can sample and hold the important leakage current information needed for prognosis, decreases the sampling rate requirement", pois em [23] os dados foram coletados com equipamento de até 10 GSa/s, o que "can make this method too expensive".

Inferência minha: o artigo é um trabalho de prognóstico (RUL), não apenas de diagnóstico; os autores posicionam-se explicitamente contra a literatura de Zoeller et al. [13], [14], [16]–[19] e Tsyokhla et al. [20], que "were able to diagnose when an insulation issue is present but a prognosis for the insulation was not provided" (p. 2).

## 3. Sistema/componente e mecanismo(s) de degradação tratados

Sistema (fato do artigo):
- Estatores de máquinas de indução trifásicas, ligação estrela, 5 kW nominais, isolamento classe F; rotor removido durante os ensaios (p. 3). Tensão nominal baixa: "The machines tested experimentally have a low-voltage rating. The insulation consists of a polyester resin on the coil and paper slot liner" (p. 2).
- Circuito equivalente: isolamento entre condutores e entre condutor e terra representado como resistência e capacitância distribuídas ao longo do enrolamento (Fig. 1, p. 2); valores de C e G para terra obtidos de modelo de elementos finitos, com permissividade e resistividade volumétrica na Tabela I (p. 2) [INSERIR VALORES DA TABELA I].

Mecanismo de degradação (fato do artigo):
- Envelhecimento térmico acelerado em câmara ambiental: "Degradation of the insulation was experimentally performed by exposing the stator to an elevated temperature" (p. 3); temperaturas e durações na Tabela II (p. 4) [INSERIR VALORES DA TABELA II].
- Justificativa da escolha do estresse: "Other sources of stress were not used to degrade the insulation because thermal stress can be applied in a repeatable manner" (p. 3).
- Efeito físico assumido: "Each insulation material experiences a decrease in capacitance and resistance as it degrades [24], [25]" (p. 2); "insulation degradation results in lower capacitance and resistance regardless of the initial impedance of the insulation" (p. 2).
- Isolamento monitorado: fase-terra (groundwall), mas os defeitos encontrados eram entre espiras: "The defects found were areas of insulation between two turns. This method is monitoring the health of the insulation between the phase and ground. The turn-to-turn insulation does contribute to the overall insulation impedance to the ground; therefore, turn-to-turn faults also create a change in the leakage current overshoot" (p. 4).
- Critério de falha: defeito ou área sem isolamento identificado em inspeção visual diária, "No standard test for insulation failure was used" (p. 3). Fig. 5 mostra Máquina 1 sã, após 12 dias e em estado de falha (p. 4).

Inferência minha: o artigo não distingue mecanismos químicos (oxidação, cisão de cadeias do poliéster, fragilização do papel) nem usa modelo de Arrhenius; a "degradação" é operacionalizada apenas como tendência do indicador elétrico até a evidência visual de defeito.

## 4. Indicadores/precursores de degradação usados

| Indicador | Grandeza / unidade | Como é medido | Taxa de amostragem / periodicidade | Página |
|---|---|---|---|---|
| Sobressinal (overshoot) pico a pico da corrente de fuga transitória em resposta a degrau de tensão | Corrente (A), obtida como tensão sobre resistores série; a unidade explícita não é dada no texto extraído | Resistor em série entre o dreno/fonte do MOSFET e o terminal de fase; outro resistor entre a carcaça do estator e a terra; tensão aplicada também registrada para garantir consistência (p. 5) | Barramento CC 160 V de retificador monofásico; MOSFET com tempo de subida de 22 ns [27]; pulsos a 10 kHz, ciclo de trabalho 50 %; osciloscópio "1-GSa/s" captura 1 ms a cada 5 min; 10 transitórios por janela de 1 ms processados em 1 ponto (p. 4–5) | p. 4–5 |
| Pico positivo do overshoot (em vez de pico a pico) | Tensão de saída do detector de pico (V), proporcional ao pico de corrente | Detector de pico analógico (diodo rápido + amplificador operacional + capacitor 47 nF); saída filtrada por filtro de mediana; magnitude = diferença de tensão antes/depois da aplicação do degrau (p. 7–8) | Circuito analógico amostrado a 10 MSa/s, comparado com corrente amostrada a 1 GSa/s (p. 8) | p. 7–8 |
| Tendência temporal do overshoot | I_leak(t) em unidade do indicador; tempo em horas | Série temporal de pontos a cada 5 min | — | p. 6 |

Detalhes relevantes (fato do artigo):
- O overshoot ocorre no instante da subida da tensão (Fig. 7, p. 5); o sinal foi filtrado com wavelet Daubechies 4 no quarto nível antes de extrair o pico a pico (p. 5).
- A simulação (Figs. 3(a) e 3(b), p. 3) mostra que a magnitude do overshoot diminui com a redução de C e R, tanto para distribuição simétrica quanto assimétrica das propriedades do isolamento; "monitoring this feature can provide information about insulation degradation for machines with different insulation materials" (p. 3).
- Sensibilidade ao dV/dt: "The peak magnitude of the overshoot in the transient response is larger when the rise time is lower [...] the actual dV/dt of the switching device is assumed to be constant for this method to detect changes in the insulation properties" (p. 3; Fig. 4, p. 4).
- Para medição online, "The three phase currents need to be added together to obtain the leakage current. Current sensors with a sufficient bandwidth can measure the leakage current. Only the peak of the transient response is required for this technique so a high sampling rate is not required on the current measurement" (p. 4).
- O pico do transitório ocorre em janela de aproximadamente 35 ns; sem detector de pico seria necessária amostragem próxima de 50 MHz (p. 7).

Inferência minha: o indicador é uma resposta ao impulso de uma rede RC/LC distribuída; sua magnitude depende de C_groundwall, das perdas, do dV/dt aplicado e do comprimento do cabo (os autores usaram cabos "under 1 m", p. 3). Não é um indicador absoluto de estado (não há valor de referência normativo), mas um indicador de tendência relativa ao valor inicial da própria máquina.

## 5. Modelo/algoritmo

Classe: híbrida (inferência minha). O indicador é justificado fisicamente (modelo RC distribuído de linha de transmissão alimentado por FE, Figs. 1–4), mas o prognóstico é um estimador estatístico de tendência (EKF sobre modelo exponencial empírico), sem lei física de envelhecimento.

### 5.1 Equações do EKF (transcritas, p. 5)

Notação do artigo (p. 5): x = variáveis de estado; F = matriz de transição; w e v = ruídos de processo e de medição (o texto os chama de "process noise covariance" e "measurement noise covariance", o que é impreciso — inferência minha: w e v são vetores de ruído; Q e R são as covariâncias, como o próprio parágrafo define a seguir); H = matriz de saída; z = saída medida; M e P = matrizes de incerteza (covariância a priori e a posteriori); K = ganho de Kalman.

    x_k = F_{k-1} x_{k-1} + w_{k-1}                          (1)  p. 5
    z_k = H_k x_k + v_k                                      (2)  p. 5
    M_k = F_{k-1} P_{k-1} F_{k-1}^T + Q_{k-1}                (3)  p. 5
    K_k = M_k H_k^T (H_k M_k H_k^T + R_k)^{-1}               (4)  p. 5
    x_k = x_k + K_k (z_k - H_k x_k)                          (5)  p. 5
    P_k = (1 - K_k H_k) M_k                                  (6)  p. 5

Observação (inferência minha): (6) é escrita com "1" no lugar da matriz identidade I; (5) reutiliza o mesmo símbolo x_k para a predição e para a atualização. O artigo não explicita a linearização (jacobiano) de F para o modelo exponencial nem a forma de F e H; o leitor deve reconstruí-las de (7)–(8).

### 5.2 Modelo de tendência e vetor de estados (p. 6)

    I_leak = α e^{β t}                                      (7)  p. 6
    x = [I_leak, α, β]^T                                     (8)  p. 6

Fato do artigo (p. 6): "At first, the data showed an increase to a maximum point, followed by an exponential decay returning the value near to the initial value. The trend is not a perfect exponential decay, but approximately takes that shape."

### 5.3 Procedimento de prognóstico (fato do artigo, p. 6)

1. Filtragem do sinal de corrente (Daubechies 4, nível 4) e extração do pico a pico (p. 5).
2. O algoritmo "first finds a peak value in the data and assigns that value to α" (p. 6).
3. O EKF projeta os valores futuros do indicador com parâmetros da Tabela III [INSERIR VALORES DA TABELA III — Q, R, P_0 etc. não constam no texto extraído].
4. Limiar de falha: "The initial overshoot value, at the beginning of the experiment, is selected as the failure threshold. Failure is defined as the point when the exponential decay is within 96% of the failure threshold" (p. 6).
5. Valor inicial da estimativa de RUL: "the average lifetime provided on the insulation datasheet" (p. 6).
6. RUL "verdadeira" para avaliação: reta decrescente da vida total em t = 0 até zero no instante de falha, construída a posteriori (p. 6).

Propriedade declarada: "With an initial expected decaying exponential trend, the EKF can adjust to any changes in the rate of decay if the trajectory begins to show an acceleration or deceleration in the degradation" (p. 6).

### 5.4 Circuito detector de pico (p. 7–8)

Fato do artigo: diodo de comutação rápida com tempo de recuperação reversa de 4 ns; amplificador operacional com slew rate de 900 V/µs; capacitor de retenção otimizado experimentalmente em torno de 47 nF; detecta apenas picos positivos; saída passa por filtro de mediana; magnitude do overshoot = diferença de tensão antes e depois do degrau (p. 7–8). A saída "is lower than the actual leakage current", atribuído a atrasos dos componentes e ao tempo de carga do capacitor; "the proportional output of the peak detector was still used for prognosis" (p. 8). Verificação por simulação com o modelo de linha de transmissão da Fig. 1 (Fig. 14, p. 8).

## 6. Dados e experimento

Fato do artigo:
- Três estatores idênticos (5 kW, classe F), cada um em câmara ambiental com cabeamento inferior a 1 m; Máquinas 1 e 2 usadas para a validação do EKF (Figs. 9–11), Máquina 3 para a comparação osciloscópio vs. detector de pico (Figs. 16–17) (p. 3, 6–9).
- Estresse: somente térmico; temperatura e duração por máquina na Tabela II (p. 4) [INSERIR VALORES DA TABELA II]. A temperatura era reduzida uma vez por dia para inspeção visual (p. 3).
- Excitação elétrica: pulsos de 160 V CC, 10 kHz, 50 % de ciclo de trabalho, via MOSFET IRFB812 com tempo de subida de 22 ns; "These voltage pulses were not designed to contribute to the degradation of the insulation" (p. 4).
- Aquisição: 1 ms de dados a cada 5 min, 10 transitórios por janela → 1 ponto (p. 4–5). Máquina 3: detector de pico a 10 MSa/s vs. corrente a 1 GSa/s (p. 8); comparação nas últimas 70 h (Fig. 16, p. 9).
- Duração observável: Máquina 1 com dados até além de 100 h antes da falha (p. 7); Máquina 2 com janela de acurácia entre ~60 h e 128 h de operação (p. 7); Fig. 5(b) após 12 dias de ensaio (p. 4).
- Condição de operação: "The circuit used in this experiment in not intended to be used for a machine in operation [...] normal operation was not possible during the accelerated degradation test" (p. 5); "In this paper, the leakage current was collected offline" (p. 5).

Inferência minha: n = 3 estatores, sem repetições por condição, sem dispersão estatística; nenhuma métrica de erro agregada (RMSE, α-λ, PH) é reportada; a acurácia é descrita qualitativamente a partir de gráficos.

## 7. Métricas e resultados numéricos

Métrica usada (fato do artigo, p. 6): comparação gráfica entre RUL prevista pelo EKF e RUL "real" (reta linear decrescente), a cada instante, após conhecida a vida total.

Resultados (fato do artigo):
- Máquina 1: após o pico do overshoot, a RUL prevista "quickly decreased down toward the true RUL line. This decrease happened around after 50 h [...] had an accurate prediction within 20 h of the actual RUL within 100 h until failure occurred" (p. 7; Fig. 10, p. 6).
- Máquina 2: "the accuracy came within 20 h of the real RUL after about 60 and until 128 h of operation; it was within 10 h of the actual RUL near its end of life" (p. 7; Fig. 11, p. 7).
- Ambas: "the RUL converged to the true RUL estimation and remained near the true RUL for some time. Each RUL estimate predicted failure early" (p. 7).
- Pico a pico vs. pico positivo (Máquina 2): "the peak-to-peak and positive overshoot magnitude give a similar prognosis" (Fig. 13, p. 8).
- Máquina 3: RUL calculada da saída do detector de pico (10 MSa/s) "shows a close match to the RUL calculated from the oscilloscope" (1 GSa/s) (Fig. 17, p. 9); redução de duas ordens de grandeza na taxa de amostragem (inferência minha a partir de 1 GSa/s → 10 MSa/s).
- Requisito de amostragem sem detector de pico: ~50 MHz para pico de ~35 ns (p. 7).
- Componentes do detector: diodo t_rr = 4 ns; op-amp 900 V/µs; C ≈ 47 nF (p. 7).

Inferência minha: "within 20 h" com vida total da ordem de 130–200 h corresponde a erro relativo da ordem de 10–15 % da vida total, mas o artigo não calcula esse número; os valores de vida total não constam no texto extraído (Tabela II).

## 8. Limitações

Declaradas pelos autores:
1. (declarada) Hipótese de causalidade única: "it is assumed that any change in the leakage current is due to the insulation degradation only" (p. 2), embora correntes de mancal e outros mecanismos contribuam (p. 2, ref. [26]).
2. (declarada) dV/dt do dispositivo assumido constante; o indicador varia com o tempo de subida (p. 3, Fig. 4).
3. (declarada) Somente estresse térmico; "In real operation, many sources of the stress exist" (p. 3).
4. (declarada) Critério de falha por inspeção visual, sem ensaio normalizado; a inspeção "did not identify the strength of the remaining insulation" (p. 3).
5. (declarada) Medições offline, máquina desmontada (rotor e tampas removidos) (p. 5); o circuito de ensaio "is not intended to be used for a machine in operation" (p. 5).
6. (declarada) Prognóstico pouco informativo enquanto a máquina está sã: "A prognosis is difficult to calculate when the machine is operating normally [...] so prognosis is typically more accurate toward the true end of life" (p. 7).
7. (declarada) Saída do detector de pico inferior ao pico real por atrasos e carga do capacitor (p. 8).
8. (declarada) "The prognosis method presented here, in its current state, may not be perfectly suitable for industrial use" (p. 9).

Identificadas por mim (minha inferência):
9. Tamanho amostral: 3 estatores, sem réplicas por temperatura; impossibilidade de estimar dispersão da vida ou intervalos de confiança da RUL.
10. Tendência não monotônica (sobe até um máximo e depois decai até próximo do valor inicial, p. 6): o limiar de falha (valor inicial) é cruzado apenas na fase de decaimento; se o pico não for detectado (janela de aquisição inadequada ou ruído), α fica mal inicializado e o EKF diverge. O critério "within 96%" é arbitrário e não justificado.
11. O valor inicial da RUL (vida média de datasheet, p. 6) não existe de forma comparável para isolamentos de MT em serviço há décadas; a "RUL verdadeira" linear é uma construção a posteriori, não um dado.
12. Ausência de métricas padronizadas de prognóstico (RMSE, α-λ, horizonte de prognóstico, convergência) e de incerteza sobre a RUL (o EKF fornece P_k, mas o artigo não reporta intervalos).
13. Dependência do comprimento de cabo (< 1 m) e da geometria: em instalações reais, reflexões no cabo alteram a resposta transitória; a comparabilidade entre máquinas é apenas suposta (p. 3).
14. As Tabelas I–III (propriedades do isolamento, temperaturas/durações e parâmetros do EKF) não são discutidas no corpo do texto; a reprodutibilidade depende de valores não comentados.
15. Extensão de escala: horas em câmara vs. anos em serviço; não há fator de aceleração nem modelo térmico que converta a tendência acelerada em tendência de campo.
16. Inconsistência textual: o osciloscópio é descrito como "1-GSa/s bandwidth" (p. 4) e como "capable of sampling up to 10 GSa/s" (p. 7).

## 9. Transferibilidade para o problema-alvo

Problema-alvo: isolamento de estator de motor de indução de MT (2,3–13,8 kV, tipicamente mica-epóxi VPI com gradação de campo, partida direta, chaveado por disjuntor a vácuo), submetido a (a) sobretensões de manobra de VCB (chopping, reignições múltiplas, frentes íngremes, dV/dt elevado) com/sem snubber tiristorizado ativo (Trabalho A) e (b) estresse térmico de partidas de grandes motores sob contingência N-1 com load shedding seletivo (Trabalho B).

Fatos do repositório usados nesta análise: o Olivas Power System Studio implementa, no catálogo de componentes (`app/preprocessor/catalog.py`), chaves VCB/VCB3 com modelo estatístico de reignição parametrizado por I_chop, σ(I_chop), di/dt_crit, d(di/dt), k_dielec, U0_dielec, T_bounce e Seed; um elemento "Thyr" (tiristor); e, em `app/validation/validator_vcb.py`, uma verificação de que instâncias de MODEL VCB_* têm saídas CB_STATE ligadas às entradas de um controlador de snubber (código VCB-0xx). Ou seja, o repositório já simula em ATP transitórios de VCB com dispersão estocástica de corrente de corte e de reignição, e um snubber controlado por estado do disjuntor.

### 9.1 O que se transfere

1. Arquitetura de prognóstico (transfere-se integralmente): indicador → tendência paramétrica → EKF com estados [indicador, α, β] → projeção até limiar → RUL, com avaliação contra RUL linear a posteriori e preferência por previsão conservadora ("Predicting failure to occur slightly before the actual time of failure is desirable", p. 7). Inferência minha: essa cadeia é agnóstica ao indicador; pode ingerir tan δ, capacitância, corrente de fuga a 60 Hz, resistência de isolamento/índice de polarização ou magnitude de descargas parciais de um motor de MT.
2. Fundamento físico compartilhado: degradação → redução de C e R do groundwall → alteração da resposta transitória a um degrau (p. 2–3). Fato do artigo: a referência [2] (Younsi et al.) já mede capacitância e fator de dissipação online em motores CA. Inferência minha: em MT, C e tan δ são os indicadores clássicos de estado do groundwall; a mesma cadeia EKF pode ser aplicada a eles.
3. Princípio de "excitação oportunista": usar o transitório de chaveamento já existente no sistema como estímulo de diagnóstico, sem equipamento adicional (p. 1, 4). Hipótese: os surtos de manobra do VCB (frentes de centenas de ns a poucos µs) são, para o motor de MT, o análogo do degrau do inversor; a resposta de corrente de modo comum (soma das três correntes de fase, p. 4) a cada manobra poderia ser registrada como indicador de tendência, por manobra.
4. Aquisição de baixo custo de picos de alta frequência (detector de pico + filtro de mediana + diferença antes/depois, p. 7–8): transfere-se diretamente como técnica de instrumentação para registrar a amplitude de surtos de VCB nos terminais do motor ou o pico da corrente de modo comum, com amostragem da ordem de 10 MSa/s em vez de GSa/s. Inferência minha: é uma das contribuições mais aproveitáveis para um projeto de monitoramento industrial.
5. Papel do dV/dt constante (p. 3): o artigo exige excitação repetível. Hipótese central para o Trabalho A: um snubber tiristorizado ativo, ao conformar a frente de onda do surto de forma controlada e reprodutível, poderia converter o transitório de manobra — naturalmente estocástico — em um estímulo quase repetível, tornando comparáveis as respostas de corrente de fuga entre manobras sucessivas. Isso permitiria usar o próprio dispositivo de mitigação como gerador de estímulo de diagnóstico. Deve ser testado em ATP com o modelo VCB estocástico do repositório (variando Seed) para quantificar a dispersão do dV/dt residual com e sem snubber.
6. Tratamento de sinal: denoising por wavelet (Daubechies 4, nível 4, p. 5) antes de extrair a feature é transferível a registros de surtos.

### 9.2 O que não se transfere e por quê

1. O indicador específico (overshoot da corrente de fuga a degrau de 160 V com 22 ns de subida) não se transfere diretamente: (i) motores de MT com partida direta não recebem pulsos periódicos e consistentes — não há inversor; (ii) o transitório de VCB é estocástico por natureza (corrente de corte com dispersão σ(I_chop), reignições múltiplas condicionadas a di/dt_crit e à recuperação dielétrica k_dielec/U0_dielec, e T_bounce, exatamente os parâmetros do modelo do repositório), violando a hipótese de dV/dt constante (p. 3); (iii) a frequência de eventos é de manobras por dia/semana, não 10 kHz, o que reduz drasticamente a densidade de pontos da série temporal (o artigo usa 1 ponto a cada 5 min, p. 5).
2. Sistema de isolamento: poliéster + papel de ranhura, BT (p. 2) vs. mica-epóxi VPI com gradação de campo em MT. Inferência minha: em MT, o mecanismo dominante sob surtos íngremes é a distribuição não uniforme de tensão entre espiras da primeira bobina (dV/dt) e a erosão por descargas parciais, fenômenos não considerados no artigo; a tendência "sobe e depois decai" observada (p. 6) não tem razão para se repetir em mica-epóxi.
3. Mecanismo de envelhecimento: térmico uniforme em estufa (p. 3) vs. multiestresse (térmico cíclico de partidas, elétrico impulsivo de manobras, mecânico/eletrodinâmico de partidas, ambiental). O artigo declara que as fontes de estresse que reduzem C podem ser "accounted for" pelo método (p. 3), mas não demonstra.
4. Limiar de falha e RUL inicial: vida de datasheet (p. 6) e valor inicial do overshoot da própria máquina; para motores de MT em serviço, o "valor inicial" não está disponível e a vida de projeto (normalmente décadas) torna o limiar "96 % do valor inicial" inaplicável sem recalibração.
5. Validação: inspeção visual diária com estator desmontado (p. 3) é inviável em campo; a validação em MT exigiria ensaios normalizados (resistência de isolamento/IP, tan δ/tip-up, DP, surge test) como "verdade de campo".
6. Escala temporal: horas até a falha vs. anos; não há no artigo modelo de aceleração (Arrhenius ou similar) que permita converter a tendência acelerada em tendência de campo; a transferência de β entre regimes é hipótese, não fato.
7. Para o Trabalho B (partidas sob N-1): o artigo não modela temperatura como entrada — o EKF em (1) não tem termo de entrada u_k e β é um estado livre. Inferência minha: para ligar o load shedding seletivo (que reduz o afundamento de tensão na partida e, portanto, o tempo de aceleração e o aquecimento I²t do enrolamento) à RUL, seria preciso estender (1) com uma entrada de estresse (temperatura de ponto quente estimada, número de partidas, energia I²t da partida) modulando β, por exemplo β_k = β_0·g(T_k, n_partidas). Isso é hipótese de trabalho, não conteúdo do artigo.

### 9.3 Nota de transferibilidade: 3/5

Justificativa (inferência minha): a arquitetura prognóstica (EKF + tendência paramétrica + limiar + avaliação de RUL), a instrumentação de baixo custo (detector de pico) e o princípio de excitação oportunista transferem-se bem e são diretamente úteis para um método de monitoramento de degradação de isolamento de estator de MT. O indicador, o mecanismo de envelhecimento, o critério de falha, a escala de tensão e a escala temporal não se transferem sem reformulação substancial. A hipótese do snubber tiristorizado como "conformador de estímulo repetível" é o ponto de contato mais promissor com o Trabalho A, mas precisa de verificação por simulação (ATP, modelo VCB estocástico do repositório) e por ensaio.

## 10. Citações literais relevantes

1. "It is common for operators to perform routine maintenance to prevent catastrophic failure; however, such practice may result in replacing components or machines with a significant remaining useful life. The condition-based maintenance allows operators to delay repair until certain thresholds are reached [7]; however, these thresholds do not account for the rate of degradation." (p. 1)
2. "An accurate prognosis can allow the machine to continue normal operation up to the time of failure, as well as, reduce unnecessary costly maintenance and unexpected failures." (p. 1)
3. "In this paper, it is assumed that any change in the leakage current is due to the insulation degradation only." (p. 2)
4. "Even though rise time of semiconductor devices can vary in different operating conditions, the actual dV/dt of the switching device is assumed to be constant for this method to detect changes in the insulation properties." (p. 3)
5. "Other sources of stress were not used to degrade the insulation because thermal stress can be applied in a repeatable manner. In real operation, many sources of the stress exist." (p. 3)
6. "The initial overshoot value, at the beginning of the experiment, is selected as the failure threshold. Failure is defined as the point when the exponential decay is within 96% of the failure threshold." (p. 6)
7. "Prognosis increases in accuracy toward the end of the useful lifetime. For both Machines 1 and 2, the RUL converged to the true RUL estimation and remained near the true RUL for some time. Each RUL estimate predicted failure early. Predicting failure to occur slightly before the actual time of failure is desirable to avoid unexpected failures." (p. 7)
8. "The prognosis method presented here, in its current state, may not be perfectly suitable for industrial use. However, this paper does represents a significant step forward in stator winding insulation prognosis." (p. 9)

## 11. Ligações com RUL, PHM e argumentos de decisão (C-Level)

RUL / PHM (fato do artigo):
- Definição operacional de RUL: tempo até o indicador projetado atingir o limiar; avaliação por comparação com reta linear de RUL real (p. 6). Lição para PHM: convergência tardia ("prognosis is typically more accurate toward the true end of life", p. 7) e viés conservador desejável (p. 7).
- Linhagem metodológica: EKF já aplicado a RUL de MOSFETs [21] e de mancais [22] (p. 2, 5); o próprio grupo aplicou EKF à corrente de fuga em [1] e [23] (p. 2).
- Diagnóstico vs. prognóstico: "Failure prognosis, unlike diagnosis, can be used to assess the rate of degradation" (p. 1).

Argumentos de custo/decisão/manutenção transcritos (fato do artigo):
- Custo de falha: "Depending on the application, a failure in an electrical machine can result in significant down time or a life-threatening accident." (p. 1)
- Custo de manutenção preventiva por calendário: substituição de componentes "with a significant remaining useful life" (p. 1); CBM por limiar "does not account for the rate of degradation" (p. 1).
- Benefício do prognóstico: operar "up to the time of failure" e "reduce unnecessary costly maintenance and unexpected failures" (p. 1).
- Custo de instrumentação: monitorar "preferably while the machine continues operation without any expensive equipment" (p. 1); equipamento de 10 GSa/s "can make this method too expensive" (p. 2); o detector de pico "allowed a lower sampling rate without compromising accuracy of the prognosis" (p. 9).

Inferência minha para o discurso a C-Level: o artigo fornece três mensagens sintetizáveis — (i) RUL é uma trajetória, não um limiar (a taxa de degradação é a informação que decide entre "aguardar" e "intervir"); (ii) a acurácia do prognóstico cresce à medida que o fim de vida se aproxima, o que exige comunicar RUL com incerteza e horizonte de decisão, não como número único; (iii) o custo de aquisição pode ser reduzido em ordens de grandeza pela escolha correta da feature (pico) e do hardware (detector analógico), argumento útil para justificar um sistema de monitoramento computacional de baixo custo integrado à plataforma de simulação existente.
