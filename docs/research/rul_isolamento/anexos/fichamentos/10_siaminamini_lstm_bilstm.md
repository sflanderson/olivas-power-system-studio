# Fichamento 10 — Siami-Namini, Tavakoli e Siami Namin (2019): desempenho de LSTM e BiLSTM na previsão de séries temporais

Arquivo-fonte: `papers/txt/The_Performance_of_LSTM_and_BiLSTM_in_Forecasting_Time_Series.txt` (8 páginas; numeração interna 3285–3292 dos anais; as páginas citadas abaixo como "p. N" seguem os marcadores `===== PAGE N =====` do txt, de modo que p. 1 = 3285 e p. 8 = 3292).

Convenção de rotulagem: **[FATO]** = afirmação do artigo, com página; **[INFERÊNCIA]** = leitura/juízo meu a partir do texto; **[HIPÓTESE]** = suposição não verificável no texto.

Advertência inicial: este artigo **não trata de degradação, confiabilidade, PHM ou RUL**. É um estudo comparativo de arquiteturas de previsão (ARIMA, LSTM, BiLSTM) sobre séries financeiras. Foi incluído no corpus, presumivelmente, como referência de método para o bloco "modelos sequenciais orientados a dados" do monitoramento de isolamento. As seções 3, 4 e 6 registram, portanto, ausências explícitas.

---

## 1. Referência completa

SIAMI-NAMINI, Sima; TAVAKOLI, Neda; SIAMI NAMIN, Akbar. The Performance of LSTM and BiLSTM in Forecasting Time Series. In: **2019 IEEE INTERNATIONAL CONFERENCE ON BIG DATA (BIG DATA)**. Anais [...]. IEEE, 2019. p. 3285–3292. ISBN 978-1-7281-0858-2. DOI: [INSERIR CITAÇÃO] (não consta no texto extraído).

- Afiliações (p. 1) [FATO]: S. Siami-Namini — Department of Math and Statistics, Texas Tech University; N. Tavakoli — Department of Computer Science, Georgia Institute of Technology; A. Siami Namin — Department of Computer Science, Texas Tech University.
- Identificador de copyright: "978-1-7281-0858-2/19/$31.00 ©2019 IEEE" (p. 1). [FATO]
- Financiamento: National Science Foundation (NSF), grants 1821560 e 1723765 (p. 8). [FATO]
- Volume/número: não se aplica (artigo de anais). Local do evento: não consta no texto extraído. [INSERIR CITAÇÃO, se necessário]
- Trabalho anterior dos mesmos autores, do qual este é continuação (p. 2): ref. [20], "A Comparison of ARIMA and LSTM in Forecasting Time Series", 17th IEEE ICMLA, pp. 1394–1401, 2018 (p. 8). [FATO]

---

## 2. Objetivo do artigo

Comparar o desempenho de previsão e o comportamento de treinamento de três modelos — ARIMA, LSTM unidirecional e LSTM bidirecional (BiLSTM) — na previsão de séries temporais financeiras, investigando se "camadas adicionais de treinamento" (a passagem reversa da BiLSTM) melhoram a predição (p. 1–2). [FATO]

Questões de pesquisa enunciadas (p. 2) [FATO]:
1. "A predição melhora quando os dados de série temporal são aprendidos em ambas as direções (passado-para-futuro e futuro-para-passado)?"
2. "Quão diferentemente essas duas arquiteturas (LSTM e BiLSTM) tratam os dados de entrada?"
3. "Quão rápido essas duas arquiteturas atingem o equilíbrio?"

Contribuições declaradas (p. 2) [FATO]: (i) investigar se treinamento adicional melhora a predição no contexto financeiro; (ii) análise de desempenho mostrando "redução de 37,78% nas taxas de erro" da BiLSTM sobre a LSTM; (iii) análise comportamental do treinamento, segundo a qual BiLSTMs "buscam lotes menores de dados" e "atingem o equilíbrio mais lentamente" que LSTMs.

[INFERÊNCIA] O artigo é essencialmente empírico-comparativo, com seção de fundamentação teórica (Seção III) de caráter didático. Não propõe arquitetura nova; a novidade alegada é a evidência de que a bidirecionalidade ajuda mesmo em séries numéricas sem "contexto" semântico (p. 6).

---

## 3. Sistema/componente e mecanismo(s) de degradação tratados

