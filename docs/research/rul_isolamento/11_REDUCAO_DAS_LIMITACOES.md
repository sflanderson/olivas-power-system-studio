# Redução das limitações: acoplamento, robustez, campanha completa e estratificação

Fecha as três limitações que o documento 10 deixou declaradas. Duas ficam **extintas**; a
terceira fica extinta **para efeito de decisão**, e permanece aberta apenas para o número
absoluto.

**Código**: `app/postprocessor/prognosis/switching_campaign.py`,
`app/simulation/emt/vcb_scenarios.py`.
**Dados**: `anexos/dados/campanha_rul_n150.json` (300 manobras com formas de onda, Δt = 0,2 µs)
e `anexos/dados/varredura_vcb_n150_dt200ns.json`.

---

## 1. O acoplamento entre a taxa terminal e o dano acumulado

### 1.1 Por que é computável sem simular nada

A distribuição de picos da manobra **não depende do dano da isolação**: o pico é propriedade do
circuito e do disjuntor. A suportabilidade residual, sim, decai — $U_w(D) = U_{w0}\,\psi(D)$.
Logo

$$p(D) = P\big(V_{pk} \ge U_{w0}\,\psi(D)\big)$$

lê-se direto da distribuição empírica de picos já medida. `PeakDistribution` e `survival()`
resolvem a curva **por trechos**: $p$ só muda quando o limiar cruza um pico observado, e entre
dois cruzamentos a sobrevivência decai geometricamente. Isso evita iterar sobre as dezenas de
milhões de manobras de uma vida típica.

### 1.2 Sem mitigação, o acoplamento é inócuo — e a razão é física

| $\psi(D)$ | 1,00 | 0,90 | 0,80 | 0,70 | 0,60 | 0,50 |
|---|---|---|---|---|---|---|
| Limiar [kV] | 21,64 | 19,48 | 17,31 | 15,15 | 12,98 | 10,82 |
| $p(D)$ | 5,333 % | 5,333 % | 5,333 % | 5,333 % | 5,333 % | 5,333 % |

$p$ é **rigorosamente constante em toda a vida**. A causa é a bimodalidade da distribuição: o
corpo termina em **9,63 kV** e a cauda começa em **182,82 kV** — uma lacuna de **19×** sem
nenhuma realização. Fisicamente, a escalada é uma fuga: a máquina vê ~2 pu ou é destruída, e não
existe manobra "moderadamente severa" que uma isolação enfraquecida passaria a capturar. Como
$\psi_{min} = 0{,}50$ e a sensibilidade só começaria em $\psi = 0{,}445$, o modelo **nunca sai da
região plana**.

**Conclusão: a cota superior declarada no documento 10 era exata, não conservadora.**

### 1.3 Com para-raios, o acoplamento acorda no fim da vida

Os picos grampeados ficam em 11,71 kV, e há realizações entre 10,8 e 21,6 kV. O $\psi$ crítico é
0,541, atingido em **$D = 0{,}917$**:

| Grandeza | Sem acoplamento | Com acoplamento |
|---|---|---|
| $E[N]$ com para-raios | $1{,}437\cdot10^6$ | $1{,}319\cdot10^6$ |

O acoplamento corta **8 %** da vida mitigada e **nada** da não mitigada. E o resultado de projeto
é este: **o para-raios não elimina o caminho terminal, adia-o para os últimos 8 % da vida**,
quando a suportabilidade degradada volta a ser cruzada pelas manobras grampeadas.

## 2. Robustez ao expoente não calibrado

Varrendo o expoente de tensão na faixa da literatura — 3,8 a 11,7 [LITERATURA: CIGRE WG D1.43,
TB 703] — e recalculando o dano sobre os perfis **já simulados**:

| $n$ | Sem mitigação | Com para-raios | Razão |
|---|---|---|---|
| 3,80 | 18,75 | $8{,}0\cdot10^4$ | $4{,}3\cdot10^3$ |
| 7,75 | 18,75 | $5{,}6\cdot10^6$ | $3{,}0\cdot10^5$ |
| 11,70 | 18,75 | $2{,}3\cdot10^8$ | $1{,}2\cdot10^7$ |
| **Dispersão** | **1,00** | $2{,}92\cdot10^3$ | — |

O para-raios vence em **todo** o intervalo. E a razão é estrutural, não numérica: **quando o
caminho terminal domina, a vida é $1/p$ e o expoente não entra na conta** — a dispersão da
configuração sem mitigação é exatamente 1.

**Conclusão: a recomendação de mitigação é livre de calibração.** O que continua dependendo dos
parâmetros não calibrados é apenas o número absoluto da configuração mitigada — e este varia por
fator de $2{,}9\cdot10^3$, de modo que não deve ser exibido sem a faixa.

## 3. Campanha completa: as 150 manobras com formas de onda

O documento 10 reportou uma campanha de 60 manobras, cuja taxa (1/60) divergia da varredura
(8/150) por posição das travessias na sequência. A campanha foi refeita para as 150, nas duas
configurações, a Δt = 0,2 µs.

| Configuração | Travessias | $N_{term}$ | $N_{env}$ | $N_{fim}$ | Caminho dominante |
|---|---|---|---|---|---|
| Sem mitigação | 8 / 150 | **18,75** | $8{,}78\cdot10^6$ | **18,75** | travessia do envelope |
| Com para-raios | 0 / 150 | > 50 | $1{,}44\cdot10^6$ | $\mathbf{1{,}44\cdot10^6}$ | envelhecimento |

