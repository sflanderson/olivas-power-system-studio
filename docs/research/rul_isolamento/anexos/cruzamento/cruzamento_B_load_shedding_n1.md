# Cruzamento com o Documento B — load shedding seletivo para partida de grandes motores sob N-1 (NSGA-II/III + surrogates) e consumo de vida do isolamento

**Documento-alvo:** "Selective Load Shedding for the Switching of Large Motors Under N-1 Contingency: Constrained Multiobjective Optimization with NSGA-II, NSGA-III and Regression Surrogates", primeira submissão, SEPOC 2026, autores omitidos para revisão cega [FATO: doc B, p. 1]. Texto integral em `papers_AB/txt/B_sepoc_load_shedding.txt`; fichamento verificado em `out/fichamentos_AB/B_load_shedding_n1_nsga.md`.

**Finalidade:** derivar, a partir dos números reais do Documento B, o perfil de estresse térmico e eletromecânico que partidas sob N-1 impõem ao isolamento de estator de motores de indução de média tensão; propor como o consumo de vida entra na formulação (1)–(4) de B ("health-aware load shedding"); mapear os 13 artigos de apoio; inventariar o que o Olivas Power System Studio já entrega; e definir o experimento computacional mínimo.

**Convenção de rótulos (regra "zero suposição"):** [FATO: doc B, p. N]; [FATO: doc A, p. N]; [FATO: artigo NN, p. N] (numeração dos 13 artigos conforme mapa dos fichamentos); [NORMA: id, cláusula/tabela]; [LITERATURA: ref verificada + URL]; [REPO: caminho:linha] (commit `26d9248`, verificado nesta sessão); [CÁLCULO PRÓPRIO: fórmula] (script `out/cross/calc_B_stress.py`, executado nesta sessão); [INFERÊNCIA FÍSICA: derivação]; [HIPÓTESE]; [FATO: ausência] (verificado por leitura integral). Páginas dos artigos e dos documentos A/B seguem os marcadores `===== PAGE N =====` dos arquivos de texto.

**Advertência sobre a premissa "5 a 7 reignições por ciclo":** no Documento B a expressão "5 to 7 times" refere-se ao múltiplo da corrente de rotor bloqueado ("The locked-rotor current, typically 5 to 7 times the rated value at a power factor near 0.2") [FATO: doc B, p. 1]; não há reignição, VCB ou sobretensão de manobra em B [FATO: ausência]. A premissa permanece [HIPÓTESE do usuário], sem suporte em A ou B.

---

## 1. O que o Documento B fornece e o que não fornece

### 1.1 Números reais de B reutilizados neste cruzamento

| Grandeza | Valor | Rótulo |
|---|---|---|
| Motor alvo | 1250 kW, cos φ = 0,89, barra 4,16 kV | [FATO: doc B, p. 2] |
| Modelo do alvo no snapshot INRUSH | carga de impedância constante, rotor bloqueado, $K_{ir}$ = 6,5, $\cos\varphi_{lr}$ = 0,20 | [FATO: doc B, p. 2] |
| Fonte | 13,8 kV, $I_{cc3\varphi}$ = 15 kA, X/R = 12 | [FATO: doc B, p. 2] |
| Transformadores | 2 × 7,5 MVA (AN) / 9 MVA (AF), $X_{HL}$ = 8 % na base 7,5 MVA, ΔYn; N-1 = um fora, o remanescente em AF | [FATO: doc B, p. 2] |
| Carga | 20 motores (75–1100 kW + alvo) e 3,6 MW estáticos; demanda plena 18,2 MVA | [FATO: doc B, p. 2] |
| $V_{\min}^{(\mathrm{INRUSH})}$ sem corte | 0,755 pu | [FATO: doc B, p. 2 e p. 3] |
| $V_{\min}^{(\mathrm{INRUSH})}$ das soluções (Tabela III) | 0,850 (M_710 + M_800 mantidas; $f_5$ = 7417 kW; $f_4$ = 43,2 kW); 0,858 (M_800; 8127 kW; 34,6 kW); 0,866 (nenhuma; 8927 kW; 26,5 kW) | [FATO: doc B, p. 3, Tabela III] |
| Limites | $V^{ir}$ = 0,85 pu (ANSI 27, "típico"); $V^{sw}$ = 1,08 pu; $S_{AF}$ = 9 MVA (pickup ANSI 49) | [FATO: doc B, p. 2] |
| Duração do inrush | "about 10 s", declarada, não derivada | [FATO: doc B, p. 2]; [FATO: ausência de base numérica] |
| Carregamento do trafo | 1,38 × $S_{AF}$ durante o inrush ("invisible to the thermal element"); 7,31 MVA sustentado = 81 % AF / 97 % AN; 2,03 × $S_{AF}$ com todas as máquinas | [FATO: doc B, p. 3] |
| Otimização | µ = 40, G = 20, 800 avaliações, sementes 42–51, constraint domination, HV, Wilcoxon α = 0,05 | [FATO: doc B, p. 3] |
| Resultado metodológico | NSGA-III 23 % abaixo da busca aleatória com 5 objetivos (degenerada); +49 % sobre aleatória e 96,5 % do NSGA-II com 3 objetivos + 3 restrições | [FATO: doc B, p. 2–4] |
| Surrogate | ridge quadrático sobre 19 bits + interações par a par: $R^2$ = 0,9999, MAE = 8,5 × 10⁻⁵ pu para $V_{\min}^{(\mathrm{INR})}$; random forest $R^2$ = 0,977; 14 343 cenários | [FATO: doc B, p. 5, Tabela VI] |
| Custo | ≈ 25 ms por avaliação (4 fluxos OpenDSS) | [FATO: doc B, p. 5] |

Verificações aritméticas: 2^19 = 524 288 cenários [FATO: doc B, p. 1]; 800 × 25 ms = 20 s por execução; 524 288 × 25 ms ≈ 3,64 h de enumeração exaustiva sequencial [CÁLCULO PRÓPRIO: produto]; 1,38 × 9 = 12,4 MVA; 2,03 × 9 = 18,3 MVA ≈ 18,2 MVA de demanda plena; 7,31/9 = 0,812; 7,31/7,5 = 0,975 [CÁLCULO PRÓPRIO], coerentes com o texto.

### 1.2 O que B não modela (verificado por leitura integral)

1. Térmica do MOTOR: nenhuma réplica térmica de motor, constante de tempo, temperatura de enrolamento ou classe térmica; a ANSI 49 de B é do transformador [FATO: doc B, p. 2, Tabela I]; [FATO: ausência].
2. Tempo de aceleração: sem curva conjugado–velocidade, conjugado de carga, inércia ou integração dinâmica; os quatro snapshots são fluxos quase-estáticos [FATO: doc B, p. 2]; validação dinâmica é trabalho futuro [FATO: doc B, p. 6].
3. $I^2t$, curvas de limite térmico, número de partidas, envelhecimento, RUL: as palavras "aging", "insulation", "lifetime", "remaining useful life", "degradation" não ocorrem [FATO: ausência].
4. Efeito do afundamento sobre as máquinas mantidas (escorregamento, reaceleração, queda de contatores): o único efeito considerado é a atuação da ANSI 27 via $g_1$ e $N_{viol}$ [FATO: doc B, p. 1–3]; [FATO: ausência].
5. Religamento das máquinas cortadas após a partida do alvo: não modelado [FATO: ausência]. Consequência (Seção 3): cada máquina cortada terá de ser religada, o que é um evento de partida adicional.
6. Lista das 19 máquinas (potência, fp, rendimento, $I_{LR}$): remetida aos CSV do repositório retido [FATO: doc B, p. 3]; a soma das 19 potências nominais é 8927 kW (Tabela III, ponto "none") [CÁLCULO PRÓPRIO a partir de doc B, p. 3]; M_710 e M_800 aparentam codificar kW (8927 − 7417 = 1510 = 710 + 800) [INFERÊNCIA a partir de doc B, p. 3].

---

## 2. Perfil de estresse térmico/eletromecânico imposto ao isolamento pela partida sob N-1

### 2.1 Cadeia causal (o que B fornece e onde termina)

$$
\underbrace{s \;\to\; V_{\min}^{(\mathrm{INRUSH})}(s)}_{\text{B fornece (fluxo de potência)}}
\;\to\;
\underbrace{T_m \propto V^2,\; I \propto V \;\to\; t_{acc}(V) \;\to\; I^2t \;\to\; \Delta\theta_{hs} \;\to\; \Delta L_{\text{vida}}}_{\text{B NÃO fornece; derivado abaixo}}
$$

Cada seta à direita é uma [INFERÊNCIA FÍSICA] apoiada em norma ou literatura verificada, com os parâmetros ausentes em B marcados como [HIPÓTESE].

### 2.2 Tensão de barra → corrente e conjugado

