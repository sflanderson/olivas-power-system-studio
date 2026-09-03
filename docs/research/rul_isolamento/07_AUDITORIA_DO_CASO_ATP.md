# Auditoria do caso de referência ATP e confronto com o motor dedicado

**Objetivo.** Confrontar o caso de manobra do arquivo de dados (fonte única da verdade) com o
motor de transitórios dedicado, ancorado na solução fasorial impressa pelo próprio ATP, e
registrar o que a listagem de saída revela sobre o caso.

**Diagnóstico.** O regime permanente do caso é fisicamente autoconsistente e o motor o
reproduz com erro de 0,03 % a 0,30 %. No transitório, o motor **não** reproduz a Tabela III
do trabalho — e a investigação localizou a causa no próprio modelo de disjuntor do arquivo:
como escrito, ele **não pode** produzir reignições com escalada de tensão. Os picos de 30 a
41 kV da tabela coincidem, na listagem, com instantes de comando de abertura e com eventos
numéricos de sub-rede flutuante, não com o mecanismo físico descrito.

**Arquivos consultados.** `tests/fixtures/atp/trt_all_motors_dt_ea.atp`,
`tests/fixtures/atp/trt_all_motors_com_snubber_2026-04.atp`,
`tests/fixtures/atp/referencia_regime_permanente.json` (extraído da listagem de 03-09-2026),
`app/simulation/emt/cases/atp_reference.py`, `app/simulation/emt/vcb.py`,
`docs/research/rul_isolamento/06_CASO_BASE_ATP_ESPECIFICACAO.md`.

**Arquivos afetados.** `app/simulation/emt/vcb.py` (semântica de abertura da chave tipo 13),
`tests/test_emt_vcb_snubber.py` (regressão), este documento.

**Estratégia.** Ancoragem por equivalente de Thévenin deduzido dos fasores (sem decodificar a
matriz do transformador), alinhamento literal do modelo de disjuntor, execução nas duas
configurações e leitura do código do `MODEL` linha a linha.

**Limitações.** Sem o arquivo de saída de tracado (`.pl4`) da execução original, a origem
exata dos 41,44 kV permanece hipótese; a rede a montante entra por equivalente de Thévenin e
o cabo a montante dependente da frequência não está representado no transitório.

**Próximo passo recomendado.** Corrigir os dois defeitos do `MODEL` (seção 3), reexecutar no
ATP e no motor dedicado, e só então reavaliar a Tabela III.

---

## 1. Ancoragem e validação do regime permanente

Equivalente de Thévenin por fase deduzido da solução fasorial [FATO: listagem], usando do
arquivo apenas o resistor de neutro (12,009 Ω) e o ramo de magnetização (1138,52 Ω), que não
dependem da matriz do transformador. Conferência independente: o termo mútuo resolvido sem
informar o cartão devolveu $12{,}0092 + j0{,}0106\ \Omega$ — o próprio resistor de neutro
[CÁLCULO PRÓPRIO].

| Grandeza | Listagem | Motor dedicado | Erro |
|---|---|---|---|
| $V$(X0029A) | 3386,445 V ∠30,4988° | 3391,501 V ∠30,6446° | 0,30 % |
| $V$(01ATA) | 3149,282 V ∠29,5521° | 3149,354 V ∠29,5372° | 0,026 % |
| $I$ disjuntor A | 911,397 A ∠−48,9037° | 911,420 A ∠−48,9185° | 0,026 % |
| $I$ motor B | 925,267 A ∠71,6769° | 924,911 A ∠71,6483° | 0,063 % |
| $V$(XX0003), neutro | 49,026 V | 53,819 V | 20 % relativo; 9,97 V absolutos |
| Perda total | 997 130,9 W | 996 028,0 W | 0,11 % |

O erro do neutro é o erro de 0,3 % das correntes de fase visto através de um resíduo:
$|I_a+I_b+I_c| = 4{,}08$ A sobre correntes de 911 A [CÁLCULO PRÓPRIO].

