# PTW Total Parity Directive — 100% paridade + superação obrigatória

**Data**: 2026-04-30
**Vigência**: a partir de v3.0.3 (próxima release) — permanente
**Ordem**: pedido formal do usuário (sessão 2026-04-30, pós-audit Tutorial PTW)
**Status**: ✅ Registrado — vincula todas as releases v3.x.x e v4.x.x

---

## 1. Diretriz formal

> **"100% das funcionalidades do PTW devem estar presentes no Olivas,
> e o Olivas deve superá-las."**
> — Landerson Ferreira Silva, 2026-04-30

Esta diretriz **endurece** a 6ª garantia do Master Protocol
(originalmente "paridade + superação") para **paridade total + superação obrigatória**.

### 1.1 O que muda

| Antes (v3.0.1) | Agora (v3.0.3+) |
|----------------|-----------------|
| "Cada release contribui para paridade ou superação" | **Cada release contribui para 100% paridade E também superação** |
| Items P2 podem ser deferred | **Não há deferrals** — só sequenciamento |
| "Superação" era opcional/oportunista | **Superação é obrigatória** para cada feature implementada |
| Audit identificava gaps; "fica para v4+" era aceitável | **Audit identifica gaps; cada gap recebe sprint dedicado** |

### 1.2 Definições operacionais

**Paridade (≡)**: Olivas implementa a feature do PTW com **funcionalidade
equivalente ou maior**, validada por:
1. Reprodução do(s) exemplo(s) do tutorial/manual (golden values)
2. Cobertura de testes ≥ 80% no módulo correspondente
3. Documentação cita seção+página do manual PTW

**Superação (⨠)**: Olivas oferece **vantagem mensurável** sobre a feature
PTW. Aceitam-se 8 dimensões de superação:

| # | Dimensão | Critério |
|---|----------|----------|
| 1 | **Profundidade técnica** | Mais normas/standards cobertos OU fórmulas mais recentes |
| 2 | **Abertura** | API Pythonica embutível + open-source vs PTW closed |
| 3 | **Anti-alucinação** | Citações inline `§x.y p. NN` em código + testes pareados |
| 4 | **Composição** | Funcionalidade combinável com outras (ex: ANSI + IEC side-by-side) |
| 5 | **Internacionalização** | i18n PT/EN/ES (PTW só EN) |
| 6 | **Modernidade técnica** | Docker, CRDT, IEC 61850, Plugin Marketplace |
| 7 | **UX** | Atalhos, undo ilimitado, busca, hot-reload |
| 8 | **Custo** | OSS + dual license (PTW = caro + FlexLM) |

**Para cada feature PTW implementada, declarar EXPLICITAMENTE qual(is)
das 8 dimensões aplicam-se à superação.** Não é aceitável
"implementação só em paridade" — sempre haverá uma dimensão de superação.

## 2. Reorganização do roadmap (removendo deferrals)

A auditoria do PTW Tutorial v8.0 (`docs/PTW_TUTORIAL_AUDIT_v3.0.3.md`)
mapeou **124 features**, das quais:
- 12 já cobertas
- 6 já superadas
- 19 parciais
- 84 não implementadas
- 3 ambíguas

**Sob a nova diretriz, todas as 124 + as 6 superações únicas precisam
estar na release final v4.0.0**, sem exceções.

### 2.1 Nova classificação (3 níveis, sem P2 "nice-to-have")

| Nível | Antes | Agora | Significado |
|-------|-------|-------|-------------|
| **P0 (Tier 1)** | "Bloqueia substituição comercial" | "Tier 1 — paridade fundacional" | Editor, engine, core studies |
| **P1 (Tier 2)** | "Esperado em ferramenta industrial" | "Tier 2 — paridade industrial" | Library mgmt, reports, exports |
| **P2 (Tier 3)** | "Conveniências (nice-to-have)" | **"Tier 3 — paridade completa"** | TODO o resto: Symbol Generator, REGDEL, Aging Factor, Database Utilities, etc. |

