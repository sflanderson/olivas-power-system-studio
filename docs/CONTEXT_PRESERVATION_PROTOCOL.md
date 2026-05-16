# Context Preservation Protocol — 8ª garantia (continuidade entre sessões)

**Criado**: 2026-05-01 (sessão v3.4.0 → v3.5.0)
**Origem**: aviso de janela de contexto próxima do fim
**Status**: ⚡ **PROTOCOLO PERMANENTE ATIVO** — máxima autoridade após Master Protocol 7 garantias

---

## 1. Por que existe

A janela de contexto do Claude (mesmo Sonnet 4.7-1M) tem limite. Quando
sessões longas ultrapassam ~80% da janela, há risco de:

* **Perda de raciocínio em curso** — Claude pode "esquecer" um achado
  do início da sessão
* **Compactação automática** — sistema resume conversas, perdendo
  detalhes técnicos críticos
* **Continuidade quebrada** — nova sessão sem briefing perde tempo
  recuperando contexto

**8ª garantia formal**: *toda sessão DEVE deixar registro auditável
suficiente para que uma nova sessão Claude (com contexto limpo)
continue exatamente de onde parou, sem perder nenhuma decisão
arquitetural, débito técnico ou achado de auditoria.*

## 2. Documentos canônicos para reler ao iniciar nova sessão

**Ordem obrigatória de leitura** (toda nova sessão Claude DEVE ler estes
em sequência antes de tomar qualquer ação):

| Ordem | Doc | Razão |
|-------|-----|-------|
| 1 | `docs/SESSION_HANDOFF.md` | Estado atual + 7 garantias + última sessão |
| 2 | `docs/CONTEXT_PRESERVATION_PROTOCOL.md` (este) | Protocolo + onde está cada coisa |
| 3 | `docs/SKIPPED_BACKLOG.md` | Débito técnico ativo (anti-esquecimento) |
| 4 | `docs/PTW_TOTAL_PARITY_DIRECTIVE.md` | 6ª garantia formal "100% paridade" |
| 5 | `docs/PTW_SURPASSING_MATRIX.md` | Estado das 167 features PTW + supera ações |
| 6 | `docs/v<X.Y.Z>_HANDOFF.md` | Última release entregue |
| 7 | `docs/v<X.Y.Z+1>_AUDIT.md` ou similar | Audit ativo se houver |

**Nunca pular**. Ler todos antes de propor qualquer mudança.

## 3. Protocolos críticos aprendidos (auditáveis)

Cada protocolo abaixo deve ser aplicado em TODA release, sem exceção.
Se um deles é violado, a release é **draft**, não released.

### 3.1 Anti-alucinação
- Cita `§seção p. NN` do manual citado em **toda** fórmula/constante
- Golden tests pareados com valores publicados (PTW Tutorial, IEC 60909, IEEE 1584)
- Se valor numérico ambíguo no manual, marca 🔍 e busca fonte primária
- **Nunca** invente fórmula/constante de memória — sempre source-cite

### 3.2 Anti-perda de dados
- `Read` antes de `Edit` (sempre)
- Restore point criado a CADA release antes de tocar código
- Edits cirúrgicos: nunca editar arquivos da "lista TRAVADA"
- Backward-compat: campos novos são `Optional[...] = None`

### 3.3 Anti-débito técnico invisível
- Toda feature pulada → registrada em `docs/SKIPPED_BACKLOG.md`
- Cap **15 itens** simultâneos no SKIPPED_BACKLOG
- Revisão a cada 2 releases (ler o doc no início do sprint planning)
- Promotion forçada se 3+ releases sem revisita

### 3.4 Anti-falta-de-integração-GUI (7ª garantia)
- Toda feature backend DEVE ter trigger GUI documentado
- Audit pós-sprint: cross-reference `app/gui/` vs novos módulos
- Se feature backend é órfã GUI → P0 imediato (não defere)
- Smoke test manual descrito em handoff: "Para usar X, user clica em..."

### 3.5 Anti-fragmentação de testes
- Sweep regression a CADA release: `pytest tests/test_pp_v3_*.py -q`
- Threshold: **0 regressões** ou release é draft
- Cobertura mínima 80% em módulos novos

### 3.6 Anti-perda de contexto (8ª garantia — esta)
- Quando contexto > 70%, **prioritize** atualizar docs canônicos
- Quando contexto > 90%, **stop new work**, finalize current sprint, write handoff
- Sempre criar `restore_point` antes de risco de timeout
- TodoWrite atualizado a cada sub-task completed (visibilidade externa)

## 4. Estado canônico atual (snapshot 2026-05-01)

### 4.1 Versão e baseline
- **Versão atual**: v3.4.0
- **Próxima planejada**: v3.5.0 — Scenario Manager (Tier 1 organização)
- **Restore points**: 26
- **Sweep verde**: 488 tests
- **Última release**: `docs/v3.4.0_HANDOFF.md`

