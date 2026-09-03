# Changelog — Olivas Power System Studio

Todas as mudanças notáveis deste projeto. O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o versionamento segue [SemVer](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- `app/postprocessor/cable_sizing.py`: `_fc_grouping` (fator de correção por agrupamento, Tabela 42 NBR 5410) interpolava linearmente entre faixas da norma, produzindo valores inexistentes (ex. 0.48 para 10 circuitos, quando a norma define um único fator 0.50 para toda a faixa 9-11). A Tabela 42 é uma função em degraus, não contínua — confirmado contra a reprodução oficial da Prysmian (Guia de Dimensionamento de Cabos para Baixa Tensão, Tabela 13, "conforme tabela 42 da NBR 5410:2004"). Corrigido para busca por faixa sem interpolação; as tabelas de correção por temperatura (`_FC_TEMP_PVC`/`_FC_TEMP_XLPE`, Tabela 40) foram conferidas na mesma fonte e batem exatamente — não alteradas.

### Documented (sem alteração de código)
- `app/postprocessor/cable_sizing.py` cobre apenas os métodos de instalação A1/B1 (não-subterrâneos); a Prysmian também publica as tabelas de correção para linhas subterrâneas (temperatura do solo a 20 °C de referência, Tabela 11 "Solo") e resistividade térmica do solo (Tabela 12, NBR Tabela 41) — não incorporadas por não haver ainda suporte ao método D (subterrâneo direto), já sinalizado no código como trabalho futuro (`v0.95.x`). Evitado implementar correção sem a base de ampacidade subterrânea correspondente.

### Added — Catálogo de engenharia com dados de fabricantes (FASES 1-5)

Digitalização de manuais/datasheets oficiais (ABB, Schneider, WEG, Eaton, Siemens, SEL, GE, Bussmann, SIBA, Prysmian, Nexans, Induscabos), com proveniência por entrada. Todas as mudanças são aditivas.

- `app/equipment/library.py`: novos dataclasses `SettingRange`, `TripUnitModel` (funções LSIG de unidades de disparo MCCB/ACB — faixas de Ir/tr/Isd/tsd/Ii/Ig/tg, opções de curva, I²t ON/OFF), `FuseRating` e `FuseModel` (I²t de pré-arco/total, I1/I3, perdas). APIs `list_trip_units`/`get_trip_unit`/`list_fuses`/`get_fuse`; `stats()` e `list_vendors()` passam a incluir as novas categorias.
- `app/standards/relay_models.py`: novas entradas no registry — `ABB-REF615R`, `Siemens-7SJ82`, `GE-850`, `Schneider-MiCOM-P127`, `WEG-SRW01` (faixas de pickup/TMS/TD e funções ANSI conforme manuais).
- `app/standards/vendor_curve_constants.py` (novo): constantes de curva publicadas por SEL (C1-C5, U1-U5), GE (IEEE 4-34, ANSI 4-36, IEC 4-38, IAC 4-40) e ABB (defaults da curva programável), com família e fonte explícitas.
- `app/preprocessor/cable_catalog.py`: campos opcionais `manufacturer`/`source` em `CatalogCable`; cabos Induscabos INDULINK 3,6/6 kV (14 seções, parâmetros completos NBR 14039, 60 Hz) e Nexans TR-XLPE 6,35/11 kV (14 seções).
- `tests/test_pp_v4_1_0_vendor_catalog.py`: cobertura das novas entradas e invariantes físicos (Ir ≤ 1×In, I²t total ≥ pré-arco, Rca > Rcc, coincidência de constantes entre fontes independentes).
- `app/equipment/library.py` (aprofundamento FASE 1): unidades de disparo `ABB-XT7-EKIP-TOUCH-LSIG` (SACE Tmax XT7, 800-1600 A, Ekip Touch/Hi-Touch) e `ABB-EMAX2-EKIP-TOUCH-LSIG-IEC` (SACE Emax 2 E1.2/E2.2/E4.2/E6.2, 400-6300 A, mercado IEC) — faixas L/S/S2/I/G, fórmulas de disparo e coeficientes IEC 60255-151 próprios da ABB (SI k=0.16, distintos dos universais). Confirmado: SACE Tmax XT1/XT3 não possuem disparador eletrônico Ekip no catálogo oficial (apenas termomagnético TMD/TMF) — não digitalizados por ausência de dado; XT6 sem manual dedicado localizado — `[REQUIRES MANUAL DIGITIZATION]`.
- `app/preprocessor/cable_catalog.py` (aprofundamento FASE 4/5): cabos Prysmian Eprotenax Compact 105, 3,6/6 kV, Cu, isolação HEPR 105 °C (14 seções 10-500 mm²) — terceiro fabricante da tabela, fechando o objetivo original de cobertura cruzada em 6 kV (Induscabos + Prysmian) com R_dc de classe NBR NM 280/IEC 60228 cl. 2 coincidente entre os dois. `C_uF_per_km` derivado de Xc (Ω·km, não impresso diretamente) — atenção à convenção brasileira de separador de milhar identificada durante a digitalização (ex. "11.360" = 11360, não 11,36).
- `app/equipment/library.py` (aprofundamento FASE 1): unidade de disparo `SE-NT-NW-MICROLOGIC-2-3-5-6.0A` — Schneider (marca Square D, mercado UL) MicroLogic 2.0A/3.0A/5.0A/6.0A para MasterPact NT/NW (ACB), com dial discreto L/S/I/G e tabelas oficiais de tr (três referências: 1.5×Ir/6×Ir/7.2×Ir), tsd/tg (I²t ON/OFF) e Ig por faixa de corrente nominal (3 níveis, incluindo tetos absolutos acima de 1200 A).
- `app/equipment/library.py` (aprofundamento FASE 3): seis novos fusíveis Bussmann NH gG/gL 500 V a.c. — tamanhos 1, 02, 2, 03, 3 e 4 (a fonte já baixada `Technical Data 10164` continha essas tabelas, não digitalizadas no lote anterior que só cobriu 000/00/0). Corpos '02' e '03' são intermediários entre os tamanhos padrão (norma DIN/IEC), com faixa e I²t próprios — modelados como entradas distintas dos tamanhos '2'/'3'.
- `app/equipment/library.py` (aprofundamento FASE 1, via workflow de pesquisa): `WEG-ACW-ETS-LSI` (disparador eletrônico LSI do MCCB de alta capacidade WEG ACW, frames 400-800 A) e `SIEMENS-3WA-ETU600` (disparador LSI/LSIG/LSIG Hi-Z do disjuntor aberto SENTRON 3WA, sucessor do 3WL, In 630-6300 A). Pesquisa cruzada confirmou que **ACW é caixa moldada (MCCB), não disjuntor aberto** — WEG possui apenas uma linha de ACB (ABW/ABWC, já digitalizada); dado incluído mesmo assim por preencher lacuna real de cobertura MCCB WEG.
- `app/standards/relay_models.py` (aprofundamento FASE 2, via workflow de pesquisa): `Eaton-Digitrip-3000` (relé standalone de proteção de média tensão, retrofit para disjuntores a vácuo VCP-W — **não** é unidade de disparo integrada de disjuntor Magnum, correção de premissa) e `SEL-487E` (relé diferencial de **transformador** 87T/87Q/REF — **não** de barra; o relé de barra da SEL é o SEL-487B, produto distinto, não digitalizado). Primeira função de proteção diferencial (87) no registry de relés.
- `app/standards/relay_models.py` (aprofundamento FASE 2, via workflow de pesquisa): `ABB-REF620` (linha superior à REF615/REF615R; achado relevante — proteção de **distância (21)** e diferencial de alta impedância de barra são exclusivas do REM620/motor na mesma plataforma 620 series, o REF620/feeder **não** as possui, na revisão do manual consultada), `GE-369` (relé de **motor** correto da GE — corrige a premissa de pesquisa original: GE 750 é relé de *alimentador* e GE 845 é de *transformador*, nenhum dos dois é de motor; usa curva de sobrecarga térmica proprietária, distinta de toda família IEC/IEEE já registrada) e `Schneider-Sepam-S40` (linhagem *nativa* Schneider, distinta do MiCOM ex-Alstom/GE já digitalizado; confirma que as constantes k/α das curvas IEC são universais mas os coeficientes A/B/p das curvas "IEEE" divergem dos padrões ANSI Anexo A já digitalizados — mesma cautela já registrada para SEL vs GE ANSI). Eaton NZM4 pesquisado e confirmado como já coberto pela entrada `EATON-NZM-PXR25` existente (mesma família PXR10/20/25 independente do frame) — nenhuma entrada nova necessária, evitada duplicação.

### Verified
- Passagem adversarial de verificação (9 revisores independentes, somente leitura) de cada literal transcrito contra o texto extraído dos datasheets: ~1.400 campos conferidos. Correções aplicadas: I²t pré-arco do Bussmann 12TDLEJ6.3 (98 A²s, não 980 — expoente sobrescrito), Ig do Siemens 3VA ETU560/860 (faixa contínua 0,2-1,0×In, não dial de 5 posições), passos do Eaton Digitrip 1150 (Ir 0,05; Isd 0,5 + M1), funções S/I/G desligáveis (ABB Ekip Touch, Siemens 3WL), tensão nominal dos Bussmann aM (500 V; sufixo -690 para 690 V), CEF reclassificado como back-up, part numbers ABB CMF/CEF substituídos pelos códigos de pedido do catálogo, ampacidade enterrada/duto Nexans (legenda de ícones decodificada da página renderizada), Time multiplier do 7SJ82 (0,00-15,00) e listas ANSI (REF615R, P127, GE 850).
- `vendor_curve_constants.operate_time_ge_5param_s`: forma de 5 constantes das curvas GE ANSI/IAC (`T = TDM·[A + B/(M−C) + D/(M−C)² + E/(M−C)³]`), validada contra as Tabelas 4-37/4-41 do manual.

### Documented (sem alteração de código)
- Duas famílias numéricas distintas circulam sob os nomes "Moderately/Very/Extremely Inverse": IEEE C37.112 Anexo A (ABB/GE) e "US" (SEL U1-U5 e GE ANSI 4-36 partilham `tr`, mas os tempos de operação diferem até ~22 %). `iec60255.IEEE_CURVE_COEFFICIENTS` mistura as duas e divide por 7 — registrado em `vendor_curve_constants.py`, não alterado.
- `relay_models.SEL_751` (pré-existente): `pickup_range_per_in=(0.5, 16.0)` reproduz ampères secundários do modelo 5 A (0,10-3,20×In no datasheet) e `tms_range` máx. 1,0 vs 1,50 publicado. Não alterado (testes legados codificam 16×In); decisão do mantenedor.
- R0/X0 de cabos não é parâmetro de catálogo (depende do aterramento da blindagem e do solo) — confirmado em 3 fabricantes; permanece cálculo por instalação.

---

## [4.0.0-beta] — 2026-05-01

### 🏆 Milestone preparation

Beta release pré-produção. Inclui audit i18n completo, CHANGELOG consolidado, e validação de readiness para distribuição.

### Added
- `CHANGELOG.md` (este documento)
- `tests/test_pp_v4_0_0_beta_readiness.py` — production readiness checks

### Changed
- `app/core/version.py`: 4.0.0-alpha → 4.0.0-beta

### Validated (no code changes)
- i18n EN/ES parity: 133/133 keys (zero missing)
- Sweep regression: 219+ tests verdes
- Master Protocol 8/8 garantias mantidas

---

## [4.0.0-alpha] — 2026-05-01

### 🏆 PARIDADE TOTAL v1 ATINGIDA

Milestone histórico marcando paridade total com SKM PTW Power*Tools v11. Todas as 4 categorias do SKIPPED_BACKLOG fechadas.

### Added
- 16 milestone validation tests
- `app/postprocessor/fault_distance_walker.py` (B.4 — IEC 60909-0:2016 §3.7)

### Closed (SKIPPED_BACKLOG)
- B.4 — Decay μ·q automatic detection (network walker)
- D.3 — TCC Drawing 3-tab pages
- 🎉 SKIPPED_BACKLOG ZERADO (0/15)

---

## [3.9.0] — 2026-05-01

### Added
- `auto_classify_fault_distance(project, fault_bus_name)` → automatic NEAR/FAR classification
- 16 fault walker tests
- Categoria B 100% encerrada

---

## [3.8.2] — 2026-05-01

### Added
- TCC 3-tab pages (Settings / Curves / Datablock) per PTW Tutorial §Part 3 p.103-104
- 12 tests TCC tabs
- Categoria D 100% encerrada

### Fixed
- `QLabel` shadow bug em `TCCCoordinogramDialog.__init__`

---

## [3.8.1] — 2026-05-01

### Added
- IEEE 14-bus subset fixture (`tests/fixtures/ieee14_bus.json`)
- `PfBus.Q_min_pu/Q_max_pu/original_type` campos
- `PowerFlowSystem.solve_with_q_limits` (IEEE 399 §5.3.4)
- 14 tests Q-limit + fixture
- Categoria C 100% encerrada

---

## [3.8.0] — 2026-05-01

### Added
- `app/postprocessor/reliability_monte_carlo.py` (~280 LOC)
- 10 IEEE 493-2007 Tab 3-1 equipment presets
- Time-series Monte Carlo simulation com 90% confidence intervals
- Botão "🎲 Monte Carlo" no ReliabilityDialog
- 18 tests Reliability MC

---

## [3.7.2] — 2026-05-01

### Added
- C.1: PowerFlowDialog deprecation banner + title `[LEGACY 2-bus]`
- C.2: `chk_hybrid_demo` checkbox em EquipmentEvalDialog
- 7 tests cross-cutting

---

## [3.7.1] — 2026-05-01

### Added
- `app/postprocessor/branch_impedance.py` (~250 LOC)
- Tr/CABLE/TLIN impedance extraction (IEC 60076-1 + IEC 60364)
- `extract_branch_impedance` dispatch function
- 22 tests branch impedance

### Changed
- `build_pf_system_from_project`: usa Z real em vez de defaults

---

## [3.7.0] — 2026-05-01

### Added
- `BUS.ocomp` schema com `bus_role` property (auto/slack/pv/pq)
- B.2: 3 helpers em `analysis_dialogs.py` (`_read_bus_role`, `_find_explicit_slack`, `_read_bus_voltage_pu`)
- B.3: `motor_speed_gradient_pu_per_s` param em `calculate_short_circuit`
- 19 tests PF parity

### Changed
- `q_factor()` agora usa `n_per_unit_per_second` (IEC 60909-0:2016 §4.6.2 Tab 3)

---

## [3.6.2] — 2026-05-01

### Added
- D.1: `TCCCoordinogramWidget.set_c_lines/_draw_c_lines` (matplotlib overlay)
- D.2: `TCCCoordinogramWidget.set_protection_filter` (Phase/Ground/All combo)
- 13 tests TCC polish

---

## [3.6.0] — 2026-05-01

### Added
- `app/postprocessor/reliability.py` (~270 LOC)
- IEEE 1366-2012 indices (SAIFI, SAIDI, CAIDI, ASAI)
- IEEE 493 Gold Book series/parallel reliability
- `app/gui/reliability_dialog.py` wired no menu Análise
- 35 tests Reliability

---

## [3.5.2] — 2026-05-01

### Added
- A.1: `app/gui/add_link_tag_dialog.py` (~210 LOC) com scheme combo + preview
- A.2: `MainWindow._documents_registry` + `register_document/navigate_to_document`
- 11 tests Link Tag navigation
- Categoria A 100% encerrada

---

## [3.5.1] — 2026-05-01

### Added
- A.3: Wire path-based detection (perpendicular distance to L-routed path)
- `_point_to_segment_distance` + `_point_to_l_route_distance` helpers
- 18 tests wire detection

### Changed
- `_find_wire_at` usa fast bbox prefilter + perpendicular distance

---

## [3.5.0] — 2026-05-01

### Added
- `app/preprocessor/scenarios.py` (~250 LOC) — Scenario Manager com PromotionMode
- `app/gui/scenario_manager_dialog.py` (~200 LOC) wired no Ferramentas menu
- 18 tests Scenario Manager
- 8ª garantia formalizada: `docs/CONTEXT_PRESERVATION_PROTOCOL.md`

---

## Histórico anterior (v0.x → v3.4.0)

Para versões anteriores, consulte `docs/v3.4.0_HANDOFF.md` e os
arquivos `docs/v<X.Y.Z>_HANDOFF.md` correspondentes.

---

## Standards cobertos (cumulativo)

* **IEC 60909-0:2016** — Short-circuit currents
* **IEC 60076-1:2011** — Power transformers
* **IEC 60364-5-52:2009** — Cable sizing
* **IEEE Std 1366-2012** — Distribution Reliability Indices
* **IEEE Std 493-2007** — Gold Book (component reliability)
* **IEEE Std 399-1997** — Brown Book (industrial PF)
* **IEEE Std 1584-2018** — Arc Flash
* **IEEE Std 242-2001** — Buff Book (coordination)
* **NFPA 70E:2024** — Workplace electrical safety
* **NBR 5410** — Instalações BT
* **NBR 17227:2025** — Arc-flash classes

## License

Public domain ipotem. Uso acadêmico (Doutorado UFMG) — Landerson Ferreira Silva.
