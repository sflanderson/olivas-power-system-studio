# Fichamento 07 — Vichare e Pecht (2006): Prognostics and Health Management of Electronics

Convenções deste fichamento: "p. N" refere-se ao marcador "===== PAGE N =====" do arquivo de texto extraído (p. 1 = página impressa 222; p. 8 = página impressa 229). Cada afirmação é rotulada como **[fato do artigo]**, **[inferência minha]** ou **[hipótese]** quando houver risco de ambiguidade.

---

## 1. Referência completa

VICHARE, Nikhil M.; PECHT, Michael G. Prognostics and health management of electronics. **IEEE Transactions on Components and Packaging Technologies**, v. 29, n. 1, p. 222–229, mar. 2006. Manuscrito recebido em 12 jan. 2006. Afiliação: Electronic Prognostics and Health Management Research Center, University of Maryland, College Park, MD, EUA (p. 1).

- DOI: o texto extraído traz apenas o prefixo "Digital Object Identifier 10.1109/TCAPT.2006." (p. 1), sem o sufixo numérico. DOI completo: [INSERIR CITAÇÃO].
- ISSN/código de rodapé: "1521-3331/$20.00 © 2006 IEEE" (p. 1).
- Tipo: artigo de revisão (state-of-practice / state-of-research), sem contribuição experimental própria **[fato do artigo, p. 1: "This paper presents the state-of-practice and the current state-of-research"]**.
- Índice de termos declarados: Built-in-test (BIT), prognostics and health management (PHM) (p. 1).

---

## 2. Objetivo do artigo

Apresentar o estado da prática e o estado da pesquisa em PHM de eletrônica, organizando as abordagens em quatro categorias: (1) built-in-test (BIT); (2) fusíveis e dispositivos "canário" (expendable devices); (3) monitoramento e raciocínio sobre precursores de falha; (4) modelagem de dano acumulado a partir de cargas de ciclo de vida medidas in situ. Fornecer exemplos de cada abordagem e discutir desafios de implementação (p. 1, resumo e introdução).

Definições operacionais adotadas pelos autores (p. 1):
- "Saúde" (health): extensão da degradação ou do desvio em relação a uma condição normal esperada.
- "Diagnóstico": detecção e isolamento de faltas ou falhas.
- "Prognóstico": processo de predizer um estado futuro (de confiabilidade) com base em condições atuais e históricas.
- "PHM": método que permite avaliar a confiabilidade de um sistema em suas condições reais de ciclo de vida, determinar o advento da falha e mitigar os riscos do sistema.

Motivação declarada (p. 1): eletrônica é frequentemente o primeiro item a falhar em produtos/sistemas; a degradação em eletrônica é mais difícil de detectar do que em sistemas mecânicos (escala micro/nano, arquitetura complexa, faltas que não necessariamente levam a perda de função); há "significativa escassez de conhecimento sobre precursores de falha em eletrônica".

---

## 3. Sistema/componente e mecanismo(s) de degradação tratados

O artigo é uma revisão; não estuda um único componente. Sistemas e mecanismos citados, por abordagem:

**(a) BIT (Seção II, p. 1–2)** — circuitos, módulos/LRUs e sistemas eletrônicos; exemplos: HP-3325A (1980), sistemas oceanográficos, multichip modules, fontes de alimentação, aviônica, entretenimento de bordo Boeing 767/777; MBIT da Motorola (processador, cache L2, ASIC VMEbus, ECC RAM, EPROM, Flash, NVRAM, RTC); TSMD (time stress measurement device). Mecanismos: faltas funcionais, falhas intermitentes, ambiguidade de isolamento de falta. **[fato do artigo]**

**(b) Fusíveis e canários (Seção III, p. 2–3)** — células prognósticas em nível de semicondutor (Ridgetop "Sentinel Semiconductor") para mecanismos: descarga eletrostática (ESD), hot carrier, migração metálica, ruptura dielétrica (dielectric breakdown), efeitos de radiação (p. 2). Canários em nível de placa (Anderson et al.) para: fadiga de baixo ciclo de juntas de solda e corrosão (p. 3). Princípio: a célula-canário é escalada (menor seção transversal, maior densidade de corrente e/ou maior tensão) para falhar antes do circuito real sob as mesmas cargas (p. 2).

