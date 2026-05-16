# PTW Tutorial Audit v3.0.3 — Olivas Power System Studio vs SKM Power*Tools v8.0 (April 2019)

> **Fonte primária**: `D:\000 - UFMG - DOUTORADO\MVP\LIB\PTW Tutorial.pdf` (extraído via pdftotext-layout, 6447 linhas, 366 páginas, 11 partes + Important Concepts + Index).
> **Data da auditoria**: 2026-04-30
> **Olivas baseline**: v3.0.2 (com releases prévios v1.5.0–v3.0.2 considerados).
> **Convenção**: ✅ atende plenamente | ⚠️ parcial/com gaps | ❌ não atende | 🔍 evidência ambígua, requer validação.

---

## A. Inventário PTW Tutorial (índice navegável)

| Cap | Seção | Páginas | Funcionalidade ensinada | Tipo |
|---|---|---|---|---|
| 0 | Important Concepts — Project Files | 5 | Estrutura de projeto em pasta dedicada (.prj + drw + rpt) | Teoria |
| 0 | Important Concepts — Database | 5–6 | Componente único na DB, referenciado em múltiplas one-lines/TCCs | Teoria |
| 0 | Important Concepts — Connecting Components | 6–8 | Regras de impedância entre buses, tie-breakers via Pi-impedance | Teoria |
| 0 | Important Concepts — Navigation | 8–9 | Document types (One-line, TCC, Reports, Data Visualizer, Component Editor, Libraries), Window menu, Go-To navigation | Workflow |
| 0 | Important Concepts — Datablocks | 10–11 | Datablock format display em one-lines/TCCs/reports, link bidirecional com DB | Teoria/Workflow |
| 0 | Important Concepts — Textblocks/Link Tags/Output Forms | 12–13 | Anotações user-defined, links dinâmicos one-line→one-line/TCC/PDF | Workflow |
| 0 | Important Concepts — Reports (4 tipos) | 13–15 | Study text reports (.RPT), Enhanced (.RP2), Datablock reports, Crystal reports | Teoria |
| 0 | Important Concepts — Multiple Scenarios | 16–17 | Cenários comparativos com promoção seletiva de mudanças | Workflow |
| 0 | Important Concepts — Data Visualizer | 17–18 | Spreadsheet com 2-way DB link, Global Change, comparação multi-scenario | Workflow |
| **1** | **Build System Model** | **19–62** | | |
| 1 | Project>Options>Application | 20 | Setar engineering standard (ANSI/IEC) e units (English/Metric) antes de criar projeto | Workflow |
| 1 | Project>New | 20–21 | Criar projeto Tutorial_V8.0, geração automática de pasta | Workflow |
| 1 | One-line + Component Editor | 21–24 | Push-pin placement (não drag-drop), zoom/grid/page guides | Workflow |
| 1 | Add bus + Utility + Transformer + Cable + Load | 24–28 | Toolbar de componentes, conexão via drop em ponto de bus, auto-bus-node em série | Workflow |
| 1 | Symbol Rotation 90° | 28–29 | One-Line>Symbol Rotation>Rotate Right 90° | Workflow |
| 1 | Save One-line (1line001.drw) | 29 | Save manual (drws não auto-saved) | Workflow |
| 1 | Multiple one-lines + Copy/Paste visuais | 30–34 | Document>New, Edit>Copy/Paste entre drws, alterações DB refletem em todos | Workflow |
| 1 | Link Tags | 35–42 | One-line>Link>New Link, atributos (visible/origin/closed-arrow), navegação dinâmica | Workflow |
| 1 | Legend Tags | 43–52 | One-line>Legend Tag>New Legend Tag, formas (Diamond, Hexagon), View>Legend list | Workflow |
| 1 | Component Editor — Voltage entry | 52–54 | Bus Load Diversity Factor, Nominal System Voltage, lista "All" | Workflow |
| 1 | Cable from Library — Copper Magnetic THHN 600V | 54–55 | Library button, Link to Lib checkbox, size/length entry | Workflow |
| 1 | Transformer Library — Oil Air 60Hz, Dry Type | 56–58 | Apply/Close, Calculator buttons p/ %R/%X conversion, neutral impedance | Workflow |
| 1 | Utility — fault contribution | 59 | MVA/kVA/Amps/per-unit, Voltage pu controla pre-fault | Workflow |
| 1 | Datablock display Input Data | 60–62 | Run>Datablock Format, Toggle Datablock Icon | Workflow |
| **2** | **Run DAPPER System Studies** | **63–76** | | |
| 2 | Run>Balanced System Studies | 63–64 | Demand Load + Load Flow + Comprehensive SC, A_FAULT/IEC_FAULT alternativos | Workflow |
| 2 | Study Messages window | 64–65 | Edit Errors button, Fatal Error handling | Workflow |
| 2 | Datablock Format Load Flow Power Data | 66 | Apply em one-line, Bus Fault Currents alt | Workflow |
| 2 | Document>Report — Text/RP2/Crystal/Crystal XI | 67–69 | 4 tipos de output, Convert RPT→RP2, Disable Report Viewer | Teoria |
| 2 | Crystal Report Load Flow Report.rpt | 71 | Tree structure formatos, edição via Crystal Reports v8.0+ | Workflow |
| 2 | Datablock Report (spreadsheet) | 72–75 | Datablock Subview no Component Editor, export Excel | Workflow |
| **3** | **CAPTOR TCC** | **77–108** | | |
| 3 | Add fuse + relay + LV breaker (×2) | 77–82 | New Fuse / New Relay / New Low Voltage Breaker icons | Workflow |
| 3 | Library — Cutler-Hammer CX 15.5kV 4C-40C fuse | 83 | Fuse cartridge selection (40C) | Workflow |
| 3 | Library — GE Multilin 745 Transformer relay 5A CT | 84–85 | Electronic Relay category, OC Pickup + Extremely Inverse default | Workflow |
| 3 | Library — Square D MX Micrologic LS 100-800A breaker | 86 | LV Breaker > Static Trip subgroup, MX 480V 800A frame | Workflow |
| 3 | Library — GE SF Spectra RMS Mag-Break 70-250A | 87–88 | Thermal Magnetic Molded Case sub-category | Workflow |
| 3 | Go To/Find > Go To TCC Drawing | 89–91 | Right-mouse, geração automática TCC1.drw associado | Workflow |
| 3 | TCC editing — drag pickup/curve, Setting tab | 92–95 | OC Pickup 0.8, Ext Inverse 17.0, INST OR 5th segment, Delete Segment | Workflow |
| 3 | Run>TCC Report | 99–101 | Sort by Bus Voltage, individual TCC ou todos, Component Editor "All" | Workflow |
| 3 | TCC Settings datablock | 103–104 | Display settings on TCC, Selected Device Settings menu | Workflow |
| 3 | Crystal Report — TCC Static Trip Breakers | 105–107 | ProtDev_Multi_Functions, _ByBus, _Phase_Ground variants | Workflow |
| 3 | Form Print — TCC & One-Line 8½×11 | 96–98 | Document>Form Print, Group Print | Workflow |
| **4** | **Equipment Evaluation** | **109–117** | | |
| 4 | Run>Equipment Evaluation | 109–110 | Tabela de avaliação, Protective vs Non-Protective icons | Workflow |
| 4 | Balanced/Unbalanced + ANSI/IEC/Comprehensive selectors | 110–111 | Branch vs bus comparison; navegação por tipo (cable, 2-winding TX, 3-winding TX, transmission line, pi, generator, load, ind motor, sync motor, schedule, filter) | Workflow |
| 4 | Report button + Excel export | 112 | Spreadsheet-style report | Workflow |
| 4 | Datablock Device Evaluation Comprehensive Branch | 113 | One-line display de pass/fail + ratings | Workflow |
| 4 | Mark Components Failing / Failed Input Data | 114 | Highlight em vermelho, Component Editor filter | Workflow |
| 4 | Project>Options>Equipment Evaluation | 115–117 | User-defined limits, Continuous Ratings, Schedule circuits, Tie breakers exclude, Pi sub-types exclude | Workflow |
| **5** | **Arc Flash Evaluation** | **119–171** | | |
| 5 | Run>Arc Flash Evaluation | 119–122 | Tabela: Bus Name, PD, Bus kV, Bolted/Arcing, Trip/Delay, Breaker Open, Ground, Equip Type, Gap, AFB, WD, IE, PPE, Label#, Cable Length | Workflow |
| 5 | NFPA 70E 2015 Annex D.3 colunas | 122 | Duration of Arc, Arc Type (Box/Air) | Workflow |
| 5 | DC Systems Annex D.5 colunas | 124 | Bus Eq Resistance (Ω), DC Bolted/Arcing PD Fault, Multiplier safety | Workflow |
| 5 | NESC 2012 colunas | 124–125 | SLG Bolted Fault, Altitude, 3-Phase Multiplier (1.2-2.2 open/3.7-6.5 enclosed), Type of Work (Com/Sup), LL/LG, Separation Distance, MAD, Rubber Insulating Class | Workflow |
| 5 | Detail vs Summary view | 125–126 | Cleared Fault Threshold (default 80%), accumulated energy | Teoria |
| 5 | Scenarios — Best/Worst Case Arc Flash | 126–127 | Multi-scenario IE worst report, *S0/*S1 markers | Workflow |
| 5 | Custom Label, Work Permit (NFPA 70E 2015) | 127 | Label sizes, page margins, work permit doc generation | Workflow |
| 5 | Standard & Unit options | 128–129 | IEEE 1584 (default), NFPA 70E 2015 D.3, NESC 2012, AC SC method (Comprehensive/IEC60909/Unbalanced), Flash Boundary 2.65*MVA*t equation, English/Metric | Teoria |
| 5 | Maximum Arcing Time Duration | 129–130 | Default 2s per IEEE 1584 B.1.2, Global vs per-bus, Use Global Max Arcing Time | Workflow |
| 5 | Arcing Fault Tolerances | 130–131 | IEEE −15%/+10% default, NFPA 38% bolted, IEC60909 min/max | Teoria |
| 5 | Pre-Fault Voltage options | 131–135 | Load Flow / PU All / PU per Bus / No Load with Tap, Utility/Cable/Transformer Tolerance Min/Reg/Max | Workflow |
| 5 | Fixed/Movable for Each Bus, Transformer Tap, Phase Shift, VFD Load Side | 135–136 | Influencia limited approach boundary | Workflow |
| 5 | Defined Ground as SLG/3P Fault % | 136 | Threshold para tratar bus como grounded | Teoria |
| 5 | Reduce Generator/Sync Motor Fault Contribution | 136–137 | Decay step (e.g., 1000%→300% após 10 cycles), Recalculate Trip Time, Apply To Generators/Sync Motors | Teoria |
| 5 | Induction Motor Fault Contribution cycles + hp exclude | 138 | Step change, ignora contribuição após N cycles | Teoria |
| 5 | Fuses: All Current Limiting / All Standard / Specified in Library | 138–140 | ½ ou ¼ cycle reduction logic, current-limiting threshold table | Teoria |
| 5 | Equipment-Specific Incident Energy Equations | 140 | Arc Flash tab no PD library, "Use Equipment-Specific Incident Energy Equations" checkbox | Teoria |
| 5 | Report Options (5): Bus / PD Load Side / PD Line Side / Bus+Line / Bus+Line+Load | 141–143 | Diagrama de aplicação, Worst Case Only, Include Line+Load contributions | Teoria |
| 5 | Report Last Trip Device vs Main Device | 143 | Affects Summary View, Bus Detail, Bus Label | Teoria |
| 5 | Equipment Evaluation Failed → Report IE/PPE / As Overdutied w/o Label | 143 | (*N20a/b), (*N21a/b) markers | Teoria |
| 5 | Device Fail to Operate → Use Upstream | 143–144 | All Mains / Specified in devices / None | Teoria |
| 5 | Check Upstream for mis-coordination | 144–145 | Levels to Search, Mis-Coordination Ratio, conditions 1/2 | Teoria |
| 5 | Cleared Fault Threshold default 80% | 144–145 | "Fault Clear Threshold" semantics + Max Protection Trip Time interaction | Teoria |
| 5 | Use Maintenance Mode function for main device | 145 | ARMS-style maintenance bit | Workflow |
| 5 | Increase PPE Level by 1 for high marginal IE | 145 | Auto bump category | Workflow |
| 5 | PPE Table | 146–148 | Categories (NFPA 70E 2015 Annex H Table H.3(b)), Notes, Head/Eye, Hand/Arm, Foot, Others 1-5, Warning Label, BG/FG colors, 4 picture cols, FR_Clothing.ss3, Save/Load/Default/Reset | Teoria |
| 5 | ArcFlash menu — Bus Detail, Custom Label, Work Permit, PPE Table, Auto Update, Link/Unlink Fault Study/TCC/Ground/Gap/Equip Type/Working Distance, Export to Excel/.htm/.ss3, User-defined Arc Flash Table, non-3φ, Study Options, Font, Print/Export | 148–151 | Inteira pull-down menu coverage | Workflow |
| 5 | Additional Incident Energy & Flash Boundary additional working distances | 151–153 | 5 IEs add'l, Custom Label Designer fields | Workflow |
| 5 | Shock Approach Boundary Table | 153–154 | ShockBoundary.ss6, voltage range / inches | Teoria |
| 5 | Glove Class (ASTM D 120-95) | 154–155 | Class 00 (≤500V) e Class 0 (≤1000V), 480V → Class 0 recomendado | Teoria |
| 5 | Report Data and Order — 20 fields | 155–158 | Re-arrange + Reset, sort columns | Workflow |
| 5 | Notes Section *N1–*N23, *NESC20-26, *DCAF1-2, *S0-* | 158–159 | 30+ flags semânticos | Teoria |
| 5 | C-lines (Constant IE) on TCC | 163–165 | Show Arcing Fault for Worst-case IE / Other dash-dot, Category C-Lines per NFPA 70E PPE | Teoria |
| 5 | Accumulated Energy from Multiple Contributions | 166–168 | Util/Gen/Motor staircase example, 80% threshold | Teoria |
| 5 | Min/Max Faults effect on PPE class | 169 | Lower fault → longer trip time → higher IE example | Teoria |
| 5 | 3-Phase vs Arcing Fault relationship | 170 | IEEE 1584 base 3-phase bolted, ground/earth functions ignored | Teoria |
| 5 | Important Assumptions (15 itens) | 170–171 | Search topology, fastest trip in branch, worker stationary, ind motor sub-transient, current-limiting fuse repr, etc. | Teoria |
| **6** | **Motor Starting (TMS)** | **173–195** | | |
| 6 | Convert Bus-Node to Bus, add ind motor 100hp | 173–175 | One-Line>Convert to Bus | Workflow |
| 6 | Snap-shot via Load Flow with status=Starting | 176–181 | Status Running→Starting, Constant kVA→Constant Z auto, voltage drop 4%→14% | Workflow |
| 6 | Run>Transient Motor Starting (TMS) | 181–183 | TMS-Select Components, motors/buses, infinite source default | Workflow |
| 6 | TMS-Data Channel View Window — Case1 | 184 | Plot channels select, Cases for full vs reduced voltage | Workflow |
| 6 | TMS-Motors window | 184–185 | Motor model + Load model + current/torque base + WK² (lbs-ft²) inertia + controller (Full Voltage) | Workflow |
| 6 | Library — Typical Graphical Motor + 100HP 1800RPM Fan Exponential Load | 185–187 | Apply/Close library | Workflow |
| 6 | Dynamic Events tab | 187 | Off Line initial, Event Time 1.0s, Start Motor radial, Create Event | Workflow |
| 6 | Run TMS + Plot (Motor Speed, Bus Voltage) | 188–189 | Plot button, multi-channel | Workflow |
| 6 | Auto Transformer starter (tap 0.85, time 15s) | 190–191 | Compare Full Voltage 8.5s vs Auto TX 13.0s start | Workflow |
| 6 | Plot Properties Graph Color Monochrome+Symbol | 192 | Print formatting | Workflow |
| **7** | **Harmonic Analysis (HI_WAVE)** | **197–213** | | |
| 7 | Motor Harmonic Source Subview + library "Typical 6 Pulse IGBT" | 197–198 | Harmonic source profile | Workflow |
| 7 | Run>Harmonic Analysis (HIWAVE) | 199 | Buses (V distortion) + Branches (I distortion) selection | Workflow |
| 7 | HIWAVE Study-Case-Plot | 200–202 | Case1 run, default options | Workflow |
| 7 | Distortion plots (CBL-0001, XF2-0002) | 202 | 30° phase shift Δ-Y visible | Workflow |
| 7 | Capacitor 100 kVAR add | 203–205 | Filter Design button, Capacitor Bank Design, kVAR→μF | Workflow |
| 7 | Case2 vs Case1 — 13th harmonic resonance | 206 | Comparison plot | Workflow |
| 7 | Single Tuned Filter — Harmonic Order to Tune 4.8 | 207 | Capacitor→Filter conversion, tune below dominant harmonic | Workflow |
| 7 | Frequency Scan Plot — Z(f) | 208 | Scan magnitude, resonance elimination | Workflow |
| 7 | Harmonics Datablock + HIWAVE.rpt | 210–212 | Total V/I distortion summary | Workflow |
| **8** | **Transient Stability (I*SIM)** | **216–237** | | |
| 8 | Add Generator (1000 kVA, PQ schedule, 40kW/30kVAR) | 216–218 | New Generator icon, Component Editor schedule | Workflow |
| 8 | Run>Industrial Simulation (ISIM) — Select Components | 219–222 | Sources (Gen + Util), Motors (1 dynamic), Buses, Branches | Workflow |
| 8 | Generator models — Round Rotor Gas Turbine, IEEE 1979 Type 1 Exciter, General Use Governor | 222–224 | 3-model assignment per source | Workflow |
| 8 | Utility Infinite Bus / Infinite Machine | 224–225 | No exciter/governor needed for infinite bus | Workflow |
| 8 | Custom Motor Model — Double Cage Flux Level | 226–230 | Document>Library>Ptw.lib>ISIM Library>Induction Motor Model, Motor Parameter Estimation tool, weighting factors, Inertia 3.0, Load damping 2.0, Nom Torque −0.9 | Workflow |
| 8 | Bus Events — Apply Fault @ 0.1s, Clear @ 0.233s (8 cycles @ 60Hz) | 231 | Bus Model Setup & Dynamic Events | Workflow |
| 8 | Utility Trip Generator @ 0.233s | 232 | Source Model Setup & Event | Workflow |
| 8 | Motor MTRI-0001 Off Line + Start @ 5s | 232 | Re-start after utility loss | Workflow |
| 8 | Plot channels Gen/Util/Motor/Bus V & f | 233–234 | Save during simulation | Workflow |
| 8 | Maximum Simulation Time 50s | 234 | ISIM run | Workflow |
| 8 | Speed Deviation + Bus V plots | 235–236 | Multi-graph compare | Workflow |
| **9** | **Single-Phase / Unbalanced 3-Phase** | **238–258** | | |
| 9 | Run>Unbalanced/Single Phase Studies | 239 | DL + LF + Comprehensive SC, balanced reference | Workflow |
| 9 | UB_LF Current Datablock | 240–241 | Phase A,B,C currents | Workflow |
| 9 | Open-phase scenario (uncheck Phase A on cable) | 241–242 | B+C carry full load, Δ-Y splitting | Workflow |
| 9 | UB Sequence Currents Datablock | 245–247 | Positive/negative/zero seq for relay setting | Workflow |
| 9 | Single-phase Mid-Tap Pole Mount transformer 100 kVA 240V | 247–250 | 240V L-L → 120V L-N | Workflow |
| 9 | LOAD-0002 100 Amps phase A only | 250 | Single-phase load entry | Workflow |
| 9 | UB_SC-SLG Datablock | 254 | Phase A→ground fault | Workflow |
| 9 | Crystal Report Load Flow A,B,C Phases.rpt | 256–257 | Unbalanced LF report | Workflow |
| **10** | **Distribution Reliability** | **260–290** | | |
| 10 | Reliability indices definitions | 260–261 | MTBF, λ, MTTF, Annual Outage, MTTR, ASAI%, EENS, ECOST | Teoria |
| 10 | IEEE indices | 260, 273–275 | SAIFI, SAIDI, CAIDI, ASAI, ASUI, EENS, AENS | Teoria |
| 10 | Reliability Data sub-view per component | 261–267 | Failure rate, restore time, equipment cost, year installed | Workflow |
| 10 | Customer Reliability Data library — IEEE Single Circuit Utility, IEEE Transformer 601-15000V, ERM RAM TX 300kVA-10MVA, IEEE Cable 600V Tray, Heater Electric General CDF Type2 Industrial, Fuse 5-15kV-PREP, IEEE Protective Relays, IEEE LV Breakers, IEEE Disconnect Switch, IEEE MV Breaker | 261–267 | Library refs from IEEE/Hale-Arno paper | Workflow |
| 10 | Cable termination failures (each phase end) | 264 | λ_total = base + N_phases × N_term × λ_term | Teoria |
| 10 | Switching time (disconnect switch) | 264 | Manual isolation logic | Teoria |
| 10 | Run>Reliability Analysis study setup | 268–270 | Disconnect Switches / Include Load Reliability / Replace vs Repair / Fuse Failure Probability + Isolation Time / Alternative Supply / Transfer Load Probability / Age Factor / Evaluation Year | Workflow |
| 10 | Custom Setting Components (per-component override) | 270 | Specific repair vs replace | Workflow |
| 10 | Utility System Configurations (7 choices, Single→Dual SRC w/ Ring Bus) | 276–280 | Cost/reliability trade-off, Propst-Doan PCIC 2000-02 | Teoria |
| 10 | Utility System Evaluation — weighting factors (Reliability/Operability/Maintainability dominated) | 277–280 | Value × Weights%, system value (ex 140 vs 230) | Teoria |
| 10 | Distribution System Configurations (8 choices, Single Radial→Double Bus/Breaker Primary Selective) | 281–285 | Plus "Load Data from Database" auto-sync | Teoria |
| 10 | Custom Damage Function library | 286 | $/kW per duration, per-load CDF | Teoria |
| 10 | Failure Rate / Repair Time Aging Factors (5th-order polynomial) | 288–290 | Curve fitting from historical data, multi-order fitting model | Teoria |
| **11** | **Advanced Topics** | **292–366** | | |
| 11 | Project>Copy As / Backup / Merge | 292 | Backup inclui project + lib + datablocks + custom forms | Workflow |
| 11 | Project>Options groups (Application, One-Line, Library, TCC) | 292–294 | Defaults + override per project | Workflow |
| 11 | Document>Export — DXF / WMF / Enhanced Metafile / Clipboard | 294 | Multi-doc batch export | Workflow |
| 11 | Form Print + Form Layout | 295–297 | TCC + One-line + Title block + Logo no mesmo papel | Workflow |
| 11 | Symbol Generator program | 298 | Custom one-line symbols | Workflow |
| 11 | Custom Datablock Formats | 298–303 | New format, attribute templates (%1.0 %2mps, %a append), vector specs (Phase Sum/Max/A/B/C/AB/BC/CA), R+jI / Mag+Angle / Mag+PF / Mag formats | Workflow |
| 11 | Custom Queries — "All 2 Winding Transformers" | 303–306 | Query+Datablock spreadsheet, transformer/cable/load list | Workflow |
| 11 | User Defined Database Fields (text/number/date/time/currency) | 306 | Project>Options>User Defined Fields, queryable + datablock-able | Workflow |
| 11 | Component Clone | 307–309 | Multi-component copy with new names + same data | Workflow |
| 11 | Copy Data / Paste Data | 311 | Copy from one transformer to multiple | Workflow |
| 11 | Default Project Data | 312 | C:\PTW32\lib\Default, Component>Save as Default | Workflow |
| 11 | Template Files | 313–317 | One-line>Template, Demo project CBL1B branch as reusable template, toolbar shortcut 0–9 | Workflow |
| 11 | Scenario Manager full walkthrough | 319–344 | Clone Base/Clone clone, Activate&Exit, Diff color (peach default), Promote to Base, 3 promotion modes (Unmodified Only/All Fields/Do Not Promote) | Workflow |
| 11 | Data Visualizer detailed | 326–345 | Components/Scenarios/Datablock/Query buttons, Group Data By Component/Attribute, Group Color, Color for Difference, Min/Max columns, Show Difference, Show Comment, Show Min/Max Color, Format save | Workflow |
| 11 | Global Change in Data Visualizer (replace/scale) | 340–342 | Bulk edit selected cells | Workflow |
| 11 | Database Utilities (recover + re-index) | 348 | Project>Database Utilities | Workflow |
| 11 | UNDO unlimited steps | 349 | Destroy / Connect / Disconnect undoable | Workflow |
| 11 | Find component in any one-line/TCC | 350–351 | Edit>Find in One-line, find in TCC, find not in any one-line | Workflow |
| 11 | Data State (Incomplete/Estimated/Complete/Verified) | 352–353 | Toggle Data State Color, query by state, global change in Data Visualizer | Workflow |
| 11 | Auto-generate one-line for TCC drawing | 354–356 | "Go to TCC" creates new TCC.drw | Workflow |
| 11 | Plotting Multiple Protection Functions in Same TCC (Phase + Ground) | 357–360 | Function button, Plotted in TCC checkbox, sensor=Neutral, type=overcurrent | Workflow |
| 11 | Registry Entries / REGDEL utility | 361 | HKEY_CURRENT_USER, ProjectStartup=0/1, Protection=1(HW)/2(SW) | Workflow |
| 11 | On-line Help context-sensitive | 362 | Arrow+question icon | Workflow |
| 11 | Reference Manuals on CD (Doc folder) | 363 | DAPPER/CAPTOR/A_FAULT/IEC_FAULT/Equipment Evaluation/Arc Flash/TMS/HIWAVE/ISIM/Reliability + User's Guide | Teoria |
| 11 | Managing Libraries — copy/paste between libs, sort by ~ prefix, project-specific lib path | 364–365 | Project>Options>Library | Workflow |
| 11 | Project Backup (project + libs only used) | 365 | Backup minimization | Workflow |

---

## B. Matriz Olivas vs PTW Tutorial

| # | Funcionalidade PTW | Olivas atende? | Versão Olivas | Gap específico | Severidade |
|---|---|---|---|---|---|
| 1 | Project file structure (.prj + auto-folder) (§Important Concepts p.5) | ⚠️ | — | Sem informação confirmada de formato .prj/projeto-pasta — Olivas é MVP sem código | P0 |
| 2 | Single component DB referenciado em N one-lines (§p.5–6) | ⚠️ | v3.0.0 (CRDT) | CRDT trata de colaboração multi-usuário, mas falta documentação de arquitetura DB-única-N-views | P0 |
| 3 | Component Editor c/ subviews (Bus, Cable, TX, Util, Load, Motor) (§Part 1 p.52–60) | ❌ | — | UI Component Editor com subviews tabbed não desenvolvido | P0 |
| 4 | One-line drawing engine (push-pin placement, snap, grid, page guides) (§Part 1 p.21–24) | ❌ | — | Editor gráfico interativo PySide6/QGraphicsView ainda não criado | P0 |
| 5 | Symbol rotation 90° / 180° / 270° (§Part 1 p.28) | ❌ | — | Sem editor → sem rotação | P0 |
| 6 | Auto-bus-node em série de impedâncias (§Part 1 p.27) | ❌ | — | Lógica topológica de inserção automática | P0 |
| 7 | Multiple one-line diagrams compartilhando DB (§Part 1 p.30–34) | ❌ | — | Multi-document UI ausente | P0 |
| 8 | Link Tags dinâmicos one-line→one-line/TCC/RPT/PDF (§Part 1 p.35–42) | ❌ | — | Hyperlinks navegáveis na one-line | P1 |
| 9 | Legend Tags (Diamond, Hexagon, etc.) com View>Legend list (§Part 1 p.43–52) | ❌ | — | Anotação visual estruturada | P2 |
| 10 | Bus Load Diversity Factor (§Part 1 p.52) | 🔍 | v1.5.0 (DAPPER 22 NEC) | DAPPER demand load existe, mas factor por bus não confirmado | P1 |
| 11 | Cable Library (Copper/Al, THHN/THWN, magnetic/non-mag, voltage class) (§Part 1 p.54) | ⚠️ | v3.0.x (CAPTOR audit lib) | Foco atual em PD library; lib de cabos NEC/IEC não auditada | P1 |
| 12 | Transformer library (Oil Air, Dry, Pole Mount Single-Phase) (§Part 1 p.56, p.250) | ⚠️ | — | Lib TX típica + Calculator pu→%R/%X não confirmado | P1 |
| 13 | Library link/unlink mechanism com gray-out fields (§Part 1 p.55) | ❌ | — | Decoupling DB↔library para overrides | P1 |
| 14 | Datablock format (input/output, customizável, attribute templates %1.0%2mps %a) (§Part 1 p.60, §Adv p.298–303) | ❌ | — | Display engine de datablocks p/ one-line/TCC/Component Editor | P0 |
| 15 | Toggle Datablock Icon (§Part 1 p.62) | ❌ | — | UI control | P2 |
| 16 | Run>Balanced System Studies (Demand Load + Load Flow + Comprehensive SC) (§Part 2 p.63–64) | ⚠️ | v1.5.0 (DAPPER demand), v3.0.2 (A_FAULT Sprint A) | Demand load ✅ + SC parcial; **Load Flow** Newton-Raphson/Gauss-Seidel **não implementado** | **P0** |
| 17 | A_FAULT (machine multipliers, sep-derived X/R, asym mult, LV duty, Test PF/X/R) (§Part 2 p.63) | ✅ | v3.0.2 | Sprint A entregue | — |
| 18 | IEC_FAULT (IEC 60909) (§Part 2 p.63, §Part 5 p.128) | ⚠️ | — | Mencionado como alternativa em Arc Flash; precisa SC method completo IEC 60909 (Voltage Factor c, Tab 1-3) | **P0** |
| 19 | Comprehensive Short Circuit (parcial X/R, X' decay, separately-derived) (§Part 2/§Part 4 p.111) | ✅ (parcial) | v3.0.2 | Sprint A cobre subset; falta validação contra Reference-Comprehensive-Fault.pdf | P1 |
| 20 | Study Messages window c/ Edit Errors button (§Part 2 p.65) | ❌ | — | Diagnostics UI | P1 |
| 21 | Document>Report — Text (.RPT), RP2, Datablock, Crystal, Crystal XI (§Part 2 p.67–69) | ❌ | — | 4 sistemas de relatório distintos; pelo menos .RPT + spreadsheet | P0 |
| 22 | Crystal Reports (custom formats, BG/FG, ProtDev_Multi/ByBus/Phase_Ground) (§Part 2 p.71, §Part 3 p.105–108) | ❌ | — | 3rd-party reporting integration ou alternativa ReportLab/WeasyPrint | P1 |
| 23 | Datablock Report (Excel export) (§Part 2 p.74–75) | ❌ | — | Spreadsheet reporting | P1 |
| 24 | TCC Drawing creation via Go-To>Go To TCC Drawing (§Part 3 p.89–91) | ⚠️ | v3.0.1 (CAPTOR audit) | CAPTOR mapeado (17 segments + 10 curves) mas UI editor TCC não implementado | **P0** |
| 25 | TCC drag pickup/curve interativo (§Part 3 p.92–95) | ❌ | — | Matplotlib drag handles necessitam canvas customizado | **P0** |
| 26 | TCC Setting tab (OC Pickup, Ext Inverse time, Delete Segment, Redraw) (§Part 3 p.93–96) | ⚠️ | v3.0.1 | Lógica matemática ok; UI ausente | P0 |
| 27 | INST OR / INST override segment (§Part 3 p.93) | ⚠️ | v3.0.1 | Mapeado em 17 segments, validar nomenclatura | P1 |
| 28 | Run>TCC Report (sort by Bus Voltage / etc) (§Part 3 p.99–101) | ❌ | — | Geração de relatório TCC sortable | P1 |
| 29 | TCC Settings datablock + Selected Device Settings menu (§Part 3 p.103–104) | ❌ | — | Display de settings na TCC | P1 |
| 30 | Run>Equipment Evaluation (Protective + Non-Protective) (§Part 4 p.109–111) | ❌ | — | Módulo Equipment Evaluation (rating vs duty + continuous) | **P0** |
| 31 | EE: Branch vs Bus comparison, ANSI/IEC/Comprehensive selectors (§Part 4 p.110–111) | ⚠️ | v3.0.2 (A_FAULT) | A_FAULT pode fornecer base; falta wrapper EE | P0 |
| 32 | EE: Filter por tipo (cable, 2-3W TX, transmission, pi, gen, load, ind/sync motor, schedule, filter) (§Part 4 p.111) | ❌ | — | Componentes ainda não modelados todos | P0 |
| 33 | EE: User-defined limits (Project>Options>Equipment Evaluation) (§Part 4 p.115–117) | ❌ | — | Settings dialog | P1 |
| 34 | EE: Mark Components Failing (red highlight on one-line) (§Part 4 p.114) | ❌ | — | Visual feedback engine | P1 |
| 35 | EE: Input Data Evaluation (componentes c/ dados ausentes) (§Part 4 p.114) | ❌ | — | Validation dashboard | P1 |
| 36 | Arc Flash IEEE 1584 method (§Part 5 p.128) | ✅ | v1.6.0 | Coberto pelos 8 standards | — |
| 37 | Arc Flash NFPA 70E 2015 Annex D.3 (§Part 5 p.122) | ✅ | v1.6.0 | NFPA 70E mapeado | — |
| 38 | Arc Flash DC NFPA 70E 2015 Annex D.5 (§Part 5 p.124) | ✅ | v1.6.0 (DC NFPA 70E) | DC mapeado | — |
| 39 | Arc Flash NESC 2012/2023 (§Part 5 p.124–125) | ✅ | v1.6.0 (NESC 2023) | NESC 2023 mais novo que tutorial PTW | ✅ supera |
| 40 | EPRI Arc Flash (§) | ✅ | v1.6.0 (EPRI) | Tutorial **NÃO menciona** EPRI — Olivas supera | ✅ supera |
| 41 | NBR 17227 (Brasileiro) (§) | ✅ | v1.6.0 | Tutorial **NÃO menciona** NBR — vantagem nacional | ✅ supera (única) |
| 42 | Doughty-Neal, Terzija, CSA Z462 (§) | ✅ | v1.6.0 | Tutorial **NÃO menciona** estes — Olivas supera | ✅ supera |
| 43 | Maximum Arcing Time Duration (default 2s, IEEE 1584 B.1.2) (§Part 5 p.129–130) | ⚠️ | v1.6.0 | Lógica de cap precisa validar; per-bus override ausente | P1 |
| 44 | Arcing Fault Tolerances (−15%/+10% IEEE, 38% NFPA, IEC60909 min/max) (§Part 5 p.130–131) | 🔍 | v1.6.0 | Não confirmado se Olivas roda dual-tolerance | P1 |
| 45 | Pre-Fault Voltage options (LF, PU all, PU each, No Load with Tap) + Tolerance Min/Reg/Max para Util/Cable/TX (§Part 5 p.131–135) | ❌ | — | Voltage tolerance handling completo ausente | **P0** |
| 46 | Reduce Generator/Sync Motor Fault Contribution + Recalculate Trip Time (§Part 5 p.136–137) | ❌ | — | Decay step (1000%→300%) e Recalculate logic | **P0** |
| 47 | Induction Motor Fault Contribution N cycles + hp exclude (§Part 5 p.138) | ⚠️ | v3.0.2 (machine multipliers) | Sprint A toca machines mas exclude logic não confirmada | P1 |
| 48 | Fuses: All Current Limiting / All Standard / Specified in Library + ½ ¼ cycle reduction (§Part 5 p.138–140) | ⚠️ | v3.0.1 (CAPTOR) | CAPTOR cobre curves; current-limiting logic e tabela trip time precisam validar | P0 |
| 49 | Equipment-Specific IE Equations (Arc Flash tab in PD library) (§Part 5 p.140) | ⚠️ | v1.6.0 | Manufacturer-specific equations não mapeadas explicitamente | P1 |
| 50 | Arc Flash Report Options (Bus / PD Load Side / PD Line Side / Bus+Line / Bus+Line+Load) (§Part 5 p.141–143) | ⚠️ | v1.6.0 | 5 modos de report — possivelmente parcial | P1 |
| 51 | Cleared Fault Threshold (default 80%) + Mis-Coordination Ratio + Levels to Search (§Part 5 p.144–145) | ❌ | — | Mis-coordination upstream search | P0 |
| 52 | Maintenance Mode (ARMS-style) main device (§Part 5 p.145) | ❌ | — | Maintenance bit em PD function | P1 |
| 53 | Increase PPE by 1 for high marginal IE (§Part 5 p.145) | ❌ | — | PPE bump rule | P2 |
| 54 | PPE Table (NFPA 70E 2015 Annex H Table H.3(b)) com BG/FG colors, 4 pictures, Notes/Head/Eye/Hand/Arm/Foot/Others 1-5 (§Part 5 p.146–148) | ⚠️ | v1.6.0 | PPE estrutura existe; tabela editável com 4 pictures + 5 Others ausente | P1 |
| 55 | Auto Update Arc Flash Results on system change (§Part 5 p.145) | ❌ | — | Reactive recalc engine | P1 |
| 56 | Custom Label Designer + Work Permit (NFPA 70E 2015) (§Part 5 p.148–149) | ❌ | — | Label designer drag-drop fields | **P0** |
| 57 | Link/Unlink Fault Study/TCC/Ground/Gap/Equip Type/Working Distance per-bus (§Part 5 p.149–150) | ❌ | — | Manual override per-bus | P1 |
| 58 | Export Arc Flash to Excel/.htm/.ss3 (§Part 5 p.150) | ⚠️ | — | Export formato proprietário .ss3 não relevante; CSV/Excel/HTML básico | P2 |
| 59 | Shock Approach Boundary Table (ShockBoundary.ss6) (§Part 5 p.153–154) | ❌ | — | Limited/Restricted/Prohibited approach por voltage range | P1 |
| 60 | Glove Class Table (ASTM D 120-95) (§Part 5 p.154–155) | ❌ | — | Class 00 / 0 etc. customizável | P2 |
| 61 | C-lines (Constant IE) on TCC + Show Arcing Fault current flag (§Part 5 p.163–165) | ❌ | — | Visual aid super-importante para coordenação arc flash | P0 |
| 62 | Accumulated Energy from Multiple Contributions (staircase) (§Part 5 p.166–168) | ⚠️ | v1.6.0 | Lógica deve existir mas sem documentação visual confirmada | P1 |
| 63 | Min/Max Faults effect on PPE (§Part 5 p.169) | ⚠️ | v1.6.0 | Min/max fault handling parcial | P1 |
| 64 | Run>Transient Motor Starting (TMS) (§Part 6 p.181–183) | ❌ | — | Módulo dinâmico TMS completo | **P0** |
| 65 | Snap-shot motor starting via Status Running→Starting + Constant kVA→Constant Z auto (§Part 6 p.181) | ❌ | — | Toggle + LF integration | P0 |
| 66 | Motor model (Typical Graphical Motor library) + Load model (100HP 1800RPM Fan Exponential) (§Part 6 p.185–186) | ❌ | — | Lib motor models | P1 |
| 67 | Controller types (Full Voltage, Auto Transformer, etc) com tap/time control (§Part 6 p.184, p.190) | ❌ | — | Starter library completa | P0 |
| 68 | Dynamic Events (Off Line, Start Motor, Trip, Apply/Clear Fault) (§Part 6 p.187, §Part 8 p.231) | ❌ | — | Event-driven simulator | P0 |
| 69 | TMS Plot Channels (Motor Speed, Bus Voltage) + multi-case compare (§Part 6 p.188–192) | ❌ | — | Plotter time-domain | P0 |
| 70 | Run>Harmonic Analysis (HIWAVE) (§Part 7 p.199) | ❌ | — | Módulo de análise de harmônicos completo | **P0** |
| 71 | Harmonic Source library (Typical 6 Pulse IGBT) (§Part 7 p.198) | ❌ | — | Source spectrum library | P0 |
| 72 | Bus V distortion + Branch I distortion plots (§Part 7 p.200–202) | ❌ | — | Time + frequency domain | P0 |
| 73 | Filter Design (Capacitor Bank Design kVAR↔μF) (§Part 7 p.205) | ❌ | — | Design helper | P1 |
| 74 | Single Tuned Filter (Harmonic Order to Tune 4.8) (§Part 7 p.207) | ❌ | — | Filtro sintonizado modeling | P1 |
| 75 | Frequency Scan Plot (Z(f)) (§Part 7 p.208) | ❌ | — | Resonance detection | P0 |
| 76 | Run>Industrial Simulation (ISIM) — Transient Stability (§Part 8 p.219) | ❌ | — | Estabilidade transitória full | **P0** |
| 77 | Generator dynamic models (Round Rotor Gas Turbine, Salient Pole, etc) (§Part 8 p.222) | ❌ | — | Lib modelos | P0 |
| 78 | Exciter model (1979 IEEE Type 1 etc.) (§Part 8 p.223) | ❌ | — | IEEE std excitation models | P0 |
| 79 | Turbine Governor model (General Use, IEEE) (§Part 8 p.224) | ❌ | — | Governor models | P0 |
| 80 | Custom Motor Model — Double Cage Flux Level + Motor Parameter Estimation tool (§Part 8 p.226–230) | ❌ | — | NEMA/IEEE motor estimator | P1 |
| 81 | Bus Apply/Clear Fault events (8 cycles @ 60Hz typical) (§Part 8 p.231) | ❌ | — | Event-driven dynamics | P0 |
| 82 | Trip Generator event (§Part 8 p.232) | ❌ | — | Source disconnect | P0 |
| 83 | Maximum Simulation Time (50s default) + Speed Deviation/Bus V plots (§Part 8 p.234–236) | ❌ | — | Time integrator + plots | P0 |
| 84 | Run>Unbalanced/Single Phase Studies (DL+LF+SC) (§Part 9 p.239) | ⚠️ | v1.5.0 (DAPPER), v3.0.2 (A_FAULT) | DAPPER e SC parciais; LF unbalanced ausente | **P0** |
| 85 | UB_LF Current datablock (Phase A/B/C) (§Part 9 p.240) | ❌ | — | Phase domain output | P0 |
| 86 | Open-phase scenario (uncheck Phase A) (§Part 9 p.241) | ❌ | — | Per-phase enable/disable | P1 |
| 87 | UB Sequence Currents datablock (pos/neg/zero) (§Part 9 p.245) | ⚠️ | v3.0.2 | A_FAULT toca sequência; datablock display ausente | P1 |
| 88 | Single-phase Mid-Tap transformer (240V L-L → 120V L-N) (§Part 9 p.250) | ❌ | — | Modelo TX 1φ split-phase | **P0** (residencial BR) |
| 89 | Single-phase load (Phase A only) (§Part 9 p.250) | ❌ | — | Load por fase | P0 |
| 90 | UB_SC-SLG datablock (single-line-to-ground fault) (§Part 9 p.254) | ⚠️ | v3.0.2 | A_FAULT cobre SLG mas datablock UI ausente | P1 |
| 91 | Run>Reliability Analysis (Load Point + IEEE indices) (§Part 10 p.260) | ❌ | — | Módulo confiabilidade completo | **P0** |
| 92 | MTBF/λ/MTTF/MTTR/EENS/ECOST per load (§Part 10 p.260) | ❌ | — | Indices calculator | P0 |
| 93 | SAIFI/SAIDI/CAIDI/ASAI/ASUI/EENS/AENS per zone (§Part 10 p.260, p.273–275) | ❌ | — | IEEE 1366 indices (utility) | P0 |
| 94 | Customer Reliability Data library (IEEE 493 Gold Book + Hale-Arno) (§Part 10 p.261–267) | ❌ | — | Lib típica | P1 |
| 95 | Customer Damage Function library (CDF, $/kW por duration) (§Part 10 p.286) | ❌ | — | Cost modeling | P1 |
| 96 | Reliability study setup (Disconnect Switches/Replace vs Repair/Fuse Failure Prob/Alt Supply/Transfer Load Prob/Age Factor/Eval Year) (§Part 10 p.268–270) | ❌ | — | Settings dialog | P1 |
| 97 | Utility System Configurations (7) — Single SRC→Dual SRC w/ Ring Bus + Distribution Configurations (8) (§Part 10 p.276–285) | ❌ | — | Templates Propst-Doan | P1 |
| 98 | Utility/Distribution System Evaluation (Reliability/Operability/Maint Dominated weights) (§Part 10 p.277–280) | ❌ | — | Decision matrix | P2 |
| 99 | Aging Factor (5th-order polynomial fit) Failure Rate + Repair Time (§Part 10 p.288–290) | ❌ | — | Curve fitting historical | P2 |
| 100 | Project>Options>Application (engineering standard ANSI/IEC + units) (§Part 11 p.293) | 🔍 | v2.0.0 (i18n) | i18n cobre lang; standard/units toggle não confirmado | P0 |
| 101 | Project>Backup (project + libs used) (§Part 11 p.292, p.365) | ⚠️ | — | Backup essential | P1 |
| 102 | Project>Copy As + Project>Merge (§Part 11 p.292) | ❌ | — | Project ops | P2 |
| 103 | Document>Export — DXF / WMF / Enhanced Metafile / Clipboard (§Part 11 p.294) | ❌ | — | CAD export integrability | P1 |
| 104 | Form Print (TCC + One-line + Title + Logo) + Form Layout designer (§Part 11 p.295–297) | ❌ | — | Multi-doc layout printer | P1 |
| 105 | Symbol Generator program (custom one-line symbols) (§Part 11 p.298) | ❌ | — | User-extensible symbol lib | P2 |
| 106 | Custom Datablock Formats (attribute templates %1.0%2mps %a, vector specs Phase Sum/Max/A/B/C/AB/BC/CA, R+jI/Mag+Angle/Mag+PF) (§Part 11 p.298–303) | ❌ | — | Format editor poderoso | P1 |
| 107 | Custom Queries (All 2 Winding Transformers etc.) (§Part 11 p.303–306) | ❌ | — | Query engine sobre DB | P1 |
| 108 | User Defined Database Fields (text/number/date/time/currency) (§Part 11 p.306) | ❌ | — | Schema extensível | P1 |
| 109 | Component Clone (multi-copy + new names + same data) (§Part 11 p.307–309) | ❌ | — | Cópia de subseções | P1 |
| 110 | Copy Data / Paste Data (one→many) (§Part 11 p.311) | ❌ | — | Bulk attribute copy | P2 |
| 111 | Default Project Data (C:\PTW32\lib\Default) (§Part 11 p.312) | ❌ | — | Component defaults | P2 |
| 112 | Template Files (One-line>Template, Demo CBL1B Branch, toolbar shortcut 0–9) (§Part 11 p.313–317) | ❌ | — | Template snippets | P1 |
| 113 | Scenario Manager (Clone, Activate&Exit, Diff color peach, Promote to Base, 3 promotion modes) (§Part 11 p.319–344) | ⚠️ | v3.0.0 (CRDT) | CRDT é collab tempo-real, **scenarios são paralelos não-colab**: paradigmas diferentes. Olivas precisa Scenario Manager **adicional** ao CRDT | **P0** |
| 114 | Data Visualizer (Components/Scenarios/Datablock/Query buttons, By Component vs By Attribute, Min/Max columns, Show Difference, Show Comment, Format save) (§Part 11 p.326–345) | ❌ | — | Spreadsheet view multi-scenario | **P0** |
| 115 | Data Visualizer Global Change (replace/scale) selected cells (§Part 11 p.340–342) | ❌ | — | Bulk edit | P1 |
| 116 | Database Utilities (recover + re-index) (§Part 11 p.348) | ❌ | — | Repair tool | P2 |
| 117 | UNDO unlimited steps (Destroy/Connect/Disconnect) (§Part 11 p.349) | ❌ | — | Undo stack | P0 (essencial UX) |
| 118 | Find Component in any one-line/TCC (Edit>Find in One-line) (§Part 11 p.350–351) | ❌ | — | Search engine | P1 |
| 119 | Data State (Incomplete/Estimated/Complete/Verified) + Toggle Data State Color (§Part 11 p.352–353) | ❌ | — | Workflow status flags | P1 |
| 120 | Auto-generate one-line for TCC drawing (Go to TCC creates new .drw) (§Part 11 p.354–356) | ❌ | — | Productivity feature | P2 |
| 121 | Plotting Multiple Protection Functions (Phase + Ground) in same TCC (§Part 11 p.357–360) | ⚠️ | v3.0.1 (CAPTOR) | Curves mapeadas; UI plot multi-function não confirmada | P1 |
| 122 | Library mgmt (copy/paste between libs, ~ prefix sort, project-specific path) (§Part 11 p.364–365) | ⚠️ | v1.5.0 (Marketplace), v3.0.1 (CAPTOR audit) | Marketplace cobre plugins; PD-library Editor manual ausente | P1 |
| 123 | On-line Help context-sensitive (§Part 11 p.362) | ❌ | v2.0.0 (i18n) | Help-as-you-go | P2 |
| 124 | Live SCADA IEC 61850 MMS / GOOSE / SV (§ Não coberto pelo tutorial — necessita Reference-IEC61850) | ✅ | v2.0.0/v2.2.0/v2.2.1 | Tutorial **NÃO menciona** IEC 61850 — Olivas supera | ✅ supera (única) |
| 125 | Real-time CRDT collab multi-user (§ Não coberto pelo tutorial) | ✅ | v3.0.0 | Tutorial **NÃO menciona** colaboração — Olivas supera (mas distinto de Scenarios) | ✅ supera |
| 126 | Plugin Marketplace (§ Não coberto pelo tutorial) | ✅ | v1.5.0/v1.5.1 | Tutorial **NÃO menciona** — Olivas supera (extensibilidade) | ✅ supera |
| 127 | Docker / containerização (§ Não coberto pelo tutorial) | ✅ | v2.0.0 | Tutorial **NÃO menciona** — supera (deploy moderno) | ✅ supera |
| 128 | i18n PT/EN/ES (§ Não coberto pelo tutorial — UI inglês only) | ✅ | v2.0.0 | Tutorial **só em inglês**; mercado BR/LATAM = supera | ✅ supera (única) |

---

## C. Gaps críticos identificados (P0 — bloqueia substituição comercial)

### C.1. Editor One-Line interativo (PySide6/QGraphicsView)
- **O que é**: Canvas drag-drop de componentes (bus, util, TX, cable, motor, load, fuse, relay, breaker, capacitor, gen) com push-pin placement, snap-to-grid, page guides, símbolo rotation, auto-bus-node em série de impedâncias, multi-document.
- **Onde no tutorial**: §Part 1 p.21–34 (Build a System); §Part 11 p.298 (Symbol Generator).
- **Por que crítico**: 100% do tutorial assume one-line é o **ponto de partida**. Sem editor, o software não tem entrada de modelo.
- **Esforço**: **XL** (8–10 sprints, ~3 meses).
- **Sprint sugerido**: v3.1.0 (foundation) + v3.2.0 (refinamento).

### C.2. Component Editor com subviews tabbed
- **O que é**: UI multipanel para edição de cada tipo de componente (Bus, Cable, TX, Util, Load, Motor com 10+ subviews: Rated, Impedance, Library, Reliability Data, Harmonic Source, ISIM Model, Demand Loads, etc.).
- **Onde**: §Part 1 p.52–60; §Part 5/6/7/8/10 (subviews adicionais por estudo).
- **Por que crítico**: Toda data entry passa por aqui. Sem isso, parâmetros são CSV editing manual.
- **Esforço**: **L** (4–5 sprints).
- **Sprint**: v3.1.0–v3.2.0.

### C.3. Load Flow (Newton-Raphson + Gauss-Seidel + Fast Decoupled)
- **O que é**: Estudo balanced/unbalanced de fluxo com voltage drop, power flows, swing/PV/PQ buses, transformer tap+phase shift, VFD load side, Constant kVA / Constant Z / Constant I models.
- **Onde**: §Part 2 p.63–66; §Part 6 p.176–181 (motor starting snap-shot); §Part 9 p.239–258 (unbalanced).
- **Por que crítico**: Load Flow é o estudo **mais usado** por engenheiros antes de qualquer outro. Sem isso, Olivas é apenas "ferramenta de SC + arc flash".
- **Esforço**: **L** (3–4 sprints).
- **Sprint**: v3.3.0.

### C.4. TCC Editor interativo (matplotlib custom canvas com drag handles)
- **O que é**: Plot time-current com pickup e curves arrastáveis em tempo real, curvas IEEE/IEC já mapeadas (v3.0.1), 17 segments, settings tab, INST OR override, C-lines de PPE, fault current flags, Datablock display, multi-protection (Phase+Ground) plot.
- **Onde**: §Part 3 p.89–108 (CAPTOR completo); §Part 5 p.163–165 (C-lines); §Part 11 p.357–360 (multi-function).
- **Por que crítico**: CAPTOR é **o módulo "killer-feature"** do PTW. v3.0.1 já mapeou as curvas — falta a UI.
- **Esforço**: **L** (3–4 sprints, alavanca v3.0.1).
- **Sprint**: v3.4.0.

### C.5. Equipment Evaluation module (rating vs duty + continuous + input data eval)
- **O que é**: Tabela com pass/fail de PD/non-PD vs ratings (continuous + short-circuit), branch vs bus, ANSI/IEC/Comprehensive selectors, Project>Options limits user-defined, Mark Failed (red highlight), Input Data Evaluation.
- **Onde**: §Part 4 p.109–117 (todo Part 4).
- **Por que crítico**: Auditoria EE é entregável obrigatório em projetos elétricos brasileiros (NR-10, NBR 14039).
- **Esforço**: **M** (2 sprints, alavanca v3.0.2 A_FAULT).
- **Sprint**: v3.3.0 (junto a Load Flow).

### C.6. Scenario Manager + Data Visualizer (NÃO substitui CRDT)
- **O que é**: "What-if" scenarios paralelos dentro do mesmo projeto, com Diff color, Promote to Base, 3 modos de promotion. Data Visualizer = spreadsheet multi-scenario com Min/Max columns, Show Difference, Global Change.
- **Onde**: §Part 11 p.319–347.
- **Por que crítico**: PTW vende isso como diferencial — engenheiro não cria 4 projetos copiados, ele faz 4 scenarios. **CRDT (v3.0.0) é colaboração tempo-real, não cenários — paradigmas distintos**.
- **Esforço**: **L** (3 sprints; pode reaproveitar infra CRDT para snapshot).
- **Sprint**: v3.5.0.

### C.7. Pre-Fault Voltage tolerance handling completo
- **O que é**: Load Flow / PU All / PU per Bus / No Load with Tap + Utility/Cable/TX Tolerance Min/Reg/Max em Comprehensive SC e Arc Flash.
- **Onde**: §Part 5 p.131–135.
- **Por que crítico**: Conservatismo regulatório — engenheiro precisa rodar Min/Max para certificar pior caso. Olivas v3.0.2 toca apenas X/R machine multipliers.
- **Esforço**: **M** (1 sprint).
- **Sprint**: v3.0.3 (extension Sprint A).

### C.8. Fault contribution decay (Generator/Sync Motor + Induction Motor cycles + Recalculate Trip Time)
- **O que é**: Decay step (1000%→300% após N cycles), Apply To Generators/Sync Motors, Recalculate Trip Time using reduced current, Induction Motor exclude < hp.
- **Onde**: §Part 5 p.136–138.
- **Por que crítico**: Arc Flash em sistemas com cogeração ou motores pesados subestima energia se decay não é modelado. Crítico para indústria.
- **Esforço**: **M** (1 sprint).
- **Sprint**: v3.0.3 (Sprint B Arc Flash refinement).

### C.9. Reports system (.RPT text + Datablock spreadsheet + Crystal-style PDF)
- **O que é**: Geração automática de relatórios pós-estudo: Text fixed-format, Spreadsheet (Excel/CSV), Crystal-equivalent (ReportLab/WeasyPrint para PDF formatado), printable forms (TCC+One-line+Title+Logo).
- **Onde**: §Part 2 p.67–75; §Part 11 p.295–297 (Form Print).
- **Por que crítico**: Entregável final do projeto = relatório. Sem isso, Olivas é "calculadora", não "ferramenta de engenharia".
- **Esforço**: **L** (3 sprints).
- **Sprint**: v3.4.0 (junto a TCC) ou v3.5.0.

### C.10. Datablock display engine (one-line + TCC + Component Editor)
- **O que é**: Display configurável de qualquer combinação de input/output em qualquer documento. Attribute templates (%1.0 %2mps, %a append), vector specs (Phase Sum/Max/A/B/C/AB/BC/CA), formats (R+jI/Mag+Angle/Mag+PF/Mag).
- **Onde**: §Important Concepts p.10–11; §Part 11 p.298–303.
- **Por que crítico**: É o "tecido conector" entre studies e visualização. Sem isso, results ficam só em tabelas.
- **Esforço**: **M** (2 sprints).
- **Sprint**: v3.2.0 (junto a Component Editor).

### C.11. Single-phase Mid-Tap transformer (split-phase 240/120V) + per-phase load
- **O que é**: TX típico residencial/rural BR (também US). Phase A/B/C enable/disable em loads e cables.
- **Onde**: §Part 9 p.247–252.
- **Por que crítico**: Modelagem de redes de distribuição rurais/comerciais brasileiras requer split-phase.
- **Esforço**: **S** (1 sprint).
- **Sprint**: v3.0.3.

### C.12. UNDO unlimited stack (one-line + Component Editor)
- **O que é**: Edit>Undo para Destroy/Connect/Disconnect/data changes; ilimitado.
- **Onde**: §Part 11 p.349.
- **Por que crítico**: UX baseline moderna; sem undo, usuários perdem confiança.
- **Esforço**: **S** (1 sprint, mas precisa command pattern desde início).
- **Sprint**: v3.1.0 (foundation editor).

### C.13. TMS / HIWAVE / ISIM (Transient Motor Starting + Harmonics + Stability)
- **O que é**: 3 módulos dinâmicos pesados: time-domain motor starting, harmonics frequency-domain, transient stability com generator/exciter/governor models.
- **Onde**: §Part 6 (TMS), §Part 7 (HIWAVE), §Part 8 (ISIM).
- **Por que crítico**: PTW vende isso para indústria de processo (refinarias, mineração). Olivas pode adiar mas não pode ignorar para clientes industriais.
- **Esforço**: **XL** cada (3 sprints × 3 = 9 sprints).
- **Sprint**: v3.6.0 (TMS), v3.7.0 (HIWAVE), v4.0.0 (ISIM).

---

## D. Roadmap de paridade + superação (5–8 sprints)

| Sprint | Versão | Foco | Gaps endereçados | Manuais PTW de referência |
|---|---|---|---|---|
| 1 | **v3.0.3** | Sprint B — Arc Flash refinement + Single-phase + Pre-fault tolerance | #45, #46, #88, #89, #43, #44, #51 (mis-coord) | PTW Tutorial §Part 5 p.131–148 + Reference-Arc-Flash.pdf (não disponível, complementar com IEEE 1584-2018) |
| 2 | **v3.1.0** | Foundation — One-line Editor (canvas + push-pin + symbols) + UNDO stack | #4, #5, #6, #7, #8, #117 | PTW Tutorial §Part 1 p.21–52, §Part 11 p.298, p.349 |
| 3 | **v3.2.0** | Component Editor (subviews tabbed) + Datablock engine + Library link/unlink | #3, #11, #12, #13, #14, #15, #106, #108 | PTW Tutorial §Part 1 p.52–60, §Important Concepts p.10–11, §Part 11 p.298–303 |
| 4 | **v3.3.0** | Load Flow + Equipment Evaluation + Unbalanced studies | #16, #18 (IEC 60909 hardening), #19, #30, #31, #32, #84, #85 | PTW Tutorial §Part 2, §Part 4, §Part 9 + Reference-DAPPER.pdf, Reference-IEC60909.pdf, Reference-Equipment-Eval.pdf (não disponíveis — complementar com IEEE 141 Red Book + IEEE 399 Brown Book) |
| 5 | **v3.4.0** | TCC Editor interativo + Reports system (.RPT/Datablock/PDF) + C-lines + Multi-protection plot | #24, #25, #26, #27, #28, #29, #61, #121, #21, #22, #23, #104 | PTW Tutorial §Part 3, §Part 5 p.163–165, §Part 11 p.295–297, p.357–360 + Reference-CAPTOR.pdf (já parcialmente em v3.0.1) |
| 6 | **v3.5.0** | Scenario Manager + Data Visualizer + Find Component + Data State + Templates + Custom Queries | #113, #114, #115, #118, #119, #112, #107, #109 | PTW Tutorial §Part 11 p.313–356 |
| 7 | **v3.6.0** | TMS (Transient Motor Starting) — snap-shot + dynamic + starter library + plotter | #64, #65, #66, #67, #68, #69 | PTW Tutorial §Part 6 + Reference-TMS.pdf (não disponível — complementar com IEEE 399 Brown Book + NEMA MG 1) |
| 8 | **v3.7.0** | Reliability module (load point + IEEE indices + utility/distribution evaluation) | #91, #92, #93, #94, #95, #96, #97, #98, #99 | PTW Tutorial §Part 10 + IEEE 493 Gold Book (1997) + IEEE 1366 + Hale-Arno paper + Propst-Doan PCIC 2000-02 |
| (9) | (v4.0.0) | HIWAVE + ISIM (full) + Symbol Generator + Form Layout + Global Change | #70–#83, #105, #115 | PTW Tutorial §Part 7, §Part 8, §Part 11 + Reference-HIWAVE.pdf + Reference-ISIM.pdf (não disponíveis) |

---

## Notas finais e observações

- **Vantagens competitivas únicas do Olivas (não cobertas pelo tutorial PTW)**:
  1. **NBR 17227** (norma brasileira) — única no mercado mundial 🏆
  2. **i18n PT/EN/ES** — mercado BR/LATAM desatendido
  3. **Live SCADA IEC 61850 (MMS/GOOSE/SV/ASN.1 BER)** — PTW tutorial **não menciona** IEC 61850
  4. **CRDT colaboração tempo-real** — PTW só tem Scenarios paralelos (não realtime)
  5. **Plugin Marketplace** — extensibilidade open-source
  6. **Docker + Python 3.13** — deploy moderno

- **Convergência: NÃO confundir CRDT com Scenarios** (§gap C.6). O Scenario Manager do PTW é "branching paralelo dentro do mesmo arquivo de projeto, com merge promotion". CRDT é "edição sincronizada entre usuários no mesmo modelo". Ambos são necessários e independentes — Olivas precisa **adicionar** Scenarios sem perder o CRDT.

- **Áreas marcadas como 🔍 ambíguas** (#10 Bus Load Diversity, #44 Arcing Fault Tolerances, #100 Application standard toggle): requerem inspeção do código fonte v3.0.x ou docs internas para confirmação antes de classificação definitiva.

- **Itens marcados "necessita complementar com Reference-XYZ.pdf"** (linhas Roadmap): o tutorial é didático mas superficial; profundidade técnica está nos manuais Reference (DAPPER, CAPTOR, A_FAULT, IEC_FAULT, Equipment Eval, Arc Flash, TMS, HIWAVE, ISIM). Recomenda-se adquirir/extrair estes PDFs para auditoria de v3.4.0 em diante.

- **Esforço total estimado**: ~30–35 sprints (de v3.0.3 até v4.0.0), aproximadamente **9–12 meses** com 1 dev senior + colaboração open-source. Para v3.5.0 (paridade funcional mínima de mercado): ~6 sprints, **4–5 meses**.

- **Crítica metodológica**: O tutorial PTW v8.0 é de **2019**. Releases pós-2019 do PTW (v9, v10, v11) podem ter mudanças que não estão neste audit. A v11 atual em campo provavelmente tem features adicionais (Cloud, ML, IEC 61850?) que precisam audit complementar via Release Notes do site SKM.

- **Recomendação imediata**: Validar este audit com um engenheiro PTW user (NDA) em 1–2 sessões de 1h para calibrar Severidades e descobrir features ocultas (não-tutorial).

---

**Auditoria registrada em** `docs/PTW_TUTORIAL_AUDIT_v3.0.3.md` (commit gerado em 2026-04-30, sessão v3.0.2 → v3.0.3).
**Plano de ação derivado**: `docs/PTW_PARITY_ACTION_PLAN.md`.