# Campanha de manobras: os dois caminhos de fim de vida

Fecha a cadeia manobra → estresse → estado → vida sobre o caso de referência, com formas de onda
reais do motor EMT dedicado.

**Código**: `app/postprocessor/prognosis/switching_campaign.py`, `scripts/campanha_rul.py`.
**Dados**: `anexos/dados/campanha_rul_n60.json` (120 manobras, Δt = 0,2 µs) e
`anexos/dados/varredura_vcb_n150_dt200ns.json`.

---

## 1. Por que dois caminhos, e não um dano só

A varredura produz duas populações que **não podem ser somadas**:

* as manobras que ficam abaixo do envelope de suportabilidade da máquina e a **envelhecem** —
  estresse a integrar por Miner;
* as que o atravessam e a **rompem** — evento terminal a contar.

Somar as segundas às primeiras, como estresse, é o erro que o módulo impede: grampear a tensão de
uma travessia reduz o estresse calculado — conservador quanto à amplitude, **anticonservador
quanto ao dano** — e integra uma forma de onda que não existe
[REPO: `app/simulation/emt/flashover.py`, cabeçalho].

A vida é, portanto, o **mínimo** de dois caminhos:

$$N_{fim} = \min\big(N_{env},\ N_{term}\big)$$

com $N_{env}$ vindo do acumulador de dano ($D = 1$) e $N_{term}$ da taxa de travessia. Reportar
apenas um é reportar metade do problema — e a seção 3 mostra que reportar só o dano **inverteria
a recomendação de engenharia**.

## 2. A taxa de travessia

Conjunto convergido, 150 realizações a Δt = 0,2 µs:

| Configuração | Travessias | $p$ | Manobras esperadas até a primeira |
|---|---|---|---|
| Sem mitigação | 8 / 150 | 5,3 % (≤ 8,9 % a 95 %) | **18,8** |
| Com para-raios | 0 / 150 | ≤ 2,0 % | **mais de 50** |

**Uma manobra em dezenove atravessa o envelope normativo da máquina** na configuração sem
mitigação. É o número **calibrado** deste estudo: sai de contagem e não depende de nenhum
parâmetro de curva de vida — ao contrário do caminho do envelhecimento, cujos parâmetros
continuam não calibrados para mica-epóxi de MT [`rul_params_not_calibrated`].

### 2.1 O caso de zero eventos

Com para-raios a estimativa pontual é zero e **não informa nada**. O que se reporta é a cota: pela
regra de três, zero eventos em $n$ ensaios dá $p \le 3/n$ ao nível de 95 %. Com $n = 150$ isso é
$p \le 2\,\%$, ou seja **mais de 50 manobras** — e não "nunca". Uma varredura sem travessia
nenhuma não demonstra impossibilidade; demonstra um limite superior.

### 2.2 A campanha de 60 manobras dá 1/60, e isso não contradiz

> **Superado.** A campanha foi refeita para as 150 manobras nas duas configurações, e a taxa
> passou a coincidir exatamente com a da varredura: 8/150. Ver `11_REDUCAO_DAS_LIMITACOES.md`,
> §3. A análise abaixo permanece como o raciocínio que identificou a causa.

A campanha ponta a ponta rodou as 60 primeiras realizações da mesma sequência e encontrou **uma**
travessia — $p = 1{,}7\,\%$, com intervalo de 95 % de 0 a 4,9 %, que **contém** os 5,3 % do
conjunto completo. A razão é a posição das travessias na sequência: elas ocorrem nos índices
**59, 66, 73, 90, 91, 103, 123 e 148**, e apenas uma cai nas 60 primeiras
[CÁLCULO PRÓPRIO: medição].

A ausência de travessia nos 59 primeiros índices tem probabilidade $0{,}947^{59} \approx 4\,\%$
sob amostragem uniforme — incomum, mas dentro do esperado, e sem mecanismo que ligue o índice da
realização a qualquer grandeza física. **A estimativa a usar é a de 150 realizações**; a de 60 é
amostra pequena e está reportada aqui apenas porque é a que acompanha as formas de onda.

## 3. O achado: o para-raios AUMENTA o dano acumulado

> **Números superados.** Os valores de dano desta seção vêm da campanha de 60 manobras e de um
> denominador que contava GRUPOS de reignição em vez de manobras — dois defeitos corrigidos
> depois. O **achado qualitativo se confirma** sobre as 150 manobras, e com oito realizações em
> vez de uma; os números corretos estão em `11_REDUCAO_DAS_LIMITACOES.md`, §3.2.

