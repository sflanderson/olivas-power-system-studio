# Para-raios, compensação de Dommel e o critério de aceitação do modelo de escalada

Continuação direta de `08_VARREDURA_ESTATISTICA_VCB.md`, que fechou com dois itens abertos:

1. representar o **limite dielétrico da carga**, cuja ausência punha a cauda de escalada fora do
   domínio físico;
2. verificar, depois disso, a **dependência da escalada com a RRDS** contra Wong, Snider e Lo.

Ambos foram executados. O primeiro está fechado; o segundo está fechado quanto à **forma** da
dependência e aberto quanto à sua **localização**, pela razão exposta na §4.

**Código**: `app/simulation/emt/nonlinear.py`, `app/simulation/emt/arrester.py`,
`scripts/varredura_rrds.py`.
**Dados**: `anexos/dados/varredura_rrds_constante.json`, `…_wong.json`,
`…_wong_estendida.json`.

---

## 1. Método numérico: compensação

Um ramo não linear estampado em `[Y]` mudaria a matriz a cada mudança de ponto de operação e
exigiria refatoração a cada passo. O método de compensação evita isso: o ramo é **excluído** de
`[Y]` e substituído por uma fonte de corrente cujo valor sai da interseção de duas equações
escalares [FONTE: Dommel 1971, §V, p. 2562]:

$$e_k - e_m = e^{(0)}_{km} - z_T\,i_{km} \qquad\text{(rede, eq. 4)}$$
$$e_k - e_m = f(i_{km}) \qquad\text{(ramo, eq. 5)}$$

e a solução final por superposição, $[e] = [e^{(0)}] - [z]\,i_{km}$ (eq. 6). A característica é
representada ponto a ponto, por trechos lineares, como no programa da BPA, com a busca da
interseção partindo do trecho do passo anterior [FONTE: idem, p. 2562–2563].

O exemplo trabalhado do próprio artigo é o deste projeto: *"a lightning arrester at the
substation end of the cable"* protegendo um transformador [FONTE: Dommel 1971, Fig. 3].

**Verificação.** A álgebra foi confrontada com soluções analíticas, e não apenas consigo mesma:
num divisor resistivo o método devolve $z_T = 10{,}000000\ \Omega$ e o ponto de operação exato do
divisor; com dois ramos acoplados por um resistor comum, a matriz $z_T$ tem os termos cruzados
corretos (15 Ω na diagonal, 5 Ω fora) e a solução coincide com a associação série-paralelo
[REPO: `tests/test_emt_nonlinear.py`, 38 testes].

Mudar de trecho **não** muda a assinatura de topologia — é a vantagem central do método: sem
refatoração e sem CDA a cada mudança de ponto de operação.

## 2. O para-raios

### 2.1 Dados

As fontes primárias acessadas publicam **dois pontos** da curva $v$–$i$ de cada para-raios do
caso de 11 kV de Vollet [LITERATURA: IPST 2007, p. 4–6]:

| Para-raios | Ponto de fuga | Ponto de proteção | Expoente ajustado |
|---|---|---|---|
| Terminal do motor | 18,4 kV a 0,1 mA | 36,8 kV a 10 kA | $\alpha = 26{,}58$ |
| Cubículo (barra) | 21,6 kV a 3 mA | 76,9 kV a 40 kA | $\alpha = 12{,}92$ |

Os pontos intermediários vêm de interpolação log-log entre os dois publicados — a única
inferência feita sobre a forma da curva, e a representação corrente de um varistor de ZnO
[CÁLCULO PRÓPRIO]. Com 4 pontos por década o erro de representação em **tensão** fica em 0,15 %
e 0,31 %; o erro em corrente é enorme por construção, e não diz nada sobre a qualidade da
proteção, porque $i$ é uma potência de expoente 13 a 27 de $v$.

### 2.2 Transposição para 4,16 kV, e uma coincidência que a sustenta

O escalonamento é proporcional à tensão nominal do sistema — regra de seleção corrente, **não**
dado das fontes, e declarado como tal em `emt_arrester_scaling_by_system_voltage`. O que ele
preserva é a margem de proteção relativa do caso publicado.

Escalado para 4,16 kV ($k = 0{,}3782$), o para-raios do motor dá joelho em 6,96 kV (2,05 pu) e
tensão residual de **13,92 kV (4,10 pu)**. O envelope da IEC 60034-15:2009 para $U_N = 4{,}16$ kV
dá $U'_P = 0{,}65\,(4U_N+5) = 14{,}07$ kV (4,14 pu) entre espiras
[NORMA; ver `01_ETAPA1…md`, §3].

