# Demanda de C-Level por RUL e manutenção preditiva — pesquisa web multi-fonte

Tema: `c_level_demanda_rul`. Data da coleta: 2026-09-02. Escopo: demanda executiva (CEO/CFO/COO/CTO, diretoria de manutenção/confiabilidade) por RUL (vida útil remanescente) e manutenção preditiva (PdM); adoção 2017–2026; KPIs cobrados; barreiras; tradução de RUL em decisão financeira; custo de parada não programada em petróleo e gás (O&G) e refino; contexto brasileiro. Finalidade: subsidiar o módulo MVP de RUL de isolamento de motores de indução de média tensão (MT, 2,3–13,8 kV) do Olivas Power System Studio e o discurso para C-Level.

Convenções de rótulo (regra "zero suposição"): [FATO: doc A/B, p. N]; [FATO: artigo NN, p. N]; [NORMA: id, cláusula]; [LITERATURA: ref verificada + URL] (relatórios, surveys e artigos acessados na web nesta coleta, com página quando o documento é paginado); [REPO: caminho:linha]; [CÁLCULO PRÓPRIO: fórmula]; [INFERÊNCIA FÍSICA: derivação]; [HIPÓTESE]. Escala de confiança da Tabela 2: **A** = fonte primária acessada, metodologia declarada e amostra conhecida; **M** = fonte primária acessada, mas patrocinada por fornecedor, amostra pequena ou extrapolada, ou reprodução secundária fiel de primária identificada; **B** = apenas fonte secundária, metodologia desconhecida ou números conflitantes entre reproduções. Somente URLs efetivamente acessadas (conteúdo lido) são registradas; tentativas bloqueadas constam no Anexo A.

---

## 1. Síntese executiva

1. A demanda executiva por manutenção preditiva é documentada por surveys de grande amostra: 94 % de 1.600 executivos de 12 países (incluindo o Brasil) planejam expandir o uso de IA industrial, mas só 17 % implementaram plenamente o plano inicial e 48 % precisam "justificar continuamente" recursos [LITERATURA: Honeywell/Wakefield 2024]; 95 % de 1.560 gestores/C-suite investem ou planejam investir em IA/ML [LITERATURA: Rockwell 2025]; 84 % de 304 decisores industriais aumentam orçamento de manutenção [LITERATURA: Verdantix 2025 via MaxGrip 2026]; 67 % dos respondentes de um estudo setorial apontam ferramentas de PdM como a tecnologia emergente mais crítica [LITERATURA: Plant Engineering 2026].
2. O argumento financeiro que sustenta essa demanda é o custo da parada não programada: US$ 1,4 trilhão/ano (11 % da receita) para as 500 maiores empresas, US$ 2,3 milhões/h no setor automotivo, ~US$ 500 mil/h em O&G no biênio 2021–22 e US$ 149 milhões/ano por instalação de O&G [LITERATURA: Siemens/Senseye TCOD 2024, p. 2–8; TCOD 2022, p. 4, 11–12]; US$ 125 mil/h na média de 3.215 decisores de manutenção [LITERATURA: ABB/Sapio 2023]; no Brasil, R$ 106 milhões por dia de refinaria de 250 kb/d parada, com refinarias operando acima de 100 % da capacidade em 2026 [LITERATURA: Times Brasil 2026].
3. A adoção efetiva fica muito atrás do interesse declarado: 11 % das empresas no nível "PdM 4.0" (estável entre 2017 e 2018) [LITERATURA: PwC/Mainnovation 2018, p. 3, 8]; 27 % de adoção de PdM em 2025, contra 30 % em 2024, entre 1.320 profissionais de manutenção (EUA/Canadá) [LITERATURA: MaintainX 2025]; apenas 7 % têm IA embutida na maioria dos processos centrais [LITERATURA: IIoT World 2026].
4. Os KPIs que o C-Level cobra são consistentes entre fontes: disponibilidade/uptime (objetivo primário para 51 % em PwC), custo de manutenção, riscos SHEQ, extensão de vida do ativo, OEE, horas e incidentes de parada, MTTR, e — na camada financeira — ROI, payback e custo evitado versus caixa realizado [LITERATURA: PwC 2018, p. 9–10; TCOD 2024, p. 3, 10–11; IIoT World 2026; Tractian 2026]. A norma EN 15341:2019 padroniza o conjunto de KPIs de manutenção [NORMA: EN 15341:2019].
5. As barreiras dominantes são orçamento/ausência de business case (63 % dos que não planejam PdM 4.0 não conseguem montar o business case; budget é fator crítico para 60 %), dados (67 %), competências, cibersegurança/integração OT-TI e confiança/explicabilidade (43 % citam trust/explainability/transparência; 37 % dos executivos consideram que o próprio C-suite não entende IA) [LITERATURA: PwC 2018, p. 8–9; MaintainX 2025; IIoT World 2026; Honeywell 2024]. No Brasil, 66 % das indústrias apontam custo como principal barreira e 25 % citam dificuldade de perceber retorno; altos executivos tratam Indústria 4.0 como "modismo" e preferem projetos de benefício mais simples de avaliar [LITERATURA: CNI 2022; CNI 2020, p. 11].
6. A tradução de RUL em decisão financeira tem base metodológica publicada: ROI/custo de ciclo de vida de PHM com incerteza explícita [LITERATURA: Feldman, Jazouli e Sandborn 2009; Sandborn e Wilkinson 2007]; análise custo-benefício por simulação com erros prognósticos, em que o ganho de VPL (até US$ 5,6 milhões por aeronave) é o teto do custo aceitável do sistema PHM e taxas altas de falso alarme geram deterioração econômica [LITERATURA: Hölzel e Gollnick 2015, p. 10–14]; integração de RUL a modelo de substituição por blocos com reparo mínimo [LITERATURA: Choo e Shin 2025]; otimização estocástica com intervalos de confiança de RUL [LITERATURA: Käslin et al. 2026]; valor da informação (VoI) de monitoramento [LITERATURA: Nielsen 2021].
7. O canal de seguro existe, mas com evidência restrita: a Munich Re oferece garantia de desempenho lastreada em seguro para soluções de PdM/monitoramento de condição [LITERATURA: Munich Re IoT Cover] e a HSB reporta ROI médio de 506 % em clientes IoT [LITERATURA: HSB 2022]; não foi localizada fonte primária que quantifique redução de prêmio por RUL de motores.
8. Limites de evidência: os números de custo mais citados vêm de relatórios patrocinados por fornecedores (Siemens/Senseye: 181 entrevistas em 4 anos, extrapoladas para a Fortune Global 500; ABB; MaintainX; GE/Kimberlite) e as reproduções secundárias divergem entre si (US$ 38 mi, 49 mi, 58–59 mi para O&G offshore). As faixas "30–50 % menos parada, 20–40 % mais vida" atribuídas à McKinsey não puderam ser verificadas na fonte primária nesta coleta [INSERIR CITAÇÃO].
9. Implicação central para o Olivas: o módulo de RUL só será "cobrável" pelo C-Level se (i) entregar RUL como distribuição com horizonte de decisão, (ii) converter RUL em custo esperado evitado com custo de parada e MTTR parametrizáveis, (iii) contabilizar custo de falso alarme e (iv) expor a cadeia de evidência (dados → indicador → modelo → decisão), o que responde diretamente às barreiras de business case, confiança e explicabilidade documentadas.

---

## 2. Tabela de fatos verificados

