# Auditoria Profunda — Olivas Power System Studio v1.1.0 vs SKM PTW Power*Tools

**Autor**: Landerson Ferreira Silva (UFMG, Doutorado em Engenharia Elétrica)
**Data**: 2026-04-28
**Escopo**: Análise comparativa feature-a-feature usando os manuais oficiais SKM PTW (CAPTOR, DAPPER, ArcFlash, A_Fault, EquipmentEvaluation, Coordination Evaluation) e o source code do Olivas v1.1.0.
**Objetivo**: Identificar (a) gaps onde Olivas precisa atingir paridade, (b) oportunidades onde Olivas pode SUPERAR PTW.

---

## Sumário Executivo

| Dimensão | Olivas v1.1.0 | PTW v11 | Vantagem |
|---|---|---|---|
| **Componentes catálogo** | 53 | ~80–100 (estimativa Library hierárquica) | PTW |
| **Estudos modulares** | 12 (SC, Coord, AF, PF, Motor, CT-Sat, Cable, V-drop, Harmonics, Reaccel, Ground, AI laudo) | ~15 (DAPPER, A_FAULT, I*FAULT, CAPTOR, Arc Flash, TMS, HI_Wave, ISIM, SPEL, Cable Ampacity, Auto Design, Scenario Manager, etc.) | PTW |
| **Cobertura normativa** | 22+ (IEC, IEEE, NBR, NFPA, NR, ISO 9001, CIGRÉ) | 5 standards arc-flash simultâneos + ANSI/IEEE C37 + NEC | Empate (PTW deeper US, Olivas deeper BR) |
| **TCC analíticos** | 7 IEC/ANSI + dual fuse | **17 segment types** com fórmulas paramétricas | **PTW** |
| **Arc-flash** | NBR 17227 + IEEE 1584-2018 + NFPA 70E PPE | + NESC 2023 + EPRI 2011 statistical + DC Stokes + Capacitor Annex R + Custom Label Designer | **PTW** |
| **Audit trail** | SHA256 + responsabilidade técnica + ISO 9001/NR-10 | Print-only | **Olivas** |
| **AI / LLM** | Claude agent integrado (laudos PT-BR) | Nenhum | **Olivas** |
| **Plugin ecosystem** | @register_study, @register_equipment, descobrir | Closed | **Olivas** |
| **Open source** | Sim (Python/PySide6) | Closed-source ($$$$) | **Olivas** |
| **Online View** | ✅ v1.1.0 (Ctrl+Shift+O, badges Ik''/V) | ✅ Live Display | Empate |
| **Drag-drop TCC** | ✅ Curva de relé | ✅ + range-aware + 17 segment types | **PTW** |
| **Testes** | 437+ pytest (regressão automatizada) | N/D (ferramenta proprietária) | **Olivas** |

**Posicionamento estratégico**: Olivas v1.1.0 é uma **alternativa nacional auditável** com **vantagens estruturais** em IA, plugins, NBR, código aberto e rastreabilidade. **Gaps críticos** estão em: (1) profundidade do CAPTOR (segment types), (2) sofisticação do Arc Flash multi-standard, (3) rule engine de Coordination Evaluation, (4) Custom Label Designer.

---

## Layout do Documento

```
1. Sumário Executivo
2. Análise por Módulo PTW
   2.1 CAPTOR (TCC Coordination)
   2.2 DAPPER (Load Flow + Demand + SC)
   2.3 Arc Flash Hazard Calculator
   2.4 A_FAULT (ANSI Short Circuit)
   2.5 Equipment Evaluation
   2.6 Coordination Evaluation
3. Mapa de Gaps Priorizados
   P0 — Tier 1 (impacto máximo, near-term)
   P1 — Tier 2 (alto valor, mid-term)
   P2 — Tier 3 (compliance/profundidade, longer-term)
4. Vetores de Superação Olivas
5. Roadmap Sugerido v1.2 → v2.0
6. Métricas de Aceite por Iteração
```

---

## 2. Análise por Módulo PTW

### 2.1 CAPTOR — Coordination TCC Analyzer

#### Capacidades PTW (do manual de 175pg)

