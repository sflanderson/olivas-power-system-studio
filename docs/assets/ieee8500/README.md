# Figuras — IEEE 8500-Node Test Feeder

Figuras usadas nos slides do módulo de **fluxo de potência
desbalanceado** do Catálogo Técnico do Olivas PSS.

## Procedência (leia antes de reusar)

| Item | Origem |
|------|--------|
| Topologia, impedâncias, cargas, reguladores | Dataset **oficial** do IEEE 8500-Node Test Feeder (IEEE PES Distribution Test Feeder Working Group), caso `Master-unbal.dss` |
| Estado de tensão plotado | Solução de **referência** obtida com o motor OpenDSS (`dss-python`), tolerância 1e-8 |
| Paleta, tipografia e proporções | Design system do Catálogo Técnico (`#243018` / `#4D9A2E` / `#5A6157`) |

> **Importante:** estas figuras foram calculadas com o motor de
> referência OpenDSS sobre o dataset público, **não** exportadas da
> GUI do Olivas PSS. Elas ilustram o caso de estudo e as grandezas
> que o módulo entrega. Para material comercial que precise atribuir
> o resultado ao produto, substitua por capturas/exportações da
> própria aplicação.

Os números citados nos slides como resultado de execução do módulo
(24 iterações, 8.531 nós, 11.975,4 kW · 1.339,0 kvar, V entre
0,9357 e 1,0563 pu, taps dos 12 reguladores) vêm da execução do
Olivas PSS v7.x, não destas figuras.

## Arquivos

| Arquivo | Conteúdo |
|---------|----------|
| `ieee8500_mapa.png` | Topologia georreferenciada (4.876 barras, 3.698 segmentos) colorida pela tensão resolvida; subestação e bancos de reguladores marcados |
| `ieee8500_perfil.png` | Perfil de tensão das 3 fases contra a distância elétrica à subestação, com a faixa ANSI C84.1 Range A |
| `ieee8500_desbalanco.png` | Histograma do fator de desbalanço (VUF IEC 61000-3-13 e NEMA MG-1) nas 647 barras trifásicas da rede primária, contra o limite de 2 % |
| `ieee8500_qsts.png` | Varredura quase-estática de 24 passos: potência da fonte, tensões extremas e desbalanço máximo |
| `stats.json` | Grandezas consolidadas do caso |
| `qsts.json` | Série completa dos 24 passos |

## Reprodução

O dataset oficial **não** é versionado aqui (é material de terceiros,
~1,4 MB). Baixe-o do repositório de referência do OpenDSS
(`IEEETestCases/8500-Node`) para um diretório `ieee8500/` ao lado do
script e execute:

```bash
pip install dss-python matplotlib numpy
python scripts/make_ieee8500_figs.py     # FIG_OUT define o destino
```

O script adiciona um `EnergyMeter` na saída da subestação — sem ele o
OpenDSS não calcula a distância elétrica usada no perfil de tensão.

## Grandezas do caso (referência)

| Grandeza | Valor |
|----------|-------|
| Nós de fase | 8.531 |
| Barras | 4.876 |
| Transformadores de serviço 120/240 V | 1.177 |
| Cargas monofásicas | 2.354 |
| VUF máximo (rede primária) | 3,64 % |
| Barras trifásicas acima de 2 % de desbalanço | 56 % |
| Pior tensão no QSTS de 24 passos | 0,9114 pu |
| Pior desbalanço NEMA no QSTS | 5,44 % |