| # | Fato | Fonte (URL acessada) | Ano | Conf. |
|---|------|----------------------|-----|-------|
| 1 | Parada não programada custa às 500 maiores empresas do mundo ~US$ 1,4 trilhão/ano, 11 % da receita; planta grande média perde US$ 253 mi/ano | Siemens/Senseye, *The True Cost of Downtime 2024*, p. 2–3, 8 — https://assets.new.siemens.com/siemens/assets/api/uuid:1b43afb5-2d07-47f7-9eb7-893fe7d0bc59/TCOD-2024_original.pdf | 2024 | M |
| 2 | Custo de uma hora de parada: US$ 2,3 mi (automotivo), US$ 36 mil (FMCG); planta de indústria pesada perde US$ 59 mi/ano (1,6× 2019); em O&G o custo/hora acompanha o preço do petróleo (recorde em 2022, queda em 2023) | idem, p. 2–6 | 2024 | M |
| 3 | 25 incidentes/mês por planta (42 em 2019); 27 h/mês (39 em 2019); 326 h/ano; tempo de retomada subiu de 49 para 81 min | idem, p. 3, 10–11 | 2024 | M |
| 4 | Quase metade das empresas tem equipe dedicada de PdM (2× 2019); 87 % coletam dados que viabilizam PdM; PdM deixou de ser "prioridade estratégica" por ter virado rotina | idem, p. 3, 12–13 | 2024 | M |
| 5 | Clientes Senseye: −50 % parada não programada, −40 % custo de manutenção, +55 % produtividade da equipe, +85 % acurácia de previsão; retorno em 3 meses; extrapolação FG500: 2,1 mi h/ano, US$ 388 bi (+5 % produtividade), US$ 233 bi (−40 % custo) | idem, p. 3, 14 | 2024 | B (dados de implantações do fornecedor) |
| 6 | Metodologia: 181 entrevistas on-line (abr/2019–mar/2023) com profissionais de manutenção, engenharia e TI de grandes organizações em automotivo, FMCG, indústria pesada e O&G; extrapolação por número de plantas/empregados | idem, p. 15 | 2024 | A (para a metodologia) |
| 7 | O&G: custo de uma hora de parada "mais que dobrou em dois anos, para quase US$ 500.000"; custo anual por instalação de O&G subiu 76 % para US$ 149 mi; FG500: ~US$ 1,5 tri, 11 % da receita (8 % em 2019–20); US$ 129 mi/instalação | Siemens/Senseye, *TCOD 2022*, p. 4, 11–12 — https://assets.new.siemens.com/siemens/assets/api/uuid:3d606495-dbe0-43e4-80b1-d04e27ada920/dics-b10153-00-7600truecostofdowntime2022-144.pdf | 2023 | M |
| 8 | 7 em 10 empresas veem PdM como prioridade estratégica; 1/3 tem equipe dedicada; equipes de PdM no automotivo subiram de 11 % para 38 %; OEE de 60 vs 29 onde PdM é prioridade; payback em 3–6 meses; refinarias FG500 poderiam recuperar 72 mil h/ano (US$ 33 bi); amostra: 56 entrevistas (jan/2021–ago/2022); autores admitem que a amostra "pode inflar levemente" a prevalência | idem, p. 11, 15, 20–21 | 2023 | M |
| 9 | Parada não programada custa ~US$ 125 mil/h; mais de dois terços sofrem paradas ao menos mensalmente; 21 % ainda operam em run-to-fail; 92 % dizem que manutenção elevou o uptime; 60 % planejam aumentar investimento em confiabilidade em 3 anos; 90 % interessados em contratos por resultado; 3.215 decisores de manutenção (Sapio Research, jul/2023), setores incl. O&G e químico | ABB, *Value of Reliability* (press release via Reliabilityweb) — https://reliabilityweb.com/en/press-release/abb-survey-reveals-unplanned-downtime-costs-125000-per-hour | 2023 | M (fornecedor; amostra grande) |
| 10 | Parada não programada custa aos fabricantes industriais ~US$ 50 bi/ano; má estratégia de manutenção reduz capacidade produtiva em 5–20 %; PdM reduz tempo de planejamento em 20–50 %, eleva uptime em 10–20 % e reduz custo total de manutenção em 5–10 %; piloto químico: −80 % parada não programada e ~US$ 300 mil/ativo | Deloitte Insights, *Industry 4.0 and predictive technologies for asset maintenance* — https://www.deloitte.com/us/en/insights/industry/manufacturing-industrial-products/industry-4-0/using-predictive-technologies-for-asset-maintenance.html | 2017 | M (fontes internas não detalhadas) |
| 11 | 268 empresas (BE/DE/NL): 11 % no nível 4 (PdM 4.0), estável vs 2017; distribuição 2018: sem PdM 2 %, N1 25 %, N2 42 %, N3 20 %, N4 11 %; 60 % têm planos/intenções (49 % em 2017); dos 40 % sem planos, 63 % não conseguem montar business case, 23 % não têm dados, 8 % não têm capacidade analítica | PwC/Mainnovation, *PdM 4.0: Beyond the hype*, p. 3, 8 — https://www.mainnovation.com/wp-content/uploads/tmp/6397245268d8d3711c88cda0b4585ab02e612f2e.pdf | 2018 | A |
| 12 | Fatores críticos de sucesso: disponibilidade de dados 67 %, orçamento 60 %; objetivo principal: uptime 51 %, satisfação do cliente 12 %, custo 11 %, SHEQ 8 %, extensão de vida 7 %; "em vários casos foi o departamento de TI, não o conselho, que freou o projeto" | idem, p. 9 | 2018 | A |
| 13 | Entre 67 empresas implementando PdM 4.0: 95 % reportam resultados; uptime 60 % (média +9 %, até 25–30 %), custo 45 % (média −12 %), SHEQ 52 % (−14 %), extensão de vida 46 % (+20 %); resultados provavelmente em equipamentos isolados/pilotos ("low hanging fruit") | idem, p. 10 | 2018 | A |
| 14 | 1.320 profissionais (EUA/Canadá): adoção de PdM 27 % em 2025 (30 % em 2024); 32 % implementaram IA total/parcialmente; 65 % esperam IA até 2026; 74 % reportam parada igual ou menor; 31 % reportam custo de parada maior; barreiras à IA: orçamento 25 %, expertise 24 %, cibersegurança 22 %; 71 % têm preventiva como estratégia principal, mas 58 % gastam mais da metade do tempo reagindo; idade média dos equipamentos 24 anos | MaintainX, *2025 State of Industrial Maintenance* — https://www.getmaintainx.com/newsroom/state-of-industrial-maintenance-report-2025 ; https://www.getmaintainx.com/blog/maintenance-stats-trends-and-insights ; https://www.qualitydigest.com/inside/research-tech-article/state-industrial-maintenance-2025-maintainx-survey-061125.html | 2025 | M (fornecedor de CMMS) |
| 15 | 1.600 executivos, 12 mercados (incl. Brasil), Wakefield Research (abr–mai/2024): 94 % planejam expandir IA; 17 % implementaram plenamente; 37 % dizem que o C-suite não entende como a IA funciona; 48 % precisam justificar recursos continuamente; benefícios esperados: eficiência 64 %, cibersegurança 60 %, decisão em tempo real 59 %, segurança 39 % | Honeywell, *Industrial AI Insights* — https://www.honeywell.com/us/en/news/press-releases/2024/07/industrial-ai-uptake-is-just-getting-started-but-majority-of-sector-is-uncovering-new-use-cases-finds-honeywell-research | 2024 | M |
| 16 | 1.560 respondentes (gerência a C-suite, 17 países, mar/2025): 95 % investem/planejam investir em IA/ML em 5 anos; qualidade é o caso de uso líder (50 %); cibersegurança 49 %; capacidade de aplicar IA tornou-se competência "extremamente importante" para quase metade (10 % no ano anterior) | Rockwell Automation, *State of Smart Manufacturing 2025* — https://www.rockwellautomation.com/en-us/company/news/press-releases/Ninety-Five-Percent-of-Manufacturers-Are-Investing-in-AI-to-Navigate-Uncertainty-and-Accelerate-Smart-Manufacturing.html | 2025 | M |
| 17 | >1.800 executivos: só 25 % geram valor significativo com IA; regra 10-20-70 (algoritmos/dados/pessoas-processos); "a maioria das empresas não acompanha KPIs financeiros de suas iniciativas de IA" | BCG, *AI Radar 2025* — https://www.bcg.com/publications/2025/closing-the-ai-impact-gap | 2025 | A |
| 18 | 197 executivos (3T/2025): 80 % dos casos de IA generativa atenderam expectativas, mas só 23 % conseguem vincular a receita/custo; 33 % dos insatisfeitos dizem que funcionou no piloto e não escalou | Bain, *Executive Survey: AI Moves from Pilots to Production* — https://www.bain.com/insights/executive-survey-ai-moves-from-pilots-to-production/ | 2025 | A (não específico de PdM) |
| 19 | 550 líderes (abr–mai/2025): organizações em que o CFO tem autoridade plena sobre investimento digital atingem lucratividade acima da média em 42 % dos casos vs 18 % sem autoridade do CFO | Deloitte Insights, *C-suite leadership and AI returns* — https://www.deloitte.com/us/en/insights/topics/digital-transformation/c-suite-leadership-ai-returns.html | 2025 | A |
| 20 | 272 profissionais industriais: 64 % usam/planejam IA para PdM; barreiras: qualidade/disponibilidade de dados 54 %, integração de legado e silos 48 %, confiança/explicabilidade/transparência 43 %; só 34 % têm streaming de dados em tempo real; 7 % têm IA embutida nos processos centrais (44 % em 3 anos); resultados esperados: menos parada 53 %, melhor OEE 52 % | IIoT World, *Industrial AI Readiness Report 2026* — https://www.iiot-world.com/industrial-iot/connected-industry/industrial-ai-readiness-report-2026/ ; https://www.iiot-world.com/artificial-intelligence-ml/industrial-data-and-ai-readiness-survey-2027/ | 2026 | M (amostra autosselecionada) |
| 21 | Survey de serviços de O&M industrial: 125 respondentes (87 % com receita > US$ 1 bi, 11 setores, 8 regiões); 60 % planejam aumentar gasto em 2025–26; foco em manutenção de ativos e IA industrial | Verdantix, *Global Corporate Survey 2025: Industrial Operations And Maintenance Services* — https://www.verdantix.com/venture/report/global-corporate-survey-2025-industrial-operations-and-maintenance-services-budgets-priorities-and-tech-preferences | 2025 | M (só sumário público) |
| 22 | Survey de transformação industrial Verdantix 2025 (304 decisores): 84 % aumentam orçamento de manutenção; 86 % esperam melhorias significativas com insights baseados em IA | MaxGrip, *Game changers in APM — Verdantix 2025 survey* — https://www.maxgrip.com/resource/verdantix-survey-2025-game-changers-in-asset-performance-management/ | 2026 | B (secundária) |
| 23 | *2026 State of Manufacturing Operations & Maintenance*: 67 % apontam ferramentas de PdM como tecnologia emergente mais crítica; 49 % apps móveis (+16 pp); 31 % otimização de manutenção por IA | Plant Engineering — https://www.plantengineering.com/how-data-is-unlocking-big-gains-for-manufacturers/ | 2026 | B (amostra não informada) |
| 24 | O&G (UKCS, McKinsey 2014 citado): falhas de planta e paradas não programadas ≈ 50 % das perdas; paradas planejadas ≈ 25 %; custos de O&M cresceram 10 %/ano por 10 anos; Kimberlite/GE 2016: estratégias reativa 30 %, planejada 46 %, preditiva 24 % dos operadores, com parada não programada de 8,43 %, 7,97 % e 5,42 %; impacto financeiro US$ 58–59 mi (reativa/planejada) vs US$ 24 mi (preditiva) | Moir, Niculita e Milligan, PHME 2018, p. 2–3 — http://www.papers.phmsociety.org/index.php/phme/article/download/396/phmec_18_396 | 2018 | M (reprodução acadêmica de estudo patrocinado) |
| 25 | Kimberlite/GE (50 operadores, 2016): US$ 38 mi/ano de perdas médias offshore, US$ 88 mi nos piores; 27 dias/ano; 1 % de parada (3,65 dias) > US$ 5 mi; PdM orientada a dados reduz parada em até 36 %; <24 % usam abordagem preditiva | MaxGrip — https://www.maxgrip.com/resource/article-the-cost-of-unplanned-downtime/ ; Dispel — https://dispel.com/blog/how-digital-transformation-can-reduce-unplanned-downtime-in-the-oil-gas-industry | 2016 (est.) | B (whitepaper original não acessado) |
| 26 | 450 decisores (UK/US/FR/DE, incl. O&G): 82 % tiveram parada não programada em 3 anos; duração média 4 h; custo US$ 260 mil/h (Aberdeen 2016); 72 % têm "zero parada não programada" como prioridade máxima; 60 % tratam transformação digital como prioridade de conselho | The Manufacturer (Vanson Bourne/ServiceMax) — https://www.themanufacturer.com/articles/unplanned-downtime-affecting-82-businesses/ | 2017 | B |
| 27 | ARC Advisory Group: ~5 % da produção das indústrias de processo (US$ 20 bi/ano) perde-se em parada não programada | ABB Review 3/2007, p. 15 — https://library.e.abb.com/public/40de92d2e8c26aa48325734b00405276/15-17%203M765_ENG72dpi.pdf | 2007 | B (citação indireta, dado antigo) |
| 28 | Refinaria BP Whiting (435 mil b/d) parou por falta de energia em 1/2/2024 e poderia ficar semanas fora; gasolina no Meio-Oeste +13 c/gal e diesel +30 c/gal em uma semana | EIA, *Today in Energy* — https://www.eia.gov/todayinenergy/detail.php?id=61403 | 2024 | A |
| 29 | Refinaria média (250 mil b/d, Brent US$ 78,55): 3 dias de parada ≈ US$ 58,9 mi; 1 dia ≈ US$ 19,64 mi ≈ R$ 106 mi; fator de utilização Petrobras 95 % (1T/2026), 97,4 % (mar/2026), >100 % (abr–mai/2026); cálculo do próprio veículo | Times Brasil/CNBC — https://timesbrasil.com.br/empresas-e-negocios/combustiveis/refinarias-acima-da-capacidade-custo-paradas-manutencao/ | 2026 | M (cálculo jornalístico com premissas explícitas) |
| 30 | Parada programada da RPBC (178 mil b/d): R$ 500 mi, ~70 dias, unidade de destilação de 5.200 m³/dia; sem impacto no abastecimento por planejamento de estoques | Agência Petrobras — https://agencia.petrobras.com.br/w/negocio/petrobras-investe-r-500-milhoes-na-parada-programada-de-manutencao-da-refinaria-presidente-bernardes-de-cubatao-rpbc- | 2024 | A |
| 31 | Reduc (~240 mil b/d) ficou paralisada ~13 dias a partir de 31/8/2016 após "falha no fornecimento de energia externo da unidade" | Investing.com/Reuters — https://br.investing.com/news/stock-market-news/refinaria-da-petrobras-reduc-opera-normalmente-apos-parada-nao-programada-202801 | 2016 | A |
| 32 | Sondagem CNI (>1.000 empresas): 69 % das indústrias usam ≥1 tecnologia digital (48 % em 2016); sensores para controle de processo 46 % (27 %); sensores para identificação de produtos/condições operacionais 27 % (8 %); barreiras: custo 66 %, falta de conhecimento 25 %, dificuldade de perceber retorno 25 % | CNI/Agência de Notícias da Indústria — https://noticias.portaldaindustria.com.br/noticias/inovacao-e-tecnologia/industria-40-69-das-industrias-brasileiras-fazem-uso-de-tecnologia-digital-no-brasil/ | 2022 | A |
| 33 | 24 entrevistas com gerentes/diretores (2019): "diversas empresas encontram dificuldades junto aos altos executivos para aprovação de projetos"; executivos julgam Indústria 4.0 "apenas modismo" ou priorizam projetos "cuja avaliação dos benefícios é mais simples"; motivações: redução de custo e produtividade | CNI, *A difusão das tecnologias da Indústria 4.0 em empresas brasileiras*, p. 10–11 — https://static.portaldaindustria.com.br/media/filer_public/c4/26/c42635b7-c3c0-4763-8ed2-69aa33b8a07e/a_difusao_das_tecnologias_da_industria_40_vf.pdf | 2020 | A (qualitativo) |
| 34 | Documento Nacional ABRAMAN: pesquisa bienal, edição 2024 disponível a associados, grau de confiança estatística de 95 %; indicadores numéricos não acessíveis publicamente | ABRAMAN — https://abramanoficial.org.br/publicacoes/documento-nacional | 2024 | B (conteúdo restrito) |
| 35 | ROI de PHM: "acomodar as incertezas no cálculo de ROI de PHM está no cerne do desenvolvimento de business cases realistas"; valor de PHM = aviso antecipado, disponibilidade, menor custo de ciclo de vida (inspeção, parada, estoque, NFF) | Sandborn, página de pesquisa PHM/CALCE — https://terpconnect.umd.edu/~sandborn/research/PHM.html ; metadados: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/TR.2009.2020133?fields=title,year,abstract,venue,authors,citationCount,externalIds ; https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.microrel.2007.02.016?fields=title,year,abstract,venue,authors,citationCount,externalIds | 2007–2009 | A |
| 36 | CBA de PHM/CBM por simulação (aeronave, r = 8 %): eventos não programados caem de 5.400 para 4.250 com PHM perfeito; até −420 atrasos; ganho máximo de VPL US$ 5,6 mi por aeronave, que "é ao mesmo tempo o limite superior do custo de aquisição" do sistema; "taxas altas de falso alarme podem causar deterioração econômica" vs referência | Hölzel e Gollnick, PHM Society 2015, p. 10–14 — https://elib.dlr.de/100435/1/phmc_15_050.pdf | 2015 | A |
| 37 | RUL (ML) integrada a Weibull e substituição por blocos com reparo mínimo para decidir o instante ótimo de troca (caso CMAPSS) | Choo e Shin, IJPHM 16(1) — http://papers.phmsociety.org/index.php/ijphm/article/view/4242 | 2025 | A |
| 38 | Programação estocástica (MILP) com intervalos de confiança de RUL reduz custo de disrupção e cancelamentos, "à custa de aumentos moderados no custo de planejamento" | Käslin et al., arXiv 2608.22569 — https://arxiv.org/abs/2608.22569 | 2026 | A (preprint) |
| 39 | Valor da informação de monitoramento: ignorar dependência temporal das observações leva a custos "muito maiores que o esperado"; modelagem correta reduz custos "até um quarto" | Nielsen, *Structural Health Monitoring* — https://api.semanticscholar.org/graph/v1/paper/DOI:10.1177/14759217211030605?fields=title,year,abstract,venue,authors,externalIds | 2021 | A |
| 40 | XAI em PdM: "operadores humanos precisam confiar no sistema preditivo" em aplicações críticas; XAI "amplifica a confiança" mantendo desempenho | Cummins et al., arXiv 2401.07871 — https://arxiv.org/abs/2401.07871 | 2024 | A |
| 41 | Barreiras à IA na manufatura: natureza "caixa-preta", rastreabilidade das decisões, GDPR vs opacidade, dados pobres/enviesados, integração de legados, resistência organizacional e "apoio insuficiente da liderança" | Ahangar, Farhat e Sivanathan, *Sensors* 25(14):4357 — https://pmc.ncbi.nlm.nih.gov/articles/PMC12298069/ | 2025 | A (revisão, sem percentuais) |
| 42 | Engenheiros de processo "contornam ou reverificam IA que não mostra o trabalho", exigindo linha direta a variáveis de processo, historiador e registros de manutenção | Seeq/Control Global — https://www.controlglobal.com/control/ai-ml/article/55401808/seeq-how-to-earn-industrial-ai-trust | 2026 | B (opinião de fornecedor) |
| 43 | HSB (Munich Re): 10 maiores clientes IoT tiveram ROI médio de 506 % em 2021; ~30 bi leituras de sensores; >270 mil alertas; sem menção a redução de prêmio | HSB — https://www.munichre.com/hsb/en/press-and-publications/press-releases/2022/2022-03-29-hsb-iot-clients-gain-500-percent-roi.html | 2022 | M |
| 44 | Munich Re *IoT Cover*: garantia de disponibilidade/desempenho lastreada em seguro para soluções de PdM, análise de qualidade e monitoramento de condição; sem valores públicos | Munich Re — https://www.munichre.com/en/solutions/for-industry-clients/iot-cover.html | s.d. | M |
| 45 | FM: 427 sinistros em geração de energia (2021–2025), US$ 3,7 bi; quebras mecânicas/elétricas > 70 % dos eventos e > 80 % do impacto financeiro; transformadores pesam em interrupção de negócios; prazos de reposição de anos | IT Brief (FM) — https://itbrief.com.au/story/fm-warns-of-rising-risks-to-power-generation-assets | 2026 | B (secundária) |
| 46 | EN 15341:2019 lista KPIs da função manutenção (eficácia, eficiência, sustentabilidade) para ativos industriais; substitui EN 15341:2007 | BSI — https://knowledge.bsigroup.com/products/maintenance-maintenance-key-performance-indicators | 2019 | A (página da norma) |
| 47 | Caso GE Vernova (O&G, África): alerta de vibração em turbina evitou parada; custo evitado US$ 261.680 ("baseado na perda de produção média norte-americana") | GE Vernova — https://www.gevernova.com/software/blog/ai-prevents-gas-turbine-downtime-african-oil-gas-site | 2025 | B (caso de fornecedor) |
| 48 | Guia para CFO (fornecedor): abrir o business case com o custo da parada do último ano; payback típico 6–18 meses; VPL em 3 anos à taxa de corte; separar custo evitado de caixa realizado | Tractian — https://tractian.com/en/blog/the-cfos-guide-to-funding-a-predictive-maintenance-program | 2026 | B |
| 49 | Benchmarks devem ser tratados como "ponto de partida de conversa"; erros comuns: confundir parada de TI com parada de produção, misturar perdas anuais com horárias | ReliaMag — https://reliamag.com/guides/industrial-downtime-cost-benchmarks/ | 2026 | B |