Campanha de 60 manobras com formas de onda, com e sem para-raios:

| Configuração | Manobras no acumulador | $D$ acumulado | Caminho dominante |
|---|---|---|---|
| Sem mitigação | 59 | $3{,}25\cdot10^{-6}$ | **travessia do envelope** |
| Com para-raios | 60 | $1{,}38\cdot10^{-5}$ | envelhecimento |

O dano com para-raios é **4,3 vezes maior**. Lido isoladamente, o número recomendaria não
instalar o para-raios — o que é exatamente o inverso da conclusão correta.

### 3.1 A causa, isolada por medição

Excluindo uma única realização, os dois conjuntos ficam **idênticos**:

| Conjunto | Sem para-raios | Com para-raios |
|---|---|---|
| Todas as 60 manobras | 389 excursões | 527 excursões |
| Sem a realização 59 | **389 excursões** | **389 excursões** |

O para-raios não muda nada nas 59 manobras que nunca alcançam seu joelho (6,96 kV) — como deve
ser, já que abaixo dele conduz microampères. **Toda a diferença é a realização 59**:

| Realização 59 | Sem para-raios | Com para-raios |
|---|---|---|
| Atravessou o envelope | **sim** | não |
| Pico no motor | 10,67 pu | 3,31 pu |
| Reignições | 7 | 6 |
| Excursões de estresse contribuídas | **0** | **138** |
| Maior pico extraído | — | 11,24 kV |

### 3.2 A leitura

**O para-raios aumenta o dano acumulado porque converte falha em envelhecimento.** Sem ele, a
manobra 59 rompe a isolação e não contribui estresse nenhum — não há mais o que envelhecer. Com
ele, a máquina **sobrevive** à manobra, e sobreviver custa 138 excursões de estresse.

É a demonstração empírica da premissa do módulo: o dano acumulado só é comparável entre
configurações que produzem o **mesmo conjunto de sobreviventes**. Entre configurações que
mudam quem sobrevive, comparar dano é comparar coisas diferentes, e a comparação tem de ser feita
sobre $N_{fim} = \min(N_{env}, N_{term})$ — que é onde o para-raios ganha, e com folga: tira a
travessia da posição de caminho dominante.

## 4. O que este documento fecha

| Elo da cadeia | Estado |
|---|---|
| Manobra → forma de onda | Motor EMT dedicado, passo convergido de 0,2 µs |
| Forma de onda → estresse | `to_stress_profile` → `extract_stress_events`, com $T_1$ da IEC 60034-15 §2.4 |
| Estresse → dano | `CombinedDamageAccumulator`, **só sobre as sobreviventes** |
| Travessia → evento terminal | Taxa Bernoulli com cota de 95 %, incluindo o caso de zero eventos |
| Dois caminhos → vida | $N_{fim} = \min$, com o caminho dominante nomeado |

## 5. O que continua aberto

* **Os parâmetros da curva de vida continuam não calibrados** para o número absoluto; a
  **decisão**, porém, não depende deles (`11_REDUCAO_DAS_LIMITACOES.md`, §2). O número
  utilizável deste estudo continua sendo o do caminho terminal.
* ~~**A dependência de $p$ com o dano acumulado não é modelada.**~~ **Fechado** — modelada e
  medida: inócua sem mitigação, corta 8 % da vida mitigada
  (`11_REDUCAO_DAS_LIMITACOES.md`, §1).
* **A independência entre manobras é premissa.** Uma sequência de partidas abortadas — a condição
  que o CDV da IEC 60034-15 nomeia para o nível reforçado — a viola.
* ~~**A campanha com formas de onda cobriu 60 manobras, não 150.**~~ **Fechado** —
  `11_REDUCAO_DAS_LIMITACOES.md`, §3.

## Referências

- IEC 60034-15:2009, Tabela 1 e §2.4; IEC CDV 60034-15 (2/2199/CDV, 2024).
- VOLLET, C.; DE METZ-NOBLAT, B. In: IPST 2007, paper 07IPST106.
- WONG, S. M.; SNIDER, L. A.; LO, E. W. C. In: IPST 2003, paper 03IPST14a-03.
- DOMMEL, H. W. **IEEE Trans. PAS**, v. PAS-90, n. 6, p. 2561–2567, 1971.
- Documentos irmãos: `08_VARREDURA_ESTATISTICA_VCB.md`,
  `09_PARA_RAIOS_E_CRITERIO_DE_ACEITACAO.md`.