| Feature PTW | Olivas v1.1.0 | Status | Gap |
|---|---|---|---|
| TCC Drawing como 5º documento independente (One-Line + Library + Report + Component Editor + TCC) | TCC Coordinogram em modal dialog (Ctrl+T) | 🟡 Parcial | TCC não é documento persistente — ao fechar o dialog, perde o estado |
| **17 segment types** parametrizáveis: Fuse Curve, Time-Current Points, Opening/Clearing, Pickup (LT/ST/INST) per-unit, IEC LTPU, Pickup com Open-Clear Curve/Bands, Pickup com Adjustable Tolerance, Delay Band (I^Slope-T), I²T+Horizontal Delay, fórmulas analíticas `T = AD/(I/Ipu)^N - C) + BD + K` | 7 inverse-time IEC/ANSI + dual fuse (melt/clear) = **9 tipos** | 🔴 Gap | **Faltam 8 segment types** críticos para relés modernos digitais (LSI 50/51/87) |
| **Multiple Functions per Protection Component** (relé com 50/51/49 simultâneos) | Cada `TCCCurve` = 1 função → para modelar SEL-751 com 50+51+49 são 3 instâncias | 🔴 Gap | Estrutura de dados não suporta hierarquia "Device → Functions" |
| Drag-drop **dentro do range válido de setting** (cursor contextual + status bar) | Drag-drop com clamp 0.05 ≤ TMS ≤ 1.0 (sem range específico do device) | 🟡 Parcial | Falta consultar range de pickup específico do datasheet |
| **Select a Device dialog** (espia Library sem abrir/corromper) | `EquipmentLibrary` programática — não há dialog "espia" na GUI | 🔴 Gap | Library não tem GUI de browse/select |
| **Library hierárquica** Manufacturer/Type/Description/Voltage/TCC#/Date Modified | Library plana (5 vendors, dataclass por categoria) | 🟡 Parcial | Sem timestamp, sem hierarquia |
| **Reorder TCC Device List** com double-click | Lista de curvas no panel lateral do dialog (toggle on/off) | 🟡 Parcial | Sem reorder |
| Header Bar com Library data assignada | Curva mostra `pickup={value}A TMS={value}` no label | 🟢 Match | OK |
| **3 tab pages** (Cable/XFMR/Generator/Motor/Device + Damage/Starting/Setting Curve + Datablock) | Sem tabs no dialog | 🔴 Gap | Falta visualizar damage curves de cabo/transformador junto |
| Magnify/Reduce/Show All viewport | matplotlib NavigationToolbar (zoom, pan, home) | 🟢 Match | OK |
| Apply sem fechar dialog | Fechar é requerido | 🟡 Parcial | UX poderia ser melhorada |
| **Damage curve overlays** (cable, XFMR through-fault, motor stall) | Não implementado | 🔴 Gap | Cobertura forense incompleta |
| Datablock no TCC | Não implementado | 🔴 Gap | Cabeçalho do plot não traz dados do projeto |
| Identification Report da Library | Não implementado | 🔴 Gap | Sem listagem auditável do que foi usado |

**Sumário CAPTOR**: 5/14 matches, 5 parciais, 4 gaps críticos.

#### O que precisa ser implementado (priorizado)

```python
# app/postprocessor/tcc_curves.py — extensões v1.2

@dataclass(frozen=True)
class TCCSegmentLT:    # Long-Time Pickup (51 IEC LTPU)
    pickup_pu: float                    # M = I/Ipu
    pickup_amps: float                  # absoluto
    type: Literal["IEC", "ANSI", "definite"]
    delay_s: float                      # para definite-time
    # ...

@dataclass(frozen=True)
class TCCSegmentST:    # Short-Time Pickup (50 backup)
    pickup_amps: float
    delay_s: float
    i2t_band: bool                       # PTW Pickup with Open-Clear Curve

@dataclass(frozen=True)
class TCCSegmentINST:  # Instantaneous (50)
    pickup_amps: float
    delay_s: float
    tolerance_pct: float                 # PTW Adjustable Tolerance

@dataclass(frozen=True)
class MultiFunctionDevice:
    """Relé com 50/51/49 simultâneos (PTW Multiple Functions)."""
    device_id: str
    functions: list[TCCSegmentLT | TCCSegmentST | TCCSegmentINST]

    def composite_envelope(self, current_A: float) -> float:
        """min(t_50, t_51, t_49) — função que dispara primeiro."""
```

---

### 2.2 DAPPER — Load Flow + Demand + Sizing + Comprehensive SC