---

## 3. Números-chave

### 3.1 Custo de parada não programada

- Global, grandes empresas: US$ 1,4 tri/ano, 11 % da receita; US$ 253 mi/ano por planta grande; 326 h/ano perdidas [LITERATURA: Siemens TCOD 2024, p. 3, 10]. Em 2022: US$ 1,5 tri, US$ 129 mi/instalação [LITERATURA: TCOD 2022, p. 4, 12].
- Por hora: US$ 2,3 mi (automotivo), US$ 36 mil (FMCG) [TCOD 2024, p. 2]; ≈ US$ 500 mil (O&G, 2021–22) [TCOD 2022, p. 4]; US$ 125 mil (média de 3.215 decisores, 2023) [ABB 2023]; US$ 260 mil (Aberdeen 2016, citado) [The Manufacturer 2017; primária não acessada — INSERIR CITAÇÃO].
- O&G por instalação: US$ 149 mi/ano (2021–22, +76 %) [TCOD 2022, p. 11–12]; offshore: US$ 38 mi/ano (média) a US$ 88 mi (piores), 27 dias/ano; 1 % (3,65 dias) > US$ 5 mi [MaxGrip; Dispel — B]; UKCS: falhas e paradas não programadas ≈ 50 % das perdas [Moir et al. 2018, p. 2, citando McKinsey 2014].
- Refino: 1 dia de refinaria de 250 kb/d ≈ US$ 19,6 mi ≈ R$ 106 mi (Brent US$ 78,55) [Times Brasil 2026]; parada programada de 70 dias na RPBC custa R$ 500 mi [Agência Petrobras 2024]; parada não programada por falha de energia externa manteve a Reduc (~240 kb/d) parada ~13 dias [Reuters/Investing 2016]; parada da BP Whiting (435 kb/d) por falta de energia com efeito de +13 c/gal na gasolina regional em uma semana [EIA 2024].
- Indústria de processo: ~5 % da produção, US$ 20 bi/ano (ARC, dado de 2006–2007) [ABB Review 2007, p. 15 — B].
- Componente elétrico: em geração de energia, quebras mecânicas/elétricas respondem por > 70 % dos sinistros e > 80 % do impacto financeiro (2021–2025) [FM via IT Brief 2026 — B].

