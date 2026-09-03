# Caso base — especificação extraída do arquivo de dados ATP

**Objetivo.** Fixar, a partir do arquivo de dados como fonte única da verdade, os parâmetros
do caso de manobra que servirá de referência ao motor de transitórios dedicado.

**Arquivos.** `tests/fixtures/atp/trt_all_motors_dt_ea.atp` (caso base, sem ramo amortecedor)
e `tests/fixtures/atp/trt_all_motors_com_snubber_2026-04.atp` (variante com ramo amortecedor).

## 1. Ajustes de integração

| Grandeza | Valor | Origem |
|---|---|---|
| Passo de integração | 1 µs | cartão de dados diversos |
| Janela simulada | 45 ms | idem |
| Frequência de potência | 60 Hz | cartão `POWER FREQUENCY` |
| `XOPT`, `COPT` | em branco → 0 | indutâncias em mH, capacitâncias em µF |

## 2. Topologia (verificada por varredura de conectividade)

```
fonte X0030A/B/C  ──[ramo acoplado R,L,C]──  X0028A/B/C   (enrolamento em triângulo)
                                                  ║  matriz acoplada 6×6
                          XX0003 ──[12,009 Ω]── X0029A/B/C (enrolamento em estrela)
                                     terra
X0029x ──[cabo, modelo dependente da frequência]── X0002x   (lado fonte do disjuntor)
X0002x ──[disjuntor: chave + ramo RLC de arco]──── X0001x   (lado carga)
X0001x ──[cabo, parâmetros distribuídos constantes]── 01ATx
01ATx  ──[R = 0,691 Ω + L = 8,9795 mH]── terra                (motor)
```

O resistor de 12,009 Ω entre o ponto de estrela e a terra é o aterramento de neutro por
resistor. A matriz de 1138,52 Ω em paralelo representa o ramo de magnetização.

## 3. Parâmetros decodificados com confiança

### 3.1 Fonte
Três fontes tipo 14 (cossenoidal), 11718,4337 V de pico fase-terra, 60 Hz, defasagens
0°, +120° e −120°, `TSTART = −50` (isto é, incluída na solução fasorial de regime
permanente) e `TSTOP = 100`.

### 3.2 Motor
Ramo série R–L de cada fase para a terra: R = 0,691 Ω e L = 8,9795 mH.
Em 60 Hz: X = 3,3853 Ω, |Z| = 3,4551 Ω, fator de potência 0,2000 — coerente com o
estado de rotor bloqueado.

### 3.3 Disjuntor — dados por polo

| Parâmetro | Polo R | Polo S | Polo T |
|---|---|---|---|
| Instante de separação | 14,55 ms | 24,75 ms | 24,81 ms |
| Corrente de corte | 1 A | 2 A | 2 A |
| Capacidade de extinção | 5 A/µs | 15 A/µs | 15 A/µs |
| Recuperação dielétrica | \(V_{wth}=0{,}801\,t+1{,}226\,t^2\) (kV, t em ms) | idem | idem |
| Resistência fechado | 0,001 | 0,002 | 0,001 |
| Indutância fechado | 0,002 | **1,0** | 0,002 |
| Resistência de arco | 20 Ω | 20 Ω | 20 Ω |

Observações de auditoria:
1. A corrente de corte e a capacidade de extinção são **valores fixos distintos por polo**,
   e não faixas de amostragem.
2. O critério de reignição no código do modelo é `|V| > V_wth · 1,1`, ou seja, exige 10 %
   acima da suportabilidade — fator não descrito no texto do trabalho.
3. A extinção de alta frequência usa `|di/dt| > crítico`, confirmando a convenção invertida
   em relação à física usual (interromper quando o di/dt está **dentro** da capacidade).
4. O temporizador da recuperação dielétrica é reiniciado a cada passagem por zero da
   corrente, não no instante da extinção do arco.
5. A indutância de fechado do polo S difere das demais por fator 500. O ramo fica em
   paralelo com a chave ideal fechada, de modo que o efeito antes da abertura é pequeno,
   mas a assimetria deve ser confirmada como intencional.

### 3.4 Ramo amortecedor (apenas na variante)
Resistor de 30 Ω de cada fase para a terra, em série com um par de válvulas
antiparalelas comandadas por controlador que trava o disparo na primeira ocorrência de
estado de arco e **não o libera mais** durante a simulação.

## 4. O que permanece indeterminado

| Item | Cartão | Por que não foi decodificado |
|---|---|---|
| Transformador | matriz acoplada 6×6 com a opção `USE AR` | a semântica das duas colunas sob essa opção precisa da seção 5.3 do manual de referência do ATP; as razões observadas entre os termos diagonais são compatíveis com a relação de espiras ao quadrado numa das colunas e incompatíveis na outra, o que impede leitura segura |
| Ramo fonte–triângulo | cartões acoplados tipo 1/2/3 com termos `-1.` | mesma dependência |
| Cabo a jusante | cartão de linha a parâmetros distribuídos, campos R', A', B' com comprimento negativo | a convenção dos campos sob comprimento negativo precisa de confirmação |
| Nível de disparo do ramo amortecedor | cartão de válvula, campos `3.E3`, `1.`, `.005` | a atribuição campo a campo sob o cabeçalho impresso precisa de confirmação |

Os dados de ajuste do cabo dependente da frequência (polos e resíduos da impedância
característica e da função de propagação) estão presentes no arquivo e são utilizáveis
diretamente, assim como a geometria do cartão de cálculo de parâmetros.

## 5. Próximo passo

Resolver os quatro itens da seção 4 e montar o caso no motor dedicado nas duas
configurações, confrontando com a tabela de resultados do trabalho. Enquanto os itens
não forem resolvidos, qualquer confronto seria feito sobre uma rede a montante
arbitrada — o que invalidaria a comparação.