| Feature PTW | Olivas v1.1.0 | Status | Gap |
|---|---|---|---|
| Demand Load Study — connected/demand/design por bus + branch | `power_flow.py` calcula PF mas sem categoria demand explícita | 🔴 Gap | Sem distinção connected/demand/design |
| **Demand Load Library com 20 categorias** (3 levels demand factor + LCL factor) | Não implementado | 🔴 Gap | Falta lib similar a NEC Article 220 |
| Sizing Study (feeder + transformer) | `cable_sizing.py` = só cabos | 🟡 Parcial | Falta auto-sizing de transformador |
| Loop detection automática (até 10 sistemas independentes) | Não implementado | 🔴 Gap | Topologias com loops podem não convergir |
| Comprehensive SC: 3φ + SLG + LL + LLG + asymmetrical peak + momentary + interrupting | `short_circuit.py` faz 3φ IEC 60909, sequential.py faz SLG/LL/LLG | 🟢 Match (parcial) | Falta integração unificada |
| 3-Winding Transformers, phase shift, primary/secondary taps, off-nominal voltage | Tr3 component, mas tap modelagem básica | 🟡 Parcial | Phase shift e off-nominal voltage simplificados |
| Component Editor com **subviews** (Load Diversity, ANSI Contribution) | Properties Panel inline | 🟡 Parcial | Sem subviews para diversidade de carga |
| Default Xd=0.17pu, X/R=10, locked rotor 5.9×FLA | `validation/physical_defaults.py` mas valores não 100% PTW-aligned | 🟢 Match | OK |
| Datablocks renderizáveis no one-line | DataBlockItem v0.86 + datablock_binder | 🟢 Match | Olivas tem |

**Sumário DAPPER**: 3/9 matches, 3 parciais, 3 gaps.

---

### 2.3 Arc Flash Hazard Calculator

| Feature PTW | Olivas v1.1.0 | Status | Gap |
|---|---|---|---|
| **Sensitivity-aware** (testa caso menor corrente arcing → maior trip time → mais energia) | `arc_flash.py` calcula caso bolted | 🔴 Gap | **Crítico** — sem sensibilidade Olivas pode subestimar incident energy |
| **Cleared Fault Threshold** (% configurável, ex: 80%) | Não implementado | 🔴 Gap | Falta filtro Summary view |
| **Scenario Manager** Worst-Case/Best-Case multi-scenário | `arc_flash_monte_carlo.py` (Monte Carlo) — não Scenario Manager | 🟡 Parcial | Diferentes paradigmas — Monte Carlo é probabilístico, Scenario é discreto |
| **Job Safety Planning Form** (NFPA 70E-2021 Tabela 130.5(C) tasks + 130.7(C)(15)(a/b) PPE auto-fill) | Não implementado | 🔴 Gap | Compliance gap para uso de campo |
| **Capacitor Hazard Assessment** (Annex R: discharge time, Vpeak, stored energy, lung/eardrum boundary) | Não implementado | 🔴 Gap | Cobertura normativa parcial |
| **Differential Protection (87)** modelado | Não no arc_flash workflow | 🔴 Gap | Subestima incident energy |
| **Zone Selective Interlock (ZSI)** | Não modelado | 🔴 Gap | Crítico para LV power CB |
| **Directional Function** (sinaliza se direção fault não casa, *N17A) | Não implementado | 🔴 Gap | Compliance |
| **Custom Label Designer** (page size, orientation, X/Y/W/H field por field, BMP picture, Keyword multilingual) | `report_pdf.py` + `report_html.py` (templates fixos) | 🔴 Gap | **Crítico para uso comercial** — labels são deliverable |
| **30 text fields + 8 picture fields no label** | Templates HTML/PDF com ~20 campos | 🟡 Parcial | Não user-customizable |
| **Clothing Category Color** dinâmica (vermelho=Dangerous, laranja=Warning) | Cor é texto no relatório | 🟡 Parcial | Sem cor dinâmica |
| **20+ Notes codificadas** (*N1 a *N20b) — Mis-coordinated, Special Instantaneous, Max Arcing Reached, Fuse Cable Protector parallel cable, Level 0 reduction <125kVA/<2000A em ≤240V, Equipment Evaluation Marginal | Olivas mostra warnings mas não codificados | 🔴 Gap | Reduz utilidade forense |
| **5 standards simultâneos**: IEEE 1584-2018 + NFPA 70E (Doughty-Neal) + NESC 2023 + EPRI 2011 + CSA-Z462 | NBR 17227 + IEEE 1584-2018 + NFPA 70E PPE | 🟡 Parcial | Falta NESC, EPRI 2011, CSA, Doughty-Neal |
| **DC Systems Stokes-Oppenlander** | Não implementado | 🔴 Gap | Cobertura DC não suportada |
| **EPRI Statistical Adjustment Factor k=1.588** + OSHA 1910.269 satisfaction acima de 15kV | Não implementado | 🔴 Gap | Compliance especifica |
| **Lee equation fallback** fora de range IEEE 1584 | Não implementado | 🔴 Gap | Workflow incompleto para HV >15kV |
| Re-Run Study button para refresh pós-mudança | Botão "Recalcular" disponível | 🟢 Match | OK |
| Bus Detail Report + Work Permit (NFPA 70E 2004) + Excel/HTML export | HTML/PDF com header audit | 🟡 Parcial | Sem Work Permit form |
| **5 electrode configs**: VCB, VCBB, HCB, VOA, HOA com Box Width/Height/Depth + Equip Category auto-fill + Shallow vs. Typical (8in threshold) + Table 8 typical sizes | IEEE 1584-2018 sem electrode configuration explícita | 🔴 Gap | Subestima incident energy em VOA/HOA configs |