### 3.2 Adoção (2017–2026)

| Indicador | Valor | Fonte |
|---|---|---|
| Empresas no nível PdM 4.0 (BE/DE/NL) | 11 % (2017 e 2018) | PwC 2018, p. 3, 8 |
| Planos/intenção de PdM 4.0 | 49 % → 60 % (2017 → 2018) | PwC 2018, p. 3 |
| Equipe dedicada de PdM (grandes empresas) | 1/3 (2022); "quase metade" (2024), 2× 2019 | TCOD 2022, p. 15; TCOD 2024, p. 3 |
| Coletam dados que viabilizam PdM | 87 % | TCOD 2024, p. 13 |
| Adoção de PdM (EUA/Canadá) | 30 % (2024) → 27 % (2025) | MaintainX 2025 |
| IA implementada total/parcial em manutenção | 32 % (2025); 65 % esperam até 2026 | MaintainX 2025 |
| Usam/planejam IA para PdM | 64 % | IIoT World 2026 |
| IA embutida na maioria dos processos centrais | 7 % (44 % em 3 anos) | IIoT World 2026 |
| Planos de IA industrial plenamente implementados | 17 % | Honeywell 2024 |
| Investem/planejam IA/ML (5 anos) | 95 % | Rockwell 2025 |
| Operadores O&G offshore com abordagem preditiva | 24 % (2016) | Moir et al. 2018, p. 3 |
| Indústrias brasileiras com ≥1 tecnologia digital | 48 % (2016) → 69 % (2021) | CNI 2022 |
| Sensores para condições operacionais (Brasil) | 8 % → 27 % | CNI 2022 |

### 3.3 Benefícios reportados (faixas)

- Uptime: +10–20 % [Deloitte 2017]; média +9 %, até +25–30 % [PwC 2018, p. 10]; 92 % relatam aumento, 38 % ≥ 25 % [ABB 2023].
- Custo de manutenção: −5–10 % [Deloitte 2017]; média −12 % [PwC 2018, p. 10]; −40 % (clientes Senseye) [TCOD 2024, p. 14 — B].
- Parada não programada: −50 % (clientes Senseye) [TCOD 2024, p. 14 — B]; −80 % em piloto químico [Deloitte 2017]; −36 % (O&G offshore, preditiva vs reativa) [MaxGrip/Dispel — B]; 5,42 % vs 8,43 % de parada não programada (preditiva vs reativa) [Moir et al. 2018, p. 3].
- Extensão de vida do ativo: média +20 % [PwC 2018, p. 10]. A faixa "+20–40 % de vida, −30–50 % de parada" atribuída à McKinsey não foi verificada na fonte primária (HTTP 503) [INSERIR CITAÇÃO].
- Payback: 3 meses [TCOD 2024, p. 14 — B]; 3–6 meses [TCOD 2022, p. 15 — B]; 6–18 meses (guia de fornecedor) [Tractian 2026 — B]; ROI 506 % (IoT/seguro) [HSB 2022 — M].

### 3.4 KPIs cobrados pelo C-Level (consolidação)

- Operacionais: disponibilidade/uptime (objetivo primário de 51 %) [PwC 2018, p. 9]; horas e incidentes de parada por mês, tempo de retomada (MTTR) [TCOD 2024, p. 10–11]; OEE (60 vs 29) [TCOD 2022, p. 15]; parada reduzida (53 %) e OEE (52 %) como resultados esperados de IA [IIoT World 2026]; OTIF para fornecedores [TCOD 2024, p. 7].
- Financeiros: custo de manutenção (−12 % médio) [PwC 2018, p. 10]; custo da última parada como número de abertura, payback, VPL a 3 anos, custo evitado separado de caixa realizado [Tractian 2026 — B]; ausência de rastreio de KPIs financeiros de IA é a regra [BCG 2025]; CFO com autoridade sobre investimento digital correlaciona com lucratividade (42 % vs 18 %) [Deloitte 2025].
- Risco/segurança/ESG: redução de riscos SHEQ (52 % obtêm, média −14 %) [PwC 2018, p. 10]; segurança do trabalho (39 %) [Honeywell 2024]; energia/emissões (36 % obtêm economia de energia) [PwC 2018, p. 10]; redução de peças de reposição até 40 % e de consumo de energia [TCOD 2024, p. 14 — B].
- Normativo: EN 15341:2019 (KPIs de manutenção — econômicos, técnicos, organizacionais) [NORMA: EN 15341:2019, escopo]; ISO 55000:2024 (valor e risco para partes interessadas) [NORMA: ISO 55000:2024 — página da ISO não acessada nesta coleta, HTTP 403].

### 3.5 Barreiras

