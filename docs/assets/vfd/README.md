# Figuras — módulo de análise de inversor (VFD)

Figuras usadas nos slides **15 · VFD · Lado da rede** e
**16 · VFD · Lado do motor** do Catálogo Técnico.

## Para que servem

O Catálogo Técnico usa, nesses slides, as **capturas da própria GUI**
do Olivas PSS v7.x. As figuras deste diretório não vão para o deck:
elas são uma **verificação independente** dos números que o módulo
publica — reconstroem o caso a partir das premissas declaradas e
chegam aos mesmos resultados por um caminho separado.

## Procedência (leia antes de reusar)

Reproduzem o caso **VFD-01** (75 kW @ 480 V, retificador de 6 pulsos,
motor a 150 m de cabo) a partir das premissas declaradas no estudo —
banco de 0,050 Mvar, reator de dessintonia de 0,50 %, X/R = 11,9,
t_subida de 0,1 µs. **Foram calculadas por este script**, não
exportadas da GUI.

Os quatro resultados de saída conferem com a execução do Olivas PSS
v7.x, o que valida os parâmetros de entrada reconstruídos:

| Grandeza | Olivas PSS v7.x | Este script |
|----------|-----------------|-------------|
| Ressonância paralela | h = 18,73 | h = 18,73 |
| Impedância no pico | 55 Ω | 54,8 Ω |
| Distorção de corrente | THD_I = 80,0 % | THD_I = 80,0 % |
| Pico no terminal do motor | 1358 V | 1358 V |
| Comprimento crítico do cabo | 7,5 m | 7,5 m |

A divergência de 0,2 Ω no pico é amortecimento: a altura do pico
depende do X/R e do Q do reator, e o próprio módulo declara que
"a POSIÇÃO do pico é robusta; a ALTURA depende do amortecimento".

## Modelo

Curto do barramento deduzido da ressonância observada:
`S_sc = h_r² · Q = 18,73² × 50 kvar = 17,54 MVA`.

- `X_sys = V²/S_sc`, `R_sys = X_sys/(X/R)`
- `X_C = V²/Q`, `X_L = 0,005 · X_C` (reator de dessintonia)
- `Z_PCC(h) = Z_sys(h) ∥ Z_banco(h)` — pico paralelo em
  `h = √(X_C/(X_sys + X_L))`, notch série em `h = √(X_C/X_L) = 14,1`
- Onda refletida: `V_pico(L) = √2·V_LL·(1 + Γ)`, com `Γ` crescendo
  linearmente até `L_crit = t_subida · v/2` e saturando em 1,0

O espectro de 6 pulsos é a tabela característica do retificador
(5º: 70,9 % · 7º: 28,3 % · 11º: 18,2 % · …).

## Arquivos

| Arquivo | Conteúdo |
|---------|----------|
| `vfd_ressonancia.png` | Impedância vista do PCC, com e sem reator de dessintonia, sobre os harmônicos característicos |
| `vfd_espectro.png` | Espectro de corrente de entrada contra o limite individual (premissa até I_sc/I_L do PCC ser informada) |
| `vfd_onda_refletida.png` | Pico no terminal do motor contra o comprimento do cabo, com o limite NEMA MG-1 Parte 30 |
| `vfd_filtro.png` | Separação em frequência entre fundamental, corte do filtro senoidal e chaveamento |

## Reprodução

```bash
pip install matplotlib numpy
FIG_OUT=docs/assets/vfd python scripts/make_vfd_figs.py
```

As premissas ficam no bloco `--- premissas do caso VFD-01 ---` do
script; alterá-las regenera as quatro figuras de forma coerente.
