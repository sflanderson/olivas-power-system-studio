# Varredura estatística dos parâmetros do disjuntor a vácuo

Etapa complementar ao estudo de degradação de isolamento. Substitui a validação contra a
Tabela III do Documento A — que seria circular, por confrontar o motor dedicado com um
resultado ainda não comprovado — pela confrontação com as **faixas publicadas** e pelos
critérios de validade internos do próprio motor.

**Fonte das faixas**: `anexos/pesquisa/fisica_surtos_vcb_isolamento.md`.
**Código**: `app/simulation/emt/vcb_scenarios.py`, `scripts/varredura_vcb.py`.
**Dados**: `anexos/dados/varredura_vcb_n150.json` (900 realizações).

---

## 1. Desenho do experimento

### 1.1 Por que o tempo de arco é a variável de controle

Sortear o instante de separação uniformemente no ciclo é correto quanto à física e ineficiente
quanto à amostragem. A janela em que a escalada é provável — tempo de arco de 0 a 100 µs
[LITERATURA: Wong, Snider e Lo, IPST 2003, p. 5–6] — ocupa 1,2 % de um ciclo de 60 Hz
(100 µs sobre os 8,333 ms entre zeros de corrente) [CÁLCULO PRÓPRIO]. Uma varredura de 150
realizações cairia nessa janela uma ou duas vezes, e a distribuição resultante seria a de
manobras sem escalada — o caso desinteressante.

O tempo de arco é também a grandeza que a IEC 62271-110:2023 manda determinar em ensaio, sob o
nome de *re-ignition-free arcing time window*, para fins de chaveamento controlado
[NORMA: IEC 62271-110:2023, 3.7 e 4.1].

A parametrização inverte o cálculo: sorteia-se o tempo de arco na janela de Wong e dele deriva-se
o instante de separação, recuando a partir do zero de corrente do polo
(`PoleCurrentZeros.separation_for_arc_time`).

### 1.2 O disjuntor é tripolar

Os três polos partilham o acionamento: a separação mecânica é **comum** às três fases. O que
difere entre elas é o tempo de arco, porque cada polo tem seus próprios zeros de corrente.
Sortear as três fases de forma independente — como fazia a varredura anterior — produz um
disjuntor que não existe. Com as fases da corrente de regime do caso
(−48,90°, +71,68°, −167,72°), os zeros ficam separados de 2,751 ms — o $T/6 = 2{,}778$ ms de um
sistema equilibrado, corrigido pelo desequilíbrio do caso —, de modo que a um tempo de arco de
80 µs na fase A correspondem 2,831 ms na fase B e 5,581 ms na fase C [CÁLCULO PRÓPRIO: medição].

Corte de corrente, capacidade de extinção e RRDS continuam sorteados **por polo**: são
propriedades do arco e da superfície de contato, não do acionamento.

### 1.3 Cenários

| Cenário | Corte [A] | di/dt [A/µs] | RRDS [kV/ms] | Procedência |
|---|---|---|---|---|
| `literatura` | 2–10 | 100–600 | 5–50 | Vollet 2007; Wong 2003; Abdulahovic 2011 |
| `medido` | 2–10 | 250–350 | 5,5 | Abdulahovic 2011 (disjuntor comercial caracterizado) |
| `caso_de_referencia` | 1–2 | 5–15 | $0{,}801t + 1{,}226t^2$ | Documento A / arquivo `.atp` — **fora da faixa nos três parâmetros** |

Cada cenário roda com e sem o ramo amortecedor. $n = 150$ realizações por cenário,
$\Delta t = 1$ µs, janela de 45 ms, semente 20260903. Base de tensão: pico fase-terra de
4,16 kV = 3396,6 V.

---

## 2. Resultados

Pico de tensão no **terminal do motor**, em pu do pico fase-terra. É a grandeza que governa o
dano do isolamento e a que a Tabela III do Documento A não reporta.