**(c) Precursores de falha (Seção IV, p. 3–5)** — fontes chaveadas, cabos e conectores, CIs CMOS, osciladores VCO de alta frequência (Tabela I, p. 3); CMOS via corrente quiescente Iddq (bridging, opens, transistores parasitas, p. 3); inversores PWM VSI (faltas de transistor em aberto e disparo intermitente, p. 4); elementos de encapsulamento (interconexões de primeiro nível, dielétricos, underfills, semicondutores — Lall et al., p. 4); discos rígidos (SMART, Tabela II, p. 4); servidores Sun (MSET/SPRT, p. 4); GPS comercial (falha de precisão e de solução, p. 5).

**(d) Cargas ambientais/de uso e dano acumulado (Seção V, p. 5–6)** — placa com oito indutores SMD sem terminais soldados em FR-4 com solda eutética Sn-Pb sob o capô de automóvel: mecanismo dominante = fadiga de junta de solda (p. 5); cartões de circuito do Solid Rocket Booster (SRB) do ônibus espacial: vibração e choque, com falha inesperada de suporte de alumínio (p. 5); EEEU do braço robótico SRMS: cargas térmicas e vibracionais (p. 5–6); notebooks: cargas térmicas (p. 6); aviônica via TSMD e data mining (p. 6).

**(e) Integração (Seção VI, p. 6–7)** — conversor cc-cc COTS de 50 W; eletromigração entre metalizações a partir de corrente e temperatura (p. 6–7).

---

## 4. Indicadores/precursores de degradação usados

Nenhum indicador é medido pelos próprios autores neste artigo; a lista a seguir é o que a revisão reporta de terceiros. Unidades e taxas de amostragem só quando explicitadas no texto.

| Indicador / precursor | Grandeza / unidade | Como é medido | Taxa de amostragem | Página |
|---|---|---|---|---|
| Deslocamento da tensão de saída de fonte de alimentação | tensão (V) | monitoração da saída; associado a dano em regulador de realimentação/opto-isolador | não citada | p. 3 |
| Corrente quiescente Iddq (CMOS) | corrente de fuga (A); resolução 10 pA no sensor de Xue e Walker | monitor de corrente embutido (built-in current monitor); QCM mede a cada transição do clock do sistema | "em cada transição do clock"; operação até 100 MHz (Pecuh et al.) | p. 3–4 |
| Corrente transiente Iddt (CMOS) | corrente (A) | corrente de alimentação durante transição após aplicação de entrada | não citada | p. 3 |
| Formas de onda de corrente em inversor PWM VSI | corrente (A) | DWT (transformada wavelet discreta) + lógica fuzzy "se-então" | não citada | p. 4 |
| Taxa de crescimento de fase em interconexões de solda, intermetálicos, tensão normal na interface do chip, tensão de cisalhamento interfacial | grandezas mecânicas/metalúrgicas (unidades não dadas) | "damage proxies" (Lall et al.) | não citada | p. 4 |
| Parâmetros SMART de HDD: altura de voo da cabeça, contagem de erros, variação do tempo de spin, temperatura, taxa de transferência | diversas (unidades não dadas) | interface BIOS–HDD | não citada | p. 4 |
| Telemetria de servidores (Sun): corrente, tensão, temperatura + parâmetros "soft" (cargas, throughput, comprimento de fila, BER) | diversas | sensores já existentes; arquivo circular; resíduo = sinal real − sinal estimado por MSET; alarme por SPRT | alta taxa retida por 72 h; baixa taxa por 30 dias (valores numéricos das taxas não dados) | p. 4 |
| Erro de posição e probabilidade de indisponibilidade (outage) de GPS | erro de posição (unidade não dada); probabilidade | features de sistema via protocolo NMEA 0183; validação por ciclagem térmica acelerada | não citada | p. 5 |
| Temperatura e vibração in situ na placa (LCM) | °C; aceleração (unidade não dada) | sensores na placa em ambiente de aplicação | não citada | p. 5 |
| Histórico temporal de vibração do SRB (pré-lançamento a splashdown) | aceleração | registro a bordo | não citada | p. 5 |
| Parâmetros extraídos de sinal carga-tempo: faixa cíclica (Δs), carga média cíclica (S_mean), taxa de variação (ds/dt) | unidades da carga monitorada | algoritmos embarcados de extração; armazenamento em histogramas binados | não citada | p. 6 |
| Temperaturas internas de notebook (uso, armazenamento, transporte) | °C | OOR (ordered overall range) para picos/vales + Rainflow de três parâmetros (faixa, média, rampa) | não citada | p. 6 |
| Tempo de operação, temperatura, consumo de potência (ELIMA) | h; °C; W | sensores + memória embarcada; GSM ou RFID + Internet | não citada | p. 6 |
| Vibração, temperatura, alimentação, sobrecarga funcional, pressão do ar (aviônica, Skormin et al.) | diversas | TSMD em voo; data mining/clustering | não citada | p. 6 |
| Corrente e temperatura para suscetibilidade a eletromigração | A; °C | coletadas por BIT, usadas com modelos de dano | não citada | p. 6 |