**Tier 3 NÃO É deferral — é o último a ser entregue, mas ENTREGUE.**

### 2.2 Marcos de cobertura

| Versão | Cobertura PTW | Itens superados | Comentário |
|--------|---------------|-----------------|------------|
| v3.0.2 (atual) | 18/124 (15%) | 6 | Baseline |
| v3.0.3 | 25/124 (20%) | 7 | A_FAULT Sprint B + Single-phase |
| v3.1.0 | 32/124 (26%) | 8 | One-line Editor foundation |
| v3.2.0 | 45/124 (36%) | 10 | Component Editor + Datablock |
| v3.3.0 | 60/124 (48%) | 12 | Load Flow + EE + Unbalanced |
| v3.4.0 | 75/124 (60%) | 14 | TCC Editor + Reports |
| v3.5.0 | 90/124 (73%) | 16 | Scenarios + Data Visualizer |
| v3.6.0 | 100/124 (81%) | 18 | TMS |
| v3.7.0 | 110/124 (89%) | 20 | Reliability |
| **v4.0.0** | **124/124 (100%)** | **22+** | **Paridade total atingida** |
| **v4.1.0** | **124/124** | **30+** | **Superação cumulativa em todas as features** |

**Marco simbólico v4.0.0**: "PTW Tutorial 100% reproduzível em Olivas".
**Marco simbólico v4.1.0**: "Para cada feature PTW, Olivas tem ≥ 1 dimensão de superação documentada".

## 3. Matriz de Superação por feature (template + 20 exemplos)

Para cada uma das 124 features PTW, declarar a(s) dimensão(ões) de
superação (ver tabela 1.2). Abaixo, **20 exemplos canônicos** para
estabelecer o padrão; a matriz completa será preenchida progressivamente.

| # | Feature PTW | Versão Olivas | Dimensão(ões) de superação | Como supera |
|---|-------------|---------------|---------------------------|-------------|
| 17 | A_FAULT machine multipliers (§1.2.5) | v3.0.2 | 2, 3, 4 | API embutível `from app.standards.ansi_c37 import machine_multiplier`; citação inline `§1.2.5 p. 1-8`; composável com IEC 60909 |
| 18 | IEC_FAULT (IEC 60909) | v3.3.0 | 1, 4 | Cobertura adicional de Voltage Factor c (Tab 1-3); composável side-by-side com ANSI C37 |
| 36 | Arc Flash IEEE 1584 | v1.6.0 | 1, 4 | 8 standards side-by-side (PTW cobre só IEEE 1584+NFPA 70E+NESC) |
| 37 | NFPA 70E 2015 D.3 | v1.6.0 | 1 | Olivas usa NESC 2023 (mais novo que tutorial v8.0/2019) |
| 39 | NESC 2012/2023 | v1.6.0 | 1 | Versão 2023 vs 2012 do tutorial |
| 40 | EPRI Arc Flash | v1.6.0 | 1, 4 | Tutorial PTW NÃO cobre — Olivas adiciona |
| 41 | NBR 17227 | v1.6.0 | 1, 5 | **Único no mundo** — PTW não cobre normas BR |
| 42 | Doughty-Neal / Terzija / CSA Z462 | v1.6.0 | 1, 4 | Tutorial PTW NÃO cobre estes |
| 113 | Scenario Manager | v3.5.0 | 4, 6 | Compõe com CRDT (PTW não tem realtime collab) |
| 114 | Data Visualizer | v3.5.0 | 4, 7 | Compõe com plugin Marketplace para custom views |
| 124 | IEC 61850 (live SCADA) | v2.0.0/v2.2.x | 1, 6 | Tutorial PTW NÃO cobre — única no mercado nacional |
| 125 | CRDT real-time collab | v3.0.0 | 4, 6 | Tutorial PTW NÃO cobre — paradigma novo |
| 126 | Plugin Marketplace | v1.5.0 | 2, 6 | Tutorial PTW NÃO cobre — extensibilidade open-source |
| 127 | Docker | v2.0.0 | 6, 8 | Tutorial PTW NÃO cobre — deploy moderno |
| 128 | i18n PT/EN/ES | v2.0.0/v2.1.0 | 5 | Tutorial PTW só EN — mercado BR/LATAM |
| 4 | One-line drawing engine | v3.1.0 | 2, 6, 7 | PySide6/Qt + open-source; UNDO ilimitado desde dia-0 |
| 14 | Datablock format engine | v3.2.0 | 2, 4, 7 | Format editor open + composição com plugins de visualização |
| 16 | Run>Balanced System Studies (DAPPER+LF+SC) | v3.3.0 | 1, 3, 4 | TDD com Stevenson 3-bus + IEEE 14-bus golden values; cita IEEE 141/399 inline |
| 24 | TCC Drawing | v3.4.0 | 1, 4 | Multi-function (Phase+Ground+SLG+...) simultâneas no mesmo TCC; PTW só Phase OR Ground por vez na v8.0 |
| 91 | Reliability Analysis | v3.7.0 | 1, 3 | IEEE 1366 + IEEE 493 inline; testes pareados com Hale-Arno paper exemplo |