- **Sistema:** nenhum sistema físico. O objeto são séries de preços de índices bursáteis e de uma ação: Nikkei 225 (N225), NASDAQ Composite (IXIC), Hang Seng (HSI), S&P 500 (GSPC), Dow Jones Industrial Average (DJI) e IBM (p. 4). [FATO]
- **Mecanismo de degradação:** não há. O artigo não menciona falha, envelhecimento, desgaste, confiabilidade ou vida útil em nenhuma página. [FATO — ausência]
- Fatores de contexto reconhecidos pelos autores como influentes na previsão: "sazonalidade, choques econômicos, eventos inesperados e mudanças internas à organização que gera os dados" (p. 1). [FATO]
- [INFERÊNCIA] A única analogia possível com um processo de degradação é estrutural: uma série univariada amostrada em intervalos regulares cujo próximo valor se quer prever. Séries de preço, porém, são próximas de passeio aleatório sem tendência determinística de longo prazo, ao passo que indicadores de saúde de isolamento apresentam, em geral, tendência monotônica (ou por patamares) até um limiar de falha. A analogia é fraca já no nível estatístico.

---

## 4. Indicadores/precursores de degradação usados

Não existem indicadores de degradação. Registra-se, por completude, a variável usada:

| Grandeza | Unidade | Como é obtida | Taxa de amostragem | Página |
|---|---|---|---|---|
| "Adjusted Close" (preço de fechamento ajustado), "escolhida como a única característica" de entrada dos três modelos | pontos de índice ou unidade monetária da ação (não declarada no texto) [INFERÊNCIA] | extraída do sítio Yahoo Finance (nota de rodapé 1, p. 4) | diária, semanal e mensal, conforme a série (Tabela I, p. 4) | p. 4 |

- Períodos: índices de jan. 1985 a ago. 2018; IBM diário de jul. 2009 a jul. 2019 (p. 4). [FATO]
- Nenhum pré-processamento (normalização, diferenciação, remoção de tendência) é descrito no corpo do texto. O único indício é a linha 7 do Listing 1, "y ← train − X", que, lida literalmente, produz alvo nulo (ver §5.3). [FATO + INFERÊNCIA]
- [INFERÊNCIA] Para o problema-alvo, este quadro serve apenas como lembrete de que a escolha de um único indicador univariado, sem covariáveis de estresse, é a configuração mais pobre possível para prognóstico.

---

## 5. Modelo/algoritmo

**Classe:** orientado a dados (aprendizado profundo supervisionado, regressão univariada de um passo à frente), com ARIMA como referência estatística. [FATO, p. 1–2, 4]

### 5.1 Fundamentação apresentada (Seção III, p. 2–4) [FATO]

- **RNN:** extensão de redes *feed-forward* capaz de tratar sequências de comprimento variável por meio de "estados ocultos recorrentes"; "na prática, devido às limitações de memória das RNNs, o comprimento da informação sequencial é limitado a apenas poucos passos para trás" (p. 2). Problemas de gradiente evanescente e explosivo (p. 3); este último "pode ser resolvido truncando/esmagando os gradientes [12]" (p. 3).
- **LSTM:** célula com três portas — esquecimento, entrada e saída — cujas decisões de preservar/descartar dependem dos pesos aprendidos (p. 3).
- **BiLSTM:** "duas LSTMs são aplicadas aos dados de entrada. Na primeira rodada, uma LSTM é aplicada à sequência de entrada (camada *forward*). Na segunda rodada, a forma reversa da sequência de entrada é alimentada ao modelo LSTM (camada *backward*)" (p. 3–4), com referência a Schuster e Paliwal [25] e a Baldi et al. [3]. A reversão é comparada ao "complemento de Watson-Crick [10]" (p. 5).

### 5.2 Equações-chave (numeração original; transcrição fiel ao txt)

| Nº | Equação | Página | Observação |
|---|---|---|---|
| (1) | h_t = σ(W_x x_t + W_h h_{t−1} + b_t) | p. 2 | atualização de memória da RNN; σ = sigmoide logística, tanh ou ReLU; W_x, W_h matrizes de peso; b_t viés "constante" |
| (2) | p(x_1, …, x_T) = p(x_1) p(x_2 \| x_1) p(x_3 \| x_1, x_2) … p(x_T \| x_1, …, x_{T−1}) | p. 3 | decomposição da probabilidade da sequência |
| (3) | p(x_t \| x_1, …, x_{t−1}) = σ(h_t) | p. 3 | cada condicional modelada pelo estado h_t da eq. (1) |
| (4) | f_t = σ(W_fh[h_{t−1}], W_fx[x_t], b_f) | p. 3 | porta de esquecimento; f_t ∈ [0, 1] |
| (5) | i_t = σ(W_ih[h_{t−1}], W_ix[x_t], b_i) | p. 3 | porta de entrada (camada sigmoide) |
| (6) | c̃_t = tanh(W_ch[h_{t−1}], W_cx[x_t], b_c) | p. 3 | vetor de candidatos (camada tanh) |
| (7) | c_t = f_t ∗ c_{t−1} + i_t ∗ c̃_t | p. 3 | atualização do estado de célula |
| (8) | o_t = σ(W_oh[h_{t−1}], W_ox[x_t], b_o) | p. 3 | porta de saída |
| (9) | h_t = o_t ∗ tanh(c_t) | p. 3 | saída oculta, "valor entre −1 e 1" |
| (10) | RMSE = sqrt( (1/N) Σ_{i=1}^{N} (y_i − ŷ_i)² ) | p. 4 | N observações; y_i real; ŷ_i previsto |
| (11) | %Changes = (New Value − Original Value) / Original Value × 100 | p. 4 | percentual de redução de RMSE |