Observação **[inferência minha]**: as Tabelas I (precursores potenciais), II (parâmetros SMART) e III (cargas de ciclo de vida) não tiveram o conteúdo extraído no arquivo de texto; apenas os títulos aparecem (p. 3, 4, 5). Qualquer citação ao conteúdo dessas tabelas deve ser conferida no PDF original: [INSERIR CITAÇÃO].

---

## 5. Modelo/algoritmo

**Classe: revisão** (state-of-practice/state-of-research). O artigo **não contém equações numeradas** nem hiperparâmetros próprios **[fato do artigo, verificado em todas as 8 páginas]**. As "estruturas" apresentadas são taxonomias e fluxos metodológicos (Figs. 1–4), descritos textualmente:

1. **Taxonomia de quatro abordagens** (p. 1): BIT; fusíveis/canários; monitoramento e raciocínio sobre precursores; modelagem de estresse e dano a partir de condições de exposição (uso, temperatura, vibração, radiação).

2. **Canário / distância prognóstica** (Fig. 1, p. 3): sob as mesmas cargas ambientais e operacionais, o canário desgasta mais rápido; a diferença entre a distribuição de falha do canário e a do produto real define a "prognostic distance"; é possível calibrar múltiplos pontos de disparo com múltiplas células espaçadas ao longo da curva da banheira. Sem equação.

3. **Raciocínio sobre precursores** (p. 5): (i) identificar variáveis precursoras; (ii) caracterizar o precursor sob perfil de uso esperado ou acelerado; (iii) desenvolver modelo — "tipicamente um ajuste de curva paramétrico, rede neural, rede bayesiana ou tendência de série temporal do sinal precursor"; pressupõe perfis de uso previsíveis e simuláveis em laboratório.

4. **Arquitetura Sun (MSET + SPRT)** (Fig. 2, p. 4–5): caracterização prévia → modelo MSET (multivariate state estimation technique) aprende correlações entre todas as variáveis → em operação, gera sinal esperado em tempo real → resíduo = diferença aritmética entre série real e série esperada → SPRT (sequential probability ratio test) detecta desvios com base em distribuições (não em limiar único) → alarme. Dados retidos em arquivo circular: alta taxa por 72 h, baixa taxa por 30 dias. Sem equações no artigo.

5. **Life Consumption Monitoring — LCM (CALCE)** (Fig. 3, p. 5; Fig. 4, p. 6): cargas medidas in situ → extração embarcada de parâmetros de carga (Δs, S_mean, ds/dt) → histogramas binados → estimação de distribuições dos parâmetros de carga → modelos físicos de estresse e dano → dano acumulado → vida consumida / vida remanescente. Pré-processamento térmico: OOR + Rainflow de três parâmetros (p. 6). Sem equações no artigo (os modelos de dano estão nas referências [49], [50], [10], [57]).

6. **Integração** (Seção VI, p. 6–7): FMMEA (failure modes, mechanisms and effects analysis) para identificar "elos fracos"; ranqueamento de tempos até a falha por mecanismo; avaliação de risco por severidade e ocorrência antes da implementação de PHM; alternativa: análise de Pareto de falhas reportadas pelo fabricante (caso do conversor cc-cc de 50 W). O mesmo dado de sensor pode alimentar abordagens distintas (ex.: corrente e temperatura → modelo de eletromigração; corrente de alimentação → raciocínio sobre precursor de degradação de transistor).

