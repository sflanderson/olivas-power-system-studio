# Cruzamento — Documento A (snubber tiristorizado ativo para mitigação seletiva de sobretensões de manobra de VCB) × literatura de prognóstico/RUL × repositório Olivas Power System Studio

## 0. Convenções, insumos e regra de evidência

Rótulos usados em todas as afirmações deste documento:

- **[FATO: doc A, p. N]** — afirmação textual do Documento A (`papers_AB/txt/A_sepoc_snubber.txt`, marcadores `===== PAGE N =====`); **[FATO: doc A, Fig. N, p. 4 — leitura de figura]** — dado legível apenas na figura, conforme fichamento reparado `out/fichamentos_AB/A_snubber_tiristor_vcb.md`.
- **[FATO: artigo NN, p. N]** — afirmação de um dos 13 artigos de apoio, conforme os fichamentos `out/fichamentos/NN_*.md` (páginas segundo os marcadores do texto extraído).
- **[NORMA: id, cláusula/tabela]** — conteúdo normativo lido em amostra oficial nas pesquisas `out/etapa1/*.md` e `out/web/*.md` (a fonte de acesso é indicada nessas pesquisas).
- **[LITERATURA: ref., URL]** — fonte externa efetivamente acessada nas pesquisas citadas; **[LITERATURA-INDIRETA]** quando conhecida apenas por citação em fonte acessada.
- **[REPO: caminho:linha]** — fato verificado por leitura direta do repositório `/home/user/olivas-power-system-studio` (HEAD `26d9248`); **[REPO: git show ad308d5:trt_all_motors_dt_ea.atp:linha]** — fato do arquivo de referência recuperado do histórico git (removido da árvore de trabalho em `404a995`, conforme `out/repo/vcb_reignicao_snubber.md`).
- **[CÁLCULO PRÓPRIO: fórmula]**, **[INFERÊNCIA FÍSICA: derivação]**, **[HIPÓTESE]**, **[PREMISSA DO USUÁRIO]**, **[INSERIR CITAÇÃO]**.

Base por unidade adotada em todo o texto: $1\,\text{pu} = \sqrt{2}\,U_N/\sqrt{3} = 3{,}397\,\text{kV}$ para $U_N = 4{,}16$ kV [CÁLCULO PRÓPRIO: $4{,}16\cdot\sqrt{2}/\sqrt{3}$].

Advertência estrutural que condiciona todas as seções: o Documento A reporta **"TRV peak and rate of rise (RRRV) at the VCB"** [FATO: doc A, Tabela III, p. 3], não reporta a tensão nos terminais do motor (embora exista sonda `01AT` na Fig. 2) [FATO: doc A, Fig. 2, p. 4 — leitura de figura; FATO por omissão], não define RRRV, não define BIL e não apresenta o "modelo incremental de degradação" da camada digital [FATO: doc A, p. 2, III-B; fichamento A, §8, itens 5, 11, 15–17]. A sigla "RUL" não aparece no texto; a expressão "remaining useful life" ocorre uma única vez, na p. 2 [FATO: doc A, p. 2; fichamento A, §8, item 29].

---

## 1. Perfil de estresse dielétrico imposto por uma manobra de VCB — números reais do Documento A

### 1.1 Cenário, máquina e disjuntor

| Grandeza | Valor | Evidência |
|---|---|---|
| Motor | 1250 kW, 4,16 kV, 60 Hz, η = 0,95, fp = 0,88, $I_p/I_n$ = 6,5 | [FATO: doc A, Tabela I, p. 3] |
| Corrente nominal / de partida | $I_n \approx 207{,}5$ A; $I_p \approx 1349$ A | [CÁLCULO PRÓPRIO: $P/(\sqrt{3}\,V\,\eta\,\text{fp})$; $6{,}5\,I_n$] — coincide com "Line current (rms): 207.52 A" legível na Fig. 2 [FATO: doc A, Fig. 2, p. 4 — leitura de figura] |
| Cenário simulado | "intempestive interruption of a motor start commanded by the protection", com a máquina drenando a corrente de partida plena ($I_p/I_n$ = 6,5), "the chopping of a large inductive current under the worst possible conditions" | [FATO: doc A, p. 3, V] |
| Chopping $I_{ch}$ | 1 A a 2 A | [FATO: doc A, Tabela II, p. 3] |
| Recuperação dielétrica (RRDS) | $V_{wth}(t) = A\,t + B\,t^2$, $A = 0{,}801$ kV/ms, $B = 1{,}226$ kV/ms², $t$ contado "after arc extinction" | [FATO: doc A, p. 3, IV-B; Tabela II] |
| di/dt crítico | 5 A/µs a 15 A/µs; a corrente de AF "is interrupted when its di/dt at the zero crossing exceeds a critical value" | [FATO: doc A, p. 3, IV-B; Tabela II] |
| Dispersão de polos | "of the order of 14 ms to 25 ms" | [FATO: doc A, p. 3, IV-B; Tabela II] |
| Resistor do snubber | $R_s = 30\ \Omega$ por fase, "sized close to the surge impedance of the associated circuit" | [FATO: doc A, p. 2, III-A; Tabela II] |
| Passo e janela | 1 µs; 45 ms | [FATO: doc A, Tabela II, p. 3] |
| Modelo do motor | Ramo R–L série concentrado: $R_{eq}$ = 0,691 Ω, $L_{eq}$ = 8,9795 mH | [FATO: doc A, Fig. 2, p. 4 — leitura de figura]; confirmado como cargas `01ATA/B/C` com R = 0,691 Ω e L = 8,9795 mH no arquivo de referência [REPO: git show ad308d5:trt_all_motors_dt_ea.atp:736-738] |

### 1.2 Tabela III do Documento A e grandezas derivadas

| Fase | Sem snubber: pico (kV) / RRRV (kV/µs) | Com snubber: pico / RRRV | Pico sem (pu) | Pico com (pu) | Redução pico | Redução RRRV | $t_f \approx$ pico/RRRV sem / com (µs) |
|---|---|---|---|---|---|---|---|
| A | −30,24 / 13,90 | 6,35 / 3,28 | 8,90 | 1,87 | 79,0 % | 76,4 % | 2,18 / 1,94 |
| B | 41,44 / 15,05 | 13,65 / 13,11 | 12,20 | 4,02 | 67,1 % | 12,9 % | 2,75 / 1,04 |
| C | −38,30 / 19,00 | −9,98 / 9,43 | 11,28 | 2,94 | 73,9 % | 50,4 % | 2,02 / 1,06 |

Picos e RRRV: [FATO: doc A, Tabela III, p. 3]. Colunas em pu, reduções e $t_f$: [CÁLCULO PRÓPRIO: $V/3{,}397$; $(|V_{sem}|-|V_{com}|)/|V_{sem}|$; $V/\text{RRRV}$]. Nota de rodapé da Tabela III: "Phase B has the highest peak; the highest RRRV without mitigation is phase C (19.00 kV µs⁻¹)" [FATO: doc A, p. 3].

Ressalvas sobre a coluna $t_f$ [INFERÊNCIA FÍSICA]: (i) $t_f = V_{pk}/\text{RRRV}$ só é um tempo de frente se a frente for linear e se RRRV for a inclinação média até o pico — o artigo não define RRRV [FATO por omissão: doc A, p. 3]; (ii) o maior pico (B) e a maior RRRV (C) estão em fases distintas, e pico e RRRV de uma mesma fase podem pertencer a reignições distintas da sequência [FATO: doc A, nota da Tabela III; `out/etapa1/espira_a_espira_reignicoes_cumulativas.md`, C2]; (iii) com snubber, $t_f \approx 1$ µs nas fases B e C é igual ao passo de integração (1 µs) [FATO: doc A, Tabela II], de modo que as RRRV "com snubber" dessas fases são derivadas numéricas sobre 1–3 amostras e as frentes reais não estão resolvidas [INFERÊNCIA: fichamento A, §5.3]; (iv) a norma admite frentes de serviço "down to 0,1 µs" [NORMA: IEC 60034-15:2009, A.1], uma década abaixo do passo do estudo.

### 1.3 O que o Documento A afirma sobre o mecanismo — separação rigorosa