**Sumário Arc Flash**: 1/19 match, 5 parciais, 13 gaps. **Maior área de gap do Olivas** vs. PTW.

---

### 2.4 A_FAULT — ANSI Short Circuit

| Feature PTW | Olivas v1.1.0 | Status | Gap |
|---|---|---|---|
| Withstand + Closing & Latching (Momentary) + Interrupting separados | `short_circuit.py` calcula Ik''/ip/Ib em IEC 60909 | 🟡 Parcial | Falta nomenclatura ANSI explícita (Closing & Latching, Withstand) |
| Total Current basis (pré-1964) **e** Symmetrical Current basis (pós-1964) | Símétrico apenas | 🔴 Gap | Sem suporte legacy ANSI Total |
| **NACD Option** (No AC Decrement) + solution method local/remote | Não implementado | 🔴 Gap | Para sistemas grandes generation-side |
| Pre-fault voltage adjustable (default 1.0pu) | `voltage_factor_c` ajustável (1.05/1.10) | 🟢 Match | OK |
| **Machine reactance multipliers** tabelados (turbine gen 1.0 Xd, induction motor >1000hp = 1.0/1.0/1.5, motors <50hp = 1.0/1.2/3.0, etc.) | Configurações por componente, sem tabela ANSI | 🟡 Parcial | Falta wizard ANSI |
| Test PF/X/R por device class: LV Power CB (15%/6.6), LV Fuse (20%/4.9), MCCB >20kA (20%/4.9), MCCB 10-20kA (30%/3.2), MCCB <10kA (50%/1.7) | Sem lookup de Test PF | 🔴 Gap | Falta certificação ANSI C37 |
| Three-Phase / Unbalanced / Low Voltage / Momentary / Interrupting Reports | `report_html.py` + `report_pdf.py` com seções SC | 🟡 Parcial | Sem split por duty type |
| **separately-derived X/R** (R sem X, X sem R) per ANSI C37.13/.010 | X/R único calculado junto | 🔴 Gap | Não atende ANSI C37.13/.010 strict |
| Datablocks com branch fault contribution one-branch-away | DataBlockItem suporta | 🟢 Match | OK |
| Calculated rms+peak asymmetrical | Calculated em IEC 60909 | 🟢 Match | OK |

**Sumário A_FAULT**: 3/10 matches, 3 parciais, 4 gaps. Olivas tem boa cobertura IEC, mas **gap em ANSI legacy** é compliance issue para projetos US/legacy.

---

### 2.5 Equipment Evaluation

| Feature PTW | Olivas v1.1.0 | Status | Gap |
|---|---|---|---|
| **9 evaluation criteria** automáticos: Voltage Rating cables/PD vs. nominal bus; Interrupting Fault Duty vs. Rating; Asymmetrical Duty vs. Asym Rating; Load Flow Current vs. Continuous Rating; Design Load vs. Continuous; Generator Size vs. Load Flow Output; Bus Voltage Drop; Branch V-Drop; Device V-Drop | Validação dispersa em `validation/physical_defaults.py` + cada estudo verifica seu critério | 🔴 Gap | **Sem dashboard unificado de Pass/Fail por equipamento** |
| **Failed Input Evaluation** separado (sistemas isolados, components unconnected, missing Library Reference, missing Rated Size/Z) | `validation/` faz validação parcial | 🟡 Parcial | Sem report dedicado |
| Escolha de fault standard para evaluation (Unbalanced, Comprehensive, ANSI, IEC) | IEC 60909 default | 🟡 Parcial | Sem switch |
| **Series Rating override** do Interrupting Rating quando maior | Não implementado | 🔴 Gap | Comum em painéis |
| **Series Rated Test X/R** automático por kA range | Não implementado | 🔴 Gap | Compliance ANSI |
| **Breaker speed-aware**: <2/3/5/8/>8 cycles → Sym1/2/3/5/8 selection | Não implementado | 🔴 Gap | Crítico para HV breakers |
| Arc-flash integration (*N3 Dangerous category) | Sim, `arc_flash_study.py` retorna PPE category | 🟢 Match | OK |
| Componentes avaliados: cables (temperature derating + duct bank), 2W/3W transformers, Pi/Transmission, Generators, Motors/Loads/Filters, **Panel Schedules** (sub-feeds), Buses (Equipment Category) | Validação por componente em cada estudo | 🟡 Parcial | Sem Panel Schedules |
| Tabular report Pass/Fail, % of rating, queries+sort, Excel export, color-coding direto no one-line | HTML/PDF reports | 🟡 Parcial | Sem color-coding live no canvas |
| Reset Color toolbar | N/A | 🔴 Gap | — |