[INFERÊNCIA] As eqs. (4), (5), (6) e (8) usam notação não padrão, com argumentos separados por vírgula dentro de σ(·) e tanh(·); a forma usual é σ(W_f·[h_{t−1}, x_t] + b_f). Trata-se, ao que tudo indica, de uma abreviação tipográfica, não de uma variante do modelo. Não há equação para a combinação dos estados *forward* e *backward* da BiLSTM (concatenação, soma etc.); o artigo trata esse ponto apenas em prosa (p. 3–5). [FATO — ausência]

### 5.3 Estrutura e hiperparâmetros (Listing 1, p. 5) [FATO]

| Item | Valor / escolha | Linha do Listing |
|---|---|---|
| Partição | 70% treino / 30% teste, sequencial | 1–3 |
| Semente | `random.seed(7)` | 4 |
| Modelo | `Sequential()`; `LSTM(neurons, stateful=True)` ou `Bidirectional(LSTM(neurons, stateful=True))` | 8–12 |
| Perda / otimizador | `mean_squared_error` / `adam` | 13 |
| Treinamento | laço de `epoch` iterações com `model.fit(X, y, epochs=1, shuffle=False)` seguido de `model.reset_states()` | 14–17 |
| Neurônios | 4 | 20 |
| Épocas | 1 (Seção VI); 1 e 2 na análise comportamental (Seção VII) | 19; p. 6–7 |
| Previsão | um passo à frente; validação *walk-forward* sobre o teste | 18, 24–31 |
| Métrica | RMSE = sqrt(MSE) | 32–33 |
| Tamanho de lote, taxa de aprendizado, janela de defasagem, escalonamento | **não declarados** | — |

- Os autores descrevem o algoritmo como "*rolling*": "re-treinam os modelos cada vez que uma nova observação é buscada (linha 26). Assim, uma vez feita a predição e comparado seu valor com o real, o valor é adicionado ao conjunto de treino (linha 26) e o modelo é re-treinado (linha 27)" (p. 5). [FATO]
- [INFERÊNCIA — inconsistência grave] O pseudocódigo transcrito **não** contém o re-treinamento descrito: as linhas 26–27 apenas leem `X ← test[i]` e chamam `forecast_lstm`, e nenhuma linha acrescenta a observação ao treino ou refaz o ajuste. Além disso, `X ← test[i]` e `expected ← test[i]` (linhas 26 e 30) fazem a entrada do preditor coincidir com o valor esperado, e a linha 7 (`y ← train − X` com `X ← train`) define alvo identicamente nulo. Lido ao pé da letra, o Listing 1 não é executável nem corresponde ao procedimento narrado; deve ser tomado como esquema, e os hiperparâmetros efetivos (janela, lote, diferenciação) permanecem desconhecidos. [HIPÓTESE] O código real segue o tutorial de Brownlee [5] (p. 8), que usa diferenciação de primeira ordem, janela de defasagem 1, escalonamento para [−1, 1] e `batch_size = 1`; isso é compatível com a linha 7 (diferenciação) mas não é verificável no texto.
- **Software:** não nomeado; a sintaxe (`Sequential`, `model.fit`, `reset_states`) indica Keras. [INFERÊNCIA]

### 5.4 Comportamento de treinamento observado (Seção VII, p. 6–7) [FATO]