Verificações feitas **somente com os números da listagem**, sem o motor: impedância do motor
$V/I$ = 3,4550 Ω ∠78,463° nas três fases, idêntica ao ramo R–L; $V_{XX0003} = R_n I_n$ exato;
potência das fontes = perda total declarada [CÁLCULO PRÓPRIO].

### 1.1 Decodificação da matriz do transformador

A listagem imprime `using [A], [R]`. Aplicando $\mathbf{I} = [A]\,\mathbf{V}/(j\omega)$ às
tensões de enrolamento da própria listagem [CÁLCULO PRÓPRIO]:

| Unidade de $[A]$ | $|I_\Delta|$ | $|I_Y|$ | Listagem |
|---|---|---|---|
| H⁻¹ | 160,1 A | 918,3 A | 159,1 A / 912,0 A |
| mH⁻¹ | 160 095 A | 918 320 A | — |

Portanto $[A]$ em H⁻¹ e $[R]$ em Ω. Dados de placa implícitos: relação de espiras 5,7459
(13,8 kV Δ / 2,402 kV Y), dispersão 5,57 % na base 7,5 MVA/4,16 kV, $X/R = 9{,}0$,
$k = 0{,}99997$ [CÁLCULO PRÓPRIO].

## 2. Defeito corrigido no motor dedicado

No modo literal a chave ideal abria **no instante do comando** (`T_OPEN`) carregando a corrente
de carga (74 A no polo R; centenas de ampères nos polos S e T), que era descarregada no ramo
série de arco de 20 Ω / 50 nH / 20 pF — degrau de $i\,\Delta t/C$ = 74 A × 1 µs / 20 pF ≈ 3,7 MV
antes do amortecimento da rede, observado como 100 a 700 kV, crescendo com a redução do passo
(824 kV e 14 000 kV/µs a 50 ns) [CÁLCULO PRÓPRIO; medição]. A chave tipo 13 do ATP abre no
primeiro instante em que $|i| \le I_{mar}$; com o campo em branco, na passagem natural por zero
[LISTA: 02, §1.3 e §3.6]. Corrigido em `AtpModelCompatibility.apply()`; após a correção o polo R
corta em 14,763 ms com −0,94 A e a chave abre em 14,766 ms com 0,09 A.

## 3. Dois defeitos no `MODEL` do arquivo

### 3.1 O temporizador da recuperação dielétrica nunca é armado

```
IF TNOW > TIME_PREVr THEN
  DI_DTr := (I_CBr - I_PREV) / (TNOW - TIME_PREVr)
  TIME_PREVr := TNOW
  I_PREV := I_CBr                     <- sobrescrito ANTES do teste
ENDIF
IF I_PREV * I_CBr <= 0.0 THEN         <- vale I_CB^2 <= 0
  IF ABS(I_PREV) > 0.01 THEN          <- vale |I_CB| > 0.01
    T_ZEROr := TNOW
```
[FATO: arquivo, bloco `EXEC` do `MODEL VCB_Rr`]. O bloco `IF TNOW > TIME_PREVr` é verdadeiro em
todo passo, logo `I_PREV = I_CB` no teste seguinte: `I_PREV·I_CB ≤ 0` exige `I_CB = 0` exato e
`|I_PREV| > 0,01` exige `|I_CB| > 0,01` — contraditórios. `T_ZERO` permanece em −1, `V_WITH`
permanece em 0, e a condição de reignição `|V_CB| > V_WITH·1,1 AND V_WITH > 0` é **código
morto**. Medido no motor dedicado em modo literal: `zero_crossing_times_s = []`, `V_WITH ≡ 0`,
zero reignições nos três polos [FATO: medição].

### 3.2 A "reignição" não religa a chave e o ramo de arco não conduz