| Afirmação de A | Página | Status | Comentário |
|---|---|---|---|
| Chopping transfere $\tfrac12 L I_{ch}^2$ à capacitância de carga; primeiro pico "can reach several times the system peak voltage" | p. 2, II-A | [FATO: doc A] | A não escreve a forma fechada. Forma por balanço de energia: $\hat U_m = \sqrt{U_{pf}^2 + I_0^2\,L_b/C_b}$ [LITERATURA: Vollet e de Metz-Noblat, IPST 2007, p. 1–2, https://www.ipstconf.org/papers/Proc_IPST2007/07IPST106.pdf]. Com $L_{eq}$ = 8,98 mH e $I_{ch}$ = 2 A: $\tfrac12 L I^2$ = 18 mJ [CÁLCULO PRÓPRIO]; com $C$ = 10 nF [HIPÓTESE], $\Delta V \approx I_{ch}\sqrt{L/C} \approx 1{,}9$ kV — o chopping isolado não explica 41 kV; a escalada decorre das reignições, como o próprio A afirma ("the successive reignitions escalate the TRV to severe levels", p. 3) [INFERÊNCIA FÍSICA + FATO: doc A, p. 3]. |
| Reignição quando TRV > suportabilidade em recuperação; "the cycle repeats, generating a burst of steep front voltage escalations" | p. 2, II-A | [FATO: doc A] | Nenhuma contagem de reignições é dada [FATO por omissão]. |
| "Each reignition imposes a steep front impulse on the machine terminals" | p. 2, II-B | [FATO: doc A] | Mas a tensão nos terminais do motor não é reportada [FATO por omissão]. |
| "Because of travelling wave effects along the windings, a large fraction of this voltage appears across the first few turns [1], [6]" | p. 2, II-B | [FATO: doc A] | O motor é um ramo R–L concentrado [FATO: Fig. 2 — leitura; REPO: git show ad308d5:trt_all_motors_dt_ea.atp:736-738]; o efeito de onda viajante **no enrolamento** não é simulado — é argumento, não resultado [INFERÊNCIA]. Suporte normativo do princípio: "The highest components of both usually appear on the first or the last coil"; "no simple law has been found for pre-calculating this peak value" [NORMA: IEC 60034-15:2009, A.1 e A.3]. A fração "grande" não é quantificada por A nem por fonte primária acessada [INSERIR CITAÇÃO: Cornick e Thompson 1982; Wright, Yang e McLeay 1983; Narang et al. 1989 — textos não acessados]. |
| "Repetitive SFI stress is the driving mechanism of electrical treeing and of the slow, 'silent' fatigue of the interturn insulation" | p. 2, II-B | [FATO: doc A] | Sem referência de física de dielétricos e sem indicador mensurável associado ao termo "fadiga silenciosa" [FATO por omissão; fichamento A, §6.5]. Evidência externa pertinente: número de impulsos até ruptura decresce com a amplitude por lei de potência inversa; DP e degradação crescem quando o tempo de subida diminui [LITERATURA: CIGRE WG D1.43, TB 703, p. 21, 26–29, https://cigre.cz/dokumenty_komise/d1/WG%20D1.43_TB_Final.pdf]; mas 1000–8000 surtos de 3,0–7,8 pu (0,1 µs) não produziram degradação mensurável em 2 de 3 estatores [LITERATURA: Gupta, Lloyd e Sharma 1990, resumo via OpenAlex, DOI 10.1109/60.107228] — indício de **limiar**. |
| "The strong attenuation of the peak directly relieves the dielectric 'bombardment' of the first stator turns" | p. 4, V-C | [FATO: doc A] | A redução de pico (67 %) não se transfere integralmente à isolação entre espiras porque a RRRV cai apenas 12,9 % na fase B e a tensão longitudinal depende do tempo de subida [NORMA: IEC 60034-15:2009, A.3; INFERÊNCIA FÍSICA]. |
| "modelos tradicionais tratam a reignição como puramente probabilística, ignorando sua natureza determinística e caótica [8], [9]" | p. 1 | [FATO: doc A] | O modelo de A é fenomenológico (ramo RARC/LARC/CARC comutado), não Cassie–Mayr [FATO: doc A, Fig. 2 legenda, p. 4; REPO: git show ad308d5:trt_all_motors_dt_ea.atp:64-78, 154-156]. |
| Filtros RC fixos "mask the MHz range spectrum needed for condition monitoring" | p. 1 | [FATO: doc A] | Não demonstrado; em primeira ordem um supressor R–C com $R \approx Z_c$ atenua ≈ 6 dB de forma quase plana acima de ~20–50 kHz [CÁLCULO PRÓPRIO em `out/etapa1/metodos_monitoramento_estator_atual.md`, C4]; permanece [HIPÓTESE]. Além disso, o passo de 1 µs (Nyquist 500 kHz) não representa o espectro de MHz que A diz preservar [INFERÊNCIA]. |

### 1.4 Ponto de conexão do snubber e ponto de medição (fichamento reparado + arquivo de referência)

- Texto: "connected in parallel with the machine terminals" (p. 2, III e III-A); legenda da Fig. 1: "connected between the bus and the neutral", nó de entrada "from VCB / motor bus" [FATO: doc A, p. 2].
- Fig. 2: os ramos SCR–SCR–$R_s$ e o bloco `snub_ctrl` partem do nó do lado de carga do VCB, **a montante** do bloco LCC de 240 mm² que leva ao motor equivalente; não há ligação ao nó do motor (sonda `01AT`) [FATO: doc A, Fig. 2, p. 4 — leitura de figura, reconferida em recorte ampliado; fichamento A, §3.2].
- Confirmação independente no arquivo de referência: válvulas TYPE-11 entre `X0002C` (nó de carga do VCB `13XX0006X0002C`) e `XX0034`, e resistor de 30 Ω de `XX0034` para a terra; cargas do motor em `01ATA/B/C` separadas por segmento de cabo [REPO: git show ad308d5:trt_all_motors_dt_ea.atp:739, 837, 846-847, 736]. Verificação de colunas do cartão da l. 739: campo R (col. 27–32) = "30.", campos L e C vazios [REPO: verificação por colunas fixas]. **Correção ao mapa `out/repo/vcb_reignicao_snubber.md` §1.9**, que inferiu "[I] capacitores de 30 µF": o elemento é resistivo, coerente com $R_s$ = 30 Ω de A.
- Conclusão [INFERÊNCIA]: o snubber está no barramento do painel (lado de carga do VCB), não nos bornes físicos do motor; a literatura correlata mostra que proteção no painel pode não limitar a tensão no terminal do motor por reflexões no cabo [LITERATURA: Vollet e de Metz-Noblat 2007, §V-B, p. 5]. A tensão `01ATx` está disponível no `/OUTPUT` do arquivo de referência [REPO: git show ad308d5:trt_all_motors_dt_ea.atp:857-859] e pode ser reportada sem mudar o modelo.

### 1.5 Perfil de estresse por evento — definição operacional (proposta)

A camada digital de A extrai "peak voltage, dv/dt, absorbed energy, spectral content" e atualiza "an incremental insulation degradation model to estimate the remaining useful life" [FATO: doc A, p. 2, III-B], sem definir nenhuma das quatro grandezas [FATO por omissão]. Definição operacional proposta para cada evento $j$ (reignição ou chopping) de uma manobra $m$ [HIPÓTESE de projeto, ancorada nas normas indicadas]:

$$
\mathbf{s}_{m,j} = \big(V_{pk,j}^{\phi\text{-}g},\ V_{pk,j}^{\phi\text{-}n},\ T_{1,j},\ t_{r,j},\ (dv/dt)_{\max,j},\ E_{s,j},\ f_{dom,j},\ t_j\big)
$$

com $T_1 = 1{,}67\,(t_{90\%}-t_{30\%})$ [NORMA: IEC 60034-15:2009, 2.4], $t_r = t_{90\%}-t_{10\%}$ [NORMA: IEC 60034-18-41:2014, 3.13], $E_{s} = \int R_s\, i_s^2(t)\,dt$ durante a condução dos SCR [INFERÊNCIA FÍSICA: definição de energia em resistor; A cita "absorbed energy" sem definir], $f_{dom}$ a frequência dominante do transitório (100–200 kHz típicos [LITERATURA: Vollet 2007, p. 2]; 0,25–1,8 MHz no circuito de Helmer [LITERATURA: Wong, Snider e Lo, IPST 2003, p. 3–4]). O vetor por manobra é $\{\mathbf{s}_{m,j}\}_{j=1}^{n_{r,m}}$, com $n_{r,m}$ = número de reignições da manobra — grandeza que A não reporta (Seção 3).

Das oito componentes, o Documento A fornece numericamente apenas duas (pico e RRRV) e somente no VCB [FATO: doc A, Tabela III]. Nenhum valor de $E_s$, corrente no snubber, duração de condução, espectro ou contagem é dado [FATO por omissão; fichamento A, §5.5].

---

## 2. Comparação normativa própria: IEC 60034-15 / IEEE 522 para 4,16 kV vs. Tabela III

### 2.1 Níveis normativos para $U_N$ = 4,16 kV

| Referência | Isolação principal (fase-terra) | Entre espiras / SFI | Forma de onda | Evidência |
|---|---|---|---|---|
| IEC 60034-15:2009, Tabela 1, Notas 2 e 4 | $U_P = 4U_N + 5 = 21{,}64$ kV (Tabela 1 lista 21 kV para 4 kV) | $U'_P = 0{,}65\,U_P = 14{,}07$ kV (Tabela 1: 14 kV para 4 kV) | 1,2/50 µs; frente 0,2 ± 0,1 µs | [NORMA: IEC 60034-15:2009, Tab. 1, Notas 1–4; A.2]; [CÁLCULO PRÓPRIO] |
| IEC 60034-15:2025 (ed. 4.0), via CDV 2/2199/CDV (2024) | ≈ 5 pu = 16,98 kV (Tabela CDV, 4 kV: 16,3 kV); mínimo 8 kV | ≈ 3,5 pu = 11,89 kV (Tabela CDV, 4 kV: 11,4 kV); mínimo 5,6 kV | idem | [NORMA: IEC CDV 60034-15, 4.2 e Tab. 1 — rascunho "subject to change"; prefácio da ed. 2025 confirma harmonização com IEEE 522]; [CÁLCULO PRÓPRIO]; Tabela 1 final da ed. 2025 não acessada [INSERIR CITAÇÃO] |
| IEC 60034-15:2025, níveis reforçados (4.3) | ≈ 31,98 kV (+15 kV; teto 2× padrão) | ≈ 22,89 kV (+11 kV) | para "very frequent switching or aborted starts", mediante acordo | [NORMA: CDV, 4.3]; [CÁLCULO PRÓPRIO] |
| IEEE 522 (envelope) | 5 pu = 16,98 kV para $t_r \ge$ 1,2 µs | 3,5 pu = 11,89 kV em 0,1 µs; 1 pu em $t_r$ → 0 | patamares | [LITERATURA secundária: Baker/SKF citando IEEE 522-1992, Fig. 1; forma exata entre 0,1 e 1,2 µs não verificada — INSERIR CITAÇÃO: IEEE Std 522, Fig. 1] |
| IEEE 522-2023, máquinas em serviço | 75 % → 12,74 kV | 75 % → 8,92 kV | — | [LITERATURA secundária: Electrical Trader / Electrom — HIPÓTESE a verificar na norma] |
| IEC 60071-1, rede, $U_m$ = 7,2 kV (linha imediatamente superior a 4,4 kV) | BIL 40 ou 60 kV; 20 kV ef. | — | 1,2/50 µs | [NORMA: IEC 60071-1:2006, Tab. 2, p. 18]; a Tabela 2 não lista $U_m$ = 4,4 kV |

Nota 5 da Tabela 1 (2009), transcrita: os níveis "may not be adequate for special operating conditions (e.g. interrupted start or direct connection to overhead lines)" [NORMA: IEC 60034-15:2009, Tab. 1, Nota 5]. O cenário de A ("intempestive interruption of a motor start") corresponde, por interpretação deste documento, ao "interrupted start" da Nota 5 [INFERÊNCIA]; a ed. 2025 prevê níveis reforçados para "aborted starts" [NORMA: CDV, 4.3]. O Documento A cita a IEC 60034-15 (2025) e a IEC 60071-1 (2019) apenas como enquadramento ("framed against", "supporting compliance"), sem transcrever nível algum [FATO: doc A, p. 2 e p. 4; fichamento A, §7].

### 2.2 Razões TRV/nível — [CÁLCULO PRÓPRIO], com as ressalvas de 2.3

| Caso (Tabela III) | kV | pu | /$U_P$ 2009 (21,64) | /$U'_P$ 2009 (14,07) | /5 pu (16,98) | /3,5 pu (11,89) | /BIL rede 60 kV |
|---|---|---|---|---|---|---|---|
| B sem snubber | 41,44 | 12,20 | 1,91 | 2,95 | 2,44 | 3,49 | 0,69 |
| C sem snubber | 38,30 | 11,28 | 1,77 | 2,72 | 2,26 | 3,22 | 0,64 |
| A sem snubber | 30,24 | 8,90 | 1,40 | 2,15 | 1,78 | 2,54 | 0,50 |
| B com snubber | 13,65 | 4,02 | 0,63 | 0,97 | 0,80 | 1,15 | 0,23 |
| C com snubber | 9,98 | 2,94 | 0,46 | 0,71 | 0,59 | 0,84 | 0,17 |
| A com snubber | 6,35 | 1,87 | 0,29 | 0,45 | 0,37 | 0,53 | 0,11 |

Leituras [INFERÊNCIA FÍSICA a partir dos números]:

1. Sem mitigação, a TRV no VCB excede em ≈ 2× o nível de isolação principal (2009) e em ≈ 2,4–3,5× os níveis entre espiras/5 pu, e ultrapassaria até o nível reforçado SLI de 2025 (≈ 32 kV). Está acima do maior nível ensaiado por Gupta et al. 1990 (7,8 pu) e da faixa de ruptura de 5–10 pu reportada para isolação de espira nova [LITERATURA: Gupta et al. 1987, Parte 2, resumo; Baker/SKF, p. 5] — regime de falha imediata, não de fadiga [INFERÊNCIA]. Mas é ≈ 69 % do BIL de rede (60 kV): a máquina é o elo mais fraco da coordenação.
2. Com snubber, a fase B (4,0 pu) fica a 97 % de $U'_P$ (2009), a 115 % de 3,5 pu (2025/IEEE) e acima do critério de 75 % para máquinas em serviço — faixa "próxima da suportabilidade", que justifica um modelo de dano incremental e não um critério passa/não passa [INFERÊNCIA].
3. A comparação com o envelope tempo–tensão é obrigatória: Vollet e de Metz-Noblat aprovaram um motor de 11 kV pelo critério de magnitude (24 kV < 32 kV) e o reprovaram pelo tempo de subida ("the time rise was shorter than the wave defined in the IEC 60 034-15") [LITERATURA: IPST 2007, p. 5–6]. A Tabela III de A não permite essa comparação (item 1.2, ressalvas).
4. Comparativo de dv/dt de ensaio: SLI de 21,64 kV em 1,2 µs ≈ 18 kV/µs; SFI de 14,07 kV em 0,2 µs ≈ 70 kV/µs [CÁLCULO PRÓPRIO]. As RRRV de A (13–19 kV/µs) são da ordem do SLI e uma década abaixo do dv/dt do SFI — porém medidas no VCB, com passo de 1 µs.

### 2.3 Ressalvas que invalidam qualquer conclusão de conformidade

1. **TRV no VCB ≠ tensão nos terminais do motor.** A Tabela III é "at the VCB" [FATO: doc A, p. 3]; o snubber está no barramento do VCB, a montante do cabo de 240 mm² (Seção 1.4). O SFI normativo aplica-se "between the two terminals of the sample coils" e o SLI "between the coil terminals and earth" [NORMA: IEC 60034-15:2009, 4.2–4.3]; Vollet compara SFI com fase-neutro e SLI com fase-terra **no motor** [LITERATURA: IPST 2007, p. 4]. Nenhuma dessas grandezas é reportada por A.
2. **A não define BIL** do motor, do painel ou do cabo, nem aplica procedimento de coordenação da IEC 60071-1 [FATO por omissão; fichamento A, §7].
3. **A não define RRRV** nem o tempo de frente; a norma de máquinas usa $T_1 = 1{,}67(t_{90}-t_{30})$ e a de conversores $t_r = t_{90}-t_{10}$ [NORMA: IEC 60034-15:2009, 2.4; IEC 60034-18-41:2014, 3.13].
4. **Edição da norma**: a fórmula $4U_N+5$ / 0,65 pertence à ed. 2009; a ed. 2025 citada por A adota ≈ 5 pu / 3,5 pu (harmonização com IEEE 522), o que **reduz** o SFI para 4,16 kV de 14,1 para ≈ 11,9 kV [NORMA: CDV 2024; INFERÊNCIA a partir da Tabela CDV]. Qualquer alegação de "compliance" deve dizer com qual edição.
5. **A grandeza "TRV at the VCB"** pode ser tensão nó-terra do lado de carga (sonda "V" na Fig. 2) e não tensão através do gap [INFERÊNCIA: fichamento A, §3.2]; no arquivo de referência, os MODELS recebem `V_POS`/`V_NEG` e a saída pedida é `X0002A-C` (nó de carga) e `01ATA-C` (motor) [REPO: git show ad308d5:trt_all_motors_dt_ea.atp:585-587, 857-859].

---

## 3. Efeito cumulativo de múltiplas reignições

### 3.1 O que a literatura reporta (número por manobra e escalada)

| Fonte | O que reporta | Status |
|---|---|---|
| Vollet e de Metz-Noblat, IPST 2007, p. 2 | Sequência de reignição "may be repeated several times (up to 10) with increasing amplitude"; para quando a rigidez do gap supera a TRV; corrente de AF 100–200 kHz | [LITERATURA: https://www.ipstconf.org/papers/Proc_IPST2007/07IPST106.pdf] |
| Wong, Snider e Lo, IPST 2003, p. 4–6 | Número de reignições **aumenta** quando RRDS cai (50 → 30 V/µs) e quando a capacidade de extinção de AF é maior; escalada mais severa para RRDS 20–30 V/µs e tempo de arco 0–100 µs; Monte Carlo com 100 casos por combinação | [LITERATURA: https://www.ipstconf.org/papers/Proc_IPST2003/03IPST14a-03.pdf] |
| Xue e Popov, IPST 2013, Tab. V | Em 50 aberturas simuladas, 12/18/17 com reignição (motores 10,2/5,5/1,25 MW, 11 kV); pico até 10,4 pu (motor de 1,25 MW em partida) — tabula a **fração de aberturas com reignição**, não o número por abertura | [LITERATURA: https://www.ipstconf.org/papers/Proc_IPST2013/13IPST007.pdf] |
| Abdulahovic, tese Chalmers 2011, p. 101–120 | Carga indutiva com chopping 2,5–5 A: "very large number of reignitions"; abertura em vazio: poucas, < 1 pu; número de reignições difere entre simulação e medição, mas repetitividade e pico/frente do maior strike coincidem | [LITERATURA: https://publications.lib.chalmers.se/records/fulltext/148759/148759.pdf] |
| Glinkowski, Gutierrez e Braun, IEEE TPWRD 1997 | Probabilidade de reignições múltiplas "proportional to the arc angle and is very small"; capacitores de proteção aumentam a corrente de reignição | [LITERATURA: resumo OSTI https://www.osti.gov/biblio/477204] |
| King et al., IPST 2011, p. 2 | "three reignitions occurred" ao eliminar falta com VCB (citação indireta) | [LITERATURA-INDIRETA] |
| IEC 62271-110:2023, 3.6 | Evento de AF "single or multiple"; 4.3.2: manobra de motor em partida/rotor bloqueado "is usually the more severe operation"; 4.3.1: "No limits to the overvoltages are given" | [NORMA] |
| Gupta et al. 1987, Parte 1 (EPRI) | Dispositivos a vácuo produzem "numerosos transitórios de frente íngreme por operação de fechamento"; até 4,6 pu na partida; sem surtos significativos na abertura em regime | [LITERATURA: resumo OpenAlex, DOI 10.1109/TEC.1987.4765906] |

Síntese [INFERÊNCIA]: não existe, nas fontes acessadas, distribuição estatística publicada do número de reignições por manobra de motor de MT; há um teto ("até 10"), dependências qualitativas (RRDS, capacidade de extinção, tempo de arco, capacitância de carga) e frações de aberturas com reignição (24–36 %). A escalada de amplitude a cada reignição é consenso.

### 3.2 O que o Documento A mostra — leitura visual da Fig. 3

- Texto: apenas "successive arc reignitions" (p. 1), "multiple reignitions" (p. 1), "burst of steep front voltage escalations" (p. 2), "the successive reignitions escalate the TRV" (p. 3) [FATO: doc A]. **Nenhum número.**
- Fig. 3 (sem snubber), leitura de figura: evento menor em ≈ 19,7 ms (±6 kV nas fases B e C, oscilação ≈ 0,5 ms); surto principal a partir de ≈ 24,7 ms com sequência de excursões crescentes na fase B, da ordem de 18 → 23 → 28 → 37 → 41 kV em ≈ 0,6 ms; "ringing" decaindo até ≈ 28,5 ms; contagem visual da ordem de **6 a 10 excursões distinguíveis** na fase B [FATO: doc A, Fig. 3, p. 4 — leitura de figura; fichamento A, §5.4]. **A contagem não é determinável com confiabilidade a partir da figura impressa** [INFERÊNCIA].
- Os instantes 19,7 ms e 24,7 ms são compatíveis com os `T_OPEN` de 14,55 ms, 24,75 ms e 24,81 ms do arquivo de referência (instantes absolutos de separação, não desvios mútuos) [REPO: git show ad308d5:trt_all_motors_dt_ea.atp:589, 616, 643] — o que resolve a ambiguidade do "stagger 14–25 ms" a favor de instantes absolutos [INFERÊNCIA].
- Fig. 4 (com snubber): pico único de 13,65 kV na fase B seguido de patamar de ≈ 8 kV decaindo em ≈ 2 ms; ausência do ringing prolongado; o evento de 19,7 ms permanece com ≈ ±5–6 kV, sugerindo que o snubber não atuou nele [FATO: doc A, Fig. 4, p. 4 — leitura de figura; INFERÊNCIA]. Se o snubber reduz o **número** de reignições (não só a amplitude) não é afirmado por A [FATO por omissão]; capacitores de surto reduzem o número [LITERATURA: Abdulahovic 2011, p. 118; Xemard et al., IPST 2019, p. 5].

### 3.3 A premissa "5 a 7 reignições por ciclo"

- **Não consta do Documento A** [FATO: doc A, p. 1–3, verificado por leitura integral]. Não deve ser atribuída ao artigo.
- Situa-se dentro do teto "até 10" [LITERATURA: Vollet 2007], é compatível com a leitura visual de 6–10 excursões na Fig. 3 [leitura de figura], mas não é valor típico documentado [PREMISSA DO USUÁRIO — HIPÓTESE].
- A unidade "por ciclo" é ambígua: a sequência de reignições ocorre nos primeiros ~0,1–3 ms após a separação (modo A de Wong) ou até o próximo zero de 60 Hz (modo B); não se repete a cada ciclo de 60 Hz [LITERATURA: Wong 2003, p. 2, 5; INFERÊNCIA]. Definição recomendada: **reignições por polo por manobra**, $n_r$, tratada como variável aleatória com prior discreto em 0–10 [HIPÓTESE de modelagem].
- Sensibilidade aos parâmetros de A: a RRDS parabólica dá 2,0 kV em 1 ms e 34,7 kV em 5 ms, com inclinação instantânea $A + 2Bt$ que só atinge 20 kV/ms em $t \approx 7{,}8$ ms [CÁLCULO PRÓPRIO], contra 20–50 kV/ms lineares da literatura [LITERATURA: Vollet 2007, p. 3; Wong 2003, Tab. 1] e 5,5 kV/ms iniciais medidos [LITERATURA: Abdulahovic 2011, p. 112]; o di/dt crítico de 5–15 A/µs é 7–120× inferior aos 100–1000 A/µs da literatura [FATO: doc A, Tabela II; LITERATURA: Wong 2003, p. 1–2; Abdulahovic 2011, p. 29]. Ambos favorecem sequências longas e explicam a escalada a 41 kV; os resultados de A devem ser lidos como envelope conservador, não como estatística de campo [INFERÊNCIA]. O tempo para o gap de A suportar 41,44 kV é 5,50 ms após a extinção [CÁLCULO PRÓPRIO: raiz de $Bt^2 + At - V = 0$].

### 3.4 Acumulador de dano — equações e origem

**(D1) Lei de potência inversa em amplitude** — vida (ou número de impulsos) até falha:

$$L(V) = k\,V^{-n} \qquad\text{[LITERATURA: Feilat 2018, eq. (21), https://cdn.intechopen.com/pdfs/58128.pdf]}$$

$$N(V) \propto V^{-n}\ \text{(impulsos até ruptura, epóxi, frente 500 ns)} \qquad\text{[LITERATURA: CIGRE WG D1.43, TB 703, p. 29, Fig. 31]}$$

Expoentes medidos (fio esmaltado/pares torcidos, não mica-epóxi): $n$ = 3,8–7,1 (forma de onda), 4,5–11,7 (com/sem DP) [LITERATURA: CIGRE WG D1.43, Figs. 24 e 33]. Para mica-epóxi de MT sob impulsos de VCB: não localizado [INSERIR CITAÇÃO].

**(D2) IPL com limiar** (fadiga elétrica):

$$L = C\,(E - E_0)^{-m} \qquad\text{[LITERATURA: Tommasini 2011, https://arxiv.org/pdf/1104.0802]};\qquad t_f = t_0\,(E/E_0)^{-b}\ \text{[LITERATURA: Choudhary et al. 2022, eq. (4)]}$$

Evidência de limiar: 1000–8000 surtos de 3,0–7,8 pu (0,1 µs) sem degradação mensurável em 2 de 3 estatores [LITERATURA: Gupta, Lloyd e Sharma 1990, resumo]; PDIV/RPDIV como limiares físicos [NORMA: IEC 60034-18-41:2014, 3.2 e 3.9].

**(D3) Dependência do tempo de frente / dv/dt**: vida $\propto (dv/dt)^{-n'}$ [LITERATURA: Yang et al. 2023, High Voltage, resumo, DOI 10.1049/hve2.12375]; DP e degradação crescem quando $t_r$ diminui [LITERATURA: CIGRE WG D1.43, Figs. 26–27]. A fração da tensão terminal que cai na primeira bobina, $a(t_f)$, não tem "lei simples" [NORMA: IEC 60034-15:2009, A.3]; envelope de pior caso na Fig. 7 da IEC 60034-18-41 (valores não acessados) [NORMA; INSERIR CITAÇÃO].

**(D4) Regra de Miner** (dano linear cumulativo):

$$D = \sum_i \frac{n_i}{N_i},\qquad \text{falha em } D = 1 \qquad\text{[LITERATURA: ReliaSoft HotWire 116; Theofanous et al. 2025, eqs. (17)–(19), (25)]}$$

forma contínua para a parcela térmica: $LF = \int dt/L(\theta(t))$ [LITERATURA: Theofanous 2025, eq. (18)]. Limitações: assume linearidade e independência da ordem [LITERATURA: ReliaSoft]. Ma et al. (artigo 12) aplicam exatamente esta forma: $CL_n = 100/N_{n,life}$ (%), $CL_{1\,\text{ano}} = \sum_n CL_n$ [FATO: artigo 12, eqs. (1)–(2), p. 5].

**(D5) Parcela térmica** (para fundir com o histórico de partidas do Documento B):

$$L(\theta) = L_0\,\exp\!\big[-B\,(1/\theta_0 - 1/\theta)\big]\ \ \text{(Arrhenius–Dakin)};\qquad L(\theta) = L_0\,2^{(\theta_0-\theta)/\text{HIC}},\ \text{HIC} = 8\text{–}15\ ^\circ\text{C}\ \ \text{(Montsinger)}$$

[LITERATURA: Theofanous et al. 2025, eqs. (5), (9)–(10)]. Modelo multiestresse de Simoni: $L(V,T) = t_0\,(V/V_0)^{-n}\exp(-B\,c_T)$ com $c_T = 1/T_0 - 1/T$ (sinal corrigido; Feilat imprime $\Delta(1/T) = 1/T - 1/T_0$, que daria vida crescente com $T$) [LITERATURA: Feilat 2018, eq. (26); INFERÊNCIA FÍSICA sobre o sinal; INSERIR CITAÇÃO primária: Simoni; Montanari, Mazzanti e Simoni 2002].

**(D6) Acumulador por evento proposto para o módulo RUL** [HIPÓTESE de modelagem — todos os parâmetros a calibrar]:

$$
\Delta D_{m} = \sum_{j=1}^{n_{r,m}} \frac{1}{N_j},\qquad
N_j = N_0 \left(\frac{a(t_{f,j})\,V_{pk,j} - V_{th}}{V_{ref} - V_{th}}\right)^{-n} \left(\frac{t_{f,j}}{t_{f,0}}\right)^{m} 2^{(\theta_j-\theta_0)/\text{HIC}},\quad \text{se } a(t_{f,j})V_{pk,j} > V_{th};\ \ \frac{1}{N_j}=0 \text{ caso contrário}
$$

$$
D(t) = \sum_{m \le t} \Delta D_m + \int_0^t \frac{dt'}{L(\theta(t'))},\qquad
\widehat{\text{RUL}}_{N} = \frac{1 - D(t)}{\mathbb{E}[\Delta D_m]},\qquad
\widehat{\text{RUL}}_{t} = \frac{\widehat{\text{RUL}}_N}{\lambda_m}
$$

em que $\lambda_m$ é a taxa anual de manobras severas (partidas abortadas), $a(t_f)$ a fração na primeira bobina (D3), $V_{th}$ o limiar (D2), $m > 0$ penaliza frentes curtas (D3), e o segundo termo é a parcela térmica (D5). A saída deve ser distribuição (percentis B10/B50 de Weibull [LITERATURA: Feilat 2018, eqs. (1)–(2), (29)]) obtida por Monte Carlo sobre $n_r$, $V_{pk}$, $t_f$ e os parâmetros do VCB, com nível de confiança explícito [NORMA: ISO 13381-1:2015, 3.3 e 3.9].

**(D7) Como $n_r$ entra e o que domina** [CÁLCULO PRÓPRIO sobre a leitura visual da Fig. 3, rotulado como ilustração]: para a sequência lida 18 → 23 → 28 → 37 → 41,44 kV, $\sum_j (V_j/V_{\max})^n$ vale 1,97 ($n$ = 4), 1,59 ($n$ = 6,4) e 1,40 ($n$ = 9) "eventos equivalentes ao pico máximo". Sob IPL com $n \ge 4$, o dano da manobra é dominado pelas 1–2 últimas reignições (as de maior amplitude); a contagem $n_r$ é secundária frente à amplitude do maior strike — coerente com Abdulahovic, para quem simulação e medição divergem na contagem mas coincidem no maior strike [LITERATURA: Abdulahovic 2011, p. 118]. Consequência para a premissa "5–7": sob IPL, errar $n_r$ em ±2 altera $\Delta D_m$ em dezenas de por cento; errar o pico máximo em 2× altera-o em $2^n$ = 16–500× [INFERÊNCIA].

**(D8) Razão de dano por evento com e sem snubber** [CÁLCULO PRÓPRIO: $(41{,}44/13{,}65)^n$, sem limiar, sem correção de frente]: 68 ($n$ = 3,8); 148 ($n$ = 4,5); 1,2·10³ ($n$ = 6,4); 2,2·10⁴ ($n$ = 9); 4,4·10⁵ ($n$ = 11,7). Com limiar $V_{th}$ entre 4,0 e 12,2 pu (p. ex., 7,8 pu de Gupta 1990), o evento mitigado teria $\Delta D \approx 0$ e o não mitigado $\Delta D > 0$ — razão infinita [INFERÊNCIA]. Com correção de frente (D3), a razão cai, porque a RRRV da fase B só reduz 12,9 % [FATO: doc A, Tabela III; INFERÊNCIA]. Todos os expoentes provêm de fio esmaltado/epóxi puro, não de mica-epóxi [LITERATURA: CIGRE WG D1.43]; a transposição é [HIPÓTESE].

**(D9) Contagem anual ilustrativa** [HIPÓTESE ilustrativa]: com 5–7 reignições/polo/manobra [PREMISSA DO USUÁRIO] e 10 partidas abortadas/ano, 50–70 eventos severos/ano/polo — contra 10³–10⁴ surtos sem dano em Gupta 1990 a 3–7,8 pu; a fadiga só é relevante se $a(t_f)V_{pk}$ exceder $V_{th}$, o que reforça medir (não presumir) a fração espira-a-espira.

---

## 4. Matriz estressor × indicador × método de monitoramento × modelo de RUL (13 artigos)

Aderência (0–5) = utilidade direta para o módulo RUL de isolação de motor MT sob manobra de VCB com snubber seletivo; as notas por artigo reproduzem as dos fichamentos (§9.3) quando aplicável.

| # | Estressor (fonte no Doc A) | Indicador mensurável | Método de monitoramento | Modelo / algoritmo de RUL (artigo) | Aderência | Justificativa |
|---|---|---|---|---|---|---|
| 1 | Pico de TRV por reignição (Tab. III) | $V_{pk}$ fase-terra e fase-neutro no terminal do motor (pu) | Oscilografia disparada por evento, aquisição só na condução dos SCR [FATO: doc A, p. 2] com pre-trigger [INFERÊNCIA]; detector de pico analógico [FATO: artigo 02, p. 7–8] | Acúmulo de dano por evento (Miner) — Ma et al. (12), eqs. (1)–(3); LCM — Vichare e Pecht (07), Fig. 3–4 | 4 | O pico é a grandeza que A já fornece e que as normas usam como nível; falta apenas medi-lo no motor e não no VCB. |
| 2 | dv/dt / tempo de frente por reignição (RRRV, Tab. III) | $T_1$ (IEC), $t_r$ (10–90 %), $(dv/dt)_{\max}$ | Mesma oscilografia, banda ≥ 3,5 MHz e ≥ 50–100 MS/s para frentes de 0,1–0,2 µs [CÁLCULO PRÓPRIO em `out/etapa1/metodos_monitoramento_estator_atual.md`, 8.1] | IPL com correção de frente (D3); Yin et al. (08) usa pico de transitório como precursor, mas de semicondutor | 4 | A tensão entre espiras depende de $t_s$ [NORMA: IEC 60034-15:2009, A.3]; nenhum artigo dos 13 modela dv/dt como estressor dielétrico. |
| 3 | Número de reignições por manobra (não reportado por A) | $n_r$ por polo; intervalo entre reignições | Contagem de zeros de AF na corrente do VCB ou de incrementos de `reign_count` [REPO: app/preprocessor/atp_templates/vcb_reignition.mod:64, 101, 120] | Processo de choque/salto: "eventos abruptos que mudam a trajetória" — Muetze e Strangas (11), p. 6, 10; sem modelo quantitativo nos 13 | 3 | A literatura de VCB dá teto (≤ 10) e dependências; nenhum artigo do corpus trata degradação por eventos discretos esparsos. |
| 4 | Energia absorvida no snubber (citada por A, não calculada) | $E_s = \int R_s i_s^2 dt$; energia do arco | Corrente no ramo do snubber (TC de banda larga) | Severidade por energia liberada (analogia com fusão/vaporização de mancal) — Muetze e Strangas (11), p. 3–4 | 2 | Sem modelo de dano por energia para isolação; útil como covariável e para dimensionar $R_s$ (18–81 J por evento em 34,5 kV [LITERATURA: Mardegan, EngePower]). |
| 5 | Conteúdo espectral do transitório (citado por A) | Bandas 0,1–2 MHz; frequência dominante | Oscilografia; compatível com acoplador de DP de 80 pF (passa-altas ≈ 40 MHz) [LITERATURA: Sedding, Stone e Warren, IRMC 2017] | Nenhum dos 13 usa espectro de surto como HI; Wu et al. (13) cita features tempo-frequência para CNN | 2 | Serve a diagnóstico de reignição/pré-ignição, não a RUL direta; a alegação de mascaramento por RC é [HIPÓTESE]. |
| 6 | Estado do isolamento (consequência acumulada) | $Q_m$/NQN de DP on-line (≥ 3 kV, sem conversor) | IEC 60034-27-2:2023; percentis por classe de tensão [LITERATURA: Warren IRMC 2022, Tab. 1] | Tendência + limiar estatístico; a norma nega predição de tempo até falha [NORMA: IEC 60034-27-2:2023, Introdução] | 3 | Variável de estado lenta para atualizar $D$ (fusão bayesiana); não é RUL por si. |
| 7 | Estado do isolamento | tan δ / tip-up; IR/PI; EAR de surge test | IEC 60034-27-3/-27-4; IEEE 43; IEEE 522-2023 (75 % em serviço) | Portas go/no-go; HI dois estágios — Sharma e Seshadrinath (03), p. 4 | 2 | Off-line, periódico; IR/PI "cannot be used to predict the time to failure" [NORMA: IEC 60034-27-4:2018, Introdução]. |
| 8 | Resposta do isolamento a frente rápida | Overshoot da corrente de fuga (pico a pico ou positivo) | Detector de pico analógico (diodo 4 ns, op-amp 900 V/µs, 47 nF), 10 MSa/s [FATO: artigo 02, p. 7–8] | EKF sobre $I_{leak} = \alpha e^{\beta t}$, estados $[I_{leak}, \alpha, \beta]$, limiar = valor inicial (96 %) — Jensen, Strangas e Foster (02), eqs. (1)–(8), p. 5–6 | 3 | Arquitetura e instrumentação transferem-se; indicador validado em BT/térmico, não em MT/impulso [FATO: artigo 02, p. 2–4]. |
| 9 | Perfil de missão (manobras + partidas + carga) | Histograma de eventos por classe (rainflow em $\theta$; contagem em $V_{pk}$, $t_f$) | Registro SCADA/relé + oscilografia | Perfil de missão → carga → resistência → Miner, três escalas de tempo — Ma et al. (12), Seções II–V | 3 | Esqueleto de "onde a vida é gasta" (com/sem snubber); modelos de resistência não se transferem [FATO: artigo 12, p. 8–9]. |
| 10 | Mitigação seletiva como decisão | $p_1$, $p_{12}$, $p_{13}$, $p_{10}$ (FN/FP), $\lambda_1,\lambda_2,\lambda_3$ | Classificador + HMM sobre vetores por manobra | MTBF com/sem mitigação, caminhos 1–4, eqs. (7)–(11) — Strangas et al. (09), p. 5 | 3 | Único artigo que formaliza "quanto a mitigação decidida por prognóstico imperfeito melhora o MTBF"; taxa constante inadequada a desgaste [FATO/INFERÊNCIA: fichamento 09, §8]. |
| 11 | Modo de operação (regime / partida / manobra com ou sem snubber) | Lei de degradação comutada por modo (DMSV, $b$, $c$) | Detecção por resíduos (AGARR) — não transferível | MD-RUL, eqs. (4), (10)–(11) — Yu, Wang e Luo (06), p. 3, 5 | 3 | O snubber é, na linguagem do artigo, um comutador de modo que altera os coeficientes de degradação [INFERÊNCIA: fichamento 06, §9.1]. |
| 12 | Cargas de ciclo de vida medidas in situ | Δs, S_mean, ds/dt binados; OOR + rainflow | Sensores embarcados com extração on-board | LCM: carga → modelo de dano → vida consumida — Vichare e Pecht (07), Fig. 3–4, p. 5–6; MSET/SPRT para anomalia | 3 | Arquitetura de referência; nenhum modelo de dano fornecido [FATO: artigo 07, ausência de equações]. |
| 13 | Plataforma de envelhecimento/caracterização | Pico do transitório de desligamento vs. temperatura | Bancada com laço cenário → caracterização → DataService → módulo prognóstico | Sonnenfeld, Goebel e Celaya (04), Figs. 7–9 | 2 | Modelo de arquitetura de bancada (ref. [24] de A); indicador de semicondutor. |
| 14 | Série de indicador (HI) | HI univariado normalizado | — | CNN-BiLSTM-Attention — Yin, Hu e Cao (08); LSTM/BiLSTM — Siami-Namini et al. (10); NN/ANFIS — Ahsan et al. (05) | 2 / 1 / 2 | Pipelines reutilizáveis; BiLSTM não causal; dados run-to-failure inexistentes em MT; RUL não quantificada (08) [FATO/INFERÊNCIA: fichamentos 08, 10, 05]. |
| 15 | Enquadramento e taxonomia | Critérios de HI (monotonicidade, trendability, prognosability); incerteza | — | Revisões Liu et al. (01), Sharma e Seshadrinath (03), Wu et al. (13) | 2 / 3 / 2 | Vocabulário, escolha do paradigma híbrido, alerta de transferência negativa; nada de isolação. |

Observação transversal [INFERÊNCIA]: nenhum dos 13 artigos contém (i) um estressor dielétrico impulsivo, (ii) um indicador de isolação de MT ou (iii) um modelo estresse → dano para surtos esparsos; a lacuna que o "modelo incremental de degradação" de A pretende ocupar não é preenchida por nenhum deles, e as normas de ensaio negam explicitamente a predição de tempo até falha [NORMA: IEC 60034-27-2:2023; IEC 60034-27-3:2015; IEC 60034-27-4:2018].

---

## 5. Mapeamento direto com os cinco artigos-âncora

### 5.1 Jensen, Strangas e Foster (2018) — artigo 02: EKF, corrente de fuga, instrumentação de pico

- **O que o artigo dá** [FATO: artigo 02]: indicador = overshoot pico a pico da corrente de fuga transitória a degrau de 160 V com subida de 22 ns (p. 4–5); EKF com $x = [I_{leak}, \alpha, \beta]^T$ e $I_{leak} = \alpha e^{\beta t}$ (eqs. (7)–(8), p. 6); equações (1)–(6) do EKF (p. 5); limiar = valor inicial do overshoot, falha quando o decaimento está "within 96%" (p. 6); detector de pico analógico que reduz a amostragem de 1 GSa/s para 10 MSa/s (p. 7–9); o pico ocorre em janela de ≈ 35 ns (p. 7); "the actual dV/dt of the switching device is assumed to be constant for this method" (p. 3); estatores BT de 5 kW, envelhecimento térmico, n = 3 (p. 3–4).
- **O que A dá** [FATO: doc A, p. 2]: camada digital que extrai pico, dv/dt, energia e espectro "only during SCR conduction".
- **Mapeamento** [INFERÊNCIA]: (i) o detector de pico + filtro de mediana + diferença antes/depois (p. 7–8) é diretamente aplicável à captura do pico de tensão e da corrente de modo comum ($\sum$ correntes de fase, p. 4) a cada manobra, com amostragem da ordem de 10 MSa/s; (ii) a cadeia EKF → tendência → limiar → RUL é agnóstica ao indicador e pode receber $D(t)$ de (D6) ou uma variável lenta (Q_m, tan δ); (iii) a exigência de dV/dt constante (p. 3) é violada pelo VCB (chopping e reignições estocásticas), mas o snubber, ao conformar a frente, poderia tornar o estímulo quase repetível — [HIPÓTESE, fichamento 02, §9.1, item 5], testável em ATP variando `Seed` [REPO: app/preprocessor/atp_templates/vcb_reignition.mod:56, 83].
- **O que não transfere** [INFERÊNCIA]: indicador validado só termicamente, tendência "sobe e depois decai" sem razão física em mica-epóxi, limiar "96 % do inicial" inaplicável a motores em serviço há décadas, ausência de incerteza reportada (o EKF fornece $P_k$, não usado) [fichamento 02, §8–9]. Nota de transferibilidade: 3/5.

### 5.2 Ma, Liserre, Blaabjerg e Kerekes (2015) — artigo 12: perfil de missão → "perfil de surtos"

- **O que o artigo dá** [FATO: artigo 12]: perfil de missão anual (vento + ambiente) → perfil de carga térmica em três escalas de tempo (3 h / 1 s / 0,5 ms; p. 3–8) → contagem rainflow com $(\Delta T_j, T_{jm}, t_{cycle})$, 460 ciclos/ano (p. 4) → modelos de resistência do fabricante → $CL_n = 100/N_{n,life}$, $CL = \sum CL_n$ (eqs. (1)–(2), p. 5) → extrapolação ponderada pela distribuição de condições, eq. (3) (p. 7) → **distribuição da vida consumida por mecanismo e por condição** (Figs. 11, 17, 18, 20). Advertência: "if too rough models and longer time step are used, the generated loading profile may not contain enough thermal dynamics" (p. 2). Validação do estresse (câmera IR), não da vida (p. 10–11).
- **Mapeamento para A** [INFERÊNCIA; fichamento 12, §9.1, T1–T7]: perfil de missão do motor = histórico de manobras (número, instante de abertura relativo ao zero de corrente, estado do motor: partida/carga/vazio, snubber ativo ou não) + partidas + carga; perfil de carga = $\{\mathbf{s}_{m,j}\}$ da Seção 1.5, com o ATP no papel do modelo eletro-térmico de Ma; "curto prazo" (µs) = reignições; "médio prazo" (s) = partida; "longo prazo" = térmica de regime; resistência = curvas $N(V, t_f)$ (D1–D3), a obter em ensaio; acúmulo = (D4); extrapolação = ponderar cenários (abertura em partida × em carga × em vazio; com × sem snubber) pela frequência anual, análogo à eq. (3). Entregável: "fração da vida consumida por manobra de VCB sem snubber vs. com snubber" — o quociente auditável que justifica a mitigação.
- **O que não transfere**: modelos B10 do fabricante e Coffin–Manson (eq. (5), p. 8); ripple de $T_j$ a 50 Hz; Miner linear questionável para dano dielétrico com limiar (N3 do fichamento 12); perfil determinístico único (as manobras exigem Monte Carlo). Nota: 3/5.

### 5.3 Yin, Hu e Cao (2024) — artigo 08: CNN-BiLSTM-atenção sobre pico transitório

- **O que o artigo dá** [FATO: artigo 08]: entrada única = pico de tensão coletor–emissor no desligamento ($V_{ce\text{-}off\text{-}peak}$), citando Sonnenfeld et al. (artigo 04) como origem do indicador (p. 3); pré-processamento: remoção de outliers → EMA de 2ª ordem (eq. (9)) → Min-Max (eqs. (10)–(11)) (p. 3–4); arquitetura 1D-CNN (32 filtros) → BiLSTM (2×32) → atenção aditiva (eqs. (5)–(8)) → FC (p. 2–3, Fig. 2); métricas RMSE 0,0354, MAE 0,0248, R² 0,958 (Tab. II, p. 5); uma trajetória run-to-failure (NASA PCoE, IRG4BC30K, latch-up no 418º ciclo, p. 3).
- **Ponto de contato com A** [INFERÊNCIA]: A já prevê extrair pico, dv/dt, energia e espectro por evento (p. 2) — exatamente o tipo de feature de "pico transitório" que Yin usa como entrada. Mas há inversão de papel: no IGBT o pico é **sintoma** (cai com o envelhecimento); no motor o pico de surto é **causa** (estresse). A analogia útil é usar a sequência de vetores por manobra como covariável de um modelo sequencial **causal** (LSTM unidirecional ou GRU), com atenção temporal para pesar eventos raros (manobras com reignição) — [fichamento 08, §9.1].
- **O que não transfere**: RUL não é estimada (o modelo prevê o próximo valor do indicador, p. 5); BiLSTM e suavização em série completa vazam futuro (incompatível com predição on-line); baselines possivelmente importados; sem incerteza; regime de estresse contínuo (1 kHz) vs. episódico [fichamento 08, §8–9]. Nota: 2/5.

### 5.4 Strangas, Aviyente, Neely e Zaidi (2013) — artigo 09: prognóstico + mitigação → MTBF

- **O que o artigo dá** [FATO: artigo 09]: "a methodology to calculate the mean time between failures with and without mitigation" (p. 1); caminhos para a falha (Fig. 2, p. 5): (1) não detectada, $\text{MTBF}_1 = 1/(p_1\lambda_1)$ (eq. 7); (2) detectada tarde com falta secundária, $\text{MTBF}_2 = 1/(p_{12}\lambda_1) + 1/\lambda_2$ (eq. 8); (3) detectada cedo por prognóstico e mitigada, $\text{MTBF}_3 = 1/(p_{13}\lambda_1) + 1/\lambda_3$ (eq. 9); (4) falso positivo, $\text{MTBF}_4 = 1/\lambda_{10} + 1/\lambda_3$ com $\lambda_{10} = p_{10}/t_{sample}$ (eqs. 10, 16); $\lambda_{sys} = \sum_{i=1}^4 1/\text{MTBF}_i$ (eq. 11); "A drive, then, once it is modified to alleviate the effects of a fault, has decreased life expectancy" (p. 1); limiar de decisão 0,4 sobre $P[q_{t+1} = S_6]$ elimina FP e FN na sequência sintética (p. 8).
- **Mapeamento para A** [INFERÊNCIA; fichamento 09, §9.1]: a **mitigação seletiva** de A ("dissipative elements are present only while the anomaly lasts" [FATO: doc A, p. 2]) é uma "mitigation" no sentido de Strangas: "fault 1" = degradação incipiente da isolação de espira por surtos; caminho 3 = snubber ativo/decisão de manobra a tempo, com $\lambda_3$ incluindo a taxa de falha do próprio snubber (o TOR CIGRE C4.76 alerta que supressores "may gradually deteriorate due to cumulative effects" [CIGRE: TOR WG C4.76, 2023]); caminho 4 = disparo espúrio do snubber (custo de confiabilidade pequeno, mas não nulo). A seletividade de A é, nesse vocabulário, a escolha do limiar (nível de breakover do DIAC, não informado por A [FATO por omissão]) que equilibra $p_{10}$ e $p_1$.
- **Diferença estrutural**: em A a mitigação é reflexiva (hardware, sem decisão digital) e a camada digital "advise switching decisions" [FATO: doc A, p. 1]; em Strangas a mitigação é decidida pelo prognóstico. Os dois níveis coexistem: o hardware protege sempre; a camada digital decide restrição de partidas/intervenção.
- **O que não transfere**: taxa de falha constante (desgaste tem risco crescente); indicador $i_d$ com Choi–Williams (motor DOL não tem $i_d$); eq. (13) "Arrhenius" dimensionalmente ambígua [fichamento 09, §8]. Nota: 3/5.

### 5.5 Vichare e Pecht (2006) — artigo 07: life-cycle load monitoring

- **O que o artigo dá** [FATO: artigo 07]: quatro abordagens de PHM (BIT; canários; precursores; dano acumulado por cargas medidas in situ) (p. 1); LCM: cargas medidas → extração embarcada de $(\Delta s, S_{mean}, ds/dt)$ → histogramas binados → modelos de estresse/dano → vida consumida/remanescente (Figs. 3–4, p. 5–6); "If one can measure these loads in-situ, the load profiles can be used in conjunction with damage models to assess the degradation due to cumulative load exposures" (p. 5); MSET + SPRT para resíduos (p. 4); FMMEA como passo inicial (p. 6–7); "different approaches can be implemented based on the same sensor data" (p. 6); condição de sucesso: recuperar o custo do PHM (p. 3).
- **Mapeamento para A** [INFERÊNCIA; fichamento 07, §9]: a camada digital de A é um LCM cujo "sinal carga-tempo" é a tensão no terminal do motor durante a manobra e cujos parâmetros extraídos são $\mathbf{s}_{m,j}$; o snubber é um modificador da distribuição de cargas (reduz pico; pouco a RRRV na fase B), avaliável pela mesma contabilidade de dano. O princípio "mesmo dado, várias abordagens" corresponde à afirmação de A de que "the same event that is being mitigated can also be recorded and used for asset health estimation" [FATO: doc A, p. 4]. Canário: corpos de prova de isolação no mesmo barramento com espessura reduzida [HIPÓTESE].
- **O que não transfere**: nenhum modelo de dano, nenhuma métrica; precursores de eletrônica. Nota: 3/5.

### 5.6 Complementos de dois outros artigos

- **Yu, Wang e Luo (2014) — artigo 06**: "the same component will exhibit different degradation behaviors at different operating modes" (p. 3); EOL/RUL com limiar explícito, eqs. (10)–(11) (p. 5); prognóstico sequencial disparado por mudança de modo, estimativas independentes (p. 5). Mapeamento: modos = {regime, partida, partida N-1, manobra sem snubber, manobra com snubber}; cada manobra dispara reestimação [INFERÊNCIA; fichamento 06, §9.1].
- **Muetze e Strangas (2016) — artigo 11**: canal "History of Causes" (causas previstas, não medidas) na Fig. 4 (p. 7); "bearing currents cannot be monitored through the measurement of stator currents, they can only be estimated from operating conditions" (p. 9) — análogo: a sobretensão no terminal do motor não é medida rotineiramente, mas é calculável por ATP a partir do estado da manobra; métrica de valor $V = (E_{ref}-E_{prog})/(E_{ref}-E_{perf})$ (eq. (1), p. 8) como critério de validação orientado a custo [FATO: artigo 11; INFERÊNCIA].

---

## 6. O que o Olivas já entrega, divergências e experimento computacional mínimo reproduzível

### 6.1 Inventário verificado

| Item | O que existe | Evidência |
|---|---|---|
| Template MODELS de reignição (linhagem L2) | `MODEL vcb_reignition` com DATA `I_chop_mean {dflt: 5.0}`, `I_chop_sigma {dflt: 1.0}`, `didt_crit_0 {dflt: 16.0}` A/µs, `didt_sigma {dflt: 0.034}`, `k_dielec {dflt: 17.0}` V/µs, `U0_dielec {dflt: 690.0}` V, `T_bounce {dflt: 5.0e-4}`, `T_open {dflt: 0.05}`, `Seed {dflt: 1}`; OUTPUT `switch_cmd`, `reign_count` | [REPO: app/preprocessor/atp_templates/vcb_reignition.mod:47-64] |
| Lei de recuperação (L2) | Linear: `U_dielec_t := U0_dielec + k_dielec * (t - t_contact) * 1e6`; breakdown se `abs(v_branch) > U_dielec_t` → `reign_count := reign_count + 1` | [REPO: vcb_reignition.mod:115-120] |
| Critério de di/dt (L2) | Reignição imediata se `abs((i_branch - i_last)/timestep) > didt_crit_t*1e6` no corte; `didt_crit_t := didt_crit_0 + didt_sigma*(t - T_open)*1e6` | [REPO: vcb_reignition.mod:98-101] |
| Chopping (L2) | `I_chop_rnd := I_chop_mean + I_chop_sigma * normal(Seed)` — uma amostra por realização | [REPO: vcb_reignition.mod:83] |
| Bloco `T_bounce` | Vazio (só comentário) | [REPO: vcb_reignition.mod:123-126] |
| Defaults e OUTPUT emitidos | `VCB_REIGNITION_DEFAULTS` (5.0, 1.0, 16.0, 0.034, 17.0, 690.0, 5e-4, 1); USE emite `SWCMD_<inst> := switch_cmd`, `REIGN_<inst> := reign_count` | [REPO: app/preprocessor/vcb_model_emitter.py:103-112, 222-224] |
| Estado da cadeia L2 | `/MODELS` inserido em `INSERT_AT = 1` (antes dos cartões dT/Tmax); sem `MODELS`/`ENDMODELS`; wiring TACS manual; reparse perde `models/uses` | [REPO: app/preprocessor/bridge_to_atp.py:2382-2390]; experimento [V] em `out/repo/vcb_reignicao_snubber.md`, §2.2 e Anexo C |
| Arquivo de referência (linhagem L1, histórico git) | dT = 1 µs, Tmax = 45 ms (l. 10); `MODEL VCB_Rr/Rs/Rt` com `VWITHSTANDKV := RRDS_A*T_MS + RRDS_B*T_MS²` (l. 140-142), $t$ contado desde o último zero de corrente com `ABS(I_PREV) > 0.01` (l. 129-138); reignição se `ABS(V_CB) > V_WITH*1.1` (l. 182); extinção de AF se `ABS(DI_DT) > DIDT_CRIT*1e6 AND ABS(I_CB) < 0.1` (l. 191) **ou** se `ABS(I_CB) < 0.1 AND T_ZERO >= 0` (l. 198); chopping quando `ABS(I_CB) <= I_CHOP` (l. 165); USEs com `T_OPEN` 14,55/24,75/24,81 ms, `RRDS_A = 0.801`, `RRDS_B = 1.226`, `I_CHOP` 1/2/2 A, `DIDT_CRIT` 5/15/15 A/µs (l. 589-593, 616-620, 643-647); `MODEL SNUB_CTRL` com latch `FM := 1` se qualquer `ST* > 1.9` (l. 571-573); seis TYPE-11 (`Vig` = 3 kV, `Ihold` = 1 A, `tdeion` = 5 ms) entre `X0002x` e `XX0034/35/42` (l. 846-851); resistor de 30 Ω de `XX0034/35/42` para a terra (l. 739-741, campo R col. 27–32); motor R–L 0,691 Ω / 8,9795 mH (l. 736-738); `/OUTPUT` inclui `01ATA-C` e `X0002A-C` (l. 857-859) | [REPO: git show ad308d5:trt_all_motors_dt_ea.atp:linhas indicadas] |
| Correspondência L1 ↔ Documento A | Os valores de `RRDS_A/B`, `I_CHOP`, `DIDT_CRIT`, `T_OPEN`, dT, Tmax, $R_s$ e a topologia (SCR antiparalelo + R para a terra no barramento do VCB) coincidem um a um com as Tabelas II e a Fig. 1–2 de A; o caminho `PATENTE\MVP` do `.acp` (l. 3-4) é coerente com a patente [23] de A | [REPO: idem]; [FATO: doc A, Tabelas II, Fig. 1–2]; conclusão de que o arquivo de referência **é** o modelo de A: [INFERÊNCIA forte, não afirmada por A] |
| Métricas de transitório | `compute_transient_metrics` (pico, mínimo, RMS, frequência por zeros, amortecimento); `compute_trv_metrics` com RRRV = pico/tempo ao pico (média) e envelope IEC simplificado `kpp = 1.3`, `t3 = 4·uc` — **sem chamador** na aplicação | [REPO: app/analysis/transient_metrics.py:41-88, 91-159 (l. 131, 150-157)] |
| Analisador TRT | `_compute_max_rrrv` = máx de \|Δv/Δt\| após média móvel (`filter_window = 5`), janela opcional; `analyze_trt(waveform, envelope, ...)` — sem ponte PL4 e sem chamador na GUI | [REPO: app/postprocessor/trt_analyzer.py:299-360, 372-378] |
| Auxiliares de extração | `_find_zero_crossings` (interpolação linear, só `v[i]·v[i+1] < 0`), `_find_peaks` (máximos locais de \|v\|, desigualdade estrita) | [REPO: app/analysis/transient_metrics.py:204-224] |
| Leitura de resultados | `AtpResults{variables, time, data, delta_t, n_steps}`; rótulo `"9": "TACS"` para saídas MODELS; `find_result_files` procura só ao lado do `.atp` | [REPO: app/simulation/results_reader.py:15-25, 104-110, 385-405] |
| Execução | `RunResult{success, ..., run_dir, log_file}`; `runs/<stem>_<timestamp>/` | [REPO: app/simulation/runner.py:11-19, 320-326] |
| Varredura paramétrica | `SweepParameter(model_name, param_name, values)`; `SweepCase` sem `run_dir`; `run_parametric_sweep(base_file, parameters, runner, output_dir)` | [REPO: app/llm/parametric.py:21-45, 81-86] |
| Motor no preprocessor | `emit_motor_metadata_lines` emite comentários; "Não emite cartão UM" | [REPO: app/preprocessor/motor.py:353-360] |
| Confiabilidade | Índices IEEE 1366 (SAIFI, SAIDI, MTBF, MTTR) | [REPO: app/postprocessor/reliability.py:1-24] |
| Proveniência | `STANDARDS_CATALOG` (sem IEC 60034-15, IEC 62271-100/-110, IEEE 522), `citation()` | [REPO: app/postprocessor/audit_trail.py:71-92] |
| Plugin de estudo | `@register_study(name)` | [REPO: app/plugins/registry.py:40-52] |
| Ausências | `grep -rniE "rainflow|weibull|arrhenius|remaining useful|prognos" app --include=*.py` → vazio | [REPO: verificado nesta sessão, HEAD 26d9248] |

### 6.2 Divergências entre o modelo do repositório (L2), o arquivo de referência (L1) e o Documento A

| Aspecto | L2 (`vcb_reignition.mod`) | L1 (referência, git) | Documento A | Consequência |
|---|---|---|---|---|
| Lei de recuperação | Linear: $U_0 + k\,\Delta t$, $k$ = 17 V/µs = 17 kV/ms, $U_0$ = 690 V [REPO: .mod:52-53, 115] | Parabólica $A t + B t^2$, $A$ = 0,801 kV/ms, $B$ = 1,226 kV/ms² [REPO: ref:140-142, 590-591] | Idem L1 [FATO: doc A, Tabela II] | Em 1 ms: L2 = 17,7 kV; L1/A = 2,0 kV [CÁLCULO PRÓPRIO]. L2 é ≈ 9× mais rígido no primeiro milissegundo → muito menos reignições que A; L2 aproxima-se dos 20–50 kV/ms da literatura [LITERATURA: Vollet 2007; Wong 2003]. A lei parabólica de A só ultrapassa 17 kV/ms de inclinação em $t > 6{,}6$ ms [CÁLCULO PRÓPRIO: $(17-0{,}801)/(2\cdot1{,}226)$]. |
| Origem de $t$ | Desde o corte (`t_contact`) [REPO: .mod:106, 115] | Desde o último zero de corrente com \|I_PREV\| > 0,01 A — reinicia a cada reignição [REPO: ref:129-138] | "after arc extinction" [FATO: doc A, p. 3] | L1 implementa literalmente A: a suportabilidade recomeça do zero após cada extinção, o que favorece sequências longas [INFERÊNCIA]; Wong e Xue & Popov contam de $t_{open}$ [LITERATURA]. |
| Fator de reignição | Nenhum (`abs(v) > U_dielec_t`) [REPO: .mod:116] | `ABS(V_CB) > V_WITH*1.1` [REPO: ref:182] | Não mencionado [FATO por omissão] | Detalhe de implementação não reportado por A. |
| Chopping | $\mathcal N(5, 1^2)$ A, uma amostra/realização [REPO: .mod:48-49, 83] | Determinístico 1/2/2 A [REPO: ref:592, 619, 646] | 1–2 A [FATO: doc A, Tabela II] | L2 = 5 A é o valor médio de Cu/Cr (2–10 A) [LITERATURA: Vollet 2007; Xue e Popov 2013]; A/L1 estão no limite inferior. Energia $\tfrac12 L I^2$: 112 mJ (5 A) vs 4,5–18 mJ (1–2 A) [CÁLCULO PRÓPRIO]. |
| di/dt crítico | 16 A/µs + 0,034 A/µs²·Δt; **reignição** se \|di/dt\| > crítico no corte [REPO: .mod:50-51, 98-101] | 5/15 A/µs; **extinção** de AF se \|di/dt\| > `DIDT_CRIT` [REPO: ref:191, 593, 620] | 5–15 A/µs; AF "interrupted when its di/dt ... exceeds a critical value" [FATO: doc A, p. 3] | Convenções **opostas** entre L2 e L1/A, e ambas divergem da convenção de Helmer/Wong/Abdulahovic (extinção quando \|di/dt\| **é menor** que a capacidade, 100–600 A/µs) [LITERATURA: Wong 2003, p. 2; Abdulahovic 2011, p. 28]. Em L1, a segunda condição (l. 198: extinção a qualquer \|I_CB\| < 0,1 A após um zero) torna a extinção quase certa a cada zero de AF, maximizando o número de reignições [INFERÊNCIA a partir do código]. |
| Snubber | Inexistente no preprocessor (nenhum `.ocomp`, nenhum emissor) [REPO: `out/repo/vcb_reignicao_snubber.md`, §1.9, §5 item 6] | TYPE-11 (`Vig` 3 kV, `Ihold` 1 A, `tdeion` 5 ms) + R 30 Ω para terra; gate = latch `FM` quando qualquer polo `CB_STATE ≥ 2` [REPO: ref:571-580, 739-741, 846-851] | SCR antiparalelo + $R_s$ = 30 Ω; disparo por DIAC "depends only on the local electrical conditions"; bloqueio no zero de corrente [FATO: doc A, p. 2] | L1 dispara por **estado do disjuntor** (latch) e por tensão > 3 kV (`Vig`), não apenas por condição local — coerente com a legenda da Fig. 1 ("reads the breaker states") e em tensão com o texto ("no digital command") [FATO: doc A, p. 2; INFERÊNCIA]. `tdeion` = 5 ms impede redisparo por 5 ms após bloqueio [REPO: ref:846]; A diz que o ramo "is ready for the next event" [FATO: doc A, p. 2]. O latch nunca é reiniciado [REPO: ref:571-573]. |
| Mapa do repositório | — | Mapa inferiu "capacitores de 30 (µF)" [I] | — | **Corrigido**: campo R = 30 Ω (col. 27–32), L e C vazios [REPO: verificação por colunas, ref:739]. |
| Contadores | `reign_count` interno, sem RECORD, sem carimbo de tempo [REPO: .mod:64, 101, 120] | Nenhum contador; só transições `CB_STATE` 2↔3 [REPO: ref:181-205] | Não reporta contagem [FATO por omissão] | Nenhuma das três fontes exporta $n_r$ ao PL4. |
| Motor | Comentários (sem UM) [REPO: motor.py:353-360] | R–L concentrado [REPO: ref:736-738] | R–L concentrado [FATO: Fig. 2 — leitura] | Nenhuma representa a distribuição espira-a-espira; $a(t_f)$ tem de vir de MTL/FEM externo [INSERIR CITAÇÃO] ou de envelope de pior caso [NORMA: IEC 60034-18-41, Fig. 7]. |
| RRRV | Média pico/tempo [REPO: transient_metrics.py:131] vs máx \|Δv/Δt\| filtrado [REPO: trt_analyzer.py:299-360] | — | Não definida [FATO por omissão] | Duas definições no repositório; A não escolhe nenhuma. Registrar a definição no `source` de cada métrica. |

### 6.3 Experimento computacional mínimo reproduzível — `.atp` como fonte da verdade

Princípio: "O .atp é a fonte única da verdade" [REPO: `ORQUESTRADOR_AGENTE_ATP_STUDIO.txt:169-181` e `CONTRIBUTING_ATP_STUDIO.txt:23-30`, conforme `out/repo/vcb_reignicao_snubber.md`, §2.3]; o par (`.atp` executado em `runs/<caso>_<ts>/` + `.pl4`) é a verdade do caso, rastreável por SHA-256 [REPO: app/postprocessor/audit_trail.py:135, via mapa]. O experimento usa a linhagem L1 porque é a única com malha fechada VCB ↔ rede e com snubber já modelados; a linhagem L2 exige antes as correções E3–E5 do mapa (`MODELS/ENDMODELS`, INPUT/OUTPUT globais, posição da seção, TYPE-13 + MEASURING) [REPO: `out/repo/vcb_reignicao_snubber.md`, §3, E3–E5; §2.2 [V]].

**Passo 0 — Fixture.** Restaurar `trt_all_motors_dt_ea.atp` a partir de `git show ad308d5:trt_all_motors_dt_ea.atp` para um diretório de trabalho fora do repositório (ou como fixture sintética sem dados proprietários, conforme R5 do mapa); registrar SHA-256. Confirmar unidades: XOPT/COPT em branco na l. 10 → L em mH e C em µF [REPO: ref:9-10; INSERIR CITAÇÃO: ATP Rule Book, cartões diversos]. Verificar o wiring `I_CB* := MM0003/6/9 = v(nó)` (risco R4 do mapa) antes de confiar nas correntes.

**Passo 1 — Casos.** (a) `sem_snubber`: remover ou desabilitar os seis TYPE-11 (ou fixar `FM := 0`); (b) `com_snubber`: arquivo original. Ambos com `T_OPEN` 14,55/24,75/24,81 ms, `RRDS_A/B` 0,801/1,226, `I_CHOP` 1/2/2 A, `DIDT_CRIT` 5/15/15 A/µs — reprodução direta das Tabelas II–III de A [FATO: doc A]. Critério de aceitação: picos e RRRV em `X0002A-C` dentro de ±5 % da Tabela III (41,44/15,05; −38,30/19,00; −30,24/13,90 sem snubber; 13,65/13,11; −9,98/9,43; 6,35/3,28 com snubber) [CÁLCULO PRÓPRIO: tolerância arbitrada; HIPÓTESE de que a sonda "V" de A é `X0002x`].

**Passo 2 — Execução e leitura.** `AtpRunner.run(atp)` → `runs/<stem>_<ts>/` [REPO: runner.py:127-318, 320-326]; `read_pl4` → `AtpResults` [REPO: results_reader.py:46-96]; variáveis alvo: `v(X0002A-C)` (barramento do VCB), `v(01ATA-C)` (terminal do motor) [REPO: ref:857-859]; corrente do VCB pela segunda chave MEASURING de cada polo (col. 80 = 1, l. 839, 842, 845); corrente do ramo $R_s$ pelos cartões de 30 Ω (col. 80 = 1, l. 739-741), que permite $E_s = \sum R_s i_s^2 \Delta t$ sem alterar o modelo; as válvulas TYPE-11 pedem saída com col. 80 = 2 (l. 846-851) — tensão, segundo a convenção usual de coluna 80 dos cartões de chave [REPO: ref:739-741, 837-851; convenção de coluna 80: INSERIR CITAÇÃO — ATP Rule Book]. Validar `delta_t` = 1 µs e emitir aviso de resolução insuficiente para frentes < 2 µs (risco 5 de `out/repo/trt_transitorios_simulacao.md`).

**Passo 3 — Extração por evento** (módulo novo `app/analysis/dielectric_stress.py`, conforme E9 do mapa e §3.1 de `trt_transitorios_simulacao.md`):
1. Segmentar por polo a partir dos zeros da corrente da chave (`_find_zero_crossings`, [REPO: transient_metrics.py:204-215]) — cada zero de AF seguido de nova condução é uma reignição; contar $n_r$ por polo.
2. Para cada evento: $V_{pk}$ (nó de carga e nó do motor, fase-terra; fase-neutro por diferença de fases), $T_1$ e $t_r$ (interpolação nos níveis 30/90 % e 10/90 %), $(dv/dt)_{\max}$ via `_compute_max_rrrv` com `filter_window` explícito [REPO: trt_analyzer.py:299-360], $E_s = \sum R_s i_s^2 \Delta t$ sobre a corrente da válvula, $f_{dom}$ por `compute_transient_metrics.frequency_hz` [REPO: transient_metrics.py:72-77].
3. Registrar `delta_t`, `filter_window`, `window_us` e SHA-256 do `.atp` e do `.pl4` no payload de proveniência (`compute_input_checksum`).

**Passo 4 — Normalização normativa.** Converter cada evento em fração do envelope: $S_j = V_{pk,j}/U_{env}(t_{f,j})$ com $U_{env}$ parametrizado por edição (2009: 21,64/14,07 kV; 2025-CDV: ≈ 16,98/11,89 kV; reforçado: ≈ 31,98/22,89 kV; IEEE 522: 3,5 pu em 0,1 µs, 5 pu em ≥ 1,2 µs) [NORMA; CÁLCULO PRÓPRIO]; comparar SFI com fase-neutro e SLI com fase-terra **no nó do motor** (`01ATx`), não no VCB [LITERATURA: Vollet 2007, p. 4].

**Passo 5 — Acumulador.** Aplicar (D6) com parâmetros declarados como priors largos: $n \in [4, 12]$, $V_{th} \in \{0;\ 3{,}5\ \text{pu};\ 7{,}8\ \text{pu}\}$, $a(t_f) \in \{1;\ \text{envelope IEC 60034-18-41 Fig. 7 quando obtido}\}$, $m \in \{0; 1\}$, $N_0$ livre (normalização). Saída: $\Delta D_m^{\text{sem}}$, $\Delta D_m^{\text{com}}$ e razão $\Delta D^{\text{sem}}/\Delta D^{\text{com}}$ por combinação de parâmetros — o quociente que os artigos 12 e 07 identificam como entregável de decisão.

**Passo 6 — Monte Carlo.** Varredura de `T_OPEN` por fase (instante de separação relativo ao zero de corrente; janela de dispersão de 2,5 ms usada por Vollet [LITERATURA: IPST 2007, p. 6]) e de `I_CHOP` (1–2 A e 2–10 A) e `DIDT_CRIT` via `run_parametric_sweep` com chaves `"VCB_RR.T_OPENr"` etc. [REPO: parametric.py:81-166, via mapa]; estender `SweepCase` com `run_dir` (§3.8 de `trt_transitorios_simulacao.md`). Agregar distribuições de $n_r$, $V_{pk}$, $t_f$, $\Delta D_m$; reportar B10/B50.

**Passo 7 — RUL com/sem snubber.** $\widehat{\text{RUL}}_N = (1-D)/\mathbb E[\Delta D_m]$ e $\widehat{\text{RUL}}_t = \widehat{\text{RUL}}_N/\lambda_m$ com $\lambda_m$ como entrada (partidas abortadas/ano — dado de planta, não de A [HIPÓTESE]); apresentar como distribuição e como razão $\widehat{\text{RUL}}^{\text{com}}/\widehat{\text{RUL}}^{\text{sem}}$; opcionalmente, taxa de falha dependente do estado alimentando `ComponentReliability` de `reliability.py` e os caminhos de Strangas (eqs. (7)–(11)) com $\lambda_3$ incluindo o snubber.

**Passo 8 — Sensibilidade obrigatória.** (i) `DIDT_CRIT` com a convenção invertida (extinção quando \|di/dt\| < crítico, valores 100–600 A/µs) [LITERATURA: Wong 2003; Abdulahovic 2011]; (ii) RRDS linear 20/40 kV/ms [LITERATURA: Vollet 2007] vs parabólica de A; (iii) `Vig` do TYPE-11 (nível de breakover) e `tdeion`; (iv) ponto de conexão do snubber (barramento vs nó do motor); (v) `filter_window` e `delta_t` (0,1 µs vs 1 µs). Cada item é uma pergunta aberta da Seção 7; o experimento deve reportar quanto $n_r$, $V_{pk}$ e $\Delta D$ variam.

Critério de sucesso do MVP [HIPÓTESE de projeto]: reproduzir a Tabela III de A a partir do `.atp` (Passo 1), produzir a tensão no terminal do motor que A não reportou (Passo 2), obter $n_r$ e $t_f$ por polo (Passo 3) e entregar a razão de dano com/sem snubber como distribuição (Passos 5–7), com todos os parâmetros de dano rotulados como não calibrados até ensaio (ref. [24] de A e IEC 60034-18-42/IEEE 522 até falha).

---

## 7. Perguntas abertas

1. **Contagem de reignições em A**: quantas reignições por polo ocorrem nas Figs. 3 e 4? O modelo ATP de A (que parece ser o arquivo de referência) pode exportá-las diretamente; o número "5–7" é premissa do usuário e deve ser substituído pela contagem simulada e, depois, pela contagem medida na bancada de 4,16 kV [FATO: doc A, p. 4, [24]].
2. **Convenção do di/dt crítico**: A redige "interrupted when its di/dt ... exceeds a critical value" [FATO: doc A, p. 3] e o arquivo de referência implementa isso literalmente (l. 191), acrescido de extinção a qualquer \|I_CB\| < 0,1 A após um zero (l. 198) [REPO]. É deslize de redação, convenção própria de [1] (Silva, CEFET-MG 2026) ou intenção? A resposta muda o sentido do efeito sobre $n_r$ [LITERATURA: Wong 2003, p. 5].
3. **Origem de $A$ e $B$ da RRDS**: A remete a [1] e [7]; os valores dão recuperação ≈ 10× mais lenta que a literatura no primeiro milissegundo [CÁLCULO PRÓPRIO]. Medição ou ajuste?
4. **Tensão no terminal do motor** (`01ATx`) e fase-neutro: valores com e sem snubber, para comparação normativa correta; a Tabela III é no VCB.
5. **Tempo de frente por reignição** com passo ≤ 0,1 µs: as RRRV com snubber (B, C) são derivadas de 1 amostra [INFERÊNCIA]; o resultado de "−12,9 % em RRRV" é robusto ao passo?
6. **Nível de breakover do DIAC e latch**: A não informa o nível [FATO por omissão]; L1 usa `Vig` = 3 kV (≈ 0,9 pu) e latch por estado do disjuntor sem reset [REPO: ref:571-573, 846]. Como o hardware evitará disparo espúrio em sobretensões temporárias de 60 Hz e como o ramo "reabre" se `tdeion` = 5 ms?
7. **O snubber reduz o número de reignições ou só a amplitude?** A não afirma; capacitores de surto reduzem o número [LITERATURA: Abdulahovic 2011, p. 118]; um ramo resistivo puro pode não alongar a frente [INFERÊNCIA].
8. **Fração da tensão na primeira bobina, $a(t_f)$**: nenhuma fonte primária acessada quantifica para bobinas pré-formadas de MT [INSERIR CITAÇÃO: Cornick e Thompson 1982; Wright et al. 1983; Narang et al. 1989; Stone et al. 2014]; a IEC 60034-15 declara "no simple law" [NORMA: A.3]. Sem $a(t_f)$, o acumulador (D6) é estrutural.
9. **Expoente $n$ e limiar $V_{th}$ para mica-epóxi sob impulsos esparsos**: não publicados nas fontes acessadas [INSERIR CITAÇÃO]; ensaio de endurance a impulsos (tipo Gupta 1990; IEC 60034-18-42; IEEE 522 até falha) é o caminho.
10. **Dano por evento esparso vs. PWM**: os modelos de vida disponíveis são para estresse contínuo ou repetitivo de alta taxa; a CIGRE nota que a degradação por surto é maior a baixa frequência de repetição [LITERATURA: CIGRE WG D1.43, p. 26–28]; falta modelo calibrado para 10¹–10³ eventos/ano.
11. **Miner linear ou modelo de salto?** Reignições múltiplas podem ser eventos que mudam a trajetória (Muetze e Strangas, p. 6, 10); processo gama/Poisson marcado é alternativa não coberta pelos 13 artigos.
12. **Mascaramento espectral por RC**: a alegação de A permanece [HIPÓTESE]; medição da função de transferência de supressor R-C comercial em 100 kHz–100 MHz na bancada [24] é necessária.
13. **RUL do próprio snubber**: supressores "may gradually deteriorate due to cumulative effects" [CIGRE: TOR C4.76]; $\lambda_3$ de Strangas exige a taxa de falha do SCR/resistor sob 10¹–10³ eventos/ano.
14. **Edição da IEC 60034-15**: a Tabela 1 da ed. 2025 não foi acessada; os níveis harmonizados (≈ 3,5/5 pu) provêm do CDV [NORMA: CDV 2/2199/CDV]. Confirmar antes de citar "compliance".
15. **Wiring do arquivo de referência**: `I_CB* := v(nó)` (risco R4 do mapa) — se confirmado, o chopping por \|I_CB\| ≤ 1–2 A operaria sobre uma tensão, e os resultados de A herdariam o erro; verificar no `.acp`.
16. **Correlação entre polos**: em L2 os três USE de um VCB3 compartilham `Seed` (risco R9); em L1 é determinístico. Como A trata a dispersão estatística? Nenhuma análise Monte Carlo é apresentada [FATO por omissão; fichamento A, §8, item 27].

---

## Referências consolidadas (ABNT/IEEE, apenas fontes citadas neste documento)

Documento A: AUTORES OMITIDOS. Selective Mitigation of Vacuum Circuit Breaker Switching Overvoltages in Medium Voltage Induction Motors Using an Active Thyristor Snubber. Submissão ao SEPOC 2026 (revisão duplo-cega), 5 p. Texto local `papers_AB/txt/A_sepoc_snubber.txt`; fichamento `out/fichamentos_AB/A_snubber_tiristor_vcb.md`.

Artigos de apoio (fichamentos em `out/fichamentos/`): 01 LIU, Y.; WEN, J.; WANG, G. Machine Learning with Applications, v. 21, 100704, 2025, DOI 10.1016/j.mlwa.2025.100704. 02 JENSEN, W. R.; STRANGAS, E. G.; FOSTER, S. N. IEEE Trans. Ind. Appl., v. 54, n. 6, p. 5897–5906, 2018, DOI 10.1109/TIA.2018.2854408. 03 SHARMA, V. K.; SESHADRINATH, J. SPECon 2024, DOI 10.1109/SPECon61254.2024.10537428. 04 SONNENFELD, G.; GOEBEL, K.; CELAYA, J. R. IEEE AUTOTESTCON 2008. 05 AHSAN, M.; STOYANOV, S.; BAILEY, C. ISSE 2016, p. 273–278. 06 YU, M.; WANG, D.; LUO, M. IEEE Trans. Ind. Electron., v. 61, n. 1, p. 546–554, 2014, DOI 10.1109/TIE.2013.2244538. 07 VICHARE, N. M.; PECHT, M. G. IEEE Trans. Compon. Packag. Technol., v. 29, n. 1, p. 222–229, 2006. 08 YIN, C.; HU, Y.; CAO, W. ISEEIE 2024, p. 62–66, DOI 10.1109/ISEEIE62461.2024.00019. 09 STRANGAS, E. G.; AVIYENTE, S.; NEELY, J. D.; ZAIDI, S. S. H. IEEE Trans. Ind. Electron., v. 60, n. 8, p. 3519–3528, 2013, DOI 10.1109/TIE.2012.2227913. 10 SIAMI-NAMINI, S.; TAVAKOLI, N.; SIAMI NAMIN, A. IEEE Big Data 2019, p. 3285–3292. 11 MUETZE, A.; STRANGAS, E. G. IEEE Ind. Appl. Mag., jul./ago. 2016, p. 63–73, DOI 10.1109/MIAS.2015.2459117. 12 MA, K.; LISERRE, M.; BLAABJERG, F.; KEREKES, T. IEEE Trans. Power Electron., v. 30, n. 2, p. 590–602, 2015, DOI 10.1109/TPEL.2014.2312335. 13 WU, F.; WU, Q.; TAN, Y.; XU, X. Sensors, v. 24, 3454, 2024, DOI 10.3390/s24113454.

Normas (amostras oficiais acessadas nas pesquisas `out/etapa1/*.md` e `out/web/normas_monitoramento_isolamento.md`): IEC 60034-15:2009 (Tab. 1, Notas 1–5; 2.4; 4.2–4.4; A.1–A.3); IEC CDV 60034-15 (2/2199/CDV, 2024), 4.1–4.3, Tab. 1; IEC 60034-15:2025 (prefácio/escopo); IEC 60034-18-41:2014 (3.2, 3.9, 3.13, cl. 4); IEC 60034-27-2:2023, -27-3:2015, -27-4:2018 (Introduções); IEC 60071-1:2006, Tab. 2; IEC 60071-1:2019, 3.17; IEC 62271-110:2023 (3.2–3.7, 4.3); ISO 13381-1:2015 (3.1, 3.3, 3.9); IEEE Std 522-2023 (escopo, via IEEE SA); CIGRE TOR WG C4.76 (2023) e JWG A3.53 (2025).

Literatura verificada (URLs nas pesquisas citadas): VOLLET, C.; DE METZ-NOBLAT, B. IPST 2007, paper 106; WONG, S. M.; SNIDER, L. A.; LO, E. W. C. IPST 2003, paper 14a-03; XUE, H.; POPOV, M. IPST 2013, paper 007; ABDULAHOVIC, T. Tese, Chalmers, 2011; GLINKOWSKI, M. T.; GUTIERREZ, M. R.; BRAUN, D. IEEE Trans. Power Del., v. 12, n. 1, 1997 (resumo OSTI); XEMARD, A. et al. IPST 2019, paper 095; KING, R. et al. IPST 2011, paper 039; CIGRE WG D1.43, TB 703 (2017); GUPTA, B. K.; LLOYD, B. A.; SHARMA, D. K. IEEE Trans. Energy Convers., v. 5, n. 2, 1990 (resumo); GUPTA, B. K. et al. IEEE Trans. Energy Convers., v. EC-2, n. 4, 1987, Partes 1–3 (resumos); FEILAT, E. A. IntechOpen, 2018; CHOUDHARY, M. et al. Energies, v. 15, 3408, 2022; THEOFANOUS, A. et al. Energies, v. 18, 6087, 2025; TOMMASINI, D. arXiv:1104.0802, 2011; YANG, Y. et al. High Voltage, 2023, DOI 10.1049/hve2.12375 (resumo); SEDDING, H.; STONE, G.; WARREN, V. IRMC 2017; WARREN, V. IRMC 2022; MARDEGAN, C. S. EngePower (slides); BAKER/SKF, whitepaper de surge test (secundária); RELIASOFT, HotWire 116.

Pendentes de acesso ao texto primário [INSERIR CITAÇÃO]: IEEE Std 522 (Fig. 1); IEC 60034-15:2025, Tab. 1; IEC 60034-18-41:2014, Fig. 7 e Tab. 4; Cornick e Thompson 1982; Wright, Yang e McLeay 1983; Narang et al. 1989; Stone et al. 2014 (capítulos); Helmer e Lindmayer 1996; Kondala Rao e Gajjar 2006; Silva, dissertação CEFET-MG 2026 (ref. [1] de A); Vollet e de Metz Noblat, PCIC Europe 2007 (ref. [14] de A); ATP Rule Book (cartões diversos; TYPE-11; RECORD de MODELS).