- Os autores registram a perda por lote e concluem que a LSTM "atinge o equilíbrio" após ~3 lotes, enquanto a BiLSTM oscila, exige mais lotes e continua aprendendo na segunda época (ver §7).
- Sobre o número de lotes (Tabela III, p. 7): "o modelo LSTM dividiu os dados em 41–42 lotes (blocos maiores); ao passo que o modelo BiLSTM dividiu os mesmos dados em 71–75 lotes (blocos menores)". Explicação dos autores: como a BiLSTM treina nas duas direções, "o comprimento dos dados de treinamento que pode ser tratado por lote é quase metade" do da LSTM (p. 7).
- [INFERÊNCIA] Essa explicação não é sustentada pelo funcionamento de um *wrapper* bidirecional em Keras, que não altera o tamanho de lote; o número de lotes por época é determinado por `batch_size` e pelo comprimento de `X`, ambos não reportados. A diferença observada sugere configuração experimental distinta entre as duas execuções, e não uma propriedade intrínseca da BiLSTM. Os autores apresentam a hipótese como "uma racionalização" ("A rational to explain this behavior", p. 7), sem verificação.

---

## 6. Dados e experimento

- **Fonte:** Yahoo Finance; séries reaproveitadas parcialmente do trabalho anterior [20] (p. 4). [FATO]
- **Tabela I — séries e observações (p. 4)** [FATO]:

| Série | Treino (70%) | Teste (30%) | Total |
|---|---|---|---|
| N225.monthly | 283 | 120 | 403 |
| IXIC.daily | 8.216 | 3.521 | 11.737 |
| IXIC.weekly | 1.700 | 729 | 2.429 |
| IXIC.monthly | 390 | 168 | 558 |
| HSI.monthly | 258 | 110 | 368 |
| GSPC.daily | 11.910 | 5.105 | 17.015 |
| GSPC.monthly | 568 | 243 | 811 |
| DJI.daily | 57.543 | 24.662 | 82.205 |
| DJI.weekly | 1.189 | 509 | 1.698 |
| DJI.monthly | 274 | 117 | 391 |
| IBM.daily | 1.762 | 755 | 2.517 |
| **Total** | **84.093** | **36.039** | **120.132** |

- [INFERÊNCIA] Há inconsistências entre a Tabela I e o período declarado (jan. 1985–ago. 2018 ≈ 8.500 pregões): GSPC.daily com 17.015 e IXIC.daily com 11.737 observações só são possíveis com históricos mais longos que 1985; DJI.daily com 82.205 observações diárias equivaleria a mais de três séculos de pregões, o que é impossível — provável erro de extração/duplicação de dados ou erro tipográfico. Como DJI.daily é justamente a série com maior redução relatada (−77,60%), o resultado principal fica sob suspeita. IBM.daily (2.517 ≈ 10 anos × 252 pregões) é a única contagem plenamente coerente.
- **Ensaio acelerado / ciclos:** não se aplica. [FATO — ausência]
- **Protocolo:** treinamento no bloco inicial de 70%; previsão um passo à frente em *walk-forward* sobre os 30% finais; RMSE em unidades da série (p. 4–5). [FATO]
- **Replicações / sementes:** uma execução por série, semente fixa 7; sem intervalos de confiança nem testes de significância. [FATO — ausência; INFERÊNCIA quanto à consequência]

---

## 7. Métricas e resultados numéricos

### 7.1 Tabela II — RMSE e reduções percentuais (p. 6) [FATO]

| Série | ARIMA [20] | LSTM | BiLSTM | BiLSTM vs LSTM (%) | BiLSTM vs ARIMA (%) | LSTM vs ARIMA (%) |
|---|---|---|---|---|---|---|
| N225.monthly | 766,45 | 102,49 | 23,13 | −77,43 | −96,98 | −86,66 |
| IXIC.daily | 34,61 | 2,01 | 1,75 | −12,93 | −94,94 | −94,19 |
| IXIC.weekly | 72,53 | 7,95 | 11,53 | **+45,03** | −84,10 | −89,03 |
| IXIC.monthly | 135,60 | 27,05 | 8,49 | −68,61 | −93,37 | −80,00 |
| HSI.monthly | 1.306,95 | 172,58 | 121,71 | −29,47 | −90,68 | −86,79 |
| GSPC.daily | 14,83 | 1,74 | 0,62 | −64,36 | −95,81 | −88,26 |
| GSPC.monthly | 55,30 | 5,74 | 4,63 | −19,33 | −91,62 | −89,62 |
| DJI.daily | 139,85 | 14,11 | 3,16 | −77,60 | −97,77 | −89,91 |
| DJI.weekly | 287,60 | 26,61 | 23,05 | −13,37 | −91,98 | −90,74 |
| DJI.monthly | 516,97 | 69,53 | 23,69 | −65,59 | −95,41 | −86,50 |
| IBM.daily | 1,70 | 0,22 | 0,15 | −31,18 | −91,11 | −87,05 |
| **Média** | **302,96** | **39,09** | **20,17** | **−37,78** | **−93,11** | **−88,07** |