| Barreira | Evidência |
|---|---|
| Business case/orçamento | 63 % dos sem-plano não montam business case; budget 60 % como fator crítico [PwC 2018, p. 8–9]; orçamento 25 % [MaintainX 2025]; custo 66 % [CNI 2022]; 48 % justificam recursos continuamente [Honeywell 2024] |
| Dados/integração OT-TI | dados 67 % (fator crítico) e 23 % (sem dados) [PwC 2018, p. 8–9]; qualidade 54 %, legado/silos 48 %, só 34 % com streaming em tempo real [IIoT World 2026]; ~3/4 ainda dependem de historiadores [TCOD 2024, p. 13]; "foi o departamento de TI que freou" [PwC 2018, p. 9] |
| Competências | expertise 24 % [MaintainX 2025]; só 18 % têm cientistas de dados na manutenção [PwC 2018, p. 11]; MTTR subiu por perda de mão de obra qualificada [TCOD 2024, p. 11] |
| Cibersegurança | 22 % [MaintainX 2025]; segurança de dados crescente [PwC 2018, p. 9] |
| Confiança/caixa-preta/XAI | 43 % [IIoT World 2026]; 37 % dizem que o C-suite não entende IA [Honeywell 2024]; opacidade e rastreabilidade [Ahangar et al. 2025]; necessidade de "mostrar o trabalho" [Seeq 2026 — B]; XAI como amplificador de confiança [Cummins et al. 2024] |
| Cultura/liderança | "softer side" — gestão de mudança, decisão orientada a dados [PwC 2018, p. 9]; resistência organizacional e apoio insuficiente da liderança [Ahangar et al. 2025]; executivos veem I4.0 como "modismo" [CNI 2020, p. 11]; 70 % do esforço em pessoas/processos [BCG 2025] |
| Escala (pilot purgatory) | 33 % dos insatisfeitos: funcionou no piloto, não escalou [Bain 2025]; resultados de PdM 4.0 provavelmente em equipamentos isolados [PwC 2018, p. 10] |

### 3.6 Tradução de RUL em decisão financeira (métodos publicados)

- ROI de PHM com incerteza (simulação estocástica de custo de ciclo de vida; "point estimates" não representam business cases) [LITERATURA: Feldman, Jazouli e Sandborn 2009; Sandborn e Wilkinson 2007; Sandborn/CALCE].
- CBA por simulação de eventos discretos com erros prognósticos: o ganho de VPL fixa o teto do custo do sistema PHM; falso alarme alto destrói valor [LITERATURA: Hölzel e Gollnick 2015, p. 10–14].
- RUL → política de substituição por blocos com reparo mínimo (Weibull) [LITERATURA: Choo e Shin 2025].
- RUL com intervalo de confiança → programação estocástica (custo de planejamento vs custo de disrupção) [LITERATURA: Käslin et al. 2026].
- Valor da informação do monitoramento, com dependência temporal das observações [LITERATURA: Nielsen 2021].
- Prática de mercado: abrir com custo de parada do último ano; payback e VPL; custo evitado ≠ caixa [LITERATURA: Tractian 2026 — B].

### 3.7 Seguro

- Garantia de desempenho lastreada em seguro para soluções de PdM/monitoramento de condição (Munich Re IoT Cover) [M]; ROI de 506 % em programa IoT de seguradora (HSB) [M]; quebras elétricas/mecânicas dominam sinistros em geração de energia (FM) [B]. Nenhuma fonte primária acessada quantifica redução de prêmio condicionada a RUL de motores — [INSERIR CITAÇÃO] se o argumento for usado.

---

## 4. Controvérsias e limites de evidência

1. **Patrocínio e amostra.** Os números mais repetidos vêm de fornecedores: Siemens/Senseye (181 entrevistas em 4 anos; 56 em 2021–22; extrapolação para a Fortune Global 500 por número de plantas/empregados; benefícios de "clientes Senseye") [TCOD 2024, p. 15; TCOD 2022, p. 21]; ABB (Sapio, mas encomenda de fornecedor de serviços); MaintainX (CMMS); GE/Kimberlite (fornecedor digital); Tractian; GE Vernova. Os próprios autores do TCOD 2022 reconhecem que a amostra "pode inflar levemente a prevalência" de PdM [TCOD 2022, p. 15] e o TCOD 2024 avisa que resultados combinados entre anos "não são diretamente comparáveis" [TCOD 2024, p. 6].
2. **Divergência entre reproduções.** Para O&G offshore, o mesmo estudo Kimberlite/GE aparece como US$ 38 mi/ano (MaxGrip, Dispel), US$ 49 mi (resumos de busca) e US$ 58–59 mi vs US$ 24 mi por estratégia (Moir et al. 2018, p. 3); a economia por PdM aparece como US$ 17 mi ou US$ 34 mi. O whitepaper original não foi acessado (slideshare indisponível). Usar apenas com a ressalva.
3. **Fontes primárias não acessíveis.** McKinsey (HTTP 503), PwC (pwc.de/pwc.nl HTTP 403 — contornado pelo PDF hospedado pela Mainnovation), ARC (403), Gartner (403), ISO (403), IEEE Xplore (vazio), BusinessWire (403), Aberdeen 2016 (não localizado). Toda faixa atribuída à McKinsey ("30–50 % de parada, 20–40 % de vida"; "−18–25 % de custo") permanece [INSERIR CITAÇÃO].
4. **Definições heterogêneas.** "Adoção de PdM" varia de 11 % (nível 4 com analítica preditiva, PwC) a 27–30 % (MaintainX), 40 % (estudos setoriais citados apenas em secundárias) e "quase metade com equipe de PdM" (Siemens): o denominador (empresa, planta, ativo), o nível de maturidade e a autosseleção da amostra explicam a dispersão [INFERÊNCIA: comparação das metodologias declaradas nas fontes 6, 8, 11 e 14 da Tabela 2].
5. **Custo por hora não é transferível.** O custo de parada em O&G "segue o preço do petróleo" (recorde em 2022, queda em 2023) [TCOD 2024, p. 6]; a estimativa brasileira de R$ 106 mi/dia é um cálculo jornalístico para 250 kb/d a Brent US$ 78,55 [Times Brasil 2026]. Benchmarks misturam parada de TI com parada de produção e perdas anuais com horárias [ReliaMag 2026 — B]. Para um motor MT específico, o custo depende de haver reserva instalada, redundância de processo e criticidade da unidade — nenhuma fonte acessada fornece custo por evento de falha de motor MT em refinaria [INSERIR CITAÇÃO].
6. **Benefícios em pilotos.** A PwC adverte que os ganhos foram "provavelmente obtidos em peças isoladas de equipamento", em pilotos, possivelmente "low hanging fruit" [PwC 2018, p. 10]; Bain reporta que 33 % dos insatisfeitos tiveram sucesso no piloto sem escala [Bain 2025].
7. **Falso alarme como custo de primeira ordem.** A única análise custo-benefício com erro prognóstico acessada mostra que taxas altas de falso alarme podem tornar o PHM economicamente pior que a referência [Hölzel e Gollnick 2015, p. 14]; nenhum survey executivo acessado reporta taxa de falso alarme como KPI, o que é uma lacuna entre a literatura de PHM e a prática de gestão [INFERÊNCIA].
8. **Seguro.** As evidências sobre seguro são de produto (IoT Cover) e de ROI de sensores (HSB), não de prêmio condicionado a prognóstico de máquinas elétricas.
9. **Brasil.** Não há dado público acessado sobre adoção de PdM em motores MT no setor de O&G brasileiro; o Documento Nacional ABRAMAN 2024 é restrito a associados. A menção a manutenção preditiva na Petrobras aparece apenas em fontes secundárias sem números [HIPÓTESE de contexto: O&G/Petrobras, conforme premissa do usuário].

---

## 5. Implicações para o módulo RUL de isolamento de motores MT (Olivas) e para o discurso C-Level

### 5.1 O que o C-Level pede (síntese das fontes)

- Um número de abertura em moeda (custo de parada do último ano ou do pior cenário crível), seguido de disponibilidade, OEE, custo de manutenção e risco SHEQ [PwC 2018, p. 9–10; TCOD 2024, p. 3; Tractian 2026 — B].
- Business case com incerteza explícita e sem "point estimates" [Sandborn/CALCE; Feldman et al. 2009], porque a ausência de business case é a principal razão declarada para não adotar [PwC 2018, p. 8] e porque só 23–25 % das empresas conseguem vincular IA a resultado financeiro [Bain 2025; BCG 2025].
- Explicabilidade e rastreabilidade (linha direta do alerta aos dados) [IIoT World 2026; Cummins et al. 2024; Ahangar et al. 2025; Seeq 2026 — B] — o C-suite admite não entender IA em 37 % dos casos [Honeywell 2024].
- Escalabilidade além do piloto e integração com dados existentes (historiadores, CMMS) [TCOD 2024, p. 13; Bain 2025; IIoT World 2026].

### 5.2 Requisitos derivados para o módulo

R1. Saída de RUL como distribuição (p10/p50/p90) com horizonte de decisão e tendência, não como valor único [INFERÊNCIA a partir de Feldman et al. 2009; Käslin et al. 2026; fichamento 02, seção 11].
R2. Camada econômica parametrizável: custo de parada por hora (C_h), tempo de indisponibilidade por evento (T_ind, dependente de reserva instalada), custo de reparo/rebobinagem (C_rep), penalidades (C_pen), custo de intervenção planejada (C_plan), custo de falso alarme (C_FA), taxa de desconto (r) — defaults documentados com fonte e rótulo (ex.: C_h de O&G ≈ US$ 500 mil/h [TCOD 2022, p. 4]; R$ 106 mi/dia para refinaria de 250 kb/d [Times Brasil 2026]) e obrigatoriamente editáveis pelo usuário.
R3. Métrica de decisão: custo esperado de falha no horizonte H, valor esperado da intervenção (adiar vs antecipar) e VPL da política prognóstica vs política vigente (reativa/preventiva por calendário), com sensibilidade a P_FA e P_MF, seguindo a estrutura de Hölzel e Gollnick (2015).
R4. Ligação com KPIs normalizados: disponibilidade, MTBF/MTTR, custo de manutenção sobre valor de reposição, horas de parada — nomenclatura da EN 15341:2019 [NORMA: EN 15341:2019]; ISO 55000:2024 para a linguagem de "valor e risco" [NORMA: ISO 55000:2024 — texto não acessado].
R5. Auditabilidade: cada estimativa deve exibir a cadeia estressor → indicador de saúde → modelo de degradação → RUL → custo, com as fontes rotuladas — resposta direta às barreiras de confiança e explicabilidade [IIoT World 2026; Ahangar et al. 2025].
R6. Cenários decidíveis: RUL condicional a (a) presença/ausência do snubber tiristorizado (doc A) e (b) política de load shedding sob N-1 (doc B), para que a saída seja "vida ganha/perdida por decisão" e não apenas prognóstico [INFERÊNCIA; ver fichamentos 05 e 06]. Observação: a relação quantitativa entre reignições por manobra e dano ao isolamento não é fornecida pelo Documento A (que não quantifica reignições nem calcula RUL) e a premissa "5 a 7 reignições por ciclo" é premissa do usuário, não do artigo [FATO negativo: doc A; HIPÓTESE do usuário].