A tensão residual fica **1,1 % abaixo** do nível espira-a-espira da norma. Os dois números vêm
de fontes independentes — uma curva de catálogo publicada num artigo francês de 2007 e uma
fórmula normativa — e coincidem. É a melhor sustentação disponível para o escalonamento
[CÁLCULO PRÓPRIO].

O joelho em 2,05 pu está bem acima do pico de regime de 1,0 pu: o para-raios conduz microampères
em operação normal e dissipa milijoules na janela de 45 ms — não perturba o regime.

## 3. Resultado: a cauda volta ao domínio físico

As oito realizações que escalavam na varredura anterior, reexecutadas com e sem para-raios:

| Configuração | Pico p50 [pu] | Pico máx [pu] | Reignições máx | Energia máx no MOA |
|---|---|---|---|---|
| Sem para-raios | 52,53 | **77,53** | 128 | — |
| Com para-raios de 4,16 kV | **3,37** | **3,45** | **6** | 57,2 J |

As duas grandezas voltam à faixa publicada ao mesmo tempo:

* **Amplitude**: 3,37 a 3,45 pu, contra ~3 pu em operação normal e até 4,6 pu medidos em campo
  [F18], 4,3 pu simulados com escalada [F24] e 3,6 pu com dois para-raios em Vollet [F6].
* **Contagem**: até 6 reignições, contra as *"várias vezes (até 10)"* de Vollet
  [LITERATURA: IPST 2007, p. 2].

E o para-raios **não elimina** as reignições, como as fontes advertem — *"arresters do not limit
the multiple reignitions"* [Vollet 2007, p. 5]; *"surge arresters limit the voltages to
well-defined amplitudes, but a number of reignitions occur up to this level"*
[Liljestrand & Lindell 2016, via F-indireta]. Restam 5 a 6.

Nenhuma realização levou o para-raios além do último ponto caracterizado: a extrapolação da
curva não foi exercida.

## 4. O critério de aceitação de Wong

### 4.1 O que Wong afirma

Escalada mais severa para **tempo de arco de 0 a 100 µs** e **RRDS na faixa intermediária de 20
a 30 kV/ms**, com capacidade de extinção de inclinação negativa. RRDS e tempo de arco são os
parâmetros dominantes; a extinção de AF é secundária [LITERATURA: Wong, Snider e Lo, IPST 2003,
p. 5–6 — item F10 do levantamento].

A não monotonicidade tem razão física: recuperação **rápida demais** impede a reignição;
**lenta demais** permite a extinção no primeiro zero de alta frequência.

### 4.2 A lei de extinção, e uma reconciliação de unidades

Wong não usa capacidade de extinção constante: ajusta $di/dt = C\,(t - t_{open}) + D$. As duas
transcrições do levantamento diferem por exatamente $10^6$ — Wong traz
$(-0{,}34\cdot10^5;\ 255)$ e Abdulahovic $(-0{,}034;\ 255)$ para a mesma lei de Glinkowski
[F8, F21]. O fator é a conversão de $t$ em segundos para $t$ em µs, e a leitura que fecha
fisicamente é a de µs: com $C = -0{,}034$ A/µs² e $D = 255$ A/µs a capacidade zera em
$255/0{,}034 = 7500$ µs $= 7{,}5$ ms, que é a escala da abertura mecânica. Com a leitura literal
em A/µs² o decaimento levaria 7,5 µs, o que não corresponde a nenhuma escala do fenômeno
[CÁLCULO PRÓPRIO]. Adotada a convenção de µs; a lei está implementada em
`LinearExtinction` e os pares publicados em `WONG_EXTINCTION_LAWS`.

### 4.3 A varredura em grade

RRDS varrida em grade — não por sorteio —, 25 realizações por ponto, tempo de arco na janela de
Wong, RRDS comum aos três polos, com para-raios. Percentil 95 do pico no motor e máximo de
reignições:

| RRDS [kV/ms] | 5–37,5 | 40 | 42,5–60 | 70–200 |
|---|---|---|---|---|
| Pico p95 [pu] | 1,95–2,13 | 2,09–3,32 | **3,22–3,45** | 2,20–2,61 |
| Reignições máx | 2–3 | 2–6 | **5–7** | 0–4 |
| Reignições p50 | 2 | 2 | 2 | **0** |

A dependência **é não monotônica e tem máximo interior**, com as duas caudas pelas razões que
Wong dá:

* **Abaixo de 40 kV/ms** — a suportabilidade cresce devagar, as reignições ocorrem em tensão
  baixa e a sequência se extingue sem escalar: 2 a 3 reignições, pico de 2 pu.
* **Entre 40 e 60 kV/ms** — a banda de escalada: 5 a 7 reignições, pico de 3,4 pu.
* **Acima de 70 kV/ms** — a recuperação vence a TRV logo na primeira interrupção e a **mediana
  de reignições cai a zero**: o disjuntor simplesmente abre.