**Corrente.** Com o alvo representado como impedância constante de rotor bloqueado [FATO: doc B, p. 2], $I_{start} = K_{ir}\, I_n\, (V_t/V_n)$ [INFERÊNCIA FÍSICA: definição de carga de impedância constante]. A IEEE 399-1997, 9.3.1, afirma que durante a partida "a motor draws an inrush current directly proportional to terminal voltage" [NORMA: IEEE Std 399-1997, 9.3.1, p. 235; LITERATURA: amostra https://www.elecenghub.com/NewSamples/IEEE/181347463/IEEE-399-1997-2.pdf]. O repositório usa a mesma relação: `I_during_A = I_LR_A * V_during_pu / case.bus_pre_fault_voltage_pu` [REPO: app/postprocessor/motor_starting.py:505].

**Conjugado.** "The locked-rotor and breakdown torque will be proportional to the square of the voltage applied" [NORMA: NEMA MG 1, 14.30, via Bonnett & Boteler 2001, p. 2 (PDF); LITERATURA: https://www.aceee.org/files/proceedings/2001/data/papers/SS01_Panel2_Paper27.pdf]; "Only 25 % torque is available … with 50 % of rated voltage" [NORMA: IEEE Std 399-1997, 9.3.1, p. 235].

**Níveis críticos.** A IEEE 3002.7-2018 fixa 80 % nos terminais do motor em partida, 70 % nos terminais dos demais motores que devem reacelerar e 85 % para contatores CA [NORMA: IEEE Std 3002.7-2018, tabela de níveis críticos de tensão, reproduzida por Nivelo et al., IPST 2021, p. 2; LITERATURA: https://www.ipstconf.org/papers/Proc_IPST2021/21IPST112.pdf]. O $V^{ir}$ = 0,85 pu de B [FATO: doc B, p. 2] coincide com o nível de contator CA e é mais conservador que os 80 % dos terminais do motor [INFERÊNCIA a partir de doc B e da tabela citada].

Tabela 2.1 — Grandezas relativas nas quatro condições de B [CÁLCULO PRÓPRIO: $V^2$, $K_{ir}V$; tensões de doc B, p. 2–3]:

| Condição (doc B) | $V_t$ [pu] | $T_m/T_m(1)$ = $V^2$ | $I/I_{LR}(1)$ = $V$ | $I/I_n$ = 6,5·$V$ | $S_{inrush}/S_{inrush}(1)$ = $V^2$ |
|---|---|---|---|---|---|
| Sem corte (infactível em B) | 0,755 | 0,570 | 0,755 | 4,91 | 0,570 |
| Mínimo corte (M_710 + M_800) | 0,850 | 0,7225 | 0,850 | 5,52 | 0,7225 |
| Joelho (M_800) | 0,858 | 0,736 | 0,858 | 5,58 | 0,736 |
| Mínimas perdas (nenhuma) | 0,866 | 0,750 | 0,866 | 5,63 | 0,750 |

Observação: a corrente absoluta é menor sob afundamento (4,91–5,63 × $I_n$ contra 6,5 × $I_n$), mas o conjugado cai mais depressa ($V^2$), de modo que a aceleração se alonga e a integral $I^2 t$ cresce; é o alongamento, não a amplitude, que domina o estresse [INFERÊNCIA FÍSICA; coerente com IEEE 399 cap. 9: "High-inertia loads increase motor-starting time, and heating in the motor due to high currents drawn during starting can be intolerable" [NORMA: IEEE Std 399-1997, cap. 9, p. 234]].

### 2.3 Tempo de aceleração

Equação do movimento [INFERÊNCIA FÍSICA: dinâmica de rotação]:

$$
J\,\frac{d\omega}{dt} = T_m(\omega)\left(\frac{V_t}{V_n}\right)^2 - T_L(\omega)
\quad\Rightarrow\quad
t_{acc}(V_t) = \int_0^{\omega_f}\frac{J\,d\omega}{T_m(\omega)\,(V_t/V_n)^2 - T_L(\omega)}
\tag{E1}
$$

A IEEE 399 exige, para estudo de aceleração, $Wk^2$ do motor e da carga e curvas conjugado–velocidade [NORMA: IEEE Std 399-1997, cap. 9, p. 239]. O Olivas implementa a aproximação de conjugado médio $t = J\cdot 0{,}95\,\omega_s/(T_{m,avg} - T_{L,avg})$, com $T_{m,avg} = k_T T_n$ e $T_{L,avg} = f_L k_L T_n$ ($f_L$ = 1, 1/2, 1/3, 1/4 para carga constante, linear, quadrática, cúbica) [REPO: app/postprocessor/motor_starting.py:410-453; fatores em :148-168], **sem dependência da tensão** [REPO: motor_starting.py:410-453 — nenhum uso de `V_during_pu`]. Introduzindo $V^2$ no conjugado motor:

$$
\frac{t_{acc}(V)}{t_{acc}(1)} = \frac{k_T - f_L k_L}{k_T V^2 - f_L k_L},
\qquad
V_{stall} = \sqrt{\frac{f_L k_L}{k_T}}
\tag{E2}
$$

[INFERÊNCIA FÍSICA: razão das expressões de conjugado médio; independe de $J$, $\omega_s$ e $T_n$]. Abaixo de $V_{stall}$ o motor não acelera (a função do repositório retorna `inf` quando $T_{m,avg} \le T_{L,avg}$ [REPO: motor_starting.py:446-447]).

Tabela 2.2 — Razões $t_{acc}(V)/t_{acc}(1)$ e $I^2t(V)/I^2t(1)$ (este último $= V^2 \cdot t/t_1$) para as tensões de B [CÁLCULO PRÓPRIO: (E2); $k_T$, $k_L$, $f_L$ são [HIPÓTESE] — B não informa conjugado de partida nem tipo de carga]:

| Caso ([HIPÓTESE]) | $V_{stall}$ | 0,755 pu | 0,850 pu | 0,858 pu | 0,866 pu |
|---|---|---|---|---|---|
| $k_T$ = 0,7; carga quadrática $k_L$ = 1 ($f_L$ = 1/3) | 0,690 | t: 5,58×; $I^2t$: 3,18× | 2,13×; 1,54× | 2,01×; 1,48× | 1,91×; 1,43× |
| $k_T$ = 1,0; carga quadrática ($f_L$ = 1/3) | 0,577 | 2,82×; 1,61× | 1,71×; 1,24× | 1,65×; 1,22× | 1,60×; 1,20× |
| $k_T$ = 0,7; carga constante $k_L$ = 0,5 ($f_L$ = 1) | 0,845 | não acelera | 34,8×; 25,1× | 13,1×; 9,6× | 8,0×; 6,0× |
| $k_T$ = 1,0; carga constante $k_L$ = 0,5 ($f_L$ = 1) | 0,707 | 7,14×; 4,07× | 2,25×; 1,62× | 2,12×; 1,56× | 2,00×; 1,50× |

Leituras: (i) na condição que B declara infactível (0,755 pu) a partida pode simplesmente não completar para cargas de conjugado constante com $k_T$ modesto; (ii) mesmo na solução "mínimo corte" de B (0,850 pu, restrição $g_1$ ativa) o tempo de aceleração é 1,7–2,3 vezes o de tensão plena para carga quadrática e pode ser uma ordem de grandeza maior perto da tensão de estagnação; (iii) a diferença entre as três soluções factíveis de B (0,850–0,866 pu) é pequena em $V$ mas não desprezível em $t_{acc}$ e $I^2t$ — o objetivo/restrição de vida (Seção 3) distingue o que $g_1$ trata como equivalente [INFERÊNCIA a partir da Tabela 2.2]. O modelo de conjugado médio superestima a sensibilidade perto de $V_{stall}$ (aproximação grosseira da curva real); a IOGP S-704 exige margem de conjugado acelerante ≥ 10 % a 80 % de tensão e aceleração garantida a 80 % [NORMA: IOGP S-704 v2.0, 9.12.1.2–9.12.1.3; LITERATURA: https://www.iogp.org/bookstore/wp-content/uploads/sites/2/2024/11/S-704v2024-11-TRS-REDLINE.pdf], o que, se atendido pelo alvo, exclui os casos "não acelera" acima de 0,80 pu [INFERÊNCIA].

Um estudo comparativo em plataforma offshore mostrou que quedas de tensão de snapshot e de domínio do tempo diferem em geral < ±0,5 % (máx. 4,31 %), mas só o domínio do tempo entrega tempo de aceleração, escorregamento e conjugado [LITERATURA: Nivelo et al., IPST 2021, p. 1, 7–8, URL acima]. Isso valida o uso do $V_{\min}^{(\mathrm{INRUSH})}$ de B como entrada de (E1) e, ao mesmo tempo, mostra que B para exatamente onde a informação térmica começa [INFERÊNCIA].

### 2.4 $I^2t$ e capacidade térmica (rotor bloqueado a quente)

Com corrente aproximadamente constante durante a aceleração (limite superior conservador):

$$
I^2t(V) \approx I_{start}^2\, t_{acc}(V) = (K_{ir} I_n)^2\, V^2\, t_{acc}(V)
\tag{E3}
$$

$$
U(V) = \frac{I^2t(V)}{I_{LR}^2\, t_{LR,hot}} = \frac{V^2\, t_{acc}(V)}{t_{LR,hot}}
\tag{E4}
$$

[INFERÊNCIA FÍSICA: efeito Joule com $R$ constante; normalização pela capacidade térmica de rotor bloqueado a quente]. O repositório já define a capacidade $K = t_E\,(I_{LR}/FLA)^2$ e $t(I) = K/(I/FLA)^2$ [REPO: app/postprocessor/tcc_damage.py:551-557, 559-578], com uma única curva, sem HOT/COLD e com constante de tempo única [REPO: tcc_damage.py:518-527].

Base normativa: a IEEE 620 padroniza a apresentação das curvas de limite térmico de máquinas gaiola ≥ 250 hp, "plots of the limiting temperature of the rotor and stator in units of I²t", com condições iniciais "fria" e "quente" [NORMA: IEEE Std 620-2022, escopo; LITERATURA: https://www.en-standard.eu/ieee-620-2022-ieee-guide-for-the-presentation-of-thermal-limit-curves-for-squirrel-cage-induction-machines/; Zocholl & Benmouyal 2001, p. 2 (PDF 3), https://wprcarchives.org/wp-content/uploads/2024/07/STANLEY-E.-ZOCHOLL_USING-THERMAL-LIMIT-CURVES-TO-DEFINE-THERMAL-MODELS-OF-INDUCTION-MOTORS_2001.pdf]. Zocholl escreve $U_L = I_L^2 T_A$ (capacidade até o limite, a frio) e $U_O = I_L^2 (T_A - T_O)$ (parcela ocupada pela temperatura de operação), de modo que $I_L^2 T_O$ é a capacidade entre a temperatura de operação e o limite [LITERATURA: Zocholl 2007/2012, eqs. (19)–(21), p. 4–5 (PDF), https://cdn.selinc.com/assets/Literature/Publications/Technical%20Papers/6276_OptimizingThermalModels_SZ_20070226_Web.pdf]. Exemplo de 7 000 hp/900 rpm: $I_{LR}$ = 6,3 pu, $t_{LR}$ frio 14 s, quente 12 s, $\tau_{estator}$ = 950 s [LITERATURA: idem, p. 6 (PDF 7)]. **Advertência:** com resistência rotórica fixa "the relay … overestimates the temperature during valid start"; em partida válida de alta inércia o rotor atinge só 72 % do limite enquanto o modelo $I^2t$ dispara [LITERATURA: idem, p. 4–5 (PDF)]. Logo (E3)–(E4) são limite superior e devem ser declaradas como tal.

Tabela 2.3 — Fração $U$ da capacidade térmica quente consumida por partida, e $t_{acc}$ absoluto, para $t_{acc}(1)$ = 4 s ou 6 s e $t_{LR,hot}$ = 10, 12, 20 s [CÁLCULO PRÓPRIO: (E2), (E4); todos os parâmetros [HIPÓTESE], carga quadrática]:

| $t_{acc}(1)$; $t_{LR,hot}$ | $k_T$ | 0,755 pu | 0,850 pu | 0,858 pu | 0,866 pu |
|---|---|---|---|---|---|
| 4 s; 10 s | 0,7 | U = 1,27 (t = 22,3 s) | 0,61 (8,5 s) | 0,59 (8,1 s) | 0,57 (7,7 s) |
| 4 s; 10 s | 1,0 | 0,64 (11,3 s) | 0,50 (6,9 s) | 0,49 (6,6 s) | 0,48 (6,4 s) |
| 6 s; 12 s | 0,7 | 1,59 (33,5 s) | 0,77 (12,8 s) | 0,74 (12,1 s) | 0,72 (11,5 s) |
| 6 s; 12 s | 1,0 | 0,80 (16,9 s) | 0,62 (10,3 s) | 0,61 (9,9 s) | 0,60 (9,6 s) |
| 6 s; 20 s | 0,7 | 0,95 (33,5 s) | 0,46 (12,8 s) | 0,44 (12,1 s) | 0,43 (11,5 s) |

Leituras: (i) a partida sem corte (0,755 pu) consome, nos casos hipotéticos, entre 64 % e 159 % da capacidade térmica quente — isto é, pode exceder o limite térmico (U > 1) mesmo que a partida complete; (ii) os "10 s" de inrush declarados por B [FATO: doc B, p. 2] são da mesma ordem de $t_{LR,hot}$ típicos (10–20 s) [LITERATURA: Zocholl, exemplo 12 s; PSRC C37.96: "assume … acceleration = 10 s" quando desconhecido, https://www.pes-psrc.org/kb/report/1015.pdf, p. 44 (PDF)] — o que B considera desprezível para o transformador em óleo (constante térmica de horas) é crítico para o motor [INFERÊNCIA a partir de doc B, p. 2 e das fontes citadas]; (iii) a IOGP S-704 exige, a 80 % de tensão, $t_{LR,hot} \ge t_{acc}(80\,\%) + 5$ s [NORMA: IOGP S-704 v2.0, 9.12.1.5] — critério direto para uma restrição $g_4$ (Seção 3).

### 2.5 Temperatura de ponto quente

**Limites por classe.** Ambiente 40 °C + elevação (método da resistência) + margem de ponto quente: classe B 80 K + 10 K = 130 °C; F 105 K + 10 K = 155 °C; H 125 K + 15 K = 180 °C [NORMA: IEC 60034-1, Tabela 7, via Leroy-Somer TN11, https://www.leroy-somer.com/documentation_pdf/5202_en.pdf; NEMA MG 1 via PSRC C37.96, p. 17–18 (PDF); LITERATURA: WEG, Guia de especificação, Tabela 7.1, p. 36, https://static.weg.net/medias/downloadcenter/h32/hc5/WEG-motores-eletricos-guia-de-especificacao-50032749-brochure-portuguese-web.pdf]. Prática O&G: classe F com elevação classe B (margem 155 − 120 = 35 K) [NORMA: IOGP S-704 v2.0, 8.1; CÁLCULO PRÓPRIO].

**Elevação por partida.** Da interpretação de Zocholl (capacidade entre operação e limite = $I_L^2 T_O$) segue a estimativa adiabática [INFERÊNCIA FÍSICA]:

$$
\Delta\theta_{start}(V) \approx U(V)\,\bigl(\theta_{lim} - \theta_{op}\bigr),
\qquad
\theta_{hs}(t) = \theta_{amb} + \Delta\theta_{op} + \Delta\theta_{start}\, e^{-t/\tau}
\tag{E5}
$$

com $\tau$ a constante de tempo de resfriamento do enrolamento (ordem de 10³ s no exemplo de Zocholl) [LITERATURA: Zocholl 2007/2012, p. 6 (PDF 7)]. Exemplo: motor classe F com elevação classe B em operação ($\theta_{op}$ = 120 °C, $\theta_{lim}$ = 155 °C), $U$ = 0,6 (Tabela 2.3, 0,850 pu) → $\Delta\theta_{start}$ ≈ 21 K → pico 141 °C, abaixo de 155 °C; $U$ = 1,27 (0,755 pu) → ≈ 44 K → 164 °C, acima da classe [CÁLCULO PRÓPRIO: (E5); todos os parâmetros [HIPÓTESE]]. Strangas et al. recomendam estimar "the hot spot, rather than the average winding temperature, and to include the effects of the operating mode while doing so" [FATO: artigo 09, p. 4].

**Desequilíbrio e subtensão sustentada (efeitos adicionais, não de partida).** A −10 % de tensão, elevação de temperatura a plena carga +23 % (motor de alta eficiência) e conjugado de partida −19 % [LITERATURA: Pillay 1995 apud Bonnett & Boteler 2001, p. 6 (PDF)]; desequilíbrio: $\Delta T$ extra = 2·(%VU)² [LITERATURA: Bonnett & Boteler 2001, p. 9 (PDF)]. B não modela desequilíbrio [FATO: ausência].

### 2.6 Consumo de vida térmica (Arrhenius/Montsinger)

Modelo de Montsinger derivado de Arrhenius–Dakin: $L(\theta) = L_0\,2^{(\theta_0 - \theta)/HIC}$, com HIC tipicamente 8–15 °C conforme o material; a "regra dos 10 °C" é o caso particular HIC = 10 [LITERATURA: Theofanous et al., Energies 2025, 18, 6087, p. 11, https://aisberg.unibg.it/retrieve/43c96487-a8ad-4947-a8c8-3b350e9892a2/J65.pdf]. A observação original de Montsinger (1930) foi ≈ 8 °C em cambraia envernizada [LITERATURA: idem, p. 7–8]. O índice térmico (20 000 h ≈ 2,28 anos à temperatura de classe) é critério de qualificação, não vida em serviço [LITERATURA: idem, p. 11; Leroy-Somer TN11, p. 1–2]. Limites do modelo: cinética de 1.ª ordem, energia de ativação constante, extrapolação de três temperaturas; fadiga mecânica, vibração e campo elétrico "not explicitly accounted … can become significant in applications involving … repetitive start-stop cycles" [LITERATURA: Energies 2025, p. 31].

Fator de aceleração e vida consumida por partida [INFERÊNCIA FÍSICA: integração do fator de Montsinger sobre o transitório térmico (E5)]:

$$
AF(\theta) = 2^{(\theta - \theta_0)/HIC},
\qquad
\Delta L_{start}(V) = \frac{1}{L_0}\int_0^{t_{cool}} AF\bigl(\theta_{hs}(t;V)\bigr)\,dt
\quad[\text{fração de } L_0]
\tag{E6}
$$

Tabela 2.4 — Fator $AF$ para sobretemperatura $\Delta\theta$ acima de $\theta_0$ [CÁLCULO PRÓPRIO: $2^{\Delta\theta/HIC}$]:

| $\Delta\theta$ | HIC = 8 K | HIC = 10 K | HIC = 15 K |
|---|---|---|---|
| +5 K | 1,54× | 1,41× | 1,26× |
| +10 K | 2,38× | 2,00× | 1,59× |
| +20 K | 5,66× | 4,00× | 2,52× |
| +30 K | 13,45× | 8,00× | 4,00× |

A sensibilidade a HIC é de ≈ 40 % a +20 K; HIC deve ser tratado como parâmetro incerto, propagado por Monte Carlo [INFERÊNCIA; coerente com o padrão de MC do repositório, Seção 5]. Alternativa equivalente em forma de Arrhenius: $AF = \exp\bigl[\tfrac{E_a}{k}(\tfrac{1}{\theta_0} - \tfrac{1}{\theta})\bigr]$ com $\theta$ em K [FATO: artigo 09, eq. (12), p. 6, para semicondutores; a eq. (13) do mesmo artigo para isolamento é dimensionalmente ambígua e não deve ser usada sem reparametrização — FATO: artigo 09, p. 6; INFERÊNCIA do fichamento 09 §8]. Constantes $E_a$, $L_0$, HIC por classe e sistema isolante: [INSERIR CITAÇÃO — IEC 60034-18-31 do fabricante; nenhuma fonte acessada fornece valores para mica-epóxi VPI de MT].

### 2.7 Perfil consolidado por solução de B

Tabela 2.5 — Síntese do perfil de estresse por partida, por solução de B, sob o caso [HIPÓTESE] $k_T$ = 0,7, carga quadrática, $t_{acc}(1)$ = 6 s, $t_{LR,hot}$ = 12 s, classe F com elevação B, HIC = 10 K [CÁLCULO PRÓPRIO: Tabelas 2.1–2.4 e (E5)]:

| Solução de B | $V_t$ | $f_5$ [kW] | $I/I_n$ | $t_{acc}$ [s] | $U$ | $\Delta\theta_{start}$ [K] | $\theta_{pico}$ [°C] | $AF$ no pico | Status térmico |
|---|---|---|---|---|---|---|---|---|---|
| Sem corte | 0,755 | 0 | 4,91 | 33,5 | 1,59 | ≈ 56 | ≈ 176 | ≈ 4,2× | excede classe; > $t_{LR,hot}$ |
| Mínimo corte | 0,850 | 7417 | 5,52 | 12,8 | 0,77 | ≈ 27 | ≈ 147 | 1 (abaixo de $\theta_0$) | dentro da classe; $t_{acc} > t_{LR,hot} - 5$ s |
| Joelho | 0,858 | 8127 | 5,58 | 12,1 | 0,74 | ≈ 26 | ≈ 146 | 1 | idem |
| Mínimas perdas | 0,866 | 8927 | 5,63 | 11,5 | 0,72 | ≈ 25 | ≈ 145 | 1 | idem |

Leituras: (i) as três soluções factíveis de B são quase indistinguíveis termicamente, o que confirma que $g_1$ (tensão) e um critério térmico do alvo apontam na mesma direção mas não com a mesma resolução; (ii) sob os parâmetros hipotéticos, **nenhuma** das soluções de B satisfaz o critério IOGP $t_{acc} \le t_{LR,hot} - 5$ s = 7 s — uma restrição $g_4$ nesses termos tornaria o problema infactível para qualquer plano de corte, exigindo mudança de decisão (partida em vazio, aguardar restauração do trafo, partida com tensão reduzida controlada), o que B não contempla [INFERÊNCIA a partir da Tabela 2.5; validade condicionada aos parâmetros hipotéticos]; (iii) a vida consumida por partida é dominada não pela partida em si, mas pelo religamento das máquinas cortadas (Seção 3.1).

### 2.8 Estresses adjacentes que B não captura

1. **Máquinas mantidas ligadas durante o inrush**: a 0,850 pu de barra, os demais motores sofrem aumento de escorregamento e corrente por ~10 s [FATO: doc B, p. 2–3 para a duração; INFERÊNCIA FÍSICA para o efeito]; o nível de 70 % da IEEE 3002.7 para "motors that must reaccelerate" [NORMA: IEEE Std 3002.7-2018, via IPST 2021, p. 2] não é violado, mas o aquecimento adicional é não nulo e depende da curva de cada máquina — B só considera a ANSI 27 [FATO: doc B, p. 1–3].
2. **Religamento das máquinas cortadas**: cada máquina em $s_i = 0$ deverá ser religada após a partida do alvo; cada religamento é uma partida (sob N-1, com o alvo já em carga, portanto com tensão de barra ainda menor que no PRE-ENERG) [INFERÊNCIA; FATO: ausência em B]. O plano "mínimas perdas" (corta as 19 máquinas) implica 19 partidas adicionais; o plano "mínimo corte" implica 17. A norma geral garante apenas 2 partidas a frio e 1 a quente como mínimo de projeto, sem "por hora" [NORMA: NEMA MG 1-2006 R1, 12.54.1, via FAQ 1.41, https://www.nema.org/membership/products/mg-1-faq; IEC 60034-1/ABNT NBR 17094 via WEG, p. 29]; a IOGP exige 3 a frio, 2 a quente, ≥ 1000 partidas/ano e (texto v1.0) vida de 5000 partidas a plena tensão [NORMA: IOGP S-704, 9.12.2.1–9.12.2.5, Tabela 25, 11.3.1.3].
3. **Sequência e tempo de espera entre religamentos**: espera típica 15–40 min em operação, 35–90 min desligado (referência de fabricante, não norma) [LITERATURA: L&B Electric 1998, p. 1–2, https://www.landbelectric.com/download-document/81-medium-voltage-motor-starting.html].
4. **Falha de partida e nova tentativa**: B não avalia partidas repetidas nem religamento após falha ("partidas repetidas ou falha da partida com religamento não são avaliadas") [HIPÓTESE registrada no fichamento B §9.2]; o Documento A trata a interrupção intempestiva de partida como pior caso de sobretensão de VCB (Ip/In = 6,5) [FATO: doc A, p. 1] — o snapshot INRUSH de B é o estado elétrico em que tal interrupção ocorreria [INFERÊNCIA: junção de A e B; nenhum dos dois propõe a junção — FATO: ausência].

### 2.9 Coerência de ordem de grandeza com os números de B

Com $\eta$ [HIPÓTESE] = 0,94–0,96, $S_n$ = 1250/(0,89·η) ≈ 1,46–1,49 MVA; $S_{inrush}$ a tensão plena ≈ 9,5–9,7 MVA; a 0,850 pu ≈ 6,9–7,0 MVA [CÁLCULO PRÓPRIO]. O transformador atinge 1,38 × 9 = 12,4 MVA no inrush do plano recomendado [FATO: doc B, p. 3] com carga sustentada de 7,31 MVA (alvo a plena carga incluído) [FATO: doc B, p. 3]; a soma vetorial de ≈ 5,8 MVA remanescentes (estático + M_710 + M_800) com ≈ 7 MVA de inrush a fp 0,20 é da ordem de 12 MVA — coerente [CÁLCULO PRÓPRIO: ordem de grandeza; a composição exata exige os CSV retidos].

---

## 3. "Health-aware load shedding": consumo de vida como $f_6$ ou $g_4$ na formulação (1)–(4) de B

### 3.1 Formulação estendida

Formulação de B (transcrita): $\min_s F(s) = (f_3, f_4, f_5)$ s.a. $g_1 = V^{ir} - V_{\min}^{(\mathrm{INRUSH})} \le 0$, $g_2 = V_{\max}^{(\mathrm{POST\text{-}DISC})} - V^{sw} \le 0$, $g_3 = S_{TR}^{(sust)}/S_{AF} - 1 \le 0$, $s \in \{0,1\}^{n_m-1}$ [FATO: doc B, p. 2, eqs. (1)–(4)].

Extensão proposta [HIPÓTESE de formulação; nenhum elemento consta de B]:

$$
f_6(s) \;=\; \underbrace{\Delta L_{T}\!\bigl(V_{\min}^{(\mathrm{INRUSH})}(s)\bigr)}_{\text{alvo}}
\;+\; \underbrace{\sum_{i:\,s_i=0} \Delta L_i\!\bigl(V_i^{(\mathrm{RESTART})}(s)\bigr)}_{\text{religamento das cortadas}}
\;+\; \underbrace{\sum_{i:\,s_i=1} \Delta L_i^{sag}\!\bigl(V_{\min}^{(\mathrm{INRUSH})}(s),\,t_{acc}(s)\bigr)}_{\text{mantidas sob afundamento}}
\tag{E7}
$$

$$
g_4(s) \;=\; t_{acc}\!\bigl(V_{\min}^{(\mathrm{INRUSH})}(s)\bigr) - \bigl(t_{LR,hot} - \Delta t_{marg}\bigr) \;\le\; 0
\qquad\text{ou}\qquad
g_4'(s) \;=\; U(s) - U_{\max} \;\le\; 0
\tag{E8}
$$

em que cada $\Delta L$ é dado por (E6) via (E2)–(E5); $\Delta t_{marg}$ = 5 s reproduz a IOGP 9.12.1.5 [NORMA: IOGP S-704 v2.0, 9.12.1.5]; $U_{\max}$ < 1 impõe margem sobre a curva de limite térmico quente [NORMA: IEEE Std 620-2022, apresentação das curvas]. O segundo termo de (E7) exige um quinto snapshot por máquina religada (ou uma sequência de religamento), que B não tem [FATO: ausência]; o terceiro termo exige modelo de reaceleração das máquinas mantidas — o do repositório não é fisicamente consistente (Seção 5) — e fica como [HIPÓTESE] de segunda fase. Unidade sugerida para $f_6$: horas-equivalentes à temperatura de classe (fração de $L_0$ × $L_0$), reportando faixa por HIC ∈ {8, 10, 15} K [INFERÊNCIA].

Para partidas raras, uma alternativa de menor custo é contar o evento com severidade discreta: $f_6^{(evt)}(s) = \sum_{\text{partidas}} w\bigl(U\bigr)$, com $w$ crescente e $U$ de (E4) — o análogo direto das "durações de fase" de Ahsan et al. [FATO: artigo 05, p. 3–4] e do "switching counts" que B cita como objetivo possível em plantas maiores [FATO: doc B, p. 4] — sem que B ligue contagem a desgaste [FATO: ausência].

### 3.2 Objetivo ou restrição? A lição de degenerescência de B

B mostra que objetivos que "vanish identically on the feasible region" ($f_1$, $f_2$) colapsam a frente em subespaço de dimensão efetiva ≤ 3, e que algoritmos por direções de referência (NSGA-III) perdem pressão seletiva, ficando 23 % abaixo da busca aleatória [FATO: doc B, p. 1–2, Tabela II]; a correção foi tratar limites operacionais como restrições e dimensionar as direções à população [FATO: doc B, p. 2–4]. Aplicando a lição:

1. **$f_6$ não se anula no conjunto factível**: toda partida consome vida ($\Delta L > 0$ para qualquer $V$), portanto $f_6$ não reproduz o defeito de $f_1$/$f_2$ [INFERÊNCIA a partir de (E6)–(E7)].
2. **Risco de quase-degenerescência por colinearidade**: se $f_6$ dependesse apenas de $V_{\min}^{(\mathrm{INRUSH})}$ (primeiro termo de (E7)), e como $V_{\min}$ é quase linear nos bits [FATO: doc B, p. 5] e cresce com a potência cortada, $f_6$ seria uma função quase monótona de $f_5$: a frente $(f_5, f_6)$ degeneraria em curva, elevando a dimensão nominal (4 objetivos) sem elevar a dimensão efetiva — exatamente o cenário em que Ishibuchi et al. documentam a queda dos algoritmos por decomposição [FATO: doc B, p. 2, citando [10]]. O segundo termo de (E7) (religamentos) cresce com o corte e quebra a colinearidade: $f_6$ tem mínimo interior no espaço de $f_5$ [INFERÊNCIA]. Verificação obrigatória no experimento: coeficiente de correlação de postos entre $f_5$ e $f_6$ na frente e razão de autovalores (PCA) da frente [INFERÊNCIA metodológica].
3. **$g_4$ como restrição normativa**: limites de $t_{acc}$ ou $U$ são requisitos operacionais (IOGP 9.12.1.5; IEEE 620), não preferências — pela lógica de B ("The voltage limits are operational requirements, not preferences, so the corrected model treats them as inequality constraints" [FATO: doc B, p. 2]) devem entrar como $g_4$, mantendo $f_6$ como objetivo de preferência (quanto de vida gastar) [INFERÊNCIA].
4. **Interação $g_1$ × $g_4$**: em B, $g_1$ satura primeiro e $g_3$ nunca é ativa [FATO: doc B, p. 3]. Sob os parâmetros da Tabela 2.5, $g_4$ (IOGP) seria violada em toda a frente, tornando o problema infactível; sob $t_{LR,hot}$ = 20 s, $g_4$ seria inativa. Ou seja, $g_4$ pode (a) não mudar nada, (b) mover a fronteira recomendada para mais corte, ou (c) revelar que a operação "partir o alvo sob N-1" é inadmissível para aquele motor — o resultado (c) é informação de decisão que B não pode produzir [INFERÊNCIA].
5. **Diretriz de B para 4 objetivos**: "Above three objectives the selection pressure of crowding distance degrades, which is the scenario NSGA-III was designed for", mas "that half of the guideline rests on the literature" [FATO: doc B, p. 4]. Acrescentar $f_6$ (4 objetivos) é a primeira oportunidade de testar empiricamente a metade não testada da diretriz de B, com o mesmo protocolo (10 sementes, HV, Wilcoxon) [INFERÊNCIA].

### 3.3 Conflito esperado e forma da frente

Tabela 3.1 — Direção de variação de cada objetivo com o aumento do corte (mais $s_i$ = 0) [INFERÊNCIA a partir de doc B, p. 2–3 e de (E7)]:

| Objetivo | Tendência com mais corte | Fonte da tendência |
|---|---|---|
| $f_5$ (kW cortados) | cresce | definição [FATO: doc B, p. 2] |
| $f_4$ (perdas PRE-DISC) | decresce | "keeping more machines connected … raises losses" [FATO: doc B, p. 3] |
| $f_3$ (violações) | decresce | idem |
| $f_6$, termo do alvo | decresce ($V$ sobe, $t_{acc}$ cai) | (E2)–(E6) |
| $f_6$, termo de religamento | cresce (mais partidas) | (E7) |
| $f_6$ total | mínimo interior | soma dos dois |

Consequência: a frente $(f_4, f_5, f_6)$ deixa de ser a curva monótona $f_4$ × $f_5$ da Fig. 1 de B [FATO: doc B, p. 4, legenda] e ganha uma direção genuína; a solução "mínimas perdas" (cortar tudo) passa a ser penalizada por 19 religamentos, e a solução "mínimo corte" pela partida do alvo a 0,850 pu [INFERÊNCIA].

### 3.4 Surrogates: ridge quadrático de B versus modelos orientados a dados dos 13 artigos

**Por que o ridge de B funciona.** "bus voltage responds almost linearly to the switching of individual loads at this scale, and the pairwise terms capture the interaction effects" [FATO: doc B, p. 5]; com bits binários, $x_i^2 = x_i$, o modelo tem 19 + 171 = 190 regressores [CÁLCULO PRÓPRIO: C(19,2)]. O random forest ficou em $R^2$ = 0,977 [FATO: doc B, Tabela VI].

**Por que não replicar diretamente para $f_6$.** $t_{acc}(V)$ tem polo em $V_{stall}$ (E2) e $\Delta L$ é exponencial em $\theta$ (E6): a composição bits → $f_6$ é fortemente não linear; não há evidência acessada de que um surrogate de tempo de aceleração/$I^2t$ mantenha $R^2$ > 0,999 [INFERÊNCIA; registrado em `out/web/termico_partidas_n1_otimizacao.md` §4 item 12]. Proposta [HIPÓTESE metodológica]: **surrogate na parte quase linear, física na parte não linear** —

$$
\hat f_6(s) = f_6^{\text{físico}}\!\bigl(\hat V_{\min}(s)\bigr),
\qquad \hat V_{\min} = \text{ridge quadrático de B}
\tag{E9}
$$

de modo que o erro do surrogate (MAE 8,5 × 10⁻⁵ pu [FATO: doc B, p. 5]) é propagado por (E2)–(E6) com sensibilidade conhecida ($\partial t_{acc}/\partial V = -2k_T V\, t_{acc}^2/(J\cdot 0{,}95\omega_s/T_n)$ — grande perto de $V_{stall}$, pequena a 0,85 pu [CÁLCULO PRÓPRIO: derivada de (E2)]). A garantia de B — "Prediction errors may degrade search efficiency, but they never produce an unverified shedding recommendation, because final feasibility is always confirmed by the full power flow" [FATO: doc B, p. 5] — é preservada se a verificação final calcular $f_6$ e $g_4$ com o fluxo exato e o modelo dinâmico completo (E1), não com (E2) [INFERÊNCIA].

**Os modelos data-driven dos 13 artigos não substituem o ridge nesta tarefa:**

| Artigo | Modelo | Por que não se aplica ao surrogate de $f_6$ | Rótulo |
|---|---|---|---|
| 10 (Siami-Namini 2019) | LSTM/BiLSTM | previsão de série temporal univariada regular; o mapeamento bits → $f_6$ não é série temporal; BiLSTM não é causal para uso online; inconsistências de pseudocódigo e dados | [FATO: artigo 10, p. 4–7]; [INFERÊNCIA do fichamento 10 §8–9] |
| 08 (Yin 2024) | CNN-BiLSTM-Attention | uma trajetória run-to-failure, baselines possivelmente importados, RUL não quantificada; entrada é HI contínuo, não vetor de decisão | [FATO: artigo 08, p. 3–5]; [INFERÊNCIA do fichamento 08 §7–8] |
| 05 (Ahsan 2016) | NN/ANFIS | n = 6 amostras, extrapolação, erros 19–31 % com superestimação; exemplo do que evitar | [FATO: artigo 05, p. 3–6, Tabelas 1–2] |
| 13 (Wu 2024) | catálogo DL | "few works concern the costs, especially for the computations"; surrogates só como "dados simulados" | [FATO: artigo 13, p. 17, 21, 24] |
| Literatura de rede | MLP para triagem N-1: 97–98 % de acurácia, FN 0,0–0,64 %; GP falha sem correção de incerteza em simuladores de rede | [LITERATURA: Schaefer, Menke & Braun 2020, https://arxiv.org/abs/2008.09384; Houdouin & Saludjian 2025, https://arxiv.org/abs/2503.00094] |

Onde os modelos sequenciais entram: **não** no surrogate do otimizador, mas na camada de prognóstico (Seção 4), prevendo a trajetória do indicador de saúde alimentado pelo histórico de partidas produzido pelo otimizador [INFERÊNCIA].

### 3.5 Protocolo experimental herdado de B e ampliado

| Elemento | B | Extensão proposta | Rótulo |
|---|---|---|---|
| Algoritmos | NSGA-II, NSGA-III (energia de Riesz, |W| = µ), U-NSGA-III, aleatório | idem, a 3 e a 4 objetivos | [FATO: doc B, p. 3]; [HIPÓTESE] |
| Orçamento | µ = 40, G = 20, 800 avaliações, sementes 42–51 | idem + enumeração exaustiva (2^19 viável off-line: ≈ 3,6 h a 25 ms) para obter a frente verdadeira e IGD exato | [FATO: doc B, p. 3]; [CÁLCULO PRÓPRIO] |
| Métricas | HV com referência a 10 % de margem; Wilcoxon pareado α = 0,05 | + IGD contra frente enumerada; correlação $f_5$–$f_6$; dimensão efetiva (PCA) | [FATO: doc B, p. 3]; [INFERÊNCIA] |
| Ablação | correções aplicadas em conjunto (limitação declarada) | isolar: (a) $f_6$ só; (b) $g_4$ só; (c) ambos; (d) $f_6$ sem termo de religamento (teste de colinearidade) | [FATO: doc B, p. 4]; [HIPÓTESE] |
| Surrogate | ridge/RF para $V_{\min}$ e $f_4$; Algoritmo 2 proposto, não executado | executar Algoritmo 2 com (E9); comparar ridge direto em $f_6$ vs composto | [FATO: doc B, p. 5]; [FATO: ausência]; [HIPÓTESE] |
| Sensibilidade | nenhuma (declarado: $g_1$ ativa em exatamente 0,850) | HIC ∈ {8,10,15}; $t_{LR,hot}$ ∈ {10,12,20} s; $k_T$; tipo de carga; X/R | [INFERÊNCIA do fichamento B §9.2]; [HIPÓTESE] |

---

## 4. Mapeamento direto com os 13 artigos de apoio

### 4.1 Yu, Wang e Luo (2014) — degradação dependente de modo (artigo 06)

- "For a hybrid system, the same component will exhibit different degradation behaviors at different operating modes"; exemplo com motor: "the motor wear in the ramp-up mode is more severe than the wear in the idle mode" [FATO: artigo 06, p. 3]. Modelo (4): $\omega_1\ddot P + (1-\omega_1)\dot P = bP^{2\omega_2} + cP^{\omega_3}$, com estrutura (DMSV) e coeficientes por modo, estimados por HDE; MD-RUL por modo [FATO: artigo 06, p. 3–5].
- **Mapeamento [INFERÊNCIA]:** modos = {regime N (dois trafos), regime N-1, partida a plena tensão, partida sob N-1 sem corte (0,755 pu), partida sob N-1 com plano $s$ (0,850–0,866 pu), religamento pós-partida}. O vetor $s$ de B escolhe a sequência de modos; a topologia N-1 é o "mode change" exógeno. A lei de degradação por modo é (E6) com $V$ do modo; o DMSV corresponde a escolher entre lei exponencial (térmica) e por evento.
- **O que não transfere:** degradação sintética em circuito RC; RUL escalar sem incerteza; RUL por modo sem integração da sequência futura de modos [FATO: artigo 06, p. 6–7; INFERÊNCIA do fichamento 06 §8–9]. A integração sobre a sequência é justamente o que (E7) faz ao somar partida e religamentos.
- **Tempo de espera (WT):** o diagnóstico só se completa após a próxima mudança de modo [FATO: artigo 06, p. 3]; em plantas com partidas raras o WT pode ser de meses — argumento para usar o próprio plano de load shedding como "modo provocado" que atualiza o modelo [INFERÊNCIA do fichamento 06 §9.1].

### 4.2 Ma, Liserre, Blaabjerg e Kerekes (2015) — perfil de missão, rainflow, Miner (artigo 12)

- Arquitetura "perfil de missão → perfil de carga térmica → modelo de resistência → acúmulo de dano (Miner) → distribuição de vida por mecanismo e condição", em três constantes de tempo (longo/médio/curto prazo) [FATO: artigo 12, p. 1–2, Fig. 1–2]; extrapolação anual por ponderação pela distribuição de condições, eq. (3): $CL_{1year} = (365\cdot24/3)\sum_v W_v\, CL_{v,3h}$ [FATO: artigo 12, p. 7]; rainflow extraindo $\Delta T_j$, $T_{jm}$ e $t_{cycle}$ [FATO: artigo 12, p. 4]; "the turn ON and turn OFF of power converter will introduce significant power changes and thus have strong effects on the thermal cycling" [FATO: artigo 12, p. 6].
- **Mapeamento [INFERÊNCIA]:** perfil de missão do motor = histórico anual de {partidas a plena tensão, partidas sob N-1 por plano $s$, religamentos, horas por nível de carga e ambiente}; perfil de carga = $\theta_{hs}(t)$ por (E5); médio prazo (s–min) = transitório de partida (dominante, como as partidas/paradas do conversor em Ma); longo prazo (h–meses) = Arrhenius em regime; rainflow sobre $\theta_{hs}(t)$ conta ciclos térmicos (delaminação por dilatação diferencial — [HIPÓTESE], [INSERIR CITAÇÃO]); Miner soma (E6) por evento. A eq. (3) de Ma vira: $\Delta L_{ano} = N_{N} \Delta L(V=1) + N_{N-1}\sum_s p(s)\,f_6(s)$, com $N_{N-1}$ o número esperado de partidas sob N-1 por ano e $p(s)$ a frequência de uso de cada plano — B fornece $f_6(s)$, a estatística de contingências fornece $N_{N-1}$ [INFERÊNCIA].
- **Entregável de decisão:** "lifetime distribution — which indicates the failure contribution by different loading conditions" [FATO: artigo 12, p. 2] → quociente auditável "vida consumida por partida sob N-1 / partida normal" por plano de corte [INFERÊNCIA do fichamento 12 §11].
- **O que não transfere:** modelos B10 de solda/fios, ripple de $T_j$ a 50 Hz, Miner linear para dano dielétrico com limiar [FATO: artigo 12, p. 5, 8; INFERÊNCIA do fichamento 12 §9.2].

### 4.3 Strangas, Aviyente, Neely e Zaidi (2013) — decisão por prognóstico e mitigação (artigo 09)

- Caminhos para a falha com e sem mitigação: $MTBF_1 = 1/(p_1\lambda_1)$; $MTBF_2 = 1/(p_{12}\lambda_1) + 1/\lambda_2$; $MTBF_3 = 1/(p_{13}\lambda_1) + 1/\lambda_3$ com $\lambda_3 \ll \lambda_2$; falso positivo $MTBF_4 = 1/\lambda_{10} + 1/\lambda_3$, $\lambda_{10} = p_{10}/t_{sample}$; $\lambda_{sys} = \sum 1/MTBF_i$ [FATO: artigo 09, eqs. (7)–(11), p. 5]; "A drive, then, once it is modified to alleviate the effects of a fault, has decreased life expectancy" [FATO: artigo 09, p. 1].
- **Mapeamento [INFERÊNCIA]:** mitigação = plano de corte $s$; sistema "modificado" = planta com máquinas cortadas (λ_3 do alvo menor; produção perdida); falso positivo = corte desnecessário (custo de produção $f_5$, não de confiabilidade — B já mede); falso negativo = partir sem corte (0,755 pu, $U$ > 1, λ_2 maior). A formalização (8)–(9) liga o plano de corte ao MTBF do alvo; o limiar de decisão (0,4 sobre $P[q_{t+1} = S_6]$ no exemplo [FATO: artigo 09, p. 8]) corresponde a escolher entre planos da frente pelo nível de risco aceito.
- **Ressalvas:** taxa de falha constante e aditiva, inadequada a desgaste com risco crescente; eq. (13) de isolamento dimensionalmente ambígua; sequência de observações sintética [FATO: artigo 09, p. 4, 6, 8; INFERÊNCIA do fichamento 09 §8].
- **Ponto de contato com B:** B otimiza a decisão sem prognóstico; Strangas prognostica sem otimizar a decisão; (E7)–(E8) unem os dois [INFERÊNCIA].

### 4.4 LSTM/BiLSTM — previsão de indicadores (artigos 10 e 08)

- Equações da célula LSTM (4)–(9) e protocolo walk-forward um passo à frente [FATO: artigo 10, p. 3, 5]; BiLSTM reduziu RMSE em média 37,78 % mas piorou em IXIC.weekly (+45,03 %) e converge mais devagar [FATO: artigo 10, p. 5–7, Tabelas II–III]; CNN-BiLSTM-Attention: RMSE 0,0354, $R^2$ 0,9582 sobre uma trajetória de IGBT [FATO: artigo 08, p. 5, Tabela II].
- **Papel no pipeline [INFERÊNCIA]:** previsão da trajetória do HI de isolamento (tan δ, capacitância, DP, temperatura) com **covariáveis de estresse** vindas do otimizador (contagem de partidas sob N-1 ponderadas por $U$, $f_6$ acumulado) — modelo multivariado e causal, o oposto do univariado/bidirecional dos artigos; nunca como surrogate do otimizador (Seção 3.4). O alerta de que BiLSTM "needs fetching more training data" [FATO: artigo 10, p. 6] pesa contra arquiteturas profundas em regime de poucos eventos.

### 4.5 Vichare e Pecht (2006) — PHM de eletrônica (artigo 07)

- Quatro abordagens: BIT; fusíveis/canários; precursores; "modeling of stress and damage using exposure conditions" — LCM: cargas medidas in situ → parâmetros de carga (Δs, S_mean, ds/dt) → histogramas → modelos de dano → vida consumida [FATO: artigo 07, p. 1, 5–6, Fig. 3–4]; "If one can measure these loads in-situ, the load profiles can be used in conjunction with damage models to assess the degradation due to cumulative load exposures" [FATO: artigo 07, p. 5]; FMMEA primeiro [FATO: artigo 07, p. 6–7].
- **Mapeamento [INFERÊNCIA]:** os quatro snapshots de B (PRE-ENERG, INRUSH, PRE-DISC, POST-DISC) são o registro de carga de cada evento de partida; (E2)–(E6) são o modelo de dano; o histograma de $U$ por classe de severidade é o "binned histogram" do LCM; o load shedding é um modificador da distribuição de cargas. A recomendação de perfil de uso previsível [FATO: artigo 07, p. 5] é violada por contingências N-1 — o que favorece a abordagem 4 (dano por carga registrada) sobre a 3 (precursor com perfil fixo) [INFERÊNCIA do fichamento 07 §9].

### 4.6 Demais artigos (síntese)

| Artigo | Elemento transferido a este cruzamento | Rótulo |
|---|---|---|
| 01 (Liu 2025) | Paradigma híbrido para dados escassos (Tabela 2); regra de Miner citada para turbinas; ausência de qualquer cluster de isolamento/motor | [FATO: artigo 01, p. 2, 8]; [FATO: ausência] |
| 02 (Jensen 2018) | EKF sobre tendência $I_{leak} = \alpha e^{\beta t}$ até limiar; não há entrada de estresse — para B seria preciso $\beta_k = \beta_0\, g(\theta_k, n_{partidas})$ | [FATO: artigo 02, eqs. (7)–(8), p. 6]; [HIPÓTESE do fichamento 02 §9.2] |
| 03 (Sharma 2024) | "The two most impactful parameters for RUL estimation is the magnitude of applied voltage and the operating temperature"; [17] combina modelo elétrico-térmico com Arrhenius para perda de vida sob sub/sobretensão | [FATO: artigo 03, p. 3] |
| 04 (Sonnenfeld 2008) | Arquitetura "cenário → caracterização 1…N → DataService → módulo prognóstico" e `failSafeCycle`; temperatura como variável de confusão explícita | [FATO: artigo 04, p. 5–8, Figs. 7–9, 13] |
| 05 (Ahsan 2016) | Lição central: RUL só é determinável quando o perfil de estresse futuro é conhecido — em B o estresse futuro é a variável de decisão | [FATO: artigo 05, p. 4–6]; [INFERÊNCIA do fichamento 05 §9.1] |
| 11 (Muetze & Strangas 2016) | Canal "History of Causes" (causas estimadas de condições operacionais, não medidas) — o $V_{\min}^{(\mathrm{INRUSH})}$ de B é causa estimada por simulação; métrica de valor $V = (E_{ref} - E_{prog})/(E_{ref} - E_{perf})$ | [FATO: artigo 11, p. 6–9, Fig. 4, eq. (1)] |
| 13 (Wu 2024) | HI com monotonicidade, tendenciabilidade, prognosticabilidade; múltiplas condições operacionais como covariável (regime N/N-1/plano $s$); ensembles multiobjetivo com MOEA/D e NSGA-II | [FATO: artigo 13, p. 8, 20–21] |

Nenhum dos 13 artigos trata de load shedding, N-1, partida de motor MT ou otimização evolutiva de decisão operacional [FATO: ausência, verificada nos 13 fichamentos]; a revisão de decisão pós-prognóstico de 2020 encontrou três trabalhos de controle automático com RUL e nenhum sobre load shedding preventivo [LITERATURA: Wesendrup & Hellingrath, PHME 2020, p. 5–6, 9, https://papers.phmsociety.org/index.php/phme/article/download/1203/phmec_20_1203]; "health-aware control" é definido como síntese de controle baseada em RUL de componentes críticos [LITERATURA: Jha et al. 2019, https://arxiv.org/abs/2010.09269]. A combinação "vida consumida por partida sob N-1 como objetivo/restrição de load shedding" é lacuna documentada [INFERÊNCIA fundamentada na ausência].

---

## 5. O que o Olivas Power System Studio já entrega e o experimento computacional mínimo

### 5.1 Inventário verificado (commit `26d9248`)

| Capacidade | Onde | Estado | Rótulo |
|---|---|---|---|
| Afundamento na partida por divisor de impedância, $Z_{th}$ complexo opcional (heurística 10 % R / 90 % X se ausente) | `calculate_voltage_dip_pu` | disponível | [REPO: app/postprocessor/motor_starting.py:367-407, 389-401] |
| Corrente de partida ∝ V | `analyze_motor_starting` | disponível | [REPO: motor_starting.py:505] |
| Tempo de aceleração por conjugado médio, curvas de carga CONSTANT/LINEAR/QUADRATIC/CUBIC | `estimate_starting_time_s`, `average_load_torque_factor` | disponível; **independe da tensão** | [REPO: motor_starting.py:410-453, 148-168] |
| Critérios de aceitação 0,85 / 0,80 pu (IEEE 399 §10, NEMA MG 1) | `classify_acceptance` | disponível; só tensão | [REPO: motor_starting.py:93-96, 461-473] |
| Limite $t_{start} < 0{,}7\,t_{LR}$ e N_starts/hora | docstring e constante | **declarados, não aplicados** | [REPO: motor_starting.py:23-27, 99] |
| Aviso "verificar curva I²t" | `analyze_motor_starting` | só se $t_{start}$ > 30 s | [REPO: motor_starting.py:537-541] |
| Capacidade térmica $K = t_E (I_{LR}/FLA)^2$, $t(I) = K/(I/FLA)^2$ | `MotorThermalCurve` | disponível; curva única, sem HOT/COLD | [REPO: app/postprocessor/tcc_damage.py:551-578, 518-527] |
| Reaceleração | `simulate_reaccel` | heurística: $v_{dip} = \max(0{,}3, 1 - 0{,}3\,\Sigma S_{inrush}/S_{bus})$; tempo $J\omega^2/(\max(v^2, 0{,}01)\cdot 100)$ limitado a [0,5; 30] s; `voltage_dip_duration_s` não usado | [REPO: app/postprocessor/motor_reaccel.py:185-201, 205-216] |
| Fluxo de potência Newton–Raphson, sequência positiva, exatamente 1 SLACK, Jacobiano singular → `break` sem diagnóstico | `solve_power_flow` | disponível | [REPO: app/postprocessor/power_flow.py:380-384, 413-418, 536-545] |
| Limitação declarada "Sem otimização (load shedding, FACTS)" | docstring | — | [REPO: power_flow.py:87] |
| Monte Carlo de fluxo (CVs de carga), salva/restaura setpoints, gated | `run_pf_monte_carlo` | disponível; "Topologia fixa (N-1 ainda em backlog)" | [REPO: app/postprocessor/power_flow_monte_carlo.py:174-178, 205-212, 252-258; :15, :52] |
| Confiabilidade λ constante (λ = 8760/MTBF), preset motor 100–1000 hp (MTBF 43 800 h, MTTR 144 h) | `ComponentReliability`, `IEEE493_PRESETS` | disponível; sem risco variável | [REPO: app/postprocessor/reliability.py:103-118; reliability_monte_carlo.py:94-99] |
| Classe de isolamento (string "F") | `CatalogMotor.insulation_class` | só no catálogo; `motor_catalog_to_parameters` não a propaga | [REPO: app/preprocessor/equipment_catalog.py:124, 554-573] |
| Parâmetros de motor do projeto | `MotorParameters` | sem inércia, torque de partida, classe térmica, $t_{LR}$ | [REPO: app/preprocessor/motor.py:140-150] |
| Função 49 | `relay_51_50_49` | tempo definido, não réplica térmica | [REPO: app/postprocessor/tcc_devices.py:399] |
| Energização/ilhamento por BFS (inclui VCB) | `compute_energization` | disponível | [REPO: app/postprocessor/bus_energization.py:111] |
| Cenários what-if por cópia do projeto | `PpScenario`, `ScenarioManager` | disponível | [REPO: app/preprocessor/scenarios.py:51, 116] |
| Limitações declaradas no laudo | `KNOWN_LIMITATIONS` | disponível | [REPO: app/postprocessor/audit_trail.py:338] |
| Contrato de estudo modular | `run(project, bus_id, *, cache=None, config=None, auto_run_prereqs=True)` | disponível | [REPO: app/postprocessor/studies/__init__.py:15-24] |
| Gating comercial | `Feature`, `FEATURE_TIER_MAP` | disponível | [REPO: app/commercial/feature_gates.py:71-83] |
| Dependências | PySide6, anthropic, matplotlib, numpy, pytest, pydantic, PyYAML, openpyxl | sem pymoo/scipy; "scipy: Não adotar agora" | [REPO: requirements.txt:1-8; docs/THIRD_PARTY_NOTICES.md:98] |
| Testes | 35 (partida), 31 (fluxo), 12 (reaceleração) | CI executa subconjunto (não inclui partida/reaceleração) | [REPO: tests/test_pp_motor_starting.py, tests/test_pp_power_flow.py, tests/test_pp_v0_102_0_motor_reaccel.py — contagem `grep -c "def test_"`; mapa §1.9] |

### 5.2 Ausência de N-1, load shedding e otimização multiobjetivo — confirmação

`grep -rniE "nsga|pareto|pymoo|multiobjetiv|multi-objective|arrhenius|montsinger|remaining useful|\bRUL\b" app/ tests/ scripts/` → **zero linhas** [CÁLCULO PRÓPRIO: comando executado nesta sessão]. "load shedding" ocorre apenas em `app/postprocessor/power_flow.py:87` (limitação) e `app/standards/ansi_devices.py:325` (descrição da função ANSI 81) [REPO]. "N-1" ocorre apenas em `app/postprocessor/power_flow_monte_carlo.py:15` e `:52` (backlog) [REPO]. Não existe `docs/research/` [CÁLCULO PRÓPRIO: `ls docs/research` → inexistente]. Conclusão coerente com o mapa `out/repo/motor_partida_reaccel_fluxo.md` §1.10: "não existe hoje qualquer suporte a contingência N-1, corte de carga, otimização multiobjetivo ou modelo de envelhecimento de isolamento".

### 5.3 Experimento computacional mínimo (proposta)

Objetivo: reproduzir qualitativamente o problema de B no Olivas, acrescentar $f_6$/$g_4$ e medir o efeito sobre a frente, com verificação exata final. Todos os itens são [HIPÓTESE de projeto] salvo indicação.

**E0 — Planta de B como `PowerFlowSystem` explícito (não a partir de `.sch`).** Fonte 13,8 kV como SLACK com impedância derivada de 15 kA e X/R = 12 [FATO: doc B, p. 2] (numericamente: $Z = 13{,}8/(\sqrt3\cdot 15)$ ≈ 0,531 Ω, $X$ = 0,529 Ω, $R$ = 0,044 Ω [CÁLCULO PRÓPRIO]); um `PfBranch` para o transformador remanescente com $X$ = 0,08 na base 7,5 MVA convertido à base 100 MVA do sistema (= 1,067 pu) [REPO: power_flow.py:128-197 usa `base_MVA=100`; CÁLCULO PRÓPRIO]; barra 4,16 kV PQ com carga estática 3,6 MW [FATO: doc B, p. 2]; 19 máquinas como cargas PQ — **lista sintética** somando 8927 kW, contendo 710 kW e 800 kW, com fp e η [HIPÓTESE] (os CSV de B estão retidos [FATO: doc B, p. 3]). Alvo no INRUSH como impedância constante: o `PfBus` é PQ [REPO: power_flow.py:128-197], logo o snapshot INRUSH exige laço externo $P, Q \leftarrow P_0 V^2, Q_0 V^2$ até convergência (ou extensão ZIP do solver) [HIPÓTESE de implementação]. Critério de aceite: $V_{\min}^{(\mathrm{INRUSH})}$ com todas as máquinas em 0,755 ± 0,03 pu e os planos {M_710, M_800} / {M_800} / {} em 0,850 / 0,858 / 0,866 ± 0,01 pu [FATO: doc B, p. 2–3]; reprodução exata é impossível sem os CSV, e a diferença deve ser reportada como limitação.

**E1 — $t_{acc}(V)$.** Estender `estimate_starting_time_s` com parâmetro opcional `voltage_pu` multiplicando $T_{m,avg}$ por $V^2$ (E2), default `None` preservando os 35 testes [REPO: motor_starting.py:410-453; extensão E2 do mapa]; anexar a `MotorStartingReport` os campos opcionais `start_i2t_kA2_s`, `thermal_utilization_pu` ($U$, via `MotorThermalCurve.K_motor` [REPO: tcc_damage.py:551-557]) e ativar `DEFAULT_START_TIME_FRACTION_LIMIT` [REPO: motor_starting.py:99]. Segunda fase: integração numérica de (E1) com curva conjugado–velocidade (sem scipy: Euler/RK4 em Python puro, coerente com `docs/THIRD_PARTY_NOTICES.md:98`).

**E2 — Módulo de vida térmica.** Novo `app/postprocessor/insulation_aging.py` (ou `motor_thermal_stress.py`): (E5)–(E6) com parâmetros declarados ($\theta_{amb}$ = 40 °C, classe, $t_{LR,hot}$, $\tau$, HIC ∈ {8, 10, 15}, $L_0$ = 20 000 h como índice) e chaves em `KNOWN_LIMITATIONS` (`aging_i2t_upper_bound`, `aging_single_hotspot`, `aging_montsinger_hic_uncertain`, `aging_constants_uncited`) [REPO: audit_trail.py:338]; Monte Carlo sobre HIC e $t_{LR,hot}$ com `random.Random(seed)` no padrão dos três MCs existentes [REPO: power_flow_monte_carlo.py:205-212].

**E3 — Avaliador de plano e otimizador.** Função `evaluate_plan(s)` reproduzindo o Algoritmo 1 de B [FATO: doc B, p. 3] com um quinto snapshot por religamento (E7); NSGA-II binário em Python puro (cruzamento uniforme $p_c$ = 0,9, mutação bit-flip $p_m$ = 0,15, constraint domination, µ = 40, G = 20, sementes 42–51) [FATO: doc B, p. 3] — sem introduzir pymoo sem decisão de dependência [REPO: docs/THIRD_PARTY_NOTICES.md:98; CONTRIBUTING §14 conforme mapa]; enumeração exaustiva dos 2^19 planos como frente de referência (viável off-line num sistema de 2–3 barras) [CÁLCULO PRÓPRIO: 524 288 × 4 fluxos].

**E4 — Surrogate.** Ridge quadrático sobre 19 bits + interações (190 regressores, numpy `lstsq` com penalização) para $V_{\min}$: meta $R^2$ > 0,999 como em B [FATO: doc B, Tabela VI]; comparar (a) ridge direto em $f_6$ vs (b) composto (E9); executar o Algoritmo 2 de B com ρ ∈ {0,25; 0,5} e medir HV e número de avaliações exatas [FATO: doc B, p. 5 — proposto, não executado].

**E5 — Relatório.** Frentes $(f_4, f_5)$ vs $(f_4, f_5, f_6)$; restrições ativas por plano; HV/IGD por algoritmo; correlação $f_5$–$f_6$ e PCA da frente; sensibilidade a HIC, $t_{LR,hot}$, $k_T$, tipo de carga; tabela "vida consumida por partida sob N-1 / partida normal" por plano (entregável de Ma 2015); bloco de limitações e cabeçalho de auditoria [REPO: audit_trail.py]. Publicação em `docs/research/rul_isolamento/` (a criar) quando solicitado; o CI atual não roda os testes de partida — incluir os novos no workflow [REPO: .github/workflows/test.yml conforme mapa §1.9].

**Critérios de aceite do experimento:** (i) E0 dentro das tolerâncias; (ii) E1 não altera resultados com `voltage_pu=None` (35 testes verdes); (iii) NSGA-II supera aleatório com p ≤ 0,05 a 3 objetivos (reproduz B); (iv) a 4 objetivos, reportar se NSGA-III supera NSGA-II (teste da metade "literatura" da diretriz de B); (v) $f_6$ com termo de religamento apresenta mínimo interior em $f_5$; (vi) surrogate composto com MAE de $f_6$ inferior ao ridge direto.

---

## 6. Perguntas abertas

1. **Dados da planta de B.** Sem os CSV (potências, fp, η, $I_{LR}$ das 19 máquinas), a reprodução é apenas qualitativa; o link será liberado na versão final [FATO: doc B, p. 3]. Solicitar ao autor (a planta é o caso-base natural do MVP).
2. **Curva conjugado–velocidade e inércia do alvo.** B não os informa [FATO: ausência]; o Documento A tampouco (modela o motor como impedância para o transitório) [FATO: doc A, fichamento]. Sem eles, $t_{acc}$ e $U$ ficam em faixas (Tabelas 2.2–2.5). Fonte candidata: folha de dados do fabricante ou requisito IOGP (80 % V, margem ≥ 10 %) como envelope [NORMA: IOGP S-704, 9.12.1].
3. **Curvas de limite térmico quente/frio (IEEE 620) do alvo.** Necessárias para $t_{LR,hot}$ e para converter $U$ em temperatura; a IEEE 620 não diz como construí-las [LITERATURA: Zocholl & Benmouyal 2001, p. 2 (PDF 3)].
4. **Constantes de envelhecimento do sistema isolante (mica-epóxi VPI, MT).** HIC, $E_a$, $L_0$ por classe: nenhuma fonte acessada; IEC 60034-18-31 não acessada [INSERIR CITAÇÃO]. Até lá, o módulo reporta faixas e rotula [HIPÓTESE].
5. **Validade da regra de Miner para partidas.** Miner linear ignora ordem e interação; a Energies 2025 alerta para ciclos partida–parada repetitivos [LITERATURA: p. 31]. Alternativa: dano não linear ou processo de saltos [HIPÓTESE].
6. **Modelo das máquinas mantidas sob afundamento.** O `simulate_reaccel` do repositório não é fisicamente consistente [REPO: motor_reaccel.py:205-216; mapa §7 item 1]; o terceiro termo de (E7) exige reimplementação dinâmica.
7. **Sequência e instante dos religamentos.** B não modela [FATO: ausência]; a sequência ótima de religamento é um segundo problema combinatório (ordem × instante) que multiplica o espaço de busca — cabe como extensão do vetor de decisão ou como heurística fixa (maior máquina primeiro?) [HIPÓTESE].
8. **Frequência de partidas sob N-1.** $N_{N-1}$ por ano depende da taxa de falha do transformador e do regime de manutenção; o preset do repositório não cobre transformadores MT específicos e não foi verificado contra a IEEE 493 [REPO: reliability_monte_carlo.py:57-118; mapa `confiabilidade_eval_montecarlo.md` §1.2.1].
9. **Ajustes reais da ANSI 27.** B adota 0,85 pu "típico", sem temporização [FATO: doc B, p. 2]; com temporização, um afundamento de 10 s a 0,84 pu pode ou não atuar. O critério $g_1$ instantâneo é conservador; $g_4$ (térmico) pode ser o critério que de fato limita [INFERÊNCIA].
10. **Escolha NSGA-II vs NSGA-III a 4 objetivos.** Não testado por B [FATO: doc B, p. 4]; o experimento E3 decide.
11. **Surrogate para $f_6$.** Nenhuma evidência de $R^2$ > 0,999 para grandezas com polo em $V_{stall}$; (E9) é hipótese a testar (E4).
12. **Interseção com o Documento A.** Abortar a partida sob N-1 (por atuação térmica ou de subtensão) produz a interrupção intempestiva de partida que A trata como pior caso de sobretensão (Tabela III de A: até −38,30 kV / 19,00 kV/µs sem snubber) [FATO: doc A, Tabela III via fichamento]; o plano de corte que reduz $t_{acc}$ reduz também a janela de exposição a esse cenário — a quantificação exige acoplar o contador de dano dielétrico (A) ao térmico (B), o que nenhum dos dois documentos faz [FATO: ausência].
13. **Métricas de prognóstico.** PH, α-λ, RA/CRA [LITERATURA: Saxena et al. 2010, IJPHM 1(1), https://papers.phmsociety.org/index.php/ijphm/article/view/1336] só se aplicam quando houver trajetória de HI; para o otimizador, HV/IGD/Wilcoxon (B) bastam — a ligação entre as duas famílias de métricas fica em aberto.

---

## 7. Referências (somente fontes verificadas nesta sessão ou nos insumos citados)

Documento B — Selective Load Shedding for the Switching of Large Motors Under N-1 Contingency: Constrained Multiobjective Optimization with NSGA-II, NSGA-III and Regression Surrogates. Primeira submissão, SEPOC 2026 (autores omitidos). Arquivo `B_sepoc_load_shedding.txt`.

Documento A — Snubber ativo a tiristor para mitigação seletiva de sobretensões de manobra de VCB (SEPOC 2026). Arquivo `A_sepoc_snubber.txt`; fichamento `A_snubber_tiristor_vcb.md`.

Artigos 01–13: fichamentos em `out/fichamentos/` (referências completas nos respectivos §1): LIU, WEN, WANG (2025, Mach. Learn. Appl. 21:100704); JENSEN, STRANGAS, FOSTER (2018, IEEE TIA 54(6):5897–5906, DOI 10.1109/TIA.2018.2854408); SHARMA, SESHADRINATH (2024, SPECon, DOI 10.1109/SPECon61254.2024.10537428); SONNENFELD, GOEBEL, CELAYA (2008, AUTOTESTCON); AHSAN, STOYANOV, BAILEY (2016, ISSE, p. 273–278); YU, WANG, LUO (2014, IEEE TIE 61(1):546–554, DOI 10.1109/TIE.2013.2244538); VICHARE, PECHT (2006, IEEE TCAPT 29(1):222–229); YIN, HU, CAO (2024, ISEEIE, DOI 10.1109/ISEEIE62461.2024.00019); STRANGAS, AVIYENTE, NEELY, ZAIDI (2013, IEEE TIE 60(8):3519–3528, DOI 10.1109/TIE.2012.2227913); SIAMI-NAMINI, TAVAKOLI, SIAMI NAMIN (2019, IEEE Big Data, p. 3285–3292); MUETZE, STRANGAS (2016, IEEE IAS Mag., p. 63–73, DOI 10.1109/MIAS.2015.2459117); MA, LISERRE, BLAABJERG, KEREKES (2015, IEEE TPEL 30(2):590–602, DOI 10.1109/TPEL.2014.2312335); WU, WU, TAN, XU (2024, Sensors 24(11):3454, DOI 10.3390/s24113454).

Normas e literatura (acessadas conforme `out/web/termico_partidas_n1_otimizacao.md` §6 e `out/web/entrega_trabalho_computacional.md` §6, 2 set. 2026): IEEE Std 399-1997, cap. 9 (amostra); IEEE Std 3002.7-2018 (metadados; tabela via NIVELO et al., IPST 2021, 21IPST112); IEEE Std 620-2022 (metadados); IEEE C37.96-2012 via PSRC WG J10 (2013); IEC 60034-1 Tabela 7 via Leroy-Somer TN11 (2024); NEMA MG 1 via FAQ NEMA e via BONNETT & BOTELER (ACEEE 2001); IOGP S-704 v2.0 redline (2024); WEG, Guia de especificação de motores (50032749); ZOCHOLL (SEL, 2007/2012); ZOCHOLL & BENMOUYAL (WPRC 2001); THEOFANOUS et al. (Energies 2025, 18:6087, DOI 10.3390/en18236087); L&B ELECTRIC (1998); SCHAEFER, MENKE & BRAUN (arXiv 2008.09384); HOUDOUIN & SALUDJIAN (arXiv 2503.00094); WESENDRUP & HELLINGRATH (PHME 2020); JHA et al. (arXiv 2010.09269); SAXENA et al. (IJPHM 2010, DOI 10.36001/ijphm.2010.v1i1.1336).

Não acessadas (usar [INSERIR CITAÇÃO]): IEC 60034-18-31; IEC 60034-12 (texto integral); IEEE 620-2022 (texto integral); IEEE 3002.7-2018 (texto integral); MONTSINGER (1930); DAKIN (1948); MONTANARI, MAZZANTI & SIMONI (2002); BRANCATO (1992); ISHIBUCHI et al. (2017) e DEB & JAIN (2014) — citados por B, não lidos nesta sessão.

Repositório: `/home/user/olivas-power-system-studio`, commit `26d9248`; mapas `out/repo/motor_partida_reaccel_fluxo.md` e `out/repo/confiabilidade_eval_montecarlo.md`; script de cálculo `out/cross/calc_B_stress.py`.