**Total Tier 1 features mapeadas neste exemplo**: 20.
**A matriz completa (124 linhas) será mantida em `docs/PTW_SURPASSING_MATRIX.md`** — preenchida durante cada sprint, requisito obrigatório para fechar release.

## 4. Critério de aceite para fechamento de release

A partir de **v3.0.3**, nenhuma release pode ser fechada sem:

1. ✅ TodoWrite completo das features PTW endereçadas no sprint
2. ✅ Cada feature implementada cita seção+página do manual em docstring
3. ✅ Cada feature tem entrada na `PTW_SURPASSING_MATRIX.md` com ≥ 1 dimensão de superação
4. ✅ Testes próprios cobrem ≥ 80% do módulo novo (≥ 5 testes mínimo)
5. ✅ Sweep targeted regression verde
6. ✅ Restore point criado
7. ✅ Handoff doc + SESSION_HANDOFF atualizados
8. ✅ Smoke test reproduzindo exemplo do tutorial (quando aplicável)

**Sem isso, a release é "draft", não "released"**. Versão `version.py`
não bumpa até passar nos 8 critérios.

## 5. Implicações práticas no fluxo de trabalho

### 5.1 Ordem dentro de cada sprint

1. Audit do manual relevante (se ainda não existir)
2. TDD: escrever testes com valores do manual citados
3. Engine: stdlib quando possível, Pydantic schemas
4. UI: command pattern para UNDO desde dia-0
5. Update da `PTW_SURPASSING_MATRIX.md`
6. Targeted sweep
7. Restore point + handoff doc

### 5.2 O que não é aceitável

| ❌ Anti-pattern | ✅ Padrão correto |
|---------------|-------------------|
| "Vamos fazer paridade agora, superação fica para depois" | Sempre ≥ 1 dimensão de superação por feature, declarada na release |
| "Esse item é P2, deixa para v5" | Sempre Tier 1/2/3 — Tier 3 é último, mas é entregue |
| "Implementei mas o teste é só smoke" | ≥ 80% cobertura no módulo novo + golden value se possível |
| "Não cita o manual porque não tenho aqui" | Adquirir/extrair o manual ANTES de codar |
| "Vou simplificar — só faço o caso comum" | Cobertura completa do que o tutorial demonstra |

### 5.3 O que é encorajado

- **Composição**: features que combinam capacidades viram superação por dimensão 4
- **Validação cruzada**: rodar mesmo problema em ANSI + IEC + Comprehensive
- **Plugins**: cada nova feature considera se o Marketplace pode ser entry-point para extensões customizadas
- **i18n desde dia-0**: novas strings UI sempre passam por `_()` para PT/EN/ES
- **CRDT-friendly**: estruturas de dados imutáveis ou com merge bem definido

## 6. Riscos e mitigações da diretriz