O critério de aceitação está, portanto, **atendido quanto à forma**. Antes da correção a
dependência era monotônica crescente até 92 pu, sem cauda descendente; agora tem máximo
interior, que é o que a fonte descreve.

### 4.4 A localização difere, e por quê

O máximo está em **40 a 60 kV/ms** neste circuito, contra os **20 a 30 kV/ms** que Wong reporta
no dele. A diferença é de circuito, não de mecanismo: o limiar de reignição é a corrida entre a
rampa $\mathrm{RRDS}\cdot(t - t_{sep})$ e a TRV da rede, e a TRV de primeiro polo a abrir deste
caso — 1,8 a 2,3 pu sobre 3,4 kV — não é a do sistema de ensaio de Wong. Deslocar o máximo
exigiria reproduzir o circuito dele, o que está fora do escopo.

O que **não** explica a diferença, verificado: o para-raios. No ponto de controle de
100 kV/ms, com e sem para-raios, o resultado é idêntico (p95 de 2,38 pu, mediana de zero
reignições) — a cauda descendente é a corrida recuperação × TRV, e o para-raios só atua dentro
da banda de escalada, onde grampeia a amplitude [CÁLCULO PRÓPRIO: medição].

E o que a lei de extinção de Wong muda, verificado: pouco. Trocando a capacidade constante pela
lei de inclinação negativa, o limiar da banda move-se de 40 para 42,5 kV/ms e nada mais — o que
é consistente com a própria conclusão de Wong de que a extinção de AF é o parâmetro **menos**
importante dos três [F10].

## 5. Estado dos dois itens

| Item de `08_…md`, §4 | Estado |
|---|---|
| 1. Representar o limite dielétrico da carga | **Fechado.** Para-raios ZnO por compensação; cauda de 77,5 → 3,45 pu e de 128 → 6 reignições, ambas na faixa publicada |
| 2. Dependência com a RRDS contra Wong | **Fechado quanto à forma** (máximo interior, com as duas caudas pelas razões da fonte); a localização é 40–60 kV/ms neste circuito contra 20–30 no de Wong, por diferença de TRV |
| 3. Teto de sanidade no consumidor do resultado | Pendente — cabe ao acumulador de dano, não ao motor |
| 4. Alimentar o modelo de dano com a cauda | **Liberado para a configuração COM para-raios.** Sem para-raios a cauda continua fora do domínio físico e não deve ser usada |

## 6. O que continua aberto

* **A curva do para-raios é uma reconstrução** de dois pontos publicados, escalada de 11 para
  4,16 kV por regra de seleção. Um para-raios real tem curva de catálogo. O que os resultados
  podem afirmar é a margem de proteção relativa, não o nível residual de um equipamento
  específico [`emt_arrester_two_point_curve`, `emt_arrester_scaling_by_system_voltage`].
* **Não há modelo dinâmico de para-raios** (IEEE WG 3.4.11 / Pinceti-Giannettoni): para frentes
  de microssegundo a tensão residual real excede a estática, de modo que o nível de proteção
  calculado é cota inferior [`emt_nonlinear_no_dynamic_arrester_model`].
* **Não há classe de descarga**: a energia é medida (57,2 J no pior caso) mas não confrontada
  automaticamente com a capacidade do para-raios [`emt_arrester_no_energy_rating`].
* **A instalação sem para-raios continua sem limite dielétrico.** O caso do arquivo `.atp` não
  tem para-raios, e para ele a cauda de escalada permanece fora do domínio físico. A alternativa
  mínima — um limiar de disrupção no envelope da IEC 60034-15 — não foi implementada.

## Referências

- DOMMEL, H. W. Nonlinear and time-varying elements in digital simulation of electromagnetic
  transients. **IEEE Transactions on Power Apparatus and Systems**, v. PAS-90, n. 6,
  p. 2561–2567, 1971.
- VOLLET, C.; DE METZ-NOBLAT, B. Vacuum circuit breaker model: application case to motors
  switching. In: IPST 2007, Lyon, paper 07IPST106.
- WONG, S. M.; SNIDER, L. A.; LO, E. W. C. Overvoltages and reignition behavior of vacuum
  circuit breaker. In: IPST 2003, New Orleans, paper 03IPST14a-03.
- ABDULAHOVIC, T. *Analysis of High-Frequency Electrical Transients in Offshore Wind Parks*.
  Tese (Doutorado), Chalmers, 2011.
- XEMARD, A. et al. In: IPST 2019, paper 19IPST095.
- IEC 60034-15:2009.
- Levantamento consolidado, com a verificação de cada valor:
  `anexos/pesquisa/fisica_surtos_vcb_isolamento.md`.