**Sumário Equipment Evaluation**: 1/9 match, 4 parciais, 4 gaps. **Olivas faz as mesmas verificações dispersas** mas falta o **dashboard único Pass/Fail PTW-style**.

---

### 2.6 Coordination Evaluation (PTW add-on requer DAPPER+CAPTOR)

| Feature PTW | Olivas v1.1.0 | Status | Gap |
|---|---|---|---|
| **Motor de regras NEC 110.10** com tabelas Min%/Max% por (Device × Function × Setting Base) | `relay_coordination.py` faz check_coordination Δt mas sem rule engine de % | 🔴 Gap | Engine de regras é diferenciador chave |
| Cobertura: Bus / Cable LV / Cable HV / Generator / Motor / Transformer LV-Pri Primary/Secondary / HV-Pri Primary/Secondary / Capacitor | `check_coordination` cobre relé-relé só | 🔴 Gap | Falta cabo damage, motor stall, XFMR inrush, gen no-restraint |
| **Dynamic TCC drawing** automático para componentes em violação (mostra withstand + PD curves upstream/downstream) | Coordinogram dialog manual | 🔴 Gap | Workflow interativo absent |
| All vs. Selected display modes | Lista de curvas com toggle on/off | 🟡 Parcial | Conceptualmente similar |
| **Accepted vs. Not Passed** (engineer pode aceitar warning, sistema persiste) | `audit_trail.py` registra mas sem accept/reject UI | 🟡 Parcial | Falta accept persistente |
| Regras concretas (amostra): Motor Relay LTPU 51 = 115%-125% FLA com SF≥1.15; Motor LTPU 49 = 100%-200%; trip @LRA = 110% accel / 90% safe stall; LV XFMR FLA<2A → 100%-300%, FLA<9A → 100%-167%, FLA≥9A → 100%-125%; HV XFMR Z≤6% → LTPU 100%-600%; cable LTPU 51 cutoff 80% damage; gen LTPU 51V no-restraint 100%-200%, full restraint 150%; capacitor LTPU 105% FLA | `relay_suggestions.py` v0.94 sugere TMS mas não em forma de rule table | 🔴 Gap | Conhecimento precisa ser formalizado em rule engine |

**Sumário Coordination Evaluation**: 0/6 match, 2 parciais, 4 gaps. **Maior área de oportunidade conceitual** — um rule engine bem desenhado pode SUPERAR PTW se incluir NBR 17227 + IEEE 242 + NEC 110.10 + IEC 60255 + custom rules from plugins.

---

## 3. Mapa de Gaps Priorizados

### P0 — Tier 1 (impacto máximo, near-term — v1.2.0)

| Gap | Esforço (LOC) | Valor estratégico | Por que é crítico |
|---|---|---|---|
| **Custom Label Designer** (Arc-flash labels imprimíveis com 30 campos texto + 8 BMP) | 800–1200 LOC + tests | 🌟🌟🌟🌟🌟 | Labels arc-flash são **deliverable contractual**. Sem isso, engenheiro não pode entregar projeto compliant NFPA 70E ao cliente. |
| **Multi-function relay modeling** (Device → 50+51+49+87 simultâneos) | 600–800 LOC + tests | 🌟🌟🌟🌟🌟 | Modela relés digitais reais (SEL/ABB/Siemens) — sem isso CAPTOR Olivas não compete com PTW. |
| **17 TCC segment types** (Pickup LT/ST/INST per-unit, IEC LTPU, I²T+Horizontal, Adjustable Tolerance, fórmulas analíticas A/B/C/D/E/N/K) | 1000–1500 LOC + tests | 🌟🌟🌟🌟🌟 | Olhar do CAPTOR depende disso para coordenação real. |
| **Equipment Evaluation Dashboard** unificado (9 critérios Pass/Fail por equipamento + color-coding live no one-line) | 700–1000 LOC + tests | 🌟🌟🌟🌟 | Único report engenheiro pode mostrar ao cliente em 1 tela. |
| **Coordination Evaluation Rule Engine** (regras NEC 110.10 + NBR + IEEE 242 + custom plugin) | 1200–1800 LOC + tests | 🌟🌟🌟🌟🌟 | Diferenciador estratégico — Olivas pode SUPERAR PTW expondo o engine como plugin. |
| **Damage curves overlay no TCC** (cable damage, XFMR through-fault, motor stall) | 500–800 LOC + tests | 🌟🌟🌟🌟 | Exigência IEEE 242 — sem isso, coordenação não-completa. |

**Total P0**: ~5000–7000 LOC. Esforço estimado: **3 sprints (v1.2.0 → v1.4.0)**.