### 4.2 Master Protocol — 7 garantias ativas
1. Auditar — antes de codar
2. Registrar — TodoWrite + handoff
3. Anti-alucinação — citações + golden tests
4. Anti-regressão — sweep targeted
5. Restore point — snapshot por release
6. Paridade Total + Superação vs PTW (revisada 2026-04-30)
7. Acessibilidade GUI obrigatória (formalizada 2026-04-30 v3.1.0)
8. Context Preservation (este, formalizado 2026-05-01)

### 4.3 SKIPPED_BACKLOG (11 itens — anti-esquecimento)
Ver `docs/SKIPPED_BACKLOG.md`. Política: cap 15, revisão bi-release.

### 4.4 Manuais auditados profundamente (4)
1. CAPTOR (v3.0.1)
2. A_Fault (v3.0.2-v3.0.5)
3. PTW Tutorial v8.0 (v3.0.3 — 167 features mapeadas)
4. (parcial) ANSI/IEEE C37.5/C37.010 + IEC 60909-0:2016

### 4.5 Cobertura PTW
- **51/167 (31%)** features Tutorial cobertas
- Marco v4.0.0: paridade total (167/167)
- Marco v4.1.0: superação total (≥1 dimensão por feature)

## 5. Como nova sessão DEVE continuar

### 5.1 Checklist de boot

```
[ ] Ler docs/SESSION_HANDOFF.md (sempre primeiro)
[ ] Ler docs/CONTEXT_PRESERVATION_PROTOCOL.md (este)
[ ] Ler docs/SKIPPED_BACKLOG.md
[ ] Ler último docs/v<X.Y.Z>_HANDOFF.md
[ ] Ler docs/PTW_TOTAL_PARITY_DIRECTIVE.md (refresh garantias)
[ ] Verificar VERSION via app/core/version.py
[ ] Rodar smoke test: pytest tests/test_pp_v3_<latest>_*.py -q
[ ] Se sweep verde, ok proceder; se vermelho, fix antes
```

### 5.2 Ações proibidas

❌ Tomar decisão arquitetural sem reler `PTW_TOTAL_PARITY_DIRECTIVE.md`
❌ Adicionar feature backend sem trigger GUI (7ª garantia)
❌ Skip item técnico sem registrar em `SKIPPED_BACKLOG.md`
❌ Codar fórmula técnica sem citação `§seção p. NN`
❌ Editar arquivos da "lista TRAVADA" Master Protocol
❌ Fechar release com testes vermelhos

### 5.3 Ações obrigatórias

✅ TodoWrite atualizado a cada sub-task
✅ Restore point antes de risco de timeout
✅ Handoff doc + SESSION_HANDOFF + SURPASSING_MATRIX a cada release
✅ Smoke test manual descrito ("Para usar X, user clica em...")
✅ Audit GUI cross-reference para novos módulos backend
✅ Sweep targeted regression antes de bump version

## 6. Sinais de fim de janela de contexto

Quando vir QUALQUER destes sinais, ATIVE protocolo de finalização:

1. System reminder mencionando "compactation" ou "context window"
2. TodoWrite com >10 itens in_progress (overload)
3. Sessão > 50 chapters via `mcp__ccd_session__mark_chapter`
4. Aviso explícito do usuário sobre context

**Protocolo de finalização emergencial** (5 passos):

```
1. STOP novo trabalho — não comece sub-sprint adicional
2. Finalize sub-sprint atual COM testes verdes
3. Atualize SESSION_HANDOFF + SKIPPED_BACKLOG (mesmo se incompleto)
4. Crie restore point
5. Escreva handoff doc da release atual (mesmo se reduzida)
```

## 7. Lições aprendidas (registradas)

### v3.0.x (A_FAULT)
- Anti-alucinação: golden tests com valores publicados é o padrão ouro
- Audit profundo via agente paralelo > leitura sequencial

### v3.1.x (Editor)
- Editor existente (~7800 LOC) → audit reduziu XL para incremental
- linked_library wiring gap só foi descoberto em audit retroativo v3.2.0

### v3.2.0
- 7ª garantia (acessibilidade GUI) formalizada
- Audit retroativo expôs gap PpProperty → PropertyRow

### v3.3.x
- Audit pré-sprint identificou 8 achados; v3.3.1 fechou 4 deferreds
- Padrão de auditar ANTES de codar é validado

### v3.4.0
- SKIPPED_BACKLOG persistente criado para evitar débito invisível
- Cap 15 + revisão bi-release adotado

### v3.5.0+ (futuras lições)
- (preencher conforme aprende)

## 8. Compromisso público

Este protocolo é o **contrato de continuidade** da sessão Olivas Power
System Studio. Qualquer Claude (atual ou futura sessão) que ler este
documento concorda implicitamente em segui-lo.

**Anti-perda de contexto**: se você é uma nova sessão Claude lendo
isto e o usuário disse "continuar de onde parou" sem mais detalhes,
SIGA o checklist da §5.1 antes de qualquer ação.

---

**Atualizado por**: sessão v3.4.0 → v3.5.0 (2026-05-01)
**Próxima revisão obrigatória**: a cada release que adicionar/fechar
itens no SKIPPED_BACKLOG.