| # | Risco | Mitigação |
|---|-------|-----------|
| 1 | Escopo balão (124 features × superação cada) | Tier 3 (~30 features) entregam superação trivial (só "open-source + i18n") |
| 2 | Timeline pressionada | Estimativa atual 9–12 meses; aceitar slip se qualidade for sacrificada |
| 3 | Manuais Reference faltando (DAPPER, IEC_FAULT, etc.) | Bloqueia sprint correspondente até manual ser obtido — não codar sem fonte |
| 4 | Validação golden values demanda exemplos do tutorial | Reprodução do exemplo do tutorial é parte do teste de aceite |
| 5 | Risco de over-engineering em features Tier 3 | Aceita-se superação mínima (dim. 2 + 5 + 6 são "free" se Olivas é OSS Python i18n Docker) |
| 6 | Plugin Marketplace pode não ser entry-point natural | Aceita-se que algumas features Tier 3 superam apenas por dim. 2/5/6, não por extensibilidade |

## 7. Recomendação de aquisição de manuais Reference

Os seguintes manuais **devem ser obtidos** para sprints v3.3.0+:

| Manual | Sprint dependente | Status |
|--------|-------------------|--------|
| Reference-DAPPER.pdf | v3.3.0 | ⚠️ verificar `LIB/PTW_MANUAL/` |
| Reference-IEC60909.pdf | v3.3.0 | ⚠️ verificar |
| Reference-Equipment-Eval.pdf | v3.3.0 | ⚠️ verificar |
| Reference-CAPTOR.pdf | v3.4.0 | ✅ já auditado v3.0.1 |
| Reference-A_Fault.pdf | v3.0.3 | ✅ já auditado v3.0.2 |
| Reference-TMS.pdf | v3.6.0 | ⚠️ verificar |
| Reference-HIWAVE.pdf | v3.7.0/v4.0.0 | ⚠️ verificar |
| Reference-ISIM.pdf | v4.0.0 | ⚠️ verificar |
| Reference-Reliability.pdf | v3.7.0 | ⚠️ verificar |
| PTW Version 11 Enhancements.pdf | v3.0.x+ | 🔴 crítico — features pós-2019 |

**Ação imediata recomendada**: rodar inventário de `LIB/PTW_MANUAL/`
para confirmar quais manuais Reference já estão localmente; os
ausentes viram blockers de sprint até serem obtidos.

## 8. Atualização do Master Protocol

A 6ª garantia é **revisada** a partir desta data:

### 8.1 Texto antigo (v3.0.1)

> **6. Paridade + Superação vs PTW** — esta release contribui para
> paridade ou superação vs PTW? Cita manual?

### 8.2 Texto novo (v3.0.3+)

> **6. Paridade Total + Superação Obrigatória vs PTW** —
> 1. **Auditar** manual antes de codar; citar `§seção p. página` em código + testes
> 2. **Implementar 100%** das features do tutorial/manual coberto pelo sprint
> 3. **Declarar EXPLICITAMENTE** ≥ 1 dimensão de superação (das 8 listadas) na `PTW_SURPASSING_MATRIX.md`
> 4. **Reproduzir exemplo do tutorial** como golden test sempre que possível
> 5. **Bloquear release** se algum dos 8 critérios de aceite (§4) não passar

### 8.4 8ª garantia ⚡ NOVA (registrada 2026-05-01, vigência v3.5.0+)