**Algoritmos citados nominalmente**: DWT + lógica fuzzy (Kanniche e Mamat-Ibrahim); MSET + SPRT (Sun); OOR + Rainflow de três parâmetros (Vichare et al.); data mining/clustering (Skormin et al.); modelos paramétricos de correlação offset-de-feature vs. falha de solução (Brown et al., GPS). Nenhum hiperparâmetro é fornecido **[fato do artigo]**.

---

## 6. Dados e experimento

Nenhum experimento próprio. Casos experimentais de terceiros resumidos:

- **Lufthansa Airbus A320 (Johnson, 1996)**, p. 2: média diária de 2.000 registros de erro no BIT; cerca de 70 correspondiam a faltas reportadas por pilotos; cerca de 70 reportes de pilotos não tinham registro correspondente no BIT; de 17 LRUs substituídas por dia, tipicamente apenas 2 apresentavam falta correlacionada com o reporte.
- **Células prognósticas Ridgetop**, p. 2: processos CMOS de 0,35, 0,25 e 0,18 (unidade "µm" perdida na extração; texto traz "0.18-n"); consumo "aproximadamente 600 mW" conforme texto extraído (**[inferência minha]**: possível perda do prefixo µ na extração — conferir no PDF); área de célula "800 m2 at the 0.25-m process" (texto extraído; provavelmente 800 µm² em processo de 0,25 µm — conferir).
- **Monitor de corrente Pecuh et al.**, p. 4: testado em série de inversores com faltas simuladas de abertura e curto; ambas detectadas; até 100 MHz com efeito desprezível no circuito sob teste.
- **Sensor Xue e Walker**, p. 4: resolução de Iddq de 10 pA; saída digital via scan chain; verificado por fabricação de chip de teste.
- **Sun**, p. 4: dados de sensores existentes em servidores; retenção 72 h (alta taxa) e 30 dias (baixa taxa).
- **GPS (Brown et al.)**, p. 5: caracterização da feature principal em faixa de condições operacionais; validação por ciclagem térmica acelerada; o BIT não deu indicação de falha de solução iminente durante o ensaio.
- **LCM automotivo (Ramakrishnan e Pecht)**, p. 5: placa com 8 indutores SMD leadless em FR-4, solda eutética Sn-Pb, sob o capô, condução normal na região de Washington, DC; temperatura e vibração medidas in situ; "a metodologia LCM previu com precisão a vida remanescente" (sem número).
- **SRB (Mathew et al.)**, p. 5: histórico de vibração do pré-lançamento ao splashdown; falha elétrica não esperada em mais 40 missões; falha inesperada por suporte de alumínio quebrado (perda de vida por choque).
- **EEEU/SRMS (Shetty et al.)**, p. 5–6: perfil térmico e vibracional; modelos de dano + inspeção + ensaio acelerado; expectativa de mais 20 anos de vida.
- **ELIMA (UE)**, p. 6: set. 2001 a fev. 2005; dois protótipos (console de jogos e refrigerador-freezer doméstico) com sensores e memória embarcados.
- **Conversor cc-cc COTS 50 W (Goodman et al.)**, p. 7: análise de Pareto de falhas do fabricante para direcionar o PHM.

Número de amostras/ciclos: não reportado para nenhum caso **[fato do artigo]**.

---

## 7. Métricas e resultados numéricos (com página)

- Quatro metas do PHM: alerta antecipado; minimizar manutenção não programada/estender ciclos; reduzir custo de ciclo de vida (inspeção, downtime, inventário); melhorar qualificação e suporte logístico (p. 1).
- Política CBM+ do DoD (nov. 2002) e DoD 5000.2: PHM "tornou-se requisito para qualquer sistema vendido ao DoD"; pesquisa de 2005 com 11 programas CBM apontou "electronics prognostics" como uma das funcionalidades mais necessárias, "sem consideração de custo" (p. 1).
- BIT A320: 2.000 logs/dia; ~70 coincidentes; ~70 sem log; 17 LRUs/dia substituídas, só 2 com falta correlacionada (p. 2) → **[inferência minha]** taxa de acerto de substituição da ordem de 12 %.
- Células prognósticas: 3 nós de processo; ~600 mW (ver ressalva de extração); ~800 (µ)m² (p. 2).
- Iddq: 100 MHz (Pecuh); 10 pA (Xue e Walker) (p. 4).
- Sun: 72 h / 30 dias de retenção (p. 4).
- SRB: > 40 missões de vida elétrica remanescente (p. 5). EEEU: > 20 anos (p. 6).
- ELIMA: 42 meses de projeto (set. 2001–fev. 2005) (p. 6).
- Conversor cc-cc: 50 W (p. 7).
- Não há métricas de acurácia prognóstica (erro de RUL, horizonte, precisão/recall) em nenhum caso **[fato do artigo]**.