- Texto (p. 5): a redução BiLSTM sobre LSTM "varia de (−)77,60% para DJI.daily a (−)12,93% para IXIC.daily"; "em média, os valores de RMSE para LSTM e BiLSTM são 39,09 e 20,17, respectivamente, alcançando (−)37,78% de redução em média"; "em quase todos os casos (exceto IXIC.weekly) observa-se uma redução significativa". [FATO]
- Os valores de ARIMA são importados do trabalho anterior [20] (cabeçalho da Tabela II, p. 6). [FATO]
- [INFERÊNCIA] (i) As médias de RMSE são dominadas pelas séries de maior escala (HSI, N225, DJI.monthly); médias de RMSE entre séries com escalas de 1,70 a 1.306,95 não têm significado estatístico. (ii) A "média" de −37,78% é a média aritmética das reduções percentuais, incluindo o caso de piora (+45,03%); o adjetivo "significativa" (p. 5) não é acompanhado de teste. (iii) Sem *baseline* ingênuo (persistência, x̂_{t+1} = x_t), não se pode saber se as LSTMs superam a previsão trivial, que em séries de preço costuma ser competitiva; reduções de 88–93% sobre ARIMA sugerem [HIPÓTESE] ARIMA mal especificado em [20], e não ganho real de modelagem.

### 7.2 Trajetórias de perda (Seção VII e Fig. 3, p. 6–8; série IBM) [FATO]

| Configuração | Início | Comportamento | Final / estabilização |
|---|---|---|---|
| LSTM, época = 1 | 0,061 | cai após o 3º lote para 0,0256 e permanece estável | 0,0244 no 42º lote (p. 6) |
| BiLSTM, época = 1 | 0,0404 | **sobe** até 0,0874 no 3º lote, depois decresce lentamente | nunca atinge 0,0256 (p. 6) |
| LSTM, época = 2, rodada 1 | 0,048 | estabiliza após o 3º lote | 0,019 (p. 7) |
| BiLSTM, época = 2, rodada 1 | 0,184 | estabiliza após o 8º lote | 0,044 (p. 7) |
| LSTM, época = 2, rodada 2 | 0,015 | estável ("nada de valor é aprendido" na 2ª rodada) | 0,0237 (p. 7) |
| BiLSTM, época = 2, rodada 2 | 0,135 | cai rapidamente a 0,026, flutua, estabiliza após o 9º lote | 0,0295 (p. 7) |

### 7.3 Tabela III — estatísticas descritivas da perda, série IBM (p. 7) [FATO]

| Modelo | Mín. | Máx. | DP | Nº de lotes |
|---|---|---|---|---|
| LSTM, época = 1 | 0,014 | 0,061 | 0,007 | 42 |
| BiLSTM, época = 1 | 0,026 | 0,087 | 0,012 | 71 |
| LSTM, época = 2 (rodada 1) | 0,013 | 0,048 | 0,005 | 41 |
| BiLSTM, época = 2 (rodada 1) | 0,025 | 0,184 | 0,02 | 75 |
| LSTM, época = 2 (rodada 2) | 0,01 | 0,23 | 0,004 | 42 |
| BiLSTM, época = 2 (rodada 2) | 0,022 | 0,135 | 0,013 | 73 |

- Interpretação dos autores: DP maior da BiLSTM (0,012 vs 0,007 na época 1; 0,013 vs 0,004 na rodada 2 da época 2) "indica que o modelo LSTM unidirecional atinge o equilíbrio mais rápido" e que "a BiLSTM requer mais dados para ajustar os parâmetros de forma ótima" (p. 7). [FATO]
- [INFERÊNCIA] O "Máx. 0,23" da LSTM (época 2, rodada 2) é incompatível com o texto, que afirma perda iniciando em 0,015 e "estável" até 0,0237 com DP 0,004; trata-se, com alta probabilidade, de erro tipográfico (0,023). Note-se ainda que o menor valor de perda alcançado pela BiLSTM (0,022–0,026) é sempre **maior** que o da LSTM (0,010–0,014), o que contradiz, na própria série IBM, a superioridade de RMSE relatada na Tabela II (0,15 vs 0,22) — a menos que a perda de treinamento e o RMSE de teste estejam em escalas distintas (perda sobre dados escalonados, RMSE em unidades originais), o que o artigo não esclarece.

---

## 8. Limitações