A taxa terminal agora coincide exatamente com a da varredura, porque a campanha percorre as
mesmas 150 realizações. **A limitação está extinta.**

### 3.1 Dois defeitos que a campanha completa revelou

A primeira execução das 150 **falhou no pós-processamento**, depois de completar toda a
simulação. Duas distinções estavam confundidas, e ambas erravam a conta:

1. **`None` não é perfil vazio.** Uma realização não produziu excursão acima do limiar de
   *detecção* de 5 kV. `None` é ausência de medição e impede integrar; vazio é medição que não
   encontrou excursão — **dano nulo, e uma manobra que ocorreu**.
2. **`n_operations` não conta manobras.** Conta *grupos de reignição* dentro do perfil, e um
   perfil que reúne as três fases declara até três grupos. O denominador correto é o da
   campanha.

Ambos corrigidos. A consequência é que **os números de envelhecimento do documento 10 estão
superados**: aqueles vieram de 60 manobras com o denominador inflado pelas fases. Os desta seção
os substituem.

### 3.2 A conversão de falha em envelhecimento, confirmada em escala

O achado do documento 10 — o para-raios **aumenta** o dano acumulado — confirma-se sobre as 150,
e agora com oito realizações em vez de uma:

| Configuração | Manobras no acumulador | $D$ acumulado |
|---|---|---|
| Sem mitigação | 142 | $1{,}62\cdot10^{-5}$ |
| Com para-raios | 150 | $1{,}04\cdot10^{-4}$ |

Fator de 6,5. As oito realizações que atravessam o envelope sem para-raios **sobrevivem** com
ele, e sobreviver custa dano. Lido isoladamente, o número recomendaria não instalar o para-raios;
lido pelo critério correto, $\min(N_{env}, N_{term})$, o para-raios ganha por **fator de
76 000**.

## 4. Estratificação: a mesma precisão com um sétimo do custo

A varredura uniforme gasta 78 % das execuções na faixa de RRDS em que nada acontece. Com a banda
de escalada caracterizada (documento 09, §4.3), a estratificação aloca as execuções onde a
variância está, sem perder a não tendenciosidade — o estimador $p = \sum_h W_h\,p_h$ é
exatamente não tendencioso para qualquer alocação.

**Premissa verificada:** as oito travessias têm RRDS de polo condutor entre **40,7 e 48,3 kV/ms**,
todas no estrato alto. O estrato baixo dá **0 em 107**.

| Estimador | $p$ | Desvio padrão | Execuções |
|---|---|---|---|
| Uniforme | 5,333 % | 1,835 % | 150 |
| Pós-estratificado | **4,134 %** | **1,319 %** | as mesmas 150 |
| Alocação de Neyman | — | 0,706 % | 150 |

Ganho de variância de **6,8×** com o mesmo orçamento; para igualar a precisão da uniforme bastam
**~22 execuções em vez de 150**.

### 4.1 Um refinamento do número principal

O estimador pós-estratificado corrige um desequilíbrio real do sorteio uniforme, que tirou 43
realizações do estrato alto contra as 33,3 esperadas — uma flutuação de +2,0 σ. A estimativa
refinada é, portanto,

$$p = 4{,}1\,\% \pm 1{,}3\,\%,\qquad\text{ou uma manobra em } 24,$$

com os 5,3 % anteriores dentro do intervalo. Os dois estimadores são não tendenciosos; o
pós-estratificado tem menor variância sobre os mesmos dados e é o que se deve citar.

## 5. Estado das limitações

| Limitação do documento 10 | Estado |
|---|---|
| Dependência de $p$ com o dano não modelada | **Extinta.** Modelada e medida: inócua sem mitigação (lacuna de 19×), corta 8 % da vida mitigada |
| Parâmetros da curva de vida não calibrados | **Extinta para a decisão** (dispersão 1 quando a travessia domina); aberta para o número absoluto (fator $2{,}9\cdot10^3$) |
| Campanha cobriu 60 manobras, taxa vinha das 150 | **Extinta.** As 150 rodaram com formas de onda nas duas configurações |

## 6. O que continua aberto

* **O número absoluto de vida da configuração mitigada** exige ensaio do sistema isolante
  (IEC 60034-18-42, extrapolação por lei de potência inversa com aceleração em frequência). É a
  única das limitações que não se reduz por cômputo.
* **A lacuna de 19× é propriedade deste circuito.** Num circuito de espectro de picos contínuo o
  acoplamento voltaria a importar — e agora está implementado para computá-lo.
* **$\psi(D)$ linear é escolha de modelagem.** A conclusão da §1.2 é robusta a ela porque a
  lacuna é de uma ordem de grandeza, não por precisão de $\psi$.
* **A varredura de RRDS foi feita a Δt = 1 µs.** A forma da dependência não deve mudar, mas os
  limiares da banda (40–60 kV/ms) podem deslocar.

## Referências

- CIGRE WG D1.43, TB 703 — faixa do expoente de tensão.
- IEC 60034-15:2009, Tabela 1 — envelope de suportabilidade.
- IEC 60034-18-42 — qualificação de isolação Tipo II e extrapolação de vida.
- WONG, S. M.; SNIDER, L. A.; LO, E. W. C. In: IPST 2003, paper 03IPST14a-03.
- Documentos irmãos: `08`, `09` e `10`.