---

## 8. Limitações

**Declaradas pelos autores:**
1. [declarada] Degradação em eletrônica é difícil de detectar (escala micro/nano; faltas não implicam perda de função); escassez de conhecimento sobre precursores (p. 1).
2. [declarada] BIT sofre de alarmes falsos e ambiguidade de isolamento de falta; foi usado como diagnóstico, não prognóstico; restrito a sistemas de baixo volume; muitas falhas podem ser reais mas intermitentes (p. 2).
3. [declarada] Canários: questões abertas sobre reenergização após troca, arquiteturas protetivas pós-reparo, requalificação de sistemas legados, área ocupada em silício/placa e recuperação do custo adicional (p. 3).
4. [declarada] Raciocínio sobre precursores pressupõe perfis de uso previsíveis e simuláveis; mudança não caracterizada de perfil gera falso alarme; caracterização "pode ser demorada, custosa e pode não funcionar" (p. 5).
5. [declarada] Necessidade de reduzir memória e consumo do dispositivo de monitoração (p. 6).
6. [declarada] Nanossensores MTE: nenhum produto ou protótipo desenvolvido (p. 4).

**Identificadas por mim:**
7. [minha inferência] Ausência total de equações, modelos de dano explícitos e métricas de desempenho prognóstico; o artigo é um mapa, não um método.
8. [minha inferência] Recorte em eletrônica de baixa tensão/encapsulamento; nada sobre dielétricos de alta/média tensão, descargas parciais, envelhecimento térmico-elétrico de isolação sólida (Arrhenius, lei de potência inversa) ou máquinas rotativas.
9. [minha inferência] Viés de autocitação: parcela substancial dos casos é do próprio grupo CALCE (refs. [10], [16], [26], [29], [31], [49]–[52], [57], [61]); a afirmação "LCM previu com precisão" (p. 5) não vem acompanhada de número.
10. [minha inferência] Abordagem MSET/SPRT é descrita sem discutir condições de treinamento, drift ou não estacionariedade — pontos críticos para motores com regime variável.
11. [minha inferência] Datado (2006): não aborda aprendizado profundo, quantificação de incerteza bayesiana em RUL, nem métricas padrão de prognóstico (prognostic horizon, α-λ), que só se consolidaram depois.
12. [minha inferência] Tabelas I–III (núcleo do conteúdo sobre precursores e cargas) não legíveis no texto extraído; risco de citação incompleta.

---

## 9. Transferibilidade para o problema-alvo

**Problema-alvo**: isolamento de estator de motor de indução MT (2,3–13,8 kV) submetido a (a) sobretensões de manobra de VCB (chopping, reignições múltiplas, frentes íngremes/dV/dt) com/sem snubber tiristorizado ativo; (b) estresse térmico de partidas de grandes motores sob contingência N-1 com load shedding seletivo.

### O que se transfere