`SW_STATEr := 0.0` ocorre uma única vez, em `T_OPEN`; não há atribuição `SW_STATEr := 1.0` em
nenhum estado [FATO: arquivo]. Uma reignição (estado 3) apenas comuta o ramo paralelo para
$R_{arc} = 20\ \Omega$, $L_{arc} = 50$ nH e $C_{arc} = 20$ pF **em série**. Um capacitor de
20 pF em série tem $|Z| \approx 8\ \mathrm{k\Omega}$ a 1 MHz e $133\ \mathrm{M\Omega}$ a 60 Hz:
não conduz corrente de reignição e não pode produzir escalada. Medido com a ordem de
atualização pretendida (`I_PREV` atualizado após o teste): 1100 a 1600 comutações de estado
por polo, `extHF = 0`, e picos de TRV **idênticos** aos do caso sem reignição [FATO: medição].

Consequência: o mecanismo "reignições sucessivas com escalada" que o trabalho descreve não pode
ser gerado por este `MODEL`, em nenhuma das duas leituras da ordem de atualização.

## 4. Confronto com a Tabela III (motor dedicado, modo literal, Δt = 1 µs, 45 ms)

| Fase | Config. | Tab. III pico / RRRV | Motor dedicado pico / RRRV | Reign. | Corte | Chave abre | $V$ motor |
|---|---|---|---|---|---|---|---|
| A | sem | −30,24 / 13,90 | 7,90 / 0,26 | 0 | 14,763 ms | 14,766 ms, 0,09 A | 3,15 kV |
| B | sem | 41,44 / 15,05 | 6,24 / 0,27 | 0 | 27,125 ms | 27,132 ms, 0,05 A | 3,20 kV |
| C | sem | −38,30 / 19,00 | −6,10 / 0,23 | 0 | 27,332 ms | 27,340 ms, −0,18 A | 3,13 kV |
| A | com | 6,35 / 3,28 | −5,94 / 3,25 | 0 | 14,763 ms | 14,764 ms, 5,75 A | 3,15 kV |
| B | com | 13,65 / 13,11 | −3,76 / 0,43 | 0 | 26,816 ms | 26,823 ms, 0,28 A | **5,15 kV** |
| C | com | −9,98 / 9,43 | −4,20 / 0,41 | 0 | 27,119 ms | 27,129 ms, −0,15 A | **4,94 kV** |

Picos em kV, RRRV em kV/µs. **Insensibilidade ao passo**: refinando de 1 µs para 50 ns o pico do
polo R muda 0,4 % (7,904 → 7,934 kV), contra a razão de 3,2 vezes que o artefato anterior exibia
— é o critério que separa resultado físico de degrau numérico [CÁLCULO PRÓPRIO: medição].

**O ramo amortecedor reduz a TRV e PIORA a tensão no motor.** A redução no gap confirma-se nas
três fases, mas a tensão no terminal do motor — a grandeza que governa o dano do isolamento —
sobe de 3,20 para 5,15 kV na fase B e de 3,13 para 4,94 kV na fase C. O trabalho não reporta
essa grandeza. A causa é a mesma do achado 5 da seção 5: com disparo em 2404 V e comando
travado, o ramo de 30 Ω conduz em regime — a energia dissipada medida na janela de 45 ms é de
1218 J na fase B e 1562 J na fase C, contra 0,39 J na fase A, que separa isolada
[CÁLCULO PRÓPRIO: medição]. Quilojoules em 45 ms são potência de regime, não energia de surto.

Leitura: com corte de 1 a 2 A, a energia magnética aprisionada é $\tfrac12 L I^2 \le 18$ mJ e a
TRV é a de primeiro polo a abrir com carga indutiva — 1,8 a 2,3 pu — sem escalada porque não há
mecanismo de reignição (seção 3). A concordância da fase A **com** amortecedor (6,35 vs 5,94 kV;
3,28 vs 3,25 kV/µs) é a única linha em que a Tabela III e o motor coincidem, e é justamente a
linha em que o próprio trabalho não reporta reignições.

## 5. O que a listagem do ATP mostra