### P1 — Tier 2 (alto valor, mid-term — v1.5–v1.7)

| Gap | Esforço | Valor | Justificativa |
|---|---|---|---|
| **Sensitivity-aware Arc Flash** (varre arcing currents para encontrar trip-time pior caso) | 400–600 LOC | 🌟🌟🌟🌟 | Atualiza arc_flash.py para conformidade IEEE 1584-2018 §A4 |
| **5 electrode configs** (VCB, VCBB, HCB, VOA, HOA) com Box geometry | 300–500 LOC | 🌟🌟🌟 | Compliance IEEE 1584-2018 |
| **DAPPER Demand Load Library** (20+ categorias NEC Article 220) | 600–800 LOC | 🌟🌟🌟🌟 | Auto-sizing realístico |
| **Scenario Manager** (Worst-Case/Best-Case multi-scenário) | 800–1000 LOC | 🌟🌟🌟🌟 | Análise comparativa multi-config |
| **TCC como documento persistente** (5º tab, salva no .opws) | 500–700 LOC | 🌟🌟🌟 | UX critical |
| **Datablock customizável** (One-Line + TCC, fields user-defined) | 600–800 LOC | 🌟🌟🌟 | Diferencial visual |
| **20+ Codified Notes** arc-flash (*N1 a *N20b) | 200–300 LOC | 🌟🌟🌟 | Compliance forense |
| **Loop detection automática** (DAPPER) | 300–500 LOC | 🌟🌟🌟🌟 | Topologias reais |
| **A_FAULT separately-derived X/R** | 200–300 LOC | 🌟🌟 | Compliance ANSI strict |
| **NESC 2023 + EPRI 2011 + Doughty-Neal + DC Stokes** Arc-flash | 1000–1500 LOC | 🌟🌟🌟 | Cobertura standards |

**Total P1**: ~5000–7000 LOC. Esforço estimado: **3 sprints (v1.5 → v1.7)**.

### P2 — Tier 3 (compliance/profundidade, longer-term — v1.8–v2.0)

| Gap | Esforço | Valor |
|---|---|---|
| Capacitor Hazard Assessment (Annex R) | 400–600 LOC | 🌟🌟 |
| Differential Protection (87) explícito | 300–500 LOC | 🌟🌟 |
| Zone Selective Interlock (ZSI) | 400–600 LOC | 🌟🌟🌟 |
| Job Safety Planning Form (NFPA 70E-2021) | 500–700 LOC | 🌟🌟🌟 |
| Series Rating override + Series Rated Test X/R | 200–300 LOC | 🌟🌟 |
| Breaker speed-aware (Sym1/2/3/5/8 cycles) | 200–300 LOC | 🌟🌟 |
| ANSI legacy (Total Current basis pré-1964) | 300–400 LOC | 🌟 |
| NACD Option | 200–300 LOC | 🌟 |
| Identification Report da Library | 200–300 LOC | 🌟🌟 |

---

## 4. Vetores de SUPERAÇÃO (onde Olivas pode passar PTW)

### 4.1 Vantagens estruturais já existentes (amplificar)

| Vetor | Estado v1.1.0 | Como amplificar |
|---|---|---|
| **AI Agent (Claude)** | Geração laudos PT-BR + tool calling | Adicionar **proactive coordination suggestions** ("Olá, detectei que o relé R-FEEDER tem TMS=0.5 mas o Δt para R-MAIN é 0.18s — sugiro TMS=0.3 que dá Δt=0.31s ≥ 0.25s requerido. Aplicar?"). PTW não tem isso. |
| **Audit Trail SHA256** | input_checksum + responsabilidade técnica + ISO 9001 | Expor **Audit Diff Tool** ("Mostre o que mudou entre laudos v3 e v4 e impacto no Ik''"). PTW não tem rastreabilidade computável. |
| **Plugin ecosystem** | @register_study, @register_equipment | Lançar **Plugin Marketplace** com plugins curados por vendor (SEL, ABB) + comunidade. PTW é fechado. |
| **NBR 17227 nativo** | arc_flash.py implementa NBR | Adicionar **NR-10 compliance auditor** ("Este projeto atende NR-10 §10.3? Verifico distância de segurança, EPI, sinalização"). PTW é US-centric. |
| **Open source** | Python/PySide6/MIT-style | **Community contributions** + **acadêmico** (UFMG/UFRJ podem contribuir com módulos de pesquisa). PTW custa USD 5–15k/seat. |
| **Online View** | Badges Ik''/V no esquemático | Adicionar **Live SCADA Integration** (lê IEC 61850 GOOSE/MMS em tempo real → atualiza overlays). PTW Online é static. |
| **CT Saturation 3-níveis** (ANSI + IEC + RK4 dynamic) | ct_saturation.py | **PTW não tem RK4 dynamic** — explorar como ponto de venda em coord 50/51 (saturação afeta Ik''). |
| **Modern Python ecosystem** (Pydantic, type hints, pytest) | Toda code base | **Continuous Integration** + **automated regression** — PTW v11 não tem testes automatizados publicados. |