> **8. Context Preservation (continuidade entre sessões)** — *Toda
> sessão Claude DEVE deixar registro auditável suficiente para que
> uma nova sessão (com contexto limpo) continue exatamente de onde
> parou, sem perder decisão arquitetural, débito técnico ou achado
> de auditoria.*
>
> **Critérios formais de aceite** (adicionados aos 11 anteriores):
> 12. Documentos canônicos (SESSION_HANDOFF, SKIPPED_BACKLOG, CONTEXT_PRESERVATION_PROTOCOL, PTW_TOTAL_PARITY_DIRECTIVE) atualizados a cada release
> 13. Quando context > 70%, prioridade muda para finalização e doc-update
> 14. Quando context > 90%, ATIVA protocolo de finalização emergencial (5 passos do CONTEXT_PRESERVATION_PROTOCOL §6)
>
> **Documento canônico**: `docs/CONTEXT_PRESERVATION_PROTOCOL.md`.
>
> **Justificativa**: a janela de contexto é finita; sem protocolo,
> sessões longas perdem detalhes técnicos críticos no compactation
> automático. A 8ª garantia formaliza o que era prática implícita.

### 8.3 7ª garantia ⚡ NOVA (registrada 2026-04-30, vigência v3.1.0+)

> **7. Acessibilidade GUI obrigatória** — *Toda feature backend
> implementada DEVE ter ponto de entrada acessível ao usuário no GUI
> (menu, toolbar, dialog, property panel ou paleta). Backend órfão é
> proibido a partir de v3.1.0.*
>
> **Critérios formais de aceite GUI** (adicionados aos 8 anteriores):
> 9. Cada novo módulo backend tem **trigger GUI** documentado (menu/toolbar/dialog) **antes** do release fechar
> 10. **Deep GUI audit** após cada sprint backend — cross-reference com `app/gui/main_window.py` para verificar 0 órfãos
> 11. **Smoke test manual** (descrito no handoff): "Para usar a feature X, o usuário clica em..."
>
> **Aplicação retroativa**: módulos órfãos pré-v3.1.0 (A_FAULT Sprints
> A+B+C+D, ~10 módulos) entram no backlog **bloqueante** de v3.1.0
> sob Track B (Backfill GUI). Ver `docs/v3.1.0_GUI_AUDIT.md`.
>
> **Justificativa**: a 6ª garantia exige paridade + superação vs PTW,
> mas paridade só é real se o **usuário consegue acessar a feature**.
> Backend perfeito sem GUI = zero paridade prática.

## 9. Próximos passos imediatos

1. ✅ Documento `docs/PTW_TOTAL_PARITY_DIRECTIVE.md` criado (este)
2. ⏳ Inventariar `LIB/PTW_MANUAL/` para mapear manuais disponíveis
3. ⏳ Criar `docs/PTW_SURPASSING_MATRIX.md` com 124 linhas (template, preenchimento incremental)
4. ⏳ Re-escrever `docs/PTW_PARITY_ACTION_PLAN.md` removendo "deferrals" e categoria P2; reclassificar como Tier 1/2/3
5. ⏳ Atualizar `docs/PTW_PARITY_OBJECTIVE.md` com o novo texto da 6ª garantia
6. ⏳ Atualizar `docs/SESSION_HANDOFF.md` com pointer para esta diretriz
7. ⏳ Iniciar **v3.0.3 Sprint B** sob o novo regime (audit Reference-A_Fault.pdf §1.4–1.5; reproduzir Cases §1.4.1)

## 10. Compromisso público

Este documento é o **compromisso formal** assinado pela sessão de
2026-04-30 entre o usuário (Landerson) e o agente (Claude/Olivas).

**Toda release v3.x.x e v4.x.x respeitará esta diretriz.** A não-observância
em qualquer sprint é razão suficiente para reabrir a release como draft.

---

**Vinculação cruzada**:
- Manual Protocol original: `docs/v1.7.0_MASTER_PROTOCOL.md` (5 garantias)
- Safeguards: `docs/v1.6.0_SAFEGUARDS_PROTOCOL.md`
- 6ª garantia inicial: `docs/PTW_PARITY_OBJECTIVE.md`
- Audit Tutorial: `docs/PTW_TUTORIAL_AUDIT_v3.0.3.md`
- Action Plan operacional: `docs/PTW_PARITY_ACTION_PLAN.md`
- **Esta diretriz: `docs/PTW_TOTAL_PARITY_DIRECTIVE.md`** — máxima autoridade sobre as anteriores em caso de conflito