1. **Arquitetura "cargas medidas in situ + modelo físico de dano → vida consumida" (LCM, p. 5–6)** — transfere-se diretamente como esqueleto do método. **[hipótese]** Mapeamento: sinal carga-tempo = tensão terminal do motor durante manobra do VCB (amostrada com largura de banda de MHz) e temperatura de enrolamento durante partidas; parâmetros extraídos = amplitude de pico da sobretensão, dV/dt de frente, número de reignições por manobra, energia de surto (para a); faixa cíclica de temperatura Δθ, θ_mean, taxa de aquecimento dθ/dt por partida (para b); histogramas binados por classe de severidade; modelo de dano = regra de acumulação (ex.: Miner) sobre modelo de envelhecimento elétrico-térmico. O snubber tiristorizado entra como modificador da distribuição das cargas (reduz dV/dt e reignições), e o load shedding N-1 como modificador do perfil térmico das partidas — ambos avaliáveis pela mesma contabilidade de dano.
2. **Pré-processamento Rainflow de três parâmetros + OOR (p. 6)** — transfere-se sem alteração para o histórico térmico de partidas (b); para (a) o análogo é contagem de eventos de surto por classe de amplitude/dV/dt **[inferência minha]**.
3. **Pipeline MSET + SPRT sobre resíduos (p. 4)** — transfere-se como camada de detecção de anomalia sobre indicadores de isolação (corrente de fuga, tan δ, capacitância, atividade de descarga parcial, temperatura) correlacionados com carga e ambiente; a decisão por distribuição em vez de limiar único é diretamente aplicável.
4. **Passo inicial via FMMEA e ranqueamento de mecanismos por tempo até a falha, severidade e ocorrência (p. 6–7)** — transfere-se como método de priorização entre mecanismos do isolamento (erosão por DP em cavidades, delaminação térmica, degradação de espira-espira por surtos íngremes, etc.).
5. **Conceito de canário com distância prognóstica calibrada (p. 2–3)** — **[hipótese]** análogo: corpos de prova de isolação (barras/bobinas-sentinela) instalados no mesmo barramento, com espessura reduzida ou estresse escalado, ensaiados periodicamente; ou uso da própria distribuição de sobretensões medida como "canário estatístico". Requer calibração por ensaio acelerado, como o artigo prescreve.
6. **Princípio "o mesmo dado alimenta várias abordagens" (p. 6)** — o registro de manobras do VCB serve tanto ao modelo de dano quanto ao raciocínio sobre precursores.
7. **Estrutura de argumentação para decisão (Seção I e III)** — as quatro metas e a exigência de recuperação do custo de PHM transferem-se integralmente ao contexto industrial (ver Seção 11).

### O que NÃO se transfere e por quê

1. Precursores específicos (Iddq, Iddt, fadiga de junta de solda, intermetálicos, SMART de HDD, NMEA de GPS) — mecanismos e escalas físicas alheios a dielétricos de MT.
2. Hardware de canário em silício (Ridgetop) e nanossensores MTE — sem correspondência para isolação de estator.
3. Modelos físicos de dano — o artigo não os fornece; para o alvo é preciso buscar modelos de envelhecimento elétrico-térmico de isolação (ex.: lei de potência inversa, Arrhenius, modelos de vida sob impulsos repetitivos) em outras fontes: [INSERIR CITAÇÃO].
4. Validação — o artigo não traz protocolo de validação nem métricas; a validação do método-alvo terá de ser desenhada com ensaios acelerados em bobinas/barras (impulsos repetitivos com dV/dt controlado; ciclagem térmica) — não há suporte quantitativo aqui.
5. Suposição de perfil de uso previsível (p. 5) — para motores em plantas de processo sob contingências N-1 o perfil é intrinsecamente variável; o próprio artigo alerta que isso gera falsos alarmes em modelos de precursor não caracterizados para tal variabilidade. Isso pesa a favor da abordagem 4 (dano por carga medida), que não depende de perfil fixo.
6. Taxas de amostragem e arquitetura de dados (72 h/30 dias) — foram pensadas para telemetria de servidor; para surtos de VCB é necessária aquisição em alta taxa por evento (disparada por manobra), não contínua — diferença de arquitetura **[inferência minha]**.

### Nota de transferibilidade: **3/5**

Justificativa: fornece o arcabouço conceitual e arquitetural (taxonomia, LCM, MSET/SPRT, FMMEA-first, canário, data reduction) que estrutura o método-alvo e a narrativa de RUL para decisão, mas não traz nenhum indicador, modelo, dado ou métrica aplicável ao isolamento de MT; tudo o que é quantitativo tem de vir de outras fontes.

---

## 10. Citações literais relevantes (máx. 8)