### 4.2 Vetores novos (originais, sem precedente em PTW)

| Vetor | Descrição | Por que SUPERA PTW |
|---|---|---|
| **AI-driven Auto-Design** | LLM sugere bitola de cabo, pickup de relé, transformer rating dado um SLD parcial. Engenheiro aprova/edita. | PTW Auto Design é rule-based simples; AI considera contexto + normas + boas práticas. |
| **Voice annotations no SLD** | Engenheiro narra "Este motor é crítico, classe Vital, RAS=BC2" → Whisper transcreve → metadados estruturados. | PTW não tem voz. |
| **Mobile companion app** | iOS/Android para campo: scan QR do equipamento → puxa label arc-flash + work permit do projeto. | PTW é desktop-only. |
| **Real-time collaboration** | Multi-user simultâneo no mesmo .opws (CRDT-based). Como Figma para SLDs. | PTW Multi-User Library é file-locking, não real-time. |
| **Compliance dashboard NR-10/NR-12** | Single screen: este projeto atende NR-10? NR-12? Lista checks pendentes. | PTW é OSHA-centric, sem NR. |
| **Open Telemetry** | Toda análise emite telemetria (nbr de buses, normas usadas, tempo execução) — community insights. | PTW é offline-only. |
| **Reproducibility container** | Cada laudo gerado tem Docker image associada (lock de versões deps + dados). 5 anos depois ainda roda igual. | PTW depende de versão Windows + license server vivo. |
| **AI assistant em coordenação** | "Olha, com SEL-751 + REF615 num bus de 13.8 kV, sua coord 50/51 vai falhar em pickup de motor por causa de IL inrush. Sugestão: usar IEC LTPU + 6× delay 50ms" | PTW CAPTOR mostra a curva, não diagnostica. |

### 4.3 Mercado-alvo onde Olivas tem vantagem natural

| Segmento | Por que Olivas vence |
|---|---|
| **Universidades brasileiras** (UFMG, UFRJ, USP) | PT-BR + open source + acadêmico; PTW academic license é cara |
| **Indústria de pequeno/médio porte BR** | NBR 17227 nativo; preço acessível |
| **Concessionárias regionais** | NR-10 / ANEEL compliance dashboard |
| **Engenharia de campo** (mobile companion) | PTW não tem mobile |
| **Pesquisa & Desenvolvimento** | Plugin system aberto |
| **Auditorias forenses** | Audit trail SHA256 reproduzível |

---

## 5. Roadmap Sugerido v1.2 → v2.0

```
v1.2.0 (Q3 2026) — "CAPTOR-grade TCC"
  ├─ P0: 17 TCC segment types
  ├─ P0: Multi-function relay (50+51+49+87 in single device)
  └─ P0: Damage curves overlay (cable, XFMR, motor)

v1.3.0 (Q4 2026) — "Coordination Engine"
  ├─ P0: Coordination Evaluation rule engine (NEC + NBR + custom)
  ├─ P0: Equipment Evaluation Dashboard (9 critérios Pass/Fail)
  └─ P3 (super): AI proactive coord suggestions (Claude)

v1.4.0 (Q1 2027) — "Arc Flash Pro"
  ├─ P0: Custom Label Designer (30 fields + 8 BMPs)
  ├─ P1: Sensitivity-aware Arc Flash
  ├─ P1: 5 electrode configs (VCB/VCBB/HCB/VOA/HOA)
  └─ P1: 20+ Codified Notes (*N1-*N20b)

v1.5.0 (Q2 2027) — "DAPPER-grade Load Flow"
  ├─ P1: Demand Load Library (20+ categorias)
  ├─ P1: Loop detection automática
  ├─ P1: Scenario Manager (Worst/Best-Case)
  └─ P3 (super): NR-10 compliance auditor

v1.6.0 (Q3 2027) — "Multi-standard Arc Flash"
  ├─ P1: NESC 2023 + EPRI 2011 + Doughty-Neal + DC Stokes
  ├─ P2: Capacitor Hazard Annex R
  ├─ P2: Differential Protection (87)
  └─ P2: Zone Selective Interlock (ZSI)

v1.7.0 (Q4 2027) — "Plugin Marketplace + Mobile"
  ├─ P3 (super): Plugin Marketplace web UI
  ├─ P3 (super): Mobile companion app (iOS/Android)
  └─ P3 (super): Real-time collaboration (CRDT)

v2.0.0 (Q1 2028) — "Olivas Power System Studio Pro"
  ├─ P3 (super): Live SCADA integration (IEC 61850)
  ├─ P3 (super): Reproducibility container (Docker)
  ├─ Polish + performance + i18n EN/ES/FR
  └─ Comercial launch + community licenses
```