### 8.1 Declaradas pelos autores
1. **[declarada]** Séries univariadas; extensão a "séries temporais multivariadas e sazonais" é deixada como trabalho futuro (p. 7).
2. **[declarada]** Dúvida prévia sobre a existência de "contexto" nos dados numéricos que justifique a leitura reversa, ao contrário do que ocorre em texto (p. 6); resolvida apenas empiricamente.
3. **[declarada]** A BiLSTM "atinge o equilíbrio muito mais lentamente" e "precisa buscar mais lotes de dados" (p. 1, 6–7) — custo de treinamento maior.
4. **[declarada]** O caso IXIC.weekly, em que a BiLSTM é pior que a LSTM, é reconhecido, mas não explicado (p. 5).

### 8.2 Identificadas por mim
5. **[minha inferência]** Pseudocódigo inconsistente com o procedimento narrado (§5.3): não há re-treinamento *rolling* no Listing 1, a entrada do preditor coincide com o valor esperado e o alvo de treino é nulo. Sem código-fonte, o experimento não é reprodutível.
6. **[minha inferência]** Hiperparâmetros irrisórios e sem busca: 4 neurônios e 1 época (p. 5), sem tamanho de lote, taxa de aprendizado, janela de entrada ou escalonamento declarados. A comparação LSTM vs BiLSTM pode refletir apenas o dobro de parâmetros da segunda, e não a bidirecionalidade.
7. **[minha inferência]** Uma única execução por série com semente fixa; ausência de intervalos de confiança, replicações e testes de hipótese para sustentar "significativa" (p. 5).
8. **[minha inferência]** Inconsistência de contagem de dados (DJI.daily com 82.205 observações diárias, Tabela I, p. 4), justamente na série com o maior ganho relatado.
9. **[minha inferência]** Agregação de RMSE e de percentuais entre séries de escalas incomensuráveis (p. 6); ausência de métricas relativas (MAPE, MASE) e de *baseline* de persistência, indispensável em séries próximas a passeio aleatório.
10. **[minha inferência]** *Baseline* ARIMA importado de outro artigo [20], sem re-execução nas mesmas condições e sem descrição de ordem (p, d, q).
11. **[minha inferência]** A explicação para o número de lotes (p. 7) não corresponde ao funcionamento do *wrapper* bidirecional; o fenômeno mais provavelmente decorre de configuração experimental distinta.
12. **[minha inferência]** Uso vago de "equilíbrio": a estabilização da perda por lote em uma época única, com 4 neurônios, não caracteriza convergência; e o "aprendizado contínuo" da BiLSTM na 2ª época (p. 7) é igualmente compatível com sobreajuste, não testado.
13. **[minha inferência]** Contradição aparente entre perda mínima de treinamento (BiLSTM sempre maior, Tabela III) e RMSE de teste (BiLSTM menor, Tabela II) para a mesma série IBM, sem esclarecimento de escalas.
14. **[minha inferência]** Para previsão *online* um passo à frente, a BiLSTM só é causal se a janela reversa contiver apenas passado; o artigo não descreve a janela, de modo que não se pode excluir vazamento de informação futura no bloco de teste.
15. **[minha inferência]** Nenhuma consideração de incerteza preditiva, horizonte multi-passo (embora a introdução critique ARIMA justamente pelo longo prazo, p. 1), ou custo computacional em números.

---

## 9. Transferibilidade para o problema-alvo (isolamento de estator de motor de indução MT)

Problema-alvo: isolamento de estator (2,3–13,8 kV) submetido a (a) sobretensões de manobra de VCB — *chopping*, reignições múltiplas, frentes íngremes, dV/dt — com/sem *snubber* tiristorizado (Trabalho A do autor) e (b) estresse térmico de partidas de grandes motores sob contingência N-1 com *load shedding* (Trabalho B).

### 9.1 O que se transfere