1. "Here, health is defined as the extent of degradation or deviation from an expected normal condition." (p. 1)
2. "'Prognostics' is the process of predicting a future state (of reliability) based on current and historic conditions. Prognostics and health management (PHM) is a method that permits the reliability of a system to be evaluated in its actual life-cycle conditions, to determine the advent of failure, and mitigate the system risks." (p. 1)
3. "Of the seventeen line-replaceable units replaced daily, typically only two were found to have faults that correlated with the fault indicated by the reports." (p. 2)
4. "Canaries can be calibrated to provide sufficient advance warning of failure (prognostic distance) to enable appropriate maintenance and replacement activities." (p. 3)
5. "Finally, the company has to ensure that the additional cost of implementing PHM can be recovered through increased operational and maintenance efficiencies." (p. 3)
6. "Based on the characterization, a model is developed—typically a parametric curve-fit, neural-network, Bayesian network, or a time-series trending of a precursor signal. This approach assumes that there is one or more expected usage profiles that are predictable and can be simulated in a laboratory setup." (p. 5)
7. "If one can measure these loads in-situ, the load profiles can be used in conjunction with damage models to assess the degradation due to cumulative load exposures." (p. 5)
8. "In fact, different approaches can be implemented based on the same sensor data." (p. 6)

---

## 11. Ligações com RUL, PHM e C-Level

**RUL / PHM (fatos do artigo):**
- Definição de prognóstico como predição de estado futuro de confiabilidade (p. 1) e de PHM como avaliação de confiabilidade nas condições reais de ciclo de vida (p. 1).
- Duas rotas explícitas para RUL: (i) precursor → modelo de correlação → vida residual (Lall et al., p. 4; Brown et al., p. 5); (ii) cargas medidas → modelo físico de dano → vida consumida/remanescente (LCM, p. 5–6). O artigo observa que a rota (i), na versão de Lall, "elimina a necessidade de conhecimento de estresses operacionais prévios ou posteriores" e serve a peças reimplantadas (p. 4) — argumento útil para motores legados sem histórico de manobras **[inferência minha]**.
- BIT "geralmente não foi projetado para fornecer prognóstico ou vida útil remanescente" (p. 2) — distinção diagnóstico vs. prognóstico que deve aparecer na tese.
- Resultados de RUL citados: SRB > 40 missões (p. 5); EEEU > 20 anos (p. 6).

**C-Level / custo / decisão / manutenção (transcrições com página):**
- Metas do PHM (p. 1): "1) advance warning of failures; 2) minimizing unscheduled maintenance, extending maintenance cycles, and maintaining effectiveness through timely repair actions; 3) reducing the life-cycle cost of equipment by decreasing inspection costs, downtime, and inventory; and 4) improving qualification and assisting in the design and logistical support of fielded and future systems."
- "In recent years, PHM has emerged as one of the key enablers for achieving efficient system-level maintenance and lowering life-cycle costs." (p. 1)
- CBM+ (nov. 2002): "shift unscheduled corrective equipment maintenance of new and legacy systems to preventive and predictive approaches that schedule maintenance based upon the evidence of need." (p. 1)
- DoD 5000.2: "program managers shall optimize operational readiness through affordable, integrated, embedded diagnostics and prognostics [...]" (p. 1); pesquisa de 2005 com 11 programas CBM: "electronics prognostics" como uma das funcionalidades mais necessárias "without regard for cost" (p. 1).
- Custo de falsos alarmes de BIT: "BIT can be prone to false alarms and can result in unnecessary costly replacement, re-qualification, delayed shipping, and loss of system availability." (p. 2)
- Recuperação do investimento: citação 5 acima (p. 3).
- Risco de projeto: "the characterization and model development process can often be time-consuming and costly and may not work." (p. 5)
- Visão de cadeia de suprimentos (p. 7): sensores com algoritmos embarcados → detecção, diagnóstico e prognóstico de vida remanescente "that would ultimately drive the supply chain"; informação prognóstica via telemetria sem fio para oficiais de manutenção; RFID para localizar peças; portal web seguro para aquisição de peças de reposição "on an as-needed basis".

**Uso sugerido na tese e na entrega computacional [inferência minha]:** a Seção I (metas 1–4) e as passagens de p. 2–3 e p. 5 fornecem a "linguagem de C-Level" para justificar o método: transformar manutenção corretiva de motores MT em manutenção baseada em evidência, com contabilidade explícita de (i) custo de falsos alarmes, (ii) custo de caracterização/modelagem e (iii) recuperação via redução de paradas não programadas — os três itens que o artigo lista como condições de sucesso. A conexão com os trabalhos A (snubber) e B (load shedding N-1) é a de que ambos são intervenções que alteram a distribuição de cargas medida in situ, e o método de monitoramento de degradação é o que permite quantificar, em vida consumida, o benefício de cada intervenção — argumento de decisão de investimento **[hipótese]**.