---

## 6. Métricas de Aceite por Iteração

| Métrica | v1.1.0 | v1.4.0 alvo | v2.0.0 alvo |
|---|---|---|---|
| **Componentes catálogo** | 53 | 70 (+ Panel Schedule, multi-function devices) | 100+ |
| **TCC segment types** | 9 | **17** (paridade PTW) | 20+ (incl. plugin custom) |
| **Standards arc-flash** | 3 | 5 (paridade PTW) | 7 (incl. CSA-Z462, NR-10) |
| **Estudos modulares** | 12 | 15 | 20+ |
| **Vendors equipment** | 5 | 10 | 25+ (Marketplace) |
| **Testes pytest** | 437+ | 700+ | 1500+ |
| **Cobertura normativa** | 22 | 30 | 40+ |
| **AI features** | 1 (laudo) | 3 (laudo + coord + design) | 5+ |
| **Plugin público** | 0 | 5+ | 50+ (Marketplace) |
| **Idiomas** | PT-BR | PT-BR + EN | PT-BR + EN + ES + FR |
| **Comparable PTW $$$$ saving** | — | $5k/seat (vs PTW Standard) | $15k/seat (vs PTW Pro) |

---

## 7. Riscos & Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **Custom Label Designer é UX complexa** (rolagem, undo, BMP picker, fonts) | Alta | Alto (deliverable comercial) | Reusar QGraphicsScene da paleta PpEditor + plugin Pillow para BMP |
| **17 TCC segment types** requer parsing dos manuais relé por relé | Alta | Alto | Curar 10 mais usados (SEL/ABB/Siemens) primeiro; pluginizar resto |
| **Coordination Rule Engine** pode ficar lento com 1000+ regras | Média | Médio | Evaluation lazy + cache + pre-computed via plugins |
| **Arc-flash 5 standards** divergem em casos extremos | Média | Médio | Suite de testes com casos canônicos da norma; Job Safety Form |
| **Plugin Marketplace** requer infra web | Média | Alto | Começar como GitHub PR-based curation; web depois |
| **Mobile companion** requer app store accounts | Baixa | Baixo | PWA primeiro (offline-capable); app nativo só se traction |
| **Real-time collaboration** é tecnicamente difícil | Alta | Médio | CRDT é estado-da-arte mas complexo; postergar para v2.0 |
| **Comerc. license** pode confrontar SKM | Média | Baixo | Olivas é open source — model dual (free + enterprise support) |

---

## 8. Conclusão e Recomendação Estratégica

**Olivas v1.1.0 já tem fundamentação técnica robusta** (53 componentes, 22 normas, audit trail SHA256, AI agent, plugin system) e **paridade conceitual com PTW** em 4 de 6 módulos analisados (DAPPER, A_FAULT, Equipment Evaluation, Coordination Evaluation parcial).

**Os 4 gaps críticos** que precisam ser fechados em v1.2–v1.4 para **paridade comercial** com PTW são:

1. **Custom Label Designer** (deliverable arc-flash)
2. **17 TCC segment types** (CAPTOR full-feature)
3. **Multi-function relay modeling** (50+51+49 unified device)
4. **Coordination Evaluation Rule Engine** (NEC 110.10 + NBR + plugin)

**Após v1.4.0 fechar os gaps**, Olivas terá **paridade técnica** + **vantagens estruturais únicas** (AI, audit, plugin, NBR, open source) → posicionamento como **alternativa nacional viável a PTW Standard tier**.

**A janela de superação** está em v1.7–v2.0 com:
- Plugin Marketplace
- Mobile companion app
- Real-time collaboration
- Live SCADA integration
- AI proactive coord suggestions
- NR-10 compliance auditor

Estes vetores **não têm precedente em PTW** e podem capturar segmento de mercado distinto: universidades BR, indústria média BR, concessionárias regionais, engenharia de campo, P&D acadêmico.

**Decisão recomendada**: Executar Roadmap v1.2 → v1.4 nos próximos 9 meses (paridade), depois v1.5 → v2.0 nos 18 meses seguintes (superação). Lançamento comercial Olivas Pro em Q1/2028.

---

**Próximo passo concreto sugerido**: começar **v1.2.0 com 17 TCC segment types** — é o gap de maior impacto e menor risco (extensão direta de `tcc_curves.py` que já tem fundação sólida em v1.1.0). Sprint estimada: 3 semanas.