| Cenário | Amortecedor | p50 | p90 | p95 | máx | reign. > 0 | > 10 reign. | > 4,6 pu |
|---|---|---|---|---|---|---|---|---|
| `literatura` | sem | 1,75 | 2,09 | 23,88 | **77,53** | 97 % | 8/150 | 8/150 |
| `literatura` | com | 1,46 | 1,47 | 1,48 | 1,49 | 99 % | 0 | 0 |
| `medido` | sem | 1,31 | 1,36 | 1,36 | 1,40 | 100 % | 0 | 0 |
| `medido` | com | 1,46 | 1,47 | 1,48 | 1,49 | 100 % | 0 | 0 |
| `caso_de_referencia` | sem | 1,03 | 1,06 | 1,06 | 1,08 | 100 % | 0 | 0 |
| `caso_de_referencia` | com | 1,46 | 1,47 | 1,47 | 1,48 | 69 % | 0 | 0 |

Três leituras se separam claramente.

### 2.1 O corpo da distribuição é compatível com a literatura

Sem escalada, o cenário `literatura` dá mediana de 1,75 pu e o `medido`, 1,31 pu. Xemard et al.
reportam 1,85 a 2,60 pu "sem *chopping*/reignição" [LITERATURA: IPST 2019, p. 2–5]. A ordem de
grandeza confere. Estes 95 % das realizações são a parte utilizável do motor para alimentar o
modelo de dano.

### 2.2 O amortecedor suprime a escalada, e cobra por isso

O número máximo de reignições por fase cai de 39/79/29 (sem) para 1/0/0 (com), e nenhuma
realização passa de 1,49 pu. É exatamente o efeito que Vollet e de Metz-Noblat descrevem:
*"properly sized C-R surge suppressors eliminate multiple reignitions and voltage escalation"*
[LITERATURA: IPST 2007, p. 5–6].

O preço aparece nos cenários em que não havia escalada: a mediana **sobe** de 1,03 para 1,46 pu
no caso de referência e de 1,31 para 1,46 pu no cenário medido. A causa é a da auditoria
(`07_AUDITORIA_DO_CASO_ATP.md`, seção 5, achado 5): com disparo em 2404 V — 1,0009 vez a tensão
nominal fase-terra eficaz, abaixo do pico de regime de 3386 V — o ramo de 30 Ω conduz em regime
permanente e deixa de ser seletivo. A troca é de um evento raro e severo por um acréscimo
permanente e modesto; ela só se justifica se o evento raro for real.

### 2.3 O caso de referência, sob a convenção física, quase não produz transitório

Mediana de 1,03 pu e máximo de 1,08 pu. Com a convenção física de extinção
(`|di/dt| ≤ crítico` interrompe), a capacidade de 5 a 15 A/µs do arquivo é baixa demais para
interromper qualquer corrente de alta frequência: o arco persiste até o zero de frequência
industrial e não há mecanismo de escalada. A severidade publicada no Documento A depende,
portanto, da **convenção invertida** identificada na auditoria (seção 7, item 4) — não do
circuito.

---

## 3. A cauda de escalada está fora do domínio de validade do motor

Oito das 150 realizações do cenário `literatura` sem amortecedor entram em escalada e chegam a
77,53 pu (263 kV), com até 107 reignições num único polo. Isso excede tudo que a literatura
acessada reporta, em ambas as contagens:

| Grandeza | Motor dedicado (cauda) | Literatura |
|---|---|---|
| Pico fase-terra | até 77,5 pu | ~3 pu em operação normal, até 4,6 pu medido (33 motores, >700 manobras) [F18]; 4,3 pu simulado com escalada [F24] |
| Reignições por sequência | até 107 | "pode repetir-se várias vezes (**até 10**)" [Vollet 2007, p. 2] |

### 3.1 Não é artefato de discretização

Critério de insensibilidade ao passo, aplicado à pior realização:

| $\Delta t$ | 1000 ns | 500 ns | 200 ns | 100 ns |
|---|---|---|---|---|
| Pico no motor [pu] | 77,53 | 73,22 | 76,90 | 80,35 |
| Reignições (a/b/c) | 39/79/10 | 45/95/12 | 47/102/9 | 51/107/13 |

Variação de ±5 % num refinamento de 10 vezes. O resultado é uma propriedade do modelo tal como
formulado, não um degrau numérico [CÁLCULO PRÓPRIO: medição].

### 3.2 A escalada é comandada pela rampa de recuperação, não pela física de alta frequência

Diagnóstico do polo A da pior realização (RRDS sorteada 44,3 kV/ms, capacidade de extinção
460 A/µs, separação em 14,6865 ms):