| Elemento do artigo | Transferível? | Como, no problema-alvo |
|---|---|---|
| **Equações da célula LSTM** (4)–(9), p. 3, e da RNN (1), p. 2 | Sim, como referência de fundamentação | Servem de fonte citável para a formulação do bloco recorrente de um modelo de tendência de indicador de saúde (HI) do estator — p. ex., magnitude de descargas parciais Q_m (pC), tan δ ou capacitância vs. tensão, resistência de isolamento/índice de polarização, temperatura de enrolamento — desde que amostrado em intervalos regulares. |
| **Protocolo de validação *walk-forward* um passo à frente** com re-treino incremental (p. 5) | Sim, como método de validação | É o protocolo correto para um monitor *online*: cada nova medição do HI entra no treino e o erro é acumulado apenas sobre previsões genuinamente fora da amostra. Deve ser implementado de fato (o Listing 1 não o faz). |
| **RMSE (10) e variação percentual (11)**, p. 4 | Sim, como mínimo | Complementar com métricas relativas (MAPE/MASE), *baseline* de persistência e, para RUL, métricas prognósticas (horizonte prognóstico, α-λ, erro de RUL em horas/partidas/manobras). |
| **Evidência de que BiLSTM converge mais devagar e exige mais dados** (p. 6–7; Tabela III) | Sim, como alerta de projeto | Dados de isolamento de motores MT são escassos (ensaios *offline* semestrais/anuais; poucos eventos *run-to-failure*). O artigo fornece um argumento empírico — ainda que frágil — contra arquiteturas bidirecionais em regime de poucos dados. |
| **Evidência de que a BiLSTM não é uniformemente superior** (IXIC.weekly, +45,03%, p. 6) | Sim, como alerta | Exige validação por ativo/por indicador, e não escolha de arquitetura *a priori*. |
| **Argumento de que modelos regressivos lineares (ARIMA) degradam em horizonte longo** (p. 1–2) | Parcialmente | Motiva modelos não lineares para extrapolar HI até o limiar de falha (horizonte de meses/anos); mas o artigo não testa horizonte multi-passo, então a evidência é indireta. |

### 9.2 O que não se transfere e por quê