### 5.3 Fórmula de valor e exemplo ilustrativo [CÁLCULO PRÓPRIO]

Custo esperado de falha no horizonte H, para um motor sem prognóstico:

E[L_0] = P_f(H) · (C_h · T_ind + C_rep + C_pen)

Com prognóstico (probabilidade de falha residual P_f'(H) após intervenção planejada quando RUL_p10 < H):

E[L_1] = P_f'(H) · (C_h · T_ind + C_rep + C_pen) + P_int · C_plan + E[N_FA] · C_FA + C_PHM

Valor da informação de RUL no horizonte: V = E[L_0] − E[L_1]; a condição de adoção é V > 0 e, à luz de Hölzel e Gollnick (2015, p. 13), V é o teto do custo aceitável do módulo (C_PHM).

Exemplo numérico com entradas explicitamente hipotéticas, para o motor de 1250 kW / 4,16 kV do Documento A [FATO: doc A]:
- C_h = US$ 500 mil/h [LITERATURA: TCOD 2022, p. 4 — média setorial de O&G em 2021–22, não específica de refinaria]; T_ind = 48 h [HIPÓTESE: reserva de motor disponível, troca mecânica e ensaios]; C_rep = US$ 300 mil [HIPÓTESE: rebobinagem/reposição de motor MT — INSERIR CITAÇÃO]; C_pen = 0 [HIPÓTESE]; H = 12 meses; P_f(H) = 0,05 [HIPÓTESE]; P_f'(H) = 0,01 [HIPÓTESE]; P_int = 0,20 [HIPÓTESE]; C_plan = US$ 150 mil [HIPÓTESE]; E[N_FA] = 0,5/ano [HIPÓTESE]; C_FA = US$ 50 mil [HIPÓTESE]; C_PHM = US$ 40 mil/ano [HIPÓTESE].
- E[L_0] = 0,05 × (500.000 × 48 + 300.000) = 0,05 × 24.300.000 = US$ 1.215.000.
- E[L_1] = 0,01 × 24.300.000 + 0,20 × 150.000 + 0,5 × 50.000 + 40.000 = 243.000 + 30.000 + 25.000 + 40.000 = US$ 338.000.
- V ≈ US$ 877 mil/ano por motor, dominado pelo termo C_h · T_ind; se o motor não causar parada de unidade (T_ind efetivo → 0 por redundância), V cai para 0,04 × 300.000 − 95.000 ≈ −US$ 83 mil, isto é, o módulo não se paga por esse motor isolado.
Conclusão do cálculo: o valor do RUL para o C-Level é uma função primária da criticidade (existência de reserva e redundância de processo), não da acurácia do modelo; o módulo deve, portanto, classificar motores por criticidade antes de estimar RUL, e reportar o resultado como faixa (sensibilidade a P_f, T_ind, C_h) [INFERÊNCIA a partir do cálculo].

### 5.4 Pontos de acoplamento no repositório

- `ComponentReliability(mtbf_hours, mttr_hours)` com λ constante e sem função de risco h(t) [REPO: app/postprocessor/reliability.py:73–118; mapa `confiabilidade_eval_montecarlo.md` §1.1]: a camada econômica pode consumir `mttr_hours` como T_ind e `failure_rate_per_year` como P_f de referência (política reativa), enquanto o módulo de prognóstico fornece P_f'(H) dependente do estado.
- `run_monte_carlo(...)` amostra tempos entre falhas exponenciais e MTTR lognormal [REPO: app/postprocessor/reliability_monte_carlo.py:242–346]: base natural para propagar a incerteza de RUL até custo esperado (processo não homogêneo, conforme extensão §3.4 do mapa).
- `EquipmentInstance.duty: dict` documentado com chaves `I_load_A`, `I_design_A`, `I_fault_kA`, `ip_kA`, `V_drop_pct` [REPO: app/postprocessor/equipment_eval.py:98–105]: ponto de injeção de `rul_p10_years`, `life_consumed_pct`, `expected_loss_usd` sem alterar a dataclass; para motores o dashboard atual retorna 1 PASS e 8 N/A [REPO: mapa §1.4, verificação executada], logo há espaço para regras de prognóstico/custo.
- `generate_html_dashboard` deriva colunas dos `rule_id` e formata `evaluated_value` como percentual [REPO: app/postprocessor/equipment_eval_dashboard.py:171–177, 254–255]: uma regra `EQ-MOTOR-RUL-COST` pode expor "custo esperado no horizonte / custo de reposição" em %, coerente com a convenção existente.
- Presets IEEE 493 (`induction_motor_400hp`) não verificados contra a norma [REPO: app/gui/reliability_dialog.py:209–215; mapa §1.2] — manter [INSERIR CITAÇÃO] até conferir tabela e página.
- Grandezas de estresse já produzidas pela cadeia de simulação: modelo de reignição de VCB (I_chop, di/dt crítico, recuperação dielétrica) e validação do snubber [REPO: app/preprocessor/vcb_model_emitter.py; app/validation/validator_vcb.py — conforme fichamento 01, §11]; partida de motor com aviso de curva I²t para t_start > 30 s [REPO: app/postprocessor/motor_starting.py:537–541]; curva térmica sem HOT/COLD [REPO: app/postprocessor/tcc_damage.py:449–601]. Esses são os insumos de "estressor" a converter em índice de saúde; a conversão em si não existe no repositório nem nos Documentos A e B [FATO negativo: docs A e B; mapa do repositório].

### 5.5 Mensagens para o discurso C-Level (cada uma com o lastro disponível)

1. "Uma hora de parada em O&G custou, em média, cerca de US$ 500 mil em 2021–22 e o custo acompanha o preço do petróleo" [TCOD 2022, p. 4; TCOD 2024, p. 6 — amostra pequena, fornecedor]. Para refinaria brasileira, "um dia parado ≈ R$ 106 mi" [Times Brasil 2026 — cálculo com premissas explícitas]. Sempre substituir pelo número da própria planta, como recomendam os guias de CFO e os críticos de benchmark [Tractian 2026; ReliaMag 2026 — B].
2. "Refinarias brasileiras operam acima de 100 % da capacidade de referência (abr–mai/2026)" [Times Brasil 2026]: sem folga, toda falha de motor crítico vira perda de produção, o que eleva C_h · T_ind [INFERÊNCIA].
3. "Quem faz PdM com analítica reporta +9 % de uptime, −12 % de custo, −14 % de risco SHEQ e +20 % de vida de ativo, em 95 % dos casos" [PwC 2018, p. 10 — n = 67, pilotos].
4. "A barreira nº 1 não é o algoritmo: é o business case (63 %), os dados (54–67 %) e a confiança (43 %)" [PwC 2018, p. 8–9; IIoT World 2026]. O módulo responde às três com camada econômica, ingestão de dados existentes e cadeia de evidência auditável.
5. "Falso alarme custa dinheiro: análises custo-benefício de PHM mostram que taxas altas de falso alarme anulam o ganho" [Hölzel e Gollnick 2015, p. 14]; por isso o módulo reporta P_FA e o custo de intervenção planejada, não só a RUL.
6. "Quebras elétricas e mecânicas concentram > 80 % do impacto financeiro dos sinistros em geração de energia, com prazos de reposição de anos" [FM via IT Brief 2026 — B]: argumento de risco e de estoque de reserva, a confirmar em fonte primária [INSERIR CITAÇÃO].
7. "O CFO precisa estar na decisão: onde o CFO tem autoridade sobre o investimento digital, 42 % das empresas têm lucratividade acima da média, contra 18 %" [Deloitte 2025].
8. No Brasil, "66 % das indústrias apontam custo e 25 % não conseguem perceber retorno" [CNI 2022] e "altos executivos tratam Indústria 4.0 como modismo e preferem projetos com benefício mais fácil de avaliar" [CNI 2020, p. 11]: o entregável deve ser, antes de tudo, uma avaliação de benefício simples e verificável.

### 5.6 Lacunas a preencher

- Custo por evento de falha de motor MT em refinaria/plataforma (com e sem reserva) — [INSERIR CITAÇÃO].
- Fonte primária McKinsey para as faixas de benefício — [INSERIR CITAÇÃO].
- Whitepaper GE/Kimberlite 2016 (conciliar US$ 38/49/58 mi) — [INSERIR CITAÇÃO].
- Indicadores do Documento Nacional ABRAMAN 2024 (custo de manutenção/faturamento, mix preditiva) — [INSERIR CITAÇÃO].
- Prêmio de seguro condicionado a monitoramento/prognóstico de máquinas elétricas — [INSERIR CITAÇÃO].
- Texto de ISO 55000:2024 e de EN 15341:2019 (tabelas de KPIs) — acesso à norma necessário [NORMA: não lida].

---

## 6. Referências (ABNT)

ABB. *ABB survey reveals unplanned downtime costs $125,000 per hour* (press release reproduzido por Reliabilityweb). 2023. Disponível em: https://reliabilityweb.com/en/press-release/abb-survey-reveals-unplanned-downtime-costs-125000-per-hour. Acesso em: 2 set. 2026.

ABRAMAN. *Documento Nacional*. 2024. Disponível em: https://abramanoficial.org.br/publicacoes/documento-nacional. Acesso em: 2 set. 2026.

AGÊNCIA PETROBRAS. *Petrobras investe R$ 500 milhões na parada programada de manutenção da Refinaria Presidente Bernardes de Cubatão (RPBC)*. 28 jun. 2024. Disponível em: https://agencia.petrobras.com.br/w/negocio/petrobras-investe-r-500-milhoes-na-parada-programada-de-manutencao-da-refinaria-presidente-bernardes-de-cubatao-rpbc-. Acesso em: 2 set. 2026.

AHANGAR, M. N.; FARHAT, Z. A.; SIVANATHAN, A. AI trustworthiness in manufacturing: challenges, toolkits, and the path to Industry 5.0. *Sensors*, v. 25, n. 14, 4357, 2025. DOI 10.3390/s25144357. Disponível em: https://pmc.ncbi.nlm.nih.gov/articles/PMC12298069/. Acesso em: 2 set. 2026.

BAIN & COMPANY. *Executive survey: AI moves from pilots to production*. 24 nov. 2025. Disponível em: https://www.bain.com/insights/executive-survey-ai-moves-from-pilots-to-production/. Acesso em: 2 set. 2026.

BCG. *From potential to profit: closing the AI impact gap* (AI Radar 2025). 15 jan. 2025. Disponível em: https://www.bcg.com/publications/2025/closing-the-ai-impact-gap. Acesso em: 2 set. 2026.

BSI. *BS EN 15341:2019 — Maintenance. Maintenance key performance indicators*. 2019. Disponível em: https://knowledge.bsigroup.com/products/maintenance-maintenance-key-performance-indicators. Acesso em: 2 set. 2026.

CHOO, Y.; SHIN, S.-J. Integrating machine learning-based remaining useful life predictions with cost-optimal block replacement for industrial maintenance. *International Journal of Prognostics and Health Management*, v. 16, n. 1, 2025. DOI 10.36001/ijphm.2025.v16i1.4242. Disponível em: http://papers.phmsociety.org/index.php/ijphm/article/view/4242. Acesso em: 2 set. 2026.

CNI. *A difusão das tecnologias da Indústria 4.0 em empresas brasileiras*. Brasília: CNI, 2020. Disponível em: https://static.portaldaindustria.com.br/media/filer_public/c4/26/c42635b7-c3c0-4763-8ed2-69aa33b8a07e/a_difusao_das_tecnologias_da_industria_40_vf.pdf. Acesso em: 2 set. 2026.

CNI. *Indústria 4.0: 69 % das indústrias brasileiras fazem uso de tecnologia digital*. Agência de Notícias da Indústria, 26 abr. 2022. Disponível em: https://noticias.portaldaindustria.com.br/noticias/inovacao-e-tecnologia/industria-40-69-das-industrias-brasileiras-fazem-uso-de-tecnologia-digital-no-brasil/. Acesso em: 2 set. 2026.

CUMMINS, L. et al. Explainable predictive maintenance: a survey of current methods, challenges and opportunities. *arXiv*:2401.07871, 2024. Disponível em: https://arxiv.org/abs/2401.07871. Acesso em: 2 set. 2026.

DELOITTE INSIGHTS. *Industry 4.0 and predictive technologies for asset maintenance*. 9 maio 2017. Disponível em: https://www.deloitte.com/us/en/insights/industry/manufacturing-industrial-products/industry-4-0/using-predictive-technologies-for-asset-maintenance.html. Acesso em: 2 set. 2026.

DELOITTE INSIGHTS. *How the right mix of C-suite leadership can drive outsized AI returns*. 18 dez. 2025. Disponível em: https://www.deloitte.com/us/en/insights/topics/digital-transformation/c-suite-leadership-ai-returns.html. Acesso em: 2 set. 2026.

DERBECKER, M. Industrial AI won't get adopted until engineers can verify it. *Control Global*, 31 ago. 2026. Disponível em: https://www.controlglobal.com/control/ai-ml/article/55401808/seeq-how-to-earn-industrial-ai-trust. Acesso em: 2 set. 2026.

DISPEL. *Digital transformation can reduce downtime in the oil & gas industry*. 16 mar. 2021. Disponível em: https://dispel.com/blog/how-digital-transformation-can-reduce-unplanned-downtime-in-the-oil-gas-industry. Acesso em: 2 set. 2026.

EIA. *Midwest refinery outage is affecting petroleum product markets*. Today in Energy, 13 fev. 2024. Disponível em: https://www.eia.gov/todayinenergy/detail.php?id=61403. Acesso em: 2 set. 2026.

FELDMAN, K.; JAZOULI, T.; SANDBORN, P. A methodology for determining the return on investment associated with prognostics and health management. *IEEE Transactions on Reliability*, v. 58, n. 2, p. 305–316, 2009. DOI 10.1109/TR.2009.2020133. Metadados: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/TR.2009.2020133?fields=title,year,abstract,venue,authors,citationCount,externalIds. Acesso em: 2 set. 2026.

GE VERNOVA. *AI prevents gas turbine downtime for African oil & gas site*. 21 ago. 2025. Disponível em: https://www.gevernova.com/software/blog/ai-prevents-gas-turbine-downtime-african-oil-gas-site. Acesso em: 2 set. 2026.

HÖLZEL, N. B.; GOLLNICK, V. Cost-benefit analysis of prognostics and condition-based maintenance concepts for commercial aircraft considering prognostic errors. In: ANNUAL CONFERENCE OF THE PHM SOCIETY, 2015. Disponível em: https://elib.dlr.de/100435/1/phmc_15_050.pdf. Acesso em: 2 set. 2026.

HONEYWELL. *Industrial AI uptake is just getting started but majority of sector is uncovering new use cases, finds Honeywell research*. 23 jul. 2024. Disponível em: https://www.honeywell.com/us/en/news/press-releases/2024/07/industrial-ai-uptake-is-just-getting-started-but-majority-of-sector-is-uncovering-new-use-cases-finds-honeywell-research. Acesso em: 2 set. 2026.

HSB. *HSB IoT clients gain 500 percent return on investment*. 29 mar. 2022. Disponível em: https://www.munichre.com/hsb/en/press-and-publications/press-releases/2022/2022-03-29-hsb-iot-clients-gain-500-percent-roi.html. Acesso em: 2 set. 2026.

IIoT WORLD. *Industrial AI Readiness Report 2026: data comes first*. 27 jan. 2026. Disponível em: https://www.iiot-world.com/industrial-iot/connected-industry/industrial-ai-readiness-report-2026/. Acesso em: 2 set. 2026.

IIoT WORLD. *Industrial data and AI readiness survey 2027*. 10 ago. 2026. Disponível em: https://www.iiot-world.com/artificial-intelligence-ml/industrial-data-and-ai-readiness-survey-2027/. Acesso em: 2 set. 2026.

IIoT WORLD. *Predictive maintenance cost savings: case studies*. 14 fev. 2025. Disponível em: https://www.iiot-world.com/predictive-analytics/predictive-maintenance/predictive-maintenance-cost-savings/. Acesso em: 2 set. 2026.

INVESTING.COM; REUTERS. *Refinaria da Petrobras Reduc opera normalmente após parada não programada*. 13 set. 2016. Disponível em: https://br.investing.com/news/stock-market-news/refinaria-da-petrobras-reduc-opera-normalmente-apos-parada-nao-programada-202801. Acesso em: 2 set. 2026.

IT BRIEF AUSTRALIA. *FM warns of rising risks to power generation assets*. 21 jul. 2026. Disponível em: https://itbrief.com.au/story/fm-warns-of-rising-risks-to-power-generation-assets. Acesso em: 2 set. 2026.

KÄSLIN, B. et al. Integrating prognostics, maintenance, and tail assignment under remaining useful life uncertainty: a stochastic optimisation approach for airline reliability. *arXiv*:2608.22569, 2026. Disponível em: https://arxiv.org/abs/2608.22569. Acesso em: 2 set. 2026.

KLEINUBING, R. Mining's smart shift to predictive maintenance. *Global Mining Review*/Emerson, ago. 2025. Disponível em: https://www.emerson.com/en/corporate/news/2025/minings-smart-shift-to-predictive-maintenance. Acesso em: 2 set. 2026.

MAINTAINX. *2025 State of Industrial Maintenance*. 2025. Disponível em: https://www.getmaintainx.com/newsroom/state-of-industrial-maintenance-report-2025; https://www.getmaintainx.com/blog/maintenance-stats-trends-and-insights. Acesso em: 2 set. 2026.

MAXGRIP. *The cost of unplanned downtime*. 31 ago. 2026. Disponível em: https://www.maxgrip.com/resource/article-the-cost-of-unplanned-downtime/. Acesso em: 2 set. 2026.

MAXGRIP. *Game changers in asset performance management: key insights from the Verdantix 2025 survey*. 7 jul. 2026. Disponível em: https://www.maxgrip.com/resource/verdantix-survey-2025-game-changers-in-asset-performance-management/. Acesso em: 2 set. 2026.

MOIR, K.; NICULITA, O.; MILLIGAN, W. Prognostics and health management in the oil & gas industry — a step change. In: EUROPEAN CONFERENCE OF THE PHM SOCIETY, 2018. Disponível em: http://www.papers.phmsociety.org/index.php/phme/article/download/396/phmec_18_396. Acesso em: 2 set. 2026.

MUNICH RE. *IoT Cover — gaining trust and building confidence*. s.d. Disponível em: https://www.munichre.com/en/solutions/for-industry-clients/iot-cover.html. Acesso em: 2 set. 2026.

NIELSEN, J. S. Value of information of structural health monitoring with temporally dependent observations. *Structural Health Monitoring*, 2021. DOI 10.1177/14759217211030605. Metadados: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1177/14759217211030605?fields=title,year,abstract,venue,authors,externalIds. Acesso em: 2 set. 2026.

PATRICK, L. M. Collaborating for success. *ABB Review*, n. 3, p. 15–17, 2007. Disponível em: https://library.e.abb.com/public/40de92d2e8c26aa48325734b00405276/15-17%203M765_ENG72dpi.pdf. Acesso em: 2 set. 2026.

PLANT ENGINEERING. *How data is unlocking big gains for manufacturers*. 16 jun. 2026. Disponível em: https://www.plantengineering.com/how-data-is-unlocking-big-gains-for-manufacturers/. Acesso em: 2 set. 2026.

PwC; MAINNOVATION. *Predictive Maintenance 4.0: beyond the hype — PdM 4.0 delivers results*. set. 2018. Disponível em: https://www.mainnovation.com/wp-content/uploads/tmp/6397245268d8d3711c88cda0b4585ab02e612f2e.pdf; https://www.mainnovation.com/publications/predictive-maintenance-4-0-3/. Acesso em: 2 set. 2026.

QUALITY DIGEST. *The State of Industrial Maintenance 2025: a MaintainX survey*. 11 jun. 2025. Disponível em: https://www.qualitydigest.com/inside/research-tech-article/state-industrial-maintenance-2025-maintainx-survey-061125.html. Acesso em: 2 set. 2026.

R&D WORLD. *AI adoption in engineering: 10 key trends from Avnet's latest survey*. 16 dez. 2025. Disponível em: https://www.rdworldonline.com/avnet-study-engineers-are-shipping-more-ai-products-but-confidence-in-them-remains-uneven/. Acesso em: 2 set. 2026.

RAVAGNANI, A. Refinarias brasileiras operam acima da capacidade e custo de paradas supera R$ 100 milhões por dia. *Times Brasil/CNBC*, 14 ago. 2026. Disponível em: https://timesbrasil.com.br/empresas-e-negocios/combustiveis/refinarias-acima-da-capacidade-custo-paradas-manutencao/. Acesso em: 2 set. 2026.

RELIAMAG. *Industrial downtime cost benchmarks: what published studies actually show*. 2026. Disponível em: https://reliamag.com/guides/industrial-downtime-cost-benchmarks/. Acesso em: 2 set. 2026.

ROCKWELL AUTOMATION. *Ninety-five percent of manufacturers are investing in AI to navigate uncertainty and accelerate smart manufacturing* (10th State of Smart Manufacturing Report). 3 jun. 2025. Disponível em: https://www.rockwellautomation.com/en-us/company/news/press-releases/Ninety-Five-Percent-of-Manufacturers-Are-Investing-in-AI-to-Navigate-Uncertainty-and-Accelerate-Smart-Manufacturing.html. Acesso em: 2 set. 2026.

SANDBORN, P. *Prognostics and Health Management (PHM) for electronic systems — research page*. University of Maryland/CALCE. Disponível em: https://terpconnect.umd.edu/~sandborn/research/PHM.html. Acesso em: 2 set. 2026.

SANDBORN, P.; WILKINSON, C. A maintenance planning and business case development model for the application of prognostics and health management (PHM) to electronic systems. *Microelectronics Reliability*, v. 47, n. 12, p. 1889–1901, 2007. DOI 10.1016/j.microrel.2007.02.016. Metadados: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.microrel.2007.02.016?fields=title,year,abstract,venue,authors,citationCount,externalIds. Acesso em: 2 set. 2026.

SIEMENS; SENSEYE. *The True Cost of Downtime 2022*. Erlangen: Siemens AG, 2023. Disponível em: https://assets.new.siemens.com/siemens/assets/api/uuid:3d606495-dbe0-43e4-80b1-d04e27ada920/dics-b10153-00-7600truecostofdowntime2022-144.pdf. Acesso em: 2 set. 2026.

SIEMENS; SENSEYE. *The True Cost of Downtime 2024*. Erlangen: Siemens AG, 2024. Disponível em: https://assets.new.siemens.com/siemens/assets/api/uuid:1b43afb5-2d07-47f7-9eb7-893fe7d0bc59/TCOD-2024_original.pdf. Acesso em: 2 set. 2026.

THE AEMT. *The True Cost of Downtime 2024: a comprehensive analysis*. 2024. Disponível em: https://www.theaemt.com/resource/the-true-cost-of-downtime-2024-a-comprehensive-analysis.html. Acesso em: 2 set. 2026.

THE MANUFACTURER. *Unplanned downtime affecting 82 % of businesses*. 2017. Disponível em: https://www.themanufacturer.com/articles/unplanned-downtime-affecting-82-businesses/. Acesso em: 2 set. 2026.

TRACTIAN. *The CFO's guide to funding a predictive maintenance program*. 19 ago. 2026. Disponível em: https://tractian.com/en/blog/the-cfos-guide-to-funding-a-predictive-maintenance-program. Acesso em: 2 set. 2026.

VERDANTIX. *Global Corporate Survey 2025: industrial operations and maintenance services budgets, priorities and tech preferences*. 15 ago. 2025. Disponível em: https://www.verdantix.com/venture/report/global-corporate-survey-2025-industrial-operations-and-maintenance-services-budgets-priorities-and-tech-preferences. Acesso em: 2 set. 2026.

Referências citadas por fontes acessadas, mas não acessadas diretamente nesta coleta (não usar como fonte primária): McKinsey & Company (2014; 2018) [INSERIR CITAÇÃO]; GE Oil & Gas/Kimberlite, *The impact of digital on unplanned downtime* (2016) [INSERIR CITAÇÃO]; Aberdeen, *The rising cost of downtime* (2016) [INSERIR CITAÇÃO]; ARC Advisory Group (2006) [INSERIR CITAÇÃO]; ISO 55000:2024 [NORMA: texto não lido]; Sandborn, P.; Feldman, K. The economics of PHM. In: PECHT, M. (ed.). *Prognostics and Health Management of Electronics*. Wiley, 2008, p. 85–118 [citação obtida da página de Sandborn; texto não lido].

---

## Anexo A — URLs tentadas e não acessadas (bloqueio ou conteúdo indisponível)

- https://new.abb.com/news/detail/107660/abb-survey-reveals-unplanned-downtime-costs-125-000-per-hour (HTTP 503; conteúdo obtido via Reliabilityweb).
- https://www.mckinsey.com/industries/chemicals/our-insights/using-advanced-analytics-to-boost-productivity-and-profitability-in-chemical-manufacturing e https://www.mckinsey.com/capabilities/operations/our-insights/digitally-enabled-reliability-beyond-predictive-maintenance (HTTP 503).
- https://www.pwc.de/de/industrielle-produktion/pwc-predictive-maintenance-4-0.pdf e https://www.pwc.nl/nl/assets/documents/pwc-predictive-maintenance-4-0.pdf (HTTP 403; mesmo relatório obtido via Mainnovation); https://www.pwc.be/en/news-publications/2024/ai-in-maintenance.html (403).
- http://escml.umd.edu/Papers/Sandborn-PHMConf08-paper.pdf e http://escml.umd.edu/Papers/Sandborn_PHM_Cost.pdf (HTTP 503).
- https://ieeexplore.ieee.org/document/4967922/ (página vazia).
- https://www.arcweb.com/... (HTTP 403, três páginas).
- https://www.gartner.com/en/documents/3856379 (HTTP 403).
- https://www.iso.org/standard/83053.html (HTTP 403).
- https://www.businesswire.com/news/home/20250515686548/en (HTTP 403).
- https://www.slideshare.net/slideshow/gea32876-offshorestudypaperr11/70030843 (erro de carregamento).
- https://www.mdpi.com/2075-1702/12/4/220 (HTTP 403).
- https://www.hydrocarbonpublishing.com/ReportP/power.pdf (HTTP 503).
- https://www.ismworld.org/... (redireciona a login).
- https://global.abb/group/en/news (404); https://blog.siemens.com/2024/07/the-true-cost-of-an-hours-downtime-an-industry-analysis/ (somente cabeçalho); https://www.plantengineering.com/predictive-maintenance-best-practices/ (sem dados de survey); https://abramanoficial.org.br/publicacoes/noticias/... (sem números); https://nvms.in.th/2017/02/20/whitepaper-impact-digital-unplanned-downtime/ (sem conteúdo do whitepaper); https://www.aquip.com.au/... (404); https://standards.iteh.ai/... (somente cabeçalho).