| Observável | Valor medido |
|---|---|
| Tensão do *gap* na 1ª reignição / suportabilidade no mesmo instante | 6,47 kV / **6,438 kV** |
| Tensão do *gap* na última reignição / suportabilidade | 155,32 kV / **137,44 kV** |
| Suportabilidade prevista por $\mathrm{RRDS}\cdot(t-t_{sep})$ na última | $44{,}3 \times 3{,}1055 = 137{,}6$ kV |
| Duração mediana do arco de reignição (reignição → extinção) | 15–35 µs → $f = 14$ a 33 kHz |
| $|di/dt|$ nos zeros detectados, ao longo da sequência | de 1,3 a ≈ 180 A/µs, com saturação |
| Capacidade de extinção sorteada | 460, 457 e 199 A/µs |
| Suportabilidade / $|v_{gap}|$ **após** a última reignição | ≥ 1,67 nos três polos |

Quatro fatos encadeados:

1. **A tensão de reignição acompanha a curva de suportabilidade.** Em cada evento,
   $|v_{gap}| \approx V_{wth}(t - t_{sep})$. O pico atingido é, portanto,
   $\mathrm{RRDS}\cdot\Delta t_{escalada}$ — a rampa dielétrica **define** o pico em vez de
   limitá-lo.
2. **Daí a dependência invertida com a RRDS.** Nas oito realizações em escalada, a RRDS do polo
   condutor está entre 40,7 e 48,3 kV/ms — o **topo** da faixa amostrada de 5 a 50. Wong et al.
   mostram o oposto: escalada máxima na faixa **intermediária** de 20 a 30 kV/ms, porque
   recuperação rápida demais impede a reignição [F10]. O motor reproduz a dependência ao
   contrário.
3. **A frequência da corrente de reignição é a do cabo do caso, e está correta.** O arco de
   reignição dura 15 a 35 µs, o que dá 14 a 33 kHz — exatamente $1/(4\tau)$ do cabo a jusante,
   cujos tempos de trânsito modais são 10,704, 6,751 e 6,281 µs, isto é, 23,4, 37,0 e 39,8 kHz
   [CÁLCULO PRÓPRIO: medição contra `downstream_cable_modal_data`]. Os 100–200 kHz de Vollet
   correspondem ao cabo de **216 m** do caso dele [F6] e **não são termo de comparação** para um
   cabo de tempo de trânsito uma ordem de grandeza maior.
4. **O freio de $di/dt$ não engata, e a sequência termina pela rampa.** Nessa frequência, o
   $|di/dt|$ nos zeros detectados cresce de 1,3 até cerca de 180 A/µs e satura aí — abaixo da
   faixa de 100 a 600 A/µs amostrada. O critério de extinção só chega perto de operar quando a
   amostra está no fundo da faixa (polo C, capacidade 199 A/µs, máximo medido 188,6 A/µs). O que
   de fato encerra a sequência é a **rampa de recuperação alcançando a TRV**: depois da última
   reignição a suportabilidade excede $|v_{gap}|$ por fator de 1,67 a 2,25 nos três polos
   [CÁLCULO PRÓPRIO: medição]. A escalada é, portanto, limitada — mas em 137 a 155 kV.

### 3.2.1 O que de fato falta: o limite dielétrico da carga

O motor não representa a falha dielétrica de nada a jusante. Para $U_N = 4{,}16$ kV, a
IEC 60034-15:2009 dá $U_P = 4U_N + 5 = 21{,}64$ kV para a isolação principal (**6,37 pu**) e
$U'_P = 0{,}65\,U_P = 14{,}07$ kV entre espiras (**4,14 pu**); a edição 2025 reduz o segundo a
≈ 11,9 kV (3,5 pu) [NORMA; ver `01_ETAPA1…md`, §3]. A cauda calcula até 263 kV — **doze vezes**
a suportabilidade a onda plena da máquina.

Numa instalação real, a máquina, a terminação do cabo ou um para-raios disruptam e grampeiam a
escalada muito antes disso; é o que Vollet mede, com dois para-raios, ao ficar em 32 kV num motor
de 11 kV [F6]. Sem esse elemento o motor integra um transitório que **não pode existir**. É esta
a razão pela qual a cauda está fora do domínio físico — não a frequência do anel, que está
correta.

### 3.3 A capacitância de câmara amortece, mas não é o freio que falta