1. **Sistema, mecanismo e indicador:** não há componente físico, mecanismo de degradação, indicador de saúde, limiar de falha, RUL ou incerteza. Nada orienta a escolha de precursor do isolamento (PD, tan δ, IR/PI, resposta a surto IEEE 522 [INSERIR CITAÇÃO]) nem sua relação com estresse.
2. **Natureza estatística da série:** preços são próximos de passeio aleatório, sem tendência determinística nem limiar; HIs de isolamento têm tendência (Arrhenius térmica, crescimento de PD por erosão) e limiar. Um modelo validado em séries financeiras não carrega informação sobre extrapolação de tendência de degradação.
3. **Estresse episódico vs. série regular:** as manobras de VCB são eventos de microssegundos (o repositório já modela I_chop ~ N(5 A, 1 A²), di/dt_crit(t) = 16 A/µs + 0,034 A/µs²·(t − t_open), recuperação dielétrica U_dielec(t) = 690 V + 17 V/µs·(t − t_corte) e o contador `reign_count`, em `app/preprocessor/atp_templates/vcb_reignition.mod`; e métricas de TRV/RRRV em `app/analysis/transient_metrics.py`); as partidas N-1 são eventos de segundos, raros e heterogêneos (`app/postprocessor/motor_starting.py` e `motor_reaccel.py` calculam afundamento de tensão, tempo de aceleração e limite de partidas/hora). Nada disso é uma série univariada regular. O que faria sentido — e o artigo não oferece — é (i) um índice de dano acumulado por evento (contagem de surtos ponderada por pico, dV/dt e número de reignições; número de partidas ponderado por I²t ou por excursão térmica) como **covariável** de um modelo sequencial multivariado, ou (ii) um processo de degradação por saltos (gama composto / Poisson marcado). [Proposta minha, não do artigo.]
4. **Bidirecionalidade e causalidade *online*:** a BiLSTM exige a sequência inteira (passado e futuro) da janela de entrada. Para prognóstico *online* e para decisão de despacho/*load shedding* em tempo real, apenas o passado está disponível; a BiLSTM só é admissível para suavização/rotulagem *offline* de históricos ou para detecção de anomalia retrospectiva. O artigo não discute essa restrição.
5. **Multivariabilidade e covariáveis de mitigação:** o efeito do *snubber* tiristorizado (Trabalho A) e do *load shedding* (Trabalho B) sobre a vida do isolamento só pode ser quantificado por um modelo que aceite covariáveis de estresse com/sem mitigação; o artigo é univariado e declara isso como trabalho futuro (p. 7).
6. **Qualidade da evidência:** as inconsistências de pseudocódigo, contagem de dados, agregação de métricas e ausência de replicação (§8) tornam o artigo inadequado como fonte de "resultado" a ser citado; pode ser citado, no máximo, como exemplo de comparação LSTM/BiLSTM na literatura aplicada.
7. **RUL e decisão:** não há conversão de previsão em vida remanescente nem em unidades de negócio (horas, partidas, manobras) — exatamente o que o C-Level demanda.

### 9.3 Nota

**Transferibilidade: 1/5.** Transferem-se apenas elementos genéricos e de domínio público — as equações da LSTM, o protocolo *walk-forward*, o RMSE — e dois alertas empíricos (convergência lenta e não superioridade uniforme da BiLSTM). Não há sistema, mecanismo, indicador, dado de degradação, RUL, incerteza ou tratamento de estresse episódico. A qualidade metodológica (pseudocódigo inconsistente, dados implausíveis, sem replicação) desaconselha citar seus números como evidência. Serve como referência periférica ao justificar por que um monitor de isolamento *online* deve preferir arquiteturas causais e multivariadas com poucos dados.

---

## 10. Citações literais relevantes

1. "It has been reported that artificial Recurrent Neural Networks (RNN) with memory, such as Long Short-Term Memory (LSTM), are superior compared to Autoregressive Integrated Moving Average (ARIMA) with a large margin." (p. 1, Resumo)
2. "These models perform reasonably well for short-term forecasts (i.e., the next lag), but their performance deteriorates severely for long-term predictions." (p. 1, sobre ARIMA/SARIMA/ARIMAX)
3. "In theory, RNNs are able to leverage previous sequential information for arbitrary long sequences. In practice, however, due to RNNs' memory limitations, the length of the sequential information is limited to only a few steps back." (p. 2)
4. "The rolling-based algorithms re-train the models each time a new observation is fetched (line 26). Hence, once a prediction is performed and its value is compared with the actual value, the value is added to the training set (line 26), and the model is re-trained (line 27)." (p. 5)
5. "On average, the RMSE values achieved for LSTM and BiLSTM-based models are 39.09 and 20.17, respectively, and thus achieving (−)%37.78 reduction on average." (p. 5)
6. "However, it was not clear whether training numerical time series data twice and learning from the future as well as past would help in better forecasting of time series, since there might not exist some contexts, as observable in text parsing." (p. 6)
7. "This observation may indicate that the BiLSTM model needs fetching more training data to reach the equilibrium in comparison to its unidirectional version (i.e., LSTM)." (p. 6)
8. "As a result, this paper recommends using BiLSTM instead of LSTM for forecasting problem in time series analysis. This research can be further expanded to forecasting problems for multivariate and seasonal time series." (p. 7)

---

## 11. Ligações com RUL, PHM e C-Level

**RUL / PHM**
- O artigo não usa os termos RUL, PHM, prognóstico, confiabilidade ou manutenção em nenhuma página. [FATO — ausência]
- Sua utilidade no corpus é de **fundamentação de método**: fornece, de forma citável, as equações da LSTM (p. 2–3), a distinção *feed-forward* vs. recorrente (p. 4) e o protocolo *walk-forward* (p. 5). É complementar ao fichamento 08 (Yin, Hu e Cao, 2024), que aplica CNN-BiLSTM-Attention a um indicador real de degradação de IGBT: aquele traz o indicador e o dado; este traz a formulação e uma comparação de arquiteturas. [INFERÊNCIA]
- Ponto de ligação com a taxonomia de PHM (revisões dos fichamentos 01 e 03): pertence ao ramo "orientado a dados / aprendizado profundo sequencial", sem qualquer componente físico ou híbrido. [INFERÊNCIA]
- Diálogo com os Trabalhos A e B do autor: nenhum direto. A ponte possível, proposta minha, é usar as saídas de simulação do repositório (pico de sobretensão, dV/dt, `reign_count` por manobra; afundamento de tensão, tempo de aceleração e contagem de partidas N-1) como covariáveis de estresse de um modelo recorrente **causal** e multivariado — o oposto, em três aspectos, do que o artigo faz (univariado, bidirecional, série regular).

**C-Level (custo, decisão, manutenção)**
- O artigo não apresenta argumento algum de custo, decisão, manutenção ou risco. [FATO — ausência]
- Os únicos enunciados com alguma relevância gerencial são metodológicos: (i) ARIMA "degrada severamente para predições de longo prazo" (p. 1); (ii) modelos de aprendizado são "orientados a dados em vez de orientados a modelo" (p. 1); (iii) a BiLSTM "atinge o equilíbrio muito mais lentamente" (p. 1) e exige "buscar lotes adicionais de dados" (p. 7) — implicando maior custo de treinamento e maior necessidade de dados; (iv) recomendação de usar BiLSTM (p. 7). [FATO]
- [INFERÊNCIA] Para a entrega computacional ao C-Level, o artigo é útil como contraexemplo: um KPI de "redução média de 37,78% do erro" (p. 2, 5, 7) que agrega escalas incomensuráveis, ignora o caso de piora e não vem acompanhado de incerteza ou de tradução em decisão é o tipo de indicador que não sustenta uma recomendação de manutenção. O método do doutorado deve reportar erro em unidades físicas do HI, RUL em horas/partidas/manobras com intervalo de confiança, e o ganho de vida atribuível ao *snubber* e ao *load shedding* como alavancas de decisão.