| Achado | Evidência | Severidade |
|---|---|---|
| Extremos de 22,6 pu e 19,5 pu no terminal do motor **antes de qualquer manobra** | `01ATA` mín. −76 802 V em 8 µs; `01ATC` máx. 66 285 V em 8 µs; primeiro comando em 14,55 ms [FATO: listagem, *Extrema*] | crítica |
| Nós curto-circuitados à terra durante a manobra | `Floating subnetwork found` em X0002A (≈20 ms, 30,5 ms) e X0002B (33,5 ms); `shorted to ground with 1/Ykk = FLTINF` [FATO: listagem] | crítica |
| Máximos dos sinais do disjuntor no instante exato do comando | `XX0034–X0002C` máx. 29 830 V em t = 0,02475 s = `T_OPENs` [FATO: listagem, *Times of maxima*] | alta |
| Capacitância de câmara aberta 6 µF | `COPEN = 6.` com `COPT = 0`; padrão do próprio `MODEL` 3 nF; física de câmara a vácuo: picofarads [FATO: arquivo] | alta |
| Amortecedor dispara em 2404 V = 1,0009 × tensão nominal fase-terra eficaz e trava | `Valve. 2.404E+03 1.000E+00`; `SNUB_CTRL` sem liberação; pico de regime 3386 V [FATO: listagem/arquivo] | alta |
| Simulação suspensa por esgotamento do espaço de traçado | duas ocorrências [FATO: listagem] | média |
| Listagem não corresponde ao caso base | janela 40 ms, `T_OPENt = 0,02475`, amortecedor presente [FATO: listagem] | média |

Sobre o primeiro achado: com `TSTART = −50` o ATP semeia os elementos concentrados, mas o
transitório nos primeiros 30 µs indica histórico de trânsito das linhas distribuídas partindo
de zero [INFERÊNCIA FÍSICA]; o motor dedicado semeia esse histórico e mede 2,0 mV de desvio em
cinco ciclos [FATO: medição]. Sobre o quinto: depois do primeiro evento o ramo de 30 Ω conduz
em todo semiciclo acima de 2404 V — deixa de ser seletivo e vira resistor permanentemente
ligado à terra [INFERÊNCIA FÍSICA a partir dos fatos].

## 6. Hipótese sobre a origem dos 41,44 kV

Os picos da Tabela III têm a ordem de grandeza dos eventos numéricos da listagem (degraus no
instante de comando e curto-circuito de nós flutuantes), ocorrem nos instantes de `T_OPEN`, e
não podem vir do mecanismo de reignição do `MODEL` (seção 3). A hipótese mais econômica é que
sejam artefatos numéricos [HIPÓTESE]. Decide-se com o `.pl4` da execução original: (i) o pico
ocorre no passo do comando ou após uma sequência de reignições? (ii) há mudança de sinal da
corrente da chave antes do pico?

## 7. Correções recomendadas no `MODEL`

1. Mover `I_PREV := I_CBr` para **depois** do teste de passagem por zero.
2. Na reignição, religar a chave (`SW_STATEr := 1.0`) ou dar ao ramo de arco uma impedância que
   conduza (o arco de reignição é resistivo, ordens de ohm; a capacitância pertence ao gap em
   **paralelo**, não em série).
3. `COPEN` na ordem de picofarads a nanofarads, em paralelo com o gap.
4. Extinção de alta frequência com `|di/dt| <= crítico` (convenção física).
5. Nível de disparo do amortecedor acima do pico de regime (> 3,4 kV) e liberação do comando
   após a condução, sob pena de o ramo não ser seletivo.

## Referências

- Arquivo de dados e listagem de saída do caso (fixtures deste repositório).
- Lista de Exercícios 02, EEE873 — §1.3 (critério de comutação), §3.6 (campo `Imar`).
- Documento A (SEPOC 2026), Tabela III, p. 3.
- Lin, J.; Martí, J. R. Implementation of the CDA procedure in the EMTP. IEEE Trans. Power
  Systems, v. 5, n. 2, 1990.