Reexecutando as oito realizações em escalada com capacitância em paralelo com o *gap*
(recomendação 3 da auditoria: pF a nF, e não os 6 µF do arquivo):

| $C_{gap}$ | sem | 100 pF | 1 nF | 10 nF |
|---|---|---|---|---|
| Pico mediano [pu] | 52,53 | 36,74 | 27,42 | 14,88 |
| Pico máximo [pu] | 77,53 | 51,66 | 50,86 | 30,48 |
| Reignições máx. | 128 | 110 | 106 | 49 |

Redução monotônica de 3,5 vezes na mediana, mas ainda três vezes acima do teto publicado de
4,6 pu. A capacitância de câmara reduz o $dv/dt$ e amortece a sequência, mas não é o elemento
que falta.

---

## 4. Caminho de implementação que a literatura sustenta

Em ordem de precedência, para tornar a cauda utilizável:

1. **Representar o limite dielétrico da carga.** É o elemento ausente. Em ordem de preferência:
   (a) para-raios ZnO no terminal do motor — a mitigação padrão, que Vollet e Xemard modelam e
   que grampeia a escalada em 2,64 a 3,6 pu [F6, F24]; ou, no mínimo, (b) um limiar de disrupção
   no envelope da IEC 60034-15 ($U_P = 21{,}64$ kV = 6,37 pu; $U'_P = 14{,}07$ kV = 4,14 pu para
   4,16 kV), com registro do evento. Enquanto não existir, **todo resultado de escalada acima de
   6,37 pu está fora do domínio físico**, porque descreve tensão que a máquina não suportaria.
2. **Verificar a dependência com a RRDS contra Wong [F10]** depois de (1) — e só depois, porque o
   grampeamento muda o mecanismo: a escalada deve ser máxima em 20–30 kV/ms e decrescer nos dois
   extremos. Enquanto o máximo estiver no topo da faixa, o mecanismo implementado não é o
   publicado. Este é o critério de aceitação do modelo de escalada.
3. **Impor um teto de sanidade** ao consumidor do resultado: realizações acima de
   `FIELD_PEAK_CEILING_PU` (4,6 pu) devem ser marcadas e excluídas do acumulador de dano, com
   registro, até que (1) e (2) estejam fechados.
4. **Só então** alimentar o modelo de dano com a cauda. Até lá, o modelo de dano usa o corpo da
   distribuição (p50 a p90), que é o que está comprovado.

O que **não** entra nesta lista, por já estar correto: a frequência da corrente de reignição
(§3.2, fato 3) e o referencial do relógio de recuperação (corrigido para a separação dos
contatos, conforme Wong 2003).

## 5. O que este experimento fecha e o que não fecha

**Fecha.** A parametrização por tempo de arco e o disjuntor tripolar; a compatibilidade do corpo
da distribuição com Xemard; a supressão da escalada pelo ramo amortecedor, com o custo em regime
permanente quantificado; a demonstração de que a severidade do Documento A vem da convenção de
extinção invertida, e não do circuito.

**Não fecha.** A cauda de escalada. O motor a produz de forma robusta ao passo e a limita por um
mecanismo interno consistente — a rampa de recuperação alcança a TRV —, mas em 137 a 155 kV, uma
ordem de grandeza acima do que a isolação da máquina suporta, porque nada no modelo representa a
disrupção da carga. A dependência com a RRDS sai invertida em relação a Wong. Não deve alimentar
o Asset Health Index até os itens 1 e 2 da seção 4 estarem fechados.

## Referências

- VOLLET, C.; DE METZ-NOBLAT, B. Vacuum circuit breaker model: application case to motors
  switching. In: IPST 2007, Lyon, paper 07IPST106.
- WONG, S. M.; SNIDER, L. A.; LO, E. W. C. Overvoltages and reignition behavior of vacuum
  circuit breaker. In: IPST 2003, New Orleans, paper 03IPST14a-03.
- ABDULAHOVIC, T. *Analysis of High-Frequency Electrical Transients in Offshore Wind Parks*.
  Tese (Doutorado), Chalmers, 2011.
- XEMARD, A. et al. In: IPST 2019, paper 19IPST095.
- IEC 62271-110:2023, cláusulas 3.2, 3.3, 3.6, 3.7 e 4.1.
- Levantamento consolidado com verificação de cada valor:
  `anexos/pesquisa/fisica_surtos_vcb_isolamento.md`.
